"""Source identity and requested attributes survive before any model call."""
import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from llm.gateway_network import route_network
from llm.gateway_references import resolve_read, attributes
from llm.gateway_documents import file_context_requested
from llm.gateway_findings import inventory_answer


def inventory():
    return {'devices': [
        {'id': 31, 'hostname': 'Maple-Edge', 'management_ip': '192.0.2.31', 'interfaces': [
            {'id': 1, 'name': 'eth0', 'ip_address': '10.31.0.1', 'prefix': '10.31.0.1/30'},
            {'id': 2, 'name': 'lo0', 'ip_address': '198.51.100.31', 'prefix': '198.51.100.31/32'}]},
        {'id': 32, 'hostname': 'Pine-Exit', 'management_ip': '192.0.2.32', 'interfaces': []}]}


def test_composite_path_entities_are_bound_without_matching_unknown_name_suffixes():
    inv=inventory()
    _, query=route_network('Compare Maple-Edge-Pine-Exit planned links and recorded forwarding.', inv)
    assert query['device_refs']==['Maple-Edge','Pine-Exit']
    _, query=route_network('Inspect Maple-Edge-backup.', inv)
    assert not query.get('device_refs')
    _, query=route_network('Compare Maple-Edge-Pine-Exit-backup.', inv)
    assert not query.get('device_refs')


def test_explicit_paired_network_source_request_enters_the_existing_planner(monkeypatch):
    from llm.gateway_routing import select_context
    monkeypatch.setenv('COGNISHIELD_AI_PLANNING','1')
    inv=inventory()
    generate=AsyncMock(return_value=('{"intent":"explain","information_needs":[{"domain":"topology","question":"planned links","source_scope":"planned"},{"domain":"state","question":"recorded forwarding"}]}','fake'))
    with patch('llm.gateway_semantics.semantic_hint',AsyncMock(return_value=None)), patch('llm.orchestration.planning.select_logical_sources', side_effect=lambda p, plan, *a: _ready(plan)):
        route=asyncio.run(select_context('Compare Maple-Edge-Pine-Exit planned links and recorded forwarding.',None,'floating',None,[],[],inventory=inv,generate_fn=generate))
    assert set(route.network_domains)=={'topology','state'}
    assert set(route.device_refs)=={'31','32'}
    assert route.planning['mode']=='validated_model_plan'


async def _ready(plan):
    return plan, {}


def test_quantified_owned_documents_bind_but_ambient_drafts_do_not():
    docs=[{'id':'a','name':'design-a.md'},{'id':'b','name':'design-b.md'}]
    assert file_context_requested('Read both design drafts and explain their disagreement.',docs)
    assert not file_context_requested('Explain the general meaning of design drafts.',docs)
    assert not file_context_requested('With both drafts available, explain integer division.',docs)


def test_non_network_possessive_does_not_create_an_unresolved_device():
    assert resolve_read('Explain integer division and its result.',None,inventory()) is None
    assert resolve_read('What is its IP address?',None,inventory()).get('question')
    assert resolve_read('What about that interface?',None,inventory()).get('question')


def test_broad_address_fallback_preserves_interface_values_and_management_role():
    data=inventory();text=inventory_answer(data,attributes('Report all routed IPs and the management endpoint.'))
    for value in ['10.31.0.1','198.51.100.31','192.0.2.31','eth0','lo0']:
        assert value in text
    assert 'distinct' in text
    management=inventory_answer(data,attributes('Report the management IP address.'))
    assert '192.0.2.31' in management
    assert '10.31.0.1' not in management
    selected=inventory_answer(data,['addresses'],['1'])
    assert '10.31.0.1' in selected and '192.0.2.31' not in selected


