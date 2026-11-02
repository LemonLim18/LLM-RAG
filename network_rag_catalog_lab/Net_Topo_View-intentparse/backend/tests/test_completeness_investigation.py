"""Completeness controls and typed evidence compatibility, no live inference."""
import asyncio,json,sys,time
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm.gateway_models import Evidence,ToolResult
from llm.gateway_routing import SemanticRoute
from llm.model_roles import consent_manifest,investigation_profile
from llm.orchestration.investigation_support import *
from llm.orchestration.role_reasoning import query_identity,query_covered
from tests.test_model_role_graph import GraphRoles,plan,decision

INVENTORY={'devices':[{'id':1,'hostname':'North','vendor':'cisco_xe','interfaces':[{'id':11,'device_id':1,'name':'Ethernet1','prefix':'10.0.0.1/30','vrf':'red'}]},
    {'id':2,'hostname':'South','vendor':'juniper','interfaces':[{'id':21,'device_id':2,'name':'Ethernet1','prefix':'10.0.0.2/30','vrf':'red'}]}],
    'links':[{'id':1,'src_device_id':1,'src_interface_id':11,'dst_device_id':2,'dst_interface_id':21}]}

def row(tool='network.state',records=None,**data):return {'tool':tool,'status':'success','evidence_ids':['receipt'],'data':{'records':records or [],**data}}

def record(id='port',**kw):return {'id':id,'kind':'interface_state','device_id':1,'interface_id':11,'oper_status':'down','admin_status':'up','prefix':'10.0.0.1/30','vrf':'red',**kw}

def claim(category='interface_oper_status',value='down',**kw):
    return {'statement':'Source-owned statement, phrased freely.','category':category,'value':value,'device_id':'1','interface_id':'11','record_refs':['port'],**kw}

def check(c,records=None,tool='network.state'):
    return compatible_claims({'answer':c['statement'],'claims':[c]},[row(tool,records or [record()])],INVENTORY)['claims'][0]

def test_profile_default_off_and_consent_changes(monkeypatch):
    monkeypatch.delenv('COGNISHIELD_AI_COMPLETENESS',raising=False);old=consent_manifest();assert not investigation_profile()['enabled']
    monkeypatch.setenv('COGNISHIELD_AI_COMPLETENESS','1');p=investigation_profile()
    assert p['seconds']==360 and p['max_readers']==24 and p['max_role_calls']==5 and consent_manifest()!=old
    monkeypatch.setenv('COGNISHIELD_AI_INVESTIGATION_SECONDS','900')
    with pytest.raises(Exception):investigation_profile()

@pytest.mark.parametrize('prompt,proposed,expected',[
    ('Find why North cannot communicate with South.',{},'comprehensive'),
    ('Explain the unexpected failure.',{'investigation_breadth':'comprehensive'},'comprehensive'),
    ('Show North interface state.',{'investigation_breadth':'targeted','desired_response':'direct'},'targeted'),
    ('Investigate North using state only. Do not read configuration.',{},'restricted'),
    ('Without retrieving anything, recommend checks for North.',{},'advisory')])
def test_breadth_uses_original_restrictions(prompt,proposed,expected):assert breadth(prompt,{'proposed':proposed})==expected

def test_network_map_preserves_planned_vs_observed_and_both_owners():
    sources=[{'tool':'inventory.read','status':'success','data':INVENTORY},row(records=[record()])]
    m=network_map(INVENTORY,sources,['1','2'],True)
    assert m['detailed'][0]['interfaces'][0]['prefix']=='10.0.0.1/30'
    assert m['detailed'][1]['interfaces'][0]['prefix']=='10.0.0.2/30'
    assert m['documented_links'][0]['class']=='documented_planned_not_operational'
    assert m['source_observations'][0]['oper_status']=='down'
    assert not network_map(INVENTORY,[sources[1]],['1'])['detailed']

@pytest.mark.parametrize('category,value,kw,status',[
    ('interface_oper_status','down',{},'SUPPORTED_TYPED_OPERAND'),
    ('interface_oper_status','up',{},'CONTRADICTED_VALUE'),
    ('interface_oper_status','down',{'device_id':'2'},'CONTRADICTED_IDENTITY'),
    ('ownership','10.0.0.1/30',{'field':'prefix'},'SUPPORTED_TYPED_OPERAND'),
    ('ownership','10.0.0.2/30',{'field':'prefix'},'CONTRADICTED_VALUE'),
    ('ownership','10.0.0.1/30',{'field':'prefix','vrf':'blue'},'CONTRADICTED_IDENTITY'),
])
def test_typed_relationships_not_prose_wording(category,value,kw,status):assert check(claim(category,value,**kw))['status']==status

