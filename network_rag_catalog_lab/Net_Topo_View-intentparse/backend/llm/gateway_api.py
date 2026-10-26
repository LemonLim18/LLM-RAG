"""Authenticated shared surface. Explicit reviewed handoff; no conversational publication or execution."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import Field

from auth.auth import get_current_user, normalize_role
from llm.gateway_models import StrictModel, TurnRequest, TurnResponse,EditorSnapshot
from llm.gateway import AIGateway

router = APIRouter(prefix='/api/v1/ai', tags=['Shared local AI'])


async def require_ai_user(user=Depends(get_current_user)):
    # Legacy get_current_user permits anonymous viewing. Shared AI never does.
    if not user.get('user_id') or user.get('username')=='anonymous':
        raise HTTPException(401,'Authentication is required for shared AI',headers={'WWW-Authenticate':'Bearer'})
    if normalize_role(user.get('role')) not in {'admin','engineer','auditor'}:
        raise HTTPException(403,'AI access is not authorized')
    return user


def gateway(request: Request):
    return AIGateway(request.app.state.local_db)


class CreateConversation(StrictModel):
    assistant_kind: str = Field(pattern='^(floating|studio)$')
    id: str | None = Field(default=None, min_length=1, max_length=200)


class ApproveSyntheticCloud(StrictModel):
    turn: TurnRequest
    expected_source_revision: str = Field(min_length=1,max_length=200)


@router.get('/hybrid-context')
def get_hybrid_context(service=Depends(gateway),user=Depends(require_ai_user)):
    from llm.gemini_provider import hybrid_context
    context=hybrid_context(service.db)
    context['eligible']=context['eligible'] and normalize_role(user.get('role')) in {'admin','engineer'}
    return context


@router.post('/conversations/{identity}/approve-synthetic-cloud')
def approve_synthetic_cloud(identity:str,body:ApproveSyntheticCloud,service=Depends(gateway),user=Depends(require_ai_user)):
    from llm.gemini_provider import approve_hybrid_request
    return approve_hybrid_request(service.db,service.store,user,identity,body.turn,body.expected_source_revision)


class ReviewSelection(StrictModel):
    task_id: str | None = Field(default=None,max_length=200)
    # Empty only retains an existing unresolved server task; the worker rejects
    # new or altered unresolved entries and rendering still requires V9 ready.
    operation_id: str = Field(max_length=100)
    target_host: str = Field(default='',max_length=200)
    parameters: dict = Field(default_factory=dict)
    template_id: str | None = Field(default=None,max_length=240)


class StudioPreview(StrictModel):
    conversation_id: str
    prompt: str = Field(min_length=1,max_length=20000)
    model: str | None = None
    output_kind: str = Field(default='native',pattern='^(native|playbook)$')
    params: dict = Field(default_factory=dict)
    hosts: list[str] = Field(default_factory=list,max_length=24)
    task_id: str | None = None
    expected_revision: int | None = Field(default=None,ge=1)
    confirm_order: bool = False
    refresh_inventory: bool = False
    selection: list[ReviewSelection] | None = Field(default=None,max_length=24)


class StudioRender(StrictModel):
    conversation_id: str
    session_id: str
    expected_revision: int = Field(ge=1)
    output_kind: str = Field(pattern='^(native|playbook|reference_native|reference_playbook)$')
    reference_values: dict[str,dict] = Field(default_factory=dict)
    model: str | None = None


class SaveDocument(StrictModel):
    path: str = Field(min_length=1,max_length=240)
    content: str = Field(max_length=1000000)
    expected_revision: int = Field(ge=0)
    create: bool = False


class CheckWorkspaceRevisions(StrictModel):
    documents: list[EditorSnapshot] = Field(min_length=1,max_length=8)


@router.post('/documents/check-revisions')
def check_workspace_revisions(body: CheckWorkspaceRevisions,service=Depends(gateway),user=Depends(require_ai_user)):
    from llm.gateway import authorize_studio
    from llm.gateway_workspace import check_saved_revisions
    authorize_studio(user)
    check_saved_revisions(service.db,body.documents)
    return {'status':'unchanged','saved':False,'execution_available':False}


@router.put('/documents')
def save_document(body: SaveDocument,service=Depends(gateway),user=Depends(require_ai_user)):
    from llm.gateway import authorize_studio
    from local_providers.authoring import AuthoringStore
    from ansible.api import _assert_generated_artifact_unlocked
    authorize_studio(user)
    _assert_generated_artifact_unlocked(body.path)
    return AuthoringStore(service.db).mutate('ansible',body.path,body.content,user['username'],
        'create' if body.create else 'save',expected_revision=body.expected_revision)


@router.get('/studio/reference-template')
def open_reference_template(path:str,service=Depends(gateway),user=Depends(require_ai_user)):
    from llm.gateway import authorize_studio
    from llm.gateway_reference_drafts import reference_templates
    from local_providers.authoring import AuthoringStore
    from uuid import uuid4
    authorize_studio(user)
    if path not in {row['path'] for row in reference_templates()}: raise HTTPException(404,'Reference template not found')
    file=AuthoringStore(service.db).resolve('ansible',path)
    return {'id':uuid4().hex,'path':'playbooks/drafts/'+file.parent.name+'-'+uuid4().hex[:8]+'-'+file.name,
        'content':file.read_text(encoding='utf-8'),'device_id':'','validation':{'status':'unvalidated','scope':'editable_reference_copy'}}


@router.get('/studio/catalog')
def studio_catalog(user=Depends(require_ai_user)):
    from llm.gateway import authorize_studio
    from llm.gateway_review import catalog
    authorize_studio(user)
    return catalog()


@router.post('/studio/preview')
async def studio_preview(body: StudioPreview,service=Depends(gateway),user=Depends(require_ai_user)):
    service.store.get(body.conversation_id,user['username'],'studio')
    from llm.gateway_v9 import preview
    return await preview(service.db,user,body.prompt,body.model,body.output_kind,body.params,body.hosts,body.task_id,body.expected_revision,body.confirm_order,[entry.model_dump() for entry in body.selection] if body.selection is not None else None,body.refresh_inventory)


@router.post('/studio/render')
async def studio_render(body: StudioRender,service=Depends(gateway),user=Depends(require_ai_user)):
    service.store.get(body.conversation_id,user['username'],'studio')
    if body.output_kind.startswith('reference_'):
        from llm.gateway_reference_drafts import render_reference
        return await render_reference(service.db,user,body)
    from llm.gateway_v9 import render_draft
    return await render_draft(service.db,user,body)


class InventoryMetadata(StrictModel):
    site: str = Field(max_length=100)
    location: str = Field(max_length=200)
    aliases: list[str] = Field(max_length=30)


class SaveEngineeringFacts(StrictModel):
    facts: dict
    expected_revision: str = Field(pattern='^[a-f0-9]{64}$')


@router.put('/inventory/{device_id}/engineering-facts')
def engineering_facts(device_id:int,body:SaveEngineeringFacts,service=Depends(gateway),user=Depends(require_ai_user)):
    import json
    from llm.gateway import authorize_studio
    from llm.gateway_inventory import EngineeringFacts,facts_revision
    from pydantic import ValidationError
    authorize_studio(user)
    try: facts=EngineeringFacts.model_validate(body.facts).model_dump() if body.facts else {}
    except ValidationError as exc: raise HTTPException(422,str(exc)) from exc
    with service.db._connect() as c:
        c.execute('BEGIN IMMEDIATE')
        row=c.execute('SELECT engineering_facts_json FROM devices WHERE id=?',(device_id,)).fetchone()
        if not row: raise HTTPException(404,'Device not found')
        if facts_revision(json.loads(row[0]))!=body.expected_revision: raise HTTPException(409,'Engineering facts changed; reload before saving')
        names={r[0] for r in c.execute('SELECT name FROM interfaces WHERE device_id=?',(device_id,))}
        if any(item['name'] not in names for item in facts.get('interfaces',[])):
            raise HTTPException(422,'Interface facts must reference existing SQLite interfaces')
        c.execute('UPDATE devices SET engineering_facts_json=? WHERE id=?',(json.dumps(facts),device_id))
        c.execute('INSERT INTO audit_log(user_id,action,target,details) VALUES (?,?,?,?)',
            (user['username'],'inventory.engineering_facts',str(device_id),json.dumps({'origin':facts.get('origin'),'revision':facts_revision(facts)})))
    return {'status':'saved','revision':facts_revision(facts),'source':'stored','device_testing':'not_run'}


@router.put('/inventory/{device_id}/metadata')
def inventory_metadata(device_id:int,body:InventoryMetadata,service=Depends(gateway),user=Depends(require_ai_user)):
    import json
    from llm.gateway import authorize_studio
    authorize_studio(user)
    if any(not a.strip() or len(a)>100 for a in body.aliases):
        raise HTTPException(422,'Aliases must be nonempty and at most 100 characters')
    with service.db._connect() as c:
        c.execute('BEGIN IMMEDIATE')
        changed=c.execute('UPDATE devices SET site=?,location=?,aliases_json=? WHERE id=?',
            (body.site,body.location,json.dumps(body.aliases),device_id))
        if not changed.rowcount: raise HTTPException(404,'Device not found')
        c.execute('INSERT INTO audit_log(user_id,action,target,details) VALUES (?,?,?,?)',
            (user['username'],'inventory.metadata',str(device_id),body.model_dump_json()))
    return {'status':'saved','source':'stored'}


@router.post('/conversations')
def create(body: CreateConversation, service=Depends(gateway), user=Depends(require_ai_user)):
    return service.store.create(user['username'], body.assistant_kind, body.id)


@router.get('/conversations')
def conversations(assistant_kind: str, service=Depends(gateway), user=Depends(require_ai_user)):
    if assistant_kind not in {'floating', 'studio'}:
        raise HTTPException(422, 'Unknown assistant')
    return {'sessions': service.store.list(user['username'], assistant_kind)}


@router.get('/conversations/{identity}')
def conversation(identity: str, service=Depends(gateway), user=Depends(require_ai_user)):
    return service.store.present(identity, user['username'])


@router.get('/conversations/{identity}/turns/{request_id}/review')
def restore_generation_review(identity: str, request_id: str, service=Depends(gateway), user=Depends(require_ai_user)):
    from llm.gateway import authorize_studio
    from llm.gateway_v9 import restore_review
    authorize_studio(user)
    service.store.get(identity, user['username'], 'studio')
    preview, prompt = restore_review(service.db, user, service.store.result_for(identity, user['username'], request_id))
    return {'preview': preview, 'prompt': prompt, 'conversation': identity}


@router.delete('/conversations/{identity}')
def delete(identity: str, service=Depends(gateway), user=Depends(require_ai_user)):
    service.store.delete(identity, user['username'])
    return {'deleted': identity}


@router.post('/conversations/{identity}/turns', response_model=TurnResponse)
async def turn(identity: str, body: TurnRequest, request: Request, service=Depends(gateway), user=Depends(require_ai_user)):
    import asyncio
    task = asyncio.create_task(service.turn(identity, user, body))
    try:
        while not task.done():
            if await request.is_disconnected():
                task.cancel()
                raise HTTPException(499, 'Client disconnected; late results discarded')
            await asyncio.wait({task}, timeout=0.25)
        return await task
    finally:
        if not task.done():
            task.cancel()


@router.post('/conversations/{identity}/turns/{request_id}/cancel')
def cancel(identity: str, request_id: UUID, service=Depends(gateway), user=Depends(require_ai_user)):
    service.store.cancel(identity, user['username'], str(request_id))
    return {'status': 'cancelled'}


@router.get('/inventory')
async def inventory(service=Depends(gateway), user=Depends(require_ai_user)):
    from llm.tools import ToolAuthorization
    from auth.auth import normalize_role
    auth = ToolAuthorization(user['username'], normalize_role(user['role']), 'floating', '', frozenset({'inventory.read'}))
    return await service.registry.invoke('inventory.read', {}, auth)


@router.get('/diagnostics')
async def diagnostics(user=Depends(require_ai_user)):
    from llm.gateway_diagnostics import diagnose
    return await diagnose()


@router.post('/conversations/{identity}/attachments')
async def upload(identity: str, request: Request, service=Depends(gateway), user=Depends(require_ai_user)):
    from urllib.parse import unquote
    from llm.gateway_documents import upload_attachment
    service.store.get(identity, user['username'])
    data=bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data)>10*1024*1024: raise HTTPException(413,'Attachment exceeds 10 MiB')
    name=unquote(request.headers.get('x-file-name',''))
    return await upload_attachment(service.db, identity, user['username'], name, bytes(data))


@router.get('/conversations/{identity}/attachments')
def attachments(identity:str,service=Depends(gateway),user=Depends(require_ai_user)):
    service.store.get(identity,user['username'])
    with service.db._connect() as c:
        rows=c.execute('SELECT id,name,byte_size FROM ai_attachments WHERE conversation_id=? AND owner=? ORDER BY rowid', (identity,user['username'])).fetchall()
    return {'attachments':[dict(r) for r in rows]}


@router.get('/conversations/{identity}/attachments/{attachment_id}')
def attachment(identity:str,attachment_id:UUID,service=Depends(gateway),user=Depends(require_ai_user)):
    import json
    service.store.get(identity,user['username'])
    with service.db._connect() as c:
        row=c.execute('SELECT * FROM ai_attachments WHERE id=? AND conversation_id=? AND owner=?', (str(attachment_id),identity,user['username'])).fetchone()
    if not row: raise HTTPException(404,'Attachment not found')
    if __import__('pathlib').Path(row['name']).suffix.lower() in {'.pdf','.png','.jpg','.jpeg','.webp'}: raise HTTPException(422,'PDF attachments are analysis-only; open a text document for editing')
    return {'id':row['id'],'name':row['name'],'content':''.join(s['text'] for s in json.loads(row['segments']))}


@router.delete('/conversations/{identity}/attachments/{attachment_id}')
def remove_attachment(identity: str, attachment_id: UUID, service=Depends(gateway), user=Depends(require_ai_user)):
    service.store.get(identity, user['username'])
    with service.db._connect() as c:
        c.execute('DELETE FROM ai_attachments WHERE id=? AND conversation_id=? AND owner=?',
                  (str(attachment_id), identity, user['username']))
    return {'deleted': str(attachment_id)}


class PrepareHandoff(StrictModel):
    source_turn: UUID
    requested_action: str = Field(min_length=1,max_length=4000)


@router.get('/conversations/{identity}/turns/{request_id}/handoff-eligibility')
def handoff_eligibility(identity:str,request_id:UUID,service=Depends(gateway),user=Depends(require_ai_user)):
    from llm.gateway_handoff import eligibility
    return eligibility(service,user,identity,str(request_id))


@router.post('/conversations/{identity}/handoffs')
def prepare_handoff(identity:str,body:PrepareHandoff,service=Depends(gateway),user=Depends(require_ai_user)):
    from llm.gateway_handoff import prepare
    return prepare(service,user,identity,str(body.source_turn),body.requested_action)


@router.post('/handoffs/{identity}/accept')
def accept_handoff(identity:UUID,service=Depends(gateway),user=Depends(require_ai_user)):
    from llm.gateway_handoff import accept
    return accept(service,user,str(identity))
