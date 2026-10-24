"""Journey observer must reject wrong output/effects, not just HTTP success."""
from copy import deepcopy
import hashlib
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.evaluate_phase_g_native import interface_names,natural_request,verify_unsaved,scenario_for


def test_v9_model_transport_is_bounded_and_json_without_replacing_v9_authority():
    from local_providers.v9_worker import planning_model
    engine=planning_model('qwen2.5:1.5b','http://127.0.0.1:11434')
    assert engine.model=='qwen2.5:1.5b' and engine.format=='json'
    assert engine.num_predict==1024 and engine.num_ctx==8192
    assert engine.client_kwargs=={'timeout':45.0,'trust_env':False}


def test_model_observer_records_transport_and_bounded_output_without_semantic_credit():
    from local_providers.v9_worker import observed_invocation
    from types import SimpleNamespace
    counts={'succeeded':0,'failed':0}
    observed_invocation(counts,lambda:SimpleNamespace(content='x'*9000,usage_metadata={'output_tokens':20}))
    assert counts['succeeded']==1 and counts['observations'][0]['response_truncated']
    assert len(counts['observations'][0]['response'])==8000
    assert counts['observations'][0]['semantic_correctness']=='not_established_by_transport'
    def failure():raise TimeoutError('private transport message')
    with pytest.raises(TimeoutError):observed_invocation(counts,failure)
    assert counts['failed']==1 and counts['observations'][-1]['error_type']=='TimeoutError'
    assert 'private transport message' not in str(counts)


def test_interface_collection_does_not_turn_prefixes_or_labels_into_inventory():
    values={'interface':'ge-0/0/5.0','members':['GigabitEthernet1/0/5'],'address':'192.0.2.1/24','description':'Uplink','process_name':'CAMPUS'}
    assert interface_names(values)=={'ge-0/0/5.0','GigabitEthernet1/0/5'}


def test_natural_request_is_an_explicit_unsaved_native_request_with_real_parameters():
    prompt=natural_request({'display_name':'Set OSPF Router ID'},'LAB-R1',{'process_id':200,'router_id':'192.0.2.200'})
    assert all(s in prompt for s in ['native configuration','LAB-R1','Set OSPF Router ID','process id = 200','192.0.2.200','unsaved'])


def test_controlled_profile_uses_reviewed_facts_without_falsifying_software_compatibility():
    bundle,device=scenario_for({'vendor':'cisco','platform':'iosxe','versions':['17.9'],'operation_id':'set_ospf_router_id'}, {'process_id':200})
    assert device['engineering_facts']['model_family']=='catalyst9300'
    assert 'ospf_router_id_v1' in device['engineering_facts']['capabilities']['validated_policies']
    assert any(p['process_id']==200 for p in device['engineering_facts']['resources']['ospf_processes'])
    _,huawei=scenario_for({'vendor':'huawei','platform':'vrp','versions':['8'],'operation_id':'set_ospf_router_id'}, {'process_id':200})
    assert huawei['os_version']=='8'
    assert 'validated_policies' not in huawei['engineering_facts']['capabilities']


def test_controlled_resource_prerequisites_are_authored_without_changing_the_contract():
    binding={'vendor':'cisco','platform':'iosxe','versions':['17.9'],'operation_id':'assign_vlan_to_trunk_port'}
    _,device=scenario_for(binding,{'interface':'GigabitEthernet1/0/5','allowed_vlans':[240,241]})
    facts=device['engineering_facts']
    assert {240,241}<={v['vlan_id'] for v in facts['vlans']}
    port=next(i for i in facts['interfaces'] if i['name']=='GigabitEthernet1/0/5')
    assert port['switchport_mode']=='trunk' and port['ip_addresses']==[]
    assert facts['origin']=='planned' and device['os_version']=='17.9'
    assert 'no physical collection' in facts['resources']['source_ref']


def test_creation_targets_are_not_invented_as_existing_physical_resources():
    for operation,parameters,absent in [
        ('configure_loopback_interface',{'interface':'Loopback10','address':'10.25.0.1','prefix_length':24},'Loopback10'),
        ('configure_port_channel',{'aggregate_interface':'Port-channel10','member_interfaces':['GigabitEthernet1/0/5']},'Port-channel10')]:
        bundle,device=scenario_for({'vendor':'cisco','platform':'iosxe','versions':['17.9'],'operation_id':operation},parameters)
        assert absent not in {i['name'] for i in bundle['sources']['inventory']['data']['interfaces']}
        assert absent not in {i['name'] for i in device['engineering_facts']['interfaces']}


@pytest.mark.parametrize('wrong',['content','device','saved','execution','authority','digest'])
def test_native_journey_observer_rejects_wrong_source_effect_or_output(wrong):
    content='router ospf 200\n router-id 192.0.2.200\n exit'
    fixture={'expected_output':content};binding={'operation_id':'set_ospf_router_id'}
    doc={'device_id':'1100','path':'playbooks/drafts/01-LAB-R1-set_ospf_router_id-a.cfg','content':content,
         'digest':hashlib.sha256(content.encode()).hexdigest(),'saved':False,'execution_available':False,
         'validation':{'status':'passed','scope':'v9_operation','knowledge_release':'release','device_testing':'not_run','deployment_authorized':False}}
    result={'documents':[doc],'output_kind':'native'}
    assert verify_unsaved(result,binding,fixture,'LAB-R1',1100,'release')==doc
    bad=deepcopy(result);changed=bad['documents'][0]
    if wrong=='content':changed['content']='router ospf 201'
    elif wrong=='device':changed['device_id']='1200'
    elif wrong=='saved':changed['saved']=True
    elif wrong=='execution':changed['execution_available']=True
    elif wrong=='authority':changed['validation']['knowledge_release']='other'
    else:changed['digest']='0'*64
    with pytest.raises(AssertionError):verify_unsaved(bad,binding,fixture,'LAB-R1',1100,'release')
