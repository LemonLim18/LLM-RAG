"""Six authorized synthetic packet replays through Google's stateless REST API.

Never records authentication headers, never imports an application database,
never retries errors, and never enables a remote application provider.
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
AUDIT = ROOT / 'tmp/phase-g/iterations/20261025-hybrid-gemini-resume'
PACKETS = ROOT / 'tmp/phase-g/iterations/20261025-controlled-qwen35/packets'
CASES = [('H01', 'M01'), ('H02', 'M04'), ('H03', 'M05'),
         ('H04', 'M06'), ('H05', None), ('H06', 'M07')]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)


def freeze():
    rows = []
    for identity, previous in CASES:
        if previous:
            origin = PACKETS / (previous + '.json')
            row = json.loads(origin.read_text(encoding='utf-8'))
        else:
            origin = ROOT / 'tmp/phase-g/iterations/20261024T152118.166815Z-G11-fresh-quality-candidate-631dcf/0002-case.json'
            record = json.loads(origin.read_text(encoding='utf-8'))
            wire = record['actual']['provider_requests'][1]
            row = {'prompt': record['prompt'], 'assistant': record['expected']['assistant'],
                   'payload': {**wire['inference_parameters'], 'messages': wire['messages']},
                   'expected': 'Fulfill BOTH outcomes: show Willow-Relay actual administrative/operational records (including ge-0/0/1.0 down/down), then explain the failed forward egress hop in the declared simulation. Preserve both clauses, actual sources and modeled scope; do not infer physical tests or protocol health.'}
        assert [m['role'] for m in row['payload']['messages']] == ['system', 'user']
        row.update(id=identity, previous_case=previous, origin=str(origin.relative_to(ROOT)).replace('\\', '/'),
                   origin_sha256=sha(origin.read_bytes()), data_authorization='Explicitly approved synthetic historical Phase G fixture only')
        save(AUDIT / 'packets' / (identity + '.json'), row)
        rows.append({k: v for k, v in row.items() if k != 'payload'})
    save(AUDIT / 'comparison-manifest.json', {'timestamp': datetime.now(timezone.utc).isoformat(),
         'cases': rows, 'model': 'gemini-3.8-flash', 'endpoint': 'v1beta/interactions',
         'config': {'thinking_level': 'low', 'max_output_tokens': 2048, 'temperature': 0},
         'storage': False, 'calls': 6, 'concurrency': 1, 'retries': 0,
         'baseline': 'Preserved qwen2.5:1.5b raw outputs; same messages/evidence/schema. Baseline allowance512 versus separately declared Gemini2048. Most baseline errors completed below512, but this is not a model-only causal experiment.',
         'review': 'Full-answer expert review pending. Copied facts, source success and factual fallback are not adequate causal reasoning. All cases exposed; no G11 qualification.'})
    print('Six synthetic conditions frozen before Gemini inference.', flush=True)


async def run():
    key = os.getenv('GEMINI_API_KEY') or dotenv_values(ROOT / 'backend/.env').get('GEMINI_API_KEY')
    if not key:
        raise RuntimeError('GEMINI_API_KEY is not configured')
    async with httpx.AsyncClient(base_url='https://generativelanguage.googleapis.com',
                                trust_env=False, timeout=httpx.Timeout(120, connect=10)) as client:
        for identity, _ in CASES:
            target = AUDIT / 'direct' / (identity + '.json')
            if target.exists():
                print(json.dumps({'existing_result_preserved': identity}), flush=True)
                continue
            case = json.loads((AUDIT / 'packets' / (identity + '.json')).read_text(encoding='utf-8'))
            assert sha((ROOT / case['origin']).read_bytes()) == case['origin_sha256']
            original = case['payload']
            body = {'model': 'gemini-3.8-flash', 'store': False,
                    'system_instruction': original['messages'][0]['content'],
                    'input': original['messages'][1]['content'],
                    'generation_config': {'thinking_level': 'low', 'max_output_tokens': 2048, 'temperature': 0}}
            if isinstance(original.get('format'), dict):
                body['response_format'] = {'type': 'text', 'mime_type': 'application/json', 'schema': original['format']}
            out = {'id': identity, 'timestamp': datetime.now(timezone.utc).isoformat(),
                   'request_body_without_credentials': body, 'origin_sha256': case['origin_sha256'],
                   'assessment': 'UNREVIEWED_NO_INTELLIGENCE_CREDIT', 'events': []}
            started = time.monotonic()
            try:
                async with asyncio.timeout(119):
                    async with client.stream('POST', '/v1beta/interactions', json=body,
                                             headers={'x-goog-api-key': key}) as response:
                        out['http_status'] = response.status_code
                        out['events'].append({'stage': 'headers', 'ms': round((time.monotonic() - started) * 1000, 2)})
                        data = json.loads(await response.aread())
                        if response.is_success:
                            out['provider_status'] = data.get('status')
                            out['usage'] = data.get('usage')
                            out['model'] = data.get('model')
                            out['answer'] = ''.join(part.get('text', '') for step in data.get('steps', [])
                                if step.get('type') == 'model_output' for part in step.get('content', [])
                                if part.get('type') == 'text').strip()
                            out['completed'] = data.get('status') == 'completed' and bool(out['answer'])
                            out['step_types'] = [step.get('type') for step in data.get('steps', [])]
                            if original.get('format'):
                                parsed = json.loads(out['answer'])
                                jsonschema.validate(parsed, original['format'])
                                out.update(parsed=parsed, schema_valid=True)
                        else:
                            error = data.get('error') or {}
                            out.update(completed=False, error={'category': error.get('status'),
                                       'message': str(error.get('message', '')).replace(key, '[REDACTED]')[:1000]})
            except Exception as exc:
                out.update(completed=False, error={'category': type(exc).__name__,
                           'message': str(exc).replace(key, '[REDACTED]')[:600]})
            out['elapsed_ms'] = round((time.monotonic() - started) * 1000, 2)
            # Defense in depth: even provider-returned error/text must not copy the credential.
            out = json.loads(json.dumps(out, ensure_ascii=False).replace(key, '[REDACTED]'))
            save(target, out)
            print(json.dumps({k: out.get(k) for k in ['id', 'completed', 'schema_valid', 'elapsed_ms', 'http_status', 'error']}), flush=True)
            if out.get('http_status') in {401, 402, 403, 429}:
                print('Stopped after authentication, billing, permission or quota error; no retries.', flush=True)
                break


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze', action='store_true')
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if args.freeze:
        freeze()
    elif args.run:
        asyncio.run(run())
    else:
        parser.error('Explicit --freeze or --run required; no API calls by default')
