"""Bounded, read-only network context; source labels survive routing and synthesis."""
from collections import deque
from datetime import datetime, timezone, timedelta
import json
from copy import deepcopy
import os
import re
from typing import Literal
from uuid import uuid4

from pydantic import Field, field_validator, model_validator
from llm.gateway_models import Evidence, StrictModel, ToolResult, text_digest

READ_TOOLS = frozenset({'inventory.read', 'network.topology', 'network.telemetry',
    'network.state', 'network.syslog', 'network.incidents', 'network.configuration', 'knowledge.search'})

# These qualified attributes describe observations, not interface identity or a
# planned inventory status. Recognize field-style and natural separators without
# rewriting hostnames, and leave semantic planning/authorization to their layers.
INTERFACE_OBSERVATION = (r'\b(?:(?:interfaces?|ports?)[\s_\-\u2010-\u2015]+'
    r'(?:(?:operational|administrative|oper|admin)[\s_\-\u2010-\u2015]+)?(?:state|status)'
    r'|(?:operational(?:ly)?|administrative(?:ly)?|oper|admin)[\s_\-\u2010-\u2015]+(?:state|status|up|down))\b')
OTHER_STATE_TOPIC = r'\b(?:routes?|routing|ospf|bgp|isis|controllers?|collectors?|reachability|forwarding|jobs?|audit|source[\s_-]+health|collection[\s_-]+status|investigat\w*|diagnos\w*|troubleshoot\w*|causes?|why)\b'


def interface_state_request(prompt):
    """A scoped attribute read, never a diagnosis or operation recognizer."""
    return bool(re.search(INTERFACE_OBSERVATION,prompt,re.I) and not re.search(OTHER_STATE_TOPIC,prompt,re.I))


def bounded_record_context(data, limit):
    """Keep complete authoritative rows instead of an unreadable JSON fragment."""
    projected=deepcopy(data)
    if not isinstance(projected,dict):return {'excerpt':json.dumps(data,default=str)[:limit],'truncated':True}
    containers=[]
    def collect(value):
        if not isinstance(value,dict):return
        if isinstance(value.get('records'),list):containers.append(value)
        for source in value.get('sources',[]):collect(source.get('data'))
    collect(projected)
    while len(json.dumps(projected,default=str))>limit:
        candidates=[value for value in containers if len(value['records'])>1]
        if not candidates:return {'excerpt':json.dumps(data,default=str)[:limit],'truncated':True}
        largest=max(candidates,key=lambda value:len(json.dumps(value['records'],default=str)))
        largest['records'].pop();largest['truncated']=True
        projected['truncated']=True
    return projected


class NetworkQuery(StrictModel):
    device_refs: list[str] = Field(default_factory=list, max_length=8)
    query: str = Field(default='', max_length=4000)
    limit: int = Field(default=30, ge=1, le=100)
    start: str | None = None
    end: str | None = None
    live: bool = False
    source_scope: Literal['auto','current','historical','planned','observed','both'] = 'auto'
    record_kinds: list[str] = Field(default_factory=list,max_length=8)
    source_categories: list[str] = Field(default_factory=list,max_length=24)
    interface_refs: list[str] = Field(default_factory=list,max_length=64)
    window_minutes: int = Field(default=60,ge=1,le=10080)

    @field_validator('start','end')
    @classmethod
    def validate_time(cls,value):
        if value and (len(value)>50 or not timestamp(value)):raise ValueError('Invalid time range timestamp')
        return value

    @field_validator('source_categories')
    @classmethod
    def validate_categories(cls,value):
        from development.source_registry import BY_KEY
        if any(key not in BY_KEY for key in value):raise ValueError('Unknown scenario source category')
        return list(dict.fromkeys(value))

    @field_validator('record_kinds')
    @classmethod
    def validate_record_kinds(cls,value):
        if any(not kind or len(kind)>100 for kind in value):raise ValueError('Invalid record kind filter')
        return list(dict.fromkeys(value))

    @model_validator(mode='after')
    def validate_range(self):
        if self.start and self.end and timestamp(self.start)>timestamp(self.end):raise ValueError('Start must precede end')
        return self


def timestamp(value):
    if not value: return None
    try:
        parsed=datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError: return None


def explicit_topology_scope(text):
    """Narrow explicit source qualifiers; ambiguous requests retain auto scope.

    This constrains retrieval, not network intent recognition or diagnosis.
    Model-selected scope remains useful for implicit questions.
    """
    from llm.gateway_references import read_intent_text
    text=read_intent_text(text)
    text=re.sub(r'\b(?:not|without|excluding|ignore|instead of|rather than)\s+(?:the\s+)?(?:planned|intended|design|observed|discovered|operational|current|historical|previous|past)\b','',text,flags=re.I)
    planned=bool(re.search(r'\b(planned|intended|design)\b',text,re.I))
    observed=bool(re.search(r'\b(observed|discovered|operational|current)\b',text,re.I))
    historical=bool(re.search(r'\b(historical|previous|past)\b',text,re.I))
    if sum([planned,observed,historical])>1:return 'both'
    return 'planned' if planned else 'observed' if observed else 'historical' if historical else 'auto'


