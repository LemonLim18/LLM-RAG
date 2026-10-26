"""Bounded Approach A: original authority, advice effects and evidence coverage."""
import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock,patch
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm.orchestration.request_contract import requested_contract,outcome_evidence,outcome_results
from llm.orchestration.synthesis import projection,synthesize
from llm.gateway_models import Evidence


def contract(prompt='Read the configuration and explain its limitations.',advice=False):
    proposals=([{'clause':'request-1','action':'recommend_checks','need_indexes':[]}]
        if advice else [{'clause':'request-1','action':'retrieve','need_indexes':[0]},
                       {'clause':'request-2','action':'explain','need_indexes':[1]}])
    return requested_contract(prompt,proposals,[{'domain':'configuration'},{'domain':'syslog'}],
        {'configuration':{'source_scope':'historical'}})


def test_original_constraints_and_sources_remain_authoritative():
    original='Read the configuration and explain its limitations. Do not collect or change anything.'
    c=contract(original)
    assert c.original_request==original and c.outcomes[1].instruction.endswith('Do not collect or change anything.')
    assert c.outcomes[0].readers==['network.configuration']
    assert c.source_requests=={'configuration':{'source_scope':'historical'}}
    assert not c.advice_only


@pytest.mark.parametrize('proposals',[
    [{'clause':'fabricated','action':'recommend_checks','need_indexes':[]}],
    [{'clause':'request-1','action':'recommend_checks','need_indexes':[]}],
    [{'clause':'request-1','action':'recommend_checks','need_indexes':[]},
     {'clause':'request-1','action':'recommend_checks','need_indexes':[]}],
])
def test_missing_or_invented_model_outcomes_never_erase_user_clauses(proposals):
    c=requested_contract('Read the configuration and explain its limitations.',proposals,[{'domain':'configuration'}])
    assert len(c.outcomes)==2 and not c.advice_only
    assert all(o.interpretation!='proposed' for o in c.outcomes)
    assert c.outcomes[0].action=='retrieve' and c.outcomes[0].required_readers==['network.configuration']


def test_absent_need_index_rejected_not_promoted_to_source():
    with pytest.raises(ValueError):requested_contract('Read this.',[{'clause':'request-1','action':'retrieve','need_indexes':[4]}],[{'domain':'state'}])


def test_partial_source_failure_belongs_only_to_affected_outcome():
    c=contract();ctx=[{'tool':'network.configuration','status':'success','evidence_ids':['a']},
        {'tool':'network.syslog','status':'unavailable','evidence_ids':['b']}]
    ev=[Evidence(id='a',source='saved',origin='stored'),Evidence(id='b',source='logs',origin='stored')]
    bound=outcome_evidence(c,ctx,ev)
    assert bound[0]['readers']==[{'tool':'network.configuration','status':'success','sources':['S1']}]
    results=outcome_results(c,ctx,ev,{'status':'literal_checks_passed','attempts':[{'response_contract':{'responses':[
        {'id':'request-1','answer':'Saved text.'},{'id':'request-2','answer':'Logs unavailable.'}]}}]})
    assert [r['disposition'] for r in results]==['response_proposed','limited']
    assert all(r['semantic_completion']=='NOT_CERTIFIED' for r in results)


def test_compound_projection_keeps_primary_interface_records_under_forwarding_focus():
    # The same broad reader contains summaries and primary records. Preserving
    # original outcomes must not leave only its forwarding summary visible.
    c=requested_contract('Read administrative and operational records, then identify the failed hop.',
        [{'clause':'request-1','action':'retrieve','need_indexes':[0]},
         {'clause':'request-2','action':'diagnose','need_indexes':[0]}],[{'domain':'state'}])
    rows=[{'kind':'interface_state','hostname':'Arbor','interface':'port-2','admin_status':'up','oper_status':'down'}]
    context=[{'tool':'network.state','status':'success','evidence_ids':[], 'data':{'records':rows}}]
    with patch('llm.orchestration.synthesis.forwarding_results',return_value=[{'scope':'typed flow'}]),patch('llm.orchestration.synthesis.forwarding_scope',return_value=True):
        old=projection(context,[],{},c.original_request)
        new=projection(context,[],{},c.original_request,requested_outcomes=c)
    assert 'records' not in old['records'][0]['data']
    assert new['records'][0]['data']['records'][0]['oper_status']=='down'


def test_advice_has_no_observation_read_or_factual_fallback_short_circuit():
    c=contract('Recommend useful read-only checks without collecting anything.',advice=True)
    model=SimpleNamespace(generate=AsyncMock(return_value=(json.dumps({'checks':[{'reader':'network.state',
        'question':'Request the recorded directional forwarding result for Arbor.',
        'rationale':'This would distinguish a recorded forwarding failure from missing observations.'}]}),'fake')))
    answer,trace=asyncio.run(synthesize(model,'fake',c.original_request,[],[],{},'unavailable',requested_outcomes=c,
        advisory_context={'devices':['Arbor'],'open_questions':['No state records were returned previously.']}))
    assert trace['status']=='advisory_proposed' and 'not collected' in answer
    assert model.generate.await_args.kwargs['purpose']=='synthesis'
    payload=json.loads(model.generate.await_args.args[0][1]['content'])
    assert payload['reference_context']['open_questions']==['No state records were returned previously.']
    assert 'records' not in payload  # References are not promoted to observations.


