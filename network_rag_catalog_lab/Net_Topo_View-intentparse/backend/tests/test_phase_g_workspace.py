"""Workspace contract tests: real authoring/registry/graph; model output mocked."""
import json
import asyncio
from functools import wraps
from pathlib import Path
import sys
from uuid import uuid4
from unittest.mock import AsyncMock,patch

import pytest
from fastapi import HTTPException

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from db.manager import DatabaseManager
from llm.gateway_store import ensure_schema,ConversationStore
from llm.gateway_models import EditorSnapshot,TurnRequest,ToolResult,text_digest
from llm.gateway_workspace import reference_path,related_context,propose_related
from llm.tools import ToolAuthorization
from local_providers.authoring import AuthoringStore


def async_test(function):
    @wraps(function)
    def run(*args,**kwargs):return asyncio.run(function(*args,**kwargs))
    return run


@pytest.fixture
def workspace(tmp_path,monkeypatch):
    from local_providers import authoring
    root=tmp_path/'files';root.mkdir()
    monkeypatch.setattr(authoring,'ROOTS',{'ansible':root})
    db=DatabaseManager(str(tmp_path/'app.db'));db.initialize();ensure_schema(db)
    store=AuthoringStore(db)
    main='- hosts: R1\n  vars_files:\n    - group_vars/all.yml\n  tasks:\n    - name: Keep routing variable\n      ansible.builtin.debug:\n        msg: "{{ neighbor_ip }}"\n'
    variables='neighbor_ip: 192.0.2.2\n# KEEP_VARIABLE_COMMENT\n'
    for path,text in [('playbooks/g8/main.yml',main),('playbooks/g8/group_vars/all.yml',variables)]:store.mutate('ansible',path,text,'fixture','create')
    def snap(path,text):return EditorSnapshot(document_id=path,path=path,content=text,language='yaml',model_id='model-'+path,model_version=4,buffer_epoch=2,saved_revision=1,is_dirty=True,read_only=False)
    active=snap('playbooks/g8/main.yml',main+'# UNSAVED_MAIN\n')
    var=snap('playbooks/g8/group_vars/all.yml',variables+'# UNSAVED_VARIABLES\n')
    yield db,store,active,var
    db.close()


@pytest.mark.parametrize('path',['../../outside.yml','/etc/passwd','https://example.com/x','{{ lookup("file", "x") }}','C:\\secret.yml','*.yml'])
def test_reference_paths_reject_escape_remote_dynamic_and_globs(path):
    with pytest.raises(ValueError):reference_path('playbooks/main.yml',path)


def test_related_reads_use_unsaved_buffer_and_literal_reference_not_all_open_tabs(workspace):
    db,store,active,var=workspace
    unrelated=var.model_copy(update={'path':'playbooks/private.yml','document_id':'unrelated','saved_revision':999,'content':'UNRELATED_SECRET'})
    docs,report=related_context(db,active,[var,unrelated])
    assert len(docs)==1 and docs[0]['source']==var.path and docs[0]['text']==var.content
    assert docs[0]['unsaved'] and report['complete']
    assert 'UNRELATED_SECRET' not in json.dumps(docs)


def test_saved_revision_conflict_stops_context_before_model_use(workspace):
    db,store,active,var=workspace
    store.mutate('ansible',var.path,'neighbor_ip: 192.0.2.9\n','other','save',expected_revision=1)
    with pytest.raises(HTTPException) as exc:related_context(db,active,[var])
    assert exc.value.status_code==409


def test_reference_cycles_are_bounded_and_missing_dynamic_sources_are_disclosed(workspace):
    db,store,active,var=workspace
    store.mutate('ansible','playbooks/g8/child.yml','- import_playbook: main.yml\n','fixture','create')
    active=active.model_copy(update={'content':'- import_playbook: child.yml\n- import_playbook: absent.yml\n- import_playbook: "{{ dynamic }}"\n'})
    docs,report=related_context(db,active,[])
    assert [d['source'] for d in docs]==['playbooks/g8/child.yml']
    assert not report['complete'] and len(report['limitations'])==2


