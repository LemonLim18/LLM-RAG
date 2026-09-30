from copy import deepcopy
from io import StringIO
import json
import unittest
from unittest.mock import patch

from app import catalog
from app.knowledge.cli import main
from app.knowledge.management import KnowledgeManagementService
from app.knowledge.runtime import snapshot_scope
from app.parameters.schema_loader import load_schema
from knowledge_fixtures import KnowledgeFixture


class KnowledgeServiceManagementTests(KnowledgeFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.baseline = self.publish()
        self.manager = KnowledgeManagementService(self.base, releases_dir=self.releases)

    def edit_request(self, *changes):
        return {"expected_revision": self.manager.inspect().revision, "actor": "engineer", "reason": "Reviewed test change", "changes": list(changes)}

    def publish_request(self):
        return {"expected_revision": self.manager.inspect().revision,
                "expected_release": self.manager.inspect().data["active_release"]["release_id"],
                "actor": "engineer", "reason": "Approved revision", "mode": "offline"}

    def test_create_edit_assign_unassign_and_delete_unused_definitions(self):
        request = self.edit_request(
            {"entity": "category", "action": "create", "entity_id": "lab_domain", "values": {"display_name": "Lab Domain"}},
            {"entity": "parameter", "action": "create", "entity_id": "sample_metric", "values": {"display_name": "Sample metric", "value_type": "integer"}},
            {"entity": "membership", "action": "assign", "values": {"category_id": "lab_domain", "parameter_id": "sample_metric"}},
        )
        self.assertTrue(self.manager.apply(request).ok)
        update = self.edit_request({"entity": "category", "action": "update", "entity_id": "lab_domain", "values": {"description": "Reviewed description"}})
        self.assertTrue(self.manager.apply(update).ok)
        remove = self.edit_request(
            {"entity": "membership", "action": "unassign", "values": {"category_id": "lab_domain", "parameter_id": "sample_metric"}},
            {"entity": "parameter", "action": "delete", "entity_id": "sample_metric"},
            {"entity": "category", "action": "delete", "entity_id": "lab_domain"},
        )
        self.assertTrue(self.manager.apply(remove).ok)
        self.assertTrue(self.manager.validate().ok)

    def test_dry_run_stale_writes_and_strict_requests_do_not_change_files(self):
        request = self.edit_request({"entity": "category", "action": "update", "entity_id": "vlan", "values": {"description": "New description"}})
        before = self.manager.inspect().revision
        self.assertTrue(self.manager.apply(request, dry_run=True).ok)
        self.assertEqual(self.manager.inspect().revision, before)
        applied = self.manager.apply(request)
        self.assertTrue(applied.ok)
        self.assertEqual(self.manager.apply(request).issues[0].code, "STALE_REVISION")
        malformed = {**request, "actor": 12}
        self.assertEqual(self.manager.apply(malformed).issues[0].code, "INVALID_REQUEST")
        self.assertEqual(self.manager.inspect().revision, applied.revision)

    def test_dangling_membership_alias_conflicts_and_id_renames_are_rejected(self):
        changes = [
            {"entity": "membership", "action": "unassign", "values": {"category_id": "vlan", "parameter_id": "vlan_id"}},
            {"entity": "category", "action": "create", "entity_id": "other", "values": {"display_name": "VLAN"}},
            {"entity": "parameter", "action": "update", "entity_id": "vlan_id", "values": {"parameter_id": "renamed"}},
            {"entity": "parameter", "action": "update", "entity_id": "vlan_id", "values": {"value_type": "string"}},
        ]
        before = self.manager.inspect().revision
        for change in changes:
            with self.subTest(change=change):
                self.assertFalse(self.manager.apply(self.edit_request(change)).ok)
                self.assertEqual(self.manager.inspect().revision, before)

    def test_published_identity_cannot_be_deleted_and_retirement_requires_publish(self):
        result = self.manager.apply(self.edit_request({"entity": "operation", "action": "delete", "entity_id": "create_vlan"}))
        self.assertEqual(result.issues[0].code, "PUBLISHED_DEPENDENCY")
        request = self.edit_request({"entity": "operation", "action": "retire", "entity_id": "create_vlan"})
        self.assertTrue(self.manager.apply(request).ok)
        with snapshot_scope(self.baseline):
            self.assertEqual(catalog.get_operation("create_vlan")["status"], "active")
        published = self.manager.publish(self.publish_request())
        self.assertTrue(published.ok, published)
        from app.knowledge.runtime import active_snapshot
        with snapshot_scope(active_snapshot(self.releases)), self.assertRaises(KeyError):
            load_schema("create_vlan")

    def test_contract_edit_preview_and_publish_preserve_live_requirements_until_activation(self):
        operation = "create_vlan"
        contract = {"version": 2,
                    "mappings": [row for row in self.read("operation_parameters") if row["operation_id"] == operation],
                    "rules": [row for row in self.read("operation_rules") if row["operation_id"] == operation],
                    "templates": [row for row in self.read("template_bindings") if row["operation_id"] == operation]}
        for name in ("mappings", "rules", "templates"):
            for row in contract[name]:
                row["operation_version"] = 2
        next(row for row in contract["mappings"] if row["field_path"] == "name").update(required=True, required_order=1)
        for binding in contract["templates"]:
            binding["input_contract"]["optional_defaults"].pop("name", None)
        applied = self.manager.apply(self.edit_request({"entity": "contract", "action": "replace", "entity_id": operation, "values": contract}))
        self.assertTrue(applied.ok, applied)
        with snapshot_scope(self.baseline):
            self.assertNotIn("name", load_schema(operation)["required"])
        self.assertIn("name", self.manager.preview_schema(operation, "cisco").data["schema"]["required"])
        self.assertTrue(self.manager.publish(self.publish_request()).ok)

    def test_inactive_draft_can_be_authored_incrementally_but_not_published_incomplete(self):
        request = self.edit_request({"entity": "operation", "action": "create", "entity_id": "new_vlan_op",
            "values": {"category_id": "vlan", "display_name": "New VLAN behavior"}})
        result = self.manager.apply(request)
        self.assertTrue(result.ok, result)
        self.assertTrue(result.warnings)
        self.assertFalse(self.manager.validate().ok)
        self.assertFalse(self.manager.publish(self.publish_request()).ok)
        deletion = self.edit_request({"entity": "operation", "action": "delete", "entity_id": "new_vlan_op"})
        self.assertTrue(self.manager.apply(deletion).ok)

    def test_export_import_roundtrip_and_asset_mismatch(self):
        bundle = self.manager.export().data["bundle"]
        applied = self.manager.apply(self.edit_request({"entity": "category", "action": "update", "entity_id": "vlan", "values": {"description": "changed"}}))
        request = {"expected_revision": applied.revision, "actor": "test", "reason": "Restore metadata", "bundle": bundle}
        self.assertTrue(self.manager.import_catalog(request).ok)
        self.assertEqual(self.manager.export().data["bundle"]["catalogs"], bundle["catalogs"])
        request["expected_revision"] = self.manager.inspect().revision
        request["bundle"] = deepcopy(bundle)
        request["bundle"]["asset_hashes"] = {}
        self.assertEqual(self.manager.import_catalog(request).issues[0].code, "ASSET_MISMATCH")

    def test_cli_returns_json_result_and_nonzero_for_invalid_request(self):
        with patch("sys.stdout", StringIO()) as output:
            code = main(["--project", str(self.base), "inspect"])
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(output.getvalue())["ok"])
        path = self.root / "bad-request.json"
        path.write_text('{"actor": 1}', encoding="utf-8")
        with patch("sys.stdout", StringIO()) as output:
            code = main(["--project", str(self.base), "apply", str(path)])
        self.assertEqual(code, 1)
        self.assertFalse(json.loads(output.getvalue())["ok"])

    def test_writes_require_published_runtime_and_publication_checks_expected_draft(self):
        with patch("app.knowledge.management.active_snapshot", return_value=None):
            request = self.edit_request({"entity": "category", "action": "update", "entity_id": "vlan", "values": {"description": "changed"}})
            self.assertEqual(self.manager.apply(request).issues[0].code, "PUBLICATION_REQUIRED")
        request = self.publish_request()
        request["expected_revision"] = "stale"
        self.assertEqual(self.manager.publish(request).issues[0].code, "STALE_REVISION")


if __name__ == "__main__":
    unittest.main()
