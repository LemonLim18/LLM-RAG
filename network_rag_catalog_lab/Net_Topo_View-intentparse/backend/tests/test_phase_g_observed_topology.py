"""Observed endpoints are authored evidence, independent of planned link identity."""
from copy import deepcopy
from pathlib import Path
import sys
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from development.bundles import compile_bundle,source_schema
from development.starter import starter_bundle
from local_providers.development import ScenarioManager
from llm.gateway_network import NetworkQuery


def independent_bundle():
    bundle=starter_bundle()
    observed=bundle['sources']['topology_observed']['data']['records'][0]
    observed['values']={'endpoints':{'src_device_id':1100,'src_interface_id':1,'dst_device_id':1300,'dst_interface_id':4},
        'oper_status':'up','discovery_protocol':'LLDP'}
    bundle['sources']['topology_observed']['data']['records']=[observed]
    return bundle


def activate(manager,bundle):
    draft=manager.save_draft(bundle,owner='topology-author',expected=None)
    check=manager.validate_draft(draft['draft_id'],owner='topology-author',expected=1)
    manager.activate_draft(draft['draft_id'],owner='topology-author',expected=1,
        expected_active=manager.snapshot()[1]['source_revision'],validation_hash=check['validation_hash'])


def test_independent_observation_is_readable_from_either_endpoint_without_changing_the_plan(tmp_path):
    bundle=independent_bundle();planned=deepcopy(bundle['sources']['topology_planned']['data']['links'])
    manager=ScenarioManager(tmp_path/'state.json');activate(manager,bundle)
    scenario,_=manager.snapshot()
    for device_id in [1100,1300]:
        result=manager.result('topology',NetworkQuery(query='Read observed links.',source_scope='observed',source_categories=['topology_observed']),
            [device for device in scenario['devices'] if device['id']==device_id])
        assert result.status=='success'
        assert len(result.data['records'])==1
        row=result.data['records'][0]
        assert row['link_endpoints']=={'source':'LAB-R1','source_interface':'GigabitEthernet0/1','target':'LAB-R3','target_interface':'GigabitEthernet0/0/1'}
        assert row['endpoint_basis']=='authored_observation'
        assert result.evidence[0].origin=='simulated'
        assert result.data['topology_kind']=='observed'
    assert scenario['planned_links']==planned


@pytest.mark.parametrize('field,value',[('src_interface_id',2),('dst_interface_id',99999),('dst_device_id',1200)])
def test_observed_endpoints_require_actual_device_interface_membership(field,value):
    bundle=independent_bundle()
    bundle['sources']['topology_observed']['data']['records'][0]['values']['endpoints'][field]=value
    with pytest.raises(ValueError,match='observ|endpoint|interface'):
        compile_bundle(bundle)


def test_workbench_schema_exposes_the_same_typed_endpoints_for_observed_and_history():
    import json
    for category in ['topology_observed','topology_history']:
        values=source_schema(category)['properties']['data']['properties']['records']['items']['properties']['values']
        endpoints=values['properties']['endpoints']
        assert set(endpoints['required'])=={'src_device_id','src_interface_id','dst_device_id','dst_interface_id'}
        assert endpoints['additionalProperties'] is False
        packaged=Path(__file__).resolve().parents[1]/'development/schemas/v1'/f'{category}.schema.json'
        assert json.loads(packaged.read_text(encoding='utf-8'))==source_schema(category)


