"""State scope is enforced by the existing adapter AND authoritative reader."""
import asyncio,copy,json,sys
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi import HTTPException
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from db.manager import DatabaseManager
from llm.gateway_store import ensure_schema
from llm.gateway_services import registry_for
from llm.gateway_network import NetworkQuery,NetworkReader,network_context,scoped_interface_records
from llm.tools import ToolAuthorization
from local_providers.development import ScenarioManager

ROOT=Path(__file__).resolve().parents[2]

@pytest.fixture
def scoped_environment(tmp_path,monkeypatch):
 monkeypatch.setenv('COGNISHIELD_DEV_SIMULATION','1')
 db=DatabaseManager(str(tmp_path/'app.db'));db.initialize();ensure_schema(db)
 assert Path(db._db_path).resolve().is_relative_to(tmp_path.resolve())
 manager=ScenarioManager(tmp_path/'scenario.json');db._development_scenario=manager
 definition=json.loads((ROOT/'docs/evaluations/phase_g_claim_release_repair_v1.json').read_text(encoding='utf-8'))['fixtures']['CVR-02']
 manager.change('import',manager.snapshot()[1]['source_revision'],definition)
 try:yield db,manager
 finally:db.close()

@pytest.mark.parametrize('surface',['floating','studio'])
def test_registry_scopes_one_of_two_same_named_interfaces(scoped_environment,surface):
 db,manager=scoped_environment
 auth=ToolAuthorization('scoped-reader-owner','engineer',surface,'scope-conversation',frozenset({'network.state'}))
 result=asyncio.run(registry_for(db).invoke('network.state',{'device_refs':['703'],'interface_refs':['7031'],'record_kinds':['interface_state']},auth))
 assert result.status=='success'
 records=result.data['records'];assert len(records)==2 and result.data['total']==2
 assert {r['id'] for r in records}=={'port-7031','model-interface-7031'}
 assert all(r['device_id']==703 and r['interface_id']==7031 and r['interface']=='Ethernet9/3' for r in records)
 assert {r['source'] for r in records}=={'authored-synthetic-observer','declared_interface_observation'}
 assert all(r['prefix']=='172.30.44.1/30' and r['vrf']=='cobalt' for r in records)
 assert all(r['timestamp'] and r['admin_status']=='up' and r['oper_status']=='up' for r in records)
 assert result.evidence and all(e.origin=='simulated' for e in result.evidence)

@pytest.mark.parametrize('surface',['floating','studio'])
def test_context_adapter_sends_validated_port_to_actual_state_tool(scoped_environment,surface):
 db,_=scoped_environment;registry=registry_for(db)
 auth=ToolAuthorization('scoped-reader-owner','engineer',surface,'scope-conversation',frozenset({'network.state'}))
 with patch.object(registry,'invoke',wraps=registry.invoke) as invoke:
  results,_,_=asyncio.run(network_context(db,registry,auth,'Using recorded state only, show Meadow Ethernet9/3 administrative and operational state.',
   domains_override=['state'],device_refs_override=['703'],interface_refs_override=['7031']))
 assert invoke.await_count==1 and invoke.await_args.args[0]=='network.state'
 assert invoke.await_args.args[1]['interface_refs']==['7031']
 assert {r['interface_id'] for r in results[0]['data']['records']}=={7031}

@pytest.mark.parametrize('devices,interfaces',[
 (['703'],['999999']),(['701'],['7031']),(['703'],['7011']),(['703'],['Ethernet9/3']),(['703'],['']),(['missing-device'],['7031'])])
def test_invalid_unknown_or_wrong_owner_scope_does_not_widen(scoped_environment,devices,interfaces):
 db,_=scoped_environment
 result=NetworkReader(db).read('state',NetworkQuery(device_refs=devices,interface_refs=interfaces),None)
 assert result.status=='unavailable' and not result.data

def test_reader_permission_still_applies_to_scoped_state(scoped_environment):
 db,_=scoped_environment
 auth=ToolAuthorization('scoped-reader-owner','engineer','floating','scope-conversation',frozenset({'network.telemetry'}))
 with pytest.raises(HTTPException) as exc:
  asyncio.run(registry_for(db).invoke('network.state',{'device_refs':['703'],'interface_refs':['7031']},auth))
 assert exc.value.status_code==403

def test_exact_repeat_is_removed_but_independent_observations_and_conflicts_remain():
 row={'id':'observed-1','device_id':703,'interface_id':7031,'source':'observer','timestamp':'2026-10-29T01:00:00Z','oper_status':'up'}
 distinct=[{**row,'id':'observed-2'},{**row,'source':'second-observer'},{**row,'timestamp':'2026-10-29T01:01:00Z'},{**row,'oper_status':'down'}]
 result=scoped_interface_records([row,copy.deepcopy(row),*distinct,{'id':'other','interface_id':7011}],['7031'],relationships=True)
 assert result==[row,*distinct]

