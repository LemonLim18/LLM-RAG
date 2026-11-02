"""Six new paired conditions. No inference, oracle never sent to models."""
import hashlib,json,sys
from pathlib import Path
from datetime import datetime,timezone
from copy import deepcopy
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'));sys.path.insert(0,str(Path(__file__).parent))
from freeze_intelligence_improvement import base,materialize,record,NOW

def build():
    fixtures={};cases=[]
    def add(n,s,prompt,claims,tools,*,oracle=None,setup=None,adaptive=False):
        s['id']='EH-'+str(n).zfill(2);s['title']='Harness matched source condition '+str(n)
        s=materialize(s);fixtures[s['id']]=s
        cases.append(dict(id=s['id'],surface='floating' if n%2 else 'studio',scenario=s['id'],prompt=prompt,
            expected_claims=claims,required_tools=tools,allowed_tools=tools,independent_oracle=oracle,setup=setup,adaptive_condition=adaptive,
            prohibited_claims=['Physical network certification or device execution','A model self-assessment verifies reasoning','Unavailable data proves absence','Captures establish an operational event window without event evidence'],
            full_adequacy='All requested outcomes useful/correct; exact ownership, source/time boundaries; no material unsupported claim. Provider failures remain in all-attempt denominator. Fallback is not model reasoning.'))
    s=base(1);s['interfaces'][4]['admin_status']='down';s['interfaces'][4]['oper_status']='down'
    add(1,s,'Use recorded state only. Assess Harbor to Meadow TCP/9443 in both directions, and explain how a disabled spare Transit interface can coexist with the recorded service result. Is this physical-network certification?',
        ['Both modeled directions delivered via Transit Ethernet1/2, not the disabled spare Ethernet1/3','Preference15 wins over25; spare-down does not negate tested path','Declared modeled scope, not physical certification'],['network.state'],oracle={'service-71':{'forward':'delivered','return':'delivered'}})
    s=base(2);s['network']['tables'][1]['routes'][1]['preference']=15
    tcp=s['network']['flows'][0];udp=deepcopy(tcp);udp.update(id='udp-overlay-138',protocol='udp',destination_port=4789);s['network']['flows'].append(udp)
    s['network']['policies']=[dict(id='selective-egress-138',interface_id=7022,direction='egress',rules=[dict(id='deny-overlay',protocol='udp',destination_port=4789,action='deny')],default_action='permit')]
    add(2,s,'Compare the recorded TCP/9443 service and UDP/4789 overlay between Harbor and Meadow, including return traffic. Locate the distinguishing policy and assess whether the branch results quantify experienced packet loss. Use state only; do not read telemetry.',
        ['TCP both equal-cost branches deliver; UDP Transit Ethernet1/2 denied, Ethernet1/3 delivered','UDP forwardpartial not totaloutage; bothreturnsdelivered','No measured traffic-distribution or packet-loss percentage'],['network.state'],oracle={'service-71':{'forward':'delivered','return':'delivered'},'udp-overlay-138':{'forward':'partial','return':'delivered'}})
    s=materialize(base(3));saved=next(r for r in s['records']['configuration'] if r['device_id']==702);active=next(r for r in s['records']['running_configuration'] if r['device_id']==702)
    saved['values']['config_text']='hostname Transit\ninterface Ethernet1/2\n vrf forwarding blue\n ip address 10.71.2.1/30\n'
    active['values']['config_text']='hostname Transit\ninterface Ethernet1/2\n vrf forwarding green\n ip address 10.71.2.1/30\n'
    s['availability']['syslog']=False
    add(3,s,'Compare Transit Ethernet1/2 in the saved artifact and current capture: identify the VRF and address in each. Then determine whether these artifacts establish when the active device changed VRF; consult syslog for that event if available. Do not read topology or state.',
        ['Savedblue/currentgreen, same10.71.2.1/30 on TransitEthernet1/2','Saved12:00/current14:00 artifact timestamps do not establish actualchangeinterval','Syslogunavailable, no inferred event/actor/protocolstate'],['network.configuration','network.syslog'])
    s=base(4)
    s['records']['topology']=[record('neighbor-observation-139',701,'observed_link',{'peer_device_id':702,'peer_interface_id':7021,'link_id':710,'status':'down','message':'Recorded observer reports link down; no packet test.'},7011)]
    add(4,s,'Compare the planned Harbor Ethernet0/1 link with the recorded observed link, including peer-port ownership and observation time. What does the design establish and what does the observation establish? Use planned and observed topology only; do not retrieve configuration or state.',
        ['Planned HarborEthernet0/1 to TransitEthernet1/1','Observedlink710down at recordedtime, not demonstratedpacketdelivery','Plan is intended relationship, not proofdeployed/up; no unsupported cablecause'],['network.topology'])
    s=base(5);s['interfaces'][3]['oper_status']='down';s=materialize(s)
    current=next(r for r in s['records']['running_configuration'] if r['device_id']==702)
    current['values']['change_event_ref']='inspection-ticket-144'
    s['records']['syslog']=[record('inspection-ticket-144',702,'syslog_event',{'severity':'notice','message':'Recorded intent: inspect the optical receive path on Ethernet1/2 after intermittent receive alarms; this ticket records no completed repair or cause.'},7022),
        record('unrelated-ticket-145',702,'syslog_event',{'severity':'notice','message':'Loopback documentation review, unrelated to optical receive path.'},None)]
    add(5,s,'Begin with Transit current configuration and recorded interface state. Explain the scope of the current no-shutdown setting versus the downstream operational failure. Also explain any recorded inspection intent identified by a reference in those records; distinguish that intent from a proven root cause or completed repair. Read only relevant authorized sources.',
        ['Transitno-shutdown does notprove downstream MeadowEthernet2/1 operationalhealth','Currentconfigreferences inspection-ticket-144; event records optical receive inspection intent, not completedrepair/certifiedcause','Retrieve referenced event if not initiallyread, or explicitlyreport unresolved intent; no unrelated ticket conflation'],['network.configuration','network.state','network.syslog'],adaptive=True)
    s=materialize(base(6));s['availability']['syslog']=False
    add(6,s,'Given the previous owned configuration result, recommend two discriminating read-only checks before deciding between a routing issue and an interface problem. Explain what each result would distinguish and the uncertainty left by unavailable logs. Do not read, collect or execute anything for this reply.',
        ['Exactly advice with0newreads; references prior configuration withouttreatingit asliveforwarding','Two meaningful discriminating checks, expected distinguishingresults','Unavailablelogs leaveeventcauseunknown; no inventedincident/currentmeasurement'],[],setup='Show Transit current configuration.')
    return {'version':1,'methodology':'Source-derived independently checkable expectations authored before inference; implementation-assistant graded, not blinded/external. Six distinct conditions, paired toggle with alternating order; independent planner nondeterminism is recorded.',
        'settings':{'models':['gemini-3.1-flash-lite','gemini-3.5-flash-lite'],'thinking':'low','request_seconds':120,'max_calls_per_request':3,'semantic_verifier':'off','approach_a':False},
        'rubric':['workflow','source_selection','evidence_completeness','raw_reasoning','final_task','unsupported_claims','source_scope','MN4','provider_completion'],
        'cases':cases,'fixtures':fixtures}

