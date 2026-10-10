from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from app.workbench.api import create_app
from app.workbench import working_documents as working
from app.workbench import generated_originals as originals
from tests import test_workbench_originals as original_tests
from pydantic import ValidationError

URL = '/api/v1/workbench/working-documents'


class WorkingTests(unittest.TestCase):
    capture = original_tests.OriginalTests.capture

    def setUp(self):
        original_tests.OriginalTests.setUp(self)
        self.original = self.capture().json()['artifact']
        self.original_path = originals.storage_root() / (self.original['artifact_id'] + '.json')
        self.original_before = self.original_path.read_bytes(), self.original_path.stat().st_mtime_ns

    def open(self, original_id=None):
        return self.client.post(URL, json={'original_id': original_id or self.original['artifact_id']})

    def save(self, document, content, revision=None):
        return self.client.put(URL + '/' + document['document_id'], json={
            'expected_revision': revision or document['revision'], 'content': content})

    def test_initial_exact_content_context_and_idempotent_reopen_after_edit(self):
        created = self.open()
        self.assertEqual(created.status_code, 201, created.text)
        document = created.json()['document']
        self.assertEqual(document['content'], self.original['configuration'])
        self.assertEqual(document['original']['source'], self.original['source'])
        self.assertEqual(document['validation'], 'unvalidated')
        saved = self.save(document, '\ufeffvlan 100\r\n name ENGINEERING  \n\n').json()
        reopened = self.open()
        self.assertEqual(reopened.status_code, 200)
        self.assertEqual(reopened.json()['document'], saved)
        self.assertEqual(len(list(working.storage_root().glob('*.json'))), 1)
        self.assertEqual((self.original_path.read_bytes(), self.original_path.stat().st_mtime_ns), self.original_before)
        self.assertEqual((self.path.read_bytes(), self.path.stat().st_mtime_ns), (self.raw, self.mtime))

    def test_different_originals_even_identical_text_have_distinct_documents(self):
        first = self.open().json()['document']
        second_original = self.capture(config_index=1).json()['artifact']
        second = self.open(second_original['artifact_id']).json()['document']
        self.assertNotEqual(first['document_id'], second['document_id'])
        self.assertNotEqual(first['original']['source']['config_index'], second['original']['source']['config_index'])

    def test_revision_prevents_aba_stale_and_same_content_retry(self):
        first = self.open().json()['document']
        second = self.save(first, 'B').json()
        third = self.save(second, first['content']).json()
        self.assertEqual(third['save_sequence'], 2)
        self.assertEqual(len({d['revision'] for d in [first, second, third]}), 3)
        stale = self.save(first, 'must not overwrite')
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.json()['detail']['code'], 'STALE_WORKING_REVISION')
        unchanged_save = self.save(third, third['content']).json()
        self.assertNotEqual(unchanged_save['revision'], third['revision'])
        self.assertEqual(self.save(third, third['content']).status_code, 409)

    def test_empty_unicode_line_endings_and_bounded_encoding(self):
        document = self.open().json()['document']
        for text in ('', 'é\r\n配置\n  end  ', '\ufeff\r\n'):
            response = self.save(document, text)
            self.assertEqual(response.status_code, 200, response.text)
            document = response.json()
            self.assertEqual(document['content'], text)
            self.assertEqual(self.client.get(URL + '/' + document['document_id']).json()['content'], text)
        self.assertEqual(self.save(document, 'é' * (working.MAX_CONTENT_BYTES // 2 + 1)).status_code, 413)
        self.assertEqual(self.save(document, 'x' * (working.MAX_CONTENT_BYTES + 1)).status_code, 422)
        with self.assertRaises(ValidationError):
            working.save_document(document['document_id'], working.SaveWorkingRequest(expected_revision=document['revision'], content='\ud800'))

    def test_missing_corrupt_original_and_invalid_requests(self):
        self.assertEqual(self.open('original-' + '0' * 64).status_code, 404)
        self.assertEqual(self.open('../path').status_code, 422)
        self.assertEqual(self.client.get(URL + '/working-' + '0' * 64).status_code, 404)
        self.assertEqual(self.client.get(URL + '/bad').status_code, 422)
        document = self.open().json()['document']
        self.assertEqual(self.client.put(URL + '/' + document['document_id'], json={'content': 'x'}).status_code, 422)
        self.assertEqual(self.client.post(URL, json={'original_id': self.original['artifact_id'], 'content': 'untrusted'}).status_code, 422)
        self.original_path.write_bytes(b'{')
        self.assertEqual(self.open().json()['detail']['code'], 'CORRUPT_ARTIFACT')
        # Working reads remain independent of source original availability.
        self.assertEqual(self.client.get(URL + '/' + document['document_id']).status_code, 200)

    def test_corrupt_working_records_fail_without_repair(self):
        document = self.open().json()['document']
        path = working.storage_root() / (document['document_id'] + '.json')
        for key, value in [('content', 'tampered'), ('schema_version', 99), ('revision', str(uuid4())), ('document_id', 'working-' + '0' * 64)]:
            raw = json.dumps({**document, key: value}).encode()
            path.write_bytes(raw)
            for response in (self.client.get(URL), self.client.get(URL + '/' + document['document_id']), self.open(), self.save(document, 'x')):
                self.assertEqual(response.status_code, 409, response.text)
            self.assertEqual(path.read_bytes(), raw)

    def test_save_write_fsync_replace_failures_preserve_previous_document(self):
        document = self.open().json()['document']
        path = working.storage_root() / (document['document_id'] + '.json')
        before = path.read_bytes()
        for name in ('fsync', 'replace'):
            with patch('app.workbench.working_documents.os.' + name, side_effect=OSError('private path')):
                response = self.save(document, 'new')
                self.assertEqual(response.status_code, 503)
                self.assertNotIn('private path', response.text)
            self.assertEqual(path.read_bytes(), before)
            self.assertFalse(list(working.storage_root().glob('*.tmp')))
        real_open = Path.open
        for failure in ('write', 'flush'):
            class Failure:
                def __enter__(self): return self
                def __exit__(self, *args): self.stream.close()
                def write(self, raw):
                    if failure == 'write': self.stream.write(raw[:5]); return 5
                    return self.stream.write(raw)
                def flush(self): raise OSError('flush')
            def broken(path, *args, **kwargs):
                stream = real_open(path, *args, **kwargs)
                if args and args[0] == 'xb':
                    wrapper = Failure(); wrapper.stream = stream; return wrapper
                return stream
            with patch.object(Path, 'open', broken):
                self.assertEqual(self.save(document, 'new').status_code, 503)
            self.assertEqual(path.read_bytes(), before)

    def test_partial_original_then_create_failure_recovers_without_duplicates(self):
        with patch('app.workbench.working_documents.os.link', side_effect=OSError('publication failed')):
            self.assertEqual(self.open().status_code, 503)
        self.assertEqual(len(list(originals.storage_root().glob('*.json'))), 1)
        self.assertEqual(self.client.get(URL).json()['documents'], [])
        self.assertEqual(self.capture().json()['outcome'], 'already_saved')
        self.assertEqual(self.open().status_code, 201)
        self.assertEqual(self.open().json()['outcome'], 'reopened')

    def test_lost_save_response_and_fresh_process_reads_persisted_revision(self):
        document = self.open().json()['document']
        saved = self.save(document, 'name ENGINEERING').json()  # Lost response at browser.
        script = '''import sys,json
from pathlib import Path
from fastapi.testclient import TestClient
import app.config as config
config.STORAGE_DIR=Path(sys.argv[1])
from app.workbench.api import create_app
c=TestClient(create_app()); url=sys.argv[2]; identity=sys.argv[3]
d=c.get(url+'/'+identity).json()
assert d['content']=='name ENGINEERING'
assert c.get(url).json()['documents'][0]['revision']==d['revision']
assert not any(x in sys.modules for x in ('app.clarification','app.pipeline','langchain_ollama','chromadb'))
print(json.dumps(d))'''
        result = subprocess.run([sys.executable, '-c', script, str(self.root), URL, document['document_id']], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), saved)
        self.assertEqual(self.save(document, saved['content']).status_code, 409)

    def test_passive_reads_and_saves_never_plan_or_change_protected_sources(self):
        document = self.open().json()['document']
        inventory = Path('data/inventory/devices.json')
        before = inventory.read_bytes(), inventory.stat().st_mtime_ns
        for target in ['app.clarification.' + name for name in ('load_session', 'save_session', 'create_session', 'apply_answer', 'refresh_plan')] + [
                'app.pipeline.render', 'app.pipeline.run', 'app.vectorstore.get_vectorstore', 'socket.create_connection', 'subprocess.Popen']:
            self.enterContext(patch(target, side_effect=AssertionError(target)))
        self.assertEqual(self.save(document, 'manual text').status_code, 200)
        path = working.storage_root() / (document['document_id'] + '.json')
        snapshot = path.read_bytes(), path.stat().st_mtime_ns
        with patch('os.replace', side_effect=AssertionError('write')), patch('os.link', side_effect=AssertionError('create')):
            for url in (URL, URL + '/' + document['document_id']):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), snapshot)
        self.assertEqual((self.original_path.read_bytes(), self.original_path.stat().st_mtime_ns), self.original_before)
        self.assertEqual((self.path.read_bytes(), self.path.stat().st_mtime_ns), (self.raw, self.mtime))
        self.assertEqual((inventory.read_bytes(), inventory.stat().st_mtime_ns), before)

    def test_concurrent_open_and_stale_saves_share_one_gate(self):
        # One app/client => one supported mutation coordinator.
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.open(), range(2)))
        self.assertIn(201, [response.status_code for response in results])
        self.assertTrue(all(response.status_code in (200, 201, 503) for response in results))
        document = self.open().json()['document']
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda content: self.save(document, content), ('one', 'two')))
        self.assertEqual(sum(response.status_code == 200 for response in results), 1)
        self.assertTrue(all(response.status_code in (200, 409, 503) for response in results))
        self.assertEqual(len(list(working.storage_root().glob('*.json'))), 1)

    def test_external_change_before_replace_and_bounded_collection(self):
        document = self.open().json()['document']
        real_read = working.read_document
        count = 0
        def changed(identity):
            nonlocal count
            result = real_read(identity); count += 1
            return result if count == 1 else result.model_copy(update={'revision': uuid4()})
        with patch.object(working, 'read_document', changed):
            self.assertEqual(self.save(document, 'not saved').status_code, 409)
        self.assertEqual(real_read(document['document_id']).content, document['content'])
        with patch.object(working, 'MAX_ENTRIES', 0):
            self.assertEqual(self.client.get(URL).json()['detail']['code'], 'WORKING_CAPACITY')


if __name__ == '__main__': unittest.main()
