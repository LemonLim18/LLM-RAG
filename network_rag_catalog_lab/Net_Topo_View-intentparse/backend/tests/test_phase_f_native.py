"""Independent command-layout oracles for the reproduced Phase F defects.

The expected commands below are authored independently of template output.
These checks establish statement boundaries and requested values, not device
certification. They exercise the same sandbox/whitespace settings as V9 preview.
"""
import json
import sys
from pathlib import Path

import pytest
from jinja2 import StrictUndefined
from jinja2.sandbox import SandboxedEnvironment

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from scripts.phase_e_methods import template


def render(operation, vendor, parameters):
    rows = json.loads((ROOT / 'backend/ansible/reference/operation_drafts/index.json').read_text())['templates']
    row = next(r for r in rows if r['operation_id'] == operation and r['vendor'] == vendor)
    source = template(ROOT, row)
    return SandboxedEnvironment(undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True).from_string(source).render(**parameters).strip()


@pytest.mark.parametrize('vendor,prefix,interface,command', [
    ('cisco', 'router ospf 17', 'GigabitEthernet1/0/', 'ip ospf 17 area'),
    ('huawei', 'ospf 17', 'GigabitEthernet0/0/', 'ospf enable 17 area'),
])
@pytest.mark.parametrize('router_id', [None, '198.51.100.17'])
@pytest.mark.parametrize('count', [1, 2])
def test_ospf_each_command_is_a_separate_statement(vendor, prefix, interface, command, router_id, count):
    interfaces = [{'name': interface + str(i), 'area': str(i)} for i in range(count)]
    parameters = {'process_id': 17, 'interfaces': interfaces}
    if router_id is not None:
        parameters['router_id'] = router_id
    expected = [prefix]
    if router_id is not None:
        expected.append('router-id ' + router_id)
    for item in interfaces:
        expected.extend(['interface ' + item['name'], command + ' ' + item['area']])
    actual = render('configure_ospf', vendor, parameters)
    assert [line.strip() for line in actual.splitlines() if line.strip()] == expected
    assert 'None' not in actual and '{{' not in actual
    assert render('configure_ospf', vendor, parameters | {'router_id': router_id}) == actual


@pytest.mark.parametrize('operation', ['add_acl_rule', 'modify_acl_rule'])
@pytest.mark.parametrize('log', [False, True])
@pytest.mark.parametrize('ports', [{}, {'source_port': 12345, 'destination_port': 443}])
def test_huawei_acl_terminators_and_logging_belong_to_correct_statements(operation, log, ports):
    values = dict(acl_name='CAMPUS', acl_rule_id=7, acl_action='permit', ip_protocol='tcp',
                  source_address='198.51.100.0', source_wildcard='0.0.0.255',
                  acl_destination_address='203.0.113.0', acl_destination_wildcard='0.0.0.255', log=log)
    values.update(ports)
    rule = 'rule 7 permit tcp source 198.51.100.0 0.0.0.255 destination 203.0.113.0 0.0.0.255'
    if ports:
        rule += ' source-port eq 12345 destination-port eq 443'
    if log:
        rule += ' logging'
    expected = ['acl name CAMPUS advance', rule, 'quit']
    if operation == 'modify_acl_rule':
        expected = ['acl name CAMPUS advance', 'undo rule 7', 'quit'] + expected
    actual = render(operation, 'huawei', values)
    assert [line.strip() for line in actual.splitlines() if line.strip()] == expected
    assert 'quit' not in rule and 'None' not in actual


def test_junos_ospf_neighbor_branch_keeps_interface_and_router_id_separate():
    actual = render('configure_ospf', 'juniper', {'router_id': '198.51.100.17',
        'interfaces': [{'name': 'ge-0/0/1.0', 'area': '0'}, {'name': 'ge-0/0/2.0', 'area': '1'}]})
    assert actual.splitlines() == ['set protocols ospf area 0 interface ge-0/0/1.0',
        'set protocols ospf area 1 interface ge-0/0/2.0', 'set routing-options router-id 198.51.100.17']


def test_ospf_missing_process_or_interface_area_never_silently_renders():
    from jinja2.exceptions import UndefinedError
    for vendor in ['cisco', 'huawei']:
        for parameters in [{'interfaces': [{'name': 'Ethernet1', 'area': '0'}]},
                           {'process_id': 17, 'interfaces': [{'name': 'Ethernet1'}]}]:
            with pytest.raises(UndefinedError):
                render('configure_ospf', vendor, parameters)
