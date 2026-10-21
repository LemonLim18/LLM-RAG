"""Editable lab observations; expected diagnoses never belong in this bundle."""
from copy import deepcopy
from development.seeded import seeded_scenario
from development.source_registry import SOURCES


STARTERS={'healthy':('S-HEALTHY-ALL-SOURCES','Editable three-vendor development network'),
    'acl':('S-ACL-BLOCKS-FORWARD','Three-vendor policy and forwarding observations'),
    'conflict':('S-STALE-AND-CONFLICT','Three-vendor conflicting protocol observations and stale events')}


def starter_bundle(variant='healthy'):
    if variant not in STARTERS:raise ValueError('Unknown development starter variant')
    scenario=seeded_scenario(71,variant)
    names={d['hostname']:'LAB-R'+str(n+1) for n,d in enumerate(scenario['devices'])}
    def rename(v):
        if isinstance(v,dict):return {k:rename(x) for k,x in v.items()}
        if isinstance(v,list):return [rename(x) for x in v]
        if isinstance(v,str):
            for old,new in names.items():v=v.replace(old,new)
        return v
    scenario=rename(scenario);stamp=scenario['logical_time'];device=scenario['devices'][0]['id']
    sources={s.key:{'schema_version':'1.0','category':s.key,'status':'AVAILABLE','captured_at':stamp,'data':{'records':[]}} for s in SOURCES}
    sources['inventory']['data']={'complete':True,'devices':scenario['devices'],'interfaces':scenario['interfaces']}
    sources['topology_planned']['data']={'links':scenario['planned_links']}
    sources['running_configs']['data']['records']=scenario['records']['running_configuration']
    sources['config_snapshots']['data']['records']=scenario['records']['configuration']
    sources['simulation']['data']={'network':scenario['network']}
    sources['knowledge']['data']={'release_policy':'active_immutable_release','query':'Explain the published OSPF operation requirements','mutable':False}
    sources['conversation']['data']={'turns':['What devices are in the development inventory?'],'assistant_kind':'floating'}
    def record(key,kind,values,did=device,iid=None,current=True,time=stamp):
        return dict(id=key,device_id=did,interface_id=iid,timestamp=time,kind=kind,source='editable-development-observation',current=current,depends_on=[],values=values)
    from datetime import datetime,timedelta
    at=lambda seconds:(datetime.fromisoformat(stamp.replace('Z','+00:00'))+timedelta(seconds=seconds)).isoformat()
    for category in ['topology_observed','topology_history']:
        sources[category]['data']['records']=[record(category+'-'+str(link['id']),'observed_link',
            {'endpoints':{key:link[key] for key in ['src_device_id','src_interface_id','dst_device_id','dst_interface_id']},
             'oper_status':'up','discovery_protocol':'LLDP'},did=link['src_device_id'],
            current=category=='topology_observed',time=stamp if category=='topology_observed' else at(-300)) for link in scenario['planned_links']]
    sources['device_state']['data']['records']=[record('interface-'+str(port['id']),'interface_state',
        {key:port[key] for key in ['prefix','admin_status','oper_status']},did=port['device_id'],iid=port['id']) for port in scenario['interfaces']]
    sources['routing_state']['data']['records']=[record('table-'+str(table['device_id']),'routing_table',table,did=table['device_id']) for table in scenario['network']['tables']]
    peers=[]
    for protocol,key in [('OSPF','ospf'),('BGP','bgp')]:
        for session in scenario['network'][key]:
            peers.append(record('observed-'+session['id'],'protocol_observation',
                {'protocol':protocol,'session_id':session['id'],'observed_state':session['observed_state'],
                 'left':session['left'],'right':session['right'],'observation_basis':'same declared session as the bounded simulation'},did=session['left']['device_id']))
    sources['protocol_state']['data']['records']=peers
    sources['controller_state']['data']['records']=[record('source-controller','controller_state',
        {'controller':'LAB-SDN','configured':True,'operational':'connected','node':'LAB-R1','capabilities':['inventory','observed_topology'],'origin':'simulated'})]
    sources['telemetry']['data']['records']=[record('cpu-'+str(d['id']),'metric_sample',
        {'metric':'cpu_pct','value':value,'unit':'percent','samples':[{'timestamp':at(-60),'value':value-2},{'timestamp':at(-30),'value':value-1},{'timestamp':stamp,'value':value}]},did=d['id'])
        for d,value in zip(scenario['devices'],[18,24,15])]
    sources['interface_metrics']['data']['records']=[record('counter-'+str(port['id']),'interface_counters',
        {'metric':'out_bps','value':value,'unit':'bits_per_second','errors':0,'discards':0,
         'samples':[{'timestamp':at(-30),'value':value-2000},{'timestamp':stamp,'value':value}]},did=port['device_id'],iid=port['id'])
        for port,value in zip(scenario['interfaces'],[18000,24000,23000,17000])]
    sources['syslog']['data']['records']=[record('routing-ready','syslog_event',
        {'severity':'info','facility':'routing','message':'OSPF neighbor reached Full; no adjacency transition is recorded after this event.'},time=at(-30))]
    sources['incidents']['data']['records']=[record('maintenance-complete','incident',
        {'severity':'info','state':'resolved','summary':'Scheduled routing maintenance completed','first_observed':at(-600),'last_observed':at(-300),'cause_status':'scheduled_change_annotation'},current=False,time=at(-300))]
    sources['source_health']['data']={'records':[record('source-health','source_health',
        {'sources':{s.key:'AVAILABLE' for s in SOURCES},'collector':'simulated-source-provider','physical_collection_performed':False})],'overrides':[]}
    if variant=='acl':
        event=record('policy-change','syslog_event',{'severity':'warning','facility':'configuration',
            'message':'Recorded current configuration contains the reviewed-filter input attachment on LAB-R2 ge-0/0/0.0. This event is authored development data.'},did=scenario['devices'][1]['id'])
        event['depends_on']=[scenario['records']['running_configuration'][1]['id']]
        sources['syslog']['data']['records']=[event]
        alert=record('policy-observation-alert','incident',{'severity':'warning','state':'open',
            'summary':'Review the recorded policy attachment change','cause_status':'unassessed_authored_alert'},did=scenario['devices'][1]['id'])
        alert['depends_on']=[event['id']];sources['incidents']['data']['records'].append(alert)
    elif variant=='conflict':
        sources['protocol_state']['status']='CONFLICTING'
        sources['syslog']['status']='STALE'
        sources['syslog']['captured_at']=at(-600)
        sources['syslog']['data']['records']=[record('earlier-neighbor-event','syslog_event',
            {'severity':'warning','facility':'routing','message':'Earlier observer reported the OSPF neighbor Down. No later syslog was captured by this source.'},current=False,time=at(-600))]
        sources['source_health']['data']['records'][0]['values']['sources'].update(protocol_state='CONFLICTING',syslog='STALE')
    sources['jobs_audit']['data']['records']=[record('source-job','simulated_job',
        {'job_id':'SIM-JOB-1','status':'completed','effect':'simulated_validation_only','message':'Development validation completed; no deployment'})]
    from difflib import unified_diff
    for current in scenario['records']['running_configuration']:
        saved=next(r for r in scenario['records']['configuration'] if r['device_id']==current['device_id'])
        before=saved['values']['config_text'];after=current['values']['config_text']
        delta=''.join(unified_diff(before.splitlines(keepends=True),after.splitlines(keepends=True),fromfile='saved',tofile='current'))
        for category,kind in [('config_changes','configuration_change'),('config_drift','configuration_drift')]:
            row=record(category+'-'+str(current['device_id']),kind,
                {'basis':'literal_saved_vs_current','saved_record_id':saved['id'],'current_record_id':current['id'],
                 'diff':delta,'drift_detected':before!=after,'semantic_or_device_validation':'not_performed'},did=current['device_id'])
            row['depends_on']=[saved['id'],current['id']];sources[category]['data']['records'].append(row)
    sources['documents']['data']={'files':[{'path':'docs/operations.md','name':'Lab operations.md'}]}
    sources['attachments']['data']={'files':[{'path':'docs/capture.txt','name':'Lab capture.txt'}]}
    sources['diagrams']['data']={'files':[{'path':'docs/topology.png','name':'Lab topology.png'}],
        'limitation':'Text is readable through local OCR. OCR alone does not verify the drawn link relationships.'}
    import base64,hashlib
    def encode(value):
        raw=value.encode() if isinstance(value,str) else value
        return dict(base64=base64.b64encode(raw).decode(),sha256=hashlib.sha256(raw).hexdigest())
    from pathlib import Path
    assets={'docs/operations.md':encode('# Lab routing\nThis development network has Cisco IOS-XE, Junos and Huawei VRP devices. OSPF and BGP state are recorded separately from saved configurations.\n'),
        'docs/capture.txt':encode('LAB-R1 simulated operational note: interface state is an observation; planned links alone do not establish packet delivery.\n'),
        'docs/topology.png':encode((Path(__file__).parent/'assets/lab-topology.png').read_bytes())}
    identity,title=STARTERS[variant]
    return {'manifest':{'schema_version':'1.0','scenario_id':identity,'name':title,'description':'Source authoring starter. Missing sources remain explicit; adapter acceptance is tracked separately.',
        'scenario_revision':1,'created_by':'bundled-development-author','created_at':stamp,'mode':'development_scenario',
        'clock':{'now':stamp,'timezone':'UTC','paused':True,'rate':0},'source_files':{s.key:s.key+'.json' for s in SOURCES},
        'policy':{'real_device_access':False,'deploy_allowed':False}},'sources':sources,'assets':assets}
