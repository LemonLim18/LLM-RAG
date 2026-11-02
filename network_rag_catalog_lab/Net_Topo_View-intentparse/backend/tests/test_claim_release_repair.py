"""Core/auxiliary independence and definite contradiction release boundaries."""
import json,sys
from pathlib import Path
from unittest.mock import patch
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm.orchestration.role_reasoning import EvidenceDecision,parse_decision
from llm.model_roles import validate_result
from llm.orchestration.investigation_support import compatible_claims,release_interpretation
from tests.test_completeness_investigation import INVENTORY,row,record,claim
from tests.test_model_role_graph import GraphRoles,plan,decision

def reviewed(c,records=None,tool='network.state'):
    return compatible_claims({'answer':c['statement'],'claims':[c]},[row(tool,records or [record()])],INVENTORY)

def test_six_verdicts_are_not_one_conflict_bucket():
    assert reviewed(claim())['claims'][0]['verdict']=='SUPPORTED'
    assert reviewed(claim(value='up'))['claims'][0]['verdict']=='CONTRADICTED'
    assert reviewed(claim(record_refs=['missing']))['claims'][0]['verdict']=='INSUFFICIENT_EVIDENCE'
    assert reviewed(claim('root_cause','A possible mechanism.'))['claims'][0]['verdict']=='NOT_MECHANICALLY_CHECKABLE'
    assert reviewed(claim('measured_loss_percent','2.5'))['claims'][0]['verdict']=='MODEL_CONTRACT_ERROR'
    with patch('llm.orchestration.investigation_support._compatible_operands',side_effect=RuntimeError('validator failed')):
        r=reviewed(claim());assert r['claims'][0]['verdict']=='VALIDATOR_ERROR' and not r['conflicts']

def test_whole_device_config_missing_port_is_not_contrary_owner():
    r=record('capture',kind='running_configuration',interface_id=None,config_text='interface Ethernet1\n shutdown')
    c=claim('interface_admin_status','down',record_refs=['capture'],field='admin_status')
    assert reviewed(c,[r],'network.configuration')['claims'][0]['verdict']=='NOT_MECHANICALLY_CHECKABLE'
    wrong=record(device_id=2,interface_id=21)
    assert reviewed(claim(),[wrong])['claims'][0]['verdict']=='CONTRADICTED'

def test_paraphrased_event_is_unchecked_not_a_false_event():
    event=record('event',kind='syslog_event',message='Inspection was requested before any replacement; no repair is recorded.')
    c=claim('incident_occurred','A review was requested.',record_refs=['event'],field='message')
    r=reviewed(c,[event],'network.syslog');assert not r['conflicts']
    assert r['claims'][0]['verdict']=='NOT_MECHANICALLY_CHECKABLE'
    assert reviewed({**c,'value':event['message']},[event],'network.syslog')['claims'][0]['verdict']=='SUPPORTED'
    assert reviewed({**c,'record_refs':['unavailable']},[event],'network.syslog')['claims'][0]['verdict']=='INSUFFICIENT_EVIDENCE'

def test_conflicting_observations_not_arbitrarily_selected():
    r=reviewed(claim(),[record(),record(oper_status='up')])
    assert r['claims'][0]['verdict']=='INSUFFICIENT_EVIDENCE' and not r['conflicts']

def test_capture_time_and_ecmp_branch_boundaries():
    r=record(timestamp='2026-10-29T08:00:00+08:00')
    assert reviewed(claim(timestamp='2026-10-29T00:00:00Z'),[r])['claims'][0]['verdict']=='SUPPORTED'
    assert reviewed(claim(timestamp='2026-10-29T01:00:00Z'),[r])['claims'][0]['verdict']=='NOT_MECHANICALLY_CHECKABLE'
    flow=record('flow',kind='forwarding_assessment',derived=True,assessment={'forward':{'status':'partial','branches':[
        {'id':'a','status':'failed','failure_location':{'device_id':1,'interface_id':11}},
        {'id':'b','status':'delivered'}]}})
    c=claim('simulated_forwarding','failed',record_refs=['flow'],direction='forward',branch_id='a',scope='modeled')
    assert reviewed(c,[flow])['claims'][0]['verdict']=='SUPPORTED'
    assert reviewed({**c,'device_id':None,'interface_id':None,'branch_id':None},[flow])['claims'][0]['verdict']=='CONTRADICTED'
    assert reviewed({**c,'value':'delivered'},[flow])['claims'][0]['verdict']=='CONTRADICTED'

def test_valid_core_survives_invalid_auxiliary_without_coercion():
    raw=decision('The recorded port is down.');raw['claims']=[claim(device_id=1),claim()]
    schema=EvidenceDecision.model_json_schema();schema['x-auxiliary-fields']=['claims']
    validate_result(json.dumps(raw),schema)
    core,aux=parse_decision(json.dumps(raw),True)
    assert core.answer==raw['answer'] and len(core.claims)==1
    assert core.claims[0].device_id=='1' and aux['status']=='MODEL_CONTRACT_ERROR'
    assert aux['errors'][0]['location']=='claims/0'
    with pytest.raises(Exception):validate_result(json.dumps({**raw,'decision':'execute'}),schema)
    with pytest.raises(Exception):parse_decision('{"decision":"answer", unquoted:1}',True)
    with pytest.raises(Exception):parse_decision(json.dumps({**raw,'additional_reads':[{'reader':'network.state'}]}),True)