def test_configuration_no_shutdown_and_oper_down_are_complementary():
    config=record('config',kind='running_configuration',config_text='interface Ethernet1\n no shutdown\n')
    a=check(claim('configured_command','no shutdown',record_refs=['config']),[config],'network.configuration')
    b=check(claim(),[record()]);assert a['status']==b['status']=='SUPPORTED_TYPED_OPERAND'
    assert check(claim(record_refs=['config']),[config],'network.configuration')['status']=='INCOMPATIBLE_EVIDENCE'

def test_measured_loss_never_inferred_from_branch_count():
    modeled=record('flow',kind='forwarding_assessment',derived=True,assessment={'forward':{'status':'partial'}})
    assert check(claim('measured_loss_percent',50,record_refs=['flow']),[modeled])['status']=='INCOMPATIBLE_EVIDENCE'
    measured=record('counter',kind='interface_counters',lost_packets=5,sent_packets=200)
    assert check(claim('measured_loss_percent',2.5,record_refs=['counter']),[measured],'network.telemetry')['status']=='SUPPORTED_TYPED_OPERAND'

def test_route_presence_does_not_establish_protocol_health():
    route=record('routes',kind='routing_table',routes=[{'prefix':'0.0.0.0/0'}])
    assert check(claim('ospf_state','Full',record_refs=['routes']),[route])['status']=='INSUFFICIENT_SUPPORT'
    assert check(claim('bgp_state','Established',record_refs=['routes']),[route])['status']=='INSUFFICIENT_SUPPORT'

def test_saved_and_running_comparisons_keep_identity_and_line_context():
    a=record('saved',kind='configuration',current=False,timestamp='2026-10-27T01:00:00Z',config_text='interface Ethernet1\n description A\n shutdown\n')
    b=record('running',kind='running_configuration',current=True,timestamp='2026-10-27T02:00:00Z',config_text='interface Ethernet1\n description B\n no shutdown\n')
    other=record('other',device_id=2,kind='running_configuration',config_text='no shutdown')
    c=artifact_comparisons([row('network.configuration',[a,b,other])],INVENTORY)['comparisons']
    assert len(c)==1 and c[0]['temporal_support']=='ARTIFACT_DIFFERENCE_ONLY'
    assert c[0]['changes'][0]['before'][0]['context']=='interface Ethernet1'
    assert check(claim('configuration_change_time','2026-10-27T01:30:00Z',record_refs=['saved']),[a],'network.configuration')['status']=='INCOMPATIBLE_EVIDENCE'
    a['kind']='running_configuration'
    c=artifact_comparisons([row('network.configuration',[a,b])],INVENTORY)['comparisons']
    assert c[0]['temporal_support']=='RUNNING_OBSERVATION_INTERVAL'

def test_junos_set_diff_and_verified_change_event_are_not_activation_guesses():
    a=record('a',device_id=2,kind='configuration',timestamp='2026-10-27T01:00:00Z',config_text='set interfaces Ethernet1 description old')
    b=record('b',device_id=2,kind='running_configuration',timestamp='2026-10-27T02:00:00Z',config_text='set interfaces Ethernet1 description new',change_event_ref='change-1')
    event=record('change-1',device_id=2,kind='configuration_change',timestamp='2026-10-27T01:45:00Z',applied=True,verification_status='verified')
    c=artifact_comparisons([row('network.configuration',[a,b]),row('network.syslog',[event])],INVENTORY)['comparisons'][0]
    assert c['related_recorded_event_ids']==['change-1'] and c['vendor']=='juniper'
    assert c['changes'][0]['after'][0]['context'].startswith('set interfaces')
    assert check(claim('configuration_change_time','2026-10-27T01:45:00Z',device_id='2',interface_id=None,record_refs=['change-1']),[event],'network.syslog')['status']=='SUPPORTED_TYPED_OPERAND'

def test_conflicting_operational_records_remain_conflicting():
    assert check(claim(),[record(),record(oper_status='up')])['status']=='CONFLICTING_EVIDENCE'

def test_auto_broad_query_covers_category_subset_without_re_read():
    old=query_identity('network.syslog',{'device_refs':['1'],'source_scope':'auto','source_categories':[]},INVENTORY)
    new=query_identity('network.syslog',{'device_refs':['1'],'source_scope':'both','source_categories':['syslog']},INVENTORY)
    assert query_covered('network.syslog',new,old)

