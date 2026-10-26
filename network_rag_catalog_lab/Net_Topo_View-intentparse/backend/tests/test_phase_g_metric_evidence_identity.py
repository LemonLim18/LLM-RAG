"""Record identity, conflicting observations and calculation ownership contracts.

These checks exercise returned reader data, not prompt-specific diagnoses.
"""
import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from llm.gateway_models import Evidence
from llm.orchestration.synthesis import check_candidate, metric_observations, synthesize


def evidence_case():
    refs = [Evidence(id='reader-evidence', source='controlled telemetry', origin='simulated')]
    rows = [
        {'id': 'authored-series', 'kind': 'interface_counters', 'source_category': 'interface_metrics',
         'hostname': 'Willow', 'interface': 'port-7', 'metric': 'out_bps', 'unit': 'bits_per_second',
         'current': True, 'timestamp': '2026-10-24T02:01:00Z', 'samples': [
             {'timestamp': '2026-10-24T02:00:00Z', 'value': 2000},
             {'timestamp': '2026-10-24T02:01:00Z', 'value': 3000}]},
        {'id': 'modeled-series', 'kind': 'metric_series', 'source_category': 'simulation',
         'hostname': 'Willow', 'interface': 'port-7', 'metric': 'out_bps', 'unit': 'bps',
         'current': True, 'timestamp': '2026-10-24T02:01:00Z', 'sampling_seconds': 30,
         'window_start': '2026-10-24T02:00:00Z', 'window_end': '2026-10-24T02:01:00Z',
         'peak_utilization_pct': 72, 'congestion_hypothesis': 'plausible', 'samples': [
             {'timestamp': '2026-10-24T02:00:00Z', 'value': 71000000},
             {'timestamp': '2026-10-24T02:01:00Z', 'value': 72000000}]},
        {'id': 'other-port', 'kind': 'interface_counters', 'source_category': 'interface_metrics',
         'hostname': 'Hazel', 'interface': 'port-9', 'metric': 'out_bps', 'unit': 'bps',
         'current': True, 'timestamp': '2026-10-24T02:01:00Z', 'samples': [
             {'timestamp': '2026-10-24T02:01:00Z', 'value': 24000}]},
    ]
    return [{'tool': 'network.telemetry', 'status': 'success', 'evidence_ids': ['reader-evidence'],
             'data': {'records': rows}}], refs


def test_metric_projection_preserves_distinct_record_and_source_identity():
    context, refs = evidence_case()
    facts = metric_observations(context, refs)
    assert len({f['record_ref'] for f in facts}) == 3
    assert {f['source_category'] for f in facts} == {'simulation', 'interface_metrics'}
    assert all(f['record_ref'].startswith('S1:') for f in facts)


def test_same_interface_overlapping_source_conflicts_are_retained_in_model_context():
    context, refs = evidence_case()
    model = SimpleNamespace(generate=AsyncMock(return_value=(json.dumps({
        'answer': 'Willow has conflicting recorded traffic values; Hazel has 24000 bps. [S1]',
        'sources': ['S1']}), 'mock')), available=lambda _: False)
    asyncio.run(synthesize(model, None, 'Explain the returned interface measurement series.',
                           context, refs, {}, 'records'))
    supplied = model.generate.call_args.args[0][-1]['content']
    assert 'record_ref' in supplied and 'source_category' in supplied
    assert 'conflicting_observations' in supplied
    assert all(value in supplied for value in ['71000000', '2000', '72000000', '3000'])


@pytest.mark.parametrize('answer', [
    'Hazel has peak utilization of 72%. [S1]',
    'Hazel has peak utilization of 24%. [S1]',
    'Willow has a 30-second window and sampling interval of 30 seconds. [S1]',
])
def test_calculated_claims_cannot_borrow_another_scope_or_sampling_interval(answer):
    context, refs = evidence_case()
    errors=check_candidate('Willow has conflicting observations. '+answer, context, refs, {}, question='Explain the measurements.')
    assert any('returned calculation' in error for error in errors)


def test_valid_scoped_calculation_and_conflict_qualification_remain_accepted():
    context, refs = evidence_case()
    answer = ('Willow has conflicting observations. The modeled series has peak utilization of 72% '
              'over a 60-second window, with a sampling interval of 30 seconds. '
              'Hazel records 24000 bps; its utilization is not established. [S1]')
    assert not check_candidate(answer, context, refs, {}, question='Explain the measurements.')


def test_separate_timestamps_and_units_do_not_fabricate_a_conflict():
    from llm.orchestration.synthesis import metric_conflicts
    context, refs = evidence_case()
    context[0]['data']['records'][0]['samples'] = [
        {'timestamp': '2026-10-24T01:00:00Z', 'value': 2000}]
    assert metric_conflicts(metric_observations(context, refs)) == []
    context[0]['data']['records'][0]['samples'] = [
        {'timestamp': '2026-10-24T02:01:00Z', 'value': 72000000}]
    assert metric_conflicts(metric_observations(context, refs)) == []


def test_a_measured_percent_gauge_is_not_mistaken_for_an_invented_derived_rate():
    context=[{'tool':'network.telemetry','status':'success','evidence_ids':['m'],'data':{'records':[
        {'hostname':'Hazel','metric':'cpu_pct','unit':'percent','samples':[
            {'timestamp':'2026-10-24T02:01:00Z','value':18}]}]}}]
    refs=[Evidence(id='m',source='measured CPU',origin='stored')]
    good='Hazel CPU utilization is 18% at 2026-10-24T02:01:00Z. [S1]'
    assert not check_candidate(good,context,refs,{},question='Explain the CPU measurement.')
    assert check_candidate(good.replace('18%','24%'),context,refs,{},question='Explain the CPU measurement.')


def test_negation_of_a_rate_does_not_negate_an_earlier_window_claim():
    context,refs=evidence_case()
    text='Willow has conflicting observations. Its window length is 30 seconds, and a counter rate is not established. [S1]'
    assert any('window_duration' in e for e in check_candidate(text,context,refs,{},question='Explain the window.'))
    text=text.replace('30 seconds','60 seconds')
    assert not check_candidate(text,context,refs,{},question='Explain the window.')


def test_counter_delta_is_not_a_rate_and_reset_is_not_a_monotonic_decrease():
    context,refs=evidence_case();record=context[0]['data']['records'][1]
    record.update(metric='discards',unit='count',delta=6,average_per_second=0.1)
    record['samples']=[{'timestamp':'2026-10-24T02:00:00Z','value':16},
                       {'timestamp':'2026-10-24T02:01:00Z','value':22}]
    context[0]['data']['records']=[record]
    assert any('average_per_second' in e for e in check_candidate('Willow discard rate is 6 count per second at02:01:00Z. [S1]',context,refs,{},question='Explain the rate.'))
    assert not check_candidate('Willow discard rate is 0.1 count per second at02:01:00Z. [S1]',context,refs,{},question='Explain the rate.')
    record.update(counter_reset_or_wrap=True)
    record.pop('average_per_second');record.pop('delta')
    record['samples']=[{'timestamp':t,'value':v} for t,v in [
        ('2026-10-24T02:00:00Z',200),('2026-10-24T02:00:30Z',3),('2026-10-24T02:01:00Z',9)]]
    assert check_candidate('Willow shows a steady decrease in counters.',context,refs,{},question='Explain the series.')
    assert not check_candidate('Willow counter fell and then rose after a reset at02:01:00Z; a rate across the reset is not established. [S1]',context,refs,{},question='Explain the series.')
