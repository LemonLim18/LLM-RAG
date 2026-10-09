"""Real V9 answer semantics behind HTTP, with deterministic model doubles only."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
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
from app.clarification import apply_answer
from app.workbench.api import create_app


class WorkbenchAnswerTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(self.enterContext(TemporaryDirectory(dir=Path.cwd())))
        for module in ('app.clarification', 'app.config'):
            self.enterContext(patch(module + '.SESSIONS_DIR', self.directory))
        self.enterContext(patch.dict(os.environ, {'NETWORK_RAG_RUNTIME': 'files'}))
        for target in ('app.llm.llm', 'app.planner.intent_planner.llm', 'app.parameters.parameter_extractor.llm'):
            self.enterContext(patch(target)).invoke.return_value.content = 'null'
        self.client = self.enterContext(TestClient(create_app()))
        self.result = self.create('Create VLAN named STAFF on R1')
        self.session_id = self.result['session']['session_id']
        self.path = self.directory / f'{self.session_id}.json'
        self.url = f'/api/v1/planning/sessions/{self.session_id}/answers'
        self.question = self.result['session']['pending_questions'][0]
        self.request = self.request_for(self.result, '100')

    def create(self, prompt):
        response = self.client.post('/api/v1/planning/sessions', json={
            'prompt': prompt, 'mode': 'local_v9', 'client_request_id': str(uuid4())})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def request_for(self, result, text):
        question = result['session']['pending_questions'][0]
        return {'client_request_id': str(uuid4()), 'expected_session_revision': result['session_revision'],
                'answer': {'question_id': question['question_id'], 'revision': question['revision'],
                           'source_revision': question['source_revision'], 'kind': 'custom',
                           'raw_input': text, 'selected_ids': []}}

    def post(self, request=None):
        return self.client.post(self.url, json=request or self.request)

    def test_custom_answer_preserves_identity_and_advances_saved_revision(self):
        with patch('app.clarification.load_session', side_effect=AssertionError('No refreshing reads')), \
                patch('app.clarification.apply_answer', wraps=apply_answer) as applied:
            response = self.post()
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertTrue(result['accepted'])
        self.assertEqual(applied.call_count, 1)
        self.assertEqual(result['answered_question_id'], self.question['question_id'])
        self.assertEqual(result['session']['session_id'], self.session_id)
        self.assertEqual(result['session']['plan']['tasks'][0]['intent_id'], self.result['session']['plan']['tasks'][0]['intent_id'])
        self.assertEqual(result['session']['status'], 'ready')
        self.assertEqual(result['session']['plan']['tasks'][0]['parameters']['vlan_id'], 100)
        self.assertNotEqual(result['session_revision'], self.result['session_revision'])
        self.assertEqual(result['session_revision'], sha256(self.path.read_bytes()).hexdigest())
        self.assertEqual(result['session'], json.loads(self.path.read_bytes()))

    def test_selection_uses_stable_option_and_preserves_next_question(self):
        result = self.create('Configure OSPF on R3')
        question = result['session']['pending_questions'][0]
        self.assertTrue(question['options'])
        request = self.request_for(result, '')
        option = question['options'][0]
        request['answer'].update(kind='selection', selected_ids=[option['option_id']])
        response = self.client.post(f"/api/v1/planning/sessions/{result['session']['session_id']}/answers", json=request)
        self.assertEqual(response.status_code, 200, response.text)
        updated = response.json()['session']
        self.assertEqual(updated['session_id'], result['session']['session_id'])
        self.assertTrue(updated['pending_questions'])
        history = updated['plan']['tasks'][0]['clarification_history'][-1]
        self.assertEqual(history['answer']['selected_ids'], [option['option_id']])
        self.assertTrue(history['accepted'])

    def test_stale_saved_revision_does_not_load_refresh_or_write(self):
        before = self.path.read_bytes()
        request = {**self.request, 'expected_session_revision': '0' * 64}
        with patch('app.clarification.apply_answer') as applied, patch('app.clarification.load_session') as loaded:
            response = self.post(request)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['detail']['code'], 'STALE_SESSION')
        applied.assert_not_called()
        loaded.assert_not_called()
        self.assertEqual(before, self.path.read_bytes())

    def test_unknown_question_and_stale_question_revision(self):
        for changes, code in [({'question_id': 'unknown'}, 'QUESTION_NOT_CURRENT'),
                              ({'revision': 99}, 'STALE_QUESTION'), ({'source_revision': 'old'}, 'STALE_QUESTION')]:
            request = deepcopy(self.request)
            request['client_request_id'] = str(uuid4())
            request['answer'].update(changes)
            self.assertEqual(self.post(request).json()['detail']['code'], code)

    def test_invalid_options_types_and_mixed_answers(self):
        before = self.path.read_bytes()
        for changes in ({'kind': 'selection', 'raw_input': '', 'selected_ids': ['invented']},
                        {'kind': 'selection', 'raw_input': '', 'selected_ids': ['same', 'same']},
                        {'kind': 'bogus'}, {'selected_ids': ['option']}, {'raw_input': '  '}):
            request = deepcopy(self.request)
            request['client_request_id'] = str(uuid4())
            request['answer'].update(changes)
            self.assertEqual(self.post(request).status_code, 422)
        self.assertEqual(before, self.path.read_bytes())

    def test_duplicate_and_conflict_do_not_apply_twice(self):
        with patch('app.clarification.apply_answer', wraps=apply_answer) as applied:
            first, second = self.post(), self.post()
            changed = deepcopy(self.request)
            changed['answer']['raw_input'] = 'OTHER'
            conflict = self.post(changed)
        self.assertEqual(first.json(), second.json())
        self.assertEqual(conflict.json()['detail']['code'], 'REQUEST_ID_CONFLICT')
        self.assertEqual(applied.call_count, 1)
        stale = {**self.request, 'client_request_id': str(uuid4())}
        self.assertEqual(self.post(stale).json()['detail']['code'], 'STALE_SESSION')

    def test_missing_ineligible_and_malformed_session(self):
        self.assertEqual(self.client.post(f'/api/v1/planning/sessions/{uuid4()}/answers', json=self.request).status_code, 404)
        self.assertEqual(self.client.post('/api/v1/planning/sessions/not-a-uuid/answers', json=self.request).status_code, 422)
        ready = self.create('Create VLAN 100 named STAFF on R1')
        request = {**self.request, 'expected_session_revision': ready['session_revision'], 'client_request_id': str(uuid4())}
        response = self.client.post(f"/api/v1/planning/sessions/{ready['session']['session_id']}/answers", json=request)
        self.assertEqual(response.json()['detail']['code'], 'SESSION_NOT_ANSWERABLE')

    def test_source_change_is_rejected_without_refresh(self):
        before = self.path.read_bytes()
        with patch('app.context.source_revision', return_value='changed'), patch('app.clarification.apply_answer') as applied:
            response = self.post()
        self.assertEqual(response.json()['detail']['code'], 'STALE_SOURCE')
        self.assertEqual(before, self.path.read_bytes())
        applied.assert_not_called()

    def test_v9_rejection_returns_saved_feedback_and_new_revision(self):
        result = self.create('Create VLAN named STAFF on R1')
        request = self.request_for(result, '99999')
        response = self.client.post(f"/api/v1/planning/sessions/{result['session']['session_id']}/answers", json=request)
        self.assertEqual(response.status_code, 422, response.text)
        detail = response.json()['detail']
        self.assertEqual(detail['code'], 'V9_ANSWER_REJECTED')
        updated = detail['current_session']
        self.assertNotEqual(updated['session_revision'], result['session_revision'])
        self.assertFalse(updated['session']['history'][-1]['accepted'])
        self.assertFalse(updated['session']['plan']['tasks'][0]['configs'])
        self.assertNotEqual(updated['session']['plan']['tasks'][0]['parameters'].get('vlan_id'), 99999)

    def test_persistence_failure_is_not_reported_as_acceptance_or_retried(self):
        before = self.path.read_bytes()
        with patch('app.clarification.save_session', side_effect=OSError('disk error')) as saved:
            first, second = self.post(), self.post()
        self.assertEqual(first.status_code, 500)
        self.assertEqual(first.json(), second.json())
        self.assertEqual(saved.call_count, 1)
        self.assertEqual(before, self.path.read_bytes())

    def test_shared_gate_blocks_creation_and_other_answers(self):
        started, release = Event(), Event()
        def slow_apply(*args):
            started.set()
            if not release.wait(10):
                raise TimeoutError()
            return apply_answer(*args)
        with patch('app.clarification.apply_answer', side_effect=slow_apply), ThreadPoolExecutor() as pool:
            pending = pool.submit(self.post)
            try:
                self.assertTrue(started.wait(5))
                self.assertEqual(self.post().json()['detail']['code'], 'REQUEST_IN_PROGRESS')
                other = {**self.request, 'client_request_id': str(uuid4())}
                self.assertEqual(self.post(other).json()['detail']['code'], 'PLANNER_BUSY')
                creation = self.client.post('/api/v1/planning/sessions', json={
                    'prompt': 'Create VLAN 100 on R1', 'mode': 'local_v9', 'client_request_id': str(uuid4())})
                self.assertEqual(creation.json()['detail']['code'], 'PLANNER_BUSY')
                self.assertEqual(self.client.get('/api/v1/health').status_code, 200)
            finally:
                release.set()
            self.assertEqual(pending.result().status_code, 200)

    def test_no_execution_or_catalog_mutation(self):
        protected = [Path('data/inventory/devices.json'), Path('data/catalog/operations.json')]
        before = [path.read_bytes() for path in protected]
        with patch('subprocess.Popen', side_effect=AssertionError('execution')), \
                patch('socket.create_connection', side_effect=AssertionError('connection')):
            self.assertEqual(self.post().status_code, 200)
        self.assertEqual(before, [path.read_bytes() for path in protected])

    def test_lossy_or_legacy_restoration_is_rejected_without_rewrite(self):
        for mode in ('extra', 'legacy'):
            data = deepcopy(self.result['session'])
            if mode == 'extra':
                data['plan']['tasks'][0]['unknown_future_field'] = 'must not discard'
            else:
                data['schema_version'] = 1
            self.path.write_text(json.dumps(data), encoding='utf-8')
            before = self.path.read_bytes()
            request = {**self.request, 'client_request_id': str(uuid4()),
                       'expected_session_revision': sha256(before).hexdigest()}
            with patch('app.clarification.apply_answer') as applied:
                response = self.post(request)
            self.assertEqual(response.status_code, 409, response.text)
            self.assertEqual(before, self.path.read_bytes())
            applied.assert_not_called()

    def test_creation_gate_also_blocks_answer(self):
        started, release = Event(), Event()
        from app.clarification import create_session
        def slow_create(*args, **kwargs):
            started.set()
            if not release.wait(10):
                raise TimeoutError()
            return create_session(*args, **kwargs)
        with patch('app.clarification.create_session', side_effect=slow_create), ThreadPoolExecutor() as pool:
            pending = pool.submit(self.create, 'Create VLAN 100 named STAFF on R1')
            try:
                self.assertTrue(started.wait(5))
                self.assertEqual(self.post().json()['detail']['code'], 'PLANNER_BUSY')
            finally:
                release.set()
            pending.result()

    def test_model_failure_during_answer_is_an_error_and_leaves_saved_state(self):
        before = self.path.read_bytes()
        with patch('app.clarification.apply_answer', side_effect=ConnectionError('upstream secret')):
            response = self.post()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('upstream secret', response.text)
        self.assertEqual(before, self.path.read_bytes())


if __name__ == '__main__':
    unittest.main()
