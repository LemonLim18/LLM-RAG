"""Reader scope follows calculated relationships, not only the record owner."""
import asyncio
from copy import deepcopy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(1, str(Path(__file__).resolve().parent))
from development.starter import starter_bundle
from llm.tools import ToolAuthorization
from test_phase_g_source_contracts import source_runtime


@pytest.mark.parametrize('surface', ['floating', 'studio'])
@pytest.mark.parametrize('failure', ['healthy', 'egress_down', 'ingress_down', 'no_route'])
def test_single_transit_and_endpoints_retrieve_related_flow(source_runtime, surface, failure):
    _, manager, registry = source_runtime
    bundle = starter_bundle()
    interfaces = bundle['sources']['inventory']['data']['interfaces']
    model = bundle['sources']['simulation']['data']['network']
    if failure.endswith('_down'):
        interface = next(i for i in interfaces if i['id'] == (3 if failure == 'egress_down' else 2))
        interface.update(admin_status='down', oper_status='down')
    elif failure == 'no_route':
        next(t for t in model['tables'] if t['device_id'] == 1200)['routes'] = []
    # A local endpoint flow shares the same source record owner but never
    # traverses the transit device or the remote endpoint.
    local = deepcopy(model['flows'][0])
    local.update(id='local-only', destination_device_id=1100, destination_address=local['source_address'])
    model['flows'].append(local)
    draft = manager.save_draft(bundle, owner='scope-owner', expected=None)
    receipt = manager.validate_draft(draft['draft_id'], owner='scope-owner', expected=1)
    manager.activate_draft(draft['draft_id'], owner='scope-owner', expected=1,
        expected_active=manager.snapshot()[1]['source_revision'], validation_hash=receipt['validation_hash'])
    auth = ToolAuthorization('scope-owner', 'engineer', surface, 'scope-' + surface,
        frozenset({'network.state'}))
    for name in ['LAB-R1', 'LAB-R2', 'LAB-R3']:
        result = asyncio.run(registry.invoke('network.state',
            {'device_refs': [name], 'source_categories': ['simulation']}, auth))
        assert result.status == 'success' and all(e.origin == 'simulated' for e in result.evidence)
        flows = {r['flow']['id']: r for r in result.data['records'] if r['kind'] == 'forwarding_assessment'}
        assert 'branch-edge-icmp' in flows
        assert ('local-only' in flows) == (name == 'LAB-R1')
        assert flows['branch-edge-icmp']['scope_device_refs'] == [1100, 1200, 1300]
        assert flows['branch-edge-icmp']['assessment']['forward']['status'] == ('delivered' if failure == 'healthy' else 'failed')


def test_unknown_or_unreached_transit_is_not_invented():
    from development.bundles import compile_bundle
    from development.network_model import NetworkModel, assess_flow
    bundle = starter_bundle()
    # Stop at the origin: the topology alone cannot establish that the transit
    # was traversed. The adapter should not fabricate that relationship.
    model = bundle['sources']['simulation']['data']['network']
    next(t for t in model['tables'] if t['device_id'] == 1100)['routes'] = []
    scenario = compile_bundle(bundle)
    result = assess_flow(scenario, NetworkModel.model_validate(scenario['network']).flows[0])
    assert result['forward']['encountered_device_ids'] == [1100]