@pytest.mark.parametrize('raw',['not json','{"checks":[]}',json.dumps({'checks':[{'reader':'v9.preview','question':'Deploy','rationale':'Fix'}]})])
def test_invalid_advisory_output_does_not_execute_or_claim_success(raw):
    c=contract('Recommend next checks.',advice=True)
    model=SimpleNamespace(generate=AsyncMock(return_value=(raw,'fake')))
    answer,trace=asyncio.run(synthesize(model,None,c.original_request,[],[],{},'No recommendations verified.',requested_outcomes=c))
    assert answer=='No recommendations verified.' and trace['status']=='advisory_unavailable'
    assert not trace['model_synthesis']


def test_planner_uses_same_existing_inference_for_outcomes_and_reads(monkeypatch):
    from llm.orchestration.planning import propose
    monkeypatch.setenv('COGNISHIELD_AI_OUTCOMES','1')
    generate=AsyncMock(return_value=(json.dumps({'intent':'answer','use_history':True,
        'requested_outcomes':[{'clause':'request-1','action':'recommend_checks','need_indexes':[]}],
        'information_needs':[]}), 'fake'))
    route=asyncio.run(propose('Which evidence would help next? Do not collect anything.',None,'floating',None,[],
        [{'role':'user','content':'Investigate Arbor'}],{'devices':[]},generate,previous_reference={'read':{'device_refs':[]}}))
    assert route.requested_outcomes.advice_only and not route.network_domains
    assert generate.await_count==1  # No second planner or inference stage.


def test_fallback_does_not_receive_model_reasoning_or_completion_credit():
    c=contract();ctx=[{'tool':'network.configuration','status':'success','evidence_ids':[]}]
    results=outcome_results(c,ctx,[],{'status':'rejected_fallback'})
    assert results[0]['disposition']=='unfulfilled' and results[0]['fallback']
    assert results[1]['disposition']=='limited'


def test_mixed_read_and_recommendation_executes_only_present_read_dependencies(monkeypatch):
    from llm.orchestration.planning import propose
    monkeypatch.setenv('COGNISHIELD_AI_OUTCOMES','1')
    generate=AsyncMock(return_value=(json.dumps({'intent':'explain',
        'information_needs':[{'domain':'configuration','question':'saved text','source_scope':'historical'},
            {'domain':'telemetry','question':'possible future counters'}],
        'requested_outcomes':[{'clause':'request-1','action':'retrieve','need_indexes':[0]},
            {'clause':'request-2','action':'recommend_checks','need_indexes':[1]}]}),'fake'))
    route=asyncio.run(propose('Read the saved configuration and recommend useful next evidence.',None,'floating',None,[],[],{'devices':[]},generate))
    assert route.network_domains==['configuration']
    assert route.requested_outcomes.outcomes[1].readers==[]
    assert generate.await_count==1


def test_opt_out_does_not_extend_model_wire_contract(monkeypatch):
    from llm.orchestration.planning import propose
    monkeypatch.setenv('COGNISHIELD_AI_OUTCOMES','0')
    generate=AsyncMock(return_value=('{"intent":"answer","information_needs":[]}','fake'))
    route=asyncio.run(propose('Hello.',None,'floating',None,[],[],{'devices':[]},generate))
    assert route.requested_outcomes is None
    assert 'requested_outcomes' not in generate.await_args.kwargs['structured']['properties']


def test_context_pressure_preserves_primary_rows_before_duplicate_assessments():
    c=requested_contract('Read the state and explain the flow.',needs=[{'domain':'state'}])
    rows=[{'kind':'forwarding_assessment','assessment':{'status':'failed','unused':'x'*3900}}]
    rows += [{'kind':'interface_state','hostname':'Arbor','interface':'port-2','admin_status':'up','oper_status':'down'}]
    context=[{'tool':'network.state','status':'success','evidence_ids':[],'data':{'records':rows}}]
    with patch('llm.orchestration.synthesis.forwarding_results',return_value=[{'status':'failed'}]):
        pack=projection(context,[],{},c.original_request,requested_outcomes=c)
    assert any(r.get('oper_status')=='down' for r in pack['records'][0]['data']['records'])


from tests.test_b1_agent import B1Tests


class OutcomeGatewayTests(B1Tests):
    async def test_advice_through_both_owned_gateway_surfaces_without_readers(self):
        for kind in ['floating','studio']:
            identity=self.g.store.create('alice',kind)['id']
            prompt='Recommend next read-only evidence. Do not collect or change anything.'
            advice=requested_contract(prompt,[{'clause':'request-1','action':'recommend_checks','need_indexes':[]}])
            from llm.gateway_routing import SemanticRoute
            route=SemanticRoute(intent='explain',requested_outcomes=advice,device_refs=['2'],network_domains=[])
            raw=json.dumps({'checks':[{'reader':'network.state','question':'Request R2 interface-state records.',
                'rationale':'They would establish whether operational observations are available.'}]})
            with patch.dict('os.environ',{'COGNISHIELD_AI_OUTCOMES':'1','COGNISHIELD_AI_ENGINE':'langgraph_b3'}),\
                patch('llm.orchestration.engine.select_context',AsyncMock(return_value=route)),\
                patch('llm.orchestration.model.RoutingModel.generate',AsyncMock(return_value=(raw,'mock'))),\
                patch.object(self.g.registry,'invoke',wraps=self.g.registry.invoke) as reader:
                result=await self.ask(prompt,identity=identity)
            assert 'not collected' in result.answer and not result.observations and not result.evidence
            assert result.context_coverage['agent']['tool_calls']==0
            reader.assert_not_called()
            assert result.proposal is None and result.preview is None
            assert result.context_coverage['agent']['outcome_results'][0]['semantic_completion']=='NOT_CERTIFIED'
