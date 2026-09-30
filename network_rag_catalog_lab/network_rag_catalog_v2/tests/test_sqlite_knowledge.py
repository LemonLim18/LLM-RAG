from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from app.knowledge.authoring_store import AuthoringError, JsonAuthoringStore
from app.knowledge.authority import authority
from app.knowledge.document_repository import DocumentKnowledgeRepository
from app.knowledge.management import KnowledgeManagementService
from app.knowledge.runtime import active_snapshot, snapshot_scope
from app.knowledge.sqlite_repository import SQLiteAuthoringStore, SQLiteKnowledgeRepository
from app.parameters.schema_loader import load_schema
from knowledge_fixtures import KnowledgeFixture
from test_knowledge_services import KnowledgeServiceManagementTests as _ManagementContract


class SQLiteManagementContractTests(_ManagementContract):
    """Run the same public management contracts against both storage backends."""
    def setUp(self):
        super().setUp()
        result = self.manager.migrate_sqlite({"expected_revision": self.manager.inspect().revision,
            "actor": "test", "reason": "Verify database equivalence"})
        self.assertTrue(result.ok, result)


class SQLiteStorageTests(KnowledgeFixture, unittest.TestCase):
    def test_interrupted_authority_switch_can_resume_without_overwriting_data(self):
        from app.knowledge import sqlite_repository
        revision = self.manager.inspect().revision
        real_write = sqlite_repository._atomic_json
        def interrupt(path, document):
            if path.name == "authority.json":
                raise OSError("authority write interrupted")
            return real_write(path, document)
        request = {"expected_revision": revision, "actor": "test", "reason": "Migration recovery"}
        with patch.object(sqlite_repository, "_atomic_json", side_effect=interrupt):
            self.assertFalse(self.manager.migrate_sqlite(request).ok)
        self.assertEqual(self.manager.inspect().issues[0].code, "MISSING_AUTHORITY")
        result = self.manager.migrate_sqlite(request)
        self.assertTrue(result.ok, result)
        self.assertTrue(result.data["resumed"])
        self.assertEqual(authority(self.base), "sqlite")

    def test_missing_active_release_after_cutover_never_uses_seed_files(self):
        from shutil import copytree
        self.migrate()
        runtime_root = self.base / "storage/catalog_releases"
        copytree(self.releases, runtime_root)
        (runtime_root / "active.json").unlink()
        with self.assertRaisesRegex(ValueError, "source-mode fallback is forbidden"):
            active_snapshot(runtime_root)

    def setUp(self):
        super().setUp()
        self.baseline = self.publish()
        self.manager = KnowledgeManagementService(self.base, releases_dir=self.releases)

    def migrate(self):
        result = self.manager.migrate_sqlite({"expected_revision": self.manager.inspect().revision,
            "actor": "test", "reason": "Approved authority migration"})
        self.assertTrue(result.ok, result)
        return SQLiteAuthoringStore(self.base)

    def test_migration_preserves_every_record_and_typed_repository_contract(self):
        original = JsonAuthoringStore(self.base).snapshot()
        store = self.migrate()
        self.assertEqual(store.snapshot()["catalogs"], original["catalogs"])
        self.assertEqual(authority(self.base), "sqlite")
        readers = (SQLiteKnowledgeRepository(self.base), DocumentKnowledgeRepository(original["catalogs"]))
        for name in ("list_categories", "list_parameters", "list_operations", "list_category_parameters", "list_operation_parameters", "list_operation_rules"):
            self.assertEqual(getattr(readers[0], name)(), getattr(readers[1], name)())
        with store._connection() as connection:
            self.assertEqual(connection.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            self.assertFalse(connection.execute("PRAGMA foreign_key_check").fetchall())
            self.assertEqual(connection.execute("SELECT count(*) FROM authoring_audit").fetchone()[0], 1)

    def test_json_is_not_an_independent_authority_after_cutover(self):
        store = self.migrate()
        before = store.snapshot()
        self.write("operations", [])
        self.assertEqual(store.snapshot()["revision"], before["revision"])
        self.assertEqual(store.snapshot()["catalogs"], before["catalogs"])
        with self.assertRaisesRegex(AuthoringError, "import/export"):
            JsonAuthoringStore(self.base).commit(before["catalogs"], expected_revision="old", actor="test", reason="stale backend")
        release = self.publish()
        with snapshot_scope(release):
            self.assertEqual(load_schema("create_vlan")["required"], ["vlan_id"])
        self.assertEqual(release.manifest["authoring_backend"], "sqlite")

    def test_foreign_key_failure_rolls_back_all_records_and_audit(self):
        store = self.migrate()
        before = store.snapshot()
        candidate = deepcopy(before["catalogs"])
        candidate["category_parameters"] = [row for row in candidate["category_parameters"] if row != {"category_id": "vlan", "parameter_id": "vlan_id"}]
        with self.assertRaisesRegex(AuthoringError, "FOREIGN KEY"):
            store.commit(candidate, expected_revision=before["revision"], actor="test", reason="Invalid dependency")
        self.assertEqual(store.snapshot()["revision"], before["revision"])
        self.assertEqual(store.snapshot()["catalogs"], before["catalogs"])

    def test_failed_audit_write_rolls_back_catalog_update(self):
        store = self.migrate()
        before = store.snapshot()
        candidate = deepcopy(before["catalogs"])
        candidate["categories"][0]["description"] = "Not committed"
        with patch.object(store, "_audit", side_effect=RuntimeError("audit unavailable")), self.assertRaises(RuntimeError):
            store.commit(candidate, expected_revision=before["revision"], actor="test", reason="Atomicity")
        self.assertEqual(store.snapshot()["revision"], before["revision"])

    def test_two_clients_reject_stale_edit_and_record_versions(self):
        store = self.migrate()
        before = store.snapshot()
        candidate = deepcopy(before["catalogs"])
        candidate["categories"][0]["description"] = "Committed"
        store.commit(candidate, expected_revision=before["revision"], actor="first", reason="First edit")
        with self.assertRaisesRegex(AuthoringError, "changed"):
            SQLiteAuthoringStore(self.base).commit(before["catalogs"], expected_revision=before["revision"], actor="second", reason="Stale edit")
        with store._connection() as connection:
            row = connection.execute("SELECT actor, before_catalogs, after_catalogs FROM authoring_audit ORDER BY generation DESC LIMIT 1").fetchone()
            self.assertEqual(row[0], "first")
            self.assertEqual(json.loads(row[1]), before["catalogs"])
            self.assertEqual(json.loads(row[2]), candidate)

    def test_missing_database_does_not_silently_fall_back_to_json(self):
        store = self.migrate()
        store.path.rename(store.path.with_suffix(".backup"))
        result = self.manager.inspect()
        self.assertFalse(result.ok)
        self.assertEqual(result.issues[0].code, "DATABASE_MISSING")

    def test_stale_migration_changes_neither_authority_nor_live_release(self):
        result = self.manager.migrate_sqlite({"expected_revision": "stale", "actor": "test", "reason": "stale request"})
        self.assertEqual(result.issues[0].code, "STALE_REVISION")
        self.assertEqual(authority(self.base), "json")
        self.assertEqual(active_snapshot(self.releases).release_id, self.baseline.release_id)


# Keep unittest discovery from also collecting the imported parent class here.
del _ManagementContract

if __name__ == "__main__":
    unittest.main()
