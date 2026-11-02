"""Bounded calculations over authorized development observations, not a simulator.

No scenario IDs, expected diagnoses, prompt answers or device names are encoded.
Authority is supplied by server-produced evidence, and release still requires
existing exact-record verification. Unknown protocols/paths remain unverified.
"""
import ipaddress
from collections import defaultdict
from typing import Literal
from pydantic import Field
from llm.gateway_models import StrictModel


class Hypothesis(StrictModel):
    candidate: str
    scope: str
    supporting: list[dict] = Field(default_factory=list,max_length=30)
    contradicting: list[dict] = Field(default_factory=list,max_length=30)
    missing: list[str] = Field(default_factory=list,max_length=20)
    status: Literal['confirmed_within_scenario','strongly_supported','plausible','contradicted','insufficient_evidence']
    evidence_strength: str
    independent_observations: int = 0
    next_check: str


def assess_scenario(context,evidence):
    labels={e.id:'S'+str(n+1) for n,e in enumerate(evidence)}
    trusted={e.id for e in evidence if e.origin=='simulated' and e.authority=='development_scenario'}
    sources=[c for c in context if isinstance(c.get('data'),dict) and c['data'].get('scenario',{}).get('authoritative_development') and set(c.get('evidence_ids',[])) & trusted]
    if not sources:return None
    metas=[c['data']['scenario'] for c in sources]
    expanded=assess_expanded_model(sources,evidence)
    if expanded is not None:return expanded
    revisions={m['source_revision'] for m in metas};meta=metas[0]
    conflicts=[];gaps=[];critical=[];findings=[];hypotheses=[]
    if len(revisions)!=1:conflicts.append('Sources changed during this investigation. Refresh before drawing a conclusion.')
    for c in sources:
        if c['status']!='success':gaps.append(c['tool']+' is explicitly unavailable in the scenario')
        if c['data'].get('truncated') or c['data'].get('excerpt'):
            gaps.append(c['tool']+' is partial; its absence claims are not complete')
            if c['tool']=='network.state':critical.append('State observations are partial')
    citations=lambda c:' '.join('['+labels[e]+']' for e in c.get('evidence_ids',[]) if e in labels)
    rows=[];refs={};owners={};links={};all_rows={}
    for c in sources:
        data=c['data']
        for d in data.get('devices',[]):
            for i in d.get('interfaces',[]):owners[i['id']]=(str(d['id']),d['hostname'],i['name'])
        for link in data.get('links',[]):links[link['id']]=link
        for row in data.get('records',[]):
            all_rows[row['id']]=row
            refs[row['id']]={'record_id':row['id'],'evidence_id':next(iter(c.get('evidence_ids',[])),'')}
            if row.get('current') is True and row.get('freshness')=='fresh' and c['status']=='success' and c['tool']=='network.state':rows.append(row)
    by_interface=defaultdict(list)
    for row in rows:
        if row.get('kind')=='interface_state':by_interface[row.get('interface_id')].append(row)
    for iid,items in by_interface.items():
        if len({(r.get('admin_status'),r.get('oper_status'),r.get('prefix')) for r in items})>1:
            name=owners.get(iid,('', 'Selected device','interface '+str(iid)))
            conflicts.append(name[1]+' '+name[2]+': current observers disagree about state or prefix.')
    def references(items):return [refs[r['id']] for r in items if r['id'] in refs][:30]
    def roots(items):
        def visit(key,seen):
            if key in seen:return set()
            row=all_rows.get(key)
            if row is None:return set()  # Missing dependencies do not establish independent evidence.
            deps=row.get('depends_on',[])
            return set().union(*(visit(d,seen|{key}) for d in deps)) if deps else {key}
        return set().union(*(visit(r['id'],set()) for r in items)) if items else set()
    def cite(items):
        return ' '.join(dict.fromkeys('['+labels[refs[r['id']]['evidence_id']]+']' for r in items if r['id'] in refs and refs[r['id']]['evidence_id'] in labels))
    def hypothesis(candidate,scope,support,against,status,missing,next_check):
        hypotheses.append(Hypothesis(candidate=candidate,scope=scope,supporting=references(support),contradicting=references(against),missing=missing,status=status,
            evidence_strength='Direct scoped observations and deterministic calculation' if support else 'Decisive observations missing',independent_observations=len(roots(support)),next_check=next_check).model_dump())
    from llm.orchestration.editor_facts import literal_facts
    for row in all_rows.values():
        if row.get('kind')!='running_configuration' or row.get('current') is not True or row.get('freshness')!='fresh':continue
        text=row.get('config_text','');facts=literal_facts([{'source':'current','text':text}],'current')
        for iid,states in by_interface.items():
            if len(states)!=1 or str(states[0]['device_id'])!=str(row['device_id']):continue
            name=owners.get(iid,('','',''))[2].lower()
            observed=states[0].get('prefix')
            if observed and facts['interfaces'].get(name):
                try:disagrees=str(ipaddress.ip_interface(observed)) not in facts['interfaces'][name]
                except ValueError:continue
                if disagrees:conflicts.append('Current configuration and observed interface prefix disagree for '+owners[iid][1]+' '+owners[iid][2]+'.')
    probes=[r for r in rows if r.get('kind')=='reachability' and type(r.get('success')) is bool]
    if not probes:gaps.append('A fresh scoped reachability observation is missing');critical.append('No fresh scoped test')
    outcomes=[]
    for probe in probes:
        path=probe.get('interface_ids',[])
        # Only the declared two-ended path is evaluated, not arbitrary routing.
        endpoints=[by_interface.get(i,[]) for i in path]
        usable=len(path)==2 and all(items for items in endpoints)
        path_links=[links[i] for i in probe.get('link_ids',[]) if i in links]
        scoped=usable and len(path_links)==1 and {path_links[0]['src_interface_id'],path_links[0]['dst_interface_id']}==set(path)
        if scoped:
            # A field shared by disagreeing observers can still be compared.
            # Conflicting state is unknown; never silently select one observer.
            def consensus(items):
                result=dict(items[0])
                for key in ['admin_status','oper_status','prefix']:
                    values=[r.get(key) for r in items]
                    result[key]=values[0] if all(v==values[0] for v in values) else None
                return result
            a,b=(consensus(items) for items in endpoints)
            scoped={str(a['device_id']),str(b['device_id'])}=={str(probe['device_id']),str(probe.get('to_device_id'))}
        scope=next((v[1] for v in owners.values() if v[0]==str(probe['device_id'])),'Selected device')+' → '+str(probe.get('destination_ip','unspecified destination'))+' ('+str(probe.get('protocol','unspecified test'))+')'
        findings.append(('Scoped test succeeded: ' if probe['success'] else 'Scoped test failed: ')+scope+' at '+probe['timestamp']+'. '+cite([probe]))
        if not scoped:
            gaps.append('A unique current two-ended path and interface observations are needed for '+scope)
            critical.append('Current path is not uniquely resolved');outcomes.append('insufficient_evidence');continue
        relevant=[a,b,probe];safe=not conflicts and not critical
        down=[r for group in endpoints for r in group if r.get('admin_status')=='down' and r.get('oper_status')=='down']
        up=[r for group in endpoints for r in group if r.get('admin_status')=='up' and r.get('oper_status')=='up']
        if down and probe['success']:conflicts.append('A successful scoped test contradicts the down interface on its declared path.')
        status='confirmed_within_scenario' if down and not probe['success'] and safe else 'plausible' if down else 'contradicted' if len(up)==2 else 'insufficient_evidence'
        hypothesis('Administrative shutdown interrupts the declared path',scope,down+([probe] if not probe['success'] and down else []),up+([probe] if probe['success'] else []),status,
            [] if status in {'confirmed_within_scenario','contradicted'} else ['Resolve current path/interface state conflicts'], 'Inspect a fresh administrative/operational interface observation')
        if down:findings.append('Administrative/operational down: '+', '.join(owners[r['interface_id']][1]+' '+owners[r['interface_id']][2] for r in down)+'. '+cite(down))
        incompatible=None
        try:
            if any(not isinstance(r.get('prefix'),str) or '/' not in r['prefix'] for r in [a,b]):raise ValueError('Explicit prefix required')
            left,right=ipaddress.ip_interface(a['prefix']),ipaddress.ip_interface(b['prefix'])
            incompatible=left.version!=right.version or not (left.ip in right.network and right.ip in left.network)
            findings.append('Observed prefixes '+str(left)+' and '+str(right)+(' are mutually on-link.' if not incompatible else ' are not mutually on-link.')+' '+cite([a,b]))
        except (ValueError,KeyError,TypeError):gaps.append('Valid current prefixes are required to compare subnets')
        if incompatible and probe['success']:conflicts.append('Successful direct-path reachability conflicts with the observed off-link prefixes.')
        subnet_status='confirmed_within_scenario' if incompatible and not probe['success'] and len(up)==2 and safe and meta['model_scope']=='direct_link' else 'contradicted' if incompatible is False else 'plausible'
        hypothesis('Subnet mismatch prevents the modeled direct link',scope,[a,b,probe] if incompatible else [],[a,b] if incompatible is False else [],subnet_status,
            [] if subnet_status in {'confirmed_within_scenario','contradicted'} else ['Decisive direct-link prefix/reachability observations'], 'Compare fresh endpoint prefixes and the tested scope')
        route_status='insufficient_evidence';route_rows=[];route_gap=False
        if probe.get('routing_required') is True:
            route_rows=[r for r in rows if r.get('kind')=='routing_table' and str(r['device_id'])==str(probe['device_id'])]
            try:
                if not isinstance(probe.get('destination_ip'),str):raise ValueError('Explicit destination address required')
                dest=ipaddress.ip_address(probe['destination_ip'])
                complete=len(route_rows)==1 and route_rows[0].get('complete') is True
                matches=[r for table in route_rows for r in table.get('routes',[]) if dest in ipaddress.ip_network(r['prefix'],strict=False)]
                connected=any(dest in ipaddress.ip_interface(r['prefix']).network for r in rows if r.get('kind')=='interface_state' and str(r['device_id'])==str(probe['device_id']) and r.get('prefix') and r.get('oper_status')=='up')
                route_gap=complete and not matches and not connected
                if route_gap and probe['success']:conflicts.append('Successful routed test conflicts with a complete source table that has no applicable route.')
                route_status='strongly_supported' if route_gap and not probe['success'] and len(up)==2 and incompatible is False and safe else 'contradicted' if matches or connected else 'insufficient_evidence'
                findings.append(('Complete source route table has no route to ' if route_gap else 'Returned routing records inspected for ')+str(dest)+'. '+cite(route_rows))
            except (ValueError,KeyError,TypeError):gaps.append('Route table/destination values are incomplete or malformed')
        else:route_status='contradicted';route_rows=[probe]
        hypothesis('Missing source route explains the scoped failure',scope,route_rows+[probe] if route_gap else [],route_rows if route_status=='contradicted' else [],route_status,
            ['End-to-end forwarding/policy and return path remain outside the route-table fact'] if route_status=='strongly_supported' else [] if route_status=='contradicted' else ['A complete route table for the tested destination'], 'Inspect scoped route/next-hop and return-path observations without active collection')
        if conflicts:outcomes.append('conflicting_evidence')
        elif probe['success'] and len(up)==2 and incompatible is False and not critical:outcomes.append('healthy_within_tested_scope')
        elif status=='confirmed_within_scenario' or subnet_status=='confirmed_within_scenario':outcomes.append('confirmed_within_scenario')
        elif route_status=='strongly_supported':outcomes.append('strongly_supported')
        else:outcomes.append('insufficient_evidence')
    if not hypotheses:
        scope=', '.join(sorted({v[1] for v in owners.values()})) or 'Selected network'
        for candidate,missing,check in [
            ('Administrative shutdown interrupts the declared path',['Current administrative/operational interface state','Scoped reachability result'],'Inspect recorded current interface state and a scoped reachability observation'),
            ('Subnet mismatch prevents the modeled direct link',['Current endpoint prefixes','Observed path scope'],'Compare the recorded endpoint prefixes and path scope'),
            ('Missing source route explains the scoped failure',['Complete route table','Destination and return-path scope'],'Inspect the existing routing and destination records')]:
            uncertain=[r for values in by_interface.values() for r in values]
            support=[r for r in uncertain if r.get('admin_status')=='down'] if candidate.startswith('Administrative') else []
            against=[r for r in uncertain if r.get('admin_status')=='up'] if support else []
            hypothesis(candidate,scope,support,against,'plausible' if conflicts else 'insufficient_evidence',(['Resolve the disagreeing current observers and compare timestamps'] if conflicts else [])+missing,check)
    # A contradictory or partial source cannot be made conclusive by repeated
    # derived alerts. No number of matching symptoms establishes causation.
    if conflicts or critical:
        for h in hypotheses:
            if h['status'] in {'confirmed_within_scenario','strongly_supported'}:h['status']='plausible';h['missing'].append('Resolve contradictory or incomplete evidence')
    status='conflicting_evidence' if conflicts else outcomes[0] if len(set(outcomes))==1 else 'insufficient_evidence'
    if critical and status in {'confirmed_within_scenario','healthy_within_tested_scope'}:status='insufficient_evidence'
    events=[]
    for row in all_rows.values():
        if row.get('kind') in {'syslog','administrative_change','interface_event','configuration_event'} and row.get('timestamp'):
            events.append({'time':row['timestamp'],'message':str(row.get('message','Recorded administrative event'))[:300],'record_ref':refs[row['id']]})
    return {'development':meta,'conclusion_status':status,'hypotheses':hypotheses,'findings':list(dict.fromkeys(findings)),
        'gaps':list(dict.fromkeys(gaps)),'warnings':[],'conflicts':list(dict.fromkeys(conflicts)),'origins':['simulated'],
        'timeline':sorted(events,key=lambda r:r['time'])[-10:],'dependency_roots':len(roots(list(all_rows.values()))),
        'verification_scope':'Current authorized structured observations; two-ended declared paths only; no physical device certification'}


