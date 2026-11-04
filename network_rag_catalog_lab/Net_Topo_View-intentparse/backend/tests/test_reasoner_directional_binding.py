"""Existing directional claim/release semantics; no model-quality assertion."""
import copy

from llm.orchestration.investigation_support import compatible_claims, release_interpretation
from tests.test_release_checker_scope_repair import claim, flow, source


def delivered_return():
    record = flow()
    part = record['assessment']['return']
    part['status'] = 'delivered'
    for branch in part['branches']:
        branch['status'] = 'delivered'
        branch.pop('failure_location', None)
    return record


def assess(declaration):
    decision = {'answer': 'The return path is modeled delivered.', 'claims': [declaration],
                'core_validation': 'VALID'}
    review = {'claim_compatibility': compatible_claims(
        decision, source([delivered_return()]), {'devices': []})}
    return review, release_interpretation(decision, review)


def test_path_level_return_selector_is_direction_origin_not_record_owner():
    declaration = claim(device_id='30', interface_id=None, direction='return', value='delivered')
    review, released = assess(declaration)
    assert review['claim_compatibility']['claims'][0]['verdict'] == 'SUPPORTED'
    assert not review['claim_compatibility']['conflicts']
    assert released['answer'] == 'The return path is modeled delivered.'
    assert released['release_decision']['semantic_certified'] is False

    wrong = copy.deepcopy(declaration)
    wrong['device_id'] = '10'  # Enclosing record owner is the return destination.
    review, released = assess(wrong)
    assert review['claim_compatibility']['claims'][0]['verdict'] == 'CONTRADICTED'
    assert released['release_decision']['disposition'] == 'WITHHELD'
    assert released['release_decision']['semantic_certified'] is False


def test_omitted_optional_device_does_not_invent_a_path_origin():
    declaration = claim(device_id=None, interface_id=None, direction='return', value='delivered')
    review, released = assess(declaration)
    assert declaration['device_id'] is None
    assert review['claim_compatibility']['claims'][0]['verdict'] == 'SUPPORTED'
    assert released['answer'] == 'The return path is modeled delivered.'
    assert released['release_decision']['semantic_certified'] is False
