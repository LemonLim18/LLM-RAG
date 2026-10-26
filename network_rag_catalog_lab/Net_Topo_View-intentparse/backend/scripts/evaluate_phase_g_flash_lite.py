"""Explicit test-only Flash-Lite evaluation; no gateway/provider/config changes.

The hard evaluator timeout is300seconds, independent of the120second target.
All wire packets are synthetic; credentials occur in headers only, never saved.
"""
import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time

import httpx
import jsonschema
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'tmp/phase-g/iterations/20261025-flash-lite-35'
MODEL = 'gemini-3.5-flash-lite'
BASE = 'https://generativelanguage.googleapis.com/v1beta'
MAX_INFERENCES = 12
HTTP_SECONDS = 300


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value, secret=''):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, indent=2, ensure_ascii=False)
    if secret:
        text = text.replace(secret, '[REDACTED]')
    with path.open('x', encoding='utf-8') as handle:
        handle.write(text)


def body_for(packet):
    messages = packet['payload']['messages']
    system = '\n\n'.join(m['content'] for m in messages if m['role'] == 'system')
    contents = [{'role': 'model' if m['role'] == 'assistant' else 'user',
                 'parts': [{'text': m['content']}]} for m in messages if m['role'] != 'system']
    if not contents or contents[-1]['role'] != 'user':
        raise ValueError('No model prefill is permitted; final input must be the original user turn')
    # Current official3.5 API deprecates sampling parameters. Do not copy3.8's
    # temperature0, top_p or top_k. Original messages/evidence/schema are exact.
    config = {'thinkingConfig': {'thinkingLevel': packet.get('thinking', 'low')},
              'maxOutputTokens': packet.get('output_allowance', 8192)}
    schema = packet['payload'].get('format')
    if isinstance(schema, dict):
        config.update(responseMimeType='application/json', responseJsonSchema=schema)
    body = {'contents': contents, 'generationConfig': config}
    if system:
        body['systemInstruction'] = {'parts': [{'text': system}]}
    return body


class Pacer:
    def __init__(self):
        self.path = OUT / 'quota-events.jsonl'
        self.events = [json.loads(line) for line in self.path.read_text().splitlines()] if self.path.exists() else []

    async def admit(self, body):
        reservation = max(32, len(json.dumps(body, ensure_ascii=False)))
        if reservation > 250000:
            raise RuntimeError('Conservative reservation exceeds account-observed input TPM')
        if len(self.events) >= MAX_INFERENCES:
            raise RuntimeError('This bounded experiment has exhausted its12inference-call allowance')
        today = now()[:10]
        if sum(e['timestamp'][:10] == today for e in self.events) >= 500:
            raise RuntimeError('Observed local daily request allowance exhausted')
        waited = 0
        while True:
            epoch = time.time()
            recent = [e for e in self.events if epoch - e['started_epoch'] < 61]
            gap = max(0, 4.1 - (epoch - self.events[-1]['started_epoch'])) if self.events else 0
            if len(recent) < 15 and sum(e['charged_input_tokens'] for e in recent) + reservation <= 250000 and not gap:
                return reservation, round(waited, 3)
            delay = gap if gap else min(10, max(.1, 61 - (epoch - min(e['started_epoch'] for e in recent))))
            await asyncio.sleep(delay)
            waited += delay

    def started(self, identity, epoch, reservation):
        # Persist before dispatch: interrupted/provider-error requests consume
        # a conservative reservation and cannot be silently replayed as free.
        row = {'id': identity, 'started_epoch': epoch, 'timestamp': now(),
               'charged_input_tokens': reservation, 'actual_input_tokens': None}
        self.events.append(row)
        self._save()

    def finish(self, usage):
        count = usage.get('promptTokenCount')
        if type(count) is int and count >= 0:
            self.events[-1].update(actual_input_tokens=count, charged_input_tokens=count)
            self._save()

    def _save(self):
        self.path.write_text(''.join(json.dumps(row) + '\n' for row in self.events), encoding='utf-8')


