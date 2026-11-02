"""Frozen, authenticated, source-derived hybrid qualification. No answer mocks.

One disposable service on 8001, sequential arms, real signed owner requests and
normal synthetic-cloud consent. Instrumentation calls the original methods;
oracle/grade fields are never supplied to the application or inference model.
"""
import argparse,asyncio,copy,hashlib,json,os,socket,sys,time
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2]
AUDIT=ROOT/'tmp/phase-g/iterations/20261026-hybrid-g5g6-qualification'
SPEC=ROOT/'docs/evaluations/phase_g_hybrid_quality_qualification_v1.json'
sys.path.insert(0,str(ROOT/'backend'))

def save(path,value):
    text=json.dumps(value,indent=2,ensure_ascii=False,default=str)
    secret=os.getenv('GEMINI_API_KEY','')
    if secret:text=text.replace(secret,'[REDACTED]')
    with path.open('x',encoding='utf-8') as f:f.write(text)

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

async def main(args):
    out=AUDIT/args.name;out.mkdir(parents=True,exist_ok=True)
    os.environ.update(COGNISHIELD_MODE='local_lab',COGNISHIELD_DB_PATH=str(out/'app.db'),
        COGNISHIELD_AI_ENGINE='langgraph_b3',COGNISHIELD_AI_PLANNING='1',COGNISHIELD_AI_SYNTHESIS='1',
        COGNISHIELD_DEV_SIMULATION='1',COGNISHIELD_AI_OUTCOMES='0',COGNISHIELD_AI_HYBRID_INTERPRET='0',
        COGNISHIELD_AI_HYBRID_CALLS='1',COGNISHIELD_LOCAL_OLLAMA_MODEL='qwen2.5:1.5b',
        GEMINI_MODEL='gemini-3.5-flash-lite',COGNISHIELD_AI_HYBRID_USAGE=str(ROOT/'tmp/ai-cloud-usage.json'),
        COGNISHIELD_AI_HYBRID_RPM='15',COGNISHIELD_AI_HYBRID_INPUT_TPM='150000',COGNISHIELD_AI_HYBRID_RPD='500')
    import lab_config,httpx,uvicorn
    from db.manager import DatabaseManager
    from local_providers.development import ScenarioManager
    from local_providers.chat import runtime
    from llm.gateway_store import ensure_schema
    from llm.gateway_api import router
    from llm.gateway_models import TurnRequest
    from llm.gemini_provider import scenario_approval_context
    from llm.orchestration.model import RoutingModel
    from llm.tools import ToolRegistry
    from auth.auth import create_access_token
    from fastapi import FastAPI
    from scripts.evaluate_phase_f_registry import selected_capabilities
    spec=json.loads(SPEC.read_text(encoding='utf-8'));freeze=json.loads((AUDIT/'freeze-receipt.json').read_text())
    assert digest(SPEC)==freeze['sha256'],'Frozen registry changed'
    assert Path(lab_config.DB_PATH)==out/'app.db','Disposable DB path must be effective before import'
    appfiles={str(p.relative_to(ROOT)).replace('\\','/'):digest(p) for d in ['backend/llm','backend/local_providers','backend/development'] for p in (ROOT/d).rglob('*.py')}
    original_start=out/'runtime-freeze.json'
    if original_start.exists():
        old=json.loads(original_start.read_text());assert old['application_files']==appfiles,'Cannot silently resume across application revision'
    else:save(original_start,{'at':datetime.now(timezone.utc).isoformat(),'registry_sha256':digest(SPEC),'application_files':appfiles,
        'configuration':spec['settings'],'key_loaded':bool(os.getenv('GEMINI_API_KEY')),'db':str(lab_config.DB_PATH),
        'transport':'Actual HTTP 127.0.0.1:8001, signed JWT, owner/surface API, normal consent and registry invocation',
        'grading':'Source-derived independently checkable, implementation-assistant graded, not blinded/external'})
    db=DatabaseManager(str(out/'app.db'));db.initialize();ensure_schema(db)
    # One existing manager per test condition avoids accumulating 30 extra
    # scenarios over the application's existing bounded library. No quota is
    # weakened, and both arms see exactly the same activated revision.
    app=FastAPI();app.state.local_db=db;app.include_router(router)
    with socket.socket() as check:check.bind(('127.0.0.1',8001))
    server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=8001,log_level='error',access_log=False))
    serving=asyncio.create_task(server.serve())
    for _ in range(100):
        if server.started:break
        await asyncio.sleep(.05)
    assert server.started
    original_generate=RoutingModel.generate;original_invoke=ToolRegistry.invoke;original_send=httpx.AsyncClient.send
    token=create_access_token(916,'G5G6-QUALIFICATION-SYNTHETIC','engineer')
    try:
        async with httpx.AsyncClient(base_url='http://127.0.0.1:8001',headers={'Authorization':'Bearer '+token},timeout=125,trust_env=False) as client:
            if not (out/'loaded.json').exists():save(out/'loaded.json',{'runtime':await runtime(),'model_configuration':spec['settings'],'consent_scope':'Frozen synthetic only; no editor/uploads','credential_loaded':bool(os.getenv('GEMINI_API_KEY'))})
            for case in spec['cases'][args.offset:args.offset+args.limit]:
                if all((out/(case['id']+'-'+a+'.json')).exists() for a in args.arms.split(',')):continue
                manager=ScenarioManager(out/(case['id']+'-scenario.json'));db._development_scenario=manager
                if case['scenario'] not in manager._read()['scenarios']:
                    manager.change('import',manager.snapshot()[1]['source_revision'],spec['fixtures'][case['scenario']])
                # Operator-approved frozen synthetic bytes, still requiring
                # exact owner opt-in for each hybrid turn below.
                os.environ['COGNISHIELD_AI_HYBRID_SCENARIOS']=scenario_approval_context(db)['scenario_digest']
                for arm in args.arms.split(','):
                    path=out/(case['id']+'-'+arm+'.json')
                    if path.exists():continue
                    os.environ['COGNISHIELD_AI_HYBRID']='1' if arm=='hybrid' else '0'
                    response=await client.post('/api/v1/ai/conversations',json={'assistant_kind':case['surface']});response.raise_for_status();cid=response.json()['id']
                    async def turn(prompt,is_setup=False):
                        body=TurnRequest(request_id=uuid4(),prompt=prompt,model='qwen2.5:1.5b')
                        ctx=(await client.get('/api/v1/ai/hybrid-context')).json()
                        approval_status=None
                        if arm=='hybrid':
                            approval=await client.post('/api/v1/ai/conversations/'+cid+'/approve-synthetic-cloud',json={'turn':body.model_dump(mode='json'),'expected_source_revision':ctx['source_revision']})
                            approval_status=approval.status_code;approval.raise_for_status()
                        packets=[];reads=[];wires=[]
                        async def observed_generate(instance,*values,**kw):
                            row={'purpose':kw.get('purpose','routing'),'messages':copy.deepcopy(values[0]),'structured':copy.deepcopy(kw.get('structured',False)),'started_ms':round((time.monotonic()-started)*1000,2)};packets.append(row);at=time.monotonic()
                            try:
                                raw,selected=await original_generate(instance,*values,**kw);row.update(raw=raw,model=selected);return raw,selected
                            except Exception as exc:row['error']={'type':type(exc).__name__,'detail':str(exc)[:500]};raise
                            finally:row['elapsed_ms']=round((time.monotonic()-at)*1000,2)
                        async def observed_invoke(instance,name,arguments,authorization):
                            row={'tool':name,'arguments':copy.deepcopy(arguments),'authorization':{'assistant':authorization.assistant_kind,'owner':authorization.principal,'conversation':authorization.conversation_id,'allowed_tools':sorted(authorization.allowed_tools)},'started_ms':round((time.monotonic()-started)*1000,2)};reads.append(row);at=time.monotonic()
                            try:
                                result=await original_invoke(instance,name,arguments,authorization);row['result']=result.model_dump(mode='json');return result
                            except Exception as exc:row['error']={'type':type(exc).__name__,'detail':str(exc)[:500]};raise
                            finally:row['elapsed_ms']=round((time.monotonic()-at)*1000,2)
                        async def observed_send(http,request,*values,**kw):
                            entry=None
                            if request.url.host=='generativelanguage.googleapis.com' or request.url.path=='/api/chat':
                                entry={'host':request.url.host,'path':request.url.path,'body':json.loads(request.content),'started_ms':round((time.monotonic()-started)*1000,2)};wires.append(entry)
                            res=await original_send(http,request,*values,**kw)
                            if entry is not None:
                                entry['http_status']=res.status_code
                                if request.url.host=='generativelanguage.googleapis.com':
                                    await res.aread();entry['response']=res.json()
                            return res
                        started=time.monotonic();result={};error=None;status=None
                        try:
                            with patch.object(RoutingModel,'generate',observed_generate),patch.object(ToolRegistry,'invoke',observed_invoke),patch.object(httpx.AsyncClient,'send',observed_send):
                                res=await client.post('/api/v1/ai/conversations/'+cid+'/turns',json=body.model_dump(mode='json'));status=res.status_code;res.raise_for_status();result=res.json()
                        except Exception as exc:error={'type':type(exc).__name__,'detail':str(exc)[:600]}
                        return {'prompt':prompt,'request':body.model_dump(mode='json'),'is_setup':is_setup,'scenario':ctx,'consent_status':approval_status,'result':result,'http_status':status,'error':error,'latency_ms':round((time.monotonic()-started)*1000,2),'model_packets':packets,'authorized_reads':reads,'wires_without_headers':wires,'tools':sorted(selected_capabilities(result))}
                    setup=await turn(case['setup'],True) if case.get('setup') else None
                    record=await turn(case['prompt'])
                    record.update(case_id=case['id'],surface=case['surface'],arm=arm,conversation=cid,setup=setup,registry_sha256=digest(SPEC),started_at=datetime.now(timezone.utc).isoformat(),expected=case,grade='UNREVIEWED: HTTP/schema/tool success is not answer quality')
                    save(path,record)
                    print(json.dumps({'case':case['id'],'arm':arm,'status':record['http_status'],'tools':record['tools'],'model':record['result'].get('model'),'ms':record['latency_ms'],'error':record['error']}),flush=True)
                    # Concurrency1; ensure cloud emissions are well below15/minute.
                    if any(w['host']=='generativelanguage.googleapis.com' for w in record['wires_without_headers']):await asyncio.sleep(4.2)
    finally:
        server.should_exit=True;await serving;db.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--name',default='frozen-v1');parser.add_argument('--offset',type=int,default=0);parser.add_argument('--limit',type=int,default=30);parser.add_argument('--arms',default='local,hybrid');args=parser.parse_args()
    asyncio.run(main(args))

