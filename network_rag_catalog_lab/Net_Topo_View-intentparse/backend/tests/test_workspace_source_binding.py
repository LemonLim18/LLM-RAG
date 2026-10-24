"""Source ownership is resolved against exact authorized buffers, not model paths."""
import asyncio,json,sys
from pathlib import Path
from unittest.mock import AsyncMock,patch
import pytest
from fastapi import HTTPException
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(1,str(Path(__file__).resolve().parent))
from test_phase_g_workspace import workspace,async_test
from llm.gateway_models import TurnRequest
from llm.gateway_workspace import propose_related,WorkspaceProposalFailure,related_context
from uuid import uuid4


def request(active,var,prompt='Change neighbor_ip to 192.0.2.3 and # UNSAVED_MAIN to # REVIEWED_MAIN; preserve all other lines.'):
    return TurnRequest(request_id=uuid4(),prompt=prompt,editor=active,related_editors=[var])


def changes():
    return {'replacements':[{'old_text':'# UNSAVED_MAIN','new_text':'# REVIEWED_MAIN'},
        {'old_text':'neighbor_ip: 192.0.2.2','new_text':'neighbor_ip: 192.0.2.3'}]}


@async_test
async def test_two_file_edits_are_bound_by_the_server_without_filename_assignment(workspace):
    db,store,active,var=workspace
    async def generate(messages,structured,**kwargs):
        assert 'files' not in structured['properties'] and 'path' not in structured['properties']
        sources=json.loads(messages[1]['content'])['sources']
        assert {s['path']:s['content'] for s in sources}=={active.path:active.content,var.path:var.content}
        assert set(structured['$defs']['WorkspaceReplacement']['properties']['source_ref']['enum'])=={None,*[s['source_ref'] for s in sources]}
        return json.dumps(changes()),'mock'
    docs,_=related_context(db,active,[var])
    with patch('local_providers.chat.generate',side_effect=generate) as model:
        proposal,_=await propose_related(db,request(active,var),docs,[active,var])
    assert {f['path']:f['suggested'] for f in proposal['files']}=={
        active.path:active.content.replace('# UNSAVED_MAIN','# REVIEWED_MAIN'),
        var.path:var.content.replace('192.0.2.2','192.0.2.3')}
    assert model.call_count==1 and proposal['validation']['model_patch_calls']==1
    assert proposal['validation']['generation_mode']=='content_addressed_workspace'
    assert all(store.latest('ansible',s.path)['revision']==1 for s in [active,var])


@async_test
async def test_explicit_wrong_source_reference_is_rejected_never_relocated(workspace):
    db,store,active,var=workspace
    async def generate(messages,**kwargs):
        sources=json.loads(messages[1]['content'])['sources']
        wrong_ref=next(s['source_ref'] for s in sources if s['path']==var.path)
        wrong=changes();wrong['replacements'][0]['source_ref']=wrong_ref
        return json.dumps(wrong),'mock'
    with patch('local_providers.chat.generate',side_effect=generate) as model:
        with pytest.raises(WorkspaceProposalFailure) as failed:await propose_related(db,request(active,var),[],[active,var])
    assert model.call_count==2 and 'ambiguous' in failed.value.detail
    assert not failed.value.engineering_diagnostics['applied'] and not failed.value.engineering_diagnostics['saved']
    assert all(store.latest('ansible',s.path)['revision']==1 for s in [active,var])


@pytest.mark.parametrize('explicit',[False,True])
@async_test
async def test_ambiguous_anchor_requires_an_exact_source_reference(workspace,explicit):
    db,store,active,var=workspace
    active=active.model_copy(update={'content':active.content+'# COMMON_NOTE\n'})
    var=var.model_copy(update={'content':var.content+'# COMMON_NOTE\n'})
    async def generate(messages,**kwargs):
        replacement={'old_text':'# COMMON_NOTE','new_text':'# CORRECTED_NOTE'}
        if explicit:replacement['source_ref']=next(s['source_ref'] for s in json.loads(messages[1]['content'])['sources'] if s['path']==var.path)
        return json.dumps({'replacements':[replacement]}),'mock'
    with patch('local_providers.chat.generate',side_effect=generate):
        if not explicit:
            with pytest.raises(WorkspaceProposalFailure):await propose_related(db,request(active,var),[],[active,var])
        else:
            proposal,_=await propose_related(db,request(active,var),[],[active,var])
            assert [f['path'] for f in proposal['files']]==[var.path]
            assert proposal['original']==proposal['suggested']==active.content


