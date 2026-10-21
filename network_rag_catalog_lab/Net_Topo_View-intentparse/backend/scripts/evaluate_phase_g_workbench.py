"""Actual authenticated Workbench -> existing LangGraph/current-config slice.

Disposable SQLite only; real installed Ollama; original failures retained. This
is exposed source acceptance, not the untouched30-case model-quality benchmark.
"""
import argparse,asyncio,json,os,sys,tempfile,time,base64,hashlib
from pathlib import Path
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))


async def main(history=False,snapshots_only=False,source_acceptance=False):
    import httpx
    from fastapi import FastAPI
    from auth.auth import create_access_token
    from db.manager import DatabaseManager
    from local_providers.development import ScenarioManager
    from local_providers.development_api import router as developer
    from llm.gateway_api import router as shared
    from llm.gateway_store import ensure_schema
    from development.bundles import load_bundle
    from scripts.phase_d_audit import Run,source_manifest,digest
    os.environ.update(COGNISHIELD_DEV_WORKBENCH='1',COGNISHIELD_DEV_SIMULATION='0',COGNISHIELD_AI_ENGINE='langgraph_b3',COGNISHIELD_AI_PLANNING='1',COGNISHIELD_AI_SYNTHESIS='1')
    run=Run('G3-generated-snapshots' if snapshots_only else 'G3-recorded-history' if history else 'G2-current-config','real_model_full_agent',{'model':'qwen2.5:1.5b','source_digest':digest(json.dumps(source_manifest(),sort_keys=True).encode()),'scope':'Actual ASGI authentication, developer APIs, shared gateway and Ollama; no second application server or ordinary mutation.'},phase='phase-g')
    with tempfile.TemporaryDirectory(dir=ROOT/'tmp/phase-g',prefix='source-') as directory:
        folder=Path(directory);db=DatabaseManager(str(folder/'app.db'));db.initialize();ensure_schema(db)
        db._development_scenario=ScenarioManager(folder/'state.json',enabled_default=False)
        app=FastAPI();app.state.local_db=db;app.include_router(developer);app.include_router(shared)
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://local-controlled',headers={'Authorization':'Bearer '+create_access_token(927,'G-SOURCE-OWNER','admin')},timeout=240) as client:
                async def call(method,path,body=None):
                    response=await client.request(method,path,json=body);response.raise_for_status();return response.json()
                prefix='/api/v1/development-network/workbench'
                import shutil
                editable=folder/'bundle';shutil.copytree(ROOT/'backend/development/scenarios/healthy_all_sources_v2',editable)
                running=editable/'running_configs.json';external=json.loads(running.read_text(encoding='utf-8'))
                external['data']['records'][0]['values']['config_text']+='! G_JSON_CURRENT_T1\n'
                running.write_text(json.dumps(external,indent=2),encoding='utf-8')
                bundle=load_bundle(editable)
                (run.path/'external-json-T1.json').write_text(json.dumps(bundle,indent=2),encoding='utf-8')
                current=bundle['sources']['running_configs']['data']['records'][0]
                original=current['values']['config_text'].replace('! G_JSON_CURRENT_T1\n','')
                def document(marker):
                    raw=('Recorded maintenance note: '+marker+'. The maintenance window covers inspection only; no device changes are authorized.\n').encode()
                    bundle.setdefault('assets',{})['docs/history.md']={'base64':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest()}
                    bundle['sources']['documents'].update(status='AVAILABLE',captured_at=bundle['manifest']['clock']['now'],data={'files':[{'path':'docs/history.md','name':'Recorded history.md'}]})
                if history:document('G_JSON_CURRENT_T1')
                draft=await call('POST',prefix+'/drafts',{'bundle':bundle})
                status=await call('GET',prefix)
                conversations={kind:(await call('POST','/api/v1/ai/conversations',{'assistant_kind':kind}))['id'] for kind in ['floating','studio']}
                for phase in ([1,2,3] if history else [1,2]):
                    if phase==2:
                        current['values']['config_text']=original+'! G_API_DRAFT_T2\n'
                        current['timestamp']='2026-10-18T01:00:10Z'
                        bundle['manifest']['clock']['now']='2026-10-18T01:00:10Z'
                        bundle['sources']['running_configs']['captured_at']='2026-10-18T01:00:10Z'
                        if history:document('G_API_DRAFT_T2')
                        draft=await call('POST',prefix+'/drafts',{'bundle':bundle,'draft_id':draft['draft_id'],'expected_revision':draft['draft_revision']})
                    if phase==3:
                        choice=next(row for row in status['history'] if row['scenario_id']==bundle['manifest']['scenario_id'])
                        status=await call('POST',prefix+'/history/'+choice['id']+'/restore',{'expected_active':status['context']['source_revision']})
                    else:
                        receipt=await call('POST',prefix+'/drafts/'+draft['draft_id']+'/validate',{'expected_revision':draft['draft_revision']})
                        status=await call('POST',prefix+'/drafts/'+draft['draft_id']+'/activate',{'expected_revision':draft['draft_revision'],'expected_active':status['context']['source_revision'],'validation_hash':receipt['validation_hash']})
                    for kind,cid in conversations.items():
                        if snapshots_only:continue
                        prompt='What is the current configuration for LAB-R1?' if phase==1 else 'Show LAB-R1 current running configuration after the activated edit.'
                        started=time.monotonic();result=await call('POST','/api/v1/ai/conversations/'+cid+'/turns',{'request_id':str(uuid4()),'prompt':prompt,'model':'qwen2.5:1.5b'})
                        marker='G_API_DRAFT_T2' if phase==2 else 'G_JSON_CURRENT_T1'
                        tools=[r['tool'] for r in result.get('observations',[])];ok=(result['status']=='success' and marker in result['answer'] and 'network.configuration' in tools and not result.get('proposal') and not result.get('preview'))
                        run.record('G-CURRENT-'+kind.upper()+'-T'+str(phase),'PASS' if ok else 'FAIL',expected={'marker':marker,'tool':'network.configuration','effect':'read only','provenance':'simulated/current'},actual={'result':result,'active_revision':status['context'],'selected_tools':tools,'transport':'authenticated ASGI public APIs'},prompt=prompt,latency_ms=round((time.monotonic()-started)*1000,2))
                        print(json.dumps({'run':str(run.path),'kind':kind,'phase':phase,'pass':ok,'tools':tools,'answer':result['answer']},ensure_ascii=True),flush=True)
                        if not ok:return False
                        if history:
                            prompt='Read Recorded history.md and explain its maintenance scope and exact note marker. Use the currently active source revision.'
                            started=time.monotonic();result=await call('POST','/api/v1/ai/conversations/'+cid+'/turns',{'request_id':str(uuid4()),'prompt':prompt,'model':'qwen2.5:1.5b'})
                            files=result.get('context_coverage',{}).get('files',{});opposite='G_API_DRAFT_T2' if phase!=2 else 'G_JSON_CURRENT_T1'
                            ok=result['status']=='success' and marker in result['answer'] and opposite not in result['answer'] and files.get('tool')=='document.read' and not result.get('proposal') and not result.get('preview')
                            run.record('G-HISTORY-DOCUMENT-'+kind.upper()+'-T'+str(phase),'PASS' if ok else 'FAIL',expected={'marker':marker,'reader':'document.read','excluded_marker':opposite,'scope':'inspection only; no device changes'},actual={'response':result,'active_revision':status['context'],'model':result.get('model'),'quality_gate':'Inspect actual prose separately; marker and reader checks only'},prompt=prompt,latency_ms=round((time.monotonic()-started)*1000,2))
                            print(json.dumps({'run':str(run.path),'kind':kind,'phase':phase,'document_pass':ok,'answer':result['answer']},ensure_ascii=True),flush=True)
                            if not ok:return False
                    if phase==2:
                        snapshots=db._development_scenario.snapshot()[0]['records']['configuration']
                        retained=sum('G_JSON_CURRENT_T1' in r['values'].get('config_text','') for r in snapshots)
                        run.record('G-SNAPSHOT-T1-RETAINED','PASS' if retained else 'FAIL',expected='T1 retained as historical capture in the active T2 revision',actual={'matching_historical_records':retained})
                        if not retained:return False
                        if snapshots_only:
                            capture=db._development_scenario.capture(1100,status['context']['source_revision'])
                            for kind,cid in conversations.items():
                                prompt='Show LAB-R1 saved configuration snapshots.'
                                started=time.monotonic();result=await call('POST','/api/v1/ai/conversations/'+cid+'/turns',{'request_id':str(uuid4()),'prompt':prompt,'model':'qwen2.5:1.5b'})
                                rows=[row for item in result.get('observations',[]) if item['tool']=='network.configuration' for row in (item.get('data') or {}).get('records',[])]
                                captured=next((row for row in rows if row['id']==capture['id']),None)
                                ok=result['status']=='success' and captured and not captured['current'] and captured['kind']=='configuration_snapshot' and 'G_API_DRAFT_T2' in result['answer'] and 'G_JSON_CURRENT_T1' in result['answer']
                                run.record('G-CAPTURE-'+kind.upper(),'PASS' if ok else 'FAIL',expected={'captured_marker':'G_API_DRAFT_T2','prior_marker':'G_JSON_CURRENT_T1','tool':'network.configuration','scope':'historical; simulated'},actual={'response':result,'capture_record_id':capture['id'],'setup':'Existing ScenarioManager.capture service; no physical device or ordinary SQLite write'},prompt=prompt,latency_ms=round((time.monotonic()-started)*1000,2))
                                print(json.dumps({'run':str(run.path),'surface':kind,'pass':bool(ok),'answer':result['answer']}),flush=True)
                                if not ok:return False
                if source_acceptance:
                    # Independent source gate, not an LLM reasoning benchmark.
                    # Keep actual returned values/answers even when a check fails.
                    failed=False
                    for case in ['stale','error','missing','saved','unknown','future']:
                        external=json.loads(running.read_text(encoding='utf-8'))
                        external['status']={'stale':'STALE','error':'ERROR','missing':'MISSING'}.get(case,'AVAILABLE')
                        external['data']['records'][0]['values']['config_text']=original+'! G_SOURCE_'+case.upper()+'\n'
                        external['data']['records'][0]['timestamp']='2026-10-18T00:55:00Z' if case=='stale' else '2026-10-18T02:00:00Z' if case=='future' else '2026-10-18T01:00:00Z'
                        external['captured_at']=external['data']['records'][0]['timestamp']
                        # Actual filesystem edit -> existing bundle loader; no
                        # direct injection into a reader or answer constructor.
                        running.write_text(json.dumps(external,indent=2),encoding='utf-8')
                        try:edited_bundle=load_bundle(editable)
                        except ValueError as exc:
                            if case!='future' or 'Source capture exceeds virtual now' not in str(exc):raise
                            (run.path/'future-rejected-source.json').write_text(json.dumps(external,indent=2),encoding='utf-8')
                            run.record('G-CURRENT-FUTURE-ADMISSION','PASS',expected='Future source captures are rejected before activation',actual={'error':str(exc),'active_revision_unchanged':status['context'],'no_gateway_read':True})
                            continue
                        edited_bundle['manifest']['clock']['now']='2026-10-18T01:00:10Z'
                        (run.path/('external-json-'+case+'.json')).write_text(json.dumps(edited_bundle,indent=2),encoding='utf-8')
                        draft=await call('POST',prefix+'/drafts',{'bundle':edited_bundle,'draft_id':draft['draft_id'],'expected_revision':draft['draft_revision']})
                        receipt=await call('POST',prefix+'/drafts/'+draft['draft_id']+'/validate',{'expected_revision':draft['draft_revision']})
                        status=await call('POST',prefix+'/drafts/'+draft['draft_id']+'/activate',{'expected_revision':draft['draft_revision'],'expected_active':status['context']['source_revision'],'validation_hash':receipt['validation_hash']})
                        for kind,cid in conversations.items():
                            prompt=('Show LAB-R1 saved configuration snapshots, not its current configuration.' if case=='saved' else
                                    'Show the current running configuration for LAB-NOT-RECORDED.' if case=='unknown' else
                                    'Show LAB-R1 current running configuration and its source availability and capture time.')
                            started=time.monotonic();result=await call('POST','/api/v1/ai/conversations/'+cid+'/turns',{'request_id':str(uuid4()),'prompt':prompt,'model':'qwen2.5:1.5b'})
                            (run.path/(case+'-'+kind+'-response.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
                            answer=result['answer'];observations=result.get('observations',[])
                            records=[row for item in observations if item['tool']=='network.configuration' for row in (item.get('data') or {}).get('records',[])]
                            tools=[item['tool'] for item in observations]
                            ok=not result.get('proposal') and not result.get('generation_preview')
                            if case=='stale':
                                ok=ok and 'G_SOURCE_STALE' in answer and 'stale' in answer.lower() and '00:55:00' in answer and 'current simulated running configuration' not in answer
                            elif case in {'error','missing','future'}:
                                ok=ok and not records and 'G_SOURCE_' not in answer and 'G_JSON_CURRENT_T1' not in answer and 'G_API_DRAFT_T2' not in answer
                                if case!='future':ok=ok and case.upper() in answer.upper()
                            elif case=='saved':
                                ok=ok and bool(records) and all(not row.get('current') for row in records) and 'G_SOURCE_SAVED' not in answer and 'historical' in answer.lower()
                            else:ok=ok and not records and 'G_SOURCE_' not in answer and 'LAB-NOT-RECORDED' in answer
                            if case!='unknown':ok=ok and tools==['network.configuration']
                            if case=='stale':ok=ok and all(e['origin']=='simulated' and e['freshness']=='stale' for e in result.get('evidence',[]))
                            run.record('G-CURRENT-'+kind.upper()+'-'+case.upper(),'PASS' if ok else 'FAIL',expected={'case':case,'authorized_reader':'network.configuration','no_editor_effect':True},actual={'response':result,'selected_tools':tools,'revision':status['context'],'model_reasoning_credit':False},prompt=prompt,latency_ms=round((time.monotonic()-started)*1000,2))
                            failed=failed or not ok
                            print(json.dumps({'run':str(run.path),'case':case,'surface':kind,'pass':bool(ok),'answer':answer,'tools':tools}),flush=True)
                    if failed:return False
                if history:
                    restored=db._development_scenario
                    rows=restored.snapshot()[0]['records']['running_configuration']
                    ok=any('G_JSON_CURRENT_T1' in r['values'].get('config_text','') for r in rows) and any(row['virtual_now'].startswith('2026-10-18T01:00:10') for row in restored.history(owner='G-SOURCE-OWNER'))
                    run.record('G-HISTORY-T2-RECOVERABLE','PASS' if ok else 'FAIL',expected='Exact restored T1 state; replaced T2 remains in recorded history, not falsely injected into the restored past',actual={'restored':restored.snapshot()[1],'history':restored.history(owner='G-SOURCE-OWNER')})
                    if not ok:return False
                print(json.dumps({'run':str(run.path),'pass':True,'browser_acceptance':'NOT_INFERRED'}),flush=True)
                return True
        finally:db.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group();group.add_argument('--history',action='store_true');group.add_argument('--snapshots-only',action='store_true');group.add_argument('--source-acceptance',action='store_true');args=parser.parse_args()
    raise SystemExit(0 if asyncio.run(main(args.history,args.snapshots_only,args.source_acceptance)) else 1)
