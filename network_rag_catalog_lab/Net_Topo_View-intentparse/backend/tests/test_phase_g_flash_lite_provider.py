"""Bounded provider/approval/relationship regressions, synthetic SQLite only."""
import asyncio
from copy import deepcopy
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch
from uuid import uuid4

import httpx
import pytest
from fastapi import HTTPException

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm.gemini_provider import (interpret_rest,approve_hybrid_request,HybridRequest,
    scenario_approval_context,_quota_update)
from llm.gateway_models import TurnRequest
from llm.orchestration.synthesis import forwarding_claim_errors


@pytest.fixture(autouse=True)
def isolated(monkeypatch,tmp_path):
    monkeypatch.setenv('GEMINI_MODEL','gemini-3.5-flash-lite')
    monkeypatch.setenv('GEMINI_API_KEY','fake-unit-key')
    monkeypatch.setenv('COGNISHIELD_AI_HYBRID_USAGE',str(tmp_path/'usage.json'))
    monkeypatch.setenv('COGNISHIELD_AI_HYBRID','1')
    monkeypatch.setenv('COGNISHIELD_DEV_SIMULATION','1')
    monkeypatch.setenv('COGNISHIELD_AI_HYBRID_INTERPRET','0')


def test_flash_lite_exact_transport_and_usage():
    captured=[]
    schema={'type':'object','properties':{'answer':{'type':'string'}},'required':['answer'],'additionalProperties':False}
    async def send(client,request,**kwargs):
        body=json.loads(request.content);captured.append(body)
        assert request.url.path.endswith('gemini-3.5-flash-lite:generateContent')
        return httpx.Response(200,json={'modelVersion':'gemini-3.5-flash-lite','usageMetadata':{
            'promptTokenCount':10,'candidatesTokenCount':8,'thoughtsTokenCount':3,'totalTokenCount':21},
            'candidates':[{'finishReason':'STOP','content':{'parts':[{'thought':True,'text':'not answer'},{'text':'{"answer":"scoped"}'}]}}]},request=request)
    messages=[{'role':'system','content':'original rules'},{'role':'user','content':'example'},
              {'role':'assistant','content':'example response'},{'role':'user','content':'actual source identities λ'}]
    with patch.object(httpx.AsyncClient,'send',send),patch('llm.gemini_provider._quota_update',wraps=_quota_update) as quota:
        out,model,usage=asyncio.run(interpret_rest(messages,schema,timeout=2))
    assert json.loads(out)=={'answer':'scoped'} and model=='gemini-3.5-flash-lite'
    body=captured[0];assert body['systemInstruction']['parts'][0]['text']=='original rules'
    assert [c['parts'][0]['text'] for c in body['contents']]==[m['content'] for m in messages[1:]]
    assert body['generationConfig']['responseJsonSchema']==schema
    assert 'temperature' not in body['generationConfig'] and 'tools' not in body
    assert usage['total_thought_tokens']==3 and usage['total_output_tokens']==8
    assert quota.call_args_list[0].kwargs['reservation']==len(json.dumps(body,ensure_ascii=False).encode('utf-8'))


@pytest.mark.parametrize('finish,text,category',[
    ('MAX_TOKENS','{"answer":"partial"}','INCOMPLETE_GENERATION'),
    ('STOP','not JSON','INVALID_STRUCTURED_OUTPUT'),
    ('STOP','{"other":"wrong"}','INVALID_STRUCTURED_OUTPUT')])
def test_provider_incomplete_or_invalid_is_not_semantic_success(finish,text,category):
    async def send(client,request,**kwargs):
        return httpx.Response(200,json={'candidates':[{'finishReason':finish,'content':{'parts':[{'text':text}]}}]},request=request)
    schema={'type':'object','properties':{'answer':{'type':'string'}},'required':['answer'],'additionalProperties':False}
    with patch.object(httpx.AsyncClient,'send',send),pytest.raises(HTTPException) as error:
        asyncio.run(interpret_rest([{'role':'user','content':'synthetic'}],schema,timeout=2))
    assert error.value.provider_category==category and error.value.provider_dispatched


