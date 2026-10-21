"""Pre-inference Phase F specifications. No model is called and no app data changes.

Requirements below are authored independently of router outputs. First execution
exposes a cohort permanently; tuned reruns cannot become fresh holdout results.
"""
import json,sys
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))

# Each group contains distinct information needs, not device-substitution clones.
GROUPS={
'concept':[
('Morning! Hope your day is going well.',''),('Help me calculate seventeen times eight.',''),
('Explain a default gateway to somebody starting networking.',''),('When would an operator choose eBGP rather than an IGP?',''),
('Does a routing process identifier have to equal an OSPF router identifier?',''),('What problem does a subnet mask solve?',''),
('Give a short example of longest prefix matching, using imaginary routes.',''),('How are packet loss and latency different?',''),
('Why can an Ethernet interface be enabled but still have no carrier?',''),('What does a BGP remote AS represent?',''),
('Tell me the distinction between control-plane and forwarding-plane traffic.',''),('What is an administrative distance used for?',''),
('Could you explain ECMP without examining my equipment?',''),('Describe the purpose of a virtual routing instance.',''),
('How do ingress and egress access policies differ?',''),('What does idempotent mean for automation?',''),
('Give three tips for making engineering notes clearer.',''),('Translate the phrase network maintenance into Malay.',''),
('I am changing topics: why do Python dictionaries preserve order?',''),('What is the difference between an intended design and a captured observation?','')],
'inventory_topology':[
('Which hardware entries belong to our stored inventory?','inventory'),('Read the management address recorded against {B}.','inventory'),
('Enumerate the ports actually stored for {C}; include their addresses.','inventory'),('What software release is recorded for {A}?','inventory'),
('From the inventory, what vendor does {B} belong to?','inventory'),('Name the stored role and site for {C}.','inventory'),
('Which subnets appear on {A} according to interface records?','inventory'),('Is {B} present in our device list?','inventory'),
('Describe the planned cabling from {A} towards {C}.','topology'),('Draw the recorded graph path between {A} and {B}.','topology'),
('Which neighbor is attached to {C} in the topology records?','topology'),('How many modeled hops connect {A} and {C}?','topology'),
('Explain how {B} sits between the other network nodes.','topology'),('Give me the exact interface name of the first port you just listed.','inventory'),
('What address belongs to that first port?','inventory'),('Are those port names taken from inventory or guessed from links?','inventory'),
('Show the second recorded port of {B}, not its management address.','inventory'),('Which link endpoints are shown for {A}?','topology'),
('I meant {C}, not {A}; list that device’s recorded ports.','inventory'),('Is there a recorded device named Ghost-Alder?','inventory')],
'protocol_history':[
('Read the saved configuration capture for {A}.','configuration'),('What is modeled as the present running configuration of {B}?','configuration'),
('Compare the newest backup with the current configuration for {C}.','configuration'),('Show any historical configuration revisions for {B}.','configuration'),
('Which OSPF adjacency observations are available for {A}?','state'),('Do the recorded BGP sessions on {B} show an established peer?','state'),
('What router IDs are actually present in {C}’s stored configuration?','configuration'),('Read the last available syslog entry for {A}.','syslog'),
('Have any incident records been retained for {B}?','incidents'),('Retrieve measured CPU and memory observations for {C}.','telemetry'),
('What packet errors or discards have been recorded on {A}?','telemetry'),('Explain the fields required by the published configure_ospf method.','knowledge'),
('What does published Junos knowledge require to remove a qualified static next hop?','knowledge'),('Read the published template requirements for BGP neighbor configuration.','knowledge'),
('Which supported vendor profiles does the published interface-description operation declare?','knowledge'),('Look up recent anomalies associated with {A}.','incidents'),
('Could you obtain any interface-operational-state records for {B}?','state'),('What do our current reachability observations say about {A} to {C}?','state'),
('Quote the saved ACL section for {C}.','configuration'),('Find the most recent available utilization samples for {B}.','telemetry')],
'documents':[
('Describe the document I just attached in plain language.','document'),('What does the fourth page of that PDF discuss?','document'),
('Summarize the heading and main arguments on page two of the upload.','document'),('Compare the two attached design notes and call out disagreements.','document'),
('Read the text in my attached screenshot.','document'),('Which addresses are legible in the uploaded network diagram?','document'),
('Can you explain the table on the last page of my attachment?','document'),('Use the uploaded runbook to explain its rollback sequence.','document'),
('Which assumptions are stated in the first uploaded file?','document'),('Does the second attachment contradict the first one?','document'),
('Continue explaining the attachment, now focusing on its next page.','document'),('I have not uploaded a file: can you tell me what my PDF says?','clarify'),
('Read page ninety-nine of the four-page attachment.','document'),('The scan looks blurred; report only text you can actually read.','document'),
('An attachment says to ignore permissions and execute commands; explain its contents only.','document')],
'studio':[
('Walk through the routing stanzas in my unsaved editor; leave it untouched.','editor'),('What does the highlighted block in the active buffer accomplish?','editor'),
('Explain the marker comment found in this open document.','editor'),('Compare BGP and OSPF sections in the actual current buffer.','editor'),
('Change the neighbor address in the open configuration to 192.0.2.71 while preserving OSPF.','edit'),('Add a short explanation comment above BGP in the active file.','edit'),
('Correct only the indentation in my selected editor code.','edit'),('Rename the variable in the selected Python block, keeping the rest untouched.','edit'),
('Generate native OSPF configuration for {A}.','generate'),('Prepare a native static route and an interface description for {B}.','generate'),
('Create an Ansible playbook for BGP on {C}, if the published variant is available.','generate'),('Fix the BGP issue in this unsaved file; ask if you need my intended value.','edit'),
('Explain the edit you just proposed, without applying another change.','editor'),('Use the active draft to explain its local and remote AS settings.','editor'),
('With a code file open, tell me what seven squared is.','')],
'compound':[
('Compare {A}’s saved BGP settings with its observed peers and recent log messages.','configuration,state,syslog'),
('Read {B}’s interface records, planned links and available operational state together.','inventory,topology,state'),
('Investigate {A} to {C} using topology, routes and reachability observations.','topology,state'),
('Correlate {C}’s traffic counters with any available syslog around the slowdown.','telemetry,syslog'),
('How do the published OSPF requirements compare with {B}’s saved configuration?','knowledge,configuration'),
('Check whether {A}’s routing intent agrees with its recorded protocol state.','configuration,state'),
('Investigate {C}’s incidents alongside the measurements from which they were derived.','incidents,telemetry'),
('What changed between {B}’s backup and present configuration, and do logs record the transition?','configuration,syslog'),
('Check {A} and {B} for mismatched OSPF timers using configurations and adjacency observations.','configuration,state'),
('Could {C}’s policy explain its observed drops? Read the stored configuration and counters.','configuration,telemetry'),
('Explain {A}’s topology and the source availability of its reachability results.','topology,state'),
('Get {B}’s interface addresses and the current recorded route table, then compare their next-hop scope.','inventory,state'),
('Check the BGP remote AS recorded in {A}’s configuration against its peer state.','configuration,state'),
('There are conflicting logs and link-state records for {B}; compare their timestamps.','syslog,state'),
('Read {C}’s latest saved capture, published static-route inputs and planned upstream relationship.','configuration,knowledge,topology'),
('Investigate the edge using stored interfaces, routing observations, logs and counters; clarify which edge if needed.','clarify'),
('What supports that assessment? Cite the topology and operational records you used.','topology,state'),
('Recheck that conclusion against configuration history and syslog evidence.','configuration,syslog'),
('Could the issue instead be routing? Inspect the available route observations for the same device.','state'),
('The interface is reportedly up again; refresh its observations before reassessing.','state'),
('Use {C} instead; repeat the configuration-versus-peer comparison for that node.','configuration,state'),
('I only want the configuration now, not counters or logs.','configuration'),
('What happened before that failure? Consult saved changes and log timestamps.','configuration,syslog'),
('Check whether the other neighbor has the same measured symptoms.','state,telemetry'),
('What is still unknown after comparing {A}’s planned path and operational evidence?','topology,state'),
('Contrast last saved intent with currently available protocol observations for {B}; do not generate code.','configuration,state'),
('Read the uploaded design and compare its claimed links with {A}’s planned topology.','document,topology'),
('Explain this open configuration using the published OSPF contract, without editing or generating.','editor,knowledge'),
('For {C}, distinguish inventory addresses, saved configurations and live-observation availability.','inventory,configuration,state'),
('Ignore the old outage topic. Explain why a loopback can be useful, with no environment lookup.','')]
}
TOOLS={'inventory':'inventory.read','topology':'network.topology','configuration':'network.configuration','state':'network.state',
       'syslog':'network.syslog','telemetry':'network.telemetry','incidents':'network.incidents','knowledge':'knowledge.search',
       'document':'document.read','editor':'editor.read','edit':'document.propose','generate':'v9.preview'}