def test_authored_endpoints_override_a_legacy_plan_hint_and_preserve_historical_event(tmp_path):
    bundle=independent_bundle()
    # The existing bounded event editor requires an explicit supported stanza;
    # it must keep rejecting other vendor/document forms instead of guessing.
    bundle['sources']['running_configs']['data']['records'][0]['values']['config_text']='hostname LAB-R1\ninterface GigabitEthernet0/1\n no shutdown\n'
    row=bundle['sources']['topology_observed']['data']['records'][0]
    row['values']['link_id']=1  # Old plan points at R2, not the authored R3.
    historical=deepcopy(row)
    historical.update(id='independent-observation-history',current=False,timestamp='2026-10-18T00:59:00Z')
    bundle['sources']['topology_history']['data']['records']=[historical]
    manager=ScenarioManager(tmp_path/'state.json');activate(manager,bundle)
    _,meta=manager.snapshot()
    manager.transition(1,'down',meta['source_revision'])
    scenario,_=manager.snapshot()
    old=next(r for r in scenario['records']['topology'] if r['id']==historical['id'])
    current=next(r for r in scenario['records']['topology'] if r['id']==row['id'])
    assert old['values']['oper_status']=='up' and old['timestamp']=='2026-10-18T00:59:00Z'
    assert current['values']['oper_status']=='down'
    result=manager.result('topology',NetworkQuery(query='Read observed links.',source_scope='observed'),
        [d for d in scenario['devices'] if d['id']==1300])
    assert result.data['records'][0]['link_endpoints']['target']=='LAB-R3'
    assert result.data['records'][0]['endpoint_basis']=='authored_observation'


def test_observed_source_names_and_negative_plan_clause_do_not_select_other_sources():
    from development.source_registry import BY_KEY,explicit_read_sources
    from llm.gateway_network import explicit_topology_scope
    prompt='Read only authored observed topology for LAB-R3. Which device and exact interfaces were recorded by LLDP, at what capture time? Do not infer intended cabling or physical reachability.'
    assert explicit_read_sources(prompt,list(BY_KEY))==['topology_observed']
    assert explicit_read_sources('Read observed links for LAB-R3.',list(BY_KEY))==['topology_observed']
    assert explicit_topology_scope(prompt)=='observed'


def test_exclusive_observed_request_rejects_model_inventory_and_state_fanout():
    import asyncio
    from unittest.mock import AsyncMock,patch
    from development.source_registry import BY_KEY
    from llm.gateway_routing import select_context,SemanticRoute
    inventory={'devices':[{'id':1300,'hostname':'LAB-R3','aliases':[],'interfaces':[]}],
        'scenario':{'id':'test'},'logical_source_categories':list(BY_KEY)}
    prompt='Read only authored observed topology for LAB-R3. Which interfaces were recorded by LLDP? Do not infer intended cabling or physical reachability.'
    wrong=SemanticRoute(intent='answer',network_domains=['inventory','topology','state'])
    with patch.dict('os.environ',{'COGNISHIELD_AI_PLANNING':'1'}),\
         patch('llm.orchestration.planning.propose',AsyncMock(return_value=wrong)):
        route=asyncio.run(select_context(prompt,'test','floating',None,[],[],inventory=inventory))
    assert route.network_domains==['topology']
    assert route.source_requests['topology']['source_categories']==['topology_observed']
    assert 'exclusive source' in route.planning['reason']


def test_prohibited_configuration_action_does_not_become_a_positive_reader_request():
    from llm.gateway_references import read_intent_text
    from llm.gateway_network import route_network
    from development.source_registry import explicit_read_sources,BY_KEY
    question='Compare observed topology and planned topology for LAB-R3. Explain the disagreement and what it does not prove. Do not generate or modify configuration.'
    inventory={'devices':[{'id':1300,'hostname':'LAB-R3','aliases':[],'interfaces':[]}]}
    assert 'configuration' not in route_network(question,inventory)[0]
    assert set(explicit_read_sources(question,list(BY_KEY)))=={'topology_observed','topology_planned'}
    assert 'read the saved configuration' in read_intent_text('Do not modify it, but read the saved configuration.')
    assert 'Change the neighbor' in read_intent_text('Change the neighbor but do not save the file.')


