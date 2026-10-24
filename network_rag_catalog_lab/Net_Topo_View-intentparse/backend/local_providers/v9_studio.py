"""Translate V9's published plan into the original Studio presentation contract."""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import uuid

from fastapi import HTTPException
import yaml
from lab_config import PROJECT_DIR, LOCAL_LAB, LOCAL_OLLAMA_URL
from db.local_migrations import backup_database


def enabled():
    return LOCAL_LAB and os.getenv('COGNISHIELD_STUDIO_ENGINE', 'original') == 'v9'


def ensure_schema(db):
    with db._connect() as conn:
        if conn.execute("SELECT 1 FROM schema_migrations WHERE version='v9-studio-1'").fetchone():
            return
    backup_database(db._db_path, 'v9-studio-1')
    with db._connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        conn.execute('CREATE TABLE IF NOT EXISTS studio_v9_sessions (id TEXT PRIMARY KEY, owner TEXT NOT NULL, prompt TEXT NOT NULL, body TEXT NOT NULL, inventory_hash TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP)')
        conn.execute("INSERT INTO schema_migrations(version) VALUES ('v9-studio-1')")


def inventory(db):
    from local_providers.development import active_for
    if manager:=active_for(db):
        snapshot=manager.inventory();rows=[dict(d,aliases_json=json.dumps(d['aliases']),engineering_facts_json=json.dumps(d['engineering_facts'])) for d in snapshot['devices']]
        interfaces=[i for d in snapshot['devices'] for i in d['interfaces']]
    else:
        with db._connect() as conn:
            columns = {r[1] for r in conn.execute('PRAGMA table_info(devices)')}
            extras = ',site,location,aliases_json' if 'site' in columns else ''
            if 'engineering_facts_json' in columns: extras += ',engineering_facts_json'
            rows = [dict(r) for r in conn.execute('SELECT id,hostname,management_ip,vendor,model,os_version,role,status'+extras+' FROM devices ORDER BY id')]
            interfaces = [dict(r) for r in conn.execute('SELECT id,device_id,name,interface_type,ip_address FROM interfaces ORDER BY id')]
    result = []
    for row in rows:
        vendor = {'cisco_ios':'cisco','cisco_xe':'cisco','huawei_vrp':'huawei','juniper_junos':'juniper'}.get(row['vendor'], row['vendor'] or '')
        version = row['os_version'] or ''
        # Do not invent software compatibility from hardware model or a blank version.
        iosxe = row['vendor'] == 'cisco_xe' or bool(re.match(r'IOS[- ]?XE\s+', version, re.I))
        platform = 'iosxe' if vendor == 'cisco' and iosxe else {'huawei':'vrp','juniper':'junos'}.get(vendor, 'ios' if vendor == 'cisco' else '')
        version = re.sub(r'^IOS[- ]?XE\s+', '', version, flags=re.I)
        from llm.gateway_inventory import project_facts
        result.append(project_facts({'id':str(row['id']), 'hostname':row['hostname'], 'display_name':row['hostname'], 'aliases':json.loads(row.get('aliases_json','[]')),
                       'management_ip':row['management_ip'], 'vendor':vendor, 'platform':platform, 'version':version,
                       'role':row['role'], 'status':row['status'], 'site':row.get('site',''), 'location':row.get('location',''),
                       'interfaces':[{'id':i.get('id'), 'name':i['name'], 'mode':i['interface_type'], 'aliases':[]} for i in interfaces if i['device_id']==row['id']]},json.loads(row.get('engineering_facts_json','{}'))))
    if manager:
        for item in result:item['scenario_revision']=snapshot['scenario']['source_revision']
    return result


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def worker(payload):
    root = Path(os.getenv('COGNISHIELD_V9_ROOT', str(PROJECT_DIR.parent / 'network_rag_catalog_v2'))).resolve()
    python = Path(os.getenv('COGNISHIELD_V9_PYTHON', str(PROJECT_DIR.parents[1] / '.venv/Scripts/python.exe')))
    if not python.is_file() or not (root / 'app/pipeline.py').is_file():
        raise HTTPException(503, 'Configured V9 source/runtime is unavailable; no legacy fallback was used.')
    payload.update(root=str(root), ollama_url=LOCAL_OLLAMA_URL)
    from local_providers.knowledge import knowledge_root
    managed = knowledge_root() / 'storage/catalog_releases'
    if knowledge_root().exists():
        if not (managed / 'active.json').is_file():
            raise HTTPException(503, 'Managed knowledge has no active release; complete initialization or restore it.')
        payload['releases'] = str(managed)
    from local_providers.studio import provider
    payload['model'] = provider(payload.get('model')).model_name()
    try:
        proc = subprocess.run([str(python), '-B', str(Path(__file__).with_name('v9_worker.py'))],
                              input=json.dumps(payload), text=True, encoding='utf-8', capture_output=True, timeout=180,
                              cwd=PROJECT_DIR, env={**os.environ, 'PYTHONDONTWRITEBYTECODE':'1'})
        output = json.loads(proc.stdout)
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        raise HTTPException(503, 'V9 worker failed or timed out; no artifacts were committed.') from exc
    if not output.get('ok'):
        raise HTTPException(422, output.get('error', 'V9 rejected the request'))
    return output


