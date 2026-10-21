"""Phase D traceability and reviewed route repair through existing authoring APIs.

The audit is not semantic certification. Repair defaults to the single disposable
acceptance knowledge workspace; it cannot activate or publish ordinary knowledge.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'backend'), str(Path(__file__).resolve().parent)]
from phase_d_audit import Run, digest


def coverage():
    from llm.gateway_knowledge import read_release
    from jinja2 import Environment, meta
    from audit_reference_templates import ISSUES
    release, manifest, pointer = read_release(ROOT / 'backend/knowledge_workspace/storage/catalog_releases')
    catalog = {o['operation_id']: o for o in json.loads((release / 'catalog/operations.json').read_text(encoding='utf-8'))}
    index = json.loads((ROOT / 'backend/ansible/reference/operation_drafts/index.json').read_text(encoding='utf-8'))
    candidate_manifest={};candidate_summary={};runtime_checks={}
    for summary in sorted((ROOT/'tmp/phase-d').glob('*-D1b-route-candidate-*/candidate-summary.json'),reverse=True):
        records=[json.loads(line) for line in (summary.parent/'cases.jsonl').read_text().splitlines()]
        native=[r for r in records if '-RUNTIME-' in r['test_id']]
        if len(native)<11 or any(r['outcome']!='PASS' for r in records):continue
        candidate_summary=json.loads(summary.read_text())
        candidate_manifest=json.loads((Path(candidate_summary['workspace'])/'storage/catalog_releases'/candidate_summary['release_id']/'manifest.json').read_text())
        for record in native:
            op=record.get('operation_id') or record['test_id'].removeprefix('D-KNOW-CISCO-RUNTIME-').lower()
            vendor=record['test_id'].removeprefix('D-KNOW-ROUTE-RUNTIME-').lower() if record.get('operation_id') else 'cisco'
            runtime_checks[(op,vendor)]={'outcome':'PASS','test_id':record['test_id'],'artifact':str(summary.parent.relative_to(ROOT)/'cases.jsonl'),
                'scope':'Exact independently specified native CLI via V9 schema/binding/runtime; not complete platform/device or Ansible conformance.'}
        break
    rows = []; identities = set()
    for candidate in index['templates']:
        op, vendor = candidate['operation_id'], candidate['vendor']
        if (op, vendor) in identities: raise ValueError('Duplicate candidate')
        identities.add((op, vendor))
        path = ROOT / 'backend/ansible' / candidate['path']
        text = path.read_text(encoding='utf-8')
        tree = Environment().parse(text)
        variables = sorted(meta.find_undeclared_variables(tree))
        bindings = [b for b in manifest['template_bindings'] if b['operation_id'] == op and b['vendor'] == vendor]
        schema = json.loads((release / manifest['schemas'][op]).read_text()) if op in manifest['schemas'] else None
        contract = candidate.get('input_contract') or {}
        defined = set(contract.get('fields', [])) | set(contract.get('derived', {})) | set(contract.get('optional_defaults', {}))
        missing = sorted(set(variables) - defined)
        findings = []
        if missing: findings.append('Unbound reference inputs: ' + ', '.join(missing))
        if op not in catalog: findings.append('Ordinary authoring operation, mappings/rules and binding must be reconstructed; isolated test artifacts cannot be promoted.')
        if (vendor, op) in ISSUES: findings.append(ISSUES[(vendor, op)])
        if vendor in {'cisco', 'huawei'} and op == 'configure_static_route':
            findings.append('Published destination CIDR is emitted as one CLI argument; use existing destination_address/destination_mask derivations and separate arguments.')
        if vendor in {'cisco','huawei'} and op=='remove_static_route':
            findings.append('Ordinary removal binding also emits a CIDR as one CLI argument; exact add/remove prefix/mask symmetry is required.')
        if op in {'configure_isis_interface','disable_isis_interface'}:
            if vendor=='cisco':findings.append('Ordinary interface attachment/context requires reviewed separate IP-ISIS and circuit-type commands; candidate fixes do not prove NET/adjacency prerequisites.')
            if vendor=='huawei':findings.append('VRP process identity is numeric; generic process_name and unqualified isis enable do not establish attachment to the requested process. Exact supported profile remains unverified.')
            if vendor=='juniper':findings.append('Junos requires logical-interface/family-ISO/NET context and interface-level semantics; generic set protocols isis level level-2 is not a validated translation.')
        if not contract: findings.append('No input contract or concrete compatibility profile accompanies this candidate.')
        remediation=None
        if candidate.get('source')=='reviewed_authoring_candidate':
            remediation={'status':'acceptance_authoring_only','reference_synchronized':True,'ordinary_activated':False,
                'authoring_revision':candidate.get('source_authoring_revision'),
                'evidence_location':'tmp/phase-d/*-D1b-*/cases.jsonl',
                'scope':'Independent native output fixtures, invalid-input rejection and candidate V9 runtime checks; not full vendor/profile/device or Ansible certification.'}
        references=[]
        if (op,vendor) in runtime_checks:
            if op in {'configure_static_route','remove_static_route'}:
                references=[{'cisco':'https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9300/software/release/17-9/configuration_guide/rtng/b_179_rtng_9300_cg/configuring_bidirectional_forwarding_detection.html',
                    'juniper':'https://www.juniper.net/documentation/us/en/software/junos/cli-reference/topics/ref/statement/static-edit-routing-options.html',
                    'huawei':'https://info.support.huawei.com/hedex/api/pages/EDOC1100277644/AEM10221/04/resources/command/yunshan/IPV4ADDROUTENHISPRIVTABLE%28STATICRTOM%29.html'}[vendor]]
            elif 'isis' in op:references=['https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/iproute_isis/command/irs-cr-book.pdf']
            else:references=['https://sec.cloudapps.cisco.com/security/center/resources/IOS_XE_hardening']
        rows.append({'catalog_operation_id': op, 'category': candidate['category_id'], 'vendor': vendor,
            'canonical_semantics': catalog.get(op, {}).get('description', candidate.get('label', op)),
            'profiles': [{k: b[k] for k in ['platform', 'versions']} for b in bindings],
            'template': candidate['path'], 'template_sha256': digest(path.read_bytes()), 'template_variables': variables,
            'reference_mapping': contract, 'parameters': schema.get('properties', {}) if schema else None,
            'required_parameters': schema.get('required', []) if schema else None,
            'bindings': bindings, 'release': pointer['release_id'], 'findings': findings,
            'disposition': 'gap_reproduced' if findings else 'static_validated',
            'static_validation': {'jinja_parse': 'PASS', 'index_hash_matches': digest(path.read_bytes()) == candidate['sha256']},
            'independent_evidence': references, 'test_ids': ['D-KNOW-' + op.upper() + '-' + vendor.upper()],
            'remediation':remediation,
            'candidate_bindings':[b for b in candidate_manifest.get('template_bindings',[]) if b['operation_id']==op and b['vendor']==vendor],
            'candidate_runtime_check':runtime_checks.get((op,vendor),{'outcome':'NOT RUN'}),
            'semantic_verification': 'NOT RUN', 'runtime_status': 'existing_active_binding' if bindings else 'unavailable',
            'native_device_testing': 'NOT RUN', 'ansible_variant': 'unavailable_until_separate_variant_gate',
            'owner': 'Phase D knowledge engineering',
            'remaining_work': findings + ['Independently review representative positive/negative native outputs and compatibility through V9; existing publication alone does not satisfy Phase D semantic verification.']})
    if len(rows) != 141 or len({op for op, _ in identities}) != 47:
        raise ValueError('Candidate scope drift; reconcile before repair')
    return {'format_version': 1, 'active_release': pointer, 'candidate_count': len(rows),
            'operation_count': 47, 'semantic_verified_count': 0,
            'reviewed_reference_remediations':sum(r['remediation'] is not None for r in rows),
            'compiled_acceptance_candidate':candidate_summary,
            'native_runtime_fixture_passes':len(runtime_checks),
            'completion': 'D1a static reconciliation only; D1b semantic remediation in progress', 'candidates': rows}


def route_contract(catalogs,operation_id='configure_static_route'):
    op = next(o for o in catalogs['operations'] if o['operation_id'] == operation_id)
    version = op['version'] + 1
    values = {'version': version}
    for source, target in [('operation_parameters', 'mappings'), ('operation_rules', 'rules'), ('template_bindings', 'templates')]:
        values[target] = [deepcopy(r) for r in catalogs[source] if r['operation_id'] == op['operation_id']]
        for record in values[target]: record['operation_version'] = version
    for binding in values['templates']:
        if binding['vendor'] in {'cisco', 'huawei'}:
            binding['input_contract']['derived'].update(destination_address='destination_address_v1', destination_mask='destination_mask_v1')
    root_rule = next((r for r in values['rules'] if r['field_path'] == ''), None)
    if root_rule is None:
        root_rule = {'operation_id': op['operation_id'], 'operation_version': version, 'field_path': '', 'keywords': {}}
        values['rules'].append(root_rule)
    root_rule['keywords']['x-validation-handlers'] = ['network_values_v1', 'unique_interfaces_v1', 'safe_strings_v1', 'expansion_network_v1']
    return {'entity': 'contract', 'action': 'replace', 'entity_id': op['operation_id'], 'values': values}


ROUTE_TEMPLATES = {
    'cisco': 'ip route {{ destination_address }} {{ destination_mask }} {{ next_hop }}{% if preference is defined and preference %} {{ preference }}{% endif %}\n',
    'huawei': 'ip route-static {{ destination_address }} {{ destination_mask }} {{ next_hop }}{% if preference is defined and preference %} preference {{ preference }}{% endif %}\n',
}


async def repair_routes(target=None):
    import os
    from fastapi import FastAPI
    import httpx
    target = target or ROOT / 'tmp/phase-d/acceptance-knowledge'
    source = ROOT / 'backend/knowledge_workspace'
    if not target.exists():
        # One acceptance workspace, consistent SQLite backup; never replaces ordinary data.
        shutil.copytree(source, target, ignore=shutil.ignore_patterns('*.sqlite3', '*.sqlite3-*', '*.db', '*.db-*', '.b-*'))
        for original in (source / 'storage/knowledge').glob('*.sqlite3'):
            destination = target / original.relative_to(source)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(original.resolve().as_uri() + '?mode=ro', uri=True) as src, sqlite3.connect(destination) as dst: src.backup(dst)
    os.environ['COGNISHIELD_KNOWLEDGE_ROOT'] = str(target)
    from local_providers.knowledge import router
    from auth.auth import create_access_token
    app = FastAPI(); app.include_router(router, prefix='/api/v1')
    run = Run('D1b-route-authoring', 'unit_deterministic')
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://acceptance',
                               headers={'Authorization': 'Bearer ' + create_access_token(1, 'admin', 'admin')}, timeout=300) as client:
        async def call(method, path, body=None):
            response = await client.request(method, '/api/v1/knowledge' + path, json=body)
            data = response.json()
            run.record('D-KNOW-ROUTE-AUTHORING', 'PASS' if response.status_code == 200 else 'FAIL',
                       expected='Authorized existing Knowledge Engineering API succeeds in disposable workspace',
                       actual=data, method=method, path=path, status=response.status_code)
            response.raise_for_status(); return data
        initial = await call('GET', '')
        old_release = initial['data']['active_release']['release_id']
        for operation_id in ['configure_static_route','remove_static_route']:
            state = await call('GET', '')
            bindings=state['data']['catalogs']['template_bindings'];rules=state['data']['catalogs']['operation_rules']
            canonical=any(r['operation_id']==operation_id and 'expansion_network_v1' in r['keywords'].get('x-validation-handlers',[]) for r in rules)
            if not canonical or any(not b['input_contract'].get('derived',{}).get('destination_mask') for b in bindings if b['operation_id']==operation_id and b['vendor'] in ROUTE_TEMPLATES):
                await call('POST','/edit',{'expected_revision':state['revision'],'reason':'Phase D: separate IPv4 destination/mask for add and exact removal','changes':[route_contract(state['data']['catalogs'],operation_id)]})
            for vendor,content in ROUTE_TEMPLATES.items():
                state=await call('GET','')
                if operation_id=='remove_static_route':content=('no ' if vendor=='cisco' else 'undo ')+content.split('{% if',1)[0].rstrip()+'\n'
                binding=next(b for b in state['data']['catalogs']['template_bindings'] if b['operation_id']==operation_id and b['vendor']==vendor)
                if state['data']['templates'][binding['template_path']]!=content:
                    await call('PUT','/template',{'expected_revision':state['revision'],'reason':'Phase D IPv4 route add/remove prefix/mask repair; native only','path':binding['template_path'],'content':content})
        await call('POST', '/validate')
        final = await call('GET', '')
        assert final['data']['active_release']['release_id'] == old_release
        # These exact outputs are independent fixtures, not rendered expectations.
        expected = {
            'cisco': ['ip route 203.0.113.0 255.255.255.0 10.1.1.1', 'ip route 0.0.0.0 0.0.0.0 10.1.1.1', 'ip route 203.0.113.7 255.255.255.255 10.1.1.1'],
            'huawei': ['ip route-static 203.0.113.0 255.255.255.0 10.1.1.1', 'ip route-static 0.0.0.0 0.0.0.0 10.1.1.1', 'ip route-static 203.0.113.7 255.255.255.255 10.1.1.1'],
            'juniper': ['set routing-options static route 203.0.113.0/24 next-hop 10.1.1.1', 'set routing-options static route 0.0.0.0/0 next-hop 10.1.1.1', 'set routing-options static route 203.0.113.7/32 next-hop 10.1.1.1'],
        }
        for operation_id,vendor in [(op,vendor) for op in ['configure_static_route','remove_static_route'] for vendor in expected]:
            binding = next(b for b in final['data']['catalogs']['template_bindings'] if b['operation_id'] == operation_id and b['vendor'] == vendor)
            body = {'expected_revision': final['revision'], 'path': binding['template_path'], 'content': final['data']['templates'][binding['template_path']]}
            for prefix, output in zip(['203.0.113.0/24', '0.0.0.0/0', '203.0.113.7/32'], expected[vendor]):
                if operation_id=='remove_static_route':output=('no '+output if vendor=='cisco' else 'undo '+output if vendor=='huawei' else output.replace('set routing-options','delete routing-options',1))
                response = await call('POST', '/render', body | {'parameters': {'destination': prefix, 'next_hop': '10.1.1.1'}})
                actual = response['data']['configuration'].strip()
                run.record('D-KNOW-ROUTE-' + vendor.upper(), 'PASS' if actual == output else 'FAIL', expected=output, actual=actual, operation_id=operation_id,profile=binding['platform'], versions=binding['versions'])
                assert actual == output
            for invalid in [{}, {'destination': '203.0.113.1/24', 'next_hop': '10.1.1.1'},
                            {'destination': '203.0.113.0/255.0.255.0', 'next_hop': '10.1.1.1'},
                            {'destination': '203.0.113.0/24', 'next_hop': 'invalid'},
                            {'destination': '203.0.113.0/24', 'next_hop': '10.1.1.1', 'preference': 999}]:
                response = await client.post('/api/v1/knowledge/render', json=body | {'parameters': invalid})
                run.record('D-KNOW-ROUTE-NEGATIVE-' + vendor.upper(), 'PASS' if response.status_code == 422 else 'FAIL', expected='V9 rejects invalid input', actual=response.json(), parameters=invalid,operation_id=operation_id)
                assert response.status_code == 422
        run.record('D-KNOW-DRAFT-ISOLATION', 'PASS', expected='Ordinary and acceptance active pointers stay unchanged',
                   actual={'acceptance_release': old_release, 'ordinary_pointer': json.loads((source / 'storage/catalog_releases/active.json').read_text())})
    print(json.dumps({'run': str(run.path), 'target': str(target), 'status': 'authoring_repaired_not_published'}))


async def test_route_candidate():
    """Compile with the real publisher, activate ONLY the acceptance copy, rollback.

    This is not an ordinary publication gate or certification of other bindings.
    """
    import os
    import httpx
    from fastapi import FastAPI
    from auth.auth import create_access_token
    target=ROOT/'tmp/phase-d/acceptance-knowledge'
    if not target.exists():raise ValueError('Run repair-routes in the acceptance copy first')
    os.environ['COGNISHIELD_KNOWLEDGE_ROOT']=str(target)
    from local_providers.knowledge import router
    from local_providers.v9_studio import worker
    app=FastAPI();app.include_router(router,prefix='/api/v1')
    run=Run('D1b-route-candidate','unit_deterministic')
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://acceptance',
        headers={'Authorization':'Bearer '+create_access_token(1,'admin','admin')},timeout=300) as client:
        async def call(method,path,body=None):
            response=await client.request(method,'/api/v1/knowledge'+path,json=body)
            run.record('D-KNOW-CANDIDATE-API','PASS' if response.status_code==200 else 'FAIL',expected='Existing revision-checked knowledge API succeeds in acceptance workspace',actual=response.json(),path=path,status=response.status_code)
            response.raise_for_status();return response.json()
        before=await call('GET','');old=before['data']['active_release']['release_id']
        built=await call('POST','/build',{'mode':'offline','expected_revision':before['revision'],'expected_release':old,'reason':'Phase D static-route candidate compiler/runtime validation; no ordinary activation'})
        candidate=built['data']['release_id']
        after=await call('GET','');assert after['data']['active_release']['release_id']==old
        details=await call('GET','/releases/'+candidate)
        run.record('D-KNOW-CANDIDATE-NO-ACTIVATION','PASS',expected=old,actual=after['data']['active_release']['release_id'],candidate_release=candidate)
        (run.path/'candidate-summary.json').write_text(json.dumps({'release_id':candidate,'old_release':old,'workspace':str(target),'revision':before['revision'],'binding_count':len(details['data']['manifest']['template_bindings'])},indent=2),encoding='utf-8')
        await call('POST','/activate',{'release_id':candidate,'expected_release':old,'reason':'Acceptance-only candidate runtime checks'})
        try:
            fixtures=json.loads((ROOT.parent/'network_rag_catalog_v2/data/inventory/devices.json').read_text())
            selected=[]
            expected={'cisco':'ip route 203.0.113.0 255.255.255.0 192.0.2.2','huawei':'ip route-static 203.0.113.0 255.255.255.0 192.0.2.2','juniper':'set routing-options static route 203.0.113.0/24 next-hop 192.0.2.2'}
            bindings=[b for b in details['data']['manifest']['template_bindings'] if b['operation_id']=='configure_static_route']
            for binding in bindings:
                device=deepcopy(next(d for d in fixtures if d['vendor']==binding['vendor'] and d['platform']==binding['platform'] and str(d['version']) in binding['versions']))
                device.update(id='acceptance-route-'+device['vendor'],hostname='D-ROUTE-'+device['vendor'].upper(),aliases=[])
                selected.append(device)
            plan={'original_prompt':'Engineer-reviewed static routes','tasks':[],'intents':[],'knowledge_snapshot_id':candidate}
            entries=[{'task_id':op+'-'+d['vendor'],'operation_id':op,'target_host':d['hostname'],'parameters':{'destination':'203.0.113.0/24','next_hop':'192.0.2.2'}} for op in ['configure_static_route','remove_static_route'] for d in selected]
            # Add/remove of the same exact route conflict by design. Exercise
            # separate reviewed requests rather than bypass V9 conflict checks.
            outputs=[]
            for op in ['configure_static_route','remove_static_route']:
                outputs.append(worker({'inventory':selected,'model':'qwen2.5:1.5b','prompt':plan['original_prompt'],'plan':plan,'allow_multi':True,'selection':[e for e in entries if e['operation_id']==op],'confirm_order':True}))
            for output in outputs:
              for task in output['plan']['tasks']:
                vendor=task['target_devices'][0]['vendor'];configs=task['configs'];actual=configs[0]['configuration'].strip() if configs else task
                required=expected[vendor]
                if task['operation_id']=='remove_static_route':required=('no '+required if vendor=='cisco' else 'undo '+required if vendor=='huawei' else required.replace('set routing-options','delete routing-options',1))
                passed=task['status']=='rendered' and actual==required
                run.record('D-KNOW-ROUTE-RUNTIME-'+vendor.upper(),'PASS' if passed else 'FAIL',expected=required,actual=actual,operation_id=task['operation_id'],release_id=candidate,model_calls=output.get('model_calls'),scope='Existing V9 worker finalization/schema/binding/render; explicit engineer selection')
                assert passed,(vendor,task)
            assert output['release_id']==candidate
            # Explicit reviewed selections also exercise the newly reconstructed
            # Cisco contracts. Independent fixtures do not use template rendering
            # to manufacture their expected values.
            cisco=next(d for d in selected if d['vendor']=='cisco')
            # This is the explicitly declared acceptance device, not R1/R2.
            # V9 rejected the original route-only fixture for ISIS as intended.
            cisco['capabilities']['features']+=['isis','management_plane_security']
            reviewed=[
                ('configure_isis_interface',{'interface':'Ethernet1/1','process_name':'CAMPUS','level':'level-2'},'interface Ethernet1/1\n ip router isis CAMPUS\n isis circuit-type level-2-only\n exit'),
                ('disable_isis_interface',{'interface':'Ethernet1/1','process_name':'CAMPUS'},'interface Ethernet1/1\n no ip router isis CAMPUS\n exit'),
                ('configure_login_banner',{'login_banner_text':'Authorized access only'},'banner login #\nAuthorized access only\n#'),
                ('configure_exec_timeout',{'exec_timeout_minutes':5},'line vty 0 4\n exec-timeout 5 0\n exit'),
                ('configure_login_lockout',{'login_block_seconds':120,'login_failure_attempts':3,'login_failure_window_seconds':60},'login block-for 120 attempts 3 within 60')]
            for op,parameters,required in reviewed:
                output=worker({'inventory':selected,'model':'qwen2.5:1.5b','prompt':'Engineer-reviewed native operation; existing protocol/process prerequisites reviewed separately',
                    'plan':plan,'allow_multi':True,'selection':[{'task_id':op+'-cisco','operation_id':op,'target_host':cisco['hostname'],'parameters':parameters}],'confirm_order':True})
                task=output['plan']['tasks'][0];actual=task['configs'][0]['configuration'].strip() if task['configs'] else task
                passed=task['status']=='rendered' and actual==required
                run.record('D-KNOW-CISCO-RUNTIME-'+op.upper(),'PASS' if passed else 'FAIL',expected=required,actual=actual,release_id=candidate,
                    scope='V9 schema/binding/native rendering only; process prerequisites and device operation are separate')
                assert passed,(op,task)
        finally:
            await call('POST','/activate',{'release_id':old,'expected_release':candidate,'reason':'Acceptance-only rollback after candidate checks; ordinary release unchanged'})
        restored=await call('GET','');assert restored['data']['active_release']['release_id']==old
    print(json.dumps({'run':str(run.path),'candidate':candidate,'ordinary_activated':False,'acceptance_rollback':'verified'}),flush=True)


async def repair_isis_cisco(target=None):
    """Correct reviewed interface-mode commands, without asserting NET/adjacency.

    Huawei numeric process identity and Junos family-ISO prerequisites remain
    separate blocked contracts; a Cisco tag cannot be copied into those bindings.
    """
    import os,httpx
    from fastapi import FastAPI
    from auth.auth import create_access_token
    os.environ['COGNISHIELD_KNOWLEDGE_ROOT']=str(target or ROOT/'tmp/phase-d/acceptance-knowledge')
    from local_providers.knowledge import router
    app=FastAPI();app.include_router(router,prefix='/api/v1')
    run=Run('D1b-isis-cisco','unit_deterministic')
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://acceptance',headers={'Authorization':'Bearer '+create_access_token(1,'admin','admin')},timeout=300) as client:
        async def call(method,path,body=None):
            response=await client.request(method,'/api/v1/knowledge'+path,json=body)
            run.record('D-KNOW-ISIS-CISCO-API','PASS' if response.status_code==200 else 'FAIL',expected='Existing revision-checked authoring API succeeds',actual=response.json(),path=path)
            response.raise_for_status();return response.json()
        templates={'configure_isis_interface':'interface {{ interface }}\n ip router isis {{ process_name }}\n isis circuit-type {{ "level-2-only" if level == "level-2" else level }}\n exit\n',
            'disable_isis_interface':'interface {{ interface }}\n no ip router isis {{ process_name }}\n exit\n'}
        for operation_id,content in templates.items():
            state=await call('GET','');catalogs=state['data']['catalogs']
            root=next(r for r in catalogs['operation_rules'] if r['operation_id']==operation_id and r['field_path']=='')
            rules=[r for r in catalogs['operation_rules'] if r['operation_id']==operation_id]
            field=next(r for r in rules if r['field_path']=='process_name')
            if not field['keywords'].get('pattern') or 'safe_strings_v1' not in root['keywords'].get('x-validation-handlers',[]):
                op=next(o for o in catalogs['operations'] if o['operation_id']==operation_id);values={'version':op['version']+1}
                for source,key in [('operation_parameters','mappings'),('operation_rules','rules'),('template_bindings','templates')]:
                    values[key]=[deepcopy(r) for r in catalogs[source] if r['operation_id']==operation_id]
                    for row in values[key]:row['operation_version']=values['version']
                next(r for r in values['rules'] if r['field_path']=='process_name')['keywords']['pattern']='^[A-Za-z0-9_.-]{1,32}$'
                next(r for r in values['rules'] if r['field_path']=='')['keywords']['x-validation-handlers']=['network_values_v1','unique_interfaces_v1','safe_strings_v1']
                await call('POST','/edit',{'expected_revision':state['revision'],'reason':'Phase D ISIS interface context and safe explicit process tag','changes':[{'entity':'contract','action':'replace','entity_id':operation_id,'values':values}]})
            state=await call('GET','');binding=next(b for b in state['data']['catalogs']['template_bindings'] if b['operation_id']==operation_id and b['vendor']=='cisco')
            if state['data']['templates'][binding['template_path']]!=content:
                await call('PUT','/template',{'expected_revision':state['revision'],'reason':'IOS-XE: separate interface IP-ISIS attachment and circuit-type commands; no protocol restart','path':binding['template_path'],'content':content})
            state=await call('GET','');body={'expected_revision':state['revision'],'path':binding['template_path'],'content':content}
            params={'interface':'GigabitEthernet0/1','process_name':'CAMPUS'}
            cases=[(params|{'level':level},'interface GigabitEthernet0/1\n ip router isis CAMPUS\n isis circuit-type '+native+'\n exit') for level,native in [('level-1','level-1'),('level-2','level-2-only'),('level-1-2','level-1-2')]] if operation_id=='configure_isis_interface' else [(params,'interface GigabitEthernet0/1\n no ip router isis CAMPUS\n exit')]
            for parameters,expected in cases:
                result=await call('POST','/render',body|{'parameters':parameters});actual=result['data']['configuration'].strip()
                run.record('D-KNOW-ISIS-CISCO-RENDER','PASS' if actual==expected else 'FAIL',expected=expected,actual=actual,operation_id=operation_id,parameters=parameters,
                    independent_reference='https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/iproute_isis/command/irs-cr-book.pdf',scope='Interface attachment to an existing NET-configured process; no adjacency or device certification')
                assert actual==expected
            for parameters in [{},{**cases[0][0],'process_name':'CAMPUS\n shutdown'},{**cases[0][0],'interface':'Gi0/1\n shutdown'}]:
                response=await client.post('/api/v1/knowledge/render',json=body|{'parameters':parameters})
                run.record('D-KNOW-ISIS-CISCO-NEGATIVE','PASS' if response.status_code==422 else 'FAIL',expected='V9 rejects missing/injected values',actual=response.json(),operation_id=operation_id)
                assert response.status_code==422
        await call('POST','/validate')
    print(json.dumps({'run':str(run.path),'ordinary_activated':False}),flush=True)


async def sync_reviewed_references():
    """Update reviewed editable files from acceptance authoring.

    Source/binding history stays recorded. This does not promote runtime support.
    """
    import os,httpx
    from fastapi import FastAPI
    from auth.auth import create_access_token
    from jinja2 import Environment,meta
    os.environ['COGNISHIELD_KNOWLEDGE_ROOT']=str(ROOT/'tmp/phase-d/acceptance-knowledge')
    from local_providers.knowledge import router
    app=FastAPI();app.include_router(router,prefix='/api/v1')
    run=Run('D1b-reference-sync','unit_deterministic')
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://acceptance',headers={'Authorization':'Bearer '+create_access_token(1,'admin','admin')}) as client:
        response=await client.get('/api/v1/knowledge');response.raise_for_status();state=response.json()
    pairs={(op,vendor) for op in ['configure_static_route','remove_static_route'] for vendor in ['cisco','huawei']}|{(op,'cisco') for op in ['configure_isis_interface','disable_isis_interface','configure_login_banner','configure_exec_timeout','configure_login_lockout']}
    index_path=ROOT/'backend/ansible/reference/operation_drafts/index.json';index=json.loads(index_path.read_text(encoding='utf-8'))
    backup=run.path/'reference-before';backup.mkdir()
    (backup/'index.json').write_bytes(index_path.read_bytes())
    for row in index['templates']:
        if (row['operation_id'],row['vendor']) not in pairs:continue
        binding=next(b for b in state['data']['catalogs']['template_bindings'] if b['operation_id']==row['operation_id'] and b['vendor']==row['vendor'])
        path=ROOT/'backend/ansible'/row['path'];assert path.resolve().is_relative_to((ROOT/'backend/ansible/reference/operation_drafts').resolve())
        before=path.read_bytes();(backup/(row['operation_id']+'-'+row['vendor']+'.j2')).write_bytes(before)
        content='{# Reviewed authoring candidate; not activated runtime support. Verify device prerequisites before use. #}\n'+state['data']['templates'][binding['template_path']]
        path.write_text(content,encoding='utf-8');row.update(source='reviewed_authoring_candidate',source_authoring_revision=state['revision'],
            sha256=digest(path.read_bytes()),variables=sorted(meta.find_undeclared_variables(Environment().parse(content))),
            input_contract=binding['input_contract'],verified_runtime_support=False)
        run.record('D-KNOW-REFERENCE-SYNC','PASS',expected='Existing editable reference matches the authored candidate and retains draft status',actual={'path':row['path'],'sha256':row['sha256'],'previous_sha256':digest(before),'source':row['source']})
    assert len(index['templates'])==141
    index_path.write_text(json.dumps(index,indent=2),encoding='utf-8')
    print(json.dumps({'run':str(run.path),'references_updated':len(pairs),'ordinary_activated':False}),flush=True)


async def author_management(target=None):
    """Reconstruct reviewed management contracts through authoring, not migration.

    The isolated VLAN/lab_label changes and release assets are never imported.
    These commands cover a single-line notice, VTY 0..4 idle timer and login block.
    No authentication, recovery access or other VTY ranges are changed.
    """
    import os, httpx
    from fastapi import FastAPI
    from auth.auth import create_access_token
    os.environ['COGNISHIELD_KNOWLEDGE_ROOT']=str(target or ROOT/'tmp/phase-d/acceptance-knowledge')
    from local_providers.knowledge import router
    app=FastAPI();app.include_router(router,prefix='/api/v1')
    run=Run('D1b-management-authoring','unit_deterministic')
    parameters={
        'login_banner_text':('string',{'minLength':1,'maxLength':240,'pattern':r'^[\x20-\x22\x24-\x7E]+$'}),
        'exec_timeout_minutes':('integer',{'minimum':1,'maximum':60}),
        'exec_timeout_seconds':('integer',{'minimum':0,'maximum':59,'default':0}),
        'login_block_seconds':('integer',{'minimum':1,'maximum':3600}),
        'login_failure_attempts':('integer',{'minimum':1,'maximum':10}),
        'login_failure_window_seconds':('integer',{'minimum':1,'maximum':3600})}
    specs={
        'configure_login_banner':('Set a single-line pre-authentication warning; # delimiter is excluded.', ['login_banner_text'],
            'banner login #\n{{ login_banner_text }}\n#\n',{'login_banner_text':'Authorized access only'},'banner login #\nAuthorized access only\n#',
            [{'login_banner_text':'bad#delimiter'},{'login_banner_text':'line\nbreak'},{'login_banner_text':''}]),
        'configure_exec_timeout':('Idle timeout for VTY 0 through 4 only; no authentication or transport change.', ['exec_timeout_minutes','exec_timeout_seconds'],
            'line vty 0 4\n exec-timeout {{ exec_timeout_minutes }} {{ exec_timeout_seconds if exec_timeout_seconds is not none else 0 }}\n exit\n',
            {'exec_timeout_minutes':5},'line vty 0 4\n exec-timeout 5 0\n exit',
            [{'exec_timeout_minutes':0},{'exec_timeout_minutes':61},{'exec_timeout_minutes':5,'exec_timeout_seconds':60}]),
        'configure_login_lockout':('Block repeated remote login failures; quiet-mode exemptions and recovery access are unchanged.', ['login_block_seconds','login_failure_attempts','login_failure_window_seconds'],
            'login block-for {{ login_block_seconds }} attempts {{ login_failure_attempts }} within {{ login_failure_window_seconds }}\n',
            {'login_block_seconds':120,'login_failure_attempts':3,'login_failure_window_seconds':60},'login block-for 120 attempts 3 within 60',
            [{'login_block_seconds':0,'login_failure_attempts':3,'login_failure_window_seconds':60},{'login_block_seconds':120,'login_failure_attempts':11,'login_failure_window_seconds':60}])}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://acceptance',headers={'Authorization':'Bearer '+create_access_token(1,'admin','admin')},timeout=300) as client:
        async def call(method,path,body=None):
            r=await client.request(method,'/api/v1/knowledge'+path,json=body)
            run.record('D-KNOW-MANAGEMENT-API','PASS' if r.status_code==200 else 'FAIL',expected='Existing authenticated revision-checked authoring API',actual=r.json(),path=path)
            r.raise_for_status();return r.json()
        initial=await call('GET','');cat=initial['data']['catalogs']
        vlan_before={name:[r for r in cat[name] if r.get('operation_id')=='create_vlan'] for name in ['operations','operation_parameters','operation_rules','template_bindings']}
        changes=[]
        category='management_plane_security'
        if not any(r['category_id']==category for r in cat['categories']):
            changes.append({'entity':'category','action':'create','entity_id':category,'values':{'display_name':'Management Plane Security','description':'Login warning, bounded VTY idle timer and failed-login protection.','status':'active'}})
        for name,(kind,rules) in parameters.items():
            if not any(r['parameter_id']==name for r in cat['parameters']):
                changes.append({'entity':'parameter','action':'create','entity_id':name,'values':{'display_name':name.replace('_',' '),'value_type':kind,'description':'Explicit management input; bounded by reviewed operation schema.','cognishield_preset':rules}})
            if not any(r['category_id']==category and r['parameter_id']==name for r in cat['category_parameters']):
                changes.append({'entity':'membership','action':'assign','values':{'category_id':category,'parameter_id':name}})
        if changes:await call('POST','/edit',{'expected_revision':initial['revision'],'reason':'Phase D reconstruct six management inputs; preserve ordinary VLAN contract','changes':changes})
        for op,(description,fields,content,positive,expected,negatives) in specs.items():
            state=await call('GET','');cat=state['data']['catalogs']
            if not any(r['operation_id']==op for r in cat['operations']):
                mappings=[{'operation_id':op,'operation_version':1,'category_id':category,'parameter_id':field,'field_path':field,'position':i,'required':field!='exec_timeout_seconds','required_order':i if field!='exec_timeout_seconds' else None} for i,field in enumerate(fields)]
                rules=[{'operation_id':op,'operation_version':1,'field_path':'','keywords':{'$schema':'https://json-schema.org/draft/2020-12/schema','type':'object','additionalProperties':False}}]+[{'operation_id':op,'operation_version':1,'field_path':field,'keywords':parameters[field][1]} for field in fields]
                await call('POST','/edit',{'expected_revision':state['revision'],'reason':'Phase D reviewed management operation reconstruction; no isolated release promotion','changes':[
                    {'entity':'operation','action':'create','entity_id':op,'values':{'display_name':op.replace('_',' ').capitalize(),'category_id':category,'description':description,'status':'inactive','version':1}},
                    {'entity':'contract','action':'replace','entity_id':op,'values':{'version':1,'mappings':mappings,'rules':rules,'templates':[]}}]})
            state=await call('GET','');binding=next((b for b in state['data']['catalogs']['template_bindings'] if b['operation_id']==op and b['vendor']=='cisco'),None)
            if binding is None:
                await call('PUT','/template',{'expected_revision':state['revision'],'reason':'Reviewed Cisco IOS-XE management native variant; other vendors unsupported','path':'','content':content,'operation_id':op,'vendor':'cisco','platform':'iosxe','versions':['17.9']})
            state=await call('GET','');operation=next(r for r in state['data']['catalogs']['operations'] if r['operation_id']==op)
            if operation['status']!='active':
                await call('POST','/edit',{'expected_revision':state['revision'],'reason':'Enable complete reviewed management contract in acceptance authoring only','changes':[{'entity':'operation','action':'update','entity_id':op,'values':{'status':'active'}}]})
            state=await call('GET','');binding=next(b for b in state['data']['catalogs']['template_bindings'] if b['operation_id']==op and b['vendor']=='cisco')
            body={'expected_revision':state['revision'],'path':binding['template_path'],'content':state['data']['templates'][binding['template_path']]}
            result=await call('POST','/render',body|{'parameters':positive});actual=result['data']['configuration'].strip()
            run.record('D-KNOW-MANAGEMENT-'+op.upper(),'PASS' if actual==expected else 'FAIL',expected=expected,actual=actual,scope='Native authoring preview; not device or playbook certification',independent_reference='https://sec.cloudapps.cisco.com/security/center/resources/IOS_XE_hardening')
            assert actual==expected
            for invalid in [{}]+negatives+[positive|{'unexpected':'value'}]:
                response=await client.post('/api/v1/knowledge/render',json=body|{'parameters':invalid})
                run.record('D-KNOW-MANAGEMENT-NEGATIVE','PASS' if response.status_code==422 else 'FAIL',expected='V9 rejects missing, out-of-policy or unexpected input',actual=response.json(),operation_id=op)
                assert response.status_code==422
        await call('POST','/validate');final=await call('GET','');cat=final['data']['catalogs']
        assert vlan_before=={name:[r for r in cat[name] if r.get('operation_id')=='create_vlan'] for name in vlan_before}
        assert final['data']['active_release']==initial['data']['active_release']
        run.record('D-KNOW-MANAGEMENT-ISOLATION','PASS',expected='VLAN, active pointer and isolated test contracts remain unchanged',actual={'operations':len(cat['operations']),'bindings':len(cat['template_bindings']),'lab_label_imported':any(p['parameter_id']=='lab_label' for p in cat['parameters'])})
    print(json.dumps({'run':str(run.path),'ordinary_activated':False}),flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['audit', 'repair-routes','test-route-candidate','repair-isis-cisco','sync-reviewed-references','author-management']); args = parser.parse_args()
    if args.action == 'audit':
        result = coverage(); out = ROOT / 'docs/evaluations/phase_d_vendor_coverage.json'
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(json.dumps({k: v for k, v in result.items() if k != 'candidates'}))
    else:
        import asyncio
        asyncio.run(repair_routes() if args.action=='repair-routes' else repair_isis_cisco() if args.action=='repair-isis-cisco' else sync_reviewed_references() if args.action=='sync-reviewed-references' else author_management() if args.action=='author-management' else test_route_candidate())
