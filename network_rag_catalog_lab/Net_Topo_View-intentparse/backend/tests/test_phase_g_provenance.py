"""Plural references and source attribution use owned retrievals, not model prose."""
import sys,json
import pytest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm.gateway_references import resolve_read
from llm.gateway_findings import network_answer
from llm.gateway_models import Evidence
from unittest.mock import patch
import asyncio
from unittest.mock import AsyncMock


def test_explicit_published_method_fields_are_authoritative_reads():
    from llm.gateway_references import published_knowledge_read
    for prompt in ['Explain the fields required by the published configure_ospf method.',
            'Which inputs does the published remove_static_route method accept?',
            'What does published Junos knowledge require to remove a qualified static next hop?',
            'Describe published knowledge about BGP timers.',
            'Describe the catalog method fields for a future_operation.']:
        result=published_knowledge_read(prompt,{'devices':[]})
        assert result and result['network_domains']==['knowledge']
    for prompt in ['How does OSPF work?', 'Create a configuration using the published method.',
            'Explain the published method in the open file.']:
        assert published_knowledge_read(prompt,{'devices':[]}) is None


def test_explicit_reader_receives_request_even_when_legacy_router_classifies_general():
    from llm.gateway_network import network_context
    from llm.gateway_models import ToolResult
    registry=type('Registry',(),{'invoke':AsyncMock(return_value=ToolResult(status='unavailable'))})()
    question='Explain the fields required by the published configure_ospf method.'
    with patch('llm.gateway_services.inventory_snapshot',return_value={'devices':[]}):
        asyncio.run(network_context(object(),registry,None,question,domains_override=['knowledge']))
    args=registry.invoke.call_args.args
    assert args[0]=='knowledge.search' and args[1]['query']==question


def test_named_registered_source_read_cannot_be_replaced_by_attachment_guess():
    from llm.gateway_routing import select_context
    from development.source_registry import BY_KEY
    generator=AsyncMock(return_value=(json.dumps({'intent':'analyze_files','use_attachments':True,
        'information_needs':[]}), 'test-model'))
    with patch.dict('os.environ',{'COGNISHIELD_AI_PLANNING':'1'}),patch('llm.gateway_semantics.semantic_hint',AsyncMock(return_value={'intent':'analyze_files','domains':[]})):
        result=asyncio.run(select_context('Read the source health records. Which logical sources are stale or in error?',
            'test-model','floating',None,[{'name':'context.pdf'}],[],inventory={
                'devices':[],'logical_source_categories':list(BY_KEY)},generate_fn=generator))
    assert result.network_domains==['state'] and not result.use_attachments
    assert result.source_requests['state']['source_categories']==['source_health']


def test_health_status_attribute_is_not_a_request_for_metric_samples():
    from development.source_registry import explicit_read_sources,BY_KEY
    request='Compare the source health record telemetry claim with the selected scenario effective telemetry source status.'
    assert explicit_read_sources(request,BY_KEY)==['source_health']
    assert set(explicit_read_sources('Read source health and telemetry samples.',BY_KEY))=={'source_health','telemetry'}
    assert explicit_read_sources('Read source health in this uploaded document.',BY_KEY)==[]
    from llm.orchestration.planning import IntentPlan,InformationNeed,select_logical_sources
    plan=IntentPlan(intent='explain',information_needs=[InformationNeed(domain='state',question='source health claim'),
        InformationNeed(domain='telemetry',question='effective telemetry source status')])
    result,_=asyncio.run(select_logical_sources(request,plan,AsyncMock(),None,list(BY_KEY)))
    assert {need.domain for need in result.information_needs}=={'state'}
    plan.information_needs[-1]=InformationNeed(domain='telemetry',question='CPU measurement samples')
    result,_=asyncio.run(select_logical_sources('Read source health and telemetry samples.',plan,AsyncMock(),None,list(BY_KEY)))
    assert {need.domain for need in result.information_needs}=={'state','telemetry'}


