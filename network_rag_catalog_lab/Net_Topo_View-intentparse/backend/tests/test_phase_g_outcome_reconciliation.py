"""Original action/source authority across one existing read-only contract."""
import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock,patch
import pytest
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm.orchestration.request_contract import (requested_contract,requested_clauses,
    request_action,outcome_results,outcome_support_errors,project_read_outcomes)
from llm.orchestration.planning import propose
from llm.orchestration.synthesis import synthesize
from llm.gateway_models import Evidence


INV={'devices':[{'id':8,'hostname':'Birch','management_ip':'192.0.2.8','interfaces':[]}]}


@pytest.mark.parametrize('text',[
    'Recommend relevant evidence without reading it.',
    'Which records should we inspect next? Do not retrieve them.',
    'What observations could I request to distinguish the explanations?',
    'Could you suggest useful checks for the unresolved issue?',
])
def test_requested_advice_cannot_become_empty_retrieve_or_immediate_read(text):
    c=requested_contract(text,[{'clause':'request-1','action':'retrieve','need_indexes':[]}])
    assert c.advice_only and c.original_request==text
    assert c.execution_queries({'state':{'source_scope':'current'}})=={}


@pytest.mark.parametrize('text',[
    'Read the suggested syslog now.',
    'What did the report recommend?',
    'Do not recommend checks; read the saved configuration.',
    'Explain why that past recommendation failed.',
])
def test_past_negative_and_immediate_reads_are_not_advisory_requests(text):
    assert request_action(text)!='recommend_checks'


def test_original_configuration_and_log_operands_survive_refinement_to_log_only():
    text='Read Birch saved configuration and read its syslog, then explain the limitation.'
    c=requested_contract(text,needs=[{'domain':'configuration'}],inventory=INV)
    executable=c.execution_queries({'syslog':{'source_scope':'historical'}})
    assert set(executable)=={'configuration','syslog'}
    assert c.outcomes[0].required_readers==['network.configuration']
    assert c.outcomes[1].required_readers==['network.syslog']
    assert executable['configuration']['source_scope']=='historical'


def test_capture_time_operands_are_not_replaced_by_inventory_or_one_capture():
    c=requested_contract('Compare Birch saved text with its current simulated text.',
        needs=[{'domain':'inventory'}],inventory=INV)
    assert c.source_requests['configuration']['source_scope']=='both'
    q=c.execution_queries({'inventory':{},'configuration':{'source_scope':'current','source_categories':['running_configs']}})
    assert q['configuration']['source_scope']=='both' and 'source_categories' not in q['configuration']


def test_original_state_dependency_survives_topology_only_model_plan():
    c=requested_contract('Assess modeled delivery through Birch and explain the reverse direction.',
        needs=[{'domain':'topology'}],inventory=INV)
    assert 'state' in c.execution_queries({'topology':{}})


def test_sentence_actions_split_without_splitting_addresses_or_file_names():
    text='Read Birch at 192.0.2.8. Explain the capture in audit.cfg.'
    parts=requested_clauses(text)
    assert len(parts)==2 and '192.0.2.8' in parts[0]['text'] and 'audit.cfg' in parts[1]['text']


def test_source_failure_and_nonempty_model_text_do_not_prove_completion():
    c=requested_contract('Read Birch configuration and read its syslog.',inventory=INV)
    ctx=[{'tool':'network.configuration','status':'success','evidence_ids':['config']},
        {'tool':'network.syslog','status':'unavailable','evidence_ids':['logs']}]
    ev=[Evidence(id='config',source='saved',origin='stored'),Evidence(id='logs',source='logs',origin='stored')]
    parts={'responses':[{'id':'request-1','answer':'Read it.','sources':['S1']},
        {'id':'request-2','answer':'Unavailable.','sources':['S2']}]}
    r=outcome_results(c,ctx,ev,{'status':'literal_checks_passed','attempts':[{'response_contract':parts}]})
    assert [v['disposition'] for v in r]==['response_proposed','limited']
    assert all(v['semantic_completion']=='NOT_CERTIFIED' for v in r)
    parts['responses'][0]['sources']=['S2']
    assert outcome_support_errors(c,parts,ctx,ev)


def test_same_planner_protocol_examples_satisfy_the_new_wire_contract(monkeypatch):
    monkeypatch.setenv('COGNISHIELD_AI_OUTCOMES','1')
    model=AsyncMock(return_value=('{"intent":"answer","requested_outcomes":[{"clause":"request-1","action":"retrieve","need_indexes":[]}],"information_needs":[]}', 'fake'))
    route=asyncio.run(propose('Which read-only evidence should I request next?',None,'floating',None,[],[],INV,model))
    assert route.requested_outcomes.advice_only and not route.network_domains
    for message in model.await_args.args[0]:
        if message['role']=='assistant':assert 'requested_outcomes' in json.loads(message['content'])
    assert model.await_count==1


