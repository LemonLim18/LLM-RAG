"""Source contract acceptance, separate from model reasoning and GUI acceptance.

These exercise the registered authorized readers against a complete sealed
scenario, including every declared availability state. They neither invent a
reader for conversation setup nor substitute a publication for a V9 reference.
"""
import asyncio
import json
from pathlib import Path
import sys

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from development.bundles import load_bundle
from development.source_registry import SOURCES, STATUSES
from db.manager import DatabaseManager
from llm.gateway_services import registry_for
from llm.tools import ToolAuthorization
from local_providers.development import ScenarioManager

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('status', ['MISSING', 'UNAVAILABLE', 'STALE', 'ERROR', 'CONFLICTING', 'UNSUPPORTED', 'NOT_QUERIED'])
def test_exceptional_source_metadata_survives_fallback_without_an_explicit_metadata_question(status):
    from llm.orchestration.synthesis import source_envelopes, source_metadata_footer
    context = [{'tool': 'network.state', 'status': 'error' if status == 'ERROR' else 'unavailable',
                'data': {'records': [], 'source_statuses': {'device_state': status},
                         'source_captures': {'device_state': '2026-10-18T01:00:00+00:00'}}}]
    answer, added = source_metadata_footer('The interface reader is unavailable for LAB-R1. [S1]',
                                            source_envelopes(context), 'What state is LAB-R1 in?')
    assert added and '**' + status + '**' in answer
    assert 'source captured `2026-10-18T01:00:00+00:00`' in answer
    assert 'LAB-R1' in answer and '[S1]' in answer


@pytest.mark.parametrize('status', ['error', 'unavailable', 'unsupported'])
def test_failed_readers_cannot_be_synthesized_into_network_observations(status):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from llm.orchestration.synthesis import synthesize
    context = [{'tool': 'network.state', 'status': status,
                'data': {'records': [], 'source_statuses': {'device_state': 'ERROR'},
                         'source_captures': {'device_state': '2026-10-18T01:00:00Z'}}}]
    model = SimpleNamespace(generate=AsyncMock(return_value=(
        '{"answer":"The administrative state is ERROR","sources":[],"hypotheses":[]}', 'test')))
    fallback = 'The requested interface-state reader is unavailable for LAB-R1. No interface state is established. [S1]'
    answer, trace = asyncio.run(synthesize(model, None, 'What is its state?', context, [], {}, fallback))
    model.generate.assert_not_awaited()
    assert trace['status'] == 'unavailable_sources_fallback' and not trace['model_synthesis']
    assert 'administrative state is ERROR' not in answer and answer.startswith(fallback)
    assert '**ERROR**' in answer and '2026-10-18T01:00:00Z' in answer


@pytest.mark.parametrize('source,domain', [('interface_metrics','telemetry'), ('running_configs','configuration'),
                                           ('device_state','state'), ('syslog','syslog')])
def test_named_interface_resolves_identity_without_replacing_requested_source(source, domain):
    from llm.gateway_references import resolve_read
    inventory = {'devices': [{'id':1100, 'hostname':'LAB-R1', 'management_ip':'192.0.2.1',
                              'aliases':[], 'interfaces':[{'id':1,'name':'GigabitEthernet0/1'}]}],
                 'logical_source_categories':[item.key for item in SOURCES]}
    title = next(item.title for item in SOURCES if item.key == source)
    route = resolve_read('Read only '+title+' for LAB-R1 GigabitEthernet0/1.', None, inventory)
    assert route['domains'] == [domain]
    assert route['device_refs'] == ['1100'] and route['interface_refs'] == ['1']
    assert route['source_requests'] == {domain:{'source_categories':[source]}}
    plain = resolve_read('What IP address does LAB-R1 GigabitEthernet0/1 have?', None, inventory)
    assert plain['domains'] == ['inventory'] and plain['interface_refs'] == ['1']


