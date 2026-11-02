"""Advice execution boundaries and successful explanation preservation, no cloud."""
import asyncio,json,sys,time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock,patch
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm.gateway_routing import advisory_route
from llm.orchestration.request_contract import advisory_contract,requested_contract,project_read_outcomes
from llm.orchestration.synthesis import synthesize
from llm.gateway_models import Evidence

@pytest.mark.parametrize('prompt',[
 'Recommend two useful evidence requests without reading them.',
 'Based on that limitation, recommend evidence for Birch. Do not collect anything.',
 'Which observations should I inspect next, and why would they help? Do not retrieve them.',
 'Which records should I ask for next about that uncertainty, and why would they help? Do not read or collect them now.',
])
def test_advice_uses_existing_contract_without_general_outcome_pilot(prompt,monkeypatch):
    monkeypatch.setenv('COGNISHIELD_AI_OUTCOMES','0')
    c=advisory_contract(prompt)
    assert c and c.advice_only and c.original_request==prompt
    route=advisory_route(prompt,None,{'devices':[]})
    assert not route.network_domains and not route.source_requests and not route.use_editor

@pytest.mark.parametrize('prompt',[
 'Read Birch syslog now, then recommend next checks.',
 'Do not suggest checks; show the recorded route table.',
 'What did the old report recommend?',
 'Explain how routers select routes.',
])
def test_advice_boundary_does_not_suppress_present_reads_or_general_questions(prompt):
    assert advisory_contract(prompt) is None

def test_valid_mapping_and_shared_read_parts_survive_projection():
    c=requested_contract('Read Birch saved text. Explain how its fields map to the published requirements.',
        needs=[{'domain':'configuration'},{'domain':'knowledge'}])
    rows=[{'tool':'network.configuration','status':'success','evidence_ids':['c'],'data':{}},
          {'tool':'knowledge.search','status':'success','evidence_ids':['k'],'data':{}}]
    parts=[{'id':o.id,'answer':'The recorded process maps to process_id [S1,S2].','sources':['S1','S2']} for o in c.outcomes]
    result,reasons=project_read_outcomes(c,parts,rows,[])
    assert result==parts and reasons==[]  # No duplicated record sections.

def test_advice_rationale_is_not_falsely_treated_as_a_current_observation():
    c=advisory_contract('Recommend relevant questions; do not read them.')
    payload={'checks':[{'reader':'network.configuration','question':'What configuration was active at the observation time?',
      'rationale':'This question could clarify configuration assumptions relevant to operational state; it is not a measurement.'}]}
    model=SimpleNamespace(generate=AsyncMock(return_value=(json.dumps(payload),'test-model')))
    answer,trace=asyncio.run(synthesize(model,None,c.original_request,[],[],{},'fallback',requested_outcomes=c,
        advisory_context={'authorized_readers':['network.configuration'],'devices':['Birch']}))
    assert trace['status']=='advisory_proposed' and 'not verified observations' in answer
    assert trace['scope'].startswith('Typed unexecuted')
    assert model.generate.await_count==1

def test_quota_hard_input_cap_cannot_be_raised_by_environment(tmp_path,monkeypatch):
    from llm.gemini_provider import _quota_update
    from fastapi import HTTPException
    monkeypatch.setenv('COGNISHIELD_AI_HYBRID_USAGE',str(tmp_path/'quota.json'))
    monkeypatch.setenv('COGNISHIELD_AI_HYBRID_INPUT_TPM','999999')
    with pytest.raises(HTTPException) as e:_quota_update('gemini-3.5-flash-lite',reservation=150001)
    assert e.value.status_code==429


def test_published_optional_modality_is_bound_to_its_field_not_sentence():
    from llm.orchestration.synthesis import PublishedAnswerDraft,published_answer_errors
    facts=[{'operation_id':'test','required':[],'required_by_vendor':{'cisco':['process_id']},'vendor_platforms':[],
        'sources':['S1'],'fields':[{'field':'process_id','type':'integer'},{'field':'router_id','type':'string'}]}]
    def errors(text):return published_answer_errors(PublishedAnswerDraft(answer=text,sources=['S1'],operation_ids=['test']),facts,'Map fields')
    assert not errors('The process_id (20) and optional router_id identify the mapped commands. [S1]')
    assert not errors('The process_id (20) and optional router identifier fields map to commands. [S1]')
    assert errors('process_id is optional. [S1]')
    assert errors('process_id and router_id are optional. [S1]')


