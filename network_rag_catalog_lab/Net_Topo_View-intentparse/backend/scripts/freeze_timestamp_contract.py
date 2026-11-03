"""OFFLINE ONLY: six fresh synthetic conditions and one description delta.

No models, registered readers, DB, quota writes or consent approvals. Existing
pure network calculations establish modeled fixtures; no app dataset is changed.
"""
import argparse,asyncio,copy,hashlib,importlib.util,json,os,sys
from contextlib import ExitStack
from dataclasses import asdict
from datetime import datetime,timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
AUDIT=ROOT/'tmp/phase-g/iterations/20261102T104614Z-timestamp-contract-experiment'
SPEC=ROOT/'docs/evaluations/phase_g_gemini35_timestamp_contract_v1.json'
sys.path.insert(0,str(ROOT/'backend'))
ENV={'COGNISHIELD_AI_SOURCECLAIM_TIMESTAMP_EXPERIMENT':'off','COGNISHIELD_AI_REASONING_CONTRACT':'off',
    'COGNISHIELD_AI_REASONER_INTERPRETATION_EXPERIMENT':'off','COGNISHIELD_AI_OUTCOMES':'0',
    'COGNISHIELD_AI_COMPLETENESS':'1','COGNISHIELD_AI_INVESTIGATION_SECONDS':'120',
    'COGNISHIELD_AI_EVIDENCE_HARNESS':'0','COGNISHIELD_AI_EVIDENCE_LAYOUT':'current',
    'COGNISHIELD_AI_PROVIDER_WIRE_SCHEMA':'full','COGNISHIELD_AI_EXPERIMENT_SEMANTIC_VERIFIER':'off',
    'COGNISHIELD_AI_HYBRID_INTERPRET':'0','COGNISHIELD_LOCAL_OLLAMA_MODEL':'qwen2.5:1.5b'}

def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(text):return hashlib.sha256(text.encode()).hexdigest()
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2)
def relative(p):return p.relative_to(ROOT).as_posix()
def before_module(name):
    p=AUDIT/'source-before'/('backend/llm/'+name+'.py')
    spec=importlib.util.spec_from_file_location('_timestamp_before_'+name.replace('/','_'),p)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module);return module

class Captured(BaseException):pass
async def capture(module,inputs):
    captured={}
    class Model:
        hybrid=SimpleNamespace(role_calls=0,remote_calls=0,max_remote_calls=3)
        async def generate(self,messages,structured,**kw):
            assert not captured;captured.update(messages=messages,schema=structured,purpose=kw);raise Captured()
    from llm.gateway_models import Evidence
    args=copy.deepcopy(inputs);args['evidence']=[Evidence.model_validate(e) for e in args['evidence']]
    try:await module.decide(Model(),**args)
    except Captured:pass
    assert captured;return captured

async def serialized_wire(messages,schema):
    """Capture the actual adapter's body before a socket send; fake key/quota."""
    import httpx
    from llm.gemini_provider import interpret_rest
    captured={}
    async def intercept(client,request,*a,**kw):
        assert request.url.host=='generativelanguage.googleapis.com'
        captured.update(body=json.loads(request.content));raise Captured()
    with patch.dict(os.environ,{'GEMINI_API_KEY':'synthetic-offline-serialization-only'}),\
        patch('llm.gemini_provider._quota_update',return_value=('offline-no-reservation',0)),\
        patch.object(httpx.AsyncClient,'send',intercept):
        try:await interpret_rest(messages,schema,timeout=120,model='gemini-3.5-flash-lite',thinking='low',output_tokens=8192,schema_mode='validated_json')
        except Captured:pass
    assert captured;return captured['body']

def device(i,name):return {'id':i,'hostname':name,'management_ip':f'192.0.2.{i%150+40}',
    'vendor':'cisco_xe','os_version':'17.12','site':'timestamp-contract-synthetic'}
