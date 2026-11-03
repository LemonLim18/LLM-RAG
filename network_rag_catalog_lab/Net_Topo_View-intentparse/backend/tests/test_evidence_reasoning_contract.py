"""Declared facts and original obligations, not tests of LLM intelligence."""
import asyncio,copy,json,sys,unittest
from pathlib import Path
from types import SimpleNamespace
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm.gateway_models import Evidence
from llm.orchestration.reasoning_contract import mode,attach,validate,release,ledger
from llm.orchestration.role_reasoning import evidence_packet,decide,parse_decision,preview
from llm.orchestration.request_contract import requested_clauses

@pytest.fixture(autouse=True)
def flags(monkeypatch):
    monkeypatch.setenv('COGNISHIELD_AI_REASONING_CONTRACT','off')
    monkeypatch.setenv('COGNISHIELD_AI_COMPLETENESS','0')
    monkeypatch.setenv('COGNISHIELD_AI_OUTCOMES','0')
    monkeypatch.setenv('COGNISHIELD_AI_EVIDENCE_HARNESS','0')
    monkeypatch.setenv('COGNISHIELD_AI_EVIDENCE_LAYOUT','current')

def inputs(question='Explain the recorded state. Can you establish the cause?'):
    records=[{'id':'p1','kind':'interface_state','device_id':91,'interface_id':911,'vrf':'red',
        'timestamp':'2026-10-10T09:00:00Z','admin_status':'up','oper_status':'down'}]
    return dict(request=question,results=[{'tool':'network.state','status':'success','evidence_ids':['receipt'],
        'data':{'records':records,'source_available':True},
        'reader_receipt':{'invocation_id':'invocation','parameters':{'device_refs':['91'],'interface_refs':['911'],'live':False}}}],
        evidence=[Evidence(id='receipt',source='synthetic-state',origin='simulated')],history=[],planning={})

def packet(args=None):return attach(json.loads(evidence_packet(**(args or inputs()))),'relationships')

def decision(p):
    return {'decision':'answer','answer':'A useful qualified explanation.','sources':['S1'],'claims':[],
        'raw_output':'preserved raw model output','outcomes':[{'obligation_id':o['obligation_id'],
        'conclusion':'A useful qualified explanation.','evidence_ids':['p1'],'status':'unresolved',
        'limitations':['Cause not established'],'assertions':[]} for o in p['reasoning_contract']['obligations']]}

def typed(p,relationship,value=None,authority=None):
    f=next(x for x in p['reasoning_contract']['relationships']['facts'] if x['relationship']==relationship)
    return {'relationship_id':f['id'],'value':f['value'] if value is None else value,'authority':authority or p['reasoning_contract']['relationships']['source_records'][f['record_index']]['authority']}

def test_default_and_invalid_flag(monkeypatch):
    assert mode()=='off'
    monkeypatch.setenv('COGNISHIELD_AI_REASONING_CONTRACT','auto')
    with pytest.raises(Exception):mode()

def test_original_spans_questions_and_no_invented_domain_obligations():
    q='Explain 10.4.0.0/24 on ge-0/0/1.0. Does the evidence show continuity? Name its limitations.'
    p=packet(inputs(q));items=p['reasoning_contract']['obligations'];assert len(items)==3
    for o in items:assert q[slice(*o['original_span'])]==o['requested_outcome']
    assert len(packet(inputs('Show a recorded prefix.'))['reasoning_contract']['obligations'])==1
    assert requested_clauses(q)!=requested_clauses(q,detailed=True)
    assert not any('return-path' in o['requested_outcome'] for o in items)

def test_background_not_promoted_and_no_new_executable_scope():
    args=inputs('Archive supplied the memo. Explain the recorded state on Target.')
    p=packet(args)
    assert p['reader_results']==args['results']
    assert 'Archive' not in json.dumps(p['reasoning_contract']['obligations'][0]['scope_refs'])
    assert p['reader_results'][0]['reader_receipt']['parameters']['device_refs']==['91']

def test_feature_off_preserves_packet_schema_and_consent(monkeypatch):
    from llm.model_roles import consent_manifest
    assert 'reasoning_contract' not in json.loads(evidence_packet(**inputs()))
    original=consent_manifest();assert 'reasoning_enhancement' not in original
    monkeypatch.setenv('COGNISHIELD_AI_REASONING_CONTRACT','obligations')
    altered=consent_manifest();assert altered['reasoning_enhancement']['mode']=='obligations'
    assert {k:v for k,v in altered.items() if k!='reasoning_enhancement'}==original