def test_response_style_does_not_change_attribute_source_ownership(monkeypatch):
    from llm.gateway_routing import select_context
    monkeypatch.setenv('COGNISHIELD_AI_PLANNING','1')
    generate=AsyncMock(side_effect=AssertionError('Exact reader ownership does not require a model decision'))
    route=asyncio.run(select_context('Report all routed IPs for Maple-Edge and explain how its management endpoint differs.',
        None,'floating',None,[],[],inventory=inventory(),generate_fn=generate))
    assert route.network_domains==['inventory'] and route.intent=='explain'
    assert {'interfaces','addresses','management_address'} <= set(route.attributes)
    generate.assert_not_called()


def test_explicit_scope_overrides_model_guess_without_discarding_compound_needs():
    from llm.orchestration.planning import propose
    generate=AsyncMock(return_value=('{"intent":"explain","information_needs":[{"domain":"topology","question":"intended links","source_scope":"observed"},{"domain":"state","question":"recorded forwarding"}]}','fake'))
    route=asyncio.run(propose('Use planned links and recorded forwarding to compare Maple-Edge-Pine-Exit.',
        None,'floating',None,[],[],inventory(),generate,read_only_request=True))
    assert set(route.network_domains)=={'topology','state'}
    assert route.source_requests['topology']['source_scope']=='planned'
    assert route.planning['source_scope_adjustments']==[{'domain':'topology','proposed':'observed','required':'planned'}]


def test_invalid_plan_cannot_erase_resolved_compound_read(monkeypatch):
    from llm.gateway_routing import select_context
    monkeypatch.setenv('COGNISHIELD_AI_PLANNING','1')
    with patch('llm.orchestration.planning.propose',AsyncMock(side_effect=ValueError('Malformed model plan'))):
        route=asyncio.run(select_context('Use planned links and recorded forwarding to compare Maple-Edge-Pine-Exit.',
            None,'floating',None,[],[],inventory=inventory(),generate_fn=AsyncMock(side_effect=AssertionError('No second weaker classifier'))))
    assert set(route.network_domains)=={'topology','state'} and route.device_refs


def test_assessment_duplication_does_not_evict_requested_interface_evidence():
    from llm.orchestration.synthesis import projection
    from llm.gateway_models import Evidence
    rows=[{'kind':'protocol_assessment','protocol':protocol,'hostname':'Maple-Edge','timestamp':'2026-10-24T00:00:00Z',
        'observed_state':'Full' if protocol=='OSPF' else 'Established','configuration_differences':[],
        'unknown_prerequisites':[],'peer_parameters':[{'device_id':31,'hostname':'Maple-Edge','router_id':'192.0.2.31'},
            {'device_id':32,'hostname':'Pine-Exit','router_id':'192.0.2.32'}],'unused_description':'x'*2900}
        for protocol in ['OSPF','BGP']]
    rows.extend({'kind':'interface_state','hostname':'Maple-Edge','interface':name,'admin_status':admin,
        'oper_status':oper,'timestamp':'2026-10-24T00:00:00Z'}
        for name,admin,oper in [('eth0','up','down'),('eth1','down','down')])
    context=[{'tool':'network.state','status':'success','evidence_ids':['e'],'data':{'records':rows}}]
    packet=projection(context,[Evidence(id='e',source='state',origin='simulated')],{},
        'List administrative and operational observations and explain the recorded protocol relationships.')
    actual=packet['records'][0]['data']['records']
    assert {r['interface'] for r in actual if r['kind']=='interface_state'}=={'eth0','eth1'}
    assert len(packet['protocol_results'])==4  # two owned directions per protocol
    assert all(r['details_projected_as']=='protocol_results' for r in actual if r['kind']=='protocol_assessment')


