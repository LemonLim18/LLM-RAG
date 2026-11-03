"""Completeness/adequacy helpers for the existing graph. No IO or inference.

Coverage is server-owned; interpretation remains a model proposal. Typed claim
checks certify only their explicit operands, never unrestricted narrative.
"""
import difflib,ipaddress,re
from collections import defaultdict
from enum import Enum
from llm.orchestration.request_contract import reader_constraints,advisory_contract
from llm.orchestration.evidence_harness import coverage,guidance

READERS={'inventory':'inventory.read','knowledge':'knowledge.search',**{d:'network.'+d for d in ['state','configuration','topology','syslog','telemetry','incidents']}}
OPERATIONAL=('inventory','topology','state','configuration','syslog','telemetry','incidents')

class EvidenceClass(str,Enum):
    OPERATIONAL_STATE='operational_state'
    EVENT_RECORD='event_record'
    RUNNING_CONFIGURATION='running_configuration'
    SAVED_CONFIGURATION='saved_configuration'
    INVENTORY_TOPOLOGY='inventory_topology'
    DERIVED_ANALYSIS='derived_analysis'
    SIMULATED_SCENARIO='simulated_scenario'

# Source compatibility, not a global credibility score or causal diagnosis.
COMPATIBILITY={
    'interface_oper_status':{'operational_state'},'interface_admin_status':{'operational_state','running_configuration'},
    'ospf_state':{'operational_state','derived_analysis'},'bgp_state':{'operational_state','derived_analysis'},
    'ownership':{'inventory_topology','operational_state','running_configuration','saved_configuration'},
    'configured_command':{'running_configuration','saved_configuration'},
    'configuration_change_time':{'event_record','running_configuration'},'link_oper_status':{'operational_state'},
    'incident_occurred':{'event_record'},'no_incident':{'event_record'},'measured_loss_percent':{'operational_state'},
    'simulated_forwarding':{'derived_analysis','simulated_scenario'},'root_cause':{'operational_state','event_record','derived_analysis'}}


def enabled():
    from llm.model_roles import investigation_profile
    return investigation_profile()['enabled']


def walk(value,path=''):
    if isinstance(value,dict):
        if 'id' in value and ('kind' in value or 'config_text' in value):yield path,value
        for key,item in value.items():yield from walk(item,path+'/'+str(key).replace('~','~0').replace('/','~1'))
    elif isinstance(value,list):
        for i,item in enumerate(value):yield from walk(item,path+'/'+str(i))


def breadth(request,planning):
    policy=reader_constraints(request)
    if advisory_contract(request):return 'advisory'
    if policy['allowed'] is not None or policy['no_other_sources']:return 'restricted'
    proposed=planning.get('proposed',{})
    from llm.orchestration.investigation import is_investigation
    if proposed.get('investigation_breadth')=='comprehensive' or proposed.get('desired_response')=='investigation' or is_investigation(request):return 'comprehensive'
    return 'targeted'


def reconcile(request,route,registry,allowed):
    mode=breadth(request,route.planning);policy=reader_constraints(request)
    from llm.orchestration.request_contract import response_obligations,original_sources
    required={}
    for clause in response_obligations(request,include_actions=True) or [{'text':request}]:
        for domain,args in original_sources(clause['text'],{'devices':[]}).items():
            # A family permission (e.g. telemetry in a read-only source list)
            # is not a request to filter a multiplexed reader to one subtype.
            if reader_constraints(clause['text'])['allowed'] is not None and args.get('source_categories')==[domain]:
                args={k:v for k,v in args.items() if k!='source_categories'}
            if domain in required:
                previous=required[domain]
                args={**previous,**args,'source_categories':list(dict.fromkeys(previous.get('source_categories',[])+args.get('source_categories',[]))),
                    'source_scope':'both' if {previous.get('source_scope'),args.get('source_scope')}=={'current','historical'} else args.get('source_scope','auto')}
            required[domain]=args
            existing=route.source_requests.get(domain,{})
            route.source_requests[domain]={**existing,**{k:v for k,v in args.items() if k!='source_scope' or v!='auto'}}
    wanted=list(dict.fromkeys([*route.network_domains,*required,*(OPERATIONAL if mode=='comprehensive' else []),*sorted(policy['denied'])])) if mode!='advisory' else []
    coverage_plan=[];selected=[]
    for domain in wanted:
        name=READERS[domain];cap=registry.capability(name)
        status='CAPABILITY_READY_SOURCE_UNQUERIED'
        if not cap:status='NOT_REGISTERED'
        elif name not in allowed or cap.effect!='read':status='NOT_AUTHORIZED'
        elif domain in policy['denied'] or policy['allowed'] is not None and domain not in policy['allowed']:status='PROHIBITED'
        elif cap.availability is not None and not cap.availability():status='TEMPORARILY_UNAVAILABLE'
        else:selected.append(domain)
        coverage_plan.append({'domain':domain,'reader':name,'status':status,
            'selected_by':'model' if domain in route.network_domains else 'server_original_source' if domain in required else 'server_broad_coverage'})
    if mode=='comprehensive':
        for domain in ['configuration','topology']:
            if domain in selected:route.source_requests[domain]={**route.source_requests.get(domain,{}),'source_scope':policy['source_scopes'].get(domain,'both'),'record_kinds':[],'source_categories':[]}
    route.network_domains=selected
    route.planning['investigation']={'breadth':mode,'source_coverage_plan':coverage_plan,
        'authority':'Coverage only; added readers are server-selected, never attributed to model inference.'}
    return route


