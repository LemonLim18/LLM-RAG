"""Independent source-scope oracles; observations must not leak into plans."""
from copy import deepcopy
import asyncio
import json
import os
from pathlib import Path
import sys
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db.manager import DatabaseManager
from llm.gateway_network import NetworkQuery, NetworkReader
from llm.gateway_services import inventory_snapshot
from llm.tools import ToolAuthorization
from local_providers.development import ScenarioManager


def test_saved_protocol_settings_are_configuration_evidence_in_compound_reads():
    from llm.gateway_routing import select_context
    from llm.gateway_network import route_network
    inventory={'devices':[{'id':51,'hostname':'Spruce-Edge','aliases':[],'interfaces':[]}]}
    prompt='Compare Spruce-Edge’s saved BGP settings with its observed peers and recent log messages.'
    assert set(route_network(prompt,inventory)[0])=={'configuration','state','syslog'}
    wrong={'intent':'explain','information_needs':[
        {'domain':'state','question':'saved BGP settings','source_scope':'historical'},
        {'domain':'state','question':'observed peers'},{'domain':'syslog','question':'recent log messages'}]}
    generate=AsyncMock(return_value=(json.dumps(wrong),'test'))
    with patch.dict(os.environ,{'COGNISHIELD_AI_PLANNING':'1'}):
        route=asyncio.run(select_context(prompt,'test','floating',None,[],[],inventory=inventory,generate_fn=generate))
    assert set(route.network_domains)=={'configuration','state','syslog'}
    assert route.planning['mode']=='model_plan_invalid_fallback'
    assert route_network('Which current BGP peers are recorded for Spruce-Edge?',inventory)[0]==['state']


def test_explicit_investigation_source_list_bounds_the_initial_model_plan():
    from llm.gateway_network import route_network
    from llm.gateway_routing import select_context
    inventory={'devices':[{'id':51,'hostname':'Spruce-Edge','aliases':[],'interfaces':[]},
        {'id':52,'hostname':'Birch-Core','aliases':[],'interfaces':[]}]}
    prompt='Investigate Spruce-Edge to Birch-Core using topology, routes and reachability observations.'
    wrong={'intent':'explain','information_needs':[{'domain':'topology','question':'recorded path'},
        {'domain':'state','question':'route tables'},{'domain':'telemetry','question':'measured traffic'}]}
    generate=AsyncMock(return_value=(json.dumps(wrong),'test'))
    with patch.dict(os.environ,{'COGNISHIELD_AI_PLANNING':'1'}):
        domains,_=route_network(prompt,inventory)
        assert set(domains)=={'topology','state'}
        route=asyncio.run(select_context(prompt,'test','floating',None,[],[],inventory=inventory,generate_fn=generate))
    assert set(route.network_domains)=={'topology','state'}
    assert route.planning['mode']=='model_plan_invalid_fallback'
    assert 'telemetry' in route_network('Investigate Spruce-Edge using all available information.',inventory)[0]


def test_named_saved_section_is_a_configuration_read_not_generation():
    from llm.gateway_references import configuration_text_request,resolve_read
    from llm.gateway_routing import select_context
    inventory={'devices':[{'id':1,'hostname':'Pine-Lab','management_ip':'192.0.2.4','aliases':[],'interfaces':[]}]}
    prompt='Quote the saved ACL section for Pine-Lab.'
    assert configuration_text_request(prompt)
    refs=resolve_read(prompt,None,inventory)
    assert refs and refs['domains']==['configuration']
    generator=AsyncMock(return_value=(json.dumps({'intent':'generate_native','information_needs':[]}), 'test-model'))
    with patch.dict(os.environ,{'COGNISHIELD_AI_PLANNING':'1'}):
        route=asyncio.run(select_context(prompt,'test','floating',None,[],[],inventory=inventory,generate_fn=generator))
    assert route.intent=='answer' and route.network_domains==['configuration']
    assert not configuration_text_request('Generate an ACL section for Pine-Lab.')
    assert resolve_read('Quote the saved ACL section in this uploaded document.',None,inventory) is None


