"""Author independently checkable inputs/expectations before any inference.

This is evaluation-only data preparation, never imported by the AI runtime.
"""
from copy import deepcopy
from pathlib import Path
import hashlib,json,sys
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
NOW='2026-10-26T10:00:00Z';OLD='2026-10-26T09:40:00Z'
NAMES={610:'Kite-Edge',620:'Linden-Core',630:'Quartz-Core',640:'Sable-Leaf'}

def record(identity,did,kind,values,iid=None,current=True,stamp=NOW):
    return dict(id=identity,device_id=did,interface_id=iid,timestamp=stamp,kind=kind,source='authored-development-observer',current=current,depends_on=[],values=values)

def base(number):
    devices=[dict(id=did,hostname=name,management_ip='192.0.2.'+str(i+61),vendor='cisco_xe',os_version='17.9',model='C9300',role='edge' if did in [610,640] else 'core',site='Synthetic-October') for i,(did,name) in enumerate(NAMES.items())]
    ports=[(6101,610,'GigabitEthernet0/1','10.60.1.1/30'),(6102,610,'GigabitEthernet0/2','10.60.2.1/30'),
        (6201,620,'GigabitEthernet1/1','10.60.1.2/30'),(6202,620,'GigabitEthernet1/2','10.60.3.1/30'),
        (6301,630,'GigabitEthernet2/1','10.60.2.2/30'),(6302,630,'GigabitEthernet2/2','10.60.4.1/30'),
        (6401,640,'GigabitEthernet3/1','10.60.3.2/30'),(6402,640,'GigabitEthernet3/2','10.60.4.2/30'),
        (6100,610,'Loopback0','198.19.60.1/32'),(6400,640,'Loopback0','198.19.60.4/32')]
    interfaces=[dict(id=i,device_id=d,name=n,prefix=p,admin_status='up',oper_status='up') for i,d,n,p in ports]
    links=[dict(id=i,src_device_id=a,src_interface_id=ap,dst_device_id=b,dst_interface_id=bp) for i,a,ap,b,bp in
        [(601,610,6101,620,6201),(602,620,6202,640,6401),(603,610,6102,630,6301),(604,630,6302,640,6402)]]
    def route(identity,prefix,port,address,pref=10):return dict(id=identity,prefix=prefix,origin='static',preference=pref,metric=0,next_hops=[dict(interface_id=port,address=address,resolved=True)])
    tables=[dict(device_id=610,complete=True,routes=[route('kite-primary','198.19.60.4/32',6101,'10.60.1.2'),route('kite-alternate','198.19.60.4/32',6102,'10.60.2.2',20)]),
        dict(device_id=620,complete=True,routes=[route('linden-forward','198.19.60.4/32',6202,'10.60.3.2'),route('linden-return','198.19.60.1/32',6201,'10.60.1.1')]),
        dict(device_id=630,complete=True,routes=[route('quartz-forward','198.19.60.4/32',6302,'10.60.4.2'),route('quartz-return','198.19.60.1/32',6301,'10.60.2.1')]),
        dict(device_id=640,complete=True,routes=[route('sable-primary','198.19.60.1/32',6401,'10.60.3.1'),route('sable-alternate','198.19.60.1/32',6402,'10.60.4.1',20)])]
    flow=dict(id='declared-service',source_device_id=610,destination_device_id=640,source_address='198.19.60.1',destination_address='198.19.60.4',protocol='tcp',source_port=43000,destination_port=443,require_return=True)
    s=dict(format_version=2,id='MMQ-'+str(number).zfill(2),revision=1,title='October network evidence '+str(number),logical_time=NOW,model_scope='ipv4_observation',inventory_complete=True,
        devices=devices,interfaces=interfaces,planned_links=links,records={k:[] for k in ['state','configuration','running_configuration','topology','telemetry','syslog','incidents']},
        availability={k:True for k in ['state','configuration','running_configuration','topology','telemetry','syslog','incidents']},
        network=dict(observed_at=NOW,policy_attachments_complete=True,tables=tables,policies=[],flows=[flow],ospf=[],bgp=[],metrics=[]))
    return s