@async_test
async def test_authorized_document_tool_uses_related_source_but_floating_is_denied(workspace):
    from llm.gateway_services import registry_for
    db,store,active,var=workspace
    repository=ConversationStore(db);cid=repository.create('owner','studio')['id']
    auth=ToolAuthorization('owner','engineer','studio',cid,frozenset({'document.read'}))
    body=TurnRequest(request_id=uuid4(),prompt='Explain the playbook and where its neighbor variable is defined.',editor=active,related_editors=[var])
    result=await registry_for(db).invoke('document.read',{'turn':body.model_dump(mode='json')},auth)
    assert result.status=='success'
    assert var.content in ''.join(d['text'] for d in result.data['context'])
    assert any(e.source==var.path for e in result.evidence)
    floating=repository.create('owner','floating')['id']
    with pytest.raises(HTTPException) as exc:
        await registry_for(db).invoke('document.read',{'turn':body.model_dump(mode='json')},ToolAuthorization('owner','engineer','floating',floating,frozenset({'document.read'})))
    assert exc.value.status_code==403


@async_test
async def test_bundle_changes_authoritative_variables_preserves_other_text_and_does_not_save(workspace):
    from llm.orchestration.studio import validate_proposal
    db,store,active,var=workspace
    body=TurnRequest(request_id=uuid4(),prompt='Change the neighbor address to 192.0.2.3 in the referenced variable file; keep the playbook and all comments.',editor=active,related_editors=[var])
    raw=json.dumps({'replacements':[{'old_text':'neighbor_ip: 192.0.2.2','new_text':'neighbor_ip: 192.0.2.3'}]})
    docs,_=related_context(db,active,[var])
    with patch('local_providers.chat.generate',AsyncMock(return_value=(raw,'mock-qwen'))):proposal,model=await propose_related(db,body,docs,[active,var])
    assert proposal['original']==proposal['suggested']==active.content
    assert proposal['files'][0]['suggested']==var.content.replace('192.0.2.2','192.0.2.3')
    validate_proposal(ToolResult(status='success',data={'proposal':proposal}),body)
    from llm.orchestration.studio import proposal_explanation
    explanation=proposal_explanation({'proposal':proposal},active,[var])
    assert var.path in explanation and '192.0.2.3' in explanation and 'remains proposed' in explanation
    assert proposal['model_attempts'][0]['response']==raw
    assert proposal['validation']['generation_mode']=='content_addressed_workspace'
    assert store.latest('ansible',var.path)['revision']==1 and '192.0.2.2' in store.read('ansible',var.path)
    assert model=='mock-qwen' and proposal['validation']['saved'] is False


@async_test
async def test_model_cannot_choose_unrelated_file_or_overlapping_anchor(workspace):
    db,store,active,var=workspace
    body=TurnRequest(request_id=uuid4(),prompt='Update the referenced variable.',editor=active,related_editors=[var])
    raw=json.dumps({'files':[{'path':'playbooks/private.yml','replacements':[{'old_text':'x','new_text':'y'}]}]})
    with patch('local_providers.chat.generate',AsyncMock(return_value=(raw,'mock'))) as model:
        with pytest.raises(HTTPException) as exc:await propose_related(db,body,[],[active,var])
    assert model.await_count==2 and store.latest('ansible',var.path)['revision']==1
    assert len(exc.value.engineering_diagnostics['attempts'])==2
    assert not exc.value.engineering_diagnostics['applied']


def test_legacy_turn_serialization_keeps_existing_idempotency_hash():
    body=TurnRequest(request_id='00000000-0000-0000-0000-000000000001',prompt='hello')
    expected='{"request_id":"00000000-0000-0000-0000-000000000001","prompt":"hello","model":null,"editor":null,"attachment_ids":[]}'
    assert body.model_dump_json()==expected and 'related_editors' not in body.model_dump()


