"""Shared evidence/release regressions; mocked synthesis earns no model credit."""
import asyncio,json,sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm.gateway_models import Evidence
from llm.orchestration.synthesis import check_candidate,forwarding_results,synthesize

REGISTRY=Path(__file__).resolve().parents[2]/'docs/evaluations/phase_g_hybrid_quality_qualification_v1.json'

def scenario(number):return json.loads(REGISTRY.read_text())['fixtures'][f'QUALITY-Q{number:02d}']

def material(number):
    from development.network_model import Flow,assess_flow
    s=scenario(number);f=s['network']['flows'][0];assessment=assess_flow(s,Flow.model_validate(f))
    context=[{'tool':'network.state','status':'success','evidence_ids':['flow'],
        'scope_devices':s['devices'],'data':{'records':[{'kind':'forwarding_assessment','current':True,
            'timestamp':s['logical_time'],'flow':f,'assessment':assessment}]}}]
    return context,[Evidence(id='flow',source='Declared flow',origin='simulated')]

@pytest.mark.parametrize('number',[2,3,9])
def test_failure_owner_survives_missing_transit_rows(number):
    context,evidence=material(number)
    flow=forwarding_results(context,{'flow':'S1'})[0]
    f=flow['forward']['branches'][0]['failure_location'];r=flow['return']['branches'][0]['failure_location']
    assert f['hostname']==r['hostname']=='Willow-Transit'
    assert f['interface']==r['interface']=='ge-0/0/1.0'
    assert f['direction']=='egress' and r['direction']=='ingress'
    assert f['admin_status']==('down' if number==3 else 'up') and f['oper_status']=='down'
    assert flow['return']['branches'][0]['path']==['Canyon-Core']
    # Completed egress trail and actual failed ingress remain distinct.
    assert r['hostname']!=flow['return']['branches'][0]['path'][-1]

@pytest.mark.parametrize('number,device,direction',[(4,'Canyon-Core','return'),(5,'Willow-Transit','forward'),(7,'Harbor-Edge','forward'),(11,'Harbor-Edge','forward')])
def test_lookup_and_discard_failures_keep_actual_device_without_invented_port(number,device,direction):
    context,_=material(number);loc=forwarding_results(context,{})[0][direction]['branches'][0]['failure_location']
    assert loc['hostname']==device and 'interface' not in loc

def test_healthy_flow_has_no_invented_failure_location():
    context,_=material(1)
    assert all('failure_location' not in b for part in forwarding_results(context,{}) for d in ['forward','return'] for b in part[d]['branches'])


@pytest.mark.parametrize('number',[1,2,4,5,7,9,11,12,13])
def test_assessment_consumes_interface_lookup_and_policy_location_variants(number):
    from llm.orchestration.scenario_reasoning import assess_scenario
    context,evidence=material(number)
    context[0]['data']['scenario']={'authoritative_development':True,'source_revision':'test-revision'}
    row=context[0]['data']['records'][0];row.update(id='calculated-flow',freshness='fresh')
    evidence[0].authority='development_scenario'
    result=assess_scenario(context,evidence)
    assert result and result['findings']
    # Location metadata adds explanation operands, never changes delivery.
    expected=json.loads(REGISTRY.read_text())['cases'][number-1]['independent_expected_flow']
    assert row['assessment']['forward']['status']==expected['forward']
    assert row['assessment']['return']['status']==expected['return']

def test_user_source_and_auxiliary_relationship_are_distinct():
    from llm.orchestration.engine import required_synthesis_readers
    inv={'devices':[]}
    assert 'network.topology' not in required_synthesis_readers('Explain the forward loop and working reverse path.',inv,['state','topology'])
    assert 'network.topology' in required_synthesis_readers('Compare the planned links with observed topology.',inv,['topology'])
    assert {'network.configuration','network.syslog'}<=required_synthesis_readers('Read saved configuration and syslog.',inv,['configuration','syslog'])
    assert 'network.topology' not in required_synthesis_readers('Read configuration, not topology.',inv,['configuration','topology'])

def test_incidental_flow_does_not_require_an_unrelated_path_explanation():
    context,evidence=material(1)
    context.append({'tool':'network.configuration','status':'success','evidence_ids':['cfg'],'data':{'records':[
        {'hostname':'Harbor-Edge','kind':'configuration_snapshot','current':False,'config_text':'router ospf 18\n router-id 198.18.88.1\n'}]}})
    evidence.append(Evidence(id='cfg',source='Saved CLI',origin='simulated'))
    answer='The saved OSPF process18 is local, with router ID198.18.88.1. It does not establish protocol operation. [S2]'
    errors=check_candidate(answer,context,evidence,{},'Explain the saved OSPF process, not operational records.')
    assert not any('transit' in e or 'return direction' in e for e in errors)
    wrong='The forward path is Harbor-Edge → Canyon-Core, without intermediate nodes. [S1]'
    assert check_candidate(wrong,context,evidence,{},'Explain saved OSPF.')

