"""Actual authenticated shared-gateway probes on a disposable SQLite backup.

Uses real existing R1/R2 records, LangGraph/LangChain and configured Ollama.
No second server/app checkout, ordinary writes, copied release or model download.
"""
import asyncio
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))


def topology_oracle(answer):
    """Independent R1/R2 fixture oracle; target-port detail is optional.

    The question asks for a path. A correct answer may name only R1's port, or
    neither port. Volunteering a false R2 endpoint must still fail.
    """
    value=answer.replace('`','').casefold()
    forbidden=["r2's gigabitethernet0/1", 'gigabitethernet0/1 on r2',
               'gigabitethernet0/1 at r2', 'gigabitethernet0/1 of r2',
               '| r2 | gigabitethernet0/1 |']
    return 'r1' in value and 'r2' in value and not any(text in value for text in forbidden)


async def main(case_set='ordinary', engine='candidate'):
    import httpx
    from fastapi import FastAPI
    from auth.auth import create_access_token
    from db.manager import DatabaseManager
    from lab_config import DB_PATH
    from llm.gateway_api import router
    from llm.gateway_store import ensure_schema
    from scripts.phase_d_audit import Run, database_fingerprints, source_manifest, digest
    assert os.getenv('COGNISHIELD_AI_SYNTHESIS') == '1'
    os.environ['COGNISHIELD_AI_PLANNING']='1' if engine=='candidate' else '0'
    before = database_fingerprints(DB_PATH)
    run = Run('F3-actual-authenticated-gateway', 'real_model_full_agent', manifest={
        'model': 'qwen2.5:1.5b', 'source': 'Read-only backup of actual stored R1/R2; new isolated conversations only.',
        'mode': case_set, 'planning_arm':engine, 'app_ports_unchanged': [5173, 8000],
        'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'source_digest':digest(json.dumps(source_manifest(),sort_keys=True).encode()),
        'provider_counter_scope':'Same-process httpx chat/generate and embedding requests; no subprocess inference is used in these cases.'}, phase='phase-f')
    location = tempfile.TemporaryDirectory(prefix='gateway-probe-', dir=ROOT / 'tmp/phase-f', ignore_cleanup_errors=True)
    folder = Path(location.name).resolve()
    assert folder.is_relative_to((ROOT / 'tmp/phase-f').resolve())
    target = folder / 'evaluation.db'
    original = sqlite3.connect(Path(DB_PATH).resolve().as_uri() + '?mode=ro', uri=True)
    copied = sqlite3.connect(target)
    try:
        original.backup(copied)
    finally:
        original.close(); copied.close()
    db = DatabaseManager(str(target))
    assert Path(db._db_path).resolve() == target.resolve() != Path(DB_PATH).resolve()
    ensure_schema(db)
    if case_set=='source-scopes':
        from local_providers.development import ScenarioManager
        os.environ['COGNISHIELD_DEV_SIMULATION']='1'
        db._development_scenario=ScenarioManager(folder/'scenario.json')
        run.manifest['source']='Central HEALTHY-001 development scenario, not ordinary R1/R2 or physical observations'
        run.manifest['scenario_revision']=db._development_scenario.snapshot()[1]
        (run.path/'manifest.json').write_text(json.dumps(run.manifest,indent=2),encoding='utf-8')
    app = FastAPI(); app.state.local_db = db; app.include_router(router)
    outcomes = []
    ordinary_cases=[
        ('topology', 'Show the recorded network path from R1 to R2.', {'network.topology'}),
        ('interfaces', 'Which interfaces are actually recorded for R2, with their addresses?', {'inventory.read'}),
        ('followup', 'What is the IP address of the first one?', {'inventory.read'}),
        ('topic-switch', 'Hello. What is 6 multiplied by 7?', set()),
    ]
    scope_cases=[
        ('planned-only', 'Show only the planned connections around R2.', {'network.topology'}),
        ('observed-followup', 'Now show the observed connections instead.', {'network.topology'}),
        ('protocol-state', 'Does R2 have any recorded OSPF adjacencies?', {'network.state'}),
        ('historical-only', 'Read the historical topology observations for R2.', {'network.topology'}),
    ]
    calls=[]
    original_send=httpx.AsyncClient.send
    async def counted_send(client,request,*args,**kwargs):
        path=request.url.path
        if path not in {'/api/chat','/api/embed','/api/embeddings','/api/generate'}:
            return await original_send(client,request,*args,**kwargs)
        body=json.loads(request.content)
        entry={'endpoint':path,'model':body.get('model'),'input_characters':sum(len(str(m.get('content',''))) for m in body.get('messages',[]))}
        calls.append(entry)
        started=time.monotonic()
        try:
            response=await original_send(client,request,*args,**kwargs)
            entry['http_status']=response.status_code
            return response
        except Exception as exc:
            entry['error_type']=type(exc).__name__
            raise
        finally:entry['request_ms']=round((time.monotonic()-started)*1000,2)
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://controlled-api', timeout=240) as client:
            denied = await client.post('/api/v1/ai/conversations', json={'assistant_kind': 'floating'})
            assert denied.status_code == 401
            client.headers['Authorization'] = 'Bearer ' + create_access_token(901, 'PHASE-F-TEST-OWNER', 'engineer')
            response = await client.post('/api/v1/ai/conversations', json={'assistant_kind': 'floating'})
            assert response.status_code == 200, response.text
            cid = response.json()['id']
            for label, prompt, required in (scope_cases if case_set=='source-scopes' else ordinary_cases):
                started = time.monotonic()
                call_start=len(calls)
                with patch.object(httpx.AsyncClient,'send',counted_send):
                    response = await client.post('/api/v1/ai/conversations/' + cid + '/turns', json={
                        'request_id': str(uuid4()), 'prompt': prompt, 'model': 'qwen2.5:1.5b'})
                assert response.status_code == 200, response.text
                result = response.json()
                tools = {r['tool'] for r in result['observations']}
                ok = result['status'] == 'success' and required <= tools
                if label == 'topic-switch': ok = ok and not tools and '42' in result['answer']
                if label == 'followup': ok = ok and '192.168.1.251' in result['answer'] and '10.1.1.2' not in result['answer']
                if label == 'interfaces': ok = ok and all(value in result['answer'] for value in ['192.168.1.251', '10.1.1.2'])
                if label == 'topology':
                    ok = ok and topology_oracle(result['answer'])
                if case_set=='source-scopes':
                    data=next((r.get('data') or {} for r in result['observations'] if r['tool']=='network.topology'),{})
                    if label=='planned-only':
                        ok=ok and bool(data.get('links')) and data.get('records')==[] and data.get('topology_kind')=='planned'
                        ok=ok and all(name in result['answer'] for name in ['R1','R2'])
                        # Independent absence oracle; a returned link and a
                        # successful HTTP response do not prove answer quality.
                        import re
                        ok=ok and not re.search(r'\b(?:no|zero)\s+(?:planned\s+)?(?:links|connections)\b',result['answer'],re.I)
                    elif label=='observed-followup':
                        ok=ok and data.get('links')==[] and bool(data.get('records')) and all(r['current'] for r in data['records']) and data.get('topology_kind')=='observed'
                    elif label=='historical-only':ok=ok and data.get('links')==[] and data.get('records')==[] and 'unavailable' in str(result['observations']).lower()
                    elif label=='protocol-state':
                        # The fixture has interface/reachability observations,
                        # but no OSPF session: a tool read cannot invent one.
                        ok=ok and not any(r.get('protocol')=='OSPF' for o in result['observations'] for r in (o.get('data') or {}).get('records',[]))
                ok = ok and not (tools & {'v9.preview', 'document.propose'})
                run.record('F3-GATEWAY-' + label, 'PASS' if ok else 'FAIL', expected={'tools': sorted(required), 'actual_records_and_owner_bound_context': True},
                    actual=result, prompt=prompt, provider_calls=calls[call_start:], latency_ms=round((time.monotonic() - started) * 1000, 2), classification=None if ok else 'actual_gateway_behavior')
                outcomes.append(ok)
                print(json.dumps({'case': label, 'pass': ok, 'tools': sorted(tools)}), flush=True)
            client.headers['Authorization'] = 'Bearer ' + create_access_token(902, 'PHASE-F-OTHER-OWNER', 'engineer')
            cross = await client.get('/api/v1/ai/conversations/' + cid)
            assert cross.status_code in {403, 404}, cross.text
            run.record('F3-GATEWAY-OWNER', 'PASS', expected='Unauthenticated401 and cross-owner403/404', actual={'unauthenticated': denied.status_code, 'cross_owner': cross.status_code})
    finally:
        db.close()
        assert folder.is_relative_to((ROOT / 'tmp/phase-f').resolve())
        location.cleanup()
        after = database_fingerprints(DB_PATH)
        assert before == after, 'Ordinary database changed during disposable API evaluation'
    summary = {'run': str(run.path), 'passed': sum(outcomes), 'cases': len(outcomes), 'ordinary_database_unchanged': True}
    with (run.path / 'result.json').open('x', encoding='utf-8') as file: json.dump(summary, file, indent=2)
    with (run.path / 'README.md').open('x',encoding='utf-8') as file:
        file.write(f'# Actual gateway {case_set} / {engine}\n\n'
            f'{sum(outcomes)}/{len(outcomes)} scoped behavior checks; separate ownership rejection passed. '
            'Read each case answer and synthesis status: record/tool correctness is not a broad answer-adequacy score. '
            'Provider requests are counted separately from graph calls. No browser acceptance is inferred. '
            'Ordinary database fingerprints were unchanged; scenario/backup state was disposable.\n')
    print(json.dumps(summary), flush=True)
    return all(outcomes)


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--case-set',choices=['ordinary','source-scopes'],default='ordinary')
    parser.add_argument('--engine',choices=['candidate','legacy'],default='candidate')
    args=parser.parse_args()
    raise SystemExit(0 if asyncio.run(main(args.case_set,args.engine)) else 1)