@async_test
async def test_explicit_unchanged_active_file_is_context_not_a_patch_target(workspace):
    db, store, active, var = workspace
    body = TurnRequest(request_id=uuid4(), prompt='Change the referenced neighbor_ip to 192.0.2.3. Keep the playbook and every comment unchanged.', editor=active, related_editors=[var])
    wrong = json.dumps({'files':[
        {'path':active.path,'replacements':[{'old_text':'# UNSAVED_MAIN','new_text':'# UNSAVED_MAIN\n# UNSAVED_MAIN'}]},
        {'path':var.path,'replacements':[{'old_text':'neighbor_ip: 192.0.2.2','new_text':'neighbor_ip: 192.0.2.3'}]}]})
    correct = json.dumps({'replacements':[{'old_text':'neighbor_ip: 192.0.2.2','new_text':'neighbor_ip: 192.0.2.3'}]})
    docs, _ = related_context(db, active, [var])
    with patch('local_providers.chat.generate', AsyncMock(side_effect=[(wrong,'mock'),(correct,'mock')])) as model:
        proposal, _ = await propose_related(db, body, docs, [active,var])
    assert model.await_count == 2
    assert proposal['original'] == proposal['suggested'] == active.content
    assert proposal['files'][0]['path'] == var.path
    assert proposal['validation']['preserved_paths'] == [active.path]
    assert 'validation_error' in proposal['model_attempts'][0]
    request = json.loads(model.call_args_list[0].args[0][1]['content'])
    assert [s['path'] for s in request['sources'] if s['editable']]==[var.path]
    assert request['preserved_paths'] == [active.path]
    assert store.latest('ansible', var.path)['revision'] == 1


@pytest.mark.parametrize('comments', [
    '# KEEP_VARIABLE_COMMENT\n# KEEP_VARIABLE_COMMENT\n# UNSAVED_VARIABLES\n',
    '# UNSAVED_VARIABLES\n',
    '# UNSAVED_VARIABLES\n# KEEP_VARIABLE_COMMENT\n',
])
def test_explicit_comment_preservation_rejects_duplicates_removal_and_reordering(workspace, comments):
    from types import SimpleNamespace
    from llm.gateway_documents import validate_edit_intent
    _, _, _, var = workspace
    with pytest.raises(HTTPException) as error:
        validate_edit_intent(SimpleNamespace(editor=var,prompt='Keep every comment unchanged; update the parameter.'),
                             'neighbor_ip: 192.0.2.3\n'+comments)
    assert error.value.status_code == 422


def test_comment_preservation_allows_the_requested_value_change(workspace):
    from types import SimpleNamespace
    from llm.gateway_documents import validate_edit_intent
    _, _, _, var = workspace
    checks = validate_edit_intent(SimpleNamespace(editor=var,prompt='Keep every comment unchanged; update the parameter.'),
                                 var.content.replace('192.0.2.2','192.0.2.3'))
    assert 'full_line_comments_preserved' in checks


@async_test
async def test_real_graph_coordinates_bundle_once_and_replay_rechecks_every_saved_revision(workspace,monkeypatch):
    from llm.gateway import AIGateway
    from llm.gateway_routing import SemanticRoute
    monkeypatch.setenv('COGNISHIELD_AI_ENGINE','langgraph_b3')
    monkeypatch.setenv('COGNISHIELD_AI_PLANNING','0')
    monkeypatch.setenv('COGNISHIELD_AI_SYNTHESIS','0')
    db,store,active,var=workspace;service=AIGateway(db);user={'username':'owner','role':'engineer'}
    cid=service.store.create('owner','studio')['id']
    body=TurnRequest(request_id=uuid4(),prompt='In these files change the neighbor variable to 192.0.2.3; keep comments.',editor=active,related_editors=[var])
    raw=json.dumps({'replacements':[{'old_text':'neighbor_ip: 192.0.2.2','new_text':'neighbor_ip: 192.0.2.3'}]})
    with patch('llm.orchestration.engine.select_context',AsyncMock(return_value=SemanticRoute(intent='edit',use_editor=True))),patch('local_providers.chat.generate',AsyncMock(return_value=(raw,'mock-qwen'))) as model:
        result=await service.turn(cid,user,body)
        assert result.kind=='edit_proposal' and result.proposal['files'][0]['path']==var.path
        again=await service.turn(cid,user,body)
        assert again.proposal==result.proposal and model.await_count==1
    store.mutate('ansible',var.path,'neighbor_ip: 192.0.2.8\n','other','save',expected_revision=1)
    with pytest.raises(HTTPException) as exc:await service.turn(cid,user,body)
    assert exc.value.status_code==409
