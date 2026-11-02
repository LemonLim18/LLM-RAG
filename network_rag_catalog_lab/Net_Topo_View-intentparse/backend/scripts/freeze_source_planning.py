"""Freeze source-derived planning conditions using the existing scenario/readers."""
import asyncio,copy,hashlib,json,os,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];AUDIT=ROOT/'tmp/phase-g/iterations/20261101-source-planning-repair'
SPEC=ROOT/'docs/evaluations/phase_g_source_planning_v1.json'
DB=ROOT/'tmp/phase-g/iterations/20261101-audit-grounded-repair/evaluation-app.db'
sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'backend/scripts')]
from freeze_af_integrated import base,rec,materialize

def build():
 cases=[]
 def add(s,prompt,queries,outcomes,prohibited,surface,profile='control',setup=None):
  s['id']='SP-'+str(len(cases)+1).zfill(2);s['title']='Independent source-planning condition '+s['id'];s['logical_time']='2026-11-01T13:00:00Z'
  materialize(s)
  cases.append(dict(id=s['id'],scenario=s,prompt=prompt,surface=surface,profile=profile,setup=setup,
    source_validation_queries=[{'domain':d,'parameters':p} for d,p in queries],expected_outcomes=outcomes,prohibited_outputs=prohibited))
 s=base(51,network=False);s['records']['running_configuration']=[rec('SP01/running-0900',631,'running_configuration',{'config_text':'interface GigabitEthernet2/0/4\n description PRE-MAINT\n no shutdown\n'},6311,stamp='2026-11-01T09:00:00Z',current=False),
 rec('SP01/running-1120',631,'running_configuration',{'config_text':'interface GigabitEthernet2/0/4\n description POST-MAINT\n no shutdown\n'},6311,stamp='2026-11-01T11:20:00Z')]
 s['records']['configuration']=[rec('SP01/unapplied',631,'configuration_snapshot',{'config_text':'interface GigabitEthernet2/0/4\n description DRAFT-ONLY\n shutdown\n','applied':False},6311,stamp='2026-11-01T10:15:00Z',current=False)]
 s['records']['state']=[rec('SP01/up-0940',631,'interface_state',{'admin_status':'up','oper_status':'up'},6311,stamp='2026-11-01T09:40:00Z',current=False),rec('SP01/down-1205',631,'interface_state',{'admin_status':'up','oper_status':'down'},6311,stamp='2026-11-01T12:05:00Z')]
 s['records']['syslog']=[rec('SP01/logging-event',631,'configuration_event',{'message':'logging buffered 32000 applied; no interface administrative change recorded','command':'logging buffered 32000'},stamp='2026-11-01T11:50:00Z')]
 add(s,'Compare Alder historical running snapshots, current running configuration and its unapplied staged artifact for GigabitEthernet2/0/4. Explain which description and administrative-command changes are actually recorded, the operational observation interval and what the11:50event establishes. Can you establish the exact running description at10:45 or the cause of the link-state change? Read configuration, recorded state and syslog only; do not read other sources.',
 [('configuration',{'device_refs':['631'],'source_scope':'both'}),('state',{'device_refs':['631'],'source_scope':'both'}),('syslog',{'device_refs':['631']})],
 ['Running PRE-MAINT09:00→POST-MAINT11:20; no shutdown in both.','DRAFT-ONLY/shutdown is unapplied staged10:15, not active or an applied event.','AdminUP/operUP09:40 and adminUP/operDOWN12:05 bracket observations only; exact change time and cause unknown.','11:50event records logging buffered32000, not interface activation or cause. Exact running description10:45 is not established.'],
 ['Staged shutdown asserted applied','Point-in-time interval turned into exact transition','Logging change asserted causal'], 'floating')
 s=base(52,vrf='tenant-green');s['network']['tables'][-1]['routes']=[]
 s['devices'].append(dict(id=975,hostname='BirchArchive',management_ip='192.0.2.205',vendor='cisco_xe',os_version='17.9',role='archive',site='isolated-background'))
 s['interfaces'].append(dict(id=9751,device_id=975,name='GigabitEthernet2/0/4',prefix='192.0.2.205/32',vrf='tenant-green',admin_status='up',oper_status='up'))
 add(s,'BirchArchive supplied the old report. Investigate Alder-to-Prism modeled HTTPS delivery in tenant-green. Explain forward versus return results, the device where return forwarding stops and the owned ingress/egress interfaces traversed. Does route presence on Alder establish successful bidirectional forwarding? Explain protocol and physical-measurement limitations. Read recorded state and topology only; do not read other sources.',
 [('state',{'device_refs':['631','964']}),('topology',{'device_refs':['631','964'],'source_scope':'both'})],
 ['Targets631/964; BirchArchive975 is background, never executable target.','Forward delivered; return fails at origin Prism964 with no route in complete tenant-green table; no return transit traversal.','Forward Grit ingress7421 egress7422; Opal ingress8531 egress8532; destinationPrism ingress9641.','Route presence on Alder does not establish return delivery; modeled stateless forwarding is neither physical test nor BGP/OSPF health.'],
 ['BirchArchive read as target','Return failure placed at transit device','Unknown physical fault or protocol session invented'], 'studio')
 s=base(53,network=False)
 s['records']['running_configuration']=[rec('SP03/current-label',631,'running_configuration',{'config_text':'interface GigabitEthernet2/0/4\n description OLD-TAG\n no shutdown\n','change_event_ref':'SP03/label-request'},6311)]
 logs=[rec('SP03/heartbeat-'+str(i),631,'log_event',{'message':'Recorder heartbeat '+str(i)},stamp=f'2026-11-01T12:{i:02d}:00Z') for i in range(20)]
 logs += [rec('SP03/label-request',631,'configuration_event',{'message':'A label replacement is proposed to align circuit identifiers with asset-map release Q17. No command application, cable move or service restoration is measured.'},6311,stamp='2026-11-01T06:05:00Z',depends=['SP03/asset-ledger']),rec('SP03/asset-ledger',631,'log_event',{'message':'Asset-map release Q17 assigns circuit tag METRO-712 to this recorded port; this is a registry assignment, not a packet or physical verification.'},6311,stamp='2026-11-01T06:00:00Z')]
 s['records']['syslog']=logs
 add(s,'Investigate Alder current interface-description record and follow its source-owned change reference. Explain the proposed label purpose and exact assigned circuit tag. Does this establish command application, a physical cable move or restored forwarding? Use configuration and syslog only; do not read other sources or perform collection or engineering actions.',
 [('configuration',{'device_refs':['631'],'source_scope':'current'}),('syslog',{'device_refs':['631'],'limit':8}),('syslog',{'device_refs':['631'],'limit':100})],
 ['Initial8logs omit linked records; authorized larger read finds SP03/label-request and SP03/asset-ledger.','Proposed alignment with asset-map Q17, assigned tagMETRO-712; current config still OLD-TAG.','No command application, physical cable move or restored forwarding is established; exact linked records reach actual revised model input.'],
 ['Source found only in graph not model input','Proposed tag called active','Physical/forwarding restoration asserted'], 'studio','enhanced')
 s=copy.deepcopy(cases[0]['scenario'])
 add(s,'Using our earlier Alder interface context, recommend two different passive evidence checks that distinguish configured administrative intent from operational failure. Explain one limitation for each. Do not read, collect, test, modify or generate anything.',[],
 ['Zero new reader execution; owned prior interface6311 context retained.','Useful distinct passive configuration/admin-history and operational-event/counter recommendations; explicit limitations, not current observations.'],
 ['Any new reader','Advice stated as completed collection or verified diagnosis'],'floating',setup='Using recorded state only, show Alder GigabitEthernet2/0/4 administrative and operational states. Do not read other sources.')
 return cases

