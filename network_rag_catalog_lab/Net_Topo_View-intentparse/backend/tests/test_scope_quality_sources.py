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

ROOT=Path(__file__).resolve().parents[2]

@pytest.mark.parametrize('surface',['floating','studio'])
def test_independent_temporal_facts_and_event_have_distinct_authority(tmp_path,monkeypatch,surface):
 monkeypatch.setenv('COGNISHIELD_DEV_SIMULATION','1')
 db=DatabaseManager(str(tmp_path/'app.db'));db.initialize();ensure_schema(db)
 assert Path(db._db_path).resolve().is_relative_to(tmp_path.resolve())
 try:
  spec=json.loads((ROOT/'docs/evaluations/phase_g_scope_quality_v1.json').read_text(encoding='utf-8'))
  m=ScenarioManager(tmp_path/'scenario.json');db._development_scenario=m
  m.change('import',m.snapshot()[1]['source_revision'],next(iter(spec['fixtures'].values())))
  registry=registry_for(db);auth=ToolAuthorization('source-oracle','engineer',surface,'source-proof',frozenset({'network.configuration','network.state','network.syslog','network.telemetry'}))
  rows=[]
  for tool,args in [('network.configuration',{'source_scope':'both'}),('network.state',{'source_scope':'both','interface_refs':['8122'],'record_kinds':['interface_state']}),('network.syslog',{}),('network.telemetry',{'interface_refs':['8122']})]:
   result=asyncio.run(registry.invoke(tool,{'device_refs':['812'],**args},auth));assert result.status=='success'
   rows.append({'tool':tool,'data':result.data,'status':result.status})
  state=rows[1]['data']['records']
  assert {(r['timestamp'],r['oper_status']) for r in state}=={('2026-10-29T03:50:00Z','up'),('2026-10-29T04:50:00Z','down')}
  event=rows[2]['data']['records'][0];assert event['timestamp']=='2026-10-29T04:20:00Z' and event['applied'] and event['verification_status']=='verified'
  assert event['kind']=='configuration_change' and 'oper_status' not in event
  pairs=artifact_comparisons(rows,inventory_snapshot(db))['comparisons']
  running=[p for p in pairs if p['comparison_kind']=='RUNNING_HISTORY']
  assert {(p['before']['id'],p['after']['id']) for p in running}=={('spruce-running-a','spruce-running-c'),('spruce-running-c','spruce-running-now')}
  assert any('mtu 9000' in str(p['changes']) for p in running)
  assert all('spruce-staged-b' not in str([p['before'],p['after']]) for p in running)
  assert any('spruce-staged-b' in str([p['before'],p['after']]) and p['temporal_support']=='ARTIFACT_DIFFERENCE_ONLY' for p in pairs)
  assert all(p['device_id']=='812' for p in pairs)
  counter=rows[3]['data']['records'][0];assert counter['rx_discards']==42 and counter['rx_errors']==0 and counter['interface_id']==8122
 finally:db.close()
