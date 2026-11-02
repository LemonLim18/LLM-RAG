"""Frozen evidence/ground-truth contracts; no model or network."""
import hashlib,json,sys
from pathlib import Path
import pytest,jsonschema
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from local_providers.development import Scenario
from development.network_model import assess_flow,Flow
from llm.orchestration.investigation_support import walk
ROOT=Path(__file__).resolve().parents[2]
AUDIT=ROOT/'tmp/phase-g/iterations/20261101-audit-grounded-repair'
SPEC=ROOT/'docs/evaluations/phase_g_audit_grounded_reasoning_v1.json'
REGISTRY=json.loads(SPEC.read_text(encoding='utf-8'))
FREEZE=json.loads((AUDIT/'freeze-receipt.json').read_text(encoding='utf-8'))

@pytest.mark.parametrize('case',REGISTRY['cases'],ids=lambda c:c['id'])
def test_source_operands_and_core_contract_are_frozen(case):
    proof=next(c for c in FREEZE['cases'] if c['id']==case['id'])
    p=AUDIT/'frozen-v1'/case['id']/'frozen-packet.json'
    assert hashlib.sha256(p.read_bytes()).hexdigest()==proof['packet_sha256']
    frozen=json.loads(p.read_text(encoding='utf-8'))
    Scenario.model_validate(case['scenario'])
    assert hashlib.sha256(SPEC.read_bytes()).hexdigest()==FREEZE['registry_sha256']
    packet=json.loads(frozen['messages'][1]['content'])
    assert 'expected' not in packet and 'independent_source_oracle' not in packet and 'prohibited' not in packet
    assert packet['original_user_instruction']==case['prompt']
    assert packet['reader_results']==frozen['inputs']['results']
    if case['advisory']:
        assert not packet['reader_results']
        assert packet['advisory_context']['prior_authorized_records']==frozen['actual_authorized_rows']
    assert sorted(r['id'] for row in frozen['actual_authorized_rows'] for _,r in walk(row.get('data')))==sorted(proof['record_ids'])
    assert len(packet['requested_clauses'])<=8
    jsonschema.Draft202012Validator.check_schema(frozen['schema'])
    if case['expected_flow']:
        actual=assess_flow(case['scenario'],Flow.model_validate(case['scenario']['network']['flows'][0]))
        assert {k:actual[k]['status'] for k in ['forward','return']}==case['expected_flow']

def test_exact_ownership_and_direction_oracles_are_independent():
    cases={c['id']:c for c in REGISTRY['cases']}
    a=assess_flow(cases['AGR-01']['scenario'],Flow.model_validate(cases['AGR-01']['scenario']['network']['flows'][0]))
    assert a['forward']['branches'][0]['failure_location']['direction']=='egress'
    assert a['return']['branches'][0]['failure_location']['direction']=='ingress'
    b=assess_flow(cases['AGR-02']['scenario'],Flow.model_validate(cases['AGR-02']['scenario']['network']['flows'][0]))
    assert b['forward']['branches'][0]['failure_location']['device_id']==284
    assert b['forward']['branches'][0]['failure_location']['interface_id']==2841
    assert b['return']['status']=='delivered'

def test_published_schema_requires_interface_objects_not_network_statement():
    p=json.loads((AUDIT/'frozen-v1/AGR-06/frozen-packet.json').read_text(encoding='utf-8'))
    contract=p['independent_source_oracle']['actual_published_contract'][0]['published_requirements']['operations'][0]['schema']
    assert 'interfaces' in contract['required']
    assert set(contract['properties']['interfaces']['items']['required'])=={'name','area'}
    assert 'process_id' in contract['x-required-by-vendor']['cisco']