def source_coverage(plan,results,executed_queries=()):
    """Per-invocation coverage; family summaries never erase partial success.

    Old results remain unbound. A last same-family query is not evidence of
    which invocation produced an older result.
    """
    output=[]
    for source in plan:
        matches=[r for r in results if r['tool']==source['reader']]
        item=dict(source)
        if matches:
            queries=[];seen=set()
            for row in matches:
                data=row.get('data');data={} if data is None else data
                embedded=row.get('reader_receipt') or {}
                identity=embedded.get('invocation_id')
                candidates=[q for q in executed_queries if identity and q.get('invocation_id')==identity]
                binding='HISTORICAL_UNBOUND' if not identity else 'EXACT_INVOCATION'
                receipt=embedded
                if identity and (embedded.get('tool')!=row['tool'] or candidates and any(
                    any(q.get(k)!=embedded.get(k) for k in ['tool','parameters','source_revisions']) for q in candidates)):
                    binding='RECEIPT_MISMATCH';receipt={}
                elif identity and executed_queries and not candidates:
                    binding='INVOCATION_NOT_FOUND';receipt={}
                if identity:
                    # Only an exact repeated invocation/result is redundant.
                    # Different invocations of the same query are retained.
                    import json
                    fingerprint=json.dumps(row,sort_keys=True,default=str)
                    if (identity,fingerprint) in seen:continue
                    seen.add((identity,fingerprint))
                if receipt.get('invocation_status')=='failed' or row.get('status') in {'error','denied'}:status='QUERY_FAILED'
                elif isinstance(data,dict) and (data.get('source_available') is False or data.get('current_available') is False and row.get('source_request',{}).get('source_scope')=='current'):status='SOURCE_UNAVAILABLE'
                elif isinstance(data,list):
                    status='PARTIALLY_RETRIEVED' if any(isinstance(d,dict) and d.get('retrieval_coverage',{}).get('truncated') for d in data) else 'QUERIED_SUCCESSFULLY' if data else 'QUERIED_ZERO_MATCHES'
                elif isinstance(data,dict) and data.get('truncated') or receipt.get('truncated'):status='PARTIALLY_RETRIEVED'
                elif any(True for _ in walk(data)) or any(data.get(k) for k in ['devices','links','nodes','samples','sources'] if isinstance(data,dict)):status='QUERIED_SUCCESSFULLY'
                elif isinstance(data,dict) and data.get('records')==[]:status='QUERIED_ZERO_MATCHES'
                elif row.get('status')=='unavailable':status='SOURCE_UNAVAILABLE'
                else:status='SOURCE_UNAVAILABLE_OR_UNKNOWN'
                queries.append({'invocation_id':identity,'reader':row['tool'],'receipt_binding':binding,
                    'parameters':receipt.get('parameters'),'source_revisions':receipt.get('source_revisions',[]),
                    'source_scope':row.get('source_request',{}),'status':status,
                    'invocation_status':receipt.get('invocation_status'),
                    'truncated':status=='PARTIALLY_RETRIEVED',
                    'evidence_ids':list(row.get('evidence_ids',[])),
                    'record_refs':receipt.get('record_refs') or list(dict.fromkeys(str(r['id']) for _,r in walk(data)))})
            statuses=[q['status'] for q in queries]
            successful={'QUERIED_SUCCESSFULLY','QUERIED_ZERO_MATCHES'}
            if 'PARTIALLY_RETRIEVED' in statuses or any(s in successful for s in statuses) and any(s not in successful for s in statuses):
                combined='PARTIALLY_RETRIEVED'
            elif 'QUERIED_SUCCESSFULLY' in statuses:combined='QUERIED_SUCCESSFULLY'
            elif 'QUERIED_ZERO_MATCHES' in statuses:combined='QUERIED_ZERO_MATCHES'
            elif 'QUERY_FAILED' in statuses:combined='QUERY_FAILED'
            elif 'SOURCE_UNAVAILABLE' in statuses:combined='SOURCE_UNAVAILABLE'
            else:combined='SOURCE_UNAVAILABLE_OR_UNKNOWN'
            item.update(status=combined,query_statuses=statuses,queries=queries,
                receipt_ids=list(dict.fromkeys(e for row in matches for e in row.get('evidence_ids',[]))))
        output.append(item)
    return output


