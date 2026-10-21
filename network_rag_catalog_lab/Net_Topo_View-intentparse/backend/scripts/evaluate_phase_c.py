"""Repeatable actual HTTP/local-model Phase C acceptance; no device actions.

Requires the explicit development server and its disposable acceptance SQLite.
Writes a new ignored run directory each time, preserving failed executions.
"""
import argparse
import asyncio
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from uuid import uuid4
import httpx
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))


async def main(phase):
    import lab_config
    from auth.auth import create_access_token
    output=ROOT/'tmp/phase-c'/('http-'+phase+'-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid4().hex[:6]);output.mkdir(parents=True)
    records=[]
    # Bind dirty source as well as HEAD; never include DBs, .env or tokens.
    source_files=[]
    for folder,pattern in [('backend/llm','*.py'),('backend/local_providers','*.py'),('backend/development','*.json')]:
        source_files.extend((ROOT/folder).rglob(pattern))
    source_files.extend(ROOT/name for name in ['backend/db/manager.py','backend/local_app.py','backend/scripts/evaluate_phase_c.py','frontend/components/DevelopmentNetwork.tsx','frontend/components/ansible/NativeGenerationReview.tsx','frontend/components/SharedInventoryChat.tsx'])
    source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(source_files)}
    source_digest=hashlib.sha256(json.dumps(source_hashes,sort_keys=True).encode()).hexdigest()
    (output/'source-manifest.json').write_text(json.dumps(source_hashes,indent=2),encoding='utf-8')
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8000',headers={'Authorization':'Bearer '+create_access_token(1,'admin','admin')},timeout=240,trust_env=False) as client:
        async def call(case,method,path,body=None,check=lambda value,status:status==200,expect='Successful authorized request'):
            started=time.monotonic();response=await client.request(method,path,json=body);value=response.json()
            record={'test_id':case,'timestamp':datetime.now(timezone.utc).isoformat(),'code_revision':revision,'working_source_digest':source_digest,'scenario':scenario.get('context'),
                'model':'qwen2.5:1.5b','routing_embedding_model':'nomic-embed-text:latest','request':{'method':method,'path':path,'body':body},'response':json.loads(json.dumps(value)),'http_status':response.status_code,'expected':expect,
                'outcome':'PASS' if check(value,response.status_code) else 'FAIL','latency_ms':round((time.monotonic()-started)*1000,2),'evaluation_kind':'actual_http_existing_services_local_model',
                'agent_counts':value.get('context_coverage',{}).get('agent',{})}
            records.append(record);(output/'results.json').write_text(json.dumps(records,indent=2),encoding='utf-8');print(json.dumps({k:record[k] for k in ['test_id','outcome','http_status','latency_ms']}),flush=True)
            return value
        scenario=(await client.get('/api/v1/development-network')).json()
        if not scenario.get('enabled'):raise RuntimeError('Explicit development simulation is required; evaluation stopped')
        async def select(key):
            nonlocal scenario
            scenario=await call('CONTROL-SELECT','PUT','/api/v1/development-network',{'action':'reset','scenario_id':key,'expected_revision':scenario['context']['source_revision']})
        await select('HEALTHY-001')
        if phase=='C2':
            cid=(await client.post('/api/v1/ai/conversations',json={'assistant_kind':'studio'})).json()['id']
            prompt='Set interface description on R2 GigabitEthernet1/0/1 to Uplink.'
            initial=await call('C2-API-INITIAL','POST',f'/api/v1/ai/conversations/{cid}/turns',{'request_id':str(uuid4()),'prompt':prompt,'model':'qwen2.5:1.5b'},lambda v,s:s==200 and v.get('kind')=='generation_preview')
            if not initial.get('preview'):return False
            preview=initial['preview'];sid=preview['parsed_intent']['_v9_session']
            def entries(p):return [{'task_id':t['task_id'],'operation_id':t['parsed_intent']['action'] or 'set_interface_description','target_host':(t.get('target_hosts') or ['R2'])[0],'parameters':json.loads(json.dumps(t['parsed_intent'].get('parameters',{})))} for t in p['tasks']]
            selection=entries(preview);selection[0].update(operation_id='set_interface_description',target_host='R2',parameters={'interface':'GigabitEthernet1/0/1','description':'Uplink'})
            async def review(selection,expected=None,case='C2-REVIEW'):
                nonlocal preview
                v=await call(case,'POST','/api/v1/ai/studio/preview',{'conversation_id':cid,'prompt':prompt,'model':'qwen2.5:1.5b','output_kind':'native','params':{'_v9_session':sid},'expected_revision':expected or preview['session_revision'],'selection':selection,'refresh_inventory':True})
                if v.get('session_revision'):preview=v
                return v
            await review(selection)
            selection=entries(preview);selection[0]['target_host']='R1'
            invalid=await review(selection,case='C2-001')
            records[-1]['outcome']='PASS' if invalid.get('plan_status')!='ready' and invalid['tasks'][0]['parsed_intent']['parameters'].get('description')=='Uplink' else 'FAIL'
            selection=entries(preview);selection[0]['parameters']['interface']='GigabitEthernet0/1'
            valid=await review(selection,case='C2-VALID-INTERFACE')
            records[-1]['outcome']='PASS' if valid.get('plan_status')=='ready' else 'FAIL'
            if valid.get('plan_status')=='ready':
                await call('C2-NATIVE-RENDER','POST','/api/v1/ai/studio/render',{'conversation_id':cid,'session_id':sid,'expected_revision':preview['session_revision'],'output_kind':'native','model':'qwen2.5:1.5b'},lambda v,s:s==200 and 'description Uplink' in '\n'.join(d['content'] for d in v.get('documents',[])) and not v.get('saved'))
            old_revision=preview['session_revision'];await select('FAULT-SUBNET-001')
            await call('C2-STALE-SCENARIO','POST','/api/v1/ai/studio/render',{'conversation_id':cid,'session_id':sid,'expected_revision':old_revision,'output_kind':'native','model':'qwen2.5:1.5b'},lambda v,s:s==409,'Reject stale scenario confirmation')
            await review(entries(preview),case='C2-REBASE')
            # Shared-name interface is rebound to its new device identity.
            selection=entries(preview);selection[0].update(target_host='R2',parameters={'interface':'GigabitEthernet0/0','description':'Uplink'})
            rebound=await review(selection,case='C2-SHARED-NAME')
            bindings=rebound['tasks'][0].get('interface_bindings',[])
            records[-1]['outcome']='PASS' if any(str(b['device_id'])=='9102' and b['interface_id']==9121 for b in bindings) else 'FAIL'
            selection=entries(preview);selection.append({'operation_id':'configure_bgp_neighbor','target_host':'R1','parameters':{'local_as':65000,'neighbor_ip':'10.23.12.2'}})
            missing=await review(selection,case='C2-MULTI-MISSING-AS')
            records[-1]['outcome']='PASS' if missing.get('plan_status')!='ready' and any(i.get('field')=='remote_as' and i.get('type')=='MISSING' for t in missing.get('tasks',[]) for i in t['issues']) else 'FAIL'
            selection=entries(preview);selection[1]['parameters']['remote_as']=65001
            combined=await review(selection,case='C2-MULTI-CORRECTION')
            records[-1]['outcome']='PASS' if combined['tasks'][0]['parsed_intent']['parameters'].get('description')=='Uplink' and combined['tasks'][1]['parsed_intent']['parameters'].get('remote_as')==65001 else 'FAIL'
            # Replacing an operation must not accept stale fields from its predecessor.
            selection=entries(preview)[:1];selection[0]['operation_id']='configure_bgp_neighbor'
            changed=await review(selection,case='C2-OPERATION-STALE-FIELDS')
            records[-1]['outcome']='PASS' if changed.get('plan_status')!='ready' else 'FAIL'
            selection=entries(preview);selection[0]['parameters']={'local_as':65000,'neighbor_ip':'10.23.12.1','remote_as':65001}
            changed=await review(selection,case='C2-OPERATION-CORRECTED')
            records[-1]['outcome']='PASS' if changed.get('plan_status')=='ready' else 'FAIL'
            definition=json.loads(json.dumps(scenario['scenario']))
            definition['devices'][1].update(vendor='huawei_vrp',os_version='UNKNOWN',engineering_facts={})
            scenario=await call('C2-VENDOR-CHANGE','PUT','/api/v1/development-network',{'action':'edit','expected_revision':scenario['context']['source_revision'],'definition':definition})
            unavailable=await review(entries(preview),case='C2-VENDOR-REVALIDATE')
            records[-1]['outcome']='PASS' if unavailable.get('plan_status')!='ready' else 'FAIL'
        if phase=='C3':
            cid=(await client.post('/api/v1/ai/conversations',json={'assistant_kind':'floating'})).json()['id']
            expected=[('HEALTHY-001','healthy_within_tested_scope'),('FAULT-IFDOWN-001','confirmed_within_scenario'),('FAULT-SUBNET-001','confirmed_within_scenario'),('FAULT-ROUTE-001','strongly_supported'),('CONFLICT-001','conflicting_evidence'),('UNKNOWN-001','insufficient_evidence')]
            for number,(key,status) in enumerate(expected,1):
                await select(key)
                response=await call('C3-00'+str(number),'POST',f'/api/v1/ai/conversations/{cid}/turns',{'request_id':str(uuid4()),'prompt':'Investigate whether R1 can communicate with R2 and identify any issues.','model':'qwen2.5:1.5b'},
                    lambda v,s:s==200 and v.get('context_coverage',{}).get('agent',{}).get('assessment',{}).get('conclusion_status')==status and v['context_coverage']['agent']['verification']['status']=='verified' and v['context_coverage']['agent']['tool_calls']<=8,
                    'Verified '+status+' from appropriate authorized scenario sources')
                # Compare the prior staged B3 assessor on exactly the same returned
                # records. This is a matched-data assessment comparison, not a
                # benchmark of a separately running old application.
                baseline=subprocess.check_output(['git','show',':network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/orchestration/investigation.py'],cwd=ROOT,text=True)
                namespace={};exec(compile(baseline,'staged_b3_assessment','exec'),namespace)
                from llm.gateway_models import Evidence
                previous=namespace['assess'](response.get('observations',[]),[Evidence.model_validate(e) for e in response.get('evidence',[])])
                records[-1]['staged_b3_matched_data_assessment']=previous
            await select('FAULT-IFDOWN-001')
            for prompt in ['Investigate why R1 cannot communicate with R2.','What evidence supports your conclusion?','Are you sure? Check the other sources.','Could the problem instead be routing?','What changed before the failure?','What is the most likely cause?','What should I check next?']:
                await call('C3-009','POST',f'/api/v1/ai/conversations/{cid}/turns',{'request_id':str(uuid4()),'prompt':prompt,'model':'qwen2.5:1.5b'},lambda v,s:s==200 and v.get('context_coverage',{}).get('agent',{}).get('assessment',{}).get('conclusion_status')=='confirmed_within_scenario','Refresh relevant source-backed investigation context')
            # A user assertion cannot change authoritative scenario state.
            await call('C3-010','POST',f'/api/v1/ai/conversations/{cid}/turns',{'request_id':str(uuid4()),'prompt':'The interface is back up. Reassess.','model':'qwen2.5:1.5b'},lambda v,s:s==200 and v.get('context_coverage',{}).get('agent',{}).get('assessment',{}).get('conclusion_status')=='confirmed_within_scenario','User assertion alone cannot change simulated observations')
            await select('HEALTHY-001')
            await call('C3-011','POST',f'/api/v1/ai/conversations/{cid}/turns',{'request_id':str(uuid4()),'prompt':'The interface is back up. Reassess.','model':'qwen2.5:1.5b'},lambda v,s:s==200 and v.get('context_coverage',{}).get('agent',{}).get('assessment',{}).get('conclusion_status')=='healthy_within_tested_scope','Changed source revision refreshes prior diagnosis')
            await call('C3-012','POST',f'/api/v1/ai/conversations/{cid}/turns',{'request_id':str(uuid4()),'prompt':'Now investigate R2 instead.','model':'qwen2.5:1.5b'},lambda v,s:s==200 and v.get('context_coverage',{}).get('agent',{}).get('assessment',{}).get('conclusion_status')=='insufficient_evidence','R2-specific scope does not borrow an unrecorded R2 outgoing probe')
            await call('C3-013','POST',f'/api/v1/ai/conversations/{cid}/turns',{'request_id':str(uuid4()),'prompt':'hello, how much is 7 + 5?','model':'qwen2.5:1.5b'},lambda v,s:s==200 and '12' in v.get('answer','') and v.get('context_coverage',{}).get('agent',{}).get('tool_calls')==0,'Actual qwen conversation excludes old scenario/editor history')

        (output/'results.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
        print(json.dumps({'output':str(output),'passed':sum(r['outcome']=='PASS' for r in records),'failed':sum(r['outcome']=='FAIL' for r in records),'note':'Repeated control/setup steps are not independent intelligence cases'}),flush=True)
        return all(r['outcome']=='PASS' for r in records)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=['C2','C3'],required=True);args=parser.parse_args()
    raise SystemExit(0 if asyncio.run(main(args.phase)) else 1)