async def inference(client, key, pacer, packet):
    target = OUT / 'results' / (packet['id'] + '.json')
    if target.exists():
        return json.loads(target.read_text(encoding='utf-8'))
    if any(e['id'] == packet['id'] for e in pacer.events):
        raise RuntimeError('Prior interrupted request exists without a result; inspect it rather than automatically repeat')
    body = body_for(packet)
    reserve, waiting = await pacer.admit(body)
    epoch = time.time(); start = time.monotonic()
    pacer.started(packet['id'], epoch, reserve)
    result = {'id': packet['id'], 'timestamp': now(), 'model': MODEL,
              'request_without_credentials': body, 'packet_sha256': sha(OUT / 'packets' / (packet['id'] + '.json')),
              'pacing_seconds': waiting, 'hard_test_timeout_seconds': HTTP_SECONDS,
              'completed': False, 'assessment': 'UNREVIEWED; HTTP200/JSON alone is not complete-task success'}
    try:
        async with asyncio.timeout(HTTP_SECONDS):
            response = await client.post(BASE + '/models/' + MODEL + ':generateContent',
                headers={'x-goog-api-key': key}, json=body,
                timeout=httpx.Timeout(HTTP_SECONDS, connect=15))
            data = response.json()
        result['http_status'] = response.status_code
        if not response.is_success:
            result['error'] = data.get('error') or {'status': 'UNKNOWN_PROVIDER_ERROR'}
        else:
            candidates = data.get('candidates') or []
            candidate = candidates[0] if candidates else {}
            parts = candidate.get('content', {}).get('parts', [])
            answer = ''.join(p.get('text', '') for p in parts if not p.get('thought')).strip()
            result.update(raw_response=data, usage=data.get('usageMetadata') or {},
                answer=answer, finish_reason=candidate.get('finishReason'),
                thought_text=''.join(p.get('text', '') for p in parts if p.get('thought')),
                completed=bool(answer and candidate.get('finishReason') == 'STOP'))
            if isinstance(packet['payload'].get('format'), dict):
                try:
                    parsed = json.loads(answer); result.update(parsed=parsed, json_valid=True)
                    jsonschema.validate(parsed, packet['payload']['format'])
                    result['application_schema_valid'] = True
                except json.JSONDecodeError as exc:
                    result.update(json_valid=False, application_schema_valid=False,
                        validation_error={'type': type(exc).__name__, 'detail': str(exc)[:500]})
                except jsonschema.ValidationError as exc:
                    result.update(application_schema_valid=False,
                        validation_error={'type': type(exc).__name__, 'detail': exc.message[:500], 'path': list(exc.absolute_path)})
    except (asyncio.TimeoutError, httpx.HTTPError, ValueError) as exc:
        result['error'] = {'category': type(exc).__name__, 'detail': str(exc).replace(key, '[REDACTED]')[:500]}
    result['elapsed_ms'] = round((time.monotonic() - start) * 1000, 2)
    result['within_120_seconds'] = result['elapsed_ms'] <= 120000
    pacer.finish(result.get('usage') or {})
    save(target, result, key)
    print(json.dumps({k: result.get(k) for k in ['id', 'http_status', 'completed', 'application_schema_valid',
        'elapsed_ms', 'within_120_seconds', 'usage', 'finish_reason']}), flush=True)
    return result


async def main(args):
    manifest = json.loads((OUT / 'manifest.json').read_text(encoding='utf-8'))
    for row in manifest['cases']:
        assert sha(OUT / 'packets' / (row['id'] + '.json')) == row['packet_sha256']
    key = os.getenv('GEMINI_API_KEY') or dotenv_values(ROOT / 'backend/.env').get('GEMINI_API_KEY')
    if not key:
        raise RuntimeError('The configured backend credential is unavailable')
    pacer = Pacer()
    async with httpx.AsyncClient(trust_env=False) as client:
        path = OUT / 'model-access.json'
        if not path.exists():
            start = time.monotonic()
            try:
                response = await client.get(BASE + '/models/' + MODEL, headers={'x-goog-api-key': key}, timeout=20)
                access = {'http_status': response.status_code, 'response': response.json(),
                          'elapsed_ms': round((time.monotonic() - start) * 1000, 2)}
            except (httpx.HTTPError, ValueError) as exc:
                access = {'error_type': type(exc).__name__}
            save(path, access, key)
        access = json.loads(path.read_text(encoding='utf-8'))
        if access.get('http_status') != 200:
            print('Model access failed; no inference attempted.', flush=True)
            return
        ids = ['C00'] if args.probe else [row['id'] for row in manifest['cases'] if row['id'] != 'C00']
        connection = OUT / 'results/C00.json'
        if not args.probe and (not connection.exists() or not json.loads(connection.read_text(encoding='utf-8')).get('completed')):
            raise RuntimeError('Successful synthetic connectivity must be established before the cohort')
        failures = 0
        for identity in ids:
            packet = json.loads((OUT / 'packets' / (identity + '.json')).read_text(encoding='utf-8'))
            for origin, value in packet.get('preserved_hashes', {}).items():
                assert sha(ROOT / origin) == value
            result = await inference(client, key, pacer, packet)
            status = result.get('http_status')
            failures = failures + 1 if not result.get('completed') else 0
            if status in {400, 401, 402, 403, 404, 422, 429} or failures >= 2:
                print('Stopped after a contract/access/quota error or two noncompleted requests; no retry loop.', flush=True)
                break


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--probe', action='store_true')
    mode.add_argument('--run', action='store_true')
    asyncio.run(main(parser.parse_args()))
