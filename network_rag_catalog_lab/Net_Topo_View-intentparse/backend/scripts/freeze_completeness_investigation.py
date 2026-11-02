"""Freeze eight new paired tasks plus three original MN references, no inference."""
import json,sys,hashlib
from pathlib import Path
from datetime import datetime,timezone,timedelta
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'));sys.path.insert(0,str(Path(__file__).parent))
from freeze_intelligence_improvement import base,materialize,record,NOW

def build():
    cases=[];fixtures={}
    def add(n,s,prompt,expected,tools,oracle=None,setup=None):
        s['id']='CF-'+str(n).zfill(2);s['title']='Completeness-first independent condition '+str(n);s=materialize(s);fixtures[s['id']]=s
        cases.append({'id':s['id'],'scenario':s['id'],'surface':'floating' if n%2 else 'studio','prompt':prompt,'expected_claims':expected,
            'required_tools':tools,'allowed_tools':['inventory.read','network.topology','network.state','network.configuration','network.syslog','network.telemetry','network.incidents'],
            'independent_oracle':oracle,'setup':setup,'prohibited_claims':['Physical collection or execution occurred','Unread or unavailable logs establish no event','Source citations certify all causal prose','Wrong device/interface ownership','Capture times alone establish active change timing']})
    s=base(1);s['interfaces'][2]['oper_status']='down';s=materialize(s)
    current=next(r for r in s['records']['running_configuration'] if r['device_id']==702);current['values']['change_event_ref']='optical-order-212'
    s['records']['syslog']=[record('routine-'+str(i),702,'routine_notification',{'message':'Routine recorder heartbeat '+str(i)}) for i in range(45)]
    s['records']['syslog'].append(record('optical-order-212',702,'syslog_event',{'message':'Recorded purpose: inspect the receive optical path on Transit Ethernet1/2 after intermittent alarms. This is inspection intent, not a completed repair or confirmed physical cause.'},7022))
    add(1,s,'Investigate why Harbor cannot communicate with Meadow. Check all relevant available sources, explain the affected hop and the no-shutdown setting, compare available configuration artifacts, and establish any recorded inspection purpose referenced by the configuration. Distinguish observations, modeled failure, and unproven physical cause.',
        ['TransitEthernet1/2adminup/operdown blocksforward egress andreturningress indeclaredmodel','Currentno-shutdown means administrativeenablement not operationalguarantee','Saved/currentartifacts do not alone prove activationhistory','optical-order-212actualevent states opticalreceiveinspection intent not completedrepair','Broadfamilycoverage plus visible limits; relevant unread reference should triggeractualsupplementaryread ifinitialquerymissesit'],
        ['inventory.read','network.topology','network.state','network.configuration','network.syslog','network.telemetry','network.incidents'],{'forward':'failed','return':'failed'})
    s=base(2);s['interfaces'][2]['oper_status']='down'
    add(2,s,'Show Transit Ethernet1/2 administrative state, operational state and prefix. Explain why administrative enablement does not establish delivery. Use recorded state only; do not read configuration or logs.',
        ['TransitEthernet1/2:adminup/operdown,10.71.2.1/30','No invented physicalcause or deliveryguarantee','Onlystateexecuted'],['network.state'])
    s=base(3);s['network']['policies']=[dict(id='traffic-egress-213',interface_id=7022,direction='egress',rules=[dict(id='deny-app',protocol='tcp',destination_port=9443,action='deny')],default_action='permit')]
    add(3,s,'Using state only, explain why the installed routes do not deliver Harbor to Meadow TCP/9443. Locate the failing device, interface and direction, compare the return result, and tell me whether these records establish BGP session health. Do not read configuration.',
        ['Forwardegressdeny TransitEthernet1/2 traffic-egress-213/deny-app','Returndelivered; forwardroutepresence notdeliveryproof','NoBGPsessionrecord; noEstablishedclaim'],['network.state'],{'forward':'failed','return':'delivered'})
    s=base(4);s['interfaces'][0]['name']='Ethernet1/2';s['interfaces'][0]['vrf']='guest';s['interfaces'][2]['vrf']='red'
    add(4,s,'Use inventory and planned topology only. Compare Harbor Ethernet1/2 and Transit Ethernet1/2: give each owner, prefix and recorded VRF. Identify the documented peer of Harbor Ethernet1/2 and explain what the plan cannot establish operationally.',
        ['HarborEthernet1/2 10.71.1.1/30guest; TransitEthernet1/2 10.71.2.1/30red','HarborportpeersTransitEthernet1/1 notsame-namedEthernet1/2','Plannedinventorydoesnotproveoperationaldelivery'],['inventory.read','network.topology'])
    s=base(5);s['interfaces'][2]['admin_status']='down';s['interfaces'][2]['oper_status']='down';s=materialize(s)
    s['records']['configuration']=[r for r in s['records']['configuration'] if r['device_id']!=702]
    a=record('run-before-215',702,'running_configuration',{'config_text':'hostname Transit\ninterface Ethernet1/2\n description old\n no shutdown\n'},current=False);a['timestamp']='2026-10-26T10:00:00Z'
    saved=record('unapplied-file-215',702,'configuration',{'config_text':'hostname Transit\ninterface Ethernet1/2\n description staged-only\n shutdown\n'},current=False);saved['timestamp']='2026-10-26T11:00:00Z'
    b=record('run-prechange-215',702,'running_configuration',{'config_text':'hostname Transit\ninterface Ethernet1/2\n description uplink\n no shutdown\n'},current=False);b['timestamp']='2026-10-26T12:00:00Z'
    s['records']['configuration'] +=[a,saved,b];current=next(r for r in s['records']['running_configuration'] if r['device_id']==702)
    current['values']['config_text']='hostname Transit\ninterface Ethernet1/2\n description uplink\n shutdown\n';current['values']['change_event_ref']='applied-change-215'
    e=record('applied-change-215',702,'configuration_change',{'message':'Recorded applied interface shutdown on Transit Ethernet1/2','applied':True,'verification_status':'verified'},7022);e['timestamp']='2026-10-26T13:00:00Z';e['depends_on']=['run-prechange-215',current['id']];s['records']['syslog']=[e]
    add(5,s,'Investigate Transit Ethernet1/2 shutdown history and its modeled forwarding effect. Compare the actual running captures and the staged saved file; identify the important command difference with interface context. Distinguish the running-observation interval from the verified applied event time and do not treat the staged file as earlier running state.',
        ['12:00runningno-shutdown to14:00runningshutdown','Verified appliedevent13:00 onTransitsameport','11:00savedfileisnotactive-stateproof','Textdiffretainsinterfacecontext; no cross-devicepair','Declaredforwardegress/returningressblocked, nophysicalcollection'],['network.configuration','network.state','network.syslog'],{'forward':'failed','return':'failed'})
    s=base(6);s['records']['topology']=[record('neighbor-report-216',701,'observed_link',{'peer_device_id':702,'peer_interface_id':7021,'link_id':710,'status':'down'},7011)]
    s['records']['telemetry']=[record('loss-sample-216',701,'interface_counters',{'lost_packets':3,'sent_packets':120,'unit':'packets','window_start':'2026-10-26T13:55:00Z','window_end':NOW},7011)]
    add(6,s,'Compare the documented Harbor Ethernet0/1 adjacency with its recorded link report and interface state. Then calculate loss from the returned packet counters and explain why the modeled TCP delivery verdict does not negate that observation. Read only topology, state and telemetry.',
        ['PlanHarborEthernet0/1 toTransitEthernet1/1','Observedlinkreportdown versusinterfaceup discrepancy disclosed','Counter3/120=2.5percentwithinrecordedwindow','Modeleddeliverydifferentassumptions/scope thanpacketmeasurements; no globalhealthclaim'],['network.topology','network.state','network.telemetry'],{'forward':'delivered','return':'delivered'})
    s=base(7);s['availability']['syslog']=False
    add(7,s,'Read Transit current configuration, routing/state records and available syslog only. Explain the interface settings and whether route presence or no-shutdown establishes OSPF adjacency. Explain what the unavailable event source leaves unresolved without inventing events or claiming none occurred.',
        ['Currentno-shutdown andprefixes scopedtoTransit','NoOSPFneighborobservation, routesnotadjacencyproof','Unavailablelogsnotproofnoevents; no physicalrootcauseinvented'],['network.configuration','network.state','network.syslog'])
    s=base(8)
    add(8,s,'Without retrieving anything new, recommend two read-only checks that would distinguish an interface problem from a routing problem for Transit. Use the prior owned configuration appropriately, explain what each check can actually establish, and state any remaining uncertainty. Do not execute or change anything.',
        ['0newreaders;2usefulnoncircularcheckswithaccuratesourcecapabilities','Priorconfigdoesnotproveoperationalstate; tabledoesnotproveprotocolsessionhealth','No inventedcurrentobservation/action'],[],setup='Show Transit current configuration.')
    original=json.loads((ROOT/'docs/evaluations/phase_g_model_neutral_functional_v1.json').read_text(encoding='utf-8'))
    fixtures[original['fixture']['id']]=original['fixture']
    for c in original['cases'][:3]:cases.append({**c,'reference':True,'scenario':original['fixture']['id'],'expected_claims':c['expected'],'allowed_tools':list(READERS),'reference_note':'Exact original MN integration prompt/fixture, not new generalization evidence.'})
    return {'version':1,'methodology':'Eight independently authored paired task conditions covering15requested categories; hand-checkable source expectations verified before inference. Implementation-assistant graded, not blinded/external. Three exact original references are separately labelled and not unique new cases.',
        'rubric':['source_coverage','requested_outcomes','identity','temporal_scope','technical_reasoning','raw_vs_final','typed_compatibility','automatic_refinement','provider_failure','latency'],
        'grading':'Extra authorized relevant reads are efficiency only, not automatic task failures. Adequate requires every requested outcome correct/appropriately limited; fallback and schema passes do not establish model reasoning.',
        'budget':{'max_actual_cloud_including_browser':72,'enhanced_request_seconds':360,'enhanced_role_calls':5,'baseline_seconds':120,'baseline_role_calls':3},'cases':cases,'fixtures':fixtures}

