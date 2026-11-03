"""Offline compatibility/fixture tests, not proof of Gemini intelligence."""
import asyncio,copy,hashlib,json,sys,time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from fastapi import HTTPException
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import freeze_timestamp_contract as freezer
from llm import model_roles
from llm.orchestration import role_reasoning

@pytest.fixture(autouse=True)
def flags(monkeypatch):
    for k,v in freezer.ENV.items():monkeypatch.setenv(k,v)

def binding():return freezer.digest(json.dumps(model_roles.consent_manifest(),sort_keys=True))

def test_default_off_and_exact_manifest_preimage(monkeypatch):
    monkeypatch.delenv('COGNISHIELD_AI_SOURCECLAIM_TIMESTAMP_EXPERIMENT')
    assert model_roles.sourceclaim_timestamp_mode()=='off'
    assert model_roles.consent_manifest()==freezer.before_module('model_roles').consent_manifest()
    assert 'sourceclaim_timestamp_experiment' not in model_roles.consent_manifest()

@pytest.mark.parametrize('value',['on','1','auto','Candidate',''])
def test_invalid_mode_fails_closed(value,monkeypatch):
    monkeypatch.setenv('COGNISHIELD_AI_SOURCECLAIM_TIMESTAMP_EXPERIMENT',value)
    with pytest.raises(HTTPException) as e:model_roles.consent_manifest()
    assert e.value.status_code==422

@pytest.mark.parametrize('index',range(6))
def test_six_fresh_schemas_only_change_description_and_not_messages(index,monkeypatch):
    c=freezer.cases()[index];args=freezer.inputs(c)
    off=asyncio.run(freezer.capture(role_reasoning,args));before=asyncio.run(freezer.capture(freezer.before_module('orchestration/role_reasoning'),args))
    assert off==before
    assert json.dumps(off['schema'])==json.dumps(before['schema'])
    assert json.dumps(off['messages'],ensure_ascii=False)==json.dumps(before['messages'],ensure_ascii=False)
    monkeypatch.setenv('COGNISHIELD_AI_SOURCECLAIM_TIMESTAMP_EXPERIMENT','candidate')
    on=asyncio.run(freezer.capture(role_reasoning,args));schema=copy.deepcopy(on['schema'])
    assert schema['$defs']['SourceClaim']['properties']['timestamp'].pop('description')==role_reasoning.SOURCECLAIM_TIMESTAMP_DESCRIPTION
    assert schema==off['schema'] and on['messages']==off['messages'] and on['purpose']==off['purpose']
    assert 'description' not in role_reasoning.SourceClaim.model_json_schema()['properties']['timestamp']
    assert json.loads(on['messages'][1]['content'])['original_user_instruction']==c['question']

@pytest.mark.parametrize('index',[0,1,5])
def test_actual_google_serialization_preserves_only_field_description(index,monkeypatch):
    args=freezer.inputs(freezer.cases()[index]);off=asyncio.run(freezer.capture(role_reasoning,args))
    monkeypatch.setenv('COGNISHIELD_AI_SOURCECLAIM_TIMESTAMP_EXPERIMENT','candidate')
    on=asyncio.run(freezer.capture(role_reasoning,args))
    with patch('socket.create_connection',freezer.forbidden):
        a=asyncio.run(freezer.serialized_wire(off['messages'],off['schema']))
        b=asyncio.run(freezer.serialized_wire(on['messages'],on['schema']))
    assert b['contents']==a['contents'] and b['systemInstruction']['parts'][0]==a['systemInstruction']['parts'][0]
    prefix='Return only JSON satisfying this exact application schema: '
    serialized=json.loads(b['systemInstruction']['parts'][1]['text'][len(prefix):])
    assert serialized==on['schema']
    assert serialized['$defs']['SourceClaim']['properties']['timestamp']['description']==role_reasoning.SOURCECLAIM_TIMESTAMP_DESCRIPTION
    b['systemInstruction']['parts'][1]=a['systemInstruction']['parts'][1];assert a==b
    assert a['generationConfig']=={'thinkingConfig':{'thinkingLevel':'low'},'maxOutputTokens':8192,'responseMimeType':'application/json'}

def test_consent_binds_exact_candidate_and_old_consent_rejected(monkeypatch):
    old=model_roles.consent_manifest();old_binding=binding()
    monkeypatch.setenv('COGNISHIELD_AI_SOURCECLAIM_TIMESTAMP_EXPERIMENT','candidate')
    current=model_roles.consent_manifest();detail=current.pop('sourceclaim_timestamp_experiment')
    assert current==old and detail['description']==role_reasoning.SOURCECLAIM_TIMESTAMP_DESCRIPTION
    assert detail['description_sha256']==hashlib.sha256(detail['description'].encode()).hexdigest()
    assert detail['schema_pointer']=='/$defs/SourceClaim/properties/timestamp/description'
    from llm.gemini_provider import HybridRequest
    source={'scenario_digest':'synthetic','source_revision':'revision'}
    scope=SimpleNamespace(db=object(),role_binding=old_binding,approved_scenario=source)
    with patch('llm.gemini_provider.hybrid_context',lambda db:{'enabled':True,'eligible':True,'role_binding':binding(),**source}):
        with pytest.raises(HTTPException) as e:HybridRequest.assert_current_roles(scope)
        assert e.value.status_code==403
        scope.role_binding=binding();HybridRequest.assert_current_roles(scope)
    previous=binding();monkeypatch.setattr(role_reasoning,'SOURCECLAIM_TIMESTAMP_DESCRIPTION',detail['description']+' changed')
    assert previous!=binding()

