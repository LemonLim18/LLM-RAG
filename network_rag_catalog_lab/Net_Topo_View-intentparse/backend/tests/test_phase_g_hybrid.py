"""Synthetic remote-policy/transport tests; no real API calls or secret fixtures."""
import asyncio
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
import sys
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from llm.gemini_provider import HybridRequest, external_request_identity, interpret_rest
from llm.gateway_models import Evidence, TurnRequest, EditorSnapshot
from llm.orchestration.model import RoutingModel


@pytest.fixture(autouse=True)
def isolated_google_transport(monkeypatch,tmp_path):
    monkeypatch.setenv('GEMINI_MODEL','gemini-3.5-flash-lite')
    monkeypatch.setenv('COGNISHIELD_AI_MULTI_MODEL_EXPERIMENT','0')
    monkeypatch.setenv('COGNISHIELD_AI_HYBRID','1')
    monkeypatch.setenv('COGNISHIELD_AI_HYBRID_USAGE',str(tmp_path/'usage.json'))


def test_exact_request_history_owner_surface_approval_is_required(monkeypatch):
    body = TurnRequest(request_id=uuid4(), prompt='Explain synthetic records')
    history = []; store = SimpleNamespace(history=lambda identity, user: history)
    connection = sqlite3.connect(':memory:')
    connection.execute('CREATE TABLE ai_attachments(conversation_id TEXT,owner TEXT)')
    @contextmanager
    def connect():
        yield connection
    db = SimpleNamespace(_connect=connect)
    user = {'username': 'synthetic-owner','role':'engineer'}
    monkeypatch.setattr('llm.gemini_provider.scenario_approval_context', lambda db: {'eligible':True,'scenario_digest':'approved','source_revision':'revision'})
    assert HybridRequest.create(db,store,user,'floating','conversation',body,time.monotonic()) is None
    stamp = external_request_identity(user['username'],'floating','conversation',body,history)
    db._ai_external_approvals = {stamp:{'expires':time.monotonic()+120,'scenario_digest':'approved','source_revision':'revision','role_binding':__import__('llm.gemini_provider',fromlist=['hybrid_context']).hybrid_context(db)['role_binding']}}
    assert HybridRequest.create(db,store,user,'floating','conversation',body,time.monotonic())
    assert HybridRequest.create(db,store,user,'studio','conversation',body,time.monotonic()) is None
    assert HybridRequest.create(db,store,{'username':'other'},'floating','conversation',body,time.monotonic()) is None
    assert HybridRequest.create(db,store,user,'floating','other',body,time.monotonic()) is None
    assert HybridRequest.create(db,store,user,'floating','conversation',body.model_copy(update={'prompt':'private replacement'}),time.monotonic()) is None
    history.append({'role':'user','content':'later unapproved history'})
    assert HybridRequest.create(db,store,user,'floating','conversation',body,time.monotonic()) is None
    connection.close()


def test_private_editor_or_attachment_context_cannot_enable_cloud():
    body=TurnRequest(request_id=uuid4(),prompt='Explain',attachment_ids=[uuid4()])
    assert HybridRequest.create(SimpleNamespace(),None,{},'studio','x',body,time.monotonic()) is None


def test_source_provenance_and_structured_complexity_gate():
    scope=HybridRequest(time.monotonic())
    simulated=Evidence(id='s',source='development.state',origin='simulated')
    uploaded=Evidence(id='u',source='private.txt',origin='user_supplied')
    rows=[{'tool':'network.state','status':'success','evidence_ids':['s']}]
    scope.prepare_synthesis(rows,[simulated],{'proposed':{'desired_response':'investigation'}},{})
    assert scope.synthesis_allowed
    scope.prepare_synthesis(rows,[simulated],{'proposed':{'desired_response':'direct'}},{})
    assert not scope.synthesis_allowed
    scope.prepare_synthesis(rows,[simulated],{'proposed':{'desired_response':'direct'}},{'hypotheses':[{'status':'confirmed_within_scenario'}]})
    assert not scope.synthesis_allowed  # Ambient assessment alone cannot escalate a simple lookup.
    scope.prepare_synthesis([{'tool':'document.read','evidence_ids':['u']}],[uploaded],{'proposed':{'desired_response':'investigation'}},{})
    assert not scope.synthesis_allowed


def test_shared_deadline_and_remote_call_limit(monkeypatch):
    monkeypatch.setenv('COGNISHIELD_AI_HYBRID_SECONDS','999')
    scope=HybridRequest(time.monotonic()-100)
    assert 19<scope.remaining()<=20 and scope.budget('routing')==0
    scope.remote_calls=scope.max_remote_calls
    with pytest.raises(HTTPException) as error:
        asyncio.run(scope.generate([],{},'synthesis'))
    assert error.value.status_code==429


def test_stateless_rest_preserves_messages_schema_usage_without_tools(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','synthetic-test-credential')
    schema={'type':'object','properties':{'answer':{'type':'string'}},'required':['answer']}
    captured=[]
    async def send(client,request,**kwargs):
        payload=json.loads(request.content);captured.append(payload)
        assert request.headers['x-goog-api-key']=='synthetic-test-credential'
        return httpx.Response(200,json={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'{"answer":"scoped result"}'}]}}], 'usageMetadata':{'promptTokenCount':10,'candidatesTokenCount':4}},request=request)
    with patch.object(httpx.AsyncClient,'send',send):
        answer,model,usage=asyncio.run(interpret_rest([{'role':'system','content':'original instruction'},
            {'role':'user','content':'synthetic evidence'}],schema,timeout=2))
    assert json.loads(answer)['answer']=='scoped result' and usage['total_output_tokens']==4
    assert captured[0]['generationConfig']['responseFormat']['text']['schema']==schema
    assert captured[0]['systemInstruction']['parts'][0]['text']=='original instruction' and captured[0]['contents'][0]['parts'][0]['text']=='synthetic evidence'
    assert 'tools' not in captured[0] and 'previous_interaction_id' not in captured[0]


