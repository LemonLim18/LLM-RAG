"""Bounded, read-only network context; source labels survive routing and synthesis."""
from collections import deque
from datetime import datetime, timezone, timedelta
import json
import os
import re
from typing import Literal
from uuid import uuid4

from pydantic import Field, field_validator, model_validator
from llm.gateway_models import Evidence, StrictModel, ToolResult, text_digest

READ_TOOLS = frozenset({'inventory.read', 'network.topology', 'network.telemetry',
    'network.syslog', 'network.incidents', 'network.configuration', 'knowledge.search'})


class NetworkQuery(StrictModel):
    device_refs: list[str] = Field(default_factory=list, max_length=8)
    query: str = Field(default='', max_length=4000)
    limit: int = Field(default=30, ge=1, le=100)
    start: str | None = None
    end: str | None = None
    live: bool = False
    window_minutes: int = Field(default=60,ge=1,le=10080)

    @field_validator('start','end')
    @classmethod
    def validate_time(cls,value):
        if value and (len(value)>50 or not timestamp(value)):raise ValueError('Invalid time range timestamp')
        return value

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


def redact(text):
    return re.sub(r'(?im)^([^\n]*(?:password|secret|community|private-key|authentication-key)[^\n]*).*$', '[credential line redacted]', str(text))


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
        if query.live:
            return self.live(domain,query,devices,authorization)
        if domain=='topology': return self.topology(query,devices,inventory)
        if domain=='configuration': return self.configuration(query,devices,authorization)
        if domain=='knowledge':
            from llm.gateway_knowledge import documentation_context
            documents, evidence=documentation_context(query.query)
            return ToolResult(status='success' if documents else 'unavailable',data=documents,evidence=evidence,
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
        ids={d['id'] for d in devices}; interfaces={i['id']:i for d in inventory['devices'] for i in d['interfaces']}
        names={d['id']:d['hostname'] for d in inventory['devices']}
        links=[dict(link,source=names.get(link['src_device_id']),target=names.get(link['dst_device_id']),
            source_interface=interfaces.get(link['src_interface_id'],{}).get('name'),target_interface=interfaces.get(link['dst_interface_id'],{}).get('name')) for link in inventory['links']]
        path=None
        if len(devices)==2:
            queue=deque([(devices[0]['id'],[devices[0]['id']])]); seen=set()
            while queue:
                node, trail=queue.popleft()
                if node==devices[1]['id']: path=[names[i] for i in trail]; break
                if node in seen: continue
                seen.add(node)
                for link in links:
                    if node in (link['src_device_id'],link['dst_device_id']):
                        other=link['dst_device_id'] if node==link['src_device_id'] else link['src_device_id']
                        if other not in seen: queue.append((other,trail+[other]))
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
        from lab_config import FIXTURE_DIR
        from local_providers.observations import JsonObservations, FixtureError
        ids={d['id'] for d in devices}; results=[]
        try:
            obs=JsonObservations(FIXTURE_DIR).read(self.db,range_minutes=1440)
            if domain=='telemetry':
                rows=[]
                for device in devices:
                    for point in obs.device(device['id']).metrics:
                        value={key:getattr(point,key) for key in point.model_fields_set}
                        rows.append({'device_id':device['id'],'hostname':device['hostname'],**value})
                    for interface in device['interfaces']:
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
        ids={d['id'] for d in devices}
        with self.db._connect() as c:
            rows=[dict(r) for r in c.execute('SELECT id,device_id,config_text,captured_at,source_type,snapshot_type,owner_username FROM config_snapshots WHERE device_id IN ('+','.join('?' for _ in ids)+') ORDER BY id DESC LIMIT 100',tuple(ids))] if ids else []
        rows=[r for r in rows if (auth.role=='admin' or r['owner_username']==auth.principal) and self.in_range(r,query)]
        for row in rows:
            row['config_text']=redact(row['config_text'])[:12000]
            source=str(row.get('source_type') or '').lower()
            row['origin']='simulated' if 'simulat' in source or 'fixture' in source else 'sample' if 'sample' in source else 'stored'
        result=self.result('sqlite.config_snapshots',{'records':rows[:query.limit],'truncated':len(rows)>query.limit,
            'live_available':False,'coverage':'Stored captures; configurations are truncated to 12000 characters and credential lines removed.'},devices,
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


def route_network(prompt, inventory):
    """Bounded domain routing; never recognizes engineering operations or executes actions."""
    domains=[]; text=prompt.lower()
    for domain,pattern in [('inventory',r'\b(inventory|devices?|routers?|switches?|interfaces?|vendors?|platforms?)\b'),
        ('topology',r'\b(topology|path|neighbou?r|links?|connected|connectivity)\b'),
        ('telemetry',r'\b(telemetry|metrics?|cpu|memory|traffic|bandwidth|utilization|latency|packet loss|statistics)\b'),
        ('syslog',r'\b(syslog|logs?|logging)\b'),('incidents',r'\b(incidents?|anomal\w*|alerts?|drift|outage|failures?)\b'),
        ('configuration',r'\b(configurations?|running.config|config history|snapshots?|backups?)\b')]:
        if re.search(pattern,text): domains.append(domain)
    investigation=bool(re.search(r'\b(investigat\w*|diagnos\w*|root cause|correlat\w*|troubleshoot\w*)\b',text))
    if investigation: domains=['inventory','topology','telemetry','syslog','incidents','configuration']
    # Conceptual questions do not need all network records.
    general=bool(re.match(r'\s*(what (is|are|does)|explain|compare|difference|how (does|do|to))\b',text)) and not re.search(r'\b(my|our|this network|current|planned|stored|live|history)\b',text)
    refs=[d['hostname'] for d in inventory['devices'] if any(re.search(r'(?<![\w-])'+re.escape(str(ref))+r'(?![\w-])',prompt,re.I) for ref in [d['hostname'], d.get('management_ip') or '', *d.get('aliases',[])] if ref)]
    unknown=[name for name in re.findall(r'\b(?:R|SW|RTR|EDGE|CORE)[-_]?\d+\b',prompt,re.I) if not any(name.casefold() in {d['hostname'].casefold(), *[alias.casefold() for alias in d.get('aliases',[])]} for d in inventory['devices'])]
    refs.extend(unknown)
    refs=list(dict.fromkeys(refs))[:8]
    if general and not refs and not investigation:
        if re.search(r'\b(ospf|bgp|isis|ansible|junos|cisco|juniper|huawei|qos|acl|routing|switching|netconf)\b',text):return ['knowledge'],{'query':prompt[:4000]}
        return [],{}
    if refs and not domains: domains=['inventory']
    live=bool(re.search(r'\b(live|real[- ]?time|right now)\b',text))
    dates=re.findall(r'\d{4}-\d{2}-\d{2}(?:T[\d:.]+Z)?',prompt)
    query={'device_refs':refs,'query':prompt[:4000],'live':live}
    relative=re.search(r'(?:last|past)\s+(\d+)\s*(minutes?|mins?|hours?|hrs?|days?)',text)
    if relative:
        scale=1440 if relative[2].startswith('day') else 60 if relative[2].startswith(('hour','hr')) else 1
        query['window_minutes']=max(1,min(10080,int(relative[1])*scale))
        query['start']=(datetime.now(timezone.utc)-timedelta(minutes=query['window_minutes'])).isoformat()
    if dates: query['start']=dates[0] if 'T' in dates[0] else dates[0]+'T00:00:00Z'
    if len(dates)>1: query['end']=dates[1] if 'T' in dates[1] else dates[1]+'T23:59:59Z'
    return domains,query


async def network_context(db, registry, authorization, prompt, domains_override=None):
    from llm.gateway_services import inventory_snapshot
    inventory=inventory_snapshot(db)
    domains,query=route_network(prompt,inventory)
    if domains_override is not None:
        allowed={"inventory","topology","telemetry","syslog","incidents","configuration","knowledge"}
        domains=list(dict.fromkeys(domain for domain in domains_override if domain in allowed))
    contexts=[]; evidence=[]
    for domain in domains:
        tool='inventory.read' if domain=='inventory' else 'knowledge.search' if domain=='knowledge' else 'network.'+domain
        if domain=='inventory':
            result=await registry.invoke(tool,{},authorization)
            data=result.data
            references=query.get('device_refs',[])
            if references:
                matched=[d for d in data['devices'] if d['hostname'] in references]
                missing=[name for name in references if name not in {d['hostname'] for d in matched}]
                data={**data,'devices':matched,'unresolved_devices':missing}
            for column,choices in [('vendor',['cisco','juniper','huawei']),('role',['core','distribution','access','edge']),('status',['planned','active','offline','staged'])]:
                requested=[choice for choice in choices if re.search(r'\b'+choice+r'\b',prompt,re.I)]
                if len(requested)==1:data={**data,'devices':[d for d in data['devices'] if requested[0] in str(d[column]).lower()]}
            summary={'device_count':len(data['devices']),'interface_count':sum(len(d['interfaces']) for d in data['devices'])}
            for column in ['vendor','role','status','site']:
                summary['by_'+column]={key:sum(str(d[column] or 'unspecified')==key for d in data['devices']) for key in sorted({str(d[column] or 'unspecified') for d in data['devices']})}
            data={**data,'summary':summary,'devices':data['devices'][:100],'truncated':len(data['devices'])>100}

        else:
            result=await registry.invoke(tool,query,authorization); data=result.data
        contexts.append({'tool':tool,'status':result.status,'message':result.message,'data':data,'evidence_ids':[e.id for e in result.evidence]})
        for item in result.evidence:
            if query.get('start') or query.get('end'):item.requested_time_range={key:query[key] for key in ['start','end'] if query.get(key)}
        evidence.extend(result.evidence)
    total=sum(len(json.dumps(c,default=str)) for c in contexts)
    # Keep each source independently represented when context is bounded.
    per_source=max(1000,24000//max(1,len(contexts)))
    for context in contexts:
        encoded=json.dumps(context['data'],default=str)
        if len(encoded)>per_source: context['data']={'excerpt':encoded[:per_source],'truncated':True}
    included=sum(len(json.dumps(c,default=str)) for c in contexts)
    return contexts,evidence,{'complete':included>=total,'total_characters':total,'included_characters':included,'domains':domains}