if __name__=='__main__':
    from local_providers.development import Scenario
    from development.network_model import assess_flow,Flow
    spec=build();proof=[]
    for case in spec['cases']:
        s=Scenario.model_validate(spec['fixtures'][case['scenario']]).model_dump(mode='json');spec['fixtures'][case['scenario']]=s
        actual={f['id']:assess_flow(s,Flow.model_validate(f)) for f in s['network']['flows']}
        for ref,expected in (case['independent_oracle'] or {}).items():
            assert all(actual[ref][direction]['status']==value for direction,value in expected.items()),(case['id'],actual)
        proof.append({'id':case['id'],'calculated_flows':actual,'expected':case['expected_claims']})
    a=ROOT/'tmp/phase-g/iterations/20261027-evidence-harness'
    path=ROOT/'docs/evaluations/phase_g_evidence_harness_v2.json'
    with path.open('x',encoding='utf-8') as f:json.dump(spec,f,indent=2)
    for name,value in [('freeze-v2.json',{'at':datetime.now(timezone.utc).isoformat(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'cases':6,'max_cloud_including_browser':54,'frozen_before_inference':True,'authoring_correction':'v1 materialized EH05 port state before changing operational value; corrected before any inference; v1 preserved unused.'}),('source-expectations-v2.json',proof)]:
        with (a/name).open('x',encoding='utf-8') as f:json.dump(value,f,indent=2)
    print('Frozen six paired conditions; source oracles checked; zero inference.')