def redact(text):
    return re.sub(r'(?im)^([^\n]*(?:password|secret|community|private-key|authentication-key)[^\n]*).*$', '[credential line redacted]', str(text))


def explicit_configuration_scope(text):
    """Explicit temporal qualifiers constrain a reader, not CLI semantics."""
    # Capture metadata describes the requested source; it does not request a
    # different historical source. Keep explicit saved snapshots distinguishable.
    text=re.sub(r'\b(?:capture(?:d)?|retrieval|collection)\s+(?:time|timestamp|date)\b','',text,flags=re.I)
    text=re.sub(r'\b(?:not|without|excluding|ignore|instead of|rather than)\s+(?:(?:the|its|their)\s+)?(?:current|active|running|stored|saved|historical|previous|planned|intended)\b','',text,flags=re.I)
    current=bool(re.search(r'\b(current|active|running)\b',text,re.I))
    historical=bool(re.search(r'\b(stored|saved|historical|previous|backups?|snapshots?|captures?)\b',text,re.I))
    if current and historical:return 'both'
    if current:return 'current'
    if historical:return 'historical'
    if re.search(r'\b(planned|intended)\b',text,re.I):return 'planned'
    return 'auto'


def planned_graph_path(devices,links,names):
    """One recorded undirected graph calculation shared by both source adapters."""
    if len(devices)!=2:return None
    queue=deque([(devices[0]['id'],[devices[0]['id']])]);seen={devices[0]['id']}
    while queue:
        node,trail=queue.popleft()
        if node==devices[1]['id']:return [names[i] for i in trail]
        for link in links:
            if node in (link['src_device_id'],link['dst_device_id']):
                other=link['dst_device_id'] if node==link['src_device_id'] else link['src_device_id']
                if other not in seen:
                    seen.add(other);queue.append((other,trail+[other]))
    return None