class CompletenessGraph(GraphRoles):
    async def run_complete(self,prompt,outputs,surface='floating'):
        with patch.dict('os.environ',{'COGNISHIELD_AI_COMPLETENESS':'1'}):return await self.scoped(surface,prompt,outputs)

    async def test_broad_source_coverage_recovers_incomplete_model_plan(self):
        r,packets=await self.run_complete('Investigate why R2 cannot communicate. Find the cause.',[plan(['state']),decision('Recorded state is limited; no physical cause is certified.')])
        actual={row['tool'] for row in r.observations}
        assert set(READERS[d] for d in OPERATIONAL)<=actual
        planned=r.context_coverage['agent']['planning']['investigation']['source_coverage_plan']
        assert any(p['selected_by']=='server_broad_coverage' for p in planned)
        p=json.loads(packets[1]['messages'][1]['content']);assert p['investigation_context']['network']['inventory_authorized_read']
        assert p['investigation_context']['claim_source_compatibility']

    async def test_explicit_restriction_and_advice_remain_hard_boundaries(self):
        for prompt,domains in [('Investigate R2 using state only. Do not read configuration.',['state']),('Recommend checks for R2; do not collect anything.',[])]:
            r,_=await self.run_complete(prompt,[plan(['state','configuration']),decision('Scoped qualified interpretation.')])
            assert [row['tool'] for row in r.observations]==['network.'+d for d in domains]

    async def test_server_follows_actual_dependency_after_model_answer(self):
        async def config(params,auth):
            records=[] if params.source_categories==['config_changes'] else [{'id':'capture','kind':'running_configuration','device_id':2,'config_text':'hostname R2','change_event_ref':'work-abc'}]
            return ToolResult(status='success',data={'records':records,'source_available':True},evidence=[Evidence(id=__import__('uuid').uuid4().hex,source='controlled-fixture',origin='simulated')])
        async def logs(params,auth):
            return ToolResult(status='success',data={'records':[{'id':'work-abc','kind':'syslog_event','device_id':2,'message':'Recorded maintenance inspection, no executed remediation.'}],'source_available':True},evidence=[Evidence(id=__import__('uuid').uuid4().hex,source='controlled-fixture',origin='simulated')])
        self.g.registry._tools['network.configuration']['fn']=config;self.g.registry._tools['network.syslog']['fn']=logs
        first=plan(['configuration']);first.update(investigation_breadth='targeted',desired_response='explanation')
        r,p=await self.run_complete('Explain R2 current configuration and its recorded reference.',[first,decision('A reference is present; its intent is not established. [S1]'),decision('The new event records maintenance inspection, not completed remediation. [S1]')],'studio')
        assert len(p)==3 and any(row['tool']=='network.syslog' for row in r.observations)
        assert 'Recorded maintenance inspection' in p[-1]['messages'][1]['content']
        events=r.context_coverage['agent']['investigation']['drafts']
        assert events[0]['initiator']=='server_post_draft' and events[0]['validated_queries']
        assert r.answer.endswith('The new event records maintenance inspection, not completed remediation. [S1]')


def test_without_preface_does_not_erase_positive_main_read():
    from llm.orchestration.request_contract import reader_constraints,request_action
    assert request_action('Without reading configuration, show recorded state.')=='retrieve'
    policy=reader_constraints('Without reading configuration, show recorded state.')
    assert 'configuration' in policy['denied'] and 'state' not in policy['denied']


def test_consented_profile_budgets_share_one_clock(monkeypatch):
    async def run():
        from llm.gemini_provider import HybridRequest
        from llm.model_roles import InferenceResult
        from unittest.mock import AsyncMock
        monkeypatch.setenv('COGNISHIELD_AI_COMPLETENESS','1')
        scope=HybridRequest(time.monotonic());scope.assert_current_roles=lambda:None;scope.max_remote_calls=5
        call=AsyncMock(return_value=InferenceResult('{}','test-google-model','google'))
        with patch('llm.model_roles.infer',call):
            await scope.generate_role('complex_planner',[],False)
            assert 88<call.call_args.args[1].deadline-time.monotonic()<=90
            assert 350<scope.remaining()<=360
            for _ in range(4):await scope.generate_role('evidence_reasoner',[],False)
            with pytest.raises(Exception) as e:await scope.generate_role('evidence_reasoner',[],False)
            assert getattr(e.value,'provider_category',None)=='ROLE_CALL_LIMIT' and call.await_count==5
    asyncio.run(run())

