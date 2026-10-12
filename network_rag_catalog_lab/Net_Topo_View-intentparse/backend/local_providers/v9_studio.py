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
    with db._connect() as conn:
        rows = [dict(r) for r in conn.execute('SELECT id,hostname,management_ip,vendor,model,os_version,role,status FROM devices ORDER BY id')]
        interfaces = [dict(r) for r in conn.execute('SELECT device_id,name,interface_type,ip_address FROM interfaces ORDER BY id')]
    result = []
    for row in rows:
        vendor = {'cisco_ios':'cisco','cisco_xe':'cisco','huawei_vrp':'huawei','juniper_junos':'juniper'}.get(row['vendor'], row['vendor'] or '')
        version = row['os_version'] or ''
        # Do not invent software compatibility from hardware model or a blank version.
        iosxe = row['vendor'] == 'cisco_xe' or bool(re.match(r'IOS[- ]?XE\s+', version, re.I))
        platform = 'iosxe' if vendor == 'cisco' and iosxe else {'huawei':'vrp','juniper':'junos'}.get(vendor, 'ios' if vendor == 'cisco' else '')
        version = re.sub(r'^IOS[- ]?XE\s+', '', version, flags=re.I)
        result.append({'id':str(row['id']), 'hostname':row['hostname'], 'display_name':row['hostname'], 'aliases':[],
                       'management_ip':row['management_ip'], 'vendor':vendor, 'platform':platform, 'version':version,
                       'role':row['role'], 'status':row['status'], 'site':'', 'location':'',
                       'interfaces':[{'name':i['name'], 'mode':i['interface_type'], 'aliases':[]} for i in interfaces if i['device_id']==row['id']]})
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
    ensure_schema(db)
    params = req.params or {}
    sid = params.get('_v9_session')
    previous = session(db,sid,user['username']) if sid else None
    data = inventory(db)
    if previous and previous['inventory_hash'] != digest(data):
        raise HTTPException(409, 'Inventory changed. Start a fresh preview.')
    corrections = {k:v for k,v in params.items() if k in {'vlan_id','name'}} if previous else {}
    output = await asyncio.to_thread(worker, {'inventory':data, 'prompt':req.intent_description,
        'plan':json.loads(previous['body'])['plan'] if previous else None, 'hosts':req.target_hosts,
        'corrections':corrections, 'model':req.model})
    sid = sid or uuid.uuid4().hex
    with db._connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        if previous:
            cursor=conn.execute('UPDATE studio_v9_sessions SET body=?,revision=revision+1 WHERE id=? AND revision=?', (json.dumps(output),sid,previous['revision']))
            if cursor.rowcount != 1: raise HTTPException(409,'Preview changed concurrently; reopen it.')
        else:
            conn.execute('INSERT INTO studio_v9_sessions(id,owner,prompt,body,inventory_hash) VALUES (?,?,?,?,?)', (sid,user['username'],req.intent_description,json.dumps(output),digest(data)))
        conn.execute('INSERT INTO audit_log(user_id,action,target,details) VALUES (?,?,?,?)', (user['username'],'v9.preview',sid,json.dumps({'release':output['release_id']})))
    return presentation(output,sid,data)