def materialize(s):
    for d in s['devices']:
        ports=[i for i in s['interfaces'] if i['device_id']==d['id']]
        for domain,current in [('configuration',False),('running_configuration',True)]:
            text='hostname '+d['hostname']+'\n'
            for port in ports:
                text+='interface '+port['name']+'\n ip address '+port['prefix']+'\n '+('shutdown' if current and port['admin_status']=='down' else 'no shutdown')+'\n!\n'
            if any(r['device_id']==d['id'] for r in s['records'][domain]):continue
            s['records'][domain].append(record(('saved-' if not current else 'current-')+str(d['id']),d['id'],'configuration',{'config_text':text,'source_type':'development_current' if current else 'simulated_snapshot'},current=current,stamp=NOW if current else OLD))
    existing={r['id'] for r in s['records']['state']}
    s['records']['state'] += [record('port-'+str(p['id']),p['device_id'],'interface_state',{k:p[k] for k in ['prefix','admin_status','oper_status']},p['id']) for p in s['interfaces'] if 'port-'+str(p['id']) not in existing]
    return s

def build():
    fixtures={};cases=[]
    def add(n,s,prompt,expected,required,allowed=None,causal=True,oracle=None,adaptive=None,setup=None,forbidden=None):
        s=materialize(s);fixtures[s['id']]=s
        cases.append(dict(id='MMQ-'+str(n).zfill(2),surface='floating' if n%2 else 'studio',scenario=s['id'],prompt=prompt,
            expected_claims=expected,required_tools=required,allowed_tools=allowed or required,causal=causal,
            prohibited_claims=forbidden or ['Physical collection or device action occurred','Model interpretation is certified'],
            independent_oracle=oracle,adaptive_condition=adaptive,setup=setup,
            obligations=[part.strip() for part in prompt.split(';') if part.strip()]))
    state=['network.state'];causal_prompt='Assess the declared TCP/443 forward and return service from Kite-Edge to Sable-Leaf. Explain the mechanism, affected direction and exact stop location, or the limit of what can be established. Use recorded state only; do not test devices.'
    s=base(1);add(1,s,causal_prompt,['Both directions delivered via Linden-Core; LPM selects the /32 primary rather than merely proving route presence','Supported only within declared forwarding scope'],state,oracle={'forward':'delivered','return':'delivered'})
    s=base(2);s['interfaces'][3].update(admin_status='down',oper_status='down');add(2,s,'Investigate the Kite-Edge to Sable-Leaf service using recorded forwarding and Linden-Core current configuration. Identify whether a valid route is enough, and attribute the affected interfaces correctly.',
        ['Valid route does not deliver through Linden-Core GigabitEthernet1/2 administratively down; egress forward and ingress return failure','Current shutdown corroborates administrative block; not independent physical testing'],['network.state','network.configuration'],['network.state','network.configuration','network.topology'],oracle={'forward':'failed','return':'failed','forward_reason':'egress interface down'})
    s=base(3);s['interfaces'][6]['oper_status']='down';add(3,s,causal_prompt,['Forward stops at Sable-Leaf GigabitEthernet3/1 ingress, admin up/oper down','Return stops egress on same port; no proof of bad cable or administrative shutdown'],state,oracle={'forward':'failed','return':'failed','forward_reason':'ingress interface down'})
    s=base(4);s['network']['tables'][1]['routes']=s['network']['tables'][1]['routes'][1:];add(4,s,causal_prompt,['Complete Linden-Core table has no destination route; forward stops there before egress','Return still delivered; source route existence is insufficient'],state,oracle={'forward':'failed','return':'delivered','forward_reason':'no route'})
    s=base(5);s['network']['tables'][3]['routes']=[];add(5,s,causal_prompt,['Forward reaches Sable-Leaf; reverse starts there and fails no route to198.19.60.1','Do not reverse addresses or infer that forward success establishes bidirectional service'],state,oracle={'forward':'delivered','return':'failed'})
    s=base(6);s['network']['flows'][0]['destination_port']=8443;s['network']['policies']=[dict(id='inbound-service-filter',interface_id=6201,direction='ingress',rules=[dict(id='deny8443',destination='198.19.60.4/32',protocol='tcp',destination_port=8443,action='deny')],default_action='permit')]
    add(6,s,causal_prompt.replace('TCP/443','TCP/8443'),['Linden-Core GigabitEthernet1/1 ingress filter denies destination8443; not egress or Sable fault','Return delivered under reversed ports; no temporal ordering claim'],state,oracle={'forward':'failed','return':'delivered','forward_reason':'ingress policy'})
    s=base(7);s['network']['tables'][0]['routes'][0]['preference']=30;s['network']['flows'][0].update(protocol='udp',destination_port=5353);s['network']['policies']=[dict(id='quartz-out-filter',interface_id=6302,direction='egress',rules=[dict(id='deny5353',protocol='udp',destination_port=5353,action='deny')],default_action='permit')]
    add(7,s,causal_prompt.replace('TCP/443','UDP/5353'),['Lower-preference route selects Quartz-Core; egress GigabitEthernet2/2 denies UDP5353','Return delivered via Linden-Core; no assumed symmetric path'],state,oracle={'forward':'failed','return':'delivered','forward_reason':'egress policy'})
    s=base(8);s['network']['tables'][0]['routes'][1]['preference']=10;s['interfaces'][3].update(admin_status='down',oper_status='down');s['network']['tables'][3]['routes'][0]['preference']=30
    add(8,s,causal_prompt,['ECMP forward partial: Linden branch fails, Quartz branch delivers; not complete outage','Return delivered via Quartz; no measured loss percentage'],state,oracle={'forward':'partial','return':'delivered'})
    s=base(9);s['network']['tables'][0]['routes'][1]['preference']=10
    for i in [3,5]:s['interfaces'][i].update(admin_status='down',oper_status='down')
    add(9,s,causal_prompt,['Both equal-cost branches fail on their different egress interfaces; no surviving path','Do not use existence of the second route to claim failover success'],state,oracle={'forward':'failed','return':'failed'})
    s=base(10);s['network']['tables'][1]['routes'][0]['next_hops']=[dict(interface_id=6201,address='10.60.1.1',resolved=True)]
    add(10,s,causal_prompt,['Forward loops between Kite and Linden; return is delivered','A working return direction does not make the forward loop temporary or harmless'],state,oracle={'forward':'failed','return':'delivered','forward_reason':'forwarding loop'})
    s=base(11)
    for p in s['interfaces']:p['vrf']='amber'
    for t in s['network']['tables']:t['vrf']='amber'
    s['network']['flows'][0].update(vrf='amber',destination_vrf='amber');s['network']['tables'][1]['routes']=s['network']['tables'][1]['routes'][1:]
    s['network']['tables'].append(dict(device_id=620,vrf='default',complete=True,routes=[dict(id='default-only-destination',prefix='198.19.60.4/32',origin='static',preference=1,next_hops=[dict(interface_id=6202,address='10.60.3.2',resolved=True)])]))
    add(11,s,causal_prompt,['Linden amber table lacks destination route although default VRF has it','No implicit VRF leak; return delivered in amber'],state,oracle={'forward':'failed','return':'delivered','forward_reason':'no route'})
    s=base(12);s['network']['tables'][0]['complete']=False;add(12,s,causal_prompt,['Forward UNKNOWN from incomplete Kite table even with a visible /32','Do not equate unavailable more-specific routes with absent configuration or failed delivery'],state,oracle={'forward':'unknown','return':'delivered'})
    s=base(13);s['network']['tables'][0]['routes'][0]['next_hops'][0]['resolved']=None
    add(13,s,causal_prompt,['Forward UNKNOWN: next-hop resolution observation unavailable on Kite chosen egress','No proof neighbor resolution failed or cable down'],state,oracle={'forward':'unknown','return':'delivered','forward_reason':'resolution unavailable'})
    s=base(14);s['network']['policy_attachments_complete']=False;add(14,s,causal_prompt,['Forward and return UNKNOWN because attachment completeness is not established','Visible route/link facts cannot certify delivery or diagnose ACL denial'],state,oracle={'forward':'unknown','return':'unknown'})
    s=base(15);s['network']['tables'][1]['routes'][0].update(action='discard',next_hops=[])
    add(15,s,causal_prompt,['Linden selected discard route drops forward packet before any egress-interface test','Return delivered; valid route can intentionally discard'],state,oracle={'forward':'failed','return':'delivered','forward_reason':'discard route'})
    s=base(16);s['interfaces'][2]['prefix']='10.60.9.2/30';s['network']['tables'][0]['routes'][0]['next_hops'][0]['address']='10.60.9.2';s['network']['tables'][1]['routes'][1]['next_hops'][0]['address']='10.60.1.1'
    add(16,s,causal_prompt,['Forward and return fail because adjacent interface prefixes are not mutually on-link','Scope is declared modeled adjacency; not a live packet capture'],state,oracle={'forward':'failed','return':'failed','forward_reason':'not mutually on-link'})
    s=base(17);left=dict(device_id=610,interface_id=6101,router_id='198.19.60.11',area='0.0.0.0',process='23',hello_seconds=10,dead_seconds=40,network_type='point_to_point',authentication='profile-a',area_type='normal',mtu=1500,mtu_ignore=False,role='point_to_point');right={**left,'device_id':620,'interface_id':6201,'router_id':'198.19.60.22','area':'0.0.0.7','process':'91'}
    s['network']['ospf']=[dict(id='recorded-ospf',left=left,right=right,observed_state='Full')]
    add(17,s,'Investigate the recorded OSPF relationship between Kite-Edge and Linden-Core. Compare peer settings, explain the conflict with the observation and tell me whether you can certify current adjacency health. Use recorded state only.',
        ['Observed Full conflicts with modeled area0 versus area7 mismatch; disclose rather than silently pick one','Process23 versus91 are local identifiers, not the cause','Cannot certify current protocol health'],state,oracle={'protocol':'OSPF','required_issue':'area mismatch'},adaptive='Conflicting observations need qualified answer, not forced extra read')
    s=base(18);left=dict(device_id=610,address='198.19.60.1',local_as=65310,remote_as=65320,address_families=['ipv4_unicast'],hold_seconds=90,keepalive_seconds=30,update_source='198.19.60.1',authentication='profile-b');right={**left,'device_id':640,'address':'198.19.60.4','local_as':65320,'remote_as':65399,'update_source':'198.19.60.4'}
    s['network']['bgp']=[dict(id='recorded-bgp',left=left,right=right,observed_state='Active',transport_reachable=True,policy_observed=True,next_hop_valid=True)]
    add(18,s,'Investigate the recorded BGP session between Kite-Edge and Sable-Leaf. Explain the AS relationships and observed state, and distinguish transport reachability from an established BGP session. Use recorded state only.',
        ['Kite local65310 remote65320; Sable local65320 remote65399 mismatch against Kite65310','Active is not Established, transport reachable does not cure AS mismatch','No invented router ID or timer issue'],state,oracle={'protocol':'BGP','required_issue':'remote AS mismatch'})
    # Remaining task-completion conditions preserve separate independent outcomes.
    s=base(19);s['interfaces'][3].update(admin_status='down',oper_status='down');s['availability']['syslog']=False
    add(19,s,'Compare Linden-Core current configuration against its saved capture, quote the significant interface difference, and inspect syslog for its cause. Separate what is recorded from what remains unknown.',
        ['Current Gi1/2 shutdown, saved no shutdown, same prefix','No logs retrieved; neither no-event nor operator-intent conclusion'],['network.configuration','network.syslog'],causal=False)
    s=base(20);s['network']['flows']=[];s=materialize(s)
    s['records']['configuration'][0]['values']['config_text']='hostname Kite-Edge\n! OCTOBER_SAVED_64\nrouter ospf 23\n router-id 198.19.60.61\n network 10.60.1.0 0.0.0.3 area 0\nrouter bgp 65310\n neighbor 198.19.60.4 remote-as 65320\n'
    # add() materializes once; avoid duplicate captures in this authored variant.
    s['records']['configuration']=s['records']['configuration'][:1];s['records']['running_configuration']=[]
    add(20,s,'Explain Kite-Edge saved OSPF and BGP text, including the actual router ID, local AS, remote neighbor AS and the marker. Explain which router ID is not established by that capture. Do not generate anything.',
        ['OSPF process23 router-ID198.19.60.61; BGP local65310 neighbor198.19.60.4 remote65320','OCTOBER_SAVED_64; no explicit BGP router-ID; not active-state claim'],['network.configuration'],['network.configuration','knowledge.search'],causal=False)
    s=base(21);add(21,s,'Compare the published configure_ospf operation requirements with Kite-Edge saved configuration. Map only fields supported by that saved text and explain the compatibility and validation limits. Do not generate configuration.',
        ['Published operation requirements from active release; saved text has no router ospf stanza, so no process/router-ID mapping established','No template, vendor-version, full validation or operational compatibility certification'],['knowledge.search','network.configuration'],causal=False)
    s=base(22);s['network']['flows']=[];s['records']['state']=[record('past-port',610,'interface_state',{'admin_status':'up','oper_status':'up','prefix':'10.60.1.1/30'},6101,False,OLD)]
    add(22,s,'Compare Kite-Edge GigabitEthernet0/1 state at the older captured point with its current recorded state. Can you establish uninterrupted availability between them? Give the evidence limit without fetching logs.',
        ['Both point observations up, older09:40,current10:00','Cannot establish continuous uptime from endpoints','No syslog read'],['network.state'],['network.state'],causal=False,forbidden=['Continuous availability proved','Syslog retrieved'])
    s=base(23);s['records']['telemetry']=[record('cpu-window',620,'metric_sample',{'metric':'cpu_pct','value':87,'unit':'percent','sampling_seconds':30,'samples':[{'timestamp':'2026-10-26T09:59:00Z','value':31},{'timestamp':'2026-10-26T09:59:30Z','value':60},{'timestamp':NOW,'value':87}]})]
    add(23,s,'Read Linden-Core CPU telemetry and saved configuration. Explain the observed CPU trend and what the configuration can and cannot establish about its cause; do not infer packet loss from CPU alone.',
        ['CPU31→60→87percent,30ssampling over09:59–10:00','Saved configuration not a CPU cause or packet-loss measurement'],['network.telemetry','network.configuration'],causal=False)
    s=base(24);s['availability']['state']=False
    add(24,s,'Investigate whether the planned Kite-Edge to Sable-Leaf topology establishes usable connectivity. Read topology and available operational state, and separate intent from observations.',
        ['Planned diamond links do not establish delivery','State explicitly unavailable; operational diagnosis withheld'],['network.topology','network.state'],causal=False,adaptive='Unavailable observation; no redundant retry')
    s=base(25);s['interfaces'][3].update(admin_status='down',oper_status='down')
    add(25,s,'Based on that saved/current context, recommend two prioritized diagnostic evidence checks for Linden-Core and why each would help. Do not read, collect, test or change anything now.',
        ['Owned Linden target retained','Two useful unexecuted checks distinguish reason for change and current implications, not just repeat recorded configuration','No new authorized reader'],[],[],causal=False,setup='Show Linden-Core current configuration.',adaptive='Advisory prohibition; prior references only')
    s=base(26);s['availability']['state']=False
    add(26,s,'Explain whether Kite-Edge can reach Sable-Leaf using only the saved configuration. State what cannot be determined from that source and recommend the next observation, but do not read operational state or any other source.',
        ['Saved configuration cannot establish current delivery or outage','Useful proposed observation, no state read','Do not treat saved interfaces as operationally up'],['network.configuration'],['network.configuration'],causal=False,adaptive='Additional evidence prohibited, qualified direct answer')
    s=base(27);s['interfaces'][3].update(admin_status='down',oper_status='down')
    add(27,s,'Start with the Kite-Edge and Sable-Leaf stored configurations and planned topology to investigate the reported service problem. If their relationships reveal an unresolved intermediate condition, inspect the relevant recorded source and explain the supported mechanism. Do not test devices.',
        ['Source captures alone insufficient; discover Linden on selected path','Operational records/current config establish Linden Gi1/2 block if read; otherwise withhold diagnosis','No invented state from the planned link'],['network.configuration','network.topology'],['network.configuration','network.topology','network.state'],causal=False,adaptive='Intermediate device and distinct target query may be needed')
    s=base(28);s['interfaces'][3].update(admin_status='down',oper_status='down')
    add(28,s,'Read Linden-Core saved configuration first. Explain whether that capture establishes the present state of GigabitEthernet1/2; if not, consult its current recorded configuration before making the comparison. Do not read topology, syslog or telemetry.',
        ['Saved no shutdown/current shutdown comparison; historical versus current timestamps','Same configuration reader with distinct scope is legitimate if initially omitted','No source families outside configuration'],['network.configuration'],['network.configuration'],causal=False,adaptive='Same reader distinct historical/current query')
    s=base(29);s['network']['flows']=[];left=dict(device_id=610,interface_id=6101,router_id='198.19.60.11',area='0',process='23',hello_seconds=10,dead_seconds=40,network_type='broadcast',authentication='profile-a',area_type='normal',mtu=1500,mtu_ignore=False,role='DROther');right={**left,'device_id':620,'interface_id':6201,'router_id':'198.19.60.22','process':'91'};s['network']['ospf']=[dict(id='two-way-peers',left=left,right=right,observed_state='2-Way')]
    add(29,s,'Explain the recorded OSPF2-Way observation for Kite-Edge and Linden-Core. Determine whether both DROther roles make it necessarily a fault, and distinguish that from missing proof of physical reachability. Read recorded state only.',
        ['DROther pair on broadcast can remain2-Way normally; no compulsory Full','Compatible declared settings not physical/session-health certification'],['network.state'],['network.state'],causal=False)
    s=base(30);s['records']['syslog']=[record('old-maintenance',620,'syslog_event',{'message':'Approved interface description review completed; no state-change record was captured.','severity':'info'},current=False,stamp=OLD)]
    add(30,s,'Review Linden-Core saved configuration and its available historical syslog. Summarize the recorded maintenance message, compare what the two records establish, and identify one unresolved operational question. Do not infer that the absence of a shutdown event proves no shutdown occurred.',
        ['Exact maintenance content09:40; no observed state-change capture','Saved config plus historical log not current operating state','Unresolved question explicitly separated'],['network.configuration','network.syslog'],causal=False,adaptive='Sufficient historical evidence for scoped answer; no unnecessary collection')
    # Remove accidental duplicate materialization in explicit saved-text fixture.
    f=fixtures['MMQ-20'];seen=set();f['records']['configuration']=[r for r in f['records']['configuration'] if not (r['id'] in seen or seen.add(r['id']))]
    return {'version':1,'models':{'planner':'gemini-3.1-flash-lite','reasoner':'gemini-3.5-flash-lite','ordinary':'qwen2.5:1.5b'},'settings':{'semantic_verifier':'off','approach_a':False,'schema_mode':'validated_json','request_seconds':120,'maximum_cloud_calls':3},
        'methodology':'New task conditions with manually authored expected mechanisms, route/policy arithmetic and exact source contracts. Independently checkable; implementation-assistant graded, not blinded/external. Oracle fields never enter runtime.',
        'grading':{'G5_fully_adequate_required':26,'denominator':30,'G4_formal':'Original120routingand60historicalgate retained; this30cohortispartial evidence','G6_formal':'Originalindependentconformance+causal+UNKNOWNgatesretained',
            'dimensions':['intent','evidence_coverage','source_and_device_binding','facts','causal_mechanism','outcome_completion','unsupported_claims','uncertainty','readability','release_safety'],
            'full_adequacy':'Every requested outcome correct and sufficiently explained; no significant unsupported claim. Qualified/partial/fallback separate. No points solely for repeating typedstatus or HTTP200.'},'cases':cases,'fixtures':fixtures}

