"""Pre-inference checks of benchmark scope/context, not model evaluations."""
from collections import Counter
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def registry():
    return json.loads((ROOT / 'docs/evaluations/phase_f_case_registry.json').read_text())


def test_frozen_distribution_and_distinct_case_ids():
    data = registry()
    assert len(data['routing_cases']) == 120
    assert len(data['quality_cases']) == 30
    assert len(data['permission_cases']) == 10
    ids = [r['id'] for key in ['routing_cases', 'quality_cases', 'permission_cases'] for r in data[key]]
    assert len(set(ids)) == len(ids)
    assert Counter(r['group'] for r in data['routing_cases']) == {'concept': 20, 'inventory_topology': 20,
        'protocol_history': 20, 'documents': 15, 'studio': 15, 'compound': 30}


def test_elliptical_quality_questions_have_real_gateway_setup_turns():
    rows = {r['id']: r for r in registry()['quality_cases']}
    for number in [5, 11, 13, 15, 17, 19, 23, 28]:
        assert rows[f'F-QUALITY-{number:03d}']['starting_state']['setup_turns'], number


def test_screenshot_routing_case_has_image_not_pdf_fixture():
    data = registry()
    row = next(r for r in data['routing_cases'] if 'text in my attached screenshot' in r['prompt'])
    fixture = data['document_fixtures'][row['starting_state']['attachment_fixture']]
    assert fixture['name'].endswith('.png')
    assert fixture['expected_ocr_text']


def test_page_and_unsaved_buffer_oracles_contain_actual_values():
    data = registry()
    pages = data['document_fixtures']['migration-note']['pages']
    assert len(pages) == 4 and 'Rollback' in pages[3] and '65030' in pages[2]
    assert 'UNSAVED_F_QUALITY' in data['editor_fixtures']['routing-buffer']
    assert 'remote-as 65274' in data['editor_fixtures']['routing-buffer']


def test_execution_fixture_pdf_is_actually_readable_through_existing_extractor():
    import sys
    sys.path.insert(0, str(ROOT / 'backend'))
    import lab_config  # Match startup's existing document-interpreter configuration.
    from scripts.evaluate_phase_f_registry import pdf_bytes
    from llm.gateway_documents import extract_pdf
    pages = registry()['document_fixtures']['migration-note']['pages']
    extracted = extract_pdf(pdf_bytes(pages))
    assert [segment['page'] for segment in extracted] == [1, 2, 3, 4]
    assert 'Rollback' in extracted[3]['text']
    assert '65020' in extracted[2]['text'] and '65030' in extracted[2]['text']


def test_screenshot_fixture_uses_existing_document_runtime_when_api_has_no_pillow():
    import sys
    from unittest.mock import patch
    sys.path.insert(0,str(ROOT/'backend'))
    import lab_config
    from scripts.evaluate_phase_f_registry import attachment_bytes
    fixture=registry()['document_fixtures']['clear-screenshot']
    with patch.dict(sys.modules,{'PIL':None}):
        files=attachment_bytes(fixture)
    assert files[0][0]==fixture['name']
    assert files[0][1].startswith(b'\x89PNG\r\n\x1a\n')
    assert 1000<len(files[0][1])<1024*1024


def test_execution_capability_scoring_distinguishes_unaccepted_proposals():
    import sys
    sys.path.insert(0, str(ROOT / 'backend'))
    from scripts.evaluate_phase_f_registry import selected_capabilities
    result = {'observations': [], 'context_coverage': {'routing': {'editor': True}},
        'proposal': {'original': 'old', 'suggested': 'new'}}
    assert selected_capabilities(result) == {'document.propose'}
    assert selected_capabilities({'kind': 'generation_preview'}) == {'v9.preview'}