def test_drift_comparison_uses_literal_diff_renderer_without_claiming_change_history():
    from llm.gateway_findings import network_answer
    diff = '--- saved\n+++ current\n@@ -1 +1 @@\n-description Old\n+description New\n'
    context = [{'tool':'network.configuration','status':'success','evidence_ids':[],
                'data':{'records':[{'kind':'configuration_drift','hostname':'LAB-R1',
                                  'timestamp':'2026-10-18T01:00:00Z','diff':diff,
                                  'drift_detected':True,'saved_record_id':'saved-1100',
                                  'current_record_id':'active-1100','semantic_or_device_validation':'not_performed'}]}}]
    answer = network_answer(context, [], question='Explain the recorded configuration drift.')
    assert 'Recorded drift comparison for LAB-R1' in answer
    assert '```diff\n'+diff in answer and '\\n-description' not in answer
    assert 'saved-1100' in answer and 'active-1100' in answer
    assert 'does not establish an intervening change event' in answer
    assert 'not_performed' in answer
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from llm.orchestration.synthesis import synthesize
    model = SimpleNamespace(generate=AsyncMock(side_effect=AssertionError('Partial diffs cannot establish full protocol semantics')))
    displayed, trace = asyncio.run(synthesize(model, None, 'Explain this drift.', context, [], {}, answer))
    model.generate.assert_not_awaited()
    assert displayed == answer and trace['status'] == 'literal_comparison_fallback'
    assert not trace['model_synthesis']


def test_observation_time_cannot_be_replaced_by_later_source_capture_time():
    from llm.orchestration.synthesis import source_envelope_errors
    context=[{'tool':'network.state','status':'success','data':{
        'source_statuses':{'routing_state':'AVAILABLE'},
        'source_captures':{'routing_state':'2026-10-18T01:04:00Z'},
        'records':[{'kind':'routing_table','timestamp':'2026-10-18T01:03:00Z'}]}}]
    assert source_envelope_errors("The observation time is '2026-10-18T01:04:00Z'.",context,'Give observation and capture time.')
    assert not source_envelope_errors("The observation time is '2026-10-18T01:03:00Z'. Source captured at 2026-10-18T01:04:00Z.",context,'Give both times.')


@pytest.fixture
def source_runtime(tmp_path, monkeypatch):
    monkeypatch.setenv('COGNISHIELD_MODE', 'local_lab')
    monkeypatch.setenv('COGNISHIELD_DEV_WORKBENCH', '1')
    db = DatabaseManager(str(tmp_path / 'ordinary.db'))
    db.initialize()
    manager = ScenarioManager(tmp_path / 'scenario.json', enabled_default=False)
    db._development_scenario = manager
    try:
        yield db, manager, registry_for(db)
        with db._connect() as connection:
            assert connection.execute('SELECT count(*) FROM devices').fetchone()[0] == 0
    finally:
        db.close()


def test_all_24_sources_map_to_existing_read_or_owned_conversation_contract(source_runtime):
    _, _, registry = source_runtime
    assert len(SOURCES) == len({source.key for source in SOURCES}) == 24
    for source in SOURCES:
        schema = json.loads((ROOT / 'development/schemas/v1' / (source.key + '.schema.json')).read_text(encoding='utf-8'))
        assert set(schema['properties']['status']['enum']) == set(STATUSES)
        if source.tool == 'conversation.turn':
            assert source.key == 'conversation'
            # This uses owner-bound turn ingestion, not a fictional callable tool.
            assert registry.capability(source.tool) is None
            continue
        capability = registry.capability(source.tool)
        assert capability and capability.effect == 'read'
        assert capability.assistants == frozenset({'floating', 'studio'})
        assert capability.required_permissions == frozenset({'network.inventory.read'})
        assert capability.input_model.model_json_schema()['additionalProperties'] is False


