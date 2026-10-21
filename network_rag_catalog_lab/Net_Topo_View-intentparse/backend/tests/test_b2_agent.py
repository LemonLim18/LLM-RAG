"""B2 real LangGraph/SQLite/registry; injected models are labelled as such."""
import asyncio
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock,patch
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tests import test_b1_agent as baseline
from llm.gateway import AIGateway
from llm.gateway_models import TurnRequest,ToolResult,Evidence
from llm.gateway_routing import SemanticRoute
from llm.orchestration.memory import InvestigationSaver,InvestigationMemory
from llm.orchestration.investigation import assess
from llm.gateway_network import READ_TOOLS
from llm.tools import ToolAuthorization
from fastapi import HTTPException


class B2Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        baseline.B1Tests.setUp(self)
        self.b2=patch.dict(os.environ,{'COGNISHIELD_AI_ENGINE':'langgraph_b2'})
        self.b2.start();self.addCleanup(self.b2.stop)
    ask=baseline.B1Tests.ask

    async def test_invalid_planning_fallback_still_composes_retrieved_ordinary_evidence(self):
        route=SemanticRoute(intent='explain',network_domains=['configuration','state','syslog'],device_refs=['2'],
            network_request='Compare saved settings with observations and logs.',planning={'mode':'model_plan_invalid_fallback'})
        composer=AsyncMock(return_value=('The saved capture was retrieved, but operational observations are unavailable, so the comparison is incomplete.',{'status':'literal_checks_passed','model_synthesis':True}))
        with patch.dict(os.environ,{'COGNISHIELD_AI_SYNTHESIS':'1'}),\
                patch('llm.orchestration.engine.select_context',AsyncMock(return_value=route)),\
                patch('llm.orchestration.synthesis.synthesize',composer):
            result=await self.ask('Compare R2 saved settings with observed peers and recent log messages.')
        self.assertEqual(result.status,'success')
        composer.assert_awaited_once()
        self.assertIn('comparison is incomplete',result.answer)
        self.assertIn('network.configuration',{item['tool'] for item in composer.await_args.args[3]})

    async def test_adaptive_investigation_and_persistent_evidence_followup(self):
        r=await self.ask('Investigate why R1 cannot communicate with R2 using the available information')
        self.assertEqual(r.status,'success',r.answer)
        a=r.context_coverage['agent'];self.assertEqual(a['rounds'],2);self.assertEqual(a['tool_calls'],6)
        self.assertIn('confirmed root cause',r.answer);self.assertIn('not a packet-reachability test',r.answer)
        self.g=AIGateway(self.db)  # new gateway, no in-memory agent state
        follow=await self.ask('What evidence supports your conclusion?')
        self.assertEqual(follow.context_coverage['agent']['checkpointing'],'restored')
        self.assertEqual(set(follow.context_coverage['retrieval']['device_refs']),{'1','2'})
        self.assertEqual(len(follow.observations),6)
        with self.db._connect() as c:
            rows=c.execute('SELECT body FROM ai_agent_checkpoints').fetchall()
            self.assertLessEqual(len(rows),32)
            text='\n'.join(row[0] for row in rows)
            self.assertNotIn('OWNED_CONFIG',text);self.assertNotIn('PRIVATE_BOB_CONFIG',text)
            self.assertNotIn('authorization',text);self.assertNotIn('config_text',text)
            self.assertEqual(c.execute('SELECT status FROM ai_agent_investigations').fetchone()[0],'completed')

    async def test_other_interface_restart_and_changed_revision(self):
        await self.ask('What interfaces does R2 have?')
        await self.ask('What is the IP address of the first one?')
        self.g=AIGateway(self.db)
        r=await self.ask('What about the other interface?')
        self.assertIn('10.1.1.2',r.answer);self.assertNotIn('192.168.1.251',r.answer)
        with self.db._connect() as c:c.execute("UPDATE interfaces SET ip_address='192.0.2.44' WHERE id=3")
        again=await self.ask('Are you sure?')
        self.assertIn('192.0.2.44',again.answer);self.assertNotIn('10.1.1.2',again.answer)
        self.assertIn('freshly authorized',again.answer)

    async def test_topic_change_clears_investigation(self):
        await self.ask('Investigate R2 connectivity')
        with patch('llm.orchestration.engine.select_context',AsyncMock(return_value=SemanticRoute(intent='answer'))),patch('local_providers.chat.generate',AsyncMock(return_value=('Hello!','test'))):
            hello=await self.ask('hello')
        self.assertFalse(hello.observations)
        auth=ToolAuthorization('alice','engineer','floating',self.cid,READ_TOOLS)
        saver=InvestigationSaver(self.g.store,auth,'not-a-running-turn')
        memory,status=saver.load_memory();self.assertFalse(memory.goal);self.assertFalse(memory.device_refs)

    async def test_mapping_authorization_schema_and_deletion(self):
        await self.ask('Show R2 interfaces')
        auth=ToolAuthorization('alice','engineer','floating',self.cid,READ_TOOLS)
        saver=InvestigationSaver(self.g.store,auth,'x')
        with self.assertRaises(HTTPException):saver.get_tuple({'configurable':{'thread_id':'forged'}})
        with self.assertRaises(HTTPException):InvestigationSaver(self.g.store,ToolAuthorization('bob','engineer','floating',self.cid,READ_TOOLS),'x')
        with self.assertRaises(HTTPException):InvestigationSaver(self.g.store,ToolAuthorization('alice','engineer','studio',self.cid,READ_TOOLS),'x')
        with self.db._connect() as c:c.execute('UPDATE ai_agent_investigations SET schema_version=999')
        memory,status=saver.load_memory();self.assertEqual(status,'schema_reset');self.assertFalse(memory.device_refs)
        self.g.store.delete(self.cid,'alice')
        with self.db._connect() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM ai_agent_checkpoints').fetchone()[0],0)

    async def test_cancel_resume_replays_only_reads_no_duplicate_response(self):
        real=self.g.registry.invoke;entered=asyncio.Event()
        async def pause(name,args,auth):
            if name=='network.topology':entered.set();await asyncio.sleep(30)
            return await real(name,args,auth)
        request=TurnRequest(request_id=uuid4(),prompt='Investigate R2 connectivity')
        with patch.object(self.g.registry,'invoke',pause):
            task=asyncio.create_task(self.g.turn(self.cid,self.user,request))
            await asyncio.wait_for(entered.wait(),5);task.cancel()
            with self.assertRaises(asyncio.CancelledError):await task
        with self.db._connect() as c:
            self.assertEqual(c.execute('SELECT state FROM ai_turns WHERE request_id=?',(str(request.request_id),)).fetchone()[0],'cancelled')
        self.g=AIGateway(self.db)
        result=await self.ask('Continue the investigation')
        self.assertEqual(result.status,'success',result.answer)
        self.assertEqual(result.context_coverage['retrieval']['device_refs'],['2'])
        retry=TurnRequest(request_id=uuid4(),prompt='Show R2 interfaces')
        first=await self.g.turn(self.cid,self.user,retry)
        with patch.object(self.g.registry,'invoke',AsyncMock(side_effect=AssertionError('replay'))):
            second=await self.g.turn(self.cid,self.user,retry)
        self.assertEqual(first,second)

    async def test_multi_source_direct_read_and_unavailable_does_not_fault(self):
        r=await self.ask("Check R2's interfaces and stored configuration, then investigate available syslogs")
        self.assertEqual(r.status,'success',r.answer)
        self.assertTrue({'inventory.read','network.configuration','network.syslog'}<={i['tool'] for i in r.observations})
        self.assertIn('OWNED_CONFIG',r.answer);self.assertNotIn('PRIVATE_BOB_CONFIG',r.answer)
        self.assertFalse(any(e.origin=='live' for e in r.evidence))
        self.assertLessEqual(r.context_coverage['agent']['tool_calls'],8)

    async def test_conflicting_and_stale_evidence_not_root_cause(self):
        with self.db._connect() as c:c.execute("UPDATE config_snapshots SET config_text='interface Gi0/1\n ip address 203.0.113.1 255.255.255.0' WHERE owner_username='alice'")
        r=await self.ask('Investigate R2 connectivity')
        self.assertTrue(r.context_coverage['agent']['assessment']['conflicts'])
        self.assertIn('disagree',r.answer);self.assertIn('neither establishes',r.answer)

    async def test_document_followup_reuses_existing_pipeline_and_no_network(self):
        segments=[{'text':'Page four explains OSPF neighbor timers.','page':4,'extraction':'direct_text'},
            {'text':'Page five explains BGP route policy.','page':5,'extraction':'direct_text'}]
        with self.db._connect() as c:c.execute('INSERT INTO ai_attachments(id,conversation_id,owner,name,digest,byte_size,segments) VALUES(?,?,?,?,?,?,?)',
            (str(uuid4()),self.cid,'alice','routing.pdf','test',100,json.dumps(segments)))
        route=SemanticRoute(intent='analyze_files',use_attachments=True)
        with patch('llm.orchestration.engine.select_context',AsyncMock(return_value=route)),patch('local_providers.chat.generate',AsyncMock(return_value=('OSPF neighbor timers.','test'))):
            r=await self.ask('What does page 4 of my uploaded PDF explain?')
        self.assertIn('page 4',r.answer);self.assertFalse(r.observations)
        with patch('llm.orchestration.engine.select_context',AsyncMock(return_value=route)),patch('local_providers.chat.generate',AsyncMock(return_value=('BGP route policy.','test'))):
            r=await self.ask('What about page 5?')
        self.assertIn('page 5',r.answer);self.assertNotIn('page 4',r.answer)

    async def test_contextual_reads_do_not_require_device_references(self):
        from llm.orchestration.investigation import contextual_route
        from llm.gateway_services import inventory_snapshot
        inventory=inventory_snapshot(self.db)
        self.assertIsNone(contextual_route('What does page 4 of this PDF explain? Describe its actual content.',InvestigationMemory(),None,inventory))
        result=contextual_route('Explain the published OSPF operation requirements',InvestigationMemory(),None,inventory)
        self.assertEqual(result.network_domains,['knowledge']);self.assertEqual(result.device_refs,[])

    async def test_published_requirements_authorized_reader_no_generation(self):
        documents=[{'source':'published:configure_ospf','text':'OSPF contract','published_requirements':{'operations':[
            {'operation_id':'configure_ospf','description':'Configure OSPF','schema':{'required':['process_id','router_id']},'profiles':[{'vendor':'cisco','platform':'iosxe','versions':['17.9']}]}]}}]
        with patch('llm.gateway_knowledge.documentation_context',return_value=(documents,[Evidence(id='published-test',source='published:configure_ospf',origin='stored',source_revision='release',authority='published_operation_documentation')])):
            r=await self.ask("Explain the published OSPF operation requirements and compare them with R2's stored configuration")
        self.assertEqual(r.kind,'answer');self.assertIn('`process_id`',r.answer);self.assertIn('OWNED_CONFIG',r.answer)
        self.assertTrue({'knowledge.search','network.configuration'}<={i['tool'] for i in r.observations})
        self.assertIsNone(r.preview);self.assertEqual(r.context_coverage['agent']['verification']['status'],'verified')

    async def test_partial_tool_failure_preserves_other_evidence(self):
        real=self.g.registry.invoke
        async def fail(name,args,auth):
            if name=='network.syslog':raise HTTPException(503,'test unavailable')
            return await real(name,args,auth)
        with patch.object(self.g.registry,'invoke',fail):r=await self.ask('Investigate R2 connectivity')
        details=r.context_coverage['agent']['record_details']
        self.assertIn('OWNED_CONFIG',details);self.assertNotIn('PRIVATE_BOB_CONFIG',details)
        self.assertIn('unavailable',r.answer.lower());self.assertNotIn('```',r.answer)
        self.assertEqual(r.status,'success')

    async def test_checkpoint_retention_corruption_and_unsupported_state(self):
        await self.ask('Show R2 interfaces')
        auth=ToolAuthorization('alice','engineer','floating',self.cid,READ_TOOLS)
        saver=InvestigationSaver(self.g.store,auth,'inactive')
        with self.db._connect() as c:
            c.execute("UPDATE ai_agent_checkpoints SET body='not json'")
        self.assertEqual(saver.load_memory()[1],'invalid_reset')
        with self.assertRaises(HTTPException):saver.put(saver.config(),{'id':'x','channel_values':{'memory':{}}},{}, {})
        with self.db._connect() as c:
            c.execute("UPDATE ai_agent_investigations SET updated_at=datetime('now','-31 days')")
        renewed=InvestigationSaver(self.g.store,auth,'inactive')
        self.assertNotEqual(renewed.thread,saver.thread)
        self.assertEqual(renewed.load_memory()[1],'empty')

    async def test_concurrent_turn_rejected_and_permission_rechecked(self):
        real=self.g.registry.invoke;entered=asyncio.Event();release=asyncio.Event()
        async def pause(name,args,auth):
            entered.set();await release.wait();return await real(name,args,auth)
        with patch.object(self.g.registry,'invoke',pause):
            first=asyncio.create_task(self.ask('Show R2 interfaces'))
            await asyncio.wait_for(entered.wait(),5)
            with self.assertRaises(HTTPException) as error:await self.ask('Show R1 interfaces')
            self.assertEqual(error.exception.status_code,409)
            release.set();await first
        denied=await self.ask('Are you sure?',user={'username':'alice','role':'unknown'})
        self.assertEqual(denied.status,'denied');self.assertFalse(denied.observations)

    async def test_timeout_records_interruption_and_accepts_new_read_request(self):
        from llm.orchestration.engine import run as real_run
        real=self.g.registry.invoke
        async def pause(name,args,auth):
            if name=='network.topology':await asyncio.sleep(3)
            return await real(name,args,auth)
        async def bounded(*args,**kwargs):return await real_run(*args,**kwargs,timeout=1.0)
        with patch('llm.orchestration.engine.run',bounded),patch.object(self.g.registry,'invoke',pause):
            result=await self.ask('Investigate R2 connectivity')
        self.assertEqual(result.status,'unavailable')
        with self.db._connect() as c:self.assertEqual(c.execute('SELECT status FROM ai_agent_investigations').fetchone()[0],'interrupted')
        result=await self.ask('Resume the investigation')
        self.assertEqual(result.status,'success',result.answer)
        self.assertEqual(result.context_coverage['agent']['restored_status'],'interrupted')

    async def test_no_model_claims_saved_and_source_disappearance_rechecked(self):
        await self.ask('Show R2 interfaces')
        # Corrupt only old assistant prose, as if an earlier model invented facts.
        with self.db._connect() as c:
            row=c.execute("SELECT request_id,result FROM ai_turns WHERE conversation_id=?",(self.cid,)).fetchone()
            result=json.loads(row['result']);result['answer']='R2 Loopback999 has 203.0.113.222'
            c.execute('UPDATE ai_turns SET result=? WHERE request_id=?',(json.dumps(result),row['request_id']))
        result=await self.ask('Are you sure?')
        self.assertNotIn('Loopback999',result.answer);self.assertNotIn('203.0.113.222',result.answer)

    def test_conflicting_telemetry_same_time_is_not_silently_resolved(self):
        data={'records':[{'device':'R2','time':'2026-10-16T10:00:00Z','field':'loss','value':0},
            {'device':'R2','time':'2026-10-16T10:00:00Z','field':'loss','value':100}]}
        assessment=assess([{'tool':'network.telemetry','status':'success','data':data}],[])
        self.assertTrue(assessment['conflicts']);self.assertEqual(assessment['conclusion_status'],'insufficient_for_confirmed_root_cause')

    async def test_mixed_document_network_uses_separate_grounding(self):
        identity=str(uuid4())
        with self.db._connect() as c:c.execute('INSERT INTO ai_attachments(id,conversation_id,owner,name,digest,byte_size,segments) VALUES(?,?,?,?,?,?,?)',
            (identity,self.cid,'alice','routing.txt','test',50,json.dumps([{'text':'OSPF uses area identifiers.','page':None,'extraction':'direct_text'}])))
        route=SemanticRoute(intent='analyze_files',use_attachments=True,network_domains=['inventory'],device_refs=['2'])
        with patch('llm.orchestration.engine.select_context',AsyncMock(return_value=route)),patch('local_providers.chat.generate',AsyncMock(return_value=('R2 uses 203.0.113.222.','test'))) as model:
            r=await self.ask('Compare my attached document with R2 interfaces')
        self.assertIn('192.168.1.251',r.answer);self.assertNotIn('203.0.113.222',r.answer)
        self.assertIn('withheld',r.answer)
        supplied=str(model.call_args.args)
        self.assertIn('OSPF uses area identifiers.',supplied);self.assertNotIn('192.168.1.251',supplied)

    async def test_failed_new_routing_does_not_erase_durable_goal(self):
        await self.ask('Investigate R2 connectivity')
        with patch('llm.orchestration.engine.select_context',AsyncMock(side_effect=HTTPException(503,'model offline'))):
            result=await self.ask('An uncertain new request')
        self.assertEqual(result.status,'unavailable')
        result=await self.ask('Resume the investigation')
        self.assertEqual(result.context_coverage['retrieval']['device_refs'],['2'])

    async def test_document_selection_persists_and_removed_attachment_clarifies(self):
        ids=[str(uuid4()),str(uuid4())]
        with self.db._connect() as c:
            for identity,text in zip(ids,['OSPF area identifiers.','Unrelated BGP policy.']):
                c.execute('INSERT INTO ai_attachments(id,conversation_id,owner,name,digest,byte_size,segments) VALUES(?,?,?,?,?,?,?)',
                    (identity,self.cid,'alice',identity+'.txt','test',50,json.dumps([{'text':text,'page':None,'extraction':'direct_text'}])))
        route=SemanticRoute(intent='analyze_files',use_attachments=True)
        with patch('llm.orchestration.engine.select_context',AsyncMock(return_value=route)),patch('local_providers.chat.generate',AsyncMock(return_value=('OSPF area identifiers.','test'))) as model:
            await self.ask('Read my first attachment',attachment_ids=[ids[0]])
            self.g=AIGateway(self.db)
            result=await self.ask('Explain that document further')
            self.assertEqual(result.context_coverage['agent']['document_refs'],[ids[0]])
            self.assertNotIn('Unrelated BGP policy.',str(model.call_args.args))
            with self.db._connect() as c:c.execute('DELETE FROM ai_attachments WHERE id=?',(ids[0],))
            result=await self.ask('Explain that document further')
            self.assertEqual(result.kind,'clarification')

    async def test_explicit_correction_replaces_subject(self):
        await self.ask('Show R2 interfaces')
        result=await self.ask('Actually I meant R1, not R2')
        self.assertEqual(result.context_coverage['retrieval']['device_refs'],['1'])
        self.assertIn('192.168.1.250',result.answer);self.assertNotIn('10.1.1.2',result.answer)


if __name__=='__main__':unittest.main()