def test_candidate_flag_never_grants_cloud_authority(monkeypatch):
    monkeypatch.setenv('COGNISHIELD_AI_SOURCECLAIM_TIMESTAMP_EXPERIMENT','candidate')
    with patch('httpx.AsyncClient.send',freezer.forbidden),pytest.raises(HTTPException) as e:
        asyncio.run(model_roles.infer('evidence_reasoner',model_roles.InferenceRequest([{'role':'user','content':'Synthetic'}],{'type':'object'},time.monotonic()+10)))
    assert e.value.status_code==403

def test_six_source_fixtures_valid_and_existing_calculations_check_oracles():
    from local_providers.development import Scenario
    cs=freezer.cases();assert len(cs)==6
    for c in cs:
        Scenario.model_validate(c['scenario']);assert c['oracle']['required_components'] and c['oracle']['prohibited_conclusions']
        assert c['oracle']['positive_and_negative_controls'] and c['oracle']['distinct_from_historical']
    h5=cs[4]['scenario']['records']['state'][0]['values']['assessment']
    assert h5['forward']['status']=='unknown' and h5['return']['status']=='delivered'
    h6=cs[5]['scenario']['records']['state'];trap=h6[0]['values']['assessment'];log=h6[1]['values']['assessment']
    stop=trap['forward']['branches'][0]['failure_location']
    assert trap['forward']['status']=='failed' and trap['return']['status']=='delivered'
    assert (stop['device_id'],stop['interface_id'],stop['direction'])==(5302,53022,'egress')
    assert log['forward']['status']==log['return']['status']=='delivered'
    assert freezer.check_oracles(cs)['source_time_arithmetic_and_model_locations']=='PASS'

def test_existing_semantics_record_binding_and_event_value_are_separate():
    from llm.orchestration.investigation_support import compatible_claims
    c=freezer.cases()[0];args=freezer.inputs(c);claim={**c['oracle']['claim_bindings'][0],'statement':'A source-bound application time.','scope':'recorded','direction':None,'vrf':None}
    inventory={'devices':[{**d,'interfaces':[p for p in c['scenario']['interfaces'] if p['device_id']==d['id']]} for d in c['scenario']['devices']]}
    def check(x):return compatible_claims({'answer':x['statement'],'claims':[x]},args['results'],inventory)['claims'][0]
    assert check(claim)['verdict']=='SUPPORTED'
    assert check({**claim,'timestamp':claim['value']})['verdict']=='NOT_MECHANICALLY_CHECKABLE'
    assert check({**claim,'value':claim['timestamp']})['verdict']=='CONTRADICTED'

def test_incident_time_support_not_expanded_by_description(monkeypatch):
    from llm.orchestration.investigation_support import compatible_claims
    c=freezer.cases()[1];args=freezer.inputs(c);x={**c['oracle']['claim_bindings'][0],'statement':'Source observed an interruption.','scope':'recorded'}
    inventory={'devices':[{**d,'interfaces':[]} for d in c['scenario']['devices']]}
    off=compatible_claims({'claims':[x]},args['results'],inventory)
    monkeypatch.setenv('COGNISHIELD_AI_SOURCECLAIM_TIMESTAMP_EXPERIMENT','candidate')
    assert compatible_claims({'claims':[x]},args['results'],inventory)==off
    assert off['claims'][0]['verdict']=='INSUFFICIENT_EVIDENCE' and not off['conflicts']

def test_captured_at_fallback_only_when_record_timestamp_absent():
    from llm.orchestration.investigation_support import compatible_claims
    c=freezer.cases()[0];args=freezer.inputs(c)
    record=args['results'][0]['data']['records'][0];record['captured_at']=record.pop('timestamp')
    x={**c['oracle']['claim_bindings'][0],'statement':'A verified source field.','scope':'recorded'}
    inventory={'devices':[{**d,'interfaces':c['scenario']['interfaces']} for d in c['scenario']['devices']]}
    def check():return compatible_claims({'claims':[x]},args['results'],inventory)['claims'][0]['verdict']
    assert check()=='SUPPORTED'
    record['timestamp']=None
    assert check()=='NOT_MECHANICALLY_CHECKABLE'

def test_no_material_evidence_or_source_queries_added_in_candidate(monkeypatch):
    args=freezer.inputs(freezer.cases()[4]);before=copy.deepcopy(args)
    monkeypatch.setenv('COGNISHIELD_AI_SOURCECLAIM_TIMESTAMP_EXPERIMENT','candidate')
    with patch('llm.tools.ToolRegistry.invoke',freezer.forbidden),patch('socket.create_connection',freezer.forbidden):
        on=asyncio.run(freezer.capture(role_reasoning,args))
    assert args==before and on['schema']['properties']['additional_reads']['maxItems']==0
    packet=json.loads(on['messages'][1]['content']);assert len(on['messages'][1]['content'])<64000
    assert packet['reader_results']==args['results'] and 'reasoning_contract' not in packet

def test_noncomprehensive_schema_unchanged_when_no_claim_contract(monkeypatch):
    monkeypatch.setenv('COGNISHIELD_AI_COMPLETENESS','0');args=freezer.inputs(freezer.cases()[0])
    a=asyncio.run(freezer.capture(role_reasoning,args));monkeypatch.setenv('COGNISHIELD_AI_SOURCECLAIM_TIMESTAMP_EXPERIMENT','candidate')
    b=asyncio.run(freezer.capture(role_reasoning,args));assert a==b
