"""Projection fidelity and constrained citations; mocked tests are not LLM scores."""
import asyncio
import json
import sys
import pytest
from pathlib import Path

from jsonschema import Draft202012Validator

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from llm.gateway_models import Evidence
from llm.orchestration.synthesis import projection, synthesize, check_candidate


def test_partial_source_failure_cannot_be_synthesized_as_a_successful_comparison():
    context,evidence=ospf_material()
    context.append({'tool':'network.syslog','status':'unavailable','evidence_ids':['logs'],
        'data':{'records':[],'source_available':False},'message':'Scenario source is explicitly unavailable'})
    evidence.append(Evidence(id='logs',source='Syslog reader',origin='simulated'))
    question='Compare Oak-Edge’s saved BGP settings with observed peers and recent log messages.'
    bad='Oak-Edge’s saved BGP settings match its observed peers and recent log messages. [S1]'
    errors=check_candidate(bad,context,evidence,{},question)
    assert any('unavailable' in item.lower() for item in errors)
    assert check_candidate('The logs are unavailable, so the saved settings and BGP peers match. [S1] [S2]',context,evidence,{},question)
    assert check_candidate('Saved BGP settings were not available due to syslog being unavailable. Observed BGP peers and log messages were not provided as the protocol was not found in the configuration capture. [S1] [S2]',context,evidence,{},question)
    assert check_candidate('Saved BGP settings do not match the observed peers or logs. Syslog is unavailable. [S1] [S2]',context,evidence,{},question)
    good='I cannot complete the comparison: saved configuration was not retrieved, no BGP peer observations were returned, and syslog is unavailable. [S1] [S2]'
    assert not check_candidate(good,context,evidence,{},question)


def test_protocol_comparison_projects_each_requested_source_without_unrelated_ospf():
    from llm.orchestration.synthesis import protocol_comparison_material
    context,evidence=ospf_material()
    context.extend([
        {'tool':'network.configuration','status':'success','evidence_ids':['config'],'data':{'records':[
            {'hostname':'Oak-Edge','timestamp':'2026-10-18T01:00:00Z','current':False,'config_text':'router ospf 20\n router-id 203.0.113.1\n'}]}},
        {'tool':'network.syslog','status':'unavailable','evidence_ids':['logs'],'data':{'records':[]}}])
    evidence.extend([Evidence(id='config',source='Saved configuration',origin='simulated'),Evidence(id='logs',source='Syslog',origin='simulated')])
    bad='The configuration reader retrieved the current configuration, but no BGP section marker was found in the log records. No BGP peers were returned and syslog is unavailable. [S1] [S2] [S3]'
    assert check_candidate(bad,context,evidence,{},'Compare saved BGP settings with observed peers and recent log messages.')
    packet=json.dumps(protocol_comparison_material(context,'Compare saved BGP settings with observed peers and recent log messages.',evidence))
    assert 'router ospf' not in packet and '203.0.113.2' not in packet
    assert all(tool in packet for tool in ['network.configuration','network.state','network.syslog'])
    class Model:
        async def generate(self,messages,**kwargs):
            raise AssertionError('Missing protocol section/peer data cannot authorize a synthesized comparison verdict')
    answer,report=asyncio.run(synthesize(Model(),'test','Compare Oak-Edge saved BGP settings with observed peers and recent log messages.',context,evidence,{},'unsafe raw fallback'))
    assert report['status']=='insufficient_evidence_fallback',report
    assert 'router ospf' not in answer and 'cannot establish' in answer


def test_joint_interface_reads_use_relevant_records_and_a_prose_fallback():
    evidence=[Evidence(id=key,source=key,origin='simulated') for key in ['inventory','links','state']]
    context=[{'tool':'inventory.read','status':'success','evidence_ids':['inventory'],'data':{'devices':[
        {'id':2,'hostname':'Birch','engineering_facts':{'unrelated':'DO_NOT_SEND'},'interfaces':[
            {'id':3,'name':'ge-0/0/0.0','ip_address':'10.1.0.2','subnet_mask':'255.255.255.252'}]}]}},
        {'tool':'network.topology','status':'success','evidence_ids':['links'],'data':{'topology_kind':'planned','links':[
            {'source':'Oak','source_interface':'Gi0/1','target':'Birch','target_interface':'ge-0/0/0.0'}]}},
        {'tool':'network.state','status':'success','evidence_ids':['state'],'data':{'records':[
            {'kind':'interface_state','hostname':'Birch','interface':'ge-0/0/0.0','admin_status':'up','oper_status':'up','current':True,'timestamp':'2026-10-18T01:00:00Z'},
            {'kind':'routing_table','routes':[{'prefix':'UNRELATED_ROUTE'}]}]}}]
    class Model:
        async def generate(self,messages,**kwargs):
            packet=messages[-1]['content']
            assert 'untrusted_interface_sources' in packet
            assert 'DO_NOT_SEND' not in packet and 'UNRELATED_ROUTE' not in packet
            assert 'ge-0/0/0.0' in packet and '10.1.0.2' in packet and 'Gi0/1' in packet
            return json.dumps({'answer':'The requested records are as follows:','sources':['S1','S2','S3'],'hypotheses':[]}),'test'
    question='Read Birch interface records, planned links and available operational state together.'
    invented_continuity='Birch ge-0/0/0.0 is operational and has been operational since the simulation start. Recorded at 2026-10-18T01:00:00Z. [S1] [S2] [S3]'
    assert any('continuous' in error or 'interval' in error for error in check_candidate(invented_continuity,context,evidence,{},question))
    answer,report=asyncio.run(synthesize(Model(),'test',question,context,evidence,{},'RAW_TABLE_DUMP'))
    assert report['status']=='rejected_fallback'
    assert all(value in answer for value in ['Birch','ge-0/0/0.0','10.1.0.2','Oak','Gi0/1','up','2026-10-18T01:00:00Z'])
    assert 'RAW_TABLE_DUMP' not in answer and '|' not in answer


def ospf_material():
    evidence=[Evidence(id='observed-ospf',source='Recorded protocol state',origin='simulated')]
    context=[{'tool':'network.state','status':'success','evidence_ids':['observed-ospf'],
        'scope_devices':[{'id':1,'hostname':'Oak-Edge'}],'data':{'records':[
            {'kind':'protocol_assessment','protocol':'OSPF','peer_parameters':[
                {'device_id':1,'hostname':'Oak-Edge','router_id':'203.0.113.1'},
                {'device_id':2,'hostname':'Birch-Core','router_id':'203.0.113.2'}],
                'observed_state':'Full','timestamp':'2026-10-19T01:00:00Z','freshness':'fresh',
                'conflict':False,'unknown_prerequisites':['authentication']},
            {'kind':'routing_table','routes':[{'prefix':'198.51.100.0/24','origin':'static'}]}]}}]
    return context,evidence


def test_protocol_roles_do_not_make_the_local_router_its_own_neighbor():
    context,evidence=ospf_material();question='Which OSPF adjacency observations are available for Oak-Edge?'
    bad='Neighbor: Oak-Edge with router_id 203.0.113.1. Neighbor: Birch-Core with router_id 203.0.113.2. State Full. Static routes are configured. [S1]'
    errors=check_candidate(bad,context,evidence,{},question)
    assert any('local router ID' in error for error in errors) and any('unrelated' in error for error in errors)
    good='Oak-Edge has a recorded OSPF neighbor Birch-Core, router ID 203.0.113.2, in state Full at 2026-10-19T01:00:00Z. Its local router ID is 203.0.113.1. [S1]'
    assert not check_candidate(good,context,evidence,{},question)
    assert check_candidate(good.replace('state Full','healthy state'),context,evidence,{},question)
    assert check_candidate(good.replace('state Full','Full/Established state'),context,evidence,{},question)
    assert check_candidate(good+' There are no unverified prerequisites.',context,evidence,{},question)
    assert check_candidate(good+' There are no conflicting observations or unverified prerequisites.',context,evidence,{},question)
    assert check_candidate(good.replace('Birch-Core','an unnamed peer'),context,evidence,{},question)
    assert not check_candidate(good+' Authentication remains unchecked.',context,evidence,{},question)


def test_protocol_model_input_keeps_endpoint_roles_without_unrequested_route_tables():
    context,evidence=ospf_material()
    class Model:
        async def generate(self,messages,**kwargs):
            packet=messages[-1]['content']
            assert 'untrusted_protocol_observations' in packet and '203.0.113.2' in packet
            assert 'routing_table' not in packet and '198.51.100.0' not in packet
            return json.dumps({'answer':'Oak-Edge has a recorded OSPF neighbor Birch-Core (router ID 203.0.113.2), state Full, captured 2026-10-19T01:00:00Z. This does not establish all-traffic health. [S1]','sources':['S1'],'hypotheses':[]}),'test-model'
    answer,report=asyncio.run(synthesize(Model(),'test','Which OSPF adjacency observations are available for Oak-Edge?',context,evidence,{'development':{'id':'test'}},'fallback'))
    assert 'Birch-Core' in answer and report['status']=='literal_checks_passed'


