"""Independent fixture conformance through real authorized readers, no inference."""
import asyncio,json,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from db.manager import DatabaseManager
from llm.gateway_services import registry_for
from llm.gateway_store import ensure_schema
from llm.tools import ToolAuthorization
from local_providers.development import ScenarioManager
ROOT=Path(__file__).resolve().parents[2]
SPEC=json.loads((ROOT/'docs/evaluations/phase_g_multi_model_g4_g6_v1.json').read_text(encoding='utf-8'))

@pytest.mark.parametrize('case',[c for c in SPEC['cases'] if c['causal']],ids=lambda c:c['id'])
def test_frozen_source_conformance_both_surfaces(case,tmp_path,monkeypatch):
    monkeypatch.setenv('COGNISHIELD_DEV_SIMULATION','1')
    db=DatabaseManager(str(tmp_path/'app.db'));db.initialize();ensure_schema(db)
    assert Path(db._db_path).resolve().is_relative_to(tmp_path.resolve())
    manager=ScenarioManager(tmp_path/'scenario.json');db._development_scenario=manager
    manager.change('import',manager.snapshot()[1]['source_revision'],SPEC['fixtures'][case['scenario']])
    registry=registry_for(db);returned=[]
    try:
        for surface in ['floating','studio']:
            auth=ToolAuthorization('independent-fixture-owner','engineer',surface,'source-conformance-'+surface,frozenset({'network.state'}))
            result=asyncio.run(registry.invoke('network.state',{'device_refs':['Kite-Edge','Linden-Core','Quartz-Core','Sable-Leaf'],'record_kinds':['forwarding_assessment','protocol_assessment']},auth))
            assert result.status=='success' and all(e.origin=='simulated' for e in result.evidence)
            rows=result.data['records'];expected=case['independent_oracle']
            if 'forward' in expected:
                assessment=next(r['assessment'] for r in rows if r['kind']=='forwarding_assessment')
                assert assessment['forward']['status']==expected['forward']
                assert assessment['return']['status']==expected['return']
                if expected.get('forward_reason'):assert any(expected['forward_reason'] in branch['reason'] for branch in assessment['forward']['branches'])
            else:
                record=next(r for r in rows if r['kind']=='protocol_assessment' and r['protocol']==expected['protocol'])
                serialized=json.dumps(record)
                if case['id']=='MMQ-17':assert 'area mismatch' in serialized and 'Full' in serialized
                else:assert '65399' in serialized and '65310' in serialized and 'Active' in serialized
            returned.append(rows)
        assert returned[0]==returned[1]
        assert 'expected_claims' not in json.dumps(returned)
    finally:db.close()
