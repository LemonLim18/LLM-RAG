"""Provider protocol and scoped role checks; no live external requests."""
import asyncio,json,sys,time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock,patch
import httpx,pytest
from fastapi import HTTPException
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm.model_roles import role_config,infer,InferenceRequest,validate_result

SCHEMA={'type':'object','properties':{'answer':{'type':'string'}},'required':['answer'],'additionalProperties':False}
class Consent:
    def assert_current_roles(self):pass

def test_default_roles_and_retired_model(monkeypatch):
    assert role_config('local_default').model=='qwen2.5:1.5b'
    assert role_config('complex_planner').model=='gemini-3.1-flash-lite'
    assert role_config('evidence_reasoner').model=='gemini-3.5-flash-lite'
    monkeypatch.setenv('COGNISHIELD_AI_REASONER_MODEL','gemini-3.8-flash')
    with pytest.raises(HTTPException):role_config('evidence_reasoner')

def test_external_configuration_cannot_grant_consent():
    with pytest.raises(HTTPException) as e:asyncio.run(infer('complex_planner',InferenceRequest([{'role':'user','content':'Synthetic test'}],SCHEMA,time.monotonic()+10)))
    assert e.value.status_code==403

def test_ollama_socket_normalizes_usage_without_external_authority():
    response=SimpleNamespace(content='{"answer":"local"}',response_metadata={'done_reason':'stop'},usage_metadata={'input_tokens':5,'output_tokens':2,'total_tokens':7})
    client=SimpleNamespace(ainvoke=AsyncMock(return_value=response))
    with patch('llm.orchestration.model.chat_model',AsyncMock(return_value=(client,'qwen2.5:1.5b'))):
        result=asyncio.run(infer('local_default',InferenceRequest([{'role':'user','content':'Synthetic'}],SCHEMA,time.monotonic()+10)))
    assert result.provider=='ollama' and result.usage['total_input_tokens']==5 and result.usage['total_tokens']==7

def test_google_roles_share_one_adapter_preserve_context():
    async def run():
        messages=[{'role':'system','content':'System'},{'role':'assistant','content':'Owned synthetic context'},{'role':'user','content':'Question'}]
        call=AsyncMock(return_value=('{"answer":"x"}','gemini-3.1-flash-lite',{'total_input_tokens':8}))
        with patch('llm.gemini_provider.interpret_rest',call):
            result=await infer('complex_planner',InferenceRequest(messages,SCHEMA,time.monotonic()+20),authorization=Consent())
        assert result.text=='{"answer":"x"}' and result.usage['total_input_tokens']==8
        assert call.call_args.args==(messages,SCHEMA)
        assert call.call_args.kwargs['model']=='gemini-3.1-flash-lite' and call.call_args.kwargs['output_tokens']==2048
    asyncio.run(run())

@pytest.mark.parametrize('model',['gemini-3.1-flash-lite','gemini-3.5-flash-lite'])
def test_google_generate_content_contract_and_usage(model,monkeypatch,tmp_path):
    monkeypatch.setenv('GEMINI_API_KEY','synthetic-not-a-credential')
    monkeypatch.setenv('COGNISHIELD_AI_HYBRID_USAGE',str(tmp_path/'quota.json'))
    packets=[]
    async def send(client,request,*a,**kw):
        packets.append((str(request.url),json.loads(request.content)))
        return httpx.Response(200,request=request,json={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'internal','thought':True},{'text':'{"answer":"ok"}'}]}}],
            'usageMetadata':{'promptTokenCount':10,'candidatesTokenCount':5,'thoughtsTokenCount':2,'totalTokenCount':17}})
    from llm.gemini_provider import interpret_rest
    with patch.object(httpx.AsyncClient,'send',send):
        raw,used,usage=asyncio.run(interpret_rest([{'role':'system','content':'Instruction'},{'role':'user','content':'Synthetic'}],SCHEMA,timeout=10,model=model,thinking='low',output_tokens=2048))
    assert raw=='{"answer":"ok"}' and used==model and usage['total_thought_tokens']==2
    assert ':generateContent' in packets[0][0] and 'interactions' not in packets[0][0]
    assert packets[0][1]['generationConfig']['responseFormat']['text']['schema']==SCHEMA

def test_google_and_shared_project_quota_do_not_double_daily_allowance(monkeypatch,tmp_path):
    from llm.gemini_provider import _quota_update
    monkeypatch.setenv('COGNISHIELD_AI_HYBRID_USAGE',str(tmp_path/'quota.json'));monkeypatch.setenv('COGNISHIELD_AI_HYBRID_RPD','2')
    _quota_update('gemini-3.1-flash-lite',reservation=10);_quota_update('gemini-3.5-flash-lite',reservation=10)
    with pytest.raises(HTTPException) as e:_quota_update('gemini-3.1-flash-lite',reservation=10)
    assert e.value.status_code==429

