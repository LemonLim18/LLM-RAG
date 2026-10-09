"""Passive reads of real V9 persistence, including fresh interpreter recovery."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from app.clarification import ClarificationSession, save_session, session_to_dict
from app.planner.models import ExecutionPlan, PlannedTask
from app.workbench.api import create_app


class WorkbenchRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(self.enterContext(TemporaryDirectory(dir=Path.cwd())))
        for module in ('app.config', 'app.clarification'):
            self.enterContext(patch(module + '.SESSIONS_DIR', self.directory))
        self.session_id = str(uuid4())
        question = dict(question_id='q-original', task_id='task-original', field_path='area',
                        revision=3, source_revision='historical-source', wording='Which area?',
                        options=[], allow_custom=True, multiple=False, expected_schema={'type': 'string'})
        task = PlannedTask('task-original', 'Configure OSPF', 'routing', 'configure_ospf', {}, ['R3'],
                           status='needs_clarification', questions=[question], revision=3,
                           logical_intent_id='intent-original', parameter_evidence={'area': {'source': 'user'}},
                           issues=[{'type': 'MISSING', 'field': 'area'}])
        self.session = ClarificationSession(self.session_id, 'created', 'updated', 'needs_clarification',
            ExecutionPlan('Configure OSPF', tasks=[task], status='needs_clarification',
                          runtime_authority='published', knowledge_snapshot_id='historical-release',
                          source_revision='historical-source', context_revision='old-inventory'),
            history=[{'type': 'request', 'text': 'Configure OSPF'}])
        save_session(self.session)
        self.path = self.directory / f'{self.session_id}.json'
        self.url = f'/api/v1/planning/sessions/{self.session_id}'
        self.client = self.enterContext(TestClient(create_app()))

    def test_exact_content_hash_timestamps_and_no_runtime_calls(self):
        before, modified = self.path.read_bytes(), self.path.stat().st_mtime_ns
        targets = ['app.clarification.' + name for name in
                   ('load_session', 'create_session', 'apply_answer', 'refresh_plan', 'save_session')]
        targets += ['app.pipeline.render', 'app.pipeline.run', 'langchain_ollama.ChatOllama.invoke',
                    'app.vectorstore.get_vectorstore', 'app.context.source_revision',
                    'app.context.context_revision', 'subprocess.Popen', 'socket.create_connection',
                    'pathlib.Path.write_bytes', 'pathlib.Path.write_text', 'pathlib.Path.replace']
        for target in targets:
            self.enterContext(patch(target, side_effect=AssertionError('Passive GET used ' + target)))
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body['session'], json.loads(before))
        self.assertEqual(body['session_revision'], sha256(before).hexdigest())
        self.assertEqual(body['freshness'], 'not_checked')
        self.assertEqual(body['mutation_eligibility'], 'not_checked')
        self.assertNotIn('client_request_id', body)
        self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.path.stat().st_mtime_ns, modified)

    def test_historical_ready_output_is_preserved_without_revalidation(self):
        self.session.status = self.session.plan.status = 'ready'
        task = self.session.plan.tasks[0]
        task.status, task.questions = 'rendered', []
        task.configs = [{'device_id': 'dev-r3', 'configuration': 'set protocols ospf area 0 interface ge-0/0/0'}]
        save_session(self.session)
        body = self.client.get(self.url).json()
        self.assertEqual(body['session'], session_to_dict(self.session))
        self.assertEqual(body['session']['plan']['knowledge_snapshot_id'], 'historical-release')
        self.assertEqual(body['freshness'], 'not_checked')

    def test_invalid_ids_and_missing_files(self):
        for identity in ('not-a-uuid', '123', '%2e%2e%2fsecret'):
            self.assertIn(self.client.get('/api/v1/planning/sessions/' + identity).status_code, (404, 422))
        response = self.client.get('/api/v1/planning/sessions/' + str(uuid4()))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['detail']['code'], 'SESSION_NOT_FOUND')

    def test_malformed_unsupported_and_inconsistent_payloads_are_not_rewritten(self):
        original = session_to_dict(self.session)
        cases = [b'{', b'[]', b'{"x":1,"x":2}', b'{"bad": NaN}']
        for change in ('version', 'identity', 'extra', 'pending', 'task', 'status', 'question'):
            data = deepcopy(original)
            if change == 'version': data['schema_version'] = 1
            if change == 'identity': data['session_id'] = str(uuid4())
            if change == 'extra': data['plan']['tasks'][0]['unknown_field'] = True
            if change == 'pending': data['pending_questions'] = []
            if change == 'task': data['plan']['tasks'].append(deepcopy(data['plan']['tasks'][0]))
            if change == 'status': data['status'] = 'ready'
            if change == 'question': data['plan']['tasks'][0]['questions'][0]['task_id'] = 'other'
            cases.append(json.dumps(data).encode())
        for raw in cases:
            with self.subTest(raw=raw[:80]):
                self.path.write_bytes(raw)
                modified = self.path.stat().st_mtime_ns
                response = self.client.get(self.url)
                self.assertEqual(response.status_code, 409, response.text)
                self.assertIn(response.json()['detail']['code'], ('INVALID_SAVED_SESSION', 'UNSUPPORTED_SESSION_VERSION'))
                self.assertEqual(raw, self.path.read_bytes())
                self.assertEqual(modified, self.path.stat().st_mtime_ns)
                self.assertNotIn(str(self.directory), response.text)

    def test_storage_error_is_sanitized(self):
        with patch('pathlib.Path.read_bytes', side_effect=PermissionError('private secret path')):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('private secret', response.text)

    def test_path_escape_is_rejected_before_read(self):
        with patch('pathlib.Path.resolve', side_effect=[self.directory, self.directory.parent / 'outside.json']), \
                patch('pathlib.Path.read_bytes') as read:
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 409)
        read.assert_not_called()

    def test_byte_revision_is_for_the_snapshot_not_a_second_read(self):
        raw = self.path.read_bytes()
        with patch('pathlib.Path.read_bytes', side_effect=[raw, b'changed']) as read:
            response = self.client.get(self.url)
        self.assertEqual(response.json()['session_revision'], sha256(raw).hexdigest())
        read.assert_called_once()

    def test_fresh_process_reads_same_storage_without_importing_ai_runtime(self):
        script = '''
import json, sys
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.workbench.api import create_app
with patch('app.config.SESSIONS_DIR', Path(sys.argv[1])):
    with TestClient(create_app()) as client:
        response = client.get('/api/v1/planning/sessions/' + sys.argv[2])
        assert response.status_code == 200, response.text
        print(response.text)
assert not {'app.clarification', 'app.pipeline', 'app.llm', 'app.embeddings', 'app.vectorstore'} & sys.modules.keys()
'''
        before = self.path.read_bytes()
        completed = subprocess.run([sys.executable, '-c', script, str(self.directory), self.session_id],
                                   capture_output=True, text=True, timeout=30)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        body = json.loads(completed.stdout)
        self.assertEqual(body['session'], json.loads(before))
        self.assertEqual(body['session_revision'], sha256(before).hexdigest())


if __name__ == '__main__':
    unittest.main()
