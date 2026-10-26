"""Frozen authenticated HTTP gateway evaluation; synthetic DB, existing API/graph.

One temporary acceptance listener8001, stopped in finally. No ordinary app
restart, no source publication, no credentials/HTTP headers in traces.
"""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import time
from unittest.mock import patch
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
AUDIT=ROOT/'tmp/phase-g/iterations/20261026-flash-lite-hybrid'


async def main(arm, fault=None):
    out=AUDIT/(('fault_'+fault) if fault else 'arm_'+arm);out.mkdir(parents=True,exist_ok=True)
    db_path=out/'synthetic.db'
    if db_path.exists():raise RuntimeError('Preserve existing run; no automatic replay')
    os.environ.update(COGNISHIELD_DB_PATH=str(db_path),COGNISHIELD_AI_ENGINE='langgraph_b3',
        COGNISHIELD_AI_PLANNING='1',COGNISHIELD_AI_SYNTHESIS='1',COGNISHIELD_DEV_SIMULATION='1',
        COGNISHIELD_AI_OUTCOMES='1' if arm=='on' else '0',
        COGNISHIELD_AI_HYBRID_USAGE=str(AUDIT/'gateway-cloud-usage.json'))
    import lab_config
    import httpx
    import uvicorn
    from fastapi import FastAPI
    from auth.auth import create_access_token
    from db.manager import DatabaseManager
    from llm.gateway_api import router
    from llm.gateway_models import TurnRequest
    from llm.gateway_store import ensure_schema
    from local_providers.development import ScenarioManager
    from local_providers.chat import runtime
    from scripts.evaluate_phase_f_registry import selected_capabilities
    spec_path=ROOT/'docs/evaluations/phase_g_flash_lite_integration_v1.json'
    spec=json.loads(spec_path.read_text(encoding='utf-8'))
    # Never seize/replace an existing acceptance server.
    with socket.socket() as probe:probe.bind(('127.0.0.1',8001))
    db=DatabaseManager(str(db_path));db.initialize();ensure_schema(db)
    manager=ScenarioManager(out/'scenario.json');db._development_scenario=manager
    for fixture in spec['fixtures'].values():
        manager.change('import',manager.snapshot()[1]['source_revision'],fixture)
    app=FastAPI();app.state.local_db=db;app.include_router(router)
    server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=8001,log_level='error',access_log=False))
    serving=asyncio.create_task(server.serve())
    for _ in range(100):
        if server.started:break
        if serving.done():await serving
        await asyncio.sleep(.05)
    if not server.started:raise RuntimeError('Acceptance HTTP server did not start')
    token=create_access_token(903,'FLASH-LITE-SYNTHETIC-OWNER','engineer')
    other=create_access_token(904,'OTHER-SYNTHETIC-OWNER','engineer')
    audit_user=create_access_token(905,'FLASH-LITE-SYNTHETIC-OWNER','auditor')
    secret=os.getenv('GEMINI_API_KEY','')
    real_send=httpx.AsyncClient.send
    summary=[];security=[]
    def save(name,value):
        text=json.dumps(value,indent=2,ensure_ascii=False)
        if secret:text=text.replace(secret,'[REDACTED]')
        with (out/name).open('x',encoding='utf-8') as f:f.write(text)
    try:
        async with httpx.AsyncClient(base_url='http://127.0.0.1:8001',headers={'Authorization':'Bearer '+token},timeout=125,trust_env=False) as client:
            loaded=await runtime()
            save('effective-backend-process.json',{'pid':os.getpid(),'listener':8001,'local_model':loaded['active_model'],
                'cloud_model':os.getenv('GEMINI_MODEL'),'hybrid':os.getenv('COGNISHIELD_AI_HYBRID'),
                'remote_planning':os.getenv('COGNISHIELD_AI_HYBRID_INTERPRET'),
                'approach_a':os.getenv('COGNISHIELD_AI_OUTCOMES'),'credential_loaded':bool(secret),
                'database':str(lab_config.DB_PATH),'registry_sha256':hashlib.sha256(spec_path.read_bytes()).hexdigest()})
            assert loaded['active_model']=='qwen2.5:1.5b' and os.getenv('GEMINI_MODEL')=='gemini-3.5-flash-lite'
            cases=spec['cases']
            if fault:
                base=next(case for case in cases if case['id']=='FL-C2')
                cases=[{**base,'id':'FAULT-'+surface,'assistant':surface,'turns':base['turns'][:1]} for surface in ['floating','studio']]
            for case in cases:
                manager.change('select',manager.snapshot()[1]['source_revision'],scenario_id=spec['fixtures'][case['variant']]['id'])
                created=await client.post('/api/v1/ai/conversations',json={'assistant_kind':case['assistant']});created.raise_for_status();cid=created.json()['id']
                for number,turn in enumerate(case['turns'],1):
                    body=TurnRequest(request_id=uuid4(),prompt=turn['prompt'],model='qwen2.5:1.5b')
                    context=(await client.get('/api/v1/ai/hybrid-context')).json()
                    assert context['enabled'] and context['eligible'],context
                    payload={'turn':body.model_dump(mode='json'),'expected_source_revision':context['source_revision']}
                    approved=None
                    if fault!='unapproved':
                        approved=await client.post('/api/v1/ai/conversations/'+cid+'/approve-synthetic-cloud',json=payload)
                        approved.raise_for_status()
                    calls=[]
                    async def observed(http,request,*args,**kwargs):
                        is_cloud=request.url.host=='generativelanguage.googleapis.com'
                        entry=None
                        if is_cloud and fault=='unapproved':
                            raise AssertionError('An unapproved complex request reached the cloud transport')
                        if is_cloud or request.url.path in {'/api/chat','/api/embed'}:
                            entry={'host':request.url.host,'path':request.url.path,'body':json.loads(request.content)};calls.append(entry)
                        if is_cloud and fault=='provider-429':
                            response=httpx.Response(429,json={'error':{'status':'RESOURCE_EXHAUSTED'}},request=request)
                        elif is_cloud and fault=='contradiction':
                            wrong='The path fails between Cypress-Edge and Basalt-Transit due to egress interface ge-0/0/1.0 on Basalt-Transit, resulting in a subsequent ingress failure on Orchid-End.'
                            schema=entry['body']['generationConfig']['responseJsonSchema']
                            candidate={'hypotheses':[]}
                            if 'responses' in schema.get('properties',{}):
                                candidate['responses']=[{'id':'request-'+str(i),'answer':wrong,'sources':['S1']} for i in [1,2]]
                            else:candidate.update(answer=wrong,sources=['S1'])
                            response=httpx.Response(200,json={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(candidate)}]}}]},request=request)
                        else:response=await real_send(http,request,*args,**kwargs)
                        if is_cloud and entry is not None:
                            entry.update(http_status=response.status_code,raw_response=response.json())
                        return response
                    started=time.monotonic();result={};error=None
                    try:
                        with patch.object(httpx.AsyncClient,'send',observed):
                            response=await client.post('/api/v1/ai/conversations/'+cid+'/turns',json=body.model_dump(mode='json'))
                            response.raise_for_status();result=response.json()
                    except Exception as exc:error={'type':type(exc).__name__,'detail':str(exc)[:500]}
                    record={'case':case['id'],'turn':number,'arm':arm,'surface':case['assistant'],'prompt':turn['prompt'],
                        'fault_injection':fault,'real_cloud_inference':not bool(fault),
                        'expected':turn,'scenario':context,'approval':approved.json() if approved is not None else {'approved':False},'conversation':cid,
                        'latency_ms':round((time.monotonic()-started)*1000,2),'actual_tools':sorted(selected_capabilities(result)),
                        'provider_requests_without_headers':calls,'result':result,'error':error,'assessment':'UNREVIEWED_NO_CREDIT_FOR_HTTP_OR_FALLBACK'}
                    save(case['id']+'-'+str(number)+'.json',record)
                    if fault:
                        cloud=[r for r in calls if r['host']=='generativelanguage.googleapis.com']
                        if fault=='unapproved':
                            assert not cloud and not result.get('context_coverage',{}).get('hybrid') and result
                        else:
                            assert len(cloud)==1 and all('gemini-3.8' not in r['path'] for r in cloud)
                            synthesis=result.get('context_coverage',{}).get('agent',{}).get('verification',{}).get('synthesis',{})
                            assert 'fallback' in synthesis.get('status',''),synthesis
                            assert 'path fails between Cypress-Edge and Basalt-Transit' not in result.get('answer','')
                    summary.append({'case':case['id'],'turn':number,'tools':record['actual_tools'],'status':result.get('status'),
                        'model':result.get('model'),'latency_ms':record['latency_ms'],'hybrid':result.get('context_coverage',{}).get('hybrid')})
                    print(json.dumps(summary[-1]),flush=True)
            # Real authenticated denial paths: no model/tool interception needed.
            context=(await client.get('/api/v1/ai/hybrid-context')).json()
            body=TurnRequest(request_id=uuid4(),prompt='Explain the synthetic flow',model='qwen2.5:1.5b')
            payload={'turn':body.model_dump(mode='json'),'expected_source_revision':context['source_revision']}
            url='/api/v1/ai/conversations/'+cid+'/approve-synthetic-cloud'
            for name,headers,data,expected in [
                ('other_owner',{'Authorization':'Bearer '+other},payload,{403,404}),
                ('auditor',{'Authorization':'Bearer '+audit_user},payload,{403}),
                ('stale_revision',None,{**payload,'expected_source_revision':'stale'},{409}),
                ('uploaded_context',None,{**payload,'turn':{**payload['turn'],'attachment_ids':[str(uuid4())]}},{403})]:
                response=await client.post(url,json=data,**({'headers':headers} if headers else {}))
                security.append({'name':name,'http_status':response.status_code,'pass':response.status_code in expected})
            # Flag alone cannot dispatch: unapproved arithmetic turn has no scope.
            unapproved=TurnRequest(request_id=uuid4(),prompt='What is 8 plus 5?',model='qwen2.5:1.5b')
            response=await client.post('/api/v1/ai/conversations/'+cid+'/turns',json=unapproved.model_dump(mode='json'));response.raise_for_status()
            value=response.json();security.append({'name':'unapproved_request_no_cloud_scope','pass':'hybrid' not in value.get('context_coverage',{}),'answer':value.get('answer')})
            save('security.json',security);save('summary.json',summary)
    finally:
        server.should_exit=True
        await serving
        db.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arm',choices=['off','on'],required=True)
    parser.add_argument('--fault',choices=['provider-429','contradiction','unapproved'])
    args=parser.parse_args();asyncio.run(main(args.arm,args.fault))
