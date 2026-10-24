"""Actual authenticated Studio -> V9 native journeys, never publication/deployment.

Published engineer fixtures are regression expectations, not independent vendor
certification. Each journey retains the original NL interpretation, explicit
engineer review correction, revision-checked render and UNSAVED document payload.
"""
import argparse
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))


def interface_names(value):
    """Fixture interfaces become explicit planned inventory, never live facts."""
    import re
    if isinstance(value,str):
        return {value} if re.fullmatch(r'(?:GigabitEthernet|Ethernet|FastEthernet|Loop[Bb]ack|Port-channel|Eth-Trunk|10GE|GE|XGE|ge-|xe-|et-|ae|lo|irb)[\w./:-]*',value) else set()
    if isinstance(value,dict):return set().union(*(interface_names(v) for v in value.values())) if value else set()
    if isinstance(value,list):return set().union(*(interface_names(v) for v in value)) if value else set()
    return set()


def natural_request(operation,host,parameters):
    fields='; '.join(k.replace('_',' ')+' = '+json.dumps(v,ensure_ascii=False) for k,v in parameters.items())
    return 'Generate native configuration for '+host+': '+operation['display_name']+'. Use '+fields+'. Prepare an unsaved draft for explicit review only.'


def verify_unsaved(result,binding,fixture,host,device_id,release):
    documents=result.get('documents',[])
    assert result.get('output_kind')=='native' and len(documents)==1,'One native document required'
    doc=documents[0]
    assert doc['saved'] is False and doc['execution_available'] is False,'No save/execution permitted'
    assert str(doc['device_id'])==str(device_id),'Wrong target device'
    assert doc['path'].startswith('playbooks/drafts/') and binding['operation_id'] in doc['path'] and host in doc['path'],'Wrong draft identity'
    assert doc['content'].strip()==fixture['expected_output'].strip(),'Native output differs from published engineer regression fixture'
    assert doc['digest']==hashlib.sha256(doc['content'].encode()).hexdigest(),'Document digest mismatch'
    validation=doc['validation']
    assert validation['status']=='passed' and validation['scope']=='v9_operation' and validation['knowledge_release']==release,'Wrong V9 validation authority'
    assert validation['device_testing']=='not_run' and validation['deployment_authorized'] is False,'Do not invent device validation'
    return doc


