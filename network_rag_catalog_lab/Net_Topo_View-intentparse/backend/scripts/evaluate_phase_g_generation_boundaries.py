"""Actual compound Studio/V9 journey and negative gates in the owned G7 DB.

Run only after the native batch stops: scenario activation is intentionally
serialized. Existing immutable engineer fixtures supply regression expectations;
this is neither new publication nor independent device/Ansible certification.
"""
import argparse
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import time
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))


async def main(args):
    import httpx
    from fastapi import FastAPI
    from auth.auth import create_access_token
    from db.manager import DatabaseManager
    from llm.gateway_api import router
    from llm.gateway_knowledge import read_release
    from local_providers.development import ScenarioManager
    from local_providers.development_api import router as development
    from local_providers.knowledge import knowledge_root
    from local_providers.knowledge_review import identity
    from scripts.evaluate_phase_g_native import scenario_for,verify_unsaved
    from scripts.phase_d_audit import Run,source_manifest

    os.environ.update(COGNISHIELD_DEV_WORKBENCH='1',COGNISHIELD_DEV_SIMULATION='0',
        COGNISHIELD_AI_ENGINE='langgraph_b3',COGNISHIELD_AI_PLANNING='1',COGNISHIELD_AI_SYNTHESIS='1')
    previous=(ROOT/args.resume).resolve()
    assert previous.is_relative_to((ROOT/'tmp/phase-g/iterations').resolve())
    workspace=Path(json.loads((previous/'workspace-ref.json').read_text())['path'])
    release,manifest,pointer=read_release(knowledge_root()/'storage/catalog_releases')
    methods=json.loads((release/manifest['cognishield_engineer_reviews']['artifact_path']).read_text())['bindings']
    chosen=[('cisco','set_ospf_router_id'),('juniper','configure_static_route'),('huawei','configure_bgp_neighbor')]
    entries=[];bundle=None
    for vendor,operation in chosen:
        binding=next(b for b in manifest['template_bindings'] if b['vendor']==vendor and b['operation_id']==operation)
        fixture=deepcopy(next(m for m in methods if m['identity']==identity(binding))['method']['fixtures'][0])
        if vendor=='huawei' and operation=='configure_bgp_neighbor':
            # This independent request configures a neighbor, not a peer group.
            # The native method's fixture carries a cross-vendor optional field
            # which this Huawei template does not emit; do not claim that clause.
            fixture['parameters'].pop('peer_group',None)
        small,device=scenario_for(binding,fixture['parameters'])
        if bundle is None:bundle=small
        inventory=bundle['sources']['inventory']['data']
        inventory['devices']=[deepcopy(device) if d['id']==device['id'] else d for d in inventory['devices']]
        existing={i['id'] for i in inventory['interfaces']}
        inventory['interfaces'].extend(deepcopy(i) for i in small['sources']['inventory']['data']['interfaces'] if i['id'] not in existing)
        entries.append({'binding':binding,'fixture':fixture,'device':device})
    bundle['manifest'].update(scenario_id='G7-COMPOUND-CONTROLLED',name='Three-vendor reviewed native workflow')
    prompt=('Prepare native configuration drafts for review: on LAB-R1 set OSPF process 200 router ID to 192.0.2.200; '
        'on LAB-R2 configure the static route 10.50.0.0/16 via 192.0.2.2 with preference 100; '
        'on LAB-R3 configure BGP local AS 65020 and neighbor 192.0.2.2 remote AS 65030, '
        'description "Reviewed uplink". Do not save or execute anything.')
    # Actual requests must agree with the frozen, published fixture values.
    assert entries[0]['fixture']['parameters']['router_id']=='192.0.2.200'
    assert entries[1]['fixture']['parameters']['destination']=='10.50.0.0/16'
    assert entries[2]['fixture']['parameters']['local_as']==65020
    run=Run('G7-compound-and-boundaries','real_model_full_agent',{'knowledge_release':pointer['release_id'],
        'model':'qwen2.5:1.5b','source_manifest':source_manifest(),'prompt':prompt,'holdout':False,
        'expectations':entries,'not_unique_141_journey_credit':True},phase='phase-g')
    db=DatabaseManager(str(workspace/'app.db'));db.initialize()
    db._development_scenario=ScenarioManager(workspace/'state.json',enabled_default=False)
    app=FastAPI();app.state.local_db=db;app.include_router(development);app.include_router(router)
    all_ok=True;trace={};started=time.monotonic()
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://controlled-g7',
            headers={'Authorization':'Bearer '+create_access_token(929,'G7-ENGINEER','admin')},timeout=240) as client:
            async def call(method,path,body=None,allowed=(200,)):
                response=await client.request(method,path,json=body)
                result=response.json()
                trace.setdefault('requests',[]).append({'method':method,'path':path,'body':body,'status':response.status_code,'response':result})
                assert response.status_code in allowed,(response.status_code,str(result)[:2000])
                return result
            prefix='/api/v1/development-network/workbench'
            state=await call('GET',prefix)
            controlled=json.loads((previous/'controlled-draft-ref.json').read_text())
            current=await call('GET',prefix+'/drafts/'+controlled['draft_id'])
            async def activate(value):
                nonlocal current,state
                current=await call('POST',prefix+'/drafts',{'bundle':value,'draft_id':current['draft_id'],'expected_revision':current['draft_revision']})
                receipt=await call('POST',prefix+'/drafts/'+current['draft_id']+'/validate',{'expected_revision':current['draft_revision']})
                state=await call('POST',prefix+'/drafts/'+current['draft_id']+'/activate',{'expected_revision':current['draft_revision'],
                    'expected_active':state['context']['source_revision'],'validation_hash':receipt['validation_hash']})
            await activate(bundle)
            cid=(await call('POST','/api/v1/ai/conversations',{'assistant_kind':'studio'}))['id']
            initial=await call('POST','/api/v1/ai/conversations/'+cid+'/turns',{'request_id':str(uuid4()),'prompt':prompt,'model':'qwen2.5:1.5b'})
            assert initial['status']=='success' and initial['kind']=='generation_preview'
            preview=initial['preview'];sid=preview['parsed_intent']['_v9_session']
            selections=[{'operation_id':e['binding']['operation_id'],'target_host':e['device']['hostname'],
                'parameters':e['fixture']['parameters'],'template_id':e['binding']['artifact_path']} for e in entries]
            async def review(selection,allowed=(200,)):
                nonlocal preview
                result=await call('POST','/api/v1/ai/studio/preview',{'conversation_id':cid,'prompt':prompt,'model':'qwen2.5:1.5b',
                    'output_kind':'native','params':{'_v9_session':sid},'expected_revision':preview['session_revision'],
                    'confirm_order':True,'selection':selection},allowed=allowed)
                if 'session_revision' in result:preview=result
                return result
            def render_body(kind='native'):
                return {'conversation_id':cid,'session_id':sid,'expected_revision':preview['session_revision'],'output_kind':kind,'model':'qwen2.5:1.5b'}
            await review(selections)
            assert preview['plan_status']=='ready' and len(preview['tasks'])==3
            output=await call('POST','/api/v1/ai/studio/render',render_body())
            assert len(output['documents'])==3
            for entry in entries:
                doc=next(d for d in output['documents'] if str(d['device_id'])==str(entry['device']['id']))
                verify_unsaved({'output_kind':'native','documents':[doc]},entry['binding'],entry['fixture'],
                    entry['device']['hostname'],entry['device']['id'],pointer['release_id'])
            run.record('G7-COMPOUND-THREE-VENDOR','PASS',expected='Three reviewed native outputs with exact target/parameters and no save/action',
                actual=output,prompt=prompt,latency_ms=round((time.monotonic()-started)*1000,2))
            # Negative schema values cannot render, even after explicit review.
            bad=deepcopy(selections);bad[2]['parameters']['remote_as']=0
            await review(bad)
            assert preview['plan_status']!='ready'
            invalid=await call('POST','/api/v1/ai/studio/render',render_body(),allowed=(409,422))
            run.record('G7-NEGATIVE-AS-SCHEMA','PASS',expected='Invalid AS blocked; no rendered documents',actual=invalid)
            # Missing fields remain clarification; there is no model-filled substitute.
            bad=deepcopy(selections);bad[1]['parameters'].pop('next_hop')
            await review(bad);assert preview['plan_status']!='ready'
            missing=await call('POST','/api/v1/ai/studio/render',render_body(),allowed=(409,422))
            run.record('G7-NEGATIVE-MISSING-PARAMETER','PASS',expected='Missing next hop cannot reach render',actual=missing)
            # A template for a different platform must not be accepted.
            bad=deepcopy(selections);bad[1]['template_id']=entries[0]['binding']['artifact_path']
            revision=preview['session_revision']
            incompatible=await review(bad,allowed=(422,))
            assert 'does not match' in str(incompatible) and preview['session_revision']==revision
            run.record('G7-NEGATIVE-WRONG-VENDOR-TEMPLATE','PASS',expected='Incompatible selection rejected without updating the owned plan',actual=incompatible)
            await review(selections);assert preview['plan_status']=='ready'
            changed=deepcopy(bundle);changed['manifest']['description']='Explicit new source revision for stale-review rejection'
            await activate(changed)
            stale=await call('POST','/api/v1/ai/studio/render',render_body(),allowed=(409,))
            run.record('G7-NEGATIVE-SOURCE-REVISION','PASS',expected='Source revision invalidates old confirmation',actual=stale)
            await review(selections);assert preview['plan_status']=='ready'
            unavailable=await call('POST','/api/v1/ai/studio/render',render_body('playbook'),allowed=(422,))
            assert 'variant' in str(unavailable).lower()
            run.record('G7-ANSIBLE-UNAVAILABLE-VARIANT','PASS',expected='No active validated variants; no raw CLI mislabeled Ansible',actual=unavailable)
    except Exception as exc:
        all_ok=False;trace['error']=type(exc).__name__+': '+str(exc)
        run.record('G7-COMPOUND-BOUNDARY-INCOMPLETE','FAIL',expected='All compound and negative gates verified',actual={'error':trace['error']},classification='actual_gateway_or_evaluator_failure')
    finally:
        db.close()
        (run.path/'actual.json').write_text(json.dumps(trace,indent=2,default=str),encoding='utf-8')
        (run.path/'result.json').write_text(json.dumps({'outcome':'PASS' if all_ok else 'FAIL','unique_141_credit':0,
            'ordinary_database_used':False,'publication':False,'saved':False,'device_action':False},indent=2),encoding='utf-8')
    print(json.dumps({'run':str(run.path),'outcome':'PASS' if all_ok else 'FAIL','error':trace.get('error')}),flush=True)
    return all_ok


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--resume',required=True)
    raise SystemExit(0 if asyncio.run(main(parser.parse_args())) else 1)
