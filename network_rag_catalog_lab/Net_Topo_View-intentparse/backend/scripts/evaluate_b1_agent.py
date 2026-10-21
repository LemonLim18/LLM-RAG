"""Compare legacy/B1 on identical SQLite snapshots and real local inference."""
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
    cases=[('interfaces','What interfaces does R2 have?','inventory.read',['192.168.1.251','10.1.1.2']),
        ('first address','What is the IP address of the first one?','inventory.read',['192.168.1.251']),
        ('confirmation','Are you sure?','inventory.read',['192.168.1.251']),
        ('configuration',"Show R2's stored configuration.",'network.configuration',['hostname R2','simulated']),
        ('latest syslog','What is the latest available syslog for R1?','network.syslog',['simulated']),
        ('connection','Explain the recorded connection between R1 and R2.','network.topology',['R1','R2','GigabiEthernet0/1']),
        ('investigation','Investigate R1 packet loss using topology, telemetry, logs, incidents and configuration history.','network.telemetry',['simulated','verified root cause']),
        ('greeting','hello',None,[]),
        ('paraphrase','Could you describe what our setup contains?','inventory.read',['R1','R2']),
        ('unknown','Show R99 interfaces',None,[]),
        ('missing live','Show live packet loss measurements for R2 right now','network.telemetry',['unavailable'])]
    report=[];real_send=httpx.AsyncClient.send
    counters={}
    async def counted_send(client,request,*a,**kw):
        if str(request.url).startswith(LOCAL_OLLAMA_URL):
            key='model_calls' if request.url.path=='/api/chat' else 'embedding_calls' if request.url.path=='/api/embed' else 'discovery_calls'
            counters[key]=counters.get(key,0)+1
        return await real_send(client,request,*a,**kw)
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
        for engine in ['legacy','langgraph_b1']:
            target=Path(folder)/(engine+'.db')
            src=sqlite3.connect(Path(DB_PATH).as_uri()+'?mode=ro',uri=True);dst=sqlite3.connect(target)
            try:src.backup(dst)
            finally:src.close();dst.close()
            db=DatabaseManager(str(target));g=AIGateway(db);user={'username':'admin','role':'admin'};cid=g.store.create('admin','floating')['id']
            with patch.dict(os.environ,{'COGNISHIELD_AI_ENGINE':engine}),patch.object(httpx.AsyncClient,'send',counted_send):
                for label,prompt,tool,values in cases:
                    counters.clear();started=time.monotonic()
                    r=await g.turn(cid,user,TurnRequest(request_id=uuid4(),prompt=prompt,model='qwen2.5:1.5b'))
                    actual=[item['tool'] for item in r.observations]
                    correct=(tool in actual if tool else not actual) and all(v in r.answer for v in values)
                    if label=='unknown':correct=(r.kind=='clarification' and not actual) or ('Unresolved device references: R99' in r.answer and all(not (x.get('data') or {}).get('devices') for x in r.observations))
                    if label=='first address':correct=correct and '10.1.1.2' not in r.answer
                    item={'engine':engine,'case':label,'passed':correct,'status':r.status,'kind':r.kind,'tools':actual,
                        'latency_ms':round((time.monotonic()-started)*1000,2),'model_calls':counters.get('model_calls',0),
                        'embedding_calls':counters.get('embedding_calls',0),'tool_calls':r.context_coverage.get('agent',{}).get('tool_calls',len(actual)),
                        'agent':r.context_coverage.get('agent'),'answer':r.answer,'origins':sorted({e.origin for e in r.evidence})}
                    report.append(item);print(json.dumps({k:v for k,v in item.items() if k not in {'answer','agent'}}),flush=True)
            db.close()
    result={'model':'qwen2.5:1.5b','source':'ordinary SQLite read-only backups; real Ollama; HTTP calls counted without replacing responses','results':report}
    (ROOT/'tmp/ai-intelligence-audit/b1-comparison.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    return all(item['passed'] for item in report)


if __name__=='__main__':raise SystemExit(0 if asyncio.run(main()) else 1)