def test_saved_section_quote_does_not_substitute_unrelated_configuration():
    from llm.gateway_findings import network_answer
    from llm.gateway_models import Evidence
    context=[{'tool':'network.configuration','status':'success','evidence_ids':['saved'],'data':{
        'records':[{'device_id':1,'hostname':'Pine-Lab','timestamp':'2026-10-18T01:00:00Z',
            'config_text':'sysname Pine-Lab\nbgp 65030\n peer 192.0.2.1 as-number 65020\n','current':False}]}}]
    evidence=[Evidence(id='saved',source='Saved capture',origin='stored')]
    prompt='Quote the saved ACL section for Pine-Lab.'
    answer=network_answer(context,evidence,question=prompt)
    assert 'No literal ACL' in answer and 'bgp 65030' not in answer
    for text,expected in [
        ('hostname Pine-Lab\nip access-list extended EDGE\n permit tcp any any eq 22\nrouter bgp 65030\n',['ip access-list extended EDGE',' permit tcp any any eq 22']),
        ('sysname Pine-Lab\nacl number 3001\n rule 5 permit ip\nbgp 65030\n',['acl number 3001',' rule 5 permit ip']),
        ('set system host-name Pine-Lab\nset firewall family inet filter EDGE term ssh then accept\nset protocols bgp group EBGP type external\n',['set firewall family inet filter EDGE term ssh then accept'])]:
        context[0]['data']['records'][0]['config_text']=text
        answer=network_answer(context,evidence,question=prompt)
        assert all(line in answer for line in expected)
        assert 'bgp 65030' not in answer and 'set protocols bgp' not in answer


@pytest.fixture
def scenario_reader(tmp_path):
    with patch.dict(os.environ, {'COGNISHIELD_DEV_SIMULATION': '1'}):
        db = DatabaseManager(str(tmp_path / 'app.db'))
        db.initialize()
        manager = ScenarioManager(tmp_path / 'state.json')
        db._development_scenario = manager
        scenario, meta = manager.snapshot()
        old = deepcopy(scenario['records']['topology'][0])
        old.update(id='old-link-observation', timestamp='2026-10-17T08:00:00Z', current=False)
        old['values']['oper_status'] = 'down'
        scenario['records']['topology'].append(old)
        manager.change('edit', meta['source_revision'], scenario)
        auth = ToolAuthorization('scope-test', 'admin', 'floating', 'owned',
            frozenset({'network.topology'}), permissions=frozenset({'network.inventory.read'}))
        try:
            yield NetworkReader(db), auth, db
        finally:
            db.close()


@pytest.mark.parametrize('scope,query', [
    ('planned', 'Show planned connections'), ('auto', 'Show the planned topology only')])
def test_planned_topology_excludes_operational_observations(scenario_reader, scope, query):
    reader, auth, _ = scenario_reader
    result = reader.read('topology', NetworkQuery(device_refs=['R1', 'R2'],
        source_scope=scope, query=query), auth)
    assert result.status == 'success'
    assert result.data['links']
    assert result.data['records'] == []
    assert result.data['total'] == 0
    assert result.data['topology_kind'] == 'planned'
    assert result.evidence[0].time_scope == 'unspecified'


@pytest.mark.parametrize('scope', ['current', 'observed'])
def test_current_observed_topology_excludes_old_observations_and_plans(scenario_reader, scope):
    reader, auth, _ = scenario_reader
    result = reader.read('topology', NetworkQuery(device_refs=['R1', 'R2'], source_scope=scope), auth)
    assert result.status == 'success'
    assert [r['oper_status'] for r in result.data['records']] == ['up']
    assert result.data['links'] == []
    assert result.evidence[0].time_scope == 'current'


def test_historical_topology_does_not_substitute_current_or_planned_state(scenario_reader):
    reader, auth, _ = scenario_reader
    result = reader.read('topology', NetworkQuery(device_refs=['R1', 'R2'], source_scope='historical'), auth)
    assert [r['oper_status'] for r in result.data['records']] == ['down']
    assert result.data['links'] == []
    assert result.data['topology_kind'] == 'historical'
    assert result.evidence[0].time_scope == 'historical'


