"""Recorded metric values and query windows must preserve actual sample scope."""
from copy import deepcopy
from pathlib import Path
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from development.starter import starter_bundle
from development.bundles import compile_bundle


@pytest.mark.parametrize('value',[float('nan'),float('inf'),float('-inf'),True])
def test_recorded_metric_value_must_be_finite_and_numeric(value):
    bundle=starter_bundle()
    bundle['sources']['telemetry']['data']['records'][0]['values']['value']=value
    with pytest.raises(ValueError):compile_bundle(bundle)


@pytest.mark.parametrize('samples',[
    [{'timestamp':'2026-10-18T01:00:01Z','value':18}],
    [{'timestamp':'2026-10-18T00:59:30','value':18}],
    [{'timestamp':'2026-10-18T00:59:30Z','value':18},{'timestamp':'2026-10-18T00:59:00Z','value':17}],
    [{'timestamp':'2026-10-18T00:59:30Z','value':float('inf')}],
    [{'timestamp':'2026-10-18T00:59:30Z','value':101}],
    [{'timestamp':'2026-10-18T00:59:30Z','value':True}],
])
def test_recorded_sample_times_units_and_values_are_validated(samples):
    bundle=starter_bundle()
    bundle['sources']['telemetry']['data']['records'][0]['values']['samples']=samples
    with pytest.raises(ValueError):compile_bundle(bundle)


def test_missing_samples_remain_gaps_and_resets_are_not_rewritten():
    bundle=starter_bundle()
    bundle['sources']['telemetry']['data']['records'][0]['values']['samples'][1]['value']=None
    bundle['sources']['interface_metrics']['data']['records'][0]['values'].update(
        metric='errors',unit='count',value=2,samples=[
            {'timestamp':'2026-10-18T00:59:00Z','value':120},
            {'timestamp':'2026-10-18T01:00:00Z','value':2}])
    scenario=compile_bundle(bundle)
    cpu=next(r for r in scenario['records']['telemetry'] if r['values'].get('metric')=='cpu_pct')
    assert cpu['values']['samples'][1]['value'] is None
    counter=next(r for r in scenario['records']['telemetry'] if r['values'].get('metric')=='errors')
    assert [p['value'] for p in counter['values']['samples']]==[120,2]


@pytest.mark.parametrize('change',[{'unit':'bps'},{'sampling_seconds':True},{'sampling_seconds':0}])
def test_known_metric_units_and_sampling_intervals_follow_existing_contract(change):
    bundle=starter_bundle()
    bundle['sources']['telemetry']['data']['records'][0]['values'].update(change)
    with pytest.raises(ValueError):compile_bundle(bundle)
    bundle['sources']['telemetry']['data']['records'][0]['values'].pop('samples')
    with pytest.raises(ValueError):compile_bundle(bundle)


def test_scoped_counter_math_reuses_existing_engine_and_custom_metrics_remain_readable():
    from development.network_model import metric_sample_window
    from llm.gateway_network import timestamp
    values={'metric':'errors','unit':'count','value':300,'sampling_seconds':30,'unscoped_drops':82,
        'samples':[{'timestamp':'2026-10-18T00:59:00Z','value':120},
            {'timestamp':'2026-10-18T00:59:30Z','value':2},
            {'timestamp':'2026-10-18T01:00:00Z','value':300}]}
    result=metric_sample_window(values,None,timestamp('2026-10-18T00:59:30Z'),[],1,None)
    assert result['counter_reset_or_wrap'] is True and 'average_per_second' not in result
    assert 'unscoped_drops' not in result and result['unscoped_fields_omitted']==['unscoped_drops']
    result=metric_sample_window(values,timestamp('2026-10-18T00:59:30Z'),None,[],1,None)
    assert result['delta']==298 and result['average_per_second']==pytest.approx(298/30)
    custom={**values,'metric':'custom_queue_depth','unit':'items'}
    result=metric_sample_window(custom,None,None,[],1,None)
    assert result['samples']==values['samples'] and 'delta' not in result