@pytest.mark.parametrize('status',['possible','unresolved','established'])
def test_complete_structured_coverage_is_not_semantic_certificate(status):
    p=packet();d=decision(p)
    for o in d['outcomes']:o['status']=status
    r=validate(d,p);assert r['coverage_complete'] and not r['semantic_certified']
    assert release({**d,'reasoning_validation':r})['answer']==d['answer']

def test_missing_outcome_is_not_missing_source_even_with_complete_self_report():
    p=packet();d=decision(p);d['outcomes'].pop();d['outcome_assessments']=[{'status':'supported','assessment':'Everything complete'}]
    r=validate(d,p);assert not r['coverage_complete']
    finding=r['findings'][0];assert finding['kind']=='MISSING_OBLIGATION'
    assert finding['evidence_availability']=='records_admitted_not_semantic_sufficiency'
    assert 'not a missing-source finding' in release({**d,'reasoning_validation':r})['answer']

@pytest.mark.parametrize('change,kind',[
    ('duplicate','INVALID_OBLIGATION_ID'),('unknown','INVALID_OBLIGATION_ID'),
    ('evidence','INVALID_EVIDENCE_REFERENCE'),('relation','INVALID_RELATIONSHIP_REFERENCE'),
    ('binding','INCORRECT_EVIDENCE_BINDING')])
def test_authoritative_bindings_fail_closed_optional_navigation_is_unverified(change,kind):
    p=packet();d=decision(p);o=d['outcomes'][0]
    if change=='duplicate':d['outcomes'].append(copy.deepcopy(o))
    if change=='unknown':o['obligation_id']='invented'
    if change=='evidence':o['evidence_ids']=['invented']
    if change=='relation':o['assertions']=[{'relationship_id':'R999999','value':'up','authority':'recorded'}]
    if change=='binding':
        p['sources'].append({'id':'other-receipt'});o['evidence_ids']=['S2'];o['assertions']=[typed(p,'interface_oper_state')]
    r=validate(d,p);assert kind in [f['kind'] for f in r['findings']]
    if change=='relation':
        released=release({**d,'reasoning_validation':r})
        assert released['reasoning_release']['optional_metadata_status']=='INVALID_UNVERIFIED'
        assert d['answer'] in released['answer'] and not r['semantic_certified']
        return
    assert release({**d,'reasoning_validation':r})['reasoning_release']['disposition']=='WITHHELD_INVALID_BINDING'

def test_valid_source_label_resolves_to_its_existing_receipt():
    p=packet();d=decision(p);d['outcomes'][0].update(evidence_ids=['S1'],assertions=[typed(p,'interface_oper_state')])
    r=validate(d,p);assert not r['findings']
    assert release({**d,'reasoning_validation':r})['answer']==d['answer']

@pytest.mark.parametrize('field,wrong',[('device_identity',92),('interface_identity',922),('vrf_membership','blue'),('interface_oper_state','up')])
def test_declared_identity_scope_and_state_contradictions_not_released(field,wrong):
    p=packet();d=decision(p);o=d['outcomes'][0];o['assertions']=[typed(p,field,wrong)];o['status']='established'
    r=validate(d,p);assert r['conflicts']
    assert release({**d,'reasoning_validation':r})['answer']!=d['answer']
    o['assertions']=[typed(p,field)];r=validate(d,p)
    assert not r['conflicts'] and release({**d,'reasoning_validation':r})['answer']==d['answer']

def test_temporal_semantics_and_positive_verified_application_retained():
    args=inputs('Compare snapshots and staged content. State whether activation is established.')
    args['results'][0]['tool']='network.configuration'
    rows=args['results'][0]['data']['records']=[
        {'id':'run1','kind':'running_configuration','device_id':91,'timestamp':'2026-10-10T07:00:00Z','config_text':'description A'},
        {'id':'run2','kind':'running_configuration','device_id':91,'timestamp':'2026-10-10T08:00:00Z','config_text':'description B'},
        {'id':'draft','kind':'configuration_snapshot','device_id':91,'saved_at':'2026-10-10T07:20:00Z','config_text':'shutdown'},
        {'id':'applied','kind':'configuration_change','device_id':91,'timestamp':'2026-10-10T07:50:00Z','effective_at':'2026-10-10T07:49:00Z','applied':True,'verification_status':'verified'}]
    p=packet(args);v=p['reasoning_contract']['relationships']
    assert p['reader_results'][0]['data']['records']==rows
    assert v['sample_groups'][0]['between_samples']=='not_established_by_sample_pair'
    assert not any(v['source_records'][f['record_index']]['record_id']=='draft' and f['relationship']=='application_status' for f in v['facts'])
    assert any(v['source_records'][f['record_index']]['record_id']=='applied' and f['relationship']=='application_status' and f['value'] is True for f in v['facts'])
    assert any(f['relationship']=='effective_at' and f['value'].endswith('07:49:00Z') for f in v['facts'])
    assert not any('cause' in f['relationship'] for f in v['facts'])

