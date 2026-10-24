"""Returned evidence, validation and formatting must share source scope."""
import asyncio,json,sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm.gateway_models import Evidence
from llm.orchestration.synthesis import projection,synthesize,check_candidate
from llm.orchestration.planning import additional_reads


def flow_context():
    return [{'tool':'network.state','status':'success','evidence_ids':['f'],
        'scope_devices':[{'id':1,'hostname':'Birch'},{'id':3,'hostname':'Cedar'}],
        'data':{'records':[{'kind':'forwarding_assessment','flow':{'source_device_id':1,'destination_device_id':3,
            'source_address':'192.0.2.1','destination_address':'192.0.2.3','vrf':'default'},
            'assessment':{'status':'partial','forward':{'status':'delivered','branches':[{'status':'delivered','reason':'destination reached',
                'hops':[{'hostname':'Birch','interface':'port-a'},{'hostname':'Maple','interface':'port-b'}]}]},
                'return':{'status':'failed','branches':[{'status':'failed','reason':'no route','hops':[]}]}}},
            {'kind':'interface_state','hostname':'Birch','interface':'port-a','prefix':'10.2.0.1/30','admin_status':'up','oper_status':'down'}]}}]


def test_typed_flow_and_other_state_facts_survive_unfamiliar_question_wording():
    context=flow_context();evidence=[Evidence(id='f',source='recorded',origin='simulated')]
    packet=projection(context,evidence,{},'Read the recorded two-way delivery observations.')
    assert packet['forwarding_results'][0]['return']['status']=='failed'
    assert packet['forwarding_results'][0]['destination_device']=='Cedar'
    assert any(row.get('kind')=='interface_state' for row in packet['records'][0]['data']['records'])
    assert '10.2.0.1/30' in json.dumps(packet)


def test_actual_directional_constraints_apply_even_without_a_flow_prompt_keyword():
    errors=check_candidate('The forward path is Cedar to Birch; the return path is delivered.',flow_context(),[],{},'Explain the records.')
    assert errors


def test_protocol_roles_and_reciprocal_checks_are_available_without_a_protocol_keyword():
    context=[{'tool':'network.state','status':'success','evidence_ids':['p'],'scope_devices':[],
        'data':{'records':[{'kind':'protocol_assessment','protocol':'BGP','observed_state':'Active','peer_parameters':[
            {'device_id':1,'hostname':'Birch','local_as':64520,'remote_as':64530},
            {'device_id':2,'hostname':'Cedar','local_as':64530,'remote_as':64599}]}]}}]
    facts=projection(context,[Evidence(id='p',source='peers',origin='stored')],{},'Explain those recorded roles.')['protocol_results']
    assert facts[0]['reciprocal_as_check']=={'configured_remote_as':64530,'expected_peer_local_as':64530,'matches':True}
    assert facts[1]['reciprocal_as_check']['matches'] is False
    assert facts[1]['neighbor']['local_as']==64520


def test_adaptive_planner_sees_structural_results_not_a_false_empty_reader():
    model=AsyncMock(return_value=('{"information_needs":[{"domain":"state","question":"Scoped observations"}],"reason":"Read the missing operational evidence"}','mock'))
    context=[{'tool':'network.topology','status':'success','data':{'nodes':[{'id':1},{'id':2}],
        'links':[{'id':7}], 'graph_path':['Birch','Cedar'],'PRIVATE_TEXT':'DO_NOT_SEND'}}]
    asyncio.run(additional_reads('Assess the available relationship.', ['state'],{'gaps':['Scoped observations missing']},context,None,model))
    packet=json.loads(model.call_args.args[0][-1]['content'])
    assert packet['reads'][0]['payload_shapes']=={'nodes':2,'links':1,'graph_path':2}
    assert packet['reads'][0]['reader_succeeded'] is True
    assert 'DO_NOT_SEND' not in str(packet)


def test_mixed_published_source_keeps_config_and_validates_requiredness():
    context=[{'tool':'knowledge.search','status':'success','evidence_ids':['k'],'data':[{
        'evidence_id':'k','published_requirements':{'operations':[{'operation_id':'reviewed_method','description':'Reviewed OSPF inputs',
            'schema':{'required':['interfaces'],'properties':{'interfaces':{'type':'array'},'process_id':{'type':'integer'}},
                'x-required-by-vendor':{'cisco':['process_id']}},'profiles':[{'vendor':'juniper','platform':'junos','versions':['1']}]}]}}]},
        {'tool':'network.configuration','status':'success','evidence_ids':['c'],'data':{'records':[
            {'hostname':'Birch','config_text':'set protocols ospf area 0 interface port-a\n! MIXED_CAPTURE_WITNESS'}]}}]
    evidence=[Evidence(id='k',source='published',origin='stored'),Evidence(id='c',source='capture',origin='stored')]
    model=SimpleNamespace(generate=AsyncMock(return_value=(json.dumps({'answer':'The published method always requires process_id. [S1] The capture has OSPF. [S2]',
        'sources':['S1','S2'],'operation_ids':['reviewed_method']}),'mock')),available=lambda purpose:False)
    _,trace=asyncio.run(synthesize(model,None,'Compare published requirements with the saved source.',context,evidence,{},'all source fallback'))
    assert trace['status']=='rejected_fallback'
    assert any('unconditionally required' in error for attempt in trace['attempts'] for error in attempt['errors'])
    assert 'MIXED_CAPTURE_WITNESS' in model.generate.call_args.args[0][-1]['content']


