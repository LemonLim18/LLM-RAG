"""Durable creation outcomes with real V9 saves and deterministic failure injection."""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import builtins
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
from app.planner.models import ExecutionPlan
from app.workbench.api import create_app
from app.workbench import creation_receipts as receipts
from app.workbench.planning_models import PlanningRequest
from app.workbench.planning_service import PlanningService


class SimulatedCrash(BaseException):
    pass


class CreationReceiptTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(self.enterContext(TemporaryDirectory(dir=Path.cwd())))
        self.enterContext(patch('app.config.SESSIONS_DIR', self.directory))
        self.enterContext(patch('app.clarification.SESSIONS_DIR', self.directory))
        self.client = self.enterContext(TestClient(create_app()))
        self.request = {'prompt': 'Create VLAN 100 on R1', 'mode': 'local_v9', 'client_request_id': str(uuid4())}
        self.calls = 0

    def create(self, prompt, *, verbose=False):
        self.calls += 1
        session = ClarificationSession(str(uuid4()), 'created', 'updated', 'ready',
                                       ExecutionPlan(prompt, status='ready', runtime_authority='files'))
        save_session(session)
        return session

    def post(self, client=None, **changes):
        return (client or self.client).post('/api/v1/planning/sessions', json={**self.request, **changes})

    def lookup(self, client=None):
        return (client or self.client).get('/api/v1/planning/requests/' + self.request['client_request_id'])

    def test_completed_survives_fresh_app_and_fresh_interpreter_without_importing_ai(self):
        with patch('app.clarification.create_session', side_effect=self.create):
            created = self.post()
            self.assertEqual(created.status_code, 200, created.text)
            with TestClient(create_app()) as fresh:
                self.assertEqual(self.post(fresh).json(), created.json())
                outcome = self.lookup(fresh)
        self.assertEqual(self.calls, 1)
        self.assertEqual(outcome.headers['cache-control'], 'no-store')
        self.assertEqual(outcome.json()['session_id'], created.json()['session']['session_id'])
        receipt = receipts.read_receipt(self.request['client_request_id'])
        self.assertEqual(receipt.fingerprint, receipts.request_fingerprint(self.request['prompt'], 'local_v9'))
        self.assertNotIn(self.request['prompt'], receipts.receipt_path(receipt.client_request_id).read_text())
        script = '''
import sys
from pathlib import Path
import app.config
app.config.SESSIONS_DIR = Path(sys.argv[1])
from fastapi.testclient import TestClient
from app.workbench.api import create_app
with TestClient(create_app()) as client:
    response = client.get('/api/v1/planning/requests/' + sys.argv[2])
    assert response.status_code == 200, response.text
    assert response.json()['status'] == 'completed', response.text
assert not any(m in sys.modules for m in ('app.clarification', 'app.pipeline', 'app.llm', 'ollama'))
'''
        result = subprocess.run([sys.executable, '-c', script, str(self.directory), self.request['client_request_id']],
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_identity_conflict_invalid_mode_and_actual_saved_consistency(self):
        with patch('app.clarification.create_session', side_effect=self.create):
            created = self.post().json()
            with TestClient(create_app()) as fresh:
                self.assertEqual(self.post(fresh, prompt='Different request').status_code, 409)
                self.assertEqual(self.post(fresh, mode='demo').status_code, 422)
            path = self.directory / (created['session']['session_id'] + '.json')
            data = json.loads(path.read_bytes())
            data['plan']['original_prompt'] = 'Different request'
            path.write_text(json.dumps(data), encoding='utf-8')
            self.assertEqual(self.lookup().json()['status'], 'corrupt')
            self.assertEqual(self.post().status_code, 409)
        self.assertEqual(self.calls, 1)

    def test_unknown_and_invalid_id_are_passive(self):
        self.assertEqual(self.lookup().json()['status'], 'unknown')
        self.assertEqual(self.client.get('/api/v1/planning/requests/not-a-uuid').status_code, 422)
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_storage_failure_before_acceptance_never_invokes_v9(self):
        with patch('app.workbench.creation_receipts.os.replace', side_effect=OSError('private path')), \
                patch('app.clarification.create_session') as create:
            response = self.post()
            create.assert_not_called()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('private path', response.text)
        self.assertEqual(self.lookup().json()['status'], 'unknown')

    def test_crash_after_acceptance_before_invocation_blocks_restart_replay(self):
        original = builtins.__import__
        def interrupted(name, *args, **kwargs):
            if name == 'app.clarification':
                raise SimulatedCrash()
            return original(name, *args, **kwargs)
        service = PlanningService()
        with patch('builtins.__import__', side_effect=interrupted), self.assertRaises(SimulatedCrash):
            service.create(PlanningRequest(**self.request))
        self.assert_restart_indeterminate()
        self.assertEqual(list(self.directory.glob('*.json')), [])

    def assert_restart_indeterminate(self):
        with TestClient(create_app()) as fresh, patch('app.clarification.create_session') as create:
            self.assertEqual(self.lookup(fresh).json()['status'], 'indeterminate')
            self.assertEqual(self.post(fresh).json()['detail']['code'], 'CREATION_INDETERMINATE')
            create.assert_not_called()

    def test_failure_during_v9_retains_uncertainty_not_false_terminal_failure(self):
        with patch('app.clarification.create_session', side_effect=ConnectionError('upstream secret')):
            self.assertEqual(self.post().status_code, 503)
        self.assertEqual(self.lookup().json()['status'], 'indeterminate')
        self.assert_restart_indeterminate()

    def test_post_save_pre_receipt_crash_never_creates_a_second_session(self):
        real_write = receipts.write_receipt
        def interrupted(receipt, **kwargs):
            if receipt.status == 'completed':
                raise SimulatedCrash()
            return real_write(receipt, **kwargs)
        with patch('app.workbench.creation_receipts.write_receipt', side_effect=interrupted), \
                patch('app.clarification.create_session', side_effect=self.create), self.assertRaises(SimulatedCrash):
            PlanningService().create(PlanningRequest(**self.request))
        self.assertEqual(self.calls, 1)
        self.assertEqual(len(list(self.directory.glob('*.json'))), 1)
        self.assert_restart_indeterminate()

    def test_failed_completed_publication_retains_accepted_receipt(self):
        real_replace = receipts.os.replace
        def fail_completion(source, destination):
            if json.loads(Path(source).read_bytes())['status'] == 'completed':
                raise OSError('disk failure')
            return real_replace(source, destination)
        with patch('app.workbench.creation_receipts.os.replace', side_effect=fail_completion), \
                patch('app.clarification.create_session', side_effect=self.create):
            self.assertEqual(self.post().status_code, 503)
        self.assertEqual(receipts.read_receipt(self.request['client_request_id']).status, 'accepted')
        self.assertEqual(len(list(self.directory.glob('*.json'))), 1)
        self.assert_restart_indeterminate()

    def test_safely_established_pre_invocation_error_is_terminal(self):
        original = builtins.__import__
        def unavailable(name, *args, **kwargs):
            if name == 'app.clarification':
                raise ImportError('private information')
            return original(name, *args, **kwargs)
        with patch('builtins.__import__', side_effect=unavailable):
            self.assertEqual(self.post().status_code, 503)
        with TestClient(create_app()) as fresh, patch('app.clarification.create_session') as create:
            self.assertEqual(self.lookup(fresh).json()['status'], 'terminal_error')
            self.assertEqual(self.post(fresh).status_code, 503)
            create.assert_not_called()

    def test_current_process_in_progress_is_not_a_restart_success(self):
        started, release = Event(), Event()
        def slow(prompt, **kwargs):
            started.set()
            if not release.wait(10):
                raise TimeoutError()
            return self.create(prompt, **kwargs)
        with patch('app.clarification.create_session', side_effect=slow), ThreadPoolExecutor() as pool:
            future = pool.submit(self.post)
            try:
                self.assertTrue(started.wait(5))
                self.assertEqual(self.lookup().json()['status'], 'in_progress')
                self.assertEqual(self.post().json()['detail']['code'], 'REQUEST_IN_PROGRESS')
                with TestClient(create_app()) as other:
                    self.assertEqual(self.lookup(other).json()['status'], 'indeterminate')
            finally:
                release.set()
            self.assertEqual(future.result().status_code, 200)

    def test_corrupt_bounded_receipts_and_missing_saved_session_never_replay(self):
        with patch('app.clarification.create_session', side_effect=self.create):
            created = self.post().json()
        path = receipts.receipt_path(self.request['client_request_id'])
        original = path.read_bytes()
        data = json.loads(original)
        for content in (b'{', b' ' * 4097, b'[' * 1100 + b']' * 1100, b'{"version":1,"version":1}',
                        json.dumps({**data, 'client_request_id': str(uuid4())}).encode(),
                        json.dumps({**data, 'version': 2}).encode(),
                        json.dumps({**data, 'status': 'accepted'}).encode()):
            with self.subTest(content=content[:80]):
                path.write_bytes(content)
                with patch('app.clarification.create_session') as create:
                    self.assertEqual(self.lookup().json()['status'], 'corrupt')
                    self.assertEqual(self.post().status_code, 409)
                    create.assert_not_called()
        path.write_bytes(original)
        (self.directory / (created['session']['session_id'] + '.json')).unlink()
        self.assertEqual(self.lookup().json()['status'], 'corrupt')

    def test_passive_lookup_uses_latest_saved_bytes_and_never_writes_or_executes(self):
        with patch('app.clarification.create_session', side_effect=self.create):
            created = self.post().json()
        path = self.directory / (created['session']['session_id'] + '.json')
        data = json.loads(path.read_bytes())
        data['updated_at'] = 'later-answer'
        data['plan']['runtime_authority'] = 'historical-authority'
        path.write_text(json.dumps(data, indent=3), encoding='utf-8')
        files = [path, receipts.receipt_path(self.request['client_request_id'])]
        before = [(file.read_bytes(), file.stat().st_mtime_ns) for file in files]
        for target in ('app.clarification.create_session', 'app.clarification.load_session',
                       'app.clarification.save_session', 'app.clarification.apply_answer',
                       'app.pipeline.refresh_plan', 'subprocess.Popen', 'socket.create_connection'):
            self.enterContext(patch(target, side_effect=AssertionError('Passive lookup only')))
        outcome = self.lookup().json()
        self.assertEqual(outcome['status'], 'completed')
        self.assertEqual(outcome['session_revision'], sha256(path.read_bytes()).hexdigest())
        self.assertEqual(before, [(file.read_bytes(), file.stat().st_mtime_ns) for file in files])

    def test_storage_capacity_refuses_new_work_without_eviction(self):
        with patch('app.workbench.creation_receipts.MAX_RECEIPTS', 0), patch('app.clarification.create_session') as create:
            response = self.post()
            self.assertEqual(response.json()['detail']['code'], 'RECEIPT_CAPACITY')
            create.assert_not_called()
        self.assertEqual(self.lookup().json()['status'], 'unknown')

    def test_cached_success_cannot_override_lost_receipt(self):
        with patch('app.clarification.create_session', side_effect=self.create):
            self.assertEqual(self.post().status_code, 200)
            receipts.receipt_path(self.request['client_request_id']).unlink()
            self.assertEqual(self.lookup().json()['status'], 'unknown')
            self.assertEqual(self.post().json()['detail']['code'], 'RECEIPT_INCONSISTENT')
        self.assertEqual(self.calls, 1)

    def test_storage_errors_and_receipt_path_escape_are_sanitized(self):
        original = Path.resolve
        def escaped(path, *args, **kwargs):
            if path.name == '.creation_requests':
                return self.directory.parent / 'outside'
            return original(path, *args, **kwargs)
        with patch.object(Path, 'resolve', escaped):
            self.assertEqual(self.lookup().json()['status'], 'corrupt')
        with patch.object(Path, 'open', side_effect=PermissionError('private path')):
            response = self.lookup()
            self.assertEqual(response.status_code, 503)
            self.assertNotIn('private path', response.text)


if __name__ == '__main__':
    unittest.main()