@pytest.mark.parametrize('text,invalid',[
    ('The contract has optional process_id. Cisco requires process_id by vendor-conditional rules. [S1]',False),
    ('process_id is optional for Cisco. Cisco requires process_id. [S1]',True),
    ('process_id is optional for Juniper. [S1]',False),
])
def test_vendor_qualification_preserves_field_and_platform_identity(text,invalid):
    from llm.orchestration.synthesis import PublishedAnswerDraft,published_answer_errors
    facts=[{'operation_id':'test','required':[],'required_by_vendor':{'cisco':['process_id']},
        'vendor_platforms':[{'vendor':'cisco','platform':'iosxe','versions':[]},{'vendor':'juniper','platform':'junos','versions':[]}],
        'sources':['S1'],'fields':[{'field':'process_id','type':'integer'},{'field':'router_id','type':'string'}]}]
    errors=published_answer_errors(PublishedAnswerDraft(answer=text,sources=['S1'],operation_ids=['test']),facts,'Map fields')
    assert bool(errors)==invalid


def test_disabled_down_alias_is_not_an_ownership_contradiction():
    from llm.orchestration.synthesis import interface_state_claim_errors
    ctx=[{'tool':'network.state','status':'success','data':{'records':[{'kind':'interface_state',
        'hostname':'Transit','interface':'Eth7','current':True,'admin_status':'down','oper_status':'down'}]}}]
    assert not interface_state_claim_errors('The outgoing interface Eth7 on Transit is disabled.',ctx)
    assert interface_state_claim_errors('The outgoing interface Eth7 on Transit is enabled.',ctx)


def test_explicit_unverified_configuration_caveat_is_not_healthy_claim():
    from llm.orchestration.synthesis import check_candidate
    assert 'Configuration text does not establish completeness or operational health' not in check_candidate(
        'The saved configuration is historical; operational state remains unverified.',[],[],{})
    assert 'Configuration text does not establish completeness or operational health' in check_candidate(
        'The configuration proves the device is operational.',[],[],{})


def test_quota_usage_update_cannot_hide_original_provider_error(monkeypatch):
    from llm.gemini_provider import interpret_rest
    from fastapi import HTTPException
    import httpx
    monkeypatch.setenv('GEMINI_API_KEY','fake-test-key');monkeypatch.setenv('GEMINI_MODEL','gemini-3.5-flash-lite')
    async def send(client,request,**kwargs):return httpx.Response(401,json={'error':{'status':'UNAUTHENTICATED'}},request=request)
    with patch('llm.gemini_provider._quota_update',side_effect=[('persisted-reservation',0),HTTPException(503,'test ledger busy')]),\
         patch.object(httpx.AsyncClient,'send',send),pytest.raises(HTTPException) as error:
        asyncio.run(interpret_rest([{'role':'user','content':'synthetic'}],False,timeout=2))
    assert error.value.provider_http_status==401 and error.value.provider_category=='UNAUTHENTICATED'
    assert 'conservative reservation' in error.value.provider_usage['quota_accounting']

from tests import test_b1_agent as fixtures
import unittest

class AdviceGatewayBoundary(unittest.IsolatedAsyncioTestCase):
    setUp=fixtures.B1Tests.setUp
    ask=fixtures.B1Tests.ask

    async def test_both_surfaces_off_preserve_owned_context_and_do_not_execute(self):
        for surface in ['floating','studio']:
            cid=self.g.store.create('alice',surface)['id']
            with patch.dict('os.environ',{'COGNISHIELD_AI_ENGINE':'langgraph_b3','COGNISHIELD_AI_OUTCOMES':'0'}):
                await self.ask('Show R2 interfaces',identity=cid)
                raw=json.dumps({'checks':[{'reader':'network.state','question':'Which operational observations exist for R2?',
                    'rationale':'Those records could distinguish a source gap from a recorded device state.'}]})
                with patch('llm.orchestration.model.RoutingModel.generate',AsyncMock(return_value=(raw,'test-model'))) as model,\
                     patch.object(self.g.registry,'invoke',wraps=self.g.registry.invoke) as reader:
                    r=await self.ask('Based on that limitation, recommend a useful check for R2. Do not read, collect, or change anything.',identity=cid)
                reader.assert_not_called()
                packet=json.loads(model.await_args.args[0][1]['content'])
                assert packet['reference_context']['devices']==['R2'] and 'R2' in packet['reference_context']['prior_user_goal']
                assert packet['reference_context']['prior_read_receipts'][0]['tool']=='inventory.read'
                assert packet['reference_context']['prior_read_receipts'][0]['status']=='success'
                assert 'OWNED_CONFIG' not in str(packet) and not r.observations
                assert 'Recommended evidence' in r.answer and r.context_coverage['routing']['history']

