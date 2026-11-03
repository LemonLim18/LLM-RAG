"""Explicitly authorized 18-attempt reasoner-only fixed-evidence comparison.

No planner/reader execution, prompt changes, retry, service or ordinary-data IO.
Existing role adapter, owner consent, quota ledger and release checks are reused.
"""
import argparse,asyncio,copy,hashlib,json,os,sys,time
from datetime import datetime,timezone
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'tmp/phase-g/iterations/20261102-evidence-reasoning-contract'
SPEC=ROOT/'docs/evaluations/phase_g_evidence_reasoning_contract_v3.json'
DB=ROOT/'tmp/phase-g/iterations/20261101-audit-grounded-repair/evaluation-app.db'
sys.path.insert(0,str(ROOT/'backend'))

def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(path,value):
    text=json.dumps(value,ensure_ascii=False,indent=2,default=str)
    for key in ['GEMINI_API_KEY','OPENAI_API_KEY']:
        if os.getenv(key):text=text.replace(os.environ[key],'[REDACTED]')
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:f.write(text+'\n')

async def main(args):
    assert args.authorize_registry==sha(SPEC),'Explicit frozen registry authorization required'
    assert load(OUT/'live-preservation-before.json')['authorization']
    os.environ.update(COGNISHIELD_MODE='local_lab',COGNISHIELD_DEV_SIMULATION='1',COGNISHIELD_DB_PATH=str(DB),
        COGNISHIELD_DEV_STATE=str(OUT/'scenarios/RC-01.json'),COGNISHIELD_AI_HYBRID='1',
        COGNISHIELD_AI_MULTI_MODEL_EXPERIMENT='1',COGNISHIELD_AI_HYBRID_INTERPRET='0',COGNISHIELD_AI_COMPLETENESS='1',
        COGNISHIELD_AI_OUTCOMES='0',COGNISHIELD_AI_EVIDENCE_HARNESS='0',COGNISHIELD_AI_EVIDENCE_LAYOUT='current',
        COGNISHIELD_AI_PROVIDER_WIRE_SCHEMA='full',COGNISHIELD_AI_EXPERIMENT_SEMANTIC_VERIFIER='off',
        COGNISHIELD_LOCAL_OLLAMA_MODEL='qwen2.5:1.5b',COGNISHIELD_AI_INVESTIGATION_SECONDS='120')
    import lab_config,httpx
    from db.manager import DatabaseManager
    from llm.gateway_store import ConversationStore
    from llm.gateway_models import TurnRequest,Evidence
    from llm.gemini_provider import HybridRequest,approve_hybrid_request,scenario_approval_context
    from llm.model_roles import consent_manifest,role_config
    from llm.orchestration.role_reasoning import decide,preview
    from llm.orchestration.investigation_support import compatible_claims,release_interpretation
    from local_providers.development import ScenarioManager
    assert Path(lab_config.DB_PATH).resolve()==DB.resolve()
    cfg=role_config('evidence_reasoner')
    assert (cfg.provider,cfg.model,cfg.thinking,cfg.output_tokens,cfg.schema_mode)==('google','gemini-3.5-flash-lite','low',8192,'validated_json')
    frozen_sources=load(OUT/'runtime-source-freeze.json')['sources']
    assert all(sha(ROOT/p)==h for p,h in frozen_sources.items()),'Runtime changed after packet freeze'
    ledger=OUT/'live-dispatch-ledger.jsonl';assert not ledger.exists(),'No automatic continuation/retry'
    spec=load(SPEC);db=DatabaseManager(str(DB));store=ConversationStore(db)
    user={'username':'reasoning-contract-freezer','role':'admin'}
    original_send=httpx.AsyncClient.send;wires=[];current={};results=[]
    async def send(client,request,*a,**kw):
        if request.url.host!='generativelanguage.googleapis.com':
            raise RuntimeError('This experiment authorizes only the existing Google reasoning endpoint')
        assert request.url.path.endswith('/gemini-3.5-flash-lite:generateContent')
        prior=[json.loads(x) for x in ledger.read_text().splitlines()] if ledger.exists() else []
        assert len(prior)<18,'Hard dispatch ceiling'
        identity={'id':uuid4().hex,'at':datetime.now(timezone.utc).isoformat(),**current,'model':'gemini-3.5-flash-lite'}
        with ledger.open('a',encoding='utf-8') as f:f.write(json.dumps(identity)+'\n')
        wire={'dispatch':identity,'body':json.loads(request.content)};wires.append(wire);started=time.monotonic()
        try:
            response=await original_send(client,request,*a,**kw)
            wire.update(provider_http_status=response.status_code,response=response.json());return response
        except Exception as exc:wire['transport_error']=type(exc).__name__;raise
        finally:wire['seconds']=time.monotonic()-started
    save(OUT/'live-runtime-freeze-v2.json',{'registry_sha256':sha(SPEC),'sources':frozen_sources,
        'authorization':'Explicit user reply authorizes up to18calls on the same sixconditions; V3 metadata corrections documented before confirmation.',
        'request_budget_seconds':120,'single_reasoner_call_per_arm':True,'new_planner_or_reader_calls':0,
        'order':'Case order RC01-RC06; arms control/A/B; not randomized or blinded.'})
    try:
        with patch.object(httpx.AsyncClient,'send',send):
            for case in spec['cases']:
                file=OUT/'frozen-v3'/case['id']/'packet.json';assert sha(file)==case['packet_sha256']
                frozen=load(file);scenario=ROOT/frozen['scenario_path'];assert sha(scenario)==case['scenario_sha256']
                manager=ScenarioManager(scenario);db._development_scenario=manager
                context=scenario_approval_context(db);assert context is not None
                os.environ['COGNISHIELD_AI_HYBRID_SCENARIOS']=context['scenario_digest']
                context=scenario_approval_context(db);assert context['eligible']
                cid=store.create(user['username'],case['case']['surface'])['id']
                s=manager.snapshot()[0];inventory={'devices':[{**d,'interfaces':[p for p in s['interfaces'] if p['device_id']==d['id']]} for d in s['devices']]}
                for arm in ['off','obligations','relationships']:
                    current.update(case=case['id'],arm=arm)
                    os.environ['COGNISHIELD_AI_REASONING_CONTRACT']=arm
                    body=TurnRequest(request_id=uuid4(),prompt=case['case']['prompt'])
                    approval=approve_hybrid_request(db,store,user,cid,body,manager.snapshot()[1]['source_revision'])
                    started=time.monotonic();scope=HybridRequest.create(db,store,user,case['case']['surface'],cid,body,started)
                    assert scope is not None and scope.approved_scenario['scenario_digest']==context['scenario_digest']
                    selected=frozen['arms'][arm];wire_start=len(wires)
                    r={'case':case['id'],'arm':arm,'surface':case['case']['surface'],'at':datetime.now(timezone.utc).isoformat(),
                        'registry_sha256':sha(SPEC),'packet_sha256':sha(file),'conversation':cid,'owner':user['username'],
                        'consent':approval,'settings':consent_manifest(),'scenario':context,
                        'model_messages':selected['messages'],'model_schema':selected['schema'],
                        'authorized_frozen_results':frozen['inputs']['results'],'new_reads':0,'new_planner_calls':0,
                        'automatic_workflow_eligibility':scope.multi_model,'full_gateway_or_browser_acceptance':False}
                    try:
                        with scope.activate():raw,model=await scope.generate_role('evidence_reasoner',selected['messages'],selected['schema'])
                        r.update(raw=raw,model=model)
                        class Replay:
                            hybrid=scope
                            async def generate(self,messages,structured,**kw):
                                assert messages==selected['messages'] and structured==selected['schema'],'Runtime packet drift'
                                return raw,model
                        inputs=copy.deepcopy(frozen['inputs']);inputs['evidence']=[Evidence.model_validate(e) for e in inputs['evidence']]
                        d=await decide(Replay(),**inputs)
                        typed={'claim_compatibility':compatible_claims(d,inputs['results'],inventory)}
                        released=release_interpretation(d,typed)
                        final,validation=preview(released,'off',inputs['results'],inputs['evidence'],{},inputs['request'])
                        r.update(decision=d,typed_review=typed,final_answer=final,release_trace=validation,contract_status='VALID')
                    except Exception as exc:
                        r.update(error={'class':type(exc).__name__,'http':getattr(exc,'status_code',None),
                            'provider_http_status':getattr(exc,'provider_http_status',None),'category':getattr(exc,'provider_category',None),
                            'detail':str(exc)[:800],'validation_diagnostic':getattr(exc,'validation_diagnostic',None)},
                            raw=getattr(exc,'raw_output',r.get('raw')),semantic_verdict='NOT_CERTIFIED')
                    r.update(seconds=time.monotonic()-started,role_trace=scope.trace,usage=scope.usage,
                        wires_without_headers=wires[wire_start:],scenario_revision_after=manager.snapshot()[1]['source_revision'])
                    save(OUT/'live-results'/(case['id']+'-'+arm+'.json'),r);results.append(r)
                    print(json.dumps({'case':case['id'],'arm':arm,'seconds':round(r['seconds'],2),
                        'dispatches':len(r['wires_without_headers']),'contract':r.get('contract_status'),'error':r.get('error',{}).get('category')}),flush=True)
                    err=r.get('error',{})
                    if err and err.get('category')!='INVALID_STRUCTURED_OUTPUT':
                        save(OUT/'live-stop.json',{'case':case['id'],'arm':arm,'error':err,'automatic_retry':False});return
    finally:
        os.environ['COGNISHIELD_AI_REASONING_CONTRACT']='off'
        save(OUT/'live-runtime-traces-v2.json',{'wires_without_headers':wires,'completed_cells':len(results),'cloud_cap':18,'new_reads':0,'new_planner_calls':0})
        db.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--authorize-registry',required=True)
    asyncio.run(main(p.parse_args()))
