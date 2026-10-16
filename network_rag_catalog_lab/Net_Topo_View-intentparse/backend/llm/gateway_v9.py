"""Shared V9 service adapter. Preserve the existing published worker and contracts."""
import asyncio
import json
from types import SimpleNamespace

from fastapi import HTTPException

from llm.gateway import authorize_studio
from local_providers import v9_studio


async def preview(db,user,prompt,model,output_kind='native',params=None,hosts=None,task_id=None,expected_revision=None,confirm_order=False,selection=None):
    authorize_studio(user)
    result=await v9_studio.preview(db,SimpleNamespace(intent_description=prompt,model=model,params=params or {},target_hosts=hosts or [],allow_multi=True,task_id=task_id,expected_revision=expected_revision,confirm_order=confirm_order,selection=selection),user)
    result['output_kind']=output_kind
    if output_kind=='playbook':
        from llm.gateway_knowledge import read_release
        from local_providers.knowledge import knowledge_root
        _, manifest, _ = read_release(knowledge_root()/'storage/catalog_releases')
        support=[]
        devices=v9_studio.inventory(db)
        for item in result.get('tasks',[result]):
            target=next((d for d in devices if d['hostname'] in item['target_hosts']),None)
            matches=[v for v in manifest.get('cognishield_playbooks',{}).get('variants',[]) if
                v['operation_id']==item['parsed_intent']['action'] and target and v['vendor']==target['vendor'] and
                v['platform']==target['platform'] and target['version'] in v['versions']]
            support.append({'task_id':item.get('task_id'),'supported':len(matches)==1})
        supported=bool(support) and all(i['supported'] for i in support)
        result['playbook_support']={'status':'published_requires_validation' if supported else 'unsupported', 'tasks':support,
            'message':'Each vendor variant will be validated before the combined playbook is returned.' if supported else 'A reviewed Ansible variant is missing for one or more operations or targets. You can review native configuration for the whole request.'}
    return result


async def render_draft(db,user,body):
    from uuid import uuid4
    from llm.gateway_models import text_digest
    authorize_studio(user)
    previous=v9_studio.session(db,body.session_id,user['username'])
    if previous['revision']!=body.expected_revision:
        raise HTTPException(409,'Preview changed; review it again')
    inventory=v9_studio.inventory(db)
    if v9_studio.digest(inventory)!=previous['inventory_hash']:
        raise HTTPException(409,'Inventory changed; start a new preview')
    raw=json.loads(previous['body'])
    output=await asyncio.to_thread(v9_studio.worker,{'inventory':inventory,'prompt':previous['prompt'],
        'plan':raw['plan'],'hosts':[],'corrections':{},'model':body.model,'allow_multi':True})
    if v9_studio.digest(v9_studio.inventory(db))!=previous['inventory_hash'] or v9_studio.session(db,body.session_id,user['username'])['revision']!=body.expected_revision:
        raise HTTPException(409,'Preview or inventory changed during rendering')
    if output['plan']['status']!='ready': raise HTTPException(422,'Complete all V9 clarification before rendering')
    tasks=output['plan']['tasks']
    drafts=[]
    for index,task in enumerate(tasks):
        if len(task['configs'])!=1 or len(task['target_devices'])!=1:
            raise HTTPException(422,'Every operation must resolve to one validated device binding before output.')
        if body.output_kind=='native':
            content=task['configs'][0]['configuration']
            suffix=(output.get('task_artifacts',{}).get(task['intent_id']) or output.get('artifact_metadata') or {}).get('extension','.cfg')
            validation={'status':'passed','scope':'v9_operation','knowledge_release':output['release_id'],
                'device_testing':'not_run','deployment_authorized':False}
        else:
            from llm.gateway_playbooks import render_playbook
            content,validation=await render_playbook(output,task)
            suffix='.yml'
        import re
        host=re.sub(r'[^a-zA-Z0-9_-]','_',task['target_devices'][0]['hostname'])
        drafts.append({'id':uuid4().hex,'path':f"playbooks/drafts/{index+1:02d}-{host}-{task['operation_id']}-{uuid4().hex[:8]}{suffix}",
            'task_id':task['intent_id'],'content':content,'device_id':task['device_id'],'digest':text_digest(content),
            'validation':validation,'saved':False,'execution_available':False})
    if body.output_kind=='playbook' and len(drafts)>1:
        from llm.gateway_playbooks import combine_playbooks
        content,validation=await combine_playbooks(drafts)
        drafts=[{**drafts[0],'id':uuid4().hex,'path':'playbooks/drafts/combined-'+uuid4().hex[:8]+'.yml',
                 'device_id':'','content':content,'digest':text_digest(content),'validation':validation}]
    # Validation can take time: recheck authority and every source before releasing any output.
    from llm.gateway_knowledge import read_release
    from local_providers.knowledge import knowledge_root
    if read_release(knowledge_root()/'storage/catalog_releases')[2]['release_id']!=output['release_id'] or v9_studio.digest(v9_studio.inventory(db))!=previous['inventory_hash'] or v9_studio.session(db,body.session_id,user['username'])['revision']!=body.expected_revision:
        raise HTTPException(409,'Knowledge, inventory or review changed during generation. Review again.')
    return {**drafts[0], 'documents':drafts, 'task_count':len(tasks), 'output_kind':body.output_kind}



async def propose_native_edit(db,user,body):
    authorize_studio(user)
    editor=body.editor
    devices=v9_studio.inventory(db)
    device_id=editor.device_id
    if not device_id:
        import re
        match=re.fullmatch(r'playbooks/generated/job_(\d+)/[^/]+',editor.path)
        if match:
            with db._connect() as c:
                row=c.execute('SELECT device_id,owner_username FROM jobs WHERE id=?',(int(match[1]),)).fetchone()
            if row and (user['role']=='admin' or row['owner_username']==user['username']): device_id=str(row['device_id'])
    if not device_id or not any(d['id']==device_id for d in devices):
        raise HTTPException(422,'Choose the document device from local inventory before requesting an operation-aware edit.')
    result=await asyncio.to_thread(v9_studio.worker, {'action':'document_edit','inventory':devices,
        'device_id':device_id,'prompt':body.prompt,'content':editor.content,'model':body.model})
    if v9_studio.digest(v9_studio.inventory(db))!=v9_studio.digest(devices):
        raise HTTPException(409,'Inventory changed during the edit; request a new proposal.')
    from llm.gateway_knowledge import read_release
    from local_providers.knowledge import knowledge_root
    if read_release(knowledge_root()/'storage/catalog_releases')[2]['release_id']!=result['release_id']:
        raise HTTPException(409,'Published knowledge changed during the edit; request a new proposal.')
    return result['proposed_content'], {'model':result['model'],'status':'passed','scope':result['validation'],
        'knowledge_release':result['release_id'],'operation_id':result['operation_id'],
        'platform_compatibility':'published_binding','device_testing':'not_run','deployment_authorized':False}