def test_missing_page_read_is_a_prerequisite_clarification_without_fabricated_evidence():
    import sys
    from copy import deepcopy
    sys.path.insert(0,str(ROOT/'backend'))
    from scripts.evaluate_phase_f_registry import missing_page_clarification,selected_capabilities
    result={'status':'clarification_required','kind':'clarification',
        'answer':'Page 99 is absent; available pages: 1, 2, 3, 4.', 'evidence':[],
        'context_coverage':{'files':{'tool':'document.read','included_characters':0,
            'page_selection':{'requested':[99],'missing':[99],'included':[],'available':[1,2,3,4]}}}}
    assert missing_page_clarification(result)
    assert selected_capabilities(result)=={'document.read'}
    for change in [{'evidence':[{'page':99}]},{'answer':'Please upload something.'},
                   {'proposal':{'suggested':'invented'}},{'status':'success'}]:
        assert not missing_page_clarification({**deepcopy(result),**change})
    result['context_coverage']['files']['page_selection']['available'].append(99)
    assert not missing_page_clarification(result)


def test_missing_selection_cannot_be_scored_as_a_fabricated_highlight_explanation():
    import sys
    sys.path.insert(0,str(ROOT/'backend'))
    from scripts.evaluate_phase_f_registry import missing_selection_clarification
    result={'status':'clarification_required','kind':'clarification','answer':'Select the block to explain.',
        'context_coverage':{'routing':{'editor':True},'files':{'selection_requested':True,'selection_available':False,'selection_included':False}}}
    assert missing_selection_clarification(result,{'content':'router bgp 65000','selection':None})
    assert not missing_selection_clarification(result,{'selection':{'text':'router bgp 65000'}})
    assert not missing_selection_clarification({**result,'evidence':[{'source':'invented selection'}]},{'selection':None})


def test_quality_run_uses_its_frozen_network_not_the_routing_fixture():
    import sys
    sys.path.insert(0,str(ROOT/'backend'))
    from scripts.evaluate_phase_f_registry import case_fixture
    spec=registry();row=spec['quality_cases'][3]
    fixture=case_fixture(row,spec,{'id':'WRONG-ROUTING-FIXTURE'})
    assert fixture['id']=='FQ-NET-01'
    assert fixture['devices'][1]['os_version']=='23.4'
    assert any(i.get('prefix')=='10.124.9.2/30' for i in fixture['interfaces'])


def test_quality_fixture_activation_reuses_existing_scenario(tmp_path):
    import sys
    sys.path.insert(0,str(ROOT/'backend'))
    from scripts.evaluate_phase_f_registry import activate_fixture
    from local_providers.development import ScenarioManager
    spec=registry();manager=ScenarioManager(tmp_path/'scenario.json')
    healthy=spec['network_fixtures']['healthy']
    faulty=spec['network_fixtures']['interface_down']
    activate_fixture(manager,healthy)
    activate_fixture(manager,healthy)
    activate_fixture(manager,faulty)
    activate_fixture(manager,healthy)
    current,meta=manager.snapshot()
    assert current['id']==healthy['id']
    assert len(current['interfaces'])==len(healthy['interfaces'])
    assert all(all(actual[k]==v for k,v in expected.items())
               for actual,expected in zip(current['interfaces'],healthy['interfaces']))
    assert len([r for r in manager.catalog() if r['id']==healthy['id']])==1


def test_edit_prerequisite_is_reported_pending_only_with_real_missing_selection():
    import sys
    sys.path.insert(0,str(ROOT/'backend'))
    from scripts.evaluate_phase_f_registry import pending_editor_prerequisite
    row={'expected_workflow':'edit','prompt':'Correct only the indentation in my selected editor code.'}
    result={'status':'clarification_required','kind':'clarification','answer':'Please select the code.',
        'context_coverage':{'routing':{'editor':True},'files':{'selection_requested':True,'selection_available':False}},
        'evidence':[],'proposal':None,'preview':None}
    assert pending_editor_prerequisite(row,result,{'selection':None})
    assert not pending_editor_prerequisite(row,result,{'selection':{'text':'real selected code'}})
    assert not pending_editor_prerequisite({**row,'prompt':'Change the BGP neighbor address.'},result,{'selection':None})
    assert not pending_editor_prerequisite(row,{**result,'proposal':{'suggested':'guessed code'}},{'selection':None})