if __name__=='__main__':
    from local_providers.development import Scenario
    from development.network_model import assess_flow,Flow,protocol_findings,NetworkModel
    data=build();receipts=[]
    for case in data['cases']:
        s=Scenario.model_validate(data['fixtures'][case['scenario']]).model_dump(mode='json');data['fixtures'][case['scenario']]=s
        oracle=case['independent_oracle']
        if oracle and 'forward' in oracle:
            r=assess_flow(s,Flow.model_validate(s['network']['flows'][0]))
            assert r['forward']['status']==oracle['forward'],(case['id'],r['forward'])
            assert r['return']['status']==oracle['return'],(case['id'],r['return'])
            if oracle.get('forward_reason'):assert any(oracle['forward_reason'] in b['reason'] for b in r['forward']['branches'])
            receipts.append({'id':case['id'],'expected':oracle,'calculation':r})
    out=ROOT/'tmp/phase-g/iterations/20261026-multi-model-qualification';spec=ROOT/'docs/evaluations/phase_g_multi_model_g4_g6_v1.json'
    with spec.open('x',encoding='utf-8') as f:json.dump(data,f,indent=2,ensure_ascii=False)
    with (out/'freeze-receipt.json').open('x',encoding='utf-8') as f:json.dump({'at':datetime.now(timezone.utc).isoformat(),'sha256':hashlib.sha256(spec.read_bytes()).hexdigest(),'case_count':len(data['cases']),'causal_count':sum(c['causal'] for c in data['cases']),'frozen_before_inference':True},f,indent=2)
    with (out/'conformance-before.json').open('x',encoding='utf-8') as f:json.dump(receipts,f,indent=2)
    print('Frozen30distinctconditions;18causal;hand-authored expectations validated before inference')