def network_map(inventory,results,targets,broad=False):
    """Recorded identity is separate from operational observations."""
    permitted=any(r['tool']=='inventory.read' and r['status']=='success' for r in results)
    related=set(map(str,targets));observations=[]
    for i,row in enumerate(results):
        for path,record in walk(row.get('data'),'/reader_results/'+str(i)+'/data'):
            if record.get('device_id') is not None:related.add(str(record['device_id']))
            if record.get('interface_id') is not None or any(k in record for k in ['prefix','vrf','admin_status','oper_status']):
                observations.append({'record_path':path,**{k:record[k] for k in ['id','device_id','interface_id','hostname','interface','prefix','vrf','timestamp','admin_status','oper_status'] if k in record}})
    devices=inventory.get('devices',[]);group=defaultdict(int)
    for d in devices:group[str(d.get('site') or 'unspecified')]+=1
    overview=[{k:d.get(k) for k in ['id','hostname','role','site','vendor','model','os_version']} for d in devices[:100]] if permitted and broad else []
    detailed=[]
    if permitted:
        for d in devices:
            if str(d['id']) not in related:continue
            ports=d.get('interfaces',[])
            detailed.append({'id':d['id'],'hostname':d['hostname'],'vendor':d.get('vendor'),'platform':d.get('model'),
                'interfaces':[{k:p.get(k) for k in ['id','device_id','name','prefix','ip_address','subnet_mask','vrf']} for p in ports[:128]],
                'remaining_interface_ids':[p['id'] for p in ports[128:]],'authority':'Recorded inventory; no operational status inferred'})
    links=[{'id':x.get('id'),'endpoints':{k:x[k] for k in ['src_device_id','src_interface_id','dst_device_id','dst_interface_id'] if k in x},'class':'documented_planned_not_operational'} for x in inventory.get('links',[]) if permitted and (broad or str(x.get('src_device_id')) in related or str(x.get('dst_device_id')) in related)]
    return {'inventory_authorized_read':permitted,'total_recorded_devices':len(devices) if permitted else None,'site_counts':dict(group) if permitted else {},
        'overview':overview,'remaining_overview_ids':[d['id'] for d in devices[100:]] if overview else [],'detailed':detailed,'documented_links':links,
        'source_observations':observations,'limitations':['Inventory documents identity/intent, not current operational health.','Remaining IDs explicitly disclose context limits; request a scoped inventory read for details.']}


def classify(record,reader):
    kind=record.get('kind','');classes=[]
    if 'config_text' in record:
        running=kind=='running_configuration' or record.get('snapshot_type')=='running' or record.get('configuration_state')=='running'
        classes=['running_configuration' if running else 'saved_configuration']
    elif kind in {'syslog_event','configuration_change','incident','alert'}:classes=['event_record']
    elif record.get('derived') or kind in {'forwarding_assessment','protocol_assessment','metric_series'}:classes=['derived_analysis']
    elif kind in {'interface_state','routing_table','observed_link','protocol_observation','metric_sample','interface_counters'}:classes=['operational_state']
    elif reader in {'inventory.read','network.topology'}:classes=['inventory_topology']
    return classes or ['unknown']


def evidence_envelope(results):
    entries=[]
    for i,row in enumerate(results):
        data=row.get('data') or {};origin=(data.get('scenario') or {}).get('origin','unknown') if isinstance(data,dict) else 'unknown'
        for path,record in walk(data,'/reader_results/'+str(i)+'/data'):
            classes=classify(record,row['tool'])
            if origin=='simulated':classes=[*classes,'simulated_scenario']
            entries.append({'artifact_id':record['id'],'record_path':path,'source':row['tool'],'classes':classes,'origin':origin,
                'device_id':record.get('device_id'),'interface_id':record.get('interface_id'),'captured_at':record.get('timestamp',record.get('captured_at')),
                'verification_status':record.get('verification_status','not_established'),'current':record.get('current')})
    return entries


def context_lines(text):
    """Lexical IOS stanza anchors / Junos set paths, not vendor semantics."""
    anchor='';output=[]
    for n,line in enumerate(text.splitlines(),1):
        if line and not line[0].isspace() and not line.startswith(('!','#')):anchor=line
        output.append({'line':n,'text':line,'context':line if line.startswith(('set ','delete ')) else anchor})
    return output


