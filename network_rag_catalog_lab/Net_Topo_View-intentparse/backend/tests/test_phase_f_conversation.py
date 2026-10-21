"""Concept questions do not authorize context reads or engineering effects."""
import asyncio
import json
import os
from pathlib import Path
import sys
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm.gateway_references import resolve_read
from llm.gateway_routing import select_context

INVENTORY={'devices':[{'id':91,'hostname':'Leaf-Alder','aliases':[],
    'management_ip':'192.0.2.91','interfaces':[]}]}


def test_explicit_artifact_preparation_is_v9_authoring_not_an_interface_attribute_read():
    from llm.gateway_routing import requested_authoring_artifact
    prompt='Prepare a native static route and an interface description for Leaf-Alder.'
    assert requested_authoring_artifact(prompt)=='native'
    assert resolve_read(prompt,None,INVENTORY) is None
    model=AsyncMock()
    with patch.dict(os.environ,{'COGNISHIELD_AI_PLANNING':'1'}):
        route=asyncio.run(select_context(prompt,'test','studio',{'path':'open.cfg'},[],[],inventory=INVENTORY,generate_fn=model))
    assert route.intent=='generate_native' and not route.use_editor and not route.network_domains
    model.assert_not_awaited()
    for read in ['Explain how to prepare a native configuration.','Prepare a comparison of the stored configuration and published requirements.','Show the native interface description in the saved configuration.']:
        assert requested_authoring_artifact(read) is None


@pytest.mark.parametrize('attribute',['interface-operational-state','interface operational state',
    'port administrative status','oper_status','interfaces administratively down'])
def test_qualified_operational_attributes_reach_state_reader_not_inventory_shortcut(attribute):
    from llm.gateway_network import route_network
    prompt='Could you obtain '+attribute+' records for Leaf-Alder?'
    assert 'state' in route_network(prompt,INVENTORY)[0]
    generate=AsyncMock(return_value=(json.dumps({'intent':'answer','information_needs':[
        {'domain':'state','question':'Requested operational interface observations'}]}),'test'))
    with patch.dict(os.environ,{'COGNISHIELD_AI_PLANNING':'1'}):
        route=asyncio.run(select_context(prompt,'test','floating',None,[],[],inventory=INVENTORY,generate_fn=generate))
    assert route.network_domains==['state'] and route.device_refs==['91']
    generate.assert_awaited()


def test_operational_attribute_words_alone_do_not_request_network_evidence():
    from llm.gateway_network import route_network
    assert route_network('Explain interface operational state in general.',INVENTORY)[0]==[]
    assert resolve_read('Set the interface administrative state on Leaf-Alder.',None,INVENTORY) is None


def test_unscoped_attribute_words_do_not_turn_concepts_into_inventory_reads():
    assert resolve_read('Why can an Ethernet interface be enabled but still have no carrier?',None,INVENTORY) is None
    assert resolve_read('Explain the distinction between interface addresses and management addresses.',None,INVENTORY) is None
    assert resolve_read('List the interface addresses in our stored inventory.',None,INVENTORY)['domains']==['inventory']


def test_named_diagnostic_paraphrase_cannot_bypass_authoritative_readers():
    prompt='Find the supported cause of the failed modeled path between Leaf-Alder and its peer.'
    resolved=resolve_read(prompt,None,INVENTORY)
    assert resolved and {'inventory','topology','state','configuration'}<=set(resolved['domains'])
    assert resolve_read('Find a useful metaphor for explaining network paths.',None,INVENTORY) is None
    from llm.orchestration.investigation import is_investigation
    assert is_investigation(prompt)
    generate=AsyncMock(return_value=(json.dumps({'intent':'answer','information_needs':[
        {'domain':domain,'question':'Requested diagnostic evidence'} for domain in ['inventory','topology','state','configuration']]}),'test'))
    with patch.dict(os.environ,{'COGNISHIELD_AI_PLANNING':'1'}),patch('llm.gateway_semantics.semantic_hint',AsyncMock(return_value={'intent':'answer','domains':[]})):
        route=asyncio.run(select_context(prompt,'test','floating',None,[],[],inventory=INVENTORY,generate_fn=generate))
    assert {'inventory','topology','state','configuration'}<=set(route.network_domains)
    assert route.planning['mode']=='validated_model_plan'


def test_instruction_negation_is_not_a_device_identity_correction():
    inventory={'devices':INVENTORY['devices']+[{'id':92,'hostname':'Leaf-Birch','aliases':[],
        'management_ip':'192.0.2.92','interfaces':[]}]}
    previous={'context_coverage':{'retrieval':{'domains':['inventory'],'device_refs':['92'],
        'interface_refs':[],'attributes':['addresses'],'entities':[{'device_id':'92'}]}}}
    prompt='Find the supported cause of any communication problem between Leaf-Alder and Leaf-Birch using recorded evidence only. Do not assume that missing measurements mean a failure.'
    result=resolve_read(prompt,previous,inventory)
    assert not result.get('question') and set(result['device_refs'])=={'Leaf-Alder','Leaf-Birch'}
    correction=resolve_read('I meant Leaf-Alder, not Leaf-Birch.',previous,inventory)
    assert correction['device_refs']==['Leaf-Alder'] and correction['use_history']