def test_all_unknown_flow_boundary_is_data_driven_and_keeps_missing_prerequisite():
    context,evidence=material(13)
    model=SimpleNamespace(generate=AsyncMock(side_effect=AssertionError('No inference on this unsupported class')))
    answer,trace=asyncio.run(synthesize(model,None,'Do these observations establish communication?',context,evidence,{},'records'))
    assert trace['status']=='insufficient_flow_evidence_fallback'
    assert 'unknown' in answer and 'policy' in answer and 'routing evidence' not in answer
    model.generate.assert_not_awaited()

def test_unknown_flow_does_not_suppress_an_independent_configuration_outcome():
    context,evidence=material(13)
    context.append({'tool':'network.configuration','status':'success','evidence_ids':['cfg'],'data':{'records':[
        {'hostname':'Harbor-Edge','kind':'configuration_snapshot','current':False,'config_text':'hostname Harbor-Edge\n'}]}})
    evidence.append(Evidence(id='cfg',source='Saved CLI',origin='simulated'))
    model=SimpleNamespace(generate=AsyncMock(return_value=(json.dumps({'answer':'The saved hostname is Harbor-Edge. Delivery remains unknown because policy observations are unavailable. [S1] [S2]','sources':['S1','S2'],'hypotheses':[]}), 'unit')))
    _,trace=asyncio.run(synthesize(model,None,'Explain the saved configuration and available observations.',context,evidence,{},'records'))
    assert trace['status']!='insufficient_flow_evidence_fallback' and model.generate.await_count>0

def config_context():
    return [{'tool':'network.configuration','status':'success','data':{'records':[
        {'hostname':'RouterOne','kind':'configuration_snapshot','current':False,'config_text':'hostname RouterOne\nrouter bgp 65101\n neighbor 192.0.2.2 remote-as 65202\n'},
        {'hostname':'RouterTwo','kind':'configuration_snapshot','current':False,'config_text':'hostname RouterTwo\nrouter bgp 65303\n neighbor 192.0.2.9 remote-as 65404\n'}]}}]

@pytest.mark.parametrize('answer,bad',[
    ('RouterOne local AS65101 and remote AS65202 are saved configured values, not session measurements.',False),
    ('RouterOne local AS65303 and remote AS65404 are saved configured values.',True),
    ('RouterTwo local AS65303 and remote AS65404 are saved configured values.',False),
    ('RouterTwo remote AS65202 is recorded.',True),
])
def test_literal_configuration_role_facts_stay_owner_bound(answer,bad):
    errors=check_candidate(answer,config_context(),[],{},'Explain saved BGP values.')
    assert bool([e for e in errors if 'AS' in e])==bad


def test_asking_for_local_as_does_not_require_every_remote_as():
    ctx=config_context()[:1]
    ctx[0]['data']['records']=ctx[0]['data']['records'][:1]
    answer='RouterOne local AS 65101 is a configured value, not an observed session.'
    assert not check_candidate(answer,ctx,[],{},'Explain RouterOne local AS.')
    assert check_candidate(answer,ctx,[],{},'Explain RouterOne local and remote AS roles.')

@pytest.mark.parametrize('answer,bad',[
    ('These samples establish continuous availability of the network.',True),
    ('Both points are up, establishing uninterrupted connectivity.',True),
    ('These points do not establish continuous availability.',False),
    ('Monitor continuous availability before making that claim.',False),
    ('The observed interface is up at the recorded time.',False),
])
def test_point_state_does_not_certify_an_interval(answer,bad):
    from llm.orchestration.synthesis import source_envelope_errors
    ctx=[{'tool':'network.state','status':'success','data':{'records':[{'kind':'interface_state','admin_status':'up','oper_status':'up'}]}}]
    assert bool(source_envelope_errors(answer,ctx,'Explain state.'))==bad


