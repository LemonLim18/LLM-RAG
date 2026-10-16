"""Isolated acceptance tests. No production DB or network adapter is used."""
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

TEST_DIR = Path(tempfile.mkdtemp(prefix='cognishield-m0-'))
os.environ['COGNISHIELD_MODE'] = 'local_lab'
os.environ['COGNISHIELD_DB_PATH'] = str(TEST_DIR / 'test.db')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from local_app import app
from lab_config import DB_PATH
from db.local_migrations import ensure_local_schema

@pytest.fixture
def client(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Unexpected network adapter or process execution')
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    with TestClient(app) as c:
        from auth.auth import create_access_token
        c.headers['Authorization'] = 'Bearer ' + create_access_token(1, 'm0-test', 'admin')
        yield c

def call(c, method, path, data=None, expected=200):
    r = c.request(method, '/api/v1' + path, json=data)
    assert r.status_code == expected, (path, r.status_code, r.text)
    return r.json()

def test_crud_restart_relationships_and_history(client):
    c = client
    a = call(c,'POST','/netbox/devices',{'hostname':'M0-test-a','management_ip':'192.0.2.11','management_subnet_mask':'24'})
    b = call(c,'POST','/netbox/devices',{'hostname':'M0-test-b','management_ip':'192.0.2.12','management_subnet_mask':'24'})
    assert a['netbox_sync_pending'] is False
    call(c,'POST','/netbox/devices',{'hostname':'M0-test-a'},409)
    call(c,'POST','/netbox/devices',{'hostname':' '},422)
    call(c,'POST','/netbox/devices',{'hostname':'bad-ip','management_ip':'not-an-ip'},400)
    call(c,'PUT',f"/netbox/devices/{a['id']}",{'hostname':'M0-test-renamed','model':'persisted'})
    ia = call(c,'POST',f"/netbox/devices/{a['id']}/interfaces",{'name':'Ethernet1','interface_type':'l2'})
    ib = call(c,'POST',f"/netbox/devices/{b['id']}/interfaces",{'name':'Ethernet1','interface_type':'l2'})
    call(c,'PUT',f"/netbox/devices/{a['id']}/interfaces/{ia['id']}",{'name':'Ethernet2'})
    payload = dict(src_device_id=a['id'],src_interface_id=ia['id'],dst_device_id=b['id'],dst_interface_id=ib['id'])
    link = call(c,'POST','/netbox/links',payload)
    call(c,'POST','/netbox/links',payload,409)
    call(c,'PUT',f"/netbox/links/{link['id']}",payload | {'discovery_protocol':'manual'})
    call(c,'PUT',f"/netbox/links/{link['id']}",payload | {'src_interface_id':ib['id']},422)
    call(c,'PUT',f"/netbox/devices/{a['id']}/interfaces/{ia['id']}",{'interface_type':'l3','ip_address':'192.0.2.1','subnet_mask':'24'},400)
    topology = call(c,'GET','/topology')
    assert topology['source']=='local_sqlite_inventory'
    assert topology['nodes']['M0-test-renamed']['connectedNode']==['M0-test-b']
    snapshot = call(c,'POST','/network/config-backup/import',{'device_id':a['id'],'config_text':'hostname M0-test-renamed\n','description':'isolated sample'})
    sid = snapshot['snapshot_id']
    call(c,'PATCH',f'/network/config-backup/snapshots/{sid}/description',{'description':'retained'})
    assert call(c,'GET',f'/network/config-backup/snapshots/{sid}/content')['config_text'].startswith('hostname')
    with sqlite3.connect(DB_PATH) as conn:
        assert conn.execute('PRAGMA foreign_key_check').fetchall()==[]
        assert conn.execute("SELECT count(*) FROM audit_log WHERE action='link.update'").fetchone()[0]==1
    # New application lifespan and connections read committed data.
    with TestClient(app) as restarted:
        restarted.headers.update(c.headers)
        assert call(restarted,'GET',f"/netbox/devices/{a['id']}")['model']=='persisted'
        assert len(call(restarted,'GET',f"/netbox/devices/{a['id']}/interfaces")['interfaces'])==1
        assert call(restarted,'GET',f'/network/config-backup/snapshots/{sid}/content')['config_text'].startswith('hostname')
    call(c,'DELETE',f'/network/config-backup/snapshots/{sid}')
    call(c,'DELETE',f"/netbox/devices/{a['id']}/interfaces/{ia['id']}")
    assert call(c,'GET','/netbox/links')['links']==[]
    call(c,'DELETE',f"/netbox/devices/{a['id']}")
    call(c,'DELETE',f"/netbox/devices/{b['id']}")
    assert any(row['action']=='device.delete' for row in call(c,'GET','/audit')['items'])

def test_offline_stable_and_no_remote_entrypoints(client, tmp_path, monkeypatch):
    c=client
    # This test deletes its inventory first. Repository demo telemetry references
    # device IDs 1/2 and must not become this test's authoritative observations.
    import local_app
    from local_providers.observations import JsonObservations
    (tmp_path/'observations.json').write_text('{"version":1,"defaults":{"availability":"up","metrics":[]}}',encoding='utf-8')
    monkeypatch.setattr(local_app,'observations',JsonObservations(tmp_path))
    assert call(c,'GET','/lab/capabilities')['scheduled_jobs']==[]
    assert app.state.remote_jobs==[]
    assert call(c,'GET','/monitor/metrics/dashboard-bundle')==call(c,'GET','/monitor/metrics/dashboard-bundle')
    for path in ['/netbox/sync/devices','/netbox/push-all','/topology/crawl','/ssh/sessions',
                 '/ansible/jobs/1/check','/ansible/jobs/1/execute','/agent/execute',
                 '/monitor/update-config','/syslog/sync-server',
                 '/sdn/controllers/1/sync']:
        call(c,'POST',path,{},503)
    # M0.2 provides a simulated service check; an absent saved NTP profile is
    # rejected before any check. The socket/process guards above remain active.
    call(c,'POST','/common-services/test-ntp',{},422)
    assert not {'integrated_backend','paramiko','pynetbox','chromadb','ansible_runner','scheduler.core','monitor.api','sdn.api'} & {name for name, module in sys.modules.items() if getattr(module, '__file__', None)}
    assert call(c,'GET','/ansible/files')['tree']
    with c.websocket_connect('/ws') as ws:
        assert ws.receive_json()['topology']['source']=='local_sqlite_inventory'

def test_policy_transaction_and_delete_audit(client):
    c=client
    policy={'policy_id':'m0-isolated-policy','name':'M0 Test','category':'ntp',
            'scope':{},'rules':[{'id':'r1','action':'must_exist','target':'ntp','value':'ntp server 192.0.2.1','severity':'low'}]}
    response=call(c,'POST','/policies',policy)
    assert response['policy']['policy_id']==policy['policy_id']
    call(c,'PUT','/policies/m0-isolated-policy',{'description':'persisted'})
    assert call(c,'GET','/policies/m0-isolated-policy/audit')['total']>=2
    call(c,'DELETE','/policies/m0-isolated-policy')
    assert any(r['action']=='policy.delete' and 'update' in r['details'] for r in call(c,'GET','/audit')['items'])

def test_legacy_migration_backup_idempotent(tmp_path):
    legacy=tmp_path/'legacy.db'
    original=Path(__file__).resolve().parents[2]/'net_topo.db'
    with sqlite3.connect(f'file:{original.as_posix()}?mode=ro',uri=True) as source:
        original_count=source.execute('SELECT count(*) FROM devices').fetchone()[0]
        with sqlite3.connect(legacy) as dest: source.backup(dest)
    ensure_local_schema(legacy)
    backups=list((tmp_path/'backups').glob('*.db'))
    assert len(backups)==1
    with sqlite3.connect(backups[0]) as backup:
        assert not backup.execute("SELECT 1 FROM sqlite_master WHERE name='schema_migrations'").fetchone()
    ensure_local_schema(legacy)
    assert len(list((tmp_path/'backups').glob('*.db')))==1
    with sqlite3.connect(legacy) as migrated:
        assert migrated.execute('SELECT count(*) FROM devices').fetchone()[0]==original_count
        assert migrated.execute('PRAGMA integrity_check').fetchone()[0]=='ok'

