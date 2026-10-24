"""Bounded forwarding assertions: direction, missing evidence and point time.

These are generalized neighbors of actual G6 model failures, not a universal
natural-language verifier or a new forwarding implementation.
"""
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def flow(forward='failed', reason='no route', back='delivered'):
    return {'source_device': 'Fir-Edge', 'destination_device': 'Elm-Edge',
            'forward': {'status': forward, 'branches': [{'status': forward, 'reason': reason, 'path': ['Fir-Edge']}]},
            'return': {'status': back, 'branches': [{'status': back, 'reason': 'destination address reached', 'path': ['Elm-Edge', 'Birch-Core', 'Fir-Edge']}]}}


@pytest.mark.parametrize('answer,record,expected', [
    ('The intermediate device Birch-Core is a potential point of failure, as it is not part of the declared path.', flow(), 'recorded path'),
    ('The incomplete routing table prevents the delivery of the forward flow.', flow('unknown', 'routing table unavailable'), 'unknown'),
    ('The devices are not configured with the necessary routing information.', flow('unknown', 'routing table unavailable', 'unknown'), 'configuration'),
    ('The successful return shows the forwarding loop is not a permanent issue.', flow(reason='forwarding loop'), 'duration'),
    ('There is a loop in the forward path, which is not supported by the simulation source.', flow(reason='forwarding loop'), 'denies'),
    ('The forward and return flow between Fir-Edge and Elm-Edge is not declared.', flow('unknown', 'routing table unavailable', 'unknown'), 'declared'),
])
def test_rejects_unsupported_forwarding_relationship_or_conclusion(answer, record, expected):
    from llm.orchestration.synthesis import forwarding_claim_errors
    assert any(expected in error for error in forwarding_claim_errors(answer, [record]))


@pytest.mark.parametrize('answer,record', [
    ('Forward delivery is unknown because the routing table is unavailable. Return delivery is recorded through Birch-Core.', flow('unknown', 'routing table unavailable')),
    ('The recorded forward loop blocks this flow; a working return does not establish whether the loop is temporary.', flow(reason='forwarding loop')),
    ('Birch-Core appears in the recorded return path. The forward calculation stopped at Fir-Edge with no route.', flow()),
    ('The unavailable routing table does not establish whether the devices are configured with the necessary routes.', flow('unknown', 'routing table unavailable', 'unknown')),
])
def test_keeps_evidence_qualified_explanation(answer, record):
    from llm.orchestration.synthesis import forwarding_claim_errors
    assert forwarding_claim_errors(answer, [record]) == []


def test_return_destination_is_bound_to_the_reverse_traffic_tuple():
    from llm.orchestration.synthesis import forwarding_claim_errors
    record=flow('delivered','destination reached','failed')
    record['traffic_scope']={'source_address':'198.18.1.1','destination_address':'198.18.1.3'}
    record['return']['branches']=[{'status':'failed','reason':'no route','path':['Elm-Edge']}]
    wrong='The return direction fails at Elm-Edge because there is no route to the destination address198.18.1.3.'
    assert forwarding_claim_errors(wrong,[record])
    good='The forward destination is198.18.1.3. The return destination is198.18.1.1; the return branch stops at Elm-Edge with no route.'
    assert not forwarding_claim_errors(good,[record])
    assert forwarding_claim_errors('The return direction fails at Elm-Edge. There is no route to the destination address198.18.1.3.',[record])


def test_declared_flow_endpoint_cannot_be_called_outside_tested_scope():
    from llm.orchestration.synthesis import forwarding_claim_errors
    assert forwarding_claim_errors('Elm-Edge is not part of the tested scope, while Fir-Edge is fully supported.',[flow()])
    assert forwarding_claim_errors('Elm-Edge is not part of the forwarding assessment, while Fir-Edge is.',[flow()])
    assert not forwarding_claim_errors('The declared endpoints are Fir-Edge and Elm-Edge; this test does not establish traffic outside the tested scope.',[flow()])


def test_named_transit_on_one_direction_cannot_be_assigned_to_the_other():
    from llm.orchestration.synthesis import forwarding_claim_errors
    record=flow('delivered','destination reached','failed')
    record['forward']['branches'][0]['path']=['Fir-Edge','Birch-Core','Elm-Edge']
    record['return']['branches']=[{'status':'failed','reason':'no route','path':['Elm-Edge']}]
    wrong='The recorded return path traverses Birch-Core and ends at Elm-Edge, where the failure occurred.'
    assert forwarding_claim_errors(wrong,[record])
    good='The forward path traverses Birch-Core. The recorded return branch stops at its origin Elm-Edge; it does not establish return transit through Birch-Core.'
    assert not forwarding_claim_errors(good,[record])


def test_literal_paths_preserve_each_recorded_branch_and_hop_order():
    from llm.orchestration.synthesis import forwarding_claim_errors
    record=flow('delivered','destination reached')
    record['forward']['branches']=[{'status':'delivered','reason':'destination reached','path':['Fir-Edge','Elm-Edge']},
        {'status':'delivered','reason':'destination reached','path':['Fir-Edge','Birch-Core','Elm-Edge']}]
    good='Forward paths: Fir-Edge → Elm-Edge and Fir-Edge → Birch-Core → Elm-Edge. Return path: Elm-Edge → Birch-Core → Fir-Edge.'
    assert not forwarding_claim_errors(good,[record])
    wrong='Forward path: Fir-Edge → Birch-Core → Elm-Edge. Return path: Birch-Core → Elm-Edge → Fir-Edge.'
    assert forwarding_claim_errors(wrong,[record])
    wrong='Forward paths:\n- Fir-Edge → Birch-Core → Elm-Edge\n- Fir-Edge → Birch-Core → Elm-Edge'
    assert forwarding_claim_errors(wrong,[record])
    good='Forward paths:\n- Fir-Edge → Elm-Edge\n- Fir-Edge → Birch-Core → Elm-Edge'
    assert not forwarding_claim_errors(good,[record])


