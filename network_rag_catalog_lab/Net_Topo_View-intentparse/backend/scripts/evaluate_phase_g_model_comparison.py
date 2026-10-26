"""Bounded, sequential Ollama replay of frozen synthetic gateway packets.

No application imports, database writes, model downloads, or global configuration.
Raw packets and results live in the ignored audit directory; expectations require
human full-answer review, never an automatic intelligence pass.
"""
import argparse
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

import httpx
import jsonschema

ROOT = Path(__file__).resolve().parents[2]
ITERATIONS = ROOT / 'tmp/phase-g/iterations'
OLD = '20261024T090242.496220Z-G11-fresh-quality-candidate-c3a60b'
PAIRED = '20261024T161958.804761Z-G11-fresh-quality-candidate-bf1a92'
FINAL = '20261024T163531.689698Z-G11-fresh-quality-candidate-b233c5'
PILOT = '20261024T152118.166815Z-G11-fresh-quality-candidate-631dcf'

# These are evaluation oracles, not application routing or production guards.
CASES = [
    ('M01', PAIRED, 8, 1, 'causal', 'complex',
     'A route exists but forward delivery fails at Willow-Relay ge-0/0/1.0 admin/oper down; explain why route presence alone is insufficient. Keep simulated ICMP/VRF scope. Do not invent the owner of the incompletely identified return ingress.'),
    ('M02', PAIRED, 4, 1, 'causal', 'complex',
     'Both declared directions deliver through Willow-Relay. Explain forward and reverse modeled scope; reverse success does not prove continuous physical availability or all protocol prerequisites.'),
    ('M03', OLD, 8, 1, 'relationships', 'moderate',
     'Return direction originates at Granite-End toward Spruce-Start and fails there for no route. It does not traverse the forward relay path. Respect the original system demand to mention both directions without reversing endpoints.'),
    ('M04', OLD, 19, 1, 'ownership', 'moderate',
     'Two intended links: Spruce-Start GigabitEthernet0/1 to Willow-Relay ge-0/0/0.0; Willow-Relay ge-0/0/1.0 to Granite-End GigabitEthernet0/0/1. Planned links do not prove physical reachability.'),
    ('M05', FINAL, 4, 1, 'compound', 'complex',
     'Show actual saved commands for Spruce-Start, OSPF20/router-id198.19.213.1, and independently state unavailable syslog. No absence-of-events, collected-log, or current-running-state assertion. Complete both response clauses.'),
    ('M06', PILOT, 9, 0, 'published_mapping', 'complex',
     'Map published configure_ospf fields to actual saved process20/router-id198.19.213.1/interface GigabitEthernet0/1 area0. Explain vendor-dependent process requirement and unverified compatibility/current deployment/full validation. Do not generate; preserve both source roles.'),
    ('M07', FINAL, 1, 3, 'advisory', 'moderate',
     'Provide concrete unexecuted read-only questions and explain their value, or identify missing destination/service scope. Do not claim inventory measures reachability. Avoid circular repetition of the user question. Parent setup only read inventory, so no uniquely best diagnostic sequence is certified.'),
    ('M08', OLD, 15, 1, 'temporal_control', 'moderate',
     'Saved02:29:50Z/current02:30:00Z command text is identical. State equality and capture times; do not infer no intervening changes, interval continuity, or physical state.'),
    ('M09', OLD, 22, 1, 'document_control', 'simple',
     'Page2 proposes hello22/dead88 seconds. It establishes neither present use nor non-use. Cite the actual document/page; no action.'),
    ('M10', OLD, 25, 0, 'editor_control', 'moderate',
     'Unsaved OSPF process81/router-id203.0.113.81; BGP localAS64681/neighbor203.0.113.82/remoteAS64682; markers KEEP_BASELINES and UNSAVED_QUALIFICATION. No explicit BGP router-ID or edit/save claim. Explain actual content.'),
    ('M11', OLD, 7, 0, 'planning', 'simple',
     'Read-only state/forwarding needs preserve both requested state read and failed-hop explanation. No write/generation or unnecessary clarification. Topology is allowed for modeled path relationships; inventory alone is insufficient.'),
    ('M12', OLD, 27, 2, 'routing_control', 'simple',
     'General Python slicing explanation routes to answer, without editor, attachment, network reads or unnecessary clarification.'),
]
OPTIONS = {'temperature': 0, 'num_ctx': 8192, 'num_predict': 512,
           'seed': 0, 'top_p': .9, 'top_k': 40, 'repeat_penalty': 1.1,
           'presence_penalty': 0, 'frequency_penalty': 0}
