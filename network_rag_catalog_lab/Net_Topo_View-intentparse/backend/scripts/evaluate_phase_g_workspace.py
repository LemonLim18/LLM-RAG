"""Actual shared LangGraph/Ollama coordinated proposal; disposable authorized files."""
import argparse,asyncio,json,os,sys,time
from pathlib import Path
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
MAIN='- hosts: LAB-R1\n  vars_files:\n    - group_vars/all.yml\n  tasks:\n    - name: Keep routing variable\n      ansible.builtin.debug:\n        msg: "{{ neighbor_ip }}"\n# REVIEW_BEFORE\n# UNSAVED_MAIN_KEEP\n'
VARIABLES='neighbor_ip: 192.0.2.2\n# UNSAVED_VARIABLE_KEEP\n'
PROMPT='In the active playbook and its referenced group_vars file, change neighbor_ip from 192.0.2.2 to 192.0.2.3 in its authoritative variable file. Also replace only the marker comment # REVIEW_BEFORE with # REVIEW_AFTER in the playbook. Preserve all other lines and comments. Propose both file changes for review; do not apply or save.'

async def main(spec_path=None):
 import httpx
 from fastapi import FastAPI
 from auth.auth import create_access_token
 from db.manager import DatabaseManager
 from llm.gateway_api import router
 from llm.gateway_store import ensure_schema
 from local_providers import authoring
 from scripts.phase_d_audit import Run,source_manifest
 os.environ.update(COGNISHIELD_AI_ENGINE='langgraph_b3',COGNISHIELD_AI_PLANNING='1',COGNISHIELD_AI_SYNTHESIS='1')
 spec=json.loads(Path(spec_path).read_text(encoding='utf-8')) if spec_path else {
  'id':'G8-COORDINATED-EDIT-001','prompt':PROMPT,
  'sources':[{'path':'playbooks/g8_case/main.yml','content':MAIN,'language':'yaml'},
             {'path':'playbooks/g8_case/group_vars/all.yml','content':VARIABLES,'language':'yaml'}],
  'expected':{'playbooks/g8_case/main.yml':MAIN.replace('# REVIEW_BEFORE','# REVIEW_AFTER'),'playbooks/g8_case/group_vars/all.yml':VARIABLES.replace('192.0.2.2','192.0.2.3')},
  'prohibited':['Saving','Device execution','Unrelated code changes','Inlining the variable in the playbook']}
 sources=spec['sources'];prompt=spec['prompt'];expected=spec['expected']
 assert 2<=len(sources)<=9 and len({s['path'] for s in sources})==len(sources),'Invalid frozen source specification'
 assert set(expected).issubset({s['path'] for s in sources}),'Expected files must be supplied sources'
 run=Run('G8-real-workspace','real_model_full_agent',{'source_manifest':source_manifest(),'model':'qwen2.5:1.5b','holdout':False,'expectation_frozen_before_inference':True,'proposed_only':True,'specification':str(spec_path) if spec_path else 'original-exposed-case'},phase='phase-g')
 (run.path/'case-specification.json').write_text(json.dumps(spec,indent=2),encoding='utf-8')
 workspace=ROOT/'tmp'/('g8-live-'+uuid4().hex[:6]);workspace.mkdir();files=workspace/'files';files.mkdir();authoring.ROOTS={'ansible':files}
 db=DatabaseManager(str(workspace/'app.db'));db.initialize();ensure_schema(db)
 app=FastAPI();app.state.local_db=db;app.include_router(router)
 def snapshot(source):
  path=source['path'];return {'document_id':path,'path':path,'content':source['content'],'language':source.get('language','yaml'),'model_id':'g8-'+path,'model_version':1,'buffer_epoch':1,'saved_revision':0,'is_dirty':True,'read_only':False}
 started=time.monotonic();trace={'workspace':str(workspace),'prompt':prompt};outcome='FAIL'
 try:
  async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://g8-evaluation',headers={'Authorization':'Bearer '+create_access_token(933,'G8-ENGINEER','engineer')},timeout=240) as client:
   response=await client.post('/api/v1/ai/conversations',json={'assistant_kind':'studio'});response.raise_for_status();cid=response.json()['id']
   response=await client.post('/api/v1/ai/conversations/'+cid+'/turns',json={'request_id':str(uuid4()),'prompt':prompt,'model':'qwen2.5:1.5b','editor':snapshot(sources[0]),'related_editors':[snapshot(s) for s in sources[1:]]})
   trace.update(http_status=response.status_code,result=response.json());response.raise_for_status()
   value=response.json();proposal=value.get('proposal') or {};changes=proposal.get('files',[])
   assert value['kind']=='edit_proposal' and value['status']=='success','Actual graph did not return a coordinated proposal'
   assert {f['path']:f['suggested'] for f in changes}==expected,'Model proposal did not satisfy exact two-file instruction'
   assert proposal['validation']['saved'] is False
   with db._connect() as c:
    assert c.execute('SELECT count(*) FROM authoring_revisions').fetchone()[0]==0
    trace['persisted_turns']=c.execute('SELECT count(*) FROM ai_turns WHERE conversation_id=?',(cid,)).fetchone()[0]
   assert trace['persisted_turns']==1;outcome='PASS'
 except Exception as exc:trace['error']=type(exc).__name__+': '+str(exc)
 finally:
  db.close()
  with (run.path/'actual.json').open('x',encoding='utf-8') as f:json.dump(trace,f,indent=2)
  run.record(spec['id'],outcome,expected=expected,actual={'trace':'actual.json','error':trace.get('error')},classification='MODEL_OR_WORKFLOW_FAILURE' if outcome=='FAIL' else None,latency_ms=round((time.monotonic()-started)*1000,2))
  print(json.dumps({'run':str(run.path),'outcome':outcome,'error':trace.get('error')}),flush=True)
 return outcome=='PASS'

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--case-spec',type=Path);args=parser.parse_args()
 raise SystemExit(0 if asyncio.run(main(args.case_spec)) else 1)
