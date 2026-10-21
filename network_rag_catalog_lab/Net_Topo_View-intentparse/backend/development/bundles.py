"""Versioned editable source bundles compiled into the existing Scenario model.

Only this loader resolves linked files; readers consume activated bytes. Paths
cannot leave a bundle, follow symlinks/junctions, or reach private test oracles.
No archive extraction, arbitrary filesystem tool or competing data store exists.
"""
from copy import deepcopy
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path,PurePosixPath
from typing import Literal
from pydantic import AwareDatetime,Field,model_validator
from llm.gateway_models import StrictModel
from development.source_registry import BY_KEY,STATUSES

Status=Literal['AVAILABLE','MISSING','UNAVAILABLE','STALE','ERROR','CONFLICTING','UNSUPPORTED','NOT_QUERIED']


class Clock(StrictModel):
    now:AwareDatetime
    timezone:str='UTC'
    paused:Literal[True]=True
    rate:Literal[0]=0


class SourceFile(StrictModel):
    schema_version:Literal['1.0']='1.0'
    category:str
    status:Status='AVAILABLE'
    captured_at:AwareDatetime
    data:dict

    @model_validator(mode='after')
    def known_category(self):
        if self.category not in BY_KEY:raise ValueError('Unknown logical source category')
        json.dumps(self.data,allow_nan=False)
        return self


class Manifest(StrictModel):
    schema_version:Literal['1.0']='1.0'
    scenario_id:str=Field(pattern=r'^[A-Z0-9][A-Z0-9_-]{0,79}$')
    name:str=Field(min_length=1,max_length=150)
    description:str=Field(default='',max_length=2000)
    scenario_revision:int=Field(ge=1)
    created_by:str=Field(min_length=1,max_length=100)
    created_at:AwareDatetime
    mode:Literal['development_scenario']='development_scenario'
    clock:Clock
    source_files:dict[str,str]
    source_hashes:dict[str,str]=Field(default_factory=dict)
    policy:dict[str,Literal[False]]

    @model_validator(mode='after')
    def complete_registry(self):
        if set(self.source_files)!=set(BY_KEY):raise ValueError('Manifest must declare exactly all24 source categories')
        if len(set(self.source_files.values()))!=24:raise ValueError('Each source requires its own file')
        if self.policy!={'real_device_access':False,'deploy_allowed':False}:raise ValueError('External/device effects must be disabled')
        return self


def safe_file(root,relative):
    root=Path(root).resolve();part=PurePosixPath(relative)
    if any(p.casefold() in {'test_oracles','.git','.env','knowledge_workspace'} for p in root.parts):
        raise ValueError('Private oracle, secret and knowledge roots cannot be scenario imports')
    if '\\' in relative or ':' in relative or part.is_absolute() or '..' in part.parts or not part.parts:
        raise ValueError('Linked file must use a contained relative path')
    if any(p.casefold() in {'test_oracles','.git','.env','knowledge_workspace'} for p in part.parts):
        raise ValueError('Private oracle, secrets and knowledge paths are not scenario assets')
    current=root
    for name in part.parts:
        current=current/name
        if current.is_symlink() or current.exists() and getattr(current.stat(),'st_file_attributes',0)&0x400:
            raise ValueError('Linked assets cannot traverse symlinks or reparse points')
    if not current.resolve().is_relative_to(root) or not current.is_file():raise ValueError('Missing or out-of-root linked asset')
    if current.stat().st_size>2_000_000:raise ValueError('Scenario asset exceeds2MB')
    return current


def load_bundle(root):
    root=Path(root).resolve()
    manifest=Manifest.model_validate_json(safe_file(root,'manifest.json').read_bytes())
    sources={};assets={};errors=[]
    for category,relative in manifest.source_files.items():
        try:
            raw=safe_file(root,relative).read_bytes()
            source=SourceFile.model_validate_json(raw)
            if source.category!=category:raise ValueError('Source category does not match manifest key')
            expected=manifest.source_hashes.get(category)
            if expected and hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('Source hash differs; explicitly revalidate the edited draft')
            if source.captured_at>manifest.clock.now:raise ValueError('Source capture exceeds virtual now')
            sources[category]=source.model_dump(mode='json')
            for row in source.data.get('records',[]):
                values=row.get('values',{})
                if values.get('config_file'):
                    path=values['config_file'];assets[path]=safe_file(root,path).read_bytes().decode('utf-8')
            for item in source.data.get('files',[]):
                path=item['path'];raw=safe_file(root,path).read_bytes()
                import base64
                assets[path]={'base64':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest()}
        except (ValueError,OSError,KeyError) as exc:errors.append({'file':relative,'category':category,'error':str(exc)[:1500]})
    if errors:raise ValueError(json.dumps(errors))
    bundle={'manifest':manifest.model_dump(mode='json'),'sources':sources,'assets':assets}
    compile_bundle(bundle)
    return bundle


