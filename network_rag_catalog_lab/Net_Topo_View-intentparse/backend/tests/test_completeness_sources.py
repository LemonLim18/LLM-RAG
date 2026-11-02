"""Source-derived frozen fixture conformance; both actual reader surfaces."""
import asyncio,json,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from db.manager import DatabaseManager
from llm.gateway_store import ensure_schema
from llm.gateway_services import registry_for,inventory_snapshot
from llm.tools import ToolAuthorization
from local_providers.development import ScenarioManager
from llm.orchestration.investigation_support import artifact_comparisons
ROOT=Path(__file__).resolve().parents[2];SPEC=json.loads((ROOT/'docs/evaluations/phase_g_completeness_first_v1.json').read_text())

@pytest.mark.parametrize('case',SPEC['cases'],ids=lambda c:c['id'])
def test_sources_and_frozen_expectations(case,tmp_path,monkeypatch):
    monkeypatch.setenv('COGNISHIELD_DEV_SIMULATION','1')
    db=DatabaseManager(str(tmp_path/'app.db'));db.initialize();ensure_schema(db)
    assert Path(db._db_path).resolve().is_relative_to(tmp_path.resolve())
    m=ScenarioManager(tmp_path/'scenario.json');db._development_scenario=m
    m.change('import',m.snapshot()[1]['source_revision'],SPEC['fixtures'][case['scenario']]);registry=registry_for(db);outputs=[]
    try:
        for surface in ['floating','studio']:
            tools=case['required_tools'] or ['network.configuration']
            auth=ToolAuthorization('source-oracle-owner','engineer',surface,'source-'+surface,frozenset(set(tools)|{'network.syslog'}));results=[]
            for tool in tools:
                args={'device_refs':[str(d['id']) for d in SPEC['fixtures'][case['scenario']]['devices']]}
                if tool=='inventory.read':args={}
                if tool in {'network.configuration','network.topology'}:args['source_scope']='both'
                if tool=='network.syslog':args['limit']=8
                r=asyncio.run(registry.invoke(tool,args,auth));data=r.data or {};results.append({'tool':tool,'status':r.status,'data':data})
                if tool=='network.state' and case.get('independent_oracle'):
                    a=next(x['assessment'] for x in data['records'] if x['kind']=='forwarding_assessment')
                    assert all(a[d]['status']==v for d,v in case['independent_oracle'].items())
                if case['id']=='CF-01' and tool=='network.syslog':
                    assert data['truncated'] and 'optical-order-212' not in str(data['records'])
                    more=asyncio.run(registry.invoke(tool,{**args,'source_categories':['syslog'],'limit':100},auth))
                    assert 'optical-order-212' in str(more.data['records']) and 'receive optical path' in str(more.data['records'])
                if case['id']=='CF-06' and tool=='network.telemetry':assert all(str(v) in str(data) for v in [3,120,'loss-sample-216'])
                if case['id'] in {'CF-07','MN-03'} and tool=='network.syslog':assert data['source_available'] is False
            if case['id']=='CF-05':
                pairs=artifact_comparisons(results,inventory_snapshot(db))['comparisons'];p=next(x for x in pairs if x['before']['id']=='run-prechange-215' and x['after']['id']=='current-702')
                assert p['temporal_support']=='RUNNING_OBSERVATION_INTERVAL' and 'applied-change-215' in p['related_recorded_event_ids']
            outputs.append(results)
        assert outputs[0]==outputs[1]
    finally:db.close()
