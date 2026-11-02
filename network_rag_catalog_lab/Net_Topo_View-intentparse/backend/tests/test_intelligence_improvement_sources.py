"""Pre-inference new fixture checks through both actual authorized reader surfaces."""
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
SPEC=json.loads((ROOT/'docs/evaluations/phase_g_intelligence_improvement_holdout_v1.json').read_text(encoding='utf-8'))

@pytest.mark.parametrize('case',SPEC['cases'],ids=lambda c:c['id'])
def test_holdout_operands_are_available_to_both_surfaces(case,tmp_path,monkeypatch):
    monkeypatch.setenv('COGNISHIELD_DEV_SIMULATION','1')
    db=DatabaseManager(str(tmp_path/'app.db'));db.initialize();ensure_schema(db)
    assert Path(db._db_path).resolve().is_relative_to(tmp_path.resolve())
    manager=ScenarioManager(tmp_path/'scenario.json');db._development_scenario=manager
    manager.change('import',manager.snapshot()[1]['source_revision'],SPEC['fixtures'][case['scenario']]);registry=registry_for(db)
    output=[]
    try:
        for surface in ['floating','studio']:
            tools=case['required_tools'] or ['network.configuration']
            auth=ToolAuthorization('independent-holdout-owner','engineer',surface,'holdout-source-'+surface,frozenset(tools));surface_results=[]
            for tool in tools:
                args={'device_refs':['Harbor','Transit','Meadow']}
                if tool=='network.configuration':args['source_scope']='historical' if case['id']=='MNI-07' else 'both'
                r=asyncio.run(registry.invoke(tool,args,auth));surface_results.append(r.data)
                if tool=='network.configuration':
                    assert r.data['records']
                    assert 'HOLDOUT_ROUTING_71' in str(r.data) if case['id']=='MNI-07' else any(x.get('current') for x in r.data['records'])
                if tool=='network.syslog' and case['id']=='MNI-05':assert r.data['source_available'] is False
                if tool=='network.state':
                    if case['id']=='MNI-08':assert r.data['source_available'] is False;continue
                    rows=r.data['records'];o=case['independent_oracle']
                    if o:
                        v=next(x['assessment'] for x in rows if x['kind']=='forwarding_assessment')
                        assert v['forward']['status']==o['forward'] and v['return']['status']==o['return']
                    if case['id']=='MNI-06':assert all(str(value) in str(rows) for value in [64571,64572,64579,'Full','Active'])
                if tool=='network.telemetry':assert all(str(value) in str(r.data) for value in [22,57,89])
            output.append(surface_results)
        assert output[0]==output[1]
        assert 'expected_claims' not in json.dumps(output)
    finally:db.close()
