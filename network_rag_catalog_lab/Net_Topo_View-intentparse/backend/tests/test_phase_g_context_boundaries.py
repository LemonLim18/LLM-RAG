"""Relevant context and user read constraints; not model reasoning scores."""
import asyncio
import json
import os
from pathlib import Path
import sys
from unittest.mock import AsyncMock,patch

import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm.gateway_routing import select_context


async def context_biased_classifier(messages,**kwargs):
    offered=kwargs['structured']['properties']['intent']['enum']
    return json.dumps({'intent':'analyze_files' if 'analyze_files' in offered else 'answer'}),'configured-model'


@pytest.mark.parametrize('metadata',[
    [{'name':'operations.md','category':'documents'},{'name':'topology.png','category':'diagrams'}],
    [{'name':'owned-upload.pdf','id':'owned-attachment'}],
])
@pytest.mark.parametrize('question',[
    'Explain the difference between a local process label and a protocol router identifier.',
    'What is a PDF file format used for?',
])
def test_unrelated_general_question_does_not_inherit_available_file_context(metadata,question):
    with patch.dict(os.environ,COGNISHIELD_AI_PLANNING='0'),patch('llm.gateway_semantics.semantic_hint',AsyncMock(return_value=None)):
        route=asyncio.run(select_context(question,None,'floating',None,metadata,[],
            inventory={'devices':[]},generate_fn=context_biased_classifier))
    assert route.intent=='answer' and not route.use_attachments and not route.network_domains


@pytest.mark.parametrize('question',[
    'Explain route preference without reading any of our network records.',
    'Describe routing in general; do not query local inventory records.',
])
def test_explicit_no_private_read_constraint_precedes_a_model_tool_guess(question):
    async def choose_read(messages,**kwargs):
        decision={'network_domains':['state'],'request':question} if 'network_domains' in kwargs['structured']['properties'] else {'intent':'network'}
        return json.dumps(decision),'configured-model'
    with patch.dict(os.environ,COGNISHIELD_AI_PLANNING='0'),patch('llm.gateway_semantics.semantic_hint',AsyncMock(return_value=None)):
        route=asyncio.run(select_context(question,None,'floating',None,
            [{'name':'operations.md','category':'documents'}],[],inventory={'devices':[]},generate_fn=choose_read))
    assert route.intent=='answer' and not route.use_attachments and not route.network_domains


@pytest.mark.parametrize('question',['Explain operations.md.','What does page 4 of my PDF explain?',
    'Can you read this, the content inside?','What does this uploaded note say on page one?',
    'Summarize the attached report.','Does this four-page attachment contain page nine?',
    "Compare that note's second and third pages."])
def test_bound_file_questions_keep_the_existing_document_path(question):
    with patch.dict(os.environ,COGNISHIELD_AI_PLANNING='0'),patch('llm.gateway_semantics.semantic_hint',AsyncMock(return_value=None)):
        route=asyncio.run(select_context(question,None,'floating',None,[{'name':'operations.md','id':'owned-attachment'}],[],
            inventory={'devices':[]},generate_fn=context_biased_classifier))
    assert route.intent=='analyze_files' and route.use_attachments


@pytest.mark.parametrize('suffix',['',' Do not edit or generate.',' Never change or deploy anything.'])
def test_published_comparison_keeps_explicit_unsaved_editor_binding(suffix):
    from types import SimpleNamespace
    editor=SimpleNamespace(path='draft.cfg',selection=None)
    route=asyncio.run(select_context('Compare the active unsaved buffer with published OSPF operation requirements.'+suffix,
        None,'studio',editor,[],[],inventory={'devices':[]},generate_fn=context_biased_classifier))
    assert route.intent=='explain' and route.use_editor and route.network_domains==['knowledge']


def test_unsaved_editor_reference_is_not_a_deictic_request_for_ambient_documents():
    from types import SimpleNamespace
    editor=SimpleNamespace(path='playbooks/draft.cfg',selection=None)
    route=asyncio.run(select_context('Explain this unsaved routing buffer and its actual addresses. Do not modify it.',
        None,'studio',editor,[{'name':'operations.md','category':'documents'}],[],
        inventory={'devices':[]},generate_fn=context_biased_classifier))
    assert route.intent=='explain' and route.use_editor and not route.use_attachments
