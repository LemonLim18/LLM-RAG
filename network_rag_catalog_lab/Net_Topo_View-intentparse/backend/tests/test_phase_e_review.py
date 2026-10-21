"""Review authority tests. TEST-SENIOR records exist only in in-memory fixtures."""
import json,os,sqlite3,sys,tempfile,unittest
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'backend'),str(ROOT.parent/'network_rag_catalog_v2')]
from local_providers.knowledge_review import identity,fingerprint,initialize,approve,review_status,assert_activation_authorized,ACKNOWLEDGEMENT,publication_decision,authorize_activation,prepare_publication_methods,schema_sample
from app.knowledge.management import KnowledgeManagementService


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.connection=sqlite3.connect(':memory:');self.addCleanup(self.connection.close)
        self.base=Path(self.folder.name);self.service=KnowledgeManagementService(self.base)
        binding={'operation_id':'set_note','operation_version':1,'vendor':'cisco','platform':'iosxe','versions':['17.9'],
            'template_path':'data/templates/cisco/test/set_note/iosxe/template.j2','input_contract':{'fields':['description'],'optional_defaults':{},'derived':{}}}
        self.binding=binding
        self.draft={'revision':'TEST-REVISION-1','catalogs':{
            'categories':[{'category_id':'test','display_name':'Test','description':'Test fixtures only','status':'active'}],
            'parameters':[{'parameter_id':'description','display_name':'Description','description':'Test description','value_type':'string'}],
            'category_parameters':[{'category_id':'test','parameter_id':'description'}],
            'operations':[{'operation_id':'set_note','category_id':'test','display_name':'Set note','description':'Set a fixture interface description','status':'active','version':1,'schema_source':'registry','mapping_mode':'none'}],
            'operation_parameters':[{'operation_id':'set_note','operation_version':1,'category_id':'test','parameter_id':'description','field_path':'description','position':0,'required':True,'required_order':0}],
            'operation_rules':[{'operation_id':'set_note','operation_version':1,'field_path':'','keywords':{'type':'object','additionalProperties':False}},
                {'operation_id':'set_note','operation_version':1,'field_path':'description','keywords':{'minLength':1,'maxLength':40,'pattern':'^[A-Za-z0-9 ._-]+$'}}],
            'template_bindings':[binding],'context_rules':{'version':1,'operations':{}}},
            'sources':{binding['template_path']:b'description {{ description }}\n'}}
        self.method={'assumptions':['Fixture only; no device.'],'limitations':['Not vendor or device certified.'],'material_risks':['Review existing interface.'],
            'fixtures':[{'parameters':{'description':'Uplink'},'expected_output':'description Uplink\n'}],'invalid_inputs':[{}, {'description':'bad\nshutdown'},{'description':'Uplink','unexpected':True}]}
        initialize(self.connection,self.base/'releases')
        self.connection.execute('CREATE TABLE authoring_state(singleton INTEGER PRIMARY KEY,generation INTEGER)')
        self.connection.execute('INSERT INTO authoring_state VALUES(1,1)')
        self.connection.execute('INSERT INTO cognishield_method_specs VALUES (?,?)',(identity(binding),json.dumps(self.method)))

    def request(self,decision='approve'):
        value,_=fingerprint(self.draft,self.binding,self.method)
        return {'expected_revision':self.draft['revision'],'request_id':'TEST-REQUEST-001','acknowledgement':ACKNOWLEDGEMENT,'reason':'TEST fixture sign-off, never a human production approval',
            'decisions':[{'identity':identity(self.binding),'fingerprint':value,'decision':decision,'resolved_risks':self.method['material_risks']}]}

    def test_real_compiler_render_and_invalid_inputs_pass_without_external_certification(self):
        report=review_status(self.service,self.connection,self.draft,checks=True)
        row=report['rows'][0];self.assertEqual(row['checks']['status'],'PASS',row['checks']);self.assertFalse(row['approved'])
        self.assertEqual(row['certifications'],{'vendor_semantics':'NOT_VERIFIED','device':'NOT_RUN','ansible':'NOT_RUN'})

    def test_exact_approval_is_auditable_idempotent_and_reused(self):
        body=self.request();first=approve(self.service,self.connection,self.draft,body,'TEST-SENIOR',self.base/'releases')
        second=approve(self.service,self.connection,self.draft,body,'TEST-SENIOR',self.base/'releases')
        self.assertEqual(first,second);self.assertEqual(self.connection.execute('SELECT count(*) FROM cognishield_method_approvals').fetchone()[0],1)
        self.assertTrue(review_status(self.service,self.connection,self.draft)['rows'][0]['approved'])
        other=deepcopy(self.draft);other['revision']='TEST-UNRELATED-REVISION';other['catalogs']['operations'][0]['version']=2
        for name in ['operation_parameters','operation_rules','template_bindings']:
            for record in other['catalogs'][name]:record['operation_version']=2
        self.assertTrue(review_status(self.service,self.connection,other)['rows'][0]['approved'])
        self.assertEqual(first['data']['decisions'][0]['approved_by'],'TEST-SENIOR')

    def test_material_source_contract_scope_and_method_changes_require_new_approval(self):
        approve(self.service,self.connection,self.draft,self.request(),'TEST-SENIOR',self.base/'releases')
        for change in ['source','schema','scope','method']:
            with self.subTest(change=change):
                draft=deepcopy(self.draft);binding=draft['catalogs']['template_bindings'][0]
                if change=='source':draft['sources'][binding['template_path']]+=b'! different\n'
                elif change=='schema':draft['catalogs']['operation_rules'][1]['keywords']['maxLength']=39
                elif change=='scope':binding['versions']=['18.1']
                else:self.connection.execute('UPDATE cognishield_method_specs SET body=?',(json.dumps(self.method|{'limitations':['Changed material limit']}),))
                self.assertFalse(review_status(self.service,self.connection,draft)['rows'][0]['approved'])
                self.connection.execute('UPDATE cognishield_method_specs SET body=?',(json.dumps(self.method),))

    def test_stale_fingerprint_missing_ack_risk_and_bad_render_are_rejected(self):
        for change in ['revision','hash','ack','risk','render']:
            with self.subTest(change=change):
                body=deepcopy(self.request())
                if change=='revision':body['expected_revision']='stale'
                elif change=='hash':body['decisions'][0]['fingerprint']='0'*64
                elif change=='ack':body['acknowledgement']='approve everything'
                elif change=='risk':body['decisions'][0]['resolved_risks']=[]
                else:
                    wrong=self.method|{'fixtures':[{'parameters':{'description':'Uplink'},'expected_output':'wrong'}]}
                    self.connection.execute('UPDATE cognishield_method_specs SET body=?',(json.dumps(wrong),))
                    body['decisions'][0]['fingerprint']=fingerprint(self.draft,self.binding,wrong)[0]
                with self.assertRaises(Exception):approve(self.service,self.connection,self.draft,body,'TEST-SENIOR',self.base/'releases')
                self.connection.execute('UPDATE cognishield_method_specs SET body=?',(json.dumps(self.method),))
        self.assertEqual(self.connection.execute('SELECT count(*) FROM cognishield_method_approvals').fetchone()[0],0)

    def test_revocation_is_preserved_without_deleting_approval_history(self):
        approve(self.service,self.connection,self.draft,self.request(),'TEST-SENIOR',self.base/'releases')
        body=self.request('reject');body['request_id']='TEST-REQUEST-REVOKE'
        approve(self.service,self.connection,self.draft,body,'TEST-SENIOR',self.base/'releases')
        self.assertFalse(review_status(self.service,self.connection,self.draft)['rows'][0]['approved'])
        self.assertEqual(self.connection.execute('SELECT count(*) FROM cognishield_method_approvals').fetchone()[0],2)

    def test_publish_action_is_authorization_without_extra_signoff_and_reuses_it(self):
        row=review_status(self.service,self.connection,self.draft,checks=True)['rows'][0]
        first=publication_decision(self.connection,row,'TEST-PUBLISHER','TEST requested Publish action',self.base/'releases','publish','next_compatible_immutable_release')
        second=publication_decision(self.connection,row,'TEST-PUBLISHER','TEST publish retry',self.base/'releases','publish','next_compatible_immutable_release')
        self.assertEqual(first,second)
        self.assertEqual(first['approval_action'],'publish')
        self.assertEqual(first['approval_authority'],'authenticated_engineer_publication_action')
        self.assertEqual(first['approved_by'],'TEST-PUBLISHER')
        self.assertEqual(first['certifications']['vendor_semantics'],'NOT_VERIFIED')
        self.assertEqual(self.connection.execute('SELECT count(*) FROM cognishield_method_approvals').fetchone()[0],1)

    def test_activate_authorizes_the_exact_unsigned_built_pack(self):
        row=review_status(self.service,self.connection,self.draft,checks=True)['rows'][0]
        snapshot=SimpleNamespace(release_id='TEST-BUILT-PACK',manifest={'template_bindings':[self.binding|{'template_sha256':row['template_sha256']}],
            'cognishield_engineer_reviews':{'artifact_path':'reviews.json'}},schema=lambda *_:row['schema'],
            service=SimpleNamespace(get_operation=lambda _:SimpleNamespace(description='Set a fixture interface description')),
            read_json=lambda _: {'bindings':[row]})
        with self.assertRaises(ValueError):assert_activation_authorized(self.connection,snapshot,None)
        authorize_activation(self.connection,snapshot,'TEST-ACTIVATOR','TEST explicit Activate',self.base/'releases')
        assert_activation_authorized(self.connection,snapshot,None)
        record=review_status(self.service,self.connection,self.draft)['rows'][0]['approval']
        self.assertEqual(record['release_target'],'TEST-BUILT-PACK');self.assertEqual(record['approval_action'],'activate')
        self.assertIsNone(row['approval'])  # Immutable package was not rewritten.

    def test_new_template_needs_no_separate_method_form_or_semantic_certificate(self):
        self.connection.execute('DELETE FROM cognishield_method_specs')
        draft=deepcopy(self.draft)
        draft['sources'][self.binding['template_path']]=b'engineer_selected_syntax {{ description }}\n'
        prepare_publication_methods(self.service,self.connection,draft,self.base/'releases')
        row=review_status(self.service,self.connection,draft,checks=True)['rows'][0]
        self.assertEqual(row['checks']['status'],'PASS',row['checks'])
        self.assertIn('engineer_selected_syntax',row['method']['fixtures'][0]['expected_output'])
        self.assertFalse(row['approved'])
        publication_decision(self.connection,row,'TEST-PUBLISHER','TEST subjective syntax publication',self.base/'releases','publish','next_compatible_immutable_release')
        self.assertTrue(review_status(self.service,self.connection,draft)['rows'][0]['approved'])

    def test_author_edit_refreshes_render_fixture_without_semantic_veto(self):
        draft=deepcopy(self.draft);draft['sources'][self.binding['template_path']]=b'custom_description {{ description }}\n'
        prepare_publication_methods(self.service,self.connection,draft,self.base/'releases')
        row=review_status(self.service,self.connection,draft,checks=True)['rows'][0]
        self.assertEqual(row['method']['fixtures'][0]['expected_output'],'custom_description Uplink')
        self.assertEqual(row['checks']['status'],'PASS')
        self.assertEqual(row['method']['material_risks'],self.method['material_risks'])

    def test_unsafe_template_or_invalid_schema_still_cannot_publish(self):
        draft=deepcopy(self.draft);draft['sources'][self.binding['template_path']]=b'{{ description.__class__.__mro__ }}'
        with self.assertRaises(Exception):prepare_publication_methods(self.service,self.connection,draft,self.base/'releases')
        row=review_status(self.service,self.connection,self.draft,checks=True)['rows'][0]
        row['checks']['status']='FAIL'
        with self.assertRaises(ValueError):publication_decision(self.connection,row,'TEST','bad render',self.base/'releases','publish','next')

    def test_schema_sample_prefers_typed_author_examples(self):
        schema={'type':'object','required':['interface','address'],'additionalProperties':False,'properties':{
            'interface':{'type':'string','pattern':'^CUSTOM-[0-9]+$','examples':['CUSTOM-42']},
            'address':{'type':'string','format':'ipv4','default':'198.51.100.7'}}}
        self.assertEqual(schema_sample(schema),{'interface':'CUSTOM-42','address':'198.51.100.7'})

    def test_publication_checks_exact_frozen_content_and_current_approval(self):
        approve(self.service,self.connection,self.draft,self.request(),'TEST-SENIOR',self.base/'releases')
        row=review_status(self.service,self.connection,self.draft,checks=True)['rows'][0]
        binding=self.binding|{'template_sha256':row['template_sha256']}
        snapshot=SimpleNamespace(release_id='TEST-RELEASE',manifest={'template_bindings':[binding],'cognishield_engineer_reviews':{'artifact_path':'reviews.json'}},
            schema=lambda *_:row['schema'],service=SimpleNamespace(get_operation=lambda _:SimpleNamespace(description='Set a fixture interface description')),
            read_json=lambda _: {'bindings':[row]})
        assert_activation_authorized(self.connection,snapshot,None)
        binding['template_sha256']='0'*64
        with self.assertRaises(ValueError):assert_activation_authorized(self.connection,snapshot,None)


