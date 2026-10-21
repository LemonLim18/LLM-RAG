"""Exposed source/answer checks through real auth, gateway, graph and Ollama.

These are development regressions with explicit fixtures, not blind quality
scores. Actual model drafts/fallbacks are retained in each response trace.
"""
import argparse,asyncio,json,os,re,sys,tempfile,time
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
RECORD_LANES={
    'changes':{'category':'config_changes','tool':'network.configuration',
        'prompt':'Show only recorded configuration changes for LAB-R1, including the capture references and literal diff.',
        'values':[{'change_summary':'Added the recorded Uplink-T1 interface description'},
                  {'change_summary':'Added the recorded Uplink-T2 interface description'}]},
    'saved':{'category':'config_snapshots','tool':'network.configuration',
        'prompt':'Show LAB-R1 saved configuration snapshots only.',
        'values':[{'config_text':'hostname LAB-R1\n! G_SAVED_JSON_T1\ninterface Loopback0\n description Recorded-T1\n'},
                  {'config_text':'hostname LAB-R1\n! G_SAVED_JSON_T2\ninterface Loopback0\n description Recorded-T2\n'}]},
    'state':{'category':'device_state','tool':'network.state',
        'prompt':'Read only device and interface state for LAB-R1. Give the exact recorded interface, prefix, administrative versus operational states and observation time. Do not substitute planned inventory or the separately declared simulation.',
        'values':[{'prefix':'10.73.0.1/30','admin_status':'up','oper_status':'down'},
                  {'prefix':'10.74.0.1/30','admin_status':'down','oper_status':'down'}]},
    'syslog':{'category':'syslog','tool':'network.syslog',
        'prompt':'Read only syslog for LAB-R1. Explain the latest recorded message, severity and event time. Do not infer unrecorded current device state.',
        'values':[{'message':'Interface GigabitEthernet0/1 packet discard threshold exceeded.','severity':'warning'},
                  {'message':'Interface GigabitEthernet0/1 discard alert cleared.','severity':'info'}]},
    'incidents':{'category':'incidents','tool':'network.incidents',
        'prompt':'Read only incidents and alerts for LAB-R1. Give the recorded incident summary, severity, status and event time. Do not infer a current outage.',
        'values':[{'summary':'Capacity review queued for LAB-R1','state':'open','severity':'warning'},
                  {'summary':'Capacity review closed for LAB-R1','state':'resolved','severity':'info'}]},
    'jobs':{'category':'jobs_audit','tool':'network.state',
        'prompt':'Read only simulated jobs and audit for LAB-R1. Explain the job ID, recorded outcome, effect and time. Was a device change executed?',
        'values':[{'job_id':'SIM-AUDIT-71','status':'failed','effect':'simulated_validation_only','message':'Development schema check failed; no device execution'},
                  {'job_id':'SIM-AUDIT-72','status':'completed','effect':'simulated_validation_only','message':'Development schema check completed; no device execution'}]},
    'controller':{'category':'controller_state','tool':'network.state',
        'prompt':'Read only controller state for LAB-R1. Explain the recorded controller name, connection status and capture time. Do not infer device connectivity.',
        'values':[{'controller':'LAB-CONTROL-T1','operational':'connected'},
                  {'controller':'LAB-CONTROL-T2','operational':'disconnected'}],
        'literals':[['LAB-CONTROL-T1','connected'],['LAB-CONTROL-T2','disconnected']]},
    'routing':{'category':'routing_state','tool':'network.state',
        'prompt':'Read only routing and forwarding observations for LAB-R1. Explain the exact recorded destination prefix, next hop and observation time. Do not substitute calculated simulation results or infer packet delivery.',
        'values':[{'routes':[{'id':'edited-route-t1','prefix':'203.0.113.0/24','origin':'static','preference':10,'next_hops':[{'interface_id':1,'address':'10.72.0.2','resolved':True}]}]},
                  {'routes':[{'id':'edited-route-t2','prefix':'198.51.100.0/24','origin':'static','preference':10,'next_hops':[{'interface_id':1,'address':'10.72.0.2','resolved':True}]}]}],
        'literals':[['203.0.113.0/24','10.72.0.2'],['198.51.100.0/24','10.72.0.2']]},
    'counters':{'category':'interface_metrics','tool':'network.telemetry',
        'prompt':'Read only interface counters for LAB-R1. Explain the recorded GigabitEthernet0/1 output rate, units and sample time. Do not substitute device telemetry or infer continuous link health.',
        'values':[{'value':25000,'samples':[{'timestamp':'2026-10-18T01:00:00Z','value':25000}]},
                  {'value':31000,'samples':[{'timestamp':'2026-10-18T01:01:00Z','value':31000}]}],
        'literals':[['25000','GigabitEthernet0/1'],['31000','GigabitEthernet0/1']]},
    'drift':{'category':'config_drift','tool':'network.configuration',
        'prompt':'Read only recorded configuration drift for LAB-R1. Explain the saved versus current capture references and literal difference. Do not claim device deployment or independently verified semantics.',
        'values':[{'basis':'literal_saved_vs_current','drift_detected':True},
                  {'basis':'literal_saved_vs_current','drift_detected':True}],
        'literals':[['Uplink-T1'],['Uplink-T2']]},
    'device_metrics':{'category':'telemetry','tool':'network.telemetry',
        'prompt':'Read only telemetry samples for LAB-R1. Give the recorded CPU sample value, units, observation time and source availability. Do not infer continuous health.',
        'values':[{'metric':'cpu','value':18,'unit':'percent'},
                  {'metric':'cpu','value':27,'unit':'percent'}]},
    'health_records':{'category':'source_health','tool':'network.state',
        'prompt':'Read only source health records for LAB-R1. Explain the authored source-availability claims, their observation time and the health-source status. Do not infer physical collection or current device health.',
        'values':[{'physical_collection_performed':False},
                  {'physical_collection_performed':False}]},
}


