"""Exposed, real-model document/source acceptance, not a blind quality score."""
import asyncio,base64,hashlib,json,os,sys,tempfile,time
from pathlib import Path
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))


async def main(selection_only=False,ocr_explanations=False):
    import httpx
    from fastapi import FastAPI
    from auth.auth import create_access_token
    from db.manager import DatabaseManager
    from llm.gateway_api import router as shared
    from llm.gateway_store import ensure_schema
    from local_providers.development import ScenarioManager
    from local_providers.development_api import router as developer
    from development.starter import starter_bundle
    from scripts.phase_d_audit import Run,source_manifest,digest
    os.environ.update(COGNISHIELD_DEV_WORKBENCH='1',COGNISHIELD_DEV_SIMULATION='0',COGNISHIELD_AI_ENGINE='langgraph_b3',COGNISHIELD_AI_PLANNING='1',COGNISHIELD_AI_SYNTHESIS='1')
    run=Run('G9-ocr-explanations' if ocr_explanations else 'G3-document-selection' if selection_only else 'G3-documents','real_model_full_agent',{'model':'qwen2.5:1.5b','source_digest':digest(json.dumps(source_manifest(),sort_keys=True).encode()),'independent_holdout':False},phase='phase-g')
    failed=False
    with tempfile.TemporaryDirectory(dir=ROOT/'tmp/phase-g',prefix='documents-') as directory:
        folder=Path(directory);db=DatabaseManager(str(folder/'app.db'));db.initialize();ensure_schema(db)
        manager=ScenarioManager(folder/'state.json',enabled_default=False);db._development_scenario=manager
        app=FastAPI();app.state.local_db=db;app.include_router(developer);app.include_router(shared)
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://local-controlled',headers={'Authorization':'Bearer '+create_access_token(928,'G-DOCUMENT-OWNER','admin')},timeout=240) as client:
                async def call(method,path,body=None):
                    response=await client.request(method,path,json=body);response.raise_for_status();return response.json()
                if ocr_explanations:
                    from unittest.mock import patch
                    from scripts.evaluate_phase_f_registry import attachment_bytes
                    spec=json.loads((ROOT/'docs/evaluations/phase_f_case_registry.json').read_text())
                    name,raw=attachment_bytes(spec['document_fixtures']['clear-screenshot'])[0]
                    provider_calls=[];original_send=httpx.AsyncClient.send
                    async def traced_send(http,request,*args,**kwargs):
                        if request.url.path in {'/api/chat','/api/generate','/api/embed','/api/embeddings'}:
                            payload=json.loads(request.content)
                            provider_calls.append({'endpoint':request.url.path,'model':payload.get('model'),
                                'messages':payload.get('messages',[]),'structured_schema':payload.get('format')})
                        return await original_send(http,request,*args,**kwargs)
                    for surface in ['floating','studio']:
                        cid=(await call('POST','/api/v1/ai/conversations',{'assistant_kind':surface}))['id']
                        uploaded=await client.post('/api/v1/ai/conversations/'+cid+'/attachments',content=raw,headers={'X-File-Name':name})
                        uploaded.raise_for_status()
                        for label,prompt in [('EXPLANATION','Explain the OSPF and BGP parameters in my attached screenshot. Keep the local and remote AS roles distinct; do not infer diagram connections.'),
                                ('FOLLOWUP','Which protocol do those AS numbers belong to, and what do the two roles mean?'),
                                ('TOPIC','New topic: what is 1 + 1?')]:
                            provider_calls.clear();started=time.monotonic()
                            with patch.object(httpx.AsyncClient,'send',traced_send):
                                result=await call('POST','/api/v1/ai/conversations/'+cid+'/turns',{'request_id':str(uuid4()),'prompt':prompt,'model':'qwen2.5:1.5b'})
                            coverage=result.get('context_coverage',{});answer=result['answer']
                            ok=result['status']=='success' and not result.get('proposal') and not result.get('preview')
                            if label=='TOPIC':ok=ok and '2' in answer and not result.get('evidence') and not coverage.get('files')
                            else:
                                ok=ok and coverage.get('routing',{}).get('attachments') and 'BGP' in answer
                                if label=='EXPLANATION':ok=ok and all(value in answer for value in ['OSPF','10','40','65020','65030'])
                                else:
                                    # The follow-up asks what the roles mean,
                                    # not for numeric values to be repeated.
                                    # Preserve factual/meaning checks and manual
                                    # prose review instead of rewarding repetition.
                                    from llm.orchestration.verification import document_answer_errors
                                    ok=ok and not document_answer_errors(answer,[{'source':name,'text':spec['document_fixtures']['clear-screenshot']['expected_ocr_text']}],question=prompt)
                            failed|=not ok
                            run.record('G-OCR-'+label+'-'+surface.upper(),'PASS' if ok else 'FAIL',
                                expected={'requested_capability':'explanation' if label!='TOPIC' else 'conversation','source':name if label!='TOPIC' else None,
                                    'source_values':'OSPF hello10/dead40; BGP local65020/remote65030','prohibited':'AS reassignment, invented diagram relationships or editor effects'},
                                actual={'response':result,'provider_calls':list(provider_calls),'provider_call_count':len(provider_calls),
                                    'quality_grade':'PENDING_FULL_PROSE_REVIEW; token checks alone do not establish adequacy'},
                                prompt=prompt,latency_ms=round((time.monotonic()-started)*1000,2))
                            print(json.dumps({'run':str(run.path),'surface':surface,'case':label,'minimum_checks':bool(ok),'answer':answer}),flush=True)
                    (run.path/'result.json').write_text(json.dumps({'complete':True,'minimum_checks_passed':not failed,'holdout':False,'full_prose_quality':'PENDING_MANUAL_REVIEW'},indent=2),encoding='utf-8')
                    return not failed
                prefix='/api/v1/development-network/workbench';bundle=starter_bundle()
                bundle['sources']['documents']['data']={'files':[{'path':'docs/maintenance.md','name':'Maintenance.md'}]}
                bundle['sources']['attachments'].update(status='MISSING',data={'files':[]})
                conversations={kind:(await call('POST','/api/v1/ai/conversations',{'assistant_kind':kind}))['id'] for kind in ['floating','studio']}
                draft=None;state=await call('GET',prefix)
                for phase,window in ([(2,'18:20 UTC')] if selection_only else [(1,'17:40 UTC'),(2,'18:20 UTC')]):
                    text='# Maintenance\nThe maintenance window starts at '+window+'. Only the BGP neighbor address is to change. Keep the existing OSPF section unchanged. Review the diff before explicitly saving; no automatic deployment is authorized.\n'
                    raw=text.encode();bundle['assets']['docs/maintenance.md']={'base64':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest()}
                    if phase==2:
                        bundle['manifest']['clock']['now']='2026-10-18T01:01:00Z'
                        bundle['sources']['documents']['captured_at']='2026-10-18T01:01:00Z'
                    draft=await call('POST',prefix+'/drafts',{'bundle':bundle,**({'draft_id':draft['draft_id'],'expected_revision':draft['draft_revision']} if draft else {})})
                    preview=await call('POST',prefix+'/drafts/'+draft['draft_id']+'/extract',{'expected_revision':draft['draft_revision'],'category':'documents','path':'docs/maintenance.md'})
                    assert window in preview['segments'][0]['text']
                    receipt=await call('POST',prefix+'/drafts/'+draft['draft_id']+'/validate',{'expected_revision':draft['draft_revision']})
                    state=await call('POST',prefix+'/drafts/'+draft['draft_id']+'/activate',{'expected_revision':draft['draft_revision'],'expected_active':state['context']['source_revision'],'validation_hash':receipt['validation_hash']})
                    if selection_only:continue
                    for surface,cid in conversations.items():
                        prompt='Read Maintenance.md. When does the window start, what will change and what must stay unchanged?'
                        started=time.monotonic();result=await call('POST','/api/v1/ai/conversations/'+cid+'/turns',{'request_id':str(uuid4()),'prompt':prompt,'model':'qwen2.5:1.5b'})
                        coverage=result.get('context_coverage',{});answer=result['answer']
                        ok=(result['status']=='success' and window in answer and 'BGP' in answer and 'OSPF' in answer and coverage.get('files',{}).get('tool')=='document.read' and result.get('model')=='qwen2.5:1.5b' and any(e['origin']=='simulated' for e in result['evidence']) and not result.get('preview') and not result.get('proposal'))
                        failed|=not ok
                        run.record('G-DOCUMENT-'+surface.upper()+'-T'+str(phase),'PASS' if ok else 'FAIL',expected={'window':window,'scope':'BGP change, OSPF preserved','tool':'document.read','synthesis':'actual model'},actual={'response':result,'active_revision':state['context']},prompt=prompt,latency_ms=round((time.monotonic()-started)*1000,2))
                        print(json.dumps({'run':str(run.path),'surface':surface,'phase':phase,'pass':ok,'answer':answer}),flush=True)
                if selection_only:
                    for surface,cid in conversations.items():
                        uploaded=await client.post('/api/v1/ai/conversations/'+cid+'/attachments',content=b'Backups are retained for 21 days. This retention note is unrelated to routing maintenance.',headers={'Content-Type':'application/octet-stream','X-File-Name':'Retention.md'})
                        uploaded.raise_for_status()
                        for label,prompt,name,need in [
                            ('UPLOAD','Read this attached file. What is its backup retention period?','Retention.md','21'),
                            ('SCENARIO','Read Maintenance.md. When does the window start and which protocol must stay unchanged?','Maintenance.md','18:20'),
                            ('FOLLOWUP','What protocol must stay unchanged in that document?','Maintenance.md','OSPF')]:
                            started=time.monotonic();result=await call('POST','/api/v1/ai/conversations/'+cid+'/turns',{'request_id':str(uuid4()),'prompt':prompt,'model':'qwen2.5:1.5b'})
                            selected={i['name'] for i in result.get('context_coverage',{}).get('files',{}).get('selected_documents',[])}
                            ok=result['status']=='success' and selected=={name} and need in result['answer'] and not result.get('proposal') and not result.get('preview')
                            failed|=not ok
                            run.record('G-DOC-SELECTION-'+label+'-'+surface.upper(),'PASS' if ok else 'FAIL',expected={'only_source':name,'required_content':need,'effect':'read only'},actual=result,prompt=prompt,latency_ms=round((time.monotonic()-started)*1000,2))
                            print(json.dumps({'run':str(run.path),'surface':surface,'case':label,'pass':ok,'selected':sorted(selected),'answer':result['answer']}),flush=True)
                for surface,cid in conversations.items():
                    prompt='New topic: what is 1 + 1?';result=await call('POST','/api/v1/ai/conversations/'+cid+'/turns',{'request_id':str(uuid4()),'prompt':prompt,'model':'qwen2.5:1.5b'})
                    ok=(result['status']=='success' and '2' in result['answer'] and not result['evidence'] and not result['context_coverage'].get('files'))
                    failed|=not ok;run.record('G-DOCUMENT-TOPIC-SWITCH-'+surface.upper(),'PASS' if ok else 'FAIL',expected='Arithmetic without document context or readers',actual=result,prompt=prompt)
                (run.path/'result.json').write_text(json.dumps({'complete':True,'passed':not failed,'holdout':False,'model_capacity_gate':'NOT_ASSESSED'},indent=2),encoding='utf-8')
                print(json.dumps({'run':str(run.path),'passed':not failed}),flush=True)
        finally:db.close()
    return not failed


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group();group.add_argument('--selection-only',action='store_true');group.add_argument('--ocr-explanations',action='store_true');args=parser.parse_args()
    raise SystemExit(0 if asyncio.run(main(args.selection_only,args.ocr_explanations)) else 1)