TARGET = {'simple': 30, 'moderate': 60, 'complex': 120}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)


def freeze(folder):
    folder.mkdir(parents=True, exist_ok=False)
    cases = []
    for identity, source, number, index, category, complexity, expected in CASES:
        path = ITERATIONS / source / f'{number:04d}-case.json'
        original = path.read_bytes()
        record = json.loads(original)
        packet = deepcopy(record['actual']['provider_requests'][index])
        assert packet['endpoint'] == '/api/chat'
        payload = {**packet['inference_parameters'], 'messages': packet['messages']}
        body_hash = sha(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode())
        row = {'id': identity, 'category': category, 'complexity': complexity,
               'request_target_seconds': TARGET[complexity], 'expected': expected,
               'assistant': record['expected']['assistant'], 'prompt': record['prompt'],
               'origin': str(path.relative_to(ROOT)).replace('\\', '/'),
               'origin_sha256': sha(original), 'wire_index': index,
               'original_payload_sha256': body_hash, 'payload': payload,
               'inherited_input_limitations': 'Preserved historical packet; not a new unseen test. Advisory scope is incomplete; exact causal return-interface ownership is not fully declared.' if identity in {'M01', 'M07'} else ''}
        write_new(folder / 'packets' / f'{identity}.json', row)
        cases.append({k: v for k, v in row.items() if k != 'payload'})
    manifest = {'timestamp': datetime.now(timezone.utc).isoformat(),
                'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                'cases': cases, 'shared_options': OPTIONS,
                'matched_arms': ['baseline512', 'qwen35_off512'],
                'thinking_subset': ['M01', 'M05', 'M06'],
                'optional_token_experiments': {'qwen35_off1024': ['M01', 'M05', 'M06'], 'qwen35_on1536': ['M01', 'M06']},
                'design': 'Direct preserved-message comparison. Streaming transport normalized for partial-output capture. Both models receive explicit identical sampling options, overriding model-specific defaults. Documents originally allowed768 tokens; matched arm deliberately normalizes to512. No direct replay counts as gateway end-to-end success.',
                'review': 'Independently checked raw source fields; manual full-answer scoring required. Implementation assistant is grader, not independent external certification.',
                'budgets': 'One replay is one isolated request with30/60/120 second hard wall including metadata/schema validation. No retry. Gateway admission requires separate actual multi-call measurements under120 seconds.'}
    write_new(folder / 'manifest.json', manifest)
    print(json.dumps({'frozen': str(folder), 'conditions': len(cases), 'manifest_sha256': sha((folder / 'manifest.json').read_bytes())}), flush=True)


async def resources(client):
    try:
        return (await client.get('/api/ps', timeout=3)).json()
    except (httpx.HTTPError, ValueError) as exc:
        return {'error': type(exc).__name__}


