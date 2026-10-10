"""Real production adapter/catalog/rendering, controlled interpretation, isolated stores."""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from threading import Event
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4
from app import document_edits as edits
from app.clarification import save_session
from app.devices.inventory import load_inventory
from app.workbench import working_documents as working
from app.workbench import generated_originals as originals
from tests import test_workbench_originals as original_tests

URL = '/api/v1/workbench/working-documents'
TEXT = '! retained header\nvlan 20\n name STAFF\n exit\n!\ninterface GigabitEthernet1\n description untouched\n!\nvlan 200\n name GUEST\n exit\n'


class EditTests(unittest.TestCase):
    capture = original_tests.OriginalTests.capture

    def setUp(self):
        original_tests.OriginalTests.setUp(self)
        self.inventory_path = self.root / 'inventory.json'
        inventory = load_inventory()
        self.inventory_path.write_text(json.dumps(inventory), encoding='utf-8')
        self.enterContext(patch('app.devices.inventory.INVENTORY_FILE', self.inventory_path))
        self.device = next(d for d in inventory if d['id'] == 'lab-sw1')
        task = self.session.plan.tasks[0]
        task.category = 'vlan'
        task.device_id = self.device['id']
        task.target_refs = [self.device['id']]
        self.request['device_id'] = self.device['id']
        task.operation_id = 'create_vlan'
        task.target_devices = [self.device]
        task.configs = [dict(device_id=self.device['id'], configuration=TEXT,
                            **{k: self.device[k] for k in ('hostname', 'vendor', 'platform', 'version')})]
        save_session(self.session)
        self.raw = self.path.read_bytes()
        self.request['expected_session_revision'] = sha256(self.raw).hexdigest()
        self.original = self.capture().json()['artifact']
        opened = self.client.post(URL, json={'original_id': self.original['artifact_id']})
        self.assertEqual(opened.status_code, 201, opened.text)
        self.doc = opened.json()['document']
        self.url = URL + '/' + self.doc['document_id'] + '/propose-edit'
        self.interpreter = self.enterContext(patch('app.document_edits.interpret', return_value=edits.Interpretation(
            outcome='edit', operation_id='rename_vlan', vlan_id=20, new_vlan_name='ENGINEERING', current_vlan_name='STAFF')))

    def propose(self, **overrides):
        return self.client.post(self.url, json={
            'expected_revision': self.doc['revision'], 'current_content': TEXT,
            'instruction': 'Change VLAN 20 name from STAFF to ENGINEERING', **overrides})

    def assert_code(self, response, status, code):
        self.assertEqual(response.status_code, status, response.text)
        self.assertEqual(response.json()['detail']['code'], code)

    def test_real_catalog_rendered_proposal_without_any_writes(self):
        from app.context import source_revision
        source_before = source_revision()
        paths = [self.path, self.inventory_path, originals.storage_root() / (self.original['artifact_id'] + '.json'), working.storage_root() / (self.doc['document_id'] + '.json')]
        before = [(p.read_bytes(), p.stat().st_mtime_ns) for p in paths]
        with patch('app.clarification.save_session', side_effect=AssertionError('no session save')), patch('app.clarification.create_session', side_effect=AssertionError('no plan')), patch('app.clarification.apply_answer', side_effect=AssertionError('no answer')), patch('app.workbench.working_documents.save_document', side_effect=AssertionError('no save')):
            response = self.propose()
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(result['proposed_content'], TEXT.replace('STAFF', 'ENGINEERING'))
        self.assertEqual(result['base_content_sha256'], sha256(TEXT.encode()).hexdigest())
        self.assertEqual(result['evidence']['device_id'], 'lab-sw1')
        self.assertEqual(result['authority']['runtime'], 'direct_files')
        self.assertIsNone(result['authority']['release_id'])
        self.assertEqual(result['authority']['retrieval'], 'not_used')
        self.assertEqual(before, [(p.read_bytes(), p.stat().st_mtime_ns) for p in paths])
        self.assertEqual(source_revision(), source_before)
        self.assertEqual(len(self.interpreter.call_args.args), 4)
        self.assertEqual(self.interpreter.call_args.args[3], TEXT)

    def test_current_unsaved_buffer_second_edit_and_noop(self):
        self.interpreter.return_value = edits.Interpretation(outcome='edit', operation_id='rename_vlan', vlan_id=20, new_vlan_name='FINANCE', current_vlan_name='ENGINEERING')
        current = TEXT.replace('STAFF', 'ENGINEERING') + '! manual change\n'
        response = self.propose(current_content=current, instruction='Rename VLAN 20 from ENGINEERING to FINANCE')
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['proposed_content'], current.replace('ENGINEERING', 'FINANCE'))
        self.interpreter.return_value.current_vlan_name = None
        response = self.propose(current_content=current.replace('ENGINEERING', 'FINANCE'), instruction='Rename VLAN 20 to FINANCE')
        self.assertEqual(response.json()['outcome'], 'no_change')
        self.assertEqual(working.read_document(self.doc['document_id']).content, TEXT)

    def test_exact_bom_crlf_spaces_and_unrelated_occurrences(self):
        text = '\ufeff' + TEXT.replace('name STAFF', 'name STAFF  ').replace('\n', '\r\n') + '! STAFF elsewhere  '
        result = self.propose(current_content=text).json()
        self.assertEqual(result['proposed_content'], text.replace('name STAFF', 'name ENGINEERING'))

    def test_stale_saved_revision_before_inference(self):
        self.assert_code(self.propose(expected_revision=str(uuid4())), 409, 'STALE_WORKING_REVISION')
        self.interpreter.assert_not_called()

    def test_unknown_and_invalid_document(self):
        self.assertEqual(self.client.post(URL + '/working-' + '0' * 64 + '/propose-edit', json={'expected_revision': self.doc['revision'], 'current_content': TEXT, 'instruction': 'rename'}).status_code, 404)
        self.assertEqual(self.client.post(URL + '/invalid/propose-edit', json={}).status_code, 422)

    def test_invalid_bounded_input_and_extra_context_rejected(self):
        for override in ({'instruction': ' '}, {'instruction': 'x' * 2001}, {'current_content': 'x' * 65537}, {'current_content': 'é' * 40000}, {'device_id': 'dev-r2'}, {'instruction': ''}):
            with self.subTest(override=list(override)):
                self.assertEqual(self.propose(**override).status_code, 422)
        self.interpreter.assert_not_called()

    def test_missing_parameter_returns_clarification_not_fake_progression(self):
        self.interpreter.return_value = edits.Interpretation(outcome='clarification_required', operation_id='rename_vlan', vlan_id=20)
        result = self.propose(instruction='Rename VLAN 20').json()
        self.assertEqual(result['outcome'], 'clarification_required')
        self.assertIsNone(result['proposed_content'])

    def test_unsupported_instruction_is_explicit(self):
        self.interpreter.return_value = edits.Interpretation(outcome='unsupported')
        self.assertEqual(self.propose(instruction='Delete interface and deploy').json()['outcome'], 'unsupported')

    def test_parameters_schema_and_literal_evidence(self):
        for value in ('has spaces', 'A' * 30, 'ENGINEERING\nshutdown'):
            self.interpreter.return_value.new_vlan_name = value
            self.assert_code(self.propose(), 422, 'INVALID_EDIT_PARAMETERS')
        self.interpreter.return_value.new_vlan_name = 'INVENTED'
        self.assert_code(self.propose(), 422, 'UNGROUNDED_EDIT')

    def test_ambiguous_missing_nested_or_duplicate_blocks(self):
        for text in ('', 'banner motd #\n' + TEXT + '#', TEXT + 'vlan 20\n name SECOND\n', TEXT.replace('vlan 20', 'vlan 20,101'), TEXT.replace(' name STAFF', ' name STAFF\n name SECOND'), TEXT.replace(' name STAFF', ' interface nested\n name STAFF'), TEXT.replace(' name STAFF', '')):
            with self.subTest(text=text[:30]):
                self.assert_code(self.propose(current_content=text), 422, 'EDIT_BLOCK_UNSUPPORTED')

    def test_old_name_conflict(self):
        self.assert_code(self.propose(current_content=TEXT.replace('STAFF', 'MANUAL')), 422, 'EDIT_OLD_VALUE_CONFLICT')

    def test_explicit_other_device_and_unknown_model_target(self):
        self.assert_code(self.propose(instruction='On R2 rename VLAN 20 from STAFF to ENGINEERING'), 422, 'EDIT_TARGET_CONFLICT')
        self.interpreter.assert_not_called()
        self.interpreter.return_value.target = 'R999'
        self.assert_code(self.propose(instruction='On R999 rename VLAN 20 from STAFF to ENGINEERING'), 422, 'EDIT_TARGET_CONFLICT')

    def test_explicit_matching_device_uses_actual_target_resolver(self):
        self.interpreter.return_value.target = 'SW1'
        self.assertEqual(self.propose(instruction='On SW1 rename VLAN 20 from STAFF to ENGINEERING').status_code, 200)

    def test_source_device_change_or_missing(self):
        inventory = load_inventory()
        next(d for d in inventory if d['id'] == 'lab-sw1')['platform'] = 'nxos'
        self.inventory_path.write_text(json.dumps(inventory), encoding='utf-8')
        self.assert_code(self.propose(), 409, 'EDIT_DEVICE_CHANGED')
        self.inventory_path.write_text(json.dumps([d for d in inventory if d['id'] != 'lab-sw1']), encoding='utf-8')
        self.assert_code(self.propose(), 409, 'EDIT_TARGET_UNAVAILABLE')

    def test_invalid_original_or_storage(self):
        path = originals.storage_root() / (self.original['artifact_id'] + '.json')
        path.write_text('{}', encoding='utf-8')
        self.assertEqual(self.propose().status_code, 409)
        self.interpreter.assert_not_called()

    def test_model_failure_timeout_and_invalid_output(self):
        for error, code, status in [(TimeoutError(), 'LOCAL_MODEL_UNAVAILABLE', 503), (ConnectionError('private path'), 'LOCAL_MODEL_UNAVAILABLE', 503), (ValueError('private output'), 'INVALID_MODEL_RESPONSE', 502)]:
            self.interpreter.side_effect = error
            response = self.propose()
            self.assert_code(response, status, code)
            self.assertNotIn('private', response.text)

    def test_inference_outside_mutation_gate_and_late_revision_rejection(self):
        entered, release = Event(), Event()
        interpreted = self.interpreter.return_value
        def infer(*_):
            entered.set()
            self.assertTrue(release.wait(10))
            return interpreted
        self.interpreter.side_effect = infer
        with ThreadPoolExecutor(1) as pool:
            future = pool.submit(self.propose)
            self.assertTrue(entered.wait(10))
            try:
                self.assert_code(self.propose(), 503, 'EDIT_BUSY')
                saved = self.client.put(URL + '/' + self.doc['document_id'], json={'expected_revision': self.doc['revision'], 'content': TEXT + '! saved during inference'})
                self.assertEqual(saved.status_code, 200, saved.text)
            finally:
                release.set()
            self.assert_code(future.result(), 409, 'STALE_WORKING_REVISION')

    def test_source_revision_changed_during_interpretation(self):
        with patch('app.context.source_revision', side_effect=['before', 'after']):
            self.assert_code(self.propose(), 409, 'EDIT_SOURCE_CHANGED')

    def test_device_policy_and_render_failure(self):
        with patch('app.devices.context_validator.validate_device_context', return_value=[{'type': 'UNSUPPORTED_OPERATION'}]):
            self.assert_code(self.propose(), 422, 'EDIT_VENDOR_VALIDATION')
        with patch('app.templates.renderer.render', return_value='vlan 20\n name ENGINEERING\n shutdown\n exit\n'):
            self.assert_code(self.propose(), 422, 'EDIT_BLOCK_UNSUPPORTED')

    def test_actual_r1_profile_and_unrecorded_vlan_remain_rejected(self):
        from app.devices.context_validator import validate_device_context
        r1 = next(d for d in load_inventory() if d['id'] == 'dev-r1')
        self.assertTrue(validate_device_context('rename_vlan', 'vlan', {'vlan_id': 100, 'new_vlan_name': 'ENGINEERING'}, [r1]))
        self.interpreter.return_value.vlan_id = 100
        self.assert_code(self.propose(instruction='Rename VLAN 100 from STAFF to ENGINEERING'), 422, 'EDIT_VENDOR_VALIDATION')

    def test_real_interpreter_contract_invokes_configured_llm_not_fallback(self):
        # The real inference wrapper is tested separately from the adapter double.
        # Avoid replacing the module: access original function retained by patch.
        function = self._original_interpret
        with patch('app.llm.llm') as model:
            model.bind.return_value.invoke.return_value = SimpleNamespace(content=json.dumps({'outcome': 'edit', 'operation_id': 'rename_vlan', 'vlan_id': 20, 'new_vlan_name': 'ENGINEERING'}))
            parsed = function('Rename VLAN 20 to ENGINEERING', {}, self.device)
            self.assertEqual(parsed.new_vlan_name, 'ENGINEERING')
            model.bind.return_value.invoke.assert_called_once()
            model.bind.return_value.invoke.return_value = SimpleNamespace(content='not JSON')
            with self.assertRaises(ValueError): function('rename', {}, self.device)

    _original_interpret = staticmethod(edits.interpret)