def test_protocol_interpretation_does_not_require_repeating_every_identifier():
    context,evidence=ospf_material();context[0]['data']['records'][0]['observed_state']='Init'
    question='What does this Init state imply about the OSPF adjacency?'
    good='The recorded OSPF state is Init. In OSPF, that means a Hello was received, but bidirectional Hello communication is not yet established. It does not establish a specific root cause or tested packet delivery. [S1]'
    assert not check_candidate(good,context,evidence,{},question)
    assert check_candidate('Init confirms that bidirectional Hello communication is established. [S1]',context,evidence,{},question)
    assert check_candidate('Init means the routers have exchanged Link State Request packets but have not yet received Link State Descriptions. [S1]',context,evidence,{},question)
    assert not check_candidate(good+' Init does not prove Link State Request exchange.',context,evidence,{},question)
    assert check_candidate(good+' Thus database description and link state exchange have not yet occurred.',context,evidence,{},question)
    assert check_candidate(good+' This means the database/link-state exchanges have not yet occurred.',context,evidence,{},question)
    assert check_candidate(good+' The database description and link state request/update exchange have not yet been initiated.',context,evidence,{},question)
    assert check_candidate(good+' Database exchanges never happened earlier.',context,evidence,{},question)
    assert not check_candidate(good+' Its earlier adjacency history is unknown.',context,evidence,{},question)
    assert check_candidate(good+' The routers are not yet in the Established state.',context,evidence,{},question)
    assert check_candidate(good+" The neighbor is not yet listed in the local router's neighbor list.",context,evidence,{},question)
    assert check_candidate(good+' The routers are in the process of establishing an adjacency.',context,evidence,{},question)
    assert not check_candidate(good+' It might persist without further evidence.',context,evidence,{},question)
    assert not check_candidate(good+' This does not establish that the database/link-state exchanges have not yet occurred.',context,evidence,{},question)
    assert check_candidate('Init indicates the OSPF adjacency has been established, but bidirectional Hello communication has not yet been established. Its cause is unknown. [S1]',context,evidence,{},question)
    assert check_candidate(good+' The neighbor has not yet sent a Hello packet in response.',context,evidence,{},question)
    assert not check_candidate(good+' We cannot conclude whether the neighbor has not yet sent another Hello.',context,evidence,{},question)


def test_published_requirement_synthesis_preserves_fields_and_vendor_choices():
    from llm.orchestration.synthesis import PublishedAnswerDraft,published_contract_facts,published_answer_errors
    context=[{'tool':'knowledge.search','status':'success','data':[{'source':'published:remove_method','evidence_id':'k',
        'published_requirements':{'operations':[{'operation_id':'remove_method','description':'Remove one recorded next hop.',
            'schema':{'required':['destination','next_hop'],'x-required-by-vendor':{'juniper':['next_hop_kind']},
                'properties':{'destination':{'type':'string'},'next_hop':{'type':'string'},'next_hop_kind':{'type':'string','enum':['next-hop','qualified-next-hop']}}},
            'profiles':[{'vendor':'juniper','platform':'junos','versions':['test']}]}]}}]}]
    evidence=[Evidence(id='k',source='published:remove_method',origin='stored',authority='published_operation_documentation')]
    question='What does published Junos knowledge require to remove a qualified static next hop?'
    good='Supply `destination` and `next_hop`; Junos also requires `next_hop_kind`, choosing `qualified-next-hop` for this case. This distinguishes the published removal branch. [S1]'
    facts=published_contract_facts(context,evidence)
    draft=PublishedAnswerDraft(answer=good,sources=['S1'],operation_ids=['remove_method'])
    assert not published_answer_errors(draft,facts,question)
    assert published_answer_errors(draft.model_copy(update={'answer':'Only `destination` is needed. [S1]'}),facts,question)
    assert published_answer_errors(draft.model_copy(update={'answer':good+' Also supply `invented_parameter`.'}),facts,question)
    assert published_answer_errors(draft.model_copy(update={'operation_ids':['absent_method']}),facts,question)
    class Model:
        async def generate(self,messages,**kwargs):
            assert 'required_by_vendor' in messages[-1]['content']
            assert kwargs['structured']['properties']['operation_ids']['items']['enum']==['remove_method']
            return draft.model_dump_json(),'test-model'
    answer,report=asyncio.run(synthesize(Model(),'test',question,context,evidence,{},'fallback'))
    assert report['status']=='literal_checks_passed' and '`qualified-next-hop`' in answer


def test_contract_array_items_and_vendor_requirements_are_not_flattened():
    from llm.orchestration.synthesis import PublishedAnswerDraft,published_answer_errors
    facts=[{'operation_id':'fixture','required':['interfaces'],'required_by_vendor':{'cisco':['process_id']},
        'vendor_platforms':[{'vendor':'cisco','platform':'iosxe','versions':['test']}], 'sources':['S1'],
        'fields':[{'field':'interfaces','type':'array','item_type':'object','required':True}, {'field':'process_id','type':'integer'}, {'field':'router_id','type':'string'}]}]
    draft=PublishedAnswerDraft(answer='interfaces is an array of strings. process_id is optional. [S1]',sources=['S1'],operation_ids=['fixture'])
    errors=published_answer_errors(draft,facts,'Explain the required fields.')
    assert any('objects' in error for error in errors) and any('globally optional' in error for error in errors)
    good=draft.model_copy(update={'answer':'interfaces is an array of objects. process_id is vendor-conditionally required for Cisco. [S1]'})
    assert not published_answer_errors(good,facts,'Explain the required fields.')
    assert published_answer_errors(good.model_copy(update={'answer':'interfaces is required. router_id (string, required). [S1]'}),facts,'Explain the required fields.')
    assert published_answer_errors(good.model_copy(update={'answer':'The method requires the following fields: interfaces and router_id. [S1]'}),facts,'Explain the required fields.')
    assert published_answer_errors(good.model_copy(update={'sources':['S1','S2']}),facts,'Explain the required fields.')


def test_metric_gaps_do_not_become_constant_usage_or_unavailable_sources():
    context=[{'tool':'network.telemetry','status':'success','evidence_ids':['m'],'data':{'source_available':True,'records':[
        {'hostname':'Oak','metric':'cpu_pct','unit':'percent','current':False,'timestamp':'2026-10-18T00:59:30Z',
            'samples':[{'timestamp':'2026-10-18T00:59:00Z','value':16},{'timestamp':'2026-10-18T00:59:30Z','value':None}]}]}}]
    evidence=[Evidence(id='m',source='Recorded telemetry',origin='simulated')]
    question='Explain the CPU observations and the gap.'
    good='Oak has a recorded16percent sample at00:59:00Z. The next point is missing; usage during the gap is unknown. [S1]'
    assert check_candidate('CPU remained at16% throughout the entire window. [S1]',context,evidence,{},question)
    assert check_candidate('The telemetry data is unavailable. [S1]',context,evidence,{},question)
    assert check_candidate('The samples show a steady increase in CPU from16% to16%. [S1]',context,evidence,{},question)
    assert not check_candidate(good,context,evidence,{},question)
    class Model:
        async def generate(self,messages,**kwargs):
            assert 'missing (unknown, not zero)' in messages[-1]['content']
            return json.dumps({'answer':good,'sources':['S1'],'hypotheses':[]}),'test-model'
    answer,report=asyncio.run(synthesize(Model(),'test',question,context,evidence,{},'fallback'))
    assert report['status']=='literal_checks_passed' and 'gap' in answer


def test_single_metric_answer_identifies_record_not_only_a_bare_number():
    context=[{'tool':'network.telemetry','status':'success','data':{'records':[
        {'hostname':'Oak','metric':'cpu_pct','unit':'percent','current':True,
            'samples':[{'timestamp':'2026-10-18T01:00:00Z','value':18}]}]}}]
    evidence=[Evidence(id='m',source='Recorded telemetry',origin='simulated')]
    question='What CPU measurement is recorded for Oak in the requested window?'
    assert check_candidate('18 percent. [S1]',context,evidence,{},question)
    assert check_candidate('Oak CPU was18 percent. [S1]',context,evidence,{},question)
    assert not check_candidate('Oak CPU was18 percent at01:00:00Z. [S1]',context,evidence,{},question)
    context[0]['data']['records'][0]['samples'].append({'timestamp':'2026-10-18T01:00:30Z','value':None})
    assert not check_candidate('The missing point at01:00:30Z is unknown, not zero. [S1]',context,evidence,{},'Are you sure that missing point is zero?')


