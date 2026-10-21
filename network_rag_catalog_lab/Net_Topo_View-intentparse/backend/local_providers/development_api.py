"""Developer-only scenario controls; never registered as conversational tools."""
from fastapi import APIRouter,Depends,HTTPException,Request
from typing import Literal
from pydantic import Field,ValidationError
from llm.gateway_models import StrictModel
from auth.rbac import require_any,require_admin
from llm.gateway_api import require_ai_user
from local_providers.development import active_for

router=APIRouter(prefix='/api/v1/development-network',tags=['Development network'],dependencies=[Depends(require_ai_user)])


def manager(request):
    result=active_for(request.app.state.local_db)
    if not result:raise HTTPException(409,'Explicit local development simulation is disabled; no scenario fallback')
    return result


class Change(StrictModel):
    action: str = Field(pattern='^(select|edit|duplicate|import|reset)$')
    expected_revision: str = Field(max_length=100)
    scenario_id: str | None = None
    definition: dict | None = None


class Transition(StrictModel):
    expected_revision: str
    interface_id: int
    admin_status: str


@router.get('',dependencies=[Depends(require_any)])
def status(request:Request):
    m=active_for(request.app.state.local_db)
    if not m:return {'enabled':False,'message':'Set COGNISHIELD_DEV_SIMULATION=1 in local-lab server configuration and restart to enable.'}
    s,meta=m.snapshot()
    return {'enabled':True,'scenario':s,'context':meta,'catalog':m.catalog()}


@router.get('/schema')
def schema():
    from local_providers.development import Scenario
    return Scenario.model_json_schema()


@router.put('',dependencies=[Depends(require_admin)])
def change(body:Change,request:Request,user=Depends(require_ai_user)):
    m=manager(request)
    try:s,meta=m.change(body.action,body.expected_revision,body.definition,body.scenario_id,owner=user['username'])
    except ValidationError as exc:raise HTTPException(422,exc.errors(include_input=False,include_context=False)) from exc
    return {'enabled':True,'scenario':s,'context':meta,'catalog':m.catalog()}


@router.post('/interface-event',dependencies=[Depends(require_admin)])
def transition(body:Transition,request:Request):
    m=manager(request);m.transition(body.interface_id,body.admin_status,body.expected_revision)
    return status(request)


async def workbench_admin(user=Depends(require_ai_user)):
    from auth.auth import normalize_role
    if normalize_role(user.get('role'))!='admin':raise HTTPException(403,'Scenario authoring requires an authenticated administrator')
    return user


def workbench_manager(request):
    import os
    from lab_config import LOCAL_LAB
    if not LOCAL_LAB or not any(os.getenv(flag)=='1' for flag in ['COGNISHIELD_DEV_WORKBENCH','COGNISHIELD_DEV_SIMULATION']):
        raise HTTPException(409,'Development Workbench is not enabled in this local server configuration')
    result=getattr(request.app.state.local_db,'_development_scenario',None)
    if result is None:raise HTTPException(503,'Restart the local server to attach the configured scenario manager')
    return result


class DraftWrite(StrictModel):
    bundle:dict
    draft_id:str|None=None
    expected_revision:int|None=Field(default=None,ge=1)


class DraftCheck(StrictModel):
    expected_revision:int=Field(ge=1)


class DraftActivate(DraftCheck):
    expected_active:str
    validation_hash:str=Field(pattern=r'^[a-f0-9]{64}$')


def checked(action):
    try:return action()
    except ValidationError as exc:raise HTTPException(422,exc.errors(include_input=False,include_context=False)) from exc
    except (ValueError,KeyError,OSError) as exc:raise HTTPException(422,str(exc)[:3000]) from exc


@router.get('/workbench')
def workbench(request:Request,user=Depends(workbench_admin)):
    from development.source_registry import catalog
    m=workbench_manager(request);s,meta=m.snapshot(fresh=True)
    active_error=''
    try:bundle=m.activated_bundle() if m.is_enabled() else None
    except HTTPException as exc:
        if exc.status_code!=503:raise
        # Admin recovery metadata remains available; no corrupt source bytes
        # enter the conversation runner or replace the selected scenario.
        bundle=None;active_error=str(exc.detail)
    setup=(bundle or {}).get('sources',{}).get('conversation',{})
    setup_data=setup.get('data',{}) if setup.get('status')=='AVAILABLE' else {}
    return {'enabled':m.is_enabled(),'context':meta,'sources':catalog(),'drafts':m.list_drafts(owner=user['username']),
        'active_source_statuses':s.get('source_statuses',{}),'active_activation':m._read().get('workbench_activation'),
        'conversation_setup':{'turns':setup_data.get('turns',[]),'assistant_kind':setup_data.get('assistant_kind','floating')},
        'history':m.history(owner=user['username']),'active_source_error':active_error}