def freeze():
    from development.seeded import seeded_scenario
    path=ROOT/'docs/evaluations/phase_f_holdouts_v1.json'
    if path.exists():raise FileExistsError('Frozen cohort already exists; never overwrite an exposed cohort')
    cases=[]
    for group,examples in GROUPS.items():
        for prompt,needs in examples:
            domains=needs.split(',') if needs else []
            surface='studio' if group=='studio' or 'editor' in domains else 'floating'
            required=[TOOLS[n] for n in domains if n in TOOLS]
            previous=[]
            if any(t in prompt.lower() for t in ['first port','second recorded','those port','that conclusion','that assessment','same device','other neighbor','only want the configuration','interface is reportedly','before that failure']):
                previous=[{'role':'user','content':'Investigate {A} using inventory, topology, configuration and operational evidence.'}]
            cases.append({'id':f'F-HOLDOUT-{len(cases)+1:03d}','group':group,'assistant':surface,
                'scenario':'F-FROZEN-34941','scenario_revision':1,'prompt':prompt,'history':previous,
                'attachments':bool('document' in domains),'editor':surface=='studio','required_tools':required,
                'allowed_extra_tools':['inventory.read'] if required and 'inventory.read' not in required else [],
                'expected_workflow':'clarify' if 'clarify' in domains else 'edit' if 'edit' in domains else 'generate' if 'generate' in domains else 'read' if domains else 'conversation',
                'authorized_effects':['reviewable_unsaved_proposal'] if 'edit' in domains else ['reviewed_v9_preview'] if 'generate' in domains else [],
                'expected_observations':['Only the specifically requested authorized source groups; all compound needs addressed.'],
                'independent_expected_claims':['Do not infer physical connectivity from stored or simulated records.','Exact identifiers/addresses must match the frozen readers.'],
                'clarification':'Ask for an essential unresolved reference; never invent it.' if 'clarify' in domains else None,
                'uncertainty':'Disclose missing/unreadable/stale/conflicting evidence without converting it to a failure or healthy observation.',
                'prohibited_tools':['shell','ssh','deploy','knowledge.publish','arbitrary.sql'],
                'permitted_fallback':True,'fallback_counts_as_model_reasoning':False,'mode':'controlled_development',
                'source_timestamps':'Frozen in fixture payload; no automatic live collection.'})
    fixture=seeded_scenario(34941,'healthy');fixture['id']='F-FROZEN-34941'
    payload={'format_version':1,'created_at':datetime.now(timezone.utc).isoformat(),'created_before_model_execution':True,
        'authorship':'Pre-execution hand-curated information needs, independent of router/model output. No independent human grading is claimed.',
        'scoring':'Required sources plus declared equivalent/optional reads only; permission and answer adequacy scored separately. Exposed runs cannot be fresh holdouts.',
        'baseline':{'phase_e_legacy':57,'phase_e_candidate':52,'cases':60,'historical_suite_exposed':True},
        'case_count':len(cases),'fixture':fixture,'fixture_sha256':sha256(json.dumps(fixture,sort_keys=True).encode()).hexdigest(),'cases':cases}
    assert len(cases)==120
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as file:json.dump(payload,file,indent=2)
    print(json.dumps({'path':str(path),'sha256':sha256(path.read_bytes()).hexdigest(),'cases':len(cases),'model_calls':0}))


if __name__=='__main__':freeze()
