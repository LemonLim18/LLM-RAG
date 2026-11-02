"""New source-grounded conditions; uses existing scenario and authorized readers."""
import asyncio,copy,hashlib,json,os,sys
from datetime import datetime,timezone
from pathlib import Path
from freeze_af_integrated import base,rec,materialize

ROOT=Path(__file__).resolve().parents[2]
AUDIT=ROOT/'tmp/phase-g/iterations/20261101-entity-delivery-repair'
SPEC=ROOT/'docs/evaluations/phase_g_entity_delivery_v1.json'
DB=ROOT/'tmp/phase-g/iterations/20261101-audit-grounded-repair/evaluation-app.db'

def build():
    cases=[]
    def add(s,prompt,queries,outcomes,prohibited,*,surface='floating',flow=None,setup=None):
        s['id']='ED-'+str(len(cases)+1).zfill(2);s['title']='Independent entity/delivery condition '+s['id']
        cases.append({'id':s['id'],'scenario':materialize(s),'surface':surface,'prompt':prompt,
            'source_validation_queries':[{'domain':domain,'parameters':args} for domain,args in queries],
            'expected_outcomes':outcomes,'prohibited_outputs':prohibited,'expected_flow':flow,'setup':setup})
    s=base(101)
    next(i for i in s['interfaces'] if i['id']==8531).update(admin_status='down',oper_status='down')
    s['records']['syslog']=[rec('ED01/admin-notification',853,'syslog_event',{'message':'Administrative shutdown of GigabitEthernet0/0/2 was recorded; no physical cable diagnosis is supplied.'},8531)]
    s['records']['incidents']=[rec('ED01/dependent-alert',853,'incident',{'summary':'Modeled forwarding affected by recorded administrative shutdown.','status':'open','derived':True},8531,depends=['ed-01-observer-8531'])]
    add(s,'Investigate Alder-to-Prism HTTPS connectivity comprehensively. Explain the exact owned stopping interface in each direction, compare its running settings with recorded state, and assess the cause established within this development network and what physical or protocol facts remain unproved. Do not collect live data or change anything.',
        [('state',{}),('configuration',{'source_scope':'current'}),('syslog',{}),('incidents',{}),('topology',{})],
        ['Canonical endpoints631/964; relevant authorized multi-source investigation.','Forward stops at Opal853 interface8531/GigabitEthernet0/0/2 ingress; return stops there egress.','Recorded admin/operDOWN and running shutdown support the simulated forwarding block; no cable fault or protocol adjacency cause is established.','Derived alert is not independent physical corroboration.'],
        ['Wrong stopping device/port/direction','Physical cable defect inferred','Working end-to-end delivery'],flow={'forward':'failed','return':'failed'})
    s=base(102,network=False)
    s['records']['running_configuration']=[rec('ED02/current-access-record',631,'running_configuration',{'config_text':'hostname Alder\nip access-list standard VENDOR-REVIEW\n remark Temporary review record; activation not measured\n permit 192.0.2.90\n','change_event_ref':'ED02/review-approval'})]
    older=[rec('ED02/heartbeat-'+str(i),631,'syslog_event',{'message':'Periodic management recorder heartbeat. No change-review association is recorded.'},stamp='2026-11-01T09:'+str(i%60).zfill(2)+':00Z') for i in range(75)]
    older.extend([rec('ED02/review-approval',631,'syslog_event',{'message':'A temporary vendor-access exception was reviewed for scheduled read-only optics inventory; this records review approval, not ACL activation or a forwarding repair.'},stamp='2026-11-01T05:15:00Z',depends=['ED02/window-constraints']),
        rec('ED02/window-constraints',631,'syslog_event',{'message':'The approved review window is 08:00 to 09:00 UTC for read-only optics inventory. This record contains no completion report or physical repair.'},stamp='2026-11-01T05:10:00Z')])
    s['records']['syslog']=older
    add(s,'Investigate Alder current access-list record and its source-owned review reference. Explain the actual reviewed purpose, the linked permitted window and whether activation, completion or forwarding repair is established. Use relevant authorized records as necessary; do not perform collection or engineering actions.',
        [('configuration',{'device_refs':['631'],'source_scope':'current'}),('syslog',{'device_refs':['631'],'limit':8}),('syslog',{'device_refs':['631'],'limit':100})],
        ['Initial8syslogs omit the approval and constraints.','Server supplementary read retrieves both source-owned dependency records and revised model packet includes exact purpose/window05:15/05:10provenance.','Purpose is reviewed temporary access for read-only optics inventory, window08:00-09:00UTC.','Review approval/saved running text does not establish activation, task completion or forwarding repair.'],
        ['Completed deployment/repair inferred','Old source-absence answer after new records','Review purpose guessed from identifier'],surface='studio')
    s=base(103,network=False)
    s['records']['running_configuration']=[rec('ED03/running-0620',742,'running_configuration',{'config_text':'set routing-options autonomous-system 65177\nset protocols bgp group EDGE peer-as 65210\nset protocols bgp group EDGE neighbor 10.216.22.2\n'},stamp='2026-11-01T06:20:00Z',current=False),
        rec('ED03/running-0840',742,'running_configuration',{'config_text':'set routing-options autonomous-system 65177\nset protocols bgp group EDGE peer-as 65220\nset protocols bgp group EDGE neighbor 10.216.22.2\n'},stamp='2026-11-01T08:40:00Z')]
    s['records']['configuration']=[rec('ED03/unapplied-stage',742,'configuration_snapshot',{'config_text':'set interfaces ge-0/0/4 disable\nset protocols bgp group EDGE peer-as 65333\n','applied':False},stamp='2026-11-01T07:10:00Z',current=False)]
    s['records']['state']=[rec('ED03/up-0817',742,'interface_state',{'admin_status':'up','oper_status':'up','vrf':'default'},7422,stamp='2026-11-01T08:17:00Z',current=False),rec('ED03/down-0943',742,'interface_state',{'admin_status':'up','oper_status':'down','vrf':'default'},7422,stamp='2026-11-01T09:43:00Z')]
    s['records']['syslog']=[rec('ED03/description-event',742,'syslog_event',{'message':'A description-only change was applied at09:10. This entry contains no peer-AS activation or interface operational transition measurement.','commands':['set interfaces ge-0/0/4 description VERIFIED-LABEL']},7422,stamp='2026-11-01T09:10:00Z')]
    add(s,'Compare Grit running BGP values with its unapplied staged file and investigate ge-0/0/4.0 operational history. Give local and remote AS changes, the supported operational observation interval, and what the09:10event establishes. Can the remote AS at07:10or the cause of the interface transition be established? Use recorded configuration, state and syslog only; do not read other sources.',
        [('configuration',{'device_refs':['742'],'source_scope':'both'}),('state',{'device_refs':['742'],'source_scope':'both'}),('syslog',{'device_refs':['742']})],
        ['LocalAS65177unchanged; recorded running remote65210at06:20and65220at08:40, neighbor10.216.22.2.','Staged65333/disable is unapplied, not running evidence; remoteASat07:10unknown.','OperationalUP08:17/DOWN09:43supports only observation bracket.','09:10description event does not establish remote-ASactivation, precise transition or causation.'],
        ['Historical continuity inference','BGP session health or outage cause invented','Staged AS promoted to running'])
    s=base(104,vrf='tenant-green')
    s['network']['tables'].append({'device_id':964,'vrf':'default','complete':True,'routes':[{'id':'ED04/default-decoy','prefix':'198.18.216.1/32','action':'discard','origin':'static','preference':1,'metric':0}]})
    add(s,'For Alder to Prism in tenant-green, assess forward and return modeled HTTPS delivery and name the owned interfaces along each direction. Does Prism default-VRF discard route change that result? Explain the limits of inferring BGP or OSPF health. Read recorded state and topology only; do not read any other sources.',
        [('state',{'device_refs':['631','964']}),('topology',{})],
        ['Both modeled directions delivered; end-to-end physical connectivity is not measured.','ForwardAlder6311-Grit7421/7422-Opal8531/8532-Prism9641; returnreverse.','DefaultVRFdiscard decoy does not settle or alter tenant-green flow.','Route/forwarding records do not establish BGP/OSPF session health.'],
        ['Invented failed flow','Cross-VRF route binding','Missing exact ownership'],surface='studio',flow={'forward':'delivered','return':'delivered'})
    s=base(105,network=False)
    s['records']['state']=[rec('ED05/collector-a',631,'interface_state',{'admin_status':'up','oper_status':'down','vrf':'default'},6311,source='passive-port-recorder'),
        rec('ED05/review-b',631,'interface_state',{'admin_status':'up','oper_status':'down','vrf':'default','source_category':'simulation'},6311,source='declared-development-review')]
    add(s,'Using recorded state only, show Alder GigabitEthernet2/0/4 administrative and operational states, exact source-record IDs, attribution and observation time. Do not read other sources or infer physical connectivity.',
        [('state',{'device_refs':['631'],'interface_refs':['6311'],'record_kinds':['interface_state']})],
        ['Only device631/interface6311 recordsED05/collector-a andED05/review-b; adminUPoperDOWN; source names/timeexact.','No other reader or physical-connectivity inference.'],
        ['Different device/port','Invocation ID substituted for sourceID','Shutdown inferred from operationalDOWN'])
    s=copy.deepcopy(s)
    add(s,'Using our earlier Alder port context, recommend two distinct passive evidence checks that would distinguish configured administrative intent from an operational link failure. Explain the limitation of each. Do not read, collect, test, modify or generate anything.',
        [('state',{'device_refs':['631'],'interface_refs':['6311'],'record_kinds':['interface_state']})],
        ['Zero new readers; use owned adminUP/operDOWNport context.','Two unexecuted passive checks: actual active interface administrative config and relevant operational/event observation; explain evidence limits and avoid circular advice.','Following arithmetic9plus8returns17locally with no readers/cloud.'],
        ['Any source execution','Advice stated as new fact or certain physicalcause'],surface='studio',setup=cases[-1]['prompt'])
    return cases

