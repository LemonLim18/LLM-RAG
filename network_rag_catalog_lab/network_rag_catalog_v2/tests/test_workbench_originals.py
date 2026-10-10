"""Immutable capture uses temporary storage and real V9 serialized sessions."""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Event
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from app.clarification import ClarificationSession, save_session
from app.planner.models import ExecutionPlan, PlannedTask
from app.workbench.api import create_app
from app.workbench import generated_originals as originals
from app.workbench.planning_service import PlanningService, PlanningError

URL = '/api/v1/workbench/artifacts/generated-originals'


class OriginalTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory(dir=Path.cwd()))).resolve()
        self.sessions = self.root / 'sessions'
        self.sessions.mkdir()
        self.enterContext(patch('app.config.STORAGE_DIR', self.root))
        for module in ('app.config', 'app.clarification'):
            self.enterContext(patch(module + '.SESSIONS_DIR', self.sessions))
        self.session_id = str(uuid4())
        self.text = '\ufeff! café\r\ninterface Ethernet1\n  description exact  \r\n\n'
        tasks = []
        for index in range(2):
            device = dict(id=f'dev-r{index + 1}', hostname=f'R{index + 1}', vendor='cisco', platform='ios', version='15')
            config = dict(device_id=device['id'], configuration=self.text + str(index), **{k: v for k, v in device.items() if k != 'id'})
            tasks.append(PlannedTask(f'task-{index}', 'request', 'routing', 'configure_ospf', {}, [device['id']],
                                    target_devices=[device], configs=[config, {**config, 'configuration': self.text}],
                                    status='rendered', device_id=device['id'], logical_intent_id='logical-1'))
        self.session = ClarificationSession(self.session_id, 'created', 'updated', 'ready',
            ExecutionPlan('request', tasks=tasks, status='ready', runtime_authority='direct_files', source_revision='old-source'))
        save_session(self.session)
        self.path = self.sessions / f'{self.session_id}.json'
        self.raw = self.path.read_bytes()
        self.mtime = self.path.stat().st_mtime_ns
        self.request = dict(session_id=self.session_id, expected_session_revision=sha256(self.raw).hexdigest(),
                            task_id='task-0', device_id='dev-r1', config_index=0)
        self.client = self.enterContext(TestClient(create_app()))

    def capture(self, **overrides):
        return self.client.post(URL, json={**self.request, **overrides})

    def test_exact_capture_associations_list_detail_and_source_unchanged(self):
        for task, device, entry in [('task-0', 'dev-r1', 0), ('task-0', 'dev-r1', 1), ('task-1', 'dev-r2', 0)]:
            response = self.capture(task_id=task, device_id=device, config_index=entry)
            self.assertEqual(response.status_code, 201, response.text)
            artifact = response.json()['artifact']
            expected = self.session.plan.tasks[int(task[-1])].configs[entry]['configuration']
            self.assertEqual(artifact['configuration'], expected)
            self.assertEqual(artifact['content_sha256'], sha256(expected.encode('utf-8')).hexdigest())
            self.assertEqual(artifact['source'], dict(session_id=self.session_id, session_revision=self.request['expected_session_revision'],
                                                    task_id=task, device_id=device, config_index=entry))
            self.assertEqual(artifact['logical_intent_id'], 'logical-1')
            self.assertEqual(artifact['authority']['plan_runtime_authority'], 'direct_files')
            self.assertEqual(self.client.get(URL + '/' + artifact['artifact_id']).json(), artifact)
        listing = self.client.get(URL).json()['artifacts']
        self.assertEqual(len(listing), 3)
        self.assertEqual([item['artifact_id'] for item in listing], sorted(item['artifact_id'] for item in listing))
        self.assertTrue(all('configuration' not in item for item in listing))
        self.assertEqual(self.path.read_bytes(), self.raw)
        self.assertEqual(self.path.stat().st_mtime_ns, self.mtime)

    def test_repeat_lost_response_and_new_process(self):
        original = self.capture().json()['artifact']  # Browser could lose this response.
        again = TestClient(create_app()).post(URL, json=self.request)
        self.assertEqual(again.status_code, 200)
        self.assertEqual(again.json(), dict(api_version=1, outcome='already_saved', artifact=original))
        script = '''import sys,json
from pathlib import Path
from fastapi.testclient import TestClient
import app.config as config
config.STORAGE_DIR=Path(sys.argv[1]); config.SESSIONS_DIR=config.STORAGE_DIR/'sessions'
from app.workbench.api import create_app
c=TestClient(create_app()); url=sys.argv[2]
assert c.get(url).status_code==200
r=c.post(url,json=json.loads(sys.argv[3])); assert r.status_code==200, r.text
assert r.json()['outcome']=='already_saved'
assert not any(x in sys.modules for x in ('app.clarification','app.pipeline','langchain_ollama','chromadb'))
print(r.json()['artifact']['artifact_id'])'''
        process = subprocess.run([sys.executable, '-c', script, str(self.root), URL, json.dumps(self.request)], capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertIn(original['artifact_id'], process.stdout)
        self.assertEqual(len(list(originals.storage_root().glob('*.json'))), 1)

    def test_stale_and_changed_session_original_still_readable(self):
        original = self.capture().json()['artifact']
        self.session.plan.tasks[0].configs[0]['configuration'] = 'new output'
        save_session(self.session)
        self.assertEqual(self.capture().json()['detail']['code'], 'STALE_SOURCE_SESSION')
        self.assertEqual(self.client.get(URL + '/' + original['artifact_id']).json(), original)
        revision = sha256(self.path.read_bytes()).hexdigest()
        other = self.capture(expected_session_revision=revision)
        self.assertEqual(other.status_code, 201)
        self.assertNotEqual(other.json()['artifact']['artifact_id'], original['artifact_id'])

    def test_invalid_coordinates_and_associations(self):
        for overrides in [dict(task_id='unknown'), dict(device_id='dev-r2'), dict(config_index=8)]:
            self.assertEqual(self.capture(**overrides).json()['detail']['code'], 'SOURCE_ASSOCIATION_ERROR')
        for overrides in [dict(session_id='../escape'), dict(expected_session_revision='invalid'), dict(config_index=-1), dict(config_index=True), dict(configuration='injected')]:
            self.assertEqual(self.capture(**overrides).status_code, 422)
        for corruption in ('duplicate_target', 'hostname', 'missing_text', 'device'):
            data = json.loads(self.raw)
            task = data['plan']['tasks'][0]
            if corruption == 'duplicate_target': task['target_devices'] *= 2
            if corruption == 'hostname': task['configs'][0]['hostname'] = 'wrong-device'
            if corruption == 'missing_text': task['configs'][0]['configuration'] = ''
            if corruption == 'device': task['device_id'] = 'dev-r2'
            self.path.write_bytes(json.dumps(data).encode())
            response = self.capture(expected_session_revision=sha256(self.path.read_bytes()).hexdigest())
            self.assertEqual(response.status_code, 409, response.text)
        self.assertFalse(originals.storage_root().exists())

    def test_metadata_uses_only_recorded_target_when_config_omits_it(self):
        self.session.plan.tasks[0].configs[0] = dict(device_id='dev-r1', configuration=self.text)
        save_session(self.session)
        response = self.capture(expected_session_revision=sha256(self.path.read_bytes()).hexdigest())
        self.assertEqual(response.status_code, 201, response.text)
        artifact = response.json()['artifact']
        self.assertEqual((artifact['hostname'], artifact['vendor'], artifact['platform']), ('R1', 'cisco', 'ios'))

    def test_missing_malformed_unsupported_session_and_artifact_ids(self):
        self.assertEqual(self.capture(session_id=str(uuid4())).status_code, 404)
        for raw in (b'{', b'[]', b'{"schema_version":1}'):
            self.path.write_bytes(raw)
            self.assertEqual(self.capture(expected_session_revision=sha256(raw).hexdigest()).status_code, 409)
        self.assertEqual(self.client.get(URL + '/wrong').status_code, 422)
        self.assertEqual(self.client.get(URL + '/original-' + '0' * 64).status_code, 404)

    def test_write_flush_and_publication_failures_leave_no_partial_records(self):
        for target in ('os.fsync', 'os.link'):
            with patch('app.workbench.generated_originals.' + target, side_effect=OSError('private-path')):
                response = self.capture()
                self.assertEqual(response.status_code, 503, response.text)
                self.assertNotIn('private-path', response.text)
            self.assertEqual(self.client.get(URL).json()['artifacts'], [])
            self.assertEqual(list(originals.storage_root().iterdir()), [])
        real_open = Path.open
        class BrokenStream:
            def __enter__(self): return self
            def __exit__(self, *args): self.stream.close()
            def write(self, raw): self.stream.write(raw[:10]); return 10
        def partial(path, *args, **kwargs):
            stream = real_open(path, *args, **kwargs)
            if args and args[0] == 'xb':
                wrapper = BrokenStream(); wrapper.stream = stream; return wrapper
            return stream
        with patch.object(Path, 'open', partial):
            self.assertEqual(self.capture().status_code, 503)
        self.assertEqual(list(originals.storage_root().iterdir()), [])
        self.assertEqual(self.path.read_bytes(), self.raw)

    def test_post_publication_failure_is_discoverable_not_overwritten(self):
        real_read = originals.read_original
        with patch.object(originals, 'read_original', side_effect=PlanningError(503, 'ARTIFACT_STORAGE_UNAVAILABLE', 'Uncertain')):
            self.assertEqual(self.capture().status_code, 503)
        listed = self.client.get(URL).json()['artifacts']
        self.assertEqual(len(listed), 1)
        record = real_read(listed[0]['artifact_id'])
        self.assertEqual(self.capture().json()['artifact'], record.model_dump(mode='json'))

    def test_flush_and_serialization_errors_never_publish(self):
        real_open = Path.open
        class FlushFailure:
            def __enter__(self): return self
            def __exit__(self, *args): self.stream.close()
            def write(self, raw): return self.stream.write(raw)
            def flush(self): raise OSError('flush failed')
        def broken_flush(path, *args, **kwargs):
            stream = real_open(path, *args, **kwargs)
            if args and args[0] == 'xb':
                wrapper = FlushFailure(); wrapper.stream = stream; return wrapper
            return stream
        with patch.object(Path, 'open', broken_flush):
            self.assertEqual(self.capture().status_code, 503)
        real_canonical = originals.canonical
        def broken_serialization(value):
            if 'captured_at' in value: raise ValueError('serialization failure')
            return real_canonical(value)
        with patch.object(originals, 'canonical', broken_serialization):
            self.assertEqual(self.capture().json()['detail']['code'], 'INVALID_ORIGINAL')
        self.assertEqual(list(originals.storage_root().iterdir()), [])
        self.assertEqual(self.path.read_bytes(), self.raw)

    def test_capture_never_calls_runtime_or_modifies_inventory(self):
        inventory = Path('data/inventory/devices.json')
        protected = inventory.read_bytes(), inventory.stat().st_mtime_ns
        targets = ['app.clarification.' + name for name in ('load_session', 'create_session', 'apply_answer', 'refresh_plan', 'save_session')]
        targets += ['app.pipeline.run', 'app.pipeline.render', 'app.vectorstore.get_vectorstore', 'socket.create_connection',
                    'subprocess.Popen', 'app.workbench.inventory_registration.register_device', 'os.replace']
        for target in targets:
            self.enterContext(patch(target, side_effect=AssertionError('Forbidden: ' + target)))
        self.assertEqual(self.capture().status_code, 201)
        self.assertEqual((inventory.read_bytes(), inventory.stat().st_mtime_ns), protected)
        self.assertEqual((self.path.read_bytes(), self.path.stat().st_mtime_ns), (self.raw, self.mtime))

    def test_damaged_collection_and_capacity_are_explicit(self):
        root = originals.storage_root()
        root.mkdir(parents=True)
        orphan = root / 'crash.tmp'
        orphan.write_bytes(b'partial')
        self.assertEqual(self.client.get(URL).json()['artifacts'], [])
        with patch.object(originals, 'MAX_ENTRIES', 0):
            self.assertEqual(self.client.get(URL).json()['detail']['code'], 'ARTIFACT_CAPACITY')
        (root / 'invalid.json').write_bytes(b'{}')
        self.assertEqual(self.client.get(URL).json()['detail']['code'], 'CORRUPT_ARTIFACT')
        self.assertEqual(orphan.read_bytes(), b'partial')

    def test_corrupt_records_and_identity_collisions_are_not_repaired(self):
        record = self.capture().json()['artifact']
        path = originals.storage_root() / (record['artifact_id'] + '.json')
        raw = path.read_bytes()
        for change in ('truncated', 'content', 'schema', 'id', 'provenance'):
            data = json.loads(raw)
            if change == 'content': data['configuration'] = 'tamper'
            if change == 'schema': data['schema_version'] = 99
            if change == 'id': data['source']['device_id'] = 'other'
            if change == 'provenance': data['vendor'] = 'invented'
            damaged = b'{' if change == 'truncated' else json.dumps(data).encode()
            path.write_bytes(damaged)
            for response in (self.client.get(URL), self.client.get(URL + '/' + record['artifact_id']), self.capture()):
                self.assertEqual(response.status_code, 409, response.text)
            self.assertEqual(path.read_bytes(), damaged)
        # Internally consistent record at the right identity but different content.
        data = json.loads(raw); data['configuration'] = 'different'
        data['content_sha256'] = sha256(b'different').hexdigest()
        data['record_sha256'] = sha256(originals.canonical({k: v for k, v in data.items() if k != 'record_sha256'})).hexdigest()
        path.write_bytes(originals.canonical(data))
        self.assertEqual(self.capture().json()['detail']['code'], 'ARTIFACT_IDENTITY_CONFLICT')

    def test_passive_reads_without_source_or_runtime_or_writes(self):
        artifact = self.capture().json()['artifact']
        path = originals.storage_root() / (artifact['artifact_id'] + '.json')
        before = path.read_bytes(), path.stat().st_mtime_ns
        targets = ['app.clarification.' + name for name in ('load_session', 'create_session', 'apply_answer', 'refresh_plan', 'save_session')]
        targets += ['app.pipeline.run', 'app.pipeline.render', 'app.vectorstore.get_vectorstore', 'socket.create_connection',
                    'app.workbench.generated_originals.get_saved_session', 'os.link', 'os.replace', 'pathlib.Path.write_bytes', 'pathlib.Path.write_text']
        for target in targets:
            self.enterContext(patch(target, side_effect=AssertionError('Forbidden: ' + target)))
        for route in (URL, URL + '/' + artifact['artifact_id']):
            result = self.client.get(route)
            self.assertEqual(result.status_code, 200, result.text)
            self.assertEqual(result.headers['cache-control'], 'no-store')
        self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)
        self.assertEqual((self.path.read_bytes(), self.path.stat().st_mtime_ns), (self.raw, self.mtime))

    def test_shared_gate_concurrent_capture_and_other_mutations(self):
        service = PlanningService()
        request = originals.CaptureRequest(**self.request)
        entered, release = Event(), Event()
        real_capture = originals.capture_original
        def slow(value):
            entered.set(); release.wait(5); return real_capture(value)
        with ThreadPoolExecutor(max_workers=2) as pool, patch.object(originals, 'capture_original', side_effect=slow):
            future = pool.submit(service.capture_original, request)
            self.assertTrue(entered.wait(5))
            try:
                with self.assertRaises(PlanningError) as error: service.capture_original(request)
                self.assertEqual(error.exception.status, 503)
                with self.assertRaises(PlanningError): service.register_inventory_device(None)
            finally: release.set()
            self.assertEqual(future.result().outcome, 'created')
        self.assertEqual(service.capture_original(request).outcome, 'already_saved')

    def test_bounds_and_no_overwrite_on_publication_race(self):
        with patch.object(originals, 'MAX_RECORD_BYTES', 10):
            self.assertEqual(self.capture().status_code, 413)
        with patch.object(originals, 'MAX_ENTRIES', 0):
            self.assertEqual(self.capture().json()['detail']['code'], 'ARTIFACT_CAPACITY')
        real_link = originals.os.link
        def raced(source, destination):
            real_link(source, destination)
            raise FileExistsError()
        with patch.object(originals.os, 'link', raced):
            response = self.capture()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['outcome'], 'already_saved')


if __name__ == '__main__':
    unittest.main()