def session(db, sid, owner):
    with db._connect() as conn:
        row = conn.execute('SELECT * FROM studio_v9_sessions WHERE id=? AND owner=?', (sid,owner)).fetchone()
    if not row:
        raise HTTPException(404, 'V9 preview session not found for this account.')
    return dict(row)


async def preview(db, req, user):
    from llm.gateway import authorize_studio
    authorize_studio(user)
    ensure_schema(db)
    params = req.params or {}
    sid = params.get('_v9_session')
    previous = session(db,sid,user['username']) if sid else None
    data = inventory(db)
    inventory_changed=bool(previous and previous['inventory_hash']!=digest(data))
    refresh=bool(getattr(req,'refresh_inventory',False))
    if inventory_changed and not refresh and getattr(req,'selection',None) is None:
        raise HTTPException(409,'Inventory/scenario changed. Revalidate the review against current inventory before confirming.')
    raw = json.loads(previous['body']) if previous else {}
    multi = bool(getattr(req, 'allow_multi', False))
    task_id = getattr(req, 'task_id', None)
    if previous and multi and getattr(req, 'expected_revision', None) != previous['revision']:
        raise HTTPException(409, 'The review changed. Reopen the latest interpretation before correcting it.')
    if previous and multi and task_id and task_id not in raw.get('schemas', {}):
        raise HTTPException(409, 'This task no longer exists. Reopen the review.')
    schema = raw.get('schemas', {}).get(task_id, raw.get('schema', {}))
    corrections = {k:v for k,v in params.items() if k in {*schema.get('properties', {}), 'operation_id'}} if previous else {}
    selection=getattr(req,'selection',None)
    if selection is not None and not previous: raise HTTPException(422,'Open a preview before changing its selection.')
    output = await asyncio.to_thread(worker, {'inventory':data, 'prompt':req.intent_description,
        'plan':json.loads(previous['body'])['plan'] if previous else None, 'hosts':req.target_hosts,
        'corrections':corrections, 'model':req.model, 'allow_multi':multi, 'task_id':task_id,
        'confirm_order':bool(getattr(req, 'confirm_order', False)), 'selection':selection,
        'refresh_inventory':inventory_changed and (refresh or selection is not None), 'conversation_reply':getattr(req,'conversation_reply',None)})
    if digest(inventory(db)) != digest(data):
        raise HTTPException(409, 'Inventory changed during interpretation. Review again.')
    sid = sid or uuid.uuid4().hex
    with db._connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        if previous:
            cursor=conn.execute('UPDATE studio_v9_sessions SET body=?,inventory_hash=?,revision=revision+1 WHERE id=? AND revision=?', (json.dumps(output),digest(data),sid,previous['revision']))
            if cursor.rowcount != 1: raise HTTPException(409,'Preview changed concurrently; reopen it.')
        else:
            conn.execute('INSERT INTO studio_v9_sessions(id,owner,prompt,body,inventory_hash) VALUES (?,?,?,?,?)', (sid,user['username'],req.intent_description,json.dumps(output),digest(data)))
        conn.execute('INSERT INTO audit_log(user_id,action,target,details) VALUES (?,?,?,?)', (user['username'],'v9.preview',sid,json.dumps({'release':output['release_id']})))
    return review_presentation(output, sid, data, previous['revision'] + 1 if previous else 1, multi)


def review_presentation(output, sid, data, revision, multi=True):
    """Present an existing plan; no interpretation, validation mutation or render."""
    result = presentation(output, sid, data)
    result['session_revision'] = revision
    if multi:
        result['tasks'] = []
        for task in output['plan']['tasks']:
            single = {**output, 'plan':{**output['plan'], 'tasks':[task]}, 'schema':output['schemas'][task['intent_id']]}
            item = presentation(single, sid, data)
            item.update(task_id=task['intent_id'], status=task['status'],
                        request_text=task['request_text'], reference=output.get('task_references',{}).get(task['intent_id']),
                        issues=review_issues(task), operation_candidates=task.get('operation_candidates', []))
            result['tasks'].append(item)
        result['plan_status'] = output['plan']['status']
        result['plan_issues'] = output['plan']['issues']
    return result


