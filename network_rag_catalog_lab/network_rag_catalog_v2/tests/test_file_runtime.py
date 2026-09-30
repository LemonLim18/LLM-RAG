from copy import deepcopy
import json
import os
import unittest
from unittest.mock import MagicMock, patch

from app.config import BASE_DIR
from app.knowledge.runtime import current_snapshot, snapshot_scope


class FileRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, {"NETWORK_RAG_RUNTIME": "files"}))
        self.enterContext(snapshot_scope(None))
        for target in ("app.llm.llm", "app.planner.intent_planner.llm", "app.parameters.parameter_extractor.llm"):
            self.enterContext(patch(target)).invoke.return_value.content = "null"

    def test_direct_catalog_has_all_requested_operations_and_schemas(self):
        from app.file_runtime import file_documents
        from app.knowledge.vendor_coverage import read_scope
        documents = file_documents()
        ids = {row["id"] for row in documents}
        requested = {identity for rows in read_scope()["categories"].values() for identity in rows}
        self.assertEqual(len(requested), 38)
        self.assertEqual(len(ids), 44)
        self.assertTrue(requested <= ids)
        for doc in documents:
            schema = BASE_DIR / "data/operations" / doc["metadata"]["category"] / doc["id"] / "schema.json"
            self.assertTrue(schema.is_file())
            self.assertIn("Parameter contract", doc["page_content"])
            self.assertNotIn("release_id", doc["metadata"])

    def test_file_mode_does_not_read_a_release(self):
        from app.knowledge.runtime import _current, _UNBOUND
        token = _current.set(_UNBOUND)
        try:
            with patch("app.knowledge.runtime.active_snapshot", side_effect=AssertionError("release lookup")):
                self.assertIsNone(current_snapshot())
                with snapshot_scope():
                    self.assertIsNone(current_snapshot())
        finally:
            _current.reset(token)

    def test_all_existing_new_operation_examples_render_from_direct_templates(self):
        from app.pipeline import run
        with patch("app.knowledge.publication.publish", side_effect=AssertionError("publication forbidden")):
            count = 0
            for category in ("vlan", "interface", "static_routing", "ospf", "acl", "qos"):
                cases = json.loads((BASE_DIR / "knowledge_packs" / category / "cases.json").read_text(encoding="utf-8"))
                for case in cases:
                    # Existing fixtures use semicolons within one operation; terminal syntax uses commas.
                    prompt = case["prompt"].replace(";", ",")
                    with self.subTest(operation=case["operation_id"]):
                        plan = run(prompt, verbose=False)
                        self.assertEqual(plan.status, "ready", [(t.operation_id, t.issues) for t in plan.tasks])
                        self.assertEqual(len(plan.tasks), 1)
                        self.assertEqual(plan.tasks[0].operation_id, case["operation_id"])
                        self.assertEqual(plan.tasks[0].parameters, case["parameters"])
                        self.assertTrue(plan.tasks[0].configs[0]["configuration"].strip())
                        count += 1
            self.assertEqual(count, 32)

    def test_missing_parameter_and_mixed_targets_preserve_render_gate(self):
        from app.pipeline import run, resume_task, refresh_plan
        plan = run('Create VLAN 100 named STAFF on R1; rename VLAN, vlan_id 20 on SW1', verbose=False)
        self.assertEqual([(t.operation_id, t.target_devices[0]["hostname"]) for t in plan.tasks],
                         [("create_vlan", "R1"), ("rename_vlan", "SW1")])
        self.assertEqual(plan.status, "needs_clarification")
        self.assertFalse(any(task.configs for task in plan.tasks))
        self.assertEqual(plan.tasks[1].questions[0]["field_path"], "new_vlan_name")
        plan.tasks[1] = resume_task(plan.tasks[1], "ENGINEERING")
        refresh_plan(plan)
        self.assertEqual(plan.status, "ready")

    def test_vendor_semantics_never_fall_back_to_cisco(self):
        from app.templates.renderer import render
        device = {"hostname": "SW2", "vendor": "huawei", "platform": "vrp", "version": "V200R024C10"}
        with self.assertRaisesRegex(ValueError, "Schema validation"):
            render(device, "modify_vlan", {"vlan_id": 20, "vlan_status": "suspend"})

    def test_required_and_optional_inputs_are_validated_for_direct_render(self):
        from app.templates.renderer import render
        device = {"hostname": "SW1", "vendor": "cisco", "platform": "iosxe", "version": "17.9"}
        with self.assertRaisesRegex(ValueError, "Required parameter"):
            render(device, "configure_access_port", {"interface": "GigabitEthernet1/0/1"})
        result = render(device, "configure_access_port", {"interface": "GigabitEthernet1/0/1", "vlan_id": 20, "description": "User port"})
        self.assertIn("description User port", result)

    def test_direct_ingestion_never_publishes_and_verifies_stored_contents(self):
        from app.ingest import ingest_files
        documents = [{"id": "create_vlan", "page_content": "catalog", "metadata": {"catalog_revision": "test"}}]
        vs = MagicMock()
        vs.get.return_value = {"ids": ["old", "create_vlan"], "metadatas": [{}, documents[0]["metadata"]], "documents": ["old", "catalog"]}
        with patch("app.ingest.Chroma", return_value=vs), patch("app.file_runtime.catalog_revision", return_value="test"), patch("app.file_runtime.file_documents", return_value=documents), patch("app.knowledge.publication.publish", side_effect=AssertionError("publication forbidden")):
            receipt = ingest_files()
        self.assertEqual(receipt["ids"], ["create_vlan"])
        vs.delete.assert_called_once_with(ids=["old"])


if __name__ == "__main__":
    unittest.main()
