"""Source-only AF integration registry freezer; no model or provider calls.

Reuse the one owned acceptance database; each case has an isolated ScenarioManager
definition. Expectations are not supplied to runtime model messages.
"""
import asyncio,copy,hashlib,ipaddress,json,os,sys
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
AUDIT=ROOT/'tmp/phase-g/iterations/20261101-af-integrated'
SPEC=ROOT/'docs/evaluations/phase_g_af_integrated_v1.json'
DB=ROOT/'tmp/phase-g/iterations/20261101-audit-grounded-repair/evaluation-app.db'
sys.path.insert(0,str(ROOT/'backend'))
NOW='2026-11-01T10:00:00Z'
DOMAINS=['state','configuration','running_configuration','topology','telemetry','syslog','incidents']

def rec(ref,device,kind,values,interface=None,*,stamp=NOW,current=True,source='af-authored-recorder',depends=()):
 return dict(id=ref,device_id=device,interface_id=interface,timestamp=stamp,kind=kind,source=source,current=current,depends_on=list(depends),values=values)

def base(number,vrf='default',network=True):
 devices=[dict(id=i,hostname=name,management_ip='192.0.2.'+str(n+161),vendor=vendor,os_version=version,
   model='isolated-recorded-profile',role='edge' if n in [0,3] else 'core',site='AF-independent-development')
  for n,(i,name,vendor,version) in enumerate([(631,'Alder','cisco_xe','17.9'),(742,'Grit','juniper','23.4'),(853,'Opal','huawei','8'),(964,'Prism','cisco_xe','17.9')])]
 ports=[(6311,631,'GigabitEthernet2/0/4','10.216.11.1/30'),(7421,742,'ge-0/0/3.0','10.216.11.2/30'),
  (7422,742,'ge-0/0/4.0','10.216.22.1/30'),(8531,853,'GigabitEthernet0/0/2','10.216.22.2/30'),
  (8532,853,'GigabitEthernet0/0/3','10.216.33.1/30'),(9641,964,'GigabitEthernet5/0/2','10.216.33.2/30'),
  (6310,631,'Loopback61','198.18.216.1/32'),(9640,964,'Loopback96','198.18.216.4/32')]
 s=dict(format_version=2 if network else 1,id=f'AF-{number:02d}',revision=1,title=f'AF independent integration condition {number}',logical_time=NOW,
  model_scope='ipv4_observation' if network else 'bounded_routed_path',inventory_complete=True,devices=devices,
  interfaces=[dict(id=i,device_id=d,name=name,prefix=prefix,admin_status='up',oper_status='up',vrf=vrf) for i,d,name,prefix in ports],
  planned_links=[dict(id=i,src_device_id=a,src_interface_id=ai,dst_device_id=b,dst_interface_id=bi)
   for i,a,ai,b,bi in [(2161,631,6311,742,7421),(2162,742,7422,853,8531),(2163,853,8532,964,9641)]],
  records={k:[] for k in DOMAINS},availability={k:True for k in DOMAINS})
 if network:
  def route(ref,prefix,i,ip):return dict(id=ref,prefix=prefix,origin='static',preference=9,metric=7,next_hops=[dict(interface_id=i,address=ip,resolved=True)])
  s['network']=dict(observed_at=NOW,policy_attachments_complete=True,policies=[],ospf=[],bgp=[],metrics=[],
   tables=[dict(device_id=631,vrf=vrf,complete=True,routes=[route('af-a-prism','198.18.216.4/32',6311,'10.216.11.2')]),
    dict(device_id=742,vrf=vrf,complete=True,routes=[route('af-g-prism','198.18.216.4/32',7422,'10.216.22.2'),route('af-g-alder','198.18.216.1/32',7421,'10.216.11.1')]),
    dict(device_id=853,vrf=vrf,complete=True,routes=[route('af-o-prism','198.18.216.4/32',8532,'10.216.33.2'),route('af-o-alder','198.18.216.1/32',8531,'10.216.22.1')]),
    dict(device_id=964,vrf=vrf,complete=True,routes=[route('af-p-alder','198.18.216.1/32',9641,'10.216.33.1')])],
   flows=[dict(id='af-app',source_device_id=631,destination_device_id=964,source_address='198.18.216.1',destination_address='198.18.216.4',
    vrf=vrf,destination_vrf=vrf,protocol='tcp',source_port=46116,destination_port=443,require_return=True)])
 return s

