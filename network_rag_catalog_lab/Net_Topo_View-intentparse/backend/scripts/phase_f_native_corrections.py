"""Scoped Phase F authoring via the existing API; never publishes/activates.

Independent statement-layout fixtures accompany four reproduced source fixes.
Use --apply only for authorized ordinary authoring. Publication remains the
existing authenticated GUI action. No ordinary device/inventory writes occur.
"""
import argparse
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
import httpx
from auth.auth import create_access_token
from scripts.phase_e_methods import template

SCOPE = [('configure_ospf', 'cisco'), ('configure_ospf', 'huawei'),
         ('add_acl_rule', 'huawei'), ('modify_acl_rule', 'huawei')]


def independent_fixtures(operation, vendor):
    """Expected statements from the requested operation, never rendered text."""
    fixtures = []
    if operation == 'configure_ospf':
        interface = {'cisco': 'GigabitEthernet1/0/', 'huawei': 'GigabitEthernet0/0/'}[vendor]
        header = 'router ospf 17' if vendor == 'cisco' else 'ospf 17'
        for router_id, count in [('198.51.100.17', 2), ('198.51.100.17', 1), ('absent', 1)]:
            parameters = {'process_id': 17, 'interfaces': [{'name': interface + str(i), 'area': str(i)} for i in range(count)]}
            lines = [header]
            if router_id != 'absent':
                parameters['router_id'] = router_id
            if router_id and router_id != 'absent':
                lines.append(' router-id ' + router_id)
            for i in range(count):
                if vendor == 'cisco':
                    lines.extend([' interface ' + interface + str(i), '  ip ospf 17 area ' + str(i)])
                else:
                    lines.extend(['interface ' + interface + str(i), ' ospf enable 17 area ' + str(i)])
            fixtures.append({'parameters': parameters, 'expected_output': '\n'.join(lines)})
    else:
        base = {'acl_name': 'CAMPUS', 'acl_rule_id': 17, 'acl_action': 'permit', 'ip_protocol': 'tcp',
                'source_prefix': '198.51.100.0/24', 'destination_prefix': '203.0.113.0/24'}
        for ports, logging in [('both', True), ('absent', False), ('destination', False)]:
            parameters = base | {'log': logging}
            rule = ' rule 17 permit tcp source 198.51.100.0 0.0.0.255 destination 203.0.113.0 0.0.0.255'
            if ports == 'both':
                parameters.update(source_port=12345, destination_port=443)
                rule += ' source-port eq 12345 destination-port eq 443'
            elif ports == 'destination':
                parameters['destination_port'] = 443
                rule += ' destination-port eq 443'
            if logging:
                rule += ' logging'
            lines = ['acl name CAMPUS advance', rule, 'quit']
            if operation == 'modify_acl_rule':
                lines = ['acl name CAMPUS advance', ' undo rule 17', 'quit'] + lines
            fixtures.append({'parameters': parameters, 'expected_output': '\n'.join(lines)})
    return fixtures


async def execute(args):
    destination = ROOT / 'tmp/phase-f/iterations' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-native-authoring')
    destination.mkdir(parents=True)
    report = {'apply': args.apply, 'started_at': datetime.now(timezone.utc).isoformat(), 'calls': [], 'status': 'RUNNING'}
    def save():
        (destination / 'result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    token = create_access_token(1, 'codex-phase-f-authoring', 'engineer')
    try:
        async with httpx.AsyncClient(base_url=args.url, headers={'Authorization': 'Bearer ' + token}, timeout=300) as client:
            async def call(method, path, body=None, expected=200):
                response = await client.request(method, '/api/v1/knowledge' + path, json=body)
                report['calls'].append({'method': method, 'path': path, 'status': response.status_code})
                save()
                assert response.status_code == expected, (path, response.status_code, response.text[:4000])
                return response.json()
            original = await call('GET', '')
            report['active_before'] = original['data']['active_release']['release_id']
            rows = json.loads((ROOT / 'backend/ansible/reference/operation_drafts/index.json').read_text())['templates']
            review = (await call('GET', '/reviews'))['data']['rows']
            prepared = []
            for operation, vendor in SCOPE:
                row = next(r for r in rows if (r['operation_id'], r['vendor']) == (operation, vendor))
                binding = next(b for b in original['data']['catalogs']['template_bindings'] if (b['operation_id'], b['vendor']) == (operation, vendor))
                content = template(ROOT, row)
                fixtures = independent_fixtures(operation, vendor)
                for fixture in fixtures:
                    output = await call('POST', '/render', {'expected_revision': original['revision'], 'path': binding['template_path'], 'content': content, 'parameters': fixture['parameters']})
                    assert output['data']['configuration'].strip() == fixture['expected_output'].strip(), (operation, vendor, output, fixture)
                invalids = [{}, fixtures[0]['parameters'] | {'unknown_input': True},
                            fixtures[0]['parameters'] | ({'router_id': None} if operation == 'configure_ospf' else {'source_port': None})]
                for invalid in invalids:
                    await call('POST', '/render', {'expected_revision': original['revision'], 'path': binding['template_path'], 'content': content, 'parameters': invalid}, 422)
                method = deepcopy(next(r['method'] for r in review if (r['binding']['operation_id'], r['binding']['vendor']) == (operation, vendor)))
                method['fixtures'] = fixtures
                method['limitations'] = [line for line in method['limitations'] if not line.startswith('Golden output is a generated review proposal')]
                method['limitations'].append('Independent Phase F command-boundary fixtures; no device or universal vendor certification is implied.')
                method['invalid_inputs'] = invalids
                prepared.append((binding, content, method))
            report['preflight'] = 'PASS: 12 independent exact previews and 12 negative requests (including explicit null rejected by the published schema)'
            report['prepared'] = [{'operation': b['operation_id'], 'vendor': b['vendor'], 'template_sha256': sha256(c.encode()).hexdigest(), 'fixtures': m['fixtures']} for b, c, m in prepared]
            if args.apply:
                for binding, content, method in prepared:
                    state = await call('GET', '')
                    if state['data']['templates'][binding['template_path']] != content:
                        await call('PUT', '/template', {'expected_revision': state['revision'], 'reason': 'Phase F: preserve separate OSPF/ACL statements and scope ACL logging to rule creation', 'path': binding['template_path'], 'content': content})
                    state = await call('GET', '')
                    identity = next(r['identity'] for r in review if r['binding']['template_path'] == binding['template_path'])
                    await call('PUT', '/review-method', {'expected_revision': state['revision'], 'identity': identity, 'method': method, 'reason': 'Phase F independent newline, multi-interface, absent/null and ACL logging fixtures'})
                await call('POST', '/validate')
            final = await call('GET', '')
            assert final['data']['active_release']['release_id'] == report['active_before']
            report.update(status='PASS', active_unchanged=True, publication_performed=False, final_revision=final['revision'])
    except BaseException as error:
        report.update(status='FAIL', error=repr(error))
        raise
    finally:
        save()
        print(json.dumps({'artifact': str(destination), 'status': report['status'], 'applied': args.apply}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8000')
    parser.add_argument('--apply', action='store_true')
    asyncio.run(execute(parser.parse_args()))