def test_independent_directions_ingress_vrf_and_modeled_denial():
    args=inputs();r=args['results'][0]['data']['records'][0]
    r.update(id='flow',kind='forwarding_assessment',derived=True,assessment={
        'forward':{'status':'delivered','scope':{'vrf':'red'},'branches':[{'hops':[{'device_id':92,'ingress':{'device_id':92,'interface_id':921},'egress':{'device_id':92,'interface_id':922}}]}]},
        'return':{'status':'failed','scope':{'vrf':'blue'},'branches':[{'failure_location':{'device_id':93,'interface_id':931,'interface_role':'ingress'}}]}})
    p=packet(args);facts=p['reasoning_contract']['relationships']['facts']
    assert any(f['value']==921 and f['scope']['device_id']==92 and f['scope']['direction']=='forward' for f in facts)
    assert any(f['value']=='failed' and f['scope']['direction']=='return' for f in facts)
    assert all('device_id' not in f['scope'] and not f['inherits_record_scope'] for f in facts if f['value']=='failed')
    d=decision(p)
    for o in d['outcomes']:o['evidence_ids']=['flow']
    f=next(f for f in facts if f['value']=='failed')
    d['outcomes'][0]['assertions']=[{'relationship_id':f['id'],'value':'delivered','authority':'modeled'}]
    assert validate(d,p)['conflicts']
    d['outcomes'][0]['assertions']=[{'relationship_id':f['id'],'value':'failed','authority':'physical'}]
    assert validate(d,p)['conflicts']
    d['outcomes'][0]['assertions'][0]['authority']='modeled'
    assert not validate(d,p)['conflicts']

def test_conflicts_and_unknown_times_are_not_silently_normalized():
    args=inputs();first=args['results'][0]['data']['records'][0]
    args['results'][0]['data']['records'].append({**first,'oper_status':'up','source':'contradictory-recorder'})
    original=copy.deepcopy(args);p=packet(args)
    assert args==original and len(p['reader_results'][0]['data']['records'])==2
    facts=p['reasoning_contract']['relationships']['facts']
    assert {f['value'] for f in facts if f['relationship']=='interface_oper_state'}=={'up','down'}
    assert 'transition_time' not in json.dumps(p['reasoning_contract'])

def test_metadata_cannot_evict_raw_operands_at_admission_bound(monkeypatch):
    monkeypatch.setenv('COGNISHIELD_AI_REASONING_CONTRACT','relationships')
    args=inputs();args['results'][0]['data']['records'][0]['note']='x'*58000
    original=copy.deepcopy(args);p=json.loads(evidence_packet(**args))
    assert p['reader_results']==args['results'] and len(json.dumps(p,ensure_ascii=False,separators=(',',':')))<=64000
    assert args==original
    args['results'][0]['data']['records'][0]['note']='x'*65000
    with pytest.raises(Exception) as e:evidence_packet(**args)
    assert e.value.status_code==413

@pytest.mark.parametrize('raw',['not JSON','{"decision":"answer", bad}',json.dumps({'decision':'execute','answer':'no','outcomes':[]}),json.dumps({'decision':'answer','answer':'x','outcomes':'not-list'})])
def test_invalid_core_or_partial_json_cannot_bypass_validation(raw):
    with pytest.raises(Exception):parse_decision(raw,grounded=True)

@pytest.mark.parametrize('selected',['off','obligations','relationships'])
def test_actual_decide_and_preview_share_contract_without_extra_inference(monkeypatch,selected):
    monkeypatch.setenv('COGNISHIELD_AI_REASONING_CONTRACT',selected)
    args=inputs('Explain the recorded state.');calls=[]
    class Model:
        hybrid=SimpleNamespace(remote_calls=0,max_remote_calls=3)
        async def generate(self,messages,structured,purpose):
            calls.append((messages,structured));p=json.loads(messages[-1]['content'])
            d={'decision':'answer','answer':'State is recorded; cause is not established. [S1]','sources':['S1'],
               'outcome_assessments':[{'clause':c['id'],'status':'limited','sources':['S1'],'assessment':'Source-scoped observation'} for c in p['requested_clauses']]}
            if selected!='off':d['outcomes']=[{'obligation_id':o['obligation_id'],'conclusion':d['answer'],'status':'unresolved','evidence_ids':['p1'],'limitations':[]} for o in p['reasoning_contract']['obligations']]
            return json.dumps(d),'synthetic-test-model'
    d=asyncio.run(decide(Model(),**args));answer,trace=preview(d,'off',[],args['evidence'],{},args['request'])
    assert len(calls)==1 and 'cause is not established' in answer
    assert ('reasoning_validation' in trace)==(selected!='off')
    assert ('outcomes' in calls[0][1]['properties'])==(selected!='off')