def scenario(cid,devices,interfaces=(),network=None):
    return {'format_version':2 if network else 1,'id':cid,'title':'Timestamp contract synthetic '+cid,
        'revision':1,'logical_time':'2026-10-28T23:59:00Z','model_scope':'ipv4_observation' if network else 'bounded_routed_path',
        'inventory_complete':True,'devices':devices,'interfaces':list(interfaces),'planned_links':[],
        'records':{d:[] for d in ['state','configuration','running_configuration','syslog','incidents','topology','telemetry']},
        'availability':{d:True for d in ['state','configuration','running_configuration','syslog','incidents','topology','telemetry']},
        **({'network':network} if network else {})}
def row(ref,kind,device_id,time,values,port=None,source='authored-synthetic-audit'):
    return {'id':ref,'kind':kind,'device_id':device_id,'interface_id':port,'timestamp':time,'source':source,'current':True,'values':values}
def claim(ref,device_id,time,field,value,category='configuration_change_time',port=None):
    return {'record_refs':[ref],'device_id':str(device_id),'interface_id':str(port) if port else None,
        'timestamp':time,'field':field,'value':value,'category':category}
def network_fixture(cid):
    ds=[device(5301,'LumenProbe'),device(5302,'TransitHub'),device(5303,'ArchiveSink')]
    values=[(53010,5301,'Loopback7','198.18.88.1/32'),(53011,5301,'Ethernet2/1','10.88.1.1/30'),
        (53021,5302,'Ethernet2/1','10.88.1.2/30'),(53022,5302,'Ethernet2/9','10.88.2.1/30'),
        (53031,5303,'Ethernet3/1','10.88.2.2/30'),(53030,5303,'Loopback9','198.18.88.3/32')]
    ports=[{'id':i,'device_id':d,'name':n,'prefix':p,'vrf':'monitor','admin_status':'up','oper_status':'up'} for i,d,n,p in values]
    def route(ref,prefix,port,ip,resolved=True):return {'id':ref,'prefix':prefix,'origin':'static','preference':12,
        'next_hops':[{'interface_id':port,'address':ip,'resolved':resolved}]}
    network={'observed_at':'2026-10-28T18:00:00Z','policy_attachments_complete':True,'policies':[],'flows':[],
        'tables':[{'device_id':5301,'vrf':'monitor','complete':True,'routes':[route('lp-to-archive','198.18.88.3/32',53011,'10.88.1.2')]},
            {'device_id':5302,'vrf':'monitor','complete':True,'routes':[route('hub-to-archive','198.18.88.3/32',53022,'10.88.2.2'),route('hub-to-probe','198.18.88.1/32',53021,'10.88.1.1')]},
            {'device_id':5303,'vrf':'monitor','complete':True,'routes':[route('archive-to-probe','198.18.88.1/32',53031,'10.88.2.1')]}]}
    s=scenario(cid,ds,ports,network)
    s['planned_links']=[{'id':881,'src_device_id':5301,'src_interface_id':53011,'dst_device_id':5302,'dst_interface_id':53021},
        {'id':882,'src_device_id':5302,'src_interface_id':53022,'dst_device_id':5303,'dst_interface_id':53031}]
    return s

