"""OFFLINE ONLY: freeze one paired instruction experiment from preserved inputs.

No provider client, DB manager, scenario reader, consent approval or inference.
Fresh user authorization and server-owned exact consent are still required to
run the prepared comparison. This utility cannot dispatch the comparison.
"""
import argparse,asyncio,copy,hashlib,importlib.util,json,os,socket,sys
from dataclasses import asdict
from datetime import datetime,timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
AUDIT=ROOT/'tmp/phase-g/iterations/20261102-gemini35-interpretation'
PREVIOUS=ROOT/'tmp/phase-g/iterations/20261102-evidence-reasoning-contract'
ORIGINAL_SPEC=ROOT/'docs/evaluations/phase_g_evidence_reasoning_contract_v3.json'
SPEC=ROOT/'docs/evaluations/phase_g_gemini35_interpretation_v1.json'
sys.path.insert(0,str(ROOT/'backend'))

# Child-process settings only: reproduce the original control envelope.
ENV={
    'COGNISHIELD_AI_REASONER_INTERPRETATION_EXPERIMENT':'off',
    'COGNISHIELD_AI_REASONING_CONTRACT':'off','COGNISHIELD_AI_OUTCOMES':'0',
    'COGNISHIELD_AI_COMPLETENESS':'1','COGNISHIELD_AI_INVESTIGATION_SECONDS':'120',
    'COGNISHIELD_AI_EVIDENCE_HARNESS':'0','COGNISHIELD_AI_EVIDENCE_LAYOUT':'current',
    'COGNISHIELD_AI_PROVIDER_WIRE_SCHEMA':'full','COGNISHIELD_AI_EXPERIMENT_SEMANTIC_VERIFIER':'off',
    'COGNISHIELD_AI_HYBRID_INTERPRET':'0','COGNISHIELD_LOCAL_OLLAMA_MODEL':'qwen2.5:1.5b',
}

