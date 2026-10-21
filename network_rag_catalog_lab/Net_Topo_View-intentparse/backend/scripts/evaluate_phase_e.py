"""Frozen source-selection evaluation, reusing the gateway and model adapter.

No shared scenario file changes, network collection or ordinary DB writes.
Routing scores are not answer adequacy or evidence of native model tool calls.
"""
import argparse,asyncio,json,os,sys,time
from pathlib import Path
from hashlib import sha256
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
SPEC=ROOT/'docs/evaluations/phase_e_holdouts_v1.json'


def create():
    rows=[]
    def add(group,prompts,tools,assistant='floating',documents=False):
        for prompt in prompts:
            rows.append(dict(id=f'E-HOLDOUT-{len(rows)+1:03d}',group=group,prompt=prompt,assistant=assistant,attachments=documents,
                required_tools=tools,allowed_extra_tools=['inventory.read'] if tools and 'inventory.read' not in tools else [],
                prohibited=['unrequested write effect','fabricated source facts','unrelated old context']))
    add('conversation',['Hi there!','What is 19 plus 24?','Explain binary versus hexadecimal.','How does TCP acknowledge data?','Why use version control?','What does idempotent mean?','Explain DNS caching.','How do a list and a set differ in Python?','What is a subnet mask in general?','How do OSPF and BGP differ conceptually?'],[])
    add('inventory',['Which interfaces are recorded on {B}?','Tell me the management address of {A}.','List the vendors of the recorded devices.','Which addresses belong to interfaces on {C}?','How many interfaces are recorded for {B}?','What software version is recorded for {A}?','What is the recorded role of {C}?','Which site contains {B}?'],['inventory.read'])
    add('topology',['Describe the planned topology between {A} and {B}.','Show the recorded network path from {A} to {C}.','Which recorded links touch {B}?','Explain the planned connection between {B} and {C}.'],['network.topology'])
    add('configuration',['Read the saved configuration for {C}.','Show the latest stored backup of {B}.','Compare {A} current configuration with its saved snapshot.','What running configuration is available for {B}?','Retrieve configuration history for {A}.','List the recorded configuration captures for {C}.'],['network.configuration'])
    add('operational',['Which recent syslogs exist for {B}?','Get the latest available log from {A}.'],['network.syslog'])
    add('operational',['Read available CPU measurements for {C}.','What interface traffic is recorded on {B}?'],['network.telemetry'])
    add('operational',['What incident records concern {C}?','Show recorded alerts on {A}.'],['network.incidents'])
    add('protocol',['Does {A} have a recorded OSPF adjacency with {B}?','What BGP peer session state is recorded for {C}?'],['network.state'])
    add('documents',['What does page 4 of this PDF explain?','Summarize the attached design document.','Can you read the contents of this uploaded file?','What text is visible in the attached screenshot?','Explain the diagram in the uploaded PDF.','What limitations are stated on page 2?'],['document.read'],documents=True)
    add('published',['Explain the published OSPF operation parameter requirements.','Which inputs does the catalog require for a BGP operation?'],['knowledge.search'])
    add('editor',['Explain the actual unsaved configuration without changing it.','Describe the BGP section in the open file.'],['editor.read'],'studio')
    add('editor',['Replace the BGP neighbor address in the active file with 192.0.2.44; retain OSPF.','Change the router ID in the selected OSPF section of my open buffer.','Add a comment to the current code explaining the neighbor statement.','Correct the description in the open template.'],['document.propose'],'studio')
    add('generation',['Generate new native OSPF configuration on {A}.','Create a static-route configuration on {C} to 203.0.113.0/24 via 192.0.2.2.','Configure BGP on {B} using local AS 65020 and remote AS 65030.','Generate interface description Uplink on {A} GigabitEthernet0/1.','Create native QoS policing configuration on {C}; ask for missing rate values.','Generate native configuration combining OSPF and static routing on {A}.'],['v9.preview'],'studio')
    add('compound',['Check {B} current configuration and its BGP peer session state.','Read available syslogs and current configuration for {A}.'],[], 'floating')
    rows[-2]['required_tools']=['network.configuration','network.state'];rows[-1]['required_tools']=['network.configuration','network.syslog']
    add('compound',['Compare published OSPF operation requirements with {B} stored configuration.','Explain the catalog BGP parameter requirements alongside {C} saved configuration.'],['knowledge.search','network.configuration'])
    assert len(rows)==60
    value={'format_version':1,'scope':'60 single-turn source/workflow routing holdouts. No content-answer, permission-effect or native-tool-call certification is inferred.',
        'created_before_execution':True,'scoring':'All required tools and only declared optional identity inventory; no tuning during first execution. Each run exposes its cases for future use as regressions. Multi-turn actual-agent cases remain separate.',
        'routing_target':.90,'seed':2027,'cases':rows}
    with SPEC.open('x',encoding='utf-8') as f:json.dump(value,f,indent=2)
    print(json.dumps({'created':str(SPEC),'cases':60,'sha256':sha256(SPEC.read_bytes()).hexdigest()}))


