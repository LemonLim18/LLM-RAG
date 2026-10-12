"""Focused tests for restored original local workflows; no real adapter is used."""
import json
from pathlib import Path
import pytest
from tests.test_m0_local import client, call
from db.manager import DatabaseManager
from db.models import ConfigSnapshot
from lab_config import DB_PATH
import local_app
from local_providers.workflows import LocalWorkflowProvider

def device(client, hostname='M023-router'):
    return call(client,'POST','/netbox/devices',{'hostname':hostname,'management_ip':'192.0.2.44','management_subnet_mask':'255.255.255.0','vendor':'cisco_ios','status':'planned','role':'access'})

def test_day0_profile_ztp_and_local_outcome(client, tmp_path, monkeypatch):
    d=device(client)
    # Existing profile service is used by the original generator parameters.
    call(client,'PUT','/common-services/profiles/global/global',{'ntp_server_ip':'192.0.2.123','syslog_host_ip':'192.0.2.124'})
    generated=call(client,'POST',f"/onboarding/generate/{d['id']}")
    assert 'ntp server 192.0.2.123' in generated['config'] and generated['execution']=='local_render'
    call(client,'POST',f"/onboarding/day0/{d['id']}/override",{'config':'hostname M023-router\n! reviewed','filename':'reviewed.txt'})
    assert call(client,'POST',f"/onboarding/generate/{d['id']}")['is_override'] is True
    fixture=tmp_path/'workflow_outcomes.json'
    fixture.write_text(json.dumps({'version':1,'capture':{'default_config':'hostname {hostname}'},'ztp_publish':{'default_status':'success','message':'fixture success','device_outcomes':[]},'restore':{'default_status':'success','message':'restore success','device_outcomes':[]}}))
    monkeypatch.setattr(local_app,'workflow_outcomes',LocalWorkflowProvider(tmp_path))
    job=call(client,'POST','/onboarding/ztp/publish',{'device_ids':[d['id']],'config_overrides':{str(d['id']):'hostname M023-router'}})
    assert job['status']=='success'
    assert call(client,'GET',f"/onboarding/ztp/publish/{job['job_id']}")['items'][0]['stage']=='simulated_publish'
    fixture.write_text(json.dumps({'version':1,'capture':{'default_config':'hostname {hostname}'},'ztp_publish':{'default_status':'failed','message':'fixture failure','device_outcomes':[]},'restore':{'default_status':'success','message':'restore success','device_outcomes':[]}}))
    assert call(client,'POST','/onboarding/ztp/publish',{'device_ids':[d['id']]} )['status']=='failed'

def test_capture_diff_restore_and_approval_policy(client,tmp_path,monkeypatch):
    d=device(client,'M023-backup')
    fixture=tmp_path/'workflow_outcomes.json'
    def put(restore='success'):
        fixture.write_text(json.dumps({'version':1,'capture':{'default_config':'hostname {hostname}\nntp server 192.0.2.1\n','device_configs':[{'device_id':d['id'],'config_text':'hostname {hostname}\nntp server 192.0.2.77\n'}]},'ztp_publish':{'default_status':'success','message':'ok','device_outcomes':[]},'restore':{'default_status':restore,'message':'fixture '+restore,'device_outcomes':[]}}))
    put(); monkeypatch.setattr(local_app,'workflow_outcomes',LocalWorkflowProvider(tmp_path))
    first=call(client,'POST','/network/config-backup/capture',{'device_id':d['id'],'description':'first'})
    assert 'ntp server 192.0.2.77' in call(client,'GET',f"/network/config-backup/snapshots/{first['snapshot_id']}/content")['config_text']
    second=call(client,'POST','/network/config-backup/import',{'device_id':d['id'],'config_text':'hostname M023-backup\nntp server 192.0.2.2\n','description':'second'})
    assert call(client,'GET',f"/network/config-backup/snapshots/{second['snapshot_id']}/diff")['has_previous'] is True
    assert call(client,'POST',f"/network/config-backup/snapshots/{second['snapshot_id']}/restore")['commands_applied']==0
    put('failed'); call(client,'POST',f"/network/config-backup/snapshots/{first['snapshot_id']}/restore",expected=502)
    policy={'policy_id':'m023-ntp','name':'NTP required','category':'ntp','scope':{},'rules':[{'id':'ntp','action':'must_exist','target':'ntp server 192.0.2.2','severity':'high'}]}
    call(client,'POST','/policies',policy)
    baseline=DatabaseManager(str(DB_PATH)).save_config_snapshot(ConfigSnapshot(device_id=d['id'],config_text='hostname M023-backup\nntp server 192.0.2.1\n',snapshot_type='baseline'))
    result=call(client,'POST',f"/compliance/scan/{d['id']}")['result']
    assert result['status'] in {'compliant','drifted','violated'}
    request=call(client,'POST','/deploy/requests',{'title':'M023 review','description':'local only'})
    queue=call(client,'GET','/api/deploy/queue',expected=404) if False else None
    # Approval router sits outside /api/v1; exercise it directly.
    r=client.get('/api/deploy/queue?status_filter=pending'); assert r.status_code==200
    assert any(x['request_id']==request['request_id'] for x in r.json()['items'])
    assert client.post(f"/api/deploy/{request['request_id']}/approve",json={'comment':'reviewed'}).json()['status']=='approved'
