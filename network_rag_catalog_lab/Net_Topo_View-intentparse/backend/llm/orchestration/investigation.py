"""Evidence-driven bounded planning and conservative, inspectable conclusions."""
import re
from llm.gateway_routing import SemanticRoute

NETWORK = ['inventory','topology','configuration','telemetry','syslog','incidents']


def contextual_route(prompt,memory,previous,inventory):
    """Resolve investigation references from records, not an assistant narrative."""
    follow=bool(re.search(r'\b(evidence supports|your conclusion|other relevant|other sources|could the problem|what changed|most likely cause|check next|reassess|back up|now investigate|continue (?:the |my |this )?investigation|resume (?:the |my |this )?investigation)\b',prompt,re.I))
    if follow and memory.goal and memory.domains:
        resolved=[]
        for ref in memory.device_refs:
            matches=[d for d in inventory['devices'] if ref.casefold() in {str(d['id']),d['hostname'].casefold(),str(d.get('management_ip') or '').casefold(),*[a.casefold() for a in d.get('aliases',[])]}]
            if len(matches)!=1:
                return SemanticRoute(intent='clarify',question='A previously referenced device is no longer recorded uniquely. Which device should I investigate?')
            resolved.append(str(matches[0]['id']))
        from llm.gateway_network import route_network
        current_query=route_network(prompt,inventory)[1]
        explicit=current_query.get('device_refs',[])
        # The old goal supplies conversational purpose, not competing dates.
        # Entity references are separately rebound above; new explicit time
        # bounds must be parsed only from the latest instruction.
        current_window=any(key in current_query for key in ('start','end','window_minutes'))
        return SemanticRoute(intent='answer',use_history=True,device_refs=explicit or list(dict.fromkeys(resolved)),
            interface_refs=memory.interface_refs,attributes=memory.attributes,
            network_domains=memory.domains,network_request=prompt if current_window else memory.goal+'\nFollow-up: '+prompt,
            source_requests={} if re.search(r'\b(other (?:relevant )?(?:information )?sources|all available sources)\b',prompt,re.I) else memory.source_requests)
    if re.search(r'\b(uploaded|attached|pdf|page\s+\d+)\b',prompt,re.I) and re.search(r'\b(compare|explain|check|read|investigate)\b',prompt,re.I) and not re.search(r'\b(generate|create|modify|deploy|apply)\b',prompt,re.I):
        from llm.gateway_network import route_network
        domains,query=route_network(prompt,inventory)
        if query.get('device_refs') and domains:
            return SemanticRoute(intent='analyze_files',use_attachments=True,network_domains=domains,
                device_refs=query['device_refs'],network_request=prompt)
    # Published engineering explanations are reads, even when an operation's
    # name contains "configure". V9 still selects and defines the operation.
    from llm.gateway_references import published_knowledge_read
    published=published_knowledge_read(prompt,inventory)
    if published:return SemanticRoute(intent='explain',**published)
    return None


def is_investigation(prompt):
    return bool(re.search(r'\b(investigat\w*|diagnos\w*|troubleshoot\w*|cannot communicate|root cause|other relevant|other sources)\b|\b(?:find|identify|determine)\b.{0,60}\b(?:cause|fault|reason)\b|\b(?:assess|evaluate|verify|check)\b.{0,100}\b(?:modeled|modelled|forwarding|connectivity|reachability|return|reverse)\b',prompt,re.I))


def initial_domains(route,prompt):
    domains=list(route.network_domains)
    # For an open investigation first inspect structure and saved context.
    # Explicitly requested tools remain in the first round.
    if is_investigation(prompt) and len(domains)>=5 and not re.search(r'\b(telemetry|measurements|syslogs?|logs|incidents|all (?:available )?(?:sources|evidence))\b',prompt,re.I):
        return [d for d in ['inventory','topology','configuration'] if d in domains]
    return domains


def records(data):
    if not isinstance(data,dict):return []
    return list(data.get('records',[]))+[r for s in data.get('sources',[]) for r in records(s.get('data'))]