class ReasoningGatewayGraph(unittest.IsolatedAsyncioTestCase):
    from tests.test_model_role_graph import GraphRoles as _fixtures
    setUp=_fixtures.setUp
    scoped=_fixtures.scoped

    def test_old_consent_cannot_authorize_new_reasoning_mode(self):
        import time
        from uuid import uuid4
        from unittest.mock import patch
        from llm.gateway_models import TurnRequest
        from llm.gemini_provider import approve_hybrid_request,HybridRequest
        context={'eligible':True,'scenario_digest':'synthetic','source_revision':'r1','scenario_id':'test'}
        with patch.dict('os.environ',{'COGNISHIELD_AI_HYBRID':'1','COGNISHIELD_AI_MULTI_MODEL_EXPERIMENT':'1','COGNISHIELD_AI_REASONING_CONTRACT':'off'}),patch('llm.gemini_provider.scenario_approval_context',return_value=context):
            cid=self.g.store.create('alice','floating')['id'];body=TurnRequest(request_id=uuid4(),prompt='Investigate R2 saved configuration.')
            approve_hybrid_request(self.db,self.g.store,self.user,cid,body,'r1')
            with patch.dict('os.environ',{'COGNISHIELD_AI_REASONING_CONTRACT':'relationships'}):
                assert HybridRequest.create(self.db,self.g.store,self.user,'floating',cid,body,time.monotonic()) is None

    async def test_no_read_advice_stays_zero_execution_with_contract_enabled(self):
        from unittest.mock import patch
        from tests.test_model_role_graph import plan,decision
        d=decision('Ask for the recorded admin history and a separate operational observation; neither check has been performed.')
        d['outcomes']=[{'obligation_id':'request-1','conclusion':d['answer'],'status':'unresolved','evidence_ids':[],
            'limitations':['Proposed checks are not observations']}]
        with patch.dict('os.environ',{'COGNISHIELD_AI_REASONING_CONTRACT':'relationships'}):
            r,packets=await self.scoped('floating','Recommend two passive checks for R2; do not read or collect anything.',[plan(['state']),d])
        assert not r.observations and len(packets)==2 and d['answer'] in r.answer

    async def test_both_existing_assistants_preserve_model_prose_and_declared_coverage(self):
        from unittest.mock import patch
        from tests.test_model_role_graph import plan,decision
        for surface in ['floating','studio']:
            d=decision('Saved text is present; activation is not established. [S1]')
            d['outcomes']=[{'obligation_id':'request-1','conclusion':d['answer'],
                'evidence_ids':['S1'],'status':'unresolved','limitations':['Saved text is not activation evidence']}]
            with patch.dict('os.environ',{'COGNISHIELD_AI_REASONING_CONTRACT':'relationships'}):
                r,packets=await self.scoped(surface,'Investigate R2 using saved configuration only.',[plan(['configuration']),d])
            assert len(packets)==2 and {row['tool'] for row in r.observations}=={'network.configuration'}
            assert d['answer'] in r.answer
            trace=r.context_coverage['agent']['experimental_interpretation']
            assert trace['reasoning_validation']['coverage_complete'] and not trace['reasoning_validation']['semantic_certified']
            assert trace['outcomes'][0]['status']=='unresolved'

    async def test_missing_model_outcome_is_reported_without_extra_reads_or_critic(self):
        from unittest.mock import patch
        from tests.test_model_role_graph import plan,decision
        d=decision('Only saved text is known. [S1]');d['outcomes']=[]
        with patch.dict('os.environ',{'COGNISHIELD_AI_REASONING_CONTRACT':'obligations'}):
            r,packets=await self.scoped('floating','Investigate R2 using saved configuration only.',[plan(['configuration']),d])
        assert len(packets)==2
        assert 'not a missing-source finding' in r.answer
        assert r.context_coverage['agent']['experimental_interpretation']['reasoning_validation']['findings'][0]['kind']=='MISSING_OBLIGATION'