def test_observed_answer_cannot_substitute_inventory_ports_or_omit_the_peer():
    from llm.orchestration.synthesis import check_candidate
    from llm.gateway_models import Evidence
    context=[{'tool':'network.topology','status':'success','evidence_ids':['observation'],
        'data':{'topology_kind':'observed','records':[{'kind':'observed_link','timestamp':'2026-10-18T01:00:00Z',
            'discovery_protocol':'LLDP','endpoint_basis':'authored_observation',
            'link_endpoints':{'source':'LAB-R3','source_interface':'GigabitEthernet0/0/1','target':'LAB-R1','target_interface':'GigabitEthernet0/1'}}]}},
        {'tool':'inventory.read','status':'success','data':{'devices':[{'hostname':'LAB-R3','interfaces':[{'name':'LoopBack0'}]}]}}]
    evidence=[Evidence(id='observation',source='development.topology',origin='simulated')]
    question='Which device and exact interfaces were recorded by LLDP, at what capture time?'
    wrong='LLDP records LAB-R3 interfaces GigabitEthernet0/0/1 and LoopBack0 at2026-10-18T01:00:00Z. [S1]'
    assert check_candidate(wrong,context,evidence,{},question)
    correct='Recorded LLDP connects LAB-R3 GigabitEthernet0/0/1 with LAB-R1 GigabitEthernet0/1 at2026-10-18T01:00:00Z. [S1]'
    assert not check_candidate(correct,context,evidence,{},question)


def test_planned_observed_comparison_preserves_actual_peers_and_rejects_false_absence():
    from llm.orchestration.synthesis import topology_comparison_facts,check_candidate
    from llm.gateway_models import Evidence
    plan={'source':'LAB-R2','source_interface':'ge-0/0/1.0','target':'LAB-R3','target_interface':'GigabitEthernet0/0/1'}
    observed={'source':'LAB-R1','source_interface':'GigabitEthernet0/1','target':'LAB-R3','target_interface':'GigabitEthernet0/0/1'}
    context=[{'tool':'network.topology','status':'success','evidence_ids':['comparison'],'scope_devices':[{'id':1300,'hostname':'LAB-R3'}],
        'data':{'topology_kind':'combined','links':[plan],'records':[{'link_endpoints':observed,'timestamp':'2026-10-18T01:01:00Z','current':True}]}}]
    evidence=[Evidence(id='comparison',source='development.topology',origin='simulated')]
    fact=topology_comparison_facts(context,evidence)[0]
    assert fact['planned_only']==[plan] and fact['observed_only'][0]['source']=='LAB-R1'
    question='Compare the planned and observed topology for LAB-R3.'
    wrong='The planned topology does not include this specific router. The observed topology has LAB-R3. [S1]'
    assert check_candidate(wrong,context,evidence,{},question)
    correct='The plan links LAB-R3 to LAB-R2, while the observation records LAB-R3 with LAB-R1. This difference does not prove a physical outage or which source is wrong. [S1]'
    assert not check_candidate(correct,context,evidence,{},question)
    context[0]['data']['records'][0]['link_endpoints']={'source':'LAB-R3','source_interface':plan['target_interface'],'target':'LAB-R2','target_interface':plan['source_interface']}
    fact=topology_comparison_facts(context,evidence)[0]
    assert fact['matching_relationship_count']==1 and not fact['planned_only'] and not fact['observed_only']