def test_typed_flow_relation_is_kept_without_slicing_other_endpoints():
 flow={'id':'flow-a','kind':'forwarding_assessment','assessment':{'forward':{'branches':[{'hops':[{'device_id':703,'interface_id':7031},{'device_id':702,'interface_id':7022}]}]}}}
 unrelated={'id':'unrelated','interface_id':7011,'message':'Mentions7031','notes':{'interface_id':7031}}
 assert scoped_interface_records([flow,unrelated],['7031'],relationships=True)==[flow]
 assert flow['assessment']['forward']['branches'][0]['hops'][1]['interface_id']==7022

def test_provider_repeat_does_not_become_extra_scoped_row(scoped_environment):
 db,manager=scoped_environment;s,meta=manager.snapshot();s=copy.deepcopy(s)
 original=next(r for r in s['records']['state'] if r['id']=='port-7031')
 s['records']['state'].append(copy.deepcopy(original))
 with patch.object(manager,'snapshot',return_value=(s,meta)):
  result=NetworkReader(db).read('state',NetworkQuery(device_refs=['703'],interface_refs=['7031'],record_kinds=['interface_state']),None)
 assert [r['id'] for r in result.data['records']].count('port-7031')==1
 assert len(result.data['records'])==2

def test_unscoped_and_unsupported_live_semantics_are_preserved(scoped_environment):
 db,_=scoped_environment;reader=NetworkReader(db)
 unscoped=reader.read('state',NetworkQuery(device_refs=['703'],record_kinds=['interface_state']),None)
 assert {r['interface_id'] for r in unscoped.data['records']}=={7030,7031,7032}
 assert reader.read('state',NetworkQuery(device_refs=['703'],interface_refs=['7031'],live=True),None).status=='unavailable'
 assert reader.read('configuration',NetworkQuery(device_refs=['703'],interface_refs=['7031']),None).status=='unavailable'

def test_factual_projection_identifies_distinct_sources(scoped_environment):
 from llm.gateway_findings import network_answer
 db,_=scoped_environment
 result=NetworkReader(db).read('state',NetworkQuery(device_refs=['703'],interface_refs=['7031'],record_kinds=['interface_state']),None)
 text=network_answer([{'tool':'network.state','status':result.status,'data':result.data,'evidence_ids':[e.id for e in result.evidence]}],result.evidence)
 assert 'Record / source' in text
 assert 'port-7031' in text and 'model-interface-7031' in text
 assert 'authored-synthetic-observer' in text and 'declared_interface_observation' in text
 assert 'Ethernet2/2' not in text and 'Loopback0' not in text

def test_direct_approved_role_plan_preserves_server_resolved_port():
 from tests.test_model_role_graph import GraphRoles,plan,decision
 from llm.gateway_services import inventory_snapshot
 async def check():
  harness=GraphRoles();harness.setUp()
  try:
   device=next(d for d in inventory_snapshot(harness.db)['devices'] if d['hostname']=='R2')
   interface=device['interfaces'][0]
   original=NetworkReader.read;seen=[]
   def observe(reader,domain,query,authorization):
    if domain=='state':seen.append(query.model_dump())
    return original(reader,domain,query,authorization)
   with patch.object(NetworkReader,'read',observe):
    for surface in ['floating','studio']:
     await harness.scoped(surface,f"Using state only, compare R2 {interface['name']} administrative and operational state.",
      [plan(['state']),decision('No current state observation is available; no state values inferred.')])
   assert len(seen)==2
   assert all(q['device_refs']==[str(device['id'])] and q['interface_refs']==[str(interface['id'])] for q in seen)
  finally:harness.doCleanups()
 asyncio.run(check())


@pytest.mark.parametrize('prefix',['Use state only','Use only state'])
def test_explicit_state_boundary_is_not_replaced_by_identity_attributes(prefix):
 from tests.test_model_role_graph import GraphRoles,plan,decision
 from llm.gateway_services import inventory_snapshot
 async def check():
  harness=GraphRoles();harness.setUp()
  try:
   device=next(d for d in inventory_snapshot(harness.db)['devices'] if d['hostname']=='R2')
   interface=device['interfaces'][0]
   prompt=f'{prefix} to compare R2 {interface["name"]} administrative and operational observations, including prefix and source. Do not read other sources.'
   for surface in ['floating','studio']:
    result,packets=await harness.scoped(surface,prompt,[plan(['state']),decision('The requested observation is unavailable; no state value is inferred.')])
    assert [r['tool'] for r in result.observations]==['network.state']
    assert len(packets)==2 and 'exclusive source restriction' not in result.answer
    denied,packets=await harness.scoped(surface,prompt,[plan(['state','configuration'])])
    assert not denied.observations and 'exclusive source restriction' in denied.answer
  finally:harness.doCleanups()
 asyncio.run(check())