def test_real_planning_function_cannot_replace_configuration_with_syslog(monkeypatch):
    monkeypatch.setenv('COGNISHIELD_AI_OUTCOMES','1')
    model=AsyncMock(return_value=(json.dumps({'intent':'answer',
        'requested_outcomes':[{'clause':'request-1','action':'retrieve','need_indexes':[]},
            {'clause':'request-2','action':'retrieve','need_indexes':[]}],
        'information_needs':[{'domain':'configuration','question':'saved capture','source_scope':'historical'}]}),'fake'))
    route=asyncio.run(propose('Read Birch saved configuration and read its syslog.',None,'floating',None,[],[],INV,model,read_only_request=True))
    assert set(route.network_domains)=={'configuration','syslog'}
    assert route.requested_outcomes.outcomes[0].readers==['network.configuration']
    assert 'authoritative_reader_identity' not in str(route.planning)


def test_empty_unresolved_read_is_a_limitation_not_fabricated_record_answer():
    c=requested_contract('Read that unknown record.')
    model=SimpleNamespace(generate=AsyncMock())
    answer,trace=asyncio.run(synthesize(model,None,c.original_request,[],[],{},'',requested_outcomes=c))
    assert trace['status']=='unresolved_outcome_read' and 'no resolved evidence' in answer
    model.generate.assert_not_awaited()


def test_outcome_fallback_preserves_existing_verified_temporal_limitation():
    text='Read Birch saved and current configuration. Compare them over the intervening interval.'
    c=requested_contract(text,needs=[{'domain':'configuration'}],inventory=INV)
    rows=[{'hostname':'Birch','kind':kind,'current':current,'timestamp':time,'config_text':'hostname Birch\n'}
        for kind,current,time in [('configuration_snapshot',False,'2026-10-24T01:00:00Z'),
            ('running_configuration',True,'2026-10-24T02:00:00Z')]]
    context=[{'tool':'network.configuration','status':'success','evidence_ids':['c'],'data':{'records':rows}}]
    model=SimpleNamespace(generate=AsyncMock())
    answer,trace=asyncio.run(synthesize(model,None,text,context,[Evidence(id='c',source='saved/current',origin='stored')],{},'fallback',requested_outcomes=c))
    assert 'Matching text establishes equality of these captures only' in answer
    assert 'does not establish that no changes occurred between them' in answer
    assert trace['status']=='capture_interval_scope_fallback'
    model.generate.assert_not_awaited()


@pytest.mark.parametrize('prefix',['Given the previous read','Based on the earlier assessment','Considering those records'])
def test_discourse_prefaces_do_not_turn_requested_recommendations_into_reads(prefix):
    c=requested_contract(prefix+', recommend useful evidence and explain its purpose.',
        needs=[{'domain':'inventory'},{'domain':'configuration'}])
    assert c.advice_only and c.execution_queries({'inventory':{},'configuration':{}})=={}
    assert not requested_contract(prefix+', read the saved configuration.').advice_only


def test_configuration_source_grammar_handles_singular_and_plural_command_text():
    from llm.gateway_references import configuration_record_request
    for noun in ['command','commands']:
        assert configuration_record_request('Show Birch saved '+noun+' text together with syslog.')
        c=requested_contract('Show Birch saved '+noun+' text together with syslog.',inventory=INV)
        assert {'configuration','syslog'}<=set(c.execution_queries({'syslog':{}}))
    assert not configuration_record_request('Show Birch current log message text.')


def test_failed_reader_prose_is_replaced_per_outcome_not_accepted_as_success():
    c=requested_contract('Read Birch saved configuration and read its syslog.',inventory=INV)
    ctx=[{'tool':'network.configuration','status':'success','evidence_ids':['c'],
        'data':{'records':[{'hostname':'Birch','config_text':'hostname Birch\n'}]}},
        {'tool':'network.syslog','status':'unavailable','message':'Source unavailable','evidence_ids':['s'],'data':{}}]
    ev=[Evidence(id='c',source='saved',origin='stored'),Evidence(id='s',source='logs',origin='stored')]
    parts=[{'id':o.id,'answer':'Successfully retrieved records.','sources':[]} for o in c.outcomes]
    projected,reasons=project_read_outcomes(c,parts,ctx,ev)
    assert 'hostname Birch' in projected[0]['answer']
    assert 'retrieval limitation' in projected[1]['answer'] and 'Successfully' not in projected[1]['answer']
    assert [p['sources'] for p in projected]==[['S1'],['S2']]
    assert reasons[1]['reason']=='source_unavailable'
    # Original model output remains intact for honest grading.
    assert all(p['answer']=='Successfully retrieved records.' for p in parts)


