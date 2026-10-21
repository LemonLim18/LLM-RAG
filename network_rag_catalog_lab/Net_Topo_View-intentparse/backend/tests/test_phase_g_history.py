"""Recorded scenario recovery: sealed files, ownership, CAS and pinned reads."""
from copy import deepcopy
import base64,hashlib,json,sys
from pathlib import Path
import pytest
from fastapi import HTTPException
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from local_providers.development import ScenarioManager
from tests.test_phase_g_workbench import draft_bundle


def bundle_at(stamp,marker):
    bundle=draft_bundle();bundle['manifest']['clock']['now']=stamp
    record=bundle['sources']['running_configs']['data']['records'][0]
    record['timestamp']=stamp;record['values']['config_text']='hostname LAB-R1\r\n! '+marker+'\r\n'
    raw=('Maintenance note '+marker+'.\n').encode();asset={'base64':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest()}
    bundle['assets']['docs/note.md']=asset
    bundle['sources']['documents'].update(status='AVAILABLE',captured_at=stamp,data={'files':[{'path':'docs/note.md','name':'History note.md'}]})
    return bundle


def activate(manager,bundle,owner='alice'):
    draft=manager.save_draft(bundle,owner=owner,expected=None)
    receipt=manager.validate_draft(draft['draft_id'],owner=owner,expected=1)
    manager.activate_draft(draft['draft_id'],owner=owner,expected=1,expected_active=manager.snapshot()[1]['source_revision'],validation_hash=receipt['validation_hash'])


def test_restore_archived_config_files_and_clock_as_a_new_revision(tmp_path):
    manager=ScenarioManager(tmp_path/'state.json',enabled_default=False)
    t1=bundle_at('2026-10-19T01:00:00Z','HISTORY_T1');t2=bundle_at('2026-10-19T01:01:00Z','HISTORY_T2')
    activate(manager,t1);first=manager.snapshot()[1];activate(manager,t2);second=manager.snapshot()[1]
    choice=next(row for row in manager.history(owner='alice') if row['scenario_id']=='S-TEST-BUNDLE')
    assert choice['restorable'] and 'bundle' not in choice and 'scenario' not in choice
    with manager.pin():
        old_assets=manager.activated_bundle()
        manager.restore_history(choice['id'],owner='alice',expected_active=second['source_revision'])
        assert manager.snapshot()[1]['source_revision']==second['source_revision']
        assert manager.activated_bundle()==old_assets
    restored,meta=manager.snapshot(fresh=True)
    assert meta['logical_time']==first['logical_time'] and meta['revision']>second['revision']
    assert meta['source_revision'] not in {first['source_revision'],second['source_revision']}
    assert restored['records']['running_configuration'][0]['values']['config_text'].endswith('HISTORY_T1\r\n')
    assert manager.activated_bundle()['assets']==t1['assets'] and manager.is_enabled()
    # Restore itself is recorded, so the replaced T2 state remains recoverable.
    assert any(row['virtual_now']==second['logical_time'] for row in manager.history(owner='alice'))


def test_restore_rejects_other_owner_stale_revision_and_corrupt_history(tmp_path):
    manager=ScenarioManager(tmp_path/'state.json',enabled_default=False)
    activate(manager,bundle_at('2026-10-19T01:00:00Z','T1'));old=manager.snapshot()[1]
    activate(manager,bundle_at('2026-10-19T01:01:00Z','T2'));current=manager.snapshot()[1]
    choice=next(row for row in manager.history(owner='alice') if row['scenario_id']=='S-TEST-BUNDLE')
    assert manager.history(owner='bob')==[]
    for owner,revision,status in [('bob',current['source_revision'],404),('alice',old['source_revision'],409)]:
        before=manager.path.read_bytes()
        with pytest.raises(HTTPException) as failure:manager.restore_history(choice['id'],owner=owner,expected_active=revision)
        assert failure.value.status_code==status and manager.path.read_bytes()==before
    state=manager._read();row=next(row for row in state['workbench_history'] if row['id']==choice['id'])
    row['bundle']['assets']['docs/note.md']['base64']='dGFtcGVyZWQ=';manager._write(state);before=manager.path.read_bytes()
    assert not next(row for row in manager.history(owner='alice') if row['id']==choice['id'])['restorable']
    with pytest.raises(HTTPException) as failure:manager.restore_history(choice['id'],owner='alice',expected_active=current['source_revision'])
    assert failure.value.status_code==409 and manager.path.read_bytes()==before