def compile_bundle(bundle):
    from local_providers.development import Scenario
    manifest=Manifest.model_validate(bundle['manifest'])
    if set(bundle)-{'manifest','sources','assets'}:raise ValueError('Unknown bundle fields')
    for relative,asset in bundle.get('assets',{}).items():
        part=PurePosixPath(relative)
        if '\\' in relative or ':' in relative or part.is_absolute() or '..' in part.parts or any(p.casefold() in {'test_oracles','.git','.env','knowledge_workspace'} for p in part.parts):
            raise ValueError('Invalid contained asset path')
        if len(json.dumps(asset).encode())>3_000_000:raise ValueError('Asset exceeds bounded encoded size')
        if not isinstance(asset,str):
            import base64
            try:
                if set(asset)!={'base64','sha256'}:raise ValueError('Asset requires bytes and digest only')
                raw=base64.b64decode(asset['base64'],validate=True)
                if len(raw)>2_000_000:raise ValueError('Asset exceeds2MB')
                if hashlib.sha256(raw).hexdigest()!=asset['sha256']:raise ValueError('Asset digest differs from its bytes')
            except (TypeError,KeyError) as exc:raise ValueError('Invalid encoded asset') from exc
    if set(bundle['sources'])!=set(BY_KEY):raise ValueError('Bundle must contain all24 sources')
    sources={key:SourceFile.model_validate(value) for key,value in bundle['sources'].items()}
    allowed_data={key:{'records'} for key in BY_KEY}
    allowed_data.update(inventory={'complete','devices','interfaces'},topology_planned={'links'},
        knowledge={'release_policy','query','mutable'},documents={'files'},attachments={'files'},
        diagrams={'files','limitation'},conversation={'turns','assistant_kind'},simulation={'network'},source_health={'records','overrides'})
    for key,source in sources.items():
        from jsonschema import Draft202012Validator
        error=next(Draft202012Validator(source_schema(key)).iter_errors(source.model_dump(mode='json')),None)
        if error:
            pointer='/'.join(str(part).replace('~','~0').replace('/','~1') for part in error.absolute_path)
            raise ValueError(manifest.source_files[key]+'#/'+pointer+': '+error.message[:500])
        if set(source.data)-allowed_data[key]:raise ValueError(key+': unknown data fields')
        if key in {'documents','attachments','diagrams'}:
            from llm.gateway_documents import EXTENSIONS
            for item in source.data.get('files',[]):
                if set(item)-{'path','name'} or not isinstance(item.get('path'),str):raise ValueError(key+': file descriptor requires path/name only')
                if item['path'] not in bundle.get('assets',{}):raise ValueError(key+': missing linked file bytes')
                if Path(item.get('name') or item['path']).suffix.lower() not in EXTENSIONS:raise ValueError(key+': unsupported document type')
                if not isinstance(bundle['assets'][item['path']],dict):raise ValueError(key+': file requires encoded bytes and digest')
        if key=='knowledge' and (source.data.get('mutable') is not False or source.data.get('release_policy')!='active_immutable_release'):
            raise ValueError('Published V9 knowledge can only reference the active immutable release')
        if key=='conversation':
            turns=source.data.get('turns',[])
            if not isinstance(turns,list) or len(turns)>8 or any(not isinstance(t,str) or len(t)>2000 for t in turns):raise ValueError('Conversation setup accepts up to8 user requests, never fabricated assistant replies')
    inventory=sources['inventory'].data
    scenario={'format_version':1,'id':manifest.scenario_id,'revision':manifest.scenario_revision,'title':manifest.name,
        'logical_time':manifest.clock.now.isoformat(),'model_scope':'direct_link','inventory_complete':inventory.get('complete',False),
        'devices':deepcopy(inventory.get('devices',[])),'interfaces':deepcopy(inventory.get('interfaces',[])),
        'planned_links':deepcopy(sources['topology_planned'].data.get('links',[])),
        'records':{domain:[] for domain in ['state','topology','configuration','running_configuration','telemetry','syslog','incidents']},
        'availability':{},'source_statuses':{},'source_manifest':{'schema_version':'1.0','source_categories':list(sources),'mode':'development_scenario',
            'bundle_digest':hashlib.sha256(json.dumps(bundle,sort_keys=True).encode()).hexdigest()}}
    record_ids=set();record_categories={}
    for key,source in sources.items():
        if source.category!=key:raise ValueError(key+': source category mismatch')
        if source.captured_at>manifest.clock.now:raise ValueError(key+': source capture exceeds virtual now')
        entry=BY_KEY[key];scenario['source_statuses'][key]={'status':source.status,'captured_at':source.captured_at.isoformat(),'domain':entry.domain,'kind':entry.kind}
        if not entry.domain:continue
        scenario['availability'][entry.domain]=scenario['availability'].get(entry.domain,False) or source.status in {'AVAILABLE','STALE','CONFLICTING'}
        rows=deepcopy(source.data.get('records',[]))
        if not isinstance(rows,list):raise ValueError(key+': records must be an array')
        for row in rows:
            if row['id'] in record_ids:raise ValueError(key+': duplicate record identity')
            record_ids.add(row['id'])
            record_categories[row['id']]=key
            if row.get('kind')!=entry.kind:raise ValueError(key+': record kind must be '+entry.kind)
            values=row.setdefault('values',{})
            values['source_category']=key
            if entry.editor=='configuration':
                linked=values.pop('config_file',None)
                if linked:
                    text=bundle.get('assets',{}).get(linked)
                    if not isinstance(text,str):raise ValueError(key+': missing linked configuration bytes')
                    if 'config_text' in values:raise ValueError('Use config_text or config_file, not both')
                    values['config_text']=text
                if not isinstance(values.get('config_text'),str):raise ValueError(key+': configuration text is required')
                if key=='running_configs' and row.get('current') is not True:raise ValueError(key+': current configuration must be current')
                if key=='config_snapshots' and row.get('current') is not False:raise ValueError(key+': saved capture must be historical')
            if key in {'telemetry','interface_metrics'}:
                from development.network_model import validate_recorded_metric
                validate_recorded_metric(values,row['timestamp'])
                if datetime.fromisoformat(row['timestamp'].replace('Z','+00:00'))>source.captured_at:
                    raise ValueError(key+': metric observation exceeds source capture time')
            if source.status=='STALE':row['current']=False
            if source.status in {'AVAILABLE','STALE','CONFLICTING'}:scenario['records'][entry.domain].append(row)
    for item in sources['source_health'].data.get('overrides',[]):
        key=item['category'];status=item['status']
        if key not in BY_KEY or status not in STATUSES:raise ValueError('Invalid source health override')
        scenario['source_statuses'][key]['status']=status
        if status in {'MISSING','UNAVAILABLE','ERROR','UNSUPPORTED','NOT_QUERIED'}:
            for rows in scenario['records'].values():rows[:]=[r for r in rows if r['values'].get('source_category')!=key]
        elif status=='STALE':
            for rows in scenario['records'].values():
                for r in rows:
                    if r['values'].get('source_category')==key:r['current']=False
    for domain in scenario['records']:
        scenario['availability'][domain]=any(value['domain']==domain and value['status'] in {'AVAILABLE','STALE','CONFLICTING'} for value in scenario['source_statuses'].values())
    present={row['id'] for rows in scenario['records'].values() for row in rows}
    # Preserve dependency identities without admitting unavailable content. A
    # recorded incident/diff may outlive its source; it is not independent proof
    # that the missing observation was successfully retrieved.
    scenario['unavailable_record_refs']={identity:category for identity,category in record_categories.items() if identity not in present}
    simulation=sources['simulation'].data.get('network')
    if simulation and scenario['source_statuses']['simulation']['status'] in {'AVAILABLE','STALE','CONFLICTING'}:
        scenario.update(format_version=2,model_scope='ipv4_observation',network=simulation)
    # Device/interface definitions remain structurally validated below for
    # scenario identity and every cross-source reference. Reader availability is
    # independent: ERROR/MISSING must be testable without inventing identities or
    # publishing the internal definitions as successfully retrieved inventory.
    validated=Scenario.model_validate(scenario).model_dump()
    for device in validated['devices']:
        now=[r for r in validated['records']['running_configuration'] if r['device_id']==device['id'] and r['current']]
        if len(now)>1:raise ValueError('Multiple current configurations for '+device['hostname'])
    return validated


