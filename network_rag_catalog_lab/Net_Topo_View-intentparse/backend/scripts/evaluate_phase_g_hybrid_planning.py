"""Bounded real planning comparison and authenticated gateway replay.

Synthetic records only; no headers/secrets in artifacts and no ordinary DB use.
Existing IntentPlan and gateway validators remain the only planning authority.
"""
import argparse,asyncio,hashlib,json,os,socket,sys,time
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[2]
AUDIT=ROOT/'tmp/phase-g/iterations/20261026-hybrid-g4-advisory'
SPEC=ROOT/'docs/evaluations/phase_g_hybrid_g4_advisory_v1.json'
sys.path.insert(0,str(ROOT/'backend'))

def save(path,data):
    text=json.dumps(data,indent=2,ensure_ascii=False)
    secret=os.getenv('GEMINI_API_KEY','')
    if secret:text=text.replace(secret,'[REDACTED]')
    with path.open('x',encoding='utf-8') as f:f.write(text)

def setup(name):
    out=AUDIT/name;out.mkdir(parents=True,exist_ok=True)
    if (out/'app.db').exists():raise RuntimeError('Preserve original execution; use a separately named corrected run')
    os.environ.update(COGNISHIELD_MODE='local_lab',COGNISHIELD_DB_PATH=str(out/'app.db'),
      COGNISHIELD_AI_ENGINE='langgraph_b3',COGNISHIELD_AI_PLANNING='1',COGNISHIELD_AI_SYNTHESIS='1',
      COGNISHIELD_DEV_SIMULATION='1',COGNISHIELD_AI_OUTCOMES='0',
      COGNISHIELD_AI_HYBRID_USAGE=str(ROOT/'tmp/ai-cloud-usage.json'),
      COGNISHIELD_AI_HYBRID_INPUT_TPM='150000',COGNISHIELD_AI_HYBRID_RPM='15',COGNISHIELD_AI_HYBRID_RPD='500')
    import lab_config
    from db.manager import DatabaseManager
    from llm.gateway_store import ensure_schema
    from local_providers.development import ScenarioManager
    db=DatabaseManager(str(out/'app.db'));db.initialize();ensure_schema(db)
    manager=ScenarioManager(out/'scenario.json');db._development_scenario=manager
    spec=json.loads(SPEC.read_text(encoding='utf-8'))
    for fixture in spec['fixtures'].values():manager.change('import',manager.snapshot()[1]['source_revision'],fixture)
    return out,db,manager,spec

