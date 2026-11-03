"""Bounded, explicitly authorized RC/H comparison using existing consent/adapter.

Freeze and preflight never dispatch. Each round executes 24 fresh cells once,
no retry; the task-wide send ledger caps both rounds at48. No readers/planner.
"""
import argparse,asyncio,copy,hashlib,json,os,sys,time
from datetime import datetime,timezone
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from freeze_timestamp_contract import ENV,load,sha,capture,serialized_wire
DB=ROOT/'tmp/phase-g/iterations/20261101-audit-grounded-repair/evaluation-app.db'
FLAG='COGNISHIELD_AI_REASONER_ANSWER_INTEGRITY'

def save(path,value):
    text=json.dumps(value,ensure_ascii=False,indent=2,default=str)
    for key in ['GEMINI_API_KEY','OPENAI_API_KEY']:
        if os.getenv(key):text=text.replace(os.environ[key],'[REDACTED]')
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:f.write(text+'\n')

def prohibited(*a,**kw):raise AssertionError('This fixed-evidence comparison forbids new readers/planner')

async def main(args):
    out=Path(args.audit).resolve();assert out.is_relative_to(ROOT/'tmp/phase-g/iterations')
    before=load(out/'preservation-before.json');assert before['authorization']['max_total_dispatches']==48
    rd=out/f'round-{args.round}';manifest=rd/'freeze.json';global_ledger=out/'dispatch-ledger.jsonl'
    os.environ.update(ENV);os.environ[FLAG]='off'
    os.environ.update(COGNISHIELD_MODE='local_lab',COGNISHIELD_DEV_SIMULATION='1',COGNISHIELD_DB_PATH=str(DB),
        COGNISHIELD_AI_HYBRID='1',COGNISHIELD_AI_MULTI_MODEL_EXPERIMENT='1',
        COGNISHIELD_DEV_STATE=str(rd/'scenario-state/RC-01.json'),COGNISHIELD_AI_HYBRID_USAGE=str(ROOT/'tmp/ai-cloud-usage.json'),
        COGNISHIELD_AI_HYBRID_RPM='15',COGNISHIELD_AI_HYBRID_INPUT_TPM='150000',COGNISHIELD_AI_HYBRID_RPD='500')
    import lab_config,httpx
    from llm.model_roles import consent_manifest,role_config
    from llm.orchestration import role_reasoning
    from llm.gemini_provider import HybridRequest,approve_hybrid_request,scenario_approval_context
    from llm.gateway_models import TurnRequest,Evidence
    from llm.tools import ToolRegistry
    assert Path(lab_config.DB_PATH).resolve()==DB.resolve() and DB.exists()
    assert os.getenv('GEMINI_API_KEY'),'Existing ignored credential missing'
    cfg=role_config('evidence_reasoner');assert (cfg.provider,cfg.model,cfg.thinking,cfg.output_tokens,cfg.schema_mode)==('google','gemini-3.5-flash-lite','low',8192,'validated_json')
    assert role_config('complex_planner').model=='gemini-3.1-flash-lite' and role_config('local_default').model=='qwen2.5:1.5b'
    if args.freeze:
        assert not manifest.exists()
        if args.round==2:
            assert load(out/'round-1/grading.json')['candidate_acceptance_passed'] is False
            assert (out/'revision-rationale.md').exists()
        cases=[];order=[]
        for index,cid in enumerate([f'{prefix}-{n:02d}' for prefix in ['RC','H'] for n in range(1,7)]):
            if cid.startswith('RC'):
                old=ROOT/f'tmp/phase-g/iterations/20261102-evidence-reasoning-contract/frozen-v3/{cid}/packet.json'
                frozen=load(old);inputs=frozen['inputs'];state=load(ROOT/frozen['scenario_path']);scenario=state['scenarios'][state['selected']]
                surface=frozen['case']['surface'];oracle=frozen['case'];control=frozen['arms']['off']
            else:
                old=ROOT/f'tmp/phase-g/iterations/20261102T104614Z-timestamp-contract-experiment/frozen-v1/{cid}/pair.json'
                frozen=load(old);fixture=load(ROOT/frozen['case_path']);inputs=frozen['inputs'];scenario=fixture['scenario'];surface=fixture['surface'];oracle=fixture['oracle'];control=frozen['arms']['control']
            selected={}
            for arm in ['control','candidate']:
                os.environ[FLAG]='off' if arm=='control' else 'candidate'
                current=await capture(role_reasoning,inputs)
                assert current['schema']==control['schema']
                if arm=='control':assert current['messages']==control['messages']
                body=await serialized_wire(current['messages'],current['schema']);wire=rd/'wires'/f'{cid}-{arm}.json'
                wire.parent.mkdir(parents=True,exist_ok=True)
                with wire.open('xb') as stream:stream.write(json.dumps(body,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8'))
                selected[arm]={**current,'consent_manifest':consent_manifest(),'role_binding':hashlib.sha256(json.dumps(consent_manifest(),sort_keys=True).encode()).hexdigest(),
                    'wire_path':wire.relative_to(ROOT).as_posix(),'wire_sha256':sha(wire)}
            assert selected['candidate']['messages'][1:]==selected['control']['messages'][1:]
            assert selected['candidate']['messages'][0]['content']==selected['control']['messages'][0]['content']+'\n\n'+role_reasoning.ANSWER_INTEGRITY_CANDIDATE
            cases.append({'id':cid,'surface':surface,'source_path':old.relative_to(ROOT).as_posix(),'source_sha256':sha(old),
                'inputs':inputs,'scenario':scenario,'oracle':oracle,'arms':selected})
            for arm in (['control','candidate'] if index%2==0 else ['candidate','control']):order.append({'case':cid,'arm':arm,'sequence':len(order)+1})
        runtime={p:sha(ROOT/p) for p in before['files'] if p.startswith('backend/llm/') and p.endswith('.py')}
        save(manifest,{'round':args.round,'at':datetime.now(timezone.utc).isoformat(),'cases':cases,'order':order,'runtime_sources':runtime,
            'runner_sha256':sha(Path(__file__)),'instruction':role_reasoning.ANSWER_INTEGRITY_CANDIDATE,
            'instruction_sha256':hashlib.sha256(role_reasoning.ANSWER_INTEGRITY_CANDIDATE.encode()).hexdigest(),
            'max_attempts_round':24,'max_attempts_task':48,'no_retries':True,'fixed_sources_oracles':True})
        os.environ[FLAG]='off';print(json.dumps({'freeze':str(manifest),'sha256':sha(manifest),'cells':24,'dispatches':0}));return
    assert args.authorize_registry==sha(manifest),'Exact frozen manifest mismatch'
    spec=load(manifest);assert spec['runner_sha256']==sha(Path(__file__))
    assert all(sha(ROOT/p)==h for p,h in spec['runtime_sources'].items()),'Runtime drift'
    assert role_reasoning.ANSWER_INTEGRITY_CANDIDATE==spec['instruction']
    cases={x['id']:x for x in spec['cases']}
    for case in cases.values():
        assert sha(ROOT/case['source_path'])==case['source_sha256']
        for arm,selected in case['arms'].items():
            os.environ[FLAG]='off' if arm=='control' else 'candidate'
            current=await capture(role_reasoning,case['inputs']);assert current['messages']==selected['messages'] and current['schema']==selected['schema']
            assert consent_manifest()==selected['consent_manifest'] and sha(ROOT/selected['wire_path'])==selected['wire_sha256']
            assert httpx.Request('POST','https://generativelanguage.googleapis.com/offline-only',json=load(ROOT/selected['wire_path'])).content==(ROOT/selected['wire_path']).read_bytes()
    from db.manager import DatabaseManager
    from llm.gateway_store import ConversationStore
    from local_providers.development import ScenarioManager,Scenario
    db=DatabaseManager(str(DB));store=ConversationStore(db);user={'username':'answer-integrity-evaluator','role':'admin'}
    contexts_path=rd/'evaluation-contexts.json';contexts=load(contexts_path) if contexts_path.exists() else {};fresh=not contexts_path.exists();managers={}
    for cid,case in cases.items():
        state=rd/'scenario-state'/f'{cid}.json';scenario=case['scenario'];sid=scenario['id'];value={'version':1,'epoch':1,'enabled':True,'selected':sid,'scenarios':{sid:scenario}}
        if not state.exists():save(state,value)
        else:assert load(state)==value
        managers[cid]=ScenarioManager(state);assert managers[cid].snapshot()[0]==Scenario.model_validate(scenario).model_dump()
        if fresh:contexts[cid]=store.create(user['username'],case['surface'])['id']
        assert store.get(contexts[cid],user['username'])['assistant_kind']==case['surface']
    if fresh:save(contexts_path,contexts)
    def scope_for(cid,arm):
        db._development_scenario=managers[cid];context=scenario_approval_context(db);assert context is not None
        os.environ['COGNISHIELD_AI_HYBRID_SCENARIOS']=context['scenario_digest'];context=scenario_approval_context(db);assert context['eligible']
        os.environ[FLAG]='off' if arm=='control' else 'candidate';assert consent_manifest()==cases[cid]['arms'][arm]['consent_manifest']
        body=TurnRequest(request_id=uuid4(),prompt=cases[cid]['inputs']['request'])
        approval=approve_hybrid_request(db,store,user,contexts[cid],body,context['source_revision'])
        started=time.monotonic();scope=HybridRequest.create(db,store,user,cases[cid]['surface'],contexts[cid],body,started)
        assert scope is not None and scope.role_binding==cases[cid]['arms'][arm]['role_binding'];scope.assert_current_roles()
        return scope,approval,context,started
    if args.preflight_only:
        checks=[]
        with patch.object(httpx.AsyncClient,'send',prohibited),patch.object(ToolRegistry,'invoke',prohibited):
            for cell in spec['order']:
                scope,approval,context,_=scope_for(cell['case'],cell['arm']);checks.append({**cell,'consent':approval,'source':context,'role_binding':scope.role_binding})
        save(rd/'preflight.json',{'passed':True,'manifest_sha256':sha(manifest),'cells':checks,'dispatches':0});os.environ[FLAG]='off';db.close();print('Preflight PASS:24fresh owner/source/model consents;0dispatch.');return
    assert load(rd/'preflight.json')['manifest_sha256']==sha(manifest)
    assert not (rd/'runtime-traces.json').exists() and not (rd/'cells').exists(),'No replacement generations or automatic resume'
    prior=[json.loads(x) for x in global_ledger.read_text().splitlines()] if global_ledger.exists() else []
    assert not any(x['round']==args.round for x in prior)
    assert len(prior)+(24)<=48
    if args.round==2:assert load(out/'round-1/grading.json')['candidate_acceptance_passed'] is False and (out/'revision-rationale.md').exists()
    wires=[];results=[];current={};original_send=httpx.AsyncClient.send
    async def send(client,request,*a,**kw):
        assert request.url.host=='generativelanguage.googleapis.com' and request.url.path.endswith('/gemini-3.5-flash-lite:generateContent')
        selected=cases[current['case']]['arms'][current['arm']];assert request.content==(ROOT/selected['wire_path']).read_bytes(),'Frozen wire differs'
        ledger=[json.loads(x) for x in global_ledger.read_text().splitlines()] if global_ledger.exists() else []
        round_rows=[x for x in ledger if x['round']==args.round];assert len(ledger)<48 and len(round_rows)<24
        assert current==spec['order'][len(round_rows)]
        identity={'id':uuid4().hex,'at':datetime.now(timezone.utc).isoformat(),'round':args.round,**current,'model':'gemini-3.5-flash-lite'}
        with global_ledger.open('a',encoding='utf-8') as f:f.write(json.dumps(identity)+'\n')
        wire={'dispatch':identity,'body':json.loads(request.content),'request_body_sha256':hashlib.sha256(request.content).hexdigest()};wires.append(wire);started=time.monotonic()
        try:
            response=await original_send(client,request,*a,**kw);wire['provider_http_status']=response.status_code
            try:wire['response']=response.json()
            except ValueError:wire['response_parse']='NON_JSON_PROVIDER_BODY'
            return response
        except Exception as exc:wire['transport_error']=type(exc).__name__;raise
        finally:wire['seconds']=time.monotonic()-started
    from llm.orchestration.investigation_support import compatible_claims,release_interpretation
    try:
        with patch.object(httpx.AsyncClient,'send',send),patch.object(ToolRegistry,'invoke',prohibited):
            for cell in spec['order']:
                current.clear();current.update(cell);cid,arm=cell['case'],cell['arm'];case=cases[cid];selected=case['arms'][arm]
                scope,approval,context,started=scope_for(cid,arm);offset=len(wires);snapshot=managers[cid].snapshot()[0]
                inventory={'devices':[{**d,'interfaces':[i for i in snapshot['interfaces'] if i['device_id']==d['id']]} for d in snapshot['devices']]}
                record={**cell,'round':args.round,'at':datetime.now(timezone.utc).isoformat(),'conversation':contexts[cid],'surface':case['surface'],
                    'model_messages':selected['messages'],'model_schema':selected['schema'],'consent':approval,'settings':consent_manifest(),
                    'approved_scenario':context,'manifest_sha256':sha(manifest),'new_planners_readers_retries':0,'full_gateway_browser_acceptance':False}
                try:
                    with scope.activate():raw,model=await scope.generate_role('evidence_reasoner',selected['messages'],selected['schema'])
                    record.update(raw=raw,parsed_json=json.loads(raw),model=model)
                    class Replay:
                        hybrid=scope
                        async def generate(self,messages,structured,**kwargs):
                            assert messages==selected['messages'] and structured==selected['schema'];return raw,model
                    inputs=copy.deepcopy(case['inputs']);inputs['evidence']=[Evidence.model_validate(x) for x in inputs['evidence']]
                    decision=await role_reasoning.decide(Replay(),**inputs);review={'claim_compatibility':compatible_claims(decision,inputs['results'],inventory)}
                    released=release_interpretation(decision,review);final,trace=role_reasoning.preview(released,'off',inputs['results'],inputs['evidence'],{},inputs['request'])
                    record.update(decision=decision,typed_review=review,release_decision=released['release_decision'],final_answer=final,release_trace=trace,contract_status='VALID_CORE')
                except Exception as exc:
                    record.update(raw=getattr(exc,'raw_output',record.get('raw')),error={'class':type(exc).__name__,'http':getattr(exc,'status_code',None),
                        'detail':str(exc)[:800],'category':getattr(exc,'provider_category',None),'validation_diagnostic':getattr(exc,'validation_diagnostic',None)},semantic_verdict='NOT_CERTIFIED')
                record.update(seconds=time.monotonic()-started,wires_without_headers=wires[offset:],role_trace=scope.trace,usage=scope.usage,quota_ledger_sha256=sha(ROOT/'tmp/ai-cloud-usage.json'))
                assert managers[cid].snapshot()[1]['source_revision']==context['source_revision']
                save(rd/'cells'/f'{cid}-{arm}.json',record);results.append(record)
                print(json.dumps({**cell,'seconds':round(record['seconds'],2),'contract':record.get('contract_status'),'error':record.get('error',{}).get('category')}),flush=True)
                if record.get('error') and record['error'].get('category')!='INVALID_STRUCTURED_OUTPUT':
                    save(rd/'stopped.json',{'cell':cell,'error':record['error'],'no_retry':True});break
    finally:
        os.environ[FLAG]='off';save(rd/'runtime-traces.json',{'completed_cells':len(results),'wires_without_headers':wires,'new_planners_readers_retries':0});db.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--audit',required=True);p.add_argument('--round',type=int,choices=[1,2],required=True)
    p.add_argument('--freeze',action='store_true');p.add_argument('--preflight-only',action='store_true');p.add_argument('--authorize-registry');asyncio.run(main(p.parse_args()))
