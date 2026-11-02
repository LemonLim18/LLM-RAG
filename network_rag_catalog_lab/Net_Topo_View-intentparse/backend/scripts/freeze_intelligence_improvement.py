"""New12-condition, source-derived holdout. Evaluation data, not runtime rules."""
from copy import deepcopy
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
NOW='2026-10-26T14:00:00Z';OLD='2026-10-26T12:00:00Z'
NAMES={701:'Harbor',702:'Transit',703:'Meadow'}
def record(ref,device,kind,values,interface=None,current=True):
    return dict(id=ref,device_id=device,interface_id=interface,kind=kind,values=values,timestamp=NOW if current else OLD,current=current,source='authored-synthetic-observer',depends_on=[])

def base(number):
    s=dict(format_version=2,id='MNI-'+str(number).zfill(2),revision=1,title='Independent October condition '+str(number),logical_time=NOW,
        model_scope='ipv4_observation',inventory_complete=True,
        devices=[dict(id=i,hostname=n,management_ip='192.0.2.'+str(i-630),vendor='cisco_xe',os_version='17.9',model='C9300',role='core' if i==702 else 'edge',site='Synthetic-Holdout') for i,n in NAMES.items()],
        interfaces=[dict(id=i,device_id=d,name=n,prefix=p,admin_status='up',oper_status='up') for i,d,n,p in [
            (7011,701,'Ethernet0/1','10.71.1.1/30'),(7021,702,'Ethernet1/1','10.71.1.2/30'),
            (7022,702,'Ethernet1/2','10.71.2.1/30'),(7031,703,'Ethernet2/1','10.71.2.2/30'),
            (7023,702,'Ethernet1/3','10.71.3.1/30'),(7032,703,'Ethernet2/2','10.71.3.2/30'),
            (7010,701,'Loopback0','198.18.71.1/32'),(7030,703,'Loopback0','198.18.71.3/32')]],
        planned_links=[dict(id=i,src_device_id=a,src_interface_id=ap,dst_device_id=b,dst_interface_id=bp) for i,a,ap,b,bp in [
            (710,701,7011,702,7021),(711,702,7022,703,7031),(712,702,7023,703,7032)]],
        records={d:[] for d in ['state','configuration','running_configuration','topology','telemetry','syslog','incidents']},
        availability={d:True for d in ['state','configuration','running_configuration','topology','telemetry','syslog','incidents']})
    def route(ref,prefix,port,address,preference=15):return dict(id=ref,prefix=prefix,origin='static',preference=preference,metric=2,next_hops=[dict(interface_id=port,address=address,resolved=True)])
    s['network']=dict(observed_at=NOW,policy_attachments_complete=True,policies=[],ospf=[],bgp=[],metrics=[],
        tables=[dict(device_id=701,complete=True,routes=[route('harbor-to-meadow','198.18.71.3/32',7011,'10.71.1.2')]),
            dict(device_id=702,complete=True,routes=[route('transit-a','198.18.71.3/32',7022,'10.71.2.2'),route('transit-b','198.18.71.3/32',7023,'10.71.3.2',25),route('transit-return','198.18.71.1/32',7021,'10.71.1.1')]),
            dict(device_id=703,complete=True,routes=[route('meadow-return','198.18.71.1/32',7031,'10.71.2.1')])],
        flows=[dict(id='service-71',source_device_id=701,destination_device_id=703,source_address='198.18.71.1',destination_address='198.18.71.3',protocol='tcp',source_port=45171,destination_port=9443,require_return=True)])
    return s

def materialize(s):
    for d in s['devices']:
        for domain,current in [('configuration',False),('running_configuration',True)]:
            if any(r['device_id']==d['id'] for r in s['records'][domain]):continue
            text='hostname '+d['hostname']+'\n'
            for p in s['interfaces']:
                if p['device_id']==d['id']:text+='interface '+p['name']+'\n ip address '+p['prefix']+'\n '+('shutdown' if current and p['admin_status']=='down' else 'no shutdown')+'\n!\n'
            s['records'][domain].append(record(('current-' if current else 'saved-')+str(d['id']),d['id'],domain,{'config_text':text},current=current))
    existing={r['id'] for r in s['records']['state']}
    s['records']['state'] += [record('port-'+str(p['id']),p['device_id'],'interface_state',{k:p[k] for k in ['prefix','admin_status','oper_status']},p['id']) for p in s['interfaces'] if 'port-'+str(p['id']) not in existing]
    return s

