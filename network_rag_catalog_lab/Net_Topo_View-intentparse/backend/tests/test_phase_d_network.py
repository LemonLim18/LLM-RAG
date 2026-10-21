"""Independent small graph oracles for the declared model; no packet execution."""
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from development.examples import mixed_vendor_path,performance_observations,protocol_observations
from development.network_model import NetworkModel,Flow,assess_flow,forwarding,protocol_findings,metric_findings
from local_providers.development import Scenario,ScenarioManager


class ForwardingTests(unittest.TestCase):
    def setUp(self):self.s=Scenario.model_validate(mixed_vendor_path()).model_dump();self.flow=Flow.model_validate(self.s['network']['flows'][0])

    def test_three_vendor_forward_and_return(self):
        result=assess_flow(self.s,self.flow)
        self.assertEqual(result['status'],'delivered')
        self.assertEqual([h['hostname'] for h in result['forward']['branches'][0]['hops']],['Branch-Aster','Core-Birch'])
        self.assertEqual([h['hostname'] for h in result['return']['branches'][0]['hops']],['Edge-Cedar','Core-Birch'])

    def test_return_failure_and_incomplete_table_are_not_healthy(self):
        self.s['network']['tables'][2]['routes']=[]
        result=assess_flow(self.s,self.flow)
        self.assertEqual(result['forward']['status'],'delivered');self.assertEqual(result['return']['status'],'failed');self.assertEqual(result['status'],'partial')
        self.s['network']['tables'][2]['complete']=False
        self.assertEqual(assess_flow(self.s,self.flow)['status'],'unknown')

    def test_acl_first_match_direction_and_return(self):
        self.s['network']['policies']=[dict(id='core-in',interface_id=2,direction='ingress',default_action='permit',
            rules=[dict(id='deny-flow',source='198.18.0.1/32',destination='198.18.0.3/32',action='deny'),dict(id='permit-rest',action='permit')])]
        result=assess_flow(self.s,self.flow)
        self.assertEqual(result['forward']['status'],'failed');self.assertIn('core-in/deny-flow',result['forward']['branches'][0]['reason'])
        location=result['forward']['branches'][0]['failure_location']
        self.assertEqual(location['hostname'],'Core-Birch')
        self.assertEqual(location['interface'],'ge-0/0/0.0')
        self.assertEqual(location['direction'],'ingress')
        self.assertEqual(location['policy_rule'],'core-in/deny-flow')
        self.assertEqual([h['hostname'] for h in result['forward']['branches'][0]['hops']],['Branch-Aster'])
        self.assertEqual(result['return']['status'],'delivered')
        self.s['network']['policies'][0]['rules'].reverse()
        self.assertEqual(assess_flow(self.s,self.flow)['status'],'delivered')

    def test_ecmp_one_branch_down_and_budget(self):
        self.s['interfaces'] += [dict(id=8,device_id=1100,name='GigabitEthernet0/2',prefix='10.44.0.9/30',admin_status='down',oper_status='down',vrf='default'),dict(id=9,device_id=1300,name='GigabitEthernet0/0/2',prefix='10.44.0.10/30',admin_status='up',oper_status='up',vrf='default')]
        self.s['planned_links'].append(dict(id=3,src_device_id=1100,src_interface_id=8,dst_device_id=1300,dst_interface_id=9))
        route=self.s['network']['tables'][0]['routes'][0]
        route['next_hops'].append(dict(interface_id=8,address='10.44.0.10',resolved=True))
        self.assertEqual(assess_flow(self.s,self.flow)['status'],'partial')
        self.assertEqual(forwarding(self.s,self.flow,max_branches=1)['status'],'unknown')

    def test_longest_prefix_and_recursive_resolution(self):
        table=self.s['network']['tables'][0]
        table['routes'].append(dict(id='discard-default',prefix='0.0.0.0/0',origin='static',preference=1,action='discard'))
        self.assertEqual(assess_flow(self.s,self.flow)['status'],'delivered')
        table['routes'][0]['next_hops']=[dict(address='10.44.0.2',resolved=True)]
        table['routes'].append(dict(id='connected-resolution',prefix='10.44.0.0/30',origin='connected',preference=0,next_hops=[dict(interface_id=1,resolved=True)]))
        self.assertEqual(assess_flow(self.s,self.flow)['status'],'delivered')
        table['routes'][-1]['next_hops']=[dict(address='10.44.0.2',resolved=True)]
        self.assertEqual(assess_flow(self.s,self.flow)['status'],'unknown')

    def test_vrf_isolation_and_explicit_leak(self):
        for i in self.s['interfaces']:i['vrf']='blue' if i['device_id']==1100 or i['id'] in {2,6} else 'red'
        self.flow=self.flow.model_copy(update={'vrf':'blue','destination_vrf':'red'})
        tables=self.s['network']['tables'];tables[0]['vrf']='blue';tables[1]['vrf']='blue';tables[2]['vrf']='red'
        core_blue=tables[1];to_cedar=core_blue['routes'].pop(0)
        core_red=dict(device_id=1200,vrf='red',complete=True,routes=[to_cedar])
        self.s['network']['tables'].append(core_red)
        self.assertEqual(assess_flow(self.s,self.flow)['status'],'failed')
        core_blue['routes'].append(dict(id='explicit-blue-red',prefix='198.18.0.3/32',origin='static',preference=10,action='leak',leak_to_vrf='red'))
        core_red['routes'].append(dict(id='explicit-red-blue',prefix='198.18.0.1/32',origin='static',preference=10,action='leak',leak_to_vrf='blue'))
        self.assertEqual(assess_flow(self.s,self.flow)['status'],'delivered')

    def test_unknown_neighbors_policies_and_stale_inputs(self):
        self.s['network']['tables'][0]['routes'][0]['next_hops'][0]['resolved']=None
        self.assertEqual(assess_flow(self.s,self.flow)['status'],'unknown')
        self.s['network']['tables'][0]['routes'][0]['next_hops'][0]['resolved']=True
        self.s['network']['policy_attachments_complete']=False
        self.assertEqual(assess_flow(self.s,self.flow)['status'],'unknown')

    def test_invalid_references_ports_prefixes_and_future_time(self):
        for mutation in [lambda s:s['network']['tables'][0]['routes'][0].update(prefix='198.18.0.3/24'),
                         lambda s:s['network']['tables'][0]['routes'][0]['next_hops'][0].update(interface_id=4),
                         lambda s:s['network'].update(observed_at='2030-01-01T00:00:00Z')]:
            s=deepcopy(self.s);mutation(s)
            with self.assertRaises(ValueError):Scenario.model_validate(s)

    def test_authorized_reader_and_existing_assessment(self):
        from db.manager import DatabaseManager
        from llm.gateway_store import ensure_schema
        from llm.gateway_network import NetworkReader,NetworkQuery
        from llm.gateway_services import inventory_snapshot
        from llm.orchestration.scenario_reasoning import assess_scenario
        from llm.tools import ToolAuthorization
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'COGNISHIELD_DEV_SIMULATION':'1'}):
            db=DatabaseManager(str(Path(folder)/'app.db'));db.initialize();ensure_schema(db)
            try:
                self.s['id']='IMPORTED-D2-TEST'
                manager=ScenarioManager(Path(folder)/'state.json');manager.change('import',manager.snapshot()[1]['source_revision'],self.s)
                db._development_scenario=manager
                auth=ToolAuthorization('alice','engineer','floating','owned',frozenset({'network.state'}),permissions=frozenset({'network.inventory.read'}))
                result=NetworkReader(db).read('state',NetworkQuery(device_refs=['Branch-Aster','Core-Birch','Edge-Cedar']),auth)
                self.assertEqual(result.status,'success');self.assertEqual(result.data['records'][0]['assessment']['status'],'delivered')
                context=[dict(tool='network.state',status=result.status,data=result.data,evidence_ids=[e.id for e in result.evidence])]
                assessment=assess_scenario(context,result.evidence)
                self.assertEqual(assessment['conclusion_status'],'healthy_within_tested_scope')
                import asyncio
                from llm.gateway_services import registry_for
                from llm.gateway_network import network_context
                inventory_auth=ToolAuthorization('alice','engineer','floating','owned',frozenset({'inventory.read'}),permissions=frozenset({'network.inventory.read'}))
                rows,_,_=asyncio.run(network_context(db,registry_for(db),inventory_auth,'Show Core-Birch interfaces',domains_override=['inventory'],device_refs_override=['1200']))
                self.assertEqual([d['hostname'] for d in rows[0]['data']['devices']],['Core-Birch'])
                stale=deepcopy(self.s);stale['logical_time']='2026-10-18T02:00:00Z'
                manager.change('edit',manager.snapshot()[1]['source_revision'],stale)
                fresh=NetworkReader(db).read('state',NetworkQuery(),auth)
                context=[dict(tool='network.state',status=fresh.status,data=fresh.data,evidence_ids=[e.id for e in fresh.evidence])]
                self.assertEqual(assess_scenario(context,fresh.evidence)['conclusion_status'],'insufficient_evidence')
                with db._connect() as c:self.assertEqual(c.execute('SELECT count(*) FROM devices').fetchone()[0],0)
            finally:db.close()