def source_schema(category):
    """Versioned strict file envelope plus existing typed entity/record schemas."""
    from local_providers.development import Device,Interface,Link,Record
    if category not in BY_KEY:raise ValueError('Unknown source category')
    schema=SourceFile.model_json_schema();schema['properties']['category']={'const':category}
    data={'type':'object','additionalProperties':False,'properties':{}}
    def model_schema(model):
        value=model.model_json_schema();definitions=value.get('$defs',{})
        def expand(node):
            if isinstance(node,list):return [expand(item) for item in node]
            if not isinstance(node,dict):return node
            if '$ref' in node and node['$ref'].startswith('#/$defs/'):
                return expand({**definitions[node['$ref'].split('/')[-1]],**{k:v for k,v in node.items() if k!='$ref'}})
            return {key:expand(item) for key,item in node.items() if key!='$defs'}
        return expand(value)
    def array(model):return {'type':'array','items':model_schema(model),'maxItems':3000}
    if category=='inventory':data['properties']={'devices':array(Device),'interfaces':array(Interface),'complete':{'type':'boolean'}}
    elif category=='topology_planned':data['properties']={'links':array(Link)}
    elif category in {'documents','attachments','diagrams'}:
        data['properties']={'files':{'type':'array','maxItems':30,'items':{'type':'object','required':['path'],'additionalProperties':False,'properties':{'path':{'type':'string'},'name':{'type':'string'}}}}}
        if category=='diagrams':data['properties']['limitation']={'type':'string'}
    elif category=='conversation':data['properties']={'turns':{'type':'array','maxItems':8,'items':{'type':'string','maxLength':2000}},'assistant_kind':{'enum':['floating','studio']}}
    elif category=='knowledge':data['properties']={'release_policy':{'const':'active_immutable_release'},'mutable':{'const':False},'query':{'type':'string'}}
    elif category=='simulation':
        from development.network_model import NetworkModel
        data['properties']={'network':model_schema(NetworkModel)}
    else:
        data['properties']={'records':array(Record)}
        if category in {'topology_observed','topology_history'}:
            from local_providers.development import ObservedEndpoints
            data['properties']['records']['items']['properties']['values']={'type':'object','additionalProperties':True,
                'properties':{'endpoints':model_schema(ObservedEndpoints),
                    'link_id':{'type':'integer','description':'Optional legacy reference to planned topology; explicit observed endpoints take precedence.'},
                    'oper_status':{'enum':['up','down','unknown']},'discovery_protocol':{'type':'string','minLength':1,'maxLength':100}}}
        if category=='protocol_state':
            from development.network_model import OSPFSession,BGPSession
            variants=[]
            for protocol,model in [('OSPF',OSPFSession),('BGP',BGPSession)]:
                values=model_schema(model)
                values['properties']['session_id']=values['properties'].pop('id')
                values['required']=['session_id' if key=='id' else key for key in values.get('required',[])]
                values['properties'].update(protocol={'const':protocol},observation_basis={'type':'string','maxLength':1000})
                values['required'].append('protocol');variants.append(values)
            # Preserve legacy one-ended records without treating their freeform
            # claims as validated two-ended sessions. New structured endpoints
            # must satisfy the same session schemas used by the bounded model.
            data['properties']['records']['items']['properties']['values']={'type':'object',
                'if':{'anyOf':[{'required':['left']},{'required':['right']}]},'then':{'oneOf':variants}}
        if category in {'telemetry','interface_metrics'}:
            from development.network_model import Sample
            sample=model_schema(Sample);sample['properties']['timestamp']['format']='date-time'
            data['properties']['records']['items']['properties']['values']={'type':'object','additionalProperties':True,
                'required':['metric','unit','value'],'properties':{'metric':{'type':'string','minLength':1},
                    'unit':{'type':'string','minLength':1},'value':{'type':'number','minimum':0},
                    'sampling_seconds':{'type':'integer','minimum':1,'maximum':86400},
                    'samples':{'type':'array','minItems':1,'maxItems':300,'items':sample}}}
        if category=='source_health':data['properties']['overrides']={'type':'array','items':{'type':'object','additionalProperties':False,'required':['category','status'],'properties':{'category':{'enum':list(BY_KEY)},'status':{'enum':list(STATUSES)}}}}
    schema['properties']['data']=data
    return schema
