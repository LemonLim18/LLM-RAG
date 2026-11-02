"""Real gateway/graph/readers; synthetic inference is mocked explicitly."""
import asyncio,json,sys,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock,patch
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi import HTTPException
from tests import test_b1_agent as fixtures
from llm.gateway_models import TurnRequest
from llm.gemini_provider import HybridRequest,hybrid_context,approve_hybrid_request
from llm.model_roles import InferenceResult
from llm.orchestration.role_reasoning import validate_additional

def plan(domains):
    return {'intent':'explain','information_needs':[{'domain':d,'question':'Original request'} for d in domains],
        'goal':'Explain requested synthetic records','desired_response':'investigation'}

def decision(text='Reasoned interpretation [S1].',extra=None):
    return {'decision':'need_more_evidence' if extra else 'answer','answer':text,'sources':['S1'] if '[S1]' in text else [],
        'additional_reads':extra or [],'remaining_requirements':[]}

class GraphRoles(unittest.IsolatedAsyncioTestCase):
    setUp=fixtures.B1Tests.setUp

    async def scoped(self,surface,prompt,outputs,*,change=None):
        cid=self.g.store.create('alice',surface)['id'];body=TurnRequest(request_id=uuid4(),prompt=prompt)
        packets=[]
        async def infer(role,request,authorization=None):
            authorization.assert_current_roles();packets.append({'role':role,'messages':request.messages,'schema':request.schema})
            result=dict(outputs[len(packets)-1])
            if role=='evidence_reasoner' and 'outcome_assessments' not in result:
                original=json.loads(request.messages[1]['content'])['requested_clauses']
                result['outcome_assessments']=[{'clause':c['id'],'status':'unresolved' if result['decision']=='need_more_evidence' else 'supported',
                    'sources':result.get('sources',[]),'assessment':'Explicitly mocked self-assessment, not intelligence evidence.',
                    'missing_facts':['Mocked source gap'] if result['decision']=='need_more_evidence' else []} for c in original]
            return InferenceResult(json.dumps(result),'synthetic-'+role,'google')
        environment={'COGNISHIELD_AI_ENGINE':'langgraph_b3','COGNISHIELD_AI_PLANNING':'1','COGNISHIELD_AI_SYNTHESIS':'1',
            'COGNISHIELD_AI_OUTCOMES':'0','COGNISHIELD_AI_HYBRID':'1','COGNISHIELD_AI_MULTI_MODEL_EXPERIMENT':'1',
            'COGNISHIELD_AI_EVIDENCE_REFINE':'1','COGNISHIELD_AI_EXPERIMENT_SEMANTIC_VERIFIER':'off'}
        with patch.dict('os.environ',environment),patch('llm.gemini_provider.scenario_approval_context',return_value={
            'eligible':True,'scenario_digest':'synthetic','source_revision':'r1','scenario_id':'test'}),\
            patch('llm.model_roles.infer',infer),patch('llm.orchestration.model.chat_model',AsyncMock(side_effect=AssertionError('No prerequisite Qwen allowed'))):
            approve_hybrid_request(self.db,self.g.store,self.user,cid,body,'r1')
            if change:change()
            response=await self.g.turn(cid,self.user,body)
        return response,packets

    async def test_both_surfaces_direct_planning_and_complete_configuration_operands(self):
        for surface in ['floating','studio']:
            r,packets=await self.scoped(surface,'Investigate R2 using saved configuration and syslog.',[
                plan(['configuration','syslog']),decision('The saved text names R2. Syslog is unavailable; it cannot establish whether an event occurred. [S1]')])
            self.assertEqual([p['role'] for p in packets],['complex_planner','evidence_reasoner'])
            self.assertEqual({row['tool'] for row in r.observations},{'network.configuration','network.syslog'})
            self.assertIn('OWNED_CONFIG',packets[1]['messages'][1]['content'])
            self.assertNotIn('PRIVATE_BOB',str(packets))
            self.assertTrue(r.answer.startswith('**Unverified AI interpretation'))
            self.assertIn('it cannot establish',r.answer)

    async def test_one_supplementary_round_and_final_continuation(self):
        extra=[{'reader':'network.syslog','parameters':{'device_refs':['2']},'gap':'Event records',
            'why':'To distinguish a configuration symptom from a recorded event','evidence_refs':['S1']}]
        r,packets=await self.scoped('floating','Investigate why R2 cannot communicate.',[
            plan(['configuration']),decision('Only saved text is available [S1].',extra),decision('The saved text is present, but no syslog observation is available. [S1]')])
        self.assertEqual(len(packets),3)
        self.assertEqual([p['role'] for p in packets],['complex_planner','evidence_reasoner','evidence_reasoner'])
        self.assertEqual({row['tool'] for row in r.observations},{'network.configuration','network.syslog'})
        self.assertEqual(packets[2]['schema']['properties']['additional_reads']['maxItems'],0)
        self.assertEqual(r.context_coverage['agent']['rounds'],2)

    async def test_advice_does_not_execute_even_when_model_proposes_reads(self):
        for surface in ['floating','studio']:
            r,packets=await self.scoped(surface,'Recommend the next useful checks for R2; do not read or collect anything.',[
                plan(['state','configuration']),decision('Ask for an interface-state observation to distinguish administrative from operational failure. This is a recommendation, not an observation.')])
            self.assertEqual(r.observations,[])
            self.assertEqual(len(packets),2)
            self.assertIn('recommendation',r.answer)

    async def test_failed_structural_receipts_cannot_be_released_with_semantics_off(self):
        with patch('llm.orchestration.engine.verify_records',return_value={'status':'failed','reason':'Synthetic receipt mismatch'}):
            r,_=await self.scoped('floating','Investigate R2 using saved configuration.',[plan(['configuration']),decision('A model claim [S1].')])
        self.assertNotIn('A model claim',r.answer)
        self.assertIn('structural integrity',r.answer)

    def test_configuration_cannot_enable_remote_without_approval(self):
        with patch.dict('os.environ',{'COGNISHIELD_AI_MULTI_MODEL_EXPERIMENT':'1'}):
            body=TurnRequest(request_id=uuid4(),prompt='Investigate R2')
            self.assertIsNone(HybridRequest.create(self.db,self.g.store,self.user,'floating',self.cid,body,time.monotonic()))

    def test_consent_binds_verifier_mode_and_roles(self):
        with patch.dict('os.environ',{'COGNISHIELD_AI_MULTI_MODEL_EXPERIMENT':'1','COGNISHIELD_AI_EXPERIMENT_SEMANTIC_VERIFIER':'off'}):
            original=hybrid_context(self.db)['role_binding']
            with patch.dict('os.environ',{'COGNISHIELD_AI_EXPERIMENT_SEMANTIC_VERIFIER':'report_only'}):
                self.assertNotEqual(original,hybrid_context(self.db)['role_binding'])

    def test_comparison_within_one_reader_is_complex_but_basic_explanation_is_local(self):
        with patch.dict('os.environ',{'COGNISHIELD_AI_HYBRID':'1','COGNISHIELD_AI_MULTI_MODEL_EXPERIMENT':'1'}),patch(
            'llm.gemini_provider.scenario_approval_context',return_value={'eligible':True,'scenario_digest':'synthetic','source_revision':'r1','scenario_id':'test'}):
            for prompt,expected in [('Compare R2 current configuration with its saved configuration.',True),('Explain R2 current configuration.',False)]:
                cid=self.g.store.create('alice','floating')['id'];body=TurnRequest(request_id=uuid4(),prompt=prompt)
                approve_hybrid_request(self.db,self.g.store,self.user,cid,body,'r1')
                scope=HybridRequest.create(self.db,self.g.store,self.user,'floating',cid,body,time.monotonic())
                self.assertEqual(scope.multi_model,expected)

    def test_supplementary_authority_and_original_scope(self):
        inventory={'devices':[{'id':'1','hostname':'R1'},{'id':'2','hostname':'R2'},{'id':'3','hostname':'Unrelated'}]}
        state=SimpleNamespace(request='Investigate R2',device_refs=['2'],results=[],evidence=[])
        def run(name,args):
            item={'reader':name,'parameters':args,'gap':'Missing record','why':'Relevant observation','evidence_refs':[]}
            return validate_additional({'additional_reads':[item]},state,inventory,self.g.registry,frozenset({'network.state'}))
        for name,args in [('document.propose',{}),('network.state',{'live':True}),('network.state',{'device_refs':['Unrelated']}),('network.state',{'device_refs':['unknown']})]:
            queries,rejections=run(name,args);self.assertFalse(queries);self.assertEqual(len(rejections),1)
        queries,rejections=run('network.state',{'device_refs':['R2']})
        self.assertEqual(queries[0]['domain'],'state');self.assertFalse(rejections)
