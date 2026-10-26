import asyncio,json,sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock,patch
import os
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm.gateway_models import Evidence
from llm.orchestration.request_contract import response_obligations,compound_schema,assemble_response
from llm.orchestration.synthesis import AnswerDraft,synthesize,check_candidate,forwarding_claim_errors
from llm.gateway_routing import select_context
from llm.gateway_documents import file_context_requested,editor_context_requested


def test_original_clauses_not_model_read_hints_define_response_contract():
    text='Quote the explicit router-ID command and explain whether it determines a different protocol identifier.'
    parts=response_obligations(text)
    assert len(parts)==2 and parts[1]['text']=='explain whether it determines a different protocol identifier.'
    assert response_obligations('Compare BGP and OSPF forward and return observations.')==[]
    schema=compound_schema(AnswerDraft.model_json_schema(),parts)
    assert schema['properties']['responses']['minItems']==2
    assert schema['$defs']['ClauseResponse']['properties']['id']['enum']==['request-1','request-2']


def test_ordered_compound_answers_can_share_one_source_and_include_an_uncited_concept():
    parts=response_obligations('Quote the saved hostname and explain the general meaning of a hostname.')
    raw=json.dumps({'responses':[{'id':'request-2','answer':'A hostname identifies a device.','sources':[]},
        {'id':'request-1','answer':'The saved command is hostname Willow.','sources':['S1']}]})
    answer,trace=assemble_response(raw,parts,AnswerDraft)
    assert answer.answer.startswith('The saved command') and answer.sources==['S1']
    assert trace['coverage'].startswith('Structural')


@pytest.mark.parametrize('ids',[['request-1','request-1'],['request-1','invented'],['request-1']])
def test_missing_duplicate_or_fabricated_user_clauses_cannot_release(ids):
    parts=response_obligations('Read the record and explain its limitation.')
    with pytest.raises(ValueError):assemble_response(json.dumps({'responses':[
        {'id':key,'answer':'Recorded facts.','sources':['S1']} for key in ids]}),parts,AnswerDraft)


def test_compound_synthesis_uses_the_contract_without_an_auxiliary_citation_requirement():
    parts=response_obligations('Read the saved hostname and explain its meaning.')
    context=[{'tool':'network.configuration','status':'success','evidence_ids':['c'],
        'data':{'records':[{'hostname':'Willow','config_text':'hostname Willow\n'}]}}]
    model=SimpleNamespace(generate=AsyncMock(return_value=(json.dumps({'responses':[
        {'id':'request-1','answer':'The saved command is hostname Willow.','sources':['S1']},
        {'id':'request-2','answer':'It records the device name; it does not establish live connectivity.','sources':['S1']}]}),'mock')))
    answer,trace=asyncio.run(synthesize(model,None,'Read the saved hostname and explain its meaning.',context,
        [Evidence(id='c',source='saved',origin='stored')],{},'fallback',user_obligations=parts))
    assert trace['status']=='literal_checks_passed' and 'device name' in answer
    assert trace['attempts'][0]['response_contract']['obligations']==parts


def test_causal_followup_retains_prior_evidence_dependencies_but_source_switch_does_not():
    from llm.gateway_references import resolve_read
    previous={'context_coverage':{'retrieval':{'domains':['state','configuration'],'device_refs':['7'],
        'interface_refs':[],'attributes':[],'entities':[],'source_requests':{'state':{'source_scope':'observed'}}}}}
    inventory={'devices':[{'id':7,'hostname':'Willow','interfaces':[]}]}
    resolved=resolve_read('If transport worked, would that resolve this configuration discrepancy?',previous,inventory)
    assert set(resolved['domains'])=={'state','configuration'} and resolved['comparison_domains']==['state','configuration']
    switched=resolve_read('Read only the saved configuration for that device.',previous,inventory)
    assert switched['domains']==['configuration'] and not switched.get('comparison_domains')


def test_page_reference_binds_unique_owned_pdf_without_reading_other_available_files():
    pdf={'id':'owned','name':'unfamiliar.pdf'}
    assert file_context_requested('From page 7, give the stated time.',[pdf])
    assert not file_context_requested('From page 7, give the stated time.',[pdf,{'id':'other','name':'second.pdf'}])
    assert not file_context_requested('With that PDF still attached, explain integer division.',[pdf])
    assert file_context_requested('With that PDF attached, explain it.',[pdf])


def test_qualified_unsaved_reference_does_not_require_a_hardcoded_file_type_noun():
    editor=SimpleNamespace(path='playbooks/private.cfg',selection=None)
    assert editor_context_requested('Explain the actual unsaved fragment.',editor)
    assert not editor_context_requested('Explain the concept of unsaved work in general.',editor)


def test_classifier_uncertainty_without_an_unresolved_reference_remains_conversational():
    generate=AsyncMock(return_value=('{"intent":"clarify","use_editor":false,"use_attachments":false}','mock'))
    with patch.dict(os.environ,COGNISHIELD_AI_PLANNING='0'),patch('llm.gateway_semantics.semantic_hint',AsyncMock(return_value=None)):
        route=asyncio.run(select_context('At a high level, why can an identifier stay stable across addressing changes?',None,
            'floating',None,[],[],generate_fn=generate))
    assert route.intent=='answer' and not route.network_domains


