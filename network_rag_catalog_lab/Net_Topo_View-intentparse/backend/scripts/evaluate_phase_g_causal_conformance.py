"""Actual-model causal outputs for private, independent forwarding fixtures.

Only observable mutations enter the scenario. Expected outcomes stay here in the
evaluator; final prose remains NOT RUN pending independent complete-answer review.
Serialize after the native evaluator when reusing its owned SQLite workspace.
"""
import argparse
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from uuid import uuid4
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))


def observable_bundle(specification):
    from development.starter import starter_bundle
    bundle=starter_bundle()
    bundle['manifest'].update(scenario_id='S-CONTROLLED-CAUSAL',name='Controlled network observations')
    for mutation in specification['mutations']:
        parts=mutation['path'].strip('/').split('/');node=bundle
        for part in parts[:-1]:node=node[int(part)] if isinstance(node,list) else node[part]
        if isinstance(node,list):
            if parts[-1]=='-':node.append(deepcopy(mutation['value']))
            else:node[int(parts[-1])]=deepcopy(mutation['value'])
        else:node[parts[-1]]=deepcopy(mutation['value'])
    return bundle


def check_expected_record(records,specification):
    """Evaluator-only oracle comparison; never placed in a model/tool prompt."""
    matching=[r for r in records if r['kind']==specification['record_kind']
        and all(r.get(k)==v for k,v in specification['selector'].items())]
    assert len(matching)==1
    for path,value in specification['expected'].items():
        parts=path.split('/');node=matching[0]
        if parts[-1]=='$absent':
            for key in parts[:-2]:node=node[key]
            assert (parts[-2] not in node)==value,path
        else:
            for key in parts:node=len(node) if key=='$length' else node[key]
            assert node==value,(path,node,value)


