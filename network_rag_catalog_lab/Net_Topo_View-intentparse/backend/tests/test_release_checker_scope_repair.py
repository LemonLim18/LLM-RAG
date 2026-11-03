"""Three release-only repairs; no inference, readers or semantic grader."""
import copy,json,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm.orchestration.investigation_support import compatible_claims,release_interpretation
from llm.orchestration.reasoning_contract import validate,release
from tests.test_evidence_reasoning_contract import packet,decision,typed

def source(records):return [{'tool':'network.state','status':'success','data':{'records':records},'evidence_ids':['source']}]

def claim(**kw):
    return {'statement':'A source-bound assertion.','category':'simulated_forwarding','record_refs':['flow'],
        'device_id':'10','interface_id':'101','vrf':'violet','timestamp':None,'field':'status','direction':'forward','branch_id':None,'scope':'modeled','value':'delivered',**kw}

def check(c,records):return compatible_claims({'answer':c['statement'],'claims':[c]},source(records),{'devices':[]})

def temporal(**kw):return {'id':'event','kind':'configuration_change','device_id':10,'timestamp':'2026-09-14T09:34:00Z',
    'effective_at':'2026-09-14T09:33:00Z','verification_status':'verified','applied':True,**kw}

def temporal_claim(**kw):return claim(category='configuration_change_time',record_refs=['event'],interface_id=None,vrf=None,
    scope='recorded',direction=None,field='effective_at',value='2026-09-14T09:33:00Z',**kw)

def flow():return {'id':'flow','kind':'forwarding_assessment','device_id':10,'derived':True,'assessment':{
    'forward':{'status':'delivered','scope':{'source_device_id':10,'destination_device_id':30,'vrf':'violet'},'branches':[{
        'id':'f','status':'delivered','hops':[{'device_id':10,'interface_id':101,'interface':'out10','vrf':'violet'},
            {'device_id':20,'interface_id':202,'interface':'out20','vrf':'violet','ingress':{'device_id':20,'interface_id':201,'direction':'ingress','vrf':'violet'}}],
        'destination_ingress':{'device_id':30,'interface_id':301,'direction':'ingress','vrf':'violet'}}]},
    'return':{'status':'failed','scope':{'source_device_id':30,'destination_device_id':10,'vrf':'violet'},'branches':[{
        'id':'r','status':'failed','hops':[{'device_id':30,'interface_id':302,'vrf':'violet'}],
        'failure_location':{'device_id':20,'interface_id':203,'direction':'ingress','vrf':'violet'}}]}}}

def test_explicit_effective_field_does_not_substitute_record_timestamp():
    assert check(temporal_claim(),[temporal()])['claims'][0]['verdict']=='SUPPORTED'

def test_successful_egress_is_not_a_failure_location():
    assert check(claim(),[flow()])['claims'][0]['verdict']=='SUPPORTED'

def test_optional_unknown_hint_does_not_wholesale_suppress_core():
    p=packet();d=decision(p);d['outcomes'][0]['assertions']=[{'relationship_id':'invented-hint','value':'down','authority':'recorded'}]
    result=release({**d,'reasoning_validation':validate(d,p)})
    assert d['answer'] in result['answer'] and result['reasoning_release']['model_prose_released']

@pytest.mark.parametrize('field,time',[
    ('effective_at','09:33:00'),('timestamp','09:34:00'),('observed_at','09:32:00'),
    ('recorded_at','09:35:00'),('saved_at','09:20:00'),('vendor_activated_at','09:31:00')])
def test_explicit_temporal_fields_keep_their_own_values(field,time):
    event=temporal(observed_at='2026-09-14T09:32:00Z',recorded_at='2026-09-14T09:35:00Z',
        saved_at='2026-09-14T09:20:00Z',vendor_activated_at='2026-09-14T09:31:00Z')
    c=temporal_claim();c.update(field=field,value='2026-09-14T'+time+'Z')
    r=check(c,[event]);assert r['claims'][0]['verdict']=='SUPPORTED'
    assert r['claims'][0]['actual_values']==[event[field]]

def test_wrong_effective_value_contradicts_even_if_record_timestamp_matches():
    c=temporal_claim();c['value']=temporal()['timestamp']
    r=check(c,[temporal()]);assert r['claims'][0]['verdict']=='CONTRADICTED'
    assert r['claims'][0]['actual_values']==[temporal()['effective_at']]