def presentation(output,sid,data):
    plan=output['plan']; task=plan['tasks'][0]; schema=output['schema']
    fields=[{'field':key,'label':key.replace('_',' ').title(),'type':'number' if spec.get('type')=='integer' else 'text',
             'required':key in schema.get('required',[]), 'value':task['parameters'].get(key),
             'min':spec.get('minimum'), 'max':spec.get('maximum')} for key,spec in schema['properties'].items()]
    issues=task['issues']+plan['issues']
    missing=[f for f in fields if any(i.get('field')==f['field'] and i.get('type')=='MISSING' for i in issues)]
    errors=[i['message'] for i in issues if i.get('type') not in {'MISSING','MISSING_TARGET'}]
    hosts=[d['hostname'] for d in task['target_devices']]
    reasoning=[f"V9 published release {output['release_id']}", f"Operation: {task['operation_id']}",
               'V9 validates the engineering contract. Human approval is still required; no deployment or policy approval is implied.',
               'Parameter provenance: '+json.dumps(task['parameter_provenance']), *[i['message'] for i in issues]]
    result={'categories':['vlan'], 'references':[{'doc_name':'playbook.yml','feature':'vlan','vendor':'cisco_ios','path':'reference/vlan/cisco_ios/playbook.yml'}],
        'reasoning':reasoning,'policy_approved':False,'target_hosts':hosts,'schema_editable_fields':fields,
        'parsed_intent':{'engine':'v9','_v9_session':sid,'action':'create_vlan','feature':'vlan','parameters':task['parameters'],
                         'resolved_devices':hosts,'validation_errors':errors,'knowledge_snapshot_id':output['release_id']}}
    if not hosts and not errors:
        result['interfaces_for_selection']={'question':'Select a stored target','devices':[{'hostname':d['hostname'],'interfaces':d['interfaces']} for d in data]}
        result['params_disambiguation']={'question':'Select the target from SQLite inventory.','fields':[{'field':'target_devices','label':'Target devices','type':'text','required':True}]}
    elif missing:
        result['params_disambiguation']={'question':'V9 requires these values before generation.','fields':missing}
    return result


async def generate(db,req,user):
    if req.verify_with_dry_run:
        raise HTTPException(422,'Remote Ansible execution is unavailable in local mode.')
    params=req.params or {}
    sid=params.get('_v9_session')
    if not sid: raise HTTPException(422,'Open and review a V9 preview before generation.')
    previous=session(db,sid,user['username']); data=inventory(db)
    if digest(data)!=previous['inventory_hash']: raise HTTPException(409,'Inventory changed. Start a fresh preview.')
    raw=json.loads(previous['body'])
    output=await asyncio.to_thread(worker, {'inventory':data,'prompt':previous['prompt'],'plan':raw['plan'],
        'hosts':req.target_hosts,'corrections':{k:v for k,v in params.items() if k in {'vlan_id','name'}},'model':req.model})
    if digest(inventory(db)) != previous['inventory_hash']:
        raise HTTPException(409,'Inventory changed during validation. Start a fresh preview.')
    plan=output['plan']; task=plan['tasks'][0]
    if plan['status']!='ready':
        raise HTTPException(422, {'message':'V9 validation requires correction.', 'issues':[i['message'] for i in task['issues']+plan['issues']]})
    values=task['parameters']; host=task['target_devices'][0]['hostname']
    config={'vlan_id':values['vlan_id'],'state':'active'}
    if values.get('name'): config['name']=values['name']
    playbook=yaml.safe_dump([{'name':'V9 validated VLAN creation','hosts':[host],'gather_facts':False,'tasks':[
        {'name':'Ensure validated VLAN exists','cisco.ios.ios_vlans':{'config':[config],'state':'merged'}}]}],sort_keys=False)
    from config_engine.safety import validate_playbook_yaml
    report=validate_playbook_yaml(playbook_yaml=playbook,vendor='cisco_ios',feature='vlan',target_hosts=[host],execution_engine='ansible_native')
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
        files=[{'path':base+'/playbook.yml','content':playbook}, {'path':base+'/native_config.txt','content':native}, {'path':base+'/v9_review.md','content':explanation}]
        manifest={'engine':'v9','knowledge_snapshot_id':output['release_id'],'session_id':sid,'files':[{'path':f['path']} for f in files]}
        for f in files:
            conn.execute("INSERT INTO authoring_revisions(namespace,path,content,kind,deleted,actor,revision) VALUES ('ansible',?,?,'file',0,?,1)",(f['path'],f['content'],user['username']))
        conn.execute('UPDATE jobs SET ansible_entrypoint_path=?,ansible_artifact_manifest=? WHERE id=?',(files[0]['path'],json.dumps(manifest),jid))
        conn.execute('UPDATE studio_v9_sessions SET body=?,revision=revision+1 WHERE id=?',(json.dumps(output),sid))
        conn.execute('INSERT INTO audit_log(user_id,action,target,details) VALUES (?,?,?,?)',(user['username'],'v9.generate',str(jid),json.dumps(manifest)))
    return {'job_id':jid,'request_id':cr,'status':'playbook_generated','playbook':playbook,'artifact_type':'playbook',
            'entrypoint_path':files[0]['path'],'files':files,'manifest':manifest,'target_hosts':[host]}