@pytest.mark.parametrize('status', STATUSES)
def test_all_network_sources_preserve_status_revision_and_unavailable_boundaries(source_runtime, status):
    _, manager, registry = source_runtime
    bundle = load_bundle(ROOT / 'development/scenarios/healthy_all_sources_v2')
    network_sources = [source for source in SOURCES if source.tool.startswith('network.')]
    for source in network_sources:
        bundle['sources'][source.key]['status'] = status
    draft = manager.save_draft(bundle, owner='source-owner', expected=None)
    receipt = manager.validate_draft(draft['draft_id'], owner='source-owner', expected=1)
    manager.activate_draft(draft['draft_id'], owner='source-owner', expected=1,
        expected_active=manager.snapshot()[1]['source_revision'], validation_hash=receipt['validation_hash'])
    revision = manager.snapshot()[1]['source_revision']

    async def exercise():
        for surface in ['floating', 'studio']:
            auth = ToolAuthorization('source-owner', 'engineer', surface, 'contract-only',
                frozenset(source.tool for source in network_sources))
            for source in network_sources:
                arguments = {'device_refs': ['LAB-R1'], 'source_categories': [source.key]}
                if source.key == 'config_snapshots': arguments['source_scope'] = 'historical'
                if source.key == 'topology_history': arguments['source_scope'] = 'historical'
                result = await registry.invoke(source.tool, arguments, auth)
                assert result.data['source_statuses'] == {source.key: status}, (source.key, result)
                assert result.data['scenario']['source_revision'] == revision
                assert result.evidence and all(e.origin == 'simulated' for e in result.evidence)
                assert all(e.source_revision == revision for e in result.evidence)
                assert all(e.captured_at == result.data['source_captures'][source.key] for e in result.evidence)
                if status == 'STALE':assert all(e.freshness == 'stale' for e in result.evidence)
                # The explicit observed category means current observations.
                # A stale observation is withheld instead of being relabelled
                # current; its source envelope must still retain STALE.
                withheld_current = source.key == 'topology_observed' and status == 'STALE'
                if status in {'AVAILABLE', 'STALE', 'CONFLICTING'} and not withheld_current:
                    assert result.status == 'success', (source.key, status, result)
                else:
                    assert result.status == ('error' if status == 'ERROR' else 'unavailable')
                    assert result.data['records'] == [], (source.key, status)
                    assert not result.data.get('links'), (source.key, status)
                denied = ToolAuthorization('source-owner', 'engineer', surface, 'contract-only',
                    frozenset({source.tool}), permissions=frozenset())
                with pytest.raises(HTTPException) as error:
                    await registry.invoke(source.tool, arguments, denied)
                assert error.value.status_code == 403
    asyncio.run(exercise())


@pytest.mark.parametrize('status', ['STALE', 'ERROR', 'MISSING'])
def test_historical_topology_answer_distinguishes_event_time_capture_and_reader_status(source_runtime, status):
    from llm.gateway_findings import network_answer
    _, manager, registry = source_runtime
    bundle = load_bundle(ROOT / 'development/scenarios/healthy_all_sources_v2')
    source = bundle['sources']['topology_history']
    source.update(status=status, captured_at='2026-10-18T01:00:30Z')
    source['data']['records'][0]['timestamp'] = '2026-10-18T00:57:00Z'
    bundle['manifest']['clock']['now'] = '2026-10-18T01:01:00Z'
    draft = manager.save_draft(bundle, owner='source-owner', expected=None)
    receipt = manager.validate_draft(draft['draft_id'], owner='source-owner', expected=1)
    manager.activate_draft(draft['draft_id'], owner='source-owner', expected=1,
        expected_active=manager.snapshot()[1]['source_revision'], validation_hash=receipt['validation_hash'])
    auth = ToolAuthorization('source-owner', 'engineer', 'floating', 'contract-only', frozenset({'network.topology'}))
    result = asyncio.run(registry.invoke('network.topology', {'device_refs':['LAB-R1'], 'source_categories':['topology_history']}, auth))
    answer = network_answer([{'tool':'network.topology','status':result.status,'message':result.message,'scope_devices':[{'id':1100,'hostname':'LAB-R1'}],
        'data':result.data,'evidence_ids':[e.id for e in result.evidence]}], result.evidence)
    assert status in answer and 'topology_history' in answer and '2026-10-18T01:00:30' in answer
    if status == 'STALE':
        assert '2026-10-18T00:57:00' in answer and 'Historical topology' in answer
    else:
        assert 'unavailable' in answer and 'does not establish the absence' in answer
        assert 'For LAB-R1:' in answer
        assert '2026-10-18T00:57:00' not in answer