@async_test
async def test_unknown_or_context_only_source_cannot_enter_the_transaction(workspace):
    db,store,active,var=workspace
    raw=json.dumps({'replacements':[{'source_ref':'private.yml','old_text':'neighbor_ip: 192.0.2.2','new_text':'neighbor_ip: 192.0.2.3'}]})
    with patch('local_providers.chat.generate',AsyncMock(return_value=(raw,'mock'))) as model:
        with pytest.raises(WorkspaceProposalFailure):await propose_related(db,request(active,var),[],[active,var])
    assert model.await_count==2


@async_test
async def test_preserved_source_cannot_make_a_shared_anchor_appear_unambiguous(workspace):
    db,store,active,var=workspace
    active=active.model_copy(update={'content':active.content+'# SHARED_CONTEXT\n'})
    var=var.model_copy(update={'content':var.content+'# SHARED_CONTEXT\n'})
    body=request(active,var,'Keep the playbook unchanged and modify its referenced variable file.')
    raw=json.dumps({'replacements':[{'old_text':'# SHARED_CONTEXT','new_text':'# CHANGED_CONTEXT'}]})
    with patch('local_providers.chat.generate',AsyncMock(return_value=(raw,'mock'))):
        with pytest.raises(WorkspaceProposalFailure) as failed:await propose_related(db,body,[],[active,var])
    assert 'ambiguous' in failed.value.detail


@async_test
async def test_saved_revision_change_during_inference_prevents_bundle_release(workspace):
    db,store,active,var=workspace
    async def generate(messages,**kwargs):
        store.mutate('ansible',var.path,'neighbor_ip: 192.0.2.99\n','other','save',expected_revision=1)
        return json.dumps(changes()),'mock'
    with patch('local_providers.chat.generate',side_effect=generate):
        with pytest.raises(HTTPException) as failed:await propose_related(db,request(active,var),[],[active,var])
    assert failed.value.status_code==409 and store.latest('ansible',active.path)['revision']==1
    assert store.read('ansible',var.path)=='neighbor_ip: 192.0.2.99\n'


@async_test
async def test_cancellation_cannot_release_or_save_a_partial_transaction(workspace):
    db,store,active,var=workspace;entered=asyncio.Event()
    async def generate(messages,**kwargs):entered.set();await asyncio.Event().wait()
    with patch('local_providers.chat.generate',side_effect=generate):
        task=asyncio.create_task(propose_related(db,request(active,var),[],[active,var]))
        await entered.wait();task.cancel()
        with pytest.raises(asyncio.CancelledError):await task
    assert all(store.latest('ansible',s.path)['revision']==1 for s in [active,var])


@async_test
async def test_empty_edits_and_overlaps_are_rejected_with_a_two_call_limit(workspace):
    db,store,active,var=workspace
    for raw in [json.dumps({'replacements':[]}),json.dumps({'replacements':[
        {'old_text':'neighbor_ip: 192.0.2.2','new_text':'neighbor_ip: 192.0.2.3'},
        {'old_text':'192.0.2.2','new_text':'192.0.2.4'}]})]:
        with patch('local_providers.chat.generate',AsyncMock(return_value=(raw,'mock'))) as model:
            with pytest.raises(WorkspaceProposalFailure) as failed:await propose_related(db,request(active,var),[],[active,var])
        assert model.await_count==2 and not failed.value.engineering_diagnostics['saved']


@async_test
async def test_active_plus_eight_related_sources_retains_existing_changed_file_budget(workspace):
    db,store,active,var=workspace
    snapshots=[active,var];replacements=[changes()['replacements'][1]]
    for number in range(7):
        path=f'playbooks/g8/extra{number}.yml';content=f'# RELATED_{number}_BEFORE\n'
        store.mutate('ansible',path,content,'fixture','create')
        snapshots.append(var.model_copy(update={'document_id':path,'path':path,'content':content,'model_id':path}))
        replacements.append({'old_text':f'# RELATED_{number}_BEFORE','new_text':f'# RELATED_{number}_AFTER'})
    body=request(active,var).model_copy(update={'related_editors':snapshots[1:]})
    with patch('local_providers.chat.generate',AsyncMock(return_value=(json.dumps({'replacements':replacements}),'mock'))):
        proposal,_=await propose_related(db,body,[],snapshots)
    assert len(proposal['files'])==8 and proposal['original']==proposal['suggested']==active.content
    replacements.append(changes()['replacements'][0])
    with patch('local_providers.chat.generate',AsyncMock(return_value=(json.dumps({'replacements':replacements}),'mock'))) as model:
        with pytest.raises(WorkspaceProposalFailure) as failed:await propose_related(db,body,[],snapshots)
    assert model.await_count==2 and 'eight changed-file' in failed.value.detail
