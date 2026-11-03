"""Freeze six independent reasoning-only cases using existing authorized readers.

No provider calls. Reuses the single acceptance DB; no ordinary data/services.
"""
import asyncio,copy,hashlib,json,os,sys
from datetime import datetime,timezone
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'tmp/phase-g/iterations/20261102-evidence-reasoning-contract'
SPEC=ROOT/'docs/evaluations/phase_g_evidence_reasoning_contract_v3.json'
DB=ROOT/'tmp/phase-g/iterations/20261101-audit-grounded-repair/evaluation-app.db'
sys.path.insert(0,str(ROOT/'backend'))

def scenario(name,network=False):
    s={'format_version':2 if network else 1,'id':name,'title':'Reasoning contract independent condition '+name,
       'revision':1,'logical_time':'2026-11-02T16:00:00Z','model_scope':'ipv4_observation' if network else 'bounded_routed_path',
       'inventory_complete':True,'devices':[],'interfaces':[],'planned_links':[],
       'records':{d:[] for d in ['state','configuration','running_configuration','syslog','topology','telemetry','incidents']},
       'availability':{d:True for d in ['state','configuration','running_configuration','syslog','topology','telemetry','incidents']}}
    for i,n in enumerate(['CedarEdge','MicaCore','IrisExit'],1):
        did=i*1101;s['devices'].append({'id':did,'hostname':n,'management_ip':f'192.0.2.{i+30}','vendor':'cisco_xe','os_version':'17.12','site':'reasoning-contract-synthetic'})
    ports=[(11011,1101,'Ethernet1/1','10.241.1.1/30'),(22021,2202,'Ethernet1/1','10.241.1.2/30'),
           (22022,2202,'Ethernet1/2','10.241.2.1/30'),(33031,3303,'Ethernet1/1','10.241.2.2/30'),
           (11010,1101,'Loopback11','198.19.71.1/32'),(33030,3303,'Loopback33','198.19.71.3/32')]
    s['interfaces']=[{'id':i,'device_id':d,'name':n,'prefix':p,'admin_status':'up','oper_status':'up','vrf':'violet'} for i,d,n,p in ports]
    s['planned_links']=[{'id':71,'src_device_id':1101,'src_interface_id':11011,'dst_device_id':2202,'dst_interface_id':22021},
                         {'id':72,'src_device_id':2202,'src_interface_id':22022,'dst_device_id':3303,'dst_interface_id':33031}]
    if network:
        def route(i,p,port,ip):return {'id':i,'prefix':p,'origin':'static','preference':7,'next_hops':[{'interface_id':port,'address':ip,'resolved':True}]}
        s['network']={'observed_at':s['logical_time'],'policy_attachments_complete':True,'policies':[],'ospf':[],'bgp':[],'metrics':[],
         'tables':[{'device_id':1101,'vrf':'violet','complete':True,'routes':[route('cedar-to-iris','198.19.71.3/32',11011,'10.241.1.2')]},
                   {'device_id':2202,'vrf':'violet','complete':True,'routes':[route('mica-to-iris','198.19.71.3/32',22022,'10.241.2.2'),route('mica-to-cedar','198.19.71.1/32',22021,'10.241.1.1')]},
                   {'device_id':3303,'vrf':'violet','complete':True,'routes':[route('iris-to-cedar','198.19.71.1/32',33031,'10.241.2.1')]}],
         'flows':[{'id':'tls-report','source_device_id':1101,'destination_device_id':3303,'source_address':'198.19.71.1','destination_address':'198.19.71.3',
                   'vrf':'violet','destination_vrf':'violet','protocol':'tcp','source_port':47813,'destination_port':8443,'require_return':True}]}
    return s

def record(ref,kind,values,time,device=1101,interface=None,current=True):
    return {'id':ref,'kind':kind,'device_id':device,'interface_id':interface,'timestamp':'2026-11-02T'+time+'Z',
            'source':'independent-synthetic-observer','current':current,'values':values}

