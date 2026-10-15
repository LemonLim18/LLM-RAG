"""One isolated authoring -> publication -> existing Studio verification."""
import os
from pathlib import Path
import sys
import tempfile
import json

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
(ROOT / 'tmp').mkdir(exist_ok=True)
TEST_ROOT = Path(tempfile.mkdtemp(prefix='knowledge-check-', dir=ROOT / 'tmp'))
os.environ.update(COGNISHIELD_MODE='local_lab', COGNISHIELD_STUDIO_ENGINE='v9',
    COGNISHIELD_KNOWLEDGE_ROOT=str(TEST_ROOT/'knowledge'), COGNISHIELD_DB_PATH=str(TEST_ROOT/'app.db'), AUTH_BYPASS_ROLES='0')
from fastapi.testclient import TestClient
from local_app import app
from auth.auth import create_access_token


def test_publication_loop():
    with TestClient(app) as client:
        client.headers['Authorization'] = 'Bearer ' + create_access_token(1, 'knowledge-admin', 'admin')
        def call(method, path, body=None, expected=200):
            response = client.request(method, '/api/v1'+path, json=body)
            assert response.status_code == expected, (path,response.status_code,response.text[:3000])
            return response.json()
        assert not call('GET','/knowledge')['data']['initialized']
        initial = call('POST','/knowledge/initialize', {'reason':'Isolated baseline import'})
        print('PASS: verified baseline imported into V9 SQLite', flush=True)
        release = initial['data']['active_release']['release_id']
        path = next(r['template_path'] for r in initial['data']['catalogs']['template_bindings'] if r['operation_id']=='create_vlan' and r['vendor']=='cisco')
        original = initial['data']['templates'][path]
        invalid = {'expected_revision':initial['revision'],'reason':'Invalid template', 'path':path,'content':'{{ unknown_parameter }}'}
        call('PUT','/knowledge/template',invalid,422)
        assert call('GET','/knowledge')['revision'] == initial['revision']
        call('PUT','/knowledge/template',{**invalid,'path':'../../escape.j2'},422)
        call('PUT','/knowledge/template',{**invalid,'reason':'Reviewed native template change','content':original+'\n! Knowledge publication verified\n'})
        draft = call('GET','/knowledge')
        assert draft['data']['active_release']['release_id']==release
        assert draft['data']['catalogs']['operations'][0]['version'] > initial['data']['catalogs']['operations'][0]['version']
        call('PUT','/knowledge/template',{**invalid,'content':original},409)
        call('POST','/knowledge/validate')
        render = {'expected_revision':draft['revision'], 'path':path,
                  'content':draft['data']['templates'][path], 'parameters':{'vlan_id':30}}
        assert 'vlan 30' in call('POST','/knowledge/render',render)['data']['configuration']
        call('POST','/knowledge/render',render|{'parameters':{'vlan_id':5000}},422)
        publication = {'expected_revision':draft['revision'],'expected_release':release,'reason':'Approve isolated template change'}
        client.headers['Authorization']='Bearer '+create_access_token(2,'knowledge-engineer','engineer')
        call('POST','/knowledge/publish',publication,403)
        client.headers['Authorization']='Bearer '+create_access_token(1,'knowledge-admin','admin')
        published = call('POST','/knowledge/publish',publication)
        assert published['data']['release_id']!=release
        call('POST','/knowledge/publish',publication,409)
        active = published['data']['release_id']
        built = call('POST','/knowledge/build',publication|{'expected_release':active})['data']['release_id']
        assert call('GET','/knowledge')['data']['active_release']['release_id']==active
        frozen = call('GET','/knowledge/releases/'+built)
        assert frozen['ok']
        activation={'release_id':built,'expected_release':active,'reason':'Verify explicit activation'}
        call('POST','/knowledge/activate',activation|{'expected_release':release},409)
        assert call('GET','/knowledge')['data']['active_release']['release_id']==active
        call('POST','/knowledge/activate',activation)
        assert call('GET','/knowledge')['data']['active_release']['release_id']==built
        call('POST','/knowledge/activate',{'release_id':active,'expected_release':built,'reason':'Verify rollback'})
        restored=call('GET','/knowledge')
        assert restored['revision']==draft['revision']
        assert restored['data']['active_release']['release_id']==active
        print('PASS: validated render, build-only isolation, frozen inspection, stale activation rejection, activation and rollback',flush=True)
        call('POST','/netbox/devices',{'hostname':'Knowledge-SW1','management_ip':'192.0.2.88','management_subnet_mask':'24','vendor':'cisco_ios','os_version':'IOS-XE 17.9','status':'planned'})
        request={'intent_description':'Create VLAN 30 on Knowledge-SW1','target_hosts':['Knowledge-SW1'],'model':'qwen2.5:1.5b'}
        preview=call('POST','/ansible/preview-intent',request)
        assert preview['parsed_intent']['knowledge_snapshot_id']==published['data']['release_id']
        generated=call('POST','/ansible/create-and-plan',request|{'params':{'_v9_session':preview['parsed_intent']['_v9_session'],'vlan_id':30}})
        native=next(r['content'] for r in generated['files'] if r['path'].endswith('native_config.txt'))
        assert '! Knowledge publication verified' in native and 'vlan 30' in native
        headers=dict(client.headers)
    with TestClient(app) as client:
        client.headers.update(headers)
        persisted=client.get('/api/v1/knowledge').json()
        assert persisted['data']['active_release']['release_id']==published['data']['release_id']
        assert 'Knowledge publication verified' in persisted['data']['templates'][path]
        assert persisted['data']['history'][0]['actor']=='knowledge-admin'
    print('PASS: draft isolation, Jinja/path validation, revision conflict, version bump, admin publication, Studio consumption, audit and restart persistence',flush=True)


if __name__=='__main__': test_publication_loop()