@pytest.mark.parametrize('answer',[
    'The missing point at 2026-10-18T00:59:00+00:00 is unknown and not zero. [S1]',
    'Oak CPU was27 percent at2026-10-18T00:59:30Z. The gap remains unknown. [S1]',
    'Oak CPU was0 percent at2026-10-18T00:59:30Z. The gap remains unknown. [S1]',
    'Oak CPU was 27% at 2026-10-18T00:59:00+00:00 and 0% at 2026-10-18T00:59:30+00:00. The gap is unknown. [S1]',
])
def test_metric_value_and_missing_status_belong_to_their_actual_timestamp(answer):
    from llm.orchestration.synthesis import metric_attribution_errors,metric_observations
    context=[{'tool':'network.telemetry','status':'success','data':{'records':[
        {'hostname':'Oak','metric':'cpu_pct','unit':'percent','samples':[
            {'timestamp':'2026-10-18T00:59:00Z','value':27},
            {'timestamp':'2026-10-18T00:59:30Z','value':None}]}]}}]
    evidence=[Evidence(id='m',source='Recorded telemetry',origin='simulated')]
    question='Is the missing point zero?'
    assert metric_attribution_errors(answer,metric_observations(context))
    assert check_candidate(answer,context,evidence,{},question)
    good='Oak CPU was27 percent at2026-10-18T00:59:00Z, and at2026-10-18T00:59:30Z the value is missing, not zero. [S1]'
    assert not check_candidate(good,context,evidence,{},question)
    assert not metric_attribution_errors(good,metric_observations(context))
    numeric_context=json.loads(json.dumps(context))
    numeric_context[0]['data']['records'][0]['samples'][1]['value']=18
    assert not metric_attribution_errors('Oak CPU was27% at2026-10-18T00:59:00Z and18% at2026-10-18T00:59:30Z. [S1]',metric_observations(numeric_context))


def test_identical_config_captures_do_not_prove_no_intervening_changes():
    context=[{'tool':'network.configuration','status':'success','data':{'records':[
        {'hostname':'Oak-Edge','kind':'running_configuration','current':True,'timestamp':'2026-10-19T01:00:00Z','config_text':'hostname Oak-Edge\n'},
        {'hostname':'Oak-Edge','kind':'configuration_snapshot','current':False,'timestamp':'2026-10-19T00:00:00Z','config_text':'hostname Oak-Edge\n'}]}}]
    evidence=[Evidence(id='config',source='Recorded configurations',origin='simulated')]
    question='Compare the newest backup with the current configuration.'
    assert check_candidate('There are no differences, indicating the configuration has not been modified since the saved capture was taken. [S1]',context,evidence,{},question)
    assert not check_candidate('No literal differences appear between these two returned records. This does not rule out intervening changes. [S1]',context,evidence,{},question)


def test_interface_address_cannot_become_a_configured_router_id():
    context=[{'tool':'network.configuration','status':'success','evidence_ids':['c'],'data':{'records':[
        {'hostname':'Oak','config_text':'sysname Oak\ninterface GigabitEthernet0/0/1\n ip address 10.1.0.2 255.255.255.252\nquit\nbgp 65002\n peer 10.1.0.1 as-number 65001\n','current':False,'timestamp':'2026-10-19T01:00:00Z'}]}}]
    evidence=[Evidence(id='c',source='Stored configuration',origin='stored')]
    question='What router IDs are actually present in Oak’s stored configuration?'
    assert check_candidate('The router ID present is 10.1.0.2. [S1]',context,evidence,{},question)
    assert not check_candidate('No explicit router-ID command in the supported forms appears in the saved text. Its effective ID cannot be determined from the interface address. [S1]',context,evidence,{},question)
    class Model:
        async def generate(self,messages,**kwargs):
            assert '10.1.0.2' not in messages[-1]['content']
            return json.dumps({'answer':'No explicit router-ID command was found in the supported forms in Oak’s saved configuration. The effective router ID cannot be inferred from other addresses. [S1]','sources':['S1'],'hypotheses':[]}),'test-model'
    answer,report=asyncio.run(synthesize(Model(),'test',question,context,evidence,{},'fallback'))
    assert report['status']=='literal_checks_passed' and 'No explicit' in answer


def test_unavailable_records_are_not_absent_records_or_a_device_profile():
    context=[{'tool':'network.incidents','status':'unavailable','scope_devices':[{'id':1,'hostname':'Oak'}],
        'evidence_ids':['i'],'message':'Collector unavailable','data':{'records':[],'source_available':False}}]
    evidence=[Evidence(id='i',source='Incident reader',origin='stored')]
    question='Have any incident records been retained for Oak?'
    assert check_candidate('No incident records have been retained for Oak. [S1]',context,evidence,{},question)
    assert check_candidate('Oak is a Cisco router at this site. [S1]',context,evidence,{},question)
    assert check_candidate('The requested information is unavailable. [S1]',context,evidence,{},question)
    assert check_candidate('No packet errors or discards have been recorded on Oak. [S1]',context,evidence,{},question)
    assert check_candidate('The reader is unavailable, preventing the recording of packet errors on Oak. [S1]',context,evidence,{},question)
    class Model:
        async def generate(self,messages,**kwargs):
            raise AssertionError('An unavailable reader supplies no observations for synthesis')
    from llm.gateway_findings import network_answer
    fallback=network_answer(context,evidence,question=question)
    answer,report=asyncio.run(synthesize(Model(),'test',question,context,evidence,{},fallback))
    assert report['status']=='unavailable_sources_fallback' and not report['model_synthesis']
    assert 'unavailable' in answer and 'Oak' in answer and '[S1]' in answer
    assert 'No matching records' not in answer and 'No incident records' not in answer


def material():
    evidence = [Evidence(id='private-evidence-reference', source='Stored planned topology', origin='stored')]
    context = [{'tool': 'network.topology', 'status': 'success', 'evidence_ids': [evidence[0].id],
                'scope_devices': [{'id': 1, 'hostname': 'R1'}, {'id': 2, 'hostname': 'R2'}],
                'data': {'nodes': [{'id': 1, 'hostname': 'R1'}, {'id': 2, 'hostname': 'R2'}],
                         'links': [{'source': 'R1', 'target': 'R2', 'source_interface': 'GigabitEthernet0/1',
                                    'target_interface': 'GigabitEthernet0/2'}],
                         'topology_kind': 'planned', 'reachability': 'not_measured'}}]
    return context, evidence


def test_topology_projection_preserves_link_facts_and_provenance():
    context, evidence = material()
    packet = projection(context, evidence, {}, 'Explain the planned connection.')
    assert packet['records'][0]['data']['links'] == context[0]['data']['links']
    assert packet['records'][0]['sources'] == ['S1']
    assert packet['sources'][0]['origin'] == 'stored'
    assert 'private-evidence-reference' not in json.dumps(packet)


def test_markdown_colon_is_not_part_of_an_interface_identifier():
    evidence=[Evidence(id='iface-proof',source='Stored interfaces',origin='stored')]
    context=[{'tool':'inventory.read','status':'success','data':{'devices':[
        {'id':1,'hostname':'Birch-Edge','interfaces':[
            {'name':'ge-0/0/0.0','prefix':'192.0.2.5/30'},
            {'name':'Ethernet1:2','prefix':'198.51.100.5/30'}]}]}}]
    answer="Birch-Edge's recorded interfaces:\n- ge-0/0/0.0: 192.0.2.5/30\n- Ethernet1:2: 198.51.100.5/30 [S1]"
    assert not check_candidate(answer,context,evidence,{})
    assert check_candidate(answer.replace('ge-0/0/0.0:','ge-0/0/0.1:'),context,evidence,{})
    assert check_candidate(answer.replace('Ethernet1:2:','Ethernet1:3:'),context,evidence,{})


def test_return_path_question_keeps_forwarding_evidence_before_irrelevant_rows():
    flow={'kind':'forwarding_assessment','assessment':{'status':'delivered',
        'forward':{'status':'delivered','branches':[{'status':'delivered','reason':'declared routes','hops':[{'hostname':'Birch-Edge','interface':'Ethernet1'}]}]},
        'return':{'status':'delivered','branches':[{'status':'delivered','reason':'declared routes','hops':[{'hostname':'Alder-Edge','interface':'Ethernet2'}]}]}}}
    context=[{'tool':'network.state','status':'success','data':{'records':[
        {'kind':'interface_state','interface':'Ethernet'+str(i),'note':'X'*400} for i in range(16)]+[flow]}}]
    evidence=[Evidence(id='flow-proof',source='Scoped forwarding model',origin='simulated')]
    packet=projection(context,evidence,{},'Assess the modeled path, including the return direction.')
    result=packet['forwarding_results'][0]
    assert result['forward']['status']=='delivered' and result['return']['status']=='delivered'
    assert result['return']['branches'][0]['path']==['Alder-Edge']