def artifact_comparisons(results,inventory):
    from llm.gateway_network import timestamp
    vendors={str(d['id']):d.get('vendor') for d in inventory.get('devices',[])};groups=defaultdict(list);events=[]
    for i,row in enumerate(results):
        for path,r in walk(row.get('data'),'/reader_results/'+str(i)+'/data'):
            if classify(r,row['tool'])==['event_record']:events.append(r)
            if row['tool']!='network.configuration' or not isinstance(r.get('config_text'),str) or r.get('device_id') is None:continue
            key=(str(r.get('device_id')),r.get('vendor',vendors.get(str(r.get('device_id')))),str(r.get('vrf','device_context')))
            groups[key].append((path,r))
    output=[];omitted=0
    for identity,artifacts in groups.items():
        artifacts.sort(key=lambda x:((timestamp(x[1].get('timestamp',x[1].get('captured_at'))).timestamp() if timestamp(x[1].get('timestamp',x[1].get('captured_at'))) else float('-inf')),str(x[1]['id'])))
        # A stored/staged artifact interleaved by capture time must not erase
        # the comparison between consecutive actual running observations.
        # Retain cross-artifact diffs separately; neither establishes a change
        # event or continuous operational state between captures.
        running_artifacts=[x for x in artifacts if classify(x[1],'network.configuration')==['running_configuration']]
        pairs=list(zip(running_artifacts,running_artifacts[1:]))
        seen={(a[0],b[0]) for a,b in pairs}
        pairs.extend((a,b) for a,b in zip(artifacts,artifacts[1:]) if (a[0],b[0]) not in seen)
        for (ap,a),(bp,b) in pairs:
            if len(output)>=16:omitted+=1;continue
            before=context_lines(a['config_text']);after=context_lines(b['config_text']);matcher=difflib.SequenceMatcher(a=[x['text'] for x in before],b=[x['text'] for x in after],autojunk=False)
            changes=[{'operation':tag,'before':before[i:j],'after':after[k:l]} for tag,i,j,k,l in matcher.get_opcodes() if tag!='equal']
            running=all(classify(x,'network.configuration')==['running_configuration'] for x in [a,b])
            times=[timestamp(x.get('timestamp',x.get('captured_at'))) for x in [a,b]]
            ordered=all(times) and times[0]<times[1]
            refs={a['id'],b['id'],a.get('change_event_ref'),b.get('change_event_ref')}-{None}
            related=[e['id'] for e in events if e['id'] in refs or refs.intersection(e.get('depends_on',[]))]
            output.append({'device_id':identity[0],'vendor':identity[1],'vrf_context':identity[2],
                'before':{'id':a['id'],'path':ap,'captured_at':a.get('timestamp',a.get('captured_at')),'class':classify(a,'network.configuration')[0]},
                'after':{'id':b['id'],'path':bp,'captured_at':b.get('timestamp',b.get('captured_at')),'class':classify(b,'network.configuration')[0]},
                'comparison_kind':'RUNNING_HISTORY' if running else 'SAVED_HISTORY' if all(classify(x,'network.configuration')==['saved_configuration'] for x in [a,b]) else 'CROSS_ARTIFACT',
                'changes':changes,'related_recorded_event_ids':related,'temporal_support':'RUNNING_OBSERVATION_INTERVAL' if running and ordered else 'UNORDERED_RUNNING_CAPTURES' if running else 'ARTIFACT_DIFFERENCE_ONLY',
                'limitations':'Textual/contextual differences, not semantic equivalence, exact activation time, actor or proven root cause. Event references are associations, not causality.'})
    return {'comparisons':output,'omitted_pairs':omitted,'scope':'Only same device/vendor/VRF context; consecutive running observations plus adjacent textual artifacts. Saved files are not running-history observations; raw records retained.'}


