"""Need refinement and composition must preserve compound task boundaries."""
import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock
from unittest.mock import patch
import os

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm.gateway_models import Evidence
from llm.orchestration.planning import InformationNeed,IntentPlan,select_logical_sources
from llm.orchestration.synthesis import synthesize


def test_source_refinement_cannot_erase_an_unselected_reader_need():
    plan=IntentPlan(intent='explain',information_needs=[
        InformationNeed(domain='configuration',question='Compare the saved peer configuration',source_scope='historical'),
        InformationNeed(domain='syslog',question='Explain the later peer log event')])
    model=AsyncMock(return_value=('{"source_categories":["syslog"]}','mock'))
    selected,trace=asyncio.run(select_logical_sources('Compare the saved peer settings with the later log event.',plan,model,None,['config_snapshots','syslog']))
    assert [(n.domain,n.question,n.source_scope) for n in selected.information_needs]==[(n.domain,n.question,n.source_scope) for n in plan.information_needs]
    assert selected.information_needs[1].source_categories==['syslog']


def test_refinement_preserves_separate_needs_and_prevalidated_source_constraints():
    plan=IntentPlan(intent='explain',information_needs=[
        InformationNeed(domain='state',question='Report controller connection',source_categories=['controller_state']),
        InformationNeed(domain='state',question='Report actual protocol observation',source_categories=['protocol_state'])])
    model=AsyncMock(return_value=('{"source_categories":["controller_state"]}','mock'))
    selected,_=asyncio.run(select_logical_sources('Explain the controller connection and protocol observations.',plan,model,None,['controller_state','protocol_state']))
    assert [(n.question,n.source_categories) for n in selected.information_needs]==[(n.question,n.source_categories) for n in plan.information_needs]


def test_indexed_semantic_source_choices_correct_one_reader_without_losing_other_goal():
    plan=IntentPlan(intent='explain',information_needs=[
        InformationNeed(domain='telemetry',question='Describe the controller connection'),
        InformationNeed(domain='configuration',question='Compare the saved command',source_scope='historical')])
    model=AsyncMock(return_value=('{"need_sources":[{"need_index":0,"source_categories":["controller_state"]},{"need_index":1,"source_categories":["config_snapshots"]}]}','mock'))
    selected,_=asyncio.run(select_logical_sources('Compare controller connection with the saved command.',plan,model,None,['controller_state','config_snapshots']))
    assert [(n.domain,n.question,n.source_scope) for n in selected.information_needs]==[
        ('state',plan.information_needs[0].question,'auto'),('configuration',plan.information_needs[1].question,'historical')]


def test_duplicate_need_selection_and_cross_reader_fanout_reject_safely():
    plan=IntentPlan(intent='explain',information_needs=[InformationNeed(domain='state',question='recorded state')])
    for payload in [
        {'need_sources':[{'need_index':0,'source_categories':['controller_state']},{'need_index':0,'source_categories':['device_state']}]},
        {'need_sources':[{'need_index':0,'source_categories':['controller_state','running_configs']}]},
        {'need_sources':[{'need_index':2,'source_categories':['controller_state']}]},
        {'need_sources':[{'need_index':0,'source_categories':['document.read']}]},
    ]:
        selected,trace=asyncio.run(select_logical_sources('Describe recorded state.',plan,AsyncMock(return_value=(json.dumps(payload),'mock')),None,['controller_state','device_state','running_configs']))
        assert selected==plan and trace['status']=='invalid_fallback'


def test_model_facing_source_protocol_has_one_canonical_representation():
    plan=IntentPlan(intent='explain',information_needs=[InformationNeed(domain='state',question='controller connection')])
    model=AsyncMock(return_value=('{"need_sources":[{"need_index":0,"source_categories":["controller_state"]}]}','mock'))
    selected,trace=asyncio.run(select_logical_sources('Explain the controller connection.',plan,model,None,['controller_state']))
    wire=model.call_args.kwargs['structured']
    assert set(wire['properties'])=={'need_sources'}
    assert wire['additionalProperties'] is False
    assert selected.information_needs[0].source_categories==['controller_state']


