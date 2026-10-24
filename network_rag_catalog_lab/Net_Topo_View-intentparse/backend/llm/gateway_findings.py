"""Deterministic release boundary for investigations with no observations."""


def cell(value):
    return str(value if value is not None and value!='' else 'Not recorded').replace('|','\\|').replace('\n',' ')


def table(headers, rows):
    return '| '+' | '.join(headers)+' |\n|'+'|'.join('---' for _ in headers)+'|\n'+'\n'.join('| '+' | '.join(cell(v) for v in row)+' |' for row in rows)


def interface_subnet(interface):
    """Calculate only from an explicit stored prefix/mask; no default masks."""
    import ipaddress
    address=interface.get('prefix') or interface.get('ip_address')
    if not address:return 'Not recorded'
    if '/' not in address:
        mask=interface.get('subnet_mask')
        if not mask:return 'Not recorded'
        address=address+'/'+str(mask)
    try:return str(ipaddress.ip_interface(address).network)
    except ValueError:return 'Stored prefix or mask is invalid'


def inventory_answer(data, attrs=(), interface_refs=()):
    devices=data.get('devices',[])
    if 'interfaces' in attrs or 'prefixes' in attrs or interface_refs:
        ports=[(d,i) for d in devices for i in d['interfaces'] if not interface_refs or str(i['id']) in interface_refs]
        answer=('**'+cell(devices[0]['hostname'])+'** has '+str(len(ports))+' matching recorded interface(s):\n\n' if len(devices)==1 else 'Recorded interfaces:\n\n')
        if len(ports)<=8:
            lines=[]
            for d,i in ports:
                label=('**'+cell(d['hostname'])+'** · ' if len(devices)>1 else '')+'`'+cell(i['name'])+'`'
                if 'prefixes' in attrs:detail='subnet `'+interface_subnet(i)+'` · address `'+cell(i.get('prefix') or i.get('ip_address'))+'`'
                else:detail='`'+cell(i.get('prefix') or i.get('ip_address'))+'`'
                lines.append('- '+label+' — '+detail)
            answer+='\n'.join(lines) if lines else 'No matching interfaces are recorded.'
        else:
            rows=[(d['hostname'],i['name'],interface_subnet(i) if 'prefixes' in attrs else i.get('prefix') or i.get('ip_address'),i.get('interface_type')) for d,i in ports]
            answer+=table(['Device','Interface','Subnet' if 'prefixes' in attrs else 'IP address','Type'],rows[:100])
        rows=ports
        if len(rows)>100:answer+='\n\nOnly the first 100 interfaces are shown.'
        if 'management_address' in attrs:
            answer+='\n\n'+ '\n'.join('**'+cell(d['hostname'])+' management IP:** `'+cell(d.get('management_ip'))+'`.' for d in devices)
            answer+=' These are the device management records, distinct from the interface address records above.'
    else:
        fields=[('hostname','Device')]
        columns={'addresses':('management_ip','Management address'),'vendor':('vendor','Vendor'),
            'model':('model','Model'),'os_version':('os_version','OS version'),'role':('role','Role'),
            'site':('site','Site'),'status':('status','Recorded status')}
        fields += [columns[a] for a in attrs if a in columns]
        if len(fields)==1:fields += [columns[a] for a in ['vendor','addresses','role']]
        if len(devices)==1 and attrs and len(fields)<=4:
            device=devices[0]
            details=[label+': **`'+cell(device.get(key))+'`**' for key,label in fields[1:]]
            answer='**'+cell(device['hostname'])+'** — '+ '; '.join(details)+'.'
        else:
            answer=f"The stored inventory contains {data.get('summary',{}).get('device_count',len(devices))} matching device(s).\n\n"
            if devices:answer+=table([label for _,label in fields],[[d.get(key) for key,_ in fields] for d in devices[:100]])
    if data.get('unresolved_devices'):answer+='\n\nUnresolved device references: '+', '.join(data['unresolved_devices'])
    if data.get('truncated'):answer+='\n\nThe returned inventory is partial.'
    if data.get('scenario'):
        answer=answer.replace('Stored interface inventory','Development interface inventory').replace('The stored inventory','The development inventory')
        source=data.get('inventory_source',{})
        if source.get('captured_at'):
            answer+='\n\nSimulated inventory captured at `'+str(source['captured_at'])+'`'+(' · **STALE**' if source.get('status')=='STALE' else '')+'.'
        return answer
    return answer