def test_direct_reachability_question_uses_flow_records_not_protocol_health():
    context=[{'tool':'network.state','status':'success','evidence_ids':['state'],
        'scope_devices':[{'id':1,'hostname':'Oak'},{'id':2,'hostname':'Elm'}],
        'data':{'records':[
            {'kind':'protocol_assessment','protocol':'OSPF','observed_state':'Full'},
            {'kind':'protocol_assessment','protocol':'BGP','observed_state':'Established'},
            {'kind':'forwarding_assessment','flow':{'source_device_id':1,'destination_device_id':2,'protocol':'icmp'},
                'assessment':{'forward':{'status':'delivered','branches':[]},
                    'return':{'status':'failed','branches':[]}}}]}}]
    evidence=[Evidence(id='state',source='Recorded model observations',origin='simulated')]
    question='What do the current reachability observations say about Oak to Elm?'
    packet=projection(context,evidence,{},question)
    assert packet['forwarding_results'][0]['return']['status']=='failed'
    assert 'protocol_assessment' not in json.dumps(packet['records'])
    bad='The OSPF and BGP sessions are in the Established state, indicating full connectivity and no issues with prefix acceptance or end-to-end forwarding. [S1]'
    errors=check_candidate(bad,context,evidence,{},question)
    assert any('OSPF' in error for error in errors)
    assert any('scope' in error or 'traffic' in error for error in errors)
    good='The recorded ICMP forward result is delivered, but the return result is failed. These development-simulation observations do not establish full connectivity. [S1]'
    assert not check_candidate(good,context,evidence,{},question)
    unrelated=projection(context,evidence,{},'Explain the recorded OSPF state.')
    # Source constraints survive phrasing changes, while presentation focus
    # still leaves an OSPF question on its actual protocol records.
    assert unrelated['forwarding_focus'] is False
    assert any(row.get('protocol')=='OSPF' for row in unrelated['records'][0]['data']['records'])


def test_forwarding_synthesis_cannot_hide_current_observation_conflicts():
    evidence=[Evidence(id='flow',source='Scoped model and observed interface records',origin='simulated')]
    context=[{'tool':'network.state','status':'success','evidence_ids':['flow'],'data':{'records':[
        {'kind':'forwarding_assessment','assessment':{'status':'delivered',
            'forward':{'status':'delivered','branches':[]},'return':{'status':'delivered','branches':[]}}}]}}]
    conflict='Current interface observations disagree about administrative state: up versus down.'
    assessment={'conclusion_status':'conflicting_evidence','development':{'id':'test'},'conflicts':[conflict]}
    question='Investigate whether the selected routers can communicate.'
    errors=check_candidate('The conflicting observations are resolved by the forward and return outcomes: both delivered. [S1]',context,evidence,assessment,question)
    assert any('resolve' in value for value in errors)
    wrong='The conflicting observations do not affect communication between the selected devices. Forward and return delivery succeeded. [S1]'
    assert any('affect' in value for value in check_candidate(wrong,context,evidence,assessment,question))
    assert check_candidate('Forward delivered and return delivered, so connectivity is confirmed. [S1]',context,evidence,assessment,question)
    class Model:
        async def generate(self,messages,**kwargs):
            assert conflict in messages[-1]['content']
            return json.dumps({'answer':'The recorded model reports forward delivered and return delivered, but current interface observations disagree. Current connectivity remains uncertain. [S1]','sources':['S1'],'hypotheses':[]}),'unit-test-model'
    answer,result=asyncio.run(synthesize(Model(),'test',question,context,evidence,assessment,'fallback',investigation=True))
    assert 'disagree' in answer and result['status']=='literal_checks_passed'


def test_forwarding_projection_names_complete_paths_and_keeps_failed_trace_partial():
    context=[{'tool':'network.state','status':'success','evidence_ids':['flow'],
        'scope_devices':[{'id':1,'hostname':'Birch-Edge'},{'id':3,'hostname':'Cedar-Edge'}],
        'data':{'records':[{'kind':'forwarding_assessment','flow':{'source_device_id':1,'destination_device_id':3},
            'assessment':{'forward':{'status':'delivered','branches':[{'status':'delivered','reason':'declared routes',
                'hops':[{'hostname':'Birch-Edge'},{'hostname':'Alder-Core'}]}]},
                'return':{'status':'blocked','branches':[{'status':'blocked','reason':'missing route','hops':[{'hostname':'Cedar-Edge'}]}]}}}]}}]
    packet=projection(context,[Evidence(id='flow',source='Model',origin='simulated')],
        {'conclusion_status':'internal_diagnosis_label','verification_scope':'Internal classification'},'Assess the modeled path and return direction.')
    result=packet['forwarding_results'][0]
    assert result['forward']['branches'][0]['path']==['Birch-Edge','Alder-Core','Cedar-Edge']
    assert result['return']['branches'][0]['path']==['Cedar-Edge']
    assert result['return']['status']=='blocked' and result['sources']==['S1']
    assert 'conclusion_status' not in json.dumps(packet) and 'internal_diagnosis_label' not in json.dumps(packet)
    del context[0]['data']['records'][0]['assessment']['return']
    missing=projection(context,[Evidence(id='flow',source='Model',origin='simulated')],{},'Assess the return direction.')
    assert missing['forwarding_results'][0]['return']=={'status':'not_recorded','branches':[]}


def test_direct_reachability_does_not_mislabel_endpoints_or_omit_transit():
    context=[{'tool':'network.state','status':'success','evidence_ids':['flow'],
        'scope_devices':[{'id':1,'hostname':'Oak'},{'id':3,'hostname':'Elm'}],
        'data':{'records':[{'kind':'forwarding_assessment','flow':{'source_device_id':1,'destination_device_id':3},
            'assessment':{'forward':{'status':'delivered','branches':[{'status':'delivered','hops':[{'hostname':'Oak'},{'hostname':'Birch'}]}]},
                'return':{'status':'delivered','branches':[{'status':'delivered','hops':[{'hostname':'Elm'},{'hostname':'Birch'}]}]}}}]}}]
    evidence=[Evidence(id='flow',source='Declared forwarding model',origin='simulated')]
    question='What do the reachability observations say about Oak to Elm?'
    wrong='Oak and Elm are both intermediate devices. The recorded traffic traversed these devices in both directions; the path is functional. [S1]'
    errors=check_candidate(wrong,context,evidence,{},question)
    assert any('transit' in value for value in errors)
    assert any('endpoint' in value for value in errors)
    correct='The simulated forward path Oak → Birch → Elm and return path Elm → Birch → Oak both delivered the tested traffic. Birch is the transit device; Oak and Elm are the endpoints. [S1]'
    assert not check_candidate(correct,context,evidence,{},question)
    natural='Traffic traverses the intermediate device Birch, which forwards the tested flow from Oak to Elm. Forward and return delivery succeed in the model. [S1]'
    assert not check_candidate(natural,context,evidence,{},question)
    wrong_list='The recorded forward path traverses intermediate devices Birch and Oak, and the return path traverses the same devices in reverse order. Both directions delivered. [S1]'
    assert any('endpoint' in error for error in check_candidate(wrong_list,context,evidence,{},question))


def test_reachability_display_attaches_exact_test_scope_without_model_credit():
    context=[{'tool':'network.state','status':'success','evidence_ids':['flow'],
        'scope_devices':[{'id':1,'hostname':'Oak'},{'id':2,'hostname':'Elm'}],
        'data':{'records':[{'kind':'forwarding_assessment','timestamp':'2026-10-18T01:00:00Z',
            'flow':{'source_device_id':1,'destination_device_id':2,'source_address':'192.0.2.1','destination_address':'192.0.2.2','protocol':'icmp','vrf':'blue'},
            'assessment':{'forward':{'status':'delivered','branches':[]},'return':{'status':'delivered','branches':[]}}}]}}]
    evidence=[Evidence(id='flow',source='Declared model',origin='simulated')]
    original='Both directions delivered the tested traffic within this development simulation. [S1]'
    class Model:
        async def generate(self,*args,**kwargs):return json.dumps({'answer':original,'sources':['S1'],'hypotheses':[]}),'test-model'
    answer,report=asyncio.run(synthesize(Model(),'test','What do the reachability observations show?',context,evidence,{},'fallback'))
    assert all(value in answer for value in ['ICMP','192.0.2.1','192.0.2.2','blue','2026-10-18T01:00:00Z'])
    assert report['display_test_scope_added'] is True
    assert report['attempts'][0]['candidate']['answer']==original