class NetworkReader:
    def __init__(self, db): self.db = db

    def devices(self, query):
        from llm.gateway_services import inventory_snapshot
        data = inventory_snapshot(self.db)
        if not query.device_refs: return data['devices'], data
        matches=[]
        for reference in query.device_refs:
            found=[d for d in data['devices'] if reference.casefold() in {str(d['id']), d['hostname'].casefold(), str(d['management_ip'] or '').casefold(), *[a.casefold() for a in d['aliases']]}]
            if len(found)!=1: raise ValueError('Device reference is missing or ambiguous: '+reference)
            if found[0] not in matches: matches.append(found[0])
        return matches, data

    def result(self, source, data, devices, *, origin='stored', captured=None, status='success', message=''):
        now=datetime.now(timezone.utc)
        stamp=timestamp(captured)
        freshness='unknown' if not stamp else ('fresh' if 0 <= (now-stamp).total_seconds() <= 120 else 'stale')
        return ToolResult(status=status, data=data, message=message, evidence=[Evidence(id=uuid4().hex,
            source=source, origin=origin, authority='recorded_network_context',
            time_scope='historical' if stamp and freshness=='stale' else 'current' if origin=='live' else 'unspecified',
            captured_at=str(captured) if captured else None, retrieved_at=now.isoformat(), freshness=freshness,
            device_refs=[str(d['id']) for d in devices], source_revision=text_digest(json.dumps(data,sort_keys=True,default=str)))])

    def read(self, domain, query, authorization):
        try: devices, inventory=self.devices(query)
        except ValueError as exc: return ToolResult(status='unavailable',message=str(exc))
        if query.interface_refs:
            recorded={str(i['id']) for d in devices for i in d['interfaces']}
            if domain!='telemetry' or not set(query.interface_refs)<=recorded:
                return ToolResult(status='unavailable',message='The requested interface scope is not recorded for these devices or this reader.')
            if query.live:
                return ToolResult(status='unavailable',message='This live reader does not support an exact interface scope; no broader measurements were substituted.')
        from local_providers.development import active_for
        if query.source_categories:
            from development.source_registry import BY_KEY
            expected_tool='knowledge.search' if domain=='knowledge' else 'network.'+domain
            if any(not BY_KEY[key].supports(expected_tool) for key in query.source_categories):
                raise ValueError('Logical source filter is incompatible with the requested reader')
        if domain!='knowledge' and (manager:=active_for(self.db)):
            return manager.result(domain,query,devices)
        if query.source_categories and domain!='knowledge':
            return ToolResult(status='unavailable',data={'source_available':False,'requested_source_categories':query.source_categories},
                message='These logical source filters belong to a development scenario. Ordinary records were not substituted; use the ordinary reader without a scenario filter.')
        if domain=='state':return ToolResult(status='unavailable',message='Structured routing/protocol/reachability observations are unavailable in this environment')
        if query.live:
            return self.live(domain,query,devices,authorization)
        if domain=='topology': return self.topology(query,devices,inventory)
        if domain=='configuration': return self.configuration(query,devices,authorization)
        if domain=='knowledge':
            from llm.gateway_knowledge import documentation_context
            reference=None;reference_evidence=[];lookup=query.query
            if query.source_categories==['knowledge'] and (manager:=active_for(self.db)):
                bundle=manager.activated_bundle();scenario,meta=manager.snapshot()
                if bundle:
                    source=bundle['sources']['knowledge'];state=scenario['source_statuses']['knowledge']
                    reference={'query':source['data']['query'][:4000],'status':state['status'],'captured_at':state['captured_at'],
                        'source_revision':meta['source_revision'],'authority':'retrieval_request_only; active immutable V9 knowledge remains authoritative'}
                    reference_evidence=[Evidence(id=uuid4().hex,source='development.knowledge_reference',origin='simulated',
                        authority='development_scenario_reference',captured_at=state['captured_at'],source_revision=meta['source_revision'],
                        freshness='stale' if state['status']=='STALE' else 'not_applicable')]
                    if state['status'] not in {'AVAILABLE','STALE','CONFLICTING'}:
                        return ToolResult(status='error' if state['status']=='ERROR' else 'unavailable',data=[],evidence=reference_evidence,
                            message='Scenario knowledge reference source is '+state['status']+'; no published lookup was performed.')
                    lookup=reference['query']
            documents, evidence=documentation_context(lookup)
            if reference:
                published={item.id for item in evidence if item.authority=='published_operation_documentation'}
                documents=[row for row in documents if row.get('evidence_id') in published and row.get('source','').startswith('published:')]
                evidence=[item for item in evidence if item.id in {row.get('evidence_id') for row in documents}]
            if reference and documents:documents=[{**row,'scenario_reference':reference} if i==0 else row for i,row in enumerate(documents)]
            return ToolResult(status='success' if documents else 'unavailable',data=documents,evidence=evidence+reference_evidence,
                message='' if documents else 'No matching local documentation was retrieved. General engineering knowledge may be used, labelled separately.')
        return self.observations(domain,query,devices)

    def live(self,domain,query,devices,authorization):
        if os.getenv('COGNISHIELD_AI_LIVE_READS')!='1':
            return ToolResult(status='unavailable',data={'requested':'live '+domain,'live_available':False},
                message='Live provider reads are disabled. Enable COGNISHIELD_AI_LIVE_READS with the existing configured collector; stored and simulated sources remain separate.')
        if domain=='telemetry':
            # Reuse the low-level collector query. The legacy summary fabricates
            # synthetic CPU/packet estimates and is deliberately not used here.
            from monitor import api as monitor
            if not monitor.INFLUXDB_TOKEN:
                return ToolResult(status='unavailable',message='The existing InfluxDB collector is not configured.')
            refs=[ref for d in devices for ref in [d['hostname'],d['management_ip']] if ref]
            if not refs or any(not re.fullmatch(r'[a-zA-Z0-9_.:-]+',ref) for ref in refs):
                return ToolResult(status='unavailable',message='Live query needs safe, recorded hostnames or management addresses.')
            terms=[key for key in ['cpu','memory','errors','discards'] if key in query.query.lower()] or ['cpu','memory']
            definitions=[monitor.METRIC_DEFS.get(key,{}) for key in terms]
            measurements=sorted({m for definition in definitions for m in definition.get('measurements',[])})
            fields=sorted({f for definition in definitions for f in definition.get('fields',[])})
            if not fields: return ToolResult(status='unavailable',message='No supported measured metric was requested.')
            try:
                raw=monitor._query_metric_rows(min(query.window_minutes,1440),measurements,fields,selected_devices=refs,limit=query.limit,sort_desc=True)
                rows=[{'time':r.get('_time'),'device':monitor._row_device_key(r),'interface':monitor._row_interface_key(r),
                    'field':r.get('_field'),'value':r.get('_value'),'measurement':r.get('_measurement')} for r in raw]
                rows=[r for r in rows if self.in_range(r,query)]
                return self.result('influxdb.measured_metrics',{'records':rows[:query.limit],'total':len(rows),
                    'truncated':len(rows)>query.limit,'window_minutes':min(query.window_minutes,1440),'units':'Original collector units; counters are not rates.'},devices,
                    origin='live',captured=max((r['time'] for r in rows if r['time']),default=None),status='success' if rows else 'unavailable')
            except Exception: return ToolResult(status='unavailable',message='The configured collector query failed; no simulated values were substituted.')
        if domain=='topology':
            topology=self.db.get_topology()
            captured=topology.get('timestamp')
            if not captured or not topology.get('nodes'):
                return ToolResult(status='unavailable',message='No timestamped crawler topology is available. Planned links do not establish live connectivity.')
            names={d['hostname'] for d in devices}
            nodes={name:{k:node.get(k) for k in ['mgmt_ip','status','edgeLink'] if k in node} for name,node in topology['nodes'].items() if name in names}
            return self.result('crawler.topology_cache',{'nodes':nodes,'reachability':'not_tested','collection_triggered':False},devices,origin='live',captured=captured)
        if domain=='syslog':
            result=self.observations(domain,query,devices)
            sources=[source for source in (result.data or {}).get('sources',[]) if source.get('origin')!='simulated' and (source.get('data') or {}).get('records')]
            return ToolResult(status='success' if sources else 'unavailable',data={'sources':sources},
                evidence=[e for e in result.evidence if e.origin!='simulated'],message='Stored syslog receive records retain their timestamps; no device polling was triggered.')
        return ToolResult(status='unavailable',message='This domain has stored history only; no live collector is connected.')

    def topology(self,query,devices,inventory):
        scope=query.source_scope if query.source_scope!='auto' else explicit_topology_scope(query.query)
        if scope in {'current','observed','historical'}:
            kind='historical' if scope=='historical' else 'observed'
            return ToolResult(status='unavailable',data={'records':[],'topology_kind':kind,'source_available':False},message=kind.capitalize()+' link observations are unavailable; planned topology was not substituted.')
        ids={d['id'] for d in devices}; interfaces={i['id']:i for d in inventory['devices'] for i in d['interfaces']}
        names={d['id']:d['hostname'] for d in inventory['devices']}
        links=[dict(link,source=names.get(link['src_device_id']),target=names.get(link['dst_device_id']),
            source_interface=interfaces.get(link['src_interface_id'],{}).get('name'),target_interface=interfaces.get(link['dst_interface_id'],{}).get('name')) for link in inventory['links']]
        path=planned_graph_path(devices,links,names)
        selected=[link for link in links if link['src_device_id'] in ids or link['dst_device_id'] in ids]
        return self.result('sqlite.planned_topology',{'nodes':[{'id':d['id'],'hostname':d['hostname'],'role':d['role']} for d in devices],
            'links':selected[:query.limit],'total_links':len(selected),'truncated':len(selected)>query.limit,
            'graph_path':path,'reachability':'not_measured','topology_kind':'planned','live_available':False},devices)

    def in_range(self,row,query):
        stamp=timestamp(row.get('timestamp') or row.get('time') or row.get('created_at') or row.get('captured_at'))
        start,end=timestamp(query.start),timestamp(query.end)
        return (not start or bool(stamp and stamp>=start)) and (not end or bool(stamp and stamp<=end))

    @staticmethod
    def matches_incident(value, devices):
        try: entries=json.loads(value) if isinstance(value,str) else value
        except (ValueError,TypeError): entries=re.split(r'[,;\s]+',str(value))
        if not isinstance(entries,list): entries=[entries]
        refs={str(d['id']).casefold() for d in devices}|{d['hostname'].casefold() for d in devices}
        return any(str(entry).casefold() in refs for entry in entries)

    def observations(self,domain,query,devices):
        from lab_config import FIXTURE_DIR,LOCAL_LAB
        from local_providers.observations import JsonObservations, FixtureError
        ids={d['id'] for d in devices}; results=[]
        try:
            if not LOCAL_LAB:
                raise FixtureError('Simulated JSON observations are disabled in normal mode; no external measurements were substituted.')
            obs=JsonObservations(FIXTURE_DIR).read(self.db,range_minutes=1440)
            if domain=='telemetry':
                rows=[]
                for device in devices:
                    for point in ([] if query.interface_refs else obs.device(device['id']).metrics):
                        value={key:getattr(point,key) for key in point.model_fields_set}
                        rows.append({'device_id':device['id'],'hostname':device['hostname'],**value})
                    for interface in device['interfaces']:
                        if query.interface_refs and str(interface['id']) not in query.interface_refs:continue
                        for point in obs.interface(interface['id']).metrics:
                            rows.append({'device_id':device['id'],'hostname':device['hostname'],'interface':interface['name'],**{key:getattr(point,key) for key in point.model_fields_set}})
            else:
                groups=['syslog'] if domain=='syslog' else ['alerts','events']
                rows=[row for group in groups for row in obs.events(group) if row['device_id'] in ids]
            rows=[row for row in rows if self.in_range(row,query)]
            rows.sort(key=lambda r:str(r.get('time') or r.get('timestamp') or ''),reverse=True)
            captured=next((r.get('time') or r.get('timestamp') for r in rows),None)
            results.append(self.result('json_fixture.'+domain,{'records':rows[:query.limit],'total':len(rows),'truncated':len(rows)>query.limit,
                'fixture_revision':obs.revision,'live_available':False},devices,origin='simulated',captured=captured,
                status='success' if rows else 'unavailable',message='' if rows else 'No simulated records match this scope.'))
        except FixtureError as exc: results.append(ToolResult(status='unavailable',message=str(exc)))
        # Historical records are a separate source, not relabelled simulated data.
        tables={'syslog':['device_syslog_events'],'incidents':['drift_events','security_events','incidents']}.get(domain,[])
        with self.db._connect() as c:
            for table in tables:
                if not c.execute('SELECT 1 FROM sqlite_master WHERE name=?',(table,)).fetchone(): continue
                columns={r[1] for r in c.execute('PRAGMA table_info('+table+')')}
                if table=='incidents':
                    raw=[dict(r) for r in c.execute('SELECT id,anomaly_type,severity,affected_devices,detected_at,root_cause_summary,root_cause_confidence,status,resolved_at FROM incidents ORDER BY detected_at DESC LIMIT 100')]
                    rows=[row for row in raw if self.in_range({'timestamp':row['detected_at']},query) and (not query.device_refs or self.matches_incident(row['affected_devices'], devices))]
                    results.append(self.result('sqlite.incidents',{'records':rows[:query.limit],'inference_status':'Recorded diagnoses are historical claims, not independently verified root cause.'},devices,captured=rows[0]['detected_at'] if rows else None,status='success' if rows else 'unavailable'))
                    continue
                if 'device_id' not in columns: continue
                raw=[dict(r) for r in c.execute('SELECT * FROM '+table+' WHERE device_id IN ('+','.join('?' for _ in ids)+') ORDER BY id DESC LIMIT 501',tuple(ids))] if ids else []
                rows=[{k:redact(v) if isinstance(v,str) else v for k,v in row.items() if k not in {'credentials','password','token'}} for row in raw if self.in_range(row,query)]
                results.append(self.result('sqlite.'+table,{'records':rows[:query.limit],'truncated':len(rows)>query.limit},devices,
                    captured=next((r.get('created_at') for r in rows),None),status='success' if rows else 'unavailable'))
        return ToolResult(status='success' if any(r.status=='success' for r in results) else 'unavailable',
            data={'sources':[{'status':r.status,'data':r.data,'message':r.message,'origin':r.evidence[0].origin if r.evidence else 'unavailable','source':r.evidence[0].source if r.evidence else None,'evidence_ids':[e.id for e in r.evidence]} for r in results]},evidence=[e for r in results for e in r.evidence],
            message='Local mode has no live measurements. Simulated and stored records retain their source and original timestamps.')

    def configuration(self,query,devices,auth):
        current=query.source_scope=='current' or query.source_scope=='auto' and bool(re.search(r'\b(current|running)\b',query.query,re.I)) and not re.search(r'\b(stored|saved|historical|backup|not the current|not running)\b',query.query,re.I)
        if current:
            return ToolResult(status='unavailable',data={'records':[],'current_available':False},message='The current running configuration source is unavailable. Stored snapshots are a separate historical source; none was substituted.')
        if query.source_scope=='planned':return ToolResult(status='unavailable',message='Intended configuration is not available from the stored-snapshot reader.')
        ids={d['id'] for d in devices}
        with self.db._connect() as c:
            rows=[dict(r) for r in c.execute('SELECT id,device_id,config_text,captured_at,source_type,snapshot_type,owner_username FROM config_snapshots WHERE device_id IN ('+','.join('?' for _ in ids)+') ORDER BY id DESC LIMIT 100',tuple(ids))] if ids else []
        rows=[r for r in rows if (auth.role=='admin' or r['owner_username']==auth.principal) and self.in_range(r,query)]
        for row in rows:
            row['hostname']=next((d['hostname'] for d in devices if d['id']==row['device_id']),None)
            row['config_text']=redact(row['config_text'])[:12000]
            source=str(row.get('source_type') or '').lower()
            row['origin']='simulated' if 'simulat' in source or 'fixture' in source else 'sample' if 'sample' in source else 'stored'
        result=self.result('sqlite.config_snapshots',{'records':rows[:query.limit],'truncated':len(rows)>query.limit,
            'live_available':False,'current_available':False,'coverage':'Stored captures; configurations are truncated to 12000 characters and credential lines removed.'},devices,
            captured=rows[0]['captured_at'] if rows else None,status='success' if rows else 'unavailable',message='' if rows else 'No authorized stored configuration snapshots match this scope.')
        if rows:
            result.evidence=[]
            for origin in sorted({row['origin'] for row in rows[:query.limit]}):
                group=[row for row in rows[:query.limit] if row['origin']==origin]
                refs=self.result('sqlite.config_snapshots',{'records':group},devices,origin=origin,
                    captured=group[0]['captured_at']).evidence
                for ref in refs: ref.time_scope='historical'
                result.evidence.extend(refs)
        return result


