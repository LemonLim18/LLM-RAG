"""Whole JSON integrity is distinct from independent auxiliary diagnostics."""
import asyncio, json, sys
from pathlib import Path
from unittest.mock import patch
import httpx, pytest
from fastapi import HTTPException
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm.gemini_provider import interpret_rest
from llm.orchestration.role_reasoning import EvidenceDecision, parse_decision


@pytest.mark.parametrize('mode',['validated_json','json_schema'])
@pytest.mark.parametrize('kind',['valid','quoted','bad_json','bad_auxiliary','bad_decision','bad_query','bad_sources'])
def test_whole_core_validation_in_both_transports(monkeypatch,tmp_path,mode,kind):
    monkeypatch.setenv('GEMINI_API_KEY','synthetic-test-only')
    monkeypatch.setenv('COGNISHIELD_AI_HYBRID_USAGE',str(tmp_path/'usage.json'))
    schema=EvidenceDecision.model_json_schema();schema['x-auxiliary-fields']=['claims']
    value={'decision':'answer','answer':'Recorded state only; physical cause is unknown.','sources':['actual-source'],
           'additional_reads':[],'claims':[]}
    if kind=='quoted':value['answer']='Recorded status: "down". The exact command is `description "WAN"`.'
    if kind=='bad_auxiliary':value['claims']={'category':'not-an-array'}
    if kind=='bad_decision':value['decision']='execute'
    if kind=='bad_query':value.update(decision='need_more_evidence',additional_reads=[{'reader':'network.state','parameters':{},'gap':3}])
    if kind=='bad_sources':value['sources']=[123]
    raw=json.dumps(value) if kind!='bad_json' else '{"decision":"answer","answer":"status: "down"","sources":[]}'
    calls=[]
    async def send(client,request,*args,**kwargs):
        calls.append(json.loads(request.content))
        return httpx.Response(200,request=request,json={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':raw}]}}]})
    with patch.object(httpx.AsyncClient,'send',send):
        if kind in {'bad_json','bad_decision','bad_query','bad_sources'}:
            with pytest.raises(HTTPException) as exc:
                asyncio.run(interpret_rest([{'role':'user','content':'Synthetic reader output'}],schema,timeout=5,model='gemini-3.5-flash-lite',schema_mode=mode))
            assert exc.value.provider_category=='INVALID_STRUCTURED_OUTPUT'
            assert exc.value.raw_output==raw and exc.value.validation_diagnostic
        else:
            result,_,_=asyncio.run(interpret_rest([{'role':'user','content':'Synthetic reader output'}],schema,timeout=5,model='gemini-3.5-flash-lite',schema_mode=mode))
            core,aux=parse_decision(result,independent_claims=True)
            assert core.answer==value['answer'] and core.sources==['actual-source']
            assert aux['status']==('MODEL_CONTRACT_ERROR' if kind=='bad_auxiliary' else 'VALID')
    assert len(calls)==1
    assert ('responseFormat' in calls[0]['generationConfig'])==(mode=='json_schema')
    assert 'responseJsonSchema' not in calls[0]['generationConfig']


def test_rejected_native_schema_is_provider_failure_without_retry_or_mode_switch(monkeypatch,tmp_path):
    monkeypatch.setenv('GEMINI_API_KEY','synthetic-test-only')
    monkeypatch.setenv('COGNISHIELD_AI_HYBRID_USAGE',str(tmp_path/'usage.json'));calls=[]
    async def send(client,request,*args,**kwargs):
        calls.append(json.loads(request.content))
        return httpx.Response(400,request=request,json={'error':{'code':400,'status':'INVALID_ARGUMENT','message':'Synthetic schema rejection'}})
    with patch.object(httpx.AsyncClient,'send',send),pytest.raises(HTTPException) as exc:
        asyncio.run(interpret_rest([{'role':'user','content':'Synthetic'}],EvidenceDecision.model_json_schema(),timeout=5,model='gemini-3.5-flash-lite',schema_mode='json_schema'))
    assert exc.value.provider_http_status==400 and exc.value.provider_category=='INVALID_ARGUMENT'
    assert len(calls)==1 and 'responseFormat' in calls[0]['generationConfig']