def test_failed_forward_delivery_is_not_reversed_by_a_working_return_path():
    context=[{'tool':'network.state','status':'success','evidence_ids':['flow'],
        'scope_devices':[{'id':1,'hostname':'Oak'},{'id':3,'hostname':'Elm'}],
        'data':{'records':[{'kind':'forwarding_assessment','flow':{'source_device_id':1,'destination_device_id':3},
            'assessment':{'forward':{'status':'failed','branches':[{'status':'failed','hops':[{'hostname':'Oak'}],
                'failure_location':{'hostname':'Birch','interface':'Ethernet7','direction':'ingress','policy_rule':'edge/deny','action':'deny'}}]},
                'return':{'status':'delivered','branches':[{'status':'delivered','hops':[{'hostname':'Elm'},{'hostname':'Birch'}]}]}}}]}}]
    evidence=[Evidence(id='flow',source='Scoped declared model',origin='simulated')]
    question='Investigate whether Oak can communicate with Elm.'
    bad='Oak can communicate with Elm. Birch was not observed in the recorded return path. The failure in forward delivery was due to ingress policy review. [S1]'
    errors=check_candidate(bad,context,evidence,{},question)
    assert any('forward direction failed' in value for value in errors)
    assert any('falsely described as absent' in value for value in errors)
    assert any('policy drop' in value for value in errors)
    good='Forward delivery is blocked by ingress policy edge/deny at Birch Ethernet7; return delivery Elm → Birch → Oak succeeds in this model. This does not establish working source-to-destination delivery. [S1]'
    assert not check_candidate(good,context,evidence,{},question)


def test_failed_trace_preserves_the_actual_transit_interface_not_an_endpoint_fault():
    context=[{'tool':'network.state','status':'success','evidence_ids':['flow'],'data':{'records':[
        {'kind':'interface_state','device_id':2,'interface_id':8,'hostname':'Birch-Transit','interface':'ge-0/0/1.0',
            'admin_status':'down','oper_status':'down','current':True,'freshness':'fresh'},
        {'kind':'interface_state','device_id':1,'interface_id':9,'hostname':'Oak-Edge','interface':'Ethernet1',
            'admin_status':'up','oper_status':'up','current':True,'freshness':'fresh'},
        {'kind':'forwarding_assessment','assessment':{'forward':{'status':'failed','branches':[
            {'status':'failed','reason':'egress interface down','hops':[
                {'device_id':1,'hostname':'Oak-Edge','interface_id':9,'interface':'Ethernet1'},
                {'device_id':2,'hostname':'Birch-Transit','interface_id':8,'interface':'ge-0/0/1.0'}]}]}}}]}}]
    evidence=[Evidence(id='flow',source='Scoped modeled observations',origin='simulated')]
    question='Find the supported cause of the failed modeled path.'
    fault=projection(context,evidence,{},question)['forwarding_results'][0]['forward']['branches'][0]['blocked_interface']
    assert fault=={'hostname':'Birch-Transit','interface':'ge-0/0/1.0','admin_status':'down','oper_status':'down'}
    assert check_candidate('The cause is an ingress interface down. [S1]',context,evidence,{},question)
    context[0]['scope_devices']=[{'id':1,'hostname':'Oak-Edge'},{'id':2,'hostname':'Birch-Transit'}]
    assert check_candidate('Birch-Transit ge-0/0/1.0 is down. The ingress interface on Oak-Edge is down. [S1]',context,evidence,{},question)
    assert not check_candidate('In the development simulation, Birch-Transit interface ge-0/0/1.0 is administratively and operationally down; it blocks the recorded forward calculation. [S1]',context,evidence,{},question)


def test_path_assessment_cannot_release_a_bare_trace_or_unfinished_outcome():
    context=[{'tool':'network.state','status':'success','data':{'records':[{
        'kind':'forwarding_assessment','assessment':{'forward':{'status':'delivered'},'return':{'status':'delivered'}}}]}}]
    evidence=[Evidence(id='flow',source='Model',origin='simulated')]
    question='Assess the modeled path including the return direction.'
    assert check_candidate('The forward path is marked as\n\nSources: [S1]',context,evidence,{},question)
    assert check_candidate('The modeled forward and return paths are symmetric. [S1]',context,evidence,{},question)
    assert not check_candidate('Both directions are delivered within this development simulation. [S1]',context,evidence,{},question)
    assert check_candidate("Both directions are delivered, confirming the model's accuracy. [S1]",context,evidence,{},question)


def test_reverse_direction_is_not_a_loop_and_missing_measurement_is_not_failure():
    context=[{'tool':'network.topology','status':'success','data':{'reachability':'not_measured'}},
        {'tool':'network.state','status':'success','data':{'records':[{'kind':'forwarding_assessment','assessment':{
            'forward':{'status':'delivered','branches':[{'status':'delivered','hops':[{'hostname':'Birch'},{'hostname':'Cedar'}]}]},
            'return':{'status':'delivered','branches':[{'status':'delivered','hops':[{'hostname':'Cedar'},{'hostname':'Birch'}]}]}}}]}}]
    evidence=[Evidence(id='flow',source='Model',origin='simulated')]
    assert check_candidate('The reverse path indicates a routing loop. [S1]',context,evidence,{})
    assert check_candidate('Reachability is not measured, indicating the network is not reachable. [S1]',context,evidence,{})
    assert not check_candidate('The reverse path is not evidence of a loop. Unmeasured physical reachability remains unknown. [S1]',context,evidence,{})


def test_model_receives_readable_direction_facts_and_only_their_source_labels():
    evidence=[Evidence(id=str(i),source='Record',origin='simulated') for i in range(3)]
    context=[{'tool':'network.state','status':'success','evidence_ids':['2'],'data':{'records':[{
        'kind':'forwarding_assessment','assessment':{'forward':{'status':'delivered'},'return':{'status':'not_recorded'}}}]}}]
    class Model:
        async def generate(self,messages,**kwargs):
            assert 'Forward outcome: delivered.' in messages[-1]['content']
            assert 'Return outcome: not_recorded.' in messages[-1]['content']
            assert 'conclusion_status' not in messages[-1]['content']
            assert kwargs['structured']['properties']['sources']['items']['enum']==['S3']
            return json.dumps({'answer':'Forward delivery is supported within the simulation; the return direction is not recorded, so two-way delivery is unknown. [S3]','sources':['S3']}),'unit-model'
    answer,report=asyncio.run(synthesize(Model(),'unit-model','Assess the modeled path including the return direction.',context,evidence,{},'fallback'))
    assert report['status']=='literal_checks_passed' and '[S3]' in answer
    labelled,report=asyncio.run(synthesize(Model(),'unit-model','Assess the modeled path including the return direction.',context,evidence,
        {'development':{'id':'scenario-proof'}},'fallback'))
    assert labelled.startswith('**Development simulation**') and report['display_provenance_added']
    assert not report['candidate']['answer'].startswith('**Development simulation**')


def test_bgp_role_projection_names_peers_and_requires_values_for_consistency():
    evidence=[Evidence(id='peers',source='Recorded protocol peers',origin='simulated')]
    context=[{'tool':'network.state','status':'success','scope_devices':[
        {'id':1,'hostname':'Oak-Edge'},{'id':2,'hostname':'Birch-Edge'}],
        'data':{'records':[{'kind':'protocol_assessment','protocol':'BGP','observed_state':'Established',
            'peer_parameters':[{'device_id':1,'local_as':65111,'remote_as':65222},
                {'device_id':2,'local_as':65222,'remote_as':65111}]}]}}]
    question='Does the recorded BGP session between Oak-Edge and Birch-Edge have consistent AS roles?'
    peers=projection(context,evidence,{},question)['records'][0]['data']['records'][0]['peer_parameters']
    assert [p['hostname'] for p in peers]==['Oak-Edge','Birch-Edge']
    assert check_candidate('Yes, the AS roles are consistent. [S1]',context,evidence,{},question)
    assert not check_candidate('Oak-Edge has local AS 65111 and remote AS 65222. Birch-Edge has local AS 65222 and remote AS 65111. These roles match reciprocally. [S1]',context,evidence,{},question)
    assert check_candidate('Oak-Edge has local AS 65222 and remote AS 65111. Birch-Edge has local AS 65111 and remote AS 65222. [S1]',context,evidence,{},question)
    assert check_candidate("Oak-Edge's local AS is 65111, while Birch-Edge's remote AS is 65222. [S1]",context,evidence,{},question)
    assert check_candidate('Both peers have the same local AS value (65111) and remote AS value (65222). [S1]',context,evidence,{},question)
    assert not check_candidate('The peers do not have the same local AS. Oak-Edge has local AS 65111 and remote AS 65222. Birch-Edge has local AS 65222 and remote AS 65111. [S1]',context,evidence,{},question)
    assert check_candidate('The session does not have consistent AS roles. Oak-Edge has local AS 65111 and remote AS 65222. Birch-Edge has local AS 65222 and remote AS 65111. [S1]',context,evidence,{},question)
    context[0]['data']['records'][0]['peer_parameters'][1]['remote_as']=65112
    assert not check_candidate('The session does not have consistent AS roles. Oak-Edge has local AS 65111 and remote AS 65222. Birch-Edge has local AS 65222 and remote AS 65112. [S1]',context,evidence,{},question)
    for peer in context[0]['data']['records'][0]['peer_parameters']:
        peer.update(local_as=65111,remote_as=65111)
    assert not check_candidate('Both peers have the same local AS value (65111) and remote AS value (65111). [S1]',context,evidence,{},question)


