"""Optional organization of existing receipts, not a planner or semantic verifier.

No IO, source execution or model inference. Queries are proposals validated by
the SAME supplementary-query boundary that governs real execution.
"""
import os
from copy import deepcopy


def canonical_packet(packet):
    """Experimental organization of unchanged authorized payloads, not a summary.

    Each source envelope is one actual invocation. Record identity/contradiction
    stays inside its payload; equal records from different sources are not merged.
    Only navigation paths, redundant metadata and disabled tool schemas change.
    """
    from llm.orchestration.investigation_support import walk,classify
    from llm.gateway_network import timestamp
    original=deepcopy(packet);rows=original.get('reader_results',[])
    boundary=deepcopy(original.get('retrieval_boundary',{}))
    sources=deepcopy(original.get('sources',[]))
    result={k:deepcopy(original[k]) for k in [
        'original_user_instruction','requested_clauses','owned_user_context',
        'scope','evidence_type_boundaries','omissions','continuation','advisory_context'] if k in original}
    result['packet_layout']={'version':'canonical_v1',
        'rule':'source_records payloads are unchanged authorized results, grouped by actual invocation. Record IDs and citations retain their original authority. Views are navigation, not new observations.'}
    result['sources']=sources
    result['source_records']=[{**{k:deepcopy(v) for k,v in row.items() if k!='data'},'payload':deepcopy(row.get('data'))} for row in rows]
    def path(value):
        if isinstance(value,str):
            for i in range(len(rows)):
                before='/reader_results/'+str(i)+'/data'
                if value==before or value.startswith(before+'/'):
                    return '/source_records/'+str(i)+'/payload'+value[len(before):]
        return value
    result['original_source_constraints']=boundary.pop('source_restrictions',{})
    bound={r.get('reader_receipt',{}).get('invocation_id') for r in rows}
    # Retain unbound/historical queries. Never guess which result they produced.
    unbound=[q for q in boundary.pop('executed_queries',[]) if not q.get('invocation_id') or q['invocation_id'] not in bound]
    if unbound:boundary['unbound_executed_queries']=unbound
    planning=deepcopy(original.get('planning_proposal_not_authority',{}))
    schemas=planning.pop('authorized_reader_schemas',None)
    if boundary.get('supplementary_permitted') is False or boundary.get('advisory_only'):
        for key in ['reader_schemas','guidance_schemas','reader_schema_refs','reader_guidance','query_defaults']:boundary.pop(key,None)
        boundary['capability_schemas_omitted']='No further tool proposal is permitted; actual published operation schemas in source payloads remain unchanged.'
    elif schemas and not boundary.get('reader_schemas') and not boundary.get('guidance_schemas'):
        boundary['reader_schemas']=schemas
    proposed=planning.get('proposed')
    if isinstance(proposed,dict) and proposed.get('goal')==original.get('original_user_instruction'):
        proposed.pop('goal')
        planning['goal_ref']='original_user_instruction'
    result['planning_proposal_not_authority']=planning
    result['retrieval_boundary']=boundary
    context=deepcopy(original.get('investigation_context',{}))
    network=context.pop('network',{})
    if isinstance(network,dict):
        # The canonical index already contains every observation path.
        network.pop('observation_record_paths',None)
        for observation in network.get('source_observations',[]):
            if 'record_path' in observation:observation['record_path']=path(observation['record_path'])
    relations=[]
    temporal={key:[] for key in ['running_observations','saved_artifacts','staged_artifacts','recorded_events','operational_observations']}
    index=[];operational_groups={}
    existing={entry.get('record_path'):entry for entry in original.get('record_identity_index',[])}
    work=[(row,'/reader_results/'+str(i)+'/data') for i,row in enumerate(rows)]
    prior=(original.get('advisory_context') or {}).get('prior_authorized_records',[])
    work.extend((row,'/advisory_context/prior_authorized_records/'+str(i)+'/data') for i,row in enumerate(prior))
    for row,base in work:
        for source_path,record in walk(row.get('data'),base):
            reference=path(source_path)
            entry=deepcopy(existing.get(source_path,{}))
            entry.update(id=record['id'],record_path=reference)
            entry.setdefault('classes',classify(record,row['tool']))
            index.append(entry)
            # Pointers expose actual directional/relationship structure without
            # copying or inventing an edge, owner, branch or numerical value.
            fields=[key for key in ['assessment','forward','return','routes','peer_parameters','endpoints','graph_path'] if key in record]
            if fields:relations.append({'record_id':record['id'],'record_path':reference,'fields':fields})
            kind=record.get('kind','');classes=classify(record,row['tool'])
            if kind=='running_configuration':bucket='running_observations'
            elif kind=='planned_configuration' or record.get('artifact_role')=='unapplied_staged':bucket='staged_artifacts'
            elif 'config_text' in record:bucket='saved_artifacts'
            elif 'event_record' in classes:bucket='recorded_events'
            elif 'operational_state' in classes:bucket='operational_observations'
            else:continue
            navigation={'record_id':record['id'],'record_path':reference,
                **{key:record[key] for key in ['device_id','interface_id','vrf','timestamp','captured_at'] if key in record}}
            if bucket=='operational_observations':
                identity=(record.get('device_id'),record.get('interface_id'),record.get('vrf'),kind)
                signature=tuple(str(record.get(key)) for key in ['admin_status','oper_status','state','status','observed_state'])
                operational_groups.setdefault(identity,[]).append((navigation,signature))
            else:temporal[bucket].append(navigation)
    # Repeated same-time equal observations are still distinct raw records,
    # but do not need a second timeline. Show temporal samples or conflicts.
    for group in operational_groups.values():
        times={(entry.get('timestamp'),entry.get('captured_at')) for entry,_ in group}
        if len(times)>1 or len({signature for _,signature in group})>1:
            temporal['operational_observations'].extend(entry for entry,_ in group)
    for values in temporal.values():
        def order(item):
            stamp=timestamp(item.get('timestamp') or item.get('captured_at'))
            return (str(item.get('device_id','')),str(item.get('interface_id','')),stamp.timestamp() if stamp else float('inf'),str(item['record_id']))
        values.sort(key=order)
    history=context.pop('artifact_history',{})
    for comparison in history.get('comparisons',[]):
        for operand in ['before','after']:
            if 'path' in comparison.get(operand,{}):comparison[operand]['path']=path(comparison[operand]['path'])
    temporal['artifact_comparisons']=history
    temporal['limits']='Record timestamps/capture fields retain source meanings. Views do not infer continuity, exact activation or physical causation.'
    result['temporal_view']=temporal
    result['relationship_view']={'network_context':network,'record_relationships':relations}
    result['claim_source_compatibility']=deepcopy(context.get('claim_source_compatibility',{}))
    result['record_index']=index
    result['source_types']=deepcopy(original.get('source_evidence_types',{}))
    ledger=original.get('evidence_requirement_ledger',{})
    result['source_dependencies']=deepcopy(ledger.get('dependencies',[]))
    result['unresolved_dependencies']=[d for d in result['source_dependencies'] if d.get('retrieval')=='NOT_RETRIEVED_LOCATION_UNKNOWN']
    # These contain the actual prior draft/correction, not another model's
    # summary. Keep them when present; empty duplicate envelopes add no facts.
    previous={k:context[k] for k in ['previous_draft','previous_review'] if context.get(k)}
    if previous:result['previous_draft']=previous
    return result