async def plans(name):
    out,db,manager,spec=setup(name)
    from llm.orchestration.planning import propose
    from llm.orchestration.model import RoutingModel
    from llm.gateway_services import inventory_snapshot
    from llm.gateway_references import previous_context_reference
    from llm.gemini_provider import interpret_rest
    import httpx
    original=httpx.AsyncClient.send
    try:
        for case in spec['planning_cases']:
            manager.change('select',manager.snapshot()[1]['source_revision'],scenario_id=spec['fixtures'][case['variant']]['id'])
            inventory=inventory_snapshot(db)
            for arm in ['local','cloud']:
                output=out/(case['id']+'-'+arm+'.json')
                if output.exists():continue
                packets=[];wires=[];clock=time.monotonic()
                local=RoutingModel()
                async def generate(messages,structured=False,model=None,purpose='routing'):
                    packet={'purpose':purpose,'messages':messages,'schema':structured}
                    packets.append(packet)
                    if arm=='cloud':
                        raw,selected,usage=await interpret_rest(messages,structured,timeout=min(35,120-(time.monotonic()-clock)))
                        packet['usage']=usage
                    else:raw,selected=await local.generate(messages,structured=structured,model=model,purpose=purpose)
                    packet.update(raw=raw,model=selected);return raw,selected
                async def observed(client,request,*args,**kw):
                    entry=None
                    if request.url.host=='generativelanguage.googleapis.com' or request.url.path=='/api/chat':
                        entry={'host':request.url.host,'path':request.url.path,'body':json.loads(request.content)};wires.append(entry)
                    response=await original(client,request,*args,**kw)
                    if entry is not None and request.url.host=='generativelanguage.googleapis.com':
                        entry.update(status=response.status_code,response=response.json())
                    return response
                route=None;error=None
                try:
                    with patch.object(httpx.AsyncClient,'send',observed):
                        route=await asyncio.wait_for(propose(case['prompt'],'qwen2.5:1.5b',case['surface'],None,[],
                            case.get('history',[]),inventory,generate,read_only_request=True,
                            previous_reference=previous_context_reference(case.get('previous'))),120)
                except Exception as exc:error={'type':type(exc).__name__,'detail':str(exc)[:600]}
                domains=set(route.network_domains) if route else set()
                expected=set(case['required_domains']);forbidden=set(case.get('prohibited_domains',[]))
                checks={'validated_route':route is not None,'required_domains':expected<=domains,
                        'no_prohibited_domains':not bool(domains&forbidden),
                        'scopes':bool(route) and all(route.source_requests.get(d,{}).get('source_scope')==s for d,s in case.get('scope',{}).items()),
                        'read_only':bool(route) and route.intent in {'answer','explain'},
                        'history':bool(route and route.use_history) if case.get('previous') else True}
                record={'case':case,'arm':arm,'registry_sha256':hashlib.sha256(SPEC.read_bytes()).hexdigest(),
                    'inventory_metadata':inventory,'packets':packets,'wires_without_headers':wires,
                    'route':route.model_dump() if route else None,'error':error,'checks':checks,
                    'latency_ms':round((time.monotonic()-clock)*1000,2),'content_review':'UNREVIEWED; schema/domain checks are not full interpretation adequacy'}
                save(output,record);print(json.dumps({'id':case['id'],'arm':arm,'checks':checks,'latency_ms':record['latency_ms']}),flush=True)
    finally:db.close()