def literal_configuration_section(text,question):
    """Bounded literal command excerpts, not effective vendor configuration parsing."""
    import re
    match=re.search(r'\b(ACL|OSPF|BGP)\s+(?:section|stanza|block|lines)\b',question,re.I)
    if not match:return None
    topic=match[1].upper()
    patterns={'ACL':r'^(?:ip(?:v6)? access-list\b|access-list\b|acl\b|set firewall\b|firewall\s*\{)',
        'OSPF':r'^(?:router ospf\b|ospf\b|set protocols ospf\b)',
        'BGP':r'^(?:router bgp\b|bgp\b|set protocols bgp\b)'}
    lines=text.splitlines();selected=set()
    for start,line in enumerate(lines):
        if not re.search(patterns[topic],line.lstrip(),re.I):continue
        selected.add(start)
        if line.lstrip().startswith(('set ','access-list ')):continue
        indentation=len(line)-len(line.lstrip());balance=line.count('{')-line.count('}')
        for index in range(start+1,len(lines)):
            current=lines[index]
            if balance>0:
                selected.add(index);balance+=current.count('{')-current.count('}')
                if balance<=0:break
            elif current.strip() and len(current)-len(current.lstrip())>indentation:selected.add(index)
            elif not current.strip():continue
            else:break
    return topic,'\n'.join(lines[index] for index in sorted(selected))


