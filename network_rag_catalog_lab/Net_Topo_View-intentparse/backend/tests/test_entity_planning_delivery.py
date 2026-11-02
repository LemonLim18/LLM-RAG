"""The existing registered-name grammar reaches the existing role graph."""
import json,sys,unittest
from pathlib import Path
from unittest.mock import patch
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm.gateway_network import route_network
from tests.test_model_role_graph import GraphRoles,plan,decision

def test_ambiguous_alias_is_retained_for_canonical_clarification_not_chosen():
    inventory={'devices':[{'id':1,'hostname':'North','aliases':['shared-edge'],'management_ip':None},
        {'id':2,'hostname':'South','aliases':['shared-edge'],'management_ip':None},
        {'id':3,'hostname':'Transit','aliases':[],'management_ip':None}]}
    for prompt in ['Investigate shared-edge connectivity.','Investigate shared-edge-to-Transit connectivity.']:
        refs=route_network(prompt,inventory,expand_investigation=False)[1]['device_refs']
        assert 'shared-edge' in refs and 'North' not in refs and 'South' not in refs

class EntityRoleGraph(unittest.IsolatedAsyncioTestCase):
    setUp=GraphRoles.setUp
    scoped=GraphRoles.scoped

    async def test_joined_endpoints_preserve_original_obligations_through_planner_and_readers(self):
        for surface,chain in [('floating','R1-to-R2'),('studio','R2-to-R1')]:
            question='Investigate '+chain+' connectivity using recorded state and topology only. Explain both directional limits. Do not read other sources.'
            with patch.dict('os.environ',{'COGNISHIELD_AI_COMPLETENESS':'1'}):
                result,packets=await self.scoped(surface,question,[plan(['state','topology']),decision('The returned records do not establish end-to-end delivery. [S1]')])
            assert packets[0]['role']=='complex_planner'
            assert question in json.dumps(packets[0]['messages'])
            assert {r['tool'] for r in result.observations}=={'network.state','network.topology'}
            assert all(set(r['device_refs'])=={'1','2'} for r in result.observations)
            packet=json.loads(packets[1]['messages'][-1]['content'])
            assert packet['original_user_instruction']==question
            assert set(packet['planning_proposal_not_authority']['resolved_device_refs'])=={'1','2'}
            assert 'network.configuration' not in json.dumps([r['tool'] for r in result.observations])

    async def test_background_name_does_not_override_validated_planner_target(self):
        proposal=plan(['state'])
        question='R1 should not be read; investigate R2 using recorded state only. Do not read other sources.'
        result,packets=await self.scoped('floating',question,[proposal,decision('The returned state has no physical-connectivity proof. [S1]')])
        assert all(r['device_refs']==['2'] for r in result.observations)