@pytest.mark.parametrize('prompt',[
    'Which observations should an engineer obtain next, and why? Do not retrieve or collect anything now.',
    'For the same pair, suggest the next read-only checks without executing them. Explain the remaining uncertainty.',
    'Regarding that limitation, recommend further evidence. Do not read other sources.',
])
def test_advice_keeps_owned_scope_without_executing_prospective_checks(prompt,monkeypatch):
    from llm.gateway_routing import advisory_route
    monkeypatch.setenv('COGNISHIELD_AI_OUTCOMES','0')
    inventory={'devices':[{'id':1,'hostname':'Rowan','interfaces':[]},{'id':2,'hostname':'Alder','interfaces':[]}]}
    previous={'context_coverage':{'retrieval':{'device_refs':['1','2'],'domains':['state'],
        'entities':[{'device_id':'1'},{'device_id':'2'}],'source_requests':{}}}}
    route=advisory_route(prompt,previous,inventory)
    assert route and route.use_history and route.device_refs==['1','2']
    assert not route.network_domains and not route.source_requests and route.requested_outcomes.advice_only


@pytest.mark.parametrize('prompt',[
    'Read Rowan saved configuration, then recommend two checks.',
    'For Rowan, retrieve state now and explain it.',
    'What did the old report suggest obtaining?',
])
def test_prospective_advice_does_not_erase_present_or_historical_request(prompt):
    from llm.gateway_routing import advisory_route
    assert advisory_route(prompt,None,{'devices':[]}) is None


def test_source_prohibition_cannot_trigger_old_investigation_scope():
    from llm.orchestration.investigation import contextual_route,is_investigation
    from llm.orchestration.memory import InvestigationMemory
    from llm.gateway_references import resolve_read,read_intent_text
    inventory={'devices':[{'id':1,'hostname':'Rowan','interfaces':[]}]}
    memory=InvestigationMemory(goal='Investigate Rowan.',domains=['inventory','state','topology'],device_refs=['1'])
    prompt='For that same device, read its saved configuration. Do not read other sources.'
    previous={'context_coverage':{'retrieval':{'device_refs':['1'],'domains':['inventory'],
        'entities':[{'device_id':'1','interface_id':'11'},{'device_id':'1','interface_id':'12'}],
        'attributes':['interfaces'],'source_requests':{}}}}
    assert not is_investigation(prompt)
    assert contextual_route(prompt,memory,previous,inventory) is None
    resolved=resolve_read(read_intent_text(prompt),previous,inventory)
    assert resolved['device_refs']==['1'] and resolved['domains']==['configuration']
    assert not resolved['attributes']
    previous['context_coverage']['retrieval']['entities'].append({'device_id':'2','interface_id':'21'})
    assert 'question' in resolve_read(read_intent_text(prompt),previous,inventory)
    assert is_investigation('Check other sources for that investigation.')
    assert contextual_route('Check other sources for that investigation.',memory,previous,inventory).use_history


def test_event_and_record_timestamp_stay_distinct_in_safe_projection():
    from llm.gateway_findings import network_answer
    context=[{'tool':'network.syslog','status':'success','evidence_ids':['log'],'data':{'records':[
        {'hostname':'Rowan','kind':'syslog_event','timestamp':'2026-10-26T08:06:00Z',
         'event_time':'2026-10-26T08:05:00Z','message':'A recorded transition','current':False}]}}]
    answer=network_answer(context,[Evidence(id='log',source='Event reader',origin='simulated')])
    assert 'event recorded `2026-10-26T08:05:00Z`' in answer
    assert 'Record timestamp `2026-10-26T08:06:00Z`' in answer


@pytest.mark.parametrize('extra,prohibit,expected',[(True,True,['configuration']),(False,True,['configuration']),(True,False,['configuration','state'])])
def test_latest_exclusive_owned_read_cannot_be_widened_by_model(extra,prohibit,expected,monkeypatch):
    from unittest.mock import patch
    from llm.gateway_routing import select_context,SemanticRoute
    monkeypatch.setenv('COGNISHIELD_AI_PLANNING','1')
    inventory={'devices':[{'id':1,'hostname':'Rowan','management_ip':'192.0.2.1','interfaces':[]}]}
    previous={'context_coverage':{'retrieval':{'domains':['inventory'],'device_refs':['1'],
        'entities':[{'device_id':'1','interface_id':'11'},{'device_id':'1','interface_id':'12'}]}}}
    proposal=SemanticRoute(intent='explain',network_domains=['configuration','state'] if extra else ['configuration'])
    prompt='For that same device, read its saved configuration and explain its protocol identifiers.'
    if prohibit:prompt+=' Do not read other sources.'
    with patch('llm.orchestration.planning.propose',AsyncMock(return_value=proposal)):
        result=asyncio.run(select_context(prompt,None,'floating',None,[],[],previous,inventory))
    assert result.network_domains==expected and result.device_refs==['1']