def test_source_name_separators_and_health_subject_do_not_select_measurements():
    from development.source_registry import explicit_read_sources,BY_KEY
    for source_name in ['source health','source-health','source_health','source–health']:
        request='Read only the '+source_name+' records for telemetry. What is its effective status?'
        assert explicit_read_sources(request,BY_KEY)==['source_health']
    assert set(explicit_read_sources('Read source-health and telemetry samples.',BY_KEY))=={'source_health','telemetry'}
    assert explicit_read_sources('Read interface-metrics.',BY_KEY)==['interface_metrics']
    assert explicit_read_sources('Read current_configuration.',BY_KEY)==['running_configs']


def test_named_network_source_supersedes_previous_pdf_pronouns():
    from llm.gateway_routing import select_context
    from development.source_registry import BY_KEY
    previous={'context_coverage':{'routing':{'attachments':True},'files':{'selected_documents':[{'name':'old.pdf','origin':'user_supplied'}]}}}
    request='Read only the source-health records for telemetry. What is its effective status, does the authored health record agree, and when was the health record captured?'
    inventory={'devices':[],'logical_source_categories':list(BY_KEY)}
    resolved=resolve_read(request,previous,inventory)
    assert not resolved or not resolved.get('documents')
    generator=AsyncMock(return_value=(json.dumps({'intent':'analyze_files','use_attachments':True,'information_needs':[]}),'test'))
    with patch.dict('os.environ',{'COGNISHIELD_AI_PLANNING':'1'}):
        result=asyncio.run(select_context(request,'test','studio',None,[{'name':'old.pdf'}],[],previous=previous,
            inventory=inventory,generate_fn=generator))
    assert result.network_domains==['state'] and not result.use_attachments
    assert result.source_requests['state']['source_categories']==['source_health']


def test_exact_published_identity_excludes_other_contracts_and_unknown_methods(tmp_path):
    from llm.gateway_knowledge import documentation_context
    release=tmp_path/'storage/catalog_releases';release.mkdir(parents=True)
    (release/'active.json').write_text('{}')
    (release/'retrieval_documents.json').write_text(json.dumps([
        {'id':'future_operation','page_content':'Operation future_operation. Published fields and requirements.'},
        {'id':'different_operation','page_content':'Operation different_operation. Published fields and requirements.'}]))
    invoke=type('Invoke',(),{'__call__':lambda self,action,args,actor:{'data':{'operations':[]}}})()
    with patch('local_providers.knowledge.knowledge_root',return_value=tmp_path),\
            patch('llm.gateway_knowledge.read_release',return_value=(release,{}, {'release_id':'test-release'})),\
            patch('local_providers.knowledge.invoke',side_effect=invoke),\
            patch('lab_config.BACKEND_DIR',tmp_path):
        rows,evidence=documentation_context('Explain the fields required by the published future_operation method.')
        assert len(rows)==len(evidence)==1 and evidence[0].source=='published:future_operation'
        assert documentation_context('Explain the fields required by the published missing_operation method.')==([],[])


def test_published_contract_answer_cites_its_authorized_source():
    from llm.orchestration.investigation import knowledge_text
    evidence=[Evidence(id='e',source='published:future_operation',origin='stored')]
    context=[{'tool':'knowledge.search','status':'success','data':[{'source':'published:future_operation','evidence_id':'e',
        'published_requirements':{'operations':[{'operation_id':'future_operation','description':'The published method.',
            'schema':{'required':['addresses'],'properties':{}},'profiles':[]}]}}]}]
    answer=knowledge_text(context,evidence)
    assert '[S1]' in answer and '`addresses`' in answer
    missing=knowledge_text([{'tool':'knowledge.search','status':'unavailable','data':[]}],[])
    assert 'No operation fields were inferred' in missing