def investigation_source_domains(prompt):
    """An explicit evidence list bounds initial reads, not later gap retrieval."""
    clause=re.search(r'\b(?:using|based on|consulting)\s+(.+?)(?:[;!?\n]|$)',prompt,re.I)
    if not clause or re.search(r'\ball\s+(?:available\s+)?(?:sources|evidence|information)\b',clause[1],re.I):return []
    requested=clause[1]
    domains,_=route_network('Read '+requested,{'devices':[]},expand_investigation=False)
    if re.search(r'\b(?:routes?|routing tables?|reachability|forwarding)\b',requested,re.I):domains.append('state')
    domains=list(dict.fromkeys(domains))
    # Unknown/implicit source descriptions remain the semantic planner's job.
    return domains if len(domains)>=2 else []


def route_network(prompt, inventory, *, expand_investigation=True):
    """Bounded domain routing; never recognizes engineering operations or executes actions."""
    from llm.gateway_references import read_intent_text
    prompt=read_intent_text(prompt)
    domains=[]; text=prompt.lower()
    for domain,pattern in [('inventory',r'\b(inventory|devices?|routers?|switches?|interfaces?|vendors?|platforms?)\b'),
        ('topology',r'\b(topology|cabling|paths?|hops?|neighbou?r|links?|connections?|connected|connectivity)\b'),
        ('telemetry',r'\b(telemetry|metrics?|measurements?|counters?|discards?|cpu|memory|traffic|bandwidth|utilization|latency|packet loss|statistics)\b|\b(?:interface|port)\s+(?:(?:input|output)\s+)?errors?\b'),
        ('syslog',r'\b(syslogs?|logs?|logging)\b'),('incidents',r'\b(incidents?|anomal\w*|alerts?|drift|outage|failures?)\b'),
        ('state',r'\b(controllers?|collectors?|source health|collection status)\b|\bprotocol\s+(?:state|observations?|sessions?|adjacenc\w*)\b|'+INTERFACE_OBSERVATION),
        ('configuration',r'\b(configs?|configurations?|running[ .-]?config|snapshots?|backups?)\b')]:
        if re.search(pattern,text): domains.append(domain)
    investigation=bool(re.search(r'\b(investigat\w*|diagnos\w*|root cause|correlat\w*|troubleshoot\w*)\b',text))
    if investigation and expand_investigation:
        # Preserve the explicit legacy rollback path; the enabled shared planner
        # uses the named initial list and can retrieve more after evaluating gaps.
        scoped=investigation_source_domains(prompt) if os.getenv('COGNISHIELD_AI_PLANNING','0')=='1' else []
        domains=scoped or ['inventory','topology','telemetry','syslog','incidents','configuration']
    # Conceptual questions do not need all network records.
    general=bool(re.match(r'\s*(what (is|are|does)|explain|compare|difference|how (does|do|to))\b',text)) and not re.search(r'\b(my|our|this network|current|planned|stored|live|history)\b',text)
    refs=[d['hostname'] for d in inventory['devices'] if any(re.search(r'(?<![\w-])'+re.escape(str(ref))+r'(?![\w-])',prompt,re.I) for ref in [d['hostname'], d.get('management_ip') or '', *d.get('aliases',[])] if ref)]
    recognized_spans=[match.span() for d in inventory['devices'] for ref in [d['hostname'],*d.get('aliases',[])] if ref
        for match in re.finditer(r'(?<![\w-])'+re.escape(ref)+r'(?![\w-])',prompt,re.I)]
    unknown=[match[0] for match in re.finditer(r'\b(?:R|SW|RTR|EDGE|CORE)[-_]?\d+\b',prompt,re.I)
        if not any(left<=match.start() and match.end()<=right for left,right in recognized_spans)]
    refs.extend(unknown)
    from llm.gateway_references import configuration_text_request
    if configuration_text_request(prompt):
        target=re.search(r'\b(?:for|on)\s+(?:(?:device|router|switch)\s+)?[`\"\']?([A-Za-z][\w.:-]{0,99})',prompt,re.I)
        target_name=target[1].rstrip('.') if target else ''
        if target_name and target_name.casefold() not in {'all','each','every','the','that','this','it','its','our','my','these','those'}:
            # A literal target supplied by the user must reach the existing
            # resolver even when unknown. An empty scope means all devices and
            # must not silently replace an unrecorded hostname.
            if not any(target_name.casefold() in {str(ref).casefold() for ref in [d['hostname'],d.get('management_ip'),*d.get('aliases',[])]} for d in inventory['devices']):refs.append(target_name)
    refs=list(dict.fromkeys(refs))[:8]
    from llm.gateway_references import configuration_text_request,configuration_record_request
    if refs and (configuration_record_request(prompt) or configuration_text_request(prompt) and re.search(r'\b(?:saved|stored|running|current)\b',text)):
        domains=list(dict.fromkeys(domains+['configuration']))
    if refs and re.search(r'\b(?:find|identify|determine)\b.{0,60}\b(?:cause|fault|reason)\b',text):
        # A named diagnostic paraphrase is a record investigation, not a
        # request for a generic list of possible networking problems.
        domains=list(dict.fromkeys(domains+['inventory','topology','state','configuration']))
    if refs and re.search(r'\b(ospf|bgp|is-is|isis)\b',text) and re.search(r'\b(adjacenc\w*|neighbou?rs?|peers?|sessions?)\b',text):
        # Inventory and physical links cannot establish protocol adjacency.
        domains=list(dict.fromkeys([d for d in domains if d!='topology']+['state']))
    if refs and re.search(r'\b(?:forward(?:ing)?|return|reverse)\s+(?:paths?|directions?)\b|\b(?:modeled|modelled|simulated)\s+(?:paths?|forwarding)\b|\bbidirectional\s+(?:paths?|reachability|forwarding)\b',text):
        # Graph links alone cannot establish either forwarding direction. The
        # existing state reader supplies scoped model traces/observations.
        domains=list(dict.fromkeys(domains+['topology','state']))
    if general and not refs and not investigation:
        if re.search(r'\b(ospf|bgp|isis|ansible|junos|cisco|juniper|huawei|qos|acl|routing|switching|netconf)\b',text):return ['knowledge'],{'query':prompt[:4000]}
        return [],{}
    if refs and not domains: domains=['inventory']
    # Mentioning absent live evidence is not a request to replace every stored
    # reader with a live collector. Keep this query modifier separate from the
    # semantic capability decision; explicit positive live requests still apply.
    observation_request=re.sub(r'\b(?:missing|unavailable|without|no|lack of|absence of)\s+(?:fresh\s+)?(?:live|real[- ]?time)(?:\s+(?:evidence|data|observations|measurements))?', '', text)
    observation_request=re.sub(r'\b(?:do not|don.t|never)\s+(?:infer|assume|claim)\s+(?:a\s+)?live\b', '', observation_request)
    live=bool(re.search(r'\b(live|real[- ]?time|right now)\b',observation_request))
    dates=re.findall(r'\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2}))?',prompt)
    query={'device_refs':refs,'query':prompt[:4000],'live':live}
    if re.search(r'\b(latest|most recent)\b',text):query['limit']=1
    relative=re.search(r'(?:last|past)\s+(\d+)\s*(minutes?|mins?|hours?|hrs?|days?)',text)
    if relative:
        scale=1440 if relative[2].startswith('day') else 60 if relative[2].startswith(('hour','hr')) else 1
        query['window_minutes']=max(1,min(10080,int(relative[1])*scale))
        anchor=timestamp((inventory.get('scenario') or {}).get('logical_time')) or datetime.now(timezone.utc)
        query['start']=(anchor-timedelta(minutes=query['window_minutes'])).isoformat()
    if dates: query['start']=dates[0] if 'T' in dates[0] else dates[0]+'T00:00:00Z'
    if len(dates)>1: query['end']=dates[1] if 'T' in dates[1] else dates[1]+'T23:59:59Z'
    return domains,query


