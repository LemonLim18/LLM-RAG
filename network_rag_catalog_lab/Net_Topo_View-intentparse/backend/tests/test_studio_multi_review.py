"""No model or server started: verify the shared adapter preserves every V9 binding."""
import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import HTTPException
from db.manager import DatabaseManager
from llm.gateway_store import ensure_schema
from local_providers import v9_studio
from llm.gateway_v9 import preview, render_draft
from llm.gateway_playbooks import combine_playbooks


class PartialSelectionTests(unittest.TestCase):
    def test_existing_unresolved_binding_can_be_retained_but_never_forged_or_changed(self):
        from local_providers.v9_worker import retained_unresolved_task
        from llm.gateway_api import ReviewSelection
        task=SimpleNamespace(intent_id='pending-bgp',operation_id='',target_devices=[],parameters={'local_as':65000})
        resolved=SimpleNamespace(intent_id='static-route',operation_id='configure_static_route',target_devices=[],parameters={})
        plan=SimpleNamespace(tasks=[resolved,task])
        entry=ReviewSelection(task_id='pending-bgp',operation_id='',parameters={'local_as':65000}).model_dump()
        self.assertIs(retained_unresolved_task(plan,entry),task)
        self.assertIsNone(retained_unresolved_task(plan,{**entry,'operation_id':'configure_bgp_neighbor'}))
        for change in [{'task_id':'forged'},{'task_id':'static-route'},{'target_host':'R1'},{'parameters':{'local_as':1}},{'template_id':'anything'}]:
            with self.subTest(change=change),self.assertRaises(ValueError):retained_unresolved_task(plan,{**entry,**change})


class MultiReviewTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = DatabaseManager(str(Path(self.tmp.name)/'unit.db'))
        self.db.initialize(); ensure_schema(self.db); self.addCleanup(self.db.close)
        self.user = {'username':'reviewer','role':'engineer'}
        self.inventory = [{'id':'1','hostname':'CISCO','vendor':'cisco','platform':'iosxe','version':'17.9'},
                          {'id':'2','hostname':'JUNIPER','vendor':'juniper','platform':'junos','version':'23.2R1'}]
        tasks=[]
        for i,device in enumerate(self.inventory):
            tasks.append({'intent_id':f'task-{i}', 'operation_id':'create_vlan','category':'vlan',
                'parameters':{'vlan_id':10+i,'name':'STAFF'},'parameter_provenance':{},'issues':[],
                'target_devices':[device], 'device_id':device['id'],'status':'rendered','request_text':'Create VLAN',
                'configs':[{'configuration':f'vendor {device["vendor"]} vlan {10+i}'}]})
        schema={'properties':{'vlan_id':{'type':'integer','minimum':1,'maximum':4094},'name':{'type':'string'}},'required':['vlan_id']}
        self.output={'plan':{'tasks':tasks,'issues':[],'status':'ready'},'schema':schema,
            'schemas':{t['intent_id']:schema for t in tasks},'task_references':{},'task_artifacts':{},'release_id':'release','allow_multi':True}
        self.calls=[]
        def worker(payload):
            self.calls.append(copy.deepcopy(payload)); return copy.deepcopy(self.output)
        self.patches=[patch.object(v9_studio,'inventory',return_value=self.inventory),patch.object(v9_studio,'worker',side_effect=worker),
                      patch('llm.gateway_knowledge.read_release',return_value=(Path('.'),{'cognishield_playbooks':{'variants':[]}}, {'release_id':'release'}))]
        for p in self.patches: p.start(); self.addCleanup(p.stop)

    async def test_all_bindings_visible_and_corrections_scoped_with_revision(self):
        result=await preview(self.db,self.user,'Create VLANs','model')
        self.assertEqual([t['task_id'] for t in result['tasks']],['task-0','task-1'])
        self.assertEqual(result['plan_status'],'ready')
        sid=result['parsed_intent']['_v9_session']
        params={'_v9_session':sid,'vlan_id':99}
        with self.assertRaises(HTTPException) as stale:
            await preview(self.db,self.user,'Create VLANs','model',params=params,task_id='task-1',expected_revision=999)
        self.assertEqual(stale.exception.status_code,409)
        await preview(self.db,self.user,'Create VLANs','model',params=params,task_id='task-1',expected_revision=1)
        self.assertEqual(self.calls[-1]['task_id'],'task-1')
        self.assertEqual(self.calls[-1]['corrections'],{'vlan_id':99})
        self.assertEqual(len(self.calls[-1]['plan']['tasks']),2)

    async def test_complete_native_output_no_jobs_or_implicit_saves(self):
        result=await preview(self.db,self.user,'Create VLANs','model')
        body=SimpleNamespace(session_id=result['parsed_intent']['_v9_session'],expected_revision=1,output_kind='native',model='model')
        output=await render_draft(self.db,self.user,body)
        self.assertEqual(len(output['documents']),2)
        self.assertEqual([d['device_id'] for d in output['documents']],['1','2'])
        self.assertIn('juniper',output['documents'][1]['content'])
        self.assertTrue(all(not d['saved'] and not d['execution_available'] for d in output['documents']))
        with self.db._connect() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM jobs').fetchone()[0],0)
            self.assertEqual(c.execute('SELECT count(*) FROM authoring_revisions').fetchone()[0],0)
        self.output['plan']['status']='needs_clarification'
        with self.assertRaises(HTTPException): await render_draft(self.db,self.user,body)

    async def test_missing_playbook_variant_does_not_hide_native_tasks(self):
        result=await preview(self.db,self.user,'Create VLANs','model','playbook')
        self.assertEqual(result['playbook_support']['status'],'unsupported')
        self.assertEqual(len(result['playbook_support']['tasks']),2)
        self.assertEqual(len(result['tasks']),2)

    async def test_changed_release_rejects_entire_output(self):
        result=await preview(self.db,self.user,'Create VLANs','model')
        body=SimpleNamespace(session_id=result['parsed_intent']['_v9_session'],expected_revision=1,output_kind='native',model='model')
        with patch('llm.gateway_knowledge.read_release',return_value=(Path('.'),{}, {'release_id':'changed'})):
            with self.assertRaises(HTTPException) as changed: await render_draft(self.db,self.user,body)
        self.assertEqual(changed.exception.status_code,409)

    async def test_combined_playbook_keeps_hosts_and_order_and_requires_whole_validation(self):
        import yaml
        drafts=[{'content':yaml.safe_dump([{'hosts':host,'tasks':[{'name':host,'test.vendor.module':{}}]}]),
                 'validation':{'status':'passed','dependencies':{'test.vendor':'1.0.0'},'required_plugins':{'module':['test.vendor.module']}}} for host in ['CISCO','JUNIPER']]
        with patch('llm.gateway_validation.validate_ansible',return_value={'status':'passed','dependencies':{'test.vendor':'1.0.0'}}) as validate:
            content,_=await combine_playbooks(drafts)
            self.assertEqual([p['hosts'] for p in yaml.safe_load(content)],['CISCO','JUNIPER'])
            self.assertEqual(validate.call_count,1)
        with patch('llm.gateway_validation.validate_ansible',return_value={'status':'unavailable'}):
            with self.assertRaises(HTTPException): await combine_playbooks(drafts)
        drafts[1]['validation']['dependencies']['test.vendor']='2.0.0'
        with self.assertRaises(HTTPException): await combine_playbooks(drafts)


if __name__ == '__main__': unittest.main()
