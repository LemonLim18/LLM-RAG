"""Identifier fidelity and unchanged strict parsing; not model-quality tests."""
import copy
import json

import pytest
from pydantic import ValidationError

from llm.orchestration.investigation_support import compatible_claims
from llm.orchestration.role_reasoning import SourceClaim, parse_decision


def declaration(device_id='42'):
    return {'statement': 'The recorded interface is up.', 'category': 'interface_oper_status',
            'record_refs': ['port-record'], 'device_id': device_id, 'interface_id': '4201',
            'field': 'oper_status', 'value': 'up', 'scope': 'recorded'}


@pytest.mark.parametrize('identifier', ['42', '0042', '9007199254740993'])
def test_quoted_identifier_spelling_survives_without_normalization(identifier):
    raw = declaration(identifier)
    parsed = SourceClaim.model_validate_json(json.dumps(raw))
    assert parsed.device_id == identifier
    assert json.loads(parsed.model_dump_json())['device_id'] == identifier
    assert raw['device_id'] == identifier


@pytest.mark.parametrize('field,value', [
    ('device_id', 42), ('device_id', True), ('interface_id', 4201), ('record_refs', [17]),
])
def test_bad_identifier_types_are_rejected_not_silently_coerced(field, value):
    raw = declaration()
    raw[field] = value
    before = copy.deepcopy(raw)
    with pytest.raises(ValidationError):
        SourceClaim.model_validate(raw)
    decision, auxiliary = parse_decision(json.dumps({
        'decision': 'answer', 'answer': 'The recorded interface is up.', 'claims': [raw],
    }), independent_claims=True)
    assert raw == before
    assert decision.claims == []
    assert auxiliary['status'] == 'MODEL_CONTRACT_ERROR'
    assert auxiliary['valid_claims'] == 0


@pytest.mark.parametrize('source_id,correct,wrong', [(42, '42', '0042'), ('0042', '0042', '42')])
def test_quoted_id_must_still_match_its_actual_source_identity(source_id, correct, wrong):
    record = {'id': 'port-record', 'kind': 'interface_state', 'device_id': source_id,
              'interface_id': 4201, 'oper_status': 'up'}
    results = [{'tool': 'network.state', 'status': 'success', 'data': {'records': [record]}}]

    def verdict(identifier):
        decision = {'answer': 'The recorded interface is up.', 'claims': [declaration(identifier)]}
        return compatible_claims(decision, results, {'devices': []})['claims'][0]['verdict']

    assert verdict(correct) == 'SUPPORTED'
    assert verdict(wrong) == 'CONTRADICTED'
