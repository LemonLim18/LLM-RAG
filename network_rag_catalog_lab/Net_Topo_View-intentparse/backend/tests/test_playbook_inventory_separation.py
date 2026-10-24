"""Generated playbook target selectors are distinct from inventory credentials."""
from pathlib import Path
from types import SimpleNamespace
import sys
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm.gateway_playbooks import render_template

TEMPLATE='''- hosts: {{ target_host }}
  gather_facts: false
  vars:
    ansible_connection: ansible.netcommon.network_cli
    ansible_network_os: cisco.ios.ios
  tasks:
    - name: Reviewed BGP neighbor
      cisco.ios.ios_config:
        parents: router bgp {{ local_as }}
        lines:
          - neighbor {{ peer }} remote-as {{ remote_as }}
'''

def render(template=TEMPLATE,host='Edge-A'):
    variant=SimpleNamespace(template=template,connection_plugin='ansible.netcommon.network_cli',
        platform_plugin='cisco.ios.ios',module_fqcns=['cisco.ios.ios_config'])
    return render_template(variant,{'local_as':65010,'peer':'192.0.2.21','remote_as':65021},host,'')

def test_resolved_target_selector_and_configuration_parameters_need_no_credentials():
    output=render()
    assert 'hosts: Edge-A' in output and 'router bgp 65010' in output
    assert 'neighbor 192.0.2.21 remote-as 65021' in output
    assert 'vars_files' not in output and 'ansible_password' not in output

@pytest.mark.parametrize('key',['ansible_user','ansible_password','ansible_ssh_pass','ansible_become_password','ansible_ssh_private_key_file'])
def test_generated_connection_credentials_stay_in_managed_inventory(key):
    with pytest.raises(ValueError,match='managed inventory'):
        render(TEMPLATE.replace('    ansible_network_os:',f'    {key}: DO_NOT_EMIT_TEST_VALUE\n    ansible_network_os:'))

def test_missing_target_selector_is_not_a_genuine_playbook():
    with pytest.raises(ValueError,match='resolved inventory hostname'):
        render(TEMPLATE.replace('  hosts:', '  omitted:').replace('- hosts:', '- omitted:'))