def test_core_and_query_contracts_cannot_be_declared_auxiliary():
    schema=EvidenceDecision.model_json_schema();schema['x-auxiliary-fields']=['decision']
    with pytest.raises(Exception):validate_result(json.dumps({'decision':'execute','answer':'Action'}),schema)

def test_release_keeps_prose_but_never_claims_semantic_certification():
    d={'answer':'Useful source-scoped interpretation.','raw_output':'valid',
        'auxiliary_validation':{'status':'MODEL_CONTRACT_ERROR'}}
    review={'claim_compatibility':reviewed(claim(record_refs=['missing']))}
    r=release_interpretation(d,review)
    assert r['answer'].startswith(d['answer']) and r['release_decision']['unchanged_model_prose']
    assert not r['release_decision']['semantic_certified'] and 'Verification limits' in r['answer']

def test_known_false_sentence_isolated_or_explicitly_withheld():
    c=claim(value='up',statement='The port is up.')
    review={'claim_compatibility':reviewed(c)}
    r=release_interpretation({'answer':'The port is up. A different supported point remains.','raw_output':'valid'},review)
    assert 'The port is up.' not in r['answer'] and 'different supported point' in r['answer']
    assert r['release_decision']['disposition']=='PARTIAL_WITHHELD'
    r=release_interpretation({'answer':'An unlocatable paraphrase of the contradicted assertion.','raw_output':'valid'},review)
    assert r['release_decision']['disposition']=='WITHHELD'

class GraphReleaseRepair(GraphRoles):
    async def run_profile(self,prompt,outputs):
        with patch.dict('os.environ',{'COGNISHIELD_AI_COMPLETENESS':'1'}):return await self.scoped('floating',prompt,outputs)

    async def test_auxiliary_failure_does_not_trigger_regeneration(self):
        answer=decision('The saved text is available; activation is not established. [S1]');answer['claims']=[claim(device_id=2)]
        result,packets=await self.run_profile('Investigate R2 using saved configuration only.',[plan(['configuration']),answer])
        assert len(packets)==2 and 'activation is not established' in result.answer
        assert result.context_coverage['agent']['experimental_interpretation']['auxiliary_validation']['status']=='MODEL_CONTRACT_ERROR'

    async def test_prior_valid_draft_retained_after_revision_contract_failure(self):
        # A rejected executable query warrants one bounded correction, without
        # discarding the valid qualified core if that correction is malformed.
        extra=[{'reader':'network.state','parameters':{'device_refs':['2'],'live':True},'gap':'Missing observation','why':'Discriminate alternatives','evidence_refs':['S1']}]
        first=decision('Only saved text is available; no live conclusion is supported. [S1]',extra)
        r,packets=await self.run_profile('Investigate R2 using saved configuration only.',[plan(['configuration']),first,{'decision':'execute','answer':'Invalid'}])
        assert len(packets)==3 and 'no live conclusion is supported' in r.answer
        assert r.context_coverage['agent']['investigation']['revision_failures'][0]['retained_valid_core']

    async def test_core_unknown_source_still_fails_closed(self):
        bad=decision('Unsupported source [S99].');bad['sources']=['S99']
        r,_=await self.run_profile('Investigate R2 using saved configuration only.',[plan(['configuration']),bad])
        assert 'Unsupported source [S99]' not in r.answer

    def controlled_state(self):
        from llm.gateway_models import ToolResult,Evidence
        async def read(params,auth):
            return ToolResult(status='success',data={'records':[record('observed-port',device_id=2,interface_id=21)]},
                evidence=[Evidence(id='controlled-receipt',source='synthetic',origin='simulated')])
        self.g.registry._tools['network.state']['fn']=read

    def false_and_correct(self):
        wrong=decision('The recorded interface is up. No changes were made. [S1]')
        wrong['claims']=[claim(value='up',statement='The recorded interface is up.',device_id='2',interface_id='21',record_refs=['observed-port'])]
        correct=decision('The recorded interface is down. No physical cause is established. [S1]')
        correct['claims']=[{**wrong['claims'][0],'value':'down','statement':'The recorded interface is down.'}]
        return wrong,correct

    async def test_real_contradiction_corrects_then_preserves_correct_prose(self):
        self.controlled_state();wrong,correct=self.false_and_correct()
        r,packets=await self.run_profile('Investigate R2 using state only.',[plan(['state']),wrong,correct])
        assert len(packets)==3 and 'recorded interface is down' in r.answer
        assert 'recorded interface is up' not in r.answer
        feedback=json.loads(packets[-1]['messages'][1]['content'])['continuation']['conflicts'][0]
        assert feedback['verdict']=='CONTRADICTED' and feedback['actual_values']==['down']
        assert feedback['bound_source_facts'][0]['device_id']==2

    async def test_failed_revision_cannot_release_known_false_prior_core(self):
        self.controlled_state();wrong,_=self.false_and_correct()
        r,_=await self.run_profile('Investigate R2 using state only.',[plan(['state']),wrong,{'decision':'execute','answer':'Invalid'}])
        assert 'The recorded interface is up.' not in r.answer
        assert r.context_coverage['agent']['experimental_interpretation']['release_decision']['disposition']=='PARTIAL_WITHHELD'

    async def test_dropping_auxiliary_claim_does_not_hide_unchanged_false_sentence(self):
        self.controlled_state();wrong,_=self.false_and_correct();dropped={**wrong,'claims':[]}
        r,packets=await self.run_profile('Investigate R2 using state only.',[plan(['state']),wrong,dropped,dropped,dropped])
        assert len(packets)==5 and 'The recorded interface is up.' not in r.answer