def test_configuration_comparison_uses_actual_temporal_pair_and_literal_changes():
    from llm.orchestration.synthesis import configuration_comparisons
    context=[{'tool':'network.configuration','status':'success','evidence_ids':['configs'],'data':{'records':[
        {'hostname':'Oak-Edge','current':True,'kind':'running_configuration','timestamp':'2026-10-19T01:00:00Z',
            'config_text':'hostname Oak-Edge\ninterface Ethernet1\n shutdown\n'},
        {'hostname':'Oak-Edge','current':False,'kind':'configuration_snapshot','timestamp':'2026-10-19T00:59:00Z',
            'config_text':'hostname Oak-Edge\ninterface Ethernet1\n'}]}}]
    evidence=[Evidence(id='configs',source='Recorded configurations',origin='simulated')]
    question='What changed between Oak-Edge saved configuration and the current one?'
    comparison=configuration_comparisons(context,{'configs':'S1'})[0]
    assert comparison['added_lines']==[' shutdown'] and comparison['removed_lines']==[]
    assert comparison['current_time']>'2026-10-19T00:59:00Z'
    assert check_candidate('Current configuration has different OSPF settings. [S1]',context,evidence,{},question)
    assert check_candidate('The saved configuration includes ` shutdown`. [S1]',context,evidence,{},question)
    assert check_candidate('The current configuration does not include ` shutdown`. [S1]',context,evidence,{},question)
    assert not check_candidate('The current configuration adds ` shutdown`; the saved capture does not contain that line. [S1]',context,evidence,{},question)
    class Model:
        async def generate(self,messages,**kwargs):
            assert 'added_lines' in messages[-1]['content'] and ' shutdown' in messages[-1]['content']
            return json.dumps({'answer':'The current configuration adds this line compared with the saved capture:\n```cli\n shutdown\n```\n[S1]','sources':['S1'],'hypotheses':[]}),'unit-test-model'
    answer,report=asyncio.run(synthesize(Model(),'unit-test-model',question,context,evidence,{},'fallback'))
    assert report['status']=='literal_checks_passed' and ' shutdown' in answer
    context[0]['data']['records'].pop(0)
    assert configuration_comparisons(context,{'configs':'S1'})==[]


@pytest.mark.parametrize('status,expected_model',[
    ('literal_checks_passed','unit-test-model'),('repaired_literal_checks_passed','unit-test-model'),
    ('rejected_fallback',None),('unavailable_fallback',None)])
def test_verified_repaired_synthesis_retains_model_attribution(tmp_path_factory,status,expected_model):
    import os
    from unittest.mock import AsyncMock,patch
    from uuid import uuid4
    from db.manager import DatabaseManager
    from llm.gateway import AIGateway
    from llm.gateway_models import TurnRequest
    from llm.gateway_routing import SemanticRoute
    from llm.gateway_store import ensure_schema
    db=DatabaseManager(str(tmp_path_factory.mktemp('model')/'gateway.db'));db.initialize();ensure_schema(db)
    try:
        gateway=AIGateway(db);cid=gateway.store.create('model-proof','floating')['id']
        bundle=([{'tool':'network.state','status':'success','data':{'records':[]}}],[],{},'Reviewed model prose.')
        info={'engine':'langgraph_b3','verification':{'status':'verified','synthesis':{
            'status':status,'model_synthesis':True,'model':'unit-test-model'}}}
        result=(SemanticRoute(intent='answer',network_domains=['state']),bundle,info)
        with patch.dict(os.environ,{'COGNISHIELD_AI_ENGINE':'langgraph_b3'}),patch('llm.orchestration.engine.run',AsyncMock(return_value=result)):
            response=asyncio.run(gateway.turn(cid,{'username':'model-proof','role':'engineer'},TurnRequest(request_id=uuid4(),prompt='Explain the recorded state.')))
        assert response.answer=='Reviewed model prose.' and response.model==expected_model
    finally:db.close()


def test_model_output_contract_requires_available_citation_when_evidence_exists():
    context, evidence = material()
    class CheckedModel:
        async def generate(self, messages, *, structured, model, purpose):
            validator = Draft202012Validator(structured)
            assert not validator.is_valid({'answer': 'There is a planned link.'})
            assert not validator.is_valid({'answer': 'There is a planned link.', 'sources': []})
            assert not validator.is_valid({'answer': 'There is a planned link.', 'sources': ['S99']})
            value = {'answer': 'R1 connects to R2 in the stored planned topology.', 'sources': ['S1'], 'hypotheses': []}
            assert validator.is_valid(value)
            return json.dumps(value), 'TEST-model'
    answer, report = asyncio.run(synthesize(CheckedModel(), 'TEST-model', 'Explain the planned connection.', context, evidence, {}, 'verified fallback'))
    assert report['status'] == 'literal_checks_passed'
    assert '[S1]' in answer and report['model_synthesis']


def test_interface_attribution_cannot_borrow_another_endpoint_name():
    context, evidence = material()
    bad = "R2's GigabitEthernet0/1 interface is the recorded endpoint. [S1]"
    assert any('interface' in error.lower() for error in check_candidate(bad, context, evidence, {}))
    good = "R2's GigabitEthernet0/2 interface is the recorded endpoint. [S1]"
    assert not check_candidate(good, context, evidence, {})
    two_subjects = 'R1 connects to R2 via GigabitEthernet0/1 on R1 and GigabitEthernet0/1 on R2. [S1]'
    assert any('interface' in error.lower() for error in check_candidate(two_subjects, context, evidence, {}))


def test_stored_planned_graph_cannot_be_called_confirmed_live():
    context, evidence = material()
    assert check_candidate('The network path from R1 to R2 is confirmed as live. [S1]', context, evidence, {})
    assert not check_candidate('The recorded path from R1 to R2 is not confirmed as live. [S1]', context, evidence, {})


def test_gateway_oracle_allows_optional_detail_but_rejects_wrong_endpoint():
    from scripts.evaluate_phase_f_gateway import topology_oracle
    assert topology_oracle('The recorded path is R1 -> R2, via GigabitEthernet0/1 on R1. [S1]')
    assert topology_oracle('R1 -> R2. [S1]')
    assert not topology_oracle("R1 -> R2, reaching R2's GigabitEthernet0/1. [S1]")
    assert not topology_oracle('R1 -> R2 via GigabitEthernet0/1 on R1 and GigabitEthernet0/1 on R2. [S1]')


def test_returned_device_cannot_be_described_as_absent_from_inventory():
    context=[{'tool':'inventory.read','status':'success','data':{'devices':[{'id':7,'hostname':'Oak-Edge','interfaces':[]}]}}]
    evidence=[Evidence(id='inventory',source='Stored inventory',origin='stored')]
    assert check_candidate('No, Oak-Edge is not present in our device list. [S1]',context,evidence,{})
    assert not check_candidate('Oak-Edge is present in the inventory. Its reachability is not established. [S1]',context,evidence,{})
    assert not check_candidate('The software release for Oak-Edge is not recorded. [S1]',context,evidence,{})