def test_topology_only_investigation_cannot_release_a_directional_diagnosis():
    context=[{'tool':'network.topology','status':'success','evidence_ids':['t'],'data':{'links':[
        {'source':'Birch','source_interface':'port-a','target':'Cedar','target_interface':'port-b'}]}}]
    model=SimpleNamespace(generate=AsyncMock())
    answer,trace=asyncio.run(synthesize(model,None,'Assess the connection.',context,[Evidence(id='t',source='plan',origin='stored')],{},'fallback',investigation=True))
    assert not model.generate.called and trace['status']=='insufficient_operational_scope_fallback'
    assert 'Birch' in answer and 'port-a' in answer and 'Cedar' in answer and 'port-b' in answer
    assert 'does not establish' in answer or 'do not establish' in answer


def test_conflicted_protocol_causal_prose_is_withheld_independently_of_prompt_wording():
    context=[{'tool':'network.state','status':'success','evidence_ids':['p'],'scope_devices':[],
        'data':{'records':[{'kind':'protocol_assessment','protocol':'BGP','observed_state':'Active',
            'peer_parameters':[{'device_id':1,'hostname':'Birch','local_as':64520,'remote_as':64530},
                {'device_id':2,'hostname':'Cedar','local_as':64530,'remote_as':64599}]}]}},
        {'tool':'network.configuration','status':'success','evidence_ids':['c'],
            'data':{'records':[{'config_text':'SOURCE_CONFIG_WITNESS'}]}}]
    model=SimpleNamespace(generate=AsyncMock(side_effect=AssertionError('Unsupported causal class must not invoke a model')))
    answer,trace=asyncio.run(synthesize(model,None,'Would another working prerequisite settle that?',context,
        [Evidence(id='p',source='recorded peers',origin='simulated')],{},'SOURCE_CONFIG_WITNESS'))
    assert trace['status']=='protocol_constraints_fallback' and not trace['model_synthesis']
    assert not model.generate.called and 'SOURCE_CONFIG_WITNESS' in answer
    assert all(value in answer for value in ['Birch','Cedar','64520','64530','64599','Active','[S1]'])
    assert 'does not match peer local AS' in answer or 'does not match' in answer
    assert 'does not establish that separate protocol prerequisites match' in answer


def test_conflicting_ospf_records_use_the_same_typed_safety_boundary():
    from llm.orchestration.synthesis import protocol_constraint_summary,protocol_observations
    context=[{'tool':'network.state','status':'success','evidence_ids':['p'],'data':{'records':[
        {'kind':'protocol_assessment','protocol':'OSPF','observed_state':'Full','conflict':True,
            'configuration_differences':['hello_seconds mismatch'],'timestamp':'2026-10-23T01:00:00Z',
            'unknown_prerequisites':['authentication'],'peer_parameters':[
                {'device_id':1,'hostname':'Birch','hello_seconds':10},
                {'device_id':2,'hostname':'Cedar','hello_seconds':20}]}]}}]
    facts=protocol_observations(context,'',{'p':'S1'},focus=False)
    answer=protocol_constraint_summary(facts)
    assert all(value in answer for value in ['Full','10','20','authentication','2026-10-23T01:00:00Z'])
    assert 'a cause is not confirmed' in answer
    for fact in facts:fact.update(conflict=False,configuration_differences=[])
    assert protocol_constraint_summary(facts)==''


def test_auxiliary_model_reader_does_not_become_an_extra_user_citation_requirement():
    context=[{'tool':'network.configuration','status':'success','evidence_ids':['c'],
        'data':{'records':[{'hostname':'Birch','config_text':'hostname Birch\n'}]}},
        {'tool':'inventory.read','status':'success','evidence_ids':['i'],
            'data':{'devices':[{'id':1,'hostname':'Birch','vendor':'cisco'}]}}]
    evidence=[Evidence(id='c',source='saved',origin='stored'),Evidence(id='i',source='inventory',origin='stored')]
    model=SimpleNamespace(generate=AsyncMock(return_value=(json.dumps({
        'answer':'The saved text names the router Birch. [S1]','sources':['S1']}),'mock')),
        available=lambda purpose:False)
    answer,trace=asyncio.run(synthesize(model,None,'Explain the saved name.',context,evidence,{},'fallback',
        objectives=[{'domain':'configuration','question':'Explain the saved name'},
            {'domain':'inventory','question':'Supporting device identity'}],required_readers={'network.configuration'}))
    assert trace['status']=='literal_checks_passed' and 'saved text names the router Birch' in answer
    packet=model.generate.call_args.args[0][-1]['content']
    assert 'Supporting device identity' in packet and 'reader_citation_required' in packet
