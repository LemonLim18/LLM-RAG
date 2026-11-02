"""Explicit local-development scenario authority. Never writes ordinary inventory.

One atomic JSON control file holds selection, editable versions and captures.
All consumers project the same validated revision through existing contracts.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import threading
from contextlib import contextmanager
from contextvars import ContextVar
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field, model_validator
from fastapi import HTTPException
from development.network_model import NetworkModel

BASE = Path(__file__).resolve().parents[1]/'development/scenarios'
_pins=ContextVar('development_scenario_read_pins',default={})
_asset_pins=ContextVar('development_scenario_asset_pins',default={})


class Model(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)


class Device(Model):
    id: int = Field(gt=0)
    hostname: str = Field(pattern=r'^[\w.-]{1,80}$')
    management_ip: str
    vendor: str
    os_version: str
    model: str = ''
    role: str = 'edge'
    site: str = 'Development'
    location: str = ''
    status: str = 'active'
    aliases: list[str] = Field(default_factory=list,max_length=20)
    engineering_facts: dict = Field(default_factory=dict)


class Interface(Model):
    id: int = Field(gt=0)
    device_id: int
    name: str = Field(min_length=1,max_length=100)
    interface_type: str = 'routed'
    prefix: str | None = None
    admin_status: str = Field(default='unknown',pattern='^(up|down|unknown)$')
    oper_status: str = Field(default='unknown',pattern='^(up|down|unknown)$')
    vrf: str = Field(default='default',min_length=1,max_length=80)
    speed_bps: int | None = Field(default=None,gt=0)


class Link(Model):
    id: int
    src_device_id: int
    src_interface_id: int
    dst_device_id: int
    dst_interface_id: int


class ObservedEndpoints(Model):
    """Device-scoped observed identities; no dependency on a planned link."""
    src_device_id: int = Field(gt=0)
    src_interface_id: int = Field(gt=0)
    dst_device_id: int = Field(gt=0)
    dst_interface_id: int = Field(gt=0)


def observation_endpoints(planned_links,values):
    if 'endpoints' in values:
        return ObservedEndpoints.model_validate(values['endpoints']).model_dump(),'authored_observation'
    link=next((link for link in planned_links if link['id']==values.get('link_id')),None)
    return (link,'planned_link_reference') if link else (None,'unresolved')


class Record(Model):
    id: str = Field(min_length=1,max_length=100)
    device_id: int
    interface_id: int | None = None
    timestamp: str
    kind: str
    source: str
    current: bool = True
    depends_on: list[str] = Field(default_factory=list,max_length=30)
    values: dict = Field(default_factory=dict)

    @model_validator(mode='after')
    def json_values(self):
        json.dumps(self.values,allow_nan=False)
        return self


class Scenario(Model):
    format_version: int = Field(default=1,ge=1,le=2)
    id: str = Field(pattern=r'^[A-Z0-9][A-Z0-9_-]{0,79}$')
    revision: int = Field(ge=1)
    title: str = Field(max_length=150)
    logical_time: str
    model_scope: str = Field(pattern='^(direct_link|bounded_routed_path|ipv4_observation)$')
    inventory_complete: bool = False
    devices: list[Device] = Field(max_length=100)
    interfaces: list[Interface] = Field(max_length=1000)
    planned_links: list[Link] = Field(max_length=1000)
    records: dict[str,list[Record]]
    availability: dict[str,bool]
    network: NetworkModel | None = None
    source_statuses: dict = Field(default_factory=dict)
    source_manifest: dict = Field(default_factory=dict)
    unavailable_record_refs: dict[str,str] = Field(default_factory=dict,max_length=3000)

    @model_validator(mode='after')
    def coherent_references(self):
        def stamp(value):
            t=datetime.fromisoformat(value.replace('Z','+00:00'))
            if not t.tzinfo:raise ValueError('Timestamps require an explicit timezone')
            return t
        now=stamp(self.logical_time)
        if self.format_version==2 and self.network is None:raise ValueError('Version 2 requires typed network observations')
        if self.network:
            if self.format_version!=2 or self.model_scope!='ipv4_observation':raise ValueError('Expanded network model requires version 2 and ipv4_observation scope')
            self.network.validate_references(self.devices,self.interfaces,now)
        ds={d.id for d in self.devices};ifs={i.id:i for i in self.interfaces}
        if len(ds)!=len(self.devices) or len(ifs)!=len(self.interfaces):raise ValueError('Duplicate device/interface identity')
        if len({d.hostname.casefold() for d in self.devices})!=len(ds):raise ValueError('Duplicate hostname')
        aliases={}
        for device in self.devices:
            for name in {device.hostname.casefold(),*[a.casefold() for a in device.aliases]}:
                if name in aliases and aliases[name]!=device.id:raise ValueError('Ambiguous device alias')
                aliases[name]=device.id
        if len({(i.device_id,i.name.casefold()) for i in self.interfaces})!=len(ifs):raise ValueError('Duplicate device-scoped interface')
        for d in self.devices:ipaddress.ip_address(d.management_ip)
        for i in self.interfaces:
            if i.device_id not in ds:raise ValueError('Unknown interface owner')
            if i.prefix:ipaddress.ip_interface(i.prefix)
        for link in self.planned_links:
            for device,interface in [(link.src_device_id,link.src_interface_id),(link.dst_device_id,link.dst_interface_id)]:
                if interface not in ifs or ifs[interface].device_id!=device:raise ValueError('Link endpoint is not on its device')
        allowed={'state','telemetry','syslog','incidents','configuration','running_configuration','topology'}
        if set(self.records)-allowed or set(self.availability)-allowed:raise ValueError('Unknown source domain')
        rows=[r for values in self.records.values() for r in values]
        if len(rows)>3000 or len({r.id for r in rows})!=len(rows):raise ValueError('Record count or identity limit')
        ids={r.id for r in rows}
        unavailable=self.unavailable_record_refs
        if set(unavailable)&ids or any(len(identity)>100 or category not in self.source_statuses or
                self.source_statuses[category].get('status') not in {'MISSING','UNAVAILABLE','ERROR','UNSUPPORTED','NOT_QUERIED'}
                for identity,category in unavailable.items()):raise ValueError('Invalid unavailable source reference')
        for row in rows:
            if row.device_id not in ds or row.interface_id and (row.interface_id not in ifs or ifs[row.interface_id].device_id!=row.device_id):raise ValueError('Invalid observation scope')
            if stamp(row.timestamp)>now:raise ValueError('Observation is later than logical simulation time')
            if set(row.depends_on)-ids-set(unavailable) or row.id in row.depends_on:raise ValueError('Invalid evidence dependency')
            if row.kind=='observed_link' and 'endpoints' in row.values:
                ends=ObservedEndpoints.model_validate(row.values['endpoints'])
                pairs=[(ends.src_device_id,ends.src_interface_id),(ends.dst_device_id,ends.dst_interface_id)]
                if pairs[0]==pairs[1]:raise ValueError('Observed endpoints must identify different ports')
                if row.device_id not in {device for device,_ in pairs}:raise ValueError('Observed endpoint owner must be one of its devices')
                if row.interface_id is not None and (row.device_id,row.interface_id) not in pairs:raise ValueError('Observed interface scope must match an endpoint')
                for device,interface in pairs:
                    if interface not in ifs or ifs[interface].device_id!=device:raise ValueError('Observed endpoint interface is not recorded on its device')
            if row.kind=='protocol_observation':
                from development.network_model import recorded_protocol_model
                observation=recorded_protocol_model(row.values,row.timestamp)
                if observation:
                    observation.validate_references(self.devices,self.interfaces,now)
                    session=(observation.ospf or observation.bgp)[0]
                    if row.device_id not in {session.left.device_id,session.right.device_id}:raise ValueError('Protocol observation owner must be one of its endpoints')
        # Cycles would make derived evidence appear independent.
        dependencies={r.id:r.depends_on for r in rows}
        visited=set()
        def visit(key,trail):
            if key in visited:return
            if len(trail)>80:raise ValueError('Evidence dependency depth exceeds 80')
            if key in trail:raise ValueError('Cyclic observation dependencies')
            # Unavailable declared references are terminal identities; no
            # content or dependency chain was retrieved from their sources.
            for parent in dependencies.get(key,[]):visit(parent,trail|{key})
            visited.add(key)
        for key in dependencies:visit(key,set())
        return self


def active_for(db):
    from lab_config import LOCAL_LAB
    manager=getattr(db,'_development_scenario',None)
    if not LOCAL_LAB or not manager:return None
    if id(manager) in _pins.get():return manager
    permitted=os.getenv('COGNISHIELD_DEV_SIMULATION')=='1' or os.getenv('COGNISHIELD_DEV_WORKBENCH')=='1'
    return manager if permitted and manager.is_enabled() else None


def attach(db):
    from lab_config import LOCAL_LAB,PROJECT_DIR
    if LOCAL_LAB and (os.getenv('COGNISHIELD_DEV_SIMULATION')=='1' or os.getenv('COGNISHIELD_DEV_WORKBENCH')=='1'):
        target=Path(os.getenv('COGNISHIELD_DEV_STATE',str(PROJECT_DIR/'tmp/development-network/state.json'))).resolve()
        if not target.is_relative_to(PROJECT_DIR):raise ValueError('Development state must remain inside this workspace')
        db._development_scenario=ScenarioManager(target,enabled_default=os.getenv('COGNISHIELD_DEV_SIMULATION')=='1')
        if os.getenv('COGNISHIELD_DEV_SIMULATION')!='1':
            manager=db._development_scenario
            with manager.lock:
                state=manager._read()
                if 'enabled' not in state:
                    state['enabled']=False;manager._write(state)


class ScenarioManager:
    def __init__(self,path,enabled_default=True):
        self.path=Path(path);self.lock=threading.RLock()
        self.library={p.stem:Scenario.model_validate_json(p.read_text()).model_dump() for p in sorted(BASE.glob('*.json'))}
        if not self.library:raise ValueError('Scenario library is empty')
        self.path.parent.mkdir(parents=True,exist_ok=True)
        if not self.path.exists():self._write({'version':1,'epoch':1,'enabled':enabled_default,'selected':os.getenv('COGNISHIELD_DEV_SCENARIO','HEALTHY-001'),'scenarios':deepcopy(self.library)})

    def is_enabled(self):
        with self.lock:return self._read().get('enabled',True)

    def deactivate(self,*,owner,expected_active):
        with self.lock:
            scenario,context=self.snapshot(fresh=True)
            if context['source_revision']!=expected_active:raise HTTPException(409,'Scenario changed before deactivation')
            state=self._read();self._archive(state,scenario,context,owner);state['enabled']=False;state['epoch']+=1
            state['workbench_deactivation']={'owner':owner,'at':datetime.now(timezone.utc).isoformat()};self._write(state)

    def list_drafts(self,*,owner):
        with self.lock:return [{k:r[k] for k in ['draft_id','draft_revision','updated_at','validation_hash']}|{'scenario_id':r['bundle']['manifest']['scenario_id']}
            for r in self._read().get('workbench_drafts',{}).values() if r['owner']==owner]

    def _read(self):
        if self.path.stat().st_size>16000000:raise HTTPException(413,'Scenario store exceeds 16 MB')
        data=json.loads(self.path.read_text())
        if data.get('version')!=1 or data['selected'] not in data['scenarios']:raise HTTPException(503,'Development state needs recovery; no fixture fallback')
        return data

    def _write(self,data):
        payload=json.dumps(data,indent=2).encode('utf-8')
        if len(payload)>16_000_000:raise HTTPException(413,'Scenario store quota exceeded; existing state remains unchanged')
        temporary=self.path.with_suffix('.'+uuid4().hex+'.tmp')
        temporary.write_bytes(payload);os.replace(temporary,self.path)

    def activated_bundle(self):
        """Sealed source bytes, never the mutable draft or a filesystem path."""
        if id(self) in _asset_pins.get():return deepcopy(_asset_pins.get()[id(self)])
        with self.lock:
            state=self._read()
            if not state['scenarios'][state['selected']].get('source_manifest'):return None
            bundle=state.get('workbench_bundles',{}).get(state['selected'])
            expected=state['scenarios'][state['selected']].get('source_manifest',{}).get('bundle_digest')
            if expected and (not bundle or hashlib.sha256(json.dumps(bundle,sort_keys=True).encode()).hexdigest()!=expected):
                raise HTTPException(503,'Activated scenario source bytes failed integrity verification; no alternate source was substituted')
            return deepcopy(bundle)

    def snapshot(self,*,fresh=False):
        pinned=_pins.get().get(id(self))
        if pinned is not None and not fresh:return deepcopy(pinned)
        with self.lock:
            state=self._read();s=Scenario.model_validate(state['scenarios'][state['selected']]).model_dump()
            digest=hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest()
            return s,{'id':s['id'],'revision':s['revision'],'epoch':state['epoch'],'source_revision':str(state['epoch'])+':'+digest,'logical_time':s['logical_time'],'model_scope':s['model_scope'],'authoritative_development':True,
                'mode':'development_scenario','origin':'simulated','virtual_now':s['logical_time']}

    @contextmanager
    def pin(self):
        """One immutable revision/clock per async gateway turn, even on activation."""
        with self.lock:value=self.snapshot();bundle=self.activated_bundle()
        token=_pins.set({**_pins.get(),id(self):value})
        asset_token=_asset_pins.set({**_asset_pins.get(),id(self):bundle})
        try:yield value[1]
        finally:_pins.reset(token);_asset_pins.reset(asset_token)

    def save_draft(self,bundle,*,owner,expected,draft_id=None):
        from development.bundles import compile_bundle
        if len(json.dumps(bundle).encode())>4_000_000:raise HTTPException(413,'Workbench draft exceeds4MB')
        # Drafts can be incomplete, but malformed manifest/registry never enters
        # the store. Full cross-source checks run in the separate Validate step.
        from development.bundles import Manifest,SourceFile
        from development.source_registry import BY_KEY
        Manifest.model_validate(bundle['manifest'])
        if set(bundle['sources'])!=set(BY_KEY):raise ValueError('Draft requires all24 source files')
        for source in bundle['sources'].values():SourceFile.model_validate(source)
        with self.lock:
            state=self._read();drafts=state.setdefault('workbench_drafts',{})
            if draft_id:
                old=drafts.get(draft_id)
                if not old or old['owner']!=owner:raise HTTPException(404,'Owned scenario draft not found')
                if old['draft_revision']!=expected:raise HTTPException(409,'Draft changed; reload before saving')
                version=old['draft_revision']+1
            else:
                if expected is not None:raise HTTPException(409,'New draft has no previous revision')
                if len(drafts)>=40:raise HTTPException(413,'Workbench draft retention limit40')
                draft_id=uuid4().hex;version=1
            entry={'draft_id':draft_id,'owner':owner,'draft_revision':version,'bundle':deepcopy(bundle),
                'updated_at':datetime.now(timezone.utc).isoformat(),'validation_hash':None}
            drafts[draft_id]=entry;self._write(state)
            return deepcopy(entry)

    def get_draft(self,draft_id,*,owner):
        with self.lock:
            entry=self._read().get('workbench_drafts',{}).get(draft_id)
            if not entry or entry['owner']!=owner:raise HTTPException(404,'Owned scenario draft not found')
            return deepcopy(entry)

    def validate_draft(self,draft_id,*,owner,expected):
        from development.bundles import compile_bundle
        with self.lock:
            entry=self.get_draft(draft_id,owner=owner)
            if entry['draft_revision']!=expected:raise HTTPException(409,'Draft changed before validation')
            scenario=compile_bundle(entry['bundle'])
            digest=hashlib.sha256(json.dumps(entry['bundle'],sort_keys=True).encode()).hexdigest()
            state=self._read();state['workbench_drafts'][draft_id]['validation_hash']=digest;self._write(state)
            return {'valid':True,'validation_hash':digest,'draft_revision':expected,'scenario_id':scenario['id'],
                'sources':len(scenario['source_statuses']),'virtual_now':scenario['logical_time']}

    @staticmethod
    def _history_id(entry):
        return entry.get('id') or hashlib.sha256(json.dumps({key:entry.get(key) for key in ['context','timestamp','replaced_by']},sort_keys=True).encode()).hexdigest()[:32]

    @staticmethod
    def _history_problem(entry):
        """Verify recorded bytes; never substitute today's files for lost history."""
        try:
            scenario=entry['scenario'];context=entry['context']
            expected=context['source_revision'].split(':',1)[1]
            if hashlib.sha256(json.dumps(scenario,sort_keys=True).encode()).hexdigest()!=expected:
                return 'Recorded scenario integrity failed'
            Scenario.model_validate(scenario)
            bundle=entry.get('bundle');manifest=scenario.get('source_manifest',{})
            if manifest and bundle is None:return 'This older entry has no archived source files'
            if bundle is not None:
                expected=manifest.get('bundle_digest') or entry.get('bundle_hash')
                if not expected or hashlib.sha256(json.dumps(bundle,sort_keys=True).encode()).hexdigest()!=expected:
                    return 'Recorded source-file integrity failed'
                if bundle.get('manifest',{}).get('scenario_id')!=scenario['id']:return 'Recorded scenario and files have different identities'
        except (ValueError,KeyError,TypeError,IndexError,AttributeError):return 'Recorded scenario needs migration or recovery'
        return ''

    def _archive(self,state,scenario,context,owner):
        bundle=deepcopy(state.get('workbench_bundles',{}).get(scenario['id'])) if scenario.get('source_manifest') else None
        entry={'id':uuid4().hex,'scenario':deepcopy(scenario),'context':deepcopy(context),
            'replaced_by':owner,'timestamp':datetime.now(timezone.utc).isoformat(),
            'was_enabled':state.get('enabled',True),'bundle':bundle,
            'bundle_hash':hashlib.sha256(json.dumps(bundle,sort_keys=True).encode()).hexdigest() if bundle is not None else None}
        if problem:=self._history_problem(entry):entry['integrity_problem']=problem
        state['workbench_history']=(state.get('workbench_history',[])+[entry])[-20:]

    def history(self,*,owner):
        """Owner-bound metadata only; sealed contents never leave this endpoint."""
        with self.lock:
            rows=[]
            for entry in reversed(self._read().get('workbench_history',[])):
                if not isinstance(entry,dict) or entry.get('replaced_by')!=owner:continue
                scenario=entry.get('scenario',{});problem=self._history_problem(entry)
                if not isinstance(scenario,dict):scenario={}
                rows.append({'id':self._history_id(entry),'scenario_id':scenario.get('id'),
                    'title':scenario.get('title'),'revision':scenario.get('revision'),
                    'virtual_now':scenario.get('logical_time'),'recorded_at':entry.get('timestamp'),
                    'restorable':not problem,'reason':problem,'has_source_pack':entry.get('bundle') is not None,'was_enabled':entry.get('was_enabled')})
            return rows

    def copy_history_draft(self,history_id,*,owner):
        from development.bundles import compile_bundle
        with self.lock:
            entry=next((row for row in self._read().get('workbench_history',[]) if row.get('replaced_by')==owner and self._history_id(row)==history_id),None)
            if not entry:raise HTTPException(404,'Owned recorded scenario revision not found')
            if problem:=self._history_problem(entry):raise HTTPException(409,problem)
            if entry.get('bundle') is None:raise HTTPException(409,'This legacy revision has no source pack to copy')
            compile_bundle(entry['bundle'])
            return self.save_draft(deepcopy(entry['bundle']),owner=owner,expected=None)

    def restore_history(self,history_id,*,owner,expected_active):
        from development.bundles import compile_bundle
        with self.lock:
            state=self._read()
            entry=next((row for row in state.get('workbench_history',[]) if row.get('replaced_by')==owner and self._history_id(row)==history_id),None)
            if not entry:raise HTTPException(404,'Owned recorded scenario revision not found')
            current,context=self.snapshot(fresh=True)
            if context['source_revision']!=expected_active:raise HTTPException(409,'Active scenario changed; inspect it before restoring')
            if problem:=self._history_problem(entry):raise HTTPException(409,problem)
            restored=Scenario.model_validate(deepcopy(entry['scenario'])).model_dump();bundle=deepcopy(entry.get('bundle'))
            if bundle is not None:compile_bundle(bundle)  # Current schema/path/policy contracts still apply.
            self._archive(state,current,context,owner)
            old=state['scenarios'].get(restored['id'],{})
            restored['revision']=max(restored['revision'],old.get('revision',0))+1
            state['scenarios'][restored['id']]=restored;state['selected']=restored['id'];state['epoch']+=1
            state['enabled']=True  # Explicit Restore-as-active action, never model-selected.
            if bundle is None:state.setdefault('workbench_bundles',{}).pop(restored['id'],None)
            else:state.setdefault('workbench_bundles',{})[restored['id']]=bundle
            state['workbench_activation']={'owner':owner,'history_id':history_id,'restored_at':datetime.now(timezone.utc).isoformat()}
            self._write(state)
            return self.snapshot(fresh=True)

    def activate_draft(self,draft_id,*,owner,expected,expected_active,validation_hash):
        from development.bundles import compile_bundle
        with self.lock:
            entry=self.get_draft(draft_id,owner=owner)
            if entry['draft_revision']!=expected:raise HTTPException(409,'Draft changed before activation')
            digest=hashlib.sha256(json.dumps(entry['bundle'],sort_keys=True).encode()).hexdigest()
            if digest!=validation_hash or entry['validation_hash']!=digest:raise HTTPException(409,'Validate this exact draft before activation')
            current,meta=self.snapshot(fresh=True)
            if meta['source_revision']!=expected_active:raise HTTPException(409,'Active scenario changed; inspect it before activation')
            scenario=compile_bundle(entry['bundle']);state=self._read()
            self._archive(state,current,meta,owner)
            old=state['scenarios'].get(scenario['id'])
            scenario['revision']=(old['revision']+1) if old else 1
            # Preserve an actual prior current text as a historical capture
            # when an engineer activates changed text. Existing saved records
            # remain byte-for-byte intact; no ordinary snapshot table is used.
            if old:
                # Runtime captures belong to this scenario's snapshot history,
                # independently of the editable pack. Keep those generated
                # captures across activations; deliberately removed authored
                # rows are governed by the new draft, not resurrected here.
                for record in old['records'].get('configuration',[]):
                    generated=record['values'].get('snapshot_type') in {'capture','revision_capture'} or record['id'].startswith('revision-capture-')
                    if generated and not any(row['id']==record['id'] for row in scenario['records']['configuration']):
                        scenario['records']['configuration'].append(deepcopy(record))
                for record in old['records'].get('running_configuration',[]):
                    new=next((r for r in scenario['records']['running_configuration'] if r['device_id']==record['device_id'] and r['current']),None)
                    if record['current'] and new and record['values'].get('config_text')!=new['values'].get('config_text'):
                        capture=deepcopy(record);capture.update(id='revision-capture-'+uuid4().hex,kind='configuration_snapshot',current=False,depends_on=[])
                        capture['values']['source_category']='config_snapshots'
                        capture['values']['snapshot_type']='revision_capture'
                        scenario['records']['configuration'].append(capture)
                scenario=Scenario.model_validate(scenario).model_dump()
            state['scenarios'][scenario['id']]=scenario;state['selected']=scenario['id'];state['epoch']+=1
            state['enabled']=True
            state['workbench_activation']={'owner':owner,'draft_id':draft_id,'draft_revision':expected,'bundle_hash':digest}
            state.setdefault('workbench_bundles',{})[scenario['id']]=deepcopy(entry['bundle'])
            self._write(state)
            return self.snapshot(fresh=True)

    def catalog(self):
        with self.lock:return [{'id':s['id'],'title':s['title'],'revision':s['revision']} for s in self._read()['scenarios'].values()]

    def change(self,action,expected,definition=None,scenario_id=None,*,owner=None):
        with self.lock:
            current,meta=self.snapshot(fresh=True)
            if expected!=meta['source_revision']:raise HTTPException(409,'Scenario changed; reload before editing')
            state=self._read()
            if action=='select':
                if scenario_id not in state['scenarios']:raise HTTPException(404,'Scenario not found')
                state['selected']=scenario_id
            elif action=='reset':
                key=scenario_id or current['id']
                if key not in self.library:raise HTTPException(422,'Only bundled scenarios have a reset definition')
                restored=deepcopy(self.library[key]);restored['revision']=state['scenarios'].get(key,restored)['revision']+1
                state['scenarios'][key]=restored;state['selected']=key
            elif action in {'edit','import','duplicate'}:
                if definition is None:raise HTTPException(422,'A scenario definition is required')
                if len(json.dumps(definition).encode())>2000000:raise HTTPException(413,'Scenario exceeds 2 MB')
                s=Scenario.model_validate(definition).model_dump();key=s['id']
                if action=='edit' and key!=current['id']:raise HTTPException(422,'Edit cannot change scenario identity; duplicate instead')
                if action!='edit' and key in state['scenarios']:raise HTTPException(409,'Scenario already exists')
                if len(state['scenarios'])>=40 and key not in state['scenarios']:raise HTTPException(413,'Scenario library limit is 40')
                s['revision']=current['revision']+1 if action=='edit' else 1
                state['scenarios'][key]=s;state['selected']=key
            else:raise HTTPException(422,'Unknown scenario action')
            if owner:self._archive(state,current,meta,owner)
            selected=state['scenarios'][state['selected']]
            if not selected.get('source_manifest'):state.setdefault('workbench_bundles',{}).pop(selected['id'],None)
            state['epoch']+=1;self._write(state)
            return self.snapshot()

    def capture(self,device_id,expected):
        with self.lock:
            s,meta=self.snapshot()
            if expected!=meta['source_revision']:raise HTTPException(409,'Scenario changed before capture')
            rows=[r for r in s['records'].get('running_configuration',[]) if r['device_id']==device_id and r['current']]
            if len(rows)!=1 or not s['availability'].get('running_configuration',False):raise HTTPException(422,'No unique current simulated running configuration')
            row=deepcopy(rows[0]);row.update(id='capture-'+uuid4().hex,timestamp=s['logical_time'],kind='configuration_snapshot',current=False,depends_on=[rows[0]['id']])
            row['values'].update(snapshot_type='capture',source_category='config_snapshots')
            s['records'].setdefault('configuration',[]).append(row)
            self.change('edit',expected,s)
            return row

    def transition(self,interface_id,admin_status,expected):
        """A modeled administrative event, never an instruction to a device."""
        from datetime import timedelta
        with self.lock:
            s,meta=self.snapshot()
            if meta['source_revision']!=expected:raise HTTPException(409,'Scenario changed before event')
            interface=next((i for i in s['interfaces'] if i['id']==interface_id),None)
            if not interface or admin_status not in {'up','down'}:raise HTTPException(422,'Choose a recorded interface and admin state')
            s['logical_time']=(datetime.fromisoformat(s['logical_time'].replace('Z','+00:00'))+timedelta(seconds=1)).isoformat()
            interface.update(admin_status=admin_status,oper_status='down' if admin_status=='down' else 'unknown')
            event='admin-'+uuid4().hex
            for rows in s['records'].values():
                for r in rows:
                    if r['interface_id']==interface_id and r['kind'] in {'interface_state','interface_counters'}:r['current']=False
                    if r['kind']=='reachability' and interface_id in r['values'].get('interface_ids',[]):r['current']=False
                    if r['kind']=='observed_link' and r['current']:
                        endpoints,_=observation_endpoints(s['planned_links'],r['values'])
                        if endpoints and interface_id in [endpoints['src_interface_id'],endpoints['dst_interface_id']]:
                            r.update(timestamp=s['logical_time'],depends_on=[event]);r['values']['oper_status']='down' if admin_status=='down' else 'unknown'
            make=lambda key,kind,values,deps=[]:dict(id=key,device_id=interface['device_id'],interface_id=interface_id,timestamp=s['logical_time'],kind=kind,source='development-event-sequence',current=True,depends_on=deps,values=values)
            s['records']['state'].append(make(event,'interface_state',{k:interface[k] for k in ['prefix','admin_status','oper_status']}))
            if admin_status=='down':
                s['records']['telemetry'].append(make('counters-'+uuid4().hex,'interface_counters',{'in_bps':0,'out_bps':0},[event]))
                for old in list(s['records']['state']):
                    if old['kind']=='reachability' and interface_id in old['values'].get('interface_ids',[]):
                        probe=deepcopy(old);probe.update(id='modeled-probe-'+uuid4().hex,timestamp=s['logical_time'],current=True,depends_on=[event]);probe['values']['success']=False
                        s['records']['state'].append(probe)
                        break
            s['records']['syslog'].append(make('log-'+uuid4().hex,'configuration_event',{'severity':'info','message':interface['name']+' administrative state set to '+admin_status},[event]))
            s['records']['incidents'].append(make('alert-'+uuid4().hex,'derived_alert',{'severity':'warning' if admin_status=='down' else 'info','message':'Administrative state transition'},[event]))
            configurations=[r for r in s['records'].get('running_configuration',[]) if r['device_id']==interface['device_id'] and r['current']]
            if len(configurations)!=1:raise HTTPException(422,'Event requires one current simulated configuration')
            config=configurations[0];text=config['values']['config_text']
            pattern=r'(?m)(^interface '+re.escape(interface['name'])+r'\n(?:[ \t].*\n)*?)[ \t]+(?:no )?shutdown(?=\n|$)'
            updated,count=re.subn(pattern,lambda m:m[1]+' '+('shutdown' if admin_status=='down' else 'no shutdown'),text)
            if count!=1:raise HTTPException(422,'This scenario needs an explicit vendor-specific event edit; configuration was not guessed')
            config['current']=False;fresh=deepcopy(config);fresh.update(id='running-'+uuid4().hex,current=True,timestamp=s['logical_time'],depends_on=[event]);fresh['values'].update(config_text=updated,captured_at=s['logical_time'])
            s['records']['running_configuration'].append(fresh)
            return self.change('edit',expected,s)

    def inventory(self):
        s,meta=self.snapshot();devices=[]
        for d in s['devices']:
            row=deepcopy(d);row['engineering_facts_revision']=hashlib.sha256(json.dumps(d['engineering_facts'],sort_keys=True).encode()).hexdigest()
            row['interfaces']=[]
            for interface in s['interfaces']:
                if interface['device_id']!=d['id']:continue
                i=deepcopy(interface);address=ipaddress.ip_interface(i['prefix']) if i['prefix'] else None
                i.update(ip_address=str(address.ip) if address else None,subnet_mask=str(address.netmask) if address else None,status=i['oper_status'])
                row['interfaces'].append(i)
            devices.append(row)
        return {'devices':devices,'links':s['planned_links'],'structure_source':'development_scenario','scenario':meta,
            'inventory_source':deepcopy(s.get('source_statuses',{}).get('inventory',{})),
            'logical_source_categories':sorted(s.get('source_statuses',{})),
            'inventory_complete':s['inventory_complete'],'reachability':'see_scoped_observations','live_state_available':False}

    def result(self,domain,query,devices):
        from llm.gateway_models import ToolResult,Evidence
        from llm.gateway_network import timestamp,explicit_topology_scope
        s,meta=self.snapshot();ids={int(d['id']) for d in devices}
        if query.live:return ToolResult(status='unavailable',data={'scenario':meta},message='Physical live data is unavailable; development observations are not live measurements.')
        available=s['availability'].get(domain,False)
        from development.source_registry import BY_KEY
        source_states={key:value for key,value in s.get('source_statuses',{}).items()
            if key in BY_KEY and BY_KEY[key].supports('network.'+domain)}
        categories=list(query.source_categories)
        if not categories and domain=='configuration' and s.get('source_statuses'):
            from llm.gateway_network import explicit_configuration_scope
            temporal=query.source_scope if query.source_scope!='auto' else explicit_configuration_scope(query.query)
            if temporal=='current':categories=['running_configs']
            elif temporal=='historical':categories=['config_snapshots','config_changes']
        if categories:source_states={key:value for key,value in source_states.items() if key in categories}
        source_statuses={key:value['status'] for key,value in source_states.items()}
        if source_states:available=any(value in {'AVAILABLE','STALE','CONFLICTING'} for value in source_statuses.values())
        records=[]
        source_rows=list(s['records'].get(domain,[])) if available else []
        if domain=='state' and available and s.get('network'):
            from development.network_model import NetworkModel,assess_flow,protocol_findings
            model=NetworkModel.model_validate(s['network'])
            # The same central snapshot supplies every input. Derived assessments
            # retain model-source identities, not extra independent observations.
            for flow in model.flows:
                result=assess_flow(s,flow)
                # Flow ownership is not its relationship scope. Retain either
                # endpoint and devices actually reached by the bounded model,
                # including a transit where lookup/ingress fails before a hop
                # can be recorded. Planned adjacency alone is not traversal.
                scope={flow.source_device_id,flow.destination_device_id}
                for direction in ['forward','return']:
                    scope.update((result.get(direction) or {}).get('encountered_device_ids',[]))
                if not scope.intersection(ids):continue
                source_rows.append({'id':'model-flow-'+flow.id,'device_id':flow.source_device_id,'interface_id':None,
                    'timestamp':model.observed_at,'kind':'forwarding_assessment','source':'declared_ipv4_observation_model',
                    'current':True,'depends_on':[],'values':{'flow':flow.model_dump(),'assessment':result,'derived':True,'scope_device_refs':sorted(scope),
                    'model_source_ids':[r.id for t in model.tables for r in t.routes],'source_category':'simulation'}})
            for finding in protocol_findings(model):
                if not set(finding['devices']).intersection(ids):continue
                # Endpoint identities come from the same pinned scenario, not
                # an LLM interpretation of local/remote numerical references.
                for peer in finding.get('peer_parameters',[]):
                    peer['hostname']=next(d['hostname'] for d in s['devices'] if d['id']==peer['device_id'])
                    interface=next((i for i in s['interfaces'] if i['id']==peer.get('interface_id')),None)
                    if interface:peer['interface']=interface['name']
                source_rows.append({'id':'model-protocol-'+finding['id'],'device_id':finding['devices'][0],'interface_id':None,
                    'timestamp':model.observed_at,'kind':'protocol_assessment','source':'declared_protocol_observations',
                    'current':True,'depends_on':[],'values':{**finding,'scope_device_refs':finding['devices'],'derived':True,'model_source_ids':[finding['id']],'source_category':'simulation'}})
            # Exact routing/interface questions need the actual declared records,
            # not only the calculated diagnosis. These are the same snapshot.
            for table in model.tables:
                if table.device_id not in ids:continue
                source_rows.append({'id':'model-table-'+str(table.device_id)+'-'+table.vrf,'device_id':table.device_id,'interface_id':None,
                    'timestamp':model.observed_at,'kind':'routing_table','source':'declared_routing_table','current':True,'depends_on':[],
                    'values':{'vrf':table.vrf,'complete':table.complete,'routes':[r.model_dump() for r in table.routes],'source_category':'simulation'}})
            for interface in s['interfaces']:
                if interface['device_id'] not in ids:continue
                source_rows.append({'id':'model-interface-'+str(interface['id']),'device_id':interface['device_id'],'interface_id':interface['id'],
                    'timestamp':model.observed_at,'kind':'interface_state','source':'declared_interface_observation','current':True,'depends_on':[],
                    'values':{**{k:interface.get(k) for k in ['name','prefix','vrf','admin_status','oper_status']},'source_category':'simulation'}})
        if domain=='telemetry' and available and s.get('network'):
            from development.network_model import NetworkModel,metric_findings
            for finding in metric_findings(NetworkModel.model_validate(s['network']),s['interfaces']):
                if finding['device_id'] not in ids:continue
                source_rows.append({'id':'model-metric-'+finding['id'],'device_id':finding['device_id'],'interface_id':finding['interface_id'],
                    'timestamp':finding['timestamp'],'kind':'metric_series','source':'declared_metric_samples','current':True,'depends_on':[],
                    'values':{**finding['values'],'interpretation':finding['notes'],'derived':True,'model_source_ids':[finding['id']],'source_category':'simulation'}})
        if domain=='configuration':
            available=available or s['availability'].get('running_configuration',False)
            source_rows+=s['records'].get('running_configuration',[]) if s['availability'].get('running_configuration',False) else []
            current=query.source_scope=='current' or query.source_scope=='auto' and bool(re.search(r'\b(current|active|running)\b',query.query,re.I))
            history=query.source_scope=='historical' or query.source_scope=='auto' and bool(re.search(r'\b(stored|saved|history|snapshots?|captures?|backups?)\b',query.query,re.I))
            typed_history=bool(set(categories)&{'config_changes','config_drift'})
            if typed_history:
                # A change/drift source is already a distinct record contract.
                # Temporal words must not substitute running text or snapshots
                # for an explicitly selected change event.
                pass
            elif query.source_scope=='planned':
                source_rows=[r for r in source_rows if r['kind']=='planned_configuration'];available=bool(source_rows)
            elif current and not history:
                available=s['availability'].get('running_configuration',False)
                source_rows=[r for r in source_rows if r['kind']=='running_configuration' and
                    (r['current'] or source_statuses.get(r.get('values',{}).get('source_category'))=='STALE')]
            elif history and not current:source_rows=[r for r in source_rows if not r['current'] and r['kind']!='planned_configuration']
        topology_scope=query.source_scope if query.source_scope!='auto' else explicit_topology_scope(query.query)
        if domain=='topology':
            # Explicit logical sources constrain the returned data even when a
            # model leaves temporal scope at auto. Identity definitions are not
            # proof that an unavailable planned source was read successfully.
            scopes={'topology_planned':'planned','topology_observed':'observed','topology_history':'historical'}
            if len(categories)==1 and categories[0] in scopes:topology_scope=scopes[categories[0]]
            if not categories:
                wanted={'planned':['topology_planned'],'observed':['topology_observed'],'current':['topology_observed'],
                    'historical':['topology_history']}.get(topology_scope)
                if wanted:
                    source_states={key:value for key,value in source_states.items() if key in wanted}
                    source_statuses={key:value['status'] for key,value in source_states.items()}
            if topology_scope=='planned':source_rows=[]
            elif topology_scope in {'observed','current'}:source_rows=[r for r in source_rows if r['current']]
            elif topology_scope=='historical':source_rows=[r for r in source_rows if not r['current']]
            elif topology_scope=='both' and explicit_topology_scope(query.query)=='both' and not re.search(r'\b(historical|history|previous|past)\b',query.query,re.I):
                # Comparing the plan with observations means current observed
                # relationships, unless history was actually requested. A past
                # matching link must not cancel a current peer discrepancy.
                source_rows=[r for r in source_rows if r['current']]
        for r in source_rows:
            category=r['values'].get('source_category')
            if categories and category is None:
                from development.source_registry import recorded_category
                category=recorded_category(r,'network.'+domain)
            if categories and category not in categories:continue
            if r['kind']=='protocol_observation':
                from development.network_model import recorded_protocol_model,protocol_findings
                observation=recorded_protocol_model(r['values'],r['timestamp'])
                if observation:
                    finding=protocol_findings(observation)[0]
                    for peer in finding['peer_parameters']:
                        peer['hostname']=next(d['hostname'] for d in s['devices'] if d['id']==peer['device_id'])
                        port=next((i for i in s['interfaces'] if i['id']==peer.get('interface_id')),None)
                        if port:peer['interface']=port['name']
                    # Computed comparison accompanies the authored observation;
                    # it is not another independent measurement or a replacement
                    # for the separately declared simulation session.
                    r={**r,'values':{**r['values'],**{key:val for key,val in finding.items() if key not in {'id'}},
                        'scope_device_refs':finding['devices'],'derived_comparison':True}}
            if category=='simulation' and s.get('source_statuses',{}).get('simulation',{}).get('status')=='STALE':
                r={**r,'current':False}
            # An observer's device is not the whole relationship scope. A typed
            # link reference permits reading its record from either endpoint;
            # it does not turn planned endpoints into operational observations.
            link,endpoint_basis=observation_endpoints(s['planned_links'],r['values']) if domain=='topology' else (None,None)
            link_match=bool(link and ids.intersection({link['src_device_id'],link['dst_device_id']}))
            if r['device_id'] not in ids and not ids.intersection(r['values'].get('scope_device_refs',[])) and not link_match:continue
            if query.record_kinds and r['kind'] not in query.record_kinds:continue
            if domain=='telemetry' and (query.start or query.end) and isinstance(r['values'].get('samples'),list):
                from development.network_model import metric_sample_window
                scoped=metric_sample_window(r['values'],timestamp(query.start),timestamp(query.end),s['interfaces'],r['device_id'],r['interface_id'])
                if scoped is None:continue
                captured=r['timestamp'];last=scoped['window_end']
                r={**r,'timestamp':last,'current':r['current'] and timestamp(last)==timestamp(captured),
                    'values':{**scoped,'captured_at':captured}}
            elif query.start and timestamp(r['timestamp'])<timestamp(query.start) or query.end and timestamp(r['timestamp'])>timestamp(query.end):continue
            age=(timestamp(s['logical_time'])-timestamp(r['timestamp'])).total_seconds()
            row={**r['values'],'hostname':next(d['hostname'] for d in s['devices'] if d['id']==r['device_id']),'interface':next((i['name'] for i in s['interfaces'] if i['id']==r['interface_id']),None),**{k:v for k,v in r.items() if k!='values'},'freshness':'fresh' if r['current'] and 0<=age<=120 else 'stale'}
            gaps=[{'record_ref':ref,'source_category':s['unavailable_record_refs'][ref],
                'status':s['source_statuses'][s['unavailable_record_refs'][ref]]['status']}
                for ref in r.get('depends_on',[]) if ref in s.get('unavailable_record_refs',{})]
            if gaps:row['unavailable_dependencies']=gaps
            if link:
                row['link_endpoints']={side:next(d['hostname'] for d in s['devices'] if d['id']==link[field])
                    for side,field in [('source','src_device_id'),('target','dst_device_id')]}
                row['link_endpoints'].update({side:next(i['name'] for i in s['interfaces'] if i['id']==link[field])
                    for side,field in [('source_interface','src_interface_id'),('target_interface','dst_interface_id')]})
                row['endpoint_basis']=endpoint_basis
            records.append(row)
        if domain in {'state','telemetry'}:
            from llm.gateway_network import scoped_interface_records
            records=scoped_interface_records(records,query.interface_refs,relationships=domain=='state')
        from llm.gateway_network import redact
        for row in records:
            if 'config_text' in row:row['config_text']=redact(row['config_text'])
        records.sort(key=lambda r:r['timestamp'],reverse=True)
        if source_states:available=any(value in {'AVAILABLE','STALE','CONFLICTING'} for value in source_statuses.values())
        data={'records':records[:query.limit] if available else [],'scenario':meta,'total':len(records),'truncated':len(records)>query.limit,'source_available':available,
            **({'source_statuses':source_statuses,'source_captures':{key:value.get('captured_at') for key,value in source_states.items()}} if source_states else {})}
        if domain=='state' and any(row.get('kind')=='source_health' for row in data['records']):
            # Preserve authored health claims separately. Effective availability
            # is derived from this same pinned revision after configured overrides.
            data['effective_source_statuses']={key:{field:value[field] for field in ['status','captured_at'] if field in value}
                for key,value in s.get('source_statuses',{}).items()}
        if domain=='topology':
            if topology_scope in {'observed','current','historical'}:
                data.update(topology_kind='historical' if topology_scope=='historical' else 'observed',source_available=bool(records),nodes=[],links=[])
                available=bool(records)
            else:
                # Plans are an inventory source, independent of observer uptime.
                plan_state=source_states.get('topology_planned')
                plan_requested=not categories or 'topology_planned' in categories
                plan_available=plan_requested and (plan_state['status'] in {'AVAILABLE','STALE','CONFLICTING'} if plan_state else not s.get('source_statuses') and bool(s['planned_links'] or s['inventory_complete']))
                available=plan_available or bool(records)
                data.update(topology_kind='combined' if records else 'planned',source_available=available,
                    nodes=[{'id':d['id'],'hostname':d['hostname'],'role':d['role']} for d in devices] if available else [])
            names={d['id']:d['hostname'] for d in s['devices']};ifs={i['id']:i for i in s['interfaces']}
            if topology_scope not in {'observed','current','historical'}:data['links']=[dict(l,source=names[l['src_device_id']],target=names[l['dst_device_id']],source_interface=ifs[l['src_interface_id']]['name'],target_interface=ifs[l['dst_interface_id']]['name']) for l in s['planned_links'] if plan_available and (l['src_device_id'] in ids or l['dst_device_id'] in ids)]
            if topology_scope not in {'observed','current','historical'}:
                from llm.gateway_network import planned_graph_path
                data['graph_path']=planned_graph_path(devices,s['planned_links'],names) if plan_available else None
                data['reachability']='not_measured'
            data['source_captures']={key:value.get('captured_at') for key,value in source_states.items()}
        evidence=Evidence(id=uuid4().hex,source='development.'+domain,origin='simulated',authority='development_scenario',time_scope='current' if any(r['current'] for r in records) else 'historical' if records else 'unspecified',captured_at=records[0]['timestamp'] if records else None,retrieved_at=datetime.now(timezone.utc).isoformat(),freshness='fresh' if any(r['freshness']=='fresh' for r in records) else 'stale' if records else 'unknown',source_revision=meta['source_revision'],device_refs=[str(i) for i in sorted(ids)])
        if len(source_states)==1:
            # A failed/current-filtered reader can still know its source capture
            # time. Do not give the model a contradictory null Evidence capture
            # beside the exact same source's populated envelope. Event timestamps
            # remain on individual records, distinct from this source capture.
            selected_state=next(iter(source_states.values()))
            evidence.captured_at=selected_state.get('captured_at')
            if selected_state['status']=='STALE':evidence.freshness='stale'
        if domain=='topology' and topology_scope=='planned' and 'topology_planned' in source_states:
            evidence.captured_at=source_states['topology_planned'].get('captured_at')
            # Planned is the source's topology_kind, not a new public Evidence
            # enum. It establishes neither current observations nor forecasts.
            evidence.time_scope='unspecified'
            evidence.freshness='stale' if source_statuses['topology_planned']=='STALE' else 'not_applicable'
        return ToolResult(status='success' if available else 'error' if 'ERROR' in source_statuses.values() else 'unavailable',data=data,evidence=[evidence],message='' if available else 'Scenario source status: '+', '.join(sorted(set(source_statuses.values()))) if source_statuses else 'Scenario source is explicitly unavailable')


