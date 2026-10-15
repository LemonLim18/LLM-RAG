import os, tempfile, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['COGNISHIELD_MODE']='local_lab'
os.environ['COGNISHIELD_STUDIO_ENGINE']='v9'
os.environ['COGNISHIELD_KNOWLEDGE_ROOT']=str(Path(tempfile.mkdtemp(prefix='v9-root-',dir=Path(__file__).resolve().parents[2]/'tmp'))/'not-initialized')
os.environ['COGNISHIELD_DB_PATH']=str(Path(tempfile.mkdtemp(prefix='cognishield-v9-check-'))/'test.db')
from fastapi.testclient import TestClient
from local_app import app
from auth.auth import create_access_token

def test_v9_vertical_slice():
 with TestClient(app) as c:
  c.headers['Authorization']='Bearer '+create_access_token(1,'v9-check','admin')
  def call(method,path,body=None,expected=200):
   r=c.request(method,'/api/v1'+path,json=body)
   assert r.status_code==expected,(path,r.status_code,r.text[:2000])
   return r.json()
  call('POST','/knowledge/initialize',{'reason':'Isolated V9 bridge check'})
  call('POST','/netbox/devices',{'hostname':'V9-Test','management_ip':'192.0.2.80','management_subnet_mask':'24','vendor':'cisco_ios','os_version':'IOS-XE 17.9','status':'planned'})
  request={'intent_description':'Create VLAN on V9-Test','target_hosts':['V9-Test'],'model':'qwen2.5:1.5b'}
  p=call('POST','/ansible/preview-intent',request)
  assert p['parsed_intent']['engine']=='v9'
  assert p['params_disambiguation']['fields'][0]['field']=='vlan_id'
  sid=p['parsed_intent']['_v9_session']
  print('V9 clarification passed',flush=True)
  p=call('POST','/ansible/preview-intent',request|{'params':{'_v9_session':sid,'vlan_id':10,'name':'Art'}})
  assert not p.get('params_disambiguation') and not p['parsed_intent']['validation_errors'],p
  assert 'interfaces_for_selection' not in p, 'Resolved VLAN target must not reopen the interface picker'
  call('POST','/ansible/create-and-plan',request|{'params':{'_v9_session':sid,'vlan_id':5000}},422)
  result=call('POST','/ansible/create-and-plan',request|{'params':{'_v9_session':sid,'vlan_id':20,'name':'Reviewed'}})
  assert 'cisco.ios.ios_config' in result['playbook'] and 'src: native_config.txt' in result['playbook']
  assert 'Reviewed' in next(f['content'] for f in result['files'] if f['path'].endswith('.txt'))
  assert 'vlan 20' in next(f['content'] for f in result['files'] if f['path'].endswith('.txt'))
  path=result['entrypoint_path']; assert call('GET','/ansible/files/'+path)['content']==result['playbook']
  call('PUT','/ansible/files/'+path,{'content':result['playbook']+'\n# saved\n'})
  call('POST','/ansible/preview-intent',{'intent_description':'Create VLAN 10 on V9-Test and delete VLAN 20 on V9-Test','model':'qwen2.5:1.5b'},422)
  assert c.post('/api/v1/ansible/jobs/1/run').status_code==503
  from local_providers.v9_studio import session
  import local_app
  from fastapi import HTTPException
  try: session(local_app.db,sid,'other-user'); assert False
  except HTTPException as e: assert e.status_code==404
  with local_app.db._connect() as conn:
   assert conn.execute("SELECT count(*) FROM audit_log WHERE action='v9.generate'").fetchone()[0]==1
   assert conn.execute('SELECT count(*) FROM jobs').fetchone()[0]==1
  headers=dict(c.headers)
 with TestClient(app) as c:
  c.headers.update(headers)
  assert '# saved' in c.get('/api/v1/ansible/files/'+path).json()['content']
 print('PASS: V9 clarification, corrections, validation, artifacts, ownership, audit, restart and execution isolation',flush=True)

if __name__=='__main__': test_v9_vertical_slice()
