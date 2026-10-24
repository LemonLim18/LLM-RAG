"""Independent hand-defined forwarding outcomes through both authorized readers.

No expected outcome is manufactured using the model under test. These tests do
not invoke an LLM or claim causal-answer quality or full G6 acceptance.
"""
import asyncio,json
from pathlib import Path
import sys
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(1,str(Path(__file__).resolve().parent))
from development.starter import starter_bundle
from development.bundles import safe_file
from llm.tools import ToolAuthorization
from test_phase_g_source_contracts import source_runtime

ORACLE=Path(__file__).resolve().parents[1]/'development/test_oracles/phase_g_forwarding_conformance_v3.json'
CASES=json.loads(ORACLE.read_text(encoding='utf-8'))['cases']


def input_bundle(specification):
    bundle=starter_bundle()
    bundle['manifest'].update(scenario_id='S-CONTROLLED-NETWORK',name='Controlled development topology')
    for mutation in specification['mutations']:
        parts=mutation['path'].strip('/').split('/');node=bundle
        for part in parts[:-1]:node=node[int(part)] if isinstance(node,list) else node[part]
        if isinstance(node,list):
            if parts[-1]=='-':node.append(mutation['value'])
            else:node[int(parts[-1])]=mutation['value']
        else:node[parts[-1]]=mutation['value']
    return bundle


@pytest.mark.parametrize('specification',CASES,ids=[c['id'] for c in CASES])
def test_independent_conformance_both_authorized_surfaces(source_runtime,specification):
    _,manager,registry=source_runtime
    bundle=input_bundle(specification)
    draft=manager.save_draft(bundle,owner='conformance-owner',expected=None)
    receipt=manager.validate_draft(draft['draft_id'],owner='conformance-owner',expected=1)
    manager.activate_draft(draft['draft_id'],owner='conformance-owner',expected=1,
        expected_active=manager.snapshot()[1]['source_revision'],validation_hash=receipt['validation_hash'])
    actual=[]
    for surface in ['floating','studio']:
        auth=ToolAuthorization('conformance-owner','engineer',surface,'controlled-'+surface,frozenset({'network.state'}))
        result=asyncio.run(registry.invoke('network.state',{'device_refs':['LAB-R1','LAB-R3'],'source_categories':['simulation']},auth))
        assert result.status=='success' and all(e.origin=='simulated' for e in result.evidence)
        flow=next(r for r in result.data['records'] if r['kind']=='forwarding_assessment' and r['flow']['id']=='branch-edge-icmp')
        assessment=flow['assessment'];expected=specification['expected']
        assert assessment['forward']['status']==expected['forward']
        assert assessment['return']['status']==expected['return']
        if expected.get('forward_reason_contains'):
            assert any(expected['forward_reason_contains'] in b['reason'] for b in assessment['forward']['branches'])
        actual.append(assessment)
        assert specification['id'] not in json.dumps(result.model_dump())
        assert 'forward_reason_contains' not in json.dumps(result.model_dump())
    assert actual[0]==actual[1]
    with pytest.raises(ValueError,match='oracle'):safe_file(ORACLE.parent,ORACLE.name)


EXTENDED_ORACLE=ORACLE.with_name('phase_g_extended_conformance_v1.json')
EXTENDED_CASES=json.loads(EXTENDED_ORACLE.read_text(encoding='utf-8'))['cases']


def assert_expected_fields(record, expected):
    """Compare independently declared facts, including absent derived values."""
    for path, value in expected.items():
        parts=path.split('/');node=record
        if parts[-1]=='$absent':
            for key in parts[:-2]:node=node[key]
            assert (parts[-2] not in node)==value,path
            continue
        for key in parts:
            node=len(node) if key=='$length' else node[key]
        assert node==value,(path,node,value)


@pytest.mark.parametrize('specification',EXTENDED_CASES,ids=[c['id'] for c in EXTENDED_CASES])
def test_extended_independent_conformance_both_authorized_surfaces(source_runtime,specification):
    _,manager,registry=source_runtime
    draft=manager.save_draft(input_bundle(specification),owner='conformance-owner',expected=None)
    receipt=manager.validate_draft(draft['draft_id'],owner='conformance-owner',expected=1)
    manager.activate_draft(draft['draft_id'],owner='conformance-owner',expected=1,
        expected_active=manager.snapshot()[1]['source_revision'],validation_hash=receipt['validation_hash'])
    actual=[]
    for surface in ['floating','studio']:
        tool=specification['tool']
        auth=ToolAuthorization('conformance-owner','engineer',surface,'extended-'+surface,frozenset({tool}))
        # The simulation logical selector belongs to network.state. Existing
        # telemetry exposes modeled series through its ordinary bounded query,
        # not an incompatible state-only logical source filter.
        params={'device_refs':['LAB-R1','LAB-R2','LAB-R3']}
        if tool=='network.state':params['source_categories']=['simulation']
        result=asyncio.run(registry.invoke(tool,params,auth))
        assert result.status=='success' and all(e.origin=='simulated' for e in result.evidence)
        matching=[r for r in result.data['records'] if r['kind']==specification['record_kind']
            and all(r.get(key)==value for key,value in specification['selector'].items())]
        assert len(matching)==1
        assert_expected_fields(matching[0],specification['expected'])
        from scripts.evaluate_phase_g_causal_conformance import check_expected_record
        check_expected_record(result.data['records'],specification)
        assert specification['id'] not in json.dumps(result.model_dump())
        actual.append(matching[0])
    assert actual[0]==actual[1]
    with pytest.raises(ValueError,match='oracle'):safe_file(EXTENDED_ORACLE.parent,EXTENDED_ORACLE.name)