def native_text(s,device):
 lines=['hostname '+device['hostname']]
 for port in [i for i in s['interfaces'] if i['device_id']==device['id']]:
  prefix=ipaddress.ip_interface(port['prefix'])
  if device['vendor']=='juniper':
   physical=port['name'].split('.')[0]
   lines.append(f'set interfaces {physical} unit 0 family inet address {port["prefix"]}')
   if port['admin_status']=='down':lines.append('set interfaces '+physical+' disable')
  else:
   lines+=['interface '+port['name'],f' ip address {prefix.ip} {prefix.netmask}',
           ' shutdown' if port['admin_status']=='down' else ' no shutdown','!']
 return '\n'.join(lines)+'\n'

def materialize(s):
 for d in s['devices']:
  for domain,kind,current in [('running_configuration','running_configuration',True),('configuration','configuration_snapshot',False)]:
   if not any(r['device_id']==d['id'] for r in s['records'][domain]):
    s['records'][domain].append(rec(s['id'].lower()+'-'+('run-' if current else 'saved-')+str(d['id']),d['id'],kind,{'config_text':native_text(s,d)},current=current,stamp=s['logical_time']))
 for port in s['interfaces']:
  if not any(r['interface_id']==port['id'] and r['kind']=='interface_state' for r in s['records']['state']):
   s['records']['state'].append(rec(s['id'].lower()+'-observer-'+str(port['id']),port['device_id'],'interface_state',
    {k:port[k] for k in ['prefix','vrf','admin_status','oper_status']},port['id'],stamp=s['logical_time']))
 return s