def cases():
    """Oracles follow explicit sources/calculations, not candidate wording."""
    from development.network_model import assess_flow,Flow
    items=[]
    def add(cid,s,question,domains,expected,prohibited,bindings,controls,distinction,surface):
        items.append({'id':cid,'scenario':s,'question':question,'domains':domains,'surface':surface,
            'oracle':{'required_components':expected,'prohibited_conclusions':prohibited,'claim_bindings':bindings,
                'positive_and_negative_controls':controls,'distinct_from_historical':distinction}})
    s=scenario('H-01',[device(5101,'NacreDist')],[{'id':51017,'device_id':5101,'name':'Ethernet2/7','vrf':'default','admin_status':'up','oper_status':'up'}])
    event=row('h01-mtu-ack','configuration_change',5101,'2026-10-28T08:17:00Z',
        {'message':'Verified MTU restoration to 1500 on Ethernet2/7','effective_at':'2026-10-28T08:04:00Z','applied':True,'verification_status':'verified'},51017)
    snapshot=row('h01-followup','running_configuration',5101,'2026-10-28T08:22:00Z',{'config_text':'interface Ethernet2/7\n mtu 1500','observed_at':'2026-10-28T08:22:00Z'},51017)
    s['records']['syslog']=[event];s['records']['running_configuration']=[snapshot]
    add('H-01',s,'Explain the verified MTU restoration on NacreDist Ethernet2/7. Distinguish its effective time, the audit record time and the follow-up capture; calculate the recording and capture delays. Does this establish when real payload-loss recovery occurred? Use only the supplied configuration and event records.',
        ['syslog','running_configuration'],['Verified effective MTU1500at08:04; event record08:17; follow-up configuration08:22.',
            'Recording delay13minutes; capture18minutes after effective event.','Positive applied event established; no measured payload recovery time.'],
        ['Effective time replaced by08:17or08:22','Application denied despite verification','Physical packet-loss recovery inferred'],
        [claim(event['id'],5101,event['timestamp'],'effective_at',event['values']['effective_at'],port=51017)],
        ['Retain verified application.','Reject event time used as record selector; reject wrong effective scalar.'],
        'Delayed MTU audit plus separate confirming capture and two elapsed-time outcomes; not logging-buffer interpolation.', 'studio')
    s=scenario('H-02',[device(5111,'RavineWAN'),device(5112,'PlateauWAN')])
    first=row('h02-ravine','incident',5111,'2026-10-28T21:19:00Z',{'summary':'Recorded control-channel interruption','first_observed':'2026-10-28T21:04:00Z','status':'recorded'})
    second=row('h02-plateau','incident',5112,'2026-10-28T21:10:00Z',{'summary':'Recorded control-channel interruption','first_observed':'2026-10-28T21:08:00Z','status':'recorded'})
    s['records']['incidents']=[second,first]
    add('H-02',s,'Which site first observed the control-channel interruption, RavineWAN or PlateauWAN? Compare their first-observed and record-writing times and reporting delays. Does the order the records were written establish the order of the interruptions or prove one caused the other? Use these incident records only.',
        ['incidents'],['Ravine first observed21:04; Plateau21:08, four minutes later.','Ravine recorded21:19(delay15minutes), Plateau21:10(delay2minutes).',
            'Reporting order reverses observation order; no cross-site causal or live protocol-state proof.'],
        ['Plateau first because record earlier','Record-writing time called onset','Cross-site cause or measured protocol health invented'],
        [claim(first['id'],5111,first['timestamp'],'first_observed',first['values']['first_observed'],'incident_occurred'),
            claim(second['id'],5112,second['timestamp'],'first_observed',second['values']['first_observed'],'incident_occurred')],
        ['Correct temporal prose may be retained while incident-time operands remain mechanically unverified.','Do not treat insufficient checkability as false event evidence.'],
        'Two incidents have reversed reporting order; compares source delays, no CRC/cooling coincidence.', 'floating')
    s=scenario('H-03',[device(5201,'ValeLeaf'),device(5202,'BrookLeaf')])
    va=row('h03-vale','configuration_change',5201,'2026-10-28T00:03:00Z',{'message':'Verified interface MTU set to 9000','effective_at':'2026-10-27T23:50:00Z','applied':True,'verification_status':'verified'})
    br=row('h03-brook','configuration_change',5202,'2026-10-27T23:56:00Z',{'message':'Verified interface MTU set to 9000','effective_at':'2026-10-27T23:50:00Z','applied':True,'verification_status':'verified'})
    s['records']['syslog']=[br,va]
    add('H-03',s,'Compare the acknowledgement delays for the verified 9000-byte MTU changes on ValeLeaf and BrookLeaf. Both events report the same effective time. Bind each record and delay to its device, including the midnight date boundary. Does the later acknowledgement prove later activation? Use the supplied event records only.',
        ['syslog'],['Both effective2026-10-27T23:50Z.','Vale acknowledgement2026-10-28T00:03Z:13minutes; Brook2026-10-27T23:56Z:6minutes.',
            'Equal values/effective times do not make the owner/record timestamps interchangeable; later acknowledgement not later activation.'],
        ['Swap owners or record timestamps','Treat midnight as negative or23hour delay','Infer later activation from acknowledgement order'],
        [claim(va['id'],5201,va['timestamp'],'effective_at',va['values']['effective_at']),claim(br['id'],5202,br['timestamp'],'effective_at',br['values']['effective_at'])],
        ['Correct equal-valued claims require distinct owners and record bindings.','Wrong record/effective timestamp must not become authoritative.'],
        'Cross-device equal operands and a date rollover compete for source binding; original scenarios had one-device chronology.', 'studio')
    s=scenario('H-04',[device(5211,'MarshAccess')],[{'id':52118,'device_id':5211,'name':'Ethernet4/8','admin_status':'unknown','oper_status':'unknown','vrf':'default'}])
    s['records']['running_configuration']=[
        row('h04-observer-a','running_configuration',5211,'2026-10-28T06:40:00Z',{'config_text':'interface Ethernet4/8\n no shutdown'},52118,'synthetic-collector-a'),
        row('h04-observer-b','running_configuration',5211,'2026-10-28T06:40:00Z',{'config_text':'interface Ethernet4/8\n shutdown'},52118,'synthetic-collector-b'),
        row('h04-later','running_configuration',5211,'2026-10-28T07:10:00Z',{'config_text':'interface Ethernet4/8\n shutdown'},52118,'synthetic-collector-a')]
    add('H-04',s,'Reconcile the two collectors running-configuration captures for MarshAccess Ethernet4/8 and the later capture. What is established at each observation, can you determine the configuration at 06:55 or an exact shutdown time, and do these commands establish measured link health? Use only these captures; do not resolve a conflict by assuming one collector is correct.',
        ['running_configuration'],['Same06:40observation time contains conflicting no shutdown/shutdown commands; retain both sources.',
            '07:10capture records shutdown;06:55and exact transition remain unknown.','Recorded commands do not establish physical oper status.'],
        ['Invent continuity or exact activation','Resolve conflict from list order or majority','Treat administrative config as measured oper health'],
        [],['Retain known command at each capture.','Do not infer an interval from point observations or discard the conflict.'],
        'Same-time source conflict plus later observation, unlike original monotonic buffers/verified change event.', 'floating')
    s=network_fixture('H-05');flow={'id':'poll-query','source_device_id':5301,'destination_device_id':5303,
        'source_address':'198.18.88.1','destination_address':'198.18.88.3','vrf':'monitor','destination_vrf':'monitor',
        'protocol':'udp','source_port':49152,'destination_port':161,'require_return':True}
    s['network']['flows']=[flow];s['network']['tables'][0]['routes'][0]['next_hops'][0]['resolved']=None
    computed=assess_flow(s,Flow.model_validate(flow));assert computed['forward']['status']=='unknown' and computed['return']['status']=='delivered'
    s['records']['state']=[row('h05-poll-model','forwarding_assessment',5301,'2026-10-28T18:00:00Z',{'derived':True,'flow':flow,'assessment':computed}),
        row('h05-route','routing_table',5301,'2026-10-28T18:00:00Z',s['network']['tables'][0]),
        *[row('h05-port-'+str(p['id']),'interface_state',p['device_id'],'2026-10-28T18:00:00Z',
            {'admin_status':p['admin_status'],'oper_status':p['oper_status'],'vrf':p['vrf'],'prefix':p['prefix'],'interface':p['name']},p['id']) for p in s['interfaces']]]
    add('H-05',s,'LumenProbe has a complete route toward ArchiveSink and every supplied port record is up. Explain whether the modeled UDP 161 poll and reverse path are established, identifying the remaining evidence gap. Recommend two distinct passive artifacts to request next and explain what each could resolve. Do not execute new reads, collection or tests; use only the supplied state.',
        ['state'],['Forward unknown due to unresolved/unknown next-hop resolution, despite route and port-up records; return modeled delivered.',
            'Two distinct passive recommendations with discriminating purpose, e.g.recorded neighbor-resolution and packet/application response evidence; no execution.',
            'Model delivery is not measured application response; do not recommend merely proving already-recorded port-up as the sole next step.'],
        ['Treat unknown next hop as failed or resolved','Omit requested advice','Guarantee service from route/up ports','Execute a recommendation'],
        [],['Retain reverse modeled delivery and known up states.','Unknown next-hop and application evidence remain limited.'],
        'Known-up interfaces with unresolved neighbor and asymmetric modeled results; recommendations must address a different gap than historical unknown-port case.', 'studio')
    s=network_fixture('H-06');s['network']['policies']=[{'id':'hub-trap-filter','interface_id':53022,'direction':'egress','vrf':'monitor',
        'default_action':'permit','rules':[{'id':'deny-traps','protocol':'udp','destination_port':162,'action':'deny'}]}]
    flows=[{**flow,'id':'trap-stream','source_port':49160,'destination_port':162},{**flow,'id':'log-stream','source_port':49161,'destination_port':514}]
    s['network']['flows']=flows
    for f in flows:
        result=assess_flow(s,Flow.model_validate(f))
        assert result['forward']['status']==('failed' if f['id']=='trap-stream' else 'delivered') and result['return']['status']=='delivered'
        s['records']['state'].append(row('h06-'+f['id'],'forwarding_assessment',5301,'2026-10-28T18:00:00Z',{'derived':True,'flow':f,'assessment':result}))
    add('H-06',s,'Compare the modeled UDP trap stream to port 162 and log stream to port 514 from LumenProbe to ArchiveSink in monitor. For each flow distinguish forward and return outcomes, identify TransitHub ingress and egress ownership and localize any deny. Does this prove a deployed filter caused a real monitoring outage? Use these state calculations only.',
        ['state'],['Trap forward fails atTransitHub5302Ethernet2/9egress53022hub-trap-filter/deny-traps; return delivered.',
            'Log forward and return delivered. Transit forward ingressEthernet2/1(53021), egressEthernet2/9(53022), owned byTransitHub inmonitor.',
            'Positive modeled policy consequence established; no real deployment/application-outage proof.'],
        ['Swap forward/return or flow results','Deny located atsource/destination/wrong port','Withhold supported modeled result as whollyunknown','Infer deployed outage cause'],
        [],['Preserve supported deny and successful other flow.','Reject wrong owner/direction/VRF or physical-authority claim.'],
        'Two simultaneous UDP service classes, transit egress denial and reverse delivery; not the original source-egress before/after or return-ingress TLS case.', 'floating')
    return items

