"""Focused typed model-boundary tests; these are not real-model quality scores."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock,patch
import os
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from development.examples import mixed_vendor_path
from llm.gateway_models import Evidence
from llm.orchestration.planning import propose,additional_reads
from llm.orchestration.synthesis import projection,check_candidate,synthesize


class PlanTests(unittest.IsolatedAsyncioTestCase):
    async def test_small_source_decision_corrects_reader_selection_without_permissions(self):
        from development.starter import starter_bundle
        fixture=starter_bundle();inventory={'devices':fixture['sources']['inventory']['data']['devices'],'scenario':{'mode':'development_scenario'},'logical_source_categories':list(fixture['sources'])}
        generate=AsyncMock(side_effect=[(json.dumps({'intent':'explain','information_needs':[{'domain':'telemetry','question':'controller status'}]}),'test'),
            (json.dumps({'source_categories':['controller_state','source_health']}),'test')])
        route=await propose('Explain the LAB-R1 controller and whether physical collection occurred.','test','floating',None,[],[],inventory,generate)
        self.assertEqual(route.network_domains,['state'])
        self.assertEqual(route.source_requests['state']['source_categories'],['controller_state','source_health'])
        self.assertEqual(route.planning['source_selection']['status'],'validated_model_source_selection')
        self.assertEqual(generate.await_count,2)

    async def test_legacy_scenario_keeps_its_existing_broad_reader_contract(self):
        inventory={'devices':mixed_vendor_path()['devices'],'scenario':{'id':'legacy'}}
        generate=AsyncMock(return_value=(json.dumps({'intent':'explain','information_needs':[{'domain':'state','question':'recorded protocol state'}]}),'test'))
        route=await propose('Explain Core-Birch recorded protocol state.','test','floating',None,[],[],inventory,generate)
        self.assertEqual(route.source_requests,{'state':{'source_scope':'auto'}})
        self.assertEqual(generate.await_count,1)

    async def test_failed_controller_plan_keeps_an_authoritative_state_read(self):
        from fastapi import HTTPException
        from llm.gateway_routing import select_context
        inventory={'devices':[dict(device,interfaces=[]) for device in mixed_vendor_path()['devices']]}
        with patch.dict(os.environ,{'COGNISHIELD_AI_PLANNING':'1'}),patch('llm.gateway_semantics.semantic_hint',AsyncMock(return_value=None)):
            route=await select_context('What does the controller report for Core-Birch?','test','floating',None,[],[],inventory=inventory,
                generate_fn=AsyncMock(side_effect=HTTPException(503,'Model unavailable')))
        self.assertIn('state',route.network_domains)
        self.assertEqual(route.planning['mode'],'model_plan_invalid_fallback')

    async def plan(self,value,prompt='Compare Core-Birch current configuration with its saved backups.'):
        return await propose(prompt,'test','floating',None,[],[],{'devices':mixed_vendor_path()['devices']},
            AsyncMock(return_value=(json.dumps(value),'test')))

    async def test_source_scope_merge_and_real_device_resolution(self):
        plan=await self.plan(dict(intent='answer',information_needs=[
            dict(domain='configuration',question='current',source_scope='current'),
            dict(domain='configuration',question='backups',source_scope='historical')]))
        self.assertEqual(plan.device_refs,['1200']);self.assertEqual(plan.source_requests,{'configuration':{'source_scope':'both'}})

    async def test_unknown_invented_and_authorization_fields_rejected(self):
        for value in [dict(intent='answer',devices=['R99']),dict(intent='answer',devices=['Edge-Cedar']),
                      dict(intent='answer',role='admin'),dict(intent='answer',information_needs=[dict(domain='shell',question='run')]),
                      dict(intent='edit',use_editor=True)]:
            with self.subTest(value=value),self.assertRaises(ValueError):await self.plan(value)

    async def test_unrelated_conversation_keeps_sources_empty(self):
        plan=await self.plan(dict(intent='answer'),prompt='Hello!')
        self.assertFalse(plan.network_domains);self.assertFalse(plan.device_refs);self.assertFalse(plan.use_history)

    async def test_logical_source_selection_is_validated_and_preserved(self):
        value={'intent':'explain','information_needs':[
            {'domain':'state','question':'controller record','source_categories':['controller_state']},
            {'domain':'state','question':'collector availability','source_categories':['source_health']}]}
        plan=await self.plan(value,prompt='Explain Core-Birch controller and collector records.')
        self.assertEqual(plan.source_requests['state']['source_categories'],['controller_state','source_health'])
        for category in ['config_snapshots','documents','shell']:
            with self.subTest(category=category),self.assertRaises(ValueError):
                await self.plan({'intent':'answer','information_needs':[{'domain':'state','question':'read','source_categories':[category]}]})
        # A broad request for the same reader must not be narrowed by a later need.
        value['information_needs'].insert(0,{'domain':'state','question':'all operational observations'})
        broad=await self.plan(value,prompt='Compare all operational observations with the controller records.')
        self.assertNotIn('source_categories',broad.source_requests['state'])

    async def test_semantic_decision_cannot_select_missing_document_context(self):
        from llm.gateway_routing import select_context
        generate=AsyncMock(side_effect=[(json.dumps({'intent':'network'}),'test'),
            (json.dumps({'network_domains':['telemetry'],'request':'Recorded traffic'}),'test')])
        with patch.dict(os.environ,{'COGNISHIELD_AI_PLANNING':'0'}),patch('llm.gateway_semantics.semantic_hint',AsyncMock(return_value=None)):
            route=await select_context('What traffic measurements are recorded for the uplink?','test','floating',None,[],[],generate_fn=generate)
        choices=generate.await_args_list[0].kwargs['structured']['properties']['intent']['enum']
        self.assertNotIn('analyze_files',choices);self.assertNotIn('explain',choices)
        self.assertEqual(route.network_domains,['telemetry']);self.assertFalse(route.use_attachments)
        with patch.dict(os.environ,{'COGNISHIELD_AI_PLANNING':'0'}),patch('llm.gateway_semantics.semantic_hint',AsyncMock(return_value=None)):
            route=await select_context('Read the content','test','floating',None,[],[],generate_fn=AsyncMock(return_value=('{"intent":"analyze_files"}','test')))
        self.assertEqual(route.intent,'clarify');self.assertFalse(route.use_attachments)

    async def test_additional_reads_cannot_repeat_or_elevate_tools(self):
        for domain in ['configuration','shell','v9.preview']:
            value={'information_needs':[{'domain':domain,'question':'check'}],'reason':'Resolve an observation gap'}
            with self.subTest(domain=domain),self.assertRaises(ValueError):
                await additional_reads('Why?',{'state'},{'gaps':['Missing state']},[],'test',AsyncMock(return_value=(json.dumps(value),'test')))
        queries,decision=await additional_reads('Why?',{'state'},{'gaps':['Missing state']},[],'test',AsyncMock(return_value=(json.dumps({'information_needs':[{'domain':'state','question':'routing state','source_scope':'observed'}],'reason':'Check a decisive observation'}),'test')))
        self.assertEqual(queries,{'state':{'source_scope':'observed'}})

    async def test_graph_executes_validated_additional_plan_through_existing_registry(self):
        from tests.test_b1_agent import B1Tests
        from llm.gateway_routing import SemanticRoute
        from llm.orchestration.model import RoutingModel
        fixture=B1Tests();fixture.setUp()
        try:
            with patch.dict(os.environ,{'COGNISHIELD_AI_ENGINE':'langgraph_b3','COGNISHIELD_AI_PLANNING':'1','COGNISHIELD_AI_SYNTHESIS':'0'}),patch('llm.orchestration.engine.select_context',AsyncMock(return_value=SemanticRoute(intent='answer',network_domains=['inventory'],device_refs=['2'],planning={'mode':'validated_model_plan'}))),patch.object(RoutingModel,'generate',AsyncMock(return_value=(json.dumps({'information_needs':[{'domain':'state','question':'routing state'}],'reason':'Test the missing scoped state'}),'test'))):
                result=await fixture.ask('Investigate the recorded R2 connectivity problem')
            self.assertEqual([r['tool'] for r in result.observations],['inventory.read','network.state'])
            self.assertEqual(result.context_coverage['agent']['rounds'],2)
            self.assertEqual(result.context_coverage['agent']['planning']['additional_model_decision']['status'],'validated')
        finally:fixture.doCleanups()


class GroundingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.context=[{'tool':'network.state','status':'success','evidence_ids':['opaque-internal-id'],
            'data':{'scenario':{'id':'ORACLE-HIDDEN','source_revision':'revision-hidden'},'records':[
                {'hostname':'Core-Birch','interface':'ge-0/0/1.0','prefix':'10.44.0.5/30',
                 'local_as':65020,'remote_as':65030,'observed_state':'Established'}]}}]
        self.evidence=[Evidence(id='opaque-internal-id',source='development.state',origin='simulated',authority='development_scenario')]
        self.assessment={'development':True,'conclusion_status':'insufficient_evidence'}

    def test_projection_removes_internal_identity_and_oracle_labels(self):
        data=json.dumps(projection(self.context,self.evidence,self.assessment))
        for secret in ['opaque-internal-id','ORACLE-HIDDEN','revision-hidden']:self.assertNotIn(secret,data)
        self.assertIn('10.44.0.5/30',data);self.assertIn('S1',data)

    def test_exact_and_causal_claims_are_rejected(self):
        for answer in ['Core-Birch has IP address 10.99.0.1. [S1]',
                       'Core-Birch GigabitEthernet0/99 is down. [S1]',
                       'The root cause is a failed cable. [S1]',
                       'Physical device is down. [S1]',
                       'The current configuration is complete and operational. [S1]',
                       'Core-Birch is operational.',
                       'Evidence confirms that this is a failure. [S77]']:
            with self.subTest(answer=answer):self.assertTrue(check_candidate(answer,self.context,self.evidence,self.assessment))

    def test_as_roles_and_sentence_ending_addresses(self):
        self.assertFalse(check_candidate('Core-Birch local AS is 65020 and remote AS is 65030. [S1]',self.context,self.evidence,self.assessment))
        self.assertTrue(check_candidate('Core-Birch local AS is 65030. [S1]',self.context,self.evidence,self.assessment))
        self.assertFalse(check_candidate('Core-Birch has interface address 10.44.0.5. [S1]',self.context,self.evidence,self.assessment))

    def test_unavailable_source_cannot_become_available_in_prose(self):
        context=self.context+[{'tool':'network.syslog','status':'unavailable','data':{'source_available':False}}]
        self.assertTrue(check_candidate('The syslogs on Core-Birch are available. [S1]',context,self.evidence,self.assessment))
        self.assertFalse(check_candidate('Syslogs are unavailable. Additional evidence may help. [S1]',context,self.evidence,self.assessment))

    async def test_invalid_synthesis_releases_verified_fallback(self):
        model=type('Model',(),{'generate':AsyncMock(return_value=(json.dumps({'answer':'Root cause is a broken cable. [S1]','sources':['S1']}),'test'))})()
        answer,report=await synthesize(model,'test','Why?',self.context,self.evidence,self.assessment,'Verified fallback')
        self.assertEqual(answer,'Verified fallback');self.assertEqual(report['status'],'rejected_fallback')

    async def test_malformed_synthesis_is_not_credited(self):
        model=type('Model',(),{'generate':AsyncMock(return_value=('not JSON','test'))})()
        answer,report=await synthesize(model,'test','Why?',self.context,self.evidence,self.assessment,'Verified fallback')
        self.assertEqual(answer,'Verified fallback');self.assertFalse(report['model_synthesis'])


class HandoffTests(unittest.IsolatedAsyncioTestCase):
    async def test_eligibility_is_owned_revision_checked_and_read_only(self):
        import tempfile
        from uuid import uuid4
        from fastapi import HTTPException
        from db.manager import DatabaseManager
        from llm.gateway_store import ensure_schema
        from llm.gateway import AIGateway
        from llm.gateway_models import TurnRequest
        from llm.gateway_handoff import eligibility,prepare,accept
        from local_providers.development import ScenarioManager
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'COGNISHIELD_DEV_SIMULATION':'1','COGNISHIELD_AI_ENGINE':'langgraph_b3','COGNISHIELD_AI_PLANNING':'0','COGNISHIELD_AI_SYNTHESIS':'0'}):
            db=DatabaseManager(str(Path(folder)/'app.db'));db.initialize();ensure_schema(db)
            try:
                manager=ScenarioManager(Path(folder)/'state.json');db._development_scenario=manager
                gateway=AIGateway(db);user={'username':'alice','role':'engineer'};cid=gateway.store.create('alice','floating')['id']
                request=uuid4();await gateway.turn(cid,user,TurnRequest(request_id=request,prompt='What interfaces does R2 have?'))
                checked=eligibility(gateway,user,cid,str(request));self.assertTrue(checked['eligible'])
                with db._connect() as c:self.assertEqual(c.execute('SELECT count(*) FROM ai_handoffs').fetchone()[0],0)
                for other in [{'username':'bob','role':'engineer'},{'username':'alice','role':'auditor'}]:
                    with self.assertRaises(HTTPException):eligibility(gateway,other,cid,str(request))
                handoff=prepare(gateway,user,cid,str(request),'Review the interface evidence')
                result=accept(gateway,user,handoff['id'])
                self.assertEqual(accept(gateway,user,handoff['id'])['conversation_id'],result['conversation_id'])
                with db._connect() as c:
                    self.assertEqual(c.execute('SELECT count(*) FROM ai_turns WHERE conversation_id=?',(result['conversation_id'],)).fetchone()[0],0)
                scenario,meta=manager.snapshot();manager.change('select',meta['source_revision'],scenario_id='UNKNOWN-001')
                with self.assertRaises(HTTPException):eligibility(gateway,user,cid,str(request))
            finally:db.close()