def test_history_api_keeps_admin_owner_boundary_and_does_not_expose_sealed_files(tmp_path):
    from types import SimpleNamespace
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from auth.auth import create_access_token
    from local_providers.development_api import router
    manager=ScenarioManager(tmp_path/'state.json',enabled_default=False)
    activate(manager,bundle_at('2026-10-19T01:00:00Z','T1'));activate(manager,bundle_at('2026-10-19T01:01:00Z','T2'))
    app=FastAPI();app.state.local_db=SimpleNamespace(_development_scenario=manager);app.include_router(router)
    with patch.dict('os.environ',{'COGNISHIELD_DEV_WORKBENCH':'1','COGNISHIELD_DEV_SIMULATION':'0'}),TestClient(app) as client:
        path='/api/v1/development-network/workbench'
        assert client.get(path).status_code==401
        client.headers['Authorization']='Bearer '+create_access_token(1,'alice','engineer')
        assert client.get(path).status_code==403
        client.headers['Authorization']='Bearer '+create_access_token(1,'alice','admin')
        state=client.get(path).json();choice=next(row for row in state['history'] if row['scenario_id']=='S-TEST-BUNDLE')
        assert all(value not in json.dumps(state['history']) for value in ['Maintenance note','config_text','base64'])
        client.headers['Authorization']='Bearer '+create_access_token(2,'bob','admin')
        assert client.get(path).json()['history']==[]
        assert client.post(path+'/history/'+choice['id']+'/restore',json={'expected_active':state['context']['source_revision']}).status_code==404
        assert client.post(path+'/history/'+choice['id']+'/draft').status_code==404
        client.headers['Authorization']='Bearer '+create_access_token(1,'alice','admin')
        before=manager.snapshot()[1]
        copied=client.post(path+'/history/'+choice['id']+'/draft')
        assert copied.status_code==200 and copied.json()['validation_hash'] is None
        assert b'T1' in base64.b64decode(copied.json()['bundle']['assets']['docs/note.md']['base64'])
        assert manager.snapshot()[1]==before
        client.headers['Authorization']='Bearer '+create_access_token(2,'bob','admin')
        assert client.get(path+'/drafts/'+copied.json()['draft_id']).status_code==404
        client.headers['Authorization']='Bearer '+create_access_token(1,'alice','admin')
        restored=client.post(path+'/history/'+choice['id']+'/restore',json={'expected_active':state['context']['source_revision']})
        assert restored.status_code==200 and restored.json()['context']['logical_time'].startswith('2026-10-19T01:00:00')
        assert client.post(path+'/history/'+choice['id']+'/restore',json={'expected_active':state['context']['source_revision']}).status_code==409
        corrupt=manager._read();corrupt['workbench_bundles'][corrupt['selected']]['assets']['docs/note.md']['base64']='dGFtcGVyZWQ=';manager._write(corrupt)
        recovery=client.get(path)
        assert recovery.status_code==200 and recovery.json()['active_source_error']
        restored=client.post(path+'/history/'+choice['id']+'/restore',json={'expected_active':recovery.json()['context']['source_revision']})
        assert restored.status_code==200 and not restored.json()['active_source_error']


def test_legacy_reset_does_not_reuse_files_from_a_different_pack_revision(tmp_path):
    manager=ScenarioManager(tmp_path/'state.json',enabled_default=False)
    bundle=bundle_at('2026-10-19T01:00:00Z','PRIVATE_PACK_FILE');bundle['manifest']['scenario_id']='HEALTHY-001'
    activate(manager,bundle);before=manager.snapshot()[1]['revision']
    with manager.pin():
        pinned=manager.activated_bundle()
        manager.change('reset',manager.snapshot()[1]['source_revision'],scenario_id='HEALTHY-001')
        assert manager.activated_bundle()==pinned
    assert manager.activated_bundle() is None
    assert manager.snapshot()[1]['revision']>before