def _compatible_operands(decision,results,inventory):
    """Only declared typed assertions; unrestricted prose is not certified."""
    actual=[]
    for row in results:
        parents=set(row.get('evidence_ids',[]))
        for _,r in walk(row.get('data')):actual.append((row['tool'],r,parents|{str(r['id'])}))
        if row['tool']=='inventory.read' and isinstance(row.get('data'),dict):
            for device in row['data'].get('devices',[]):
                for port in device.get('interfaces',[]):
                    # An authorized inventory receipt may cite a structured
                    # port even though inventory rows have no operational kind.
                    r={**port,'device_id':device['id'],'interface_id':port['id'],'kind':'inventory_interface'}
                    actual.append((row['tool'],r,parents|{str(port['id'])}))
    aliases={str(v).casefold():str(d['id']) for d in inventory.get('devices',[]) for v in [d['id'],d['hostname'],*d.get('aliases',[])]}
    reports=[]
    for claim in decision.get('claims',[]):
        kind=claim['category'];refs=set(claim.get('record_refs',[]));records=[(t,r) for t,r,bindings in actual if refs.intersection(bindings)]
        status='UNVERIFIED';reason='No matching authorized typed record';values=[]
        if claim.get('scope')=='physical':
            status='INCOMPATIBLE_PROVENANCE';reason='This approved investigation is synthetic; declared observations/calculations cannot certify physical infrastructure'
        else:
            compatible=[(t,r) for t,r in records if COMPATIBILITY[kind].intersection(classify(r,t))]
            if records and not compatible:status='INCOMPATIBLE_EVIDENCE';reason='The declared source class cannot establish this claim category'
            scoped=[]
            for tool,r in compatible:
                device=aliases.get(str(claim.get('device_id')).casefold(),str(claim.get('device_id')))
                interface=str(claim.get('interface_id'))
                for d in inventory.get('devices',[]):
                    if str(d['id'])==device:
                        interface=next((str(p['id']) for p in d.get('interfaces',[]) if interface in {str(p['id']),p['name']}),interface)
                interface=next((str(p['interface_id']) for _,p,_ in actual if str(p.get('id'))==interface and str(p.get('device_id'))==device and p.get('interface_id') is not None),interface)
                candidates=[r]
                if kind=='simulated_forwarding':
                    # Flow records belong to the originating endpoint; a failed
                    # hop belongs to its nested directional branch, not that
                    # top-level device. Never flatten forward/return identities.
                    candidates=[]
                    path_field=claim.get('field') or 'status'
                    path_role={'ingress.status':'ingress','egress.status':'egress'}.get(path_field)
                    # Unqualified legacy failed-at-interface declarations keep
                    # their stopping-location semantics. Qualified role fields
                    # explicitly describe traversal, not the cause/location of
                    # an eventual failure elsewhere on that branch.
                    failure_only=path_field=='failure_location.status' or path_field=='status' and claim.get('value')=='failed'
                    directions=[claim['direction']] if claim.get('direction') else ['forward','return']
                    for direction in directions:
                        part=r.get('assessment',{}).get(direction,{})
                        branches=part.get('branches',[])
                        if claim.get('branch_id'):branches=[b for b in branches if str(b.get('id'))==str(claim['branch_id'])]
                        if claim.get('device_id') or claim.get('interface_id'):
                            scope=part.get('scope',{})
                            if claim.get('device_id') and not claim.get('interface_id') and str(scope.get('source_device_id'))==device:
                                candidates.append({**r,'device_id':scope['source_device_id'],'vrf':scope.get('vrf'),'_claim_status':part.get('status')})
                            for branch in branches:
                                location=branch.get('failure_location')
                                if location and (path_role is None or location.get('direction',location.get('interface_role'))==path_role):
                                    candidates.append({**r,**location,'vrf':location.get('vrf',scope.get('vrf')),'_claim_status':branch.get('status')})
                                if not failure_only and (claim.get('interface_id') or path_role):
                                    locations=[]
                                    for hop in branch.get('hops',[]):
                                        if hop.get('interface_id') is not None:locations.append((hop,'egress'))
                                        if isinstance(hop.get('ingress'),dict):locations.append((hop['ingress'],'ingress'))
                                    if isinstance(branch.get('destination_ingress'),dict):locations.append((branch['destination_ingress'],'ingress'))
                                    for place,role in locations:
                                        if path_role is not None and role!=path_role:continue
                                        candidates.append({**r,**place,'vrf':place.get('vrf',scope.get('vrf')),'_claim_status':branch.get('status')})
                        else:candidates.append({**r,'_claim_status':part.get('status')})
                for candidate in candidates:
                    if claim.get('timestamp'):
                        from llm.gateway_network import timestamp
                        expected=timestamp(claim['timestamp']);observed=timestamp(candidate.get('timestamp',candidate.get('captured_at')))
                        if expected is None or observed is None or expected!=observed:continue
                    if claim.get('device_id') and str(candidate.get('device_id'))!=device:continue
                    if claim.get('interface_id') and str(candidate.get('interface_id'))!=interface and kind!='configured_command':continue
                    if claim.get('vrf') and candidate.get('vrf') is not None and candidate['vrf']!=claim['vrf']:continue
                    scoped.append((tool,candidate))
            if compatible and not scoped:
                # A whole-device artifact has no per-port identity; a receipt
                # may span many records. Neither proves a different owner.
                definite=[r for _,r in compatible if str(r['id']) in refs and
                    ((claim.get('device_id') and r.get('device_id') is not None and str(r['device_id'])!=device) or
                     (claim.get('interface_id') and r.get('interface_id') is not None and str(r['interface_id'])!=interface) or
                     (claim.get('vrf') and r.get('vrf') is not None and r['vrf']!=claim['vrf']))]
                # Directional modeled locations were already resolved above.
                if kind=='simulated_forwarding':
                    definite=[]
                    for _,record in compatible:
                        directions=[claim['direction']] if claim.get('direction') else ['forward','return']
                        branches=[b for d in directions for b in record.get('assessment',{}).get(d,{}).get('branches',[])
                            if not claim.get('branch_id') or str(b.get('id'))==str(claim['branch_id'])]
                        if branches and all(b.get('status') in {'delivered','failed'} for b in branches):definite.append(record)
                status='CONTRADICTED_IDENTITY' if definite else 'UNKNOWN_BINDING_SCOPE'
                reason='Explicit source ownership conflicts with the declaration' if definite else 'No unambiguous source-owned operand at the declared scope'
            for tool,r in scoped:
                field=claim.get('field');value=None
                if kind in {'interface_oper_status','interface_admin_status','link_oper_status','ownership'}:
                    key=field or {'interface_oper_status':'oper_status','interface_admin_status':'admin_status','link_oper_status':'status'}.get(kind)
                    if key in {'oper_status','admin_status','status','device_id','interface_id','prefix','ip_address','vrf','hostname','interface'}:value=r.get(key)
                    if key=='ip_address' and value is None and r.get('prefix'):
                        try:value=str(ipaddress.ip_interface(r['prefix']).ip)
                        except ValueError:pass
                elif kind in {'ospf_state','bgp_state'}:
                    if str(r.get('protocol','')).upper()==('OSPF' if kind=='ospf_state' else 'BGP'):value=r.get('observed_state',r.get('state',r.get('neighbor_state',r.get('session_state'))))
                elif kind=='configured_command':
                    lines=context_lines(r.get('config_text',''))
                    if claim.get('interface_id'):
                        names=[p['name'] for d in inventory.get('devices',[]) if str(d['id'])==str(r.get('device_id')) for p in d.get('interfaces',[]) if str(p['id'])==interface]
                        lines=[x for x in lines if any(re.search(r'(?<![\w/])'+re.escape(n)+r'(?![\w/])',x['context']) for n in names)]
                    value=claim['value'] if any(str(claim['value']).strip()==x['text'].strip() for x in lines) else None
                elif kind=='simulated_forwarding':
                    value=r.get('_claim_status') if field in {None,'status','ingress.status','egress.status','failure_location.status'} else None
                elif kind=='measured_loss_percent':
                    value=r.get('loss_percent')
                    if value is None and isinstance(r.get('lost_packets'),(int,float)) and isinstance(r.get('sent_packets'),(int,float)) and r['sent_packets']>0 and 0<=r['lost_packets']<=r['sent_packets']:value=100*r['lost_packets']/r['sent_packets']
                    if value is not None and not 0<=value<=100:value=None
                elif kind=='configuration_change_time':
                    if r.get('verification_status')=='verified' and r.get('applied') is True:
                        from llm.gateway_network import timestamp
                        # An explicit source field is never substituted with a
                        # different temporal role. Preserve the legacy default
                        # only when the declaration did not request a field.
                        recorded=r.get(field) if field else r.get('timestamp',r.get('captured_at'))
                        if timestamp(recorded) is not None:value=recorded
                elif kind=='incident_occurred':
                    value=r.get('message') if field=='message' else True if field in {None,'verification_status'} and r.get('verification_status')=='verified' else None
                elif kind=='no_incident':value=False if r.get('coverage_complete') is True and r.get('matching_event_count')==0 else None
                # Root-cause prose requires causal interpretation; record presence
                # alone is never promoted into certification of that claim.
                if value is not None:values.append(value)
            if kind=='configuration_change_time' and claim.get('field')=='observation_interval' and len(scoped)>=2:
                running=[r for t,r in scoped if classify(r,t)==['running_configuration']]
                from llm.gateway_network import timestamp
                running=[r for r in running if timestamp(r.get('timestamp',r.get('captured_at')))]
                if len(running)>=2 and len({str(r.get('device_id')) for r in running})==1 and len({r.get('config_text') for r in running})>1:
                    times=sorted((str(r.get('timestamp',r.get('captured_at'))) for r in running),key=timestamp)
                    if times[0]!=times[-1]:values.append(times[0]+'/'+times[-1])
            if not values and status=='UNVERIFIED' and kind!='root_cause':
                status='INSUFFICIENT_SUPPORT';reason='The cited record does not establish the declared value/scope; qualify the claim, do not invent support'
            if values and status not in {'INVALID_CLAIM_BINDING','CONTRADICTED_IDENTITY'}:
                def same(a,b):
                    if isinstance(a,(int,float)) and isinstance(b,(int,float)):return abs(a-b)<1e-8
                    return str(a).casefold()==str(b).casefold()
                supported=[same(v,claim['value']) for v in values]
                status='SUPPORTED_TYPED_OPERAND' if all(supported) else 'CONFLICTING_EVIDENCE' if any(supported) else 'CONTRADICTED_VALUE'
                if kind=='incident_occurred' and claim.get('field')=='message' and not all(supported):status='UNCHECKED_EVENT_PARAPHRASE'
                reason='Only declared source-owned operands checked, not the full natural-language interpretation'
        reports.append({'claim':claim,'literal_span':claim['statement'] in decision.get('answer',''),'status':status,'reason':reason,'actual_values':values})
    return {'authority':'Typed source compatibility only; claim extraction completeness and unrestricted prose remain unverified. No global credibility score.',
        'claims':reports,'conflicts':[r for r in reports if r['status'] in {'INCOMPATIBLE_EVIDENCE','CONTRADICTED_IDENTITY','CONTRADICTED_VALUE','INVALID_CLAIM_BINDING','INSUFFICIENT_SUPPORT','INCOMPATIBLE_PROVENANCE'}]}


