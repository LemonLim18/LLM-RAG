"""Compare OFF against preserved code and exercise frozen contract release.

This is deterministic contract validation, never model reasoning evaluation.
"""
import asyncio,copy,hashlib,importlib.util,json,os,sys
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'tmp/phase-g/iterations/20261102-evidence-reasoning-contract'
sys.path.insert(0,str(ROOT/'backend'))
os.environ.update(COGNISHIELD_AI_REASONING_CONTRACT='off',COGNISHIELD_AI_COMPLETENESS='1',COGNISHIELD_AI_OUTCOMES='0',
    COGNISHIELD_AI_EVIDENCE_HARNESS='0',COGNISHIELD_AI_EVIDENCE_LAYOUT='current')
from llm.orchestration.role_reasoning import decide,parse_decision,preview
from llm.orchestration.reasoning_contract import validate,release
from llm.gateway_models import Evidence

def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def preimage(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module;spec.loader.exec_module(module);return module

async def main():
    old=preimage('reasoning_task_start',OUT/'source-before/backend/llm/orchestration/role_reasoning.py')
    old_roles=preimage('roles_task_start',OUT/'source-before/backend/llm/model_roles.py')
    from llm.model_roles import consent_manifest
    assert old_roles.consent_manifest()==consent_manifest(),'OFF consent behavior changed'
    specpath=ROOT/'docs/evaluations/phase_g_evidence_reasoning_contract_v3.json';spec=load(specpath)
    assert sha(specpath)==load(OUT/'freeze-receipt-v3.json')['registry_sha256']
    reports=[]
    class Captured(Exception):pass
    for case in spec['cases']:
        path=OUT/'frozen-v3'/case['id']/'packet.json';assert sha(path)==case['packet_sha256']
        frozen=load(path);args=copy.deepcopy(frozen['inputs']);args['evidence']=[Evidence.model_validate(e) for e in args['evidence']]
        class Capture:
            hybrid=SimpleNamespace(remote_calls=0,role_calls=0,max_remote_calls=3)
            async def generate(self,messages,structured,purpose):
                self.messages=messages;self.schema=structured;raise Captured()
        os.environ['COGNISHIELD_AI_REASONING_CONTRACT']='off';before=Capture();current=Capture()
        for implementation,model in [(old.decide,before),(decide,current)]:
            try:await implementation(model,**args)
            except Captured:pass
        assert before.messages==current.messages==frozen['arms']['off']['messages']
        assert before.schema==current.schema==frozen['arms']['off']['schema']
        baseline=json.loads(before.messages[-1]['content'])
        byarm={}
        for arm,wire in frozen['arms'].items():
            packet=json.loads(wire['messages'][-1]['content'])
            assert packet['reader_results']==baseline['reader_results']
            assert packet['sources']==baseline['sources'] and packet['original_user_instruction']==baseline['original_user_instruction']
            if arm=='off':byarm[arm]={'OFF_exact_preimage_messages_schema':True};continue
            obligations=packet['reasoning_contract']['obligations'];refs=[e.id for e in args['evidence']]
            d={'decision':'answer','answer':'Deterministic fixture: qualified interpretation, not an actual model answer.',
               'sources':[],'raw_output':'synthetic contract fixture','outcomes':[
                {'obligation_id':o['obligation_id'],'conclusion':'Explicit unresolved fixture conclusion.',
                 'evidence_ids':refs,'status':'unresolved','limitations':['Synthetic fixture, not inference'],'assertions':[]} for o in obligations]}
            valid=validate(d,packet);assert valid['coverage_complete'] and not valid['findings']
            assert release({**d,'reasoning_validation':valid})['answer']==d['answer']
            partial=copy.deepcopy(d);partial['outcomes'].pop();missing=validate(partial,packet)
            assert any(f['kind']=='MISSING_OBLIGATION' for f in missing['findings'])
            facts=packet['reasoning_contract'].get('relationships',{}).get('facts',[])
            byarm[arm]={'source_operands_and_identities_unchanged':True,'valid_fixture_preserved':True,
                'missing_outcome_detected':True,'semantic_completion_not_certified':True,'facts_admitted':len(facts),
                'characters':len(wire['messages'][-1]['content'])}
            if facts:
                f=facts[0];binding=packet['reasoning_contract']['relationships']['source_records'][f['record_index']]
                bad=copy.deepcopy(d);bad['outcomes'][0]['evidence_ids']=[binding['record_id']]
                bad['outcomes'][0]['assertions']=[{'relationship_id':f['id'],'value':'intentionally wrong fixture value','authority':binding['authority']}]
                invalid=validate(bad,packet);assert invalid['conflicts']
                assert release({**bad,'reasoning_validation':invalid})['answer']!=bad['answer']
                byarm[arm]['declared_wrong_value_withheld']=True
                # Every indexed operand is independently traceable to exact raw
                # data, except the explicitly marked existing class projection.
                for fact in facts:
                    if fact['value_path'] is None:
                        assert fact['value_origin'].startswith('Existing investigation_support.classify');continue
                    b=packet['reasoning_contract']['relationships']['source_records'][fact['record_index']]
                    target=packet
                    for token in (b['record_path']+fact['value_path']).strip('/').split('/'):
                        token=token.replace('~1','/').replace('~0','~');target=target[int(token)] if isinstance(target,list) else target[token]
                    assert target==fact['value']
        reports.append({'case':case['id'],'arms':byarm})
    os.environ['COGNISHIELD_AI_REASONING_CONTRACT']='off'
    result={'registry_sha256':sha(specpath),'offline_only':True,'cloud_dispatches':0,
        'scope':'Exact OFF compatibility, identical admitted sources and synthetic release fixtures. No actual model reasoning or deduction-quality score.',
        'cases':reports,'raw_deduction_improvement':'NOT_MEASURED','live_status':'NOT_RUN_PENDING_FRESH_EXPLICIT_CONSENT',
        'promote':False,'status':'OFFLINE_CONTRACT_GATES_PASS'}
    with (OUT/'offline-review.json').open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps({'offline_conditions':len(reports),'OFF_messages_schema_consent_exact':True,'source_equality':True,'cloud_dispatches':0,'model_quality':'NOT_MEASURED'}))

if __name__=='__main__':asyncio.run(main())