def inputs(case):
    from llm.gateway_models import Evidence
    s=case['scenario'];bydev={d['id']:d['hostname'] for d in s['devices']};results=[];evidence=[]
    for domain in case['domains']:
        tool='network.configuration' if domain=='running_configuration' else 'network.'+domain
        receipt=case['id'].lower()+'-'+domain
        # This is authored fixture provenance, never a fabricated executed read.
        records=[{**copy.deepcopy(x['values']),**{k:v for k,v in x.items() if k!='values'},'hostname':bydev[x['device_id']]} for x in s['records'][domain]]
        results.append({'tool':tool,'status':'success','evidence_ids':[receipt],
            'data':{'records':records,'source_available':True,'total':len(records),'truncated':False}})
        evidence.append(Evidence(id=receipt,source='Authored synthetic timestamp fixture '+case['id']+'/'+domain,origin='simulated').model_dump())
    return {'request':case['question'],'results':results,'evidence':evidence,'history':[],'planning':{},'retrieval':{'supplementary_permitted':False}}

def check_oracles(fixtures):
    """Independent source arithmetic/ownership checks, not a semantic grader."""
    from llm.orchestration.investigation_support import compatible_claims
    dt=lambda v:datetime.fromisoformat(v.replace('Z','+00:00'))
    minutes=lambda later,earlier:(dt(later)-dt(earlier)).total_seconds()/60
    h1,h2,h3,h4,h5,h6=fixtures
    event=h1['scenario']['records']['syslog'][0];v=event['values']
    assert v['applied'] is True and v['verification_status']=='verified'
    assert minutes(event['timestamp'],v['effective_at'])==13
    assert minutes(h1['scenario']['records']['running_configuration'][0]['timestamp'],v['effective_at'])==18
    plateau,ravine=h2['scenario']['records']['incidents']
    assert minutes(plateau['values']['first_observed'],ravine['values']['first_observed'])==4
    assert minutes(ravine['timestamp'],ravine['values']['first_observed'])==15
    assert minutes(plateau['timestamp'],plateau['values']['first_observed'])==2
    brook,vale=h3['scenario']['records']['syslog']
    assert vale['values']['effective_at']==brook['values']['effective_at']
    assert minutes(vale['timestamp'],vale['values']['effective_at'])==13
    assert minutes(brook['timestamp'],brook['values']['effective_at'])==6
    a,b,later=h4['scenario']['records']['running_configuration']
    assert a['timestamp']==b['timestamp'] and a['source']!=b['source']
    assert a['values']['config_text']!=b['values']['config_text']
    assert dt(a['timestamp'])<dt('2026-10-28T06:55:00Z')<dt(later['timestamp'])
    assert all(p['admin_status']==p['oper_status']=='up' for p in h5['scenario']['interfaces'])
    assert h5['scenario']['network']['tables'][0]['routes'][0]['next_hops'][0]['resolved'] is None
    trap,log=h6['scenario']['records']['state']
    assert trap['values']['assessment']['forward']['status']=='failed'
    assert log['values']['assessment']['forward']['status']=='delivered'
    loc=trap['values']['assessment']['forward']['branches'][0]['failure_location']
    assert (loc['device_id'],loc['interface_id'],loc['direction'])==(5302,53022,'egress')
    assert h6['scenario']['network']['policies'][0]['rules'][0]['destination_port']==162
    checks=[]
    for c in fixtures:
        args=inputs(c);inventory={'devices':[{**d,'interfaces':[p for p in c['scenario']['interfaces'] if p['device_id']==d['id']]} for d in c['scenario']['devices']]}
        for expected in c['oracle']['claim_bindings']:
            declaration={**expected,'statement':'Fixture source binding, not a generated conclusion.','scope':'recorded'}
            review=compatible_claims({'claims':[declaration]},args['results'],inventory)['claims'][0]
            assert review['verdict']==('INSUFFICIENT_EVIDENCE' if c['id']=='H-02' else 'SUPPORTED')
            checks.append({'case':c['id'],'record_refs':expected['record_refs'],'correct_binding_verdict':review['verdict']})
    return {'source_time_arithmetic_and_model_locations':'PASS','typed_binding_checks':checks,
        'incident_first_observed_not_mechanically_certified':True,'model_quality_assessed':False}

