import faulthandler
faulthandler.dump_traceback_later(45, repeat=False)
import os, tempfile, json
from pathlib import Path
os.environ['COGNISHIELD_MODE']='local_lab'
os.environ['COGNISHIELD_DB_PATH']=str(Path(tempfile.mkdtemp(prefix='studio-generation-'))/'test.db')
from fastapi.testclient import TestClient
from local_app import app
from auth.auth import create_access_token
with TestClient(app) as c:
 c.headers['Authorization']='Bearer '+create_access_token(1,'studio-check','admin')
 def call(method,path,body=None):
  print('CALL',path,flush=True)
  r=c.request(method,'/api/v1'+path,json=body)
  if r.status_code!=200: print(path,r.status_code,r.text[:1600],flush=True); raise SystemExit(1)
  return r.json()
 d=call('POST','/netbox/devices',{'hostname':'StudioCheck','management_ip':'192.0.2.44','management_subnet_mask':'255.255.255.0','vendor':'cisco_ios','status':'planned','role':'access'})
 call('POST',f"/netbox/devices/{d['id']}/interfaces",{'name':'GigabitEthernet0/1','interface_type':'l2'})
 request={'intent_description':'Create VLAN 10 named Art on StudioCheck','target_hosts':['StudioCheck'],'vendor':'cisco_ios','feature':'vlan','provider':'ollama','model':'qwen2.5:1.5b','params':{'vlan_id':10,'vlan_name':'Art'}}
 preview=call('POST','/ansible/preview-intent',request|{'skip_rag':True})
 print('PREVIEW',json.dumps(preview)[:2200],flush=True)
 result=call('POST','/ansible/create-and-plan',request)
 print('GENERATED',json.dumps(result)[:2500],flush=True)
 path=result['entrypoint_path']; content=call('GET','/ansible/files/'+path)['content']; assert content==result['playbook']
 call('PUT','/ansible/files/'+path,{'content':content+'\n# saved edit\n'})
 md=path.rsplit('/',1)[0]+'/preview_modal_dialog.md'
 call('POST','/ansible/files/create-file/'+md,{'content':'# Reviewed preview\nVLAN 10 Art on StudioCheck'})
 assert call('GET','/ansible/jobs/'+str(result['job_id'])+'/result')
 headers=dict(c.headers)
with TestClient(app) as c:
 c.headers.update(headers)
 assert 'saved edit' in call('GET','/ansible/files/'+path)['content']
 assert 'Reviewed preview' in call('GET','/ansible/files/'+md)['content']
 assert c.post('/api/v1/ansible/jobs/1/run').status_code==503
 print('PASS: preview, generate, files, Markdown, restart persistence, execution blocked',flush=True)
