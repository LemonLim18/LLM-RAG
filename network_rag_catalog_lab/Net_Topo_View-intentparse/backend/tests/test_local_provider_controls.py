"""Focused regression checks for the requested local controls, using isolated data."""
import json
from tests.test_m0_local import client, call
import local_app
from local_providers.observations import JsonObservations
from local_providers.workflows import LocalWorkflowProvider

def test_credentials_and_profile_tests(client):
    saved = call(client, 'POST', '/onboarding/ztp/server-credential', {
        'username': 'verification-user', 'password': 'disposable-test-value', 'label': 'TEST_ONLY'})
    assert saved['stored']
    status = call(client, 'GET', '/onboarding/ztp/server-credential?label=TEST_ONLY')
    assert status['configured'] and status['username'] == 'verification-user' and 'password' not in status
    result = call(client, 'POST', '/onboarding/ztp/server-credential/test', {'credential_label': 'TEST_ONLY'})
    assert result['ok'] and result['source'] == 'simulated'
    call(client, 'PUT', '/common-services/profiles/global/global', {'ntp_server_ip': '192.0.2.10', 'syslog_host_ip': '192.0.2.11'})
    for service in ('ntp', 'syslog'):
        assert call(client, 'POST', '/common-services/test-' + service)['source'] == 'simulated'

def test_split_refresh_and_configuration_restore(client, tmp_path, monkeypatch):
    device = call(client, 'POST', '/netbox/devices', {'hostname': 'fixture-controls', 'vendor': 'cisco_ios', 'management_ip': '192.0.2.90', 'management_subnet_mask': '24'})
    did = device['id']
    def write(name, value):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding='utf-8')
    write('observations.json', {'version': 1, 'defaults': {'availability': 'up'}})
    write('availability.json', {'devices': [{'device_id': did, 'status': 'active'}]})
    point = {'time': '2026-10-11T08:00:00Z', 'cpu': 26, 'memory': 44, 'errors': 2, 'discards': 1, 'in_bps': 1200}
    for hours in (1, 6, 24):
        write(f'metrics/{hours}h.json', {'defaults': {'metrics': [point | {'cpu': hours}]}})
    monkeypatch.setattr(local_app, 'observations', JsonObservations(tmp_path))
    for minutes, cpu in ((60, 1), (360, 6), (1440, 24)):
        bundle = call(client, 'GET', f'/monitor/metrics/dashboard-bundle?range_minutes={minutes}')
        assert next(d for d in bundle['summary']['devices'] if d['id'] == did)['cpu'] == cpu
    assert 'fixture-controls' in call(client, 'GET', '/topology')['nodes']
    write('availability.json', {'devices': [{'device_id': did, 'status': 'inactive'}]})
    assert 'fixture-controls' not in call(client, 'GET', '/topology')['nodes']
    assert 'fixture-controls' in call(client, 'GET', '/netbox/topology/planned/local')['nodes']
    write('availability.json', {'devices': [{'device_id': 999999, 'status': 'active'}]})
    call(client, 'GET', '/topology', expected=422)
    write('availability.json', {'devices': [{'device_id': did, 'status': 'active'}]})
    fixture = {'version': 1, 'capture': {'default_config': 'hostname {hostname}\nntp server 192.0.2.1'},
               'ztp_publish': {'default_status': 'success', 'message': 'ok'},
               'restore': {'default_status': 'success', 'message': 'restored'}}
    write('workflow_outcomes.json', fixture)
    monkeypatch.setattr(local_app, 'workflow_outcomes', LocalWorkflowProvider(tmp_path))
    first = call(client, 'POST', '/network/config-backup/capture', {'device_id': did})
    path = tmp_path / 'configurations' / f'device-{did}.json'
    original = json.loads(path.read_text())
    write(f'configurations/device-{did}.json', original | {'config_text': 'hostname changed\nntp server 192.0.2.2'})
    second = call(client, 'POST', '/network/config-backup/capture', {'device_id': did})
    assert call(client, 'GET', f"/network/config-backup/snapshots/{second['snapshot_id']}/content")['config_text'].startswith('hostname changed')
    result = call(client, 'POST', f"/network/config-backup/snapshots/{first['snapshot_id']}/restore")
    assert result['backup_snapshot_id'] and json.loads(path.read_text()) == original
    fixture['restore']['default_status'] = 'failed'
    write('workflow_outcomes.json', fixture)
    call(client, 'POST', f"/network/config-backup/snapshots/{second['snapshot_id']}/restore", expected=502)
    assert json.loads(path.read_text()) == original