def assess(context,evidence):
    from llm.orchestration.scenario_reasoning import assess_scenario
    development=assess_scenario(context,evidence)
    if development:return development
    gaps=[];warnings=[];conflicts=[];origins=sorted({e.origin for e in evidence})
    for item in context:
        data=item.get('data') or {}
        if item['status']!='success':gaps.append(item['tool']+' is unavailable or incomplete')
        elif isinstance(data,dict) and (data.get('truncated') or data.get('excerpt')):gaps.append(item['tool']+' returned only an excerpt')
        elif item['tool'].startswith('network.') and item['tool']!='network.topology' and not records(data):
            gaps.append(item['tool']+' has no matching recorded observations')
    if not any(e.origin=='live' and e.freshness=='fresh' for e in evidence):
        gaps.append('Fresh live connectivity measurements are not available; a current failure or root cause is unconfirmed')
    if any(e.freshness=='stale' for e in evidence):warnings.append('Historical or stale records cannot establish current network state')
    if any(o in origins for o in ['simulated','sample']):warnings.append('Simulated/sample records are examples, not live measurements')
    # Compare only explicit interface/address pairs in Cisco-style saved text.
    # Absence of a command is never treated as a fault or compliance result.
    addresses={}
    for item in context:
        if item['tool']=='inventory.read' and isinstance(item.get('data'),dict):
            for d in item['data'].get('devices',[]):
                for interface in d.get('interfaces',[]):
                    addresses[(str(d['id']),interface['name'])]=str(interface.get('ip_address') or '').split('/')[0]
    for item in context:
        if item['tool']!='network.configuration':continue
        for row in records(item.get('data')):
            interface=None
            for line in row.get('config_text','').splitlines():
                match=re.match(r'^interface\s+(\S+)\s*$',line)
                if match:interface=match[1]
                match=re.match(r'^\s+ip address\s+(\d+\.\d+\.\d+\.\d+)\b',line)
                key=(str(row.get('device_id')),interface)
                if match and addresses.get(key) and addresses[key]!=match[1]:
                    conflicts.append('Saved configuration and inventory disagree about an interface address; neither establishes the current running configuration')
    seen={}
    for item in context:
        if item['tool']!='network.telemetry':continue
        for row in records(item.get('data')):
            key=(str(row.get('device_id',row.get('device'))),row.get('interface'),row.get('time',row.get('timestamp')),row.get('field'))
            if key[-2] and 'value' in row:
                if key in seen and seen[key]!=row['value']:conflicts.append('Telemetry records disagree for the same device, metric and timestamp')
                seen[key]=row['value']
    return {'gaps':list(dict.fromkeys(gaps)),'warnings':list(dict.fromkeys(warnings)),
        'conflicts':list(dict.fromkeys(conflicts)),'origins':origins,'conclusion_status':'insufficient_for_confirmed_root_cause'}


def additional_domains(state,assessment):
    read={item['tool'].removeprefix('network.').replace('inventory.read','inventory').replace('knowledge.search','knowledge') for item in state.results}
    desired=state.route.network_domains
    resolved=assessment.get('conclusion_status') in {'healthy_within_tested_scope','confirmed_within_scenario'}
    explicitly_more=re.search(r'\b(?:other (?:relevant )?(?:information )?sources|more evidence|cross[- ]check|all available sources)\b',state.request,re.I)
    if resolved and not assessment.get('conflicts') and not explicitly_more and set(desired)<=read:
        # Preserve declared scope. An unmodeled prerequisite of an unrelated
        # protocol is not a reason to retrieve every source after a scoped
        # forwarding calculation already establishes the requested outcome.
        return []
    if is_investigation(state.request) or is_investigation(state.memory.get('goal','')):
        # Broaden an open investigation only when actual results expose gaps,
        # conflicts or historical/simulated context. Explicit requested sources
        # still run, even when they cannot establish live conditions.
        if assessment['gaps'] or assessment['conflicts'] or assessment['warnings']:
            desired=list(dict.fromkeys(desired+NETWORK+(['state'] if assessment.get('development') else [])))
    # A failed direct reader does not make unrelated inventory attributes
    # relevant. Device identity is already resolved/authorized by the gateway;
    # inventory cannot replace unavailable logs, incidents or measurements.
    return [d for d in desired if d not in read]


