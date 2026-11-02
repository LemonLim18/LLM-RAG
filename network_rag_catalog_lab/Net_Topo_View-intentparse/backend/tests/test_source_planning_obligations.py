"""Focused source obligations with actual readers; model proposals are mocked."""
import json,sys,unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi import HTTPException
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm.gateway_network import explicit_configuration_scope,route_network
from llm.orchestration.planning import InformationNeed,source_queries
from llm.tools import ToolAuthorization
from llm.gateway_services import registry_for
from tests.test_model_role_graph import GraphRoles,plan,decision
from local_providers.development import ScenarioManager
from development.network_model import Flow,assess_flow
from types import SimpleNamespace
from llm.orchestration.investigation_support import post_draft
from llm.gateway_routing import SemanticRoute

ROOT=Path(__file__).resolve().parents[2]
SPEC=json.loads((ROOT/'docs/evaluations/phase_g_entity_delivery_v1.json').read_text(encoding='utf-8'))

@pytest.mark.parametrize('question,expected',[
 ('Compare running BGP values with an unapplied staged file.','both'),
 ('Read the staged configuration only.','historical'),
 ('Read current running configuration only, not the staged file.','current'),
 ('Show historical running snapshots and the current running configuration.','both'),
 ('Show only current configuration and its capture timestamp.','current'),
])
def test_configuration_operands(question,expected):
 assert explicit_configuration_scope(question)==expected

def test_distinct_same_family_temporal_needs_union_without_erasure():
 query=source_queries([InformationNeed(domain='configuration',question='Current commands',source_scope='current',source_categories=['running_configs']),
  InformationNeed(domain='configuration',question='Saved artifact',source_scope='historical',source_categories=['config_snapshots'])])['configuration']
 assert query=={'source_scope':'both','source_categories':['running_configs','config_snapshots']}

@pytest.mark.parametrize('question,expected',[
 ('R1 is background context. Investigate R2 using state only.',['R2']),
 ('Investigate R2 using state only; R1 is the background example.',['R2']),
 ('R1 supplied the earlier notes, but inspect R2 Gi0/0 state.',['R2']),
 ('R1 is background; investigate R2-to-R3 connectivity.',['R2','R3']),
 ('R1 is down. Inspect its interfaces.',['R1']),
 ('Compare R1 with R2 state.',['R1','R2']),
 ('R1 is background. Inspect R99 state.',['R99']),
])
def test_action_subjects_do_not_inherit_declarative_background(question,expected):
 inv={'devices':[{'id':i,'hostname':n,'aliases':[],'management_ip':None} for i,n in enumerate(['R1','R2','R3'],1)]}
 assert route_network(question,inv,expand_investigation=False)[1]['device_refs']==expected

def test_forwarding_output_retains_known_ingress_and_destination_relationships():
 s=SPEC['fixtures']['ED-04'];flow=Flow.model_validate(s['network']['flows'][0]);a=assess_flow(s,flow)
 for direction,transit_ids,destination in [('forward',[7421,8531],9641),('return',[8532,7422],6311)]:
  branch=a[direction]['branches'][0]
  assert branch['status']=='delivered' and 'failure_location' not in branch
  assert 'ingress' not in branch['hops'][0],'No fictitious ingress at the origin'
  assert [h['ingress']['interface_id'] for h in branch['hops'][1:]]==transit_ids
  assert all(h['ingress']['device_id']==h['device_id'] and h['ingress']['vrf']==h['vrf'] for h in branch['hops'][1:])
  assert branch['destination_ingress']['interface_id']==destination

def test_background_filter_uses_the_same_joined_endpoint_grammar():
 inv={'devices':[{'id':i,'hostname':name,'aliases':[],'management_ip':None} for i,name in enumerate(['Archive','Alder','Prism'],1)]}
 assert route_network('Archive supplied the old notes. Investigate Alder-to-Prism connectivity.',inv,expand_investigation=False)[1]['device_refs']==['Alder','Prism']