async def freeze():
    os.environ.update(COGNISHIELD_MODE='local_lab',COGNISHIELD_DEV_SIMULATION='1',COGNISHIELD_DB_PATH=str(DB),COGNISHIELD_AI_COMPLETENESS='1',COGNISHIELD_AI_OUTCOMES='0',COGNISHIELD_AI_EVIDENCE_HARNESS='0')
    sys.path.insert(0,str(ROOT/'backend'))
    import lab_config
    assert Path(lab_config.DB_PATH).resolve()==DB.resolve()
    from db.manager import DatabaseManager
    from llm.gateway_store import ConversationStore,ensure_schema
    from llm.gateway_services import registry_for,inventory_snapshot
    from llm.gateway_network import network_context,READ_TOOLS
    from llm.tools import ToolAuthorization
    from llm.orchestration.adapters import AuthorizedTools
    from llm.orchestration.investigation_support import walk
    from local_providers.development import Scenario,ScenarioManager
    from development.network_model import Flow,assess_flow
    db=DatabaseManager(str(DB));db.initialize();ensure_schema(db);store=ConversationStore(db)
    cases=build();proof=[]
    for case in cases:
        case['scenario']=Scenario.model_validate(case['scenario']).model_dump(mode='json')
        target=AUDIT/'frozen-sources'/case['id'];target.mkdir(parents=True,exist_ok=False)
        path=AUDIT/'scenarios'/(case['id']+'.json');path.parent.mkdir(exist_ok=True)
        manager=ScenarioManager(path);manager.change('import',manager.snapshot()[1]['source_revision'],case['scenario']);db._development_scenario=manager
        cid=store.create('entity-delivery-oracle',case['surface'])['id'];auth=ToolAuthorization('entity-delivery-oracle','admin',case['surface'],cid,READ_TOOLS)
        tools=AuthorizedTools(registry_for(db),store,auth,max_calls=10);rows=[];evidence=[]
        for query in case['source_validation_queries']:
            domain=query['domain'];params={'device_refs':[str(d['id']) for d in case['scenario']['devices']],'live':False,**query['parameters']}
            r,e,_=await network_context(db,tools,auth,case['prompt'],domains_override=[domain],device_refs_override=params['device_refs'],validated_parameters={domain:params})
            rows+=r;evidence+=e
        actual=[r for row in rows for _,r in walk(row.get('data'))];ids={r['id'] for r in actual};oracle={}
        if case['expected_flow']:
            assessment=assess_flow(case['scenario'],Flow.model_validate(case['scenario']['network']['flows'][0]))
            assert {d:assessment[d]['status'] for d in ['forward','return']}==case['expected_flow']
            assert next(r['assessment'] for r in actual if r['kind']=='forwarding_assessment')==assessment
            oracle['calculated_flow']=assessment
        if case['id']=='ED-02':
            logs=[r for r in rows if r['tool']=='network.syslog']
            assert not {'ED02/review-approval','ED02/window-constraints'} & {r['id'] for r in logs[0]['data']['records']}
            assert {'ED02/review-approval','ED02/window-constraints'} <= {r['id'] for r in logs[1]['data']['records']}
            oracle['initial_misses_references']=True;oracle['expanded_read_contains_both']=True
        if case['id']=='ED-03':assert {'ED03/running-0620','ED03/running-0840','ED03/unapplied-stage','ED03/up-0817','ED03/down-0943','ED03/description-event'}<=ids
        if case['id'] in ['ED-05','ED-06']:assert ids=={'ED05/collector-a','ED05/review-b'}
        source={'case':case['id'],'rows':rows,'evidence':[e.model_dump(mode='json') for e in evidence],'receipts':tools.requests,'oracle':oracle,'inference_calls':0}
        with (target/'source-proof.json').open('x',encoding='utf-8') as f:json.dump(source,f,indent=2)
        proof.append({'case':case['id'],'scenario_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'source_proof_sha256':hashlib.sha256((target/'source-proof.json').read_bytes()).hexdigest()})
    spec={'version':1,'at':datetime.now(timezone.utc).isoformat(),'freeze_before_inference':True,'hard_cloud_attempt_limit':32,
      'method':'New source-derived independently checkable expectations; implementation-assistant graded, not blinded/external. Grading key never included in runtime prompts.',
      'arms':['control','enhanced'],'comparison':'Integrated completeness profile, not isolated mechanism or identical-evidence model comparison.',
      'order':'Registry order, alternating control/enhanced; stop all cloud cells on first provider failure.','fixtures':{c['id']:c['scenario'] for c in cases},
      'cases':[{**c,'scenario':c['id']} for c in cases],
      'settings':{'local':'qwen2.5:1.5b','planner':'gemini-3.1-flash-lite','reasoner':'gemini-3.5-flash-lite','thinking':'low','layout':'current','wire':'full','approach_a':False},
      'allocation':{'availability':1,'paired':26,'browser':5},'rubric':['workflow','material_evidence','identity','causal_correctness','temporal_limits','complete_outcomes','source_authority','release_safety']}
    with SPEC.open('x',encoding='utf-8') as f:json.dump(spec,f,indent=2)
    with (AUDIT/'independent-freeze-receipt.json').open('x',encoding='utf-8') as f:json.dump({'registry_sha256':hashlib.sha256(SPEC.read_bytes()).hexdigest(),'cases':proof,'cloud_calls':0,'actual_registered_oracles_passed':True},f,indent=2)
    print(json.dumps({'cases':len(cases),'oracles':'PASS','sha256':hashlib.sha256(SPEC.read_bytes()).hexdigest(),'cloud':0}))

if __name__=='__main__':asyncio.run(freeze())
