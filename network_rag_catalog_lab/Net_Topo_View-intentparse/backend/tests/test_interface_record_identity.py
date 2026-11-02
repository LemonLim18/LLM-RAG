"""Exact reader identity projection; local model text is not reasoning credit."""
import asyncio,copy,json,sys
from pathlib import Path
import pytest
from fastapi import HTTPException
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm.gateway_models import Evidence
from llm.gateway_network import network_context
from llm.gateway_services import registry_for
from llm.orchestration.synthesis import interface_observations,synthesize
from llm.tools import ToolAuthorization
from tests.test_state_interface_scope import scoped_environment

QUESTION='Using recorded state only, show Meadow Ethernet9/3 administrative and operational state with source record IDs. Do not read other sources.'

def read_material(db,surface='floating'):
    auth=ToolAuthorization('record-id-owner','engineer',surface,'record-id-conversation',frozenset({'network.state'}))
    return asyncio.run(network_context(db,registry_for(db),auth,QUESTION,
        domains_override=['state'],device_refs_override=['703'],interface_refs_override=['7031'],
        source_requests={'state':{'source_scope':'observed','record_kinds':['interface_state']}}))

def test_authorized_reader_ids_survive_first_projection(scoped_environment):
    context,evidence,_=read_material(scoped_environment[0])
    actual=context[0]['data']['records']
    assert {r['id'] for r in actual}=={'port-7031','model-interface-7031'}
    facts=interface_observations(context,QUESTION,evidence)
    assert {f.get('record_id') for f in facts}=={r['id'] for r in actual}
    for fact,row in zip(facts,actual):
        assert (fact['device_id'],fact['interface_id'],fact['source'])==(row['device_id'],row['interface_id'],row['source'])
        assert fact['origin']=='simulated' and fact['source_scope']=='observed'

def test_omitted_ids_are_delivered_by_final_source_projection(scoped_environment):
    context,evidence,_=read_material(scoped_environment[0])
    class Model:
        async def generate(self,messages,**kwargs):
            # Reproduce the previous correct state answer that omitted IDs.
            return json.dumps({'answer':'Meadow Ethernet9/3: administrative state up; operational state up.',
                               'sources':['S1'],'hypotheses':[]}),'local-test'
    answer,trace=asyncio.run(synthesize(Model(),'local-test',QUESTION,context,evidence,{},'fallback'))
    assert 'port-7031' in answer and 'model-interface-7031' in answer
    assert 'authored-synthetic-observer' in answer and 'declared_interface_observation' in answer
    assert trace['display_source_record_ids_added'] is True

@pytest.mark.parametrize('surface',['floating','studio'])
def test_source_ids_and_distinct_provenance_reach_synthesis_input(scoped_environment,surface):
    context,evidence,_=read_material(scoped_environment[0],surface)
    class Model:
        async def generate(self,messages,**kwargs):
            packet=messages[-1]['content']
            for row in context[0]['data']['records']:
                assert row['id'] in packet and row['source'] in packet
            assert '"device_id": 703' in packet and '"interface_id": 7031' in packet
            # Existing output schema and model controls are unchanged.
            assert set(kwargs['structured']['properties'])=={'answer','sources','hypotheses'}
            return json.dumps({'answer':'The recorded interface is Meadow Ethernet9/3; administrative state up and operational state up. Recorded at 2026-10-26T14:00:00Z.',
                               'sources':['S1'],'hypotheses':[]}),'local-test'
    answer,trace=asyncio.run(synthesize(Model(),'local-test',QUESTION,context,evidence,{},'fallback'))
    section=answer.split('**Source record identities — returned facts**')[1]
    assert len(section.strip().splitlines())==2
    assert 'Authored/recorded observation' in section and 'Modeled observation' in section
    assert 'Ethernet2/2' not in section and 'Loopback0' not in section
    for row in context[0]['data']['records']:
        line=next(x for x in section.splitlines() if '`'+row['id']+'`' in x)
        assert row['source'] in line and row['interface'] in line and row['timestamp'] in line

def material(rows):
    return [{'tool':'network.state','status':'success','evidence_ids':['citation'],
        'source_request':{'source_scope':'observed','record_kinds':['interface_state']},
        'reader_receipt':{'invocation_id':'PRIVATE_INVOCATION_ONLY','parameters':{'credential':'PRIVATE_PARAMETER'}},
        'data':{'scenario':{'id':'test-scenario','source_revision':'revision-one','origin':'simulated'},'records':rows}}], [Evidence(id='citation',source='State reader',origin='simulated')]