async def main(lane,selected_case=None,recovery=False):
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
    run=Run('G-source-'+lane,'real_model_full_agent',{'model':'qwen2.5:1.5b','source_digest':digest(json.dumps(source_manifest(),sort_keys=True).encode()),'independent_holdout':False},phase='phase-g')
    failed=False
    with tempfile.TemporaryDirectory(dir=ROOT/'tmp/phase-g',prefix='sources-') as directory:
        folder=Path(directory);db=DatabaseManager(str(folder/'app.db'));db.initialize();ensure_schema(db)
        manager=ScenarioManager(folder/'state.json',enabled_default=False);db._development_scenario=manager
        app=FastAPI();app.state.local_db=db;app.include_router(developer);app.include_router(shared)
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://local-controlled',headers={'Authorization':'Bearer '+create_access_token(929,'G-SOURCE-OWNER','admin')},timeout=240) as client:
                async def call(method,path,body=None):
                    response=await client.request(method,path,json=body);response.raise_for_status();return response.json()
                provider_calls=[];send=httpx.AsyncClient.send
                async def traced_send(selected,request,*args,**kwargs):
                    if request.url.path not in {'/api/chat','/api/generate','/api/embed','/api/embeddings'}:return await send(selected,request,*args,**kwargs)
                    payload=json.loads(request.content);entry={'endpoint':request.url.path,'model':payload.get('model'),
                        'messages':payload.get('messages',[]),'structured_schema':payload.get('format')}
                    provider_calls.append(entry);started=time.monotonic()
                    try:
                        response=await send(selected,request,*args,**kwargs);entry['status']=response.status_code
                        # ChatOllama may request a streamed HTTP response even
                        # for a non-streaming completion. Reading it here would
                        # break the provider; actual drafts remain in the gateway
                        # trace. Capture an already buffered body only.
                        if request.url.path in {'/api/chat','/api/generate'}:
                            if not kwargs.get('stream',False):entry['output']=response.json()
                            else:entry['response_body_capture']='Gateway synthesis trace; transport body left untouched'
                        return response
                    except Exception as exc:entry['error']=type(exc).__name__;raise
                    finally:entry['elapsed_ms']=round((time.monotonic()-started)*1000,2)
                prefix='/api/v1/development-network/workbench';state=await call('GET',prefix)
                cases=(['knowledge-json','knowledge-edited','knowledge-stale','knowledge-error'] if lane=='knowledge' else
                    [lane+suffix for suffix in ['-json','-edited','-stale','-error','-missing']] if lane in RECORD_LANES else
                    [lane+suffix for suffix in ['-json','-edited','-stale','-error','-missing']] if lane in {'planned','history'} else
                    ['inventory-json','inventory-edited','inventory-stale','inventory-error'] if lane=='inventory' else ['topology-json','topology-edited','topology-compare','topology-missing','topology-stale','topology-error'] if lane=='topology' else ['starter-acl','starter-conflict'] if lane=='starter' else ['healthy','conflict'] if lane=='investigation' else ['health-json','health-override'] if lane=='health' else ['controller'] if lane=='coordination' else ['protocol-json','protocol-edited'] if lane=='protocol' else ['metric-json','metric-edited'] if lane=='telemetry' else ['diagram'])
                if recovery:cases=['inventory-json','inventory-edited']
                if selected_case:
                    if selected_case not in cases:raise ValueError('Selected case does not belong to this source lane; no acceptance run was performed')
                    cases=[selected_case]
                conversation_ids={};activated_contexts={}
                for case in cases:
                    bundle=starter_bundle()
                    if lane=='knowledge':
                        import shutil
                        from development.bundles import load_bundle
                        editable=folder/case;shutil.copytree(ROOT/'backend/development/scenarios/healthy_all_sources_v2',editable)
                        source=editable/'knowledge.json';external=json.loads(source.read_text(encoding='utf-8'))
                        method='configure_bgp_neighbor' if case.endswith('edited') else 'set_interface_description'
                        external['data']['query']='Explain published '+method+' method requirements'
                        external['captured_at']='2026-10-18T01:01:00Z' if case.endswith('edited') else '2026-10-18T01:00:00Z'
                        external['status']='ERROR' if case.endswith('error') else 'STALE' if case.endswith('stale') else 'AVAILABLE'
                        manifest=json.loads((editable/'manifest.json').read_text());manifest['clock']['now']='2026-10-18T01:01:00Z'
                        (editable/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
                        source.write_text(json.dumps(external,indent=2),encoding='utf-8');bundle=load_bundle(editable)
                    if lane in RECORD_LANES:
                        import shutil
                        from development.bundles import load_bundle
                        spec=RECORD_LANES[lane];edited=case.endswith('edited')
                        editable=folder/case;shutil.copytree(ROOT/'backend/development/scenarios/healthy_all_sources_v2',editable)
                        source=editable/(spec['category']+'.json');external=json.loads(source.read_text(encoding='utf-8'))
                        row=external['data']['records'][0]
                        row['timestamp']='2026-10-18T01:01:00Z' if edited else '2026-10-18T01:00:00Z'
                        row['values'].update(spec['values'][int(edited)])
                        if lane not in {'saved','changes'}:external['data']['records']=[row]
                        external['captured_at']=row['timestamp']
                        external['status']='STALE' if case.endswith('stale') else 'ERROR' if case.endswith('error') else 'MISSING' if case.endswith('missing') else 'AVAILABLE'
                        manifest=json.loads((editable/'manifest.json').read_text());manifest['clock']['now']='2026-10-18T01:01:00Z'
                        (editable/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
                        if lane in {'changes','drift'}:
                            import difflib
                            current_path=editable/'running_configs.json';current=json.loads(current_path.read_text(encoding='utf-8'))
                            original=json.loads((editable/'config_snapshots.json').read_text(encoding='utf-8'))['data']['records'][0]['values']['config_text']
                            changed=original+'interface GigabitEthernet0/1\n description Uplink-T'+('2' if edited else '1')+'\n'
                            current['data']['records'][0]['values']['config_text']=changed
                            current_path.write_text(json.dumps(current,indent=2),encoding='utf-8')
                            row['values'].update(diff=''.join(difflib.unified_diff(original.splitlines(True),changed.splitlines(True),fromfile='saved',tofile='current')),drift_detected=True)
                        source.write_text(json.dumps(external,indent=2),encoding='utf-8');bundle=load_bundle(editable)
                    if lane in {'planned','history'}:
                        import shutil
                        from development.bundles import load_bundle
                        editable=folder/case;shutil.copytree(ROOT/'backend/development/scenarios/healthy_all_sources_v2',editable)
                        key='topology_planned' if lane=='planned' else 'topology_history'
                        source=editable/(key+'.json');external=json.loads(source.read_text(encoding='utf-8'))
                        ends={'src_device_id':1100,'src_interface_id':1,'dst_device_id':1300,'dst_interface_id':4}
                        if case.endswith('edited'):ends.update(dst_device_id=1200,dst_interface_id=3)
                        if lane=='planned':external['data']['links']=[{'id':17,**ends}]
                        else:
                            row=external['data']['records'][0]
                            row.update(timestamp='2026-10-18T00:56:00Z' if case.endswith('edited') else '2026-10-18T00:54:00Z')
                            row['values'].update(endpoints=ends,oper_status='down' if case.endswith('edited') else 'up',discovery_protocol='LLDP')
                            external['data']['records']=[row]
                        external['captured_at']='2026-10-18T01:01:00Z' if case.endswith('edited') else '2026-10-18T01:00:00Z'
                        external['status']='STALE' if case.endswith('stale') else 'ERROR' if case.endswith('error') else 'MISSING' if case.endswith('missing') else 'AVAILABLE'
                        manifest=json.loads((editable/'manifest.json').read_text());manifest['clock']['now']='2026-10-18T01:01:00Z'
                        (editable/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
                        source.write_text(json.dumps(external,indent=2),encoding='utf-8');bundle=load_bundle(editable)
                    if lane=='inventory':
                        import shutil
                        from development.bundles import load_bundle
                        editable=folder/case;shutil.copytree(ROOT/'backend/development/scenarios/healthy_all_sources_v2',editable)
                        source=editable/'inventory.json';external=json.loads(source.read_text(encoding='utf-8'))
                        device=next(row for row in external['data']['devices'] if row['hostname']=='LAB-R2')
                        device.update(management_ip='192.0.2.92' if case=='inventory-edited' else '192.0.2.91',os_version='24.2R1')
                        port=next(row for row in external['data']['interfaces'] if row['device_id']==device['id'])
                        port['name']='xe-0/0/7.0'
                        external['status']='STALE' if case=='inventory-stale' else 'ERROR' if case=='inventory-error' else 'AVAILABLE'
                        external['captured_at']='2026-10-18T01:01:00Z' if case=='inventory-edited' else '2026-10-18T01:00:00Z'
                        manifest=json.loads((editable/'manifest.json').read_text());manifest['clock']['now']='2026-10-18T01:01:00Z'
                        (editable/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
                        source.write_text(json.dumps(external,indent=2),encoding='utf-8');bundle=load_bundle(editable)
                    if lane=='topology':
                        import shutil
                        from development.bundles import load_bundle
                        editable=folder/case;shutil.copytree(ROOT/'backend/development/scenarios/healthy_all_sources_v2',editable)
                        source=editable/'topology_observed.json';external=json.loads(source.read_text(encoding='utf-8'))
                        observed=external['data']['records'][0]
                        observed['device_id']=1300
                        observed['values']={'endpoints':{'src_device_id':1300,'src_interface_id':4,
                            'dst_device_id':1100 if case!='topology-edited' else 1200,'dst_interface_id':1 if case!='topology-edited' else 3},
                            'oper_status':'up','discovery_protocol':'LLDP'}
                        external['data']['records']=[observed]
                        if case=='topology-edited':
                            observed['timestamp']='2026-10-18T01:01:00Z';external['captured_at']=observed['timestamp']
                            manifest=json.loads((editable/'manifest.json').read_text());manifest['clock']['now']=observed['timestamp']
                            (editable/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
                        if case=='topology-missing':
                            observed['device_id']=1100
                            observed['values']['endpoints']={'src_device_id':1100,'src_interface_id':1,'dst_device_id':1200,'dst_interface_id':3}
                        if case in {'topology-stale','topology-error'}:
                            external['status']='STALE' if case.endswith('stale') else 'ERROR'
                        source.write_text(json.dumps(external,indent=2),encoding='utf-8');bundle=load_bundle(editable)
                    if lane=='starter':
                        variant=case.removeprefix('starter-')
                        bundle=await call('GET',prefix+'/starter?variant='+variant)
                        from development.bundles import load_bundle,compile_bundle
                        directory='acl_forward_all_sources_v1' if variant=='acl' else 'stale_conflict_all_sources_v1'
                        packaged=load_bundle(ROOT/'backend/development/scenarios'/directory)
                        assert compile_bundle(packaged)['network']==compile_bundle(bundle)['network']
                        bundle=packaged
                    if lane=='health':
                        import shutil
                        from development.bundles import load_bundle
                        editable=folder/case;shutil.copytree(ROOT/'backend/development/scenarios/healthy_all_sources_v2',editable)
                        for key,status in [('telemetry','STALE'),('syslog','ERROR')]:
                            source=editable/(key+'.json');value=json.loads(source.read_text(encoding='utf-8'))
                            value['status']=status;source.write_text(json.dumps(value,indent=2),encoding='utf-8')
                        source=editable/'source_health.json';value=json.loads(source.read_text(encoding='utf-8'))
                        value['data']['records'][0]['values']['sources'].update(telemetry='STALE',syslog='ERROR')
                        if case=='health-override':
                            value['data']['records'][0]['values']['sources']['telemetry']='AVAILABLE'
                            value['data']['overrides']=[{'category':'telemetry','status':'ERROR'}]
                        source.write_text(json.dumps(value,indent=2),encoding='utf-8');bundle=load_bundle(editable)
                    if lane in {'protocol','telemetry'}:
                        import shutil
                        from development.bundles import load_bundle
                        editable=folder/case;shutil.copytree(ROOT/'backend/development/scenarios/healthy_all_sources_v2',editable)
                        source=editable/('protocol_state.json' if lane=='protocol' else 'telemetry.json');external=json.loads(source.read_text(encoding='utf-8'))
                        if lane=='protocol':
                            external['data']['records'][0]['values']['left']['router_id']='203.0.113.71'
                            external['data']['records'][0]['values']['right']['router_id']='203.0.113.72'
                        else:external['data']['records'][0]['values']['samples'][1]['value']=None
                        source.write_text(json.dumps(external,indent=2),encoding='utf-8');bundle=load_bundle(editable)
                        if case=='protocol-edited':bundle['sources']['protocol_state']['data']['records'][0]['values']['observed_state']='Init'
                        if case=='metric-edited':bundle['sources']['telemetry']['data']['records'][0]['values']['samples'][0]['value']=27
                    if case=='conflict':bundle['sources']['device_state']['data']['records'][0]['values'].update(admin_status='down',oper_status='down')
                    # Retain exactly the controlled authored bytes used by this
                    # execution. Temporary input folders are cleaned afterward;
                    # the ignored audit pack permits replay without reconstructing
                    # an earlier edit from only a passing answer or a digest.
                    with (run.path/(case+'-bundle.json')).open('x',encoding='utf-8') as file:
                        json.dump(bundle,file,indent=2)
                    draft=await call('POST',prefix+'/drafts',{'bundle':bundle})
                    receipt=await call('POST',prefix+'/drafts/'+draft['draft_id']+'/validate',{'expected_revision':1})
                    state=await call('POST',prefix+'/drafts/'+draft['draft_id']+'/activate',{'expected_revision':1,'expected_active':state['context']['source_revision'],'validation_hash':receipt['validation_hash']})
                    activated_contexts[case]=state['context']
                    for surface in ['floating','studio']:
                        cid=(await call('POST','/api/v1/ai/conversations',{'assistant_kind':surface}))['id']
                        conversation_ids[surface]=cid
                        prompt=('Explain the published operation requirements selected by the scenario knowledge reference. Read only this scenario knowledge reference. Do not generate configuration.' if lane=='knowledge' else
                            RECORD_LANES[lane]['prompt'] if lane in RECORD_LANES else
                            ('Read only planned links for LAB-R1. Give the intended peer and exact interface at each endpoint, source capture time and source availability. Do not infer an observed connection or packet delivery.' if lane=='planned' else
                            'Read only topology history for LAB-R1. Give the historical LLDP peer, exact endpoint interfaces, event time and recorded link state. Do not substitute the current plan or current observed links.') if lane in {'planned','history'} else
                            'What are LAB-R2 management IP and recorded software version?' if lane=='inventory' else
                            'Read only authored observed topology for LAB-R3 now. Give the source status and capture time, and state whether a current neighbor is recorded. Do not substitute planned topology or previous observations.' if case in {'topology-missing','topology-stale','topology-error'} else
                            'Compare observed topology and planned topology for LAB-R3. Explain the disagreement and what it does not prove. Do not generate or modify configuration.' if case=='topology-compare' else
                            'Read only authored observed topology for LAB-R3. Which device and exact interfaces were recorded by LLDP, at what capture time? Do not infer intended cabling or physical reachability.' if lane=='topology' else
                            'Investigate whether LAB-R1 can communicate with LAB-R3 in the selected development scenario. Explain the strongest supported finding and any conflicting observations.' if lane=='starter' else
                            ('Read the source health records. Which logical sources are stale or in error, at what time, and was any physical collection performed?' if case=='health-json' else 'Compare the source health record telemetry claim with the selected scenario effective telemetry source status. Explain any disagreement without inferring a physical network failure.') if lane=='health' else
                            "Investigate whether LAB-R1 can communicate with LAB-R3 using the selected scenario's recorded topology and forwarding evidence. Explain the supported assessment and its limits." if lane=='investigation' else
                            'What does the simulated controller report about LAB-R1, and has it actually collected anything from physical devices?' if lane=='coordination' else
                            'Read the authored OSPF neighbor observations for LAB-R1. Give the local router ID, the neighbor device and router ID, session state and capture time. Use the protocol observation source, not the separately declared simulation.' if lane=='protocol' else
                            'Explain LAB-R1 CPU measurements from 2026-10-18T00:58:59Z to 2026-10-18T00:59:31Z using only the authored telemetry samples. What is observed, and what does the gap leave unknown?' if lane=='telemetry' else
                            'Read the device and vendor labels in Lab topology.png. Explain what is readable and any OCR or visual interpretation limitations.')
                        provider_calls.clear();started=time.monotonic()
                        with patch.object(httpx.AsyncClient,'send',traced_send):
                            result=await call('POST','/api/v1/ai/conversations/'+cid+'/turns',{'request_id':str(uuid4()),'prompt':prompt,'model':'qwen2.5:1.5b'})
                        # Preserve the actual response before any evaluator
                        # contract/assertion failure; observer bugs must not erase
                        # the original model and tool output.
                        with (run.path/(case+'-'+surface+'-response.json')).open('x',encoding='utf-8') as file:
                            json.dump({'response':result,'provider_calls':provider_calls},file,indent=2)
                        answer=result['answer'];agent=result.get('context_coverage',{}).get('agent',{});assessment=agent.get('assessment',{});tools=[i['tool'] for i in result.get('observations',[])]
                        if lane=='knowledge':
                            rows=result.get('observations',[]);data=rows[0].get('data',[]) if len(rows)==1 else []
                            expected={'method':method,'query':external['data']['query'],'status':external['status'],'active_release':'7a14a351e52b49aeb87f65d1192f0937','capture':external['captured_at']}
                            ok=result['status']=='success' and tools==['knowledge.search'] and not result.get('proposal') and not result.get('generation_preview')
                            reference_evidence=[e for e in result.get('evidence',[]) if e['source']=='development.knowledge_reference']
                            ok=ok and len(reference_evidence)==1 and reference_evidence[0]['origin']=='simulated' and expected['capture'].removesuffix('Z') in str(reference_evidence[0]['captured_at'])
                            if case.endswith('error'):
                                ok=ok and rows[0]['status']=='error' and data==[] and 'ERROR' in answer and 'could not be retrieved' in answer
                            else:
                                methods=[op['operation_id'] for row in data for op in row.get('published_requirements',{}).get('operations',[])]
                                ok=ok and methods==[method] and data[0]['scenario_reference']['query']==expected['query']
                                ok=ok and method in answer and expected['capture'].removesuffix('Z') in answer
                                if case.endswith('stale'):ok=ok and 'STALE' in answer
                                ok=ok and any(e['authority']=='published_operation_documentation' and e['origin']=='stored' and e['source_revision']==expected['active_release'] for e in result['evidence'])
                        elif lane in RECORD_LANES:
                            spec=RECORD_LANES[lane];expected={**spec['values'][int(case.endswith('edited'))],'capture':external['captured_at'],'category':spec['category'],'tool':spec['tool']}
                            rows=result.get('observations',[]);data=rows[0].get('data',{}) if len(rows)==1 else {};records=data.get('records',[])
                            negative=case.endswith(('error','missing'))
                            ok=result['status']=='success' and tools==[spec['tool']] and len(records)==(0 if negative else 1)
                            if negative:
                                ok=ok and external['status'] in answer and all(value not in answer for value in spec['values'][0].values() if isinstance(value,str))
                            else:ok=ok and records[0].get('source_category')==spec['category'] and all(records[0].get(key)==value for key,value in spec['values'][int(case.endswith('edited'))].items())
                            ok=ok and all(e['origin']=='simulated' for e in result.get('evidence',[])) and bool(result.get('evidence'))
                            ok=ok and (negative or 'LAB-R1' in answer) and expected['capture'].removesuffix('Z') in answer
                            if lane=='saved' and not negative:
                                ok=ok and expected['config_text'] in answer and not records[0]['current'] and 'historical simulated capture' in answer
                                if case.endswith('stale'):ok=ok and 'STALE' in answer
                            elif lane=='changes' and not negative:
                                ok=ok and expected['change_summary'] in answer and all(line in answer for line in row['values']['diff'].splitlines())
                                if case.endswith('stale'):ok=ok and 'STALE' in answer
                            if not negative:
                                if lane=='state':ok=ok and 'GigabitEthernet0/1' in answer and expected['prefix'] in answer and expected['admin_status'] in answer and expected['oper_status'] in answer
                                elif lane=='syslog':ok=ok and all(value in answer for value in [expected['message'].rstrip('.'),expected['severity']])
                                elif lane=='incidents':ok=ok and all(value in answer for value in [expected['summary'],expected['state'],expected['severity']])
                                elif lane=='jobs':ok=ok and all(value in answer for value in [expected['job_id'],expected['status']]) and bool(re.search(r'\b(?:no|not|never)\b.{0,50}\b(?:execut\w*|deploy\w*|device change)\b',answer,re.I))
                                elif 'literals' in spec:ok=ok and all(value in answer for value in spec['literals'][int(case.endswith('edited'))])
                            from llm.orchestration.synthesis import check_candidate
                            from llm.gateway_models import Evidence
                            errors=check_candidate(answer,rows,[Evidence.model_validate(e) for e in result['evidence']],{},prompt)
                            ok=ok and not errors;expected['answer_guard_errors']=errors
                        elif lane in {'planned','history'}:
                            rows=result.get('observations',[]);data=rows[0].get('data',{}) if len(rows)==1 else {}
                            expected={'tool':'network.topology','category':'topology_planned' if lane=='planned' else 'topology_history',
                                'peer':'LAB-R2' if case.endswith('edited') else 'LAB-R3','peer_interface':'ge-0/0/1.0' if case.endswith('edited') else 'GigabitEthernet0/0/1',
                                'capture':external['captured_at'],'status':external['status']}
                            ok=result['status']=='success' and tools==['network.topology'] and bool(result.get('evidence')) and all(e['origin']=='simulated' for e in result['evidence'])
                            ok=ok and data.get('source_statuses')=={expected['category']:expected['status']}
                            if case.endswith(('error','missing')):
                                ok=ok and rows[0]['status']==('error' if case.endswith('error') else 'unavailable') and data.get('links')==[] and data.get('records')==[]
                                ok=ok and bool(re.search(r'\b(?:unavailable|error|missing|failed|could not)\b',answer,re.I)) and expected['peer_interface'] not in answer
                            else:
                                links=data.get('links',[]) if lane=='planned' else [row.get('link_endpoints',{}) for row in data.get('records',[])]
                                ok=ok and len(links)==1 and links[0]['source']=='LAB-R1' and links[0]['target']==expected['peer']
                                ok=ok and links[0]['source_interface']=='GigabitEthernet0/1' and links[0]['target_interface']==expected['peer_interface']
                                ok=ok and all(value in answer for value in ['LAB-R1','GigabitEthernet0/1',expected['peer'],expected['peer_interface']])
                                if lane=='planned':
                                    ok=ok and expected['capture'].removesuffix('Z') in answer
                                    if case.endswith('stale'):ok=ok and 'stale' in answer.lower()
                                else:
                                    stamp=external['data']['records'][0]['timestamp'];ok=ok and stamp.removesuffix('Z') in answer and 'histor' in answer.lower()
                            from llm.orchestration.synthesis import check_candidate
                            from llm.gateway_models import Evidence
                            errors=check_candidate(answer,rows,[Evidence.model_validate(e) for e in result['evidence']],{},prompt)
                            ok=ok and not errors
                            expected['answer_guard_errors']=errors
                        elif lane=='inventory':
                            expected={'management_ip':'192.0.2.92' if case=='inventory-edited' else '192.0.2.91',
                                'os_version':'24.2R1','capture':'2026-10-18T01:01:00' if case=='inventory-edited' else '2026-10-18T01:00:00',
                                'status':'STALE' if case=='inventory-stale' else 'ERROR' if case=='inventory-error' else 'AVAILABLE'}
                            rows=result.get('observations',[]);data=rows[0].get('data',{}) if len(rows)==1 else {}
                            ok=result['status']=='success' and tools==['inventory.read'] and len(result.get('evidence',[]))==1
                            ok=ok and result['evidence'][0]['origin']=='simulated' and expected['capture'] in str(result['evidence'][0].get('captured_at'))
                            if case=='inventory-error':
                                ok=ok and rows[0]['status']=='error' and data.get('devices')==[] and 'ERROR' in answer and 'unavailable' in answer.lower()
                                ok=ok and expected['management_ip'] not in answer
                            else:
                                devices=data.get('devices',[])
                                ok=ok and len(devices)==1 and devices[0]['hostname']=='LAB-R2' and devices[0]['management_ip']==expected['management_ip'] and devices[0]['os_version']==expected['os_version']
                                ok=ok and all(expected[key] in answer for key in ['management_ip','os_version','capture'])
                                if case=='inventory-stale':ok=ok and 'STALE' in answer and result['evidence'][0]['freshness']=='stale'
                        elif case in {'topology-missing','topology-stale','topology-error'}:
                            expected={'tools':['network.topology'],'requested_source':'current observed relationships','expected':'No current observed neighbor returned; no planned or historical substitution, no physical disconnect claim'}
                            from llm.orchestration.synthesis import check_candidate
                            from llm.gateway_models import Evidence
                            observations=result.get('observations',[])
                            ok=result['status']=='success' and tools==['network.topology'] and len(observations)==1
                            ok=ok and observations[0]['status']==('error' if case=='topology-error' else 'unavailable') and observations[0]['data']['records']==[] and observations[0]['data']['links']==[]
                            if case!='topology-missing':
                                expected['status']=external['status'];expected['capture']=external['captured_at']
                                ok=ok and observations[0]['data']['source_statuses']=={'topology_observed':external['status']}
                                ok=ok and external['status'].lower() in answer.lower() and external['captured_at'].removesuffix('Z') in answer
                            ok=ok and not check_candidate(answer,observations,[Evidence.model_validate(e) for e in result['evidence']],{},prompt)
                        elif case=='topology-compare':
                            expected={'planned_pair':['LAB-R2','LAB-R3'],'observed_pair':['LAB-R1','LAB-R3'],
                                'tools':['network.topology'],'prohibited':'Missing planned router, physical outage certainty or fabricated change history'}
                            from llm.orchestration.synthesis import check_candidate
                            from llm.gateway_models import Evidence
                            ok=result['status']=='success' and tools==['network.topology'] and all(name in answer for name in ['LAB-R1','LAB-R2','LAB-R3'])
                            ok=ok and not check_candidate(answer,result['observations'],[Evidence.model_validate(e) for e in result['evidence']],{},prompt)
                            ok=ok and bool(re.search(r'\b(?:not|cannot|unproven|unknown|doesn.t)\b',answer,re.I))
                        elif lane=='topology':
                            expected={'source':'topology_observed','local':'LAB-R3','interface':'GigabitEthernet0/0/1',
                                'peer':'LAB-R1' if case=='topology-json' else 'LAB-R2',
                                'peer_interface':'GigabitEthernet0/1' if case=='topology-json' else 'ge-0/0/1.0',
                                'capture':'2026-10-18T01:00:00' if case=='topology-json' else '2026-10-18T01:01:00'}
                            observations=result.get('observations',[]);records=observations[0].get('data',{}).get('records',[]) if len(observations)==1 else []
                            ok=result['status']=='success' and tools==['network.topology'] and len(records)==1
                            ok=ok and records[0].get('link_endpoints')=={'source':expected['local'],'source_interface':expected['interface'],
                                'target':expected['peer'],'target_interface':expected['peer_interface']}
                            ok=ok and records[0].get('endpoint_basis')=='authored_observation'
                            ok=ok and all(expected[key] in answer for key in ['local','interface','peer','peer_interface','capture'])
                        elif lane=='starter':
                            expected='confirmed_within_scenario' if case=='starter-acl' else 'conflicting_evidence'
                            ok=result['status']=='success' and 'network.state' in tools and assessment.get('conclusion_status')==expected
                            if case=='starter-acl':ok=ok and 'LAB-R2' in answer and bool(re.search(r'\b(?:acl|policy|filter|denied|deny|blocked|discard)\b',answer,re.I))
                            else:ok=ok and bool(re.search(r'\b(?:conflict\w*|disagree\w*|contradict\w*)\b',answer,re.I))
                        elif lane=='investigation':
                            expected='healthy_within_tested_scope' if case=='healthy' else 'conflicting_evidence'
                            ok=result['status']=='success' and assessment.get('conclusion_status')==expected and 'network.state' in tools
                            ok=ok and (('delivered' in answer.lower() or 'delivery' in answer.lower()) if case=='healthy' else any(w in answer.lower() for w in ['conflict','disagree','contradict']))
                            if case=='conflict':
                                ok=ok and any(w in answer.lower() for w in ['compare','resolve','reconcile','refresh']) and any(w in answer.lower() for w in ['record','observation','source'])
                        elif lane=='health':
                            expected={'authored_telemetry':'AVAILABLE' if case=='health-override' else 'STALE',
                                'effective_telemetry':'ERROR' if case=='health-override' else 'STALE',
                                'syslog':'ERROR','physical_collection':False,'timestamp':'2026-10-18T01:00:00Z'}
                            ok=result['status']=='success' and tools==['network.state']
                            for token in ['telemetry','ERROR',expected['authored_telemetry'],'2026-10-18T01:00:00']:
                                ok=ok and token.casefold() in answer.casefold()
                            if case=='health-json':ok=ok and 'syslog' in answer.casefold() and bool(re.search(r'\b(?:no|not|never)\b.{0,90}\bphysical\b',answer,re.I))
                            else:ok=ok and bool(re.search(r'\b(?:disagree|different|override|conflict)\w*\b',answer,re.I))
                        elif lane=='coordination':
                            expected='Controller LAB-SDN connected; no physical device collection; authorized state reader, not telemetry substitution'
                            ok=result['status']=='success' and 'network.state' in tools and 'LAB-SDN' in answer and 'connected' in answer.lower()
                            ok=ok and bool(re.search(r'\b(?:no|not|never)\b.{0,90}\bphysical\b|\bphysical\b.{0,60}\bnot (?:performed|collected)\b',answer,re.I))
                            planning=agent.get('planning',{}).get('proposed',{})
                            ok=ok and 'state' in {need['domain'] for need in planning.get('information_needs',[])}
                        elif lane=='protocol':
                            expected='Full' if case=='protocol-json' else 'Init'
                            ok=result['status']=='success' and tools==['network.state'] and all(text in answer for text in ['203.0.113.71','203.0.113.72','LAB-R2',expected])
                            ok=ok and not any(text in answer for text in ['198.19.71.1','198.19.71.2','Full/Established'])
                            if case=='protocol-edited':ok=ok and not __import__('re').search(r'\bFull\b',answer)
                        elif lane=='telemetry':
                            expected_value=16 if case=='metric-json' else 27
                            expected={'window_values':[expected_value,None],'unit':'percent','no_outside_window_value':18,'scope':'authored telemetry, simulated/historical'}
                            observations=result.get('observations',[])
                            rows=observations[0].get('data',{}).get('records',[]) if len(observations)==1 else []
                            ok=result['status']=='success' and tools==['network.telemetry'] and len(rows)==1
                            ok=ok and [p['value'] for p in rows[0].get('samples',[])]==[expected_value,None] and rows[0].get('value') is None
                            ok=ok and str(expected_value) in answer and any(w in answer.lower() for w in ['gap','missing','unknown','unavailable'])
                        else:
                            expected='Readable Cisco/Junos/Huawei labels; OCR limitation; no verified visual topology'
                            ok=result['status']=='success' and all(w in answer for w in ['Cisco','Junos','Huawei']) and 'OCR' in answer and result.get('context_coverage',{}).get('files',{}).get('tool')=='document.read'
                            from llm.orchestration.verification import ocr_visual_errors
                            ok=ok and not ocr_visual_errors(answer,[{'extraction':'ocr'}])
                        failed|=not ok
                        synthesis=agent.get('verification',{}).get('synthesis',{})
                        repaired=synthesis.get('status')=='repaired_literal_checks_passed' or result.get('context_coverage',{}).get('document_verification',{}).get('status')=='model_repair'
                        attribution=('MODEL_REPAIRED' if repaired else 'MODEL_ACCEPTED') if result.get('model') else 'VERIFIED_FALLBACK'
                        if result['status']!='success':attribution='FAILED'
                        run.record('G-'+case.upper()+'-'+surface.upper(),'PASS' if ok else 'FAIL',expected=expected,actual={'response':result,'active_revision':state['context'],'selected_tools':tools,'attribution':attribution,'provider_calls':list(provider_calls),'provider_call_count':len(provider_calls)},prompt=prompt,latency_ms=round((time.monotonic()-started)*1000,2))
                        print(json.dumps({'run':str(run.path),'case':case,'surface':surface,'pass':ok,'attribution':attribution,'answer':answer}),flush=True)
                        if lane=='inventory' and case in {'inventory-json','inventory-edited'} and ok:
                            followup='What exact interfaces are recorded for LAB-R2?'
                            provider_calls.clear();started=time.monotonic()
                            with patch.object(httpx.AsyncClient,'send',traced_send):
                                follow=await call('POST','/api/v1/ai/conversations/'+cid+'/turns',{'request_id':str(uuid4()),'prompt':followup,'model':'qwen2.5:1.5b'})
                            actual_ports=[port['name'] for item in follow.get('observations',[]) for device in item.get('data',{}).get('devices',[]) for port in device.get('interfaces',[])]
                            correct=follow['status']=='success' and [row['tool'] for row in follow.get('observations',[])]==['inventory.read'] and actual_ports==['xe-0/0/7.0','ge-0/0/1.0','lo0.0']
                            correct=correct and all(name in follow['answer'] for name in actual_ports) and expected['capture'] in follow['answer']
                            failed|=not correct
                            run.record('G-'+case.upper()+'-INTERFACES-'+surface.upper(),'PASS' if correct else 'FAIL',expected={'interfaces':['xe-0/0/7.0','ge-0/0/1.0','lo0.0'],'capture':expected['capture']},actual={'response':follow,'provider_calls':list(provider_calls),'provider_call_count':len(provider_calls),'model_reasoning_credit':False},prompt=followup,latency_ms=round((time.monotonic()-started)*1000,2))
                            print(json.dumps({'run':str(run.path),'case':case+'-interfaces','surface':surface,'pass':correct,'answer':follow['answer']}),flush=True)
                        if lane=='protocol' and case=='protocol-edited' and ok:
                            followup='What does this Init state imply about the OSPF adjacency, and what cannot be concluded from it? Keep using the same authored source.'
                            provider_calls.clear();started=time.monotonic()
                            with patch.object(httpx.AsyncClient,'send',traced_send):
                                follow=await call('POST','/api/v1/ai/conversations/'+cid+'/turns',{'request_id':str(uuid4()),'prompt':followup,'model':'qwen2.5:1.5b'})
                            text=follow['answer'];coverage=follow.get('context_coverage',{});retrieval=coverage.get('retrieval',{});agent=coverage.get('agent',{})
                            scopes=retrieval.get('source_requests',{}).get('state',{}).get('source_categories',[])
                            correct=follow['status']=='success' and retrieval.get('device_refs')==['1100'] and scopes==['protocol_state']
                            correct=correct and 'Init' in text and 'hello' in text.lower() and bool(re.search(r'\b(?:not|no|cannot)\b',text,re.I))
                            correct=correct and '198.19.71.' not in text and not re.search(r'\bFull\b.{0,20}\b(?:established|confirmed)\b',text)
                            failed|=not correct
                            run.record('G-PROTOCOL-FOLLOWUP-'+surface.upper(),'PASS' if correct else 'FAIL',expected={'device':'1100','source_categories':['protocol_state'],'meaning':'Init: Hello received, bidirectional communication not yet established; no proved cause or packet delivery','reference':'RFC2328 section10.1; full-answer review required'},actual={'response':follow,'provider_calls':list(provider_calls),'provider_call_count':len(provider_calls),'checkpointing':agent.get('checkpointing'),'model':follow.get('model'),'quality_gate':'Source/required-meaning checks only; inspect full prose separately'},prompt=followup,latency_ms=round((time.monotonic()-started)*1000,2))
                            print(json.dumps({'run':str(run.path),'case':'protocol-followup','surface':surface,'pass':bool(correct),'model':follow.get('model'),'answer':text}),flush=True)
                        if lane=='telemetry' and ok:
                            for name,followup,expected_points in [
                                ('same-window','Are you sure the missing point is zero? Recheck that same window and source.',[expected_value,None]),
                                ('new-window','Instead read only LAB-R1 CPU from 2026-10-18T00:59:59Z to 2026-10-18T01:00:01Z, using the same authored telemetry source. What is recorded?',[18]),
                                ('source-switch','Read the telemetry from interface counters instead, for the same device and window.',[18000])]:
                                provider_calls.clear();started=time.monotonic()
                                with patch.object(httpx.AsyncClient,'send',traced_send):
                                    follow=await call('POST','/api/v1/ai/conversations/'+cid+'/turns',{'request_id':str(uuid4()),'prompt':followup,'model':'qwen2.5:1.5b'})
                                observations=follow.get('observations',[])
                                records=observations[0].get('data',{}).get('records',[]) if len(observations)==1 else []
                                points=[p['value'] for p in records[0].get('samples',[])] if len(records)==1 else []
                                refs=follow.get('context_coverage',{}).get('retrieval',{})
                                bounds=refs.get('source_requests',{}).get('telemetry',{})
                                expected_bounds=({'start':'2026-10-18T00:58:59Z','end':'2026-10-18T00:59:31Z'} if name=='same-window' else
                                    {'start':'2026-10-18T00:59:59Z','end':'2026-10-18T01:00:01Z'})
                                correct=follow['status']=='success' and [i['tool'] for i in observations]==['network.telemetry'] and points==expected_points
                                correct=correct and refs.get('device_refs')==['1100'] and bool(follow.get('evidence')) and all(e.get('requested_time_range')==expected_bounds for e in follow.get('evidence',[]))
                                correct=correct and all(bounds.get(key)==value for key,value in expected_bounds.items())
                                correct=correct and bounds.get('source_categories')==(['interface_metrics'] if name=='source-switch' else ['telemetry'])
                                from llm.orchestration.synthesis import check_candidate
                                from llm.gateway_models import Evidence
                                answer_errors=check_candidate(follow['answer'],observations,[Evidence.model_validate(e) for e in follow.get('evidence',[])],{},followup)
                                correct=correct and not answer_errors
                                failed|=not correct
                                run.record('G-METRIC-'+name.upper()+'-'+surface.upper(),'PASS' if correct else 'FAIL',expected={'points':expected_points,'window':expected_bounds,'quality_gate':'Full prose review required'},actual={'response':follow,'provider_calls':list(provider_calls),'provider_call_count':len(provider_calls),'answer_errors':answer_errors},prompt=followup,latency_ms=round((time.monotonic()-started)*1000,2))
                                print(json.dumps({'run':str(run.path),'case':name,'surface':surface,'pass':bool(correct),'points':points,'window':bounds,'model':follow.get('model'),'answer':follow['answer']}),flush=True)
                if recovery:
                    state=await call('GET',prefix)
                    selected=next(row for row in state['history'] if row['scenario_id']==bundle['manifest']['scenario_id'] and row['revision']==activated_contexts['inventory-json']['revision'])
                    denied=await client.post(prefix+'/history/'+selected['id']+'/restore',json={'expected_active':state['context']['source_revision']},headers={'Authorization':'Bearer '+create_access_token(930,'G-OTHER-OWNER','admin')})
                    ok=denied.status_code==404 and (await call('GET',prefix))['context']==state['context']
                    run.record('G-INVENTORY-RECOVERY-OWNER','PASS' if ok else 'FAIL',expected='Another authenticated owner cannot restore this recorded revision',actual={'status':denied.status_code,'active_unchanged':ok})
                    failed|=not ok
                    state=await call('POST',prefix+'/history/'+selected['id']+'/restore',{'expected_active':state['context']['source_revision']})
                    for surface,cid in conversation_ids.items():
                        for case,prompt in [('restored','What are LAB-R2 management IP and recorded software version?'),('unknown','Which management address is recorded for R999?')]:
                            provider_calls.clear();started=time.monotonic()
                            with patch.object(httpx.AsyncClient,'send',traced_send):
                                result=await call('POST','/api/v1/ai/conversations/'+cid+'/turns',{'request_id':str(uuid4()),'prompt':prompt,'model':'qwen2.5:1.5b'})
                            tools=[o['tool'] for o in result.get('observations',[])];answer=result['answer']
                            ok=not result.get('proposal') and not result.get('generation_preview')
                            if case=='restored':
                                ok=ok and tools==['inventory.read'] and '192.0.2.91' in answer and '192.0.2.92' not in answer and '24.2R1' in answer and '2026-10-18T01:00:00' in answer
                                ok=ok and result['evidence'] and all(e['origin']=='simulated' for e in result['evidence'])
                            else:ok=ok and not tools and 'R999' in answer and '192.0.2.9' not in answer
                            run.record('G-INVENTORY-'+case.upper()+'-'+surface.upper(),'PASS' if ok else 'FAIL',expected={'case':case,'restored_management_ip':'192.0.2.91','never_substitute_T2':'192.0.2.92'},actual={'response':result,'provider_calls':list(provider_calls),'active_revision':state['context'],'model_reasoning_credit':False},prompt=prompt,latency_ms=round((time.monotonic()-started)*1000,2))
                            failed|=not ok
                            print(json.dumps({'run':str(run.path),'case':case,'surface':surface,'pass':bool(ok),'answer':answer}),flush=True)
                (run.path/'result.json').write_text(json.dumps({'complete':True,'passed':not failed,'holdout':False,'quality_gate':'NOT_ASSESSED','lane':lane,'recovery':recovery},indent=2),encoding='utf-8')
        finally:db.close()
    return not failed


if __name__=='__main__':
    # A recovery run adds owner-isolation and revision-refresh checks to the
    # existing inventory cases; it does not create another evaluation service.
    parser=argparse.ArgumentParser()
    parser.add_argument('--recovery',action='store_true',help='Verify inventory revision restoration and unknown-device scope')
    parser.add_argument('lane',choices=['knowledge',*RECORD_LANES,'planned','history','inventory','investigation','diagram','coordination','protocol','telemetry','health','starter','topology']);parser.add_argument('--case',choices=['knowledge-json','knowledge-edited','knowledge-stale','knowledge-error',*[lane+suffix for lane in RECORD_LANES for suffix in ['-json','-edited','-stale','-error','-missing']],'planned-json','planned-edited','planned-stale','planned-error','planned-missing','history-json','history-edited','history-stale','history-error','history-missing','inventory-json','inventory-edited','inventory-stale','inventory-error','healthy','conflict','diagram','controller','protocol-json','protocol-edited','metric-json','metric-edited','health-json','health-override','starter-acl','starter-conflict','topology-json','topology-edited','topology-compare','topology-missing','topology-stale','topology-error']);args=parser.parse_args()
    if args.recovery and args.lane!='inventory':parser.error('--recovery requires inventory')
    raise SystemExit(0 if asyncio.run(main(args.lane,args.case,getattr(args,'recovery',False))) else 1)
