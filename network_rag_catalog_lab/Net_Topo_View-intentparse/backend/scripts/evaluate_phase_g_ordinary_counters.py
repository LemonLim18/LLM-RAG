"""Ordinary-provider named-port parity through both real shared-gateway paths."""
import asyncio
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import sys
import time
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))


async def main():
    import httpx
    from fastapi import FastAPI
    import lab_config
    from auth.auth import create_access_token
    from db.manager import DatabaseManager
    from llm.gateway_api import router
    from llm.gateway_store import ensure_schema
    from local_providers.development import ScenarioManager
    from scripts.phase_d_audit import Run,source_manifest
    os.environ.update(COGNISHIELD_AI_ENGINE='langgraph_b3',COGNISHIELD_AI_PLANNING='1',COGNISHIELD_AI_SYNTHESIS='1')
    run=Run('G9-ordinary-counter-parity','real_model_full_agent',{'model':'qwen2.5:1.5b',
        'source_manifest':source_manifest(),'holdout':False,'scenario':'disabled; ordinary JSON observation provider'},phase='phase-g')
    stamp=datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    fixture={'version':1,'interfaces':[
        {'device_id':91,'interface_id':901,'metrics':[{'time':stamp,'cpu':0,'memory':0,'errors':13,'discards':4}]},
        {'device_id':91,'interface_id':902,'metrics':[{'time':stamp,'cpu':0,'memory':0,'errors':97,'discards':28}]}]}
    prompt='Read only the recorded errors and discards counters for R1 Gi0/1. State the sample time. Do not infer rates or a current physical failure.'
    workspace=ROOT/'tmp'/('g9-counter-'+uuid4().hex[:6]);workspace.mkdir()
    (workspace/'observations.json').write_text(json.dumps(fixture),encoding='utf-8')
    (run.path/'specification.json').write_text(json.dumps({'prompt':prompt,'fixture':fixture,
        'expected_tool':'network.telemetry','expected_interface':'Gi0/1','expected_errors':13,'expected_discards':4,
        'prohibited':['Gi0/2 substituted','97 errors on Gi0/1','physical measurement claim','counter treated as rate']},indent=2),encoding='utf-8')
    lab_config.FIXTURE_DIR=workspace
    db=DatabaseManager(str(workspace/'ordinary.db'));db.initialize();ensure_schema(db)
    db._development_scenario=ScenarioManager(workspace/'scenario.json',enabled_default=False)
    with db._connect() as c:
        c.execute("INSERT INTO devices(id,hostname,vendor) VALUES(91,'R1','cisco')")
        for identity,name in [(901,'Gi0/1'),(902,'Gi0/2')]:
            c.execute('INSERT INTO interfaces(id,device_id,name,interface_type) VALUES(?,91,?,?)',(identity,name,'ethernet'))
    app=FastAPI();app.state.local_db=db;app.include_router(router)
    outcomes=[]
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://ordinary-counter-eval',
            headers={'Authorization':'Bearer '+create_access_token(935,'G9-COUNTER-OWNER','engineer')},timeout=240) as client:
            for surface in ['floating','studio']:
                started=time.monotonic();result=None;error=None
                try:
                    response=await client.post('/api/v1/ai/conversations',json={'assistant_kind':surface});response.raise_for_status()
                    cid=response.json()['id']
                    response=await client.post('/api/v1/ai/conversations/'+cid+'/turns',json={'request_id':str(uuid4()),'prompt':prompt,'model':'qwen2.5:1.5b'})
                    response.raise_for_status();result=response.json()
                    assert [r['tool'] for r in result['observations']]==['network.telemetry']
                    rows=[r for o in result['observations'] for s in o['data']['sources'] for r in s['data']['records']]
                    assert len(rows)==1 and rows[0]['interface']=='Gi0/1'
                    assert rows[0]['errors']==13 and rows[0]['discards']==4 and rows[0]['time']==stamp
                    assert result['context_coverage']['retrieval']['interface_refs']==['901']
                    assert all(e['origin']=='simulated' for e in result['evidence'])
                    assert '13' in result['answer'] and '4' in result['answer']
                    assert '97' not in result['answer'] and 'Gi0/2' not in result['answer']
                    ok=True
                except Exception as exc:ok=False;error=type(exc).__name__+': '+str(exc)
                actual={'result':result,'error':error,'source_scope_correct':ok,'answer_adequacy':'PENDING_FULL_PROSE_REVIEW'}
                (run.path/(surface+'.json')).write_text(json.dumps(actual,indent=2),encoding='utf-8')
                run.record('G9-ORDINARY-COUNTERS-'+surface.upper(),'PASS' if ok else 'FAIL',expected='Correct scoped ordinary provider and exact recorded values',
                    actual=actual,prompt=prompt,latency_ms=round((time.monotonic()-started)*1000,2),classification=None if ok else 'gateway_or_evaluator_failure')
                outcomes.append(ok)
    finally:db.close()
    print(json.dumps({'run':str(run.path),'passed':sum(outcomes),'cases':len(outcomes),'ordinary_user_db_used':False}),flush=True)
    return all(outcomes)


if __name__=='__main__':raise SystemExit(0 if asyncio.run(main()) else 1)
