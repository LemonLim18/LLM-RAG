"""Execute only the explicitly authorized frozen12cell timestamp comparison.

No new model/planner/reader or retry. Existing owner consent, role adapter and
shared quota remain authoritative. Does not change ordinary runtime defaults.
"""
import argparse,asyncio,copy,hashlib,json,os,sys,time
from datetime import datetime,timezone
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from freeze_timestamp_contract import SPEC,AUDIT as FROZEN,ENV,load,sha,capture,serialized_wire
DB=ROOT/'tmp/phase-g/iterations/20261101-audit-grounded-repair/evaluation-app.db'
REGISTRY_HASH='d8dbe4f0d70c5dce1d5ec182b71b216b87cc066b9003f5ff18330d6f941a62a4'
BYTE_HASH='5d12a9c7173daffd1da1a225bf749ad6d82bc4deabac9c46dcae2f2c19bbcbc4'
DESCRIPTION_HASH='e2f1f6a1eb5c93ef09d729e5dac5d9a195ef3a35781c143e095d432b152a5afb'

def save(path,value):
    text=json.dumps(value,ensure_ascii=False,indent=2,default=str)
    for name in ['GEMINI_API_KEY','OPENAI_API_KEY']:
        if os.getenv(name):text=text.replace(os.environ[name],'[REDACTED]')
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:f.write(text+'\n')

def fail_reader(*a,**kw):raise AssertionError('Frozen timestamp experiment forbids new registered reader execution')

