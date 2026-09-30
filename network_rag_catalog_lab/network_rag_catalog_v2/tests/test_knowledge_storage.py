from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from app.knowledge import authoring_store
from app.knowledge.authoring_store import AuthoringError, JsonAuthoringStore
from app.knowledge.document_repository import DocumentKnowledgeRepository
from knowledge_fixtures import KnowledgeFixture


class KnowledgeStorageTests(KnowledgeFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.store = JsonAuthoringStore(self.base)

    def commit(self, candidate, revision):
        return self.store.commit(candidate, expected_revision=revision, actor="test", reason="Reviewed metadata")

    def test_document_repository_matches_file_repository_and_is_defensive(self):
        snapshot = self.store.snapshot()
        repository = DocumentKnowledgeRepository(snapshot["catalogs"])
        for method in ("list_categories", "list_parameters", "list_operations", "list_category_parameters", "list_operation_parameters", "list_operation_rules"):
            self.assertEqual(getattr(repository, method)(), getattr(self.service.repository, method)())
        snapshot["catalogs"]["categories"][0]["display_name"] = "outside edit"
        repository.list_categories()[0].aliases.append("outside")
        self.assertNotEqual(repository.list_categories()[0].display_name, "outside edit")
        self.assertNotIn("outside", repository.list_categories()[0].aliases)

    def test_multi_document_commit_audits_and_rejects_stale_revision(self):
        initial = self.store.snapshot()
        candidate = deepcopy(initial["catalogs"])
        candidate["categories"][0]["description"] = "Updated"
        candidate["parameters"][0]["display_name"] = "Updated label"
        result = self.commit(candidate, initial["revision"])
        self.assertEqual(self.store.snapshot()["catalogs"], candidate)
        self.assertNotEqual(result["revision"], initial["revision"])
        journal = json.loads((self.store.history_dir / (result["audit_id"] + ".json")).read_text(encoding="utf-8"))
        self.assertEqual((journal["state"], journal["actor"]), ("committed", "test"))
        with self.assertRaisesRegex(AuthoringError, "changed"):
            self.commit(candidate, initial["revision"])

    def test_write_failure_rolls_back_exact_original_bytes(self):
        initial = self.store.snapshot()
        candidate = deepcopy(initial["catalogs"])
        candidate["categories"][0]["description"] = "Updated"
        candidate["parameters"][0]["display_name"] = "Updated label"
        original = authoring_store._atomic_text
        failed = False
        def fail_once(path, text):
            nonlocal failed
            if path.name == "parameters.json" and not failed:
                failed = True
                raise OSError("disk failure")
            original(path, text)
        with patch.object(authoring_store, "_atomic_text", side_effect=fail_once), self.assertRaisesRegex(OSError, "disk failure"):
            self.commit(candidate, initial["revision"])
        self.assertEqual(self.store.snapshot()["sources"], initial["sources"])
        self.assertFalse(self.store.pending_path.exists())

    def interrupt(self):
        initial = self.store.snapshot()
        candidate = deepcopy(initial["catalogs"])
        candidate["categories"][0]["description"] = "Interrupted"
        candidate["parameters"][0]["display_name"] = "Interrupted"
        original = authoring_store._atomic_text
        def interrupt(path, text):
            if path.name == "parameters.json":
                raise KeyboardInterrupt
            original(path, text)
        with patch.object(authoring_store, "_atomic_text", side_effect=interrupt), self.assertRaises(KeyboardInterrupt):
            self.commit(candidate, initial["revision"])
        return initial

    def test_crash_journal_blocks_readers_publishers_then_recovers(self):
        initial = self.interrupt()
        self.assertTrue(self.store.pending_path.exists())
        with self.assertRaisesRegex(AuthoringError, "recovery"):
            self.service.list_categories()
        with self.assertRaisesRegex(AuthoringError, "Recover"):
            self.publish()
        self.assertTrue(self.store.recover()["recovered"])
        self.assertEqual(self.store.snapshot()["sources"], initial["sources"])

    def test_recovery_never_overwrites_an_outside_edit(self):
        self.interrupt()
        outside = self.read("categories")
        outside[0]["description"] = "Independent user edit"
        self.write("categories", outside)
        with self.assertRaisesRegex(AuthoringError, "Outside edit"):
            self.store.recover()
        self.assertEqual(self.read("categories"), outside)
        self.assertTrue(self.store.pending_path.exists())


if __name__ == "__main__":
    unittest.main()
