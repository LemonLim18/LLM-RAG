"""Bounded thinking/layout experiments through existing exact-consented roles.
No planner inference, source reretrieval, ordinary data or editor access.
"""
import argparse,asyncio,copy,hashlib,json,os,sys,time
from datetime import datetime,timezone
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];AUDIT=ROOT/'tmp/phase-g/iterations/20261101-audit-grounded-repair'
sys.path.insert(0,str(ROOT/'backend'))
SPEC=ROOT/'docs/evaluations/phase_g_audit_grounded_reasoning_v1.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(path,value):
 text=json.dumps(value,ensure_ascii=False,indent=2,default=str)
 for name in ['GEMINI_API_KEY','OPENAI_API_KEY']:
  if os.getenv(name):assert os.environ[name] not in text,'Refusing credential exposure'
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('x',encoding='utf-8') as f:f.write(text+'\n')

async def main(args):
 if args.stage=='P2' and (AUDIT/'P2-stop.json').exists():
  raise RuntimeError('P2 failed its recorded stop condition; no further candidate dispatch is authorized in this cycle.')
 os.environ.update(COGNISHIELD_MODE='local_lab',COGNISHIELD_DEV_SIMULATION='1',
  COGNISHIELD_DB_PATH=str(AUDIT/'evaluation-app.db'),COGNISHIELD_DEV_STATE=str(AUDIT/'initial-state.json'),
  COGNISHIELD_AI_HYBRID='1',COGNISHIELD_AI_MULTI_MODEL_EXPERIMENT='1',COGNISHIELD_AI_HYBRID_INTERPRET='0',
  COGNISHIELD_AI_COMPLETENESS='1',COGNISHIELD_AI_OUTCOMES='0',COGNISHIELD_AI_EVIDENCE_HARNESS='0',
  COGNISHIELD_AI_EXPERIMENT_SEMANTIC_VERIFIER='off',COGNISHIELD_AI_INVESTIGATION_SECONDS='120',
  COGNISHIELD_AI_REASONER_MODEL='gemini-3.5-flash-lite',COGNISHIELD_AI_REASONER_SCHEMA_MODE='validated_json',
  COGNISHIELD_AI_REASONER_OUTPUT_TOKENS='8192',COGNISHIELD_AI_REASONER_THINKING='low',
  COGNISHIELD_LOCAL_OLLAMA_MODEL='qwen2.5:1.5b')
 import lab_config,httpx
 from db.manager import DatabaseManager
 from llm.gateway_store import ConversationStore
 from llm.gateway_models import TurnRequest,Evidence
 from llm.gemini_provider import HybridRequest,approve_hybrid_request,scenario_approval_context
 from llm.model_roles import consent_manifest
 from llm.orchestration.role_reasoning import decide
 from llm.orchestration.investigation_support import compatible_claims,release_interpretation
 from llm.gateway_services import inventory_snapshot
 from local_providers.development import ScenarioManager
 freeze=json.loads((AUDIT/'freeze-receipt.json').read_text(encoding='utf-8'))
 assert sha(SPEC)==freeze['registry_sha256']
 grading=json.loads((AUDIT/'grading-freeze.json').read_text(encoding='utf-8'))
 assert grading['registry_sha256']==sha(SPEC) and grading['frozen_before_inference']
 spec=json.loads(SPEC.read_text(encoding='utf-8'));db=DatabaseManager(str(AUDIT/'evaluation-app.db'))
 assert Path(db._db_path).resolve()==(AUDIT/'evaluation-app.db').resolve()
 store=ConversationStore(db);user={'username':'audit-engineer','role':'engineer'}
 counters=AUDIT/'dispatch-ledger.jsonl'
 original_send=httpx.AsyncClient.send
 wires=[];source_manifest={str(p.relative_to(ROOT)):sha(p) for folder in ['backend/llm','backend/local_providers','backend/development'] for p in (ROOT/folder).rglob('*.py')}
 runtime=AUDIT/args.stage/'runtime-freeze.json'
 if runtime.exists():assert json.loads(runtime.read_text(encoding='utf-8'))['sources']==source_manifest,'Do not mix runtime revisions'
 else:save(runtime,{'at':datetime.now(timezone.utc).isoformat(),'sources':source_manifest,'registry_sha256':sha(SPEC)})
 async def send(client,request,*a,**kw):
  if request.url.host!='generativelanguage.googleapis.com':return await original_send(client,request,*a,**kw)
  rows=[json.loads(x) for x in counters.read_text(encoding='utf-8').splitlines()] if counters.exists() else []
  assert len(rows)<48,'Task hard dispatch ceiling'
  assert sum(r['stage']==args.stage for r in rows)<(16 if args.stage in {'P1','P2'} else 4),'Stage dispatch ceiling'
  dispatch={'id':uuid4().hex,'at':datetime.now(timezone.utc).isoformat(),'stage':args.stage,
   'case':current_case['id'],'arm':current_arm,'model_path':request.url.path}
  with counters.open('a',encoding='utf-8') as f:f.write(json.dumps(dispatch)+'\n')
  wire={'dispatch':dispatch,'body':json.loads(request.content),'start':time.monotonic()};wires.append(wire)
  try:
   response=await original_send(client,request,*a,**kw)
   wire.update(status=response.status_code,body_response=response.json())
   return response
  except Exception as exc:
   wire['transport_error']=type(exc).__name__;raise
  finally:wire['seconds']=time.monotonic()-wire.pop('start')
 try:
  with patch.object(httpx.AsyncClient,'send',send):
   for case in spec['cases'][args.offset:args.offset+args.limit]:
    current_case=case
    info=next(c for c in freeze['cases'] if c['id']==case['id'])
    packet_file=AUDIT/'frozen-v1'/case['id']/'frozen-packet.json'
    assert sha(packet_file)==info['packet_sha256']
    frozen=json.loads(packet_file.read_text(encoding='utf-8'))
    assert sha(ROOT/frozen['scenario_path'])==info['scenario_file_sha256']
    manager=ScenarioManager(ROOT/frozen['scenario_path']);db._development_scenario=manager
    initial=scenario_approval_context(db);os.environ['COGNISHIELD_AI_HYBRID_SCENARIOS']=initial['scenario_digest']
    context_file=AUDIT/'owned-contexts'/(case['id']+'.json')
    if context_file.exists():
     cid=json.loads(context_file.read_text(encoding='utf-8'))['conversation']
     store.get(cid,user['username'],case['surface'])
    else:
     cid=None
     if case['advisory']:
      # A globally unique evidence ID belongs to one owned conversation. Both
      # arms reuse its unchanged history instead of fabricating new IDs.
      source_id=frozen['inputs']['advisory']['prior_source_evidence'][0]['id']
      with db._connect() as connection:
       found=connection.execute('SELECT e.conversation_id FROM ai_evidence e JOIN ansible_chat_sessions s ON s.id=e.conversation_id WHERE e.id=? AND s.owner_username=? AND s.assistant_kind=?',
        (source_id,user['username'],case['surface'])).fetchone()
      if found:cid=found[0]
     if cid is None:
      cid=store.create(user['username'],case['surface'])['id']
      if case['advisory']:
       rid=str(uuid4());sources=frozen['inputs']['advisory']['prior_source_evidence']
       store.begin(cid,user['username'],rid,'synthetic-source-setup',case['owned_goal'])
       store.finish(cid,user['username'],rid,{'answer':'Prior authorized saved configuration was read; no operational interpretation.',
        'kind':'answer','status':'success','evidence':sources,'observations':frozen['actual_authorized_rows'],
        'context_coverage':{'environment':{'origin':'simulated'},'agent':{'observations':frozen['actual_authorized_rows']}}})
     save(context_file,{'conversation':cid,'owner':user['username'],'surface':case['surface'],
      'frozen_packet_sha256':sha(packet_file),'history_unchanged_between_arms':True})
    for current_arm in (['low','medium'] if args.stage=='P1' else ['canonical']):
     path=AUDIT/args.stage/(case['id']+'-'+current_arm+'.json')
     if path.exists():
      old=json.loads(path.read_text(encoding='utf-8'));assert old['frozen_packet_sha256']==sha(packet_file)
      print(json.dumps({'skip_preserved':str(path.relative_to(AUDIT))}),flush=True);continue
     os.environ['COGNISHIELD_AI_REASONER_THINKING']='medium' if current_arm=='medium' else 'low'
     os.environ['COGNISHIELD_AI_EVIDENCE_LAYOUT']='canonical_v1' if current_arm=='canonical' else 'current'
     selected=copy.deepcopy(frozen)
     if current_arm=='canonical':
      candidate=AUDIT/'canonical-freeze-v2'/case['id']/'packet.json'
      layout_freeze=json.loads((AUDIT/'P2-layout-freeze-v2.json').read_text(encoding='utf-8'))
      identity=next(c for c in layout_freeze['cases'] if c['id']==case['id'])
      assert sha(candidate)==identity['packet_sha256']
      assert sha(AUDIT/'P1'/(case['id']+'-low.json'))==identity['P1_low_control_sha256']
      selected.update(json.loads(candidate.read_text(encoding='utf-8')))
     body=TurnRequest(request_id=uuid4(),prompt=case['prompt'])
     approved=approve_hybrid_request(db,store,user,cid,body,manager.snapshot()[1]['source_revision'])
     started=time.monotonic();scope=HybridRequest.create(db,store,user,case['surface'],cid,body,started)
     assert scope is not None,'Exact synthetic role consent required'
     w=len(wires)
     result={'stage':args.stage,'case':case['id'],'arm':current_arm,'surface':case['surface'],'request':case['prompt'],
      'at':datetime.now(timezone.utc).isoformat(),'conversation':cid,'registry_sha256':sha(SPEC),'grading_sha256':sha(AUDIT/'grading-freeze.json'),
      'frozen_packet_sha256':sha(packet_file),'scenario':frozen['scenario_meta'],'consent':approved,'settings':consent_manifest(),
      'model_messages':selected['messages'],'model_schema':selected['schema'],'authorized_results':frozen['inputs']['results'],
      'reasoning_only':True,'new_planner_calls':0,'new_reader_calls':0,'request_budget_seconds':120,
      'automatic_complex_workflow_eligible':scope.multi_model,
      'dispatch_authority':'Explicitly authorized reasoning-only role experiment with exact synthetic owner consent; automatic gateway routing is not under test.'}
     try:
      with scope.activate():raw,model=await scope.generate_role('evidence_reasoner',selected['messages'],selected['schema'])
      result.update(raw=raw,model=model)
      class Replay:
       hybrid=scope
       async def generate(self,messages,**kwargs):
        assert messages==selected['messages'] and kwargs['structured']==selected['schema'],'Replay must validate identical model-visible contract'
        return raw,model
      inputs=frozen['inputs'];sources=[Evidence.model_validate(e) for e in inputs['evidence']]
      decision=await decide(Replay(),case['prompt'],inputs['results'],sources,inputs['history'],inputs['planning'],
       advisory=inputs['advisory'],retrieval=inputs['retrieval'])
      actual_rows=inputs['results'] or frozen['actual_authorized_rows']
      review={'claim_compatibility':compatible_claims(decision,actual_rows,inventory_snapshot(db))}
      released=release_interpretation(decision,review)
      result.update(core_and_application_contract='VALID',decision=decision,typed_review=review,diagnostic_release=released,
       semantic_certification=False,full_gateway_executed=False)
     except Exception as exc:
      result.update(error={'class':type(exc).__name__,'status':getattr(exc,'status_code',None),
       'category':getattr(exc,'provider_category',None),'provider_http_status':getattr(exc,'provider_http_status',None),
       'detail':str(exc)[:800],'validation_diagnostic':getattr(exc,'validation_diagnostic',None)},
       raw=getattr(exc,'raw_output',result.get('raw')),semantic_verdict='NOT_ASSESSED' if not result.get('raw') else 'REQUIRES_FULL_ANSWER_REVIEW')
     result.update(seconds=time.monotonic()-started,role_trace=scope.trace,usage=scope.usage,wires_without_headers=wires[w:],
      scenario_revision_after=manager.snapshot()[1]['source_revision'])
     save(path,result)
     print(json.dumps({'case':case['id'],'arm':current_arm,'seconds':round(result['seconds'],2),
      'dispatches':len(result['wires_without_headers']),'valid':result.get('core_and_application_contract'),
      'error':result.get('error',{}).get('category')}),flush=True)
     if result.get('error',{}).get('provider_http_status') in [400,401,402,403,404,429,500,503]:
      print('STOP_PROVIDER_ERROR_NO_RETRY',flush=True);return
 finally:db.close()

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['P1','P2'],required=True);parser.add_argument('--offset',type=int,default=0);parser.add_argument('--limit',type=int,default=1)
 asyncio.run(main(parser.parse_args()))