async def main(args):
    import httpx
    from fastapi import FastAPI
    from auth.auth import create_access_token
    from db.manager import DatabaseManager
    from llm.gateway_api import router
    from llm.gateway_store import ensure_schema
    from local_providers.development import ScenarioManager
    from local_providers.development_api import router as development
    from llm.orchestration.model import RoutingModel
    from scripts.phase_d_audit import Run,source_manifest
    extended=getattr(args,'extended',False)
    oracle=ROOT/'backend/development/test_oracles'/('phase_g_extended_conformance_v1.json' if extended else 'phase_g_forwarding_conformance_v3.json')
    specifications=json.loads(oracle.read_text(encoding='utf-8'))['cases']
    indexes=range(len(specifications)) if extended else [0,1,3,4,7,9,10,11,14,15]
    selected=[specifications[i] for i in indexes if not args.only or specifications[i]['id'] in args.only][:args.limit]
    if not selected:raise ValueError('No selected independent fixture matches --only')
    prompt=('Assess the declared forward and return flow between LAB-R1 and LAB-R3. '
        'Explain the significant path findings, their supported cause and any uncertainty. '
        'Use only the simulation source; do not run any device test.')
    os.environ.update(COGNISHIELD_DEV_WORKBENCH='1',COGNISHIELD_DEV_SIMULATION='0',
        COGNISHIELD_AI_ENGINE='langgraph_b3',COGNISHIELD_AI_PLANNING='1',COGNISHIELD_AI_SYNTHESIS='1')
    previous=(ROOT/args.resume).resolve()
    assert previous.is_relative_to((ROOT/'tmp/phase-g/iterations').resolve())
    workspace=Path(json.loads((previous/'workspace-ref.json').read_text(encoding='utf-8'))['path'])
    run=Run('G6-causal-model-conformance','real_model_full_agent',{'model':'qwen2.5:1.5b',
        'source_manifest':source_manifest(),'oracle_sha256':hashlib.sha256(oracle.read_bytes()).hexdigest(),
        'independent_fixture_ids':[s['id'] for s in selected],'holdout':False,'answer_quality':'PENDING_INDEPENDENT_PROSE_REVIEW',
        'prompt':prompt,'not_generation_or_device_execution':True},phase='phase-g')
    db=DatabaseManager(str(workspace/'app.db'));db.initialize();ensure_schema(db)
    state_file=workspace/('causal-'+run.path.name.split('-')[-1]+'.json')
    db._development_scenario=ScenarioManager(state_file,enabled_default=False)
    app=FastAPI();app.state.local_db=db;app.include_router(development);app.include_router(router)
    source_outcomes=[]
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://causal-conformance',
            headers={'Authorization':'Bearer '+create_access_token(939,'G6-CAUSAL-OWNER','admin')},timeout=240) as client:
            async def call(method,path,body=None):
                response=await client.request(method,path,json=body);response.raise_for_status();return response.json()
            prefix='/api/v1/development-network/workbench';state=await call('GET',prefix);draft=None
            for specification in selected:
                if extended:
                    prompt=('Explain the recorded protocol observations for LAB-R1, LAB-R2 and LAB-R3. '
                        'Compare actual peer roles, prerequisite differences and contradictory or missing observations. '
                        'Use only the simulation source; do not run a device test.'
                        if specification['record_kind']=='protocol_assessment' else
                        'Assess the declared forward and return flow between LAB-R1 and LAB-R3. Explain the significant path findings and their scope. '
                        'Use only the simulation source; do not run a device test.'
                        if specification['tool']=='network.state' else
                        'Explain the modeled interface measurement series for LAB-R1, LAB-R2 and LAB-R3, including units, sampling window and whether rates or congestion are established. '
                        'Use only the available telemetry reader; do not collect new data.')
                bundle=observable_bundle(specification)
                control={'draft_id':draft['draft_id'],'expected_revision':draft['draft_revision']} if draft else {}
                draft=await call('POST',prefix+'/drafts',{'bundle':bundle,**control})
                receipt=await call('POST',prefix+'/drafts/'+draft['draft_id']+'/validate',{'expected_revision':draft['draft_revision']})
                state=await call('POST',prefix+'/drafts/'+draft['draft_id']+'/activate',{'expected_revision':draft['draft_revision'],
                    'expected_active':state['context']['source_revision'],'validation_hash':receipt['validation_hash']})
                for surface in ['floating','studio']:
                    started=time.monotonic();result=None;error=None
                    model_trace=[]
                    original_generate=RoutingModel.generate
                    async def observed_generate(instance,*values,**kwargs):
                        inference_started=time.monotonic()
                        entry={'purpose':kwargs.get('purpose','routing'),'messages':deepcopy(values[0]) if values else []}
                        try:
                            output,used=await original_generate(instance,*values,**kwargs)
                            entry.update(raw_output=output,model=used)
                            return output,used
                        except Exception as exc:
                            entry['error']=type(exc).__name__+': '+str(exc)
                            raise
                        finally:
                            entry['latency_ms']=round((time.monotonic()-inference_started)*1000,2);model_trace.append(entry)
                    try:
                        cid=(await call('POST','/api/v1/ai/conversations',{'assistant_kind':surface}))['id']
                        if getattr(args,'trace_model',False):
                            with patch.object(RoutingModel,'generate',observed_generate):
                                result=await call('POST','/api/v1/ai/conversations/'+cid+'/turns',{'request_id':str(uuid4()),'prompt':prompt,'model':'qwen2.5:1.5b'})
                        else:
                            result=await call('POST','/api/v1/ai/conversations/'+cid+'/turns',{'request_id':str(uuid4()),'prompt':prompt,'model':'qwen2.5:1.5b'})
                        assert [r['tool'] for r in result['observations']]==[specification['tool'] if extended else 'network.state']
                        if extended:
                            rows=[row for item in result['observations'] for row in item['data'].get('records',[])]
                            check_expected_record(rows,specification)
                            assert specification['id'] not in json.dumps(result)
                            assert all(e['origin']=='simulated' for e in result['evidence'])
                        else:
                            rows=[row for item in result['observations'] for row in item['data'].get('records',[]) if row.get('kind')=='forwarding_assessment']
                            assert len(rows)==1
                            assessment=rows[0]['assessment'];expected=specification['expected']
                            assert assessment['forward']['status']==expected['forward'] and assessment['return']['status']==expected['return']
                            if expected.get('forward_reason_contains'):
                                assert any(expected['forward_reason_contains'] in b['reason'] for b in assessment['forward']['branches'])
                            assert specification['id'] not in json.dumps(result)
                            assert all(e['origin']=='simulated' for e in result['evidence'])
                    except Exception as exc:error=type(exc).__name__+': '+str(exc)
                    actual={'result':result,'error':error,'source_conformance':'PASS' if error is None else 'FAIL',
                        **({'model_trace':model_trace} if getattr(args,'trace_model',False) else {}),
                        'source_revision':state['context']['source_revision'],'final_answer_adequacy':'PENDING_INDEPENDENT_PROSE_REVIEW'}
                    source_outcomes.append(error is None)
                    name=specification['id']+'-'+surface
                    (run.path/(name+'.json')).write_text(json.dumps(actual,indent=2),encoding='utf-8')
                    run.record(name,'NOT RUN' if error is None else 'FAIL',expected=specification['expected'],actual=actual,prompt=prompt,
                        classification='causal_answer_review_pending' if error is None else 'source_or_runtime_failure',latency_ms=round((time.monotonic()-started)*1000,2))
                    print(json.dumps({'case':name,'source_conformance':actual['source_conformance'],'answer_review':'PENDING','error':error,'run':str(run.path)}),flush=True)
    finally:db.close()
    return bool(source_outcomes) and all(source_outcomes)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--resume',required=True);parser.add_argument('--limit',type=int,default=10)
    parser.add_argument('--extended',action='store_true',help='Use the existing independent ECMP/protocol/metric oracle, with neutral evidence-only prompts')
    parser.add_argument('--trace-model',action='store_true',help='Archive actual model inputs and raw outputs for controlled evaluation data only')
    parser.add_argument('--only',action='append',help='Rerun selected existing fixture IDs; preserve the original run')
    args=parser.parse_args()
    if not 1<=args.limit<=10:parser.error('Use1–10 independent fixture cases')
    raise SystemExit(0 if asyncio.run(main(args)) else 1)
