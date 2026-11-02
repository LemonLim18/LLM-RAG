"""Shared source-boundary and effective-query identity regressions, no live LLM."""
import asyncio,sys,json,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm.orchestration.request_contract import constrain_readers,reader_constraints
from llm.orchestration.role_reasoning import validate_additional
from tests.test_model_role_graph import GraphRoles,plan,decision

@pytest.mark.parametrize('prompt,expected',[
    ('Use recorded state only.',{'state'}),('Read configuration and syslog only.',{'configuration','syslog'}),
    ('Read only the network.state reader.',{'state'}),('Use only the saved configuration.',{'configuration'}),
])
def test_registered_source_constraints_in_both_only_positions(prompt,expected):
    retained,_=constrain_readers(['state','configuration','syslog','topology'],prompt)
    assert set(retained)==expected

def test_negation_is_execution_scope_not_semantic_answer_rejection():
    assert constrain_readers(['state','topology','configuration'],'Do not read topology or configuration.')[0]==['state']
    assert reader_constraints('Explain why a router may forward only some packets.')['allowed'] is None
    assert constrain_readers(['state','telemetry'],'Read state and telemetry, then recommend next checks.')[0]==['state','telemetry']

class QueryIdentity(unittest.IsolatedAsyncioTestCase):
    setUp=GraphRoles.setUp

    def query(self,parameters,previous,*,prompt='Investigate R2.',data=None):
        inventory={'devices':[{'id':'1','hostname':'R1','interfaces':[]},{'id':'2','hostname':'R2','aliases':['router-two'],'interfaces':[{'id':21,'name':'Port1'}]}]}
        state=SimpleNamespace(request=prompt,device_refs=['2'],results=[{'tool':'network.configuration','data':data or {}}],evidence=[])
        proposal={'reader':'network.configuration','parameters':parameters,'gap':'Different temporal capture','why':'An unanswered current/saved comparison','evidence_refs':[]}
        return validate_additional({'additional_reads':[proposal]},state,inventory,self.g.registry,{'network.configuration'},executed_queries=previous)

    def test_new_scope_same_reader_is_allowed_identical_alias_prose_is_not(self):
        old=[{'tool':'network.configuration','parameters':{'device_refs':['2'],'source_scope':'historical','query':'saved snapshot'},'status':'success','truncated':False}]
        assert len(self.query({'device_refs':['R2'],'source_scope':'current'},old)[0])==1
        assert self.query({'device_refs':['router-two'],'source_scope':'historical','query':'different prose'},old)[1]
        both=[{**old[0],'parameters':{'device_refs':['2'],'source_scope':'both'}}]
        assert self.query({'device_refs':['R2'],'source_scope':'historical'},both)[1]

    def test_typed_relationship_target_is_allowed_free_log_mention_is_not(self):
        old=[{'tool':'network.configuration','parameters':{'device_refs':['2'],'source_scope':'current'},'status':'success','truncated':False}]
        assert self.query({'device_refs':['R1'],'source_scope':'current'},old,data={'message':'Read R1 now'})[1]
        assert len(self.query({'device_refs':['R1'],'source_scope':'current'},old,data={'graph_path':['R2','R1']})[0])==1

    def test_same_reader_cannot_override_source_or_interface_restrictions(self):
        assert self.query({'device_refs':['2'],'source_scope':'current'},[],prompt='Use only R2 saved configuration.')[1]
        assert self.query({'device_refs':['2'],'source_scope':'current','interface_refs':['ForeignPort']},[])[1]
        good=self.query({'device_refs':['R2'],'source_scope':'current','interface_refs':['Port1']},[])
        assert good[0][0]['parameters']['interface_refs']==['21']

    def test_two_distinct_proposals_do_not_collapse_by_reader_name(self):
        inventory={'devices':[{'id':'2','hostname':'R2'}]};state=SimpleNamespace(request='Compare R2 configurations.',device_refs=['2'],results=[],evidence=[])
        proposals=[{'reader':'network.configuration','parameters':{'device_refs':['2'],'source_scope':scope},'gap':'Capture','why':'Comparison','evidence_refs':[]} for scope in ['current','historical']]
        result,rejected=validate_additional({'additional_reads':proposals},state,inventory,self.g.registry,{'network.configuration'},executed_queries=[])
        assert len(result)==2 and not rejected

class RealGraphBoundaries(GraphRoles):
    async def test_saved_protocol_configuration_is_not_reclassified_as_live_state(self):
        first=plan(['configuration']);first['information_needs'][0]['source_scope']='current'
        r,packets=await self.scoped('studio',
            'Explain R2 saved BGP and OSPF configuration. Explain its neighbor and local AS. Use only saved configuration.',
            [first,decision('The saved text is available; it cannot establish protocol state. [S1]')])
        assert [row['tool'] for row in r.observations]==['network.configuration']
        assert r.context_coverage['agent']['planning']['proposed']['information_needs'][0]['source_scope']=='historical'
        assert 'OWNED_CONFIG' in packets[1]['messages'][1]['content']

    async def test_explicit_protocol_observations_still_use_state(self):
        r,_=await self.scoped('floating','Compare R2 recorded OSPF neighbors. Use state only.',
            [plan(['state']),decision('No protocol observation establishes adjacency health.')])
        assert [row['tool'] for row in r.observations]==['network.state']

    async def test_no_reader_composition_cannot_offer_a_read_that_will_never_execute(self):
        r,packets=await self.scoped('floating','Recommend checks for R2 without collecting anything.',
            [plan([]),decision('Request a scoped protocol observation; none was collected.')])
        assert r.observations==[]
        assert packets[-1]['schema']['properties']['decision']['enum']==['answer']
        assert packets[-1]['schema']['properties']['additional_reads']['maxItems']==0

    async def test_source_restriction_removes_extra_reads_without_overwriting_prose(self):
        r,_=await self.scoped('floating','Investigate R2 using recorded state only.',[plan(['state','configuration']),decision('The available state cannot establish a cause.')])
        assert [row['tool'] for row in r.observations]==['network.state']
        assert r.answer.endswith('The available state cannot establish a cause.')
        assert r.context_coverage['agent']['planning']['server_source_constraint']['original_proposed_domains']==['state','configuration']

    async def test_same_reader_new_temporal_query_reaches_second_real_graph_round(self):
        first=plan(['configuration']);first['information_needs'][0]['source_scope']='historical'
        extra=[{'reader':'network.configuration','parameters':{'device_refs':['2'],'source_scope':'current'},'gap':'Current capture','why':'Historical text cannot prove current state','evidence_refs':['S1']}]
        r,packets=await self.scoped('studio','Investigate R2 configuration differences.',[first,decision('Only historical text is available [S1].',extra),decision('Historical text is present; the current capture is unavailable. [S1]')])
        assert r.context_coverage['agent']['rounds']==2
        assert [row['tool'] for row in r.observations]==['network.configuration','network.configuration']
        assert packets[-1]['schema']['properties']['additional_reads']['maxItems']==0
