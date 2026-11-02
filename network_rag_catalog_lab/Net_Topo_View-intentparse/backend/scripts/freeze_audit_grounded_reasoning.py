"""Freeze eight independent source-derived conditions and actual reasoner inputs.
No model inference. Reuse registered readers and one disposable application DB.
"""
import asyncio,copy,hashlib,ipaddress,json,os,sys
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2]
AUDIT=ROOT/'tmp/phase-g/iterations/20261101-audit-grounded-repair'
SPEC=ROOT/'docs/evaluations/phase_g_audit_grounded_reasoning_v1.json'
sys.path.insert(0,str(ROOT/'backend'))
NOW='2026-10-31T22:00:00Z'
DOMAINS=['state','configuration','running_configuration','topology','telemetry','syslog','incidents']

def record(ref,device,kind,values,interface=None,*,stamp=NOW,current=True,source='synthetic-authored-recorder',depends=()):
 return dict(id=ref,device_id=device,interface_id=interface,timestamp=stamp,kind=kind,source=source,current=current,depends_on=list(depends),values=values)

def base(n,vrf='default'):
 names=[(221,'Peregrine','cisco_xe'),(284,'Basalt','juniper'),(306,'Coral','huawei'),(419,'Nacre','cisco_xe')]
 s=dict(format_version=2,id='AGR-'+str(n).zfill(2),revision=1,title='Independent audit-grounded condition '+str(n),
  logical_time=NOW,model_scope='ipv4_observation',inventory_complete=True,
  devices=[dict(id=i,hostname=name,management_ip='192.0.2.'+str(k+121),vendor=vendor,os_version='17.9' if vendor=='cisco_xe' else '22.4' if vendor=='juniper' else '8.180',
    model='synthetic-recorded-platform',role='edge' if k in [0,3] else 'core',site='Isolated-audit-grounded') for k,(i,name,vendor) in enumerate(names)],
  interfaces=[],planned_links=[],records={k:[] for k in DOMAINS},availability={k:True for k in DOMAINS})
 ports=[(2211,221,'GigabitEthernet3/0/1','10.202.14.1/30'),(2841,284,'ge-0/0/5.0','10.202.14.2/30'),
  (2842,284,'ge-0/0/6.0','10.202.28.1/30'),(3061,306,'GigabitEthernet1/0/8','10.202.28.2/30'),
  (3062,306,'GigabitEthernet1/0/9','10.202.42.1/30'),(4191,419,'GigabitEthernet4/0/2','10.202.42.2/30'),
  (2210,221,'Loopback30','198.18.202.1/32'),(4190,419,'Loopback40','198.18.202.4/32')]
 s['interfaces']=[dict(id=i,device_id=d,name=name,prefix=prefix,admin_status='up',oper_status='up',vrf=vrf) for i,d,name,prefix in ports]
 s['planned_links']=[dict(id=i,src_device_id=a,src_interface_id=ai,dst_device_id=b,dst_interface_id=bi) for i,a,ai,b,bi in [
  (881,221,2211,284,2841),(882,284,2842,306,3061),(883,306,3062,419,4191)]]
 def route(ref,prefix,interface,address):return dict(id=ref,prefix=prefix,origin='static',preference=8,metric=3,next_hops=[dict(interface_id=interface,address=address,resolved=True)])
 s['network']=dict(observed_at=NOW,policy_attachments_complete=True,policies=[],ospf=[],bgp=[],metrics=[],
  tables=[dict(device_id=221,vrf=vrf,complete=True,routes=[route('p-to-n','198.18.202.4/32',2211,'10.202.14.2')]),
   dict(device_id=284,vrf=vrf,complete=True,routes=[route('b-to-n','198.18.202.4/32',2842,'10.202.28.2'),route('b-to-p','198.18.202.1/32',2841,'10.202.14.1')]),
   dict(device_id=306,vrf=vrf,complete=True,routes=[route('c-to-n','198.18.202.4/32',3062,'10.202.42.2'),route('c-to-p','198.18.202.1/32',3061,'10.202.28.1')]),
   dict(device_id=419,vrf=vrf,complete=True,routes=[route('n-to-p','198.18.202.1/32',4191,'10.202.42.1')])],
  flows=[dict(id='audit-service',source_device_id=221,destination_device_id=419,source_address='198.18.202.1',destination_address='198.18.202.4',
    vrf=vrf,destination_vrf=vrf,protocol='tcp',source_port=47202,destination_port=179,require_return=True)])
 return s