def test_combined_topology_labels_both_sources(scenario_reader):
    reader, auth, _ = scenario_reader
    result = reader.read('topology', NetworkQuery(device_refs=['R1', 'R2'], source_scope='both'), auth)
    assert len(result.data['records']) == 2
    assert result.data['links']
    assert result.data['topology_kind'] == 'combined'


def test_observed_link_is_retrievable_from_either_endpoint(scenario_reader):
    reader, auth, _ = scenario_reader
    result = reader.read('topology', NetworkQuery(device_refs=['R2'], source_scope='observed'), auth)
    assert [r['oper_status'] for r in result.data['records']] == ['up']


def test_source_switch_followup_keeps_owned_device_scope_without_engineering():
    from llm.gateway_routing import select_context
    inventory = {'devices': [{'id': 91, 'hostname': 'Branch-Alder', 'management_ip': '', 'aliases': [], 'interfaces': []}]}
    previous = {'context_coverage': {'retrieval': {'domains': ['topology'], 'device_refs': ['91'],
        'interface_refs': [], 'attributes': [], 'entities': [{'device_id': '91'}]}}}
    generate = AsyncMock(side_effect=AssertionError('An exact scoped follow-up needs no model'))
    route = asyncio.run(select_context('Now show the observed connections instead.', 'test', 'floating',
        None, [], [], previous=previous, inventory=inventory, generate_fn=generate))
    assert route.intent == 'answer' and route.network_domains == ['topology']
    assert route.device_refs == ['91'] and route.use_history
    assert route.network_request == 'Now show the observed connections instead.'


@pytest.mark.parametrize('answer', [
    'There are no links between R2 and other devices. [S1]',
    'R2 has no planned connections. [S1]',
    'The planned topology contains zero links. [S1]'])
def test_nonempty_topology_cannot_be_summarized_as_no_links(answer):
    from llm.gateway_models import Evidence
    from llm.orchestration.synthesis import check_candidate
    context = [{'tool': 'network.topology', 'status': 'success', 'data': {'topology_kind': 'planned',
        'nodes': [{'hostname': 'R2'}], 'links': [{'source': 'R1', 'target': 'R2'}]}}]
    evidence = [Evidence(id='test', source='planned', origin='stored')]
    assert check_candidate(answer, context, evidence, {})
    assert not check_candidate('The planned records include a connection from R1 to R2. [S1]', context, evidence, {})


def test_plans_survive_an_unavailable_observer_without_fabricated_observations(scenario_reader):
    reader, auth, db = scenario_reader
    manager = db._development_scenario
    scenario, meta = manager.snapshot()
    scenario['availability']['topology'] = False
    manager.change('edit', meta['source_revision'], scenario)
    planned = reader.read('topology', NetworkQuery(device_refs=['R1'], source_scope='planned'), auth)
    observed = reader.read('topology', NetworkQuery(device_refs=['R1'], source_scope='observed'), auth)
    assert planned.status == 'success' and planned.data['links']
    assert observed.status == 'unavailable' and observed.data['records'] == []


def test_model_plan_must_respect_explicit_planned_only_scope():
    from llm.orchestration.planning import propose
    inventory = {'devices': [{'id': 91, 'hostname': 'Branch-Alder', 'interfaces': []}]}
    generate = AsyncMock(return_value=(json.dumps({'intent': 'answer', 'information_needs': [
        {'domain': 'topology', 'question': 'connections', 'source_scope': 'both'}]}), 'test'))
    with pytest.raises(ValueError, match='scope'):
        asyncio.run(propose('Show only the planned connections around Branch-Alder.', 'test', 'floating',
            None, [], [], inventory, generate, read_only_request=True))


@pytest.mark.parametrize('text,expected', [
    ('Observed links, not planned links.', 'observed'),
    ('Use planned links without observed records.', 'planned'),
    ('Compare planned and observed connections.', 'both'),
    ('Read the historical links.', 'historical'),
    ('Map connections.', 'auto')])
def test_explicit_scope_includes_comparisons_and_exclusions(text, expected):
    from llm.gateway_network import explicit_topology_scope
    assert explicit_topology_scope(text) == expected


