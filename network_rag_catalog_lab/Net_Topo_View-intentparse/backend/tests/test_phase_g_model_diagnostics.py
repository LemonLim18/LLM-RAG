"""Keep provider completion evidence separate from model-content adequacy."""
import asyncio
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock,patch

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm.orchestration.model import RoutingModel


def test_completion_reason_and_usage_are_retained_without_raw_context():
    response=SimpleNamespace(content='{"intent":"answer"}',response_metadata={
        'done_reason':'length','eval_count':512,'prompt_eval_count':1300,
        'private_context':'NEVER_PERSIST_THIS'},usage_metadata={'input_tokens':1300,'output_tokens':512})
    client=SimpleNamespace(ainvoke=AsyncMock(return_value=response));model=RoutingModel()
    with patch('llm.orchestration.model.chat_model',AsyncMock(return_value=(client,'existing-chat-model'))):
        result=asyncio.run(model.generate([{'role':'user','content':'private request'}],structured=True))
    assert result==('{"intent":"answer"}','existing-chat-model')
    trace=model.inference_trace[-1]
    assert trace['done_reason']=='length' and trace['output_tokens']==512
    assert trace['input_tokens']==1300 and trace['purpose']=='routing'
    assert 'NEVER_PERSIST_THIS' not in str(trace) and 'private request' not in str(trace)
    assert model.max_calls in {3,5} and model.purposes=={'routing':1}


def test_missing_provider_finish_metadata_is_explicitly_unknown():
    response=SimpleNamespace(content='answer')
    client=SimpleNamespace(ainvoke=AsyncMock(return_value=response));model=RoutingModel()
    with patch('llm.orchestration.model.chat_model',AsyncMock(return_value=(client,'existing-chat-model'))):
        asyncio.run(model.generate([{'role':'user','content':'question'}]))
    assert model.inference_trace[-1]['done_reason'] is None


def test_evaluation_replay_retains_exact_schema_options_and_independent_messages():
    from scripts.evaluate_phase_f_registry import provider_request_trace
    body={'model':'installed-model','messages':[{'role':'user','content':'controlled fixture'}],
          'format':{'type':'object','properties':{'answer':{'type':'string'}}},
          'options':{'temperature':0,'num_ctx':8192,'num_predict':512},'stream':True}
    trace=provider_request_trace(body)
    assert trace['inference_parameters']=={k:v for k,v in body.items() if k!='messages'}
    assert trace['format']==body['format'] and trace['messages']==body['messages']
    body['options']['temperature']=1;body['format']['type']='array';body['messages'][0]['content']='changed'
    assert trace['options']['temperature']==0 and trace['format']['type']=='object'
    assert trace['messages'][0]['content']=='controlled fixture'
    assert provider_request_trace({'format':'json'})['format']=='json'