class ProtocolTests(unittest.TestCase):
    def test_ospf_two_way_is_not_always_faulty_and_timer_conflict(self):
        s=mixed_vendor_path();peer=dict(device_id=1100,interface_id=1,router_id='198.18.0.1',area='0.0.0.0',hello_seconds=10,dead_seconds=40,network_type='broadcast',role='DROther')
        other={**peer,'device_id':1200,'interface_id':2,'router_id':'198.18.0.2'}
        s['network']['ospf']=[dict(id='ospf-peer',left=peer,right=other,observed_state='2-Way')]
        findings=protocol_findings(NetworkModel.model_validate(s['network']))
        self.assertEqual(findings[0]['assessment'],'healthy_within_tested_scope')
        other['hello_seconds']=20;s['network']['ospf'][0]['observed_state']='Down'
        self.assertEqual(protocol_findings(NetworkModel.model_validate(s['network']))[0]['assessment'],'strongly_supported')
        s['network']['ospf'][0]['observed_state']='Full'
        self.assertTrue(protocol_findings(NetworkModel.model_validate(s['network']))[0]['conflict'])

    def test_right_peer_only_and_raw_routing_records_are_readable(self):
        from llm.gateway_network import NetworkQuery
        with tempfile.TemporaryDirectory() as folder:
            manager=ScenarioManager(Path(folder)/'state.json')
            manager.change('select',manager.snapshot()[1]['source_revision'],scenario_id='PROTOCOL-MIXED-001')
            s,_=manager.snapshot();cedar=[d for d in s['devices'] if d['id']==1300]
            result=manager.result('state',NetworkQuery(),cedar)
            protocols=[r for r in result.data['records'] if r['kind']=='protocol_assessment']
            self.assertEqual(len(protocols),1);self.assertEqual(protocols[0]['observed_state'],'Established')
            tables=[r for r in result.data['records'] if r['kind']=='routing_table']
            self.assertEqual(tables[0]['routes'][0]['prefix'],'198.18.0.1/32')
            self.assertNotIn('Branch-Aster',json.dumps(result.data['records']))

    def test_unknown_authentication_and_mtu_exceptions_are_not_confirmed_mismatches(self):
        s=protocol_observations();a=s['network']['ospf'][0]['left'];b=s['network']['ospf'][0]['right']
        a.update(mtu=1500,authentication=None);b.update(mtu=9000,authentication='matching-method-A')
        row=protocol_findings(NetworkModel.model_validate(s['network']))[0]
        self.assertFalse(row['conflict']);self.assertIn('authentication',row['unknown_prerequisites'])
        self.assertTrue(row['conditional_findings'])
        a['mtu_ignore']=False;b['mtu_ignore']=False
        self.assertTrue(protocol_findings(NetworkModel.model_validate(s['network']))[0]['conflict'])

    def test_bgp_local_and_neighbor_addresses_have_explicit_roles(self):
        row=protocol_findings(NetworkModel.model_validate(protocol_observations()['network']))[1]
        self.assertEqual(row['peer_parameters'][0]['local_address'],'10.44.0.5')
        self.assertEqual(row['peer_parameters'][0]['neighbor_address'],'10.44.0.6')
        self.assertEqual(row['peer_parameters'][0]['local_as'],65020)