def cases():
    c=[]
    def add(s,prompt,queries,expected,prohibited,surface):
        c.append({'id':s['id'],'scenario':s,'prompt':prompt,'surface':surface,'queries':queries,
                  'expected_outcomes':expected,'prohibited_claims':prohibited})
    s=scenario('RC-01')
    s['records']['running_configuration']=[record('rc1-running','running_configuration',{'config_text':'ip route 203.0.113.0 255.255.255.0 10.241.1.2','observed_at':'2026-11-02T14:15:00Z'},'14:15:00')]
    s['records']['configuration']=[record('rc1-candidate','configuration_snapshot',{'config_text':'ip route 203.0.113.0 255.255.255.0 10.241.1.6','saved_at':'2026-11-02T15:00:00Z','configuration_state':'staged'},'15:00:00',current=False)]
    add(s,'Compare CedarEdge recorded running route with the staged candidate. Which next hops are recorded, and can you establish which was active at15:10? Explain whether the candidate was definitely not applied. Use configuration only.',
        ['configuration'],['Running observed14:15 via10.241.1.2; candidate saved15:00 via10.241.1.6.','No applied flag/effective timestamp; neither active15:10 nor definitely-unapplied is established.'],
        ['Candidate definitely applied','Candidate definitely not applied','Continuous running through15:10'], 'floating')
    s=scenario('RC-02')
    s['records']['running_configuration']=[record('rc2-'+str(i),'running_configuration',{'config_text':f'logging buffered {v}'},t,current=i==2) for i,(v,t) in enumerate([(12000,'07:00:00'),(24000,'09:00:00'),(12000,'11:00:00')])]
    s['records']['syslog']=[record('rc2-applied','configuration_change',{'message':'Verified logging buffer change to24000','applied':True,'verification_status':'verified','effective_at':'2026-11-02T08:25:00Z'},'08:26:00')]
    add(s,'Explain CedarEdge logging-buffer chronology from all captures and the verified change event. Can you infer the value at08:00 or the exact later reversion time? State what the08:25application establishes and what remains unknown. Use configuration and syslog only.',
        ['configuration','syslog'],['12000at07:00;24000at09:00;12000at11:00.','Verified application24000effective08:25; preserve positive evidence.','08:00unknown and exact later reversion unknown; endpoints do not prove continuous state.'],
        ['08:00value asserted','Exact reversion inferred from capture','Verified application denied'], 'studio')
    s=scenario('RC-03',True)
    s['network']['policies']=[{'id':'return-tls-deny','interface_id':22022,'direction':'ingress','vrf':'violet','default_action':'permit',
        'rules':[{'id':'return-src','protocol':'tcp','source_port':8443,'action':'deny'}]}]
    s['network']['tables'].append({'device_id':3303,'vrf':'default','complete':True,'routes':[{'id':'default-discard','prefix':'198.19.71.1/32','origin':'static','preference':1,'action':'discard'}]})
    add(s,'Assess CedarEdge-to-IrisExit modeled TLS delivery in violet. Identify both transit ingress and egress owners in each traversed direction. Where does return delivery stop, does the default-VRF discard matter, and is protocol or live connectivity established? Use state only.',
        ['state'],['Forwarddelivered;returnfailed atMicaCore2202 ingress22022, not IrisExit or egress22021.','ForwardMica22021ingress22022egress;return reaches22022andisdeniedbeforeegress.','Defaultdiscardisolatedfromviolet; modeledonly, no measuredprotocolhealth.'],
        ['Forwardfailed','Returnegresstraversedafterdenial','Live/protocol health asserted'], 'floating')
    s=scenario('RC-04',True)
    for port in s['interfaces']:port['admin_status']='unknown';port['oper_status']='unknown'
    add(s,'CedarEdge has a route toward IrisExit. Does that prove service on TCP8443 in violet is working in both directions? Explain the routing fact, modeled uncertainty and most useful passive evidence to request next. Read state only and do not collect or test anything.',
        ['state'],['Routepresence recorded; operationalinterfaceunknown makesmodeledoutcomeunknown, not confirmedfailure or delivery.','Recommend obtaininginterface/next-hopstate; no new collection, no physical conclusion.'],
        ['Connectivityguaranteed','Unknown state declared shutdown','Probeexecuted'], 'studio')
    s=scenario('RC-05')
    s['records']['state']=[record('rc5-crc','interface_counters',{'crc_errors':18,'sampling_seconds':60,'vrf':'violet'},'12:35:00',interface=11011)]
    s['records']['incidents']=[record('rc5-cooling','incident',{'summary':'Cabinet cooling warning','first_observed':'2026-11-02T12:30:00Z','status':'recorded'},'12:31:00')]
    s['availability']['syslog']=False
    add(s,'Could the cooling warning explain CedarEdge Ethernet1/1 errors? Distinguish chronology from cause and say whether unavailable syslog rules out a reset. Recommend two different passive checks without executing them. Use recorded state, incidents and syslog only.',
        ['state','incidents','syslog'],['Coolingfirstobserved12:30, counterssampled12:35; temporalassociationnotcause.','Coolingpossiblehypothesis; onecounterrecordnottrend; no reset conclusion from unavailablesyslog.','Two discriminatingpassivecheckswithlimits;no newexecution.'],
        ['Coolingestablishedcause','Noresetbecause logsunavailable','Countertrendinvented'], 'floating')
    s=scenario('RC-06')
    from development.network_model import assess_flow,Flow
    before=scenario('RC-06-before',True);after=copy.deepcopy(before)
    after['network']['policies']=[{'id':'egress-service-deny','interface_id':11011,'direction':'egress','vrf':'violet','default_action':'permit',
        'rules':[{'id':'service-deny','protocol':'tcp','destination_port':8443,'action':'deny'}]}]
    for tag,model in [('before',before),('after',after)]:
        assessment=assess_flow(model,Flow.model_validate(model['network']['flows'][0]))
        s['records']['state'].append(record('rc6-'+tag,'forwarding_assessment',{'derived':True,'model_variant':tag,'assessment':assessment},'13:00:00'))
    add(s,'Compare the two recorded calculation variants for TCP8443 from CedarEdge. What modeled consequence follows from attaching the egress deny policy, where is it localized, and does this prove a deployed policy caused a real outage? Use state only.',
        ['state'],['Beforeforwarddelivered;afterforwardfailedatCedar1101egress11011.','Controlledmodeledconsequenceisjustified;do notweaken to whollyunknown.','Neitherdeploymentnorrealoutagecauseestablished.'],
        ['Physicalcauseasserted','Modeledblockdenieddespitecalculation','Wrongfailedowner'], 'studio')
    return c

