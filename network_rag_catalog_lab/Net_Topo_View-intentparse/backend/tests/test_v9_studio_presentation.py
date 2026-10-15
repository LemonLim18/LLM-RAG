"""Regressions for generic V9 target clarification and declared artifact paths."""
import json
import sqlite3
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import HTTPException
from local_providers.authoring import AuthoringStore
from local_providers.v9_studio import presentation


class StudioPresentationTests(unittest.TestCase):
    def test_ambiguity_offers_only_v9_inventory_candidates(self):
        task = dict(category='test', operation_id='test', parameters={}, parameter_provenance={}, target_devices=[],
                    issues=[dict(type='AMBIGUOUS_TARGET', message='Which device?', candidates=[dict(hostname='A'), dict(hostname='B')])])
        output = dict(plan=dict(tasks=[task], issues=[]), schema=dict(properties={}), release_id='frozen')
        result = presentation(output, 'session', [dict(hostname=h, interfaces=[]) for h in ['A', 'B', 'unrelated']])
        self.assertEqual(result['params_disambiguation']['question'], 'Which device?')
        self.assertEqual([r['hostname'] for r in result['interfaces_for_selection']['devices']], ['A', 'B'])
        self.assertEqual(result['parsed_intent']['validation_errors'], [])
        task['issues'].append(dict(type='UNSUPPORTED', message='Unsupported target'))
        self.assertNotIn('interfaces_for_selection', presentation(output, 'session', []))

    def test_declared_file_requires_exact_persisted_manifest(self):
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder)/'test.db'
            class Database:
                @contextmanager
                def _connect(self):
                    conn = sqlite3.connect(database)
                    try:
                        with conn:
                            yield conn
                    finally:
                        conn.close()
            db = Database()
            path = 'playbooks/generated/job_1/native_config.cfg'
            with db._connect() as conn:
                conn.execute('CREATE TABLE jobs(id INTEGER PRIMARY KEY, ansible_artifact_manifest TEXT)')
                conn.execute('INSERT INTO jobs VALUES(1, ?)', (json.dumps(dict(engine='v9', artifact_metadata=dict(extension='.cfg'), files=[dict(path=path)])),))
            store = AuthoringStore(db, dict(ansible=Path(folder)/'ansible'))
            self.assertEqual(store.resolve('ansible', path).suffix, '.cfg')
            for other in ['playbooks/unknown.cfg', 'playbooks/generated/job_1/other.cfg', 'playbooks/generated/job_2/native_config.cfg', '../native_config.cfg']:
                with self.subTest(path=other), self.assertRaises(HTTPException):
                    store.resolve('ansible', other)


if __name__ == '__main__':
    unittest.main()
