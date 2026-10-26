"""Explicit test-only Gemma REST evaluation; never imports/changes the gateway.

All saved request bodies are synthetic. Headers and credential files are never
copied. No automatic schema repair, answer repair, service restart or activation.
"""
import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import httpx
import jsonschema
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'tmp/phase-g/iterations/20261025-gemma4-31b'
HISTORY = ROOT / 'tmp/phase-g/iterations/20261025-hybrid-gemini-resume'
MODEL = 'gemma-4-31b-it'
BASE = 'https://generativelanguage.googleapis.com/v1beta'


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def save(path, data, secret=''):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, indent=2, ensure_ascii=False)
    if secret:
        text = text.replace(secret, '[REDACTED]')
    with path.open('x', encoding='utf-8') as handle:
        handle.write(text)


class Pacer:
    """Actual prior input usage plus conservative next-body reservation.

    Unknown/incomplete usage keeps the conservative reservation. The observable
    rolling ledger survives evaluator restarts; account activity elsewhere cannot
    be discovered from an API key and is explicitly not claimed as observable.
    """
    def __init__(self):
        self.path = OUT / 'quota-events.jsonl'
        self.events = [json.loads(line) for line in self.path.read_text().splitlines()] if self.path.exists() else []

    async def admit(self, body):
        estimate = max(32, len(json.dumps(body, ensure_ascii=False)))
        if estimate > 16000:
            raise RuntimeError('Single conservative input reservation exceeds the stated16K allowance')
        waited = 0
        while True:
            recent = [row for row in self.events if time.time() - row['timestamp_epoch'] < 61]
            if len(recent) < 30 and sum(row['charged_input_tokens'] for row in recent) + estimate <= 16000:
                return estimate, round(waited, 3)
            seconds = min(10, max(.1, 61 - (time.time() - min(row['timestamp_epoch'] for row in recent))))
            print(json.dumps({'pacing_wait_seconds': round(seconds, 2), 'known_rolling_input': sum(row['charged_input_tokens'] for row in recent)}), flush=True)
            await asyncio.sleep(seconds)
            waited += seconds

    def record(self, identity, started, estimate, usage):
        actual = usage.get('promptTokenCount')
        row = {'id': identity, 'timestamp_epoch': started, 'timestamp': now(),
               'actual_input_tokens': actual,
               'charged_input_tokens': actual if type(actual) is int else estimate,
               'unknown_usage_keeps_conservative_reservation': type(actual) is not int}
        self.events.append(row)
        with self.path.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(row) + '\n')


def body_for(packet, *, thinking='minimal', strict=False, allowance=2048):
    messages = packet['payload']['messages']
    schema = packet['payload'].get('format')
    system = '\n\n'.join(row['content'] for row in messages if row['role'] == 'system')
    if schema and not strict:
        # Same original instructions/evidence. Explicit serialization is the
        # declared provider difference if server schema enforcement is absent.
        system += '\n\nReturn only a JSON value satisfying the following unchanged application schema. Do not use Markdown fences:\n' + json.dumps(schema, separators=(',', ':'))
    contents = [{'role': 'model' if row['role'] == 'assistant' else 'user',
                 'parts': [{'text': row['content']}]} for row in messages if row['role'] != 'system']
    body = {'systemInstruction': {'parts': [{'text': system}]}, 'contents': contents,
            'generationConfig': {'temperature': 0, 'maxOutputTokens': allowance,
                                 'thinkingConfig': {'thinkingLevel': thinking}}}
    if strict and schema:
        body['generationConfig'].update(responseMimeType='application/json', responseJsonSchema=schema)
    return body