def test_topology_neighbor_claim_needs_an_actual_device_relationship():
    context,evidence=material()
    context.append({'tool':'inventory.read','status':'success','data':{'devices':[
        {'id':2,'hostname':'R2','interfaces':[{'name':'Loopback0'}]}]}})
    assert check_candidate('The neighbor of R2 in the topology records is Loopback0. [S1]',context,evidence,{})
    assert not check_candidate('The neighbor of R2 in the topology records is R1. [S1]',context,evidence,{})
    context[0]['status']='unavailable';context[0]['data']['links']=[]
    assert check_candidate('The topology neighbor of R2 is R1. [S1]',context,evidence,{})
    assert not check_candidate('The topology neighbor of R2 is unknown. [S1]',context,evidence,{})
    context[0]['status']='success'
    context[0]['data']['records']=[{'link_endpoints':{'source':'R1','target':'R2'}}]
    assert not check_candidate('The topology neighbor of R2 is R1. [S1]',context,evidence,{})


def test_hop_count_uses_completed_egress_steps_not_number_of_devices():
    context=[{'tool':'network.state','status':'success','data':{'records':[{
        'kind':'forwarding_assessment','assessment':{'forward':{'branches':[{'status':'delivered',
            'hops':[{'hostname':'Oak-Edge'},{'hostname':'Ash-Core'}]}]}}}]}}]
    evidence=[Evidence(id='state',source='Declared forwarding model',origin='simulated')]
    assert check_candidate('3\n\nSources: [S1]',context,evidence,{},question='How many modeled hops connect the endpoints?')
    assert not check_candidate('2 hops. [S1]',context,evidence,{},question='How many modeled hops connect the endpoints?')


def test_direct_topology_answer_does_not_inherit_unrequested_investigation_gaps():
    context,evidence=material()
    assessment={'gaps':['Fresh reachability is missing.'],'hypotheses':[{'candidate':'possible outage'}]}
    direct=projection(context,evidence,assessment,'Describe the planned cabling.',investigation=False)
    assert 'Fresh reachability' not in json.dumps(direct)
    followup=projection(context,evidence,assessment,'What should I check next?',investigation=True)
    assert followup['calculations']['gaps']==assessment['gaps']


def test_known_intermediate_node_cannot_be_denied_in_model_prose():
    context,evidence=material()
    context[0]['data']['graph_path']=['R1','Core-Elm','R2']
    assert check_candidate('The planned path has no intermediate devices. [S1]',context,evidence,{})
    assert check_candidate('The cabling is planned and not yet implemented. [S1]',context,evidence,{})
    assert not check_candidate('The graph contains an intermediate router. Its implementation state is unknown. [S1]',context,evidence,{})


def test_multihop_investigation_cannot_claim_direct_route_or_omit_return_path():
    context=[{'tool':'network.state','status':'success','evidence_ids':['flow'],
        'scope_devices':[{'id':1,'hostname':'Oak-Edge'},{'id':3,'hostname':'Cedar-Edge'}],
        'data':{'records':[{'kind':'forwarding_assessment','flow':{'source_device_id':1,'destination_device_id':3},
            'assessment':{'forward':{'status':'delivered','branches':[{'status':'delivered','hops':[{'hostname':'Oak-Edge'},{'hostname':'Birch-Core'}]}]},
                'return':{'status':'delivered','branches':[{'status':'delivered','hops':[{'hostname':'Cedar-Edge'},{'hostname':'Birch-Core'}]}]}}}]}}]
    evidence=[Evidence(id='flow',source='Declared model',origin='simulated')]
    question='Investigate whether Oak-Edge can communicate with Cedar-Edge using the recorded forwarding evidence.'
    bad='Oak-Edge can communicate with Cedar-Edge. The recorded path shows a direct route from Oak-Edge to Cedar-Edge. Traffic is delivered. [S1]'
    errors=check_candidate(bad,context,evidence,{},question)
    assert any('direct' in error.lower() for error in errors)
    assert any('return' in error.lower() for error in errors)
    good='Within the simulated flow, both directions are delivered. Forward: Oak-Edge → Birch-Core → Cedar-Edge. Return: Cedar-Edge → Birch-Core → Oak-Edge. This is not a direct path or a physical packet test. [S1]'
    assert not check_candidate(good,context,evidence,{},question)
    # A different, hypothetical direct route is not a claim about these endpoints.
    assert not check_candidate(good+' A direct route elsewhere has not been tested.',context,evidence,{},question)


def test_controller_connection_state_is_not_device_operational_health():
    context=[{'tool':'network.state','status':'success','data':{'records':[{
        'kind':'controller_state','hostname':'Oak-Edge','controller':'LAB-CONTROLLER','node':'Oak-Edge',
        'configured':True,'operational':'connected','capabilities':['inventory']}]}}]
    evidence=[Evidence(id='state',source='Controller observation',origin='simulated')]
    bad='The controller reports that Oak-Edge device is configured and operational. [S1]'
    assert check_candidate(bad,context,evidence,{},'What does the controller report?')
    good='LAB-CONTROLLER is configured and connected for Oak-Edge, with inventory capability. Device operational health is not established by this controller connection record. [S1]'
    assert not check_candidate(good,context,evidence,{},'What does the controller report?')


def test_nonempty_interface_observations_are_not_denied_or_reversed():
    context=[{'tool':'network.state','status':'success','evidence_ids':['state'],
        'source_request':{'record_kinds':['interface_state']},'data':{'records':[
        {'kind':'interface_state','hostname':'Oak','interface':'Ethernet7','admin_status':'up',
            'oper_status':'down','timestamp':'2026-10-18T01:00:00Z','current':True}]}}]
    evidence=[Evidence(id='state',source='Recorded interface observation',origin='simulated')]
    question='Obtain interface-operational-state records for Oak.'
    assert check_candidate('No interface-operational-state records were obtained for Oak. [S1]',context,evidence,{},question)
    assert check_candidate('Yes, the interface operational state for Oak is up. [S1]',context,evidence,{},question)
    assert check_candidate('Oak Ethernet7 administrative state is down; operational state is up. [S1]',context,evidence,{},question)
    good='Oak Ethernet7: administrative state up; operational state down, recorded at2026-10-18T01:00:00Z. [S1]'
    assert not check_candidate(good,context,evidence,{},question)
    class Model:
        async def generate(self,messages,**kwargs):
            assert 'untrusted_interface_observations' in messages[-1]['content']
            assert 'Ethernet7' in messages[-1]['content']
            return json.dumps({'answer':good,'sources':['S1'],'hypotheses':[]}),'test-model'
    answer,report=asyncio.run(synthesize(Model(),'test',question,context,evidence,{},'fallback'))
    assert report['status']=='literal_checks_passed' and 'operational state down' in answer


def test_interface_answer_projects_only_an_unambiguous_source_time():
    context=[{'tool':'network.state','status':'success','evidence_ids':['state'],
        'source_request':{'record_kinds':['interface_state']},'data':{'records':[
        {'kind':'interface_state','hostname':'Oak','interface':'Ethernet7','admin_status':'up',
            'oper_status':'down','timestamp':'2026-10-18T01:00:00Z','current':True}]}}]
    evidence=[Evidence(id='state',source='Recorded interface observation',origin='simulated')]
    question='Obtain interface-operational-state records for Oak.'
    original='Oak Ethernet7: administrative state up; operational state down. [S1]'
    class Model:
        def __init__(self,answer):self.answer=answer
        async def generate(self,*args,**kwargs):
            return json.dumps({'answer':self.answer,'sources':['S1'],'hypotheses':[]}),'test-model'
    answer,report=asyncio.run(synthesize(Model(original),'test',question,context,evidence,{},'fallback'))
    assert report['status']=='literal_checks_passed'
    assert '2026-10-18T01:00:00Z' in answer
    assert report['attempts'][0]['model_candidate']['answer']==original
    assert report['attempts'][0]['observation_time_projected'] is True
    wrong=original+' Recorded at 2026-10-18T02:00:00Z.'
    answer,report=asyncio.run(synthesize(Model(wrong),'test',question,context,evidence,{},'fallback'))
    assert answer=='fallback' or report['status']=='rejected_fallback'
    assert all(not item.get('observation_time_projected') for item in report['attempts'])
    context[0]['data']['records'].append(dict(context[0]['data']['records'][0],
        interface='Ethernet8',timestamp='2026-10-18T00:30:00Z'))
    _,report=asyncio.run(synthesize(Model(original),'test',question,context,evidence,{},'fallback'))
    assert report['status']=='rejected_fallback'