def test_source_refinement_cannot_expand_a_configuration_lookup_into_unrequested_domains():
    from llm.orchestration.planning import IntentPlan,InformationNeed,select_logical_sources
    plan=IntentPlan(intent='answer',information_needs=[InformationNeed(domain='configuration',question='current config',source_scope='current')])
    generate=AsyncMock(return_value=('{"source_categories":["running_configs","controller_state","topology_planned"]}','test'))
    selected,trace=asyncio.run(select_logical_sources('Explain Oak-Router configuration.',plan,generate,'test',
        ['running_configs','controller_state','topology_planned']))
    assert selected==plan and trace['status']=='invalid_fallback'
    offered=json.loads(generate.call_args.args[0][1]['content'])['catalog']
    assert {row['source'] for row in offered}=={'running_configs'}


def test_known_network_subject_reaches_semantic_planner_despite_general_similarity():
    from llm.gateway_routing import select_context
    question='Look up recent anomalies associated with Maple-Edge.'
    inventory={'devices':[{'id':7,'hostname':'Maple-Edge','management_ip':'192.0.2.7','aliases':[],'interfaces':[]}]}
    generate=AsyncMock(return_value=(json.dumps({'intent':'answer','information_needs':[{'domain':'incidents','question':'recent anomalies'}]}),'test'))
    with patch.dict('os.environ',{'COGNISHIELD_AI_PLANNING':'1'}),\
            patch('llm.gateway_semantics.semantic_hint',AsyncMock(return_value={'intent':'answer','domains':[]})):
        route=asyncio.run(select_context(question,'test','floating',None,[],[],inventory=inventory,generate_fn=generate))
    assert generate.await_count==1 and route.network_domains==['incidents'] and route.device_refs==['7']


def test_literal_configuration_scope_uses_the_matching_authoritative_record_type():
    from llm.orchestration.planning import IntentPlan,InformationNeed,select_logical_sources
    for scope,question,key in [('current','Show the current running configuration.','running_configs'),
            ('historical','Read the saved configuration.','config_snapshots')]:
        plan=IntentPlan(intent='answer',information_needs=[InformationNeed(domain='configuration',question=question,source_scope=scope)])
        generate=AsyncMock(return_value=('{"source_categories":["config_drift"]}','test'))
        selected,trace=asyncio.run(select_logical_sources(question,plan,generate,'test',
            ['running_configs','config_snapshots','config_drift']))
        assert selected.information_needs[0].source_categories==[key]
        assert trace['status']=='authoritative_configuration_scope' and generate.await_count==0


def test_configuration_source_metadata_does_not_request_other_observations():
    from llm.orchestration.planning import IntentPlan,InformationNeed,select_logical_sources
    from llm.gateway_network import explicit_configuration_scope,route_network
    question='Show Maple-Edge current running configuration and its source availability and capture time.'
    assert explicit_configuration_scope(question)=='current'
    plan=IntentPlan(intent='answer',information_needs=[InformationNeed(domain='configuration',question='configuration',source_scope='current'),InformationNeed(domain='state',question='source availability')])
    selected,trace=asyncio.run(select_logical_sources(question,plan,AsyncMock(),'test',['running_configs','source_health']))
    assert [need.domain for need in selected.information_needs]==['configuration']
    assert selected.information_needs[0].source_categories==['running_configs']
    assert route_network('Show the current running configuration for Unrecorded-Edge.',{'devices':[]})[1]['device_refs']==['Unrecorded-Edge']
    compound=IntentPlan(intent='answer',information_needs=[InformationNeed(domain='configuration',question='configuration',source_scope='current'),InformationNeed(domain='syslog',question='logs')])
    selected,_=asyncio.run(select_logical_sources('Show Maple-Edge current configuration and syslogs.',compound,AsyncMock(return_value=('{"source_categories":[]}','test')),'test',['running_configs','syslog']))
    assert {need.domain for need in selected.information_needs}=={'configuration','syslog'}


