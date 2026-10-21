"""Behavioral contracts: real context/tool/output boundaries; disposable SQLite only."""
import os
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from db.manager import DatabaseManager
from llm.gateway import AIGateway
from llm.gateway_documents import upload_attachment, build_context
from llm.gateway_models import TurnRequest, ToolResult
from llm.gateway_store import ensure_schema


class IntelligenceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Other suites import their engine settings during collection. Bind this
        # legacy contract fixture per test, rather than leaking import-order state.
        environment=patch.dict(os.environ,{'COGNISHIELD_SEMANTIC_EMBEDDINGS':'0','COGNISHIELD_AI_ENGINE':'legacy',
            'COGNISHIELD_AI_PLANNING':'0','COGNISHIELD_AI_SYNTHESIS':'0'})
        environment.start();self.addCleanup(environment.stop)
        self.folder=tempfile.TemporaryDirectory(); self.addCleanup(self.folder.cleanup)
        self.db=DatabaseManager(str(Path(self.folder.name)/'behavior.db'))
        self.db.initialize(); ensure_schema(self.db); self.addCleanup(self.db.close)
        assert Path(self.db._db_path).resolve().is_relative_to(Path(self.folder.name).resolve())
        self.gateway=AIGateway(self.db); self.user={'username':'tester','role':'engineer'}
        self.editor=dict(document_id='doc',path='playbooks/ospf.cfg',content='router ospf 2\n router-id 192.0.2.9\n! unsaved',language='plaintext',model_id='m',model_version=2,buffer_epoch=1,saved_revision=0,is_dirty=True,read_only=False)

    async def test_topic_switch_excludes_old_editor_attachment_and_history(self):
        identity=self.gateway.store.create('tester','studio')['id']
        await upload_attachment(self.db,identity,'tester','old.cfg',b'OLD_CONFIGURATION_MARKER')
        model=AsyncMock(side_effect=[('{"intent":"answer"}','test'),('1 + 1 = 2.','test')])
        with patch('local_providers.chat.generate',model),patch.object(self.gateway.registry,'invoke',AsyncMock()) as invoke:
            result=await self.gateway.turn(identity,self.user,TurnRequest(request_id=uuid4(),prompt='Hello, how much is 1 + 1?',editor=self.editor))
        invoke.assert_not_awaited()
        supplied=json.dumps(model.call_args.args)
        self.assertNotIn('OLD_CONFIGURATION_MARKER',supplied); self.assertNotIn('192.0.2.9',supplied)
        self.assertEqual(result.evidence,[]); self.assertEqual(result.answer,'1 + 1 = 2.')

    async def test_attachment_actual_text_human_pages_and_followup_both_surfaces(self):
        for kind in ['studio','floating']:
            identity=self.gateway.store.create('tester',kind)['id']
            attached=await upload_attachment(self.db,identity,'tester','ospf.txt',b'OSPF area 7 is a stub area. Router ID 192.0.2.55.')
            for prompt in ['Read the attached content','What area number is mentioned?']:
                model=AsyncMock(side_effect=[('{"intent":"analyze_files"}','test'),('The document specifies stub area 7.','test')])
                with patch('local_providers.chat.generate',model):
                    result=await self.gateway.turn(identity,self.user,TurnRequest(request_id=uuid4(),prompt=prompt))
                supplied=json.dumps(model.call_args.args)
                self.assertIn('OSPF area 7',supplied); self.assertNotIn(attached['id'],supplied)
                self.assertEqual(result.evidence[0].source,'ospf.txt'); self.assertIsNone(result.preview)

    async def test_studio_generation_invokes_v9_and_floating_does_not(self):
        for kind in ['studio','floating']:
            identity=self.gateway.store.create('tester',kind)['id']
            with patch('local_providers.chat.generate',AsyncMock(return_value=('{"intent":"generate_native"}','test'))),patch.object(self.gateway.registry,'invoke',AsyncMock(return_value=ToolResult(status='success',data={'tasks':['ospf','bgp','static_route']}))) as invoke:
                result=await self.gateway.turn(identity,self.user,TurnRequest(request_id=uuid4(),prompt='Configure OSPF, BGP and a static route on R1'))
            if kind=='studio':
                self.assertEqual(invoke.call_args.args[0],'v9.preview'); self.assertEqual(result.kind,'generation_preview')
            else:
                invoke.assert_not_awaited(); self.assertEqual(result.kind,'clarification')

    async def test_semantic_network_selection_preserves_latest_device(self):
        identity=self.gateway.store.create('tester','floating')['id']
        with self.db._connect() as c: c.execute("INSERT INTO devices(hostname,vendor) VALUES ('R1','cisco')")
        model=AsyncMock(side_effect=[('{"intent":"network"}','test'),('{"network_domains":["inventory"],"request":"unrelated R9"}','test'),('R1 is stored.','test')])
        with patch('local_providers.chat.generate',model):
            result=await self.gateway.turn(identity,self.user,TurnRequest(request_id=uuid4(),prompt='What do we know about R1?'))
        self.assertEqual(result.context_coverage['routing']['network_domains'],['inventory'])
        model.assert_not_awaited()
        self.assertIn('R1',result.answer); self.assertNotIn('R9',result.answer)

    async def test_legacy_pdf_coverage_is_not_full_visual_coverage(self):
        identity=self.gateway.store.create('tester','floating')['id']
        with self.db._connect() as c:
            c.execute('INSERT INTO ai_attachments(id,conversation_id,owner,name,digest,byte_size,segments) VALUES (?,?,?,?,?,?,?)',(str(uuid4()),identity,'tester','old.pdf','d',20,json.dumps([{'page':1,'text':'Figure caption'}])))
        _,_,coverage=build_context(self.db,identity,self.user,TurnRequest(request_id=uuid4(),prompt='Read this PDF'))
        self.assertFalse(coverage['complete']); self.assertIn('re-upload',coverage['limitations'][0])

    async def test_missing_model_and_invalid_router_never_invoke_actions(self):
        from fastapi import HTTPException
        identity=self.gateway.store.create('tester','studio')['id']
        for value in [HTTPException(503,'Ollama unavailable'),('not JSON','test')]:
            model=AsyncMock(side_effect=value) if isinstance(value,Exception) else AsyncMock(return_value=value)
            with patch('local_providers.chat.generate',model),patch.object(self.gateway.registry,'invoke',AsyncMock()) as invoke:
                result=await self.gateway.turn(identity,self.user,TurnRequest(request_id=uuid4(),prompt='Change that'))
            invoke.assert_not_awaited(); self.assertIn(result.status,['unavailable','clarification_required'])

    async def test_handoff_is_owned_reviewed_idempotent_and_does_not_submit(self):
        from llm.gateway_handoff import prepare,accept
        from fastapi import HTTPException
        from llm.gateway_models import Evidence
        identity=self.gateway.store.create('tester','floating')['id']; request=str(uuid4())
        self.gateway.store.begin(identity,'tester',request,'hash','Inspect OSPF')
        evidence=Evidence(id='recorded-evidence',source='sqlite.inventory',origin='stored')
        self.gateway.store.finish(identity,'tester',request,{'answer':'Recorded investigation','evidence':[evidence.model_dump()]})
        handoff=prepare(self.gateway,self.user,identity,request,'Review OSPF timers and propose a correction')
        with self.assertRaises(HTTPException): accept(self.gateway,{'username':'other','role':'admin'},handoff['id'])
        with self.assertRaises(HTTPException): accept(self.gateway,{'username':'tester','role':'auditor'},handoff['id'])
        accepted=accept(self.gateway,self.user,handoff['id'])
        self.assertEqual(accept(self.gateway,self.user,handoff['id'])['conversation_id'],accepted['conversation_id'])
        self.assertEqual(self.gateway.store.history(accepted['conversation_id']),[])
        self.assertEqual(self.gateway.store.get(accepted['conversation_id'],'tester')['assistant_kind'],'studio')
        with self.db._connect() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM ai_turns WHERE conversation_id=?',(accepted['conversation_id'],)).fetchone()[0],0)
            c.execute("DELETE FROM ai_evidence WHERE id='recorded-evidence'")
        with self.assertRaises(HTTPException): accept(self.gateway,self.user,handoff['id'])

    async def test_empty_network_investigation_never_asks_model_for_a_diagnosis(self):
        from llm.gateway_routing import SemanticRoute
        identity=self.gateway.store.create('tester','floating')['id']
        with self.db._connect() as c: c.execute("INSERT INTO devices(hostname,vendor) VALUES ('R1','cisco')")
        route=SemanticRoute(intent='answer',network_domains=['topology','telemetry','syslog','incidents','configuration'])
        with patch('llm.gateway_routing.select_context',AsyncMock(return_value=route)),patch('local_providers.chat.generate',AsyncMock()) as model:
            result=await self.gateway.turn(identity,self.user,TurnRequest(request_id=uuid4(),prompt='Investigate R1 dropping packets'))
        model.assert_not_awaited()
        self.assertIn('No network root cause can be established',result.answer)
        self.assertTrue(result.observations)
        self.assertNotIn('unauthorized',result.answer)

    async def test_handoff_preserves_real_observations_without_submitting_and_rechecks_access(self):
        from llm.gateway_handoff import prepare,accept,history_context
        from llm.gateway_models import Evidence
        identity=self.gateway.store.create('tester','floating')['id']; request=str(uuid4())
        self.gateway.store.begin(identity,'tester',request,'hash','Inspect OSPF')
        evidence=Evidence(id='handoff-record',source='sqlite.config_snapshots',origin='stored')
        observations=[{'tool':'network.configuration','status':'success','data':{'records':[
            {'owner_username':'tester','config_text':'OSPF_OWNED_MARKER'},
            {'owner_username':'someone_else','config_text':'OTHER_OWNER_MARKER'}]}}]
        self.gateway.store.finish(identity,'tester',request,{'answer':'Old assistant claim','evidence':[evidence.model_dump()],'observations':observations})
        record=prepare(self.gateway,self.user,identity,request,'Explain this investigation')
        self.assertNotIn('OTHER_OWNER_MARKER',json.dumps(record['observations']))
        accepted=accept(self.gateway,self.user,record['id'])
        history=self.gateway.store.history(accepted['conversation_id'],self.user)
        self.assertIn('OSPF_OWNED_MARKER',json.dumps(history))
        self.assertNotIn('OTHER_OWNER_MARKER',json.dumps(history))
        self.assertNotIn('Old assistant claim',json.dumps(history))
        self.assertIn('recorded timestamps',accepted['warning'])
        with self.db._connect() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM ai_turns WHERE conversation_id=?',(accepted['conversation_id'],)).fetchone()[0],0)
            c.execute("DELETE FROM ai_evidence WHERE id='handoff-record'")
        self.assertEqual(history_context(self.db,accepted['conversation_id'],self.user),[])

    async def test_references_use_fresh_rows_and_exact_interface_scope(self):
        identity=self.gateway.store.create('tester','floating')['id']
        with self.db._connect() as c:
            c.execute("INSERT INTO devices(id,hostname,vendor,management_ip) VALUES(1,'R2','cisco','192.168.1.251')")
            c.execute("INSERT INTO interfaces(id,device_id,name,ip_address) VALUES(1,1,'GigabitEthernet0/0','192.168.1.251')")
            c.execute("INSERT INTO interfaces(id,device_id,name,ip_address) VALUES(2,1,'GigabiEthernet0/1','10.1.1.2')")
        async def ask(prompt):return await self.gateway.turn(identity,self.user,TurnRequest(request_id=uuid4(),prompt=prompt))
        with patch('local_providers.chat.generate',AsyncMock()) as model:
            first=await ask("What are R2's interfaces?")
            self.assertIn('GigabiEthernet0/1',first.answer)
            with self.db._connect() as c:c.execute("UPDATE interfaces SET ip_address='10.2.2.2' WHERE id=2")
            checked=await ask('Are you sure?')
            self.assertIn('10.2.2.2',checked.answer);self.assertNotIn('10.1.1.2',checked.answer)
            ambiguous=await ask('What is its IP?')
            self.assertEqual(ambiguous.kind,'clarification')
            chosen=await ask('What is the IP of R2 GigabiEthernet0/1?')
            self.assertIn('10.2.2.2',chosen.answer);self.assertNotIn('192.168.1.251',chosen.answer)
            unknown=await ask('What is the IP of R2 Loopback99?')
            self.assertEqual(unknown.kind,'clarification')
        model.assert_not_awaited()

    async def test_explicit_active_buffer_read_survives_classifier_error(self):
        identity=self.gateway.store.create('tester','studio')['id']
        with patch('local_providers.chat.generate',AsyncMock(return_value=('The comment is ! unsaved.','test'))) as model:
            result=await self.gateway.turn(identity,self.user,TurnRequest(request_id=uuid4(),prompt='Explain the active configuration and quote its unsaved comment. Do not modify it.',editor=self.editor))
        self.assertEqual(model.await_count,1)
        self.assertTrue(result.context_coverage['routing']['editor'])
        self.assertIn('! unsaved',str(model.call_args))
        self.assertIsNone(result.proposal)

    async def test_saved_configs_and_plural_syslogs_do_not_read_attachments(self):
        identity=self.gateway.store.create('tester','floating')['id']
        with self.db._connect() as c:c.execute("INSERT INTO devices(hostname) VALUES('R1')")
        await upload_attachment(self.db,identity,'tester','unrelated.txt',b'IGNORE_NETWORK_OLD_DOC')
        for prompt,tool in [('Show saved configs','network.configuration'),('Show R1 syslogs','network.syslog')]:
            result=await self.gateway.turn(identity,self.user,TurnRequest(request_id=uuid4(),prompt=prompt))
            self.assertEqual([r['tool'] for r in result.observations],[tool])
            self.assertFalse(result.context_coverage['routing']['attachments'])
            self.assertNotIn('IGNORE_NETWORK_OLD_DOC',result.answer)

    async def test_cached_network_result_cannot_survive_role_change(self):
        from fastapi import HTTPException
        identity=self.gateway.store.create('tester','floating')['id']
        with self.db._connect() as c:c.execute("INSERT INTO devices(hostname) VALUES('R1')")
        body=TurnRequest(request_id=uuid4(),prompt='Show R1 interfaces')
        await self.gateway.turn(identity,self.user,body)
        with self.assertRaises(HTTPException) as error:
            await self.gateway.turn(identity,{**self.user,'role':'auditor'},body)
        self.assertEqual(error.exception.status_code,403)

    async def test_image_invalid_oversize_and_ocr_failure(self):
        from fastapi import HTTPException
        identity=self.gateway.store.create('tester','floating')['id']
        with self.assertRaises(HTTPException): await upload_attachment(self.db,identity,'tester','huge.png',b'x'*(10*1024*1024+1))
        with patch('llm.gateway_documents.extract_pdf',return_value=[{'page':1,'text':'','limitation':'OCR unavailable'}]):
            with self.assertRaises(HTTPException) as error: await upload_attachment(self.db,identity,'tester','scan.png',b'not-image')
        self.assertEqual(error.exception.detail,'OCR unavailable')

    async def test_ocr_model_is_not_a_chat_or_diagram_model(self):
        import httpx
        from local_providers.chat import runtime
        from llm.gateway_vision import vision_context
        response=httpx.Response(200,json={'models':[{'name':'maternion/LightOnOCR-2:1b'},{'name':'nomic-embed-text:latest'},{'name':'qwen2.5:1.5b'}]},request=httpx.Request('GET','http://localhost/api/tags'))
        client=AsyncMock(); client.__aenter__.return_value=client; client.get.return_value=response
        with patch('local_providers.chat.httpx.AsyncClient',return_value=client),patch.dict(os.environ,{'COGNISHIELD_LOCAL_OLLAMA_MODEL':'auto'}):
            state=await runtime()
        self.assertEqual(state['active_model'],'qwen2.5:1.5b')
        self.assertEqual(state['providers'][0]['models'],['qwen2.5:1.5b'])
        with patch.dict(os.environ,{'COGNISHIELD_VISION_MODEL':'maternion/LightOnOCR-2:1b'}),patch('llm.gateway_vision.normalize_images') as decode:
            self.assertEqual(await vision_context(self.db,'none','tester',TurnRequest(request_id=uuid4(),prompt='Explain this diagram')),([],[],None))
        decode.assert_not_called()

    async def test_vision_missing_capability_does_not_send_images(self):
        from llm.gateway_vision import vision_context
        import httpx
        identity=self.gateway.store.create('tester','floating')['id']
        response=httpx.Response(200,json={'capabilities':['completion']},request=httpx.Request('POST','http://localhost/api/show'))
        client=AsyncMock(); client.__aenter__.return_value=client; client.post.return_value=response
        with patch('llm.gateway_vision.httpx.AsyncClient',return_value=client),patch('llm.gateway_vision.normalize_images') as decode:
            images,labels,model=await vision_context(self.db,identity,'tester',TurnRequest(request_id=uuid4(),prompt='Read diagram',model='text-only'))
        self.assertEqual(images,[]);self.assertEqual(labels,[]);self.assertIsNone(model);decode.assert_not_called()

if __name__=='__main__': unittest.main()