def network_answer(context, evidence, attrs=(), interface_refs=(), *, question=''):
    """Present exact factual records without asking a prose model to recreate them.

    No root-cause assertion is inferred from counts, simulated events or absent
    observations. Advanced hypothesis generation remains a separate workflow.
    """
    labels={e.id:'S'+str(i+1) for i,e in enumerate(evidence)}
    devices={str(d['id']):d['hostname'] for item in context if item['tool']=='inventory.read'
             for d in (item.get('data') or {}).get('devices',[])}
    devices.update({str(d['id']):d['hostname'] for item in context for d in item.get('scope_devices',[])})
    sections=[]
    for item in context:
        data=item.get('data') or {};tool=item['tool']
        if tool=='knowledge.search':
            # Published reads return typed document lists, not network envelopes.
            from llm.orchestration.investigation import knowledge_text
            if text:=knowledge_text([item],evidence):sections.append(text)
            continue
        citations=' '.join('['+labels[ref]+']' for ref in item.get('evidence_ids',[]) if ref in labels)
        if data.get('excerpt'):
            sections.append('The '+tool.removeprefix('network.').replace('inventory.read','inventory')+' reader returned more content than this response can safely display. The returned context is partial; narrow the device or time scope. '+citations)
            continue
        if tool=='inventory.read':
            if item['status']!='success':
                sections.append((item.get('message') or 'Inventory records are unavailable from this reader.')+' '+citations)
                continue
            explanation=''
            if 'provenance' in attrs:
                explanation='These values are read directly from **'+('the selected simulated inventory records' if data.get('scenario') else 'stored inventory records')+'**. This lookup does not derive interface names or addresses from topology links. '+citations+'\n\n'
            sections.append(explanation+inventory_answer(data,attrs,interface_refs)+' '+citations);continue
        if tool=='network.topology':
            if data.get('topology_kind')=='planned':
                rows=[[r['source'],r['source_interface'],r['target'],r['target_interface']] for r in data.get('links',[])]
                status=data.get('source_statuses',{}).get('topology_planned')
                capture=data.get('source_captures',{}).get('topology_planned')
                provenance=('\n\nSource status: **'+status+'**.' if status else '')+(' Captured at `'+capture+'`.' if capture else '')
                if item['status']!='success':
                    sections.append('**Planned topology** '+citations+'\n\nThe selected planned-topology reader is unavailable. '+(item.get('message') or '')+provenance+'\n\nThis does not establish that the network has no planned links.')
                    continue
                sections.append('**Planned topology** '+citations+'\n\n'+(table(['Device','Interface','Peer','Peer interface'],rows) if rows else 'No planned links match this scope.')+provenance+
                    ('\n\nRecorded graph path: '+' → '.join(data['graph_path']) if data.get('graph_path') else '')+'\n\nLinks describe planned connections; they are not a complete interface inventory or measured packet reachability.')
            else:
                observations=[r for r in data.get('records',[]) if r.get('link_endpoints')]
                lines=[]
                for row in observations[:12]:
                    ends=row['link_endpoints']
                    left='**'+str(ends.get('source','unknown device'))+'**'+(' `'+ends['source_interface']+'`' if ends.get('source_interface') else '')
                    right='**'+str(ends.get('target','unknown device'))+'**'+(' `'+ends['target_interface']+'`' if ends.get('target_interface') else '')
                    lines.append('- '+left+' ↔ '+right+' — '+str(row.get('discovery_protocol','recorded neighbor'))+', '+str(row.get('oper_status','state unknown'))+'; recorded '+str(row.get('timestamp','time unavailable'))+'. '+citations)
                title='Historical topology observations' if data.get('topology_kind')=='historical' else 'Observed topology'
                text='\n'.join(lines) if lines else 'No matching endpoint observations were returned.'
                if item['status']!='success':
                    scope=', '.join(cell(d['hostname']) for d in item.get('scope_devices',[]) if d.get('hostname'))
                    text=('For '+scope+': ' if scope else '')+'The selected topology reader is unavailable. '+(item.get('message') or '')+' This does not establish the absence of a connection.'
                # Source capture time and historical event time are separate.
                # Deterministic history answers must retain the same reader
                # status that model-synthesized answers are required to disclose.
                for category,status in data.get('source_statuses',{}).items():
                    capture=data.get('source_captures',{}).get(category)
                    text+='\n\nSource `'+cell(category)+'`: **'+cell(status)+'**'+(' · captured `'+cell(capture)+'`' if capture else '')+'.'
                if len(observations)>12:text+='\n\nShowing12 of'+str(len(observations))+' returned relationships.'
                if observations and any(row.get('endpoint_basis')=='planned_link_reference' for row in observations):
                    text+='\n\nSome endpoint identities are referenced from planned-link records; the observation does not independently establish those endpoint names.'
                sections.append('**'+title+'** '+citations+'\n\n'+text+'\n\nThese are recorded neighbor relationships, not a complete interface inventory or a packet-reachability test.')
            continue
        title={'network.state':'Routing, interface and scoped test observations','network.configuration':'Recorded configurations','network.syslog':'Syslogs','network.telemetry':'Measurements','network.incidents':'Incident history'}.get(tool)
        if not title:continue
        parts=['**'+title+'** '+citations]
        sources=data.get('sources',[{'data':data,'status':item['status'],'origin':next((e.origin for e in evidence if e.id in item.get('evidence_ids',[])),'unavailable')}])
        for source in sources:
            payload=source.get('data') or {}; records=payload.get('records',[]);origin=source.get('origin','unavailable')
            if tool=='network.configuration':
                for category,status in payload.get('source_statuses',{}).items():
                    parts.append('Source `'+cell(category)+'`: **'+cell(status)+'** · captured '+cell(payload.get('source_captures',{}).get(category))+'.')
            if not records:
                state=('Access denied; requested information is unavailable' if source.get('status')=='denied'
                    else 'Reader failed; requested information is unavailable' if source.get('status')=='error'
                    else 'No matching records were returned' if source.get('status')=='success'
                    else 'Requested information is unavailable')
                scope=', '.join(cell(d['hostname']) for d in item.get('scope_devices',[]) if d.get('hostname'))
                parts.append(('For '+scope+': ' if scope else '')+state+(' ('+origin+')' if origin!='unavailable' else '')+'.');continue
            parts.append(str(len(records))+' returned record(s) · '+origin+'.')
            if tool=='network.configuration':
                for row in records[:3]:
                    if row.get('kind') in {'configuration_change','configuration_drift'} and isinstance(row.get('diff'),str):
                        label='Recorded drift comparison for ' if row.get('kind')=='configuration_drift' else 'Recorded change for '
                        parts.append('**'+label+cell(row.get('hostname') or row.get('device_id'))+'** · '+cell(row.get('timestamp'))+'.')
                        if row.get('kind')=='configuration_drift' and isinstance(row.get('drift_detected'),bool):
                            parts.append('The recorded literal comparison '+('reports a difference' if row['drift_detected'] else 'reports no difference')+'; it does not establish an intervening change event or device validation.')
                        if row.get('change_summary'):parts.append(cell(row['change_summary']))
                        parts.append('Saved capture: `'+cell(row.get('saved_record_id'))+'` · current capture: `'+cell(row.get('current_record_id'))+'`.')
                        diff=row['diff'][:4500];fence='```' if '```' not in diff else '~~~~'
                        parts.append(fence+'diff\n'+diff+'\n'+fence if diff else 'The supplied diff contains no lines.')
                        if len(row['diff'])>4500:parts.append('Diff excerpt limited to 4,500 characters; the source record retains the full comparison.')
                        if row.get('semantic_or_device_validation'):parts.append('Recorded validation: `'+cell(row['semantic_or_device_validation'])+'`.')
                        if row.get('unavailable_dependencies'):parts.append('Some referenced captures are unavailable; this recorded comparison is not independent confirmation of those missing sources.')
                        continue
                    if 'config_text' not in row:
                        values={k:v for k,v in row.items() if k not in {'id','device_id','interface_id','source_category','depends_on','source','current','freshness'}}
                        parts.append('Recorded '+cell(row.get('kind'))+' · '+cell(row.get('timestamp'))+': '+cell(values)+'.')
                        continue
                    selected=literal_configuration_section(row['config_text'],question)
                    text=(selected[1] if selected else row['config_text'])[:4500]; fence='```' if '```' not in text else '~~~~'
                    if selected and not text:
                        parts.append('Device '+cell(row.get('hostname') or devices.get(str(row['device_id'])) or str(row['device_id']))+' · '+cell(row.get('captured_at') or row.get('timestamp'))+'. No literal '+selected[0]+' section marker was found in this returned capture. This bounded marker lookup does not establish that the device has no such configuration. '+citations)
                        continue
                    parts.append('Device '+cell(row.get('hostname') or devices.get(str(row['device_id'])) or str(row['device_id']))+' · '+cell(row.get('captured_at') or row.get('timestamp'))+' · '+cell(('current simulated running configuration' if row.get('current') else 'historical simulated capture') if data.get('scenario') else row.get('origin',origin))+'.\n\n'+fence+'cli\n'+text+'\n'+fence)
                    if selected:parts.append('Literal '+selected[0]+' command excerpt; surrounding configuration remains available in the source record.')
                    if len(row['config_text'])>4500:parts.append('Configuration excerpt limited to 4,500 characters.')
                if len(records)>3:parts.append('Showing the three most recent returned captures.')
            elif tool=='network.state':
                import json
                special={'controller_state','source_health','simulated_job','forwarding_assessment'}
                for row in records:
                    if row.get('kind')=='forwarding_assessment':
                        assessment=row.get('assessment') or {};flow=row.get('flow') or {}
                        parts.append('**Modeled forwarding — '+cell(assessment.get('status','unrecorded'))+'** · `'+cell(flow.get('source_address'))+'` → `'+cell(flow.get('destination_address'))+'`, VRF `'+cell(flow.get('vrf','unrecorded'))+'`.')
                        if row.get('timestamp'):parts.append('Observation recorded `'+cell(row['timestamp'])+'`; calculated scope, not a physical packet test.')
                        for direction in ['forward','return']:
                            result=assessment.get(direction) or {}
                            parts.append('**'+direction.capitalize()+': '+cell(result.get('status','not recorded'))+'**.')
                            for branch in result.get('branches',[])[:3]:
                                steps=' → '.join(cell(hop.get('hostname'))+(' via `'+cell(hop['interface'])+'`' if hop.get('interface') else '') for hop in branch.get('hops',[]))
                                parts.append('- '+cell(branch.get('status'))+': '+cell(branch.get('reason'))+('. Egress steps: '+steps if steps else '')+'.')
                                location=branch.get('failure_location') or {}
                                if location:parts.append('  Recorded failure: '+cell(location.get('direction'))+' on `'+cell(location.get('hostname'))+'` / `'+cell(location.get('interface'))+'`; policy `'+cell(location.get('policy_rule'))+'`, action '+cell(location.get('action'))+'.')
                    elif row.get('kind')=='controller_state':
                        parts.append('**Controller `'+cell(row.get('controller'))+'`** — connection: **'+cell(row.get('operational'))+'**; configured: '+cell(row.get('configured'))+'. Associated device: `'+cell(row.get('node') or row.get('hostname'))+'`.')
                        if row.get('capabilities'):parts.append('Recorded capabilities: '+', '.join(cell(v) for v in row['capabilities'])+'. Controller connection state does not establish device operational health.')
                    elif row.get('kind')=='source_health':
                        statuses=row.get('sources',{});issues={key:value for key,value in statuses.items() if value!='AVAILABLE'}
                        parts.append('**Source availability** — '+str(len(statuses))+' recorded source statuses'+(': '+', '.join(cell(k)+'='+cell(v) for k,v in issues.items()) if issues else '; all are marked AVAILABLE' if statuses else '; status list is empty')+'.')
                        if row.get('physical_collection_performed') is False:parts.append('No physical device collection was performed. These source statuses describe the development provider.')
                    elif row.get('kind')=='simulated_job':
                        device=row.get('hostname') or devices.get(str(row.get('device_id')))
                        parts.append('**Simulated job `'+cell(row.get('job_id'))+'`**'+(' · `'+cell(device)+'`' if device else '')+' — '+cell(row.get('status'))+'; effect: '+cell(row.get('effect'))+'. '+cell(row.get('message')))
                        if row.get('timestamp'):parts.append('Job observation recorded `'+cell(row['timestamp'])+'`; this is separate from the source capture time.')
                # A protocol label alone cannot answer an adjacency question.
                # These are typed reader facts, not a generic CLI interpretation.
                for row in records:
                    if row.get('kind')!='protocol_assessment':continue
                    parts.append('**'+cell(row.get('protocol'))+'** — recorded state: **'+cell(row.get('observed_state'))+'**. Scope: '+cell(row.get('assessment'))+'.')
                    differences=row.get('configuration_differences',[])
                    if differences:parts.append('Recorded prerequisite differences: '+', '.join(cell(v) for v in differences)+'.')
                    if row.get('conflict'):parts.append('The declared prerequisite values conflict with the recorded session state; no cause is confirmed.')
                    if row.get('unknown_prerequisites'):parts.append('Unrecorded prerequisites: '+', '.join(cell(v) for v in row['unknown_prerequisites'])+'.')
                    for index,peer in enumerate(row.get('peer_parameters',[]),1):
                        values=[key+'='+str(peer[key]) for key in ['router_id','local_as','remote_as','local_address','neighbor_address','area','hello_seconds','dead_seconds'] if peer.get(key) is not None]
                        if values:parts.append('- '+cell(devices.get(str(peer.get('device_id')),'Recorded peer '+str(index)))+': '+ '; '.join(values))
                fields=['admin_status','oper_status','prefix','success','protocol','observed_state','destination_ip','complete','routes']
                remaining=[row for row in records if row.get('kind') not in special]
                if remaining:parts.append(table(['Device / interface','Time','Observation','Recorded values'],[
                    [str(row.get('hostname') or devices.get(str(row.get('device_id')),'Selected device'))+(' · '+str(row['interface']) if row.get('interface') else ''),
                     row.get('timestamp'),row.get('kind'),'; '.join(key+'='+json.dumps(row[key],ensure_ascii=False) for key in fields if key in row)] for row in remaining[:20]]))
            elif tool=='network.telemetry':
                rows=[];seen=set();omitted=False
                for row in records:
                    stamp=row.get('time') or row.get('timestamp');name=row.get('hostname') or row.get('device') or devices.get(str(row.get('device_id'))) or str(row.get('device_id',''))
                    if row.get('interface'):name+=' · '+str(row['interface'])
                    identity=(name,row.get('field'))
                    if identity in seen or len(rows)>=8:omitted=True;continue
                    seen.add(identity)
                    metrics=[(row.get('field'),row.get('value'))] if 'field' in row else [(key,value) for key,value in row.items() if key not in {'id','device_id','hostname','interface','interface_id','time','timestamp','source','current','kind','freshness','depends_on'}]
                    useful=[(key,value) for key,value in metrics if value is not None]
                    priority=['cpu','memory','utilization_pct','errors','discards','in_bps','out_bps']
                    useful.sort(key=lambda pair:priority.index(pair[0]) if pair[0] in priority else len(priority))
                    omitted=omitted or len(useful)>7
                    rows.append([name,stamp,'; '.join(str(key)+'='+str(value) for key,value in useful[:7])])
                parts.append(table(['Device / interface','Recorded time','Measurements (source units)'],rows))
                if omitted:parts.append('Showing the latest returned row per device/interface/metric, up to eight rows and seven fields per row. Additional timestamps or fields are omitted; ask for a narrower measurement to inspect them.')
            elif tool in {'network.syslog','network.incidents'}:
                for row in records[:12]:
                    name=row.get('hostname') or devices.get(str(row.get('device_id'))) or str(row.get('device_id',row.get('affected_devices','')))
                    stamp=row.get('timestamp') or row.get('created_at') or row.get('detected_at') or row.get('time')
                    message=row.get('message') or row.get('description') or row.get('root_cause_summary') or row.get('summary')
                    details=[label+': **'+cell(row[key])+'**' for key,label in [('severity','Severity'),('state','Recorded status'),('status','Recorded status')] if row.get(key) is not None]
                    parts.append('**'+cell(name)+'** · event recorded `'+cell(stamp)+'`. '+(' · '.join(details)+'.' if details else '')+'\n\n'+cell(message))
                for category,status in payload.get('source_statuses',{}).items():
                    parts.append('Source `'+cell(category)+'`: **'+cell(status)+'** · captured `'+cell(payload.get('source_captures',{}).get(category))+'`.')
            else:
                parts.append(table(['Device','Time','Severity / type','Recorded event'],[
                    [row.get('hostname') or devices.get(str(row.get('device_id'))) or str(row.get('device_id',row.get('affected_devices',''))),
                     row.get('timestamp') or row.get('created_at') or row.get('detected_at') or row.get('time'),
                     row.get('severity') or row.get('anomaly_type') or row.get('event_type'),
                     row.get('message') or row.get('description') or row.get('root_cause_summary') or row.get('summary')] for row in records[:20]]))
            if payload.get('truncated') or len(records)>20:parts.append('This is a bounded excerpt of the available records.')
        sections.append('\n\n'.join(parts))
    development=any(isinstance(item.get('data'),dict) and item['data'].get('scenario',{}).get('authoritative_development') for item in context)
    if development:
        sections.append('*Development simulation.*')
    elif len(context)>1:
        sections.append('These are recorded observations. Simulated data and historical captures do not establish current network conditions or a verified root cause.')
    absent=None if development else empty_observation_answer(context)
    if absent:sections.append(absent)
    return '\n\n'.join(sections)


