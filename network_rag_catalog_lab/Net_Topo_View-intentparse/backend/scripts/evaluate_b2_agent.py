"""Opt-in B1/B2 comparison: actual SQLite backups, published V9 and local Ollama.

No app copies, network-device actions, OCR reprocessing or source mutations.
"""
import asyncio
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
from unittest.mock import patch
from uuid import uuid4
import httpx
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))


async def main():
    from lab_config import DB_PATH,LOCAL_OLLAMA_URL
    from db.manager import DatabaseManager
    from llm.gateway import AIGateway
    from llm.gateway_models import TurnRequest
    from llm.gateway_store import ensure_schema
    cases=[('investigation','Investigate why R1 cannot communicate with R2 using the available information.',{'inventory.read','network.topology','network.configuration','network.syslog','network.telemetry'},['root cause']),
        ('evidence followup','What evidence supports your conclusion?',{'inventory.read','network.configuration'},['root cause']),
        ('cross-check','Are you sure? Check the other relevant information sources.',{'network.syslog','network.telemetry','network.incidents'},[]),
        ('multi-source',"Check R2's relevant interfaces and configuration, then investigate available syslogs.",{'inventory.read','network.configuration','network.syslog'},['10.1.1.2','simulated']),
        ('interfaces','What interfaces does R2 have?',{'inventory.read'},['192.168.1.251','10.1.1.2']),
        ('first address','What is the IP address of the first one?',{'inventory.read'},['192.168.1.251']),
        ('other interface','What about the other interface?',{'inventory.read'},['10.1.1.2']),
        ('knowledge coordination',"Explain the published OSPF operation requirements and compare them with R2's stored configuration.",{'knowledge.search','network.configuration'},['interfaces','hostname R2']),
        ('greeting','hello',set(),[]),
        ('topic switch','What is the difference between BGP and OSPF?',set(),['BGP','OSPF']),
        ('unknown','Show R99 interfaces',set(),[]),
        ('missing live','Show live packet loss measurements for R2 right now',{'network.telemetry'},['unavailable'])]
    report=[];real_send=httpx.AsyncClient.send;counters={}
    async def counted_send(client,request,*a,**kw):
        if str(request.url).startswith(LOCAL_OLLAMA_URL):
            key='model_calls' if request.url.path=='/api/chat' else 'embedding_calls' if request.url.path=='/api/embed' else 'discovery_calls'
            counters[key]=counters.get(key,0)+1
        return await real_send(client,request,*a,**kw)
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
        for engine in ['langgraph_b1','langgraph_b2']:
            target=Path(folder)/(engine+'.db')
            src=sqlite3.connect(Path(DB_PATH).as_uri()+'?mode=ro',uri=True);dst=sqlite3.connect(target)
            try:src.backup(dst)
            finally:src.close();dst.close()
            db=DatabaseManager(str(target));ensure_schema(db)
            assert Path(db._db_path).resolve().is_relative_to(Path(folder).resolve())
            g=AIGateway(db);user={'username':'admin','role':'admin'};cid=g.store.create('admin','floating')['id']
            with patch.dict(os.environ,{'COGNISHIELD_AI_ENGINE':engine}),patch.object(httpx.AsyncClient,'send',counted_send):
                for label,prompt,required,values in cases:
                    counters.clear();started=time.monotonic()
                    r=await g.turn(cid,user,TurnRequest(request_id=uuid4(),prompt=prompt,model='qwen2.5:1.5b'))
                    actual={item['tool'] for item in r.observations}
                    correct=r.status=='success' and required<=actual and (bool(required) or not actual) and all(v.lower() in r.answer.lower() for v in values)
                    if label=='unknown':correct=r.kind=='clarification' and not actual
                    if label=='first address':correct=correct and '10.1.1.2' not in r.answer
                    if label=='other interface':correct=correct and '192.168.1.251' not in r.answer
                    item={'engine':engine,'case':label,'passed':correct,'status':r.status,'kind':r.kind,'tools':sorted(actual),
                        'latency_ms':round((time.monotonic()-started)*1000,2),**counters,'agent':r.context_coverage.get('agent'),
                        'answer':r.answer,'origins':sorted({e.origin for e in r.evidence})}
                    report.append(item);print(json.dumps({k:v for k,v in item.items() if k not in {'answer','agent'}}),flush=True)
                # Existing extracted mixed-content PDF; no expensive re-OCR.
                with db._connect() as c:
                    row=c.execute("SELECT * FROM ai_attachments WHERE name='generation process.pdf' ORDER BY rowid DESC LIMIT 1").fetchone()
                    if row:
                        c.execute('INSERT INTO ai_attachments(id,conversation_id,owner,name,digest,byte_size,segments,original_bytes) VALUES(?,?,?,?,?,?,?,?)',
                            (uuid4().hex,cid,'admin',row['name'],row['digest'],row['byte_size'],row['segments'],row['original_bytes']))
                if row:
                    for page in [4,5]:
                        counters.clear();started=time.monotonic()
                        r=await g.turn(cid,user,TurnRequest(request_id=uuid4(),prompt=f'What does page {page} of my uploaded PDF explain?',model='qwen2.5:1.5b'))
                        correct=r.status=='success' and not r.observations and any(e.page==page for e in r.evidence) and bool(r.answer) and 'evidence IDs' not in r.answer
                        report.append({'engine':engine,'case':f'PDF page {page}','passed':correct,'answer':r.answer,'latency_ms':round((time.monotonic()-started)*1000,2),**counters,'agent':r.context_coverage.get('agent')})
                        print(json.dumps({'engine':engine,'page':page,'passed':correct}),flush=True)
            db.close()
    result={'model':'qwen2.5:1.5b','source':'ordinary read-only SQLite backups; existing simulation providers; published V9 requirements; actual Ollama','results':report}
    (ROOT/'tmp/ai-intelligence-audit/b2-comparison.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    return all(item['passed'] for item in report if item['engine']=='langgraph_b2')


if __name__=='__main__':raise SystemExit(0 if asyncio.run(main()) else 1)