@pytest.mark.parametrize('prompt,wrong_intent',[
    ('Does a routing process identifier have to equal an OSPF router identifier?','generate_native'),
    ('Give three tips for making engineering notes clearer.','clarify'),
    ('What is the difference between an intended design and a captured observation?','clarify'),
    ('Why are different protocol identifiers useful?','edit')])
def test_unbound_concept_or_advice_question_cannot_become_an_engineering_effect(prompt,wrong_intent):
    generate=AsyncMock(return_value=(json.dumps({'intent':wrong_intent}),'test'))
    with patch.dict(os.environ,{'COGNISHIELD_AI_PLANNING':'1'}),patch('llm.gateway_semantics.semantic_hint',AsyncMock(return_value=None)):
        route=asyncio.run(select_context(prompt,'test','floating',None,[],[],inventory=INVENTORY,generate_fn=generate))
    assert route.intent=='answer'
    assert not route.network_domains and not route.use_editor and not route.use_attachments and not route.use_history


def test_missing_reference_still_clarifies_without_inventing_a_subject():
    route=asyncio.run(select_context('What is its IP?', 'test','floating',None,[],[],inventory=INVENTORY,
        generate_fn=AsyncMock(side_effect=AssertionError('Reference boundary should resolve before inference'))))
    assert route.intent=='clarify'


def test_explicit_context_exclusion_routes_the_remaining_request_only():
    from types import SimpleNamespace
    model=AsyncMock(return_value=('{"intent":"answer"}','test'))
    editor=SimpleNamespace(path='playbooks/old.cfg')
    with patch.dict(os.environ,{'COGNISHIELD_AI_PLANNING':'0'}),patch('llm.gateway_semantics.semantic_hint',AsyncMock(return_value=None)):
        route=asyncio.run(select_context('Forget the open configuration for a moment: calculate thirteen squared.',
            'test','studio',editor,[{'name':'old.pdf'}],[{'role':'user','content':'OLD_PRIVATE_TOPIC'}],inventory=INVENTORY,generate_fn=model))
    assert route.intent=='answer'
    assert not route.use_editor and not route.use_attachments and not route.use_history and not route.network_domains
    supplied=str(model.call_args.args)
    assert 'OLD_PRIVATE_TOPIC' not in supplied and 'An editor is open.' not in supplied
    assert 'open configuration for a moment' not in supplied


def test_selected_protocol_axioms_reject_false_equivalence_but_keep_negation():
    from llm.orchestration.synthesis import general_protocol_errors
    assert general_protocol_errors('A routing process identifier typically must equal an OSPF router identifier.')
    assert general_protocol_errors('OSPF router IDs must be identical for neighbors to form an adjacency.')
    assert not general_protocol_errors('The OSPF process ID does not have to match the router ID.')
    assert not general_protocol_errors('OSPF router IDs must not be identical; each router needs a unique ID.')


def test_ospf_identity_guards_catch_hardware_derivation_and_process_wire_claims():
    from llm.orchestration.synthesis import general_protocol_errors
    assert general_protocol_errors("The OSPF router ID is derived from the router's hardware address.")
    assert general_protocol_errors('The OSPF process number is used in OSPF packet headers to identify the sending process.')
    assert general_protocol_errors('In OSPF, the router ID identifies the router interface.')
    assert general_protocol_errors('The OSPF process number is globally unique across the network.')
    assert not general_protocol_errors('The OSPF router ID is not a MAC address; it is a 32-bit identifier.')
    assert not general_protocol_errors('An OSPF router ID may be configured or selected from an IP address; process IDs are local labels.')
    assert not general_protocol_errors('The OSPF process number is not transmitted in the OSPF packet header.')


def test_ebgp_expansion_is_not_extended_or_enhanced_bgp():
    from llm.orchestration.synthesis import general_protocol_errors
    assert general_protocol_errors('Use eBGP (Extended Border Gateway Protocol) with OSPF.')
    assert general_protocol_errors('eBGP: Enhanced Border Gateway Protocol.')
    assert not general_protocol_errors('eBGP means External BGP. BGP also supports extended messages.')


def test_general_protocol_repair_preserves_bad_draft_and_reconstruction_attribution():
    from llm.orchestration.synthesis import verify_general_protocol_answer
    bad='An OSPF process ID must match the router ID.'
    generate=AsyncMock(return_value=('No. The process ID is local and need not match the router ID.','test'))
    answer,model,report=asyncio.run(verify_general_protocol_answer('Explain their relationship.',bad,'test',generate))
    assert 'need not match' in answer and report['original_answer']==bad
    assert report['status']=='model_repair' and generate.await_count==1
    generate=AsyncMock(return_value=(bad,'test'))
    answer,model,report=asyncio.run(verify_general_protocol_answer('Explain their relationship.',bad,'test',generate))
    assert 'do not have to match' in answer and model is None
    assert report['status']=='verified_rule_fallback' and report['repair_answer']==bad
    generate=AsyncMock(side_effect=asyncio.TimeoutError())
    answer,model,report=asyncio.run(verify_general_protocol_answer('Explain their relationship.',bad,'test',generate))
    assert model is None and report['status']=='verified_rule_fallback'