def test_quota_no_dispatch_no_silent_rollback(monkeypatch):
    monkeypatch.setenv('COGNISHIELD_AI_HYBRID_RPD','1')
    _quota_update('gemini-3.5-flash-lite',reservation=10)
    async def unexpected(*args,**kwargs):raise AssertionError('No external call or Gemini3.8 substitution allowed')
    with patch.object(httpx.AsyncClient,'send',unexpected),pytest.raises(HTTPException) as error:
        asyncio.run(interpret_rest([{'role':'user','content':'synthetic'}],False,timeout=2))
    assert error.value.status_code==429 and not error.value.provider_dispatched


@pytest.mark.parametrize('status,category',[(400,'HTTP_400'),(422,'HTTP_422'),(429,'HTTP_429'),(500,'HTTP_500'),(503,'HTTP_503')])
def test_non_json_http_failures_retain_status_without_body(status,category):
    async def send(client,request,**kwargs):
        return httpx.Response(status,text='sensitive proxy diagnostics',request=request)
    with patch.object(httpx.AsyncClient,'send',send),pytest.raises(HTTPException) as error:
        asyncio.run(interpret_rest([{'role':'user','content':'synthetic'}],False,timeout=2))
    assert error.value.provider_http_status==status and error.value.provider_category==category
    assert 'sensitive' not in error.value.detail


@pytest.mark.parametrize('exception,category',[(httpx.ReadTimeout,'PROVIDER_TIMEOUT'),(httpx.ConnectError,'CONNECTIVITY_FAILURE')])
def test_timeout_and_connectivity_are_separate(exception,category):
    async def send(client,request,**kwargs):raise exception('sensitive network diagnostics')
    with patch.object(httpx.AsyncClient,'send',send),pytest.raises(HTTPException) as error:
        asyncio.run(interpret_rest([{'role':'user','content':'synthetic'}],False,timeout=2))
    assert error.value.provider_category==category and error.value.provider_dispatched
    assert 'sensitive' not in error.value.detail


@pytest.mark.parametrize('body',[[{'unexpected':'list'}],{'candidates':[42]}])
def test_wrong_provider_container_is_not_a_completed_answer(body):
    async def send(client,request,**kwargs):return httpx.Response(200,json=body,request=request)
    with patch.object(httpx.AsyncClient,'send',send),pytest.raises(HTTPException) as error:
        asyncio.run(interpret_rest([{'role':'user','content':'synthetic'}],False,timeout=2))
    assert error.value.provider_category=='INVALID_PROVIDER_RESPONSE' and error.value.provider_dispatched


@pytest.fixture
def owned_scenario(tmp_path,monkeypatch):
    from db.manager import DatabaseManager
    from llm.gateway_store import ConversationStore,ensure_schema
    from local_providers.development import ScenarioManager
    db=DatabaseManager(str(tmp_path/'app.db'));db.initialize();ensure_schema(db)
    db._development_scenario=ScenarioManager(tmp_path/'scenario.json')
    context=scenario_approval_context(db)
    monkeypatch.setenv('COGNISHIELD_AI_HYBRID_SCENARIOS',context['scenario_digest'])
    store=ConversationStore(db);user={'username':'owner','role':'engineer'}
    cid=store.create('owner','studio')['id']
    try:yield db,store,user,cid,context
    finally:db.close()


def test_owner_exact_approval_consumes_and_is_revision_bound(owned_scenario):
    db,store,user,cid,ctx=owned_scenario;body=TurnRequest(request_id=uuid4(),prompt='Explain synthetic paths')
    approve_hybrid_request(db,store,user,cid,body,ctx['source_revision'])
    assert HybridRequest.create(db,store,user,'floating',cid,body,time.monotonic()) is None
    assert HybridRequest.create(db,store,user,'studio',cid,body.model_copy(update={'prompt':'changed'}),time.monotonic()) is None
    assert HybridRequest.create(db,store,user,'studio',cid,body,time.monotonic())
    assert HybridRequest.create(db,store,user,'studio',cid,body,time.monotonic()) is None


def test_unapproved_scenario_history_and_other_owner_cannot_consent(owned_scenario,monkeypatch):
    db,store,user,cid,ctx=owned_scenario;body=TurnRequest(request_id=uuid4(),prompt='Explain')
    with pytest.raises(HTTPException):approve_hybrid_request(db,store,{'username':'other','role':'admin'},cid,body,ctx['source_revision'])
    with pytest.raises(HTTPException):approve_hybrid_request(db,store,{**user,'role':'auditor'},cid,body,ctx['source_revision'])
    with pytest.raises(HTTPException):approve_hybrid_request(db,store,user,cid,body,'stale')
    monkeypatch.setenv('COGNISHIELD_AI_HYBRID_SCENARIOS','')
    with pytest.raises(HTTPException):approve_hybrid_request(db,store,user,cid,body,ctx['source_revision'])