async def freeze():
    os.environ.update(COGNISHIELD_MODE='local_lab',COGNISHIELD_DB_PATH=str(DB),COGNISHIELD_DEV_SIMULATION='1',
        COGNISHIELD_AI_COMPLETENESS='1',COGNISHIELD_AI_OUTCOMES='0',COGNISHIELD_AI_EVIDENCE_HARNESS='0',COGNISHIELD_AI_EVIDENCE_LAYOUT='current')
    import lab_config
    assert Path(lab_config.DB_PATH).resolve()==DB.resolve()
    from db.manager import DatabaseManager
    from llm.gateway_store import ConversationStore,ensure_schema
    from llm.gateway_services import registry_for
    from llm.gateway_network import network_context,READ_TOOLS
    from llm.orchestration.adapters import AuthorizedTools
    from llm.tools import ToolAuthorization
    from llm.orchestration.role_reasoning import decide
    from local_providers.development import Scenario,ScenarioManager
    db=DatabaseManager(str(DB));ensure_schema(db);store=ConversationStore(db);frozen=[]
    def save(path,data):
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('x',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2)
    class Captured(Exception):pass
    for case in cases():
        s=Scenario.model_validate(case['scenario']).model_dump(mode='json')
        file=OUT/'scenarios'/(case['id']+'.json');existed=file.exists();manager=ScenarioManager(file)
        if not existed:manager.change('import',manager.snapshot()[1]['source_revision'],s)
        else:assert manager.snapshot()[0]==Scenario.model_validate(s).model_dump(), 'Do not overwrite frozen scenario'
        db._development_scenario=manager
        cid=store.create('reasoning-contract-freezer',case['surface'])['id']
        auth=ToolAuthorization('reasoning-contract-freezer','admin',case['surface'],cid,READ_TOOLS)
        tools=AuthorizedTools(registry_for(db),store,auth,max_calls=8);rows=[];evidence=[]
        for domain in case['queries']:
            r,e,_=await network_context(db,tools,auth,case['prompt'],domains_override=[domain],device_refs_override=['1101','3303'] if case['id'] in {'RC-03','RC-04'} else ['1101'],
                validated_parameters={domain:{'device_refs':['1101','3303'] if case['id'] in {'RC-03','RC-04'} else ['1101'],'source_scope':'both','live':False,'limit':100}})
            rows+=r;evidence+=e
        args={'request':case['prompt'],'results':rows,'evidence':evidence,'history':[],'planning':{},'retrieval':{'supplementary_permitted':False}}
        data={'case':{k:v for k,v in case.items() if k!='scenario'},'scenario_path':str(file.relative_to(ROOT)).replace('\\','/'),
              'scenario':manager.snapshot()[1],'inputs':{**args,'evidence':[e.model_dump(mode='json') for e in evidence]},'receipts':tools.requests,'arms':{}}
        for arm in ['off','obligations','relationships']:
            os.environ['COGNISHIELD_AI_REASONING_CONTRACT']=arm
            class Capture:
                hybrid=SimpleNamespace(remote_calls=0,role_calls=0,max_remote_calls=3)
                async def generate(self,messages,structured,purpose):
                    data['arms'][arm]={'messages':messages,'schema':structured};raise Captured()
            try:await decide(Capture(),**args)
            except Captured:pass
            packet=json.loads(data['arms'][arm]['messages'][-1]['content'])
            assert packet['reader_results']==rows,'Source operands changed across arms'
            assert len(data['arms'][arm]['messages'][-1]['content'])<=64000
        assert case['id']!='RC-03' or any('return-tls-deny' in json.dumps(r['data']) for r in rows)
        if case['id']=='RC-06':
            records=[x for r in rows for x in r['data'].get('records',[])];statuses={x['model_variant']:x['assessment']['forward']['status'] for x in records if x.get('model_variant')}
            assert statuses=={'before':'delivered','after':'failed'}
        if case['id'] in {'RC-03','RC-04'}:
            assessments=[record['assessment'] for row in rows for record in row['data'].get('records',[]) if record.get('kind')=='forwarding_assessment']
            assert len(assessments)==1
            if case['id']=='RC-03':
                assert assessments[0]['forward']['status']=='delivered' and assessments[0]['return']['status']=='failed'
                loc=assessments[0]['return']['branches'][0]['failure_location']
                assert loc['device_id']==2202 and loc['interface_id']==22022
            else:assert assessments[0]['forward']['status']=='unknown'
        if case['id']=='RC-05':assert any(r['tool']=='network.syslog' and r['status']=='unavailable' for r in rows)
        assert data['arms']['relationships'] and json.loads(data['arms']['relationships']['messages'][-1]['content'])['reasoning_contract']['relationships']['facts'], 'Full relationship index must be admitted in this comparison'
        dest=OUT/'frozen-v3'/case['id']/'packet.json';save(dest,data)
        frozen.append({'id':case['id'],'packet_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),
            'scenario_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
            'characters':{a:len(v['messages'][-1]['content']) for a,v in data['arms'].items()},
            'source_operands_identical':True,'case':data['case']})
    os.environ['COGNISHIELD_AI_REASONING_CONTRACT']='off'
    save(SPEC,{'version':1,'frozen_at':datetime.now(timezone.utc).isoformat(),'cloud_attempt_ceiling':18,'cloud_calls':0,
        'grading':'Source-derived independently checkable, implementation-assistant graded; not blinded. Raw and released full answers graded separately.',
        'model':'gemini-3.5-flash-lite','thinking':'low','output_tokens':8192,'no_additional_reads_between_arms':True,
        'promotion_gate':'B improves raw full-answer correctness on >=2/6; positive RC06 retained; no new unsupported causal/scope/evidence/JSON/false-suppression regression.',
        'cases':frozen})
    save(OUT/'freeze-receipt-v3.json',{'registry_sha256':hashlib.sha256(SPEC.read_bytes()).hexdigest(),'cloud_calls':0,'conditions':6,'arms':3,'new_readers':False})
    print(json.dumps({'freeze':'PASS','cases':6,'cloud_calls':0,'characters':[x['characters'] for x in frozen]}))

if __name__=='__main__':asyncio.run(freeze())