def test_returned_outcomes_are_not_missing_observations_and_metadata_gaps_remain_allowed():
    flow={'source_device':'Willow','destination_device':'Hazel','forward':{'status':'delivered','branches':[]},
        'return':{'status':'failed','branches':[{'status':'failed','path':['Hazel'],'reason':'no route'}]}}
    assert forwarding_claim_errors('The return traffic, which is expected to be failed, is not recorded.',[flow])
    assert not forwarding_claim_errors('The return next-hop address is not recorded. The return outcome is failed.',[flow])


def test_topology_relationships_and_management_entity_ownership_are_always_checked():
    links=[{'source':'Willow','source_interface':'port-a','target':'Hazel','target_interface':'port-b'},
        {'source':'Hazel','source_interface':'port-c','target':'Elm','target_interface':'port-d'}]
    context=[{'tool':'network.topology','status':'success','data':{'links':links}}]
    assert check_candidate('Willow / port-a connects to Hazel / port-c.',context,[],{},'Describe the relationships.')
    assert not check_candidate('Willow / port-a connects to Hazel / port-b.',context,[],{},'Describe the relationships.')
    context=[{'tool':'inventory.read','status':'success','data':{'devices':[{'hostname':'Willow','management_ip':'192.0.2.7',
        'interfaces':[{'name':'port-a','interface_type':'routed','ip_address':'198.51.100.7'}]}]}}]
    question='Distinguish its management address from each routed interface address.'
    assert check_candidate('Its management interface is up at192.0.2.7.',context,[],{},question)
    assert not check_candidate('The management endpoint is192.0.2.7; port-a has routed address198.51.100.7.',context,[],{},question)


def test_output_artifact_type_and_negative_source_clause_do_not_depend_on_request_prefix():
    from llm.gateway_references import requested_program_artifact
    assert requested_program_artifact('Provide a Rust function returning a sum.')
    assert requested_program_artifact('Give a Python function returning a difference.')
    assert not requested_program_artifact('Replace the Python function in helpers.py.')
    editor=SimpleNamespace(path='playbooks/private.cfg',selection=None)
    assert not editor_context_requested('Tell me a decimal value. The unsaved tab need not be read.',editor)
    assert editor_context_requested('Explain my unsaved fragment; do not change it.',editor)


def test_published_choices_are_not_observed_values_and_matching_captures_are_not_history():
    from llm.orchestration.synthesis import PublishedAnswerDraft,published_answer_errors
    facts=[{'operation_id':'synthetic','required':[],'required_by_vendor':{},'vendor_platforms':[],
        'fields':[{'field':'mode_type','enum':['alpha','beta']}],'sources':['S1']}]
    def errors(text):return published_answer_errors(PublishedAnswerDraft(answer=text,sources=['S1','S2'],operation_ids=['synthetic']),
        facts,'Compare published options with captured settings.',['S2'],['mode alpha'])
    assert errors('The configuration contains:\nmode type beta. [S1] [S2]')
    assert not errors('The configuration contains mode type alpha. [S1] [S2]')
    assert not errors('Allowed mode_type choices include alpha and beta. [S1] [S2]')
    rows=[{'hostname':'Willow','kind':kind,'current':current,'timestamp':stamp,'config_text':'hostname Willow\n'}
          for kind,current,stamp in [('running_configuration',True,'2026-10-24T01:00:00Z'),
              ('configuration_snapshot',False,'2026-10-24T00:00:00Z')]]
    context=[{'tool':'network.configuration','status':'success','data':{'records':rows}}]
    assert check_candidate('Identical records indicate there were no intervening changes.',context,[],{},'Explain these records.')
    assert not check_candidate('The captured texts are identical. This does not prove there were no intervening changes.',context,[],{},'Explain these records.')
def test_correct_rejection_of_identity_inference_does_not_require_magic_absence_formula():
    from llm.orchestration.synthesis import check_candidate
    context=[{'tool':'network.configuration','status':'success','evidence_ids':[],
        'data':{'records':[{'hostname':'Rowan','config_text':'set routing-options autonomous-system 64731\nset protocols bgp group EDGE neighbor 203.0.113.31 peer-as 64732\n'}]}}]
    question='Check whether the saved AS number establishes its router ID.'
    correct='The inference is not justified. An autonomous system number is not the same as the router ID.'
    assert not check_candidate(correct,context,[],{},question)
    assert check_candidate('The inference is justified. The AS number is its router ID.',context,[],{},question)
    assert check_candidate('The inference is not justified. Its configured router ID is 203.0.113.99.',context,[],{},question)
    assert check_candidate('The inference is not justified. Its configured router ID is 203.0.113.31.',context,[],{},question)


@pytest.mark.parametrize('prompt',[
    'The unsaved buffer need not be read, but explain binary arithmetic.',
    'Explain binary arithmetic, and the unsaved buffer need not be read.',
    'The unsaved buffer should not be consulted; then explain binary arithmetic.'
])
def test_passive_source_exclusion_preserves_adjacent_positive_obligation(prompt):
    from llm.gateway_references import main_request_text
    actual=main_request_text(prompt)
    assert 'explain binary arithmetic' in actual.casefold()
    assert 'unsaved' not in actual.casefold()
    untouched='Read edge.example.cfg at 192.0.2.4 and explain the OSPF and BGP roles.'
    assert main_request_text(untouched)==untouched

