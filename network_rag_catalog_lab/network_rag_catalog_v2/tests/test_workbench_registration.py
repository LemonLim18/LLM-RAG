"""Registration uses only a temporary copy; never the user's inventory authority."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
import unittest
from unittest.mock import patch
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from app.devices.inventory import load_inventory, resolve_targets, TargetResolutionError
from app.workbench.api import create_app
from app.workbench.inventory_service import _revision
from app.workbench.inventory_registration import DeviceRegistration, register_device
from app.workbench.planning_models import PlanningRequest, AnswerRequest
from app.workbench.planning_service import PlanningService, PlanningError


class InventoryRegistrationTests(unittest.TestCase):
    def setUp(self):
        from app.devices.inventory import INVENTORY_FILE
        self.user_path = INVENTORY_FILE
        self.user_before = (INVENTORY_FILE.read_bytes(), INVENTORY_FILE.stat().st_mtime_ns)
        self.directory = Path(self.enterContext(TemporaryDirectory(dir=Path.cwd())))
        self.path = self.directory / 'inventory' / 'devices.json'
        self.path.parent.mkdir()
        self.path.write_bytes(self.user_before[0])
        self.enterContext(patch('app.devices.inventory.INVENTORY_FILE', self.path))
        self.records = json.loads(self.user_before[0])
        self.client = self.enterContext(TestClient(create_app()))
        self.request = {'expected_inventory_revision': _revision(self.records), 'device': {
            'hostname': 'R99', 'display_name': 'Demo router 99', 'kind': 'router',
            'vendor': 'juniper', 'platform': 'junos', 'version': '23.4', 'site': 'Lab', 'role': 'edge',
            'location': 'Rehearsal', 'aliases': ['edge-r99'], 'tags': ['synthetic'],
            'capabilities': {'features': ['ospf', 'interface']},
            'interfaces': [{'name': 'ge-0/0/0', 'aliases': ['uplink99'], 'type': 'ethernet', 'role': 'uplink', 'enabled': True}],
        }}

    def tearDown(self):
        self.assertEqual(self.user_before, (self.user_path.read_bytes(), self.user_path.stat().st_mtime_ns))

    def post(self, request=None):
        return self.client.post('/api/v1/inventory/devices', json=request or self.request)

    def test_register_preserves_all_records_and_is_visible_to_loader_api_and_target_resolver(self):
        with patch('subprocess.Popen', side_effect=AssertionError('No execution')), \
                patch('socket.create_connection', side_effect=AssertionError('No network')):
            response = self.post()
        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        device = body['device']
        UUID(device['id'].removeprefix('dev-'))
        loaded = load_inventory()
        self.assertEqual(loaded[:-1], self.records)
        self.assertEqual(loaded[-1]['id'], device['id'])
        self.assertEqual(body['inventory_revision'], _revision(loaded))
        self.assertEqual(self.client.get('/api/v1/inventory/devices').json()['devices'][-1], device)
        self.assertEqual(self.client.get('/api/v1/inventory/devices/' + device['id']).json(), body)
        for name in ('R99', 'r99', 'edge-r99', 'Demo router 99'):
            self.assertEqual([item['id'] for item in resolve_targets([name])], [device['id']])
        # IDs identify API records but are not in V9's target attribute registry.
        with self.assertRaises(TargetResolutionError):
            resolve_targets([device['id']])
        for forbidden in ('management_ip', 'ansible', 'monitoring', 'source_refs'):
            self.assertNotIn(forbidden, device)
        self.assertEqual(device['interfaces'][0]['neighbor'], None)

    def test_duplicate_hostname_alias_display_and_generated_id_are_rejected(self):
        before = self.path.read_bytes()
        for field, value in [('hostname', 'r1'), ('aliases', ['CORE ROUTER 1']), ('display_name', 'R2')]:
            request = deepcopy(self.request); request['device'][field] = value
            self.assertEqual(self.post(request).json()['detail']['code'], 'IDENTITY_CONFLICT')
        with patch('app.workbench.inventory_registration.uuid4', return_value=UUID(int=99)):
            self.assertEqual(self.post().status_code, 201)
            request = deepcopy(self.request)
            request['expected_inventory_revision'] = _revision(load_inventory())
            request['device'].update(hostname='R100', display_name='Router 100', aliases=[])
            self.assertEqual(self.post(request).json()['detail']['code'], 'IDENTITY_CONFLICT')
        self.assertEqual(json.loads(before), load_inventory()[:-1])

    def test_strict_contract_invalid_and_missing_fields(self):
        before = self.path.read_bytes()
        for changes in ({'vendor': 'cisco_ios'}, {'platform': 'vrp'}, {'version': 23},
                        {'ssh_password': 'never accepted'}, {'id': 'dev-custom'}, {'hostname': 'bad\nname'},
                        {'capabilities': {'features': []}}, {'capabilities': {'features': ['invented']}},
                        {'interfaces': [{'name': 'x', 'type': 'ethernet', 'enabled': 'yes', 'role': 'uplink'}]},
                        {'interfaces': [{'name': 'x', 'type': 'ethernet', 'enabled': True, 'role': 'uplink', 'neighbor': {'device': 'R1', 'interface': 'x'}}]}):
            request = deepcopy(self.request); request['device'].update(changes)
            self.assertEqual(self.post(request).status_code, 422, changes)
        for field in ('hostname', 'site', 'role', 'version', 'capabilities'):
            request = deepcopy(self.request); del request['device'][field]
            self.assertEqual(self.post(request).status_code, 422)
        request = deepcopy(self.request); del request['expected_inventory_revision']
        self.assertEqual(self.post(request).status_code, 422)
        self.assertEqual(self.path.read_bytes(), before)

    def test_duplicate_interfaces_and_ambiguous_target_remain_v9_decisions(self):
        request = deepcopy(self.request)
        request['device']['interfaces'].append({**request['device']['interfaces'][0], 'name': 'ge-0/0/1'})
        self.assertEqual(self.post(request).json()['detail']['code'], 'IDENTITY_CONFLICT')
        self.assertEqual(self.post().status_code, 201)
        with self.assertRaises(TargetResolutionError) as caught:
            resolve_targets(['juniper'])
        self.assertEqual(caught.exception.code, 'AMBIGUOUS_TARGET')
        with self.assertRaises(TargetResolutionError):
            resolve_targets(['R404'])

    def test_stale_revision_and_whitespace_compatibility(self):
        self.path.write_text(json.dumps(self.records, separators=(',', ':')), encoding='utf-8')
        self.assertEqual(self.post().status_code, 201)
        before = self.path.read_bytes()
        self.assertEqual(self.post().json()['detail']['code'], 'STALE_INVENTORY')
        self.assertEqual(before, self.path.read_bytes())

    def test_complete_inventory_validation_preserves_unknown_attributes(self):
        self.records[0]['private_extra'] = {'future': ['keep', 42]}
        self.path.write_text(json.dumps(self.records), encoding='utf-8')
        self.request['expected_inventory_revision'] = _revision(self.records)
        self.assertEqual(self.post().status_code, 201)
        self.assertEqual(load_inventory()[0], self.records[0])
        self.assertNotIn('private_extra', self.client.get('/api/v1/inventory/devices').text)

    def test_invalid_existing_inventory_and_references_are_not_repaired(self):
        for transform in ('shape', 'neighbor', 'duplicate'):
            records = deepcopy(self.records)
            if transform == 'shape': records[0]['interfaces'] = 'bad'
            elif transform == 'neighbor': records[0]['interfaces'][0]['neighbor']['device'] = 'missing'
            else: records.append(deepcopy(records[0]))
            self.path.write_text(json.dumps(records), encoding='utf-8')
            before = self.path.read_bytes()
            self.assertEqual(self.post().json()['detail']['code'], 'INVALID_INVENTORY')
            self.assertEqual(before, self.path.read_bytes())

    def test_write_fsync_replace_failures_leave_old_json_and_release_gate(self):
        before = self.path.read_bytes()
        for target in ('app.workbench.inventory_registration.os.fsync', 'app.workbench.inventory_registration.os.replace'):
            with patch(target, side_effect=OSError('private path')):
                response = self.post()
            self.assertEqual(response.status_code, 503)
            self.assertNotIn('private path', response.text)
            self.assertEqual(before, self.path.read_bytes())
            self.assertEqual(list(self.path.parent.glob('*.tmp')), [])
        with patch.object(Path, 'open', side_effect=PermissionError('private path')):
            self.assertEqual(self.post().status_code, 503)
        self.assertEqual(self.post().status_code, 201)

    def test_external_change_detected_before_replace(self):
        def changed(_fd):
            records = deepcopy(self.records); records[0]['tags'].append('external')
            self.path.write_text(json.dumps(records), encoding='utf-8')
        with patch('app.workbench.inventory_registration.os.fsync', side_effect=changed):
            self.assertEqual(self.post().json()['detail']['code'], 'STALE_INVENTORY')
        self.assertEqual(len(load_inventory()), len(self.records))
        self.assertIn('external', load_inventory()[0]['tags'])

    def test_partial_temporary_write_never_replaces_inventory(self):
        before = self.path.read_bytes()
        original_open = Path.open
        class FailedWrite:
            def __init__(self, stream): self.stream = stream
            def __enter__(self): return self
            def __exit__(self, *args): self.stream.close()
            def write(self, content):
                self.stream.write(content[:20])
                raise OSError('simulated disk full')
        def opened(path, mode='r', *args, **kwargs):
            stream = original_open(path, mode, *args, **kwargs)
            return FailedWrite(stream) if mode == 'xb' else stream
        with patch.object(Path, 'open', opened):
            self.assertEqual(self.post().status_code, 503)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(load_inventory(), self.records)
        self.assertEqual(list(self.path.parent.glob('*.tmp')), [])

    def test_reader_observes_complete_old_or_new_snapshot(self):
        import os
        replace = os.replace
        def checked(source, target):
            self.assertEqual(load_inventory(), self.records)
            self.assertEqual(len(json.loads(Path(source).read_bytes())), len(self.records) + 1)
            replace(source, target)
            self.assertEqual(len(load_inventory()), len(self.records) + 1)
        with patch('app.workbench.inventory_registration.os.replace', side_effect=checked):
            self.assertEqual(self.post().status_code, 201)

    def test_registration_and_v9_mutations_share_the_gate(self):
        service = PlanningService()
        started, release = Event(), Event()
        def slow(request):
            started.set(); release.wait(5)
            return register_device(request)
        with patch('app.workbench.inventory_registration.register_device', side_effect=slow), ThreadPoolExecutor() as pool:
            future = pool.submit(service.register_inventory_device, DeviceRegistration(**self.request))
            try:
                self.assertTrue(started.wait(5))
                for operation in (
                    lambda: service.create(PlanningRequest(prompt='test', mode='local_v9', client_request_id=uuid4())),
                    lambda: service.answer(str(uuid4()), AnswerRequest(client_request_id=uuid4(), expected_session_revision='a'*64,
                        answer={'question_id':'q','revision':1,'source_revision':'source','kind':'custom','raw_input':'1'})),
                    lambda: service.register_inventory_device(DeviceRegistration(**self.request)),
                ):
                    with self.assertRaises(PlanningError) as caught: operation()
                    self.assertEqual(caught.exception.code, 'PLANNER_BUSY')
            finally: release.set()
            future.result()
        service._busy = True  # Same state while creation or answer owns the worker.
        with self.assertRaises(PlanningError): service.register_inventory_device(DeviceRegistration(**self.request))

    def test_inventory_change_stales_answer_without_modifying_saved_session(self):
        from app.clarification import ClarificationSession, save_session
        from app.context import context_revision, source_revision
        from app.planner.models import ExecutionPlan, PlannedTask
        self.enterContext(patch('app.context.DATA_DIR', self.directory))
        self.enterContext(patch('app.clarification.SESSIONS_DIR', self.directory))
        self.enterContext(patch('app.config.SESSIONS_DIR', self.directory))
        source = source_revision(); context = context_revision()
        question = {'question_id':'q-inventory','task_id':'task','revision':1,'source_revision':source,
                    'field_path':'vlan_id','wording':'VLAN ID?', 'allow_custom':True,'options':[]}
        task = PlannedTask('task','request','vlan','create_vlan',{},['R1'],status='needs_clarification',questions=[question])
        session = ClarificationSession(str(uuid4()),'created','updated','needs_clarification',
            ExecutionPlan('request',tasks=[task],status='needs_clarification',runtime_authority='files',context_revision=context))
        save_session(session)
        saved_path = self.directory / f'{session.session_id}.json'
        before = saved_path.read_bytes()
        self.assertEqual(self.post().status_code, 201)
        self.assertNotEqual(context_revision(), context)
        self.assertNotEqual(source_revision(), source)
        with patch('app.clarification.apply_answer') as applied:
            response = self.client.post(f'/api/v1/planning/sessions/{session.session_id}/answers', json={
                'client_request_id':str(uuid4()),'expected_session_revision':sha256(before).hexdigest(),
                'answer':{'question_id':question['question_id'],'revision':1,'source_revision':source,'kind':'custom','raw_input':'100','selected_ids':[]}})
        self.assertEqual(response.json()['detail']['code'], 'STALE_SOURCE', response.text)
        applied.assert_not_called()
        self.assertEqual(before, saved_path.read_bytes())


if __name__ == '__main__': unittest.main()
