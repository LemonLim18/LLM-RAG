"""Reviewed variant contracts and immutable native-release compatibility."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm.gateway_playbooks import validate_variant, render_template
from llm.gateway_knowledge import release_assessment


class VariantTests(unittest.TestCase):
    def variant(self):
        return dict(id='test_vlan',operation_id='create_vlan',operation_version=1,vendor='cisco',platform='iosxe',versions=['17.9'],
            module_fqcns=['cisco.ios.ios_vlans'],connection_plugin='ansible.netcommon.network_cli',platform_plugin='cisco.ios.ios',
            dependencies={'cisco.ios':'9.0.0','ansible.netcommon':'8.0.0'},fixture_parameters={'vlan_id':100},
            template='- hosts: {{ target_host }}\n  gather_facts: false\n  vars:\n    ansible_connection: ansible.netcommon.network_cli\n    ansible_network_os: cisco.ios.ios\n  tasks:\n    - name: Reviewed VLAN\n      cisco.ios.ios_vlans:\n        config:\n          - vlan_id: {{ vlan_id }}\n        state: merged\n',
            fixture_host='validation_target',expected_fixture_yaml='review required',compatibility_evidence='Test fixture only; never published or used for device execution.')

    def test_fixture_targets_modules_plugins_and_pins(self):
        variant=validate_variant(self.variant(),[{'operation_id':'create_vlan','version':1}])
        rendered=render_template(variant,{'vlan_id':100},'validation_target','vlan 100')
        self.assertIn('vlan_id: 100',rendered)
        for update in [{'dependencies':{'cisco.ios':'latest'}},{'module_fqcns':['community.network.ce_vlan']},{'operation_version':2},{'template':'{% include "evil" %}'}]:
            with self.assertRaises(ValueError): validate_variant(self.variant()|update,[{'operation_id':'create_vlan','version':1}])
        with self.assertRaises(ValueError): render_template(variant.model_copy(update={'template':variant.template.replace('cisco.ios.ios_vlans:','ansible.builtin.shell:')}),{'vlan_id':100},'validation_target','')
        with self.assertRaises(ValueError): render_template(variant.model_copy(update={'template':variant.template.replace('gather_facts: false','gather_facts: true')}),{'vlan_id':100},'validation_target','')

    def test_ordinary_coverage_keeps_native_and_optional_outputs_independent(self):
        root=Path(__file__).resolve().parents[1]/'knowledge_workspace/storage/catalog_releases'
        before=(root/'active.json').read_bytes()
        report=release_assessment(root)
        self.assertEqual(report['status'],'success')
        self.assertEqual(report['operation_count'],44);self.assertEqual(report['binding_count'],78)
        self.assertEqual(len(report['coverage']),132)
        self.assertTrue(any(row['native_status']=='supported' for row in report['coverage']))
        self.assertTrue(all(row['playbook_status']=='unsupported' for row in report['coverage']))
        self.assertEqual((root/'active.json').read_bytes(),before)


if __name__=='__main__': unittest.main()