def test_rename_prerequisite_is_not_counted_as_a_completed_patch():
    import sys
    sys.path.insert(0,str(ROOT/'backend'))
    from scripts.evaluate_phase_f_registry import pending_editor_prerequisite
    row={'expected_workflow':'edit','prompt':'Rename the variable in the selected Python block, keeping the rest untouched.'}
    editor={'selection':{'text':'result = sum(values)'}}
    result={'status':'clarification_required','kind':'clarification','answer':'What is the intended new name?',
        'context_coverage':{'routing':{'editor':True},'files':{'rename_target_required':True,'selection_available':True}},
        'evidence':[],'proposal':None,'preview':None}
    assert pending_editor_prerequisite(row,result,editor)
    assert not pending_editor_prerequisite({**row,'prompt':'Rename result to subtotal.'},result,editor)
    assert not pending_editor_prerequisite(row,{**result,'proposal':{'suggested':'def result(values): pass'}},editor)


def test_provider_tracing_does_not_consume_or_break_langchain_streams():
    import sys,httpx
    sys.path.insert(0,str(ROOT/'backend'))
    from scripts.evaluate_phase_f_registry import trace_provider_response
    response=httpx.Response(200,stream=httpx.ByteStream(b'{"message":{"content":"real decision"}}'))
    entry={'endpoint':'/api/chat'};trace_provider_response(entry,response)
    assert not response.is_stream_consumed and entry['body_capture']=='stream_unread_not_consumed_by_evaluator'
    assert response.read()==b'{"message":{"content":"real decision"}}'
    trace_provider_response(entry,response)
    assert entry['raw_response']['message']['content']=='real decision'
    embedding=httpx.Response(200,json={'model':'local','embeddings':[[0.1,0.2,0.3]]})
    entry={'endpoint':'/api/embed'};trace_provider_response(entry,embedding)
    assert entry['embedding_dimensions']==[3] and 'raw_response' not in entry


def test_unspecified_fix_is_pending_intent_not_completed_edit():
    import sys
    sys.path.insert(0,str(ROOT/'backend'))
    from scripts.evaluate_phase_f_registry import pending_editor_prerequisite
    row={'expected_workflow':'edit','prompt':'Fix the BGP issue in this unsaved file; ask if you need my intended value.'}
    result={'status':'clarification_required','kind':'clarification','answer':'What intended value or behavior do you need?',
        'context_coverage':{'routing':{'editor':True},'files':{'intended_correction_required':True}},'evidence':[],'proposal':None,'preview':None}
    assert pending_editor_prerequisite(row,result,{'content':'router bgp 65000'})
    assert not pending_editor_prerequisite({**row,'prompt':'Change local AS to 65001.'},result,{'content':'router bgp 65000'})


def test_followup_setup_requires_the_actual_proposal_not_just_http_success():
    import sys
    sys.path.insert(0,str(ROOT/'backend'))
    from scripts.evaluate_phase_f_registry import setup_turn_completed
    prompt='Propose changing the active BGP neighbor address to 192.0.2.71; do not accept or save.'
    assert not setup_turn_completed(prompt,{'status':'success','kind':'answer','answer':'Here is an explanation.'})
    assert setup_turn_completed(prompt,{'status':'success','kind':'edit_proposal','proposal':{'original':'actual','suggested':'reviewable'}})


def test_fresh_registry_is_explicit_and_does_not_fall_back_to_historical_facts():
    import sys
    sys.path.insert(0,str(ROOT/'backend'))
    from scripts.evaluate_phase_f_registry import load_registry
    path,spec,fixture=load_registry('docs/evaluations/phase_g_fresh_routing_v1.json')
    assert path.name=='phase_g_fresh_routing_v1.json'
    assert len(spec['routing_cases'])==120 and fixture['id']=='G11-CONTROLLED-48271'
    assert fixture['devices'][0]['hostname']=='Amber-Edge'
    historical,_,old_fixture=load_registry(None)
    assert historical.name=='phase_f_case_registry.json' and old_fixture['id']=='F-FROZEN-34941'