class ApprovalAuthTests(unittest.IsolatedAsyncioTestCase):
    async def test_http_denies_unsigned_approval_and_engineer_publication_despite_legacy_bypass(self):
        import httpx
        from fastapi import FastAPI
        from auth.auth import create_access_token
        from local_providers.knowledge import router
        from unittest.mock import Mock
        app=FastAPI();app.include_router(router,prefix='/api/v1')
        invoke=Mock(side_effect=AssertionError('Denied requests must not reach authoring'))
        body={'expected_revision':'test','request_id':'test-http-request','acknowledgement':ACKNOWLEDGEMENT,'reason':'TEST only','decisions':[{'identity':'test','fingerprint':'0'*64,'decision':'approve','resolved_risks':[]}]}
        with patch('local_providers.knowledge.invoke',invoke),patch.dict(os.environ,{'AUTH_BYPASS_ROLES':'1'}):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
                self.assertEqual((await client.get('/api/v1/knowledge/reviews')).status_code,401)
                headers={'Authorization':'Bearer '+create_access_token(1,'TEST-engineer','engineer')}
                self.assertEqual((await client.post('/api/v1/knowledge/review-approvals',json=body,headers=headers)).status_code,403)
                for endpoint,data in [('publish',{'mode':'offline','expected_revision':'test','expected_release':None,'reason':'TEST'}),('activate',{'release_id':'0'*32,'expected_release':None,'reason':'TEST'})]:
                    self.assertEqual((await client.post('/api/v1/knowledge/'+endpoint,json=data,headers=headers)).status_code,403)
                admin={'Authorization':'Bearer '+create_access_token(1,'TEST-admin','admin')}
                self.assertEqual((await client.post('/api/v1/knowledge/review-approvals',json=body|{'approved_by':'forged-human'},headers=admin)).status_code,422)
        invoke.assert_not_called()

    async def test_bypass_and_forged_identity_cannot_grant_senior_role(self):
        from fastapi import HTTPException
        from local_providers.knowledge import require_senior_knowledge,ReviewApproval
        with patch.dict(os.environ,{'AUTH_BYPASS_ROLES':'1'}):
            with self.assertRaises(HTTPException):await require_senior_knowledge({'username':'TEST-ENGINEER','role':'engineer','user_id':2})
        user=await require_senior_knowledge({'username':'TEST-SENIOR','role':'admin','user_id':1})
        self.assertEqual(user['username'],'TEST-SENIOR')
        with self.assertRaises(Exception):ReviewApproval.model_validate({'expected_revision':'x','request_id':'test-request','acknowledgement':ACKNOWLEDGEMENT,'reason':'test','approved_by':'forged','decisions':[]})