def test_sample_window_reads_overlapping_series_not_the_capture_aggregate(tmp_path):
    from db.manager import DatabaseManager
    from llm.gateway_network import NetworkReader,NetworkQuery
    from llm.tools import ToolAuthorization
    from local_providers.development import ScenarioManager
    db=DatabaseManager(str(tmp_path/'app.db'));db.initialize()
    manager=ScenarioManager(tmp_path/'state.json',enabled_default=False);db._development_scenario=manager
    bundle=starter_bundle()
    row=bundle['sources']['telemetry']['data']['records'][0]
    row['values']['samples'][1]['value']=None
    try:
        draft=manager.save_draft(bundle,owner='metric-owner',expected=None)
        receipt=manager.validate_draft(draft['draft_id'],owner='metric-owner',expected=1)
        manager.activate_draft(draft['draft_id'],owner='metric-owner',expected=1,
            expected_active=manager.snapshot()[1]['source_revision'],validation_hash=receipt['validation_hash'])
        auth=ToolAuthorization('metric-owner','admin','floating','owned',frozenset({'network.telemetry'}))
        query=NetworkQuery(device_refs=['LAB-R1'],source_categories=['telemetry'],
            start='2026-10-18T00:58:59Z',end='2026-10-18T00:59:31Z')
        with patch.dict('os.environ',{'COGNISHIELD_DEV_WORKBENCH':'1'}):
            result=NetworkReader(db).read('telemetry',query,auth)
        records=result.data['records']
        assert len(records)==1
        record=records[0]
        assert [p['value'] for p in record['samples']]==[16,None]
        assert record['window_end']=='2026-10-18T00:59:30+00:00'
        assert record['value'] is None  # Latest point in this window is missing.
        assert record['captured_at']==row['timestamp']
        assert record['timestamp']=='2026-10-18T00:59:30+00:00'
        assert record['current'] is False and record['missing_values'] is True
        assert result.evidence[0].origin=='simulated'
        assert result.evidence[0].time_scope=='historical'
    finally:db.close()


def test_reader_time_scope_is_retained_as_validated_intent_not_observations():
    from llm.gateway_references import retrieval_state,source_scope_references,resolve_read
    from llm.orchestration.memory import InvestigationMemory
    window={'source_scope':'historical','source_categories':['telemetry'],
        'start':'2026-10-18T00:58:59Z','end':'2026-10-18T00:59:31Z'}
    context=[{'tool':'network.telemetry','device_refs':['1100'],'source_request':window}]
    refs=retrieval_state(context,[],[],{'telemetry':{'source_scope':'auto'}})
    assert refs['source_requests']=={'telemetry':window}
    memory=InvestigationMemory.model_validate(refs)
    assert memory.source_requests=={'telemetry':window}
    previous={'context_coverage':{'retrieval':memory.model_dump()}}
    resolved=resolve_read('Are you sure? Recheck that same window and source.',previous,{'devices':[]})
    assert resolved['device_refs']==['1100'] and resolved['source_requests']=={'telemetry':window}
    assert source_scope_references({'state':{'source_scope':'observed','source_categories':['protocol_state']}})=={
        'state':{'source_scope':'observed','source_categories':['protocol_state']}}
    for invalid in [{'start':'nonsense'},{'start':window['end'],'end':window['start']},
            {'query':'SELECT * FROM secrets'},{'device_refs':['other-owner']},{'live':True}]:
        with pytest.raises(ValueError):source_scope_references({'telemetry':invalid})


def test_reader_time_ranges_preserve_explicit_utc_offsets():
    from llm.gateway_network import route_network
    prompt='Read CPU samples from 2026-10-18T08:58:59+08:00 to 2026-10-18T08:59:31+08:00.'
    _,query=route_network(prompt,{'devices':[]})
    assert query['start']=='2026-10-18T08:58:59+08:00'
    assert query['end']=='2026-10-18T08:59:31+08:00'


def test_investigation_correction_does_not_parse_old_goal_dates_as_new_request():
    from llm.orchestration.investigation import contextual_route
    from llm.orchestration.memory import InvestigationMemory
    from llm.gateway_network import route_network
    memory=InvestigationMemory(goal='Investigate CPU from 2026-10-18T00:58:59Z to 2026-10-18T00:59:31Z.',
        device_refs=['1100'],domains=['telemetry'],source_requests={'telemetry':{'source_categories':['telemetry']}})
    inventory={'devices':[{'id':1100,'hostname':'Oak','management_ip':None,'aliases':[],'interfaces':[]}]}
    route=contextual_route('Reassess from 2026-10-18T00:59:59Z to 2026-10-18T01:00:01Z.',memory,None,inventory)
    query=route_network(route.network_request,inventory)[1]
    assert query['start']=='2026-10-18T00:59:59Z' and query['end']=='2026-10-18T01:00:01Z'
    assert route.device_refs==['1100'] and route.use_history