def build():
    fixtures={};cases=[]
    def add(n,s,prompt,claims,tools,*,allowed=None,oracle=None,causal=False,setup=None,adaptive=None):
        s=materialize(s);fixtures[s['id']]=s
        cases.append(dict(id='MNI-'+str(n).zfill(2),surface='floating' if n%2 else 'studio',scenario=s['id'],prompt=prompt,expected_claims=claims,
            required_tools=tools,allowed_tools=tools if allowed is None else allowed,independent_oracle=oracle,causal=causal,setup=setup,adaptive_condition=adaptive,
            prohibited_claims=['Physical device collection/action occurred','Self-assessment or citation certifies explanation','Unavailable observations prove no event or prove operational health'],
            full_adequacy='All clauses correct with source/identity/scope and a useful explanation; no significant unsupported claim; structural self-assessment alone earns no credit.'))
    s=base(1);add(1,s,'Assess the recorded TCP/9443 forward and return service from Harbor to Meadow. Explain Transit\'s selected path versus its other route, and the actual scope of the delivery result. Use recorded state only.',
        ['Both directions delivered via Transit Ethernet1/2 and Meadow Ethernet2/1','Transit15preference route selected over25, not ECMP','Only simulated declared service, no physical proof'],['network.state'],oracle={'forward':'delivered','return':'delivered'},causal=True)
    s=base(2);s['interfaces'][3]['oper_status']='down';add(2,s,'Investigate the Harbor–Meadow TCP/9443 failure using recorded state and current configuration only. Explain the failed forward and return interfaces, whether no shutdown proves delivery, and what cannot be diagnosed.',
        ['Forward stops at Meadow Ethernet2/1 ingress operdown/adminup; return egress on same interface','Current no shutdown not operational proof; no asserted cable/root physical cause'],['network.state','network.configuration'],oracle={'forward':'failed','return':'failed','forward_reason':'ingress interface down'},causal=True)
    s=base(3);s['network']['tables'][1]['routes'][1]['preference']=15;s['network']['tables'][2]['routes'][0]['next_hops']=[dict(interface_id=7032,address='10.71.3.1',resolved=True)];s['network']['flows'][0].update(protocol='udp',destination_port=4789)
    s['network']['policies']=[dict(id='port-service-policy',interface_id=7022,direction='egress',rules=[dict(id='deny-4789',protocol='udp',destination_port=4789,action='deny')],default_action='permit')]
    add(3,s,'Compare both equal-cost forward branches for Harbor to Meadow UDP/4789 and the return direction. Explain whether this establishes a total outage or a measured packet-loss percentage. Read state only; do not read configuration.',
        ['Transit Ethernet1/2 egress policy denies one equal-cost branch; Ethernet1/3 delivers','Forwardpartial,returndelivered via MeadowEthernet2/2; no inventedpercentage orprimarypriority'],['network.state'],oracle={'forward':'partial','return':'delivered'},causal=True)
    s=base(4)
    for p in s['interfaces']:p['vrf']='violet'
    for t in s['network']['tables']:t['vrf']='violet'
    s['network']['flows'][0].update(vrf='violet',destination_vrf='violet');default=deepcopy(s['network']['tables'][1]);default['vrf']='default'
    for route in default['routes']:route['id']='default-'+route['id']
    s['network']['tables'].append(default)
    s['network']['tables'][1]['routes']=s['network']['tables'][1]['routes'][2:]
    add(4,s,'Explain Harbor to Meadow forwarding in violet versus the recorded default-VRF route at Transit. Explain the reverse direction separately. Read state only and make no configuration changes.',
        ['Forwardfailsno-routeinTransitviolet while defaultVRFdestinationrouteexists; defaultentrycannotbeleakedimplicitly','Returnvioletdelivered; exactVRFnotgenericmissingallroutes'],['network.state'],oracle={'forward':'failed','return':'delivered','forward_reason':'no route'},causal=True)
    s=base(5);s['interfaces'][2].update(admin_status='down',oper_status='down');s['availability']['syslog']=False
    add(5,s,'Compare Transit current configuration with its saved capture. Explain the significant command change and inspect available syslog. Explain what the two sources cannot tell us about the reason or timing. Use only configuration and syslog.',
        ['Ethernet1/2savedno shutdown/currentshutdown exacttimestamps','Logs unavailable not noevents; configcapturesdonotproveactor/reason/exactchangetime'],['network.configuration','network.syslog'])
    s=base(6);s['network']['flows']=[]
    ospf=[dict(device_id=d,interface_id=p,router_id=rid,area='0',process=proc,hello_seconds=10,dead_seconds=40,network_type='broadcast',mtu=1500,role='DR' if d==701 else 'BDR') for d,p,rid,proc in [(701,7011,'198.18.71.11','12'),(702,7021,'198.18.71.22','92')]]
    s['network']['ospf']=[dict(id='ospf-peers',left=ospf[0],right=ospf[1],observed_state='Full')]
    s['network']['bgp']=[dict(id='bgp-peers',left=dict(device_id=701,address='10.71.1.1',local_as=64571,remote_as=64572),right=dict(device_id=702,address='10.71.1.2',local_as=64572,remote_as=64579),observed_state='Active',transport_reachable=True)]
    add(6,s,'Compare recorded OSPF and BGP peers between Harbor and Transit. Explain which local/remote values agree or disagree, and what the recorded states do and do not establish. Read state only.',
        ['OSPFprocess12vs92localonly,Fullrecord;notprocessmismatchcause','Transitremote64579doesnotmatchHarborlocal64571; Harborremote64572matchesTransitlocal','Active+transporttrue notphysicalprooforallprerequisitesverified'],['network.state'],causal=True)
    s=base(7);s['records']['configuration']=[record('harbor-routing-capture',701,'configuration',{'config_text':'hostname Harbor\n! HOLDOUT_ROUTING_71\nrouter ospf 71\n router-id 198.18.71.111\n network 10.71.1.0 0.0.0.3 area 0\nrouter bgp 64571\n neighbor 10.71.1.2 remote-as 64572\n'},current=False)]
    add(7,s,'Explain Harbor saved OSPF and BGP capture, including the router ID, local AS, neighbor, remote AS and marker. Explain which effective router ID is not established by that text. Use saved configuration only, with no operational queries.',
        ['OSPF71routerid198.18.71.111; BGPlocal64571 neighbor10.71.1.2 remote64572; markerHOLDOUT_ROUTING_71','NoexplicitBGProuterID/effectiveIDnotestablishedbytext; notactiveconfig'],['network.configuration'])
    s=base(8);s['network']=None;s['format_version']=1;s['model_scope']='direct_link';s['availability']['state']=False
    add(8,s,'Map the planned Harbor–Transit–Meadow interfaces. Explain whether the unavailable recorded state lets you confirm current TCP/9443 delivery or an outage. Use planned topology and state only.',
        ['Correctthreeplannedlinksandendpointownership','Stateunavailable;plannedlinksneitherdeliverynoroutageproof; no fabricatedphysicalfact'],['network.topology','network.state'])
    s=base(9);s['interfaces'][2].update(admin_status='down',oper_status='down');s=materialize(s)
    s['records']['configuration'][1]['values']['change_event_ref']='optic-work-71'
    s['records']['running_configuration'][1]['values']['change_event_ref']='optic-work-71'
    s['records']['syslog']=[record('optic-work-71',702,'syslog',{'message':'Approved maintenance: temporarily shut Ethernet1/2 for scheduled optics replacement. This note records intent, not a detected optics failure.'},7022)]
    add(9,s,'Investigate the reported Transit uplink problem, starting with its saved configuration and planned links. Explain the present recorded condition and its recorded intent if relevant existing records can establish them; follow a material source reference when necessary. Do not test or change devices.',
        ['Historicalno shutdowncannotaloneprovepresent; currentEthernet1/2shutdown','Referencedoptic-work-71authorizesmaintenanceintentonly; notrecordedopticfault','Ifreadcurrent/logsinterpretnewrecords; ifunavailableexplicitqualifiedgap'],['network.configuration','network.topology'],allowed=['network.configuration','network.topology','network.state','network.syslog'],adaptive='Material present-state/intent gap; model may prefetch or propose a bounded supplementary query, never forced.')
    s=base(10);s['interfaces'][2].update(admin_status='down',oper_status='down')
    add(10,s,'Using that owned context, recommend two next diagnostic checks and explain what different explanations each could distinguish. Do not read, collect, test or change anything now.',
        ['Two usefuldistinctfuturechecksforTransitEthernet1/2;notjustrepeatknownshutdown','Recordedintent/changehistory and conditionalpost-enableoper/physical observations appropriate, noactionsperformed','Previousreferencesnotfreshphysicalproof'],[],setup='Read Transit current configuration, including Ethernet1/2.',adaptive='No-read advisory with owned successful config context.')
    s=base(11);s['network']['tables'][2]['routes']=[];s['network']['tables'][2]['complete']=False
    add(11,s,'Compare the Harbor to Meadow forward result and the reverse evidence. Explain whether the empty incomplete reverse table proves there is no route, and recommend a useful next recorded check without collecting it. Use state only.',
        ['Forwarddelivered; reverseunknownbecauseincompletetable, notconfirmedmissingroute','ProposecompleteMeadowviolet/defaultcorrectdefaulttable evidence, noextraretrieval'],['network.state'],oracle={'forward':'delivered','return':'unknown'},causal=True)
    s=base(12);s['records']['telemetry']=[record('transit-cpu',702,'telemetry',{'metric':'cpu_pct','unit':'percent','value':89.0,'sampling_seconds':300,'samples':[{'timestamp':'2026-10-26T13:50:00Z','value':22},{'timestamp':'2026-10-26T13:55:00Z','value':57},{'timestamp':NOW,'value':89}]})]
    add(12,s,'Compare Transit recorded CPU samples with the Harbor–Meadow forwarding result. Explain whether these records establish congestion, packet loss or a cause of service failure, and identify what remains unmeasured. Read telemetry and state only.',
        ['CPU22to57to89percent; scopedforwardreturndelivered','CPUdoesnotaloneestablishcongestionloss/rootcause; no numericlossinvention','No measuredtraffic/loadcorrelationoractualphysicalprobe'],['network.telemetry','network.state'],oracle={'forward':'delivered','return':'delivered'},causal=True)
    return {'version':1,'methodology':'Twelve new multi-outcome/source conditions authored independently from old answer expectations; hand-calculated route/policy/VRF/protocol outcomes. Source-derived, implementation-assistant graded, not blind/external.',
        'grading':{'dimensions':['workflow','readers','parameters','evidence','raw_reasoning','complete_task','unsupported_claims','uncertainty','MN4'],'formal_qualification':False,'fully_adequate':'Every requested outcome correct and useful, no significant unsupported claim; model self-assessments and fallback do not prove reasoning.'},
        'settings':{'roles':['gemini-3.1-flash-lite','gemini-3.5-flash-lite'],'thinking':'low','semantic_verifier':'off','approach_a':False,'request_seconds':120,'max_cloud':3},'cases':cases,'fixtures':fixtures}