class NativeContractTests(unittest.TestCase):
    def test_catalog_embeddings_use_bounded_batches_preserving_order(self):
        from local_providers.knowledge_lifecycle import configure_embeddings
        from langchain_ollama import OllamaEmbeddings
        configure_embeddings()
        import app.embeddings as module
        requests=[]
        def embed(_self,texts):
            requests.append(texts);return [[int(t)] for t in texts]
        with patch.object(OllamaEmbeddings,'embed_documents',embed):
            self.assertEqual(module.embeddings.embed_documents([str(i) for i in range(11)]),[[i] for i in range(11)])
        self.assertEqual([len(r) for r in requests],[4,4,3])

    def test_registered_rate_conversion_is_exact_and_keeps_existing_v9_derivations(self):
        from local_providers.knowledge_lifecycle import configure_native_contracts
        configure_native_contracts()
        from app.knowledge.rule_registry import derive_template_value
        self.assertEqual(derive_template_value('exact_rate_kbps_v1',{'rate_bps':20000000}),20000)
        self.assertEqual(derive_template_value('ipv4_netmask_v1',{'prefix_length':24}),'255.255.255.0')
        for value in [20000001,0,-1000,True,20000000.0]:
            with self.subTest(value=value),self.assertRaises(ValueError):derive_template_value('exact_rate_kbps_v1',{'rate_bps':value})

    def test_hosted_native_runtime_keeps_preview_sandbox_boundary(self):
        from local_providers.knowledge_lifecycle import guard_native_renderer
        from jinja2 import StrictUndefined
        from jinja2.exceptions import SecurityError,UndefinedError
        guard_native_renderer()
        import app.templates.renderer as renderer
        with self.assertRaises((SecurityError,UndefinedError)):
            renderer.Environment(undefined=StrictUndefined).from_string('{{ "".__class__ }}').render()
