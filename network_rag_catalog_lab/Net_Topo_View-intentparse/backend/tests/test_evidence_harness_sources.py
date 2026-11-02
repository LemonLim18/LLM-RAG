"""Frozen operands through real authorized readers on both surfaces; no cloud."""
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
SPEC=json.loads((ROOT/'docs/evaluations/phase_g_evidence_harness_v2.json').read_text())

@pytest.mark.parametrize('case',SPEC['cases'],ids=lambda c:c['id'])
def test_frozen_operands_both_surfaces(case,tmp_path,monkeypatch):
    monkeypatch.setenv('COGNISHIELD_DEV_SIMULATION','1')
    db=DatabaseManager(str(tmp_path/'app.db'));db.initialize();ensure_schema(db)
    assert Path(db._db_path).resolve().is_relative_to(tmp_path.resolve())
    manager=ScenarioManager(tmp_path/'scenario.json');db._development_scenario=manager
    manager.change('import',manager.snapshot()[1]['source_revision'],SPEC['fixtures'][case['scenario']])
    registry=registry_for(db);surfaces=[]
    try:
        for surface in ['floating','studio']:
            tools=case['required_tools'] or ['network.configuration']
            auth=ToolAuthorization('harness-fixture-owner','engineer',surface,'fixture-'+surface,frozenset(tools))
            results=[]
            for tool in tools:
                args={'device_refs':['Harbor','Transit','Meadow']}
                if tool=='network.configuration':args['source_scope']='both'
                if tool=='network.topology':args['source_scope']='both'
                r=asyncio.run(registry.invoke(tool,args,auth));results.append(r.data)
                if tool=='network.state' and case.get('independent_oracle'):
                    flows={x['flow']['id']:x['assessment'] for x in r.data['records'] if x['kind']=='forwarding_assessment'}
                    for ref,directions in case['independent_oracle'].items():
                        assert all(flows[ref][d]['status']==v for d,v in directions.items())
                if tool=='network.configuration' and case['id']=='EH-03':
                    assert all(v in str(r.data) for v in ['vrf forwarding blue','vrf forwarding green','10.71.2.1/30'])
                if tool=='network.syslog' and case['id']=='EH-03':assert r.data['source_available'] is False
                if tool=='network.syslog' and case['id']=='EH-05':assert 'inspection-ticket-144' in str(r.data) and 'no completed repair' in str(r.data)
                if tool=='network.topology':assert 'neighbor-observation-139' in str(r.data)
            surfaces.append(results)
        assert surfaces[0]==surfaces[1]
        assert 'expected_claims' not in json.dumps(surfaces)
    finally:db.close()