def materialize(s):
 for device in s['devices']:
  text='hostname '+device['hostname']+'\n'
  for p in s['interfaces']:
   if p['device_id']==device['id']:
    text+='interface '+p['name']+'\n ip address '+p['prefix']+'\n '+('shutdown' if p['admin_status']=='down' else 'no shutdown')+'\n!\n'
  for key,current in [('running_configuration',True),('configuration',False)]:
   if not any(r['device_id']==device['id'] for r in s['records'][key]):
    s['records'][key].append(record(('active-' if current else 'snapshot-')+str(device['id']),device['id'],key,{'config_text':text},current=current,stamp=s['logical_time']))
 for p in s['interfaces']:
  if not any(r['interface_id']==p['id'] and r['kind']=='interface_state' for r in s['records']['state']):
   s['records']['state'].append(record('observer-'+str(p['id']),p['device_id'],'interface_state',
    {k:p[k] for k in ['prefix','admin_status','oper_status','vrf']},p['id'],stamp=s['logical_time']))
 return s

def build():
 cases=[]
 def add(s,prompt,reads,claims,prohibited,*,expected_flow=None,advisory=False):
  cases.append(dict(id=s['id'],surface='floating' if len(cases)%2==0 else 'studio',prompt=prompt,scenario=materialize(s),
   authorized_queries=reads,advisory=advisory,owned_goal='Review Basalt saved neighbor configuration.' if advisory else None,
   requested_outcomes=claims,expected=claims,prohibited=prohibited,expected_flow=expected_flow,
   grading='Source-derived, independently checkable and implementation-assistant graded; not blinded. Every requested outcome must be correct or explicitly limited. No self-assessment/fallback credit.'))
 def q(domain,**params):return {'domain':domain,'parameters':params}
 s=base(1);s['interfaces'][0].update(admin_status='down',oper_status='down')
 add(s,'For the declared Peregrine-to-Nacre TCP/179 service, explain why a route can be installed while forwarding fails. Identify the stopping interfaces in each direction, compare the active command with recorded state, and distinguish the modeled cause from an unknown physical mechanism.',
  [q('state'),q('configuration',source_scope='current')],
  ['Peregrine221 GigabitEthernet3/0/1 port2211 is administratively and operationally down; active CLI shutdown agrees.',
   'Forward and return fail within the declared model at that same owned port, in the correct direction; route presence is not sufficient.',
   'This establishes a modeled administrative block, not an optic/cable failure or physical measurement.'],
  ['Wrong interface owner','Route existence proves delivery','Specific physical fault is established'],expected_flow={'forward':'failed','return':'failed'})
 s=base(2)
 s['network']['policies']=[dict(id='basalt-inbound-179',interface_id=2841,direction='ingress',vrf='default',
   rules=[dict(id='deny-declared-service',source='198.18.202.1/32',destination='198.18.202.4/32',protocol='tcp',destination_port=179,action='deny')],default_action='permit')]
 add(s,'Using the recorded state only, assess the exact TCP/179 flow from Peregrine to Nacre and its return. Explain the first failed hop and interface ownership, why installed routes do not guarantee delivery, and whether this establishes a BGP session outcome.',
  [q('state',source_scope='current')],
  ['Forward stops at Basalt284 ingress ge-0/0/5.0 port2841 under policy basalt-inbound-179; not at Coral or Nacre.',
   'Return is delivered; the ordered stateless directional policy need not deny return.',
   'Routes exist but modeled ingress policy prevents forward delivery; a TCP/179 flow assessment does not establish BGP FSM/session health.'],
  ['Wrong failed hop or direction','Forward failure proves return failure','Established/Idle BGP session invented'],expected_flow={'forward':'failed','return':'delivered'})
 s=base(3);s.pop('network');s['format_version']=1;s['logical_time']='2026-10-31T06:50:00Z'
 s['records']={k:[] for k in DOMAINS};s['records']['running_configuration']=[
  record('basalt-run-0210',284,'running_configuration',{'config_text':'set interfaces ge-0/0/6 unit 0 description BASE\nset interfaces ge-0/0/6 mtu 1600\n'},stamp='2026-10-31T02:10:00Z',current=False),
  record('basalt-run-0440',284,'running_configuration',{'config_text':'set interfaces ge-0/0/6 unit 0 description SITE-B\nset interfaces ge-0/0/6 mtu 1600\n'},stamp='2026-10-31T04:40:00Z',current=False),
  record('basalt-run-0530',284,'running_configuration',{'config_text':'set interfaces ge-0/0/6 unit 0 description SITE-B\nset interfaces ge-0/0/6 mtu 2000\n'},stamp='2026-10-31T05:30:00Z')]
 s['records']['configuration']=[record('basalt-unapplied-0305',284,'planned_configuration',{'config_text':'set interfaces ge-0/0/6 mtu 9000\nset interfaces ge-0/0/6 disable\n','artifact_role':'unapplied_staged','applied':False},stamp='2026-10-31T03:05:00Z',current=False)]
 s['records']['state']=[
  record('basalt-oper-0455',284,'interface_state',{'admin_status':'up','oper_status':'up','vrf':'default'},2842,stamp='2026-10-31T04:55:00Z',current=False),
  record('basalt-oper-0650',284,'interface_state',{'admin_status':'up','oper_status':'down','vrf':'default'},2842,stamp='2026-10-31T06:50:00Z')]
 s['records']['syslog']=[record('basalt-applied-0510',284,'configuration_change',
  {'applied':True,'verification_status':'verified','field':'mtu','before':1600,'after':2000,'message':'Recorded apply: MTU1600 to2000; no operational transition was measured in this event.'},2842,stamp='2026-10-31T05:10:00Z')]
 add(s,'Compare Basalt ge-0/0/6.0 running observations with its separate staged artifact. Give the actual running changes, the strongest up-to-down observation window, and what the applied MTU event establishes. Can you establish the running description at 03:05 or the physical cause of the transition?',
  [q('configuration',device_refs=['284'],source_scope='both'),q('state',device_refs=['284'],interface_refs=['2842'],source_scope='both',record_kinds=['interface_state']),q('syslog',device_refs=['284'],source_scope='both')],
  ['Running BASE1600 at02:10 -> SITE-B1600 at04:40 -> SITE-B2000 at05:30.',
   '03:05 staged MTU9000/disable is unapplied and not a sample of running state; running description at03:05 is not established.',
   'Operational up04:55/down06:50 brackets a transition; applied MTU event05:10 records an apply, not exact oper transition/physical causality.'],
  ['Staged disable became active','Running SITE-B is established at03:05','Applied MTU proves outage cause or exact transition'])
 s=base(4,'ops-green');s.pop('network');s['format_version']=1
 s['records']['configuration']=[record('basalt-bgp-review',284,'configuration',{'config_text':'set routing-instances ops-green protocols bgp group upstream type external\nset routing-instances ops-green protocols bgp group upstream peer-as 65342\nset routing-instances ops-green protocols bgp group upstream neighbor 10.202.28.2\nset routing-options autonomous-system 65341\n'},current=False)]
 add(s,'Without fetching or running anything, recommend two distinct passive evidence checks for Basalt in ops-green that would distinguish a forwarding-policy problem from a peer-session problem. Use the prior configuration context, say what each possible result would and would not establish, and do not assume the saved neighbor is currently established.',
  [q('configuration',device_refs=['284'],source_scope='historical')],
  ['Two contextual proposed passive checks, not new reads or execution; at least one forwarding/policy and one peer operational observation.',
   'Correct Basalt/ops-green context; saved neighbor10.202.28.2/peerAS65342 is configured, no current Established claim.',
   'Explain discriminating value and limits without claiming counters, high load or missing routes uniquely prove physical/session cause.'],
  ['Additional actual read or action','Circular advice only rereads same saved text','Present peer state invented','A counter pattern uniquely confirms physical cause'],advisory=True)
 s=base(5);s.pop('network');s['format_version']=1;s['availability']['syslog']=False;s['availability']['incidents']=False
 s['records']['configuration']=[record('peregrine-saved-bgp',221,'configuration',{'config_text':'hostname Peregrine\nrouter bgp 65221\n bgp router-id 192.0.2.221\n neighbor 10.202.14.2 remote-as 65284\n'},current=False)]
 add(s,'Use Peregrine saved configuration, available syslogs and incident records. Explain the exact BGP router ID and local/remote AS relationship, then state whether you can establish why a peer reset occurred. Keep the successful configuration findings even if the other sources are unavailable.',
  [q('configuration',device_refs=['221'],source_scope='historical'),q('syslog',device_refs=['221']),q('incidents',device_refs=['221'])],
  ['Saved Peregrine router ID192.0.2.221, localAS65221, neighbor10.202.14.2 remoteAS65284; AS numbers are not router IDs.',
   'Syslog and incident sources unavailable; no retrieved reset events, no proof no reset occurred.',
   'Explain configured eBGP relationship without asserting active configuration, live session or reset cause; retain available config outcome.'],
  ['Unavailable logs treated as retrieved','No reset because no logs','Saved CLI is current active/session state','Invented reset reason'])
 s=base(6);s.pop('network');s['format_version']=1
 s['records']['configuration']=[record('nacre-saved-ospf',419,'configuration',{'config_text':'hostname Nacre\nrouter ospf 42\n router-id 198.51.100.42\n network 10.202.42.0 0.0.0.3 area 0\n'},current=False)]
 add(s,'Compare the published configure_ospf operation requirements with Nacre saved OSPF text. Map the actual supported parameters where the saved text supplies them, identify any assumptions or missing requirements, and explain what remains unvalidated. Do not generate configuration or infer neighbor health.',
  [q('knowledge',query='Published configure_ospf operation schema requirements',limit=1),q('configuration',device_refs=['419'],source_scope='historical')],
  ['Use actual immutable configure_ospf contract fields and saved process42/routerID198.51.100.42/network10.202.42.0 wildcard0.0.0.3 area0 without inventing required fields.',
   'Map recorded values, disclose any contract/profile/platform dependencies the evidence has not validated.',
   'Saved configuration does not establish operational adjacency or V9 validation/rendering completion; no generation requested.'],
  ['Compatibility or full validation certified','Wrong local OSPF process/area interpretation','Generation or live adjacency invented'])
 s=base(7,'research-blue')
 add(s,'Assess the declared research-blue TCP service between Peregrine and Nacre in both directions from recorded state. Explain its multi-hop device and interface relationships, and give the limits of a successful modeled result rather than diagnosing an outage.',
  [q('state',source_scope='current')],
  ['Forward and return delivered under the declared research-blue model; ordered path Peregrine221 Basalt284 Coral306 Nacre419, reversed on return.',
   'Correct interfaces along each hop; no default-VRF substitution or fabricated policy/adjacency.',
   'Only declared modeled TCP flow is established, not physical connectivity, every service or routing-protocol state.'],
  ['Invented outage','Wrong VRF/port/owner','Model success proves physical/all-service health'],expected_flow={'forward':'delivered','return':'delivered'})
 s=base(8);s.pop('network');s['format_version']=1
 s['records']['state']=[
  record('coral-collector-east',306,'interface_state',{'prefix':'10.202.42.1/30','admin_status':'up','oper_status':'up','vrf':'default'},3062,source='synthetic-east-collector'),
  record('coral-collector-west',306,'interface_state',{'prefix':'10.202.42.1/30','admin_status':'up','oper_status':'down','vrf':'default'},3062,source='synthetic-west-collector')]
 add(s,'Use recorded state only for Coral GigabitEthernet1/0/9. Reconcile the two collector observations, explain whether the available evidence establishes an outage, and recommend a useful next read without performing it.',
  [q('state',device_refs=['306'],interface_refs=['3062'],source_scope='current',record_kinds=['interface_state'])],
  ['Same ownerCoral306/interface3062/prefix10.202.42.1/30/VRFdefault/time22:00, distinct eastup/westdown observations.',
   'Disclose unresolved conflict; cannot select one as current truth or establish outage/physical cause.',
   'Propose a discriminating timestamp/source/interface-state validation read without executing it in this reasoning-only test.'],
  ['Select a collector without authority','Conclude healthy/outage/physical cause','Invent differing timestamps or wrong owner'])
 return cases