@pytest.mark.parametrize('mutation',['missing','null','not_time','wrong_source','wrong_owner','wrong_record_time','not_applied','not_verified'])
def test_temporal_scope_and_authority_cannot_be_guessed(mutation):
    c=temporal_claim();event=temporal()
    if mutation=='missing':event.pop('effective_at')
    if mutation=='null':event['effective_at']=None
    if mutation=='not_time':event['effective_at']='not a date'
    if mutation=='wrong_source':c['record_refs']=['not-returned']
    if mutation=='wrong_owner':c['device_id']='99'
    if mutation=='wrong_record_time':c['timestamp']='2026-09-14T09:30:00Z'
    if mutation=='not_applied':event['applied']=False
    if mutation=='not_verified':event['verification_status']='unknown'
    r=check(c,[event]);assert r['claims'][0]['verdict']!='SUPPORTED'
    if mutation in {'missing','null','not_time'}:assert r['claims'][0]['actual_values']==[]

def test_unspecified_legacy_time_keeps_existing_default():
    c=temporal_claim();c.update(field=None,value=temporal()['timestamp'])
    assert check(c,[temporal()])['claims'][0]['verdict']=='SUPPORTED'

def test_wrong_returned_record_cannot_borrow_another_records_effective_time():
    other=temporal(id='other',effective_at='2026-09-14T09:38:00Z')
    c=temporal_claim();c['record_refs']=['other']
    r=check(c,[temporal(),other]);assert r['claims'][0]['verdict']=='CONTRADICTED'
    assert r['claims'][0]['actual_values']==[other['effective_at']]

def test_broad_receipt_keeps_conflicting_effective_times_unresolved():
    c=temporal_claim();c['record_refs']=['source']
    r=check(c,[temporal(),temporal(id='other',effective_at='2026-09-14T09:38:00Z')])
    assert r['claims'][0]['verdict']=='INSUFFICIENT_EVIDENCE'
    assert len(r['claims'][0]['actual_values'])==2 and not r['conflicts']

@pytest.mark.parametrize('device,port,field,direction,value',[
    (10,101,'egress.status','forward','delivered'),
    (20,201,'ingress.status','forward','delivered'),
    (20,202,'egress.status','forward','delivered'),
    (30,301,'ingress.status','forward','delivered'),
    (30,302,'egress.status','return','failed'),
    (20,203,'failure_location.status','return','failed'),
    (20,203,'status','return','failed')])
def test_directional_successful_traversal_and_actual_failure(device,port,field,direction,value):
    c=claim(device_id=str(device),interface_id=str(port),field=field,direction=direction,value=value)
    r=check(c,[flow()]);assert r['claims'][0]['verdict']=='SUPPORTED'

@pytest.mark.parametrize('change',[
    {'interface_id':'999'}, {'device_id':'99'}, {'vrf':'other'}, {'direction':'return'},
    {'field':'ingress.status'}, {'field':'failure_location.status'}, {'value':'failed'}])
def test_wrong_owner_interface_vrf_role_direction_or_stop_cannot_pass(change):
    c=claim(field='egress.status');c.update(change)
    r=check(c,[flow()]);assert r['claims'][0]['verdict']=='CONTRADICTED'

def test_legacy_failed_at_location_does_not_expand_to_earlier_traversed_port():
    c=claim(direction='return',device_id='30',interface_id='302',value='failed')
    assert check(c,[flow()])['claims'][0]['verdict']=='CONTRADICTED'

def test_missing_path_is_unverifiable_not_an_invented_interface():
    f=flow();f['assessment']['forward']={'status':'unknown','branches':[{'status':'unknown','reason':'no observations'}]}
    r=check(claim(),[f]);assert r['claims'][0]['verdict']=='NOT_MECHANICALLY_CHECKABLE'

def test_complete_ecmp_keeps_overall_and_branch_dispositions_separate():
    f=flow();part=f['assessment']['forward'];part['status']='partial'
    part['branches'].append({'id':'drop','status':'failed','hops':[],
        'failure_location':{'device_id':10,'interface_id':102,'direction':'egress'}})
    c=claim(branch_id='f',field='egress.status');assert check(c,[f])['claims'][0]['verdict']=='SUPPORTED'
    c.update(interface_id='102',branch_id='drop',field='failure_location.status',value='failed')
    assert check(c,[f])['claims'][0]['verdict']=='SUPPORTED'
    c.update(interface_id='101');assert check(c,[f])['claims'][0]['verdict']=='CONTRADICTED'
    c.update(device_id=None,interface_id=None,branch_id=None,field='status',value='delivered')
    assert check(c,[f])['claims'][0]['verdict']=='CONTRADICTED'