def test_explicit_new_source_can_replace_old_category_without_losing_window():
    import asyncio
    from unittest.mock import AsyncMock
    from llm.gateway_routing import select_context,SemanticRoute
    previous={'context_coverage':{'retrieval':{'domains':['telemetry'],'device_refs':['1100'],
        'source_requests':{'telemetry':{'source_scope':'observed','source_categories':['telemetry'],
            'start':'2026-10-18T00:59:59Z','end':'2026-10-18T01:00:01Z'}}}}}
    proposed=SemanticRoute(intent='explain',network_domains=['telemetry'],
        source_requests={'telemetry':{'source_scope':'observed','source_categories':['interface_metrics']}},
        planning={'source_selection':{'status':'explicit_registry_source_scope','selected_sources':['interface_metrics']}})
    with patch.dict('os.environ',{'COGNISHIELD_AI_PLANNING':'1'}),patch('llm.orchestration.planning.propose',AsyncMock(return_value=proposed)):
        route=asyncio.run(select_context('Read the telemetry from interface counters instead, for the same device and window.',
            'test','floating',None,[],[],previous=previous,inventory={'devices':[]}))
    assert route.device_refs==['1100'] and route.use_history
    assert route.source_requests['telemetry']=={'source_scope':'observed','source_categories':['interface_metrics'],
        'start':'2026-10-18T00:59:59Z','end':'2026-10-18T01:00:01Z'}


def test_actual_reader_followup_restores_window_and_explicit_new_window_replaces_it(tmp_path):
    import asyncio
    from db.manager import DatabaseManager
    from llm.gateway_network import network_context
    from llm.gateway_services import registry_for
    from llm.gateway_store import ensure_schema,ConversationStore
    from llm.gateway_references import retrieval_state
    from llm.tools import ToolAuthorization
    from local_providers.development import ScenarioManager
    db=DatabaseManager(str(tmp_path/'app.db'));db.initialize();ensure_schema(db)
    manager=ScenarioManager(tmp_path/'state.json',enabled_default=False);db._development_scenario=manager
    bundle=starter_bundle();bundle['sources']['telemetry']['data']['records'][0]['values']['samples'][1]['value']=None
    draft=manager.save_draft(bundle,owner='metric-owner',expected=None)
    receipt=manager.validate_draft(draft['draft_id'],owner='metric-owner',expected=1)
    manager.activate_draft(draft['draft_id'],owner='metric-owner',expected=1,
        expected_active=manager.snapshot()[1]['source_revision'],validation_hash=receipt['validation_hash'])
    cid=ConversationStore(db).create('metric-owner','floating')['id']
    auth=ToolAuthorization('metric-owner','admin','floating',cid,frozenset({'network.telemetry'}),permissions=frozenset({'network.inventory.read'}))
    registry=registry_for(db)
    async def read(prompt,scopes):
        return await network_context(db,registry,auth,prompt,domains_override=['telemetry'],
            device_refs_override=['LAB-R1'],source_requests=scopes)
    try:
        with patch.dict('os.environ',{'COGNISHIELD_DEV_WORKBENCH':'1'}):
            first,evidence,_=asyncio.run(read('Read samples from 2026-10-18T00:58:59Z to 2026-10-18T00:59:31Z.',
                {'telemetry':{'source_categories':['telemetry']}}))
            refs=retrieval_state(first,[],[])['source_requests']
            again,again_evidence,_=asyncio.run(read('Recheck that same window and source.',refs))
            assert [p['value'] for p in again[0]['data']['records'][0]['samples']]==[16,None]
            assert again_evidence[0].requested_time_range==evidence[0].requested_time_range
            assert again_evidence[0].time_scope=='historical'
            newer,_,_=asyncio.run(read('Instead read 2026-10-18T00:59:59Z to 2026-10-18T01:00:01Z.',refs))
            assert [p['value'] for p in newer[0]['data']['records'][0]['samples']]==[18]
            assert retrieval_state(newer,[],[])['source_requests']['telemetry']['end']=='2026-10-18T01:00:01Z'
    finally:db.close()
