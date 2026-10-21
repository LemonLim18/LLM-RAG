"""Permanent Phase D model evaluations. No model installs or ordinary writes.

Routing mode measures decisions only. Agent mode uses the authenticated existing
gateway router against one disposable acceptance database and central scenario.
Human interpretation scores stay NOT RUN until reviewed, not inferred from HTTP.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
import time
from uuid import uuid4
import httpx
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from scripts.phase_d_audit import Run,source_manifest,digest


def manifest():
    return {'source_digest':digest(json.dumps(source_manifest(),sort_keys=True).encode()),
        'model':'qwen2.5:1.5b','ports':[5173,8000],
        'knowledge_pointer':json.loads((ROOT/'backend/knowledge_workspace/storage/catalog_releases/active.json').read_text())}


async def routing(args):
    from llm.gateway_routing import select_context
    from llm.orchestration.model import RoutingModel
    from local_providers.development import ScenarioManager
    from llm.gateway_models import EditorSnapshot
    manager=ScenarioManager(ROOT/'tmp/phase-d/acceptance-scenario.json')
    manager.change('select',manager.snapshot()[1]['source_revision'],scenario_id='MIXED-PATH-001')
    inventory=manager.inventory()
    cases=json.loads((ROOT/'docs/evaluations/phase_d_cases.json').read_text())[args.suite]
    run=Run('D3-routing-'+args.engine+('-fresh' if args.suite=='fresh_holdouts' else ''),'real_model_direct',manifest());rows=[]
    os.environ['COGNISHIELD_AI_PLANNING']='1' if args.engine=='candidate' else '0'
    for case in cases[args.offset:args.offset+args.limit]:
        prompt=case['prompt'];m=RoutingModel();captured=[]
        async def generate(*a,**kw):
            value=await m.generate(*a,**kw);captured.append(value[0]);return value
        editor=EditorSnapshot(document_id='eval-buffer',path='playbooks/drafts/eval.cfg',content='router bgp 65020\n neighbor 192.0.2.2 remote-as 65030\n! KEEP\n',language='ios',model_id='eval-buffer',model_version=1,buffer_epoch=1,saved_revision=0,is_dirty=True,read_only=False) if case['assistant']=='studio' else None
        attachments=[{'id':'00000000-0000-4000-8000-000000000001','name':'engineering.pdf'}] if case['capability'] in {'DOCUMENT','SCREENSHOT','DIAGRAM','SECURITY'} else []
        started=time.monotonic()
        try:
            route=await select_context(prompt,'qwen2.5:1.5b',case['assistant'],editor,attachments,[],inventory=inventory,generate_fn=generate)
            selected={'inventory.read' if d=='inventory' else 'knowledge.search' if d=='knowledge' else 'network.'+d for d in route.network_domains}
            if route.use_attachments:selected.add('document.read')
            if route.use_editor and route.intent!='edit':selected.add('editor.read')
            if route.intent.startswith('generate_'):selected.add('v9.preview')
            if route.intent=='edit':selected.add('document.propose')
            expected={ {'attachment.read':'document.read','studio.context':'editor.read'}.get(tool,tool) for tool in case['expected_authorized_tools']}
            # This is a predeclared source-selection oracle, not answer quality.
            passed=selected==expected
            if case['negative_or_ambiguous'] and not expected and route.intent=='clarify':passed=True
            actual={'route':route.model_dump(),'tools':sorted(selected),'raw_model_outputs':captured}
        except Exception as exc:passed=False;actual={'error':str(exc),'raw_model_outputs':captured}
        row=run.record(case['id'],'PASS' if passed else 'FAIL',expected={'tools':case['expected_authorized_tools'],'scope':'Route selection only; not answer quality'},actual=actual,
            prompt=prompt,model='qwen2.5:1.5b',model_calls=m.calls,latency_ms=round((time.monotonic()-started)*1000,2),classification=None if passed else 'routing_or_rubric_discrepancy')
        rows.append(row);print(json.dumps({'case':case['id'],'outcome':row['outcome'],'calls':m.calls}),flush=True)
    print(json.dumps({'run':str(run.path),'distinct_cases':len(rows),'routing_pass':sum(r['outcome']=='PASS' for r in rows)}),flush=True)


async def agent(args):
    from fastapi import FastAPI
    from auth.auth import create_access_token
    from db.manager import DatabaseManager
    from llm.gateway_api import router
    from llm.gateway_store import ensure_schema
    from local_providers.development import ScenarioManager
    from llm.gateway_network import network_context
    from llm.gateway import AIGateway
    from llm.tools import ToolAuthorization
    from llm.gateway_network import READ_TOOLS
    from llm.orchestration.investigation import assess,conclusion_text
    from llm.orchestration.model import RoutingModel
    from llm.orchestration.synthesis import synthesize
    target=ROOT/'tmp/stabilization-20261017/acceptance.db'
    target.parent.mkdir(parents=True,exist_ok=True)
    db=DatabaseManager(str(target));db.initialize();ensure_schema(db)
    assert Path(db._db_path).resolve()==target.resolve()
    manager=ScenarioManager(ROOT/'tmp/phase-d/acceptance-scenario.json');db._development_scenario=manager
    scenario,meta=manager.snapshot()
    if scenario['id']!=args.scenario:
        scenario,meta=manager.change('select',meta['source_revision'],scenario_id=args.scenario)
    os.environ.update(COGNISHIELD_DEV_SIMULATION='1',COGNISHIELD_AI_ENGINE='langgraph_b3',
        COGNISHIELD_AI_PLANNING='1' if args.engine=='candidate' else '0',COGNISHIELD_AI_SYNTHESIS='1' if args.engine=='candidate' else '0')
    app=FastAPI();app.state.local_db=db;app.include_router(router)
    run=Run('D4-agent-'+args.engine,'real_model_full_agent',manifest()|{'scenario':meta})
    prompts=[('D-REASON-PATH','Investigate the available path from Branch-Aster to Edge-Cedar, and explain whether traffic can return.'),
        ('D-REASON-COMPOUND','Check Core-Birch interfaces, current configuration and BGP state. Explain what is established and what remains unknown.'),
        ('D-REASON-OSPF','Do Branch-Aster and Core-Birch have a recorded OSPF adjacency? Explain the matching requirements.'),
        ('D-REASON-MISSING','Investigate available recent syslogs for Core-Birch. Does missing syslog mean it has failed?'),
        ('D-REASON-TRAFFIC','Assess Core-Birch traffic and drops. Is congestion established, and what should I check next?'),
        ('D-REASON-TOPIC','Hello, what is 17 plus 26?'),
        ('D-REASON-ADAPTIVE','Investigate current configuration and syslogs on Core-Birch, then identify what other evidence would resolve any uncertainty.')]
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://acceptance',
            headers={'Authorization':'Bearer '+create_access_token(1,'phase-d-eval','admin')},timeout=150) as client:
            for case,prompt in prompts[args.offset:args.offset+args.limit]:
                before=manager.snapshot()[1]['source_revision']
                response=await client.post('/api/v1/ai/conversations',json={'assistant_kind':'floating'});response.raise_for_status();cid=response.json()['id']
                started=time.monotonic();response=await client.post(f'/api/v1/ai/conversations/{cid}/turns',json={'request_id':str(uuid4()),'prompt':prompt,'model':'qwen2.5:1.5b'})
                value=response.json();report=value.get('context_coverage',{}).get('agent',{})
                executed=response.status_code==200 and value.get('status')=='success'
                stable=before==manager.snapshot()[1]['source_revision']
                if not stable:executed=False
                run.record(case,'NOT RUN' if executed else 'FAIL',expected='Grounded useful engineering answer; independent human rubric review required',actual=value,
                    prompt=prompt,http_status=response.status_code,latency_ms=round((time.monotonic()-started)*1000,2),
                    model='qwen2.5:1.5b',tools=[i['tool'] for i in value.get('observations',[])],calls=report.get('model_call_breakdown',{}),
                    classification='scenario_changed_during_evaluation' if not stable else 'human_quality_review_pending' if executed else 'runtime_failure')
                print(json.dumps({'case':case,'status':value.get('status'),'tools':[i['tool'] for i in value.get('observations',[])], 'synthesis':report.get('verification',{}).get('synthesis',{}).get('status')}),flush=True)
                if args.comparative:
                    # M0 cannot establish local facts. M1 sees fixed verified records;
                    # M3 uses the same actual reader results with no model synthesis.
                    contexts=value.get('observations',[]);from llm.gateway_models import Evidence
                    evidence=[Evidence.model_validate(e) for e in value.get('evidence',[])]
                    assessment=assess(contexts,evidence)
                    run.record(case+'-M3','NOT RUN',expected='Independent deterministic comparison grading',actual={'answer':conclusion_text(assessment,contexts,evidence),'assessment':assessment},model_calls=0)
                    m=RoutingModel();answer,verification=await synthesize(m,'qwen2.5:1.5b',prompt,contexts,evidence,assessment,'[Candidate rejected; no model answer released]')
                    run.record(case+'-M1','NOT RUN',expected='Independent evidence-assisted interpretation grading',actual={'answer':answer,'verification':verification},model_calls=m.calls)
                    m=RoutingModel()
                    try:answer,_=await m.generate([{'role':'system','content':'Answer the question concisely. You have no local network observations. Do not invent local facts.'},{'role':'user','content':prompt}],model='qwen2.5:1.5b',purpose='model_only')
                    except Exception as exc:answer=str(exc)
                    run.record(case+'-M0','NOT RUN',expected='Ask for absent observations; do not invent local facts',actual=answer,model_calls=m.calls)
    finally:db.close()
    print(json.dumps({'run':str(run.path)}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['routing','agent']);parser.add_argument('--engine',choices=['legacy','candidate'],default='candidate')
    parser.add_argument('--suite',choices=['cases','fresh_holdouts'],default='cases')
    parser.add_argument('--offset',type=int,default=0);parser.add_argument('--limit',type=int,default=52);parser.add_argument('--scenario',default='PROTOCOL-MIXED-001');parser.add_argument('--comparative',action='store_true')
    args=parser.parse_args();asyncio.run(routing(args) if args.mode=='routing' else agent(args))