def test_shared_google_rpm_across_models(monkeypatch,tmp_path):
    from llm.gemini_provider import _quota_update
    monkeypatch.setenv('COGNISHIELD_AI_HYBRID_USAGE',str(tmp_path/'quota.json'));monkeypatch.setenv('COGNISHIELD_AI_HYBRID_RPM','1')
    _quota_update('gemini-3.1-flash-lite',reservation=10)
    receipt,wait=_quota_update('gemini-3.5-flash-lite',reservation=10)
    assert receipt is None and wait>0

def openai_env(monkeypatch,tmp_path):
    monkeypatch.setenv('COGNISHIELD_AI_REASONER_PROVIDER','openai');monkeypatch.setenv('COGNISHIELD_AI_REASONER_MODEL','gpt-4.1-mini');monkeypatch.setenv('COGNISHIELD_AI_REASONER_THINKING','off')
    monkeypatch.setenv('COGNISHIELD_AI_REASONER_SCHEMA_MODE','json_schema')
    monkeypatch.setenv('COGNISHIELD_AI_HYBRID_USAGE',str(tmp_path/'quota.json'));monkeypatch.setenv('OPENAI_API_KEY','synthetic-test-only')

def test_openai_responses_protocol_no_live_access_claim(monkeypatch,tmp_path):
    openai_env(monkeypatch,tmp_path);packets=[]
    async def send(client,request,*a,**kw):
        packets.append(json.loads(request.content))
        return httpx.Response(200,request=request,json={'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'{"answer":"ok"}'}]}],'usage':{'input_tokens':8,'output_tokens':4,'total_tokens':12}})
    with patch.object(httpx.AsyncClient,'send',send):
        result=asyncio.run(infer('evidence_reasoner',InferenceRequest([{'role':'user','content':'Synthetic'}],SCHEMA,time.monotonic()+10),authorization=Consent()))
    assert result.provider=='openai' and result.usage['total_tokens']==12
    assert packets[0]['store'] is False and packets[0]['text']['format']['schema']==SCHEMA
    assert not packets[0].get('tools') and packets[0]['input'][0]['role']=='user'

@pytest.mark.parametrize('http_status,category',[(400,'REQUEST_CONTRACT'),(401,'AUTHENTICATION'),(429,'QUOTA'),(503,'PROVIDER_UNAVAILABLE')])
def test_openai_errors_keep_reservations_no_retry(http_status,category,monkeypatch,tmp_path):
    openai_env(monkeypatch,tmp_path);calls=[]
    async def send(client,request,*a,**kw):calls.append(1);return httpx.Response(http_status,request=request,json={'error':{'message':'provider error'}})
    with patch.object(httpx.AsyncClient,'send',send),pytest.raises(HTTPException) as e:
        asyncio.run(infer('evidence_reasoner',InferenceRequest([{'role':'user','content':'Synthetic'}],SCHEMA,time.monotonic()+10),authorization=Consent()))
    assert e.value.provider_category==category and len(calls)==1
    assert len(json.loads((tmp_path/'quota.json').read_text()))==1

def test_unknown_openai_model_rejected_without_request(monkeypatch):
    monkeypatch.setenv('COGNISHIELD_AI_REASONER_PROVIDER','openai');monkeypatch.setenv('COGNISHIELD_AI_REASONER_MODEL','unverified-model')
    with pytest.raises(HTTPException):role_config('evidence_reasoner')

def test_unchanged_schema_and_deadline_are_mandatory():
    with pytest.raises(HTTPException):validate_result('{"wrong":4}',SCHEMA)
    with pytest.raises(HTTPException) as e:asyncio.run(infer('local_default',InferenceRequest([{'role':'user','content':'x'}],False,time.monotonic()-1)))
    assert e.value.status_code==504

def test_preview_off_preserves_wrong_interpretation_without_verification_credit():
    from llm.orchestration.role_reasoning import preview
    answer,trace=preview({'answer':'An intentionally incorrect model claim.','sources':[]},'off',[],[],{},'test')
    assert answer.endswith('An intentionally incorrect model claim.') and 'Unverified AI interpretation' in answer
    assert trace['status']=='experimental_unverified' and trace['interpretation_authority'].startswith('none')

def test_evidence_packet_preserves_raw_state_relationships_and_dependencies():
    from llm.orchestration.role_reasoning import evidence_packet
    from llm.gateway_models import Evidence
    data={'tool':'network.state','status':'success','evidence_ids':['record-id'],'data':{'records':[{'id':'row','depends_on':['other-row'],
        'failure_location':{'hostname':'Example','interface':'port1','direction':'ingress','admin_status':'up','oper_status':'down'},'config_text':'literal text'}]}}
    packet=json.loads(evidence_packet('Original instruction',[data],[Evidence(id='record-id',source='Source',origin='simulated')],[],{}))
    assert packet['reader_results'][0]==data and packet['sources'][0]['id']=='record-id' and packet['omissions']==[]
    with pytest.raises(HTTPException):evidence_packet('x',[{'data':'x'*70000}],[],[],{})

def test_google_explicit_json_mode_still_enforces_original_schema(monkeypatch,tmp_path):
    monkeypatch.setenv('GEMINI_API_KEY','synthetic-not-a-credential')
    monkeypatch.setenv('COGNISHIELD_AI_HYBRID_USAGE',str(tmp_path/'quota.json'))
    packets=[]
    async def send(client,request,*a,**kw):
        packets.append(json.loads(request.content))
        return httpx.Response(200,request=request,json={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'{"wrong":"value"}'}]}}]})
    from llm.gemini_provider import interpret_rest
    with patch.object(httpx.AsyncClient,'send',send),pytest.raises(HTTPException) as e:
        asyncio.run(interpret_rest([{'role':'user','content':'Synthetic'}],SCHEMA,timeout=10,model='gemini-3.1-flash-lite',schema_mode='validated_json'))
    assert e.value.provider_category=='INVALID_STRUCTURED_OUTPUT'
    assert packets[0]['generationConfig']['responseMimeType']=='application/json'
    assert json.dumps(SCHEMA) in packets[0]['systemInstruction']['parts'][-1]['text']

