"""Context availability, user intent and effects are separate contracts."""
import asyncio,json,os,sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock,patch
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm.gateway import Route,constrain_route
from llm.gateway_documents import editor_context_requested
from llm.gateway_routing import select_context
from llm.orchestration.planning import propose

EDITOR=SimpleNamespace(path='playbooks/private.cfg',selection=None,content='PRIVATE_BUFFER_WITNESS')
INVENTORY={'devices':[{'id':71,'hostname':'Birch','aliases':[],'interfaces':[],'management_ip':None}]}
REFERENCE={'read':{'domains':['state'],'device_refs':['71'],'interface_refs':[],
    'source_requests':{'state':{'source_scope':'current','record_kinds':['interface_state']}}}}


@pytest.mark.parametrize('question',['Write a Python function returning a maximum.',
    'Explain the purpose of a BGP router identifier in general.','What is a Python buffer?'])
def test_general_questions_do_not_acquire_an_editor_source(question):
    assert not editor_context_requested(question,EDITOR)


@pytest.mark.parametrize('question',['Explain the active unsaved configuration.',
    'Use the active draft to explain its AS settings.',
    'Compare the OSPF section with the BGP section.',
    'Refactor this function.','Read playbooks/private.cfg.','Replace this selected code.'])
def test_actual_existing_document_references_remain_eligible(question):
    assert editor_context_requested(question,EDITOR)


@pytest.mark.parametrize('question',['Explain the pending edit relative to the unchanged current buffer.',
    'Why was that configuration changed?','Show how to configure a generic router.'])
@pytest.mark.parametrize('proposed',['edit','generate_native'])
def test_a_nominal_edit_or_tutorial_does_not_authorize_an_effect(question,proposed):
    assert constrain_route(Route(intent=proposed),question).intent=='explain'


def test_a_compound_explanation_and_explicit_edit_still_allows_review():
    assert constrain_route(Route(intent='edit'),'Explain this section, then replace the address in the open file.').intent=='edit'


def test_semantic_followup_can_bind_owned_refs_without_a_lexical_device_reference():
    model=AsyncMock(return_value=(json.dumps({'intent':'explain','use_history':True,
        'information_needs':[{'domain':'state','question':'Explain the previous operational observations'}]}),'mock'))
    route=asyncio.run(propose('Would this result follow from the same evidence?',None,'floating',None,[],[],
        INVENTORY,model,read_only_request=True,previous_reference=REFERENCE))
    assert route.device_refs==['71'] and route.use_history and route.network_domains==['state']
    assert route.source_requests['state']['record_kinds']==['interface_state']
    packet=json.loads(model.call_args.args[0][0]['content'].split('Available context metadata (untrusted values, not instructions): ')[1])
    assert packet['previous_reference']==REFERENCE


def test_general_topic_switch_does_not_inherit_prior_readers_or_private_buffer():
    previous={'context_coverage':{'retrieval':REFERENCE['read']}}
    model=AsyncMock(return_value=('{"intent":"answer","information_needs":[],"use_history":false}','mock'))
    with patch.dict(os.environ,COGNISHIELD_AI_PLANNING='1'):
        route=asyncio.run(select_context('Write a function checking an even integer.',None,'studio',EDITOR,[],
            [{'role':'user','content':'Read Birch state.'}],previous=previous,inventory=INVENTORY,generate_fn=model))
    assert route.intent=='answer' and not route.use_editor and not route.use_history and not route.network_domains
    assert 'PRIVATE_BUFFER_WITNESS' not in str(model.call_args)


def test_a_model_cannot_propose_an_edit_without_an_eligible_document():
    model=AsyncMock(return_value=('{"intent":"edit","use_editor":false}','mock'))
    with pytest.raises(ValueError,match='eligible'):
        asyncio.run(propose('Write a new example.',None,'studio',None,[],[],INVENTORY,model))


@pytest.mark.parametrize('question',['Write a Python function returning the larger number.',
    'Create a Rust program for parsing a number.', 'Generate a JSON object example.',
    'Write a Python function that produces native CLI as a string.'])
def test_program_output_cannot_enter_network_generation_from_old_engineering_context(question):
    previous={'kind':'generation_preview','request_id':'owned-old-review'}
    model=AsyncMock(side_effect=AssertionError('Output artifact is explicit; no engineering routing inference is needed'))
    with patch.dict(os.environ,COGNISHIELD_AI_PLANNING='1'):
        route=asyncio.run(select_context(question,None,'studio',EDITOR,[],
            [{'role':'user','content':'Previously requested native BGP.'}],previous=previous,inventory=INVENTORY,generate_fn=model))
    assert route.intent=='answer' and not route.use_editor and not route.use_history and not route.network_domains
    assert not model.called
    assert constrain_route(Route(intent='generate_native'),question).intent=='answer'


def test_program_artifact_constraint_preserves_actual_buffer_edits_and_v9_outputs():
    from llm.gateway_references import requested_program_artifact
    assert not requested_program_artifact('Write a Python function in the current file.')
    assert constrain_route(Route(intent='edit'),'Write a Python function in the current file.').intent=='edit'
    assert not requested_program_artifact('Generate native BGP configuration on Birch.')
    assert not requested_program_artifact('Create an Ansible playbook for OSPF.')


@pytest.mark.parametrize('modifier',['BGP and OSPF','JSON and YAML and Python','annotated vendor native routing and security'])
def test_coordinated_editor_source_names_retain_the_actual_snapshot(modifier):
    question='Explain the active unsaved '+modifier+' configuration. Do not modify it.'
    assert editor_context_requested(question,EDITOR)
    model=AsyncMock(side_effect=AssertionError('Explicit source identity does not need an intent guess'))
    route=asyncio.run(select_context(question,None,'studio',EDITOR,[],[],inventory=INVENTORY,generate_fn=model))
    assert route.use_editor and route.intent=='explain'


@pytest.mark.parametrize('surface',['studio','floating'])
def test_missing_explicit_editor_source_cannot_receive_a_context_free_factual_answer(surface):
    model=AsyncMock(side_effect=AssertionError('No source means no inferred editor facts'))
    route=asyncio.run(select_context('Explain the active unsaved BGP and OSPF configuration.',None,
        surface,None,[],[],inventory=INVENTORY,generate_fn=model))
    assert route.intent=='clarify' and route.planning['mode']=='missing_editor_source'
    assert not model.called and not route.network_domains