def test_valid_restore_can_quarantine_a_corrupt_current_file_revision(tmp_path):
    manager=ScenarioManager(tmp_path/'state.json',enabled_default=False)
    activate(manager,bundle_at('2026-10-19T01:00:00Z','T1'))
    activate(manager,bundle_at('2026-10-19T01:01:00Z','T2'))
    choice=next(row for row in manager.history(owner='alice') if row['scenario_id']=='S-TEST-BUNDLE')
    state=manager._read();state['workbench_bundles'][state['selected']]['assets']['docs/note.md']['base64']='dGFtcGVyZWQ=';manager._write(state)
    manager.restore_history(choice['id'],owner='alice',expected_active=manager.snapshot()[1]['source_revision'])
    assert any(not row['restorable'] for row in manager.history(owner='alice'))
    assert b'T1' in base64.b64decode(manager.activated_bundle()['assets']['docs/note.md']['base64'])


def test_deactivation_retains_the_last_active_files_for_explicit_recovery(tmp_path):
    manager=ScenarioManager(tmp_path/'state.json',enabled_default=False);activate(manager,bundle_at('2026-10-19T01:00:00Z','T1'))
    manager.deactivate(owner='alice',expected_active=manager.snapshot()[1]['source_revision'])
    assert not manager.is_enabled()
    choice=next(row for row in manager.history(owner='alice') if row['scenario_id']=='S-TEST-BUNDLE')
    assert choice['restorable'] and choice['was_enabled']
    manager.restore_history(choice['id'],owner='alice',expected_active=manager.snapshot()[1]['source_revision'])
    assert manager.is_enabled()


def test_copy_recorded_sources_creates_an_owned_unvalidated_draft_only(tmp_path):
    manager=ScenarioManager(tmp_path/'state.json',enabled_default=False)
    t1=bundle_at('2026-10-19T01:00:00Z','T1');activate(manager,t1)
    activate(manager,bundle_at('2026-10-19T01:01:00Z','T2'));current=manager.snapshot()[1]
    choice=next(row for row in manager.history(owner='alice') if row['scenario_id']=='S-TEST-BUNDLE')
    copied=manager.copy_history_draft(choice['id'],owner='alice')
    assert copied['bundle']==t1 and copied['validation_hash'] is None
    assert manager.snapshot()[1]==current and manager.activated_bundle()!=t1
    with pytest.raises(HTTPException):manager.get_draft(copied['draft_id'],owner='bob')


def test_captured_config_is_readable_as_a_saved_capture_not_current_text(tmp_path):
    import asyncio
    from db.manager import DatabaseManager
    from llm.gateway import AIGateway
    from llm.gateway_store import ensure_schema
    from llm.tools import ToolAuthorization
    db=DatabaseManager(str(tmp_path/'app.db'));db.initialize();ensure_schema(db)
    manager=ScenarioManager(tmp_path/'state.json',enabled_default=False);db._development_scenario=manager
    try:
        activate(manager,bundle_at('2026-10-19T01:00:00Z','CAPTURED_VALUE'))
        capture=manager.capture(7001,manager.snapshot()[1]['source_revision'])
        gateway=AIGateway(db);cid=gateway.store.create('alice','floating')['id']
        auth=ToolAuthorization('alice','admin','floating',cid,frozenset({'network.configuration'}))
        with patch.dict('os.environ',{'COGNISHIELD_DEV_WORKBENCH':'1','COGNISHIELD_DEV_SIMULATION':'0'}):
            result=asyncio.run(gateway.registry.invoke('network.configuration',{'device_refs':['LAB-R1'],
                'source_scope':'historical','source_categories':['config_snapshots']},auth))
        row=next((row for row in result.data['records'] if row['id']==capture['id']),None)
        assert row and row['kind']=='configuration_snapshot' and row['current'] is False
        assert 'CAPTURED_VALUE' in row['config_text'] and result.evidence[0].origin=='simulated'
    finally:db.close()


def test_generated_captures_survive_successive_activations_without_reviving_deleted_authored_rows(tmp_path):
    manager=ScenarioManager(tmp_path/'state.json',enabled_default=False)
    activate(manager,bundle_at('2026-10-19T01:00:00Z','FIRST'))
    capture=manager.capture(7001,manager.snapshot()[1]['source_revision'])
    activate(manager,bundle_at('2026-10-19T01:01:00Z','SECOND'))
    third=bundle_at('2026-10-19T01:02:00Z','THIRD');third['sources']['config_snapshots']['data']['records']=[]
    activate(manager,third)
    rows=manager.snapshot()[0]['records']['configuration']
    assert any(row['id']==capture['id'] for row in rows)
    assert all(any(marker in row['values'].get('config_text','') for row in rows) for marker in ['FIRST','SECOND'])
    assert not any(row['id']=='saved-r1' for row in rows)