async def call(client, key, pacer, identity, body, target, schema=None, retry_quota=True):
    if target.exists():
        return json.loads(target.read_text(encoding='utf-8'))
    result = {'id': identity, 'timestamp': now(), 'model': MODEL, 'endpoint': 'generateContent',
              'request_body_without_credentials': body, 'attempts': [], 'assessment': 'UNREVIEWED'}
    total_started = time.monotonic()
    # At most one429 retry; both attempts/backoff share a120second clock.
    for attempt in range(2 if retry_quota else 1):
        try:
            admission = pacer.admit(body)
            estimate, pacing = (await admission if attempt == 0 else
                await asyncio.wait_for(admission, timeout=max(.01, 120 - (time.monotonic() - total_started))))
        except asyncio.TimeoutError:
            result.update(completed=False, error={'category':'RetryAdmissionDeadline', 'message':'No second request sent'})
            break
        if attempt == 0:
            total_started = time.monotonic()  # Pre-request quota pacing is reported separately.
        remaining = 120 - (time.monotonic() - total_started)
        if remaining <= 1:
            break
        started = time.time(); clock = time.monotonic(); usage = {}; response = None
        trace = {'attempt': attempt + 1, 'quota_pacing_seconds': pacing, 'started_at': now()}
        try:
            async with asyncio.timeout(remaining):
                response = await client.post(BASE + '/models/' + MODEL + ':generateContent',
                    headers={'x-goog-api-key': key}, json=body, timeout=httpx.Timeout(remaining, connect=10))
                data = response.json()
            trace['http_status'] = response.status_code
            result['http_status'] = response.status_code
            if response.is_success:
                result.pop('error', None)
                usage = data.get('usageMetadata') or {}
                candidates = data.get('candidates') or []
                candidate = candidates[0] if candidates else {}
                parts = candidate.get('content', {}).get('parts', [])
                final = ''.join(part.get('text', '') for part in parts if not part.get('thought')).strip()
                thought = ''.join(part.get('text', '') for part in parts if part.get('thought'))
                trace.update(finish_reason=candidate.get('finishReason'), usage=usage)
                result.update(response=data, usage=usage, answer=final,
                              thought_output=thought, completed=bool(final and candidate.get('finishReason') == 'STOP'))
                try:
                    parsed = json.loads(final)
                    result.update(json_valid=True, parsed=parsed)
                    if schema:
                        jsonschema.validate(parsed, schema)
                        result['application_schema_valid'] = True
                except json.JSONDecodeError as exc:
                    result.update(json_valid=False, application_schema_valid=False,
                                  validation_error={'type': type(exc).__name__, 'detail': str(exc)[:400]})
                except jsonschema.ValidationError as exc:
                    result.update(application_schema_valid=False,
                                  validation_error={'type': type(exc).__name__, 'path': list(exc.absolute_path), 'detail': exc.message[:400]})
            else:
                error = data.get('error') or {}
                trace['error'] = error
                result.update(completed=False, http_status=response.status_code, error=error)
        except (httpx.HTTPError, asyncio.TimeoutError, ValueError) as exc:
            trace['error'] = {'category': type(exc).__name__, 'message': str(exc).replace(key, '[REDACTED]')[:500]}
            result.update(completed=False, error=trace['error'])
        finally:
            trace['elapsed_ms'] = round((time.monotonic() - clock) * 1000, 2)
            pacer.record(identity, started, estimate, usage)
            result['attempts'].append(trace)
        if response is not None and response.status_code == 429 and attempt == 0 and retry_quota:
            retry = 10.0
            for detail in (result.get('error') or {}).get('details', []):
                if 'retryDelay' in detail:
                    try: retry = max(retry, float(str(detail['retryDelay']).rstrip('s')))
                    except ValueError: pass
            if retry > 60 or 120 - (time.monotonic() - total_started) < retry + 10:
                break
            result['quota_backoff_seconds'] = retry
            await asyncio.sleep(retry)
            continue
        break
    result['elapsed_ms_excluding_initial_quota_pacing'] = round((time.monotonic() - total_started) * 1000, 2)
    save(target, result, key)
    print(json.dumps({'id': identity, 'completed': result.get('completed'), 'schema_valid': result.get('application_schema_valid'),
        'http_status': result.get('http_status', (result['attempts'] or [{}])[-1].get('http_status')),
        'elapsed_ms': result['elapsed_ms_excluding_initial_quota_pacing'], 'usage': result.get('usage'),
        'error_category': (result.get('error') or {}).get('status', (result.get('error') or {}).get('category'))}), flush=True)
    return result