def assess_expanded_model(sources,evidence):
    """Release the bounded model's scope, never infer physical packet success."""
    state=[c for c in sources if c['tool'] in {'network.state','network.telemetry'}]
    rows=[(r,c) for c in state for r in c['data'].get('records',[]) if r.get('kind') in {'forwarding_assessment','protocol_assessment','metric_series'}]
    if not rows:return None
    revisions={c['data']['scenario']['source_revision'] for c in sources}
    conflicts=[];gaps=[];findings=[];hypotheses=[];outcomes=[]
    if len(revisions)!=1:conflicts.append('Source revisions changed during retrieval; refresh the modeled observations.')
    interfaces=defaultdict(list)
    for source in state:
        if source['status']!='success':continue
        for row in source['data'].get('records',[]):
            if row.get('kind')=='interface_state' and row.get('current') is True and row.get('freshness')=='fresh':
                interfaces[(row.get('device_id'),row.get('interface_id'))].append(row)
    for items in interfaces.values():
        for field in ['admin_status','oper_status','prefix']:
            values=set()
            for row in items:
                value=row.get(field)
                if value in {None,'','unknown'}:continue
                if field=='prefix':
                    try:value=str(ipaddress.ip_interface(value))
                    except ValueError:continue
                values.add(value)
            if len(values)>1:
                row=items[0]
                conflicts.append(str(row.get('hostname','Selected device'))+' '+str(row.get('interface') or row.get('interface_id'))+': current interface observations disagree about '+field.replace('_',' ')+' ('+' versus '.join(sorted(str(v) for v in values))+'). Declared model inputs do not resolve the conflict.')
    for row,source in rows:
        citation=' '.join('[S'+str(n+1)+']' for n,e in enumerate(evidence) if e.id in source.get('evidence_ids',[]))
        scope='Selected modeled traffic' if row['kind']=='forwarding_assessment' else row.get('protocol','Recorded metric')+' '+row.get('observed_state',row.get('metric',''))
        ref={'record_id':row['id'],'evidence_id':next(iter(source.get('evidence_ids',[])),'')}
        fresh=row.get('current') is True and row.get('freshness')=='fresh' and source['status']=='success' and not source['data'].get('truncated')
        if not fresh:gaps.append('Current complete modeled observations are required for '+scope)
        if row['kind']=='forwarding_assessment':
            result=row['assessment'];status=result['status']
            details=[]
            for direction in ['forward','return']:
                trace=result.get(direction)
                if trace:
                    details.append(direction+': '+trace['status'])
                    for branch in trace['branches']:
                        path='; '.join(h['hostname']+' via '+h.get('interface',h['vrf']) for h in branch['hops'])
                        findings.append((direction.capitalize()+' Egress sequence: '+path+'; ' if path else '')+branch['reason']+' '+citation)
                        location=branch.get('failure_location') or {}
                        if location.get('policy_rule') is not None:
                            findings.append(direction.capitalize()+' '+str(location['direction'])+' policy '+str(location['policy_rule'])+' at '+location['hostname']+' '+location['interface']+': '+location['action']+'. '+citation)
                        elif location.get('hostname'):
                            findings.append(direction.capitalize()+' observation at '+location['hostname']+
                                (' / '+location['interface'] if location.get('interface') else '')+': '+str(branch.get('reason','unresolved'))+'. '+citation)
            findings.insert(0,'Modeled IPv4 forwarding — '+', '.join(details)+'. '+citation)
            qualification='healthy_within_tested_scope' if status=='delivered' else 'confirmed_within_scenario' if status=='failed' else 'strongly_supported' if status=='partial' else 'insufficient_evidence'
            candidate='A forwarding fault prevents modeled delivery' if status=='delivered' else 'A declared forwarding constraint blocks traffic' if status=='failed' else 'Some modeled traffic paths work and others do not' if status=='partial' else 'Forwarding cannot be established from incomplete modeled inputs'
            denied=[branch['failure_location'] for direction in ['forward','return']
                if (trace:=result.get(direction)) and trace['status']=='failed'
                for branch in trace.get('branches',[]) if branch.get('failure_location',{}).get('action')=='deny']
            if denied:
                qualification='confirmed_within_scenario'
                candidate='An evaluated '+denied[0]['direction']+' policy blocks the selected modeled traffic direction at '+denied[0]['hostname']+' '+denied[0]['interface']
            if status=='unknown':gaps.append('Resolve the unknown hop, source or traversal limit in the forwarding trace')
        elif row['kind']=='protocol_assessment':
            qualification=row['assessment'];candidate='A modeled '+row['protocol']+' prerequisite fault prevents the recorded adjacency/session'
            differences=row.get('configuration_differences',[])
            findings.append(row['protocol']+' observed '+row['observed_state']+('; '+', '.join(differences) if differences else '; no modeled prerequisite mismatch established')+'. '+citation)
            if row.get('conflict'):
                peers=row.get('peer_parameters',[]);details=[]
                for difference in differences:
                    field=difference.removesuffix(' mismatch')
                    if peers and all(field in peer for peer in peers):
                        details.append(field+': '+', '.join(str(peer.get('hostname') or peer['device_id'])+'='+str(peer[field]) for peer in peers))
                conflicts.append(row['protocol']+' configuration prerequisites'+(' ('+'; '.join(details)+')' if details else '')+' conflict with its reported '+str(row.get('observed_state'))+' session state')
            if row.get('accepted_prefixes')==[]:findings.append('The BGP session observation has zero accepted prefixes; session state alone does not establish route distribution. '+citation)
            for note in row.get('conditional_findings',[]):findings.append(note+'. '+citation)
            if row.get('unknown_prerequisites'):gaps.append(row['protocol']+' prerequisites not fully recorded: '+', '.join(row['unknown_prerequisites']))
        else:
            candidate='Congestion explains the recorded drops' if row.get('congestion_hypothesis') else 'A current performance fault explains the recorded measurements'
            qualification='insufficient_evidence'
            findings.extend(note+'. '+citation for note in row.get('interpretation',[]))
            gaps.append('Correlate independent scoped loss/error/policy observations before confirming a performance cause')
        if not fresh:qualification='insufficient_evidence'
        outcomes.append(qualification)
        hypotheses.append(Hypothesis(candidate=candidate,scope=scope,supporting=[ref] if qualification!='healthy_within_tested_scope' else [],contradicting=[ref] if qualification=='healthy_within_tested_scope' else [],status='contradicted' if qualification=='healthy_within_tested_scope' else 'plausible' if qualification=='conflicting_evidence' or row.get('congestion_hypothesis')=='plausible' else qualification,
            evidence_strength='Calculation over explicitly declared simulated inputs; not a physical packet test',independent_observations=1,
            missing=[] if fresh else ['Fresh complete model inputs'],next_check='Inspect scoped forwarding branches or protocol source observations').model_dump())
    status='conflicting_evidence' if conflicts else outcomes[0] if len(set(outcomes))==1 else 'confirmed_within_scenario' if 'confirmed_within_scenario' in outcomes and set(outcomes)<={'confirmed_within_scenario','healthy_within_tested_scope'} else 'insufficient_evidence'
    if conflicts:
        for h in hypotheses:
            if h['status'] in {'confirmed_within_scenario','strongly_supported'}:h['status']='plausible'
            elif h['status']=='contradicted':h['status']='insufficient_evidence'
            h['missing'].append('Resolve contradictory source inputs before ruling this explanation in or out')
            h['next_check']='Compare the conflicting current interface records, their capture times and source dependencies'
    return {'development':sources[0]['data']['scenario'],'conclusion_status':status,'hypotheses':hypotheses,
        'findings':list(dict.fromkeys(findings))[:30],'gaps':list(dict.fromkeys(gaps)),'conflicts':conflicts,
        'warnings':['IPv4 stateless observation model; dynamic protocol convergence, NAT and physical measurements are not established.'],
        'origins':['simulated'],'timeline':[],'dependency_roots':1,'model_observation_kinds':sorted({row['kind'] for row,_ in rows}),
        'verification_scope':'Declared current modeled forwarding/protocol inputs only'}