def test_explicit_generation_still_reaches_its_review_workflow():
    generate=AsyncMock(return_value=(json.dumps({'intent':'generate_native'}),'test'))
    with patch.dict(os.environ,{'COGNISHIELD_AI_PLANNING':'1'}),patch('llm.gateway_semantics.semantic_hint',AsyncMock(return_value=None)):
        route=asyncio.run(select_context('Create a native OSPF configuration for Leaf-Alder.','test','studio',
            None,[],[],inventory=INVENTORY,generate_fn=generate))
    assert route.intent=='generate_native'


def test_legacy_graph_regressions_restore_user_enabled_feature_flags():
    from tests.test_b1_agent import B1Tests
    import unittest
    class Probe(B1Tests):
        def runTest(self):
            self.assertEqual(os.environ['COGNISHIELD_AI_PLANNING'],'0')
            self.assertEqual(os.environ['COGNISHIELD_AI_SYNTHESIS'],'0')
    with patch.dict(os.environ,{'COGNISHIELD_AI_PLANNING':'1','COGNISHIELD_AI_SYNTHESIS':'1'}):
        result=unittest.TestResult()
        Probe('runTest').run(result)
        assert result.wasSuccessful(),(result.failures,result.errors)
        assert os.environ['COGNISHIELD_AI_PLANNING']=='1'
        assert os.environ['COGNISHIELD_AI_SYNTHESIS']=='1'


@pytest.mark.parametrize('wording',['software release','firmware version','operating system release'])
def test_recorded_software_identity_uses_inventory_without_a_configuration_guess(wording):
    generate=AsyncMock(side_effect=AssertionError('An exact stored attribute needs no planner'))
    with patch.dict(os.environ,{'COGNISHIELD_AI_PLANNING':'1'}):
        route=asyncio.run(select_context('What '+wording+' is recorded for Leaf-Alder?',None,'floating',
            None,[],[],inventory=INVENTORY,generate_fn=generate))
    assert route.network_domains==['inventory']
    assert route.attributes==['os_version'] and route.device_refs==['Leaf-Alder']
    generate.assert_not_awaited()


def test_compound_software_and_config_request_cannot_drop_inventory_source():
    from llm.orchestration.planning import propose
    generate=AsyncMock(return_value=(json.dumps({'intent':'answer','information_needs':[
        {'domain':'configuration','question':'saved configuration'}]}),'test'))
    with pytest.raises(ValueError,match='omit'):
        asyncio.run(propose('Compare the recorded software release and saved configuration for Leaf-Alder.',
            None,'floating',None,[],[],INVENTORY,generate,read_only_request=True))


@pytest.mark.parametrize('version',['17.9',''])
def test_exact_inventory_attribute_is_released_from_verified_records(tmp_path_factory,version):
    from uuid import uuid4
    from db.manager import DatabaseManager
    from llm.gateway import AIGateway
    from llm.gateway_store import ensure_schema
    from llm.gateway_models import TurnRequest
    tmp_path=tmp_path_factory.mktemp('attrs')
    db=DatabaseManager(str(tmp_path/'attributes.db'));db.initialize();ensure_schema(db)
    try:
        from local_providers.development import ScenarioManager
        scenario=json.loads((Path(__file__).resolve().parents[2]/'docs/evaluations/phase_f_holdouts_v1.json').read_text())['fixture']
        scenario['devices'][0].update(hostname='Leaf-Alder',os_version=version)
        manager=ScenarioManager(tmp_path/'scenario.json')
        manager.change('import',manager.snapshot()[1]['source_revision'],scenario)
        db._development_scenario=manager
        service=AIGateway(db);identity=service.store.create('attribute-test-owner','floating')['id']
        with patch.dict(os.environ,{'COGNISHIELD_AI_ENGINE':'langgraph_b3','COGNISHIELD_AI_PLANNING':'1','COGNISHIELD_AI_SYNTHESIS':'1','COGNISHIELD_DEV_SIMULATION':'1'}),\
             patch('llm.orchestration.synthesis.synthesize',AsyncMock(side_effect=AssertionError('A model must not overwrite an exact inventory attribute'))):
            result=asyncio.run(service.turn(identity,{'username':'attribute-test-owner','role':'engineer'},
                TurnRequest(request_id=uuid4(),prompt='What software release is recorded for Leaf-Alder?')))
        assert result.status=='success' and result.model is None
        assert ('17.9' if version else 'Not recorded') in result.answer
        assert 'OS version' in result.answer and 'Leaf-Alder' in result.answer
        assert [r['tool'] for r in result.observations]==['inventory.read']
    finally:db.close()