async def probe(client, key, pacer):
    path = OUT / 'model-access.json'
    if not path.exists():
        started = time.monotonic()
        try:
            r = await client.get(BASE + '/models/' + MODEL, headers={'x-goog-api-key': key}, timeout=20)
            data = {'http_status': r.status_code, 'response': r.json(), 'elapsed_ms': round((time.monotonic() - started) * 1000, 2)}
        except (httpx.HTTPError, ValueError) as exc:
            data = {'error': type(exc).__name__, 'elapsed_ms': round((time.monotonic() - started) * 1000, 2)}
        save(path, data, key)
    access = json.loads(path.read_text(encoding='utf-8'))
    if access.get('http_status') != 200:
        print('Model access failed; no inference attempted.', flush=True)
        return
    packet = {'payload': {'messages': [{'role': 'user', 'content': 'Return exactly COGNISHIELD_GEMMA_READY.'}]}}
    plain = await call(client, key, pacer, 'connectivity', body_for(packet, allowance=128), OUT / 'connectivity.json')
    if not plain.get('completed'):
        return
    packet['payload']['format'] = {'type': 'object', 'properties': {'answer': {'type': 'string', 'enum': ['COGNISHIELD_GEMMA_READY']}},
                                   'required': ['answer'], 'additionalProperties': False}
    packet['payload']['messages'][0]['content'] = 'Return a JSON object with answer equal to COGNISHIELD_GEMMA_READY.'
    await call(client, key, pacer, 'strict-schema-probe', body_for(packet, strict=True, allowance=128),
               OUT / 'strict-schema-probe.json', packet['payload']['format'], retry_quota=False)
    mime_body = body_for(packet, strict=False, allowance=128)
    mime_body['generationConfig']['responseMimeType'] = 'application/json'
    await call(client, key, pacer, 'json-mime-probe', mime_body,
               OUT / 'json-mime-probe.json', packet['payload']['format'], retry_quota=False)


async def run(client, key, pacer, ids, thinking, instruction_json=False):
    probe_result = json.loads((OUT / 'strict-schema-probe.json').read_text(encoding='utf-8'))
    strict = bool(probe_result.get('completed') and probe_result.get('application_schema_valid'))
    if not strict and probe_result.get('http_status') != 400 and not instruction_json:
        raise RuntimeError('Strict-schema availability unresolved; inspect probe before proceeding')
    mime = json.loads((OUT / 'json-mime-probe.json').read_text(encoding='utf-8'))
    json_mime_supported = bool(mime.get('completed') and mime.get('json_valid'))
    for identity in ids:
        packet_path = OUT / 'packets' / (identity + '.json')
        packet = json.loads(packet_path.read_text(encoding='utf-8'))
        for origin, expected in packet.get('preserved_hashes', {}).items():
            assert digest((ROOT / origin).read_bytes()) == expected
        body = body_for(packet, thinking=thinking, strict=strict, allowance=8192 if thinking == 'high' else 2048)
        if not strict and json_mime_supported:
            body['generationConfig']['responseMimeType'] = 'application/json'
        result = await call(client, key, pacer, identity + '-' + thinking, body,
            OUT / thinking / (identity + '.json'), packet['payload'].get('format'))
        if result.get('http_status') in {401, 402, 403, 404, 429}:
            print('Stopped after persistent access/quota/billing restriction; no further cases.', flush=True)
            break


async def main(args):
    key = os.getenv('GEMINI_API_KEY') or dotenv_values(ROOT / 'backend/.env').get('GEMINI_API_KEY')
    if not key:
        raise RuntimeError('Existing credential is unavailable')
    async with httpx.AsyncClient(trust_env=False) as client:
        if args.probe:
            await probe(client, key, Pacer())
        else:
            ids = args.cases.split(',')
            if args.thinking == 'high' and len(ids) > 2:
                raise ValueError('At most two separately graded high-thinking failures are authorized')
            await run(client, key, Pacer(), ids, args.thinking, args.instruction_json)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--probe', action='store_true')
    mode.add_argument('--run', action='store_true', help='Explicitly authorize the frozen synthetic inference cohort')
    parser.add_argument('--cases', default='H01,H02,H03,H04,H05,H06,N01,N02,N03,N04')
    parser.add_argument('--thinking', choices=['minimal', 'high'], default='minimal')
    parser.add_argument('--instruction-json', action='store_true',
        help='Explicit instruction-following JSON experiment; never claims provider enforcement or weakens client schema validation')
    asyncio.run(main(parser.parse_args()))