def compatible_claims(decision,results,inventory):
    """Separate source contradiction, missing support and checker failure.

    Legacy status is retained as a diagnostic; only the explicit verdict may
    drive correction/release. No verdict certifies unrestricted answer prose.
    """
    reports=[]
    for claim in decision.get('claims',[]):
        try:
            item=_compatible_operands({'answer':decision.get('answer',''),'claims':[claim]},results,inventory)['claims'][0]
            status=item['status']
            verdict={'SUPPORTED_TYPED_OPERAND':'SUPPORTED','CONTRADICTED_VALUE':'CONTRADICTED','CONTRADICTED_IDENTITY':'CONTRADICTED',
                'INCOMPATIBLE_EVIDENCE':'INSUFFICIENT_EVIDENCE','INCOMPATIBLE_PROVENANCE':'INSUFFICIENT_EVIDENCE',
                'INSUFFICIENT_SUPPORT':'INSUFFICIENT_EVIDENCE','CONFLICTING_EVIDENCE':'INSUFFICIENT_EVIDENCE',
                'UNKNOWN_BINDING_SCOPE':'NOT_MECHANICALLY_CHECKABLE','UNCHECKED_EVENT_PARAPHRASE':'NOT_MECHANICALLY_CHECKABLE'}.get(status,'NOT_MECHANICALLY_CHECKABLE')
            values=item['actual_values']
            if values and any(type(v) is bool for v in values) and type(claim.get('value')) is not bool:verdict='MODEL_CONTRACT_ERROR'
            if claim['category']=='measured_loss_percent' and type(claim.get('value')) not in {int,float}:verdict='MODEL_CONTRACT_ERROR'
            if claim['category']=='root_cause':verdict='NOT_MECHANICALLY_CHECKABLE'
            item['verdict']=verdict
            item['source_scope']={k:claim.get(k) for k in ['record_refs','device_id','interface_id','vrf','timestamp','direction','branch_id','field','scope']}
            item['bound_source_facts']=[]
            for row in results:
                for _,record in walk(row.get('data')):
                    if str(record['id']) not in claim.get('record_refs',[]):continue
                    facts={k:record[k] for k in ['id','device_id','interface_id','vrf','timestamp','protocol','admin_status','oper_status','kind'] if k in record}
                    if claim.get('direction'):facts['failure_locations']=[b['failure_location'] for b in record.get('assessment',{}).get(claim['direction'],{}).get('branches',[]) if b.get('failure_location')]
                    item['bound_source_facts'].append(facts)
        except Exception as exc:
            # Pure validator boundary: no IO/authorization or cancellation is
            # caught here. A broken checker must not accuse the model of a lie.
            item={'claim':claim,'status':'VALIDATOR_ERROR','verdict':'VALIDATOR_ERROR','literal_span':False,
                'actual_values':[],'reason':type(exc).__name__+': '+str(exc)[:200]}
        reports.append(item)
    return {'authority':'Declared source-owned operands only; missing support is not contradiction and prose remains unverified.',
        'claims':reports,'conflicts':[r for r in reports if r['verdict']=='CONTRADICTED'],
        'limitations':[r for r in reports if r['verdict'] not in {'SUPPORTED','CONTRADICTED'}]}


