"""Neighbor cases for factual scope and editor metadata; no model score."""
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm.orchestration.synthesis import forwarding_claim_errors,check_candidate

FLOW={'source_device':'Fir-Edge','destination_device':'Elm-Edge',
    'forward':{'status':'delivered','branches':[{'reason':'destination reached','path':['Fir-Edge','Birch-Core','Elm-Edge']}]},
    'return':{'status':'delivered','branches':[{'reason':'destination reached','path':['Elm-Edge','Birch-Core','Fir-Edge']}]}}

def test_role_list_cannot_label_endpoints_as_intermediate_devices():
    assert forwarding_claim_errors('The following intermediate devices are traversed: Fir-Edge, Birch-Core, and Elm-Edge.',[FLOW])
    assert not forwarding_claim_errors('The endpoints are Fir-Edge and Elm-Edge; the intermediate device is Birch-Core.',[FLOW])

def test_hello_mismatch_does_not_establish_different_areas_or_network_types():
    context=[{'tool':'network.state','status':'success','data':{'records':[{
        'kind':'protocol_assessment','protocol':'OSPF','observed_state':'Down',
        'peer_parameters':[{'hostname':'Fir-Edge','area':'0.0.0.0','network_type':'point_to_point','hello_seconds':10},
                           {'hostname':'Birch-Core','area':'0.0.0.0','network_type':'point_to_point','hello_seconds':20}]}]}}]
    errors=check_candidate('The hello mismatch indicates that the two routers are not in the same OSPF area or have different network types.',context,[],{},'Explain these observations.')
    assert any('area' in error for error in errors) and any('network type' in error for error in errors)

def test_single_changed_interface_command_cannot_become_plural_device_state():
    context=[{'tool':'network.configuration','status':'success','data':{'records':[
        {'kind':'running_configuration','hostname':'Fir-Edge','current':True,'config_text':'set system host-name Fir-Edge\nset interfaces ge-0/0/8 disable\n'},
        {'kind':'configuration_snapshot','hostname':'Fir-Edge','current':False,'config_text':'set system host-name Fir-Edge\n'}]}}]
    errors=check_candidate('The added line `set interfaces ge-0/0/8 disable` indicates that the interfaces on the Fir-Edge device were disabled.',context,[],{},'Compare saved and current configuration.')
    assert any('single interface' in error for error in errors)

@pytest.mark.parametrize('answer',[
    'The unsaved routing buffer is frozen, indicating that it is not editable or modifiable.',
    'The buffer is read-only and cannot be modified.',
])
def test_editor_access_is_metadata_not_an_author_marker(answer):
    from llm.orchestration.studio import verify_editor_router_ids
    text='router ospf 27\n router-id 192.0.2.27\nrouter bgp 65027\n neighbor 192.0.2.28 remote-as 65028\n! FROZEN_NOTE\n'
    corrected,changed=verify_editor_router_ids(answer,[{'source':'draft.cfg','text':text,'read_only':False,'unsaved':True}],
        'draft.cfg',question='Explain this buffer including AS roles and its marker.')
    assert changed and 'not editable' not in corrected and '65027' in corrected and '65028' in corrected

def test_as_role_request_cannot_omit_the_actual_values():
    from llm.orchestration.studio import verify_editor_router_ids
    text='router bgp 65027\n neighbor 192.0.2.28 remote-as 65028\n'
    _,changed=verify_editor_router_ids('The file contains a BGP section.',[{'source':'draft.cfg','text':text}],
        'draft.cfg',question='Explain the AS roles in this buffer.')
    assert changed

def test_missing_policy_evidence_cannot_support_a_definitive_negative_cause():
    context=[{'tool':'network.state','status':'success','data':{'records':[
        {'kind':'protocol_assessment','protocol':'BGP','observed_state':'Established','peer_parameters':[]} ]}}]
    errors=check_candidate('The ingress policy does not explain the modeled drop; it is not present in the provided evidence.',
        context,[],{},'Can an ingress policy explain this modeled drop?')
    assert any('policy' in error for error in errors)

def test_quoted_as_values_do_not_verify_an_omitted_or_wrong_prose_explanation():
    from llm.orchestration.studio import verify_editor_router_ids
    text='router bgp 65027\n neighbor 192.0.2.28 remote-as 65028\n'
    wrong='AS Role: OSPF.\n```ios\n'+text+'```\nThe BGP router ID is not specified but is inferred to be 65027.'
    corrected,changed=verify_editor_router_ids(wrong,[{'source':'draft.cfg','text':text}],
        'draft.cfg',question='Explain the AS roles and router ID.')
    assert changed and 'inferred to be 65027' not in corrected and 'AS Role: OSPF' not in corrected
    good='BGP uses local AS65027 and remote AS65028 for neighbor192.0.2.28. No effective BGP router ID is established by this text.'
    assert not verify_editor_router_ids(good,[{'source':'draft.cfg','text':text}],'draft.cfg',question='Explain the AS roles.')[1]


def test_matching_captures_do_not_prove_continuity_when_user_asks_for_drift():
    context=[{'tool':'network.configuration','status':'success','data':{'records':[
        {'id':'current','kind':'running_configuration','hostname':'Cedar','current':True,
         'timestamp':'2026-10-23T01:00:00Z','config_text':'hostname Cedar\n'},
        {'id':'saved','kind':'configuration_snapshot','hostname':'Cedar','current':False,
         'timestamp':'2026-10-23T00:59:50Z','config_text':'hostname Cedar\n'}]}}]
    wrong='The configuration has not changed since then and is stable. There is no need for further configuration changes.'
    assert check_candidate(wrong,context,[],{},'Retrieve the recorded drift comparison for Cedar.')
    qualified='The two recorded configurations match. This does not establish an unchanged interval or whether further configuration changes are needed.'
    assert not check_candidate(qualified,context,[],{},'Retrieve the recorded drift comparison for Cedar.')