def row(**updates):
    return dict({'id':'Observed#A:Case.7','kind':'interface_state','device_id':84,'interface_id':8401,
        'hostname':'North','interface':'xe-0/0/7','admin_status':'up','oper_status':'down',
        'timestamp':'2026-10-31T20:00:00Z','current':True,'source':'authored-collector'},**updates)

def test_exact_duplicates_only_are_deduplicated():
    original=row()
    variants=[row(id='Model#A:Case.7',source='declared_interface_observation',source_category='simulation'),
              row(source='second-collector'),row(timestamp='2026-10-31T20:01:00Z'),row(oper_status='up')]
    context,evidence=material([original,copy.deepcopy(original),*variants])
    facts=interface_observations(context,'Show interface state and record identities.',evidence)
    assert len(facts)==5
    assert [f['record_id'] for f in facts]==[r['id'] for r in [original,*variants]]
    assert [f['oper_status'] for f in facts]==['down','down','down','down','up']

def test_same_named_ports_keep_device_and_record_ownership():
    from llm.orchestration.synthesis import interface_record_identity_section
    context,evidence=material([row(),row(id='South::Obs/9',device_id=94,interface_id=9401,hostname='South',admin_status='down')])
    facts=interface_observations(context,'Read interface state with record identifiers.',evidence)
    lines=interface_record_identity_section(facts).splitlines()
    north=next(x for x in lines if 'Observed#A:Case.7' in x);south=next(x for x in lines if 'South::Obs/9' in x)
    assert 'North' in north and 'device ID `84`' in north and 'interface ID `8401`' in north
    assert 'South' in south and 'device ID `94`' in south and 'interface ID `9401`' in south
    assert 'admin `up`' in north and 'admin `down`' in south

def test_existing_nested_source_envelopes_keep_their_own_origin_and_citation():
    from llm.orchestration.synthesis import interface_record_identity_section
    first=row();first.pop('source')
    second=row(id='Other-origin',oper_status='up');second.pop('source')
    context,evidence=material([])
    evidence.append(Evidence(id='stored-citation',source='Stored collector',origin='stored'))
    context[0]['data']={'sources':[
        {'status':'success','origin':'simulated','source':'authored-recorder','evidence_ids':['citation'],'data':{'records':[first]}},
        {'status':'success','origin':'stored','source':'historical-recorder','evidence_ids':['stored-citation'],'data':{'records':[second]}},
        {'status':'unavailable','origin':'simulated','source':'failed-recorder','data':{'records':[row(id='DO_NOT_REUSE_FAILED_RECORD')]}}]}
    facts=interface_observations(context,'Read interface state with source record IDs.',evidence)
    assert len(facts)==2
    assert (facts[0]['origin'],facts[0]['source'],facts[0]['sources'])==('simulated','authored-recorder',['S1'])
    assert (facts[1]['origin'],facts[1]['source'],facts[1]['sources'])==('stored','historical-recorder',['S2'])
    text=interface_record_identity_section(facts)
    assert 'Other-origin' in text and 'DO_NOT_REUSE_FAILED_RECORD' not in text

def test_different_ports_and_history_do_not_merge():
    context,evidence=material([row(),row(id='Historic/1',current=False,timestamp='2026-10-30T20:00:00Z'),
                               row(id='Other-port',interface_id=8402,interface='xe-0/0/8')])
    facts=interface_observations(context,'Show interface state and source record IDs.',evidence)
    assert len(facts)==3 and facts[1]['current'] is False and facts[2]['interface_id']==8402
    assert facts[0]['source_revision']=='revision-one'

def test_explicit_identity_request_does_not_silently_discard_ninth_record():
    context,evidence=material([row(id='obs-'+str(i),timestamp=f'2026-10-31T20:{i:02d}:00Z') for i in range(12)])
    assert len(interface_observations(context,'Show interface state and record IDs.',evidence))==12
    assert len(interface_observations(context,'Show interface state.',evidence))==8