async def main(args):
    out=Path(args.audit).resolve();assert out.is_relative_to(ROOT/'tmp/phase-g/iterations')
    assert out.exists() and args.authorize_registry==sha(SPEC)==REGISTRY_HASH
    assert sha(FROZEN/'exact-byte-freeze.json')==BYTE_HASH
    spec=load(SPEC);assert spec['description_sha256']==DESCRIPTION_HASH
    assert hashlib.sha256(spec['candidate_description'].encode()).hexdigest()==DESCRIPTION_HASH
    auth=load(out/'preservation-before.json')['authorization'];assert auth['max_attempts']==12 and auth['registry_sha256']==REGISTRY_HASH
    assert DB.exists();ledger=out/'dispatch-ledger.jsonl';assert not ledger.exists(),'No automatic resume or retry'
    os.environ.update(ENV)
    os.environ.update(COGNISHIELD_MODE='local_lab',COGNISHIELD_DEV_SIMULATION='1',COGNISHIELD_DB_PATH=str(DB),
        COGNISHIELD_AI_HYBRID='1',COGNISHIELD_AI_MULTI_MODEL_EXPERIMENT='1',
        COGNISHIELD_DEV_STATE=str(out/'scenario-state/H-01.json'),COGNISHIELD_AI_HYBRID_USAGE=str(ROOT/'tmp/ai-cloud-usage.json'),
        COGNISHIELD_AI_HYBRID_RPM='15',COGNISHIELD_AI_HYBRID_INPUT_TPM='150000',COGNISHIELD_AI_HYBRID_RPD='500')
    import lab_config,httpx
    from llm.model_roles import consent_manifest,role_config
    from llm.orchestration import role_reasoning
    from db.manager import DatabaseManager
    from llm.gateway_store import ConversationStore
    from llm.gateway_models import TurnRequest,Evidence
    from llm.gemini_provider import HybridRequest,approve_hybrid_request,scenario_approval_context
    from llm.orchestration.investigation_support import compatible_claims,release_interpretation
    from llm.tools import ToolRegistry
    from local_providers.development import ScenarioManager,Scenario
    assert Path(lab_config.DB_PATH).resolve()==DB.resolve()
    assert os.getenv('GEMINI_API_KEY'),'Existing backend/.env credential did not load'
    assert (role_config('evidence_reasoner').model,role_config('evidence_reasoner').thinking,role_config('evidence_reasoner').output_tokens,role_config('evidence_reasoner').schema_mode)==('gemini-3.5-flash-lite','low',8192,'validated_json')
    assert all(sha(ROOT/p)==h for p,h in spec['runtime_sources'].items()),'Runtime hash mismatch: no dispatch'
    pairs={};fixtures={};wire_files={(x['case'],x['arm']):x for x in load(FROZEN/'exact-byte-freeze.json')['cells']}
    for case in spec['cases']:
        assert sha(ROOT/case['pair_path'])==case['pair_sha256'] and sha(ROOT/case['case_path'])==case['case_sha256']
        pair=load(ROOT/case['pair_path']);fixture=load(ROOT/case['case_path']);pairs[case['id']]=pair;fixtures[case['id']]=fixture
        Scenario.model_validate(fixture['scenario'])
        assert fixture['question']==pair['inputs']['request'] and fixture['oracle']==pair['oracle']==case['oracle']
        for arm,selected in pair['arms'].items():
            os.environ['COGNISHIELD_AI_SOURCECLAIM_TIMESTAMP_EXPERIMENT']='off' if arm=='control' else 'candidate'
            current=await capture(role_reasoning,pair['inputs']);assert current['messages']==selected['messages'] and current['schema']==selected['schema']
            assert json.dumps(current['schema'])==json.dumps(selected['schema'])
            assert consent_manifest()==selected['consent_manifest']
            wire=wire_files[(case['id'],arm)]
            assert sha(ROOT/wire['wire_path'])==wire['wire_sha256'] and sha(ROOT/wire['provider_schema_path'])==wire['provider_schema_sha256']
            assert json.loads((ROOT/wire['wire_path']).read_bytes())==selected['provider_body']
            assert (ROOT/wire['provider_schema_path']).read_bytes()==json.dumps(selected['schema']).encode()
    context_file=out/'evaluation-contexts.json';db=DatabaseManager(str(DB));store=ConversationStore(db)
    user={'username':'timestamp-contract-evaluator','role':'admin'}
    contexts=load(context_file) if context_file.exists() else {};new_contexts=not context_file.exists()
    managers={}
    for cid,fixture in fixtures.items():
        state=out/'scenario-state'/f'{cid}.json'
        content={'version':1,'epoch':1,'enabled':True,'selected':cid,'scenarios':{cid:fixture['scenario']}}
        if state.exists():assert load(state)==content
        else:save(state,content)
        manager=ScenarioManager(state);managers[cid]=manager
        snapshot=manager.snapshot()[0];assert snapshot==Scenario.model_validate(fixture['scenario']).model_dump()
        if new_contexts:contexts[cid]=store.create(user['username'],fixture['surface'])['id']
        assert store.get(contexts[cid],user['username'])['assistant_kind']==fixture['surface']
    if new_contexts:save(context_file,contexts)
    def scope_for(cid,arm):
        db._development_scenario=managers[cid];context=scenario_approval_context(db);assert context is not None
        os.environ['COGNISHIELD_AI_HYBRID_SCENARIOS']=context['scenario_digest'];context=scenario_approval_context(db);assert context['eligible']
        os.environ['COGNISHIELD_AI_SOURCECLAIM_TIMESTAMP_EXPERIMENT']='off' if arm=='control' else 'candidate'
        assert consent_manifest()==pairs[cid]['arms'][arm]['consent_manifest']
        body=TurnRequest(request_id=uuid4(),prompt=pairs[cid]['inputs']['request'])
        approval=approve_hybrid_request(db,store,user,contexts[cid],body,context['source_revision'])
        started=time.monotonic();scope=HybridRequest.create(db,store,user,fixtures[cid]['surface'],contexts[cid],body,started)
        assert scope is not None and scope.role_binding==pairs[cid]['arms'][arm]['role_binding_sha256']
        scope.assert_current_roles();return scope,approval,context,started
    if args.preflight_only:
        checks=[]
        with patch.object(httpx.AsyncClient,'send',fail_reader),patch.object(ToolRegistry,'invoke',fail_reader):
            for cell in spec['call_order']:
                scope,approval,context,started=scope_for(cell['case'],cell['arm'])
                checks.append({**cell,'owner':user['username'],'consent':approval,'scenario':context,'role_binding':scope.role_binding,
                    'actual_cloud_dispatches':0,'new_reader_execution':0})
        save(out/'preflight.json',{'passed':True,'registry_sha256':REGISTRY_HASH,'byte_manifest_sha256':BYTE_HASH,'description_sha256':DESCRIPTION_HASH,
            'all12messages_schemas_wires_oracles_consent_exact':True,'credential_loaded':True,'db_is_existing_disposable':True,'cells':checks,
            'provider_calls':0,'new_readers_planners':0,'ordinary_private_editor_data':False})
        db.close();print('Preflight PASS: all12frozen cells and fresh exact owner/source/model consent;0dispatches.');return
    assert load(out/'preflight.json')['passed'],'Require zero-dispatch consent preflight'
    wires=[];results=[];current={};original_send=httpx.AsyncClient.send
    async def send(client,request,*a,**kw):
        assert request.url.host=='generativelanguage.googleapis.com' and request.url.path.endswith('/gemini-3.5-flash-lite:generateContent')
        file=wire_files[(current['case'],current['arm'])];assert request.content==(ROOT/file['wire_path']).read_bytes(),'Exact wire changed: no dispatch'
        previous=[json.loads(x) for x in ledger.read_text(encoding='utf-8').splitlines()] if ledger.exists() else []
        assert len(previous)<12 and not any(x['case']==current['case'] and x['arm']==current['arm'] for x in previous)
        assert (current['case'],current['arm'])==tuple(spec['call_order'][len(previous)][k] for k in ['case','arm'])
        identity={'id':uuid4().hex,'at':datetime.now(timezone.utc).isoformat(),**current,'model':'gemini-3.5-flash-lite'}
        with ledger.open('a',encoding='utf-8') as f:f.write(json.dumps(identity)+'\n')
        wire={'dispatch':identity,'request_body_sha256':hashlib.sha256(request.content).hexdigest(),'body':json.loads(request.content)}
        wires.append(wire);start=time.monotonic()
        try:
            response=await original_send(client,request,*a,**kw);wire['provider_http_status']=response.status_code
            try:wire['response']=response.json()
            except ValueError:wire['response_parse']='Non-JSON body; not a model completion'
            return response
        except Exception as exc:wire['transport_exception']=type(exc).__name__;raise
        finally:wire['seconds']=time.monotonic()-start
    save(out/'live-runtime-freeze.json',{'registry_sha256':REGISTRY_HASH,'byte_manifest_sha256':BYTE_HASH,'description_sha256':DESCRIPTION_HASH,
        'runner_sha256':sha(Path(__file__)),'runtime_sources':spec['runtime_sources'],'authorization':auth,'request_wide_seconds':120,
        'order':spec['call_order'],'one_reasoner_call_per_cell':True,'new_readers_planners_retries':0})
    try:
        with patch.object(httpx.AsyncClient,'send',send),patch.object(ToolRegistry,'invoke',fail_reader):
            for cell in spec['call_order']:
                cid,arm=cell['case'],cell['arm'];current.update(cell);pair=pairs[cid];selected=pair['arms'][arm]
                scope,approval,context,started=scope_for(cid,arm);before_wire=len(wires)
                snapshot=managers[cid].snapshot()[0];inventory={'devices':[{**d,'interfaces':[p for p in snapshot['interfaces'] if p['device_id']==d['id']]} for d in snapshot['devices']]}
                record={**cell,'at':datetime.now(timezone.utc).isoformat(),'surface':fixtures[cid]['surface'],'owner':user['username'],
                    'conversation':contexts[cid],'registry_sha256':REGISTRY_HASH,'frozen_pair_sha256':sha(ROOT/next(x['pair_path'] for x in spec['cases'] if x['id']==cid)),
                    'model_messages':selected['messages'],'model_schema':selected['schema'],'expected_schema_sha256':selected['schema_sha256'],
                    'expected_request_body_sha256':wire_files[(cid,arm)]['wire_sha256'],'consent':approval,'settings':consent_manifest(),
                    'approved_scenario':context,'source_fixture_sha256':sha(ROOT/pair['case_path']),
                    'authorized_frozen_results':pair['inputs']['results'],'automatic_workflow_eligibility':scope.multi_model,
                    'new_registered_reads':0,'new_planner_calls':0,'full_gateway_browser_acceptance':False}
                try:
                    with scope.activate():raw,model=await scope.generate_role('evidence_reasoner',selected['messages'],selected['schema'])
                    record.update(raw=raw,parsed_json=json.loads(raw),model=model)
                    class Replay:
                        hybrid=scope
                        async def generate(self,messages,structured,**kw):
                            assert messages==selected['messages'] and structured==selected['schema'];return raw,model
                    args_in=copy.deepcopy(pair['inputs']);args_in['evidence']=[Evidence.model_validate(e) for e in args_in['evidence']]
                    decision=await role_reasoning.decide(Replay(),**args_in)
                    review={'claim_compatibility':compatible_claims(decision,args_in['results'],inventory)}
                    released=release_interpretation(decision,review)
                    final,trace=role_reasoning.preview(released,'off',args_in['results'],args_in['evidence'],{},args_in['request'])
                    record.update(decision=decision,typed_review=review,release_decision=released.get('release_decision'),
                        final_answer=final,release_trace=trace,contract_status='VALID_CORE')
                except Exception as exc:
                    record.update(error={'class':type(exc).__name__,'http':getattr(exc,'status_code',None),'detail':str(exc)[:800],
                        'provider_http_status':getattr(exc,'provider_http_status',None),'category':getattr(exc,'provider_category',None),
                        'validation_diagnostic':getattr(exc,'validation_diagnostic',None)},raw=getattr(exc,'raw_output',record.get('raw')),
                        semantic_verdict='NOT_CERTIFIED')
                record.update(seconds=time.monotonic()-started,role_trace=scope.trace,usage=scope.usage,
                    wires_without_headers=wires[before_wire:],source_revision_after=managers[cid].snapshot()[1]['source_revision'],
                    quota_ledger_path='tmp/ai-cloud-usage.json',quota_ledger_sha256=sha(ROOT/'tmp/ai-cloud-usage.json'))
                assert record['source_revision_after']==context['source_revision']
                save(out/'cells'/f'{cid}-{arm}.json',record);results.append(record)
                print(json.dumps({'case':cid,'arm':arm,'seconds':round(record['seconds'],2),'dispatches':len(record['wires_without_headers']),
                    'contract':record.get('contract_status'),'error':record.get('error',{}).get('category')}),flush=True)
                if record.get('error') and record['error'].get('category') not in {'INVALID_STRUCTURED_OUTPUT',None}:
                    save(out/'stopped.json',{'cell':cell,'failure':record['error'],'retry':False});return
    finally:
        os.environ['COGNISHIELD_AI_SOURCECLAIM_TIMESTAMP_EXPERIMENT']='off'
        save(out/'runtime-traces.json',{'wires_without_headers':wires,'completed_cells':len(results),'maximum_dispatches':12,
            'new_registered_reads_planners_retries':0,'no_further_dispatches_automatic':True});db.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--authorize-registry',required=True);p.add_argument('--audit',required=True)
    p.add_argument('--preflight-only',action='store_true');asyncio.run(main(p.parse_args()))