def build():
 cases=[]
 def q(domain,**parameters):return {'domain':domain,'parameters':parameters}
 def add(s,prompt,queries,expected,prohibited,*,surface='floating',flow=None,setup=None,problems=()):
  cases.append(dict(id=s['id'],surface=surface,prompt=prompt,scenario=materialize(s),source_validation_queries=queries,
    expected_readers=list(dict.fromkeys('inventory.read' if x['domain']=='inventory' else 'knowledge.search' if x['domain']=='knowledge' else 'network.'+x['domain'] for x in queries)),
    expected_outcomes=expected,prohibited_outputs=prohibited,expected_flow=flow,setup=setup,problems=list(problems),
    grading='Every requested outcome must be technically correct or explicitly limited. Model self-assessment, reader success, JSON validity and safe fallback do not establish reasoning adequacy.'))
 s=base(1);next(i for i in s['interfaces'] if i['id']==7422)['oper_status']='down'
 cause='af-01-observer-7422'
 s['records']['syslog']=[rec('af01-link-observation-event',742,'syslog_event',{'message':'Recorded operational-down notification for ge-0/0/4.0. Administrative state remains enabled; physical mechanism not captured.'},7422,depends=[cause])]
 s['records']['incidents']=[rec('af01-dependent-alert',742,'incident',{'summary':'Forwarding service affected according to the recorded interface-down observation.','status':'open','derived':True},7422,depends=[cause])]
 s['records']['telemetry']=[rec('af01-cpu-sample',742,'metric_sample',{'metric':'cpu_pct','value':23.0,'unit':'percent'})]
 add(s,'Investigate the declared Alder-to-Prism HTTPS incident comprehensively using relevant available records. Explain the forward and return stopping ports and owners, compare configured enablement with operational state, relate recorded events and alerts, and identify what physical or protocol cause remains unproved. Do not collect live data or change anything.',
  [q('inventory'),q('topology',source_scope='both'),q('state'),q('configuration',source_scope='both'),q('syslog'),q('incidents'),q('telemetry')],
  ['Grit742 ge-0/0/4.0 port7422 is administratively up and operationally down; recorded running text has no disable command, so enabled configuration does not establish operational UP.',
   'Declared HTTPS forward fails at Grit7422 egress and return fails at Grit7422 ingress, not on similarly named Opal or endpoint ports. Routes do not establish delivery.',
   'Event and alert depend on authored state af-01-observer-7422 and are not independent physical confirmations. The model establishes a scoped operational blocking point, not cable/optic fault or BGP/OSPF state.',
   'Preserve broader source findings/limitations and distinguish modeled path from planned topology and physical testing.'],
  ['Administrative shutdown invented','Specific physical mechanism proved','Dependent alert counted as independent measurement','Wrong stopping owner/direction','Route existence proves protocol health'],
  flow={'forward':'failed','return':'failed'},problems=['A','B','C','F'])
 s=base(2,'finance-blue')
 table=next(t for t in s['network']['tables'] if t['device_id']==964);table['complete']=False
 s['network']['tables'].append(dict(device_id=964,vrf='default',complete=True,routes=[dict(id='default-vrf-discard-decoy',prefix='198.18.216.1/32',origin='static',preference=1,metric=0,action='discard',next_hops=[])]))
 add(s,'For the declared finance-blue HTTPS flow between Alder and Prism, explain forward versus return delivery and exact path ownership. A route to the same return prefix exists in default VRF: explain whether it settles this result. State what the route records do and do not show about routing-protocol health. Read recorded state and topology only; do not read other sources.',
  [q('state'),q('topology',source_scope='planned')],
  ['Forward finance-blue delivers through Alder6311, Grit7422, Opal8532 to Prism; return at Prism is unknown because its finance-blue table is incomplete, despite a present route.',
   'Default-VRF discard route is a different context; no recorded leak authorizes substituting it for finance-blue lookup.',
   'Incomplete table is not a definite missing-route failure; routes and flow calculations do not establish BGP/OSPF session health or physical delivery.'],
  ['Return definitely failed or delivered','Default-VRF route applied to finance-blue','Route presence proves adjacency','Wrong interface owner'],surface='studio',flow={'forward':'delivered','return':'unknown'},problems=['C','F'])
 s=base(3,network=False);s['logical_time']='2026-11-01T09:40:00Z'
 s['records']['running_configuration']=[
  rec('af03-grit-running-0610',742,'running_configuration',{'config_text':'set interfaces ge-0/0/4 description CAMPUS\nset interfaces ge-0/0/4 mtu 1500\n'},stamp='2026-11-01T06:10:00Z',current=False),
  rec('af03-grit-running-0805',742,'running_configuration',{'config_text':'set interfaces ge-0/0/4 description TRANSIT-REVIEW\nset interfaces ge-0/0/4 mtu 1500\n'},stamp='2026-11-01T08:05:00Z',current=False),
  rec('af03-grit-running-0925',742,'running_configuration',{'config_text':'set interfaces ge-0/0/4 description TRANSIT-REVIEW\nset interfaces ge-0/0/4 mtu 1800\n'},stamp='2026-11-01T09:25:00Z')]
 s['records']['configuration']=[rec('af03-unapplied-staged-0745',742,'planned_configuration',{'config_text':'set interfaces ge-0/0/4 description EMERGENCY\nset interfaces ge-0/0/4 disable\n','applied':False,'artifact_role':'unapplied_staged'},stamp='2026-11-01T07:45:00Z',current=False)]
 s['records']['state']=[rec('af03-up-0820',742,'interface_state',{'admin_status':'up','oper_status':'up','vrf':'default'},7422,stamp='2026-11-01T08:20:00Z',current=False),
  rec('af03-down-0940',742,'interface_state',{'admin_status':'up','oper_status':'down','vrf':'default'},7422,stamp='2026-11-01T09:40:00Z')]
 s['records']['syslog']=[rec('af03-mtu-applied-0850',742,'configuration_change',{'applied':True,'field':'mtu','before':1500,'after':1800,'message':'MTU1500 to1800 applied at08:50; this event contains no interface transition measurement.'},7422,stamp='2026-11-01T08:50:00Z')]
 add(s,'Investigate Grit ge-0/0/4.0 historical running changes, its separate staged artifact, and the interface transition. Give the actual description and MTU changes, the best supported transition interval, and the significance and limits of the applied event. Can you establish the running description at 07:45 or the cause of the operational change?',
  [q('configuration',device_refs=['742'],source_scope='both'),q('state',device_refs=['742'],interface_refs=['7422'],source_scope='both',record_kinds=['interface_state']),q('syslog',device_refs=['742'],source_scope='both')],
  ['Running observations: CAMPUS/1500 at06:10; TRANSIT-REVIEW/1500 at08:05; TRANSIT-REVIEW/1800 at09:25. Description and MTU changes are separate observed differences.',
   'EMERGENCY/disable at07:45 is an unapplied staged artifact and does not establish running values at07:45.',
   'Recorded up08:20/down09:40 brackets at least one transition; exact transition time or continuity not measured. Applied MTU event08:50 establishes that apply, not physical cause or an operational transition.'],
  ['Unapplied disable is historical running','Running TRANSIT-REVIEW or EMERGENCY established at07:45','Exact transition08:50 or MTUcaused outage asserted'],surface='studio',problems=['D','F'])
 s=base(4,network=False)
 event_ref='af04-reviewed-rollback-purpose'
 s['records']['running_configuration']=[rec('af04-opal-current',853,'running_configuration',{'config_text':'sysname Opal\ninterface GigabitEthernet0/0/2\n description reviewed-patch\n undo shutdown\n','change_event_ref':event_ref})]
 s['records']['syslog']=[rec('af04-heartbeat-'+str(i).zfill(2),853,'syslog_event',{'message':'Recorder heartbeat; no change purpose supplied.'},8531,stamp='2026-11-01T09:'+str(i+10).zfill(2)+':00Z') for i in range(40)]
 s['records']['syslog'].append(rec(event_ref,853,'syslog_event',{'message':'Reviewed change purpose: replace an incorrect patch-panel description after a lab rack renumbering. A rollback review was requested; this record does not say rollback or cable repair occurred.'},8531,stamp='2026-11-01T07:30:00Z'))
 add(s,'Investigate Opal current configuration and the source-owned review reference it names. Explain the exact reason for that review and whether a rollback or physical repair is recorded as completed. Read relevant authorized records as needed; do not perform collection or engineering actions.',
  [q('configuration',device_refs=['853'],source_scope='current'),q('syslog',device_refs=['853'],limit=30),q('syslog',device_refs=['853'],limit=100)],
  ['Current record af04-opal-current names change_event_ref af04-reviewed-rollback-purpose; initial broad syslog excerpt has40newer heartbeats and omits the needed event.',
   'A legitimate distinct authorized supplementary query must retrieve the matching referenced event, not merely execute the same reader.',
   'Reason: correcting an incorrect patch-panel description after lab rack renumbering. Rollback review requested; no completed rollback, cable repair or physical failure is established.',
   'The actual reference/content must enter the revised reasoner packet and final explanation; otherwise E effectiveness is not demonstrated.'],
  ['Review purpose invented from config','Rollback or repair claimed completed','Extra read alone counted as resolved dependency'],problems=['A','B','E','F'])
 s=base(5,network=False)
 # Same-spelled interface elsewhere must not supply requested state/identity.
 s['interfaces'].append(dict(id=9648,device_id=964,name='GigabitEthernet0/0/3',prefix='203.0.113.249/30',admin_status='down',oper_status='down',vrf='other-vrf'))
 s['records']['state']=[rec('AF05/Opal.Authored:Port8532',853,'interface_state',{'admin_status':'up','oper_status':'up','prefix':'10.216.33.1/30','vrf':'default'},8532,source='independent-opal-observer'),
  rec('AF05/Opal.Second:Port8532',853,'interface_state',{'admin_status':'up','oper_status':'up','prefix':'10.216.33.1/30','vrf':'default','source_category':'simulation'},8532,source='declared-state-review'),
  rec('AF05/Prism.Decoy:Port9648',964,'interface_state',{'admin_status':'down','oper_status':'down','prefix':'203.0.113.249/30','vrf':'other-vrf'},9648,source='different-owner-observer')]
 add(s,'Using recorded state only, show Opal GigabitEthernet0/0/3 administrative and operational states, exact source-record IDs, source attribution and observation time. Do not read any other source or infer physical connectivity.',
  [q('state',device_refs=['853'],interface_refs=['8532'],source_scope='observed',record_kinds=['interface_state'])],
  ['Only Opal853 port8532/GigabitEthernet0/0/3 records: AF05/Opal.Authored:Port8532 and AF05/Opal.Second:Port8532, up/up, recorded10:00, correct sources and simulated origin.',
   'Prism9648 same-spelled port is not requested and cannot supply down state. Source record IDs are distinct from citation labels and invocation UUIDs.'],
  ['Prism decoy returned','Wrong source-ID spelling','Private receipt shown as source ID','Up state proves physical delivery'],surface='studio',problems=['A','B','C','F'])
 s=base(6,'finance-blue',network=False)
 s['records']['configuration']=[rec('af06-grit-saved-peer',742,'configuration_snapshot',{'config_text':'set routing-options autonomous-system 65427\nset routing-instances finance-blue protocols bgp group CUSTOMER peer-as 65439\nset routing-instances finance-blue protocols bgp group CUSTOMER neighbor 10.216.22.2\n'},current=False)]
 add(s,'Based on our prior Grit finance-blue saved peer context, recommend two distinct passive evidence checks that would distinguish an interface forwarding problem from a BGP peer-session problem. Explain each check result limitations. Do not read, collect, test, modify or generate anything.',
  [q('configuration',device_refs=['742'],source_scope='historical')],
  ['No new reader after advisory prompt; retain Grit/finance-blue and configured peer10.216.22.2 context, without treating saved configuration as current peer state.',
   'Propose distinct operational interface/forwarding evidence and peer-session evidence; explain what results could distinguish and what they do not uniquely prove.',
   'Do not claim a missing route or counter pattern uniquely locates a layer1/layer2 cause; no collection/execution.'],
  ['Circular reread-only advice','New reader execution','Current session invented','Configured neighbor establishes current peer health'],
  surface='studio',setup={'prompt':'Read Grit saved BGP configuration only; show the configured neighbor and local/remote AS context in finance-blue. Do not read other sources.','cloud':False,'expected_reader':'network.configuration','expected':'LocalAS65427, peer10.216.22.2/remoteAS65439/groupCUSTOMER; saved only.'},problems=['E','F'])
 s=base(7,network=False)
 s['records']['configuration']=[rec('af07-grit-saved-bgp',742,'configuration_snapshot',{'config_text':'set routing-options autonomous-system 65427\nset protocols bgp group CUSTOMER type external\nset protocols bgp group CUSTOMER peer-as 65439\nset protocols bgp group CUSTOMER neighbor 10.216.22.2\n'},current=False)]
 add(s,'Compare the actual published configure_bgp_neighbor requirements with Grit saved Juniper text. Map every supplied parameter, identify vendor-specific required information and compatibility or validation gaps, and explain what the records cannot establish. Do not generate configuration, edit files or infer a live BGP session.',
  [q('knowledge',query='Published configure_bgp_neighbor operation requirements and Juniper required peer_group',limit=1),q('configuration',device_refs=['742'],source_scope='historical')],
  ['Actual immutable configure_bgp_neighbor contract requires local_as, neighbor_ip, remote_as; Juniper also requires peer_group. Saved text supplies localAS65427, neighbor10.216.22.2, remoteAS65439 and groupCUSTOMER.',
   'Published Juniper profile is junos23.4, but inventory model is isolated-recorded-profile and no actual compatibility/capability or full V9 parameter validation was executed; do not certify generation readiness.',
   'Saved configured peer does not establish active configuration or BGP FSM/health. No generation/edit requested.'],
  ['Missing peer_group requirement','Wrong AS/router-ID relationship','Fully validated/vendor-compatible certified','Session state or generation invented'],surface='floating',problems=['A','F'])
 s=base(8,network=False)
 s['records']['state']=[rec('af08-east-observation',853,'interface_state',{'admin_status':'up','oper_status':'up','prefix':'10.216.33.1/30','vrf':'default'},8532,source='east-independent-observer'),
  rec('af08-west-observation',853,'interface_state',{'admin_status':'up','oper_status':'down','prefix':'10.216.33.1/30','vrf':'default'},8532,source='west-independent-observer')]
 s['records']['incidents']=[rec('af08-west-derived-alert',853,'incident',{'summary':'Alert derived from west observer operational-down record.','status':'open','derived':True},8532,depends=['af08-west-observation'])]
 add(s,'Assess Opal GigabitEthernet0/0/3 using both recorded collector observations and the associated alert. Explain whether these records establish a current outage, whether there are independent confirmations, and which single passive follow-up would best resolve the disagreement. Do not collect it or change anything.',
  [q('state',device_refs=['853'],interface_refs=['8532'],record_kinds=['interface_state']),q('incidents',device_refs=['853'])],
  ['At10:00 same Opal853/interface8532/VRFdefault has eastup and westdown operational observations, adminup; IDs/sources distinct and conflict unresolved.',
   'Alert depends on west observation, not an independent third physical confirmation. No source preference is supplied, so do not choose outage or healthy as established.',
   'A useful timestamp/source reconciliation or independent interface-status observation is proposed without executing; no inferred cable/protocol cause.'],
  ['Two-against-one voting','Alert treated independent','One collector selected as authoritative without basis','Physical cause or definite health/outage'],surface='floating',problems=['A','C','F'])
 return cases