def test_typed_aliases_and_ip_without_mask_do_not_reject_correct_meaning():
    assert check(claim('ownership','10.0.0.1',device_id='North',interface_id='Ethernet1',field='ip_address'))['status']=='SUPPORTED_TYPED_OPERAND'


def test_query_failure_is_distinct_from_zero_match_or_source_unavailable():
    p=[{'reader':'network.syslog','status':'CAPABILITY_READY_SOURCE_UNQUERIED'}]
    assert source_coverage(p,[row('network.syslog',[])])[0]['status']=='QUERIED_ZERO_MATCHES'
    assert source_coverage(p,[row('network.syslog',[],source_available=False)])[0]['status']=='SOURCE_UNAVAILABLE'
    receipt={'invocation_id':'failed-read-1','tool':'network.syslog','parameters':{},
             'source_revisions':[],'invocation_status':'failed'}
    actual={**row('network.syslog',[]),'status':'unavailable','reader_receipt':receipt}
    assert source_coverage(p,[actual],[receipt])[0]['status']=='QUERY_FAILED'
    # An unbound historical zero-result read cannot inherit another failure.
    assert source_coverage(p,[row('network.syslog',[])],[receipt])[0]['status']=='QUERIED_ZERO_MATCHES'


def test_synthetic_values_do_not_certify_physical_claims():
    assert check(claim(scope='physical'))['status']=='INCOMPATIBLE_PROVENANCE'


def test_legacy_category_inference_is_structural_not_free_text():
    from development.source_registry import recorded_category
    assert recorded_category({'kind':'syslog_event','values':{}},'network.syslog')=='syslog'
    assert recorded_category({'kind':'unknown','values':{'message':'syslog_event'}},'network.syslog') is None
    assert recorded_category({'kind':'syslog_event','values':{'source_category':'custom'}},'network.syslog')=='custom'
    assert recorded_category({'kind':'observed_link','current':False,'values':{}},'network.topology')=='topology_history'
    assert recorded_category({'kind':'observed_link','values':{}},'network.topology') is None


def test_history_order_uses_instants_not_timestamp_strings():
    a=record('early',kind='running_configuration',timestamp='2026-10-27T09:00:00+08:00',config_text='no shutdown')
    b=record('late',kind='running_configuration',timestamp='2026-10-27T02:00:00Z',config_text='shutdown')
    p=artifact_comparisons([row('network.configuration',[b,a])],INVENTORY)['comparisons'][0]
    assert p['before']['id']=='early' and p['temporal_support']=='RUNNING_OBSERVATION_INTERVAL'
    a.pop('timestamp')
    p=artifact_comparisons([row('network.configuration',[b,a])],INVENTORY)['comparisons'][0]
    assert p['temporal_support']=='UNORDERED_RUNNING_CAPTURES'


def test_correct_claim_paraphrase_is_not_rejected_for_nonliteral_wording():
    c=claim();d={'answer':'A differently worded correct down-state explanation.','claims':[c]}
    result=compatible_claims(d,[row(records=[record()])],INVENTORY)
    assert result['claims'][0]['status']=='SUPPORTED_TYPED_OPERAND' and not result['conflicts']
    assert not result['claims'][0]['literal_span']

def test_missing_optional_vrf_qualifier_is_not_a_definitive_identity_conflict():
    r=record();r.pop('vrf')
    assert check(claim(vrf='default'),[r])['status']=='SUPPORTED_TYPED_OPERAND'


class KnowledgeLimit(GraphRoles):
    async def test_registered_limit_is_honored_without_rebuilding_retrieval(self):
        refs=[Evidence(id='doc'+str(i),source='published:test',origin='stored') for i in range(3)]
        docs=[{'evidence_id':r.id,'source':'published:test','content':'Original document '+str(i)} for i,r in enumerate(refs)]
        from llm.gateway_network import NetworkReader,NetworkQuery
        from llm.tools import ToolAuthorization
        auth=ToolAuthorization('alice','engineer','floating',self.cid,frozenset({'knowledge.search'}))
        with patch('llm.gateway_knowledge.documentation_context',return_value=(docs,refs)):
            r=NetworkReader(self.db).read('knowledge',NetworkQuery(device_refs=['R2'],query='Published requirements',limit=1),auth)
        assert len(r.data)==1 and [e.id for e in r.evidence]==['doc0']
        assert r.data[0]['content']=='Original document 0' and r.data[0]['retrieval_coverage']['truncated']


