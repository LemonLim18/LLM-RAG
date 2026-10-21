"""Real local models + authenticated application routes on disposable SQLite.

No secondary server, device execution, publication or ordinary data mutation.
Run --only with a comma separated case set to revisit a newly affected case.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
from datetime import timedelta
from uuid import uuid4
import httpx
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
BUFFER='hostname B3LAB\n! UNSAVED_B3_MARKER\nrouter ospf 10\n router-id 192.0.2.1\n network 10.1.0.0 0.0.0.255 area 0\nrouter bgp 65000\n neighbor 192.0.2.2 remote-as 65001\n! PRESERVE_B3_MARKER\n'


async def main(only):
    from fastapi import FastAPI
    from lab_config import DB_PATH
    from auth.auth import create_access_token
    from db.manager import DatabaseManager
    from llm.gateway_store import ensure_schema
    from llm.gateway_api import router
    os.environ['COGNISHIELD_AI_ENGINE']='langgraph_b3'
    report=[];output=ROOT/'tmp/ai-intelligence-audit'/('b3-studio-'+('-'.join(sorted(only)) if only else 'live')+'.json')
    output.with_suffix('.model.json').write_text('[]',encoding='utf-8')
    from local_providers import chat
    real_generate=chat.generate;model_results=[]
    async def observed(*args,**kwargs):
        result=await real_generate(*args,**kwargs)
        model_results.append({'structured':bool(kwargs.get('structured')),'response':result[0]})
        output.with_suffix('.model.json').write_text(json.dumps(model_results,indent=2),encoding='utf-8')
        return result
    recorder=patch.object(chat,'generate',observed);recorder.start()
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
        target=Path(folder)/'b3.db';src=sqlite3.connect(Path(DB_PATH).as_uri()+'?mode=ro',uri=True);dst=sqlite3.connect(target)
        try:src.backup(dst)
        finally:src.close();dst.close()
        db=DatabaseManager(str(target));ensure_schema(db)
        assert Path(db._db_path).resolve().is_relative_to(Path(folder).resolve())
        with db._connect() as c:
            uid=c.execute("SELECT id FROM users WHERE username='admin'").fetchone()[0]
            c.execute("INSERT INTO devices(id,hostname,vendor,os_version,model,role) VALUES (1003,'B3-EDGE','cisco_xe','17.9','C9500','edge')")
            c.execute("INSERT INTO interfaces(device_id,name,interface_type,ip_address) VALUES(1003,'GigabitEthernet0/1','routed','10.1.1.3')")
        app=FastAPI();app.state.local_db=db;app.include_router(router)
        headers={'Authorization':'Bearer '+create_access_token(uid,'admin','engineer',timedelta(minutes=45))}
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test',headers=headers,timeout=240) as client:
            cid=(await client.post('/api/v1/ai/conversations',json={'assistant_kind':'studio'})).json()['id']
            editor=dict(document_id='b3-eval-buffer',path='playbooks/drafts/b3-live.cfg',content=BUFFER,language='plaintext',model_id='b3-model',model_version=8,buffer_epoch=1,saved_revision=0,is_dirty=True,read_only=False)
            async def turn(label,prompt,check,context=True):
                started=time.monotonic();body={'request_id':str(uuid4()),'prompt':prompt,'model':'qwen2.5:1.5b'}
                if context:body['editor']=editor
                response=await client.post('/api/v1/ai/conversations/'+cid+'/turns',json=body)
                result=response.json();passed=response.status_code==200 and check(result)
                item={'case':label,'prompt':prompt,'passed':passed,'http':response.status_code,'latency_ms':round((time.monotonic()-started)*1000,2),'response':result}
                report.append(item);output.write_text(json.dumps(report,indent=2),encoding='utf-8')
                print(json.dumps({k:v for k,v in item.items() if k!='response'}),flush=True);return result
            if not only or 'explain' in only:
                await turn('unsaved explanation','Explain the active unsaved configuration. Identify its OSPF and BGP settings and quote the UNSAVED_B3_MARKER comment. Do not modify it.',lambda r:r.get('kind')=='answer' and 'UNSAVED_B3_MARKER' in r.get('answer','') and '192.0.2.1' in r['answer'] and '192.0.2.2' in r['answer'] and r.get('context_coverage',{}).get('routing',{}).get('editor'))
            if not only or 'edit' in only:
                edited=await turn('BGP modification','In the open configuration, replace BGP neighbor 192.0.2.2 with 192.0.2.44. Keep the entire original OSPF section and every other line unchanged.',lambda r:r.get('kind')=='edit_proposal' and (r.get('proposal') or {}).get('suggested')==BUFFER.replace('192.0.2.2 remote-as','192.0.2.44 remote-as'))
                if edited.get('proposal'):
                    await turn('explain proposal','Explain your modification.',lambda r:r.get('kind')=='answer' and not r.get('proposal') and '192.0.2.44' in r.get('answer','') and 'proposal' in r['answer'])
                    await turn('correction','Change that address instead to 192.0.2.55; keep the original OSPF section.',lambda r:r.get('kind')=='edit_proposal' and (r.get('proposal') or {}).get('suggested')==BUFFER.replace('192.0.2.2 remote-as','192.0.2.55 remote-as'))
            if not only or 'general' in only:
                await turn('general topic switch','Hello, what is 1 + 1?',lambda r:r.get('status')=='success' and '2' in r.get('answer','') and 'BGP' not in r['answer'] and not r.get('context_coverage',{}).get('routing',{}).get('editor'))
            if not only or 'knowledge' in only:
                await turn('published comparison',"Explain the published OSPF operation requirements and compare them with R2's stored configuration.",lambda r:r.get('kind')=='answer' and 'interfaces' in r.get('answer','') and 'hostname R2' in r['answer'] and not r.get('preview'))
            if not only or 'generation' in only:
                # Omit BGP remote AS deliberately, then supply it through the
                # existing authoritative review API, not another LLM interpretation.
                prompt='Generate native configuration on B3-EDGE: configure a static route to 203.0.113.0/24 via 10.1.1.1; configure a BGP neighbor 192.0.2.2 with local AS 65000. Ask me for the remote AS.'
                generated=await turn('V9 multi-operation clarification',prompt,lambda r:r.get('kind')=='generation_preview' and len((r.get('preview') or {}).get('tasks',[]))==2,False)
                preview=generated.get('preview')
                if preview:
                    print(json.dumps({'review_operations':[t['parsed_intent']['action'] for t in preview['tasks']],'plan_status':preview['plan_status']}),flush=True)
                    sid=preview['parsed_intent']['_v9_session'];selection=[]
                    desired={'configure_static_route':{'destination':'203.0.113.0/24','next_hop':'10.1.1.1'},'configure_bgp_neighbor':{'local_as':65000,'neighbor_ip':'192.0.2.2','remote_as':65001}}
                    for index,task in enumerate(preview['tasks']):
                        op=task['parsed_intent']['action'] or ['configure_static_route','configure_bgp_neighbor'][index]
                        selection.append({'task_id':task['task_id'],'operation_id':op,'target_host':'B3-EDGE','parameters':desired.get(op,task['parsed_intent']['parameters'])})
                    revised=await client.post('/api/v1/ai/studio/preview',json={'conversation_id':cid,'prompt':prompt,'model':'qwen2.5:1.5b','output_kind':'native','params':{'_v9_session':sid},'expected_revision':preview['session_revision'],'selection':selection})
                    reviewed=revised.json();ready=revised.status_code==200 and reviewed.get('plan_status')=='ready'
                    report.append({'case':'authoritative review correction','passed':ready,'http':revised.status_code,'response':reviewed})
                    if ready:
                        response=await client.post('/api/v1/ai/studio/render',json={'conversation_id':cid,'session_id':sid,'expected_revision':reviewed['session_revision'],'output_kind':'native','model':'qwen2.5:1.5b'})
                        drafts=response.json();content='\n'.join(d['content'] for d in drafts.get('documents',[]))
                        passed=response.status_code==200 and '203.0.113.0' in content and 'remote-as 65001' in content and not drafts.get('saved')
                        report.append({'case':'explicit reviewed native output','passed':passed,'http':response.status_code,'response':drafts})
                        print(json.dumps({'case':'explicit reviewed native output','passed':passed,'http':response.status_code}),flush=True)
                    output.write_text(json.dumps(report,indent=2),encoding='utf-8')
        db.close()
    recorder.stop()
    return all(row['passed'] for row in report)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--only',default='');args=parser.parse_args()
    raise SystemExit(0 if asyncio.run(main(set(args.only.split(',')) if args.only else set())) else 1)