@pytest.mark.parametrize('claim', [
    'The topology has not been updated since the source capture time.',
    'The source was captured at time unspecified.',
])
def test_source_snapshot_does_not_certify_update_absence_or_contradict_its_capture(claim):
    from llm.orchestration.synthesis import source_envelope_errors
    context = [{'tool':'network.topology','status':'unavailable','data':{
        'source_statuses':{'topology_observed':'STALE'},
        'source_captures':{'topology_observed':'2026-10-18T01:00:00Z'}}}]
    assert source_envelope_errors('STALE. '+claim,context,'Read observed topology.')
    assert not source_envelope_errors('STALE source captured at 2026-10-18T01:00:00Z; intervening updates are unknown.',context,'Read observed topology.')
    assert not source_envelope_errors('STALE. We cannot establish that the topology has not been updated since the capture.',context,'Read observed topology.')


def test_event_timestamps_cannot_be_used_as_the_source_capture():
    from llm.orchestration.synthesis import source_envelope_errors
    context=[{'tool':tool,'status':'success','data':{'source_statuses':{category:'AVAILABLE'},
        'source_captures':{category:'2026-10-18T01:00:00+00:00'}}}
        for tool,category in [('network.syslog','syslog'),('network.incidents','incidents')]]
    assert source_envelope_errors('The records were captured at the same time, 2026-10-18T00:55:00+00:00.',context,'Give separate event times.')
    assert source_envelope_errors('Both sources were captured at 00:55:00.',context,'Give separate event times.')
    assert not source_envelope_errors('Both sources were captured at 2026-10-18T01:00:00Z. Events occurred at 00:55:00 and 00:59:30.',context,'Give separate event times.')


def test_event_fallback_explains_recorded_state_and_keeps_event_capture_times_separate():
    from llm.gateway_findings import network_answer
    from llm.gateway_models import Evidence
    evidence=Evidence(id='incident',source='development.incidents',origin='simulated')
    context=[{'tool':'network.incidents','status':'success','evidence_ids':['incident'],'data':{
        'source_statuses':{'incidents':'AVAILABLE'},'source_captures':{'incidents':'2026-10-18T01:00:00Z'},
        'records':[{'hostname':'LAB-R1','timestamp':'2026-10-18T00:55:00Z','state':'resolved',
            'severity':'info','summary':'Scheduled routing maintenance completed'}]}}]
    answer=network_answer(context,[evidence])
    assert 'Recorded status: **resolved**' in answer
    assert 'event recorded `2026-10-18T00:55:00Z`' in answer
    assert 'captured `2026-10-18T01:00:00Z`' in answer
    assert 'Scheduled routing maintenance completed' in answer and '|---' not in answer


def test_invalid_model_fallback_keeps_request_reference_separate_from_published_knowledge():
    from unittest.mock import AsyncMock
    from types import SimpleNamespace
    from llm.gateway_models import Evidence
    from llm.orchestration.synthesis import synthesize
    reference={'query':'Explain published configure_ospf method requirements','status':'AVAILABLE','captured_at':'2026-10-18T01:04:00Z'}
    context=[{'tool':'knowledge.search','status':'success','evidence_ids':['ref'],'data':[{'scenario_reference':reference}]}]
    model=SimpleNamespace(generate=AsyncMock(return_value=('invalid JSON','test-model')))
    answer,trace=asyncio.run(synthesize(model,'test-model','Read this scenario knowledge reference.',context,
        [Evidence(id='ref',source='development.knowledge_reference',origin='simulated',authority='development_scenario_reference')],{},'Verified contract excerpt.'))
    assert 'Scenario knowledge reference (retrieval request only)' in answer
    assert '2026-10-18T01:04:00Z' in answer and 'AVAILABLE' in answer
    assert trace['status']=='unavailable_fallback' and trace['display_source_metadata_added']
    assert model.generate.await_count==2 and all(a['raw_output']=='invalid JSON' for a in trace['attempts'])
    assert not trace['model_synthesis']