def test_multireader_source_can_correct_the_initial_reader_shape():
    plan=IntentPlan(intent='explain',information_needs=[InformationNeed(domain='state',question='Explain the modeled measurement series')])
    model=AsyncMock(return_value=(json.dumps({'need_sources':[
        {'need_index':0,'source_categories':['simulation'],'reader':'telemetry'}]}),'mock'))
    selected,trace=asyncio.run(select_logical_sources('Explain the modeled measurement series.',plan,model,None,['simulation']))
    assert trace['status']=='validated_model_source_selection'
    assert selected.information_needs[0].domain=='telemetry'
    assert selected.information_needs[0].question==plan.information_needs[0].question


def test_multireader_shape_correction_cannot_invent_a_reader_binding():
    plan=IntentPlan(intent='explain',information_needs=[InformationNeed(domain='state',question='Recorded observations')])
    model=AsyncMock(return_value=(json.dumps({'need_sources':[
        {'need_index':0,'source_categories':['simulation'],'reader':'syslog'}]}),'mock'))
    selected,trace=asyncio.run(select_logical_sources('Explain recorded observations.',plan,model,None,['simulation']))
    assert trace['status']=='invalid_fallback' and selected==plan


def test_ambient_editor_availability_does_not_supply_a_context_binding():
    from llm.gateway_routing import select_context
    from llm.gateway_models import EditorSnapshot
    editor=EditorSnapshot(document_id='private',path='playbooks/private.cfg',content='PRIVATE_MARKER',language='text',model_id='private',model_version=1,buffer_epoch=1,saved_revision=0,is_dirty=True,read_only=False)
    model=AsyncMock(return_value=('{"intent":"explain","use_editor":false,"use_attachments":false}','mock'))
    with patch.dict(os.environ,{'COGNISHIELD_AI_PLANNING':'0'}),patch('llm.gateway_semantics.semantic_hint',AsyncMock(return_value={'intent':'explain','domains':[]})):
        route=asyncio.run(select_context('Describe how a Python dictionary works.',None,'studio',editor,[],[],generate_fn=model))
    assert route.intent=='answer' and not route.use_editor and not route.use_attachments
    assert model.await_count==1


def test_comparison_followup_retains_both_authorized_source_operands():
    from llm.gateway_routing import select_context
    inventory={'devices':[{'id':71,'hostname':'Birch','aliases':[],'interfaces':[],'management_ip':'192.0.2.71'}]}
    previous={'context_coverage':{'retrieval':{'domains':['configuration'],'device_refs':['71'],
        'entities':[{'device_id':'71'}],'attributes':[],
        'source_requests':{'configuration':{'source_scope':'historical'}}}}}
    decision={'intent':'explain','use_history':True,'information_needs':[{'domain':'syslog','question':'Compare the recorded event'}]}
    model=AsyncMock(return_value=(json.dumps(decision),'mock'))
    with patch.dict(os.environ,{'COGNISHIELD_AI_PLANNING':'1'}):
        route=asyncio.run(select_context('Compare that evidence with the stored syslogs.',None,'floating',None,[],
            [{'role':'user','content':'Read Birch saved configuration.'}],previous=previous,inventory=inventory,generate_fn=model))
    assert set(route.network_domains)=={'configuration','syslog'}
    assert route.device_refs==['71'] and route.use_history
    assert route.source_requests['configuration']['source_scope']=='historical'


def test_two_endpoint_relationship_does_not_take_the_inventory_attribute_shortcut():
    from llm.gateway_routing import select_context
    inventory={'devices':[{'id':n,'hostname':name,'aliases':[],'interfaces':[],'management_ip':None}
        for n,name in [(71,'Birch'),(72,'Cedar')]]}
    model=AsyncMock(return_value=(json.dumps({'intent':'explain','information_needs':[
        {'domain':'topology','question':'Describe the intended endpoint relationship','source_scope':'planned'}]}),'mock'))
    with patch.dict(os.environ,{'COGNISHIELD_AI_PLANNING':'1'}):
        route=asyncio.run(select_context('Describe the intended peer ports linking Birch and Cedar.',None,'floating',None,[],[],
            inventory=inventory,generate_fn=model))
    assert route.network_domains==['topology']
    assert model.await_count==1