def test_named_change_source_precedes_generic_capture_scope():
    from llm.orchestration.planning import IntentPlan,InformationNeed,select_logical_sources
    prompt='Show only recorded configuration changes for Maple-Edge, including capture references and literal diff.'
    plan=IntentPlan(intent='answer',information_needs=[InformationNeed(domain='configuration',question='changes',source_scope='historical')])
    generate=AsyncMock()
    selected,_=asyncio.run(select_logical_sources(prompt,plan,generate,'test',['running_configs','config_snapshots','config_changes']))
    assert selected.information_needs[0].source_categories==['config_changes']
    assert generate.await_count==0


def test_recorded_configuration_diff_preserves_lines_and_capture_references():
    diff='--- saved\n+++ current\n@@ -1 +1 @@\n-description Old\n+description New\n'
    result=network_answer([{'tool':'network.configuration','status':'success','data':{'records':[{'kind':'configuration_change','hostname':'Maple-Edge','timestamp':'2026-10-18T01:00:00Z','diff':diff,'change_summary':'Description changed in the recorded comparison','saved_record_id':'saved-edge','current_record_id':'active-edge','semantic_or_device_validation':'not_performed'}]},'evidence_ids':[]}],[],question='Show the recorded configuration change and literal diff.')
    assert '```diff\n'+diff in result
    assert 'Maple-Edge' in result and 'saved-edge' in result and 'active-edge' in result
    assert 'not_performed' in result and 'Description changed in the recorded comparison' in result


def test_explicit_temporal_correction_precedes_logical_source_selection():
    from llm.orchestration.planning import propose
    inventory={'devices':[{'id':7,'hostname':'Oak-Router','aliases':[]}], 'scenario':{'id':'test'},
        'logical_source_categories':['running_configs','config_snapshots','config_drift']}
    generate=AsyncMock(return_value=(json.dumps({'intent':'answer','information_needs':[{'domain':'configuration','question':'configuration','source_scope':'historical'}]}),'test'))
    route=asyncio.run(propose('Show Oak-Router current configuration.','test','floating',None,[],[],inventory,generate,True))
    assert route.source_requests['configuration']=={'source_scope':'current','source_categories':['running_configs']}
    assert route.planning['source_scope_adjustments'] and generate.await_count==1


def test_explicit_source_use_constraint_does_not_include_the_rejected_source():
    from llm.orchestration.planning import IntentPlan,InformationNeed,select_logical_sources
    plan=IntentPlan(intent='answer',information_needs=[InformationNeed(domain='state',question='protocol neighbors')])
    generate=AsyncMock(return_value=('{"source_categories":["simulation"]}','test'))
    selected,trace=asyncio.run(select_logical_sources('Read OSPF neighbors. Use the protocol observation source, not the separately declared simulation.',plan,generate,'test',['protocol_state','simulation']))
    assert selected.information_needs[0].source_categories==['protocol_state']
    assert trace['status']=='explicit_registry_source_scope' and generate.await_count==0
    # Merely saying information is simulated is not a source-selection directive.
    selected,trace=asyncio.run(select_logical_sources('Which protocol neighbors are recorded? These are not physical measurements.',plan,generate,'test',['protocol_state','simulation']))
    assert trace['status']=='validated_model_source_selection' and generate.await_count==1


def test_model_cannot_discard_resolved_followup_device_and_source_constraints():
    from llm.gateway_routing import select_context
    inventory,previous=materials();inventory['scenario']={'id':'test'}
    inventory['logical_source_categories']=['protocol_state','simulation']
    previous['context_coverage']['retrieval'].update(domains=['state'],device_refs=['7'],interface_refs=[],attributes=[],entities=[],
        source_requests={'state':{'source_scope':'observed','source_categories':['protocol_state']}})
    generate=AsyncMock(side_effect=[(json.dumps({'intent':'answer','information_needs':[{'domain':'state','question':'Init meaning','source_scope':'observed'}],'use_history':False}),'test'),
        ('{"source_categories":["simulation"]}','test')])
    with patch.dict('os.environ',{'COGNISHIELD_AI_PLANNING':'1'}):
        route=asyncio.run(select_context('What does this Init state imply about the OSPF adjacency? Keep using the same authored source.',
            'test','studio',None,[],[],previous=previous,inventory=inventory,generate_fn=generate))
    assert route.device_refs==['7'] and route.use_history
    assert route.source_requests['state']['source_categories']==['protocol_state']
    assert route.planning['reference_scope_adjustment']['model_use_history'] is False


