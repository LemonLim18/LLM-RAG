"""Small real authenticated gateway check; optional same disposable browser server.

No provider/tool mocks. Trace headers and credentials are never serialized.
"""
import argparse,asyncio,copy,hashlib,json,os,socket,subprocess,sys,time
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'tmp/phase-g/iterations/20261026-model-neutral'
SPEC=ROOT/'docs/evaluations/phase_g_model_neutral_functional_v1.json'
sys.path.insert(0,str(ROOT/'backend'))

def save(path,value):
    text=json.dumps(value,indent=2,ensure_ascii=False,default=str)
    for key in ['GEMINI_API_KEY','OPENAI_API_KEY']:
        if os.getenv(key):text=text.replace(os.environ[key],'[REDACTED]')
    with path.open('x',encoding='utf-8') as file:file.write(text)

async def main(args):
    target=OUT/args.name;target.mkdir(parents=True,exist_ok=True)
    os.environ.update(COGNISHIELD_MODE='local_lab',COGNISHIELD_DB_PATH=str(target/'app.db'),
        COGNISHIELD_DEV_SIMULATION='1',COGNISHIELD_DEV_STATE=str(target/'scenario.json'),
        COGNISHIELD_AI_ENGINE='langgraph_b3',COGNISHIELD_AI_PLANNING='1',COGNISHIELD_AI_SYNTHESIS='1',
        COGNISHIELD_AI_MULTI_MODEL_EXPERIMENT='1',COGNISHIELD_AI_HYBRID='1',COGNISHIELD_AI_HYBRID_INTERPRET='0',
        COGNISHIELD_AI_OUTCOMES='0',COGNISHIELD_AI_EXPERIMENT_SEMANTIC_VERIFIER='off',
        COGNISHIELD_LOCAL_OLLAMA_MODEL='qwen2.5:1.5b',GEMINI_MODEL='gemini-3.5-flash-lite')
    import lab_config,httpx,uvicorn
    from local_app import app
    from llm.gemini_provider import scenario_approval_context
    from llm.orchestration.model import RoutingModel
    from llm.tools import ToolRegistry
    from llm.model_roles import consent_manifest
    from auth.auth import create_access_token
    from fastapi import HTTPException
    for port in [8001,5174]:
        with socket.socket() as check:check.bind(('127.0.0.1',port))
    app.add_middleware(__import__('fastapi.middleware.cors',fromlist=['CORSMiddleware']).CORSMiddleware,
        allow_origins=['http://127.0.0.1:5174'],allow_methods=['*'],allow_headers=['*'])
    registry=json.loads(SPEC.read_text(encoding='utf-8'));frozen=json.loads((OUT/'freeze-receipt.json').read_text())
    assert hashlib.sha256(SPEC.read_bytes()).hexdigest()==frozen['sha256']
    server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=8001,log_level='error',access_log=False))
    serving=asyncio.create_task(server.serve());vite=None
    for _ in range(300):
        if server.started:break
        if serving.done():await serving
        await asyncio.sleep(.1)
    assert server.started
    db=app.state.local_db;assert Path(db._db_path).resolve()==(target/'app.db').resolve()
    manager=db._development_scenario
    if registry['fixture']['id'] not in manager._read()['scenarios']:
        manager.change('import',manager.snapshot()[1]['source_revision'],registry['fixture'])
    os.environ['COGNISHIELD_AI_HYBRID_SCENARIOS']=scenario_approval_context(db)['scenario_digest']
    token=create_access_token(1,'admin','admin');all_packets=[];all_reads=[];all_wires=[];calls=0
    original_generate=RoutingModel.generate;original_invoke=ToolRegistry.invoke;original_send=httpx.AsyncClient.send
    async def generate(instance,*values,**kw):
        row={'messages':copy.deepcopy(values[0]),'schema':kw.get('structured',False),'purpose':kw.get('purpose','routing')};all_packets.append(row)
        try:
            raw,model=await original_generate(instance,*values,**kw);row.update(raw=raw,model=model);return raw,model
        except Exception as e:row['error']=str(e)[:500];raise
    async def invoke(instance,name,arguments,authorization):
        row={'tool':name,'arguments':copy.deepcopy(arguments),'owner':authorization.principal,'surface':authorization.assistant_kind};all_reads.append(row)
        result=await original_invoke(instance,name,arguments,authorization);row['result']=result.model_dump(mode='json');return result
    async def send(instance,request,*a,**kw):
        nonlocal calls
        row=None
        if request.url.host=='generativelanguage.googleapis.com':
            if calls>=20:raise HTTPException(429,'This bounded acceptance run exhausted its20-call allowance')
            calls+=1;row={'path':request.url.path,'body':json.loads(request.content),'at':time.time()};all_wires.append(row)
        response=await original_send(instance,request,*a,**kw)
        if row is not None:
            await response.aread();row['http_status']=response.status_code;row['response']=response.json()
        return response
    try:
        with patch.object(RoutingModel,'generate',generate),patch.object(ToolRegistry,'invoke',invoke),patch.object(httpx.AsyncClient,'send',send):
            save(target/'effective.json',{'roles':consent_manifest(),'credential_loaded':bool(os.getenv('GEMINI_API_KEY')),'scenario':scenario_approval_context(db),'db':str(lab_config.DB_PATH),'historical_scores_unchanged':True})
            async with httpx.AsyncClient(base_url='http://127.0.0.1:8001',headers={'Authorization':'Bearer '+token},timeout=125,trust_env=False) as client:
                conversations={}
                for case in ([] if args.skip_turns else registry['cases']):
                    path=target/(case['id']+'.json')
                    if path.exists():continue  # Never replace original executions.
                    if case.get('continue'):cid=conversations[case['continue']]
                    else:
                        response=await client.post('/api/v1/ai/conversations',json={'assistant_kind':case['surface']});response.raise_for_status();cid=response.json()['id']
                    conversations[case['id']]=cid
                    from uuid import uuid4
                    body={'request_id':str(uuid4()),'prompt':case['prompt'],'model':'qwen2.5:1.5b'}
                    if case.get('consent',True):
                        ctx=(await client.get('/api/v1/ai/hybrid-context')).json()
                        approval=await client.post('/api/v1/ai/conversations/'+cid+'/approve-synthetic-cloud',json={'turn':body,'expected_source_revision':ctx['source_revision']});approval.raise_for_status()
                    p,r,w=len(all_packets),len(all_reads),len(all_wires);start=time.monotonic()
                    response=await client.post('/api/v1/ai/conversations/'+cid+'/turns',json=body)
                    result={'case':case['id'],'surface':case['surface'],'request':body,'expected':case,'status':response.status_code,'seconds':time.monotonic()-start,'result':response.json(),
                        'model_packets':all_packets[p:],'reads':all_reads[r:],'wires_without_headers':all_wires[w:]}
                    save(path,result);print(json.dumps({'case':case['id'],'status':response.status_code,'seconds':result['seconds'],'cloud_calls':len(result['wires_without_headers']),'tools':[row['tool'] for row in result['reads']]}),flush=True)
            if args.serve:
                vite_log=(target/'vite.log').open('w',encoding='utf-8')
                vite=subprocess.Popen(['node',str(ROOT/'frontend/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','5174','--strictPort'],cwd=ROOT/'frontend',
                    env={**os.environ,'VITE_API_URL':'http://127.0.0.1:8001','VITE_WS_URL':'ws://127.0.0.1:8001/ws'},stdout=vite_log,stderr=subprocess.STDOUT)
                save(target/'ready.json',{'backend':8001,'frontend':5174,'pid':os.getpid(),'quota_calls_so_far':calls,'stop_file':str(target/'STOP')})
                while not (target/'STOP').exists():await asyncio.sleep(.5)
                save(target/'browser-traces.json',{'packets':all_packets,'reads':all_reads,'wires_without_headers':all_wires,'total_cloud_calls':calls})
    finally:
        if vite is not None:
            vite.terminate();vite.wait(timeout=15)
        server.should_exit=True;await serving

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--name',default='functional-v1');parser.add_argument('--serve',action='store_true');parser.add_argument('--skip-turns',action='store_true');args=parser.parse_args()
    asyncio.run(main(args))