@pytest.mark.parametrize('record_id',[None,'MixedCase/Observed:7.04','record`quoted`'])
def test_missing_and_exact_spelling_ids_never_use_citation_or_private_receipt(record_id):
    from llm.orchestration.synthesis import interface_record_identity_section
    context,evidence=material([row(id=record_id)])
    facts=interface_observations(context,'Show state and observation identities.',evidence)
    text=interface_record_identity_section(facts)
    assert ('ID not recorded' in text) if record_id is None else record_id in text
    assert 'PRIVATE_INVOCATION_ONLY' not in text and 'PRIVATE_PARAMETER' not in text
    assert 'citation' not in text and '[S1]' in text

@pytest.mark.parametrize('question',[
    'Show the interface state.', 'Show the interface state without record IDs.',
    'Show the interface state; do not include source record identifiers.',
])
def test_non_requested_identity_preserves_concise_model_input_and_response(question):
    context,evidence=material([row()])
    class Model:
        async def generate(self,messages,**kwargs):
            packet=messages[-1]['content']
            assert 'Observed#A:Case.7' not in packet and 'PRIVATE_INVOCATION_ONLY' not in packet
            return json.dumps({'answer':'North xe-0/0/7: administrative state up; operational state down; recorded 2026-10-31T20:00:00Z.',
                               'sources':['S1'],'hypotheses':[]}),'local-test'
    answer,trace=asyncio.run(synthesize(Model(),'local-test',question,context,evidence,{},'fallback'))
    assert 'Source record identities' not in answer and 'Observed#A:Case.7' not in answer
    assert not trace.get('display_source_record_ids_added')
    assert trace['status']=='literal_checks_passed'

def test_correct_model_explanation_is_preserved_beside_exact_identity_fields():
    context,evidence=material([row()])
    correct='North xe-0/0/7 has administrative state up and operational state down, recorded at 2026-10-31T20:00:00Z. This observation alone does not establish a physical cause. [S1]'
    class Model:
        async def generate(self,*args,**kwargs):
            return json.dumps({'answer':correct,'sources':['S1'],'hypotheses':[]}),'local-test'
    answer,trace=asyncio.run(synthesize(Model(),'local-test','Show interface state with source record IDs.',context,evidence,{},'fallback'))
    assert correct in answer and trace['status']=='literal_checks_passed'
    assert 'Observed#A:Case.7' in answer and trace['display_source_record_ids_added']

def test_unavailable_identity_is_disclosed_without_invented_records():
    context,evidence=material([]);context[0].update(status='unavailable',data=None)
    class NoModel:
        async def generate(self,*args,**kwargs):raise AssertionError('Unavailable facts cannot authorize invented states')
    answer,trace=asyncio.run(synthesize(NoModel(),'local-test','Show interface state and source record IDs.',context,evidence,{},'The state reader is unavailable.'))
    assert 'Source record identities' in answer and 'unavailable' in answer
    assert 'PRIVATE_INVOCATION_ONLY' not in answer

@pytest.mark.parametrize('target,interface',[('701','7031'),('703','7011')])
def test_wrong_device_ownership_never_reaches_identity_projection(scoped_environment,target,interface):
    db,_=scoped_environment
    auth=ToolAuthorization('record-id-owner','engineer','floating','owned',frozenset({'network.state'}))
    result=asyncio.run(registry_for(db).invoke('network.state',{'device_refs':[target],'interface_refs':[interface]},auth))
    assert result.status=='unavailable' and not result.data

def test_denied_source_stays_denied(scoped_environment):
    db,_=scoped_environment
    auth=ToolAuthorization('record-id-owner','engineer','floating','owned',frozenset({'inventory.read'}))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(registry_for(db).invoke('network.state',{'device_refs':['703'],'interface_refs':['7031']},auth))
    assert exc.value.status_code==403

def test_no_read_advice_does_not_turn_record_ids_into_observations():
    from llm.orchestration.request_contract import advisory_contract
    contract=advisory_contract('Recommend which interface state record IDs to request next. Do not read, collect, or change anything.')
    assert contract and contract.advice_only
    class Model:
        async def generate(self,*args,**kwargs):
            return json.dumps({'checks':[{'reader':'network.state','question':'Which timestamped interface observations and source record IDs are available?',
               'rationale':'Those future records could distinguish modeled and authored observations.'}]}),'local-test'
    answer,trace=asyncio.run(synthesize(Model(),'local-test',contract.original_request,[],[],{},'fallback',requested_outcomes=contract,
                                      advisory_context={'authorized_readers':['network.state']}))
    assert trace['status']=='advisory_proposed' and 'Source record identities' not in answer