def test_role_names_from_typed_hops_survive_transit_only_scope():
    from llm.orchestration.synthesis import record_device_names
    context=[{'tool':'network.state','status':'success','scope_devices':[{'id':99,'hostname':'Transit'}],
        'data':{'records':[{'device_id':31,'hostname':'Maple-Edge','kind':'forwarding_assessment',
            'assessment':{'return':{'branches':[{'hops':[{'device_id':32,'hostname':'Pine-Exit'}]}]}}},
            {'kind':'protocol_assessment','assessment':'healthy_within_tested_scope','peer_parameters':[]}]}}]
    assert record_device_names(context)=={'99':'Transit','31':'Maple-Edge','32':'Pine-Exit'}


def test_one_nonempty_clause_cannot_hide_an_unfinished_other_clause():
    import json
    import pytest
    from llm.orchestration.request_contract import response_obligations, assemble_response
    from llm.orchestration.synthesis import AnswerDraft
    obligations=response_obligations('List the interface states and explain the blocking port.')
    responses=[{'id':'request-1','answer':'The observations are as follows:','sources':['S1']},
        {'id':'request-2','answer':'Port eth1 is recorded down and blocks egress.','sources':['S1']}]
    with pytest.raises(ValueError,match='unfinished'):assemble_response(json.dumps({'responses':responses}),obligations,AnswerDraft)
    responses[0]['answer']='The observations are as follows: eth0 is up; eth1 is down.'
    assert assemble_response(json.dumps({'responses':responses}),obligations,AnswerDraft)[0].answer


def test_inventory_role_does_not_certify_routing_or_management_reachability():
    from llm.orchestration.record_relationships import record_relationship_errors
    context=[{'tool':'inventory.read','status':'success','data':inventory()}]
    assert record_relationship_errors('The recorded addresses are part of the routing table.',context,'Explain addresses.')
    assert record_relationship_errors('The management endpoint is used for management rather than a routable IP address.',context,'Explain addresses.')
    assert not record_relationship_errors('These are recorded interface addresses. A management endpoint identifies management purpose; its reachability is not established.',context,'Explain addresses.')
    assert not record_relationship_errors('A recorded interface address is not necessarily installed in the routing table.',context,'Explain addresses.')


def test_reference_to_aggregate_trace_does_not_force_a_singular_entity():
    previous={'context_coverage':{'retrieval':{'domains':['state'],'device_refs':['31','32'],
        'attributes':[],'entities':[{'device_id':'31'},{'device_id':'32'}]}}}
    resolved=resolve_read('Which interface observation explains that trace?',previous,inventory())
    assert not resolved.get('question') and set(resolved['device_refs'])=={'31','32'}
    assert 'state' in resolved['domains']
    assert resolve_read('What is its IP address?',previous,inventory()).get('question')


def test_prohibited_collection_does_not_erase_owned_investigation_reference():
    from llm.gateway_references import read_intent_text
    previous={'context_coverage':{'retrieval':{'domains':['state'],'device_refs':['31'],
        'entities':[],'attributes':[]}}}
    prompt='Which evidence should I inspect next for that uncertainty? Never collect data or change a configuration.'
    normalized=read_intent_text(prompt)
    resolved=resolve_read(normalized,previous,inventory())
    assert resolved['device_refs']==['31'] and resolved['use_history']
    assert 'Which evidence' in normalized


def test_latest_modifier_does_not_discard_a_comparison_operand():
    _, query=route_network('Compare Maple-Edge latest saved configuration with its current configuration.',inventory())
    assert query.get('limit',20)>=2
    _, query=route_network('Show Maple-Edge latest saved configuration.',inventory())
    assert query['limit']==1


def test_semantically_selected_reader_materializes_all_temporal_operands():
    from llm.gateway_network import network_context
    from llm.gateway_models import ToolResult
    registry=type('Registry',(),{'invoke':AsyncMock(return_value=ToolResult(status='success',data={'records':[]}))})()
    with patch('llm.gateway_services.inventory_snapshot',return_value=inventory()):
        asyncio.run(network_context(None,registry,None,
            'Compare Maple-Edge latest saved text with current simulated text.',
            domains_override=['configuration'],source_requests={'configuration':{'source_scope':'both'}}))
    assert registry.invoke.call_args.args[1].get('limit',20)>=2