READERS=['inventory.read','network.topology','network.state','network.configuration','network.syslog','network.telemetry','network.incidents','knowledge.search']
if __name__=='__main__':
    from local_providers.development import Scenario
    from development.network_model import assess_flow,Flow
    spec=build();proof=[]
    for c in spec['cases']:
        s=Scenario.model_validate(spec['fixtures'][c['scenario']]).model_dump(mode='json');spec['fixtures'][c['scenario']]=s
        if c.get('independent_oracle'):
            f=Flow.model_validate(s['network']['flows'][0]);actual=assess_flow(s,f)
            assert all(actual[d]['status']==v for d,v in c['independent_oracle'].items()),(c['id'],actual)
            proof.append({'id':c['id'],'expected':c['independent_oracle'],'actual':actual})
    path=ROOT/'docs/evaluations/phase_g_completeness_first_v1.json';a=ROOT/'tmp/phase-g/iterations/20261027-completeness-first'
    with path.open('x',encoding='utf-8') as f:json.dump(spec,f,indent=2)
    for name,value in [('freeze-receipt.json',{'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'at':datetime.now(timezone.utc).isoformat(),'new_conditions':8,'reference_cases':3,'max_actual_dispatches':72,'frozen_before_inference':True}),('source-expectations.json',proof)]:
        with (a/name).open('x',encoding='utf-8') as f:json.dump(value,f,indent=2)
    print('Frozen8pairedconditions+3exactMNreferences; oracle checks pass; zero inference.')