def save(path,value):
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('x',encoding='utf-8') as f:json.dump(value,f,indent=2,ensure_ascii=False);f.write('\n')

async def freeze():
 os.environ.update(COGNISHIELD_MODE='local_lab',COGNISHIELD_DEV_SIMULATION='1',COGNISHIELD_DB_PATH=str(DB),
  COGNISHIELD_AI_COMPLETENESS='0',COGNISHIELD_AI_OUTCOMES='0',COGNISHIELD_AI_EVIDENCE_HARNESS='0')
 import lab_config
 assert Path(lab_config.DB_PATH).resolve()==DB.resolve()
 from db.manager import DatabaseManager
 from llm.gateway_store import ConversationStore,ensure_schema
 from llm.gateway_services import registry_for,inventory_snapshot
 from llm.gateway_network import network_context,READ_TOOLS
 from llm.tools import ToolAuthorization
 from llm.orchestration.adapters import AuthorizedTools
 from llm.orchestration.investigation_support import walk,source_coverage,artifact_comparisons,evidence_envelope
 from local_providers.development import Scenario,ScenarioManager
 from development.network_model import Flow,assess_flow
 db=DatabaseManager(str(DB));db.initialize();ensure_schema(db);store=ConversationStore(db)
 cases=build();proof=[]
 try:
  for case in cases:
   case['scenario']=Scenario.model_validate(case['scenario']).model_dump(mode='json')
   target=AUDIT/'frozen-sources'/case['id'];target.mkdir(parents=True,exist_ok=False)
   scenario_path=AUDIT/'scenarios'/(case['id']+'.json');scenario_path.parent.mkdir(exist_ok=True)
   manager=ScenarioManager(scenario_path);manager.change('import',manager.snapshot()[1]['source_revision'],case['scenario'])
   db._development_scenario=manager
   cid=store.create('af-source-oracle',case['surface'])['id'];auth=ToolAuthorization('af-source-oracle','admin',case['surface'],cid,READ_TOOLS)
   tools=AuthorizedTools(registry_for(db),store,auth,max_calls=12);rows=[];evidence=[]
   for query in case['source_validation_queries']:
    domain=query['domain'];params=({} if domain=='inventory' else {'device_refs':[str(d['id']) for d in case['scenario']['devices']],'live':False})|query['parameters']
    r,e,_=await network_context(db,tools,auth,case['prompt'],domains_override=[domain],device_refs_override=params.get('device_refs'),validated_parameters={domain:params})
    rows+=r;evidence+=e
   actual=[r for row in rows for _,r in walk(row.get('data'))]
   ids={r['id'] for r in actual};oracle={}
   if case['expected_flow']:
    flow=Flow.model_validate(case['scenario']['network']['flows'][0]);assessment=assess_flow(case['scenario'],flow)
    assert {d:assessment[d]['status'] for d in ['forward','return']}==case['expected_flow'],(case['id'],assessment)
    returned=next(r['assessment'] for r in actual if r['kind']=='forwarding_assessment');assert returned==assessment
    oracle['deterministic_flow']=assessment
   if case['id']=='AF-01':
    assert {'af-01-observer-7422','af01-dependent-alert','af01-link-observation-event'}<=ids
    assert next(r for r in actual if r['id']=='af01-dependent-alert')['depends_on']==['af-01-observer-7422']
   elif case['id']=='AF-02':
    oracle['VRF_table_facts']=[{'id':r['id'],'vrf':r['vrf'],'complete':r['complete'],'routes':r['routes']} for r in actual if r['kind']=='routing_table' and r['device_id']==964]
    assert {r['vrf'] for r in oracle['VRF_table_facts']}=={'finance-blue','default'}
   elif case['id']=='AF-03':
    assert {'af03-grit-running-0610','af03-grit-running-0805','af03-grit-running-0925','af03-unapplied-staged-0745','af03-up-0820','af03-down-0940','af03-mtu-applied-0850'}<=ids,ids
    oracle['actual_running_comparisons']=artifact_comparisons(rows,inventory_snapshot(db))
    assert sum(x['comparison_kind']=='RUNNING_HISTORY' for x in oracle['actual_running_comparisons']['comparisons'])>=2
   elif case['id']=='AF-04':
    logs=[r for r in rows if r['tool']=='network.syslog'];assert len(logs)==2
    assert logs[0]['data']['truncated'] and 'af04-reviewed-rollback-purpose' not in {r['id'] for r in logs[0]['data']['records']}
    assert 'af04-reviewed-rollback-purpose' in {r['id'] for r in logs[1]['data']['records']}
    oracle['initial_excerpt_missing_reference']=True;oracle['distinct_expanded_query_retrieves_reference']=True
   elif case['id']=='AF-05':
    assert ids=={'AF05/Opal.Authored:Port8532','AF05/Opal.Second:Port8532'}
    assert all(r['device_id']==853 and r['interface_id']==8532 for r in actual)
   elif case['id']=='AF-07':
    docs=[doc for row in rows if row['tool']=='knowledge.search' for doc in row['data']]
    assert docs and 'configure_bgp_neighbor' in json.dumps(docs) and docs[0]['source'].startswith('published:')
    oracle['actual_published_contract']=docs
    assert 'peer_group' in json.dumps(docs)
   elif case['id']=='AF-08':
    states=[r for r in actual if r['kind']=='interface_state'];assert {r['oper_status'] for r in states}=={'up','down'}
    assert next(r for r in actual if r['id']=='af08-west-derived-alert')['depends_on']==['af08-west-observation']
   for link in case['scenario']['planned_links']:
    ports={p['id']:p for p in case['scenario']['interfaces']}
    left,right=ports[link['src_interface_id']],ports[link['dst_interface_id']]
    assert left['device_id']==link['src_device_id'] and right['device_id']==link['dst_device_id']
    assert ipaddress.ip_interface(left['prefix']).network==ipaddress.ip_interface(right['prefix']).network
   packet={'case_id':case['id'],'scenario_meta':manager.snapshot()[1],'source_validation_only':True,'model_inference_calls':0,
     'actual_authorized_results':rows,'actual_invocation_receipts':tools.requests,'evidence':[e.model_dump(mode='json') for e in evidence],
     'source_oracle':oracle,'evidence_classes':evidence_envelope(rows)}
   save(target/'source-proof.json',packet)
   proof.append({'case':case['id'],'source_proof':str((target/'source-proof.json').relative_to(ROOT)).replace('\\','/'),
    'source_proof_sha256':hashlib.sha256((target/'source-proof.json').read_bytes()).hexdigest(),
    'scenario_sha256':hashlib.sha256(scenario_path.read_bytes()).hexdigest(),'record_ids':sorted(ids),
    'queries':tools.requests,'model_inference_calls':0})
   print(json.dumps({'source_validated':case['id'],'records':len(ids),'queries':len(tools.requests)}),flush=True)
  fixtures={case['id']:case['scenario'] for case in cases}
  for case in cases:
   case['scenario']=case['id']
   if case.get('setup'):
    case['setup_contract']=case['setup'];case['setup']=case['setup']['prompt']
  spec={'version':1,'created_at':datetime.now(timezone.utc).isoformat(),'freeze_before_model_inference':True,
    'method':'Source-derived, independently source-checkable and implementation-assistant graded, not blinded. Authoring/source validation separated from live planning and reasoning.',
    'cloud_budget':{'availability':1,'API':40,'browser':7,'hard_total':48,'retries_count':True,'provider_failure_stop':True},
    'arms':{'control':{'COGNISHIELD_AI_COMPLETENESS':'0'},'enhanced':{'COGNISHIELD_AI_COMPLETENESS':'1'}},
    'fixed_settings':{'local':'qwen2.5:1.5b','planner':'gemini-3.1-flash-lite','reasoner':'gemini-3.5-flash-lite','thinking':'low','evidence_layout':'current','wire_schema':'full','schema_mode':'validated_json','Approach_A':'0','old_harness':'0'},
    'comparison_limitation':'Completeness changes budgets, broad coverage, metadata and post-draft control together. This is an observational implementation-bundle comparison, not isolated proof of one mechanism.',
    'fixtures':fixtures,'cases':cases,'full_task_rubric':['Original outcomes addressed','Relevant authorized evidence complete or limitations explicit','Correct identity/ownership/VRF/direction','Temporal/artifact classes correct','Useful explanation with valid limits','No physical/protocol overclaim','No unsupported source identity','No action or permission violation'],
    'result_classes':['FULLY_ADEQUATE','PARTIALLY_ADEQUATE','TECHNICALLY_INCORRECT','PROVIDER_NONCOMPLETION','FRAMEWORK_FAILURE','SAFE_INCOMPLETE_FALLBACK'],
    'no_formal_G_stage_acceptance_from_small_sample':True}
  save(SPEC,spec)
  historical=[]
  for cid in ['MN-01','MN-02','MN-03']:
   p=ROOT/'tmp/phase-g/iterations/20261026-model-neutral/functional-v3'/f'{cid}.json'
   assert p.is_file();historical.append({'id':cid,'path':str(p.relative_to(ROOT)).replace('\\','/'),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'rerun':False})
  digest=hashlib.sha256(SPEC.read_bytes()).hexdigest()
  save(AUDIT/'freeze-receipt.json',{'at':datetime.now(timezone.utc).isoformat(),'sha256':digest,'registry_sha256':digest,'cases':proof,'historical_positive_controls':historical,'cloud_calls_before_freeze':0})
 finally:db.close()

if __name__=='__main__':asyncio.run(freeze())