def settings():
    enabled=os.getenv('COGNISHIELD_AI_EVIDENCE_HARNESS','0')=='1' or os.getenv('COGNISHIELD_AI_COMPLETENESS','0')=='1'
    return {part:enabled and os.getenv('COGNISHIELD_AI_HARNESS_'+part.upper(),'1')=='1'
            for part in ('ledger','guidance','provenance')}


def records(value,path=''):
    if isinstance(value,dict):
        if 'id' in value and 'kind' in value:yield path,value
        for key,item in value.items():
            yield from records(item,path+'/'+str(key).replace('~','~0').replace('/','~1'))
    elif isinstance(value,list):
        for i,item in enumerate(value):yield from records(item,path+'/'+str(i))


def coverage(packet):
    """Only receipt coverage; clause relevance beyond explicit names is unknown."""
    from development.source_registry import BY_KEY,explicit_read_sources
    from llm.gateway_network import route_network,explicit_configuration_scope,explicit_topology_scope
    rows=packet['reader_results'];policy=packet['retrieval_boundary']['source_restrictions']
    index=list(records(rows,'/reader_results'));known={r['id'] for _,r in index}
    dependencies=[]
    for path,row in index:
        # Existing typed dependency lists and explicitly named event references.
        # Never extract IDs or targets from free-text messages/configuration.
        refs=[(ref,'depends_on') for ref in row.get('depends_on',[]) if isinstance(ref,str)]
        if isinstance(row.get('change_event_ref'),str):refs.append((row['change_event_ref'],'change_event_ref'))
        gaps={r['record_ref']:r for r in row.get('unavailable_dependencies',[]) if isinstance(r,dict) and 'record_ref' in r}
        for ref,field in refs:
            dependencies.append({'record_path':path,'from_record':row['id'],'reference':ref,'field':field,
                'retrieval':'RETRIEVED' if ref in known else 'SOURCE_UNAVAILABLE' if ref in gaps else 'NOT_RETRIEVED_LOCATION_UNKNOWN',
                **({'source_category':gaps[ref].get('source_category'),'status':gaps[ref].get('status')} if ref in gaps else {})})
    receipts=[]
    for i,row in enumerate(rows):
        data=row.get('data') or {};data=data if isinstance(data,dict) else {}
        actual=[r['id'] for _,r in records(row.get('data'))]
        receipts.append({'row':i,'reader':row.get('tool'),'receipt_ids':row.get('evidence_ids',[]),
            'records':actual,'source_statuses':data.get('source_statuses',{}),
            'availability':'SOURCE_UNAVAILABLE' if data.get('source_available') is False else
                'EVIDENCE_AVAILABLE' if actual else 'RETRIEVED_NO_TYPED_RECORDS',
            'source_available':data.get('source_available'),'truncated':data.get('truncated',False)})
    clauses=[]
    for clause in packet['requested_clauses']:
        categories=explicit_read_sources('Read '+clause['text'],BY_KEY)
        readers={reader for key in categories for reader in BY_KEY[key].readers}
        # Reuse the current gateway's source aliases as well as exact catalog
        # titles ("saved configuration" is not a literal catalog title).
        domains=set(route_network(clause['text'],{'devices':[]},expand_investigation=False)[0])-{'inventory'}
        readers.update('knowledge.search' if d=='knowledge' else 'network.'+d for d in domains)
        linked=[r['row'] for r in receipts if not readers or r['reader'] in readers]
        missing=sorted(readers-{r['reader'] for r in receipts})
        clauses.append({'id':clause['id'],'original_outcome':clause['text'],
            'binding':'EXPLICIT_SOURCE_NAME_ONLY' if readers else 'REQUEST_SCOPE_RELATIONSHIP_UNKNOWN',
            'receipt_rows':linked,'explicit_categories':categories,'not_queried_readers':missing,
            'prohibited_readers':[name for name in missing if (domain:=('knowledge' if name=='knowledge.search' else name.removeprefix('network.'))) in policy.get('denied',[]) or
                policy.get('allowed') is not None and domain not in policy['allowed']],
            'coverage':'PARTIALLY_RETRIEVED' if missing and linked else 'SOURCE_NOT_QUERIED' if missing else
                'RECEIPTS_PRESENT_NOT_SEMANTIC_SUPPORT' if linked else 'NO_CURRENT_RECEIPTS',
            'targets':packet.get('planning_proposal_not_authority',{}).get('resolved_device_refs',[]),
            'temporal_scope':{**policy.get('source_scopes',{}),
                **({'configuration':explicit_configuration_scope(clause['text'])} if 'network.configuration' in readers else {}),
                **({'topology':explicit_topology_scope(clause['text'])} if 'network.topology' in readers else {})}})
    return {'authority':'Retrieval/availability only. No clause or conclusion is semantically certified.',
        'outcomes':clauses,'receipts':receipts,'dependencies':dependencies,'restrictions':policy}


