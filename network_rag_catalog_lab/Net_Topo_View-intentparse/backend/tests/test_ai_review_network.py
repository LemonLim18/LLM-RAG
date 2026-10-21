"""New review/network scope: isolated data, no device connections or validation subprocesses."""
import os
os.environ["COGNISHIELD_SEMANTIC_EMBEDDINGS"]="0"
os.environ["COGNISHIELD_AI_ENGINE"]="legacy"
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from db.manager import DatabaseManager
from llm.gateway import AIGateway
from llm.gateway_models import TurnRequest
from llm.gateway_store import ensure_schema
from llm.gateway_network import NetworkReader, NetworkQuery, READ_TOOLS, route_network, network_context
from llm.tools import ToolAuthorization


class NetworkReviewTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.root=Path(self.folder.name);self.db=DatabaseManager(str(self.root/'unit.db'))
        self.db.initialize();ensure_schema(self.db);self.addCleanup(self.db.close)
        with self.db._connect() as c:
            c.execute("INSERT INTO devices(id,hostname,vendor,role,os_version) VALUES(1,'R1','cisco_xe','core','17.9')")
            c.execute("INSERT INTO devices(id,hostname,vendor,role,os_version) VALUES(2,'R2','juniper_junos','edge','23.4')")
            for owner,text in [('alice','interface Gi0/1\n description uplink\n password secret-value'),('bob','PRIVATE-BOB')]:
                c.execute('INSERT INTO config_snapshots(device_id,config_text,config_hash,owner_username) VALUES(1,?,?,?)',(text,uuid4().hex,owner))
        fixture={'version':1,'defaults':{'metrics':[]},'devices':[{'device_id':1,'metrics':[{'time':'2026-10-10T12:00:00Z','cpu':25.0,'memory':40.0}]}],
            'syslog':[{'id':'log-1','device_id':1,'timestamp':'2026-10-10T12:00:00Z','message':'Recorded simulation log'}],
            'alerts':[{'id':'alert-1','device_id':1,'timestamp':'2026-10-10T12:00:00Z','message':'Recorded simulation alert'}]}
        (self.root/'observations.json').write_text(json.dumps(fixture),encoding='utf-8')
        self.fixture_patch=patch('lab_config.FIXTURE_DIR',self.root);self.fixture_patch.start();self.addCleanup(self.fixture_patch.stop)
        self.auth=ToolAuthorization('alice','engineer','floating','unit',READ_TOOLS)
        self.gateway=AIGateway(self.db);self.reader=NetworkReader(self.db)

    async def test_investigation_retains_sources_and_absent_metrics(self):
        context,evidence,_=await network_context(self.db,self.gateway.registry,self.auth,'Investigate R1 using metrics, syslog and alerts')
        # The explicit source clause is authoritative: no unrelated inventory,
        # topology or configuration read should be added to this investigation.
        self.assertEqual({c['tool'] for c in context},{'network.telemetry','network.syslog','network.incidents'})
        self.assertEqual(len(context),3)
        self.assertIn('simulated',{e.origin for e in evidence})
        serialized=json.dumps(context)
        self.assertNotIn('PRIVATE-BOB',serialized);self.assertNotIn('secret-value',serialized)
        metrics=next(c for c in context if c['tool']=='network.telemetry')['data']['sources'][0]['data']['records']
        self.assertEqual(metrics[0]['cpu'],25.0);self.assertNotIn('errors',metrics[0])
        self.assertTrue(all(e.origin!='live' for e in evidence))
        # Keep the original ownership/redaction assertion meaningful by actually
        # retrieving Alice's stored capture through its authorized capability.
        saved=self.reader.read('configuration',NetworkQuery(device_refs=['R1'],source_scope='historical'),self.auth)
        serialized=json.dumps(saved.model_dump())
        self.assertIn('stored',{e.origin for e in saved.evidence})
        self.assertIn('description uplink',serialized)
        self.assertNotIn('PRIVATE-BOB',serialized);self.assertNotIn('secret-value',serialized)

    async def test_topology_does_not_establish_reachability(self):
        result=self.reader.read('topology',NetworkQuery(device_refs=['R1','R2']),self.auth)
        self.assertIsNone(result.data['graph_path']);self.assertEqual(result.data['reachability'],'not_measured')

    async def test_bounded_telemetry_preserves_complete_records_and_interface_identity(self):
        from llm.gateway_network import bounded_record_context
        from llm.gateway_findings import network_answer
        from llm.orchestration.verification import verify_records
        rows=[{'device_id':1,'hostname':'R1','interface':'GigabitEthernet0/1','time':str(i),'cpu':25.0,'memory':40.0} for i in range(30)]
        result=self.reader.result('json_fixture.telemetry',{'sources':[{'origin':'simulated','status':'success','data':{'records':rows,'total':30}}]},[{'id':1}],origin='simulated')
        data=bounded_record_context(result.data,1000)
        self.assertNotIn('excerpt',data)
        self.assertLessEqual(len(json.dumps(data,default=str)),1000)
        retained=data['sources'][0]['data']['records']
        self.assertTrue(retained);self.assertLess(len(retained),30)
        self.assertTrue(data['sources'][0]['data']['truncated'])
        self.assertEqual(result.data['sources'][0]['data']['records'],rows)
        context=[{'tool':'network.telemetry','status':'success','message':'','data':data,'evidence_ids':[result.evidence[0].id]}]
        self.assertEqual(verify_records(context,result.evidence,[('network.telemetry',result)])['status'],'verified')
        answer=network_answer(context,result.evidence)
        self.assertIn('R1 · GigabitEthernet0/1',answer);self.assertIn('25.0',answer)
        self.assertNotIn('more content than',answer)

    async def test_live_disabled_never_returns_simulated_measurements(self):
        with patch.dict(os.environ,{'COGNISHIELD_AI_LIVE_READS':'0'}):
            result=self.reader.read('telemetry',NetworkQuery(live=True),self.auth)
        self.assertEqual(result.status,'unavailable');self.assertFalse(result.evidence)

    async def test_missing_live_evidence_does_not_hide_available_stored_sources(self):
        from llm.gateway_services import inventory_snapshot
        data=inventory_snapshot(self.db)
        prompt='Investigate R1 using available interfaces, topology, saved configurations, telemetry and syslogs. Distinguish missing live evidence from a fault.'
        domains,query=route_network(prompt,data)
        self.assertFalse(query['live']);self.assertIn('configuration',domains)
        topology=self.reader.read('topology',NetworkQuery(**query),self.auth)
        self.assertEqual(topology.status,'success');self.assertEqual(topology.data['topology_kind'],'planned')
        self.assertTrue(route_network('Show R1 live telemetry and identify missing live evidence.',data)[1]['live'])

    async def test_scope_time_range_and_unknown_target(self):
        result=self.reader.read('telemetry',NetworkQuery(device_refs=['R99']),self.auth)
        self.assertEqual(result.status,'unavailable')
        result=self.reader.read('telemetry',NetworkQuery(device_refs=['R1'],start='2026-10-15T00:00:00Z'),self.auth)
        self.assertEqual(result.status,'unavailable')
        context,_,_=await network_context(self.db,self.gateway.registry,self.auth,'List Cisco core devices in my inventory')
        self.assertEqual(context[0]['data']['summary']['device_count'],1)
        context,_,_=await network_context(self.db,self.gateway.registry,self.auth,'List interfaces on R99')
        self.assertEqual(context[0]['data']['devices'],[])
        self.assertEqual(context[0]['data']['unresolved_devices'],['R99'])

    async def test_general_questions_and_knowledge_are_separate_routes(self):
        from llm.gateway_services import inventory_snapshot
        data=inventory_snapshot(self.db)
        self.assertEqual(route_network('Hello, how are you?',data)[0],[])
        self.assertEqual(route_network('Explain the difference between OSPF and BGP',data)[0],['knowledge'])
        with self.assertRaises(Exception):
            await self.gateway.registry.invoke('document.propose',{},self.auth)

    async def test_floating_file_understanding_remains_owner_scoped(self):
        from llm.gateway_documents import upload_attachment
        identity=self.gateway.store.create('alice','floating')['id']
        attached=await upload_attachment(self.db,identity,'alice','device.log',b'OSPF adjacency changed')
        with patch('local_providers.chat.generate',AsyncMock(side_effect=[('{"intent":"analyze_files"}','unit'),('The log records an OSPF adjacency change.','unit')])),patch('llm.gateway_knowledge.documentation_context',return_value=([],[])):
            response=await self.gateway.turn(identity,{'username':'alice','role':'engineer'},TurnRequest(request_id=uuid4(),prompt='Explain the attached file',attachment_ids=[attached['id']]))
        self.assertTrue(any(e.origin=='user_supplied' for e in response.evidence))
        with self.assertRaises(Exception):self.gateway.store.get(identity,'bob')

    async def test_measured_zero_and_collector_failure_remain_distinct(self):
        from types import ModuleType
        from unittest.mock import Mock
        from datetime import datetime, timezone
        module=ModuleType('monitor.api'); package=ModuleType('monitor'); package.api=module
        module.INFLUXDB_TOKEN='unit-collector'
        module.METRIC_DEFS={'cpu':{'measurements':['cpu'],'fields':['usage']}}
        module._query_metric_rows=Mock(return_value=[{'_time':datetime.now(timezone.utc).isoformat(),'_field':'usage','_value':0,'_measurement':'cpu'}])
        module._row_device_key=lambda row:'R1';module._row_interface_key=lambda row:None
        with patch.dict(sys.modules,{'monitor':package,'monitor.api':module}),patch.dict(os.environ,{'COGNISHIELD_AI_LIVE_READS':'1'}):
            result=self.reader.read('telemetry',NetworkQuery(live=True,device_refs=['R1'],query='cpu'),self.auth)
            self.assertEqual(result.status,'success');self.assertEqual(result.data['records'][0]['value'],0)
            self.assertEqual(result.evidence[0].origin,'live')
            module._query_metric_rows.side_effect=RuntimeError('collector offline')
            result=self.reader.read('telemetry',NetworkQuery(live=True,query='cpu'),self.auth)
            self.assertEqual(result.status,'unavailable');self.assertIsNone(result.data)

    async def test_incident_ids_do_not_match_substrings(self):
        self.assertFalse(self.reader.matches_incident('[10, "R10"]',[{'id':1,'hostname':'R1'}]))
        self.assertTrue(self.reader.matches_incident('[1, "R10"]',[{'id':1,'hostname':'R1'}]))

    async def test_readable_citations_preserve_authoritative_records_and_document_text(self):
        from llm.gateway import model_context
        from llm.gateway_models import Evidence
        evidence=[Evidence(id='opaque-id',source='planned topology',origin='stored',source_revision='revision-hash')]
        context=[{'evidence_ids':['opaque-id'],'source_revision':'revision-hash','text':'User document hash remains verbatim'}]
        readable,sources=model_context(context,evidence)
        self.assertEqual(readable[0]['evidence_ids'],['S1']);self.assertEqual(sources[0]['id'],'S1')
        self.assertNotIn('source_revision',readable[0]);self.assertNotIn('source_revision',sources[0])
        self.assertEqual(readable[0]['text'],context[0]['text']);self.assertEqual(evidence[0].source_revision,'revision-hash')
        self.assertEqual(model_context(context,evidence,True)[1][0]['source_revision'],'revision-hash')

    async def test_live_syslog_handles_missing_fixture(self):
        with patch('lab_config.FIXTURE_DIR',self.root/'missing'),patch.dict(os.environ,{'COGNISHIELD_AI_LIVE_READS':'1'}):
            result=self.reader.read('syslog',NetworkQuery(live=True),self.auth)
        self.assertEqual(result.status,'unavailable')


class ReferenceDraftTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        from types import SimpleNamespace
        from local_providers import v9_studio
        self.user={'username':'reviewer','role':'engineer'}
        self.devices=[{'id':'1','hostname':'EDGE','vendor':'cisco','platform':'ios','version':'manual'},
                      {'id':'2','hostname':'CORE','vendor':'juniper','platform':'junos','version':'manual'}]
        self.tasks=[{'intent_id':'route','operation_id':'configure_static_route','target_devices':[self.devices[0]],'parameters':{'destination':'203.0.113.0/24','next_hop':'192.0.2.1'}},
                    {'intent_id':'peer','operation_id':'configure_bgp_neighbor','target_devices':[self.devices[1]],'parameters':{'local_as':65000,'neighbor_ip':'198.51.100.2','remote_as':65001}}]
        self.session={'revision':1,'inventory_hash':v9_studio.digest(self.devices),'body':json.dumps({'plan':{'tasks':self.tasks},'release_id':'unit-release'})}
        self.result={'release_id':'unit-release','documents':[{'task_id':t['intent_id'],'operation_id':t['operation_id'],'device':t['target_devices'][0],'content':'reviewed fixture line\n'} for t in self.tasks]}
        self.body=SimpleNamespace(session_id='owned',expected_revision=1,reference_values={},model='unit',output_kind='reference_playbook')
        patches=[patch.object(v9_studio,'session',return_value=self.session),patch.object(v9_studio,'inventory',return_value=self.devices),
                 patch('llm.gateway_knowledge.read_release',return_value=(Path('.'),{}, {'release_id':'unit-release'}))]
        for item in patches:item.start();self.addCleanup(item.stop)

    async def test_combined_draft_preserves_targets_and_review_values(self):
        import yaml
        from llm.gateway_reference_drafts import render_reference
        with patch('local_providers.v9_studio.worker',return_value=self.result) as worker:
            result=await render_reference(None,self.user,self.body)
        plays=yaml.safe_load(result['content'])
        self.assertEqual([p['hosts'] for p in plays],['EDGE','CORE'])
        self.assertIn('cisco.ios.ios_config',plays[0]['tasks'][0])
        self.assertIn('junipernetworks.junos.junos_config',plays[1]['tasks'][0])
        self.assertEqual(worker.call_args.args[0]['templates'][1]['parameters'],self.tasks[1]['parameters'])
        self.assertEqual(result['validation']['status'],'unvalidated')
        self.assertFalse(result['saved']);self.assertFalse(result['execution_available'])

    async def test_concurrent_review_change_discards_entire_draft(self):
        from fastapi import HTTPException
        from llm.gateway_reference_drafts import render_reference
        def changed(payload):self.session['revision']=2;return self.result
        with patch('local_providers.v9_studio.worker',side_effect=changed),self.assertRaises(HTTPException) as error:
            await render_reference(None,self.user,self.body)
        self.assertEqual(error.exception.status_code,409)

    async def test_unsupported_huawei_playbook_does_not_drop_target(self):
        from fastapi import HTTPException
        from llm.gateway_reference_drafts import render_reference
        self.result['documents'][1]['device']={**self.devices[1],'vendor':'huawei'}
        with patch('local_providers.v9_studio.worker',return_value=self.result),self.assertRaises(HTTPException) as error:
            await render_reference(None,self.user,self.body)
        self.assertEqual(error.exception.status_code,422)


if __name__=='__main__':unittest.main()
