"""Small authenticated hybrid gateway pilot, disposable synthetic SQLite only."""
import asyncio
import argparse
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
OUT=ROOT/'tmp/phase-g/iterations/20261025-hybrid-gemini-resume/gateway'


async def main(suite='main'):
    global OUT
    if suite!='main':OUT=OUT.parent/('gateway-'+suite)
    OUT.mkdir(parents=True,exist_ok=True)
    db_path=OUT/'synthetic.db'
    if db_path.exists():raise RuntimeError('Pilot DB already exists; preserve prior run and use a separately named rerun')
    os.environ.update(COGNISHIELD_DB_PATH=str(db_path),COGNISHIELD_AI_ENGINE='langgraph_b3',
        COGNISHIELD_AI_PLANNING='1',COGNISHIELD_AI_SYNTHESIS='1',COGNISHIELD_AI_OUTCOMES='0',
        COGNISHIELD_DEV_SIMULATION='1',COGNISHIELD_AI_HYBRID='1',GEMINI_MODEL='gemini-3.8-flash',
        COGNISHIELD_LOCAL_OLLAMA_MODEL='qwen2.5:1.5b')
    import httpx
    from fastapi import FastAPI
    from auth.auth import create_access_token
    from db.manager import DatabaseManager
    from llm.gateway_api import router
    from llm.gateway_store import ensure_schema,ConversationStore
    from llm.gateway_models import TurnRequest
    from llm.gemini_provider import external_request_identity
    from local_providers.development import ScenarioManager
    from scripts.evaluate_phase_f_registry import activate_fixture,selected_capabilities
    spec=json.loads((ROOT/'docs/evaluations/phase_g_approach_a_reconciliation_v1.json').read_text(encoding='utf-8'))
    cases=[
        ('GW01','floating','interface_down','Use Willow-Relay interface administrative and operational observations together with the declared forwarding trace to explain whether a route is sufficient for delivery.',False,False),
        ('GW02','studio','interface_down','Use Willow-Relay interface administrative and operational observations together with the declared forwarding trace to explain whether a route is sufficient for delivery.',False,False),
        ('GW03','floating','unknown','Read Spruce-Start saved configuration and read its syslog, then explain what the unavailable log source does and does not establish.',True,False),
        ('GW04','studio','unknown','Read Spruce-Start saved configuration and read its syslog, then explain what the unavailable log source does and does not establish.',True,False),
        ('GW05','floating','healthy','Hello! What is 19 multiplied by 7?',False,False),
        ('GW06','studio','healthy','Hello! What is 12 plus 8?',False,False),
        ('GW07','floating','interface_down','Use Willow-Relay interface administrative and operational observations together with the declared forwarding trace to explain whether a route is sufficient for delivery.',False,True),
        ('GW08','studio','healthy','Retrieve the published configure_ospf requirements and Spruce-Start saved configuration. Explain the supported mapping and any information that remains unverified; do not generate.',True,False),
        ('GW09','floating','unknown','Which read-only evidence should I request next to resolve that uncertainty? Do not collect or change anything.',False,False),
        ('GW10','floating','healthy','Describe the intended links incident to Willow-Relay. Keep each device name beside its own recorded port.',False,False),
    ]
    selected={'main':{'GW01','GW02','GW03','GW04','GW05','GW06','GW07'},
              'compound':{'GW03','GW04'},'knowledge':{'GW08'},'advice':{'GW09'},'topology':{'GW10'}}[suite]
    cases=[row for row in cases if row[0] in selected]
    (OUT/'specification.json').write_text(json.dumps({'cases':cases,'scope':'Seven API journeys; duplicated surface/fault-injection cases are not independent generalization. No ordinary DB, no server, no browser.','expected':{'GW01_GW02':'Scoped failed-forward/down-egress causal explanation, source identities preserved; remote synthesis only after authorized reads.','GW03_GW04':'Both exact saved commands and unavailable syslog limitation. Optional same-plan Gemini refinement, no Approach A.','GW05_GW06':'Local Qwen only,133or20; no readers or cloud.','GW07':'Injected429cloud failure; verified evidence retained with labelled fallback; no model reasoning credit.'}},indent=2),encoding='utf-8')
    db=DatabaseManager(str(db_path));db.initialize();ensure_schema(db)
    manager=ScenarioManager(OUT/'scenario.json');db._development_scenario=manager
    app=FastAPI();app.state.local_db=db;app.include_router(router)
    user={'username':'HYBRID-SYNTHETIC-EVALUATOR','role':'engineer','user_id':903}
    token=create_access_token(903,user['username'],'engineer')
    original_send=httpx.AsyncClient.send
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://hybrid-synthetic',
            headers={'Authorization':'Bearer '+token},timeout=125) as client:
            for identity,surface,variant,prompt,interpret,inject in cases:
                activate_fixture(manager,spec['network_fixtures'][variant])
                created=await client.post('/api/v1/ai/conversations',json={'assistant_kind':surface});created.raise_for_status();cid=created.json()['id']
                body=TurnRequest(request_id=uuid4(),prompt=prompt,model='qwen2.5:1.5b')
                store=ConversationStore(db)
                setup=None
                if identity=='GW09':
                    setup_body=TurnRequest(request_id=uuid4(),prompt='Read the available operational evidence for Spruce-Start.',model='qwen2.5:1.5b')
                    db._ai_external_approvals=frozenset({external_request_identity(user['username'],surface,cid,setup_body,store.history(cid,user))})
                    setup_response=await client.post('/api/v1/ai/conversations/'+cid+'/turns',json=setup_body.model_dump(mode='json'))
                    setup_response.raise_for_status();setup=setup_response.json()
                db._ai_external_approvals=frozenset({external_request_identity(user['username'],surface,cid,body,store.history(cid,user))})
                os.environ['COGNISHIELD_AI_HYBRID_CALLS']='2' if interpret else '1'
                os.environ['COGNISHIELD_AI_HYBRID_INTERPRET']='1' if interpret else '0'
                calls=[]
                async def observed_send(http,request,*args,**kwargs):
                    external=request.url.host=='generativelanguage.googleapis.com'
                    entry=None
                    if request.url.path in {'/api/chat','/api/embed','/v1beta/interactions'}:
                        entry={'host':request.url.host,'path':request.url.path,'body':json.loads(request.content)};calls.append(entry)
                    if external and inject:
                        if entry is not None:entry['injected_http']=429
                        return httpx.Response(429,json={'error':{'status':'RESOURCE_EXHAUSTED','message':'Synthetic injected quota failure'}},request=request)
                    response=await original_send(http,request,*args,**kwargs)
                    if external and entry is not None:
                        data=response.json();entry.update(http_status=response.status_code,usage=data.get('usage'),
                            raw_model_outputs=[step for step in data.get('steps',[]) if step.get('type')=='model_output'],
                            provider_error=data.get('error'))
                    return response
                started=time.monotonic();result={};error=None
                try:
                    with patch.object(httpx.AsyncClient,'send',observed_send):
                        async with asyncio.timeout(121):
                            response=await client.post('/api/v1/ai/conversations/'+cid+'/turns',json=body.model_dump(mode='json'))
                            response.raise_for_status();result=response.json()
                except Exception as exc:error={'type':type(exc).__name__,'message':str(exc)[:600]}
                record={'id':identity,'assistant':surface,'variant':variant,'prompt':prompt,'interpretation_experiment':interpret,
                    'setup':setup,
                    'injected_cloud_failure':inject,'latency_ms':round((time.monotonic()-started)*1000,2),
                    'result':result,'error':error,'provider_requests_without_headers':calls,
                    'actual_tools':sorted(selected_capabilities(result)),'assessment':'UNREVIEWED; HTTPsuccess is not task adequacy'}
                # All bodies are synthetic and approved; no headers or credential copied.
                secret=os.getenv('GEMINI_API_KEY','')
                safe=json.dumps(record,ensure_ascii=False)
                if secret:safe=safe.replace(secret,'[REDACTED]')
                with (OUT/(identity+'.json')).open('x',encoding='utf-8') as handle:handle.write(safe)
                print(json.dumps({'id':identity,'status':result.get('status'),'kind':result.get('kind'),
                    'tools':record['actual_tools'],'hybrid':result.get('context_coverage',{}).get('hybrid'),
                    'latency_ms':record['latency_ms'],'error':error}),flush=True)
            other=create_access_token(904,'OTHER-SYNTHETIC-OWNER','engineer')
            denied=await client.get('/api/v1/ai/conversations/'+cid,headers={'Authorization':'Bearer '+other})
            (OUT/'ownership-check.json').write_text(json.dumps({'different_owner_http_status':denied.status_code,
                'pass':denied.status_code in {403,404},'cloud_calls':0}),encoding='utf-8')
    finally:
        db.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite',choices=['main','compound','knowledge','advice','topology'],default='main')
    asyncio.run(main(parser.parse_args().suite))