def review_issues(task):
    # V9 retains rejected dependent values as candidates rather than parameters.
    # Show these authoritative rejections even when another capability issue
    # prevents the next missing-field round. Absence from inventory is bounded.
    issues=list(task['issues'])
    for candidate in task.get('candidates',[]):
        if candidate.get('type')=='INVALID_INTERFACE' and candidate.get('validation')=='rejected':
            issues.append({**candidate,'message':str(candidate.get('device','Selected device'))+': interface '+str(candidate.get('value'))+' is not recorded for this target. Choose a recorded interface or correct inventory.'})
    return issues


def parameter_strings(value):
    if isinstance(value,str):return {value}
    if isinstance(value,dict):return set().union(*(parameter_strings(v) for v in value.values())) if value else set()
    if isinstance(value,list):return set().union(*(parameter_strings(v) for v in value)) if value else set()
    return set()


def presentation(output,sid,data):
    plan=output['plan']; task=plan['tasks'][0] if plan['tasks'] else {'parameters':{},'issues':[],'target_devices':[],'operation_id':'','category':'','parameter_provenance':{}}; schema=output['schema']
    fields=[{'field':key,'label':key.replace('_',' ').title(),'type':'number' if spec.get('type') in {'integer','number'} else ('json' if spec.get('type') in {'array','object'} else ('boolean' if spec.get('type')=='boolean' else 'text')),
             'required':key in schema.get('required',[]), 'value':task['parameters'].get(key),
             'min':spec.get('minimum'), 'max':spec.get('maximum'), 'options':spec.get('enum'), 'description':spec.get('description',''), 'schema':spec} for key,spec in schema['properties'].items()]
    issues=review_issues(task)+plan['issues']
    missing=[f for f in fields if any(i.get('field')==f['field'] and i.get('type')=='MISSING' for i in issues)]
    ambiguity=next((i for i in issues if i.get('type')=='AMBIGUOUS_TARGET'), None)
    errors=[i['message'] for i in issues if i.get('type') not in {'MISSING','MISSING_TARGET','AMBIGUOUS_TARGET'}]
    hosts=[d['hostname'] for d in task['target_devices']]
    reasoning=[f"V9 published release {output['release_id']}", f"Operation: {task['operation_id']}",
               'V9 validates the engineering contract. Human approval is still required; no deployment or policy approval is implied.',
               'Parameter provenance: '+json.dumps(task['parameter_provenance']), *[i['message'] for i in issues]]
    result={'categories':[task['category']], 'references':[],
        'reasoning':reasoning,'policy_approved':False,'target_hosts':hosts,'schema_editable_fields':fields,
        'parsed_intent':{'engine':'v9','_v9_session':sid,'action':task['operation_id'],'feature':task['category'],'parameters':task['parameters'],
                         'resolved_devices':hosts,'validation_errors':errors,'knowledge_snapshot_id':output['release_id']}}
    # Snapshot freshness exists independently of target clarification. Omitting
    # it until a host is selected made a fresh review look like a scenario change.
    revisions={d['scenario_revision'] for d in data if d.get('scenario_revision')}
    if len(revisions)==1:result['inventory_revision']=next(iter(revisions))
    proposal = next((i for i in issues if i.get('type')=='OPERATION_PROPOSAL'), None)
    if proposal:
        result['params_disambiguation']={'question':proposal['message'], 'fields':[{'field':'operation_id','label':f"Confirm proposed operation: {task['operation_id']}",'type':'text','required':True,'value':task['operation_id']}]}
    elif not hosts and not errors:
        candidates = {c['hostname'] for c in ambiguity.get('candidates', [])} if ambiguity else None
        targets = [d for d in data if candidates is None or d['hostname'] in candidates]
        question = ambiguity['message'] if ambiguity else 'Select the target from SQLite inventory.'
        result['interfaces_for_selection']={'question':question,'devices':[{'hostname':d['hostname'],'interfaces':d['interfaces']} for d in targets]}
        result['params_disambiguation']={'question':question,'fields':[{'field':'target_devices','label':'Target devices','type':'text','required':True}]}
    elif missing:
        result['params_disambiguation']={'question':'V9 requires these values before generation.','fields':missing}
    if hosts:
        target=next((d for d in data if d['hostname']==hosts[0]),None)
        if target:
            result['recorded_interfaces']=target['interfaces']
            result['inventory_revision']=target.get('scenario_revision')
            result['interface_bindings']=[{'device_id':target['id'],'interface_id':i.get('id'),'name':i['name']} for i in target['interfaces'] if i['name'] in parameter_strings(task['parameters'])]
    return result