STARTER_ORACLES=json.loads((ROOT/'development/test_oracles/phase_g_starters.json').read_text(encoding='utf-8'))['cases']


@pytest.mark.parametrize('oracle',STARTER_ORACLES,ids=[row['id'] for row in STARTER_ORACLES])
def test_complete_starter_expectations_remain_private_to_the_evaluator(source_runtime,oracle):
    from development.bundles import safe_file
    _,manager,registry=source_runtime
    bundle=load_bundle(ROOT/'development/scenarios'/oracle['bundle'])
    assert len(bundle['sources'])==24
    draft=manager.save_draft(bundle,owner='source-owner',expected=None)
    receipt=manager.validate_draft(draft['draft_id'],owner='source-owner',expected=1)
    manager.activate_draft(draft['draft_id'],owner='source-owner',expected=1,
        expected_active=manager.snapshot()[1]['source_revision'],validation_hash=receipt['validation_hash'])
    auth=ToolAuthorization('source-owner','engineer','floating','contract-only',frozenset({'network.state'}))
    result=asyncio.run(registry.invoke('network.state',{'device_refs':['LAB-R1','LAB-R3'],'source_categories':['simulation']},auth))
    records=result.data['records']
    flow=next(row for row in records if row['kind']=='forwarding_assessment' and row['flow']['id']==oracle['flow'])
    assert flow['assessment']['forward']['status']==oracle['expected_forward']
    assert flow['assessment']['return']['status']==oracle['expected_return']
    if oracle.get('expected_drop_reason'):
        assert any(oracle['expected_drop_reason'] in str(row.get('reason','')).lower() for row in flow['assessment']['forward']['branches'])
    if oracle.get('expected_protocol_conflict'):
        assert any(row.get('conflict') for row in records if row['kind']=='protocol_assessment')
    if oracle.get('expected_syslog_status'):
        assert bundle['sources']['syslog']['status']==oracle['expected_syslog_status']
    # Neither the reader's evidence nor its activated pack contains answer keys.
    visible=json.dumps({'tool_result':result.model_dump(),'pack':manager.activated_bundle()})
    assert oracle['id'] not in visible and 'expected_forward' not in visible
    with pytest.raises(ValueError,match='oracle'):
        safe_file(ROOT/'development/test_oracles','phase_g_starters.json')
    with pytest.raises(ValueError,match='oracle'):
        safe_file(ROOT/'development','test_oracles/phase_g_starters.json')