async def execute(folder, arm, selected):
    configurations = {'baseline512': ('qwen2.5:1.5b', None, 512),
                      'qwen35_off512': ('qwen3.5:4b', False, 512),
                      'qwen35_off512_isolated': ('qwen3.5:4b', False, 512),
                      'qwen35_off512_plan60': ('qwen3.5:4b', False, 512),
                      'qwen35_on512': ('qwen3.5:4b', True, 512),
                      'qwen35_off1024': ('qwen3.5:4b', False, 1024),
                      'qwen35_on1536': ('qwen3.5:4b', True, 1536)}
    model, thinking, allowance = configurations[arm]
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    all_ids = [row['id'] for row in manifest['cases']]
    supplement = folder / 'supplement-manifest.json'
    if supplement.exists():
        all_ids.extend(row['id'] for row in json.loads(supplement.read_text(encoding='utf-8'))['cases'])
    calibration = {'qwen35_off512_isolated': ['M02'], 'qwen35_off512_plan60': ['M11']}
    chosen = selected or calibration.get(arm) or (manifest['thinking_subset'] if arm == 'qwen35_on512' else manifest['optional_token_experiments'].get(arm, all_ids))
    assert set(chosen) <= set(all_ids)
    async with httpx.AsyncClient(base_url='http://127.0.0.1:11434', trust_env=False, timeout=125) as client:
        inventory = (await client.get('/api/tags')).json()
        if model not in {row['name'] for row in inventory['models']}:
            raise RuntimeError('Required model is not installed; never download automatically')
        show = (await client.post('/api/show', json={'model': model})).json()
        metadata_path = folder / arm / 'model-metadata.json'
        if not metadata_path.exists():
            write_new(metadata_path, {'timestamp': datetime.now(timezone.utc).isoformat(), 'inventory': inventory,
                                     'version': (await client.get('/api/version')).json(),
                                     'show': {k: show.get(k) for k in ['capabilities', 'thinking', 'details', 'parameters']}})
        for identity in chosen:
            output = folder / arm / f'{identity}.json'
            if output.exists():
                print(json.dumps({'skipped_existing': identity, 'arm': arm}), flush=True)
                continue
            row = json.loads((folder / 'packets' / f'{identity}.json').read_text(encoding='utf-8'))
            wall_seconds = 60 if arm == 'qwen35_off512_plan60' else row['request_target_seconds']
            assert sha((ROOT / row['origin']).read_bytes()) == row['origin_sha256']
            payload = deepcopy(row['payload'])
            payload.update(model=model, stream=True)
            payload['options'] = {**OPTIONS, 'num_predict': allowance}
            if thinking is not None:
                payload['think'] = thinking
            else:
                payload.pop('think', None)
            result = {'id': identity, 'arm': arm, 'model': model, 'think_requested': thinking,
                      'started_at': datetime.now(timezone.utc).isoformat(), 'request': payload,
                      'origin_sha256': row['origin_sha256'], 'expected': row['expected'],
                      'wall_seconds': wall_seconds,
                      'messages_sha256': sha(json.dumps(payload['messages'], sort_keys=True, ensure_ascii=False).encode()),
                      'resources_before': await resources(client), 'response': {}, 'chunks': [],
                      'assessment': 'UNREVIEWED_NO_INTELLIGENCE_CREDIT'}
            started = time.monotonic()
            content = []
            thoughts = []
            async def infer():
                async with client.stream('POST', '/api/chat', json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        chunk = json.loads(line)
                        if 'error' in chunk:
                            raise RuntimeError(chunk['error'])
                        message = chunk.get('message') or {}
                        content.append(message.get('content', ''))
                        thoughts.append(message.get('thinking', ''))
                        result['chunks'].append(chunk)
                        if chunk.get('done'):
                            result['response'] = {k: v for k, v in chunk.items() if k != 'message'}
                            result['completed'] = True
            try:
                await asyncio.wait_for(infer(), timeout=wall_seconds - .5)
            except Exception as exc:
                result['error'] = {'type': type(exc).__name__, 'message': str(exc)[:800]}
                result['completed'] = False
            result['elapsed_ms'] = round((time.monotonic() - started) * 1000, 2)
            result['answer'] = ''.join(content)
            result['thinking_output'] = ''.join(thoughts)
            result['thinking_characters'] = len(result['thinking_output'])
            result['answer_characters'] = len(result['answer'])
            result['tokens'] = {'total_generated': result['response'].get('eval_count'),
                               'thinking': result['response'].get('thinking_eval_count'),
                               'final_answer': result['response'].get('answer_eval_count'),
                               'note': 'API total may combine thinking and content. Missing separate counts remain unknown; characters and chunks are not tokens.'}
            try:
                parsed = json.loads(result['answer'])
                schema = payload.get('format')
                if isinstance(schema, dict):
                    jsonschema.validate(parsed, schema)
                result['parsed'] = parsed
                result['schema_valid'] = True if isinstance(schema, dict) else None
            except (ValueError, jsonschema.ValidationError, jsonschema.SchemaError) as exc:
                result['schema_valid'] = False if isinstance(payload.get('format'), dict) else None
                result['parse_error'] = str(exc)[:800]
            result['resources_after'] = await resources(client)
            write_new(output, result)
            print(json.dumps({k: result.get(k) for k in ['id', 'arm', 'completed', 'elapsed_ms', 'schema_valid', 'thinking_characters', 'answer_characters', 'error']}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', type=Path, required=True)
    parser.add_argument('--freeze', action='store_true')
    parser.add_argument('--arm', choices=['baseline512', 'qwen35_off512', 'qwen35_on512', 'qwen35_off1024', 'qwen35_on1536', 'qwen35_off512_isolated', 'qwen35_off512_plan60'])
    parser.add_argument('--cases', nargs='+')
    args = parser.parse_args()
    folder = args.folder.resolve()
    if not folder.is_relative_to(ITERATIONS.resolve()):
        parser.error('Audit folder must be within the existing ignored Phase G iterations tree')
    if args.freeze:
        freeze(folder)
    elif args.arm:
        asyncio.run(execute(folder, args.arm, args.cases))
    else:
        parser.error('Choose --freeze or an explicit --arm; no inference by default')


if __name__ == '__main__':
    main()