class PacketCaptured(Exception):pass
class Capture:
 def __init__(self):self.hybrid=SimpleNamespace(role_calls=0,remote_calls=0,max_remote_calls=3);self.value=None
 async def generate(self,messages,**kwargs):
  self.value={'messages':copy.deepcopy(messages),'schema':copy.deepcopy(kwargs['structured']),'purpose':kwargs['purpose']}
  raise PacketCaptured()

def save(path,value):
 with path.open('x',encoding='utf-8') as f:json.dump(value,f,indent=2,ensure_ascii=False);f.write('\n')

async def freeze():
 os.environ.update(COGNISHIELD_MODE='local_lab',COGNISHIELD_DEV_SIMULATION='1',COGNISHIELD_AI_COMPLETENESS='1',
  COGNISHIELD_AI_OUTCOMES='0',COGNISHIELD_AI_EVIDENCE_HARNESS='0',COGNISHIELD_DB_PATH=str(AUDIT/'evaluation-app.db'),
  COGNISHIELD_DEV_STATE=str(AUDIT/'initial-state.json'))
 import lab_config
 from db.manager import DatabaseManager
 from llm.gateway_store import ConversationStore,ensure_schema
 from llm.gateway_services import registry_for,inventory_snapshot
 from llm.gateway_network import network_context,READ_TOOLS
 from llm.tools import ToolAuthorization
 from llm.orchestration.adapters import AuthorizedTools
 from llm.orchestration.role_reasoning import decide
 from llm.orchestration.investigation_support import network_map,artifact_comparisons,evidence_envelope,COMPATIBILITY,walk,source_coverage
 from development.network_model import Flow,assess_flow
 from local_providers.development import Scenario,ScenarioManager
 db=DatabaseManager(str(AUDIT/'evaluation-app.db'));db.initialize();ensure_schema(db)
 assert Path(db._db_path).resolve()==(AUDIT/'evaluation-app.db').resolve()
 store=ConversationStore(db);cases=build();proof=[]
 try:
  for case in cases:
   definition=Scenario.model_validate(case['scenario']).model_dump(mode='json');case['scenario']=definition
   out=AUDIT/'frozen-v1'/case['id'];out.mkdir(parents=True)
   manager=ScenarioManager(out/'scenario.json');db._development_scenario=manager
   manager.change('import',manager.snapshot()[1]['source_revision'],definition)
   cid=store.create('audit-engineer',case['surface'])['id'];inventory=inventory_snapshot(db)
   registry=registry_for(db);auth=ToolAuthorization('audit-engineer','engineer',case['surface'],cid,frozenset(READ_TOOLS))
   tools=AuthorizedTools(registry,store,auth,max_calls=8)
   rows=[];evidence=[]
   for item in case['authorized_queries']:
    domain=item['domain'];args={'device_refs':[str(d['id']) for d in definition['devices']],**item['parameters']}
    found,sources,_=await network_context(db,tools,auth,case['prompt'],domains_override=[domain],
      device_refs_override=args['device_refs'],validated_parameters={domain:args})
    rows.extend(found);evidence.extend(sources)
   oracle={}
   if case['expected_flow']:
    result=assess_flow(definition,Flow.model_validate(definition['network']['flows'][0]))
    assert {k:result[k]['status'] for k in ['forward','return']}==case['expected_flow'],(case['id'],result)
    actual=next(r['assessment'] for row in rows for _,r in walk(row['data']) if r['kind']=='forwarding_assessment')
    assert actual==result
    oracle={'expected':case['expected_flow'],'actual_assessment':result,
      'failure_locations':[v['failure_location'] for direction in ['forward','return'] for v in result[direction].get('branches',[]) if v.get('failure_location')]}
   if case['id']=='AGR-03':
    ids={r['id'] for row in rows for _,r in walk(row.get('data'))}
    assert {'basalt-run-0210','basalt-unapplied-0305','basalt-run-0440','basalt-run-0530','basalt-oper-0455','basalt-oper-0650','basalt-applied-0510'}<=ids,ids
   if case['id']=='AGR-05':
    assert all(row['data']['source_available'] is False for row in rows if row['tool'] in {'network.syslog','network.incidents'})
   if case['id']=='AGR-06':
    published=[doc for row in rows if row['tool']=='knowledge.search' for doc in row['data']]
    assert published and published[0]['source'].startswith('published:')
    assert 'configure_ospf' in json.dumps(published)
    oracle['actual_published_contract']=published
   if case['id']=='AGR-08':
    values=[r for row in rows for _,r in walk(row.get('data'))]
    assert {r['oper_status'] for r in values}=={'up','down'} and len(values)==2
   for link in definition['planned_links']:
    ports={p['id']:p for p in definition['interfaces']}
    a,b=ports[link['src_interface_id']],ports[link['dst_interface_id']]
    assert a['device_id']==link['src_device_id'] and b['device_id']==link['dst_device_id']
    assert ipaddress.ip_interface(a['prefix']).network==ipaddress.ip_interface(b['prefix']).network
   domains=list(dict.fromkeys(q['domain'] for q in case['authorized_queries']))
   planning={'proposed':{'intent':'explain','desired_response':'explanation' if case['advisory'] else 'investigation','goal':case['prompt'],
      'information_needs':[{'domain':d,'question':'Retrieve the explicitly authorized source records.','necessity':'required'} for d in domains]},
      'authorized_reader_schemas':{name:registry.capability(name).input_model.model_json_schema() for name in sorted(tools.tools)},
      'investigation':{'breadth':'restricted','source_coverage_plan':[{'domain':d,'reader':'knowledge.search' if d=='knowledge' else 'network.'+d,'status':'CAPABILITY_READY_SOURCE_UNQUERIED'} for d in domains]}}
   advisory=None;history=[]
   if case['advisory']:
    history=[case['owned_goal']]
    advisory={'devices':['Basalt'],'prior_user_goal':case['owned_goal'],'authorized_readers':sorted(tools.tools),
      'prior_authorized_records':rows,'prior_source_evidence':[e.model_dump(mode='json') for e in evidence],
      'prior_read_receipts':tools.requests,'rule':'Previously owned configuration only; no new read or action is permitted.'}
    use_rows=[];use_evidence=[]
   else:use_rows=rows;use_evidence=evidence
   retrieval={'executed_queries':[] if case['advisory'] else tools.requests,'remaining_tool_calls':0,'remaining_seconds':120,
     'remaining_role_calls':1,'supplementary_permitted':False,
     'investigation_context':{'network':network_map(inventory,use_rows,[] if case['advisory'] else [str(d['id']) for d in definition['devices']],False),
      'artifact_history':artifact_comparisons(use_rows,inventory),'evidence_envelopes':evidence_envelope(use_rows),
      'claim_source_compatibility':{k:sorted(v) for k,v in COMPATIBILITY.items()},'previous_review':None,'previous_draft':None}}
   capture=Capture()
   try:await decide(capture,case['prompt'],use_rows,use_evidence,history,planning,advisory=advisory,retrieval=retrieval)
   except PacketCaptured:pass
   assert capture.value
   packet={'case_id':case['id'],'surface':case['surface'],'conversation':cid,'scenario_path':str((out/'scenario.json').relative_to(ROOT)).replace('\\','/'),
    'scenario_meta':manager.snapshot()[1],'request':case['prompt'],'messages':capture.value['messages'],'schema':capture.value['schema'],
    'inputs':{'results':use_rows,'evidence':[e.model_dump(mode='json') for e in use_evidence],'history':history,'planning':planning,'advisory':advisory,'retrieval':retrieval},
    'actual_authorized_rows':rows,'actual_authorized_receipts':tools.requests,'independent_source_oracle':oracle,
    'reasoning_only':True,'planner_inference_calls':0,'new_reads_during_advisory':0}
   save(out/'frozen-packet.json',packet)
   proof.append({'id':case['id'],'packet_sha256':hashlib.sha256((out/'frozen-packet.json').read_bytes()).hexdigest(),
     'scenario_file_sha256':hashlib.sha256((out/'scenario.json').read_bytes()).hexdigest(),
     'model_input_characters':sum(len(m['content']) for m in packet['messages']),'source_ids':[e.id for e in evidence],
     'record_ids':[r['id'] for row in rows for _,r in walk(row.get('data'))],
     'source_oracle':oracle,'coverage':source_coverage(planning['investigation']['source_coverage_plan'],rows,tools.requests)})
   print(json.dumps({'frozen':case['id'],'input_characters':proof[-1]['model_input_characters'],'readers':[r['tool'] for r in rows]}),flush=True)
  spec={'version':1,'created_at':datetime.now(timezone.utc).isoformat(),'method':'Eight new source-grounded conditions; independently checkable, implementation-assistant graded, not blinded.',
   'cloud_budget':{'P1':16,'P2':16,'P3':4,'integration':8,'diagnostic':4,'total':48},
   'cases':cases,'full_adequacy':'Every requested outcome correct/appropriately limited; no significant unsupported interpretation; fallback, self-assessment and valid JSON are not reasoning credit.'}
  save(SPEC,spec);save(AUDIT/'freeze-receipt.json',{'at':datetime.now(timezone.utc).isoformat(),'registry_sha256':hashlib.sha256(SPEC.read_bytes()).hexdigest(),
   'cases':proof,'cloud_dispatches_before_freeze':0,'original_historical_expectations_unchanged':True})
 finally:db.close()

if __name__=='__main__':asyncio.run(freeze())