def conclusion_text(assessment,context,evidence=()):
    if assessment.get('development'):
        from llm.orchestration.scenario_reasoning import scenario_text
        return scenario_text(assessment,evidence)
    lines=['**Investigation assessment**','The returned records do not establish a current connectivity failure or a confirmed root cause.']
    labels={e.id:'S'+str(n+1) for n,e in enumerate(evidence)}
    for item in context:
        if item['tool']!='network.topology' or item['status']!='success':continue
        path=(item.get('data') or {}).get('graph_path')
        if isinstance(path,list) and path:
            citation=' '.join('['+labels[e]+']' for e in item.get('evidence_ids',[]) if e in labels)
            lines.append('Recorded graph path: '+' → '.join('`'+str(name)+'`' for name in path)+'. '+citation)
    lines.extend('- '+s+'.' for s in assessment['conflicts'])
    unavailable=[{'network.state':'interface, routing and protocol observations','network.telemetry':'telemetry','network.syslog':'syslogs','network.incidents':'incident observations','network.configuration':'current configuration evidence'}.get(item['tool'],item['tool'])
        for item in context if item['status']!='success']
    if unavailable:lines.append('Unavailable sources: '+', '.join(dict.fromkeys(unavailable))+'.')
    if any(isinstance(item.get('data'),dict) and item['data'].get('truncated') for item in context):
        lines.append('Some returned sources are bounded excerpts; omitted records were not assessed.')
    if assessment['warnings']:lines.append('Historical captures and simulated/sample events do not establish the present physical network state.')
    if any(i['tool']=='network.topology' for i in context):lines.append('The topology describes recorded relationships; it is not a packet-reachability test.')
    lines.append('Useful next evidence: timestamped interface/link state, routing adjacency and route-table observations from the affected time window. These would test link or routing hypotheses; no collection or device action was performed.')
    lines.append('Expand **Retrieved records** to inspect the authorized source records and their timestamps.')
    return '\n\n'.join(lines)


def knowledge_text(context,evidence=()):
    labels={item.id:'S'+str(i+1) for i,item in enumerate(evidence)}
    parts=[]
    for item in context:
        if item['tool']!='knowledge.search':continue
        rows=item.get('data') or []
        if not isinstance(rows,list):continue
        if item.get('status')!='success' or not rows:
            parts.append('Published requirements could not be retrieved for this request. No operation fields were inferred.')
            references=[e for e in evidence if e.id in item.get('evidence_ids',[]) and e.source=='development.knowledge_reference']
            if references:
                parts.append((item.get('message') or 'The selected scenario reference did not return an active published method.')+
                    ' '+' '.join('Reference source captured `'+str(e.captured_at)+'`. ['+labels[e.id]+']' for e in references))
            continue
        for row in rows:
            requirement=row.get('published_requirements')
            if not requirement:continue
            for operation in requirement.get('operations',[]):
                schema=operation['schema'];required=schema.get('required',[])
                source=next((r for r in rows if r.get('source')=='published:'+operation['operation_id']),row)
                label=labels.get(source.get('evidence_id'))
                citation=' ['+label+']' if label else ''
                parts.append('**Published '+operation['operation_id']+' requirements**'+citation+'\n\n'+operation['description']+'\n\nRequired parameters: '+(', '.join('`'+v+'`' for v in required) or 'none in the base schema')+'.')
                nested=[]
                def required_paths(node,path=''):
                    if not isinstance(node,dict):return
                    nested.extend(path+'.'+name for name in node.get('required',[]) if path)
                    for key,value in node.get('properties',{}).items():required_paths(value,path+'.'+key if path else key)
                    if 'items' in node:required_paths(node['items'],path+'[]')
                required_paths(schema)
                if nested:parts.append('Required nested fields: '+', '.join('`'+name+'`' for name in nested)+'.')
                vendor_required=schema.get('x-required-by-vendor',{})
                if vendor_required:parts.append('Additional vendor requirements: '+ '; '.join(k+': '+', '.join(v) for k,v in vendor_required.items())+'.')
                parts.append('Published native profiles: '+ '; '.join(p['vendor']+'/'+p['platform']+' ('+', '.join(str(v) for v in p['versions'])+')' for p in operation['profiles'])+'.')
        if not any(r.get('published_requirements') for r in rows):
            parts.append('Published schema requirements were unavailable. Retrieved reference prose is not an authoritative operation contract.')
    if parts and any(i['tool']=='network.configuration' for i in context):
        configs=[r for i in context if i['tool']=='network.configuration' for r in records(i.get('data'))]
        is_ospf=any('ospf' in o.get('operation_id','') for i in context if i['tool']=='knowledge.search' and isinstance(i.get('data'),list) for d in i['data'] for o in d.get('published_requirements',{}).get('operations',[]))
        found=any('ospf' in r.get('config_text','').lower() for r in configs)
        comparison=('OSPF text occurs in the returned saved captures; this alone does not validate the published parameters.' if found else 'No OSPF text was found in the returned saved excerpts. This is not proof of its absence on the device.') if is_ospf else 'The returned saved text is shown below for comparison with these parameter requirements.'
        parts.append(comparison+' A saved capture is configuration text, not the operation parameter object. Compatibility and semantic compliance were not validated; no generation was requested or performed.')
    return '\n\n'.join(parts)
