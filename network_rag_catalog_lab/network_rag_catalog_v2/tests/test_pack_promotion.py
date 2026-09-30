from contextlib import closing
from copy import deepcopy
import json
import shutil
import sqlite3
import unittest
from unittest.mock import patch

from app.config import BASE_DIR
from app.knowledge.management import KnowledgeManagementService
from app.knowledge.pack_promote import DOMAINS, merge_demo_devices, promote
from app.knowledge.runtime import active_pointer, active_snapshot, snapshot_scope
from knowledge_fixtures import KnowledgeFixture


class InventoryMergeTests(unittest.TestCase):
    def test_merge_is_idempotent_and_preserves_original_records(self):
        current = [{"id": "r1", "hostname": "R1", "aliases": ["Router 1"]}]
        additions = [{"id": "sw1", "hostname": "SW1", "aliases": ["Lab Switch 1"]}]
        original = deepcopy(current)
        merged = merge_demo_devices(current, additions)
        self.assertEqual(current, original)
        self.assertEqual(merged[:1], original)
        self.assertEqual(merge_demo_devices(merged, additions), merged)

    def test_conflicting_ids_hostnames_and_normalized_aliases_are_rejected(self):
        current = [{"id": "r1", "hostname": "R1", "aliases": ["Router 1"]}]
        for candidate in [
            {"id": "r1", "hostname": "SW1"},
            {"id": "sw1", "hostname": "r1"},
            {"id": "sw1", "hostname": "SW1", "aliases": ["router-1"]},
        ]:
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                merge_demo_devices(current, [candidate])


class RuntimeSelectionTests(unittest.TestCase):
    def test_category_preface_does_not_replace_explicit_target(self):
        from app.devices.target_query import extract_target_queries
        devices = json.loads((BASE_DIR / "knowledge_packs/fixtures/devices.json").read_text())
        queries = extract_target_queries('For static routing, send unmatched IPv4 traffic through next_hop "192.0.2.2" with preference 200 on SW1', devices)
        self.assertEqual([query["text"] for query in queries], ["SW1"])

    def test_selector_only_accepts_retrieved_ids(self):
        from app.retrieval.operation_selector import select_operation
        candidates = [{"operation_id": "create_vlan", "description": "Create a VLAN", "distance": 0.1}]
        with patch("app.retrieval.operation_selector.llm") as model:
            model.invoke.return_value.content = '{"operation_id":"create_vlan"}'
            self.assertEqual(select_operation("Make another layer-two segment", "vlan", candidates), "create_vlan")
            model.invoke.return_value.content = '{"operation_id":"invented_operation"}'
            with self.assertRaises(ValueError):
                select_operation("Make another layer-two segment", "vlan", candidates)


class PackPromotionTests(KnowledgeFixture, unittest.TestCase):
    def test_interrupted_promotion_resumes_with_backup_and_without_publication(self):
        self.releases = self.base / "storage/catalog_releases"
        self.publish()
        manager = KnowledgeManagementService(self.base)
        migration = manager.migrate_sqlite({"expected_revision": manager.inspect().revision,
                                            "actor": "test", "reason": "Test SQLite promotion"})
        self.assertTrue(migration.ok, migration)
        shutil.copytree(BASE_DIR / "knowledge_packs", self.base / "knowledge_packs")
        baseline = active_pointer(self.releases)
        original_inventory = json.loads((self.base / "data/inventory/devices.json").read_text())
        real_apply = KnowledgeManagementService.apply
        calls = []

        def interrupt(service, request, **kwargs):
            calls.append(request)
            if len(calls) == 3:
                raise ValueError("Simulated interruption after VLAN commit")
            return real_apply(service, request, **kwargs)

        with patch.object(KnowledgeManagementService, "apply", new=interrupt), self.assertRaisesRegex(ValueError, "Simulated"):
            promote(self.base, actor="test", reason="Interrupted test")
        self.assertEqual(active_pointer(self.releases), baseline)
        self.assertEqual(manager.inspect().data["counts"]["operations"], 14)
        result = promote(self.base, actor="test", reason="Resume test")
        self.assertEqual((result["operations"], result["bindings"]), (44, 78))
        self.assertFalse(result["packs"][0]["changed"])
        self.assertEqual(active_pointer(self.releases), baseline)
        self.assertEqual(json.loads((self.base / "data/inventory/devices.json").read_text())[:len(original_inventory)], original_inventory)
        with closing(sqlite3.connect(result["backup"] + "/catalog.sqlite3")) as connection:
            self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        repeated = promote(self.base, actor="test", reason="Idempotence test")
        self.assertFalse(any(pack["changed"] for pack in repeated["packs"]))
        self.assertEqual(repeated["inventory_added"], [])
        self.assertEqual(active_pointer(self.releases), baseline)
        state = manager.inspect()
        publication = manager.publish({"expected_revision": state.revision,
            "expected_release": baseline["release_id"], "actor": "test", "reason": "Isolated runtime check", "mode": "offline"})
        self.assertTrue(publication.ok, publication)
        from app.pipeline import run
        from app.parameters.evidence import literal_candidates
        from app.parameters.schema_loader import load_schema
        with snapshot_scope(active_snapshot(self.releases)), \
                patch("app.context.DATA_DIR", self.base / "data"), \
                patch("app.devices.inventory.INVENTORY_FILE", self.base / "data/inventory/devices.json"):
            for domain in DOMAINS:
                cases = json.loads((self.base / "knowledge_packs" / domain / "cases.json").read_text())
                for case in cases:
                    with self.subTest(operation=case["operation_id"]):
                        prompt = case["prompt"].replace(";", ",")
                        plan = run(prompt, verbose=False)
                        self.assertEqual(plan.status, "ready", [(task.operation_id, task.issues) for task in plan.tasks])
                        self.assertEqual(len(plan.intents), 1)
                        self.assertEqual(plan.tasks[0].operation_id, case["operation_id"])
                        self.assertEqual(plan.tasks[0].parameters, case["parameters"])
                        self.assertEqual([device["hostname"] for device in plan.tasks[0].target_devices], ["SW1"])
            schema = load_schema("modify_vlan")["properties"]["vlan_id"]
            self.assertEqual(literal_candidates("vlan_id 20,30", "vlan_id", schema), [])
            self.assertEqual(literal_candidates("vlan_id 20, vlan_id 30", "vlan_id", schema), [20, 30])
