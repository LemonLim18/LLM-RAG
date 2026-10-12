"""M0.1 acceptance tests reuse the M0 isolated database/client."""
import json
import sqlite3
import pytest
from tests.test_m0_local import client, call
from local_providers.observations import JsonObservations, Fixture, FixtureError
from local_providers.authoring import AuthoringStore
from db.manager import DatabaseManager
from lab_config import DB_PATH
from local_app import app
import local_app

def write_fixture(path, **changes):
    data={'version':1,'defaults':{'availability':'up','metrics':[{'time':'2026-01-01T00:00:00Z','cpu':21,'memory':42}]}}
    data.update(changes)
    path.write_text(json.dumps(data),encoding='utf-8')
    return data

def test_fixture_refresh_errors_references_and_source(client,tmp_path,monkeypatch):
    p=tmp_path/'observations.json'
    provider=JsonObservations(tmp_path)
    monkeypatch.setattr(local_app,'observations',provider)
    d=call(client,'POST','/netbox/devices',{'hostname':'M01-fixture-device'})
    i=call(client,'POST',f"/netbox/devices/{d['id']}/interfaces",{'name':'Ethernet1','interface_type':'l2'})
    point={'time':'2026-01-01T00:00:00Z','cpu':21,'memory':42,'in_bps':8000,'out_bps':4000,'utilization_pct':5}
    event={'id':'e1','device_id':d['id'],'timestamp':point['time'],'message':'Editable event'}
    data=write_fixture(p,interfaces=[{'device_id':d['id'],'interface_id':i['id'],'oper_status':'up','metrics':[point]}],syslog=[event],events=[event],alerts=[{**event,'severity':'high'}],snapshots=[{'id':'s1','device_id':d['id'],'timestamp':point['time'],'config_text':'hostname fixture'}])
    first=call(client,'GET','/monitor/metrics/dashboard-bundle')
    assert first['source']=='simulated' and first['live'] is False
    assert first==call(client,'GET','/monitor/metrics/dashboard-bundle')
    assert first['summary']['devices'][0]['cpu']==21
    assert call(client,'GET','/syslog/events')[0]['message']=='Editable event'
    assert call(client,'GET','/monitor/thresholds/alerts')[0]['source']=='simulated'
    topo=call(client,'GET','/netbox/topology/planned/local')
    assert topo['nodes']['M01-fixture-device']['operational_status']=='up'
    assert topo['structure_source']=='stored'
    data['defaults']['metrics'][0]['cpu']=71
    p.write_text(json.dumps(data),encoding='utf-8')
    changed=call(client,'GET','/monitor/metrics/dashboard-bundle')
    assert changed['summary']['devices'][0]['cpu']==71 and changed['fixture_revision']!=first['fixture_revision']
    for malformed in [
        '{broken',
        json.dumps({'version':1,'devices':[{'device_id':999999}]}),
        json.dumps({'version':1,'interfaces':[{'device_id':d['id'],'interface_id':999999}]}),
        json.dumps({'version':1,'defaults':{'metrics':[dict(point,cpu=101)]}}),
        json.dumps({'version':1,'defaults':{'metrics':[dict(point,time='yesterday')]}}),
        json.dumps({'version':1,'devices':[{'device_id':d['id']},{'device_id':d['id']}]}),
    ]:
        p.write_text(malformed,encoding='utf-8')
        res=call(client,'GET','/monitor/metrics/dashboard-bundle',expected=422)
        assert 'observations' in res['detail'] or 'device_id' in res['detail'] or 'interfaces' in res['detail'] or 'duplicate' in res['detail']
        assert call(client,'GET',f"/netbox/devices/{d['id']}")['hostname']=='M01-fixture-device'
    write_fixture(p)
    call(client,'DELETE',f"/netbox/devices/{d['id']}")

def test_local_template_authoring_render_validation_and_restart(client):
    path='/config/templates/cisco_ios/m01_test'
    call(client,'POST',path+'/create',{'content':'hostname {{ hostname }}'})
    call(client,'PUT','/config/schemas/m01_test/source',{'content':json.dumps({'type':'object','properties':{'hostname':{'type':'string','minLength':2}},'required':['hostname'],'additionalProperties':False})})
    assert call(client,'POST','/config/render',{'vendor':'cisco_ios','feature':'m01_test','params':{'hostname':'router'}})['config']=='hostname router'
    call(client,'POST','/config/render',{'vendor':'cisco_ios','feature':'m01_test','params':{'hostname':''}},expected=400)
    call(client,'PUT',path+'/source',{'content':'hostname {{ hostname }}\n! saved'})
    call(client,'PUT',path+'/source',{'content':'{% invalid'},expected=422)
    assert call(client,'GET',path+'/source')['content'].endswith('! saved')
    assert call(client,'POST','/config/validate',{'vendor':'cisco_ios','config_text':'hostname router'})['valid'] is True
    fresh=AuthoringStore(DatabaseManager(str(DB_PATH)))
    assert fresh.read('templates','cisco_ios/m01_test.j2').endswith('! saved')
    assert len(fresh.history('templates','cisco_ios/m01_test.j2'))==2
    call(client,'PUT','/config/schemas/m01_test/source',{'content':'{"$ref":"https://invalid.example/schema"}'},expected=422)
    call(client,'DELETE',path)
    call(client,'GET',path+'/source',expected=404)
    assert fresh.history('templates','cisco_ios/m01_test.j2')[0]['deleted']==1
    assert fresh.history('templates','cisco_ios/m01_test.j2')[1]['content'].endswith('! saved')

def test_workspace_authoring_and_path_guards(client):
    path='playbooks/m01_test.yml'
    call(client,'POST','/ansible/files/create-file/'+path,{'content':'---\n- hosts: all\n  tasks: []'})
    call(client,'PUT','/ansible/files/'+path,{'content':'---\n# saved locally'})
    read=call(client,'GET','/ansible/files/'+path)
    assert read['writable'] and read['source']=='stored'
    assert 'saved locally' in AuthoringStore(DatabaseManager(str(DB_PATH))).read('ansible',path)
    for bad in ['inventory/hosts.yml','reference/README.md','../outside.yml','playbooks/../../outside.yml','playbooks/C:/outside.yml']:
        with pytest.raises(Exception):
            AuthoringStore().mutate('ansible',bad,'bad','m01','create')
    call(client,'POST','/ansible/files/create-file/'+path,{'content':''},expected=409)
    call(client,'DELETE','/ansible/files/'+path)
    call(client,'GET','/ansible/files/'+path,expected=404)
    assert call(client,'GET','/lab/authoring/ansible/history/'+path)['revisions'][1]['content'].endswith('locally')
    caps=call(client,'GET','/lab/capabilities')
    assert caps['features']['studio.authoring'] is True
    assert caps['features']['execution.deploy'] is False
    call(client,'GET','/template-git/status',expected=503)

def test_schema_file_matches_contract():
    from lab_config import BACKEND_DIR
    assert json.loads((BACKEND_DIR/'simulation/observations.schema.json').read_text())==Fixture.model_json_schema()