def test_named_document_comparison_preserves_the_requested_network_operand():
    from llm.gateway_routing import select_context
    inventory={'devices':[{'id':71,'hostname':'Birch','aliases':[],'interfaces':[],'management_ip':None}]}
    model=AsyncMock(return_value=(json.dumps({'intent':'analyze_files','use_attachments':True,
        'information_needs':[{'domain':'configuration','question':'Read the retained capture','source_scope':'historical'}]}),'mock'))
    with patch.dict(os.environ,{'COGNISHIELD_AI_PLANNING':'1'}):
        route=asyncio.run(select_context('Compare the uploaded Design.md with Birch saved configuration.',None,'studio',None,
            [{'id':'owned-doc','name':'Design.md'}],[],inventory=inventory,generate_fn=model))
    assert route.use_attachments and route.network_domains==['configuration']


def test_protocol_summary_must_not_erase_saved_configuration_in_a_comparison():
    context=[{'tool':'network.state','status':'success','evidence_ids':['p'],'data':{'records':[
        {'kind':'protocol_observation','protocol':'BGP','hostname':'Canopy','neighbor':'Hearth','local_as':64520,'remote_as':64530,'observed_state':'Active'}]}},
        {'tool':'network.configuration','status':'success','evidence_ids':['c'],'data':{'records':[
        {'kind':'configuration_snapshot','hostname':'Canopy','current':False,'config_text':'router bgp 64520\n neighbor 203.0.113.6 remote-as 64530\n! SAVED_COMPARISON_WITNESS'}]}}]
    refs=[Evidence(id='p',source='state',origin='stored'),Evidence(id='c',source='backup',origin='stored')]
    model=type('Model',(),{'generate':AsyncMock(return_value=(json.dumps({'answer':'Both records are available. [S1] [S2]','sources':['S1','S2']}),'mock'))})()
    asyncio.run(synthesize(model,None,'Compare the BGP peer state with the saved settings.',context,refs,{},'fallback'))
    supplied=model.generate.call_args_list[0].args[0][-1]['content']
    assert 'SAVED_COMPARISON_WITNESS' in supplied and 'observed_state' in supplied


def test_one_failed_source_cannot_remove_successful_evidence_from_synthesis():
    context=[{'tool':'network.telemetry','status':'success','evidence_ids':['m'],'data':{'records':[
        {'hostname':'Canopy','metric':'cpu_pct','value':37,'unit':'percent','timestamp':'2026-10-23T03:00:00Z'}]}},
        {'tool':'network.syslog','status':'unavailable','evidence_ids':['l'],'message':'Log source timed out','data':{'source_available':False}}]
    refs=[Evidence(id='m',source='metrics',origin='stored'),Evidence(id='l',source='logs',origin='stored')]
    model=type('Model',(),{'generate':AsyncMock(return_value=(json.dumps({'answer':'CPU is recorded as 37 percent; logs are unavailable. [S1] [S2]','sources':['S1','S2']}),'mock'))})()
    asyncio.run(synthesize(model,None,'Explain the CPU reading together with the available log evidence.',context,refs,{},'fallback'))
    supplied=model.generate.call_args_list[0].args[0][-1]['content']
    assert '37' in supplied and 'Log source timed out' in supplied


def test_literal_router_id_focus_cannot_replace_other_requested_source_evidence():
    context=[{'tool':'network.configuration','status':'success','evidence_ids':['c'],'data':{'records':[
        {'hostname':'Birch','config_text':'router ospf 6\n router-id 192.0.2.6\n! COMPLETE_CAPTURE_WITNESS'}]}},
        {'tool':'network.syslog','status':'success','evidence_ids':['l'],'data':{'records':[
        {'hostname':'Birch','message':'LOG_WITNESS: peer reset','timestamp':'2026-10-23T03:00:00Z'}]}}]
    refs=[Evidence(id='c',source='saved',origin='stored'),Evidence(id='l',source='logs',origin='stored')]
    facts=[{'device':'Birch','current':False,'timestamp':'2026-10-23T02:00:00Z','commands':[{'command':'router-id 192.0.2.6','router_id':'192.0.2.6'}],'sources':['S1']}]
    model=type('Model',(),{'generate':AsyncMock(return_value=(json.dumps({'answer':'Recorded router ID is 192.0.2.6. [S1] Logs record a peer reset. [S2]','sources':['S1','S2']}),'mock'))})()
    with patch('llm.orchestration.synthesis.explicit_config_router_ids',return_value=facts):
        asyncio.run(synthesize(model,None,'Compare the configured router ID and peer reset log.',context,refs,{},'fallback'))
    supplied=model.generate.call_args_list[0].args[0][-1]['content']
    assert 'LOG_WITNESS' in supplied and 'COMPLETE_CAPTURE_WITNESS' in supplied