async def generate(db,req,user):
    from llm.gateway import authorize_studio
    authorize_studio(user)
    if req.verify_with_dry_run:
        raise HTTPException(422,'Remote Ansible execution is unavailable in local mode.')
    params=req.params or {}
    sid=params.get('_v9_session')
    if not sid: raise HTTPException(422,'Open and review a V9 preview before generation.')
    previous=session(db,sid,user['username']); data=inventory(db)
    if digest(data)!=previous['inventory_hash']: raise HTTPException(409,'Inventory changed. Start a fresh preview.')
    raw=json.loads(previous['body'])
    output=await asyncio.to_thread(worker, {'inventory':data,'prompt':previous['prompt'],'plan':raw['plan'],
        'hosts':req.target_hosts,'corrections':{k:v for k,v in params.items() if k in {*raw['schema']['properties'], 'operation_id'}},'model':req.model})
    if digest(inventory(db)) != previous['inventory_hash']:
        raise HTTPException(409,'Inventory changed during validation. Start a fresh preview.')
    plan=output['plan']; task=plan['tasks'][0]
    if plan['status']!='ready':
        raise HTTPException(422, {'message':'V9 validation requires correction.', 'issues':[i['message'] for i in task['issues']+plan['issues']]})
    values=task['parameters']; host=task['target_devices'][0]['hostname']
    if task['target_devices'][0]['vendor']!='cisco' or task['target_devices'][0]['platform']!='iosxe':
        raise HTTPException(422,'This legacy Ansible wrapper supports IOS-XE only; use native generation for other verified V9 bindings.')
    native=task['configs'][0]['configuration']
    artifact = output.get('artifact_metadata') or {'format':'native_cli','language':'text','extension':'.txt'}
    if artifact['format'] != 'native_cli':
        raise HTTPException(422, 'The current IOS-XE Ansible adapter requires native_cli output.')
    native_name = 'native_config' + artifact['extension']
    # The frozen native CLI is the source of truth. The Ansible wrapper references
    # that exact saved file; never reconstruct commands from a hardcoded VLAN map.
    playbook=yaml.safe_dump([{'name':'V9 validated '+task['operation_id'],'hosts':[host],'gather_facts':False,'tasks':[
        {'name':'Apply reviewed native configuration','cisco.ios.ios_config':{'src':native_name}}]}],sort_keys=False)
    from config_engine.safety import validate_playbook_yaml
    report=validate_playbook_yaml(playbook_yaml=playbook,vendor='cisco_ios',feature=task['category'],target_hosts=[host],execution_engine='ansible_native')
    if not report['passed']: raise HTTPException(422, {'message':'Ansible safety validation failed','issues':report['errors']})
    native=task['configs'][0]['configuration']
    explanation='# V9 engineering review\n\n'+previous['prompt']+'\n\n```json\n'+json.dumps(output,indent=2)+'\n```\n'
    # One transaction commits the reviewed job, artifacts, session and audit.
    with db._connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        row=conn.execute('SELECT revision FROM studio_v9_sessions WHERE id=?',(sid,)).fetchone()
        if row['revision']!=previous['revision']: raise HTTPException(409,'Preview changed concurrently; reopen it.')
        cr=conn.execute("INSERT INTO change_requests(title,description,status,requester,owner_username) VALUES (?,?,'pending_approval',?,?)",
            ('V9 Studio: '+previous['prompt'][:60],previous['prompt'],user['username'],user['username'])).lastrowid
        jid=conn.execute("INSERT INTO jobs(request_id,device_id,status,stage,execution_engine,ansible_playbook,generated_config,owner_username) VALUES (?,?,'pending','plan','ansible_native',?,?,?)",
            (cr,int(task['device_id']),playbook,native,user['username'])).lastrowid
        base=f'playbooks/generated/job_{jid}'
        files=[{'path':base+'/playbook.yml','content':playbook}, {'path':base+'/'+native_name,'content':native}, {'path':base+'/v9_review.md','content':explanation}]
        manifest={'engine':'v9','artifact_metadata':artifact,'knowledge_snapshot_id':output['release_id'],'session_id':sid,'files':[{'path':f['path']} for f in files]}
        for f in files:
            conn.execute("INSERT INTO authoring_revisions(namespace,path,content,kind,deleted,actor,revision) VALUES ('ansible',?,?,'file',0,?,1)",(f['path'],f['content'],user['username']))
        conn.execute('UPDATE jobs SET ansible_entrypoint_path=?,ansible_artifact_manifest=? WHERE id=?',(files[0]['path'],json.dumps(manifest),jid))
        conn.execute('UPDATE studio_v9_sessions SET body=?,revision=revision+1 WHERE id=?',(json.dumps(output),sid))
        conn.execute('INSERT INTO audit_log(user_id,action,target,details) VALUES (?,?,?,?)',(user['username'],'v9.generate',str(jid),json.dumps(manifest)))
    return {'job_id':jid,'request_id':cr,'status':'playbook_generated','playbook':playbook,'artifact_type':'playbook',
            'entrypoint_path':files[0]['path'],'files':files,'manifest':manifest,'target_hosts':[host]}