if __name__=='__main__':
    from local_providers.development import Scenario
    from development.network_model import assess_flow,Flow
    data=build();proof=[]
    for case in data['cases']:
        s=Scenario.model_validate(data['fixtures'][case['scenario']]).model_dump(mode='json');data['fixtures'][case['scenario']]=s
        if case['independent_oracle']:
            r=assess_flow(s,Flow.model_validate(s['network']['flows'][0]));o=case['independent_oracle']
            assert r['forward']['status']==o['forward'] and r['return']['status']==o['return'],(case['id'],r)
            if o.get('forward_reason'):assert any(o['forward_reason'] in b['reason'] for b in r['forward']['branches'])
            proof.append({'id':case['id'],'expected':o,'actual_calculation':r})
        assert all(row['kind']=='running_configuration' for row in s['records']['running_configuration'])
    spec=ROOT/'docs/evaluations/phase_g_intelligence_improvement_holdout_v1.json';audit=ROOT/'tmp/phase-g/iterations/20261026-intelligence-improvement'
    with spec.open('x',encoding='utf-8') as f:json.dump(data,f,indent=2,ensure_ascii=False)
    for name,value in [('freeze-receipt.json',{'at':datetime.now(timezone.utc).isoformat(),'sha256':hashlib.sha256(spec.read_bytes()).hexdigest(),'case_count':12,'frozen_before_inference':True,'max_cloud_including_browser':44}),('source-expectations.json',proof)]:
        with (audit/name).open('x',encoding='utf-8') as f:json.dump(value,f,indent=2,ensure_ascii=False)
    print('Frozen12newconditions; source oracles checked; no inference performed.')