async def network_context(db, registry, authorization, prompt, domains_override=None,device_refs_override=None,source_requests=None,interface_refs_override=None):
    from llm.gateway_services import inventory_snapshot
    inventory=inventory_snapshot(db)
    domains,query=route_network(prompt,inventory)
    # A validated semantic plan may select a reader even when the legacy
    # heuristic classifies this as general conversation. Never drop its input.
    query.setdefault('query',prompt[:4000])
    if device_refs_override is not None:
        query['device_refs']=device_refs_override
    if domains_override is not None:
        allowed={"inventory","topology","telemetry","syslog","incidents","configuration","knowledge","state"}
        domains=list(dict.fromkeys(domain for domain in domains_override if domain in allowed))
    path_scope=(len(query.get('device_refs',[]))==2 and 'topology' in domains
        and bool({'state','configuration'} & set(domains))
        and bool(re.search(r'\b(paths?|forwarding|communicat\w*|connectivity|reachability)\b',prompt,re.I)))
    if path_scope:domains=['topology']+[d for d in domains if d!='topology']
    path_device_refs=[];path_scope_limitation=None
    contexts=[]; evidence=[]
    for domain in domains:
        effective_query=query
        tool='inventory.read' if domain=='inventory' else 'knowledge.search' if domain=='knowledge' else 'network.'+domain
        if domain=='inventory':
            result=await registry.invoke(tool,{},authorization)
            data=result.data or {'devices':[]}
            references=query.get('device_refs',[])
            if references:
                def matches(d,ref):return str(ref).casefold() in {str(d['id']),d['hostname'].casefold(),str(d['management_ip'] or '').casefold(),*[a.casefold() for a in d.get('aliases',[])]}
                matched=[d for d in data['devices'] if any(matches(d,ref) for ref in references)]
                missing=[ref for ref in references if not any(matches(d,ref) for d in matched)]
                data={**data,'devices':matched,'unresolved_devices':missing}
            for column,choices in [('vendor',['cisco','juniper','huawei']),('role',['core','distribution','access','edge']),('status',['planned','active','offline','staged'])]:
                requested=[choice for choice in choices if re.search(r'\b'+choice+r'\b',prompt,re.I)]
                # A hostname such as Core-Birch is an identity, not a request
                # to filter it out unless its stored role also happens to be core.
                if len(requested)==1 and not references:data={**data,'devices':[d for d in data['devices'] if requested[0] in str(d[column]).lower()]}
            summary={'device_count':len(data['devices']),'interface_count':sum(len(d['interfaces']) for d in data['devices'])}
            for column in ['vendor','role','status','site']:
                summary['by_'+column]={key:sum(str(d[column] or 'unspecified')==key for d in data['devices']) for key in sorted({str(d[column] or 'unspecified') for d in data['devices']})}
            data={**data,'summary':summary,'devices':data['devices'][:100],'truncated':len(data['devices'])>100}
            for ref in result.evidence:
                ref.device_refs=[str(d['id']) for d in data['devices']]
                ref.source_revision=text_digest(json.dumps(data,sort_keys=True))

        else:
            scope=(source_requests or {}).get(domain,{})
            # Source/time intent only, never identity or permission data. An
            # explicit new window replaces the WHOLE old window, including an
            # old end bound when the new request supplies only a start.
            override={k:v for k,v in scope.items() if k in {'source_scope','record_kinds','source_categories','start','end','window_minutes'}}
            if any(key in query for key in ('start','end','window_minutes')):
                override={k:v for k,v in override.items() if k not in {'start','end','window_minutes'}}
            effective_query={**query,**override}
            if domain=='telemetry' and interface_refs_override:
                effective_query['interface_refs']=interface_refs_override
            if domain=='state':
                from development.source_registry import BY_KEY
                categories=effective_query.get('source_categories',[])
                interface_sources=not categories or all(BY_KEY.get(key) and BY_KEY[key].kind in {'interface_state','simulation'} for key in categories)
                if interface_state_request(prompt) and interface_sources:effective_query['record_kinds']=['interface_state']
                elif re.search(OTHER_STATE_TOPIC,prompt,re.I):effective_query.pop('record_kinds',None)
            result=await registry.invoke(tool,effective_query,authorization); data=result.data
        requested=query.get('device_refs',[])
        scoped=[str(d['id']) for d in inventory['devices'] if not requested or any(str(ref).casefold() in {str(d['id']),d['hostname'].casefold(),str(d['management_ip'] or '').casefold(),*[a.casefold() for a in d.get('aliases',[])]} for ref in requested)]
        from llm.gateway_references import source_scope_references
        retained_scope=source_scope_references({domain:{k:v for k,v in effective_query.items()
            if k in {'source_scope','source_categories','record_kinds','start','end','window_minutes'}}})[domain]
        contexts.append({'tool':tool,'status':result.status,'message':result.message,'data':data,'source_request':retained_scope,
            'scope_devices':[{'id':d['id'],'hostname':d['hostname']} for d in inventory['devices'] if str(d['id']) in scoped][:8],
            'device_refs':list(dict.fromkeys(ref for e in result.evidence for ref in e.device_refs)) or scoped,
            'evidence_ids':[e.id for e in result.evidence]})
        for item in result.evidence:
            if effective_query.get('start') or effective_query.get('end'):item.requested_time_range={key:effective_query[key] for key in ['start','end'] if effective_query.get(key)}
        evidence.extend(result.evidence)
        if path_scope and domain=='topology' and result.status=='success' and isinstance(data,dict):
            path=data.get('graph_path')
            if isinstance(path,list) and len(path)>=2:
                # Expand only from the actual authorized graph result. The
                # subsequent existing readers retain their own input/output
                # validation, provenance and permissions; no new reader or
                # guessed transit device is introduced.
                named={d['hostname']:str(d['id']) for d in inventory['devices']}
                if all(isinstance(name,str) and name in named for name in path):
                    refs=list(dict.fromkeys(named[name] for name in path))
                    if len(refs)<=8:
                        path_device_refs=refs;query['device_refs']=refs
                    else:path_scope_limitation='The returned path exceeds the eight-device read scope; transit records are incomplete.'
    total=sum(len(json.dumps(c,default=str)) for c in contexts)
    # Keep each source independently represented when context is bounded.
    per_source=max(1000,24000//max(1,len(contexts)))
    for context in contexts:
        # The knowledge adapter already bounds document count/text and returns
        # typed immutable contracts. A sliced JSON string destroys that shape
        # and fails exact provenance checks. Keep the authoritative read here;
        # synthesis builds its own bounded contract case-file afterwards.
        if context['tool']=='knowledge.search':continue
        encoded=json.dumps(context['data'],default=str)
        budget=max(per_source,10000) if context['tool']=='network.state' else per_source
        if len(encoded)>budget: context['data']=bounded_record_context(context['data'],budget)
    included=sum(len(json.dumps(c,default=str)) for c in contexts)
    return contexts,evidence,{'complete':included>=total and not path_scope_limitation,'total_characters':total,'included_characters':included,'domains':domains,
        **({'path_device_refs':path_device_refs} if path_device_refs else {}),**({'path_scope_limitation':path_scope_limitation} if path_scope_limitation else {})}