def test_peer_roles_are_protocol_context_not_device_inventory_attributes():
    from llm.gateway_references import resolve_read,attributes
    inventory={'devices':[{'id':7,'hostname':'Pine','management_ip':'192.0.2.7','aliases':[],'interfaces':[]}]}
    query='Explain recorded protocol observations for Pine, comparing actual peer roles and prerequisite differences.'
    assert attributes(query)==[]
    assert resolve_read(query,None,inventory)['domains']==['state']
    assert attributes('What is the recorded role of device Pine?')==['role']


def test_reader_name_does_not_narrow_a_shared_measurement_domain_to_cpu_samples():
    from development.source_registry import explicit_read_sources
    available=['telemetry','interface_metrics']
    assert explicit_read_sources('Use only the telemetry reader to explain interface measurements.',available)==[]
    assert explicit_read_sources('Read telemetry samples for Pine.',available)==['telemetry']
    assert explicit_read_sources('Read interface counters from the telemetry reader.',available)==['interface_metrics']


def test_raw_telemetry_cannot_substitute_for_a_requested_modeled_series_assessment():
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from llm.orchestration.synthesis import synthesize
    context=[{'tool':'network.telemetry','status':'success','data':{'records':[
        {'kind':'interface_counters','metric':'out_bps','value':16000,'unit':'bits_per_second'}]}}]
    model=SimpleNamespace(generate=AsyncMock(side_effect=AssertionError('No requested derived records')))
    answer,metadata=asyncio.run(synthesize(model,None,'Explain the modeled interface measurement series, rates and congestion.',context,[],{},'raw records'))
    assert metadata['status']=='missing_modeled_series_fallback' and not metadata['model_synthesis']
    assert 'did not return the requested' in answer and 'does not establish' in answer
    model.generate.assert_not_awaited()


def test_partial_ecmp_fallback_does_not_describe_a_complete_outage():
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from fastapi import HTTPException
    from llm.orchestration.synthesis import synthesize
    context=[{'tool':'network.state','status':'success','data':{'records':[{'kind':'forwarding_assessment',
        'flow':{'source_device_id':1,'destination_device_id':3,'source_address':'198.18.1.1','destination_address':'198.18.1.3'},
        'assessment':{'forward':{'status':'partial','branches':[
            {'status':'delivered','reason':'destination reached','hops':[{'hostname':'Fir-Edge'}]},
            {'status':'failed','reason':'egress interface down','hops':[{'hostname':'Fir-Edge'}]}]},
            'return':{'status':'delivered','branches':[{'status':'delivered','reason':'destination reached','hops':[{'hostname':'Elm-Edge'}]}]}}}]}}]
    model=SimpleNamespace(generate=AsyncMock(side_effect=HTTPException(503,'offline')))
    answer,metadata=asyncio.run(synthesize(model,None,'Assess the forward and return paths.',context,[],{},'raw'))
    assert not metadata['model_synthesis']
    assert 'Delivery depends on the selected modeled branch' in answer
    assert 'does not establish a complete outage' in answer
    assert 'Two-way delivery is not established' not in answer


def test_both_unknown_directions_release_only_scoped_facts_without_model_inference():
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from llm.gateway_models import Evidence
    from llm.orchestration.synthesis import synthesize
    context=[{'tool':'network.state','status':'success','evidence_ids':['flow'],
        'scope_devices':[{'id':1,'hostname':'Fir-Edge'},{'id':3,'hostname':'Elm-Edge'}],
        'data':{'records':[{'kind':'forwarding_assessment','timestamp':'2026-10-18T01:00:00Z',
            'flow':{'source_device_id':1,'destination_device_id':3,'source_address':'198.18.1.1','destination_address':'198.18.1.3','vrf':'RED','protocol':'icmp'},
            'assessment':{direction:{'status':'unknown','branches':[{'status':'unknown','reason':'routing table unavailable','hops':[]}]} for direction in ['forward','return']}}]}}]
    model=SimpleNamespace(generate=AsyncMock(side_effect=AssertionError('No unsupported causal inference')))
    answer,metadata=asyncio.run(synthesize(model,'qwen2.5:1.5b','Assess the declared forward and return flow.',context,
        [Evidence(id='flow',source='Declared flow',origin='simulated')],{},'unused raw records'))
    assert metadata['status']=='insufficient_flow_evidence_fallback' and not metadata['model_synthesis']
    assert 'Forward: **unknown**; return: **unknown**' in answer
    assert '2026-10-18T01:00:00Z' in answer and 'VRF `RED`' in answer
    assert 'does not establish missing device configuration or an outage' in answer
    assert '- Forward: routing table unavailable.' in answer and ':  —' not in answer
    assert 'Next check:' in answer and '[S1]' in answer
    model.generate.assert_not_awaited()