def scenario_text(assessment,evidence):
    status=assessment['conclusion_status'];meta=assessment['development']
    title={'healthy_within_tested_scope':'The recorded test supports connectivity within its tested scope.',
        'confirmed_within_scenario':'A cause is confirmed within the modeled development scope.',
        'strongly_supported':'An explanation is strongly supported; broader causation is not established.',
        'conflicting_evidence':'Current observations conflict; a definitive diagnosis is withheld.',
        'insufficient_evidence':'Available observations do not establish a definitive diagnosis.'}[status]
    if status=='healthy_within_tested_scope' and assessment.get('model_observation_kinds'):
        title=('The declared calculation supports delivery within its modeled traffic scope.' if 'forwarding_assessment' in assessment['model_observation_kinds']
               else 'The recorded protocol sessions are healthy within their observed scope. End-to-end delivery was not established.')
    lines=['**Investigation assessment** — Development simulation · '+meta['id']+' · revision '+str(meta['revision']),title]
    lines+=['- '+value for value in assessment['findings']]
    lines+=['- Conflict: '+value for value in assessment['conflicts']]
    labels={e.id:'S'+str(n+1) for n,e in enumerate(evidence)}
    for h in assessment['hypotheses']:
        cites=' '.join(dict.fromkeys('['+labels[r['evidence_id']]+']' for r in h['supporting']+h['contradicting'] if r['evidence_id'] in labels))
        lines.append('**'+h['candidate']+'**: '+h['status'].replace('_',' ')+'. '+cites)
    lines+=['- Missing: '+value for value in assessment['gaps']]
    decisive=[h['next_check'] for h in assessment['hypotheses'] if h['status'] not in {'contradicted','confirmed_within_scenario'}]
    lines.append('**Next checks:** '+('; '.join(dict.fromkeys(decisive)) if decisive else 'Reassess after the modeled state changes; no device action is required for this assessment')+'.')
    if assessment['timeline']:lines.append('**Recorded event sequence:** '+'; '.join(e['time']+' — '+e['message'] for e in assessment['timeline'])+'. Sequence alone does not establish causality.')
    lines.append('Supporting records are included with this answer. Measurements, diagnoses and test outcomes apply to the declared simulation scope.')
    return '\n\n'.join(lines)