class MetricsTests(unittest.TestCase):
    def test_correlation_is_qualified_and_counter_resets_are_not_rates(self):
        s=performance_observations();model=NetworkModel.model_validate(s['network'])
        findings=metric_findings(model,s['interfaces'])
        traffic=next(r for r in findings if r['values']['metric']=='out_bps')
        self.assertEqual(traffic['values']['peak_utilization_pct'],95)
        self.assertEqual(traffic['values']['congestion_hypothesis'],'plausible')
        self.assertEqual(findings[1]['values']['delta'],12)
        model.metrics[1].samples[1].value=1
        reset=metric_findings(model,s['interfaces'])[1]
        self.assertTrue(reset['values']['counter_reset_or_wrap']);self.assertNotIn('delta',reset['values'])

    def test_missing_gap_and_units(self):
        s=performance_observations();s['network']['metrics'][0]['samples'][1]['value']=None
        findings=metric_findings(NetworkModel.model_validate(s['network']),s['interfaces'])
        self.assertTrue(findings[0]['values']['missing_values']);self.assertNotIn('congestion_hypothesis',findings[0]['values'])
        s['network']['metrics'][0]['unit']='percent'
        with self.assertRaises(ValueError):Scenario.model_validate(s)

    def test_monitoring_and_ai_share_metrics_without_zero_filling(self):
        from local_providers.development import observation_set
        from llm.gateway_network import NetworkQuery
        with tempfile.TemporaryDirectory() as folder:
            manager=ScenarioManager(Path(folder)/'state.json')
            manager.change('select',manager.snapshot()[1]['source_revision'],scenario_id='PERFORMANCE-MIXED-001')
            s,_=manager.snapshot();core=[d for d in s['devices'] if d['id']==1200]
            result=manager.result('telemetry',NetworkQuery(),core)
            self.assertEqual(len(result.data['records']),2)
            monitoring=observation_set(manager).bundle()
            text=json.dumps(monitoring)
            self.assertIn('950000000',text)

    def test_bgp_idle_is_unknown_and_established_zero_prefixes_is_not_down(self):
        s=mixed_vendor_path();a=dict(device_id=1200,address='10.44.0.5',local_as=65020,remote_as=65030,address_families=['ipv4_unicast'])
        b=dict(device_id=1300,address='10.44.0.6',local_as=65030,remote_as=65020,address_families=['ipv4_unicast'])
        s['network']['bgp']=[dict(id='bgp-peer',left=a,right=b,observed_state='Idle')]
        self.assertEqual(protocol_findings(NetworkModel.model_validate(s['network']))[0]['assessment'],'insufficient_evidence')
        s['network']['bgp'][0].update(observed_state='Established',accepted_prefixes=[],rejected_prefixes=['198.18.0.1/32'],policy_observed=True)
        self.assertEqual(protocol_findings(NetworkModel.model_validate(s['network']))[0]['assessment'],'healthy_within_tested_scope')
        b['remote_as']=65099
        self.assertTrue(protocol_findings(NetworkModel.model_validate(s['network']))[0]['conflict'])