@router.get('/workbench/starter')
def workbench_starter(request:Request,variant:Literal['healthy','acl','conflict']='healthy',user=Depends(workbench_admin)):
    workbench_manager(request)
    from development.starter import starter_bundle
    return starter_bundle(variant)


@router.get('/workbench/schemas')
def workbench_schemas(user=Depends(workbench_admin)):
    from development.bundles import Manifest,SourceFile,source_schema
    from development.source_registry import catalog,BY_KEY
    return {'manifest':Manifest.model_json_schema(),'source':SourceFile.model_json_schema(),'categories':catalog(),
        'source_schemas':{key:source_schema(key) for key in BY_KEY}}


@router.post('/workbench/drafts')
def workbench_save(body:DraftWrite,request:Request,user=Depends(workbench_admin)):
    return checked(lambda:workbench_manager(request).save_draft(body.bundle,owner=user['username'],expected=body.expected_revision,draft_id=body.draft_id))


@router.get('/workbench/drafts/{draft_id}')
def workbench_draft(draft_id:str,request:Request,user=Depends(workbench_admin)):
    return workbench_manager(request).get_draft(draft_id,owner=user['username'])


@router.post('/workbench/drafts/{draft_id}/validate')
def workbench_validate(draft_id:str,body:DraftCheck,request:Request,user=Depends(workbench_admin)):
    return checked(lambda:workbench_manager(request).validate_draft(draft_id,owner=user['username'],expected=body.expected_revision))


class ExtractDraftFile(DraftCheck):
    category:str=Field(pattern='^(documents|attachments|diagrams)$')
    path:str=Field(min_length=1,max_length=240)


@router.post('/workbench/drafts/{draft_id}/extract')
async def workbench_extract(draft_id:str,body:ExtractDraftFile,request:Request,user=Depends(workbench_admin)):
    import asyncio,base64
    from llm.gateway_documents import extract_attachment
    from development.bundles import compile_bundle
    entry=workbench_manager(request).get_draft(draft_id,owner=user['username'])
    if entry['draft_revision']!=body.expected_revision:raise HTTPException(409,'Draft changed before extraction preview')
    bundle=entry['bundle'];checked(lambda:compile_bundle(bundle))
    item=next((f for f in bundle['sources'][body.category]['data']['files'] if f['path']==body.path),None)
    if item is None:raise HTTPException(404,'Document is not in this owned draft source')
    # Reuse the bounded upload extractor. Never open an arbitrary local path.
    raw=base64.b64decode(bundle['assets'][body.path]['base64'],validate=True)
    segments=await asyncio.to_thread(extract_attachment,item.get('name') or item['path'],raw)
    return {'name':item.get('name') or item['path'],'segments':segments,'origin':'simulated',
        'draft_revision':body.expected_revision,'active':False,'untrusted':True}


@router.post('/workbench/drafts/{draft_id}/activate')
def workbench_activate(draft_id:str,body:DraftActivate,request:Request,user=Depends(workbench_admin)):
    m=workbench_manager(request)
    checked(lambda:m.activate_draft(draft_id,owner=user['username'],expected=body.expected_revision,
        expected_active=body.expected_active,validation_hash=body.validation_hash))
    return workbench(request,user)


class Deactivate(StrictModel):
    expected_active:str


@router.post('/workbench/history/{history_id}/restore')
def workbench_restore(history_id:str,body:Deactivate,request:Request,user=Depends(workbench_admin)):
    m=workbench_manager(request)
    checked(lambda:m.restore_history(history_id,owner=user['username'],expected_active=body.expected_active))
    return workbench(request,user)


@router.post('/workbench/history/{history_id}/draft')
def workbench_copy_history(history_id:str,request:Request,user=Depends(workbench_admin)):
    return checked(lambda:workbench_manager(request).copy_history_draft(history_id,owner=user['username']))


@router.post('/workbench/deactivate')
def workbench_deactivate(body:Deactivate,request:Request,user=Depends(workbench_admin)):
    m=workbench_manager(request);m.deactivate(owner=user['username'],expected_active=body.expected_active)
    return workbench(request,user)