def test_source_health_is_not_authority_for_a_device_health_verdict():
    context=[{'tool':'network.state','status':'success','evidence_ids':['h'],'data':{'records':[
        {'kind':'source_health','hostname':'Birch','timestamp':'2026-10-23T03:00:00Z',
         'sources':{'telemetry':'AVAILABLE'},'physical_collection_performed':False}],
        'effective_source_statuses':{'telemetry':{'status':'AVAILABLE'}}}}]
    evidence=[Evidence(id='h',source='source-provider',origin='simulated')]
    model=type('Model',(),{'generate':AsyncMock(return_value=(json.dumps({
        'answer':'Birch is operational and accessible. [S1]','sources':['S1']}),'mock'))})()
    answer,trace=asyncio.run(synthesize(model,None,'Explain what the source provider records.',context,evidence,{},'fallback'))
    assert not model.generate.called
    assert trace['model_synthesis'] is False
    assert 'source availability' in answer and 'device health' in answer
    assert 'operational and accessible' not in answer


def test_published_identifier_uses_the_actual_catalog_instead_of_an_attribute_keyword_list():
    from llm.gateway_references import published_knowledge_read
    manifest={'template_bindings':[{'operation_id':'assemble_private_method'}]}
    with patch('llm.gateway_knowledge.read_release',return_value=(None,manifest,None)):
        route=published_knowledge_read('Which supported platform matrix does published assemble_private_method expose?',{'devices':[]})
    assert route['network_domains']==['knowledge']


def test_successful_empty_reader_metadata_cannot_be_promoted_to_observations():
    context=[{'tool':'network.state','status':'success','evidence_ids':['h'],'data':{
        'records':[],'source_statuses':{'source_health':'AVAILABLE'},
        'source_captures':{'source_health':'2026-10-23T03:00:00Z'}}}]
    evidence=[Evidence(id='h',source='provider',origin='simulated')]
    model=type('Model',(),{'generate':AsyncMock()})()
    answer,trace=asyncio.run(synthesize(model,None,'Explain these observations.',context,evidence,{},'fallback'))
    assert not model.generate.called and trace['status']=='no_matching_records_fallback'
    assert 'AVAILABLE' in answer and '2026-10-23T03:00:00Z' in answer
    assert 'No matching observation' in answer and 'does not establish device health' in answer


def test_compound_answer_must_cite_each_requested_reader_not_only_one():
    context=[{'tool':'network.configuration','status':'success','evidence_ids':['c'],
        'data':{'records':[{'hostname':'Birch','config_text':'hostname Birch'}]}},
        {'tool':'network.syslog','status':'success','evidence_ids':['l'],
        'data':{'records':[{'hostname':'Birch','message':'Peer reset'}]}}]
    evidence=[Evidence(id='c',source='saved',origin='stored'),Evidence(id='l',source='logs',origin='stored')]
    model=type('Model',(),{'generate':AsyncMock(return_value=(json.dumps({
        'answer':'The records include saved text and a peer reset. [S2]','sources':['S2']}),'mock')),
        'available':lambda self,purpose:False})()
    _,trace=asyncio.run(synthesize(model,None,'Explain both requested sources.',context,evidence,{},'verified fallback',
        objectives=[{'domain':'configuration','question':'Explain the saved settings'}, {'domain':'syslog','question':'Explain the log'}]))
    assert trace['status']=='rejected_fallback'
    assert any('need-1' in error for attempt in trace['attempts'] for error in attempt['errors'])
