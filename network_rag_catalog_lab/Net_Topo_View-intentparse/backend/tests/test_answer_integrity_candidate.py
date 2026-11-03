"""Instruction wiring/authorization only. No test establishes better reasoning."""
import asyncio
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / 'tmp/phase-g/iterations/20261102-answer-integrity-offline'
sys.path.insert(0, str(ROOT / 'backend'))
sys.path.insert(0, str(ROOT / 'backend/scripts'))
import freeze_timestamp_contract as capture_tools
from llm import model_roles
from llm.orchestration import role_reasoning

FLAG = 'COGNISHIELD_AI_REASONER_ANSWER_INTEGRITY'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def before(name):
    path = AUDIT / 'source-before/backend/llm' / (name + '.py')
    spec = importlib.util.spec_from_file_location('_answer_integrity_before_' + name.replace('/', '_'), path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def binding():
    return hashlib.sha256(json.dumps(model_roles.consent_manifest(), sort_keys=True).encode()).hexdigest()


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    for key, value in capture_tools.ENV.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv(FLAG, 'off')
    for key in ['COGNISHIELD_AI_REASONER_MODEL', 'COGNISHIELD_AI_REASONER_PROVIDER',
                'COGNISHIELD_AI_REASONER_THINKING', 'COGNISHIELD_AI_REASONER_OUTPUT_TOKENS',
                'COGNISHIELD_AI_REASONER_SCHEMA_MODE']:
        monkeypatch.delenv(key, raising=False)
    # Serialization tests override send/quota with their own zero-network
    # interception. No real reservation or endpoint can escape this fixture.
    # Windows asyncio.socketpair uses loopback connect for its own self-pipe;
    # blocking socket.connect breaks event-loop construction, not inference.
    # Provider send, ordinary connection helpers, quota and readers stay blocked.
    with patch('httpx.AsyncClient.send', side_effect=AssertionError('No cloud dispatch')) as send, \
            patch('socket.create_connection', side_effect=AssertionError('No sockets')) as create, \
            patch('llm.gemini_provider._quota_update', side_effect=AssertionError('No quota write')) as quota, \
            patch('llm.tools.ToolRegistry.invoke', side_effect=AssertionError('No readers')) as reader:
        yield
        send.assert_not_called()
        create.assert_not_called()
        quota.assert_not_called()
        reader.assert_not_called()


def fixture(cid):
    if cid.startswith('H-'):
        p = ROOT / 'tmp/phase-g/iterations/20261102T104614Z-timestamp-contract-experiment/frozen-v1' / cid / 'pair.json'
        value = load(p)
        return value['inputs'], value['arms']['control']
    p = ROOT / 'tmp/phase-g/iterations/20261102-evidence-reasoning-contract/frozen-v3' / cid / 'packet.json'
    value = load(p)
    return value['inputs'], value['arms']['off']


CASES = [f'{prefix}-{n:02d}' for prefix in ['RC', 'H'] for n in range(1, 7)]


def test_unset_and_off_keep_manifest_byte_exact():
    with patch.dict('os.environ', {}, clear=False):
        __import__('os').environ.pop(FLAG)
        assert model_roles.answer_integrity_mode() == 'off'
        old = before('model_roles').consent_manifest()
        assert json.dumps(model_roles.consent_manifest()) == json.dumps(old)
        assert 'reasoner_answer_integrity' not in model_roles.consent_manifest()


@pytest.mark.parametrize('value', ['', 'on', '1', 'auto', 'Candidate', 'off '])
def test_unknown_flag_values_fail_closed(value, monkeypatch):
    monkeypatch.setenv(FLAG, value)
    with pytest.raises(HTTPException) as error:
        model_roles.consent_manifest()
    assert error.value.status_code == 422


@pytest.mark.parametrize('cid', CASES)
def test_twelve_existing_controls_off_exact_and_candidate_one_suffix(cid, monkeypatch):
    args, frozen = fixture(cid)
    original = copy.deepcopy(args)
    old = asyncio.run(capture_tools.capture(before('orchestration/role_reasoning'), args))
    off = asyncio.run(capture_tools.capture(role_reasoning, args))
    assert off == old
    assert json.dumps(off['messages'], ensure_ascii=False) == json.dumps(frozen['messages'], ensure_ascii=False)
    assert json.dumps(off['schema']) == json.dumps(frozen['schema'])
    monkeypatch.setenv(FLAG, 'candidate')
    candidate = asyncio.run(capture_tools.capture(role_reasoning, args))
    suffix = '\n\n' + role_reasoning.ANSWER_INTEGRITY_CANDIDATE
    assert candidate['messages'][0]['content'] == off['messages'][0]['content'] + suffix
    assert candidate['messages'][0]['content'].count(role_reasoning.ANSWER_INTEGRITY_CANDIDATE) == 1
    assert candidate['messages'][1:] == off['messages'][1:]
    assert candidate['schema'] == off['schema']
    assert candidate['purpose'] == off['purpose']
    assert args == original
    packet = json.loads(candidate['messages'][1]['content'])
    assert packet['reader_results'] == args['results']
    assert 'reasoning_contract' not in packet
    assert len(candidate['messages'][1]['content']) <= 64000
    assert 'description' not in candidate['schema']['$defs']['SourceClaim']['properties']['timestamp']


@pytest.mark.parametrize('cid', ['RC-04', 'H-01', 'H-06'])
def test_existing_adapter_wire_changes_only_system_suffix(cid, monkeypatch):
    args, _ = fixture(cid)
    old = asyncio.run(capture_tools.capture(before('orchestration/role_reasoning'), args))
    off = asyncio.run(capture_tools.capture(role_reasoning, args))
    a = asyncio.run(capture_tools.serialized_wire(off['messages'], off['schema']))
    previous = asyncio.run(capture_tools.serialized_wire(old['messages'], old['schema']))
    assert json.dumps(a, ensure_ascii=False) == json.dumps(previous, ensure_ascii=False)
    monkeypatch.setenv(FLAG, 'candidate')
    on = asyncio.run(capture_tools.capture(role_reasoning, args))
    b = asyncio.run(capture_tools.serialized_wire(on['messages'], on['schema']))
    assert b['systemInstruction']['parts'][0]['text'] == a['systemInstruction']['parts'][0]['text'] + '\n\n' + role_reasoning.ANSWER_INTEGRITY_CANDIDATE
    b['systemInstruction']['parts'][0] = a['systemInstruction']['parts'][0]
    assert b == a
    assert a['generationConfig'] == {'thinkingConfig': {'thinkingLevel': 'low'},
        'maxOutputTokens': 8192, 'responseMimeType': 'application/json'}


def test_candidate_leaves_all_role_selections_and_budgets_unchanged(monkeypatch):
    roles = model_roles.role_manifest()
    manifest = model_roles.consent_manifest()
    monkeypatch.setenv(FLAG, 'candidate')
    current = model_roles.consent_manifest()
    extra = current.pop('reasoner_answer_integrity')
    assert current == manifest
    assert roles == model_roles.role_manifest()
    assert roles['evidence_reasoner']['model'] == 'gemini-3.5-flash-lite'
    assert roles['complex_planner']['model'] == 'gemini-3.1-flash-lite'
    assert roles['local_default']['model'] == 'qwen2.5:1.5b'
    assert extra['instruction_delta'] == role_reasoning.ANSWER_INTEGRITY_CANDIDATE
    assert extra['instruction_sha256'] == hashlib.sha256(extra['instruction_delta'].encode()).hexdigest()
    assert current['investigation_profile']['seconds'] == 120


@pytest.mark.parametrize('provider,model', [('google', 'gemini-3.1-flash-lite'),
    ('ollama', 'qwen2.5:1.5b'), ('openai', 'gpt-4.1')])
def test_candidate_cannot_target_another_model(provider, model, monkeypatch):
    monkeypatch.setenv(FLAG, 'candidate')
    monkeypatch.setenv('COGNISHIELD_AI_REASONER_PROVIDER', provider)
    monkeypatch.setenv('COGNISHIELD_AI_REASONER_MODEL', model)
    monkeypatch.setenv('COGNISHIELD_AI_REASONER_THINKING', 'off')
    with pytest.raises(HTTPException) as error:
        model_roles.answer_integrity_mode()
    assert error.value.status_code == 422


@pytest.mark.parametrize('key,value', [('COGNISHIELD_AI_REASONING_CONTRACT', 'obligations'),
    ('COGNISHIELD_AI_REASONING_CONTRACT', 'relationships'),
    ('COGNISHIELD_AI_REASONER_INTERPRETATION_EXPERIMENT', 'candidate'),
    ('COGNISHIELD_AI_SOURCECLAIM_TIMESTAMP_EXPERIMENT', 'candidate'), ('COGNISHIELD_AI_OUTCOMES', '1')])
def test_candidate_refuses_to_stack_retired_candidates(key, value, monkeypatch):
    monkeypatch.setenv(FLAG, 'candidate')
    monkeypatch.setenv(key, value)
    with pytest.raises(HTTPException) as error:
        model_roles.answer_integrity_mode()
    assert error.value.status_code == 422


def test_consent_binds_exact_candidate_and_cannot_reuse_old_approval(monkeypatch):
    from llm.gemini_provider import HybridRequest
    old = binding()
    scenario = {'scenario_digest': 'synthetic', 'source_revision': 'same'}
    scope = SimpleNamespace(db=object(), role_binding=old, approved_scenario=scenario)
    context = lambda db: {'enabled': True, 'eligible': True, 'role_binding': binding(), **scenario}
    with patch('llm.gemini_provider.hybrid_context', context):
        HybridRequest.assert_current_roles(scope)
        monkeypatch.setenv(FLAG, 'candidate')
        with pytest.raises(HTTPException) as error:
            HybridRequest.assert_current_roles(scope)
        assert error.value.status_code == 403
        scope.role_binding = binding()
        HybridRequest.assert_current_roles(scope)
        monkeypatch.setattr(role_reasoning, 'ANSWER_INTEGRITY_CANDIDATE', role_reasoning.ANSWER_INTEGRITY_CANDIDATE + ' changed')
        with pytest.raises(HTTPException):
            HybridRequest.assert_current_roles(scope)


def test_flag_is_not_cloud_authorization(monkeypatch):
    monkeypatch.setenv(FLAG, 'candidate')
    with pytest.raises(HTTPException) as error:
        asyncio.run(model_roles.infer('evidence_reasoner', model_roles.InferenceRequest(
            [{'role': 'user', 'content': 'Synthetic'}], {'type': 'object'}, time.monotonic() + 10)))
    assert error.value.status_code == 403


def test_no_case_specific_answers_or_schema_requirements_in_instruction():
    text = role_reasoning.ANSWER_INTEGRITY_CANDIDATE
    assert text.startswith('Source-grounded answer integrity\n\n')
    for forbidden in ['1500', '08:00', '07:10', 'Ravine', 'Plateau', 'TransitHub', 'RC-04', 'H-01']:
        assert forbidden not in text
    assert 'Markdown within the `answer` string remains permitted' in text


def saved_model(raw):
    calls = []
    async def generate(messages, structured, **kwargs):
        calls.append((messages, structured, kwargs))
        return raw, 'gemini-3.5-flash-lite'
    return SimpleNamespace(hybrid=SimpleNamespace(role_calls=0, remote_calls=0, max_remote_calls=3), generate=generate), calls


def args_for_decision(cid):
    from llm.gateway_models import Evidence
    args, _ = fixture(cid)
    args = copy.deepcopy(args)
    args['evidence'] = [Evidence.model_validate(e) for e in args['evidence']]
    return args


def test_same_saved_positive_response_parses_and_releases_unchanged(monkeypatch):
    raw = load(ROOT / 'tmp/phase-g/iterations/20261102-evidence-reasoning-contract/live-results/RC-03-off.json')['raw']
    off_model, off_calls = saved_model(raw)
    off = asyncio.run(role_reasoning.decide(off_model, **args_for_decision('RC-03')))
    monkeypatch.setenv(FLAG, 'candidate')
    model, calls = saved_model(raw)
    on = asyncio.run(role_reasoning.decide(model, **args_for_decision('RC-03')))
    assert on == off
    assert len(calls) == len(off_calls) == 1
    final, trace = role_reasoning.preview(on, 'off', [], [], {}, '')
    assert json.loads(raw)['answer'] in final
    assert trace['status'] == 'experimental_unverified'


def test_invalid_json_and_unknown_authoritative_source_still_fail_closed(monkeypatch):
    monkeypatch.setenv(FLAG, 'candidate')
    bad, calls = saved_model('{"answer": "text", -timestamp: "bad"}')
    with pytest.raises(ValueError):
        asyncio.run(role_reasoning.decide(bad, **args_for_decision('H-01')))
    assert len(calls) == 1
    d = load(ROOT / 'tmp/phase-g/iterations/20261102T123607Z-timestamp-contract-live/cells/H-01-control.json')['parsed_json']
    d['sources'] = ['invented-authority']
    bad, calls = saved_model(json.dumps(d))
    with pytest.raises(HTTPException) as error:
        asyncio.run(role_reasoning.decide(bad, **args_for_decision('H-01')))
    assert error.value.status_code == 422 and len(calls) == 1


def test_instruction_does_not_claim_to_repair_a_saved_semantic_failure(monkeypatch):
    monkeypatch.setenv(FLAG, 'candidate')
    saved = load(ROOT / 'tmp/phase-g/iterations/20261102T123607Z-timestamp-contract-live/cells/H-01-candidate.json')
    model, calls = saved_model(saved['raw'])
    result = asyncio.run(role_reasoning.decide(model, **args_for_decision('H-01')))
    assert '1500' not in result['answer']
    assert result['answer'] == saved['parsed_json']['answer']
    assert len(calls) == 1
    # A stub returning the old omission cannot prove the new instruction works.
    assert result['outcome_assessments'][0]['status'] == 'supported'