def fixture_prerequisites(facts, operation, parameters):
    """Author explicit disposable pre-state, never relax a V9 policy.

    These are controlled planned facts for the published regression input, not
    discovered device facts or an approval. Retain the original model/version,
    capability profile and all validators. Invalid inputs remain invalid.
    """
    resources=facts['resources']
    resources['source_ref']='Phase G explicit controlled pre-state; no physical collection'
    for field in ['vlan_id','native_vlan','allowed_vlans']:
        value=parameters.get(field,[])
        for identity in value if isinstance(value,list) else [value]:
            if type(identity) is int and not any(v['vlan_id']==identity for v in facts['vlans']):
                facts['vlans'].append({'vlan_id':identity,'name':parameters.get('current_vlan_name') or 'LAB_'+str(identity)})
    port=next((i for i in facts['interfaces'] if i['name']==parameters.get('interface')),None)
    if port and operation in {'configure_access_port','configure_trunk_port','assign_vlan_to_trunk_port','configure_trunk_allowed_vlans','set_native_vlan'}:
        port.update(switchport_mode='access' if operation=='configure_access_port' else 'trunk',
            role='switchport',ip_addresses=[],aggregate=None)
        if 'encapsulation' in port:port.update(encapsulation='ethernet-switching',logical_units=[0])
        if operation=='configure_trunk_allowed_vlans' and parameters.get('allowed_vlans'):
            port['native_vlan']=parameters['allowed_vlans'][0]
            port['allowed_vlans']=sorted(set(port.get('allowed_vlans',[]))|{port['native_vlan']})
        if operation=='set_native_vlan':
            port['allowed_vlans']=sorted(set(port.get('allowed_vlans',[]))|{parameters['native_vlan']})
    if port and operation=='assign_interface_to_ospf_area':port['ospf']=None
    if port and operation=='configure_passive_interface':
        port['ospf']={'process_id':parameters['process_id'],'area':'0'}
    if operation=='advertise_network':
        import ipaddress
        network=ipaddress.IPv4Network(parameters['network_prefix'])
        routed=next(i for i in facts['interfaces'] if i.get('switchport_mode')=='routed' and i.get('ip_addresses'))
        routed['ip_addresses']=[str(network.network_address+1)+'/'+str(network.prefixlen)]
        routed['ospf']=None
    if operation=='configure_ospf_redistribution':
        resources['route_policies'].append({'name':parameters['route_policy'],'sources':[parameters['redistribution_source']],
            'bounded':True,'default_action':'deny','allowed_prefixes':['10.50.0.0/16']})
    if 'acl_name' in parameters and operation!='create_acl':
        acl=deepcopy(resources['acls'][0]);acl['name']=parameters['acl_name']
        rule=parameters.get('acl_rule_id')
        if rule is not None:
            acl['rules']=[r for r in acl['rules'] if r['acl_rule_id']!=rule]
            if operation in {'modify_acl_rule','delete_acl_rule'}:
                acl['rules'].append({'acl_rule_id':rule,'kind':'ace','term_name':'rule-'+str(rule)})
        resources['acls']=[r for r in resources['acls'] if r['name']!=acl['name']]+[acl]
    if operation=='classify_by_dscp':
        classifier=next(c for c in resources['classifiers'] if c['name']==parameters['classifier_name'])
        classifier['dscp_values']=list(parameters['previous_dscp_values'])
    if operation=='create_classifier':
        resources['classifiers']=[c for c in resources['classifiers'] if c['name']!=parameters['classifier_name']]
        resources['qos_policies']=[]
    if operation in {'configure_scheduler','apply_qos_policy_to_interface'} and not any(p['name']==parameters['policy_name'] for p in resources['qos_policies']):
        policy=deepcopy(resources['qos_policies'][0]);policy['name']=parameters['policy_name']
        resources['qos_policies'].append(policy)
    if operation=='configure_port_channel':
        for interface in facts['interfaces']:
            if interface['name'] in parameters['member_interfaces']:
                interface.update(ip_addresses=[],service_bindings=[],aggregate=None,switchport_mode='routed')
                if 'logical_units' in interface:interface['logical_units']=[]


