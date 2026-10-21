"""B1 real graph/registry/SQLite tests; model failures are injected explicitly."""
import asyncio
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock,patch
from uuid import uuid4

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi import HTTPException
from db.manager import DatabaseManager
from llm.gateway import AIGateway
from llm.gateway_models import TurnRequest,ToolResult,Evidence
from llm.gateway_store import ensure_schema
from llm.gateway_network import READ_TOOLS
from llm.gateway_routing import SemanticRoute
from llm.tools import ToolAuthorization
from llm.orchestration.adapters import AuthorizedTools
from llm.orchestration.verification import release_answer


class B1Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.db=DatabaseManager(str(Path(self.folder.name)/'b1.db'));self.db.initialize();ensure_schema(self.db)
        assert Path(self.db._db_path).resolve().is_relative_to(Path(self.folder.name).resolve())
        self.env=patch.dict(os.environ,{'COGNISHIELD_AI_ENGINE':'langgraph_b1','COGNISHIELD_SEMANTIC_EMBEDDINGS':'0','COGNISHIELD_AI_LIVE_READS':'0',
            'COGNISHIELD_AI_PLANNING':'0','COGNISHIELD_AI_SYNTHESIS':'0'})
        self.env.start();self.addCleanup(self.env.stop)
        with self.db._connect() as c:
            c.execute("INSERT INTO devices(id,hostname,management_ip,vendor) VALUES(1,'R1','192.168.1.250','cisco')")
            c.execute("INSERT INTO devices(id,hostname,management_ip,vendor) VALUES(2,'R2','192.168.1.251','cisco')")
            for i,d,name,address in [(1,1,'Gi0/0','192.168.1.250'),(2,2,'Gi0/0','192.168.1.251'),(3,2,'Gi0/1','10.1.1.2')]:
                c.execute('INSERT INTO interfaces(id,device_id,name,ip_address) VALUES(?,?,?,?)',(i,d,name,address))
            for owner,text in [('alice','hostname R2\n! OWNED_CONFIG'),('bob','PRIVATE_BOB_CONFIG')]:
                c.execute('INSERT INTO config_snapshots(device_id,config_text,config_hash,owner_username,source_type) VALUES(2,?,?,?,?)',(text,uuid4().hex,owner,'simulated_fixture'))
        self.g=AIGateway(self.db);self.user={'username':'alice','role':'engineer'}
        self.cid=self.g.store.create('alice','floating')['id']

    async def ask(self,prompt,**kwargs):
        return await self.g.turn(kwargs.pop('identity',self.cid),kwargs.pop('user',self.user),TurnRequest(request_id=uuid4(),prompt=prompt,**kwargs))

    async def test_actual_graph_facts_followups_and_provenance(self):
        first=await self.ask('What interfaces does R2 have?')
        self.assertIn('10.1.1.2',first.answer);self.assertIn('192.168.1.251',first.answer)
        agent=first.context_coverage['agent']
        self.assertEqual(agent['engine'],'langgraph_b1');self.assertEqual(agent['tool_calls'],1)
        self.assertEqual(len(agent['nodes']),7);self.assertEqual(agent['verification']['status'],'verified')
        second=await self.ask('What is the IP address of the first one?')
        self.assertIn('192.168.1.251',second.answer);self.assertNotIn('10.1.1.2',second.answer)
        with self.db._connect() as c:c.execute("UPDATE interfaces SET ip_address='192.0.2.44' WHERE id=2")
        third=await self.ask('Are you sure?')
        self.assertIn('192.0.2.44',third.answer);self.assertNotIn('192.168.1.251',third.answer)
        self.assertEqual(third.context_coverage['agent']['tool_calls'],1)

    async def test_configuration_owner_and_native_no_fabrication(self):
        r=await self.ask("Show R2's stored configuration.")
        self.assertIn('OWNED_CONFIG',r.answer);self.assertNotIn('PRIVATE_BOB_CONFIG',r.answer)
        self.assertEqual(r.evidence[0].origin,'simulated')
        self.assertEqual(r.context_coverage['agent']['verification']['status'],'verified')
        followup=await self.ask("R2's stored configuration, please.")
        self.assertEqual(followup.kind,'answer');self.assertIn('OWNED_CONFIG',followup.answer)

    async def test_missing_evidence_causes_only_one_additional_read(self):
        r=await self.ask('Show live packet loss measurements for R2 right now')
        agent=r.context_coverage['agent']
        self.assertEqual(agent['rounds'],2);self.assertEqual(agent['tool_calls'],2)
        self.assertEqual({i['tool'] for i in r.observations},{'network.telemetry','inventory.read'})
        self.assertIn('No network root cause can be established',r.answer)
        self.assertFalse(any(e.origin=='live' for e in r.evidence))

    async def test_multi_source_graph_is_bounded(self):
        r=await self.ask('Investigate R2 using topology, measurements, logs, incidents and configuration history')
        self.assertLessEqual(r.context_coverage['agent']['tool_calls'],8)
        self.assertEqual(r.context_coverage['agent']['rounds'],1)
        self.assertEqual(len(r.observations),6)
        self.assertIn('OWNED_CONFIG',r.answer)

    async def test_greeting_uses_no_tools_and_drops_history(self):
        await self.ask('Show R2 interfaces')
        route=SemanticRoute(intent='answer')
        with patch('llm.orchestration.engine.select_context',AsyncMock(return_value=route)),patch('local_providers.chat.generate',AsyncMock(return_value=('Hello!','test'))),patch.object(self.g.registry,'invoke',AsyncMock()) as invoke:
            r=await self.ask('hello')
        invoke.assert_not_awaited();self.assertEqual(r.answer,'Hello!');self.assertEqual(r.evidence,[])
        self.assertEqual(r.context_coverage['agent']['nodes'],['understand_request','resolve_references'])
        self.assertFalse(r.context_coverage['routing']['history'])

    async def test_unknown_device_has_no_read_or_generated_facts(self):
        with patch.object(self.g.registry,'invoke',AsyncMock()) as invoke:r=await self.ask('Show R99 interfaces')
        invoke.assert_not_awaited();self.assertEqual(r.kind,'clarification');self.assertEqual(r.evidence,[])

    async def test_refusal_malformed_and_timeout_do_not_call_tools(self):
        for problem in [HTTPException(503,'Model refused'),HTTPException(503,'Model timeout'),('{"intent":"execute"}','test'),('not JSON','test')]:
            fn=AsyncMock(side_effect=problem) if isinstance(problem,Exception) else AsyncMock(return_value=problem)
            with patch('llm.orchestration.model.RoutingModel.generate',fn),patch.object(self.g.registry,'invoke',AsyncMock()) as invoke:
                r=await self.ask('Please help me look into something unusual')
            invoke.assert_not_awaited();self.assertIn(r.status,{'unavailable','clarification_required'})

    async def test_ollama_adapter_maps_provider_errors_to_unavailable(self):
        from ollama import ResponseError
        from llm.orchestration.model import RoutingModel
        client=AsyncMock();client.ainvoke.side_effect=ResponseError('Runner failure',status_code=500)
        with patch('llm.orchestration.model.chat_model',AsyncMock(return_value=(client,'test'))),self.assertRaises(HTTPException) as error:
            await RoutingModel().generate([{'role':'user','content':'hello'}])
        self.assertEqual(error.exception.status_code,503)

    async def test_unsupported_tool_and_empty_allowlist_denied(self):
        for allowed in [READ_TOOLS,frozenset()]:
            auth=ToolAuthorization('alice','engineer','floating',self.cid,allowed)
            tools=AuthorizedTools(self.g.registry,self.g.store,auth)
            with self.assertRaises(HTTPException):await tools.invoke('document.propose',{},auth)
            if not allowed:
                with self.assertRaises(HTTPException):await tools.invoke('inventory.read',{},auth)

    async def test_tool_role_is_checked_at_invocation_and_arguments_are_strict(self):
        auth=ToolAuthorization('alice','untrusted','floating',self.cid,READ_TOOLS)
        tools=AuthorizedTools(self.g.registry,self.g.store,auth)
        with self.assertRaises(HTTPException):await tools.invoke('inventory.read',{},auth)
        auth=ToolAuthorization('alice','engineer','floating',self.cid,READ_TOOLS)
        tools=AuthorizedTools(self.g.registry,self.g.store,auth)
        with self.assertRaises(ValueError):await tools.invoke('inventory.read',{'role':'admin','device_id':'R2'},auth)

    async def test_verification_source_is_independent_of_mutable_graph_results(self):
        from llm.orchestration.verification import verify_records
        auth=ToolAuthorization('alice','engineer','floating',self.cid,READ_TOOLS)
        tools=AuthorizedTools(self.g.registry,self.g.store,auth)
        result=await tools.invoke('inventory.read',{},auth)
        result.data['devices'][0]['management_ip']='8.8.8.8'
        context=[{'tool':'inventory.read','data':result.data,'evidence_ids':[e.id for e in result.evidence]}]
        self.assertEqual(verify_records(context,result.evidence,tools.results)['status'],'failed')

    async def test_tool_timeout_is_unavailable_and_budget_is_enforced(self):
        auth=ToolAuthorization('alice','engineer','floating',self.cid,READ_TOOLS)
        tools=AuthorizedTools(self.g.registry,self.g.store,auth,max_calls=1)
        with patch.object(self.g.registry,'invoke',AsyncMock(side_effect=asyncio.TimeoutError)):
            r=await tools.invoke('inventory.read',{},auth)
        self.assertEqual(r.status,'unavailable')
        with self.assertRaises(HTTPException):await tools.invoke('inventory.read',{},auth)

    async def test_graph_deadline_cancels_without_replay(self):
        from llm.orchestration.engine import run
        async def slow(*a,**k):await asyncio.sleep(1)
        auth=ToolAuthorization('alice','engineer','floating',self.cid,READ_TOOLS)
        with patch('llm.orchestration.engine.select_context',slow),self.assertRaises(asyncio.TimeoutError):
            await run(self.g,self.cid,self.user,'floating',TurnRequest(request_id=uuid4(),prompt='hello'),auth,[],[],None,{'devices':[]},timeout=.01)

    async def test_user_surface_isolation_and_idempotency(self):
        body=TurnRequest(request_id=uuid4(),prompt='Show R2 interfaces')
        a=await self.g.turn(self.cid,self.user,body)
        with patch('llm.orchestration.engine.run',AsyncMock()) as run:
            b=await self.g.turn(self.cid,self.user,body)
        run.assert_not_awaited();self.assertEqual(a,b)
        with self.assertRaises(HTTPException):await self.g.turn(self.cid,{'username':'bob','role':'admin'},body)
        studio=self.g.store.create('alice','studio')['id']
        self.assertEqual(self.g.store.history(studio,self.user),[])
        r=await self.ask('Show R1 interfaces',identity=studio)
        self.assertNotIn('agent',r.context_coverage)

    async def test_studio_v9_and_floating_write_boundaries(self):
        studio=self.g.store.create('alice','studio')['id']
        route=SemanticRoute(intent='generate_native')
        with patch('llm.gateway_routing.select_context',AsyncMock(return_value=route)),patch('llm.orchestration.engine.select_context',AsyncMock(return_value=route)),patch.object(self.g.registry,'invoke',AsyncMock(return_value=ToolResult(status='success',data={'operations':['ospf','bgp']}))) as invoke:
            r=await self.ask('Generate OSPF and BGP native configuration',identity=studio)
            self.assertEqual(r.kind,'generation_preview');self.assertEqual(invoke.call_args.args[0],'v9.preview')
            invoke.reset_mock()
            r=await self.ask('Generate OSPF and BGP native configuration')
            self.assertEqual(r.kind,'clarification');invoke.assert_not_awaited()

    async def test_existing_public_api_returns_verified_graph_result(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from llm.gateway_api import router,require_ai_user
        app=FastAPI();app.state.local_db=self.db;app.include_router(router)
        app.dependency_overrides[require_ai_user]=lambda:{**self.user,'user_id':1}
        with TestClient(app) as client:
            body={'request_id':str(uuid4()),'prompt':'What interfaces does R2 have?'}
            r=client.post('/api/v1/ai/conversations/'+self.cid+'/turns',json=body)
            self.assertEqual(r.status_code,200,r.text)
            self.assertEqual(r.json()['context_coverage']['agent']['verification']['status'],'verified')
            self.assertIn('10.1.1.2',r.json()['answer'])
            again=client.post('/api/v1/ai/conversations/'+self.cid+'/turns',json=body)
            self.assertEqual(again.json(),r.json())
            forged=client.post('/api/v1/ai/conversations/'+self.cid+'/turns',json={**body,'role':'admin'})
            self.assertEqual(forged.status_code,422)

    async def test_document_route_delegates_to_existing_service(self):
        from llm.gateway_documents import upload_attachment
        await upload_attachment(self.db,self.cid,'alice','readme.txt',b'OSPF area 7 is recorded in this document.')
        route=SemanticRoute(intent='analyze_files',use_attachments=True)
        with patch('llm.orchestration.engine.select_context',AsyncMock(return_value=route)),patch('local_providers.chat.generate',AsyncMock(return_value=('The document specifies area 7.','test'))):
            r=await self.ask('Read the uploaded file')
        self.assertIn('area 7',r.answer);self.assertEqual(r.evidence[0].origin,'user_supplied')
        self.assertEqual(r.context_coverage['agent']['tool_calls'],0)

    async def test_documentation_uses_shared_authorized_retrieval(self):
        route=SemanticRoute(intent='answer',network_domains=['knowledge'],network_request='Explain OSPF')
        ref=Evidence(id='doc-source',source='reference.md',origin='stored',authority='reference_only')
        with patch('llm.orchestration.engine.select_context',AsyncMock(return_value=route)),patch('llm.gateway_knowledge.documentation_context',return_value=([{'source':'reference.md','text':'OSPF uses a link-state database.'}],[ref])),patch('local_providers.chat.generate',AsyncMock(return_value=('OSPF uses a link-state database.','test'))):
            r=await self.ask('Explain OSPF using documentation')
        self.assertEqual(r.context_coverage['agent']['tool_calls'],1)
        self.assertEqual(r.observations[0]['tool'],'knowledge.search')
        self.assertEqual(r.evidence[0].authority,'reference_only')
        self.assertIn('provenance only',r.context_coverage['agent']['verification']['scope'])

    async def test_mismatched_graph_facts_are_not_exposed(self):
        with patch('llm.orchestration.engine.verify_records',return_value={'status':'failed'}),patch('llm.orchestration.engine.release_answer',return_value=('Unverified source facts. No conclusion.',{'status':'failed'})):
            r=await self.ask('Show R2 interfaces')
        self.assertEqual(r.status,'unavailable');self.assertEqual(r.observations,[]);self.assertEqual(r.evidence,[])

    async def test_rollback_avoids_graph(self):
        with patch.dict(os.environ,{'COGNISHIELD_AI_ENGINE':'legacy'}),patch('llm.orchestration.engine.run',AsyncMock()) as run:
            r=await self.ask('Show R2 interfaces')
        run.assert_not_awaited();self.assertIn('10.1.1.2',r.answer);self.assertNotIn('agent',r.context_coverage)


class VerificationTests(unittest.TestCase):
    def test_forged_value_is_rejected_and_fluent_hallucination_is_reconstructed(self):
        data={'devices':[{'id':2,'hostname':'R2','management_ip':'192.168.1.251','interfaces':[{'id':3,'name':'Gi0/1','ip_address':'10.1.1.2'}]}]}
        ref=Evidence(id='source',source='sqlite.inventory',origin='stored')
        authoritative=[('inventory.read',ToolResult(status='success',data=data,evidence=[ref]))]
        context=[{'tool':'inventory.read','data':copy.deepcopy(data),'status':'success','evidence_ids':['source']}]
        answer,validation=release_answer('R2 has interface Gi0/1 with IP 8.8.8.8 [S1]',context,[ref],authoritative,['interfaces'])
        self.assertTrue(validation['reconstructed']);self.assertNotIn('8.8.8.8',answer);self.assertIn('10.1.1.2',answer)
        context[0]['data']['devices'][0]['interfaces'][0]['ip_address']='8.8.8.8'
        answer,validation=release_answer('',context,[ref],authoritative,['interfaces'])
        self.assertEqual(validation['status'],'failed');self.assertNotIn('8.8.8.8',answer)

    def test_forged_provenance_is_rejected(self):
        ref=Evidence(id='source',source='sqlite.inventory',origin='stored')
        answer,state=release_answer('',[],[ref.model_copy(update={'origin':'live'})],[('inventory.read',ToolResult(status='success',data={},evidence=[ref]))])
        self.assertEqual(state['status'],'failed')

    def test_forged_counts_and_paths_do_not_pass_with_valid_citation(self):
        ref=Evidence(id='source',source='sqlite.inventory',origin='stored')
        data={'devices':[],'summary':{'device_count':999}}
        _,state=release_answer('',[{'tool':'inventory.read','data':data,'evidence_ids':['source']}],[ref],[('inventory.read',ToolResult(status='success',data={'devices':[]},evidence=[ref]))])
        self.assertEqual(state['status'],'failed')
        data={'nodes':[],'links':[],'graph_path':['R99']}
        _,state=release_answer('',[{'tool':'network.topology','data':data,'evidence_ids':['source']}],[ref],[('network.topology',ToolResult(status='success',data={'nodes':[],'links':[],'graph_path':None},evidence=[ref]))])
        self.assertEqual(state['status'],'failed')


if __name__=='__main__':unittest.main()