def test_checkpoint_scope_references_are_validated_without_persisting_tool_payloads():
    from llm.orchestration.memory import InvestigationMemory
    import pytest
    scope={'state':{'source_scope':'observed','source_categories':['protocol_state']}}
    memory=InvestigationMemory.model_validate({'source_requests':scope})
    assert InvestigationMemory.model_validate_json(memory.model_dump_json()).source_requests==scope
    assert InvestigationMemory.model_validate({}).source_requests=={}  # Additive schema1 field.
    for invalid in [{'state':{'sql':'SELECT *'}},{'state':{'source_categories':['config_snapshots']}},
            {'shell':{'source_scope':'current'}},{'state':{'source_categories':['not-in-registry']}}]:
        with pytest.raises(ValueError):InvestigationMemory(source_requests=invalid)


def materials():
    inventory={'devices':[{'id':7,'hostname':'Oak-Router','management_ip':'192.0.2.7','vendor':'juniper','aliases':[],
        'interfaces':[{'id':70,'name':'ge-0/0/0.0','ip_address':'10.2.0.1/30'},{'id':71,'name':'lo0.0','ip_address':'198.51.100.7/32'}]}]}
    previous={'context_coverage':{'retrieval':{'domains':['inventory'],'device_refs':['7'],'interface_refs':[],
        'attributes':['interfaces'],'entities':[{'device_id':'7','interface_id':'70'},{'device_id':'7','interface_id':'71'}]}}}
    return inventory,previous


def test_plural_source_question_rechecks_the_owned_list_without_link_guessing():
    inventory,previous=materials()
    result=resolve_read('Are those port names taken from inventory or guessed from links?',previous,inventory)
    assert 'question' not in result
    assert result['domains']==['inventory'] and result['interface_refs']==['70','71']
    assert {'interfaces','provenance'}<=set(result['attributes'])


def test_plural_address_read_and_ordinal_keep_the_correct_scope():
    inventory,previous=materials()
    result=resolve_read('What addresses are recorded for these interfaces?',previous,inventory)
    assert 'question' not in result and result['interface_refs']==['70','71']
    result=resolve_read('What address is recorded for the first one?',previous,inventory)
    assert result['interface_refs']==['70']
    assert resolve_read('In general, what do those interface names mean?',previous,inventory) is None


def test_explicit_replacement_excludes_named_devices_even_without_previous_result():
    inventory,_=materials()
    inventory['devices'].append({'id':8,'hostname':'Pine-Router','aliases':[],'interfaces':[]})
    for previous in [None,{'context_coverage':{'retrieval':{'domains':['inventory'],'device_refs':['7'],'attributes':['interfaces']}}}]:
        result=resolve_read('I meant Pine-Router, not Oak-Router; list that device’s recorded ports.',previous,inventory)
        assert result['device_refs']==['Pine-Router'] and result['attributes']==['interfaces']
        assert result['use_history']==bool(previous)
    result=resolve_read('List the recorded ports, not Oak-Router.',None,inventory)
    assert 'question' in result and 'device_refs' not in result
    # Negated assumptions are not named-device replacement instructions.
    assert resolve_read('Do not assume this proves connectivity. Show Oak-Router recorded ports.',None,inventory)['device_refs']==['Oak-Router']


def test_inventory_provenance_answer_explains_the_reader_instead_of_only_listing():
    inventory,_=materials()
    evidence=[Evidence(id='record',source='inventory',origin='stored')]
    answer=network_answer([{'tool':'inventory.read','status':'success','data':inventory,'evidence_ids':['record']}],evidence,['interfaces','provenance'],[])
    assert 'inventory records' in answer.lower() and 'topology' in answer.lower()
    assert 'ge-0/0/0.0' in answer and 'lo0.0' in answer and '[S1]' in answer


