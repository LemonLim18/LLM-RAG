"""Instruction/consent compatibility only; never evidence of model quality."""
import asyncio,copy,hashlib,json,sys,time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from fastapi import HTTPException

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import freeze_gemini35_interpretation as freeze
from llm import model_roles
from llm.orchestration import role_reasoning

@pytest.fixture(autouse=True)
def flags(monkeypatch):
    for k,v in freeze.ENV.items():monkeypatch.setenv(k,v)

def binding():return hashlib.sha256(json.dumps(model_roles.consent_manifest(),sort_keys=True).encode()).hexdigest()

def test_unset_defaults_off_and_does_not_add_consent_fields(monkeypatch):
    monkeypatch.delenv('COGNISHIELD_AI_REASONER_INTERPRETATION_EXPERIMENT')
    assert model_roles.reasoner_interpretation_mode()=='off'
    assert model_roles.consent_manifest()==freeze.preimage('model_roles').consent_manifest()
    assert 'reasoner_interpretation_experiment' not in model_roles.consent_manifest()

@pytest.mark.parametrize('invalid',['on','1','auto','Candidate',''])
def test_invalid_mode_cannot_grant_consent(invalid,monkeypatch):
    monkeypatch.setenv('COGNISHIELD_AI_REASONER_INTERPRETATION_EXPERIMENT',invalid)
    with pytest.raises(HTTPException) as e:model_roles.consent_manifest()
    assert e.value.status_code==422

@pytest.mark.parametrize('cid',[f'RC-{i:02d}' for i in range(1,7)])
def test_original_control_exact_and_only_candidate_suffix(cid,monkeypatch):
    frozen=freeze.load(freeze.PREVIOUS/'frozen-v3'/cid/'packet.json')
    live=freeze.load(freeze.PREVIOUS/'live-results'/f'{cid}-off.json')
    with patch('httpx.AsyncClient.send',freeze.forbidden),patch('socket.create_connection',freeze.forbidden):
        old=asyncio.run(freeze.capture(freeze.preimage('orchestration/role_reasoning'),frozen['inputs']))
        control=asyncio.run(freeze.capture(role_reasoning,frozen['inputs']))
        monkeypatch.setenv('COGNISHIELD_AI_REASONER_INTERPRETATION_EXPERIMENT','candidate')
        candidate=asyncio.run(freeze.capture(role_reasoning,frozen['inputs']))
    assert control==old
    assert control['messages']==live['model_messages']==frozen['arms']['off']['messages']
    assert control['schema']==candidate['schema']==live['model_schema']
    assert candidate['messages'][1:]==control['messages'][1:]
    assert candidate['messages'][0]=={'role':'system','content':control['messages'][0]['content']+' '+role_reasoning.TEMPORAL_INTERPRETATION_CANDIDATE}
    assert 'reasoning_contract' not in json.loads(candidate['messages'][1]['content'])
    assert len(candidate['messages'][1]['content'])<=64000

def test_candidate_consent_binds_exact_instruction_and_settings(monkeypatch):
    old=model_roles.consent_manifest();old_binding=binding()
    monkeypatch.setenv('COGNISHIELD_AI_REASONER_INTERPRETATION_EXPERIMENT','candidate')
    current=model_roles.consent_manifest();extra=current.pop('reasoner_interpretation_experiment')
    assert current==old and binding()!=old_binding
    assert extra=={'version':'temporal_evidence_v1','mode':'candidate',
        'instruction_delta':role_reasoning.TEMPORAL_INTERPRETATION_CANDIDATE,
        'instruction_sha256':freeze.digest(role_reasoning.TEMPORAL_INTERPRETATION_CANDIDATE)}
    assert current['roles']['evidence_reasoner']==freeze.load(freeze.PREVIOUS/'live-results/RC-01-off.json')['settings']['roles']['evidence_reasoner']
    monkeypatch.setattr(role_reasoning,'TEMPORAL_INTERPRETATION_CANDIDATE',role_reasoning.TEMPORAL_INTERPRETATION_CANDIDATE+' changed')
    assert model_roles.consent_manifest()['reasoner_interpretation_experiment']['instruction_sha256']!=extra['instruction_sha256']