BOUNDARIES={
    'modeled':'Declared calculation, not measured traffic distribution or physical certification.',
    'planned':'Design intent; not evidence of deployment, operational connectivity or delivery.',
    'saved':'Saved artifact; not automatically an earlier running state or a change-event window.',
    'current':'Current capture at its recorded time/context; not continuous observation.',
    'historical':'Historical point/record; transition, actor and event timing require their own evidence.',
    'observed':'Recorded observation within its stated source and time scope.',
    'unknown':'Source type not established by the typed metadata.',
}


def enrich(packet):
    """Mutate metadata only; caller already scrubbed raw source leaves."""
    enabled=settings()
    if enabled['ledger']:packet['evidence_requirement_ledger']=coverage(packet)
    if enabled['provenance']:
        by_path={p:r for p,r in records(packet['reader_results'],'/reader_results')}
        for entry in packet['record_identity_index']:
            row=by_path.get(entry['record_path'],{});kind=row.get('kind')
            classes=[]
            if row.get('derived') is True or kind in {'forwarding_assessment','protocol_assessment','metric_series'}:classes.append('modeled')
            if kind=='planned_links':classes.append('planned')
            elif kind in {'configuration','configuration_snapshot'}:classes.append('saved')
            elif kind=='running_configuration':classes.append('current')
            elif row.get('current') is False:classes.append('historical')
            elif kind in {'interface_state','observed_link','routing_table','protocol_observation','syslog_event','metric_sample','interface_counters'}:classes.append('observed')
            entry['evidence_type']=classes or ['unknown']
            # Origin is a separate dimension: authored observations in a
            # simulation still cannot become physical observations.
            source_row=packet['reader_results'][int(entry['record_path'].split('/')[2])]
            data=source_row.get('data') or {}
            entry['origin_scope']=(data.get('scenario') or {}).get('origin','unknown') if isinstance(data,dict) else 'unknown'
        packet['source_evidence_types']=[{'row':i,'type':'unavailable' if data.get('source_available') is False else
            'planned' if data.get('topology_kind')=='planned' else 'observed' if data.get('topology_kind')=='observed' else 'unknown',
            'origin':(data.get('scenario') or {}).get('origin','unknown')}
            for i,row in enumerate(packet['reader_results']) if isinstance(data:=row.get('data'),dict)]
        packet['evidence_type_boundaries']=BOUNDARIES
    if enabled['guidance']:
        # The enhanced packet exposes schemas once, only for validated hints.
        # Original plan/needs remain; duplicate raw candidate JSON is unchanged.
        plan=deepcopy(packet['planning_proposal_not_authority']);plan.pop('authorized_reader_schemas',None)
        packet['planning_proposal_not_authority']=plan
        packet['retrieval_boundary'].pop('reader_schemas',None)
        hints=packet['retrieval_boundary'].setdefault('reader_guidance',[])
        schemas={}
        for hint in hints:
            if 'input_schema' in hint:schemas[hint['reader']]=hint.pop('input_schema')
        packet['retrieval_boundary']['guidance_schemas']=schemas
        packet['retrieval_boundary']['guidance_authority']='Possible queries only; no execution or guarantee of missing facts. Other proposals still require backend validation.'
    return packet


