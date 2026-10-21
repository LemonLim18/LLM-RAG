"""Phase C contracts on disposable SQLite and one central scenario authority."""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from db.manager import DatabaseManager
from llm.gateway_store import ensure_schema
from local_providers.development import ScenarioManager,Scenario,active_for,observation_set
from llm.gateway_services import inventory_snapshot
from llm.gateway_network import NetworkReader,NetworkQuery
from llm.tools import ToolAuthorization

ROOT=Path(__file__).resolve().parents[2]
AUDIT=ROOT/'tmp/phase-c';AUDIT.mkdir(parents=True,exist_ok=True)
RUN=AUDIT/('deterministic-'+uuid4().hex+'.jsonl')


class C1Tests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.root=Path(self.folder.name);self.db=DatabaseManager(str(self.root/'app.db'));self.db.initialize();ensure_schema(self.db);self.addCleanup(self.db.close)
        assert Path(self.db._db_path).resolve().is_relative_to(self.root.resolve())
        with self.db._connect() as c:c.execute("INSERT INTO devices(id,hostname,vendor) VALUES(1,'ORDINARY','cisco_ios')")
        # This legacy deterministic suite owns its source/model switches; local
        # Workbench opt-in must not change its disable-source or call-count tests.
        self.env=patch.dict(os.environ,{'COGNISHIELD_DEV_SIMULATION':'1','COGNISHIELD_DEV_WORKBENCH':'0',
            'COGNISHIELD_AI_ENGINE':'langgraph_b3','COGNISHIELD_SEMANTIC_EMBEDDINGS':'0',
            'COGNISHIELD_AI_PLANNING':'0','COGNISHIELD_AI_SYNTHESIS':'0'})
        self.env.start();self.addCleanup(self.env.stop)
        self.manager=ScenarioManager(self.root/'state.json');self.db._development_scenario=self.manager
        self.reader=NetworkReader(self.db)
        self.auth=ToolAuthorization('alice','admin','floating','owned',frozenset({'network.state'}),permissions=frozenset({'network.inventory.read'}))

    def record(self,case,actual,condition,mode='deterministic_real_services'):
        s,meta=self.manager.snapshot()
        result={'case_id':case,'timestamp':datetime.now(timezone.utc).isoformat(),'code_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'scenario':meta,'model':None,'mode':mode,'actual':actual,'outcome':'PASS' if condition else 'FAIL','model_calls':0}
        with RUN.open('a',encoding='utf-8') as f:f.write(json.dumps(result,default=str)+'\n')
        self.assertTrue(condition,json.dumps(actual,default=str))

    def select(self,key):return self.manager.change('select',self.manager.snapshot()[1]['source_revision'],scenario_id=key)

    def test_C1_001_switch_all_readers_and_v9_inventory(self):
        from local_providers.v9_studio import inventory
        results={}
        for key in ['HEALTHY-001','FAULT-IFDOWN-001','UNKNOWN-001','CONFLICT-001']:
            self.select(key);data=inventory_snapshot(self.db)
            tools={d:self.reader.read(d,NetworkQuery(device_refs=['R1','R2']),self.auth).model_dump() for d in ['state','topology','configuration','telemetry','syslog','incidents']}
            results[key]={'tool_results':tools,'interface':data['devices'][0]['interfaces'][1]}
            self.assertEqual(inventory(self.db)[0]['scenario_revision'],data['scenario']['source_revision'])
            self.assertEqual(self.db.get_device_by_id(9101).hostname,'R1')
        self.record('C1-001',results,results['HEALTHY-001']['interface']['admin_status']=='up' and results['FAULT-IFDOWN-001']['interface']['admin_status']=='down' and results['UNKNOWN-001']['tool_results']['state']['status']=='unavailable')

    def test_C1_002_event_capture_and_no_ordinary_mutation(self):
        s,meta=self.manager.snapshot();before=s['records']['running_configuration'][0]['values']['config_text']
        self.manager.transition(9112,'down',meta['source_revision']);s,meta=self.manager.snapshot()
        capture=self.manager.capture(9101,meta['source_revision']);s,meta=self.manager.snapshot()
        current=next(r for r in s['records']['running_configuration'] if r['current'] and r['device_id']==9101)
        with self.db._connect() as c:
            ordinary=c.execute('SELECT id,hostname FROM devices').fetchall();saved=c.execute('SELECT count(*) FROM config_snapshots').fetchone()[0]
        self.record('C1-002',{'current':current,'capture':capture,'telemetry':s['records']['telemetry'][-1],'ordinary':[(r[0],r[1]) for r in ordinary],'saved_sqlite_snapshots':saved},'\n shutdown' in current['values']['config_text'] and capture['values']['config_text']==current['values']['config_text'] and not capture['current'] and saved==0 and len(ordinary)==1)

    def test_C1_003_revision_reset_restart_and_invalid_inputs(self):
        s,meta=self.manager.snapshot();initial=meta['source_revision'];self.manager.transition(9112,'down',initial)
        with self.assertRaises(Exception):self.manager.change('reset',initial)
        restored=ScenarioManager(self.root/'state.json');self.assertEqual(restored.snapshot()[1],self.manager.snapshot()[1])
        s,meta=self.manager.change('reset',self.manager.snapshot()[1]['source_revision'])
        invalid=json.loads(json.dumps(s));invalid['interfaces'][0]['prefix']='invalid'
        with self.assertRaises(ValueError):self.manager.change('edit',meta['source_revision'],invalid)
        copy=json.loads(json.dumps(s));copy['id']='COPY-001';self.manager.change('duplicate',meta['source_revision'],copy)
        self.record('C1-003',{'initial':initial,'after':self.manager.snapshot()[1]},s['interfaces'][1]['admin_status']=='up' and initial!=meta['source_revision'])

    def test_C1_004_authorization_and_production_isolation(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from local_providers.development_api import router
        from auth.auth import create_access_token
        app=FastAPI();app.state.local_db=self.db;app.include_router(router)
        with TestClient(app) as client:
            anonymous=client.get('/api/v1/development-network').status_code
            token=create_access_token(1,'alice','engineer')
            denied=client.put('/api/v1/development-network',headers={'Authorization':'Bearer '+token},json={'action':'reset','expected_revision':self.manager.snapshot()[1]['source_revision']}).status_code
        with patch('lab_config.LOCAL_LAB',False):isolated=active_for(self.db) is None and inventory_snapshot(self.db)['devices'][0]['hostname']=='ORDINARY'
        with self.assertRaises(Exception):self.db.upsert_device(self.db.get_device_by_id(9101))
        self.record('C1-004',{'anonymous':anonymous,'engineer_write':denied,'production_isolation':isolated},anonymous in {401,403} and denied==403 and isolated)

    def test_C1_005_monitoring_uses_real_scenario_counters_without_defaults(self):
        monitoring=observation_set(self.manager).bundle();traffic=monitoring['history']['data']['interface_traffic']
        self.record('C1-005',monitoring,len({r['value'] for r in traffic})==5 and not monitoring['history']['data']['pkts_in_ucast'] and monitoring['interfaces']['interfaces'][0]['in_packets'] is None)

    def test_C1_006_registry_authorization_current_state_reader(self):
        from llm.gateway import AIGateway
        from llm.gateway_models import TurnRequest
        from llm.gateway_network import READ_TOOLS
        gateway=AIGateway(self.db);cid=gateway.store.create('alice','floating')['id']
        # Use the gateway's existing authorization contract, never a model role.
        from llm.tools import ToolAuthorization
        auth=ToolAuthorization(principal='alice',role='admin',assistant_kind='floating',conversation_id=cid,allowed_tools=READ_TOOLS,permissions=frozenset({'network.inventory.read'}))
        result=asyncio.run(gateway.registry.invoke('network.state',{'device_refs':['R1']},auth))
        self.record('C1-006',result.model_dump(),result.status=='success' and any(r['kind']=='reachability' for r in result.data['records']))

    def test_C2_003_named_network_request_cannot_edit_unrelated_buffer(self):
        from unittest.mock import AsyncMock
        from llm.gateway import AIGateway
        from llm.gateway_routing import SemanticRoute
        from llm.gateway_models import TurnRequest
        g=AIGateway(self.db);cid=g.store.create('alice','studio')['id']
        editor=dict(document_id='other',path='playbooks/other.cfg',content='hostname UNRELATED\n',language='plaintext',model_id='other',model_version=1,buffer_epoch=0,saved_revision=0,is_dirty=True,read_only=False)
        result_data={'parsed_intent':{'action':'','_v9_session':'test-review'},'tasks':[],'output_kind':'native'}
        with patch('llm.orchestration.engine.select_context',AsyncMock(return_value=SemanticRoute(intent='edit',use_editor=True))),patch('llm.gateway_v9.preview',AsyncMock(return_value=result_data)) as v9:
            result=asyncio.run(g.turn(cid,{'username':'alice','role':'admin'},TurnRequest(request_id=uuid4(),prompt='Configure interface GigabitEthernet1/0/1 on R2.',editor=editor)))
        self.record('C2-003',{'kind':result.kind,'proposal':result.proposal,'routing':result.context_coverage.get('routing'),'mocked_boundary':'V9 result only'},result.kind=='generation_preview' and result.proposal is None and v9.await_count==1,mode='real_graph_mocked_v9_result')

    def test_C2_004_rejected_interface_is_visible_without_asserting_nonexistence(self):
        from local_providers.v9_studio import review_issues
        task={'issues':[], 'candidates':[{'type':'INVALID_INTERFACE','validation':'rejected','field':'interface','value':'GigabitEthernet1/0/1','device':'R1'}]}
        issues=review_issues(task)
        self.record('C2-004',issues,len(issues)==1 and 'not recorded' in issues[0]['message'] and task['issues']==[])

    def test_C1_009_current_configuration_and_source_availability_are_distinct(self):
        current=self.reader.read('configuration',NetworkQuery(device_refs=['R1'],query='Show current running configuration'),self.auth)
        historical=self.reader.read('configuration',NetworkQuery(device_refs=['R1'],query='Show stored configuration history'),self.auth)
        s,meta=self.manager.snapshot();s['availability']['running_configuration']=False;self.manager.change('edit',meta['source_revision'],s)
        unavailable=self.reader.read('configuration',NetworkQuery(device_refs=['R1'],query='Show current running configuration'),self.auth)
        self.record('C1-009',{'current':current.model_dump(),'historical':historical.model_dump(),'unavailable':unavailable.model_dump()},all(r['current'] and r['kind']=='running_configuration' for r in current.data['records']) and bool(current.data['records']) and all(not r['current'] for r in historical.data['records']) and bool(historical.data['records']) and unavailable.status=='unavailable' and not unavailable.data['records'])


class C3Tests(unittest.TestCase):
    setUp=C1Tests.setUp
    record=C1Tests.record
    select=C1Tests.select

    def turn(self,g,cid,prompt):
        from unittest.mock import AsyncMock
        from llm.gateway_routing import SemanticRoute
        from llm.gateway_models import TurnRequest
        route=SemanticRoute(intent='answer',network_domains=['inventory','topology','configuration','telemetry','syslog','incidents'],device_refs=['R1','R2'],network_request=prompt)
        with patch('llm.orchestration.engine.select_context',AsyncMock(return_value=route)):
            return asyncio.run(g.turn(cid,{'username':'alice','role':'admin'},TurnRequest(request_id=uuid4(),prompt=prompt)))

    def test_C3_001_to_006_actual_graph_scenarios_and_refresh(self):
        from llm.gateway import AIGateway
        g=AIGateway(self.db);cid=g.store.create('alice','floating')['id']
        cases=[('HEALTHY-001','healthy_within_tested_scope'),('FAULT-IFDOWN-001','confirmed_within_scenario'),('FAULT-SUBNET-001','confirmed_within_scenario'),('FAULT-ROUTE-001','strongly_supported'),('CONFLICT-001','conflicting_evidence'),('UNKNOWN-001','insufficient_evidence')]
        for n,(key,status) in enumerate(cases,1):
            self.select(key);r=self.turn(g,cid,'Investigate whether R1 can communicate with R2 and identify any issues.')
            agent=r.context_coverage['agent'];a=agent.get('assessment',{})
            self.record('C3-00'+str(n),r.model_dump(),a.get('conclusion_status')==status and agent['tool_calls']<=8 and agent['rounds']<=3 and 'network.state' in r.context_coverage['network']['domains'] and agent['verification']['status']=='verified',mode='actual_graph_registry_sqlite_mocked_semantic_decision')
            self.assertNotIn('not live measurements',r.answer)
            if key in {'CONFLICT-001','UNKNOWN-001'}:
                self.assertGreaterEqual(len(a['hypotheses']),3)
                self.assertTrue(all(h['next_check'] for h in a['hypotheses']))
            if key=='CONFLICT-001':
                self.assertEqual(a['hypotheses'][1]['status'],'contradicted')
                self.assertEqual(a['hypotheses'][2]['status'],'contradicted')
        # Restart gateway; recover owned references, retrieve changed records.
        self.select('HEALTHY-001');g=AIGateway(self.db)
        r=self.turn(g,cid,'Are you sure? Check the other sources.')
        self.assertEqual(r.context_coverage['agent']['assessment']['conclusion_status'],'healthy_within_tested_scope',str(r.context_coverage['agent']['assessment']))
        self.assertEqual(r.context_coverage['agent']['checkpointing'],'restored')

    def test_C3_014_missing_prefix_and_derived_evidence_do_not_certify(self):
        from llm.gateway import AIGateway
        self.select('FAULT-SUBNET-001');s,meta=self.manager.snapshot()
        for row in s['records']['state']:
            if row['kind']=='interface_state':row['values'].pop('prefix',None)
        self.manager.change('edit',meta['source_revision'],s)
        g=AIGateway(self.db);cid=g.store.create('alice','floating')['id'];r=self.turn(g,cid,'Investigate why R1 cannot communicate with R2.')
        a=r.context_coverage['agent']['assessment']
        self.record('C3-014',a,a['conclusion_status']=='insufficient_evidence' and bool(a['gaps']),mode='actual_graph_registry_mocked_semantic_decision')

    def test_C3_008_general_topic_excludes_investigation_context(self):
        from llm.gateway import AIGateway
        from llm.gateway_models import TurnRequest
        from llm.gateway_routing import SemanticRoute
        from unittest.mock import AsyncMock
        g=AIGateway(self.db);cid=g.store.create('alice','floating')['id'];self.turn(g,cid,'Investigate R1 and R2.')
        with patch('llm.orchestration.engine.select_context',AsyncMock(return_value=SemanticRoute(intent='answer'))),patch('local_providers.chat.generate',AsyncMock(return_value=('Hello!','test'))):
            r=asyncio.run(g.turn(cid,{'username':'alice','role':'admin'},TurnRequest(request_id=uuid4(),prompt='hello')))
        self.record('C3-008',r.model_dump(),r.context_coverage['agent']['tool_calls']==0 and not r.context_coverage['routing']['history'],mode='actual_graph_mocked_model')

    def test_C3_015_stale_observations_do_not_confirm(self):
        from llm.gateway import AIGateway
        s,meta=self.manager.snapshot();s['logical_time']='2026-10-17T10:00:00Z';self.manager.change('edit',meta['source_revision'],s)
        g=AIGateway(self.db);cid=g.store.create('alice','floating')['id'];r=self.turn(g,cid,'Investigate R1 and R2.')
        a=r.context_coverage['agent']['assessment']
        self.record('C3-015',a,a['conclusion_status']=='insufficient_evidence' and len(a['hypotheses'])==3 and not any(h['status']=='confirmed_within_scenario' for h in a['hypotheses']),mode='actual_graph_registry_mocked_semantic_decision')

    def test_C3_016_derived_incidents_are_not_independent_votes(self):
        from llm.gateway import AIGateway
        self.select('FAULT-IFDOWN-001');g=AIGateway(self.db);cid=g.store.create('alice','floating')['id']
        first=self.turn(g,cid,'Investigate R1 and R2.')
        s,meta=self.manager.snapshot()
        for n in range(4):s['records']['incidents'].append({**s['records']['incidents'][0],'id':'derived-copy-'+str(n)})
        self.manager.change('edit',meta['source_revision'],s)
        second=self.turn(g,cid,'Investigate R1 and R2.')
        a=first.context_coverage['agent']['assessment']['hypotheses'][0];b=second.context_coverage['agent']['assessment']['hypotheses'][0]
        self.record('C3-016',{'before':a,'after':b},a['independent_observations']==b['independent_observations']==2 and a['status']==b['status']=='confirmed_within_scenario',mode='actual_graph_registry_mocked_semantic_decision')

    def test_C3_017_source_change_pins_the_turn_and_refreshes_the_next(self):
        from llm.gateway import AIGateway
        original=NetworkReader.read;manager=self.manager;changed=False
        def changing(reader,domain,query,authorization):
            nonlocal changed
            if domain=='topology' and not changed:
                changed=True;manager.change('select',manager.snapshot()[1]['source_revision'],scenario_id='FAULT-IFDOWN-001')
            return original(reader,domain,query,authorization)
        g=AIGateway(self.db);cid=g.store.create('alice','floating')['id']
        with patch.object(NetworkReader,'read',changing):r=self.turn(g,cid,'Investigate R1 and R2.')
        a=r.context_coverage['agent']['assessment']
        # G1 supersedes mixed-revision detection with request-entry snapshot
        # isolation. The initial healthy turn must never consume fault records.
        revisions={item['data']['scenario']['source_revision'] for item in r.observations if item.get('data',{}).get('scenario')}
        self.assertEqual(len(revisions),1)
        self.assertTrue(all(item['data']['scenario']['id']=='HEALTHY-001' for item in r.observations if item.get('data',{}).get('scenario')))
        self.assertEqual(manager.snapshot()[0]['id'],'FAULT-IFDOWN-001')
        second=self.turn(g,cid,'Investigate R1 and R2.')
        self.record('C3-017',{'initial':a,'next':second.context_coverage['agent']['assessment']},
            a['conclusion_status']=='healthy_within_tested_scope' and second.context_coverage['agent']['assessment']['conclusion_status']=='confirmed_within_scenario',
            mode='actual_graph_registry_pinned_revision_activation_between_authorized_reads')

    def test_C3_018_scenario_handoff_is_owned_read_only_and_revision_aware(self):
        from llm.gateway import AIGateway
        from llm.gateway_handoff import prepare,accept,history_context
        from fastapi import HTTPException
        g=AIGateway(self.db);user={'username':'alice','role':'admin'};cid=g.store.create('alice','floating')['id'];r=self.turn(g,cid,'Investigate R1 and R2.')
        record=prepare(g,user,cid,r.request_id,'Review the interface evidence in Studio')
        accepted=accept(g,user,record['id']);again=accept(g,user,record['id'])
        before=history_context(self.db,accepted['conversation_id'],user)
        from llm.gateway_handoff import authorized_observations
        projected=authorized_observations(record,{'username':'alice','role':'engineer'})
        self.assertTrue(next(i for i in projected if i['tool']=='network.configuration')['data']['records'])
        with self.db._connect() as c:submitted=c.execute('SELECT count(*) FROM ai_turns WHERE conversation_id=?',(accepted['conversation_id'],)).fetchone()[0]
        self.select('FAULT-IFDOWN-001');after=history_context(self.db,accepted['conversation_id'],user)
        late=prepare(g,user,cid,r.request_id,'Review older evidence')
        late_accepted=accept(g,user,late['id'])
        self.assertIn('Inventory changed',late_accepted['warning'])
        self.assertIn('old observation payload was withheld',str(history_context(self.db,late_accepted['conversation_id'],user)))
        with self.assertRaises(HTTPException):accept(g,{'username':'bob','role':'admin'},record['id'])
        with patch.dict(os.environ,{'COGNISHIELD_DEV_SIMULATION':'0'}):
            with self.assertRaises(HTTPException):accept(g,user,record['id'])
        self.record('C3-018',{'accepted':accepted,'again':again,'history_before':before,'history_after':after,'submitted_turns':submitted},record['device_refs']==['9101','9102'] and accepted['conversation_id']==again['conversation_id'] and again['already_accepted'] and submitted==0 and 'old observation payload was withheld' in str(after),mode='actual_graph_registry_sqlite_handoff_mocked_semantic_decision')
