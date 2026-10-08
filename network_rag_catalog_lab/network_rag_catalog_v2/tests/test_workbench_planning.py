"""HTTP adapter tests: no Ollama, external infrastructure or persistent test sessions."""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.clarification import ClarificationSession, save_session, session_to_dict
from app.planner.models import ExecutionPlan, OperationIntent, PlannedTask
from app.workbench.api import create_app
from app.workbench.planning_models import PlanningRequest
from app.workbench.planning_service import PlanningService, PlanningError


class WorkbenchPlanningTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(self.enterContext(TemporaryDirectory(dir=Path.cwd())))
        self.enterContext(patch('app.clarification.SESSIONS_DIR', self.directory))
        self.enterContext(patch('app.config.SESSIONS_DIR', self.directory))
        self.enterContext(patch.dict(os.environ, {'NETWORK_RAG_RUNTIME': 'files'}))
        self.client = self.enterContext(TestClient(create_app()))
        self.request = {'prompt': 'Create VLAN 100 named STAFF on R1', 'mode': 'local_v9', 'client_request_id': str(uuid4())}

    def fixture(self, status='ready'):
        question = {'question_id': 'question-7', 'task_id': 'intent-1:dev-r1', 'field_path': 'vlan_name',
                    'revision': 3, 'source_revision': 'source', 'wording': 'Which VLAN name?',
                    'options': [{'option_id': 'option-1', 'value': 'STAFF'}]}
        task = PlannedTask('intent-1:dev-r1', self.request['prompt'], 'vlan', 'create_vlan', {'vlan_id': 100}, ['R1'],
                           status=status, device_id='dev-r1', revision=3, source_revision='source',
                           parameter_evidence={'vlan_id': {'source': 'user', 'validation': 'valid'}},
                           parameter_provenance={'vlan_id': 'user_literal'},
                           target_resolution=[{'selected': [{'device_id': 'dev-r1'}]}],
                           configs=[{'configuration': 'vlan 100', 'vendor': 'cisco'}] if status == 'ready' else [],
                           questions=[question] if status == 'needs_clarification' else [],
                           issues=[{'type': 'MISSING', 'field': 'vlan_name'}] if status == 'needs_clarification' else [],
                           runtime_authority='files', context_revision='context')
        session = ClarificationSession(str(uuid4()), 'created', 'updated', status,
                                       ExecutionPlan(self.request['prompt'], tasks=[task], status=status, runtime_authority='files'))
        save_session(session)
        return session

    def post(self, body=None):
        return self.client.post('/api/v1/planning/sessions', json=body or self.request)

    def test_serialization_is_lossless_and_revision_matches_saved_bytes(self):
        session = self.fixture()
        with patch('app.clarification.create_session', return_value=session) as create:
            response = self.post()
        self.assertEqual(response.status_code, 200, response.text)
        create.assert_called_once_with(self.request['prompt'], verbose=False)
        body = response.json()
        self.assertEqual(body['session'], session_to_dict(session))
        self.assertEqual(body['session_revision'], sha256((self.directory / f'{session.session_id}.json').read_bytes()).hexdigest())
        self.assertEqual(body['mode'], 'local_v9')
        self.assertEqual(body['client_request_id'], self.request['client_request_id'])

    def test_pending_questions_keep_ids_options_and_issues(self):
        session = self.fixture('needs_clarification')
        with patch('app.clarification.create_session', return_value=session):
            body = self.post().json()['session']
        self.assertEqual(body, session_to_dict(session))
        self.assertEqual(body['pending_questions'][0]['question_id'], 'question-7')

    def test_invalid_requests_never_call_v9(self):
        with patch('app.clarification.create_session') as create:
            for changes in ({'prompt': '  '}, {'prompt': 'x' * 8001}, {'prompt': 123},
                            {'client_request_id': 'bad-id'}, {'mode': 'demo'}, {'answer': 'unallowed'}):
                self.assertEqual(self.post({**self.request, **changes}).status_code, 422)
            create.assert_not_called()

    def test_model_failure_is_sanitized_and_retries_do_not_repeat_work(self):
        with patch('app.clarification.create_session', side_effect=ConnectionError('secret upstream details')) as create:
            first, second = self.post(), self.post()
        self.assertEqual(first.status_code, 503)
        self.assertEqual(first.json()['detail']['code'], 'LOCAL_SERVICE_UNAVAILABLE')
        self.assertEqual(first.json(), second.json())
        self.assertNotIn('secret', first.text)
        self.assertEqual(create.call_count, 1)

    def test_planning_failure_is_not_a_successful_mock(self):
        with patch('app.clarification.create_session', side_effect=ValueError('RAG index mismatch')):
            response = self.post()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()['detail']['code'], 'V9_PLANNING_FAILED')
        self.assertNotIn('session', response.json())

    def test_duplicate_result_and_conflicting_id(self):
        with patch('app.clarification.create_session', return_value=self.fixture()) as create:
            first, second = self.post(), self.post()
            conflict = self.post({**self.request, 'prompt': 'Different prompt'})
        self.assertEqual(first.json(), second.json())
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(create.call_count, 1)

    def test_v9_caught_retrieval_failure_remains_honest_clarification(self):
        intent = OperationIntent('intent-1', 'Provision something on R1', target_refs=['R1'], target_text='R1')
        with patch('app.pipeline.plan_intents', return_value=[intent]), \
                patch('app.pipeline._explicit_operation', return_value=None), \
                patch('app.pipeline.classify_category', return_value='vlan'), \
                patch('app.pipeline.retrieve_operation_candidates', side_effect=ConnectionError('retrieval unavailable')):
            response = self.post()
        self.assertEqual(response.status_code, 200, response.text)
        session = response.json()['session']
        self.assertEqual(session['status'], 'needs_clarification')
        self.assertIn('retrieval unavailable', session['plan']['tasks'][0]['feedback'])
        self.assertFalse(session['plan']['tasks'][0]['configs'])
        self.assertTrue(session['pending_questions'])

    def test_busy_gate_and_health_remain_responsive(self):
        started, release = Event(), Event()
        session = self.fixture()
        def slow_create(*args, **kwargs):
            started.set()
            if not release.wait(10):
                raise TimeoutError('test deadline')
            return session
        with patch('app.clarification.create_session', side_effect=slow_create), ThreadPoolExecutor() as pool:
            pending = pool.submit(self.post)
            try:
                self.assertTrue(started.wait(5))
                self.assertEqual(self.post().json()['detail']['code'], 'REQUEST_IN_PROGRESS')
                other = self.post({**self.request, 'client_request_id': str(uuid4())})
                self.assertEqual(other.json()['detail']['code'], 'PLANNER_BUSY')
                self.assertEqual(self.client.get('/api/v1/health').status_code, 200)
                self.assertEqual(self.client.get('/api/v1/runtime/status').status_code, 200)
            finally:
                release.set()
            self.assertEqual(pending.result().status_code, 200)

    def test_retention_capacity_does_not_evict_prior_ids(self):
        service = PlanningService()
        service._requests = {str(uuid4()): ('prior', None) for _ in range(256)}
        with self.assertRaises(PlanningError) as caught:
            service.create(PlanningRequest(**self.request))
        self.assertEqual(caught.exception.code, 'REQUEST_CAPACITY')

    def test_real_v9_creation_and_persistence_without_device_execution(self):
        for target in ('app.llm.llm', 'app.planner.intent_planner.llm', 'app.parameters.parameter_extractor.llm'):
            self.enterContext(patch(target)).invoke.return_value.content = 'null'
        with patch('subprocess.Popen', side_effect=AssertionError('No execution permitted')), \
                patch('socket.create_connection', side_effect=AssertionError('No device connections permitted')):
            response = self.post()
        self.assertEqual(response.status_code, 200, response.text)
        session = response.json()['session']
        self.assertEqual(session['status'], 'ready')
        self.assertEqual(session['plan']['tasks'][0]['device_id'], 'dev-r1')
        self.assertIn('vlan 100', session['plan']['tasks'][0]['configs'][0]['configuration'])
        saved = json.loads((self.directory / f"{session['session_id']}.json").read_text())
        self.assertEqual(saved, session)
        self.assertEqual(len(list(self.directory.glob('*.json'))), 1)

    def test_only_session_creation_mutation_is_exposed(self):
        schema = self.client.get('/api/openapi.json').json()
        mutations = [(path, method) for path, methods in schema['paths'].items() for method in methods if method in {'post', 'put', 'patch', 'delete'}]
        self.assertEqual(mutations, [('/api/v1/planning/sessions', 'post')])


if __name__ == '__main__':
    unittest.main()