def test_list_based_knowledge_coverage_is_not_unavailable():
    p=[{'reader':'knowledge.search','status':'CAPABILITY_READY_SOURCE_UNQUERIED'}]
    r=[{'tool':'knowledge.search','status':'success','data':[{'content':'Returned','retrieval_coverage':{'truncated':True}}]}]
    assert source_coverage(p,r)[0]['status']=='PARTIALLY_RETRIEVED'
    r[0]['data']=[]
    assert source_coverage(p,r)[0]['status']=='QUERIED_ZERO_MATCHES'

def test_model_adapter_uses_consented_call_limits_not_old_synthesis_two(monkeypatch):
    from llm.orchestration.model import RoutingModel
    monkeypatch.setenv('COGNISHIELD_AI_HYBRID','1')
    scope=SimpleNamespace(multi_model=True,investigation_profile={'enabled':True,'max_role_calls':5})
    with patch('llm.gemini_provider.current_hybrid_scope',return_value=scope):model=RoutingModel()
    model.calls=3;model.purposes={'routing':1,'synthesis':2}
    assert model.available('synthesis') and model.max_calls==5 and model.stage_limits['synthesis']==4


def test_declared_field_is_not_replaced_by_category_default():
    assert check(claim(value='10.0.0.1/30',field='prefix'))['status']=='SUPPORTED_TYPED_OPERAND'
    assert check(claim(value='10.0.0.2/30',field='prefix'))['status']=='CONTRADICTED_VALUE'
    assert check(claim(value='up',field='oper_status'))['status']=='CONTRADICTED_VALUE'


def test_inventory_receipt_binding_stays_source_owned_and_port_scoped():
    c=claim('ownership','10.0.0.2/30',device_id='South',interface_id='Ethernet1',field='prefix',record_refs=['inventory-receipt'])
    sources=[{'tool':'inventory.read','evidence_ids':['inventory-receipt'],'data':INVENTORY,'status':'success'}]
    def checked(value):return compatible_claims({'answer':'Unverified prose.','claims':[value]},sources,INVENTORY)['claims'][0]['status']
    assert checked(c)=='SUPPORTED_TYPED_OPERAND'
    assert checked({**c,'value':'10.0.0.1/30'})=='CONTRADICTED_VALUE'
    # A receipt lacking the named port does not prove that port cannot exist.
    assert checked({**c,'interface_id':'unrecorded'})=='UNKNOWN_BINDING_SCOPE'
    assert compatible_claims({'claims':[c]},[],INVENTORY)['claims'][0]['status']=='INSUFFICIENT_SUPPORT'


def test_flow_failed_hop_binding_uses_directional_branch_not_origin_owner():
    flow=record('flow',kind='forwarding_assessment',device_id=1,interface_id=None,derived=True,assessment={
        'forward':{'status':'failed','scope':{'source_device_id':1,'vrf':'red'},'branches':[{'status':'failed','failure_location':{'device_id':2,'interface_id':21}}]},
        'return':{'status':'delivered','scope':{'source_device_id':2,'vrf':'red'},'branches':[{'status':'delivered'}]}})
    c=claim('simulated_forwarding','failed',device_id='South',interface_id='Ethernet1',direction='forward',vrf='red',scope='modeled',record_refs=['flow'])
    assert check(c,[flow])['status']=='SUPPORTED_TYPED_OPERAND'
    assert check({**c,'device_id':'1','interface_id':'11'},[flow])['status']=='CONTRADICTED_IDENTITY'
    assert check({**c,'direction':'return'},[flow])['status']=='CONTRADICTED_IDENTITY'
    assert check({**c,'value':'delivered'},[flow])['status']=='CONTRADICTED_VALUE'
    assert check({**c,'device_id':'1','interface_id':None},[flow])['status']=='SUPPORTED_TYPED_OPERAND'
    assert check({**c,'scope':'physical'},[flow])['status']=='INCOMPATIBLE_PROVENANCE'


class FamilyRestriction(GraphRoles):
    async def test_reader_family_permission_does_not_filter_subtypes(self):
        with patch.dict('os.environ',{'COGNISHIELD_AI_COMPLETENESS':'1'}):
            result,packets=await self.scoped('floating','Investigate R2. Read only state and telemetry. Explain the recorded counters.',[plan(['state','telemetry']),decision('No physical measurements inferred.')])
        assert {r['tool'] for r in result.observations}=={'network.state','network.telemetry'}
        packet=json.loads(packets[-1]['messages'][1]['content'])
        query=next(q for q in packet['retrieval_boundary']['executed_queries'] if q['tool']=='network.telemetry')
        assert not query['parameters'].get('source_categories')
