"""Isolated shared gateway authorization, provenance, persistence and concurrency."""
import asyncio
import os
os.environ["COGNISHIELD_SEMANTIC_EMBEDDINGS"]="0"
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['COGNISHIELD_MODE'] = 'local_lab'
API_ROOT = tempfile.TemporaryDirectory(prefix='cognishield-shared-api-')
os.environ['COGNISHIELD_DB_PATH'] = str(Path(API_ROOT.name)/'api.db')
os.environ['COGNISHIELD_KNOWLEDGE_ROOT'] = str(Path(__file__).resolve().parents[2]/'tmp/shared-ai-not-initialized')
os.environ['AUTH_BYPASS_ROLES'] = '0'

from fastapi import HTTPException
from db.manager import DatabaseManager
from llm.gateway import AIGateway
from llm.gateway_models import TurnRequest, StrictModel, ToolResult
from llm.gateway_store import ensure_schema
from llm.tools import Capability, ToolAuthorization, ToolRegistry


class SharedAITests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.db = DatabaseManager(str(Path(self.folder.name) / 'test.db'))
        self.db.initialize()
        ensure_schema(self.db)
        self.addCleanup(self.db.close)
        self.gateway = AIGateway(self.db)
        self.user = dict(username='alice', role='engineer')
        self.conversation = self.gateway.store.create('alice', 'floating')['id']

    async def test_shared_provider_provenance_and_idempotency(self):
        with self.db._connect() as c:
            c.execute("INSERT INTO devices(hostname,vendor,ssh_password) VALUES ('R1','cisco_xe','must-not-leak')")
        body = TurnRequest(request_id=uuid4(), prompt='Which devices are stored?')
        model = AsyncMock(side_effect=[('{"intent":"network"}', 'test-model'), ('{"network_domains":["inventory"],"request":"Which devices are stored?"}', 'test-model'), ('Stored R1; reachability is not measured.', 'test-model')])
        with patch('local_providers.chat.generate', model):
            first = await self.gateway.turn(self.conversation, self.user, body)
            second = await AIGateway(self.db).turn(self.conversation, self.user, body)
        self.assertEqual(first, second)
        self.assertEqual(model.await_count, 2)
        self.assertEqual(first.evidence[0].origin, 'stored')
        self.assertNotIn('must-not-leak', json.dumps(model.call_args.args))
        self.assertEqual(len(self.gateway.store.history(self.conversation)), 2)

    async def test_empty_allowlist_and_surface_cannot_escalate(self):
        auth = ToolAuthorization('alice', 'admin', 'floating', self.conversation, frozenset())
        with self.assertRaises(HTTPException) as error:
            await self.gateway.registry.invoke('inventory.read', {}, auth)
        self.assertEqual(error.exception.status_code, 403)
        with self.assertRaises(PermissionError):
            self.gateway.registry.execute('inventory.read', {})
        with self.assertRaises(HTTPException):
            await self.gateway.registry.invoke('workspace.write', {}, auth)
        forged = ToolAuthorization('alice','admin','floating',self.conversation,frozenset({'document.propose','v9.preview'}))
        for name in ['document.propose','v9.preview']:
            with self.assertRaises(HTTPException): await self.gateway.registry.invoke(name,{},forged)
        missing_permission=ToolAuthorization('alice','admin','studio',self.conversation,frozenset({'inventory.read'}),permissions=frozenset())
        with self.assertRaises(HTTPException): await self.gateway.registry.invoke('inventory.read',{},missing_permission)

    async def test_cached_proposal_rechecks_current_role(self):
        session=self.gateway.store.create('alice','studio')['id']
        body=TurnRequest(request_id=uuid4(),prompt='Change this document')
        with patch.object(self.gateway, '_answer', AsyncMock(return_value=__import__('llm.gateway_models',fromlist=['TurnResponse']).TurnResponse(
            request_id=str(body.request_id),status='success',kind='generation_preview',answer='Review',preview={}))):
            await self.gateway.turn(session,self.user,body)
        with self.assertRaises(HTTPException):
            await self.gateway.turn(session,dict(username='alice',role='auditor'),body)

    async def test_explicit_request_constraints_override_model_route(self):
        from llm.gateway import Route,constrain_route
        self.assertEqual(constrain_route(Route(intent='generate_playbook'),'Generate native Cisco configuration').intent,'generate_native')
        self.assertEqual(constrain_route(Route(intent='edit'),'Explain only; do not modify').intent,'explain')
        self.assertEqual(constrain_route(Route(intent='generate_native'),'Generate native config and an Ansible playbook').intent,'clarify')

    async def test_context_reports_partial_long_single_line(self):
        from llm.gateway_documents import build_context
        session=self.gateway.store.create('alice','studio')['id']
        body=TurnRequest(request_id=uuid4(),prompt='Explain this',editor=dict(document_id='playbooks/long.txt',path='playbooks/long.txt',
            content='x'*50000,language='plaintext',model_id='m',model_version=1,buffer_epoch=0,saved_revision=0,is_dirty=True,read_only=False))
        context,evidence,coverage=build_context(self.db,session,self.user,body)
        self.assertFalse(coverage['complete']);self.assertGreater(coverage['included_characters'],0)
        self.assertLessEqual(coverage['included_characters'],24000)
        self.assertTrue(evidence)

    async def test_owners_surfaces_and_request_reuse(self):
        with self.assertRaises(HTTPException):
            self.gateway.store.get(self.conversation, 'bob')
        with self.assertRaises(HTTPException):
            self.gateway.store.create('alice', 'studio', self.conversation)
        self.assertEqual(self.gateway.store.list('alice', 'studio'), [])
        self.gateway.store.begin(self.conversation, 'alice', 'req', 'hash', 'hello')
        with self.assertRaises(HTTPException):
            self.gateway.store.begin(self.conversation, 'alice', 'other', 'hash', 'hello')
        self.gateway.store.cancel(self.conversation, 'alice', 'req')
        with self.assertRaises(HTTPException):
            self.gateway.store.finish(self.conversation, 'alice', 'req', {'answer':'late'})

    async def test_missing_model_is_not_a_fake_success(self):
        with patch('local_providers.chat.generate', AsyncMock(side_effect=HTTPException(503, 'Ollama unavailable'))):
            result = await self.gateway.turn(self.conversation, self.user, TurnRequest(request_id=uuid4(), prompt='Hello'))
        self.assertEqual(result.status, 'unavailable')
        self.assertFalse(result.execution_available)

    async def test_floating_rejects_document_payload(self):
        body = TurnRequest(request_id=uuid4(), prompt='Explain', editor=dict(document_id='x',path='playbooks/x.yml',content='secret',language='yaml',model_id='m',model_version=1,buffer_epoch=0,saved_revision=0,is_dirty=True,read_only=False))
        with self.assertRaises(HTTPException) as error:
            await self.gateway.turn(self.conversation, self.user, body)
        self.assertEqual(error.exception.status_code, 403)

    async def test_documents_unsaved_selection_and_guarded_patch(self):
        from llm.gateway_documents import build_context,propose_edit
        from local_providers.authoring import AuthoringStore
        path='playbooks/shared_test.py'
        AuthoringStore(self.db).mutate('ansible',path,'x = 1\n','alice','create')
        session=self.gateway.store.create('alice','studio')['id']
        body=TurnRequest(request_id=uuid4(),prompt='Add type annotations',editor=dict(document_id=path,path=path,
            content='x = 1\n# unsaved\n',language='python',model_id='model',model_version=2,buffer_epoch=1,saved_revision=1,is_dirty=True,read_only=False,
            selection={'text':'x = 1','start_line':1,'end_line':1}))
        context,evidence,coverage=build_context(self.db,session,self.user,body)
        self.assertIn('# unsaved',context[0]['text']);self.assertTrue(coverage['complete']);self.assertEqual(evidence[0].origin,'user_supplied')
        with patch('local_providers.chat.generate',AsyncMock(return_value=(json.dumps({'replacements':[{'old_text':'x = 1','new_text':'x: int = 1'}]}),'test'))):
            proposal,_=await propose_edit(self.db,self.user,body,context)
        self.assertIn('# unsaved',proposal['suggested'])
        self.assertEqual(AuthoringStore(self.db).read('ansible',path),'x = 1\n')
        AuthoringStore(self.db).mutate('ansible',path,'x = 2\n','other',expected_revision=1)
        with self.assertRaises(HTTPException):
            await propose_edit(self.db,self.user,body,context)

    async def test_attachment_ownership_followup_and_no_binary_fallback(self):
        from llm.gateway_documents import upload_attachment,build_context
        session=self.gateway.store.create('alice','studio')['id']
        attached=await upload_attachment(self.db,session,'alice','router.cfg',b'router ospf 1\n network 192.0.2.0 0.0.0.255 area 0\n')
        body=TurnRequest(request_id=uuid4(),prompt='Explain the OSPF configuration')
        context,evidence,coverage=build_context(self.db,session,self.user,body)
        self.assertIn('router ospf',context[0]['text']);self.assertTrue(coverage['complete'])
        other=self.gateway.store.create('alice','studio')['id']
        with self.assertRaises(HTTPException):
            build_context(self.db,other,self.user,TurnRequest(request_id=uuid4(),prompt='read',attachment_ids=[attached['id']]))
        with self.assertRaises(HTTPException): await upload_attachment(self.db,session,'alice','binary.cfg',b'\x00bad')
        with self.assertRaises(HTTPException): await upload_attachment(self.db,session,'alice','big.txt',b'x'*(10*1024*1024+1))

    async def test_patch_rejects_ambiguity_invalid_python_and_overlaps(self):
        from llm.gateway_documents import Patch,apply_patch_exact,structural_validation
        for content,replacements in [('aa aa',[{'old_text':'aa','new_text':'b'}]),('abcdef',[{'old_text':'abc','new_text':'a'},{'old_text':'bc','new_text':'b'}])]:
            with self.assertRaises(HTTPException): apply_patch_exact(content,Patch(replacements=replacements))
        with self.assertRaises(HTTPException): structural_validation('def broken(','.py')
        original='\ufeffx = 1\r\n# \u03bb\r\n'
        self.assertEqual(apply_patch_exact(original,Patch(replacements=[{'old_text':'x = 1','new_text':'x: int = 1'}])),original.replace('x = 1','x: int = 1'))

    async def test_revision_checked_saves(self):
        from local_providers.authoring import AuthoringStore
        store=AuthoringStore(self.db);path='playbooks/revision_test.yml'
        store.mutate('ansible',path,'---\n','alice','create',expected_revision=0)
        store.mutate('ansible',path,'---\n# saved\n','alice',expected_revision=1)
        with self.assertRaises(HTTPException) as error: store.mutate('ansible',path,'stale','alice',expected_revision=1)
        self.assertEqual(error.exception.status_code,409)
        self.assertIn('# saved',store.read('ansible',path))

    async def test_wsl_missing_containment_is_unavailable(self):
        from llm.gateway_validation import validate_ansible
        with patch.dict(os.environ,{'COGNISHIELD_WSL_VALIDATION_PROFILE':''}):
            result=validate_ansible('- hosts: validation_target\n  tasks: []\n')
        self.assertEqual(result['status'],'unavailable');self.assertEqual(result['device_testing'],'not_run')
        import subprocess
        forged=subprocess.CompletedProcess([],0,json.dumps({'status':'passed','syntax':'passed','lint':'passed','containment_verified':False}),'')
        with patch.dict(os.environ,{'COGNISHIELD_WSL_VALIDATION_PROFILE':'/opt/cognishield-validator/test'}),patch('subprocess.run',return_value=forged):
            result=validate_ansible('- hosts: validation_target\n  tasks: []\n')
        self.assertEqual(result['status'],'unavailable');self.assertEqual(result['syntax'],'not_run')

    async def test_studio_explanation_is_read_only_and_auditor_cannot_edit(self):
        session=self.gateway.store.create('alice','studio')['id']
        body=TurnRequest(request_id=uuid4(),prompt='Why is merged used?',editor=dict(document_id='playbooks/read.yml',path='playbooks/read.yml',content='state: merged\n# unsaved',language='yaml',model_id='m',model_version=1,buffer_epoch=0,saved_revision=0,is_dirty=True,read_only=False))
        with patch('local_providers.chat.generate',AsyncMock(side_effect=[('{"intent":"explain"}','test'),('Merged preserves unspecified entries.','test')])):
            result=await self.gateway.turn(session,self.user,body)
        self.assertEqual(result.kind,'answer');self.assertIsNone(result.proposal)
        body=body.model_copy(update={'request_id':uuid4(),'prompt':'Change this document'})
        with patch('local_providers.chat.generate',AsyncMock(return_value=('{"intent":"edit"}','test'))):
            result=await self.gateway.turn(session,dict(username='alice',role='auditor'),body)
        self.assertEqual(result.status,'denied')

    async def test_general_edit_runs_through_authorized_registry(self):
        from local_providers.authoring import AuthoringStore
        session=self.gateway.store.create('alice','studio')['id']
        path='playbooks/registry_edit.py'
        AuthoringStore(self.db).mutate('ansible',path,'x = 1\n','alice','create',expected_revision=0)
        body=TurnRequest(request_id=uuid4(),prompt='Edit x to 2',editor=dict(document_id=path,path=path,content='x = 1\n# unsaved\n',
            language='python',model_id='m',model_version=2,buffer_epoch=1,saved_revision=1,is_dirty=True,read_only=False))
        with patch('local_providers.chat.generate',AsyncMock(side_effect=[('{"intent":"edit"}','test'),
            ('{"replacements":[{"old_text":"x = 1","new_text":"x = 2"}]}','test')])):
            response=await self.gateway.turn(session,self.user,body)
        self.assertEqual(response.kind,'edit_proposal');self.assertIn('# unsaved',response.proposal['suggested'])
        self.assertEqual(AuthoringStore(self.db).read('ansible',path),'x = 1\n')


