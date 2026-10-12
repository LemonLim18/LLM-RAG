"""Read-through JSON observations. SQLite is always the inventory authority."""
import hashlib
import json
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from datetime import datetime

class Model(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)

class Point(Model):
    time: str
    cpu: float = Field(ge=0, le=100)
    memory: float = Field(ge=0, le=100)
    in_bps: float = Field(default=0, ge=0)
    out_bps: float = Field(default=0, ge=0)
    utilization_pct: float = Field(default=0, ge=0, le=100)
    errors: float = Field(default=0, ge=0)
    discards: float = Field(default=0, ge=0)
    pkts_in_ucast: float = Field(default=0, ge=0)
    pkts_out_ucast: float = Field(default=0, ge=0)
    pkts_in_mcast: float = Field(default=0, ge=0)
    pkts_out_mcast: float = Field(default=0, ge=0)
    pkts_in_bcast: float = Field(default=0, ge=0)
    pkts_out_bcast: float = Field(default=0, ge=0)

    @field_validator('time')
    @classmethod
    def timestamp(cls, value):
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            raise ValueError('timestamp must include timezone')
        return value

class DeviceObservation(Model):
    status: Literal['active','inactive'] = 'active'
    availability: Literal['up','down','unknown'] = 'unknown'
    sysuptime: int = Field(default=0, ge=0, description='SNMP uptime in hundredths of a second')
    metrics: list[Point] = Field(default_factory=list, max_length=5000)

class DeviceOverride(DeviceObservation):
    device_id: int = Field(gt=0)

class InterfaceDefaults(Model):
    admin_status: Literal['up','down','unknown'] = 'unknown'
    oper_status: Literal['up','down','unknown'] = 'unknown'
    speed_bps: float = Field(default=1000000000, gt=0)
    metrics: list[Point] = Field(default_factory=list, max_length=5000)

class InterfaceObservation(InterfaceDefaults):
    device_id: int = Field(gt=0)
    interface_id: int = Field(gt=0)

class Event(Model):
    id: str = Field(min_length=1, max_length=100)
    device_id: int = Field(gt=0)
    timestamp: str
    severity: Literal['info','low','warning','medium','high','critical'] = 'info'
    message: str = Field(min_length=1, max_length=8000)
    kind: str = Field(default='network', max_length=100)
    validate_time = field_validator('timestamp')(Point.timestamp.__func__)

class Alert(Event):
    metric: str = Field(default='cpu', max_length=100)
    value: float = 0
    threshold: float = 80
    status: Literal['active','resolved'] = 'active'

class SnapshotFixture(Model):
    id: str = Field(min_length=1, max_length=100)
    device_id: int = Field(gt=0)
    timestamp: str
    config_text: str = Field(min_length=1, max_length=2000000)
    description: str = Field(default='Simulated configuration', max_length=500)
    validate_time = field_validator('timestamp')(Point.timestamp.__func__)

class Fixture(Model):
    version: Literal[1]
    defaults: DeviceObservation = Field(default_factory=DeviceObservation)
    interface_defaults: InterfaceDefaults = Field(default_factory=InterfaceDefaults)
    event_templates: list['EventTemplate'] = Field(default_factory=list)
    thresholds: list['Threshold'] = Field(default_factory=list)
    devices: list[DeviceOverride] = Field(default_factory=list)
    interfaces: list[InterfaceObservation] = Field(default_factory=list)
    syslog: list[Event] = Field(default_factory=list)
    alerts: list[Alert] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
    snapshots: list[SnapshotFixture] = Field(default_factory=list)

class EventTemplate(Model):
    id: str = Field(min_length=1)
    timestamp: str
    message: str = Field(min_length=1)
    severity: Literal['info','low','warning','medium','high','critical'] = 'info'
    group: Literal['syslog','events'] = 'syslog'
    validate_time = field_validator('timestamp')(Point.timestamp.__func__)

class Threshold(Model):
    metric: Literal['cpu','memory','errors','discards','utilization_pct']
    threshold: float = Field(ge=0)
    severity: Literal['warning','high','critical'] = 'warning'

class FixtureError(ValueError):
    pass