async def evaluate(args):
    from scripts.phase_d_audit import Run,source_manifest,digest
    from development.seeded import seeded_scenario
    from local_providers.development import Scenario
    from llm.gateway_routing import select_context
    from llm.gateway_models import EditorSnapshot
    from llm.orchestration.model import RoutingModel
    spec=json.loads(SPEC.read_text(encoding='utf-8'))
    scenario=Scenario.model_validate(seeded_scenario(spec['seed'])).model_dump()
    inventory={'devices':[{**d,'interfaces':[i for i in scenario['interfaces'] if i['device_id']==d['id']]} for d in scenario['devices']]}
    names=dict(zip('ABC',[d['hostname'] for d in inventory['devices']]))
    os.environ['COGNISHIELD_AI_PLANNING']='1' if args.engine=='candidate' else '0'
    run=Run(('F3-exposed-regressions-' if args.phase=='phase-f' else 'E6-holdouts-')+args.engine,'real_model_direct',{'model':'qwen2.5:1.5b','spec_sha256':sha256(SPEC.read_bytes()).hexdigest(),'scenario_id':scenario['id'],'scenario_sha256':digest(json.dumps(scenario,sort_keys=True).encode()),'source_digest':digest(json.dumps(source_manifest(),sort_keys=True).encode()),'cohort':'exposed_phase_e_regression' if args.phase=='phase-f' else 'phase_e_original_cohort'},phase=args.phase)
    passed=0
    for row in spec['cases'][args.offset:args.offset+args.limit]:
        prompt=row['prompt'].format(**names);model=RoutingModel();captured=[];started=time.monotonic()
        async def generate(*a,**kw):
            answer=await model.generate(*a,**kw);captured.append({'purpose':kw.get('purpose','routing'),'output':answer[0]});return answer
        editor=EditorSnapshot(document_id='holdout',path='playbooks/drafts/holdout.cfg',content='router ospf 20\n router-id 198.19.27.1\nrouter bgp 65020\n neighbor 192.0.2.2 remote-as 65030\n! KEEP\n',language='network-config',model_id='holdout',model_version=1,buffer_epoch=1,saved_revision=0,is_dirty=True,read_only=False) if row['assistant']=='studio' else None
        attachments=[{'id':'00000000-0000-4000-8000-000000000001','name':'unfamiliar-design.pdf'}] if row['attachments'] else []
        try:
            route=await select_context(prompt,'qwen2.5:1.5b',row['assistant'],editor,attachments,[],inventory=inventory,generate_fn=generate)
            selected={'inventory.read' if d=='inventory' else 'knowledge.search' if d=='knowledge' else 'network.'+d for d in route.network_domains}
            if route.use_attachments:selected.add('document.read')
            if route.use_editor and route.intent!='edit':selected.add('editor.read')
            if route.intent=='edit':selected.add('document.propose')
            if route.intent.startswith('generate_'):selected.add('v9.preview')
            required=set(row['required_tools']);ok=required<=selected<=required|set(row['allowed_extra_tools'])
            actual={'route':route.model_dump(),'selected_tools':sorted(selected),'raw_model_outputs':captured}
        except Exception as exc:ok=False;actual={'error':str(exc),'raw_model_outputs':captured}
        passed+=ok
        run.record(row['id'],'PASS' if ok else 'FAIL',expected={'required_tools':row['required_tools'],'allowed_extra_tools':row['allowed_extra_tools'],'scope':'Source/workflow selection only'},actual=actual,prompt=prompt,model='qwen2.5:1.5b',model_calls=model.calls,latency_ms=round((time.monotonic()-started)*1000,2),classification=None if ok else 'source_or_workflow_selection')
        print(json.dumps({'case':row['id'],'outcome':'PASS' if ok else 'FAIL','model_calls':model.calls}),flush=True)
    print(json.dumps({'run':str(run.path),'source_selection_pass':passed,'cases':len(spec['cases'][args.offset:args.offset+args.limit]),'answer_adequacy':'NOT_RUN','defaults_changed':False}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--create',action='store_true');p.add_argument('--engine',choices=['legacy','candidate'],default='candidate');p.add_argument('--phase',choices=['phase-e','phase-f'],default='phase-e');p.add_argument('--offset',type=int,default=0);p.add_argument('--limit',type=int,default=60)
    args=p.parse_args()
    if args.create:create()
    else:asyncio.run(evaluate(args))