def release_interpretation(decision,review):
    """Single final policy for a valid core, with auditable limited authority."""
    result=dict(decision);answer=result.get('answer','');compat=review.get('claim_compatibility',{})
    contradictions=compat.get('conflicts',[]);withheld=[];original=answer
    for finding in contradictions:
        statement=finding['claim'].get('statement','')
        start=answer.find(statement) if statement else -1
        raw_prefix=answer[:start] if start>=0 else '';prefix=raw_prefix.rstrip()
        safe=start>=0 and answer.count(statement)==1 and statement.rstrip().endswith(('.','!','?')) and (not prefix or raw_prefix.endswith('\n') or prefix.endswith(('.','!','?')))
        if not safe:
            answer='A declared material assertion conflicts with its source-bound evidence and could not be safely isolated. The interpretation is withheld; the authorized records remain inspectable.'
            withheld=['whole_interpretation'];break
        answer=answer[:start]+'[Source-contradicted assertion withheld.]'+answer[start+len(statement):];withheld.append(statement)
    auxiliary=decision.get('auxiliary_validation',{});limitations=compat.get('limitations',[])
    notes=[]
    if auxiliary.get('status')=='MODEL_CONTRACT_ERROR':notes.append('Some auxiliary claim declarations were invalid; the valid core answer is retained without verification credit for those declarations.')
    if limitations:notes.append('Some declared assertions could not be mechanically established from their cited scope. Their interpretation remains unverified; this is not evidence that they are false.')
    if review.get('state') in {'VALIDATOR_ERROR','ADEQUACY_TIMEOUT'}:notes.append('The evidence review did not complete reliably; no verification or completeness certificate is claimed.')
    if notes:answer+='\n\n**Verification limits:** '+' '.join(notes)
    valid_core=bool(decision.get('raw_output') or decision.get('core_validation')=='VALID')
    result.update(answer=answer,release_decision={'core':'VALID' if valid_core else 'UNAVAILABLE',
        'disposition':'INCOMPLETE_RESULT' if not valid_core else 'WITHHELD' if withheld==['whole_interpretation'] else 'PARTIAL_WITHHELD' if withheld else 'QUALIFIED_UNVERIFIED' if notes else 'UNVERIFIED_PREVIEW',
        'contradictions':len(contradictions),'unsupported_or_uncheckable':len(limitations),'auxiliary_contract':auxiliary.get('status','NOT_DECLARED'),
        'withheld_spans':withheld,'unchanged_model_prose':not withheld,'semantic_certified':False,
        'missing_dependencies':review.get('unread_dependencies',[]),'outcome_assessments':'Model proposals only; task adequacy requires independent review.'})
    if withheld:result['unreleased_draft']=original
    return result