def test_expired_and_changed_history_approvals_cannot_dispatch(owned_scenario):
    db,store,user,cid,ctx=owned_scenario;body=TurnRequest(request_id=uuid4(),prompt='Explain')
    approve_hybrid_request(db,store,user,cid,body,ctx['source_revision'])
    entry=next(iter(db._ai_external_approvals.values()));entry['expires']=time.monotonic()-1
    assert HybridRequest.create(db,store,user,'studio',cid,body,time.monotonic()) is None
    approve_hybrid_request(db,store,user,cid,body,ctx['source_revision'])
    with patch.object(store,'history',return_value=[{'role':'user','content':'different owned message'}]):
        assert HybridRequest.create(db,store,user,'studio',cid,body,time.monotonic()) is None


def test_editor_and_private_history_are_not_cloud_eligible(owned_scenario):
    db,store,user,cid,ctx=owned_scenario
    body=TurnRequest(request_id=uuid4(),prompt='Explain',editor=dict(document_id='private',path='private.txt',
        content='private test buffer',language='text',model_id='m',model_version=1,buffer_epoch=0,saved_revision=0,is_dirty=True,read_only=False))
    with pytest.raises(HTTPException):approve_hybrid_request(db,store,user,cid,body,ctx['source_revision'])
    from llm.gateway_models import TurnResponse,text_digest
    body=TurnRequest(request_id=uuid4(),prompt='Private ordinary conversation')
    store.begin(cid,user['username'],str(body.request_id),text_digest(body.model_dump_json()),body.prompt)
    result=TurnResponse(request_id=str(body.request_id),status='success',answer='ordinary context',context_coverage={'environment':{'mode':'ordinary'}})
    store.finish(cid,user['username'],str(body.request_id),result.model_dump())
    fresh=TurnRequest(request_id=uuid4(),prompt='Synthetic question')
    with pytest.raises(HTTPException):approve_hybrid_request(db,store,user,cid,fresh,ctx['source_revision'])


@pytest.mark.parametrize('left,right,port',[('Alpha','Beta','Eth3'),('Node-A','Transit-Z','ge-7/4/0.0')])
def test_reached_edge_cannot_be_claimed_failed_egress(left,right,port):
    flow={'source_device':left,'destination_device':'Sink','traffic_scope':{},'forward':{
        'status':'failed','branches':[{'path':[left,right],'reason':'egress interface down',
        'blocked_interface':{'hostname':right,'interface':port}}]},'return':{'status':'failed','branches':[{'path':['Sink'],'reason':'ingress interface down'}]}}
    wrong=f'The path fails between {left} and {right} due to an egress interface failure on {right} ({port}), resulting in a subsequent ingress failure on Sink.'
    assert len(forwarding_claim_errors(wrong,[flow]))>=2
    valid=f'The forward path reaches {right}; its egress {port} is down. Return also fails, as a separate recorded calculation. No ordering is established.'
    assert not forwarding_claim_errors(valid,[flow])
    uncertain=f'The result does not show failure between {left} and {right}; the egress {port} is down at {right}.'
    assert not forwarding_claim_errors(uncertain,[flow])


def test_original_h05_rejected_and_correct_h01_preserved():
    root=Path(__file__).resolve().parents[2]
    prior=root/'tmp/phase-g/iterations/20261025-flash-lite-35'
    if not prior.exists():pytest.skip('Optional preserved external replay unavailable')
    for key,rejected in [('H01',False),('H05',True)]:
        packet=json.loads((prior/'packets'/(key+'.json')).read_text(encoding='utf-8'))
        text=packet['payload']['messages'][-1]['content'];visible,_=json.JSONDecoder().raw_decode(text[text.index('{'):])
        candidate=json.loads((prior/'results'/(key+'.json')).read_text(encoding='utf-8'))['parsed']
        answer=candidate.get('answer') or '\n\n'.join(r['answer'] for r in candidate['responses'])
        assert bool(forwarding_claim_errors(answer,visible['evidence']['forwarding_results']))==rejected