@pytest.mark.parametrize('code,status',[(401,'UNAUTHENTICATED'),(403,'PERMISSION_DENIED'),(429,'RESOURCE_EXHAUSTED'),(503,'UNAVAILABLE')])
def test_provider_failures_are_not_model_answers_and_are_not_retried(monkeypatch,code,status):
    monkeypatch.setenv('GEMINI_API_KEY','synthetic-test-credential');calls=[]
    async def send(client,request,**kwargs):
        calls.append(1)
        return httpx.Response(code,json={'error':{'status':status,'message':'synthetic-test-credential'}},request=request)
    with patch.object(httpx.AsyncClient,'send',send),pytest.raises(HTTPException) as error:
        asyncio.run(interpret_rest([{'role':'user','content':'synthetic'}],False,timeout=2))
    assert len(calls)==1 and status in error.value.detail
    assert 'synthetic-test-credential' not in str(error.value.detail)


def test_provider_timeout_is_distinct_from_semantic_rejection(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','synthetic-test-credential')
    async def send(client,request,**kwargs):raise httpx.ReadTimeout('synthetic timeout')
    with patch.object(httpx.AsyncClient,'send',send),pytest.raises(HTTPException) as error:
        asyncio.run(interpret_rest([{'role':'user','content':'synthetic'}],False,timeout=2))
    assert error.value.status_code==504 and 'no semantic verdict' in error.value.detail


def test_provider_service_unavailable_category_is_retained_without_error_body(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','synthetic-test-credential')
    async def send(client,request,**kwargs):
        return httpx.Response(503,json={'error':{'code':'service_unavailable',
            'message':'synthetic-test-credential must not be copied'}},request=request)
    with patch.object(httpx.AsyncClient,'send',send),pytest.raises(HTTPException) as error:
        asyncio.run(interpret_rest([{'role':'user','content':'synthetic'}],False,timeout=2))
    assert error.value.provider_category=='service_unavailable' and error.value.provider_http_status==503
    assert 'synthetic-test-credential' not in error.value.detail


def test_incomplete_cloud_output_is_not_released_as_a_completed_answer(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','synthetic-test-credential')
    async def send(client,request,**kwargs):
        return httpx.Response(200,json={'status':'in_progress','steps':[
            {'type':'model_output','content':[{'type':'text','text':'unfinished causal claim'}]}]},request=request)
    with patch.object(httpx.AsyncClient,'send',send),pytest.raises(HTTPException) as error:
        asyncio.run(interpret_rest([{'role':'user','content':'synthetic'}],False,timeout=2))
    assert error.value.status_code==502 and 'incomplete generation' in error.value.detail


def test_generate_content_history_preserves_typed_conversation_roles(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','synthetic-test-credential');captured=[]
    async def send(client,request,**kwargs):
        captured.append(json.loads(request.content))
        return httpx.Response(200,json={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'{}'}]}}]},request=request)
    messages=[{'role':'system','content':'same instructions'},{'role':'user','content':'first example'},
              {'role':'assistant','content':'first result'},{'role':'user','content':'actual synthetic question'}]
    with patch.object(httpx.AsyncClient,'send',send):
        asyncio.run(interpret_rest(messages,{},timeout=2))
    assert [step['role'] for step in captured[0]['contents']]==['user','model','user']
    assert [step['parts'][0]['text'] for step in captured[0]['contents']]==[m['content'] for m in messages[1:]]
    assert captured[0]['systemInstruction']['parts'][0]['text']=='same instructions'


def test_simple_local_generation_has_no_remote_interpretation(monkeypatch):
    monkeypatch.setenv('COGNISHIELD_AI_HYBRID','1')
    scope=HybridRequest(time.monotonic())
    response=SimpleNamespace(content='{"intent":"answer","information_needs":[]}',response_metadata={})
    client=SimpleNamespace(ainvoke=AsyncMock(return_value=response))
    with scope.activate(),patch('llm.orchestration.model.chat_model',AsyncMock(return_value=(client,'qwen2.5:1.5b'))):
        model=RoutingModel();output,selected=asyncio.run(model.generate([{'role':'user','content':'hello'}]))
    assert selected=='qwen2.5:1.5b' and scope.remote_calls==0


def test_rejected_remote_synthesis_cannot_trigger_hidden_local_repair(monkeypatch):
    monkeypatch.setenv('COGNISHIELD_AI_HYBRID','1')
    scope=HybridRequest(time.monotonic());scope.last_synthesis_remote=True
    with scope.activate():model=RoutingModel()
    assert not model.available('repair')


def test_auth_or_quota_failure_blocks_later_provider_calls_and_local_causal_repair(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','synthetic-test-credential')
    monkeypatch.setenv('COGNISHIELD_AI_HYBRID_CALLS','2');calls=[]
    async def send(client,request,**kwargs):
        calls.append(1)
        return httpx.Response(429,json={'error':{'status':'RESOURCE_EXHAUSTED'}},request=request)
    async def exercise():
        scope=HybridRequest(time.monotonic())
        with patch.object(httpx.AsyncClient,'send',send):
            for purpose in ['routing','synthesis']:
                with pytest.raises(HTTPException):await scope.generate([{'role':'user','content':'synthetic'}],False,purpose)
        assert scope.remote_disabled and scope.remote_calls==1 and scope.last_synthesis_remote
    asyncio.run(exercise());assert len(calls)==1
