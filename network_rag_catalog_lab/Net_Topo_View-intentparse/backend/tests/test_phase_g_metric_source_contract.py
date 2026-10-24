"""A logical source may expose typed data through multiple existing readers.

Independent expected arithmetic remains in evaluator-only fixtures. These tests
verify retrieval/provenance and status isolation, not local-model reasoning.
"""
import asyncio
from pathlib import Path
import sys
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(1,str(Path(__file__).resolve().parent))
from test_phase_g_conformance import EXTENDED_CASES, input_bundle, assert_expected_fields
from test_phase_g_source_contracts import source_runtime
from llm.tools import ToolAuthorization


def activate(manager, bundle):
    draft = manager.save_draft(bundle, owner='metric-owner', expected=None)
    receipt = manager.validate_draft(draft['draft_id'], owner='metric-owner', expected=1)
    manager.activate_draft(draft['draft_id'], owner='metric-owner', expected=1,
        expected_active=manager.snapshot()[1]['source_revision'], validation_hash=receipt['validation_hash'])


@pytest.mark.parametrize('spec', [case for case in EXTENDED_CASES if case['tool']=='network.telemetry'], ids=lambda case:case['id'])
def test_modeled_series_remains_retrievable_under_its_real_logical_source(source_runtime, spec):
    _, manager, registry = source_runtime
    activate(manager, input_bundle(spec))
    for surface in ['floating', 'studio']:
        auth = ToolAuthorization('metric-owner','engineer',surface,'metric-'+surface,frozenset({'network.telemetry'}))
        result = asyncio.run(registry.invoke('network.telemetry', {'device_refs':['LAB-R1'], 'source_categories':['simulation']}, auth))
        assert result.status=='success'
        assert result.data['source_statuses']=={'simulation':'AVAILABLE'}
        rows=result.data['records']
        selected=next(row for row in rows if all(row.get(key)==value for key,value in spec['selector'].items()))
        assert_expected_fields(selected,spec['expected'])
        assert all(row['kind']=='metric_series' and row['source_category']=='simulation' for row in rows)
        assert all(e.origin=='simulated' and e.source_revision==manager.snapshot()[1]['source_revision'] for e in result.evidence)
        assert result.evidence[0].captured_at==result.data['source_captures']['simulation']
        raw=asyncio.run(registry.invoke('network.telemetry', {'device_refs':['LAB-R1'],'source_categories':['interface_metrics']},auth))
        assert not any(row['kind']=='metric_series' for row in raw.data['records'])


@pytest.mark.parametrize('status',['AVAILABLE','STALE','ERROR','MISSING'])
def test_modeled_metrics_use_their_own_status_not_another_telemetry_source(source_runtime,status):
    _,manager,registry=source_runtime
    bundle=input_bundle(next(case for case in EXTENDED_CASES if case['id']=='G6-CONFORMANCE-028'))
    bundle['sources']['simulation']['status']=status
    for key in ['interface_metrics','telemetry']:bundle['sources'][key]['status']='ERROR'
    activate(manager,bundle)
    auth=ToolAuthorization('metric-owner','engineer','floating','metric-status',frozenset({'network.telemetry'}))
    result=asyncio.run(registry.invoke('network.telemetry',{'device_refs':['LAB-R1'],'source_categories':['simulation']},auth))
    assert result.data['source_statuses']=={'simulation':status}
    from llm.gateway_network import timestamp
    assert timestamp(result.evidence[0].captured_at)==timestamp(bundle['sources']['simulation']['captured_at'])
    if status in {'ERROR','MISSING'}:
        assert result.status in {'error','unavailable'} and result.data['records']==[]
    else:
        assert result.status=='success' and result.data['records']
        assert all(row['current']==(status=='AVAILABLE') for row in result.data['records'])
        if status=='STALE':assert result.evidence[0].freshness=='stale'


def test_source_planning_and_restored_references_share_reader_compatibility():
    from llm.orchestration.planning import InformationNeed,IntentPlan,select_logical_sources
    from llm.gateway_references import source_scope_references
    need=InformationNeed(domain='telemetry',question='Read the modeled series',source_categories=['simulation'])
    assert source_scope_references({'telemetry':{'source_categories':['simulation']}})['telemetry']['source_categories']==['simulation']
    with pytest.raises(ValueError):InformationNeed(domain='syslog',question='Read the modeled series',source_categories=['simulation'])
    plan=IntentPlan(intent='answer',information_needs=[need])
    model=AsyncMock(return_value=('{"source_categories":["simulation"]}',{}))
    selected,trace=asyncio.run(select_logical_sources('Explain the modeled interface series.',plan,model,None,['interface_metrics','telemetry','simulation']))
    assert trace['status']=='validated_model_source_selection'
    assert [(item.domain,item.source_categories) for item in selected.information_needs]==[('telemetry',['simulation'])]
    catalog=model.call_args.args[0][-1]['content']
    assert 'simulation' in catalog and 'network.telemetry' in catalog
    assert 'metric_series' in catalog


def test_multireader_source_keeps_an_already_selected_compatible_domain():
    from development.source_registry import reader_domains
    assert reader_domains(['simulation'],['telemetry'])==['telemetry']
    assert reader_domains(['simulation'],['syslog'])==['state']
    assert reader_domains(['simulation'],['state','telemetry'])==['state','telemetry']
    assert reader_domains(['syslog','simulation'],['telemetry'])==['syslog','telemetry']


def test_metric_synthesis_projection_preserves_calculations_and_correlated_series():
    from llm.orchestration.synthesis import metric_observations
    context=[{'tool':'network.telemetry','status':'success','data':{'records':[
        *[{'kind':'metric_sample','metric':'cpu_pct','unit':'percent','samples':[{'timestamp':'2026-10-18T01:00:00Z','value':18}]} for _ in range(7)],
        {'kind':'metric_series','metric':'out_bps','unit':'bps','samples':[{'timestamp':'2026-10-18T01:00:00Z','value':980000}],
         'peak_utilization_pct':98,'congestion_hypothesis':'plausible','correlated_source_ids':['discard-window'],
         'window_start':'2026-10-18T00:59:00Z','window_end':'2026-10-18T01:00:00Z','interpretation':['Correlation does not uniquely establish cause']},
        {'kind':'metric_series','metric':'discards','unit':'count','samples':[{'timestamp':'2026-10-18T01:00:00Z','value':14}],
         'delta':4,'average_per_second':4/60,'counter_reset_or_wrap':False,'model_source_ids':['discard-window']}
    ]}}]
    facts=metric_observations(context)
    assert len(facts)==9
    assert facts[0]['record_kind']=='metric_series'
    traffic=next(fact for fact in facts if fact['metric']=='out_bps')
    assert traffic['calculations']['peak_utilization_pct']==98
    assert traffic['calculations']['congestion_hypothesis']=='plausible'
    assert traffic['calculations']['correlated_source_ids']==['discard-window']
    assert traffic['interpretation']==['Correlation does not uniquely establish cause']
    drops=next(fact for fact in facts if fact['metric']=='discards')
    assert drops['calculations']['average_per_second']==4/60
    assert drops['calculation_unit']=='count/second'
    assert 'calculations' not in next(fact for fact in facts if fact['metric']=='cpu_pct')