def projection(db,kind):
    manager=active_for(db)
    if not manager:return None
    from dataclasses import fields
    from db.models import Device,Interface,Link,ConfigSnapshot
    if kind=='snapshots':
        s,_=manager.snapshot()
        return [ConfigSnapshot(id=snapshot_id(r),device_id=r['device_id'],config_text=r['values']['config_text'],captured_at=r['timestamp'],description=r['kind'],source_type='simulated',owner_username=r['values'].get('owner_username')) for r in reversed(s['records'].get('configuration',[]))]
    data=manager.inventory()
    cls={'devices':Device,'interfaces':Interface,'links':Link}[kind]
    rows=data['devices'] if kind=='devices' else data['links'] if kind=='links' else [i for d in data['devices'] for i in d['interfaces']]
    keys={f.name for f in fields(cls)}
    return [cls(**{k:v for k,v in row.items() if k in keys}) for row in rows]


def snapshot_id(record):
    return int(hashlib.sha256(record['id'].encode()).hexdigest()[:12],16)


def protect_inventory_write(db):
    if active_for(db):raise HTTPException(409,'Development scenario is authoritative. Edit it in Development Network; ordinary inventory was not changed.')


def observation_set(manager):
    """Adapt the existing monitoring shape; absent metrics stay absent."""
    from local_providers.observations import Fixture,ObservationSet
    s,meta=manager.snapshot();inventory=manager.inventory()
    devices={d['id']:d for d in inventory['devices']};interfaces={i['id']:i for d in devices.values() for i in d['interfaces']}
    def points(did,iid):
        if not s['availability'].get('telemetry',False):return []
        rows={r['timestamp']:dict(time=r['timestamp'],**r['values']) for r in s['records'].get('telemetry',[]) if r['device_id']==did and r['interface_id']==iid}
        if s.get('network'):
            from development.network_model import NetworkModel
            for series in NetworkModel.model_validate(s['network']).metrics:
                if series.device_id!=did or series.interface_id!=iid:continue
                field={'cpu_pct':'cpu','memory_pct':'memory'}.get(series.metric,series.metric)
                if field not in {'cpu','memory','in_bps','out_bps','errors','discards'}:continue
                for point in series.samples:
                    if point.value is not None:rows.setdefault(point.timestamp,{'time':point.timestamp})[field]=point.value
        return [rows[key] for key in sorted(rows)]
    # Adapt interface-only points without inventing CPU/memory measurements.
    from local_providers.observations import Point
    class DevelopmentPoint(Point):
        cpu: float | None = Field(default=None,ge=0,le=100)
        memory: float | None = Field(default=None,ge=0,le=100)
    valid=lambda rows:[DevelopmentPoint.model_validate(p) for p in rows]
    payload={'version':1,'devices':[dict(device_id=d['id'],availability='unknown',metrics=valid(points(d['id'],None))) for d in devices.values()],
        'interfaces':[dict(device_id=i['device_id'],interface_id=i['id'],admin_status=i['admin_status'],oper_status=i['oper_status'],metrics=valid(points(i['device_id'],i['id']))) for i in interfaces.values()]}
    for target,domain in [('syslog','syslog'),('events','incidents')]:
        payload[target]=[dict(id=r['id'],device_id=r['device_id'],timestamp=r['timestamp'],severity=r['values'].get('severity','info'),message=r['values'].get('message','Recorded scenario event'),kind=r['kind']) for r in s['records'].get(domain,[]) if s['availability'].get(domain,False)]
    result=ObservationSet(Fixture.model_validate(payload),devices,interfaces,meta['source_revision'])
    result.metadata=lambda:dict(source='simulated',provider='development_scenario',fixture_revision=meta['source_revision'],scenario=meta,live=False)
    original_bundle=result.bundle
    def bundle(device='',interface=''):
        output=original_bundle(device,interface);output['sample']=False
        names={d['management_ip']:d['id'] for d in devices.values()}
        for field,rows in output['history']['data'].items():
            actual={'interface_traffic':'in_bps','interface_out':'out_bps','errors':'errors','discards':'discards','utilization':'utilization_pct'}.get(field,field)
            output['history']['data'][field]=[r for r in rows if any(p['time']==r['time'] and actual in p for p in points(names.get(r['device']),next((i['id'] for i in interfaces.values() if i['device_id']==names.get(r['device']) and i['name']==r.get('interface')),None)))]
        for row in output['interfaces']['interfaces']:
            samples=points(names.get(row['device']),next((i['id'] for i in interfaces.values() if i['device_id']==names.get(row['device']) and i['name']==row['interface']),None))
            last=samples[-1] if samples else {}
            for key,field in [('in_octets','in_bps'),('out_octets','out_bps'),('errors','errors'),('discards','discards')]:
                if field not in last:row[key]=None
            row['in_packets']=row['out_packets']=None
        return output
    result.bundle=bundle
    return result