def empty_observation_answer(context):
    operational = [item for item in context if item.get('tool') in {
        'network.telemetry', 'network.syslog', 'network.incidents', 'network.configuration'}]
    if not operational:
        return None

    def has_records(data):
        if not isinstance(data, dict):
            return False
        # Truncated data cannot establish absence. Let normal synthesis handle it.
        return bool(data.get('records') or data.get('excerpt') or any(
            has_records(source.get('data')) for source in data.get('sources', [])))

    if any(has_records(item.get('data')) for item in operational):
        return None
    names = {'network.telemetry': 'Measurements', 'network.syslog': 'Syslogs',
             'network.incidents': 'Incident history', 'network.configuration': 'Configuration history'}
    lines = ['No matching operational records were returned for this request.']
    for item in operational:
        state = ('Access denied' if item['status'] == 'denied' else 'Reader failed' if item['status'] == 'error'
                 else 'No matching records were returned' if item['status'] == 'success'
                 else 'Requested source is unavailable')
        lines.append('- **' + names[item['tool']] + ':** ' + state + '.')
    topology = next((item.get('data') or {} for item in context if item.get('tool') == 'network.topology'), {})
    if topology.get('topology_kind') == 'planned':
        lines.append('- **Planned topology:** ' + str(topology.get('total_links', 0)) + ' recorded link(s) in the selected scope; packet reachability was not measured.')
    lines.extend(['', 'Missing records do not establish a fault, healthy operation, or an authorization failure. No network root cause can be established from this result.',
                  'To investigate further, supply timestamped measurements, relevant logs or configuration captures for the affected device and time range.'])
    return '\n'.join(lines)