def test_complete_bundle_cli_clone_export_and_diff_preserve_inputs_and_require_new_outputs(capsys):
    import tempfile
    import hashlib
    from types import SimpleNamespace
    from scripts.development_scenario import main,ROOT as PROJECT
    from development.bundles import compile_bundle
    source=ROOT/'development/scenarios/healthy_all_sources_v2'
    original=(source/'inventory.json').read_bytes()
    with tempfile.TemporaryDirectory(dir=PROJECT/'tmp/phase-g',prefix='g2-clone-') as directory:
        folder=Path(directory);target=folder/'cloned'
        clone=SimpleNamespace(command='bundle-clone',directory=str(source),id='G2-CLONED-SOURCE',output=str(target))
        asyncio.run(main(clone))
        cloned=load_bundle(target)
        assert len(cloned['sources'])==24 and cloned['manifest']['scenario_id']=='G2-CLONED-SOURCE'
        assert cloned['manifest']['source_hashes']=={}  # editable starter stays editable
        output=folder/'export.json'
        asyncio.run(main(SimpleNamespace(command='bundle-export',directory=str(target),output=str(output))))
        exported=json.loads(output.read_text(encoding='utf-8'))
        assert compile_bundle(exported)['devices']==compile_bundle(cloned)['devices']
        # Ordinary external JSON editing must remain available without a hash
        # authoring ceremony. Explicit integrity locks remain enforceable.
        source_file=target/'inventory.json';value=json.loads(source_file.read_text(encoding='utf-8'))
        value['data']['devices'][0]['management_ip']='192.0.2.198'
        source_file.write_text(json.dumps(value,indent=2),encoding='utf-8')
        assert load_bundle(target)['sources']['inventory']['data']['devices'][0]['management_ip']=='192.0.2.198'
        manifest_file=target/'manifest.json';manifest=json.loads(manifest_file.read_text(encoding='utf-8'))
        manifest['source_hashes']['inventory']=hashlib.sha256(source_file.read_bytes()).hexdigest()
        manifest_file.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        original_clone_bytes=source_file.read_bytes();source_file.write_bytes(original_clone_bytes+b'\n')
        with pytest.raises(ValueError,match='hash differs'):load_bundle(target)
        source_file.write_bytes(original_clone_bytes)
        report=folder/'diff.json'
        asyncio.run(main(SimpleNamespace(command='bundle-diff',before=str(source),after=str(target),output=str(report))))
        diff=json.loads(report.read_text(encoding='utf-8'))
        assert diff['changed'] and not diff['activated']
        assert any(row['section']=='inventory' and '192.0.2.198' in row['diff'] for row in diff['sections'])
        assert (source/'inventory.json').read_bytes()==original
        with pytest.raises(ValueError,match='already exist'):asyncio.run(main(clone))
        with pytest.raises(FileExistsError):asyncio.run(main(SimpleNamespace(command='bundle-export',directory=str(target),output=str(output))))
        assert json.loads(output.read_text(encoding='utf-8'))==exported


def test_external_bgp_json_t1_t2_reaches_both_authorized_readers_without_rewriting_the_model(source_runtime,tmp_path):
    import shutil
    _,manager,registry=source_runtime
    source=ROOT/'development/scenarios/healthy_all_sources_v2';editable=tmp_path/'editable'
    shutil.copytree(source,editable)
    path=editable/'protocol_state.json';original=path.read_bytes()
    revisions=[]
    for state,stamp in [('Established','2026-10-18T01:00:00Z'),('Active','2026-10-18T01:01:00Z')]:
        document=json.loads(path.read_text(encoding='utf-8'))
        bgp=next(row for row in document['data']['records'] if row['values']['protocol']=='BGP')
        bgp['values']['observed_state']=state;bgp['timestamp']=stamp;document['captured_at']=stamp
        path.write_text(json.dumps(document,indent=2),encoding='utf-8')
        manifest_path=editable/'manifest.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
        manifest['clock']['now']=stamp;manifest_path.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        draft=manager.save_draft(load_bundle(editable),owner='source-owner',expected=None)
        receipt=manager.validate_draft(draft['draft_id'],owner='source-owner',expected=1)
        manager.activate_draft(draft['draft_id'],owner='source-owner',expected=1,
            expected_active=manager.snapshot()[1]['source_revision'],validation_hash=receipt['validation_hash'])
        revisions.append(manager.snapshot()[1]['source_revision'])
        for kind in ['floating','studio']:
            auth=ToolAuthorization('source-owner','engineer',kind,'contract-only',frozenset({'network.state'}))
            result=asyncio.run(registry.invoke('network.state',{'device_refs':['LAB-R2'],'source_categories':['protocol_state']},auth))
            row=next(row for row in result.data['records'] if row['protocol']=='BGP')
            assert row['observed_state']==state and row['timestamp']==stamp
            assert [(p['hostname'],p['local_address'],p['neighbor_address'],p['local_as'],p['remote_as']) for p in row['peer_parameters']]==[
                ('LAB-R2','10.72.0.5','10.72.0.6',65020,65030),('LAB-R3','10.72.0.6','10.72.0.5',65030,65020)]
            assert result.evidence[0].source_revision==revisions[-1]
        assert manager.snapshot()[0]['network']['bgp'][0]['observed_state']=='Established'
    assert len(set(revisions))==2 and (source/'protocol_state.json').read_bytes()==original
