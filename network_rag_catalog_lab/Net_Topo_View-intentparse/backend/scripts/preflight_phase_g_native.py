"""Triage all141 through actual V9 review; NOT natural-language journey credit."""
import argparse,asyncio,json,os,sys
from copy import deepcopy
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))

async def main(args):
 import httpx
 from fastapi import FastAPI
 from auth.auth import create_access_token
 from db.manager import DatabaseManager
 from llm.gateway_api import router
 from llm.gateway_knowledge import read_release
 from local_providers.knowledge import knowledge_root
 from local_providers.knowledge_review import identity
 from local_providers.development import ScenarioManager
 from local_providers.development_api import router as development
 from scripts.evaluate_phase_g_native import scenario_for
 from development.starter import starter_bundle
 from scripts.phase_d_audit import Run,source_manifest
 os.environ.update(COGNISHIELD_DEV_WORKBENCH='1',COGNISHIELD_DEV_SIMULATION='0')
 previous=(ROOT/args.resume).resolve();assert previous.is_relative_to((ROOT/'tmp/phase-g/iterations').resolve())
 rows=[json.loads(line) for line in (previous/'cases.jsonl').read_text().splitlines()]
 passed=next(row for row in reversed(rows) if row['outcome']=='PASS')
 trace=json.loads((previous/passed['actual']['trace']).read_text())
 confirmation=trace['explicit_confirmation'];cid=confirmation['conversation_id'];sid=confirmation['session_id']
 release,manifest,pointer=read_release(knowledge_root()/'storage/catalog_releases')
 reviews=json.loads((release/manifest['cognishield_engineer_reviews']['artifact_path']).read_text())['bindings']
 run=Run('G7-all-binding-review-preflight','unit_deterministic',{'knowledge_release':pointer['release_id'],'source_manifest':source_manifest(),'model_calls_expected':0,'not_journey_credit':True,'integration_scope':'Actual authenticated V9 review, deterministic supplied selections'},phase='phase-g')
 workspace=Path(json.loads((previous/'workspace-ref.json').read_text())['path'])
 state_name=args.state_file
 if Path(state_name).name!=state_name or not state_name.endswith('.json'):raise ValueError('Use a JSON basename inside the owned evaluator workspace')
 db=DatabaseManager(str(workspace/'app.db'));db._development_scenario=ScenarioManager(workspace/state_name,enabled_default=False)
 app=FastAPI();app.state.local_db=db;app.include_router(development);app.include_router(router)
 bundle=starter_bundle();inv=bundle['sources']['inventory']['data'];selections=[];cases=[]
 overrides={}
 if args.positive_variants:
  variants=json.loads((ROOT/args.positive_variants).read_text(encoding='utf-8'))
  assert variants['knowledge_release']==pointer['release_id']
  overrides={c['binding_case_id']:c for c in variants['cases']}
  assert overrides and len(overrides)==len(variants['cases'])
 for number,binding in enumerate(manifest['template_bindings'],1):
  binding_case='G7-NATIVE-'+binding['vendor'].upper()+'-'+binding['operation_id'].upper()
  if overrides and binding_case not in overrides:continue
  variant=overrides.get(binding_case)
  fixture=variant['fixture'] if variant else next(r for r in reviews if r['identity']==identity(binding))['method']['fixtures'][0]
  small,device=scenario_for(binding,fixture['parameters']);old_id=device['id'];new_id=3000+number
  device=deepcopy(device);device.update(id=new_id,hostname='G7-'+binding['vendor']+'-'+str(number),management_ip='198.18.'+str(number//250)+'.'+str(number%250+1))
  inv['devices'].append(device)
  for interface in small['sources']['inventory']['data']['interfaces']:
   if interface['device_id']!=old_id:continue
   inv['interfaces'].append({**interface,'id':10000+len(inv['interfaces']),'device_id':new_id})
  selections.append({'operation_id':binding['operation_id'],'target_host':device['hostname'],'parameters':fixture['parameters'],'template_id':binding['artifact_path']})
  cases.append({'id':variant['id'].replace('G7-NATIVE-','G7-PREFLIGHT-') if variant else binding_case.replace('G7-NATIVE-','G7-PREFLIGHT-'),'binding':binding,'device':device,'parameters':fixture['parameters']})
 if args.only:
  pairs=[(selection,case) for selection,case in zip(selections,cases) if case['binding']['operation_id']+':'+case['binding']['vendor'] in args.only]
  selections=[p[0] for p in pairs];cases=[p[1] for p in pairs]
  if len(cases)!=len(set(args.only)):raise ValueError('Unknown or duplicated selected binding')
 try:
  async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://controlled-g7',headers={'Authorization':'Bearer '+create_access_token(929,'G7-ENGINEER','admin')},timeout=240) as client:
   async def call(method,path,body=None):
    response=await client.request(method,path,json=body)
    if response.status_code>=400:raise RuntimeError(str(response.status_code)+' '+response.text[:10000])
    return response.json()
   prefix='/api/v1/development-network/workbench';state=await call('GET',prefix)
   control_file=previous/('controlled-draft-ref.json' if state_name=='state.json' else 'controlled-draft-ref-'+Path(state_name).stem+'.json')
   controlled=json.loads(control_file.read_text(encoding='utf-8')) if control_file.exists() else None
   current=await call('GET',prefix+'/drafts/'+controlled['draft_id']) if controlled else None
   with db._connect() as c:revision=c.execute('SELECT revision FROM studio_v9_sessions WHERE id=?',(sid,)).fetchone()[0]
   results=[]
   for start in range(args.offset,len(selections),24):
    # Keep each controlled scenario within the existing100-device projection
    # budget. Do not increase application limits to fit an evaluator fixture.
    partial=deepcopy(bundle);ids={d['id'] for d in inv['devices'][:3]}|{c['device']['id'] for c in cases[start:start+24]}
    partial['sources']['inventory']['data']['devices']=[d for d in inv['devices'] if d['id'] in ids]
    partial['sources']['inventory']['data']['interfaces']=[i for i in inv['interfaces'] if i['device_id'] in ids]
    control={'draft_id':current['draft_id'],'expected_revision':current['draft_revision']} if current else {}
    draft=await call('POST',prefix+'/drafts',{'bundle':partial,**control})
    current=draft
    control_file.write_text(json.dumps({'draft_id':draft['draft_id'],'expected_revision':draft['draft_revision']}),encoding='utf-8')
    receipt=await call('POST',prefix+'/drafts/'+draft['draft_id']+'/validate',{'expected_revision':draft['draft_revision']})
    state=await call('POST',prefix+'/drafts/'+draft['draft_id']+'/activate',{'expected_revision':draft['draft_revision'],'expected_active':state['context']['source_revision'],'validation_hash':receipt['validation_hash']})
    result=await call('POST','/api/v1/ai/studio/preview',{'conversation_id':cid,'prompt':'Engineer review compatibility triage; no rendering, save or device action','model':'qwen2.5:1.5b','output_kind':'native','params':{'_v9_session':sid},'expected_revision':revision,'confirm_order':True,'selection':selections[start:start+24]})
    revision=result['session_revision']
    with (run.path/f'batch-{start//24+1}.json').open('x',encoding='utf-8') as f:json.dump({'context':state['context'],'cases':cases[start:start+24],'preview':result},f,indent=2)
    for case,task in zip(cases[start:start+24],result['tasks']):
     outcome='PASS' if task['status'] in {'validated','ready','rendered'} and not task['issues'] else 'BLOCKED'
     run.record(case['id'],outcome,expected='Actual V9 ready under existing published profile/schema and authored fixture',actual={'task_status':task['status'],'issues':task['issues']},classification='CONTEXT_OR_SCHEMA_CONSTRAINT' if outcome=='BLOCKED' else None)
     results.append({'id':case['id'],'outcome':outcome,'issues':task['issues']})
    print(json.dumps({'run':str(run.path),'processed':len(results),'ready':sum(r['outcome']=='PASS' for r in results),'blocked':sum(r['outcome']=='BLOCKED' for r in results)}),flush=True)
   with (run.path/'summary.json').open('x',encoding='utf-8') as f:json.dump({'cases':results,'journeys_credited':0,'release':pointer['release_id'],
    'ordinary_data_changed':False,'offset':args.offset,'state_file':state_name},f,indent=2)
 finally:db.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--resume',required=True);p.add_argument('--offset',type=int,default=0);p.add_argument('--state-file',default='state.json');p.add_argument('--only',action='append',help='operation_id:vendor')
 p.add_argument('--positive-variants',help='Separately frozen valid positive case registry')
 args=p.parse_args()
 if args.offset not in range(0,141,24):p.error('Offset must be a24-case boundary within141')
 asyncio.run(main(args))