def test_source_health_answer_preserves_statuses_time_and_override_disagreement():
    context=[{'tool':'network.state','status':'success','evidence_ids':['health'],'data':{'records':[
        {'kind':'source_health','hostname':'Oak','timestamp':'2026-10-18T01:00:00Z',
            'sources':{'telemetry':'AVAILABLE','syslog':'ERROR'},'physical_collection_performed':False}],
        'effective_source_statuses':{'telemetry':{'status':'STALE','captured_at':'2026-10-18T01:00:00Z'},
            'syslog':{'status':'ERROR','captured_at':'2026-10-18T01:00:00Z'}}}}]
    evidence=[Evidence(id='health',source='Development source health',origin='simulated')]
    packets=[]
    class Model:
        async def generate(self,messages,**kwargs):
            packets.append(messages[-1]['content']);raise ValueError('Controlled unavailable model')
        def available(self,purpose):return False
    answer,report=asyncio.run(synthesize(Model(),'test','Which source categories are stale or in error?',context,evidence,{},'fallback'))
    assert packets==[]  # Availability metadata cannot authorize device-health prose.
    assert all(token in answer for token in ['telemetry','STALE','AVAILABLE','syslog','ERROR','2026-10-18T01:00:00Z'])
    assert 'disagree' in answer.lower() and 'No collection from physical devices' in answer
    assert report['status']=='source_metadata_fallback' and not report['model_synthesis']
    bad='The logical sources that are stale or in error are `telemetry` and `syslog`, both with an authored health claim of **STALE** and an effective selected-revision status of **STALE**. Recorded at 2026-10-18T01:00:00Z. [S1]'
    errors=check_candidate(bad,context,evidence,{},'Which source categories are stale or in error?')
    assert any('category' in error and 'match' in error for error in errors)
    good='Recorded at 2026-10-18T01:00:00Z: telemetry authored health claim AVAILABLE; telemetry effective status STALE. These disagree. syslog authored health claim ERROR; syslog effective status ERROR. [S1]'
    assert not check_candidate(good,context,evidence,{},'Which source categories are stale or in error?')


def test_source_health_disagreement_accepts_negative_agreement_and_rejects_denial():
    context=[{'tool':'network.state','status':'success','data':{'records':[
        {'kind':'source_health','timestamp':'2026-10-18T01:01:00Z','sources':{'telemetry':'AVAILABLE'}}],
        'effective_source_statuses':{'telemetry':{'status':'ERROR'}}}}]
    base='The effective status of the telemetry source is ERROR, and the authored health claim is AVAILABLE. Captured at 2026-10-18T01:01:00Z. '
    for explanation in ['The authored claim does not agree with the effective status.',
                        'These statuses do not match.', 'They are not the same.']:
        assert not check_candidate(base+explanation,context,[],{},'Does the source health record agree?')
    for explanation in ['There is no disagreement between these statuses.', 'The two statuses agree.']:
        assert check_candidate(base+explanation,context,[],{},'Does the source health record agree?')


def test_source_health_projection_keeps_actual_time_without_releasing_model_time_claims():
    context=[{'tool':'network.state','status':'success','evidence_ids':['health'],'data':{'records':[
        {'kind':'source_health','timestamp':'2026-10-18T01:01:00Z','sources':{'telemetry':'AVAILABLE'},'physical_collection_performed':False}],
        'effective_source_statuses':{'telemetry':{'status':'ERROR'}}}}]
    evidence=[Evidence(id='health',source='Development source health',origin='simulated')]
    original='telemetry effective status ERROR; telemetry authored health claim AVAILABLE. These statuses do not match.'
    class Model:
        def __init__(self,text):self.text=text
        async def generate(self,*args,**kwargs):return json.dumps({'answer':self.text,'sources':['S1'],'hypotheses':[]}), 'test'
        def available(self,purpose):return True
    answer,report=asyncio.run(synthesize(Model(original),'test','Read source health.',context,evidence,{},'fallback'))
    assert report['status']=='source_metadata_fallback' and not report['model_synthesis']
    assert '2026-10-18T01:01:00Z' in answer
    assert report['attempts']==[]
    wrong=original+' Captured at 2026-10-18T02:00:00Z.'
    bad_answer,bad=asyncio.run(synthesize(Model(wrong),'test','Read source health.',context,evidence,{},'fallback'))
    assert bad['status']=='source_metadata_fallback' and bad['attempts']==[]
    assert '2026-10-18T02:00:00Z' not in bad_answer
    assert check_candidate(wrong,context,evidence,{},'Read source health.')

def test_missing_section_in_returned_capture_does_not_establish_absence_on_device():
    from llm.orchestration.synthesis import comparison_gap_errors
    gaps=[{'topic':'BGP configuration','pattern':r'\b(?:BGP|configuration|capture)\b',
        'reason':'No literal BGP marker found in returned capture; no device-level absence established.'}]
    for wrong in [
        "R1's saved BGP settings were not found in the configuration capture, indicating that the device does not have a BGP configuration.",
        'The router has no BGP configuration.',
        'BGP is not configured on R1.',
    ]:assert comparison_gap_errors(wrong,gaps)
    assert not comparison_gap_errors('No literal BGP section was found in these captures. This does not establish that the device has no BGP configuration.',gaps)


@pytest.mark.parametrize('wrapped',[False,True])
def test_insufficient_protocol_comparison_uses_verified_partial_records_without_speculative_synthesis(wrapped):
    context=[{'tool':'network.configuration','status':'success','evidence_ids':['cfg'],'data':{'records':[
        {'hostname':'R1','timestamp':'2026-10-18T01:00:00Z','current':False,'config_text':'hostname R1\n'}]}},
        {'tool':'network.state','status':'unavailable','data':{'records':[]}},
        {'tool':'network.syslog','status':'success','evidence_ids':['log'],'data':{'records':[
        {'hostname':'R1','timestamp':'2026-10-18T00:59:00Z','message':'Recorded receive errors','severity':'warning'}]}}]
    if wrapped:context[-1]['data']={'sources':[{'status':'success','origin':'simulated','data':context[-1]['data']}]}
    from llm.orchestration.synthesis import protocol_comparison_material
    projected=protocol_comparison_material(context,'Compare R1 saved BGP settings with observed peers and log messages.',[])
    assert projected[-1]['records'][0]['message']=='Recorded receive errors'
    evidence=[Evidence(id=key,source=key,origin='simulated') for key in ['cfg','log']]
    class NoSynthesis:
        async def generate(self,*args,**kwargs):raise AssertionError('Incomplete comparison inputs must not authorize a synthesized comparison verdict')
    answer,report=asyncio.run(synthesize(NoSynthesis(),'test','Compare R1 saved BGP settings with observed peers and log messages.',context,evidence,{},'RAW_DUMP'))
    assert report['status']=='insufficient_evidence_fallback' and not report['model_synthesis']
    assert all(value in answer for value in ['cannot establish','BGP','Recorded receive errors','2026-10-18T00:59:00Z','simulated'])
    assert 'RAW_DUMP' not in answer and 'identical' not in answer


def test_interface_projection_retains_requested_observed_prefix_and_complete_states():
    from llm.orchestration.synthesis import interface_observations,check_candidate
    from llm.gateway_models import Evidence
    context=[{'tool':'network.state','status':'success','evidence_ids':['state'],
        'data':{'records':[{'kind':'interface_state','hostname':'LAB-R1','interface':'GigabitEthernet0/1',
            'prefix':'10.73.0.1/30','admin_status':'up','oper_status':'down','timestamp':'2026-10-18T01:00:00Z','current':True}]}}]
    question='Read device and interface state for LAB-R1: exact prefix, administrative versus operational states and observation time.'
    facts=interface_observations(context,question)
    assert facts[0]['prefix']=='10.73.0.1/30'
    omitted='GigabitEthernet0/1; operational down; recorded2026-10-18T01:00:00Z. [S1]'
    assert check_candidate(omitted,context,[Evidence(id='state',source='development.state',origin='simulated')],{},question)

def test_ordinary_nested_counter_projection_preserves_field_value_association():
    from llm.orchestration.synthesis import metric_observations,counter_field_errors
    context=[{'tool':'network.telemetry','status':'success','data':{'sources':[{'data':{'records':[
        {'hostname':'R1','interface':'Gi0/1','time':'2026-10-23T00:02:53Z','errors':13.0,'discards':4.0}
    ]}}]}}]
    facts=metric_observations(context)
    assert {f['metric']:f['samples'][0]['value'] for f in facts}=={'errors':13.0,'discards':4.0}
    question='Read the errors and discards counters.'
    assert counter_field_errors('There are 4 errors and 13 discards.',facts,question)
    assert counter_field_errors('The errors and discards counters are 4.0.',facts,question)
    assert not counter_field_errors('R1 Gi0/1 has 13 errors and 4 discards in the recorded sample.',facts,question)
    assert not counter_field_errors('Recorded errors: 13.0; discards: 4.',facts,question)
    assert not counter_field_errors('The recorded errors counter for R1 Gi0/1 is 13.0. The discards counter is 4.0.',facts,question)
    assert counter_field_errors('The errors counter for R1 Gi0/1 is 4.0. The discards counter is 13.0.',facts,question)

