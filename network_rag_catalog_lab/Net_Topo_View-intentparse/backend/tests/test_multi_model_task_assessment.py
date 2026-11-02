"""Structural request/evidence integrity, explicitly not a semantic grader."""
import asyncio,json,sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi import HTTPException
from llm.gateway_models import Evidence
from llm.orchestration.role_reasoning import decide,evidence_packet,preview
from tests.test_model_role_graph import GraphRoles,plan,decision

def assessment(clause='request-1',status='supported',sources=None,missing=None):
    return {'clause':clause,'status':status,'sources':sources or [],'assessment':'A model proposal about the requested outcome.',
        'missing_facts':missing or []}

def model_output(parts=None,**changes):
    values={'decision':'answer','answer':'This is the proposed explanation.','sources':[],
        'outcome_assessments':parts if parts is not None else [assessment()]}
    return {**values,**changes}

async def invoke(output,prompt='Explain the available record.',*,continuation=None):
    model=SimpleNamespace(hybrid=SimpleNamespace(remote_calls=1,max_remote_calls=3),
        generate=AsyncMock(return_value=(json.dumps(output),'explicitly-mocked-model')))
    result=await decide(model,prompt,[],[],[],{},continuation=continuation)
    return result,model.generate.call_args.kwargs['structured']

def test_sentence_outcomes_share_original_text_and_do_not_replace_full_request():
    prompt='Explain the saved text. Compare it with the current capture; do not read logs.'
    p=json.loads(evidence_packet(prompt,[],[],[],{}))
    assert len(p['requested_clauses'])==2
    assert 'do not read logs' in p['requested_clauses'][1]['text']
    assert p['original_user_instruction']==prompt
    assert p['retrieval_boundary']['source_restrictions']['denied']==['syslog']

def test_identity_index_points_to_actual_raw_operands_without_inferred_diagnosis():
    row={'tool':'network.state','status':'success','evidence_ids':['receipt'],'data':{'records':[
        {'id':'relation','kind':'flow','device_id':8,'vrf':'green','forward':{'status':'failed','branches':[{'device_id':9,'interface_id':92}]},
         'return':{'status':'delivered'},'timestamp':'2026-10-20T01:00:00Z'}]}}
    p=json.loads(evidence_packet('Explain both directions.',[row],[Evidence(id='receipt',source='authored',origin='simulated')],[],{},
        retrieval={'executed_queries':[{'tool':'network.state','parameters':{'device_refs':['8']}}]}))
    assert p['reader_results']==[row]
    entry=p['record_identity_index'][0]
    assert entry['record_path']=='/reader_results/0/data/records/0'
    assert entry['vrf']=='green' and entry['relationship_fields']==['forward','return']
    assert 'diagnosis' not in entry and p['retrieval_boundary']['executed_queries'][0]['parameters']['device_refs']==['8']

@pytest.mark.parametrize('parts',[
    [],[assessment('invented')],[assessment(),assessment()],
])
def test_missing_duplicate_or_invented_assessments_fail_structural_coverage(parts):
    with pytest.raises(HTTPException):asyncio.run(invoke(model_output(parts)))

def test_each_requested_clause_requires_its_own_assessment():
    prompt='Explain R2 saved configuration. Compare it with the current capture.'
    with pytest.raises(HTTPException):asyncio.run(invoke(model_output(),prompt))
    result,schema=asyncio.run(invoke(model_output([assessment(),assessment('request-2')]),prompt))
    assert len(result['outcome_assessments'])==2
    assert schema['properties']['outcome_assessments']['minItems']==2

def test_limited_answer_is_valid_and_preserved_without_semantic_credit():
    output=model_output([assessment(status='limited',missing=['Unavailable syslog'])],answer='Saved text is available; logs are unavailable, so the cause remains unknown.')
    result,_=asyncio.run(invoke(output))
    text,trace=preview(result,'off',[],[],{},'Explain the available record.')
    assert text.endswith(output['answer'])
    assert trace['model_synthesis'] and 'not semantic certification' in trace['outcome_assessment_authority']

def test_nonempty_self_assessment_does_not_certify_prose_truth():
    result,_=asyncio.run(invoke(model_output(answer='A deliberately unsupported claim for a verifier-OFF structural test.')))
    text,trace=preview(result,'off',[],[],{},'Explain the available record.')
    assert text.endswith(result['answer']) and trace['semantic_verification']=='off'
    assert trace['interpretation_authority'].startswith('none')

@pytest.mark.parametrize('changes',[
    {'decision':'need_more_evidence','additional_reads':[]},
    {'decision':'need_more_evidence','additional_reads':[{'reader':'network.state','gap':'Missing state','why':'Needed'}]},
    {'decision':'answer','additional_reads':[{'reader':'network.state','gap':'Missing state','why':'Needed'}]},
])
def test_decision_cannot_silently_request_reads_without_material_gap(changes):
    with pytest.raises(HTTPException):asyncio.run(invoke(model_output(**changes)))

def test_explicit_material_gap_allows_proposal_but_execution_still_requires_registry():
    result,_=asyncio.run(invoke(model_output([assessment(status='unresolved',missing=['Recorded operational interface state'])],
        decision='need_more_evidence',additional_reads=[{'reader':'network.state','gap':'Operational state','why':'Saved CLI alone cannot establish forwarding'}])))
    assert result['decision']=='need_more_evidence'
    original={key:value for key,value in result.items() if key not in {'raw_output','model','input_packet'}}
    with pytest.raises(HTTPException):asyncio.run(invoke(original,continuation={'continuation_round':1}))

def test_self_assessment_unknown_evidence_ref_is_rejected():
    with pytest.raises(HTTPException):asyncio.run(invoke(model_output([assessment(sources=['S99'])])))

class RequiredReads(GraphRoles):
    async def test_optional_reads_remain_proposals_and_do_not_execute(self):
        first=plan(['configuration','syslog'])
        first['information_needs'][1]['necessity']='optional'
        r,packets=await self.scoped('studio','Compare R2 saved and current configuration.',[
            first,decision('The recorded saved text is available; current state remains unestablished. [S1]')])
        assert [r['tool'] for r in r.observations]==['network.configuration']
        assert r.context_coverage['agent']['planning']['optional_information_needs'][0]['domain']=='syslog'
        assert r.context_coverage['agent']['planning']['role_information_needs'][1]['necessity']=='optional'
        assert packets[0]['schema']['$defs']['InformationNeed']['properties']['necessity']['enum']==['required','optional']
        assert r.answer.endswith('The recorded saved text is available; current state remains unestablished. [S1]')

    async def test_compound_required_reads_survive_and_both_outcomes_reach_reasoner(self):
        r,packets=await self.scoped('floating','Inspect R2 saved configuration. Explain available syslog and its limitations.',[
            plan(['configuration','syslog']),decision('The saved text is present; no syslog observation establishes a cause. [S1]')])
        assert {r['tool'] for r in r.observations}=={'network.configuration','network.syslog'}
        packet=json.loads(packets[-1]['messages'][1]['content'])
        assert len(packet['requested_clauses'])==2 and 'OWNED_CONFIG' in str(packet['reader_results'])
        assert packet['retrieval_boundary']['remaining_role_calls']==2
        assert len(packet['retrieval_boundary']['executed_queries'])==2
