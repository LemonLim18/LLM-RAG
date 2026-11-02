"""Frozen full-gateway qualification; real models, readers and signed owner API.

Oracle fields live only in evaluation records, never in model requests. Results
are append-only. Reuse one disposable8001workspace; serve5174only for acceptance.
"""
import argparse,asyncio,copy,hashlib,json,os,socket,subprocess,sys,time
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
AUDIT=ROOT/'tmp/phase-g/iterations/20261026-multi-model-qualification'
SPEC=ROOT/'docs/evaluations/phase_g_multi_model_g4_g6_v1.json'

def save(path,value):
    text=json.dumps(value,indent=2,ensure_ascii=False,default=str)
    for key in ['GEMINI_API_KEY','OPENAI_API_KEY']:
        if os.getenv(key):text=text.replace(os.environ[key],'[REDACTED]')
    with path.open('x',encoding='utf-8') as f:f.write(text)

async def main(args):
    out=ROOT/args.audit/args.name;out.mkdir(parents=True,exist_ok=True)
    spec_path=ROOT/args.registry;freeze_path=ROOT/args.freeze
    os.environ.update(COGNISHIELD_MODE='local_lab',COGNISHIELD_DB_PATH=str(out/'app.db'),COGNISHIELD_DEV_STATE=str(out/'initial-scenario.json'),
        COGNISHIELD_DEV_SIMULATION='1',COGNISHIELD_AI_ENGINE='langgraph_b3',COGNISHIELD_AI_PLANNING='1',COGNISHIELD_AI_SYNTHESIS='1',
        COGNISHIELD_AI_HYBRID='1',COGNISHIELD_AI_MULTI_MODEL_EXPERIMENT='1',COGNISHIELD_AI_HYBRID_INTERPRET='0',COGNISHIELD_AI_OUTCOMES='0',
        COGNISHIELD_AI_EXPERIMENT_SEMANTIC_VERIFIER='off',COGNISHIELD_AI_EVIDENCE_REFINE='1',COGNISHIELD_AI_MULTI_MODEL_CALLS='3',
        COGNISHIELD_AI_COMPLEX_PLANNER_PROVIDER='google',COGNISHIELD_AI_COMPLEX_PLANNER_MODEL='gemini-3.1-flash-lite',
        COGNISHIELD_AI_REASONER_PROVIDER='google',COGNISHIELD_AI_REASONER_MODEL='gemini-3.5-flash-lite',
        COGNISHIELD_AI_COMPLEX_PLANNER_SCHEMA_MODE='validated_json',COGNISHIELD_AI_REASONER_SCHEMA_MODE='validated_json',
        COGNISHIELD_AI_COMPLEX_PLANNER_THINKING='low',COGNISHIELD_AI_REASONER_THINKING='low',
        COGNISHIELD_LOCAL_OLLAMA_MODEL='qwen2.5:1.5b',GEMINI_MODEL='gemini-3.5-flash-lite')
    os.environ['COGNISHIELD_AI_COMPLETENESS']='1' if args.completeness else '0'
    os.environ['COGNISHIELD_AI_EVIDENCE_HARNESS']='1' if args.harness else '0'
    import lab_config,httpx,uvicorn
    from local_app import app
    from llm.gemini_provider import scenario_approval_context
    from llm.orchestration.model import RoutingModel
    from llm.tools import ToolRegistry
    from llm.model_roles import consent_manifest
    from local_providers.development import ScenarioManager
    from auth.auth import create_access_token
    from fastapi import HTTPException
    for port in [8001,5174]:
        with socket.socket() as check:check.bind(('127.0.0.1',port))
    app.add_middleware(__import__('fastapi.middleware.cors',fromlist=['CORSMiddleware']).CORSMiddleware,allow_origins=['http://127.0.0.1:5174'],allow_methods=['*'],allow_headers=['*'])
    spec=json.loads(spec_path.read_text(encoding='utf-8'));freeze=json.loads(freeze_path.read_text(encoding='utf-8'))
    assert hashlib.sha256(spec_path.read_bytes()).hexdigest()==freeze['sha256']
    manifest={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for d in ['backend/llm','backend/local_providers','backend/development'] for p in (ROOT/d).rglob('*.py')}
    if (out/'runtime-freeze.json').exists():assert json.loads((out/'runtime-freeze.json').read_text())['source_hashes']==manifest,'Cannot mix source revisions within one cohort'
    else:save(out/'runtime-freeze.json',{'source_hashes':manifest,'roles':consent_manifest(),'registry_sha256':freeze['sha256'],'at':datetime.now(timezone.utc).isoformat()})
    server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=8001,log_level='error',access_log=False));serving=asyncio.create_task(server.serve());vite=None
    for _ in range(300):
        if server.started:break
        if serving.done():await serving
        await asyncio.sleep(.1)
    assert server.started
    db=app.state.local_db;assert Path(db._db_path).resolve()==(out/'app.db').resolve()
    packets=[];reads=[];wires=[];cloud=0
    original_generate=RoutingModel.generate;original_invoke=ToolRegistry.invoke;original_send=httpx.AsyncClient.send
    # Diagnostic-only replay of the historical adapter loss. Real authorization,
    # readers, provider calls and validation remain in use; no tool results are
    # fabricated. This is an ablation, not the historical code revision.
    from llm.orchestration import engine
    original_context=engine.network_context
    async def scoped_context(*values,**kw):
        if getattr(args,'state_scope_reference',False):
            domains=kw.get('domains_override')
            if domains==['state']:kw['interface_refs_override']=None
        return await original_context(*values,**kw)
    async def generate(instance,*values,**kw):
        start=time.monotonic();row={'messages':copy.deepcopy(values[0]),'schema':copy.deepcopy(kw.get('structured',False)),'purpose':kw.get('purpose','routing'),'at':time.time()};packets.append(row)
        try:
            raw,model=await original_generate(instance,*values,**kw);row.update(raw=raw,model=model);return raw,model
        except Exception as e:row['error']={'type':type(e).__name__,'detail':str(e)[:500]};raise
        finally:row['seconds']=time.monotonic()-start
    async def invoke(instance,name,arguments,authorization):
        start=time.monotonic();row={'tool':name,'arguments':copy.deepcopy(arguments),'owner':authorization.principal,'surface':authorization.assistant_kind,'at':time.time()};reads.append(row)
        try:
            result=await original_invoke(instance,name,arguments,authorization);row['result']=result.model_dump(mode='json');return result
        except Exception as e:row['error']=str(e)[:400];raise
        finally:row['seconds']=time.monotonic()-start
    async def send(instance,request,*a,**kw):
        nonlocal cloud
        row=None
        if request.url.host=='generativelanguage.googleapis.com':
            if cloud>=args.max_cloud:raise HTTPException(429,'Qualification call allowance exhausted; no additional dispatch')
            cloud+=1;row={'path':request.url.path,'body':json.loads(request.content),'at':time.time()};wires.append(row)
        response=await original_send(instance,request,*a,**kw)
        if row is not None:
            await response.aread();row.update(http_status=response.status_code,response=response.json())
        return response
    async def activate(case):
        manager=ScenarioManager(out/(case['id']+'-scenario.json'));db._development_scenario=manager
        if case['scenario'] not in manager._read()['scenarios']:manager.change('import',manager.snapshot()[1]['source_revision'],spec['fixtures'][case['scenario']])
        os.environ['COGNISHIELD_AI_HYBRID_SCENARIOS']=scenario_approval_context(db)['scenario_digest']
        return scenario_approval_context(db)
    try:
        with patch.object(RoutingModel,'generate',generate),patch.object(ToolRegistry,'invoke',invoke),patch.object(httpx.AsyncClient,'send',send),patch.object(engine,'network_context',scoped_context):
            token=create_access_token(1,'admin','admin')
            async with httpx.AsyncClient(base_url='http://127.0.0.1:8001',headers={'Authorization':'Bearer '+token},timeout=495 if args.completeness or args.completeness_paired else 125,trust_env=False) as client:
                async def turn(cid,prompt,consent):
                    body={'request_id':str(uuid4()),'prompt':prompt,'model':'qwen2.5:1.5b'};p,r,w=len(packets),len(reads),len(wires);start=time.monotonic();approval=None;result={};status=None;error=None
                    try:
                        if consent:
                            ctx=(await client.get('/api/v1/ai/hybrid-context')).json()
                            response=await client.post('/api/v1/ai/conversations/'+cid+'/approve-synthetic-cloud',json={'turn':body,'expected_source_revision':ctx['source_revision']});approval={'status':response.status_code,'result':response.json()};response.raise_for_status()
                        response=await client.post('/api/v1/ai/conversations/'+cid+'/turns',json=body);status=response.status_code;result=response.json()
                    except Exception as e:error={'type':type(e).__name__,'detail':str(e)[:500]}
                    return {'request':body,'approval':approval,'status':status,'seconds':time.monotonic()-start,'result':result,'error':error,'model_packets':packets[p:],'authorized_reads':reads[r:],'wires_without_headers':wires[w:]}
                selected=[] if args.skip_turns else [c for c in spec['cases'] if not args.only or c['id'] in args.only]
                # Alternate order by condition; this is a small paired study,
                # not blinded grading or a deterministic model comparison.
                paired=args.harness_paired or args.completeness_paired
                runs=[(c,arm) for i,c in enumerate(selected) for arm in
                    (['reference'] if c.get('reference') else ['control','enhanced'] if i%2==0 else ['enhanced','control'])] if paired else [(c,None) for c in selected]
                for case,arm in runs:
                    if arm:
                        flag='COGNISHIELD_AI_COMPLETENESS' if args.completeness_paired else 'COGNISHIELD_AI_EVIDENCE_HARNESS'
                        os.environ[flag]='0' if arm=='control' else '1'
                    path=out/(case['id']+('-'+arm if arm else '')+'.json')
                    if path.exists():continue
                    if (out/'PAUSE').exists():break
                    context=await activate(case)
                    response=await client.post('/api/v1/ai/conversations',json={'assistant_kind':case['surface']});response.raise_for_status();cid=response.json()['id']
                    setup=await turn(cid,case['setup'],False) if case.get('setup') else None
                    row=await turn(cid,case['prompt'],True)
                    row.update(id=case['id'],surface=case['surface'],conversation=cid,setup=setup,scenario=context,expected=case,registry_sha256=freeze['sha256'],full_answer_grade='UNREVIEWED')
                    row.update(arm=arm,role_binding=consent_manifest())
                    row['state_scope_reference_ablation']=getattr(args,'state_scope_reference',False)
                    save(path,row);print(json.dumps({'id':case['id'],'seconds':round(row['seconds'],2),'cloud':len(row['wires_without_headers']),'tools':[r['tool'] for r in row['authorized_reads']],'answer_length':len(row['result'].get('answer','')),'error':row['error']}),flush=True)
                    if row['wires_without_headers']:await asyncio.sleep(4.3)
                if args.local_controls:
                    for surface,prompt in [('floating','What is 18 plus 24?'),('studio','Show Kite-Edge recorded interface prefixes.')]:
                        case=spec['cases'][0];await activate(case)
                        cid=(await client.post('/api/v1/ai/conversations',json={'assistant_kind':surface})).json()['id'];row=await turn(cid,prompt,False)
                        save(out/('local-control-'+surface+'.json'),row)
            if args.serve:
                os.environ['COGNISHIELD_AI_COMPLETENESS']='1' if args.completeness else '0'
                os.environ['COGNISHIELD_AI_EVIDENCE_HARNESS']='1' if args.harness else '0'
                await activate(next(c for c in spec['cases'] if c['id']==args.browser_case))
                log=(out/'vite.log').open('w',encoding='utf-8');vite=subprocess.Popen(['node',str(ROOT/'frontend/node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port','5174','--strictPort'],cwd=ROOT/'frontend',env={**os.environ,'VITE_API_URL':'http://127.0.0.1:8001','VITE_WS_URL':'ws://127.0.0.1:8001/ws'},stdout=log,stderr=subprocess.STDOUT)
                save(out/'ready.json',{'backend':8001,'frontend':5174,'pid':os.getpid(),'cloud_calls':cloud,'scenario':scenario_approval_context(db),'stop_file':str(out/'STOP')})
                while not (out/'STOP').exists():await asyncio.sleep(.5)
                save(out/'browser-traces.json',{'packets':packets,'reads':reads,'wires_without_headers':wires,'cloud_calls':cloud})
    finally:
        if vite is not None:vite.terminate();vite.wait(timeout=15)
        server.should_exit=True;await serving
        if not (out/'run-receipt.json').exists():save(out/'run-receipt.json',{'cloud_calls':cloud,'completed_files':sum((out/(c['id']+suffix+'.json')).exists() for c in spec['cases'] for suffix in ('','-control','-enhanced','-reference')),'at':datetime.now(timezone.utc).isoformat()})

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--name',default='frozen-v1');parser.add_argument('--max-cloud',type=int,default=94);parser.add_argument('--only',action='append');parser.add_argument('--serve',action='store_true');parser.add_argument('--browser-case',default='MMQ-02');parser.add_argument('--local-controls',action='store_true');parser.add_argument('--registry',default=str(SPEC.relative_to(ROOT)));parser.add_argument('--freeze',default=str((AUDIT/'freeze-receipt.json').relative_to(ROOT)));parser.add_argument('--audit',default=str(AUDIT.relative_to(ROOT)));parser.add_argument('--skip-turns',action='store_true');parser.add_argument('--harness',action='store_true');parser.add_argument('--harness-paired',action='store_true');parser.add_argument('--completeness',action='store_true');parser.add_argument('--completeness-paired',action='store_true')
    parser.add_argument('--state-scope-reference',action='store_true',help='Diagnostic parameter ablation only; not a historical-code baseline')
    args=parser.parse_args()
    asyncio.run(main(args))