def test_record_redaction_cannot_erase_unrelated_operands_or_original_request():
    from llm.orchestration.role_reasoning import evidence_packet
    text=json.loads(evidence_packet('Explain the recorded configuration',[{'tool':'network.configuration','data':{
        'hostname':'Example','config_text':'hostname Example\npassword synthetic-secret\ninterface port7\n shutdown'}}],[],[],{}))
    assert text['original_user_instruction']=='Explain the recorded configuration'
    row=text['reader_results'][0]['data']
    assert row['hostname']=='Example' and 'shutdown' in row['config_text'] and 'synthetic-secret' not in row['config_text']
    assert text['omissions'][0]['field'].endswith('config_text')

@pytest.mark.parametrize('response,category',[
    ({'status':'incomplete'},'INCOMPLETE_GENERATION'),
    ({'status':'completed','output':[{'type':'message','content':[{'type':'refusal'}]}]},'MODEL_REFUSAL'),
])
def test_openai_incomplete_and_refusal_are_not_model_answers(response,category,monkeypatch,tmp_path):
    openai_env(monkeypatch,tmp_path)
    async def send(client,request,*a,**kw):return httpx.Response(200,request=request,json=response)
    with patch.object(httpx.AsyncClient,'send',send),pytest.raises(HTTPException) as e:
        asyncio.run(infer('evidence_reasoner',InferenceRequest([{'role':'user','content':'Synthetic'}],SCHEMA,time.monotonic()+10),authorization=Consent()))
    assert e.value.provider_category==category

def test_advisory_sources_can_be_actual_owned_receipts_but_not_invented():
    from llm.orchestration.role_reasoning import decide
    async def run():
        raw={'decision':'answer','answer':'Request a recorded interface observation; no read was executed.','sources':['prior-owned-receipt'],
            'outcome_assessments':[{'clause':'request-1','status':'limited','sources':['prior-owned-receipt'],
                'assessment':'A future check is advised using the owned reference, not a fresh read.'}]}
        model=SimpleNamespace(hybrid=SimpleNamespace(remote_calls=1,max_remote_calls=3),generate=AsyncMock(return_value=(json.dumps(raw),'synthetic')))
        context={'prior_read_receipts':[{'tool':'network.state','evidence_ids':['prior-owned-receipt']}]}
        result=await decide(model,'Recommend a next check',[],[],[],{},advisory=context)
        assert result['sources']==['prior-owned-receipt']
        model.generate=AsyncMock(return_value=(json.dumps({**raw,'answer':'This question could distinguish causes [S1].','sources':['S1']}),'synthetic'))
        context['prior_source_evidence']=[{'id':'prior-owned-receipt','source':'Previously read source','origin':'simulated'}]
        result=await decide(model,'Recommend a next check',[],[],[],{},advisory=context)
        assert result['input_packet']['sources'][0]['reference_scope'].startswith('Previous owned')
        context['prior_authorized_records']=[{'tool':'network.state','evidence_ids':['prior-owned-receipt'],'data':{'records':[{'id':'actual-record','kind':'interface_state'}]}}]
        model.generate=AsyncMock(return_value=(json.dumps({**raw,'sources':['actual-record']}),'synthetic'))
        assert (await decide(model,'Recommend a next check',[],[],[],{},advisory=context))['sources']==['actual-record']
        with pytest.raises(HTTPException):await decide(model,'Recommend a next check',[],[],[],{},advisory={'prior_read_receipts':[]})
    asyncio.run(run())