def test_knowledge_category_retains_published_reader_instead_of_scenario_substitution():
    from llm.gateway_network import NetworkReader,NetworkQuery
    reader=NetworkReader(object())
    evidence=[Evidence(id='published',source='Published operation',origin='stored',authority='published_knowledge')]
    with patch.object(reader,'devices',return_value=([],{'devices':[]})),patch('llm.gateway_knowledge.documentation_context',return_value=([{'text':'Published OSPF requirements'}],evidence)):
        result=reader.read('knowledge',NetworkQuery(query='Explain published OSPF requirements',source_categories=['knowledge']),None)
    assert result.status=='success' and result.evidence==evidence
def test_scenario_knowledge_reference_routes_to_existing_published_reader():
    from llm.gateway_routing import select_context
    prompt='Explain the published operation requirements selected by the scenario knowledge reference. Read only this scenario knowledge reference.'
    route=asyncio.run(select_context(prompt,None,'floating',None,[],[],inventory={'devices':[],'logical_source_categories':['knowledge']}))
    assert route.network_domains==['knowledge']
    assert route.source_requests['knowledge']['source_categories']==['knowledge']
    from llm.orchestration.investigation import contextual_route
    from llm.orchestration.memory import InvestigationMemory
    actual=contextual_route(prompt,InvestigationMemory(),None,{'devices':[],'logical_source_categories':['knowledge']})
    assert actual.source_requests['knowledge']['source_categories']==['knowledge']


@pytest.mark.parametrize('status,authority', [('AVAILABLE','published_operation_documentation'),('ERROR','published_operation_documentation'),('AVAILABLE','reference_only')])
def test_scenario_knowledge_reference_is_request_metadata_not_replacement_knowledge(tmp_path,status,authority):
    from llm.gateway_network import NetworkReader,NetworkQuery
    from llm.gateway_models import Evidence
    from development.starter import starter_bundle
    from local_providers.development import ScenarioManager
    bundle=starter_bundle();bundle['sources']['knowledge'].update(status=status)
    bundle['sources']['knowledge']['data']['query']='Explain published remove_static_route method requirements'
    manager=ScenarioManager(tmp_path/'state.json')
    draft=manager.save_draft(bundle,owner='reference-owner',expected=None)
    receipt=manager.validate_draft(draft['draft_id'],owner='reference-owner',expected=1)
    manager.activate_draft(draft['draft_id'],owner='reference-owner',expected=1,expected_active=manager.snapshot()[1]['source_revision'],validation_hash=receipt['validation_hash'])
    reader=NetworkReader(object())
    published=Evidence(id='published',source='published:remove_static_route',origin='stored',authority=authority,source_revision='immutable-release')
    with patch.object(reader,'devices',return_value=([],{'devices':[]})),patch('local_providers.development.active_for',return_value=manager),\
        patch('llm.gateway_knowledge.documentation_context',return_value=([{'source':'published:remove_static_route','evidence_id':'published','text':'Actual published requirements'}],[published])) as lookup:
        result=reader.read('knowledge',NetworkQuery(query='Read the scenario knowledge reference',source_categories=['knowledge']),None)
    if status=='ERROR':
        assert result.status=='error';lookup.assert_not_called()
    elif authority=='reference_only':
        lookup.assert_called_once();assert result.status=='unavailable' and result.data==[]
        assert all(e.authority!='reference_only' for e in result.evidence)
    else:
        lookup.assert_called_once_with(bundle['sources']['knowledge']['data']['query'])
        assert result.status=='success' and result.evidence[0]==published
        assert result.data[0]['scenario_reference']['query']==bundle['sources']['knowledge']['data']['query']
        assert result.data[0]['source']=='published:remove_static_route'
    assert any(e.origin=='simulated' and e.captured_at for e in result.evidence)