def test_plan_comparison_does_not_merge_old_observations_or_accept_swapped_source_attribution(tmp_path):
    from llm.orchestration.synthesis import check_candidate,topology_comparison_facts
    bundle=independent_bundle();manager=ScenarioManager(tmp_path/'state.json');activate(manager,bundle)
    scenario,_=manager.snapshot()
    question='Compare observed topology and planned topology for LAB-R3. Explain the disagreement and what it does not prove. Do not generate or modify configuration.'
    result=manager.result('topology',NetworkQuery(query=question),[d for d in scenario['devices'] if d['id']==1300])
    assert len(result.data['records'])==1, 'A current-plan comparison must not mix in a previous observation'
    context=[{'tool':'network.topology','status':'success','data':result.data,'evidence_ids':[result.evidence[0].id]}]
    fact=topology_comparison_facts(context,result.evidence)[0]
    assert fact['planned_only'][0]['source']=='LAB-R2'
    wrong='The planned topology shows LAB-R3 connected to LAB-R1, while the observed topology shows LAB-R3 connected to LAB-R2. This does not prove a physical fault. [S1]'
    assert check_candidate(wrong,context,result.evidence,{},question)
    wrong='The plan links LAB-R2 to LAB-R3 and observation links LAB-R1 to LAB-R3. This indicates that the network configuration has changed since the last planned topology was recorded. [S1]'
    assert check_candidate(wrong,context,result.evidence,{},question)
    correct='The plan links LAB-R2 to LAB-R3, while the observation records LAB-R1 with LAB-R3. Reconcile intended and discovered relationships; this alone does not prove a physical fault or which source is wrong. [S1]'
    assert not check_candidate(correct,context,result.evidence,{},question)
    assert check_candidate(correct+' The reference-only endpoint limitation applies.',context,result.evidence,{},question)
    assert check_candidate(correct+' It does not prove an outage; it only confirms the current physical configuration.',context,result.evidence,{},question)
    # Replay the original failing source's mixed current/history shape. A
    # matching historical edge cannot make omission of the planned peer valid.
    context[0]['data']['records'].append({'link_endpoints':fact['planned'][0],'current':False,'timestamp':'2026-10-18T00:55:00Z'})
    assert check_candidate('The observed topology and planned topology differ: the planned topology shows LAB-R3 connected to LAB-R1. This does not prove a physical outage. [S1]',context,result.evidence,{},question)


def test_excluded_plan_and_previous_records_do_not_resurrect_a_missing_current_neighbor(tmp_path):
    from llm.gateway_network import explicit_topology_scope
    from llm.orchestration.synthesis import check_candidate
    manager=ScenarioManager(tmp_path/'state.json');activate(manager,starter_bundle());scenario,_=manager.snapshot()
    question='Read only authored observed topology for LAB-R1 now. Is a current neighbor recorded? Do not substitute planned topology or previous observations.'
    assert explicit_topology_scope(question)=='observed'
    # No current observations for this device. Its planned links and historical
    # observations still exist and must not stand in for the requested source.
    bundle=starter_bundle();bundle['sources']['topology_observed']['data']['records']=[];activate(manager,bundle)
    result=manager.result('topology',NetworkQuery(query=question),[d for d in scenario['devices'] if d['id']==1100])
    assert result.status=='unavailable' and result.data['records']==[] and result.data['links']==[]
    context=[{'tool':'network.topology','status':result.status,'data':result.data,'evidence_ids':[result.evidence[0].id]}]
    assert check_candidate('Yes, a current neighbor is recorded for LAB-R1. [S1]',context,result.evidence,{},question)
    assert not check_candidate('No current observed neighbor is recorded in the returned source. This does not establish that the device is physically disconnected. [S1]',context,result.evidence,{},question)


@pytest.mark.parametrize('status,expected', [('AVAILABLE','success'),('STALE','success'),('ERROR','error'),('MISSING','unavailable')])
def test_planned_source_retains_capture_availability_and_never_substitutes_observations(tmp_path,status,expected):
    bundle=independent_bundle()
    bundle['sources']['topology_planned'].update(status=status,captured_at='2026-10-18T00:59:00Z')
    manager=ScenarioManager(tmp_path/'state.json');activate(manager,bundle)
    scenario,_=manager.snapshot()
    result=manager.result('topology',NetworkQuery(query='Read planned links for LAB-R1.',source_scope='planned',source_categories=['topology_planned']),[scenario['devices'][0]])
    assert result.status==expected
    assert result.data['source_statuses']=={'topology_planned':status}
    assert result.evidence[0].captured_at=='2026-10-18T00:59:00+00:00'
    from llm.gateway_models import ToolResult
    ToolResult.model_validate(result.model_dump())
    assert result.evidence[0].time_scope=='unspecified'
    assert result.data['topology_kind']=='planned'
    assert result.data['records']==[]
    if expected=='success':
        assert result.data['links'][0]['target']=='LAB-R2'
        assert result.evidence[0].freshness==('stale' if status=='STALE' else 'not_applicable')
    else:
        assert result.data['links']==[] and result.data['nodes']==[]
        assert not result.data.get('graph_path')


