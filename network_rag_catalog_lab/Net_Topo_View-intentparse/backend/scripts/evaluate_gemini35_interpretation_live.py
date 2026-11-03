"""One separately authorized 12-attempt comparison; no retries or new readers.

Uses frozen messages, existing role/consent/quota adapter and offline release.
This is a reasoner experiment, not full-gateway or browser acceptance.
"""
import argparse,asyncio,copy,hashlib,json,os,sys,time
from datetime import datetime,timezone
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from freeze_gemini35_interpretation import AUDIT as OUT,SPEC,ENV,load,sha,capture
DB=ROOT/'tmp/phase-g/iterations/20261101-audit-grounded-repair/evaluation-app.db'

def save(path,value):
    text=json.dumps(value,ensure_ascii=False,indent=2,default=str)
    for name in ['GEMINI_API_KEY','OPENAI_API_KEY']:
        if os.getenv(name):text=text.replace(os.environ[name],'[REDACTED]')
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:f.write(text+'\n')

async def main(args):
    assert args.authorize_registry==sha(SPEC)=='9cab06b8723e8365dd01be39183324090719edf2a1245fab2adca6258d4a4249'
    auth=load(OUT/'live-preservation-before.json')['authorization']
    assert auth['user_reply']=='Authorize the bounded 12-call comparison' and auth['maximum_dispatch_attempts']==12
    assert DB.exists(),'Reuse only the existing disposable synthetic evaluation DB'
    os.environ.update(ENV)
    os.environ.update(COGNISHIELD_MODE='local_lab',COGNISHIELD_DEV_SIMULATION='1',COGNISHIELD_DB_PATH=str(DB),
        COGNISHIELD_DEV_STATE=str(ROOT/'tmp/phase-g/iterations/20261102-evidence-reasoning-contract/scenarios/RC-01.json'),
        COGNISHIELD_AI_HYBRID='1',COGNISHIELD_AI_MULTI_MODEL_EXPERIMENT='1',
        COGNISHIELD_AI_HYBRID_USAGE=str(ROOT/'tmp/ai-cloud-usage.json'),
        COGNISHIELD_AI_HYBRID_RPM='15',COGNISHIELD_AI_HYBRID_INPUT_TPM='150000',COGNISHIELD_AI_HYBRID_RPD='500')
    import lab_config,httpx
    from llm.model_roles import consent_manifest
    from llm.orchestration import role_reasoning
    assert Path(lab_config.DB_PATH).resolve()==DB.resolve()
    assert os.getenv('GEMINI_API_KEY'),'Existing ignored backend/.env credential must load'
    spec=load(SPEC);pairs={};frozen_sources=spec['runtime_sources']
    assert all(sha(ROOT/p)==h for p,h in frozen_sources.items()),'Runtime drift; no dispatch'
    for c in spec['cases']:
        path=ROOT/c['pair_path'];assert sha(path)==c['pair_sha256']
        pair=load(path);pairs[c['id']]=pair
        source=pair['source_manifest']
        for path_key,hash_key in [('frozen_source_path','frozen_source_sha256'),('scenario_path','scenario_sha256'),('original_control_trace','original_control_trace_sha256')]:
            assert sha(ROOT/source[path_key])==source[hash_key]
        for arm,selected in pair['arms'].items():
            os.environ['COGNISHIELD_AI_REASONER_INTERPRETATION_EXPERIMENT']='off' if arm=='control' else 'candidate'
            current=await capture(role_reasoning,pair['inputs'])
            assert current['messages']==selected['messages'] and current['schema']==selected['schema']
            assert consent_manifest()==selected['consent_manifest']
    ledger=OUT/'live-dispatch-ledger.jsonl';assert not ledger.exists(),'No automatic resume or retry'
    if args.preflight_only:
        save(OUT/'live-preflight.json',{'all12_inputs_schema_consent_exact':True,'credential_loaded':True,
            'registry_sha256':sha(SPEC),'cloud_dispatches':0,'new_reads':0,'new_planners':0})
        print('Preflight PASS: all12 frozen inputs/schema/consent exact; no dispatch.');return
    from db.manager import DatabaseManager
    from llm.gateway_store import ConversationStore
    from llm.gateway_models import TurnRequest,Evidence
    from llm.gemini_provider import HybridRequest,approve_hybrid_request,scenario_approval_context
    from llm.orchestration.investigation_support import compatible_claims,release_interpretation
    from local_providers.development import ScenarioManager
    db=DatabaseManager(str(DB));store=ConversationStore(db);user={'username':'interpretation-evaluator','role':'admin'}
    original_send=httpx.AsyncClient.send;wires=[];results=[];current={};contexts={}
    async def send(client,request,*a,**kw):
        assert request.url.host=='generativelanguage.googleapis.com'
        assert request.url.path.endswith('/gemini-3.5-flash-lite:generateContent')
        prior=[json.loads(line) for line in ledger.read_text(encoding='utf-8').splitlines()] if ledger.exists() else []
        assert len(prior)<12 and not any(x['case']==current['case'] and x['arm']==current['arm'] for x in prior)
        assert (current['case'],current['arm'])==tuple(spec['call_order'][len(prior)][k] for k in ['case','arm'])
        identity={'id':uuid4().hex,'at':datetime.now(timezone.utc).isoformat(),**current,'model':'gemini-3.5-flash-lite'}
        with ledger.open('a',encoding='utf-8') as f:f.write(json.dumps(identity)+'\n')
        wire={'dispatch':identity,'body':json.loads(request.content)};wires.append(wire);started=time.monotonic()
        try:
            response=await original_send(client,request,*a,**kw)
            wire.update(provider_http_status=response.status_code,response=response.json());return response
        except Exception as exc:wire['transport_error']=type(exc).__name__;raise
        finally:wire['seconds']=time.monotonic()-started
    save(OUT/'live-runtime-freeze.json',{'registry_sha256':sha(SPEC),'runner_sha256':sha(Path(__file__)),
        'runtime_sources':frozen_sources,'authorization':auth,'request_seconds':120,'call_order':spec['call_order'],
        'single_call_per_cell':True,'new_tool_execution':0,'new_planner_calls':0,'full_gateway_browser_acceptance':False})
    try:
        with patch.object(httpx.AsyncClient,'send',send):
            for cell in spec['call_order']:
                cid,arm=cell['case'],cell['arm'];pair=pairs[cid];current.update(cell)
                manager=ScenarioManager(ROOT/pair['source_manifest']['scenario_path']);db._development_scenario=manager
                context=scenario_approval_context(db);assert context is not None
                os.environ['COGNISHIELD_AI_HYBRID_SCENARIOS']=context['scenario_digest']
                context=scenario_approval_context(db);assert context['eligible']
                os.environ['COGNISHIELD_AI_REASONER_INTERPRETATION_EXPERIMENT']='off' if arm=='control' else 'candidate'
                selected=pair['arms'][arm];assert consent_manifest()==selected['consent_manifest']
                if cid not in contexts:contexts[cid]=store.create(user['username'],pair['original_case']['surface'])['id']
                conversation=contexts[cid];body=TurnRequest(request_id=uuid4(),prompt=pair['inputs']['request'])
                approval=approve_hybrid_request(db,store,user,conversation,body,context['source_revision'])
                started=time.monotonic();scope=HybridRequest.create(db,store,user,pair['original_case']['surface'],conversation,body,started)
                assert scope is not None and scope.role_binding==selected['role_binding_sha256']
                snapshot=manager.snapshot()[0]
                inventory={'devices':[{**d,'interfaces':[p for p in snapshot['interfaces'] if p['device_id']==d['id']]} for d in snapshot['devices']]}
                record={**cell,'at':datetime.now(timezone.utc).isoformat(),'registry_sha256':sha(SPEC),
                    'conversation':conversation,'owner':user['username'],'surface':pair['original_case']['surface'],
                    'consent':approval,'scenario':context,'settings':consent_manifest(),
                    'model_messages':selected['messages'],'model_schema':selected['schema'],
                    'authorized_frozen_results':pair['inputs']['results'],'new_reader_calls':0,'new_planner_calls':0,
                    'automatic_workflow_eligibility':scope.multi_model,'full_gateway_browser_acceptance':False}
                wire_start=len(wires)
                try:
                    with scope.activate():raw,model=await scope.generate_role('evidence_reasoner',selected['messages'],selected['schema'])
                    record.update(raw=raw,model=model)
                    class Replay:
                        hybrid=scope
                        async def generate(self,messages,structured,**kw):
                            assert messages==selected['messages'] and structured==selected['schema']
                            return raw,model
                    inputs=copy.deepcopy(pair['inputs']);inputs['evidence']=[Evidence.model_validate(e) for e in inputs['evidence']]
                    decision=await role_reasoning.decide(Replay(),**inputs)
                    typed={'claim_compatibility':compatible_claims(decision,inputs['results'],inventory)}
                    released=release_interpretation(decision,typed)
                    final,trace=role_reasoning.preview(released,'off',inputs['results'],inputs['evidence'],{},inputs['request'])
                    record.update(decision=decision,typed_review=typed,final_answer=final,release_trace=trace,contract_status='VALID')
                except Exception as exc:
                    record.update(error={'class':type(exc).__name__,'http':getattr(exc,'status_code',None),
                        'provider_http_status':getattr(exc,'provider_http_status',None),'category':getattr(exc,'provider_category',None),
                        'detail':str(exc)[:800],'validation_diagnostic':getattr(exc,'validation_diagnostic',None)},
                        raw=getattr(exc,'raw_output',record.get('raw')),semantic_verdict='NOT_CERTIFIED')
                record.update(seconds=time.monotonic()-started,role_trace=scope.trace,usage=scope.usage,
                    wires_without_headers=wires[wire_start:],scenario_revision_after=manager.snapshot()[1]['source_revision'])
                assert record['scenario_revision_after']==context['source_revision']
                save(OUT/'live-results'/f'{cid}-{arm}.json',record);results.append(record)
                print(json.dumps({'case':cid,'arm':arm,'seconds':round(record['seconds'],2),
                    'dispatches':len(record['wires_without_headers']),'contract':record.get('contract_status'),
                    'error':record.get('error',{}).get('category')}),flush=True)
                if record.get('error') and record['error'].get('category') not in {'INVALID_STRUCTURED_OUTPUT',None}:
                    save(OUT/'live-stop.json',{'case':cid,'arm':arm,'error':record['error'],'retry':False});return
    finally:
        os.environ['COGNISHIELD_AI_REASONER_INTERPRETATION_EXPERIMENT']='off'
        save(OUT/'live-runtime-traces.json',{'wires_without_headers':wires,'completed_cells':len(results),'hard_dispatch_cap':12,
            'new_reader_calls':0,'new_planner_calls':0,'retry':False})
        db.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--authorize-registry',required=True)
    parser.add_argument('--preflight-only',action='store_true');asyncio.run(main(parser.parse_args()))