async def gateway(name,remote=False,advice_only=False,final_checks=False):
    out,db,manager,spec=setup(name)
    import httpx,uvicorn
    from fastapi import FastAPI
    from auth.auth import create_access_token
    from llm.gateway_api import router
    from llm.gateway_models import TurnRequest
    from llm.gemini_provider import scenario_approval_context
    from scripts.evaluate_phase_f_registry import selected_capabilities
    from local_providers.chat import runtime
    os.environ['COGNISHIELD_AI_HYBRID_INTERPRET']='1' if remote else '0'
    os.environ['COGNISHIELD_AI_HYBRID_CALLS']='2' if remote else '1'
    # These already frozen synthetic bytes were approved in the previous task.
    assert all(scenario_approval_context(db) is not None for _ in [0])
    app=FastAPI();app.state.local_db=db;app.include_router(router)
    with socket.socket() as s:s.bind(('127.0.0.1',8001))
    server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=8001,log_level='error',access_log=False))
    serving=asyncio.create_task(server.serve())
    for _ in range(100):
        if server.started:break
        await asyncio.sleep(.05)
    original=httpx.AsyncClient.send;token=create_access_token(906,'HYBRID-G4-SYNTHETIC','engineer')
    save(out/'loaded.json',{'model':(await runtime())['active_model'],'cloud':os.getenv('GEMINI_MODEL'),
        'planning':remote,'outcomes':os.getenv('COGNISHIELD_AI_OUTCOMES'),'credential_loaded':bool(os.getenv('GEMINI_API_KEY')),
        'registry_sha256':hashlib.sha256(SPEC.read_bytes()).hexdigest()})
    try:
        async with httpx.AsyncClient(base_url='http://127.0.0.1:8001',headers={'Authorization':'Bearer '+token},trust_env=False,timeout=125) as client:
            async def turn(cid,prompt,filename):
                body=TurnRequest(request_id=uuid4(),prompt=prompt,model='qwen2.5:1.5b')
                ctx=(await client.get('/api/v1/ai/hybrid-context')).json()
                approval=await client.post('/api/v1/ai/conversations/'+cid+'/approve-synthetic-cloud',
                    json={'turn':body.model_dump(mode='json'),'expected_source_revision':ctx['source_revision']})
                approval.raise_for_status()
                wires=[]
                async def observed(http,request,*args,**kw):
                    entry=None
                    if request.url.host=='generativelanguage.googleapis.com' or request.url.path=='/api/chat':
                        entry={'host':request.url.host,'path':request.url.path,'body':json.loads(request.content)};wires.append(entry)
                    response=await original(http,request,*args,**kw)
                    if entry is not None and request.url.host=='generativelanguage.googleapis.com':
                        entry.update(status=response.status_code,response=response.json())
                    return response
                start=time.monotonic();error=None;result={}
                try:
                    with patch.object(httpx.AsyncClient,'send',observed):
                        response=await client.post('/api/v1/ai/conversations/'+cid+'/turns',json=body.model_dump(mode='json'))
                        response.raise_for_status();result=response.json()
                except Exception as exc:error={'type':type(exc).__name__,'detail':str(exc)[:500]}
                record={'prompt':prompt,'conversation':cid,'remote_planning_enabled':remote,'scenario':ctx,
                    'result':result,'tools':sorted(selected_capabilities(result)),'wires_without_headers':wires,
                    'latency_ms':round((time.monotonic()-start)*1000,2),'error':error}
                save(out/(filename+'.json'),record)
                print(json.dumps({'case':filename,'tools':record['tools'],'model':result.get('model'),'latency_ms':record['latency_ms'],
                    'hybrid':result.get('context_coverage',{}).get('hybrid')}),flush=True)
                return record
            if remote:
                # Frozen difficult multi-source cases only; explicit published
                # routing remains separate and is not counted as remote planning.
                cases=[c for c in spec['planning_cases'] if c['id'] in {'G4-01','G4-03','G4-04'}]
            else:cases=[c for c in spec['planning_cases'] if c['id'] in {'G4-01','G4-03','G4-04','G4-05'}]
            if advice_only:cases=[]
            if final_checks:cases=[c for c in spec['planning_cases'] if c['id']=='G4-05']
            for case in cases:
                manager.change('select',manager.snapshot()[1]['source_revision'],scenario_id=spec['fixtures'][case['variant']]['id'])
                res=await client.post('/api/v1/ai/conversations',json={'assistant_kind':case['surface']});res.raise_for_status();cid=res.json()['id']
                await turn(cid,case['prompt'],case['id'])
            if not remote:
                for case in [] if final_checks else spec['advisory_cases']:
                    for surface in ['floating','studio']:
                        manager.change('select',manager.snapshot()[1]['source_revision'],scenario_id=spec['fixtures'][case['variant']]['id'])
                        res=await client.post('/api/v1/ai/conversations',json={'assistant_kind':surface});cid=res.json()['id']
                        await turn(cid,case['setup'],case['id']+'-'+surface+'-setup')
                        r=await turn(cid,case['prompt'],case['id']+'-'+surface)
                        assert not r['tools'] and not r['result'].get('observations'),r['tools']
                for i,c in enumerate([] if advice_only else spec['positive_controls']):
                    surface=['floating','studio'][i]
                    manager.change('select',manager.snapshot()[1]['source_revision'],scenario_id=spec['fixtures']['healthy']['id'])
                    res=await client.post('/api/v1/ai/conversations',json={'assistant_kind':surface});cid=res.json()['id']
                    r=await turn(cid,c['prompt'],'CONTROL-'+surface)
                    assert not r['result'].get('context_coverage',{}).get('hybrid',{}).get('remote_calls')
    finally:
        server.should_exit=True;await serving;db.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['plans','gateway'])
    parser.add_argument('--name',required=True);parser.add_argument('--remote',action='store_true')
    parser.add_argument('--advice-only',action='store_true');parser.add_argument('--final-checks',action='store_true');args=parser.parse_args()
    asyncio.run(plans(args.name) if args.mode=='plans' else gateway(args.name,args.remote,args.advice_only,args.final_checks))