class JsonObservations:
    def __init__(self, directory):
        self.path = Path(directory) / 'observations.json'

    def read(self, db, range_minutes=60):
        try:
            raw = self.path.read_bytes()
            if len(raw) > 10000000:
                raise FixtureError('observations.json exceeds 10 MB')
            payload = json.loads(raw)
            # Optional split files retain the original observation field shapes.
            # Old installations containing only observations.json remain supported.
            for name in ('availability', 'syslog', 'alerts'):
                part = self.path.parent / f'{name}.json'
                if part.exists():
                    content = part.read_bytes()
                    fragment = json.loads(content)
                    allowed = {'availability': {'devices', 'interfaces'}, 'syslog': {'syslog', 'events', 'event_templates'}, 'alerts': {'alerts', 'thresholds'}}[name]
                    if not isinstance(fragment, dict) or set(fragment) - allowed:
                        raise FixtureError(f'{name}.json contains unsupported fields')
                    payload.update(fragment)
                    raw += content
            hours = 1 if range_minutes <= 60 else 6 if range_minutes <= 360 else 24
            metrics = self.path.parent / 'metrics' / f'{hours}h.json'
            if metrics.exists():
                content = metrics.read_bytes()
                fragment = json.loads(content)
                if not isinstance(fragment, dict) or set(fragment) - {'defaults', 'interface_defaults', 'devices', 'interfaces'}:
                    raise FixtureError(f'metrics/{hours}h.json contains unsupported fields')
                for key in ('defaults', 'interface_defaults'):
                    if key in fragment:
                        payload[key] = {**payload.get(key, {}), **fragment[key]}
                for key, identifier in (('devices', 'device_id'), ('interfaces', 'interface_id')):
                    records = {r[identifier]: r for r in payload.get(key, [])}
                    for row in fragment.get(key, []):
                        records[row[identifier]] = {**records.get(row[identifier], {}), **row}
                    payload[key] = list(records.values())
                raw += content
            # Sparse device overlays inherit constant defaults rather than blank metrics.
            for key, default in (('devices', 'defaults'), ('interfaces', 'interface_defaults')):
                payload[key] = [{**payload.get(default, {}), **row} for row in payload.get(key, [])]
            data = Fixture.model_validate(payload, strict=True)
        except (OSError, ValidationError, ValueError, KeyError, TypeError) as exc:
            # Do not echo fixture content (configurations may contain private data).
            detail = '; '.join('.'.join(map(str,e['loc'])) + ': ' + e['type'] for e in exc.errors()) if isinstance(exc, ValidationError) else str(exc)
            raise FixtureError('Invalid simulation observations.json: ' + detail) from exc
        with db._connect() as c:
            devices = {r['id']:dict(r) for r in c.execute('SELECT id,hostname,management_ip,vendor,model,os_version FROM devices')}
            interfaces = {r['id']:dict(r) for r in c.execute('SELECT id,device_id,name FROM interfaces')}
        for group in ('devices','interfaces','syslog','alerts','events','snapshots'):
            seen=set()
            for row in getattr(data,group):
                if row.device_id not in devices:
                    raise FixtureError(f'{group}: unknown SQLite device_id {row.device_id}')
                key = getattr(row,'id', getattr(row,'interface_id',row.device_id))
                if key in seen:
                    raise FixtureError(f'{group}: duplicate reference {key}')
                seen.add(key)
                if group == 'interfaces' and (row.interface_id not in interfaces or interfaces[row.interface_id]['device_id'] != row.device_id):
                    raise FixtureError(f'interfaces: interface_id {row.interface_id} does not belong to device_id {row.device_id}')
        return ObservationSet(data, devices, interfaces, hashlib.sha256(raw).hexdigest())