async def freeze():
 os.environ.update(COGNISHIELD_MODE='local_lab',COGNISHIELD_DB_PATH=str(DB),COGNISHIELD_DEV_SIMULATION='1',COGNISHIELD_AI_COMPLETENESS='1',COGNISHIELD_AI_OUTCOMES='0',COGNISHIELD_AI_EVIDENCE_HARNESS='0')
 import lab_config
 assert Path(lab_config.DB_PATH).resolve()==DB.resolve()
 from db.manager import DatabaseManager
 from llm.gateway_store import ConversationStore,ensure_schema
 from llm.gateway_services import registry_for
 from llm.gateway_network import network_context,READ_TOOLS
 from llm.orchestration.adapters import AuthorizedTools
 from llm.tools import ToolAuthorization
 from local_providers.development import Scenario,ScenarioManager
 from llm.orchestration.investigation_support import walk
 from development.network_model import Flow,assess_flow
 db=DatabaseManager(str(DB));db.initialize();ensure_schema(db);store=ConversationStore(db);cases=build();proof=[]
 for case in cases:
  case['scenario']=Scenario.model_validate(case['scenario']).model_dump(mode='json')
  target=AUDIT/'frozen-sources'/case['id'];target.mkdir(parents=True,exist_ok=False)
  path=AUDIT/'scenarios'/(case['id']+'.json');path.parent.mkdir(exist_ok=True)
  manager=ScenarioManager(path);manager.change('import',manager.snapshot()[1]['source_revision'],case['scenario']);db._development_scenario=manager
  cid=store.create('planning-oracle',case['surface'])['id'];auth=ToolAuthorization('planning-oracle','admin',case['surface'],cid,READ_TOOLS)
  tools=AuthorizedTools(registry_for(db),store,auth,max_calls=8);rows=[]
  for query in case['source_validation_queries']:
   domain=query['domain'];params={'live':False,**query['parameters']}
   r,_,_=await network_context(db,tools,auth,case['prompt'],domains_override=[domain],device_refs_override=params['device_refs'],validated_parameters={domain:params});rows+=r
  ids={r['id'] for row in rows for _,r in walk(row.get('data'))}
  if case['id']=='SP-01':assert {'SP01/running-0900','SP01/running-1120','SP01/unapplied','SP01/up-0940','SP01/down-1205','SP01/logging-event'}<=ids
  if case['id']=='SP-02':
   flow=assess_flow(case['scenario'],Flow.model_validate(case['scenario']['network']['flows'][0]));assert flow['forward']['status']=='delivered' and flow['return']['status']=='failed';assert flow['return']['branches'][0]['failure_location']['device_id']==964
   assert 'BirchArchive' not in json.dumps([row['data'] for row in rows]),'Original instruction in receipts is not a returned background device'
  if case['id']=='SP-03':
   events=[r for r in rows if r['tool']=='network.syslog'];assert 'SP03/label-request' not in json.dumps(events[0]);assert {'SP03/label-request','SP03/asset-ledger'}<=ids
  source={'case':case['id'],'rows':rows,'receipts':tools.requests,'inference_calls':0}
  (target/'source-proof.json').write_text(json.dumps(source,indent=2),encoding='utf-8')
  proof.append({'case':case['id'],'scenario_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'source_proof_sha256':hashlib.sha256((target/'source-proof.json').read_bytes()).hexdigest()})
 spec={'version':1,'at':datetime.now(timezone.utc).isoformat(),'freeze_before_inference':True,'hard_cloud_attempt_limit':20,'method':'Source-derived independently checkable, implementation-assistant graded, not blinded. Ground truths never supplied to model.',
  'comparison':'Repaired runtime; frozen preimage deterministic control, not an unmodified live paired model cohort. Profiles differ explicitly per case.',
  'fixtures':{c['id']:c['scenario'] for c in cases},'cases':[{**c,'scenario':c['id']} for c in cases]}
 with SPEC.open('x',encoding='utf-8') as f:json.dump(spec,f,indent=2)
 with (AUDIT/'independent-freeze-receipt.json').open('x',encoding='utf-8') as f:json.dump({'registry_sha256':hashlib.sha256(SPEC.read_bytes()).hexdigest(),'cases':proof,'cloud_calls':0},f,indent=2)
 print(json.dumps({'cases':len(cases),'oracles':'PASS','cloud_calls':0}))

if __name__=='__main__':asyncio.run(freeze())