def test_ordinary_historical_topology_cannot_substitute_inventory_plans(scenario_reader):
    reader, auth, db = scenario_reader
    with patch.dict(os.environ, {'COGNISHIELD_DEV_SIMULATION': '0'}):
        result = reader.topology(NetworkQuery(source_scope='historical'), [], {'devices': [], 'links': []})
    assert result.status == 'unavailable'
    assert result.data['topology_kind'] == 'historical'
    assert 'historical' in result.message.lower()


def test_correct_two_endpoint_explanation_does_not_borrow_whole_line_ports():
    from llm.gateway_models import Evidence
    from llm.orchestration.synthesis import check_candidate
    context = [{'tool': 'network.topology', 'status': 'success', 'data': {'topology_kind': 'planned',
        'nodes': [{'hostname': 'R2'}], 'links': [{'source': 'R1', 'target': 'R2',
            'source_interface': 'GigabitEthernet0/1', 'target_interface': 'GigabitEthernet1/0/1'}]}}]
    evidence = [Evidence(id='test', source='planned', origin='stored')]
    answer = "The link joins R1's interface GigabitEthernet0/1 and R2's interface GigabitEthernet1/0/1. [S1]"
    assert not check_candidate(answer, context, evidence, {})
    assert check_candidate(answer.replace("R2's interface GigabitEthernet1/0/1", "R2's interface GigabitEthernet0/1"), context, evidence, {})
    assert check_candidate('The planned connections around R2 are as follows:\n\nSources: [S1]', context, evidence, {})
def test_unqualified_topology_uses_reader_default_not_an_invented_observed_scope():
    import asyncio,json
    from unittest.mock import AsyncMock
    from llm.orchestration.planning import propose
    inventory={'devices':[{'id':1,'hostname':'Oak-Edge','interfaces':[]}]}
    generate=AsyncMock(return_value=(json.dumps({'intent':'answer','information_needs':[
        {'domain':'topology','question':'recorded graph','source_scope':'observed'}]}),'test'))
    route=asyncio.run(propose('Read the recorded graph around Oak-Edge.',None,'floating',None,[],[],inventory,generate,read_only_request=True))
    assert route.source_requests['topology']['source_scope']=='auto'


def test_modeled_hop_question_cannot_omit_graph_source():
    import asyncio,json,pytest
    from unittest.mock import AsyncMock
    from llm.orchestration.planning import propose
    inventory={'devices':[{'id':1,'hostname':'Oak-Edge','interfaces':[]}]}
    generate=AsyncMock(return_value=(json.dumps({'intent':'answer','information_needs':[
        {'domain':'state','question':'hops'}]}),'test'))
    with pytest.raises(ValueError,match='omit'):
        asyncio.run(propose('How many modeled hops connect Oak-Edge to its peer?',None,'floating',None,[],[],inventory,generate,read_only_request=True))


def test_scenario_graph_path_is_returned_from_the_same_planned_graph(scenario_reader):
    from development.seeded import seeded_scenario
    from llm.orchestration.synthesis import projection
    reader,auth,db=scenario_reader
    scenario=seeded_scenario(73)
    manager=db._development_scenario
    manager.change('import',manager.snapshot()[1]['source_revision'],scenario)
    names=[d['hostname'] for d in scenario['devices']]
    result=reader.read('topology',NetworkQuery(device_refs=[names[0],names[2]],source_scope='planned'),auth)
    assert result.data['graph_path']==names
    packet=projection([{'tool':'network.topology','status':'success','data':result.data}],result.evidence,{},'How many modeled hops?')
    assert packet['completed_link_hop_counts']==[2]


