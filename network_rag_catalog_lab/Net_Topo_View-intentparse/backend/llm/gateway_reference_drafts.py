"""Explicit authoring drafts; cannot create a verified variant, job or deployment."""
import asyncio
import json
from pathlib import Path
from uuid import uuid4
from fastapi import HTTPException
from llm.gateway_models import text_digest
from llm.gateway import authorize_studio
from local_providers import v9_studio
from lab_config import BACKEND_DIR


def reference_templates():
    index=BACKEND_DIR/'ansible/reference/operation_drafts/index.json'
    return json.loads(index.read_text(encoding='utf-8'))['templates'] if index.is_file() else []


async def render_reference(db,user,body):
    authorize_studio(user)
    if len(json.dumps(body.reference_values))>64000:
        raise HTTPException(422,'Reference input limit exceeded')
    previous=v9_studio.session(db,body.session_id,user['username'])
    inventory=v9_studio.inventory(db)
    if previous['revision']!=body.expected_revision or v9_studio.digest(inventory)!=previous['inventory_hash']:
        raise HTTPException(409,'Review or inventory changed. Reopen the interpretation.')
    raw=json.loads(previous['body']); tasks=raw['plan']['tasks']
    if not tasks: raise HTTPException(422,'Add at least one reviewed operation.')
    templates=reference_templates(); inputs=[]; versions=[]
    for task in tasks:
        if len(task['target_devices'])!=1 or not task['operation_id']:
            raise HTTPException(422,'Choose one existing target and operation for every draft task.')
        device=task['target_devices'][0]
        row=next((r for r in templates if r['operation_id']==task['operation_id'] and r['vendor']==device['vendor']),None)
        if not row: raise HTTPException(422,'No editable reference template exists for this operation/vendor.')
        path=(BACKEND_DIR/'ansible'/row['path']).resolve()
        if not path.is_relative_to((BACKEND_DIR/'ansible/reference/operation_drafts').resolve()) or path.is_symlink():
            raise HTTPException(403,'Invalid reference template path')
        content=path.read_text(encoding='utf-8');versions.append((path,text_digest(content)))
        inputs.append({'task_id':task['intent_id'],'operation_id':task['operation_id'],'device':device,
            'parameters':task['parameters'],'extra':body.reference_values.get(task['intent_id'],{}),
            'template':content,'input_contract':row.get('input_contract'),'source_path':row['path'],'source_digest':text_digest(content)})
    result=await asyncio.to_thread(v9_studio.worker,{'action':'reference_render','inventory':inventory,'templates':inputs,
        'release_id':raw['release_id'],'model':body.model or 'reference-template'})
    if (v9_studio.session(db,body.session_id,user['username'])['revision']!=body.expected_revision
        or v9_studio.digest(v9_studio.inventory(db))!=previous['inventory_hash']
        or any(text_digest(path.read_text(encoding='utf-8'))!=digest for path,digest in versions)):
        raise HTTPException(409,'A source changed during draft rendering; review again.')
    from llm.gateway_knowledge import read_release
    from local_providers.knowledge import knowledge_root
    _,_,pointer=read_release(knowledge_root()/'storage/catalog_releases')
    if pointer['release_id']!=result['release_id']:
        raise HTTPException(409,'Published source changed; review again.')
    validation={'status':'unvalidated','scope':'reference_authoring','syntax':'not_run','lint':'not_run',
        'platform_compatibility':'not_established','semantic_validation':'not_established','device_testing':'not_run',
        'deployment_authorized':False,'source_release':result['release_id'],'templates':[{'path':row['source_path'],'digest':row['source_digest']} for row in inputs]}
    documents=[]
    if body.output_kind=='reference_playbook':
        import yaml
        plays=[]
        for item in result['documents']:
            vendor=item['device']['vendor']
            if vendor=='huawei':
                raise HTTPException(422,'Huawei native drafts are available. Ansible output requires a maintained and reviewed Huawei collection; no deprecated module was substituted.')
            junos=vendor=='juniper'
            module='junipernetworks.junos.junos_config' if junos else 'cisco.ios.ios_config'
            plays.append({'name':item['operation_id']+' · editable reference draft','hosts':item['device']['hostname'],
                'gather_facts':False,'connection':'ansible.netcommon.netconf' if junos else 'ansible.netcommon.network_cli',
                'vars':{'ansible_network_os':'junipernetworks.junos.junos' if junos else 'cisco.ios.ios'},
                'tasks':[{'name':item['operation_id'],module:({'lines':item['content'].splitlines(),'src_format':'set'} if junos else {'lines':item['content'].splitlines()})}]})
        content='# EDITABLE REFERENCE DRAFT — syntax, lint, dependencies and platform compatibility require review.\n'+yaml.safe_dump(plays,sort_keys=False,allow_unicode=True)
        documents=[{'id':uuid4().hex,'path':'playbooks/drafts/reference-combined-'+uuid4().hex[:8]+'.yml','device_id':'','content':content}]
    else:
        import re
        for index,item in enumerate(result['documents']):
            host=re.sub(r'[^a-zA-Z0-9_-]','_',item['device']['hostname'])
            documents.append({'id':uuid4().hex,'path':f'playbooks/drafts/reference-{index+1:02d}-{host}-{item["operation_id"]}-{uuid4().hex[:8]}.cfg',
                'device_id':item['device']['id'],'task_id':item['task_id'],'content':item['content']})
    for document in documents:
        selected=[row for row in inputs if document.get('task_id')==row['task_id']] if document.get('task_id') else inputs
        document['reference']={'path':', '.join(row['source_path'] for row in selected),'content':'\n\n'.join(row['template'] for row in selected)}
        document.update(validation=validation,saved=False,execution_available=False,digest=text_digest(document['content']))
    return {**documents[0],'documents':documents,'output_kind':body.output_kind,'task_count':len(tasks)}
