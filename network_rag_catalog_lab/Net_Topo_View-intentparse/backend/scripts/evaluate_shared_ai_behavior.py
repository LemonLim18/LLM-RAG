"""Opt-in real shared-gateway checks against a disposable copy of local SQLite.

No model/router/tool mocks, listeners, source database writes, generation jobs or
device operations. Existing attachment extraction is reused, not repeated.
"""
import argparse
import asyncio
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))


async def evaluate(output, model, documents):
    from lab_config import DB_PATH
    from db.manager import DatabaseManager
    from llm.gateway import AIGateway
    from llm.gateway_models import TurnRequest
    from local_providers.chat import runtime
    results=[]
    def record(name,ok,**details):
        item={'case':name,'passed':bool(ok),**details};results.append(item)
        print(json.dumps(item,ensure_ascii=False),flush=True)
    with tempfile.TemporaryDirectory(prefix='shared-ai-behavior-',ignore_cleanup_errors=True) as folder:
        target=Path(folder)/'behavior.db'
        source=sqlite3.connect(Path(DB_PATH).as_uri()+'?mode=ro',uri=True)
        copy=sqlite3.connect(target)
        try:source.backup(copy)
        finally:source.close();copy.close()
        db=DatabaseManager(str(target));g=AIGateway(db);user={'username':'admin','role':'admin'}
        assert Path(db._db_path).resolve()==target.resolve()
        with db._connect() as c:
            devices=[dict(r) for r in c.execute('SELECT id,hostname,management_ip FROM devices ORDER BY id')]
            ports=[dict(r) for r in c.execute('SELECT id,device_id,name,ip_address FROM interfaces ORDER BY id')]
        r2=next(d for d in devices if d['hostname']=='R2')
        r1=next(d for d in devices if d['hostname']=='R1')
        expected=[p for p in ports if p['device_id']==r2['id']]
        state=await runtime()
        record('chat models',all('ocr' not in m.lower() and 'embed' not in m.lower() for m in state['providers'][0]['models']),runtime=state)
        async def turn(cid,prompt,editor=None):
            response=await g.turn(cid,user,TurnRequest(request_id=uuid4(),prompt=prompt,model=model,editor=editor))
            return response,{'prompt':prompt,'answer':response.answer,'status':response.status,'kind':response.kind,
                'coverage':response.context_coverage,'tools':[r['tool'] for r in response.observations]}
        for kind in ['floating','studio']:
            cid=g.store.create('admin',kind)['id']
            r,info=await turn(cid,"What are R2's interfaces?")
            record(kind+' interfaces',r.status=='success' and info['tools']==['inventory.read'] and all(p['name'] in r.answer and p['ip_address'] in r.answer for p in expected),**info)
            r,info=await turn(cid,'Are you sure?')
            record(kind+' confirmation',all(p['name'] in r.answer and p['ip_address'] in r.answer for p in expected) and info['tools']==['inventory.read'],**info)
            r,info=await turn(cid,'What about the first one?')
            record(kind+' ordinal',expected[0]['name'] in r.answer and expected[1]['name'] not in r.answer,**info)
            r,info=await turn(cid,'What is its IP?')
            record(kind+' interface address',expected[0]['ip_address'] in r.answer and expected[1]['ip_address'] not in r.answer,**info)
            r,info=await turn(cid,'Show stored configurations for R1.')
            record(kind+' configurations',info['tools']==['network.configuration'] and 'hostname R1' in r.answer and 'simulated' in r.answer,**info)
            r,info=await turn(cid,'What about R2?')
            record(kind+' new device same subject',info['tools']==['network.configuration'] and 'hostname R2' in r.answer and 'hostname R1' not in r.answer,**info)
            r,info=await turn(cid,'Show R1 syslogs.')
            rows=[row for item in r.observations for src in (item.get('data') or {}).get('sources',[]) for row in (src.get('data') or {}).get('records',[])]
            record(kind+' syslogs',info['tools']==['network.syslog'] and bool(rows) and all(row['message'] in r.answer for row in rows[:20]),**info)
            r,info=await turn(cid,'What is connected to R2 in the planned topology?')
            record(kind+' planned topology','network.topology' in info['tools'] and 'R1' in r.answer and expected[1]['name'] in r.answer and 'not a complete interface inventory' in r.answer,**info)
            r,info=await turn(cid,'Show live packet loss measurements for R2 right now.')
            record(kind+' unavailable live data','network.telemetry' in info['tools'] and 'unavailable' in r.answer.lower() and 'No network root cause can be established' in r.answer,**info)
            r,info=await turn(cid,'Hello, what is 1 + 1?')
            record(kind+' topic switch',r.status=='success' and '2' in r.answer and not r.evidence and not info['coverage']['routing']['history'],**info)
            r,info=await turn(cid,'What is its IP?')
            record(kind+' ambiguous after topic switch',r.kind=='clarification' and not r.evidence,**info)
            if documents:
                with db._connect() as c:
                    row=c.execute("SELECT * FROM ai_attachments WHERE name='generation process.pdf' LIMIT 1").fetchone()
                    if row:
                        c.execute('INSERT INTO ai_attachments(id,conversation_id,owner,name,digest,byte_size,segments,original_bytes) VALUES(?,?,?,?,?,?,?,?)',
                            (str(uuid4()),cid,'admin',row['name'],row['digest'],row['byte_size'],row['segments'],row['original_bytes']))
                if not row:record(kind+' PDF fixture',False,error='Existing PDF fixture unavailable');continue
                r,info=await turn(cid,'Summarize the controls on page 4 of the PDF in three sentences. Do not quote unreadable labels.')
                record(kind+' PDF contents',r.status=='success' and bool(r.evidence) and {e.page for e in r.evidence}=={4} and
                    any(word in r.answer.lower() for word in ['interpretation','parameters','templates','categories']) and
                    'page 4' in r.answer.lower() and 'OCR was used' in r.answer and 'evidence id' not in r.answer.lower() and row['id'] not in r.answer,**info)
                r,info=await turn(cid,'What about page 5?')
                record(kind+' PDF follow-up',r.status=='success' and bool(r.evidence) and {e.page for e in r.evidence}=={5} and 'evidence id' not in r.answer.lower(),**info)
        studio=g.store.create('admin','studio')['id']
        editor=dict(document_id='unsaved-eval',path='playbooks/drafts/resume-behavior.cfg',content='router ospf 2\n router-id 192.0.2.9\n! UNSAVED_KEEP_MARKER\nrouter bgp 65000\n neighbor 192.0.2.10 remote-as 65001\n',language='network-config',model_id='eval',model_version=7,buffer_epoch=2,saved_revision=0,is_dirty=True,read_only=False)
        if documents:
            r,info=await turn(studio,'Explain the active configuration and quote its unsaved comment. Do not modify it.',editor)
            record('Studio active buffer explanation',r.kind=='answer' and r.proposal is None and 'UNSAVED_KEEP_MARKER' in r.answer and info['coverage'].get('routing',{}).get('editor'),**info)
            r,info=await turn(studio,'In the open file, change only the OSPF router ID from 192.0.2.9 to 192.0.2.44.',editor)
            proposal=r.proposal or {}
            record('Studio guarded edit',r.kind=='edit_proposal' and proposal.get('original')==editor['content'] and
                proposal.get('suggested')==editor['content'].replace('192.0.2.9','192.0.2.44') and 'Save' in r.answer,**info)
        with db._connect() as c:
            record('evaluation did not create jobs',c.execute('SELECT count(*) FROM jobs').fetchone()[0]==sqlite_job_count(DB_PATH))
        db.close()
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps({'source':'read-only SQLite backup; actual shared gateway and installed models','results':results},indent=2,ensure_ascii=False),encoding='utf-8')
    return all(item['passed'] for item in results)


def sqlite_job_count(path):
    c=sqlite3.connect(Path(path).as_uri()+'?mode=ro',uri=True)
    try:return c.execute('SELECT count(*) FROM jobs').fetchone()[0]
    finally:c.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'tmp/ai-intelligence-audit/resume-behavior-final.json')
    parser.add_argument('--model',default='qwen2.5:1.5b')
    parser.add_argument('--documents',action='store_true',help='Include slower real PDF/editor model answers')
    args=parser.parse_args()
    raise SystemExit(0 if asyncio.run(evaluate(args.output,args.model,args.documents)) else 1)