def test_path_investigation_reads_actual_intermediate_devices_through_registry(scenario_reader):
    from development.seeded import seeded_scenario
    from llm.gateway_network import network_context
    from llm.gateway_services import registry_for
    from llm.gateway_store import ensure_schema,ConversationStore
    from llm.orchestration.adapters import AuthorizedTools
    reader,_,db=scenario_reader
    scenario=seeded_scenario(73)
    manager=db._development_scenario
    manager.change('import',manager.snapshot()[1]['source_revision'],scenario)
    names=[d['hostname'] for d in scenario['devices']]
    ensure_schema(db);store=ConversationStore(db);cid=store.create('path-reader','floating')['id']
    tool_names=frozenset({'inventory.read','network.topology','network.state','network.configuration'})
    auth=ToolAuthorization('path-reader','engineer','floating',cid,tool_names,permissions=frozenset({'network.inventory.read'}))
    adapters=AuthorizedTools(registry_for(db),store,auth)
    context,evidence,coverage=asyncio.run(network_context(db,adapters,auth,
        'Find the supported cause of the failed modeled path between '+names[0]+' and '+names[2]+'.',
        domains_override=['inventory','state','configuration','topology'],
        device_refs_override=[str(scenario['devices'][i]['id']) for i in [0,2]]))
    assert context[0]['tool']=='network.topology'
    state=next(c for c in context if c['tool']=='network.state')
    assert names[1] in {r['hostname'] for r in state['data']['records']}
    configs=next(c for c in context if c['tool']=='network.configuration')
    assert names[1] in {r['hostname'] for r in configs['data']['records']}
    assert len(adapters.results)==4 and len(evidence)==4
    assert len(coverage['path_device_refs'])==3


def test_interface_state_read_filters_the_existing_record_contract(scenario_reader):
    from dataclasses import replace
    from llm.gateway_network import network_context
    from llm.gateway_services import registry_for
    from llm.gateway_references import retrieval_state
    reader,auth,db=scenario_reader
    auth=replace(auth,allowed_tools=frozenset({'network.state'}))
    context,_,_=asyncio.run(network_context(db,registry_for(db),auth,
        'Obtain interface-operational-state records for R2.',domains_override=['state']))
    rows=context[0]['data']['records']
    assert rows and all(row['kind']=='interface_state' for row in rows)
    assert context[0]['source_request']['record_kinds']==['interface_state']
    refs=retrieval_state(context,[],[])['source_requests']
    assert refs['state']['record_kinds']==['interface_state']
    from llm.orchestration.memory import InvestigationMemory
    assert InvestigationMemory(source_requests=refs).source_requests==refs
    again,_,_=asyncio.run(network_context(db,registry_for(db),auth,
        'Are you sure? Read that same source again.',domains_override=['state'],
        device_refs_override=['R2'],source_requests=refs))
    assert again[0]['data']['records'] and all(row['kind']=='interface_state' for row in again[0]['data']['records'])
    changed,_,_=asyncio.run(network_context(db,registry_for(db),auth,
        'Show the recorded routing table for R2 instead.',domains_override=['state'],source_requests=refs))
    assert any(row['kind']=='routing_table' for row in changed[0]['data']['records'])
    assert 'record_kinds' not in changed[0]['source_request']


def test_cabling_is_a_relationship_source_in_both_router_modes():
    from llm.gateway_network import route_network
    inventory={'devices':[{'id':1,'hostname':'Oak-Edge','interfaces':[]}]}
    assert 'topology' in route_network('Describe the planned cabling around Oak-Edge.',inventory)[0]


def test_modeled_bidirectional_path_requires_state_not_just_cabling():
    from llm.gateway_network import route_network
    from llm.orchestration.planning import propose
    inventory={'devices':[{'id':1,'hostname':'Oak-Edge','interfaces':[]}]}
    prompt='Assess the modeled path from Oak-Edge to its peer, including the return direction.'
    assert {'topology','state'}<=set(route_network(prompt,inventory)[0])
    generate=AsyncMock(return_value=(json.dumps({'intent':'explain','information_needs':[
        {'domain':'topology','question':'graph path'}]}),'test'))
    with pytest.raises(ValueError,match='omit'):
        asyncio.run(propose(prompt,None,'floating',None,[],[],inventory,generate,read_only_request=True))


def test_explicit_configuration_comparison_cannot_select_only_history():
    from llm.gateway_network import explicit_configuration_scope
    from llm.orchestration.planning import propose
    inventory={'devices':[{'id':1,'hostname':'Oak-Edge','interfaces':[]}]}
    generate=AsyncMock(return_value=(json.dumps({'intent':'explain','information_needs':[
        {'domain':'configuration','question':'versions','source_scope':'historical'}]}),'test'))
    route=asyncio.run(propose('What changed between Oak-Edge saved configuration and the current simulated one?',None,'floating',None,[],[],inventory,generate,read_only_request=True))
    assert route.source_requests['configuration']['source_scope']=='both'
    assert route.planning['source_scope_adjustments']==[{'domain':'configuration','proposed':'historical','required':'both'}]
    assert explicit_configuration_scope('Read the saved capture, not the current configuration.')=='historical'
    assert explicit_configuration_scope('Read the current configuration, without historical records.')=='current'