def scenario_for(binding,parameters):
    from development.starter import starter_bundle
    bundle=starter_bundle()
    inventory=bundle['sources']['inventory']['data']
    vendors={'cisco':'cisco_xe','juniper':'juniper_junos','huawei':'huawei_vrp'}
    device=next(d for d in inventory['devices'] if d['vendor']==vendors[binding['vendor']])
    device['os_version']=binding['versions'][0]
    fixture_path=ROOT.parent/'network_rag_catalog_v2/data/inventory/devices.json'
    profiles=json.loads(fixture_path.read_text(encoding='utf-8'))
    # Reuse recorded planned policy profiles rather than inventing a family that
    # the authoritative V9 context validator quite correctly rejects. A profile
    # with a different software version is NOT silently relabelled compatible.
    planned=next((d for d in profiles if d['vendor']==binding['vendor'] and d['platform']==binding['platform']
                  and d['version']==device['os_version'] and d.get('model_family')),None)
    if planned:
        facts={key:deepcopy(planned.get(key,{} if key not in {'interfaces','vlans'} else []))
               for key in ['model_family','source_refs','capabilities','vlans','interfaces','resources']}
        facts['origin']='planned'
        facts['source_refs']['evaluation']='Controlled Phase G planned profile; no device discovery or certification'
        facts['capabilities']['features']=sorted(set(facts['capabilities'].get('features',[]))|
            {'interface','vlan','ospf','bgp','isis','static_routing','ip_address','acl','qos','management_plane_security'})
        # This is explicitly authored test state, not an inferred live process.
        if 'process_id' in parameters and binding['operation_id']!='enable_ospf_process':
            processes=facts['resources'].get('ospf_processes',[])
            if not any(p['process_id']==parameters['process_id'] for p in processes):
                processes.append({'process_id':parameters['process_id'],'router_id':'192.0.2.10','areas':{'0':'normal','1':'normal'}})
        fixture_prerequisites(facts,binding['operation_id'],parameters)
        device['engineering_facts']=facts
    else:
        device['engineering_facts']={'origin':'planned','model_family':'controlled_'+binding['platform'],
            'source_refs':{'evaluation':'Controlled generic profile; no matching reviewed model-family policy fixture'},
            'capabilities':{'features':['interface','vlan','ospf','bgp','isis','static_routing','ip_address','acl','qos','management_plane_security']}}
    known={i['name'] for i in inventory['interfaces'] if i['device_id']==device['id']}
    planned_names={row['name'] for row in device['engineering_facts'].get('interfaces',[])}
    requested_names=interface_names(parameters)
    # Creation targets must not be projected as existing physical interfaces.
    # V9's explicit new-loopback/aggregate contracts still decide eligibility.
    if binding['operation_id']=='configure_loopback_interface':requested_names.discard(parameters.get('interface'))
    if binding['operation_id']=='configure_port_channel':requested_names.discard(parameters.get('aggregate_interface'))
    for name in sorted((requested_names|planned_names)-known):
        inventory['interfaces'].append({'id':max(i['id'] for i in inventory['interfaces'])+1,
            'device_id':device['id'],'name':name,'interface_type':'routed','admin_status':'unknown','oper_status':'unknown','vrf':'default'})
    return bundle,device