def load(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def digest(text):return hashlib.sha256(text.encode('utf-8')).hexdigest()
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def relative(path):return path.relative_to(ROOT).as_posix()
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as f:
        f.write(json.dumps(value,ensure_ascii=False,indent=2)+'\n')

def preimage(name):
    path=AUDIT/'source-before'/('backend/llm/'+name+'.py')
    spec=importlib.util.spec_from_file_location('_interpretation_before_'+name.replace('/','_'),path)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module
    spec.loader.exec_module(module);return module

class Captured(Exception):pass

async def capture(module,inputs):
    """Intercept the single generation boundary before any provider inference."""
    result={}
    class Model:
        hybrid=SimpleNamespace(role_calls=0,remote_calls=0,max_remote_calls=3)
        async def generate(self,messages,structured,**kw):
            assert not result,'More than one model call proposed'
            result.update(messages=copy.deepcopy(messages),schema=copy.deepcopy(structured),purpose=kw)
            raise Captured()
    from llm.gateway_models import Evidence
    args=copy.deepcopy(inputs);args['evidence']=[Evidence.model_validate(e) for e in args['evidence']]
    try:await module.decide(Model(),**args)
    except Captured:pass
    assert result,'Generation boundary not reached';return result

def forbidden(*a,**kw):raise AssertionError('Offline freeze forbids network or source execution')

async def freeze():
    import httpx
    from llm import model_roles
    from llm.orchestration import role_reasoning
    original=load(ORIGINAL_SPEC);before=load(AUDIT/'preservation-before.json')
    assert sha(ORIGINAL_SPEC)=='47bb09ae0a78f86a868df78143b0de109a7f10f789716d03f09e277e7c233e47'
    assert not SPEC.exists(),'Frozen registry already exists; never overwrite it'
    records=[];calls=[];all_control_exact=True
    from contextlib import ExitStack
    with ExitStack() as stack:
        stack.enter_context(patch.dict(os.environ,ENV))
        for target in ['httpx.AsyncClient.send','httpx.Client.send','socket.create_connection']:
            stack.enter_context(patch(target,forbidden))
        old_reasoning=preimage('orchestration/role_reasoning');old_roles=preimage('model_roles')
        settings=model_roles.consent_manifest()
        assert settings==old_roles.consent_manifest(),'OFF consent envelope drift'
        assert asdict(model_roles.role_config('evidence_reasoner'))==settings['roles']['evidence_reasoner']
        assert (settings['roles']['evidence_reasoner']['model'],settings['roles']['evidence_reasoner']['thinking'],
            settings['roles']['evidence_reasoner']['output_tokens'],settings['roles']['evidence_reasoner']['schema_mode'])==(
            'gemini-3.5-flash-lite','low',8192,'validated_json')
        for index,case in enumerate(original['cases']):
            cid=case['id'];source=PREVIOUS/'frozen-v3'/cid/'packet.json'
            assert sha(source)==case['packet_sha256']
            frozen=load(source);live_path=PREVIOUS/'live-results'/f'{cid}-off.json';live=load(live_path)
            assert sha(ROOT/frozen['scenario_path'])==case['scenario_sha256']
            old=await capture(old_reasoning,frozen['inputs'])
            control=await capture(role_reasoning,frozen['inputs'])
            assert control==old and control['messages']==live['model_messages'] and control['schema']==live['model_schema']
            assert control['messages']==frozen['arms']['off']['messages'] and control['schema']==frozen['arms']['off']['schema']
            assert settings==live['settings'],'Original inference settings changed'
            with patch.dict(os.environ,{'COGNISHIELD_AI_REASONER_INTERPRETATION_EXPERIMENT':'candidate'}):
                candidate=await capture(role_reasoning,frozen['inputs']);candidate_consent=model_roles.consent_manifest()
            assert candidate['messages'][0]['content']==control['messages'][0]['content']+' '+role_reasoning.TEMPORAL_INTERPRETATION_CANDIDATE
            assert candidate['messages'][1:]==control['messages'][1:] and candidate['schema']==control['schema']
            assert candidate['purpose']==control['purpose']=={'purpose':'synthesis'}
            packet=control['messages'][1]['content'];assert len(packet)<=64000
            assert not json.loads(packet).get('reasoning_contract'),'Failed reasoning overlay must stay OFF'
            dest=AUDIT/'frozen-v1'/cid/'pair.json'
            pair={'id':cid,'original_case':frozen['case'],'inputs':frozen['inputs'],
                'source_manifest':{'frozen_source_path':relative(source),'frozen_source_sha256':sha(source),
                    'scenario_path':frozen['scenario_path'],'scenario_sha256':case['scenario_sha256'],
                    'receipts':frozen['receipts'],'evidence':frozen['inputs']['evidence'],
                    'reader_results_sha256':digest(canonical(frozen['inputs']['results'])),
                    'original_control_trace':relative(live_path),'original_control_trace_sha256':sha(live_path)},
                'question_sha256':digest(frozen['inputs']['request']),'packet_sha256':digest(packet),
                'packet_characters':len(packet),'packet_bytes':len(packet.encode('utf-8')),
                'schema_sha256':digest(canonical(control['schema'])),
                'arms':{'control':{**control,'consent_manifest':settings},
                    'candidate':{**candidate,'consent_manifest':candidate_consent}},
                'consent_status':'PENDING_FRESH_USER_AUTHORIZATION_AND_EXISTING_EXACT_OWNER_APPROVAL',
                'expected_outcomes':frozen['case']['expected_outcomes'],'prohibited_claims':frozen['case']['prohibited_claims']}
            for arm in pair['arms'].values():
                arm['messages_sha256']=digest(canonical(arm['messages']))
                arm['system_instruction_sha256']=digest(arm['messages'][0]['content'])
                arm['role_binding_sha256']=digest(json.dumps(arm['consent_manifest'],sort_keys=True))
            save(dest,pair)
            records.append({'id':cid,'surface':frozen['case']['surface'],'pair_path':relative(dest),
                'pair_sha256':sha(dest),'packet_sha256':pair['packet_sha256'],'packet_characters':len(packet),
                'expected_outcomes':pair['expected_outcomes'],'prohibited_claims':pair['prohibited_claims']})
            for arm in (['control','candidate'] if index%2==0 else ['candidate','control']):
                calls.append({'sequence':len(calls)+1,'case':cid,'arm':arm})
        protected=['backend/llm/model_roles.py','backend/llm/orchestration/role_reasoning.py']
        for p in before['source_hashes']:
            if p not in protected:assert sha(ROOT/p)==before['source_hashes'][p],p
        spec={'version':1,'frozen_at':datetime.now(timezone.utc).isoformat(),'status':'OFFLINE_FROZEN_LIVE_NOT_AUTHORIZED',
            'original_registry':relative(ORIGINAL_SPEC),'original_registry_sha256':sha(ORIGINAL_SPEC),
            'original_oracles_unchanged':True,'distinct_conditions':6,'exposed_diagnostic_not_unseen':True,
            'instruction_delta':role_reasoning.TEMPORAL_INTERPRETATION_CANDIDATE,
            'instruction_delta_sha256':digest(role_reasoning.TEMPORAL_INTERPRETATION_CANDIDATE),
            'cases':records,'call_order':calls,'maximum_dispatch_attempts':12,'retries':0,
            'new_planner_calls':0,'new_reader_calls':0,'extra_model_calls':0,'calls_per_cell':1,
            'model_settings':settings['roles']['evidence_reasoner'],'control_consent_manifest':settings,
            'request_budget_seconds':120,'evidence_character_limit':64000,
            'shared_quota':{'path':'tmp/ai-cloud-usage.json','preflight_required_before_live':True,
                'rpm_ceiling':15,'input_tpm_ceiling':150000,'rpd_ceiling':500,
                'hash_at_freeze':before['quota_hash'],'rows_at_freeze':before['quota_rows']},
            'runtime_sources':{p:sha(ROOT/p) for p in before['source_hashes']},
            'grading':{'method':'Source-derived independently checkable, implementation-assistant graded; not blinded.',
                'raw_and_released_scored_separately':True,'no_retrieval_or_schema_credit':True,
                'dimensions':['full_answer_correctness','temporal_correctness','directional_correctness',
                    'causal_correctness','evidence_utilization','uncertainty_correctness','obligation_completeness',
                    'release_safety','false_suppression','operational_cost'],
                'classification':['adequate','partial','incorrect','unsupported','provider_noncompletion'],
                'raw_candidate_minimum_adequate':5,'nonregression_cases':['RC-01','RC-03','RC-04','RC-06'],
                'new_unsupported_causal_claims_allowed':0,'fallback_is_not_model_reasoning':True,
                'holdout_and_promotion_require_separate_authorization':True},
            'stop_conditions':['First provider unavailable/quota/authentication error; no retry or model switch.',
                'Source/settings/runtime hash or exact consent mismatch; no dispatch.',
                'Twelve attempts including failures; never spend unused calls automatically.'],
            'authorization':'NOT AUTHORIZED. Existing exhausted18call permission does not apply.',
            'automatic_promotion':False,'formal_phase_gate_closed':False}
        save(SPEC,spec)
        result={'status':'OFFLINE_VERIFIED_LIVE_NOT_RUN','registry':relative(SPEC),'registry_sha256':sha(SPEC),
            'candidate_sha256':spec['instruction_delta_sha256'],'all_six_control_inputs_exact':all_control_exact,
            'candidate_only_system_suffix':True,'packet_schema_sources_settings_unchanged':True,
            'cloud_dispatches':0,'actual_model_generation':0,'source_execution':0,
            'new_adequacy_scores':'NOT_RUN','fresh_authorization_required':True}
        save(AUDIT/'freeze-receipt.json',result);return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.parse_args()
    print(json.dumps(asyncio.run(freeze()),indent=2))