class ObservationSet:
    def __init__(self, data, devices, interfaces, revision):
        self.data, self.devices, self.interfaces, self.revision = data, devices, interfaces, revision
        self.by_device={r.device_id:r for r in data.devices}
        self.by_interface={r.interface_id:r for r in data.interfaces}

    def device(self, device_id):
        return self.by_device.get(device_id,self.data.defaults)

    def interface(self, interface_id):
        return self.by_interface.get(interface_id,self.data.interface_defaults)

    def metadata(self):
        return dict(source='simulated', provider='json_fixture', fixture_revision=self.revision, live=False)

    def events(self, group):
        result=[]
        entries=list(getattr(self.data,group))
        if group=='alerts':
            for did,d in self.devices.items():
                points=self.device(did).metrics
                if not points: continue
                for rule in self.data.thresholds:
                    value=getattr(points[-1],rule.metric)
                    if value>rule.threshold:
                        entries.append(Alert(id=f'threshold-{did}-{rule.metric}',device_id=did,timestamp=points[-1].time,severity=rule.severity,metric=rule.metric,value=value,threshold=rule.threshold,message=f"{d['hostname']}: simulated {rule.metric} {value} exceeds {rule.threshold}"))
        for template in self.data.event_templates:
            if template.group == group:
                for did,d in self.devices.items():
                    entries.append(Event(id=f'{template.id}-{did}',device_id=did,timestamp=template.timestamp,severity=template.severity,message=template.message.replace('{hostname}',d['hostname'])))
        for e in entries:
            d=self.devices[e.device_id]
            result.append({**e.model_dump(), **self.metadata(), 'hostname':d['hostname'], 'device_hostname':d['hostname'],
                'source_ip':d['management_ip'], 'device':d['management_ip'] or d['hostname'],
                'received_at':e.timestamp, 'created_at':e.timestamp, 'last_seen':e.timestamp,
                'raw_message':e.message, 'severity_label':e.severity})
        return result

    def bundle(self, device='', interface=''):
        summaries=[]; snapshots=[]; history={k:[] for k in ('cpu','memory','interface_traffic','interface_out','errors','discards','utilization','if_speed')}
        mapping={'cpu':'cpu','memory':'memory','interface_traffic':'in_bps','interface_out':'out_bps','errors':'errors','discards':'discards','utilization':'utilization_pct'}
        mapping.update({k:k for k in ('pkts_in_ucast','pkts_out_ucast','pkts_in_mcast','pkts_out_mcast','pkts_in_bcast','pkts_out_bcast')})
        history.update({k:[] for k in mapping if k not in history})
        for did,d in self.devices.items():
            key=d['management_ip'] or d['hostname']
            if device and device not in (key,d['hostname']): continue
            obs=self.device(did); points=obs.metrics
            ifaces=[i for i in self.interfaces.values() if i['device_id']==did]
            last=points[-1] if points else None
            up=sum(self.interface(i['id']).oper_status=='up' for i in ifaces)
            down=sum(self.interface(i['id']).oper_status=='down' for i in ifaces)
            summaries.append({**d, 'mgmt_ip':key, 'status':'up' if obs.availability=='up' else obs.availability,
                'cpu':last.cpu if last else None, 'memory':last.memory if last else None,
                'cpu_source':'simulated','memory_source':'simulated', 'source':'simulated','sample':True,'sysuptime':obs.sysuptime,
                'interfaces_admin_up':sum(self.interface(i['id']).admin_status=='up' for i in ifaces),
                'last_polled':last.time if last else None, 'errors':last.errors if last else 0,
                'discards':last.discards if last else 0, 'interfaces_total':len(ifaces),
                'interfaces_up':up,'interfaces_down':down, 'interfaces_oper_up':up,'interfaces_oper_down':down})
            for p in points:
                for name,attr in mapping.items():
                    if name in ('cpu','memory') or not ifaces:
                        history[name].append(dict(time=p.time,device=key,field=name,value=getattr(p,attr),basis='simulated',source='simulated'))
            for i in ifaces:
                if interface and i['name']!=interface: continue
                io=self.interface(i['id'])
                ipoints=io.metrics if io else []
                for p in ipoints:
                    for name,attr in mapping.items():
                        if name in ('cpu','memory'): continue
                        history[name].append(dict(time=p.time,device=key,interface=i['name'],field=name,value=getattr(p,attr),basis='simulated',source='simulated'))
                    history['if_speed'].append(dict(time=p.time,device=key,interface=i['name'],field='if_speed',value=io.speed_bps,basis='simulated'))
                latest=ipoints[-1] if ipoints else None
                snapshots.append(dict(device=key,interface=i['name'],source='simulated',
                    admin_status_label=io.admin_status.title() if io else 'Unknown',
                    oper_status_label=io.oper_status.title() if io else 'Unknown',
                    in_octets=latest.in_bps if latest else 0,out_octets=latest.out_bps if latest else 0,
                    in_packets=(latest.pkts_in_ucast+latest.pkts_in_mcast+latest.pkts_in_bcast) if latest else 0,
                    out_packets=(latest.pkts_out_ucast+latest.pkts_out_mcast+latest.pkts_out_bcast) if latest else 0,errors=latest.errors if latest else 0,
                    discards=latest.discards if latest else 0,speed=io.speed_bps if io else None,
                    last_seen=latest.time if latest else None))
        return {**self.metadata(),'sample':True,'summary':{'devices':summaries},
            'history':{'data':history},'interfaces':{'interfaces':snapshots},
            'hostnames':{'hostnames':{d['management_ip'] or d['hostname']:d['hostname'] for d in self.devices.values()}}}