def test_comparison_interpretation_is_not_overwritten_by_a_successful_read_projection():
    c=requested_contract('Compare Birch configuration and syslog.',inventory=INV)
    parts=[{'id':'request-1','answer':'A source-scoped comparison.','sources':['S1','S2']}]
    ctx=[{'tool':'network.configuration','status':'success','evidence_ids':['a'],'data':{}},
        {'tool':'network.syslog','status':'unavailable','evidence_ids':['b'],'data':{}}]
    result,reasons=project_read_outcomes(c,parts,ctx,[])
    assert result==parts and reasons==[]


def test_advisory_catalog_is_server_scoped_even_if_model_ignores_its_schema():
    c=requested_contract('Recommend useful checks.')
    raw=json.dumps({'checks':[{'reader':'network.configuration','question':'Read config','rationale':'Might help.'}]})
    model=SimpleNamespace(generate=AsyncMock(return_value=(raw,'fake')))
    answer,trace=asyncio.run(synthesize(model,None,c.original_request,[],[],{},'Unavailable recommendation.',requested_outcomes=c,
        advisory_context={'authorized_readers':['network.state'],'source_catalog':[{'source':'device_state','readers':{'network.state':['interface_state']}}]}))
    assert answer=='Unavailable recommendation.' and trace['status']=='advisory_unavailable'


from tests import test_b1_agent as fixtures
from llm.gateway_routing import SemanticRoute


class ContractGatewayTests(unittest.IsolatedAsyncioTestCase):
    setUp=fixtures.B1Tests.setUp
    ask=fixtures.B1Tests.ask

    async def test_owned_advice_context_survives_wrong_history_and_read_proposals(self):
        for surface in ['floating','studio']:
            identity=self.g.store.create('alice',surface)['id']
            with patch.dict('os.environ',{'COGNISHIELD_AI_ENGINE':'langgraph_b3','COGNISHIELD_AI_OUTCOMES':'1'}):
                await self.ask('Show R2 interfaces',identity=identity)
                prompt='Which evidence should I request next about that uncertainty? Do not collect anything.'
                bad=requested_contract(prompt,[{'clause':'request-1','action':'retrieve','need_indexes':[]}])
                route=SemanticRoute(intent='answer',use_history=False,requested_outcomes=bad)
                raw=json.dumps({'checks':[{'reader':'network.state','question':'Request R2 operational interface observations.',
                    'rationale':'This would distinguish unavailable evidence from a recorded interface state.'}]})
                model=AsyncMock(return_value=(raw,'mock'))
                with patch('llm.orchestration.engine.select_context',AsyncMock(return_value=route)),\
                    patch('llm.orchestration.model.RoutingModel.generate',model),\
                    patch.object(self.g.registry,'invoke',wraps=self.g.registry.invoke) as reader:
                    result=await self.ask(prompt,identity=identity)
                reader.assert_not_called()
                packet=json.loads(model.await_args.args[0][1]['content'])
                assert packet['reference_context']['devices']==['R2']
                assert 'R2' in packet['reference_context']['prior_user_goal']
                assert 'OWNED_CONFIG' not in str(packet) and 'PRIVATE_BOB_CONFIG' not in str(packet)
                assert 'Recommended evidence' in result.answer and not result.observations
                assert result.context_coverage['routing']['history']
                # Topic switches do not restore this unrelated device context.
                general=AsyncMock(return_value=('{"answer":"12","sources":[],"hypotheses":[]}','mock'))
                with patch('llm.orchestration.engine.select_context',AsyncMock(return_value=SemanticRoute(intent='answer'))),\
                    patch('llm.orchestration.model.RoutingModel.generate',general):
                    reply=await self.ask('What is 3 multiplied by 4?',identity=identity)
                assert '12' in reply.answer and not reply.observations
                assert 'R2' not in str(general.await_args.args[0])

    async def test_actual_reader_execution_restores_the_dropped_configuration_operand(self):
        route=SemanticRoute(intent='answer',network_domains=['syslog'],device_refs=['2'])
        composer=AsyncMock(return_value=('Saved records and log limitation.',{'status':'literal_checks_passed','attempts':[]}))
        with patch.dict('os.environ',{'COGNISHIELD_AI_ENGINE':'langgraph_b3','COGNISHIELD_AI_OUTCOMES':'1','COGNISHIELD_AI_SYNTHESIS':'1'}),\
            patch('llm.orchestration.engine.select_context',AsyncMock(return_value=route)),\
            patch('llm.orchestration.synthesis.synthesize',composer):
            result=await self.ask('Read R2 saved configuration and read its syslog.')
        assert {r['tool'] for r in result.observations}=={'network.configuration','network.syslog'}
        supplied=composer.await_args.args[3]
        assert 'OWNED_CONFIG' in str(supplied) and 'PRIVATE_BOB_CONFIG' not in str(supplied)