class SharedAPIIntegration(unittest.TestCase):
    def test_authenticated_surfaces_inventory_metadata_and_legacy_isolation(self):
        from fastapi.testclient import TestClient
        import local_app
        from auth.auth import create_access_token
        expected = Path(API_ROOT.name)/'api.db'
        # Test collection may import lab_config before this module sets its environment.
        # Pin the app's actual lifespan path, and assert it before making any mutation.
        with patch.object(local_app, 'DB_PATH', expected), patch('auth.auth._DB_PATH', expected), patch('auth.api._DB_PATH', expected), patch('netbox.api.DB_PATH', str(expected)), TestClient(local_app.app) as c:
            self.assertEqual(Path(local_app.db._db_path).resolve(), expected.resolve())
            self.assertEqual(Path(local_app.inventory._db()._db_path).resolve(), expected.resolve())
            preflight={'Origin':'http://127.0.0.1:5173','Access-Control-Request-Method':'GET','Access-Control-Request-Headers':'authorization,content-type','Access-Control-Request-Private-Network':'true'}
            self.assertEqual(c.options('/api/v1/ai/inventory',headers=preflight).status_code,200)
            self.assertEqual(c.options('/api/v1/ai/inventory',headers=preflight|{'Origin':'https://example.invalid'}).status_code,400)
            self.assertEqual(c.get('/api/v1/ai/inventory').status_code,401)
            self.assertEqual(c.get('/api/v1/ansible/chat-sessions').status_code,401)
            c.headers['Authorization']='Bearer '+create_access_token(1,'api-alice','admin')
            before=os.getenv('COGNISHIELD_LOCAL_OLLAMA_MODEL')
            state={'active_model':'one','providers':[{'name':'ollama','models':['one','two']}],'scope':'process'}
            with patch('local_providers.chat.runtime',AsyncMock(return_value=state)):
                selected=c.post('/api/v1/llm/chat/runtime',json={'provider':'ollama','model':'two'})
                self.assertEqual(selected.status_code,200);self.assertEqual(selected.json()['scope'],'request')
                self.assertEqual(c.get('/api/v1/llm/chat/runtime').json()['active_model'],'one')
            self.assertEqual(os.getenv('COGNISHIELD_LOCAL_OLLAMA_MODEL'),before)
            device=c.post('/api/v1/netbox/devices',json={'hostname':'shared-fact-check','vendor':'cisco_xe','os_version':'17.9'}).json()
            identity=device['id']
            from llm.gateway_inventory import facts_revision
            facts={'origin':'sample','model_family':'catalyst9300','source_refs':{'fixture':'isolated test only'},
                'capabilities':{'validated_policies':['c9300_vlan_rename_v1'],'vtp_mode':'transparent'},'vlans':[{'vlan_id':100,'name':'STAFF'}]}
            target=f'/api/v1/ai/inventory/{identity}/engineering-facts'
            saved=c.put(target,json={'facts':facts,'expected_revision':facts_revision({})})
            self.assertEqual(saved.status_code,200)
            self.assertEqual(c.put(target,json={'facts':facts,'expected_revision':facts_revision({})}).status_code,409)
            for unsafe in [facts|{'vendor':'juniper'},facts|{'interfaces':[{'name':'invented-port'}]}]:
                self.assertEqual(c.put(target,json={'facts':unsafe,'expected_revision':saved.json()['revision']}).status_code,422)
            import local_app
            from local_providers.v9_studio import inventory as v9_inventory
            projected=next(d for d in v9_inventory(local_app.db) if d['id']==str(identity))
            self.assertEqual(projected['engineering_facts_origin'],'sample');self.assertEqual(projected['vendor'],'cisco')
            floating=c.post('/api/v1/ai/conversations',json={'assistant_kind':'floating'}).json()
            studio=c.post('/api/v1/ai/conversations',json={'assistant_kind':'studio'}).json()
            listing=c.get('/api/v1/ansible/chat-sessions').json()['sessions']
            self.assertIn(studio['id'],[r['id'] for r in listing]);self.assertNotIn(floating['id'],[r['id'] for r in listing])
            self.assertEqual(c.put('/api/v1/ansible/chat-sessions/'+floating['id'],json={'id':floating['id'],'title':'forged','messages':[]}).status_code,404)
            self.assertEqual(c.get('/api/v1/ai/inventory').status_code,200)
            forged={'request_id':str(uuid4()),'prompt':'test','role':'admin'}
            self.assertEqual(c.post('/api/v1/ai/conversations/'+floating['id']+'/turns',json=forged).status_code,422)
            c.headers['Authorization']='Bearer '+create_access_token(2,'api-bob','admin')
            self.assertEqual(c.get('/api/v1/ai/conversations/'+studio['id']).status_code,404)


if __name__ == '__main__':
    unittest.main()