def test_aggregate_interface_health_cannot_override_a_current_down_record():
    rows=[{'kind':'interface_state','hostname':'Cedar','interface':'ge-0/0/0.0',
        'admin_status':'up','oper_status':'up','current':True,'freshness':'fresh'},
        {'kind':'interface_state','hostname':'Cedar','interface':'ge-0/0/1.0',
        'admin_status':'down','oper_status':'down','current':True,'freshness':'fresh'}]
    context=[{'tool':'network.state','status':'success','data':{'records':rows}}]
    bad='The Cedar device has interfaces ge-0/0/0.0 and ge-0/0/1.0, which are up and running. The device is observed to be healthy within the tested scope.'
    question='Describe Cedar registered interfaces and observed state.'
    assert check_candidate(bad,context,[],{},question)
    good='Cedar ge-0/0/0.0 is administratively and operationally up; ge-0/0/1.0 is administratively and operationally down. This does not establish all interfaces are healthy.'
    assert not check_candidate(good,context,[],{},question)


def test_historical_down_record_does_not_contradict_newer_current_up_record():
    rows=[{'kind':'interface_state','hostname':'Cedar','interface':'ge-0/0/0.0',
        'admin_status':'down','oper_status':'down','current':False,'freshness':'stale'},
        {'kind':'interface_state','hostname':'Cedar','interface':'ge-0/0/0.0',
        'admin_status':'up','oper_status':'up','current':True,'freshness':'fresh'}]
    context=[{'tool':'network.state','status':'success','data':{'records':rows}}]
    assert not check_candidate('The recorded current Cedar interface is up.',context,[],{},'Describe the current interface observation.')


def test_single_requested_protocol_cannot_borrow_another_protocol_established_state():
    context=[{'tool':'network.state','status':'success','data':{'records':[
        {'kind':'protocol_assessment','protocol':'OSPF','observed_state':'Down'},
        {'kind':'protocol_assessment','protocol':'BGP','observed_state':'Established'}]}}]
    assert check_candidate('The neighbor relationship is established.',context,[],{},'Explain the OSPF peer observations.')
    assert not check_candidate('OSPF is Down. BGP is Established; its state does not establish OSPF health.',context,[],{},'Explain the OSPF peer observations.')


def test_interface_list_cannot_assign_one_members_down_state_to_its_up_neighbor():
    context=[{'tool':'network.state','status':'success','data':{'records':[
        {'kind':'interface_state','hostname':'Cedar','interface':'ge-0/0/0.0','current':True,'admin_status':'up','oper_status':'up'},
        {'kind':'interface_state','hostname':'Cedar','interface':'ge-0/0/1.0','current':True,'admin_status':'down','oper_status':'down'}]}}]
    bad='The interfaces ge-0/0/0.0 and ge-0/0/1.0 are in the down state.'
    assert check_candidate(bad,context,[],{},'Describe Cedar interface observations.')
    good='The interface ge-0/0/0.0 is up. The interface ge-0/0/1.0 is down.'
    assert not check_candidate(good,context,[],{},'Describe Cedar interface observations.')
    good='The interface ge-0/0/0.0 is up, while the interface ge-0/0/1.0 is down.'
    assert not check_candidate(good,context,[],{},'Describe Cedar interface observations.')


def test_ospf_process_role_cannot_be_filled_by_an_autonomous_system_command():
    context=[{'tool':'network.configuration','status':'success','data':{'records':[
        {'hostname':'Cedar','config_text':'set routing-options autonomous-system 65000\nset protocols ospf area 0 interface ge-0/0/0.0\n'}]}}]
    assert check_candidate('The OSPF process is autonomous-system 65000.',context,[],{},'Explain the recorded settings.')


def test_multi_protocol_conflicts_and_unknown_prerequisites_remain_bound_to_their_records():
    from llm.orchestration.synthesis import projection
    rows=[{'kind':'forwarding_assessment','unrelated':True},
        {'kind':'protocol_assessment','protocol':'OSPF','observed_state':'Full','conflict':False,
         'unknown_prerequisites':['authentication','area_type']},
        {'kind':'protocol_assessment','protocol':'BGP','observed_state':'Established','conflict':True,
         'configuration_differences':['neighbor remote AS differs from peer local AS']}]
    context=[{'tool':'network.state','status':'success','data':{'records':rows}}]
    question='Explain the recorded protocol observations and compare the peer roles.'
    bad='The BGP session is established, but the OSPF session is conflicting due to a remote AS mismatch. There are no missing prerequisites or contradictory observations.'
    errors=check_candidate(bad,context,[],{},question)
    assert any('wrong protocol' in e for e in errors)
    assert any('unchecked prerequisites' in e for e in errors)
    assert any('contain a conflict' in e for e in errors)
    assert check_candidate('The OSPF protocol is configured with local AS65020 and remote AS65030.',context,[],{},question)
    assert check_candidate('The OSPF protocol is configured with local AS65020 and remote AS65030, and the BGP protocol uses local AS65030.',context,[],{},question)
    assert not check_candidate('OSPF does not use a local AS. BGP has a conflict, and OSPF prerequisites remain unverified.',context,[],{},question)
    good='OSPF is Full, with authentication and area type unverified. BGP is Established but its observed state conflicts with its configured AS mismatch; the cause remains unconfirmed.'
    assert not check_candidate(good,context,[],{},question)
    visible=projection(context,[],{},question)['records'][0]['data']['records']
    assert {r['protocol'] for r in visible}=={'OSPF','BGP'} and len(visible)==2
    assert len(rows)==3  # Source disclosure is intact.