def test_old_owned_consent_cannot_enable_candidate(monkeypatch):
    from llm.gemini_provider import HybridRequest
    old_binding=binding();scenario={'scenario_digest':'synthetic','source_revision':'revision'}
    scope=SimpleNamespace(db=object(),role_binding=old_binding,approved_scenario=scenario)
    def context(db):return {'enabled':True,'eligible':True,'role_binding':binding(),**scenario}
    with patch('llm.gemini_provider.hybrid_context',context):
        HybridRequest.assert_current_roles(scope)
        monkeypatch.setenv('COGNISHIELD_AI_REASONER_INTERPRETATION_EXPERIMENT','candidate')
        with pytest.raises(HTTPException) as e:HybridRequest.assert_current_roles(scope)
        assert e.value.status_code==403
        scope.role_binding=binding();HybridRequest.assert_current_roles(scope)

def test_candidate_configuration_alone_never_authorizes_provider(monkeypatch):
    monkeypatch.setenv('COGNISHIELD_AI_REASONER_INTERPRETATION_EXPERIMENT','candidate')
    with patch('httpx.AsyncClient.send',freeze.forbidden),pytest.raises(HTTPException) as e:
        asyncio.run(model_roles.infer('evidence_reasoner',model_roles.InferenceRequest(
            [{'role':'user','content':'Synthetic'}],{'type':'object'},time.monotonic()+10)))
    assert e.value.status_code==403

def test_candidate_leaves_ordinary_local_and_planner_roles_unchanged(monkeypatch):
    before=model_roles.role_manifest()
    monkeypatch.setenv('COGNISHIELD_AI_REASONER_INTERPRETATION_EXPERIMENT','candidate')
    assert model_roles.role_manifest()==before
    assert model_roles.investigation_profile()['seconds']==120
    assert before['local_default']['model']=='qwen2.5:1.5b'
    assert before['complex_planner']['model']=='gemini-3.1-flash-lite'

def test_simple_request_does_not_gain_packet_metadata_or_other_outcomes(monkeypatch):
    args={'request':'Show the recorded prefix.','results':[],'evidence':[],'history':[],'planning':{},
        'retrieval':{'supplementary_permitted':False}}
    off=asyncio.run(freeze.capture(role_reasoning,args))
    monkeypatch.setenv('COGNISHIELD_AI_REASONER_INTERPRETATION_EXPERIMENT','candidate')
    on=asyncio.run(freeze.capture(role_reasoning,args))
    assert off['messages'][1:]==on['messages'][1:]
    assert off['schema']==on['schema'] and len(json.loads(on['messages'][1]['content'])['requested_clauses'])==1

def test_malformed_json_and_unknown_source_are_still_rejected(monkeypatch):
    monkeypatch.setenv('COGNISHIELD_AI_REASONER_INTERPRETATION_EXPERIMENT','candidate')
    with pytest.raises(ValueError):role_reasoning.parse_decision('{partial',independent_claims=True)
    frozen=freeze.load(freeze.PREVIOUS/'frozen-v3/RC-01/packet.json')
    raw=freeze.load(freeze.PREVIOUS/'live-results/RC-01-off.json')['raw']
    value=json.loads(raw);value['sources']=['invented-authoritative-source']
    async def generate(*a,**kw):return json.dumps(value),'gemini-3.5-flash-lite'
    from llm.gateway_models import Evidence
    args=copy.deepcopy(frozen['inputs']);args['evidence']=[Evidence.model_validate(e) for e in args['evidence']]
    model=SimpleNamespace(hybrid=SimpleNamespace(role_calls=0,remote_calls=0,max_remote_calls=3),generate=generate)
    with pytest.raises(HTTPException) as e:asyncio.run(role_reasoning.decide(model,**args))
    assert e.value.status_code==422

def test_invalid_flag_fails_before_generation(monkeypatch):
    monkeypatch.setenv('COGNISHIELD_AI_REASONER_INTERPRETATION_EXPERIMENT','unsupported')
    with pytest.raises(HTTPException):
        asyncio.run(freeze.capture(role_reasoning,{'request':'Synthetic','results':[],'evidence':[],'history':[],'planning':{}}))