@pytest.mark.parametrize('change',[{'scope':'physical'}, {'category':'ospf_state'}, {'category':'bgp_state'}])
def test_success_does_not_certify_physical_or_protocol_state(change):
    c=claim();c.update(change);r=check(c,[flow()])
    assert r['claims'][0]['verdict']!='SUPPORTED'

def test_valid_navigation_resolves_while_wrong_scalar_still_blocks():
    p=packet();d=decision(p);o=d['outcomes'][0]
    o['assertions']=[typed(p,'interface_oper_state')]
    r=validate(d,p);assert not r['findings'] and not r['semantic_certified']
    o['assertions'][0]['value']='up';r=validate(d,p);assert r['conflicts']
    assert release({**d,'reasoning_validation':r})['answer']!=d['answer']

def test_bad_optional_hint_does_not_hide_independent_wrong_typed_fact():
    p=packet();d=decision(p);d['answer']='The flow is delivered.'
    d['outcomes'][0]['assertions']=[{'relationship_id':'invented','value':'delivered','authority':'modeled'}]
    wrong=claim(statement=d['answer'],direction='return',device_id='20',interface_id='203',value='delivered')
    c=check(wrong,[flow()]);assert c['conflicts']
    blocked=release_interpretation(d,{'claim_compatibility':c})
    final=release({**blocked,'reasoning_validation':validate(d,p)})
    assert 'The flow is delivered.' not in final['answer']
    assert final['release_decision']['disposition']=='PARTIAL_WITHHELD'
    assert wrong['statement'] in final['release_decision']['withheld_spans']
    assert not final['reasoning_release']['semantic_certified']
    diagnostic=final['reasoning_validation']['findings'][0]
    assert diagnostic['verification']=='UNVERIFIED_OPTIONAL_METADATA'
    assert diagnostic['assertion']['value']=='delivered'

@pytest.mark.parametrize('mutation',['unknown_source','wrong_known_source'])
def test_optional_navigation_never_authorizes_an_evidence_reference(mutation):
    p=packet();d=decision(p);o=d['outcomes'][0]
    o['assertions']=[{'relationship_id':'invented','value':'down','authority':'recorded'}]
    if mutation=='unknown_source':o['evidence_ids']=['invented']
    else:
        p['sources'].append({'id':'other-source'});o['evidence_ids']=['other-source']
        o['assertions'].append(typed(p,'interface_oper_state'))
    r=validate(d,p);final=release({**d,'reasoning_validation':r})
    assert final['reasoning_release']['disposition']=='WITHHELD_INVALID_BINDING'

def test_future_no_index_schema_and_frozen_response_compatibility(monkeypatch):
    import asyncio
    from types import SimpleNamespace
    from llm.orchestration.role_reasoning import decide,parse_decision
    from llm.model_roles import validate_result
    from tests.test_evidence_reasoning_contract import inputs
    monkeypatch.setenv('COGNISHIELD_AI_COMPLETENESS','1');monkeypatch.setenv('COGNISHIELD_AI_REASONING_CONTRACT','obligations')
    seen={}
    class Captured(Exception):pass
    class Model:
        hybrid=SimpleNamespace(role_calls=0,remote_calls=0,max_remote_calls=3)
        async def generate(self,messages,structured,**kw):seen['schema']=structured;raise Captured()
    with pytest.raises(Captured):asyncio.run(decide(Model(),**inputs('Explain recorded state.')))
    assert seen['schema']['$defs']['GroundedOutcome']['properties']['assertions']['maxItems']==0
    root=Path(__file__).resolve().parents[2]
    frozen=json.loads((root/'tmp/phase-g/iterations/20261102-evidence-reasoning-contract/live-results/RC-04-obligations.json').read_text(encoding='utf-8'))
    validate_result(frozen['raw'],frozen['model_schema'])
    old,_=parse_decision(frozen['raw'],independent_claims=True,grounded=True)
    assert old.outcomes[0].assertions  # Preserved diagnostics, not deleted.
    with pytest.raises(Exception):validate_result(frozen['raw'],seen['schema'])
