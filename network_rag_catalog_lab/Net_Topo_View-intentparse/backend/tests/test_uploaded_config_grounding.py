"""The existing native-field guard also applies to uploaded configuration text."""
import asyncio
from pathlib import Path
import sys
from unittest.mock import AsyncMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from llm.orchestration.verification import verify_ocr_answer

TEXT = ('hostname UPLOADED-EDGE\nrouter ospf 88\n router-id 198.51.100.88\n'
        'router bgp 65088\n neighbor 192.0.2.89 remote-as 65189\n! UPLOAD_MARKER\n')
DOCS = [{'source': 'uploaded.cfg', 'text': TEXT, 'start_line': 1, 'end_line': 6}]


def test_uploaded_config_cannot_transfer_ospf_id_to_bgp_or_invent_device_upload():
    wrong = 'BGP router ID: 198.51.100.88. The file was uploaded to the router and saved on the router.'
    generate = AsyncMock(side_effect=AssertionError('Use the existing literal field guard, not another model call'))
    answer, _, report = asyncio.run(verify_ocr_answer('Explain the uploaded configuration.', wrong, 'mock', DOCS, generate))
    assert report and report['status'] == 'literal_uploaded_configuration_reconstruction'
    assert report['original_answer'] == wrong and report['model_synthesis'] is False
    assert '**Local AS:** `65088`' in answer and '**remote AS:** `65189`' in answer
    assert 'No explicit router ID appears in this shown BGP section' in answer
    assert 'editor buffer' not in answer and 'uploaded configuration' in answer
    assert 'upload to a device is not established' in answer
    generate.assert_not_awaited()


def test_correct_native_as_role_interpretation_is_preserved_without_false_repair():
    correct = 'The uploaded file sets OSPF router ID 198.51.100.88. BGP local AS is 65088, with neighbor 192.0.2.89 remote AS 65189. No explicit BGP router ID is present.'
    generate = AsyncMock(side_effect=AssertionError('A correct source interpretation must not need repair'))
    answer, _, report = asyncio.run(verify_ocr_answer('Explain the uploaded configuration.', correct, 'mock', DOCS, generate))
    assert answer == correct and report is None
    generate.assert_not_awaited()


def test_native_guard_does_not_claim_to_validate_arbitrary_vendor_prose_or_compare_two_configs():
    documents = [{'source': 'reference.pdf', 'page': 1, 'text': 'The note mentions a BGP example.'}]
    answer = 'The note mentions a BGP example.'
    generate = AsyncMock(side_effect=AssertionError('No unsupported native reconstruction'))
    returned, _, report = asyncio.run(verify_ocr_answer('What is in the note?', answer, 'mock', documents, generate))
    assert returned == answer and report is None


def test_proposed_document_establishes_neither_current_device_use_nor_non_use():
    from llm.orchestration.verification import document_answer_errors
    documents=[{'source':'note.pdf','page':1,'text':'OSPF process88; hello12; dead48. These are proposed settings, not a device measurement.'}]
    question='Does that mean this device is actually running those timer values?'
    for answer in ['The device is actually running those values.',
                   'The device is not actually running those values. These are proposed settings.']:
        assert document_answer_errors(answer,documents,question)
    correct='The document describes proposed settings. It does not establish whether the device currently uses those values.'
    assert not document_answer_errors(correct,documents,question)
    wrong='The active unsaved BGP and OSPF configuration includes these details: Router ID not specified. The PDF records proposed timers.'
    assert document_answer_errors(wrong,documents,question)
    bad_repair=AsyncMock(return_value=(wrong,'mock'))
    answer,_,report=asyncio.run(verify_ocr_answer(question,wrong,'mock',documents,bad_repair))
    assert report['status']=='planned_state_limitation_fallback' and not report['model_synthesis']
    assert 'neither current use nor non-use is verified' in answer
    assert report['original_answer']==wrong
    bad_repair.assert_not_awaited()
    passive='The note indicates that these settings are not currently being used by the device.'
    answer,_,report=asyncio.run(verify_ocr_answer(question,passive,'mock',documents,bad_repair))
    assert report['status']=='planned_state_limitation_fallback'
    assert 'neither current use nor non-use is verified' in answer
    bad_repair.assert_not_awaited()