def forbidden(*a,**kw):raise AssertionError('Offline preparation prohibits inference, network and registered readers')

async def freeze():
    import httpx,socket
    from llm import model_roles
    from llm.orchestration import role_reasoning
    from llm.tools import ToolRegistry
    from llm.orchestration.model import RoutingModel
    from local_providers.development import Scenario
    assert not SPEC.exists(),'Never overwrite the frozen registry'
    selected=[];call_order=[];total_reservation=0
    with ExitStack() as stack:
        stack.enter_context(patch.dict(os.environ,ENV))
        for target in ['httpx.AsyncClient.send','httpx.Client.send','socket.create_connection']:
            stack.enter_context(patch(target,forbidden))
        stack.enter_context(patch.object(ToolRegistry,'invoke',forbidden));stack.enter_context(patch.object(RoutingModel,'generate',forbidden))
        old_reasoning=before_module('orchestration/role_reasoning');old_roles=before_module('model_roles')
        fixtures=cases();assert len(fixtures)==6
        oracle_checks=check_oracles(fixtures)
        save(AUDIT/'source-oracle-checks.json',oracle_checks)
        # Save source fixtures/oracles before constructing any candidate packet.
        for c in fixtures:
            Scenario.model_validate(c['scenario'])
            save(AUDIT/'fixtures'/c['id']/'case.json',c)
        for i,c in enumerate(fixtures):
            case_path=AUDIT/'fixtures'/c['id']/'case.json';args=inputs(c);control=await capture(role_reasoning,args)
            assert control==await capture(old_reasoning,args);off_consent=model_roles.consent_manifest()
            assert off_consent==old_roles.consent_manifest()
            with patch.dict(os.environ,{'COGNISHIELD_AI_SOURCECLAIM_TIMESTAMP_EXPERIMENT':'candidate'}):
                candidate=await capture(role_reasoning,args);on_consent=model_roles.consent_manifest()
            without=copy.deepcopy(candidate['schema']);delta=without['$defs']['SourceClaim']['properties']['timestamp'].pop('description')
            assert delta==role_reasoning.SOURCECLAIM_TIMESTAMP_DESCRIPTION and without==control['schema']
            assert control['messages']==candidate['messages'];assert control['purpose']==candidate['purpose']
            off_wire=await serialized_wire(control['messages'],control['schema']);on_wire=await serialized_wire(candidate['messages'],candidate['schema'])
            atext=off_wire['systemInstruction']['parts'][1]['text'];btext=on_wire['systemInstruction']['parts'][1]['text']
            prefix='Return only JSON satisfying this exact application schema: '
            assert json.loads(atext[len(prefix):])==control['schema'];assert json.loads(btext[len(prefix):])==candidate['schema']
            restored=copy.deepcopy(on_wire);restored['systemInstruction']['parts'][1]['text']=atext;assert restored==off_wire
            packet=control['messages'][1]['content'];assert len(packet)<=64000
            pair={'id':c['id'],'case_path':relative(case_path),'case_sha256':sha(case_path),'inputs':args,
                'authored_fixture_not_executed_reader':True,'question_sha256':digest(c['question']),
                'source_records_sha256':digest(canonical(args['results'])),'packet_sha256':digest(packet),'packet_characters':len(packet),
                'oracle':c['oracle'],'arms':{},'consent_status':'PENDING_NEW_USER_AUTHORIZATION_AND_EXISTING_EXACT_OWNER_SOURCE_REVISION_APPROVAL'}
            for arm,model_input,consent,wire in [('control',control,off_consent,off_wire),('candidate',candidate,on_consent,on_wire)]:
                reserve=len(json.dumps(wire,ensure_ascii=False).encode());total_reservation+=reserve
                pair['arms'][arm]={**model_input,'schema_sha256':digest(canonical(model_input['schema'])),
                    'messages_sha256':digest(canonical(model_input['messages'])),'consent_manifest':consent,
                    'role_binding_sha256':digest(json.dumps(consent,sort_keys=True)),'provider_body':wire,
                    'provider_body_sha256':digest(canonical(wire)),'conservative_input_reservation_bytes':reserve}
            dest=AUDIT/'frozen-v1'/c['id']/'pair.json';save(dest,pair)
            selected.append({'id':c['id'],'surface':c['surface'],'pair_path':relative(dest),'pair_sha256':sha(dest),
                'case_path':relative(case_path),'case_sha256':sha(case_path),'question_sha256':pair['question_sha256'],
                'source_records_sha256':pair['source_records_sha256'],'packet_characters':len(packet),'oracle':c['oracle']})
            for arm in (['control','candidate'] if i%2==0 else ['candidate','control']):call_order.append({'sequence':len(call_order)+1,'case':c['id'],'arm':arm})
        before=load(AUDIT/'preservation-before.json')
        spec={'version':1,'frozen_at':datetime.now(timezone.utc).isoformat(),'status':'OFFLINE_FROZEN_LIVE_NOT_AUTHORIZED',
            'candidate_description':role_reasoning.SOURCECLAIM_TIMESTAMP_DESCRIPTION,
            'description_sha256':digest(role_reasoning.SOURCECLAIM_TIMESTAMP_DESCRIPTION),
            'schema_delta_pointer':'/$defs/SourceClaim/properties/timestamp/description','cases':selected,
            'call_order':call_order,'maximum_dispatch_attempts':12,'calls_per_cell':1,'retries':0,
            'new_planner_or_reader_calls':0,'model':asdict(model_roles.role_config('evidence_reasoner')),
            'input_token_budget':{'actual_tokens':'NOT_MEASURED_NO_TOKEN_COUNT_API_CALL',
                'conservative_sum_of_body_byte_reservations':total_reservation,
                'meaning':'Existing adapter reserves serialized body bytes conservatively before dispatch, then records actual provider tokens. This is not a tokenizer count.'},
            'maximum_output_tokens_total':12*8192,'request_wide_seconds':120,'evidence_cap':64000,
            'grading':{'method':'Source-derived independently checkable, implementation-assistant graded; no model grader, not blinded or external.',
                'units':'Six fresh source arrangements,12pairedoutputs; one sample each, not statistical reliability.',
                'separate_metrics':['raw_answer_correctness','structured_claim_binding_and_semantics','whole_response_consistency','released_answer_quality'],
                'claim_gate':'All applicable temporal declarations bind the correct record/owner and record timestamp and separate event field/value. No temporal claims means NOT_DEMONSTRATED, not automatic success.',
                'required_temporal_conditions':['H-01','H-02','H-03'],
                'whole_response_gate':'No substantive prose/claim/assessment inconsistency; no paired-control adequacy regression.',
                'positive_control':'H-06must retain supported directional/modelled results.',
                'release_gate':'No incorrect verified claims, new false suppression, unauthorized reads, unsupported activation or causal assertions.',
                'diagnostic_controls':['H-04continuity/conflict','H-05advice and task completion'],
                'ambiguous_answers':'Record exact text, source pointer and reason; do not silently grant adequacy.',
                'interface_clarity_not_reasoning':'Corrected binding alone is not raw reasoning improvement. No promotion from schema/JSON/citation success.'},
            'consent':{'user_authorization':'NOT_YET_GRANTED. Prior18and12callapprovals exhausted.',
                'per_cell':'Existing exact owner/request/history/synthetic scenario revision and current model-role binding required.',
                'fixture_provenance':'New authored evaluation fixtures, not newly collected or executed reader results.',
                'ordinary_private_editor_data':'EXCLUDED','live_setup':'Seal each scenario with existing ScenarioManager/consent machinery only after new authorization; no ordinary source activation.'},
            'quota':{'path':'tmp/ai-cloud-usage.json','hash_at_freeze':before['quota_hash'],'rows_at_freeze':before['quota_rows'],
                'preflight_before_live':True,'rpm_ceiling':15,'input_tpm_ceiling':150000,'rpd_ceiling':500,'sequential':True},
            'runtime_sources':{p:sha(ROOT/p) for p in before['source_hashes']},
            'no_default_activation':True,'formal_stage_closed':False}
        assert (spec['model']['model'],spec['model']['thinking'],spec['model']['output_tokens'],spec['model']['schema_mode'])==('gemini-3.5-flash-lite','low',8192,'validated_json')
        save(SPEC,spec)
        result={'status':'OFFLINE_VERIFIED_LIVE_NOT_RUN','registry':relative(SPEC),'registry_sha256':sha(SPEC),
            'source_cases':6,'pairs':6,'candidate_schema_description_survives_actual_adapter_serialization':True,
            'off_exact_task_start':True,'only_one_description_delta':True,'same_messages_packets_settings':True,
            'real_provider_calls':0,'model_calls':0,'registered_reader_calls':0,'real_quota_reservations':0,
            'maximum_future_dispatches':12,'actual_quality':'NOT_MEASURED'}
        save(AUDIT/'freeze-receipt.json',result);print(json.dumps(result,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.parse_args();asyncio.run(freeze())