def test_topology_source_categories_cannot_return_an_unrequested_plan(tmp_path):
    manager=ScenarioManager(tmp_path/'state.json');activate(manager,independent_bundle())
    scenario,_=manager.snapshot()
    result=manager.result('topology',NetworkQuery(query='Read topology history for LAB-R1.',source_categories=['topology_history']),[scenario['devices'][0]])
    assert result.data['topology_kind']=='historical'
    assert result.data['links']==[]
    assert all(row['source_category']=='topology_history' for row in result.data['records'])


@pytest.mark.parametrize('status,answer',[
    ('STALE','The source capture time is2026-10-18T01:00:00Z, and source availability is not available. [S1]'),
    ('STALE','This is intended to be a read-only link between LAB-R1 and LAB-R3. [S1]'),
    ('ERROR','LAB-R1 planned links are unavailable. The source captures are not available and source statuses are not specified. [S1]'),
    ('AVAILABLE','LAB-R1: STALE; LAB-R3: STALE; S1: ERROR/unavailable. [S1]'),
])
def test_source_envelope_guards_reject_status_capture_and_permission_as_data_errors(status,answer):
    from llm.orchestration.synthesis import check_candidate
    from llm.gateway_models import Evidence
    context=[{'tool':'network.topology','status':'error' if status=='ERROR' else 'success','evidence_ids':['plan'],
        'scope_devices':[{'id':1100,'hostname':'LAB-R1'}], 'data':{'source_statuses':{'topology_planned':status},
            'source_captures':{'topology_planned':'2026-10-18T01:00:00Z'},'topology_kind':'planned','links':[],'records':[]}}]
    assert check_candidate(answer,context,[Evidence(id='plan',source='development.topology',origin='simulated')],{},'Give the planned links, capture time and source availability for LAB-R1.')


def test_unavailable_planned_fallback_reports_reader_failure_not_empty_network(tmp_path):
    from llm.gateway_findings import network_answer
    bundle=independent_bundle();bundle['sources']['topology_planned']['status']='ERROR'
    manager=ScenarioManager(tmp_path/'state.json');activate(manager,bundle)
    scenario,_=manager.snapshot()
    result=manager.result('topology',NetworkQuery(source_categories=['topology_planned']),[scenario['devices'][0]])
    answer=network_answer([{'tool':'network.topology','status':result.status,'data':result.data,
        'message':result.message,'evidence_ids':[result.evidence[0].id]}],result.evidence)
    assert 'ERROR' in answer and 'unavailable' in answer.lower()
    assert 'No planned links match' not in answer
    assert '2026-10-18T01:00:00' in answer


@pytest.mark.parametrize('answer',[
    'The source availability is STALE, captured2026-10-18T01:00:00Z. [S1]',
    'LAB-R1 GigabitEthernet0/1 to LAB-R3 GigabitEthernet0/0/1 is available for use. Source AVAILABLE. [S1]',
])
def test_planned_link_answers_need_requested_endpoints_and_cannot_assert_operability(answer):
    from llm.orchestration.synthesis import check_candidate
    from llm.gateway_models import Evidence
    context=[{'tool':'network.topology','status':'success','evidence_ids':['plan'],'data':{'topology_kind':'planned',
        'links':[{'source':'LAB-R1','source_interface':'GigabitEthernet0/1','target':'LAB-R3','target_interface':'GigabitEthernet0/0/1'}],
        'records':[],'source_statuses':{'topology_planned':'STALE' if 'STALE' in answer else 'AVAILABLE'}}}]
    assert check_candidate(answer,context,[Evidence(id='plan',source='development.topology',origin='simulated')],{},'Give the intended peer and exact interface at each endpoint.')