def guidance(state,inventory,registry,allowed_tools,executed_queries):
    from llm.orchestration.role_reasoning import validate_additional
    from llm.gateway_network import explicit_configuration_scope,explicit_topology_scope
    from llm.orchestration.request_contract import advisory_contract,response_obligations,reader_constraints
    from development.source_registry import BY_KEY
    if not settings()['guidance'] or advisory_contract(state.request):return []
    packet={'reader_results':state.results,'requested_clauses':response_obligations(state.request,include_actions=True) or [{'id':'request-1','text':state.request}],
        'retrieval_boundary':{'source_restrictions':reader_constraints(state.request)}}
    ledger=coverage(packet);candidates=[]
    for dep in ledger['dependencies']:
        if dep['retrieval']!='NOT_RETRIEVED_LOCATION_UNKNOWN':continue
        # A typed event reference suggests event-capable catalog entries, not
        # an invented location or an ID-prefix heuristic. Location stays unknown.
        if dep['field']=='change_event_ref':
            for key in ('syslog','config_changes'):
                source=BY_KEY[key]
                candidates.append((source.tool,{'device_refs':state.device_refs,'source_categories':[key]},dep['reference']))
    for need in state.route.planning.get('role_information_needs',[]):
        if need.get('necessity','required')!='required':continue
        name={'inventory':'inventory.read','knowledge':'knowledge.search'}.get(need['domain'],'network.'+need['domain'])
        args={'device_refs':state.device_refs,**{k:need[k] for k in ('source_scope','source_categories') if k in need}}
        if args.get('source_scope','auto')=='auto' and name in {'network.configuration','network.topology'}:
            args['source_scope']=(explicit_configuration_scope if name.endswith('configuration') else explicit_topology_scope)(need.get('question',''))
        if args.get('source_scope','auto')=='auto' and not args.get('source_categories') and any(r['tool']==name for r in executed_queries):continue
        if name!='inventory.read':candidates.append((name,args,'Original required information need; relevance remains a proposal'))
    hints=[]
    unavailable={category for row in ledger['receipts'] for category,status in row['source_statuses'].items() if status not in {'AVAILABLE','STALE','CONFLICTING'}}
    unavailable_readers={row['reader'] for row in ledger['receipts'] if row['source_available'] is False and not row['source_statuses']}
    for name,args,gap in candidates:
        if len(hints)>=3:break
        if name in unavailable_readers:continue
        if set(args.get('source_categories',[])) & unavailable:continue
        proposal={'reader':name,'parameters':args,'gap':gap,'why':'May resolve an unretrieved reference or original information need','evidence_refs':[]}
        valid,_=validate_additional({'additional_reads':[proposal]},state,inventory,registry,allowed_tools,executed_queries=executed_queries)
        if not valid:continue
        q=valid[0]
        if any(h['reader']==name and h['parameters']==q['parameters'] for h in hints):continue
        cap=registry.capability(name)
        if cap.availability is not None and not cap.availability():continue
        hints.append({'reader':name,'parameters':q['parameters'],'possible_gap':gap,
            'information':[BY_KEY[key].title for key in args.get('source_categories',[])],
            'input_schema':cap.input_model.model_json_schema(),'availability':'NOT_QUERIED_NOT_GUARANTEED'})
    return hints