def test_registry_file_scope_and_unique_case_contracts_are_checked(tmp_path):
    import sys,pytest
    sys.path.insert(0,str(ROOT/'backend'))
    from scripts.evaluate_phase_f_registry import load_registry,validate_registry
    outside=tmp_path/'private.json';outside.write_text('{}')
    with pytest.raises(ValueError,match='evaluation directory'):load_registry(str(outside))
    spec=registry();spec['routing_cases'][1]['id']=spec['routing_cases'][0]['id']
    with pytest.raises(ValueError,match='unique'):validate_registry(spec)


def test_logical_source_credit_requires_reader_result_not_a_model_plan():
    import sys
    sys.path.insert(0,str(ROOT/'backend'))
    from scripts.evaluate_phase_f_registry import selected_logical_sources
    request={'source_categories':['routing_state']}
    assert not selected_logical_sources({'observations':[], 'context_coverage':{'tool_plan':request}})
    assert not selected_logical_sources({'observations':[{'tool':'network.state','source_request':request,'data':{}}]})
    record={'observations':[{'tool':'network.state','source_request':request,
        'data':{'records':[{'source_category':'routing_state'}],'source_statuses':{'routing_state':'STALE'}}}]}
    assert selected_logical_sources(record)=={'routing_state'}
    assert selected_logical_sources({'observations':[{'tool':'network.state','status':'error',
        'data':{'source_statuses':{'routing_state':'ERROR'}}}]})=={'routing_state'}


def test_full_source_registry_activation_reuses_owned_bundle_lifecycle(tmp_path):
    import sys
    sys.path.insert(0,str(ROOT/'backend'))
    from development.bundles import load_bundle,compile_bundle
    from scripts.evaluate_phase_f_registry import activate_registry,validate_registry
    from local_providers.development import ScenarioManager
    bundle=load_bundle(ROOT/'backend/development/scenarios/healthy_all_sources_v2')
    fixture=compile_bundle(bundle)
    spec={'routing_bundle':bundle,'routing_fixture':fixture}
    validate_registry(spec)
    manager=ScenarioManager(tmp_path/'state.json',enabled_default=False)
    activate_registry(manager,spec,fixture)
    scenario,meta=manager.snapshot()
    assert len(scenario['source_statuses'])==24
    assert manager.activated_bundle()['sources']['documents']['data']['files']
    assert meta['source_revision']


def test_curated_arm_keeps_raw_model_failure_without_verifier_repair():
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    import sys
    sys.path.insert(0,str(ROOT/'backend'))
    from scripts.evaluate_phase_f_registry import curated_model_answer
    raw='An unsupported diagnosis retained for independent grading.'
    model=SimpleNamespace(generate=AsyncMock(return_value=(raw,'qwen2.5:1.5b')))
    answer,report=asyncio.run(curated_model_answer(model,'Explain the evidence',[],[],[],{},[]))
    assert answer==raw and report['repair_attempts']==0 and not report['fallback']
    assert model.generate.await_count==1
    assert model.generate.call_args.kwargs['purpose']=='model_only'


def test_curated_scope_includes_frozen_transit_evidence_and_rejects_unknown_refs():
    import pytest
    import sys
    sys.path.insert(0,str(ROOT/'backend'))
    from scripts.evaluate_phase_f_registry import curated_references
    inventory={'devices':[{'hostname':name} for name in ['Edge','Transit','Exit']]}
    expand=lambda token:{'{A}':'Edge','{B}':'Transit','{C}':'Exit'}[token]
    row={'curated_device_tokens':['{A}','{B}','{C}']}
    assert curated_references(row,inventory,['Investigate Edge to Exit'],expand)==['Edge','Transit','Exit']
    with pytest.raises(ValueError,match='controlled fixture'):
        curated_references(row,{'devices':[{'hostname':'Edge'}]},[],expand)