def test_completed_scoped_path_does_not_trigger_unrelated_reader_fanout():
    from types import SimpleNamespace
    from llm.gateway_routing import SemanticRoute
    from llm.orchestration.investigation import additional_domains
    state=SimpleNamespace(route=SemanticRoute(intent='answer',network_domains=['topology','state']),
        results=[{'tool':'network.topology','status':'success'},{'tool':'network.state','status':'success'}],
        request='Assess the modeled path, including the return direction.',memory={},device_refs=['1','3'])
    assessment={'conclusion_status':'healthy_within_tested_scope','development':True,
        'gaps':['An unrelated protocol prerequisite is not recorded'],'warnings':[],'conflicts':[]}
    assert additional_domains(state,assessment)==[]
    state.request='Are you sure? Check the other sources.'
    assert additional_domains(state,assessment)
    state.request='Assess the modeled path, including the return direction.'
    assessment['conflicts']=['Opposed source observations']
    assert additional_domains(state,assessment)


def test_interface_subnets_use_real_masks_and_do_not_guess_missing_masks(tmp_path_factory):
    from llm.gateway_findings import inventory_answer
    from llm.gateway_references import attributes
    from llm.gateway_store import ensure_schema
    tmp_path=tmp_path_factory.mktemp('masks')
    db=DatabaseManager(str(tmp_path/'masks.db'));db.initialize();ensure_schema(db)
    try:
        with db._connect() as c:
            c.execute("INSERT INTO devices(id,hostname,vendor) VALUES(1,'Oak-Edge','cisco')")
            c.execute("INSERT INTO interfaces(device_id,name,ip_address,subnet_mask) VALUES(1,'Ethernet1','192.0.2.9','255.255.255.248')")
            c.execute("INSERT INTO interfaces(device_id,name,ip_address) VALUES(1,'Ethernet2','198.51.100.9')")
        data=inventory_snapshot(db)
        assert data['devices'][0]['interfaces'][0]['subnet_mask']=='255.255.255.248'
        attrs=attributes('Which subnets appear on Oak-Edge according to interface records?')
        assert 'prefixes' in attrs
        answer=inventory_answer(data,attrs)
        assert '192.0.2.8/29' in answer and 'Ethernet1' in answer
        assert 'Not recorded' in answer and '198.51.100.0/24' not in answer
    finally:db.close()


def test_single_stored_attribute_is_answered_directly_without_a_generic_table():
    from llm.gateway_findings import inventory_answer
    answer=inventory_answer({'devices':[{'hostname':'Oak-Edge','os_version':'23.4'}]},['os_version'])
    assert 'Oak-Edge' in answer and '23.4' in answer
    assert '|---' not in answer and 'matching device(s)' not in answer


def test_interface_answers_keep_prefixes_and_requested_management_distinction():
    from llm.gateway_findings import inventory_answer
    from llm.gateway_references import attributes
    device={'id':3,'hostname':'Oak-Edge','management_ip':'192.0.2.43','interfaces':[
        {'id':8,'name':'xe-0/0/0.0','prefix':'198.51.100.5/30','ip_address':'198.51.100.5'},
        {'id':9,'name':'lo0.0','prefix':'203.0.113.9/32','ip_address':'203.0.113.9'}]}
    attrs=attributes("List Oak-Edge's stored interfaces and distinguish their addresses from its management IP.")
    answer=inventory_answer({'devices':[device]},attrs)
    assert '198.51.100.5/30' in answer and '203.0.113.9/32' in answer
    assert '192.0.2.43' in answer and 'management' in answer.lower()
    followup=inventory_answer({'devices':[device]},['addresses'],['8'])
    assert '198.51.100.5/30' in followup and '192.0.2.43' not in followup and 'lo0.0' not in followup