class SourceObligationGraph(unittest.IsolatedAsyncioTestCase):
 setUp=GraphRoles.setUp
 scoped=GraphRoles.scoped

 def scenario(self):
  manager=ScenarioManager(Path(self.folder.name)/'scenario.json')
  fixture=deepcopy(SPEC['fixtures']['ED-03'])
  fixture['source_statuses']={key:{'status':'AVAILABLE','captured_at':fixture['logical_time']} for key in ['running_configs','config_snapshots']}
  manager.change('import',manager.snapshot()[1]['source_revision'],fixture)
  self.db._development_scenario=manager

 async def test_staged_and_running_history_reach_real_reader_and_reasoner_both_surfaces(self):
  question=next(c['prompt'] for c in SPEC['cases'] if c['id']=='ED-03')
  question=question.replace('running BGP values','current running configuration BGP values')
  with patch.dict('os.environ',{'COGNISHIELD_DEV_SIMULATION':'1','COGNISHIELD_AI_COMPLETENESS':'0'}):
   self.scenario()
   for surface in ['floating','studio']:
    proposal=plan(['configuration','state','syslog']);proposal['information_needs'][0].update(source_scope='both',source_categories=['running_configs'])
    result,packets=await self.scoped(surface,question,[proposal,decision('The staged artifact does not establish application or an exact transition time. [S1]')])
    assert result.observations,result.context_coverage.get('planning_failure',{}).get('reason',result.answer)
    config=next(r for r in result.observations if r['tool']=='network.configuration')
    assert config['source_request']['source_scope']=='both'
    for record in ['ED03/running-0620','ED03/running-0840','ED03/unapplied-stage']:
     assert record in json.dumps(config) and record in packets[-1]['messages'][-1]['content']
    assert {r['tool'] for r in result.observations}=={'network.configuration','network.state','network.syslog'}

 async def test_invalid_policy_plan_is_controlled_422_and_never_reaches_reader(self):
  result,_=await self.scoped('floating','Investigate R2 using state only. Do not read other sources.',[
    {'intent':'explain','use_editor':True,'information_needs':[{'domain':'state','question':'state'}]}])
  assert result.status=='unavailable' and not result.observations
  assert result.context_coverage['planning_failure']['category']=='POLICY_REJECTED_PLAN'

 async def test_malformed_proposal_no_reader_no_reasoner(self):
  result,_=await self.scoped('studio','Investigate R2 using state only.',[{'intent':'nonexistent','information_needs':[]}])
  assert result.status=='unavailable' and not result.observations
  assert result.context_coverage['planning_failure']['category']=='SCHEMA_INVALID_PLAN'

 async def test_no_read_advice_survives_invalid_proposal_using_owned_context(self):
  result,_=await self.scoped('floating','Recommend two passive checks for R2; do not read or collect anything.',[
   {'intent':'nonexistent','information_needs':[]},decision('Recommend reviewing existing configuration and recorded link observations; neither is collected here.')])
  assert result.observations==[] and 'neither is collected' in result.answer

 async def test_current_only_does_not_expand_to_history(self):
  result,_=await self.scoped('floating','Investigate R2 using current configuration only.',[
   plan(['configuration']),decision('Current configuration was requested; unavailable current data does not establish history. [S1]')])
  row=next(r for r in result.observations if r['tool']=='network.configuration')
  assert row['source_request']['source_scope']=='current'

 async def test_source_prohibition_does_not_gain_configuration_obligation(self):
  result,_=await self.scoped('floating','Investigate R2 using state only. Do not read configuration or other sources.',[
   plan(['state']),decision('Only recorded state was inspected. [S1]')])
  assert {r['tool'] for r in result.observations}=={'network.state'}

 async def test_background_device_and_same_named_interface_bind_to_target_only(self):
  result,_=await self.scoped('studio','R1 supplied the older notes. Investigate R2 Gi0/0 using state only; do not read other sources.',[
   plan(['state']),decision('The scoped recorded state does not establish a physical cause. [S1]')])
  assert result.observations
  assert all(r['device_refs']==['2'] and r['reader_receipt']['parameters']['interface_refs']==['2'] for r in result.observations)

 async def test_omitted_literal_configuration_operand_is_reconciled_not_globally_expanded(self):
  result,_=await self.scoped('floating','Compare R2 running configuration with staged configuration. Read configuration and state only; do not read other sources.',[
   plan(['state']),decision('Available source records are limited; a staged artifact is not proof of activation. [S1]')])
  assert {r['tool'] for r in result.observations}=={'network.configuration','network.state'}
  assert next(r for r in result.observations if r['tool']=='network.configuration')['source_request']['source_scope']=='both'

 async def test_unavailable_saved_source_does_not_substitute_current_configuration(self):
  with patch.dict('os.environ',{'COGNISHIELD_DEV_SIMULATION':'1'}):
   self.scenario();manager=self.db._development_scenario;s,meta=manager.snapshot()
   s['records']['configuration']=[];s['records']['running_configuration']=[r for r in s['records']['running_configuration'] if r['current']]
   s['availability']['configuration']=False;s['source_statuses']['config_snapshots']['status']='UNAVAILABLE'
   manager.change('edit',meta['source_revision'],s)
   result=await registry_for(self.db).invoke('network.configuration',{'device_refs':['742'],'source_scope':'historical','source_categories':['config_snapshots']},
    ToolAuthorization('alice','engineer','floating',self.cid,frozenset({'network.configuration'})))
   assert result.status=='unavailable' and not result.data['records'] and result.data['source_available'] is False

 async def test_provider_failure_is_not_reclassified_as_invalid_plan(self):
  with patch('llm.orchestration.planning.propose',side_effect=HTTPException(503,'Provider unavailable')):
   result,_=await self.scoped('floating','Investigate R2 using recorded state.',[])
  assert result.status=='unavailable' and not result.observations
  assert 'planning_failure' not in result.context_coverage and 'Provider unavailable' in result.answer

 async def test_truncated_dependency_read_retains_original_invocation_filters_and_time(self):
  request='Investigate R2 using configuration and syslog only; do not read other sources.'
  original={'device_refs':['2'],'query':request,'source_scope':'historical','source_categories':[],
    'start':'2026-11-01T00:00:00Z','end':'2026-11-01T12:00:00Z','limit':30,'live':False}
  rows=[{'tool':'network.configuration','status':'success','data':{'records':[{'id':'running','kind':'running_configuration','device_id':2,'config_text':'hostname R2','change_event_ref':'change-record'}]}},
    {'tool':'network.syslog','status':'success','source_request':{'source_scope':'historical'},'data':{'records':[],'truncated':True,'source_available':True},
     'reader_receipt':{'invocation_id':'initial-log','tool':'network.syslog','parameters':original,'status':'success'}}]
  state=SimpleNamespace(request=request,results=rows,route=SemanticRoute(intent='explain',network_domains=['configuration','syslog']),investigation={},device_refs=['2'],evidence=[])
  from llm.gateway_services import inventory_snapshot
  with patch.dict('os.environ',{'COGNISHIELD_AI_COMPLETENESS':'1'}):
   review=post_draft(state,{'answer':'The referenced change is not established.','claims':[]},inventory_snapshot(self.db),self.g.registry,frozenset({'network.configuration','network.syslog'}),[])
  proposed=next(x for x in review['server_proposals'] if x['reader']=='network.syslog')['parameters']
  assert proposed=={**original,'limit':100}