def test_owned_attachment_qualifier_is_not_restricted_to_a_noun_dictionary():
    docs=[{'id':'a','name':'design-a.md'},{'id':'b','name':'design-b.md'}]
    assert file_context_requested('Compare both attached proposals.',docs)
    assert file_context_requested('Read the uploaded briefing and explain its limits.',docs)
    assert not file_context_requested('With the attached briefing available, explain integer division.',docs)


def test_registered_source_refinement_precedes_hint_based_domain_validation():
    from llm.orchestration.planning import propose
    inv=inventory();inv['logical_source_categories']=['topology_planned','incidents']
    generate=AsyncMock(side_effect=[
        ('{"intent":"explain","information_needs":[{"domain":"incidents","question":"planned links incident to Maple-Edge"}]}','fake'),
        ('{"need_sources":[{"need_index":0,"source_categories":["topology_planned"],"reader":"topology"}]}','fake')])
    route=asyncio.run(propose('Read planned topology links incident to Maple-Edge.',None,'floating',None,[],[],inv,generate,read_only_request=True))
    assert route.network_domains==['topology']
    assert route.source_requests['topology']['source_categories']==['topology_planned']


def test_unique_explicit_source_owns_ordinary_reader_without_scenario_filters():
    from llm.orchestration.planning import propose
    generate=AsyncMock(return_value=('{"intent":"explain","information_needs":[{"domain":"incidents","question":"links incident to Maple-Edge","source_scope":"planned"}]}','fake'))
    route=asyncio.run(propose('Describe intended links incident to Maple-Edge.',None,'floating',None,[],[],inventory(),generate,read_only_request=True))
    assert route.network_domains==['topology'] and generate.await_count==1
    assert route.source_requests['topology'].get('source_categories',[])==[]


def test_sampling_cadence_does_not_establish_a_reset_schedule_or_mechanism():
    from llm.orchestration.metric_evidence import metric_calculation_claim_errors
    facts=[{'device':'Maple-Edge','interface':'eth0','metric':'discards','unit':'count',
        'samples':[{'value':2300},{'value':9},{'value':13}],
        'calculations':{'counter_reset_or_wrap':True,'sampling_seconds':45}}]
    assert metric_calculation_claim_errors('The counter resets every 45 seconds when it reaches a threshold and resets to zero.',facts)
    assert not metric_calculation_claim_errors('The counter drops from2300 to9 and later rises to13. A reset or wrap is possible; no schedule or mechanism is established.',facts)


def test_matching_captures_cannot_establish_interval_even_with_later_disclaimer():
    from llm.gateway_models import Evidence
    from llm.orchestration.synthesis import synthesize, check_candidate
    context=[{'tool':'network.configuration','status':'success','evidence_ids':['c'],'data':{'records':[
        {'hostname':'Maple-Edge','kind':'running_configuration','current':True,'timestamp':'2026-10-24T02:00:00Z','config_text':'hostname Maple-Edge\n'},
        {'hostname':'Maple-Edge','kind':'configuration_snapshot','current':False,'timestamp':'2026-10-24T01:00:00Z','config_text':'hostname Maple-Edge\n'}]}}]
    bad='No changes have been made to the configuration since the last saved snapshot. This does not establish intervening state.'
    assert check_candidate(bad,context,[],{},'Compare these records.')
    model=type('Model',(),{'generate':AsyncMock(side_effect=AssertionError('No inference can fill an unobserved interval'))})()
    text,trace=asyncio.run(synthesize(model,None,'Compare these records and explain the interval.',context,
        [Evidence(id='c',source='captures',origin='stored')],{},'raw fallback'))
    assert trace['status']=='capture_interval_scope_fallback' and not trace['model_synthesis']
    assert '01:00:00' in text and '02:00:00' in text and 'does not establish' in text
