"""Phase E boundary regressions. Mocked cases do not prove model quality."""
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm.gateway_routing import select_context
from llm.orchestration.model import RoutingModel
from llm.orchestration.synthesis import synthesize,check_candidate
from llm.gateway_models import Evidence


class IntelligenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_explicit_published_contract_uses_existing_reader_without_generation(self):
        inventory={'devices':[{'id':2,'hostname':'R2','interfaces':[]}]}
        for planning in ['0','1']:
            with self.subTest(planning=planning),patch.dict(os.environ,{'COGNISHIELD_AI_PLANNING':planning}):
                generate=AsyncMock(side_effect=AssertionError('Exact source selection needs no model'))
                route=await select_context("Explain the published OSPF operation requirements and compare R2's stored configuration. Do not generate anything.",None,'studio',None,[],[],inventory=inventory,generate_fn=generate)
                self.assertEqual(set(route.network_domains),{'knowledge','configuration'})
                self.assertEqual(route.device_refs,['R2']);self.assertEqual(route.intent,'explain')
                self.assertFalse(route.use_editor);self.assertFalse(route.use_attachments)
                generate.assert_not_awaited()

    async def test_topology_paraphrase_stays_in_read_path(self):
        inventory={'devices':[{'id':1,'hostname':'R1','interfaces':[]},{'id':2,'hostname':'R2','interfaces':[]}]}
        with patch.dict(os.environ,{'COGNISHIELD_AI_PLANNING':'1'}):
            route=await select_context('Describe the recorded topology between R1 and R2.',None,'floating',None,[],[],inventory=inventory)
        self.assertEqual(route.network_domains,['topology']);self.assertFalse(route.use_attachments)

    async def test_protocol_fact_plan_cannot_substitute_interface_inventory(self):
        from llm.orchestration.planning import propose
        inventory={'devices':[{'id':2,'hostname':'R2','interfaces':[]}]}
        with self.assertRaises(ValueError):
            await propose('Does R2 have a recorded BGP peer session?',None,'floating',None,[],[],inventory,
                AsyncMock(return_value=(json.dumps({'intent':'answer','information_needs':[{'domain':'inventory','question':'devices'}]}),'test')))
        from llm.gateway_network import route_network
        self.assertIn('state',route_network('Does R2 have a recorded BGP peer session?',inventory)[0])

    async def test_explicit_sources_cannot_be_replaced_by_a_valid_but_inadequate_plan(self):
        from llm.orchestration.planning import propose
        inventory={'devices':[{'id':2,'hostname':'R2','interfaces':[]}]}
        for prompt in ['Which recorded links touch R2?','Read CPU measurements for R2.','Show recorded alerts on R2.']:
            with self.subTest(prompt=prompt),self.assertRaises(ValueError):
                await propose(prompt,None,'floating',None,[],[],inventory,AsyncMock(return_value=(json.dumps({'intent':'answer','information_needs':[{'domain':'inventory','question':'records'}]}),'test')),read_only_request=True)

    async def test_natural_explicit_editor_effect_is_a_review_proposal_not_explanation(self):
        for prompt in ['Add a comment to the current code explaining the neighbor statement.','Correct the description in the open template.']:
            with self.subTest(prompt=prompt):
                route=await select_context(prompt,None,'studio',object(),[],[])
                self.assertEqual(route.intent,'edit');self.assertTrue(route.use_editor)

    async def test_repair_keeps_first_failure_and_checks_corrected_answer(self):
        context=[{'tool':'network.state','status':'success','data':{'records':[{'hostname':'R2','address':'192.0.2.2'}]}}]
        evidence=[Evidence(id='private-id',source='fixture',origin='stored')]
        model=type('Model',(),{'generate':AsyncMock(side_effect=[
            (json.dumps({'answer':'R2 has IP address 192.0.2.99. [S1]','sources':['S1']}),'test'),
            (json.dumps({'answer':'R2 has IP address 192.0.2.2. [S1]','sources':['S1']}),'test')])})()
        answer,report=await synthesize(model,'test','What address is recorded?',context,evidence,{},'fallback')
        self.assertIn('192.0.2.2',answer);self.assertNotIn('192.0.2.99',answer)
        self.assertEqual(report['status'],'repaired_literal_checks_passed')
        self.assertEqual(len(report['attempts']),2);self.assertTrue(report['attempts'][0]['errors'])
        self.assertEqual(model.generate.await_args_list[-1].kwargs['purpose'],'repair')

    async def test_two_bad_answers_do_not_become_a_verified_success(self):
        model=type('Model',(),{'generate':AsyncMock(return_value=(json.dumps({'answer':'The root cause is a bad cable.'}),'test'))})()
        answer,report=await synthesize(model,'test','Why?',[],[],{},'No decisive evidence is available.')
        self.assertEqual(answer,'No decisive evidence is available.')
        self.assertEqual(report['status'],'rejected_fallback');self.assertEqual(model.generate.await_count,2)

    def test_narrow_ospf_rule_guard_does_not_invert_negative_explanation(self):
        self.assertTrue(check_candidate('OSPF router IDs must be identical.',[],[],{}))
        self.assertFalse(check_candidate('OSPF router IDs must not be identical; each router needs a unique ID.',[],[],{}))

    def test_per_stage_limits_cannot_be_consumed_as_unbounded_loop(self):
        with patch.dict(os.environ,{'COGNISHIELD_AI_PLANNING':'1'}):model=RoutingModel()
        self.assertTrue(model.available('retrieval'));model.purposes['retrieval']=1
        self.assertFalse(model.available('retrieval'));self.assertTrue(model.available('synthesis'))
        self.assertFalse(model.available('shell'));model.calls=model.max_calls
        self.assertFalse(model.available('repair'))

    async def test_oversized_context_rejected_before_model_or_tool_call(self):
        with patch.dict(os.environ,{'COGNISHIELD_AI_PLANNING':'1'}):model=RoutingModel()
        from fastapi import HTTPException
        with self.assertRaises(HTTPException):await model.generate([{'role':'user','content':'x'*32001}])
        self.assertEqual(model.calls,0)

    def test_verified_protocol_fallback_includes_the_actual_state_and_peer_facts(self):
        from llm.gateway_findings import network_answer
        context=[{'tool':'network.state','status':'success','evidence_ids':['source'], 'data':{'records':[{
            'hostname':'R2','kind':'protocol_assessment','protocol':'BGP','observed_state':'Active','assessment':'strongly_supported',
            'configuration_differences':['neighbor remote AS differs from peer local AS'],'peer_parameters':[{'device_id':2,'local_as':65020,'remote_as':65030,'neighbor_address':'192.0.2.3'}]}]}}]
        answer=network_answer(context,[Evidence(id='source',source='fixture',origin='simulated')])
        for fact in ['Active','65020','65030','192.0.2.3','neighbor remote AS differs']:self.assertIn(fact,answer)
        self.assertNotIn('Established',answer)


if __name__=='__main__':unittest.main()