async def main(args):
    import httpx
    from fastapi import FastAPI
    from auth.auth import create_access_token
    from db.manager import DatabaseManager
    from llm.gateway_api import router
    from llm.gateway_store import ensure_schema
    from llm.gateway_knowledge import read_release
    from local_providers.development import ScenarioManager
    from local_providers.development_api import router as development
    from local_providers.knowledge import knowledge_root
    from local_providers.knowledge_review import identity
    from scripts.phase_d_audit import Run,source_manifest,digest
    os.environ.update(COGNISHIELD_DEV_WORKBENCH='1',COGNISHIELD_DEV_SIMULATION='0',COGNISHIELD_AI_ENGINE='langgraph_b3',COGNISHIELD_AI_PLANNING='1',COGNISHIELD_AI_SYNTHESIS='1')
    release,manifest,pointer=read_release(knowledge_root()/'storage/catalog_releases')
    reviews=json.loads((release/manifest['cognishield_engineer_reviews']['artifact_path']).read_text(encoding='utf-8'))['bindings']
    operations={o['operation_id']:o for o in json.loads((release/'catalog/operations.json').read_text(encoding='utf-8'))}
    spec_path=ROOT/'docs/evaluations/phase_g_native_journey_cases_v1.json'
    frozen=json.loads(spec_path.read_text(encoding='utf-8'))
    assert frozen['knowledge_release']==pointer['release_id'] and frozen['holdout'] is False
    frozen_cases={c['id']:c for c in frozen['cases']};assert len(frozen_cases)==141
    overrides={}
    if args.positive_variants:
        variants=json.loads((ROOT/args.positive_variants).read_text(encoding='utf-8'))
        assert variants['knowledge_release']==pointer['release_id']
        overrides={c['binding_case_id']:c for c in variants['cases']}
        assert overrides and len(overrides)==len(variants['cases']) and set(overrides)<=set(frozen_cases)
        frozen_cases.update({c['id']:{**c,'expected':{'parameters':c['fixture']['parameters']}} for c in variants['cases']})
    bindings=manifest['template_bindings'];assert len(bindings)==141 and len(operations)==47
    eligible=None
    if args.eligible_review:
        eligibility=json.loads((ROOT/args.eligible_review).read_text(encoding='utf-8'))
        assert eligibility['knowledge_release']==pointer['release_id'],'Eligibility review belongs to another release'
        eligible=set(eligibility['eligible_journey_ids'])
    priority={'set_ospf_router_id':0,'configure_bgp_neighbor':1,'configure_static_route':2}
    bindings=sorted(bindings,key=lambda b:(priority.get(b['operation_id'],10),operations[b['operation_id']]['category_id']=='vlan',b['operation_id'],b['vendor']))
    pin=source_manifest()
    critical={k:v for k,v in pin.items() if k in {'backend/llm/gateway.py','backend/llm/gateway_v9.py','backend/local_providers/v9_studio.py','backend/local_providers/v9_worker.py',str(Path(__file__).relative_to(ROOT)).replace('\\','/')}}
    if args.resume:
        path=Path(args.resume).resolve();assert path.is_relative_to((ROOT/'tmp/phase-g/iterations').resolve())
        run=Run.__new__(Run);run.path=path;run.mode='real_model_full_agent'
        rows=[json.loads(line) for line in (path/'cases.jsonl').read_text(encoding='utf-8').splitlines()] if (path/'cases.jsonl').exists() else []
        run.sequence=max((r['sequence'] for r in rows),default=0)
        workspace=Path(json.loads((path/'workspace-ref.json').read_text())['path'])
        assert json.loads((path/'manifest.json').read_text())['knowledge_release']==pointer['release_id']
        with (path/('continuation-'+uuid4().hex[:8]+'.json')).open('x',encoding='utf-8') as f:json.dump({'timestamp':datetime.now(timezone.utc).isoformat(),'source_manifest':pin,
            'case_registry':args.positive_variants or str(spec_path.relative_to(ROOT)),
            'case_registry_sha256':digest((ROOT/args.positive_variants).read_bytes()) if args.positive_variants else digest(spec_path.read_bytes()),
            'state_file':args.state_file},f,indent=2)
    else:
        run=Run('G7-native-journeys','real_model_full_agent',{'knowledge_release':pointer['release_id'],'model':'qwen2.5:1.5b','source_manifest':pin,'case_registry_sha256':digest(spec_path.read_bytes()),'expectation_authority':'existing engineer-approved regression fixtures; not independent CLI certification','holdout':False},phase='phase-g')
        workspace=ROOT/'tmp'/('g7-native-'+uuid4().hex[:6]);workspace.mkdir(exist_ok=False);rows=[]
        (run.path/'workspace-ref.json').write_text(json.dumps({'path':str(workspace)}),encoding='utf-8')
    print(json.dumps({'run':str(run.path),'workspace':str(workspace),'release':pointer['release_id']}),flush=True)
    state_name=args.state_file
    if Path(state_name).name!=state_name or not state_name.endswith('.json'):raise ValueError('Use a JSON basename inside the owned evaluator workspace')
    db=DatabaseManager(str(workspace/'app.db'));db.initialize();ensure_schema(db)
    db._development_scenario=ScenarioManager(workspace/state_name,enabled_default=False)
    app=FastAPI();app.state.local_db=db;app.include_router(development);app.include_router(router)
    completed={r['test_id'] for r in rows if r['outcome']=='PASS'}
    completed_bindings={r.get('binding_case_id',r['test_id']) for r in rows if r['outcome']=='PASS'}
    attempted=0;failures=0;failed_attempts=0
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://controlled-g7',headers={'Authorization':'Bearer '+create_access_token(929,'G7-ENGINEER','admin')},timeout=240) as client:
            async def call(method,path,body=None):
                response=await client.request(method,path,json=body)
                if response.status_code>=400:raise RuntimeError(str(response.status_code)+' '+response.text[:5000])
                return response.json()
            prefix='/api/v1/development-network/workbench';state=await call('GET',prefix)
            control_file=run.path/('controlled-draft-ref.json' if state_name=='state.json' else 'controlled-draft-ref-'+Path(state_name).stem+'.json')
            controlled=json.loads(control_file.read_text(encoding='utf-8')) if control_file.exists() else None
            if controlled:
                current=await call('GET',prefix+'/drafts/'+controlled['draft_id'])
                controlled={'draft_id':current['draft_id'],'expected_revision':current['draft_revision']}
            elif state['drafts']:
                # This is the evaluator-owned disposable workspace, not ordinary
                # scenario state. Preserve every old case bundle in its trace;
                # reuse one owned draft rather than bypassing retention limits.
                current=min(state['drafts'],key=lambda d:d['updated_at'])
                controlled={'draft_id':current['draft_id'],'expected_revision':current['draft_revision']}
            for number,binding in enumerate(bindings,1):
                binding_case='G7-NATIVE-'+binding['vendor'].upper()+'-'+binding['operation_id'].upper()
                if overrides and binding_case not in overrides:continue
                variant=overrides.get(binding_case)
                case=variant['id'] if variant else binding_case
                if eligible is not None and case not in eligible:continue
                if case in completed or args.only and args.only!=binding['operation_id']+':'+binding['vendor']:continue
                if args.limit is not None and attempted>=args.limit:break
                if any(digest((ROOT/name).read_bytes())!=expected for name,expected in critical.items()):raise RuntimeError('Pinned implementation changed; stop and resume at the next safe code revision')
                assert read_release(knowledge_root()/'storage/catalog_releases')[2]==pointer,'Active release changed'
                spec=next(r for r in reviews if r['identity']==identity(binding));fixture=variant['fixture'] if variant else spec['method']['fixtures'][0]
                bundle,device=scenario_for(binding,fixture['parameters']);prompt=natural_request(operations[binding['operation_id']],device['hostname'],fixture['parameters'])
                assert frozen_cases[case]['input_prompt']==prompt and frozen_cases[case]['expected']['parameters']==fixture['parameters'],'Frozen journey specification changed'
                trace={'case':case,'binding':binding,'fixture':fixture,'prompt':prompt,
                    'expectation_authority':variant['expectation_authority'] if variant else 'engineer-approved regression, not independent certification',
                    'scenario_bundle':bundle,'state_file':state_name};started=time.monotonic();attempted+=1
                outcome='FAIL';error=None
                try:
                    draft=await call('POST',prefix+'/drafts',{'bundle':bundle,**(controlled or {})})
                    controlled={'draft_id':draft['draft_id'],'expected_revision':draft['draft_revision']}
                    control_file.write_text(json.dumps(controlled),encoding='utf-8')
                    trace['owned_draft']=controlled
                    receipt=await call('POST',prefix+'/drafts/'+draft['draft_id']+'/validate',{'expected_revision':draft['draft_revision']})
                    state=await call('POST',prefix+'/drafts/'+draft['draft_id']+'/activate',{'expected_revision':draft['draft_revision'],'expected_active':state['context']['source_revision'],'validation_hash':receipt['validation_hash']})
                    trace['scenario']=state['context'];cid=(await call('POST','/api/v1/ai/conversations',{'assistant_kind':'studio'}))['id']
                    turn=await call('POST','/api/v1/ai/conversations/'+cid+'/turns',{'request_id':str(uuid4()),'prompt':prompt,'model':'qwen2.5:1.5b'});trace['initial_turn']=turn
                    assert turn['status']=='success' and turn['kind']=='generation_preview','NL request did not produce a V9 review'
                    preview=turn['preview'];sid=preview['parsed_intent']['_v9_session']
                    assert preview.get('inventory_revision')==state['context']['source_revision'],'Unresolved review lost its known source revision'
                    with db._connect() as c:
                        trace['initial_v9_worker']=json.loads(c.execute('SELECT body FROM studio_v9_sessions WHERE id=?',(sid,)).fetchone()[0])
                    # The same explicit selection controls exposed in Studio.
                    reviewed=await call('POST','/api/v1/ai/studio/preview',{'conversation_id':cid,'prompt':prompt,'model':'qwen2.5:1.5b','output_kind':'native','params':{'_v9_session':sid},'expected_revision':preview['session_revision'],'confirm_order':True,'selection':[{'operation_id':binding['operation_id'],'target_host':device['hostname'],'parameters':fixture['parameters'],'template_id':binding['artifact_path']}]})
                    trace['reviewed_preview']=reviewed
                    assert reviewed['plan_status']=='ready' and len(reviewed['tasks'])==1,'Reviewed V9 contract is not ready'
                    task=reviewed['tasks'][0];assert task['parsed_intent']['action']==binding['operation_id'] and task['target_hosts']==[device['hostname']]
                    for key,value in fixture['parameters'].items():assert task['parsed_intent']['parameters'][key]==value,'Reviewed parameter was changed: '+key
                    body={'conversation_id':cid,'session_id':sid,'expected_revision':reviewed['session_revision'],'output_kind':'native','model':'qwen2.5:1.5b'}
                    trace['explicit_confirmation']=body
                    output=await call('POST','/api/v1/ai/studio/render',body);trace['render']=output
                    document=verify_unsaved(output,binding,fixture,device['hostname'],device['id'],pointer['release_id'])
                    (run.path/(f'{number:03d}-'+binding['vendor']+'-native.cfg')).write_text(document['content'],encoding='utf-8')
                    # Actual original worker plan/counts, not a mocked renderer.
                    with db._connect() as c:trace['final_v9_worker']=json.loads(c.execute('SELECT body FROM studio_v9_sessions WHERE id=?',(sid,)).fetchone()[0])
                    outcome='PASS';completed.add(case);completed_bindings.add(binding_case);failures=0
                except Exception as exc:
                    failures+=1;failed_attempts+=1;error=type(exc).__name__+': '+str(exc);trace['error']=error
                trace_name=f'{number:03d}-{binding["vendor"]}-attempt-{run.sequence+1}.json'
                with (run.path/trace_name).open('x',encoding='utf-8') as f:json.dump(trace,f,indent=2,default=str)
                run.record(case,outcome,binding_case_id=binding_case,expected={'operation':binding['operation_id'],'vendor':binding['vendor'],'profile':binding['platform']+' '+device['os_version'],'parameters':fixture['parameters'],'saved':False,'device_execution':False},actual={'trace':trace_name,'error':error,'unsaved_documents':len(trace.get('render',{}).get('documents',[]))},classification='STUDIO_V9_JOURNEY' if error else None,prompt=prompt,latency_ms=round((time.monotonic()-started)*1000,2))
                (run.path/'progress.json').write_text(json.dumps({'unique_native_journeys_passed':len(completed_bindings),'required':141,'attempts_this_process':attempted,'latest':case,'outcome':outcome,'remaining_gate':'Browser/profile/negative/multioperation and genuine Ansible lane remain separate'},indent=2),encoding='utf-8')
                print(json.dumps({'case':case,'outcome':outcome,'passed':len(completed_bindings),'error':error,'elapsed_s':round(time.monotonic()-started,2)}),flush=True)
                if failures>=3:break
    finally:db.close()
    return len(completed_bindings)==141 or attempted>0 and failed_attempts==0


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--resume');parser.add_argument('--only',help='operation_id:vendor');parser.add_argument('--limit',type=int);parser.add_argument('--eligible-review',help='Preserved V9 preflight eligibility; skipped cases remain unaccepted')
    parser.add_argument('--state-file',default='state.json',help='Owned disposable scenario store basename; old stores remain intact')
    parser.add_argument('--positive-variants',help='Separately frozen positive inputs; preserve original rejected fixtures')
    args=parser.parse_args();raise SystemExit(0 if asyncio.run(main(args)) else 1)