def post_draft(state,decision,inventory,registry,allowed,executed_queries):
    """Deterministic adequacy review even when the model selected answer."""
    from llm.orchestration.request_contract import response_obligations
    policy=reader_constraints(state.request);policy={k:sorted(v) if isinstance(v,set) else v for k,v in policy.items()}
    packet={'reader_results':state.results,'requested_clauses':response_obligations(state.request,include_actions=True) or [{'id':'request-1','text':state.request}],
        'retrieval_boundary':{'source_restrictions':policy},'planning_proposal_not_authority':state.route.planning}
    ledger=coverage(packet);plan=state.route.planning.get('investigation',{});families=source_coverage(plan.get('source_coverage_plan',[]),state.results,executed_queries)
    compatibility=compatible_claims(decision,state.results,inventory)
    # A revision cannot evade an already established contradiction by dropping
    # its auxiliary declaration while repeating the exact false assertion.
    for old in state.investigation.get('last_review',{}).get('claim_compatibility',{}).get('conflicts',[]):
        statement=old.get('claim',{}).get('statement','')
        if statement and statement in decision.get('answer',''):
            again=compatible_claims({'answer':decision['answer'],'claims':[old['claim']]},state.results,inventory)
            for finding in again['conflicts']:
                if finding['claim'] not in [r['claim'] for r in compatibility['conflicts']]:
                    compatibility['conflicts'].append({**finding,'carried_from_prior_draft':True})
    hints=guidance(state,inventory,registry,allowed,executed_queries)
    unresolved=[d for d in ledger['dependencies'] if d['retrieval']=='NOT_RETRIEVED_LOCATION_UNKNOWN']
    proposals=[]
    if not advisory_contract(state.request):
        # Only actual unread dependency references or missing mandatory coverage,
        # not a model's generic uncertainty or an unrelated optional source.
        for hint in hints:
            if any(hint['possible_gap']==d['reference'] for d in unresolved):
                args=dict(hint['parameters'])
                # Actual truncation, not speculative source scarcity, justifies
                # a larger scoped read. Readers expose no arbitrary pagination.
                truncated=[r for r in state.results if r['tool']==hint['reader'] and r.get('status')=='success'
                    and isinstance(r.get('data'),dict) and r['data'].get('truncated')]
                if truncated:
                    args['limit']=100
                    # Expanding an actual truncated invocation is not authority
                    # to narrow it with a guessed category for an unknown event.
                    # Retain the exact successful query when uniquely bound to
                    # these owners; ambiguous time/filter histories stay unbound.
                    same=[r.get('reader_receipt',{}).get('parameters') for r in truncated
                        if r.get('reader_receipt',{}).get('tool')==hint['reader']
                        and set(map(str,r.get('reader_receipt',{}).get('parameters',{}).get('device_refs',[])))==set(map(str,args.get('device_refs',[])))]
                    if len(same)==1 and same[0] is not None:args={**same[0],'limit':100}
                proposals.append({'reader':hint['reader'],'parameters':args,'gap':hint['possible_gap'],
                    'why':'Server post-draft review found a typed unretrieved dependency','evidence_refs':[]})
        for item in families:
            if item['status']=='CAPABILITY_READY_SOURCE_UNQUERIED':
                proposals.append({'reader':item['reader'],'parameters':{'device_refs':state.device_refs} if item['reader']!='inventory.read' else {},
                    'gap':'Mandatory broad family not inspected','why':'Server coverage requirement','evidence_refs':[]})
    return {'state':'DRAFT_INTERPRETATION','source_coverage':families,'retrieval_ledger':ledger,'claim_compatibility':compatibility,
        'server_proposals':proposals[:3],'unread_dependencies':unresolved,
        'outcome_assessments_are_proposals':decision.get('outcome_assessments',[]),
        'stop_if_no_actionable_gap':'No semantic completeness certificate: finalize strongest qualified answer, retain limitations and unchecked causal prose.'}
