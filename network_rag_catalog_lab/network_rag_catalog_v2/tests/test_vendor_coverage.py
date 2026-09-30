from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from app.api.contracts import EditRequest
from app.knowledge.management import KnowledgeManagementService
from app.knowledge.models import Operation, TemplateBinding
from app.knowledge.publication import build_documents
from app.knowledge.runtime import KnowledgeSnapshot
from app.knowledge.vendor_coverage import (
    coverage_report, prepare_coverage_request, read_scope, validate_vendor_knowledge,
)


class VendorCoverageTests(unittest.TestCase):
    """One read-only catalog validation; no live LLM or workspace mutations."""

    @classmethod
    def setUpClass(cls):
        cls.manager = KnowledgeManagementService()
        cls.before = cls.manager.store.snapshot()
        # Exercise a first application even after the workspace has been activated.
        cls.before = deepcopy(cls.before)
        for op in cls.before["catalogs"]["operations"]:
            op.pop("vendor_knowledge", None)
        cls.spec = read_scope()
        cls.request = prepare_coverage_request(cls.before, cls.spec, actor="test", reason="Coverage regression")
        cls.catalogs = deepcopy(cls.before["catalogs"])
        for change in EditRequest.model_validate(cls.request).changes:
            cls.manager._change(cls.catalogs, change)
        cls.service, cls.schemas, _ = cls.manager._validate(cls.catalogs, cls.before["sources"], complete=True)
        cls.bindings = [TemplateBinding.model_validate(row) for row in cls.catalogs["template_bindings"]]

    def test_exact_requested_scope_and_honest_counts(self):
        self.assertEqual({key: len(value) for key, value in self.spec["categories"].items()},
                         {"vlan": 4, "interface": 9, "static_routing": 4, "ospf": 9, "acl": 5, "qos": 7})
        report = coverage_report(self.catalogs, self.spec)
        self.assertEqual(report["operation_count"], 38)
        self.assertEqual(report["vendor_intent_count"], 114)
        self.assertTrue(report["complete_intent_coverage"])
        self.assertFalse(report["complete_generation_coverage"])
        for vendor, expected in (("cisco", 38), ("huawei", 10), ("juniper", 12)):
            self.assertEqual(report["vendors"][vendor]["intents"], 38)
            self.assertEqual(report["vendors"][vendor]["generation_supported"], expected)

    def test_only_metadata_changes_and_reapplication_preserves_notes(self):
        for name in self.catalogs:
            if name != "operations":
                self.assertEqual(self.catalogs[name], self.before["catalogs"][name])
        for old, new in zip(self.before["catalogs"]["operations"], self.catalogs["operations"]):
            self.assertEqual(old, {key: value for key, value in new.items() if key != "vendor_knowledge"})
        after = {**self.before, "catalogs": deepcopy(self.catalogs)}
        op = next(row for row in after["catalogs"]["operations"] if row["operation_id"] == "modify_vlan")
        op["vendor_knowledge"]["huawei"]["reason"] = "Engineer-reviewed remaining work."
        self.assertIsNone(prepare_coverage_request(after, self.spec, actor="test", reason="Resume"))

    def test_false_support_claims_are_rejected_before_publication(self):
        for vendor, status in (("huawei", "generation_supported"), ("cisco", "blocked_unverified")):
            op = next(deepcopy(row) for row in self.catalogs["operations"] if row["operation_id"] == "modify_vlan")
            op["vendor_knowledge"][vendor]["status"] = status
            with self.subTest(vendor=vendor), self.assertRaisesRegex(ValueError, "contradicts template"):
                validate_vendor_knowledge([Operation.model_validate(op)], self.bindings)
        op["vendor_knowledge"]["cisco"]["status"] = "generation_supported"
        op["vendor_knowledge"]["huawei"]["requirements"] = []
        with self.assertRaisesRegex(ValueError, "actionable requirements"):
            validate_vendor_knowledge([Operation.model_validate(op)], self.bindings)

    def test_every_vendor_intent_is_in_retrieval_content_and_metadata(self):
        documents = build_documents(self.service.list_operations(True), self.schemas, "a" * 32, self.service, self.bindings)
        docs = {row["id"]: row for row in documents}
        for op in self.catalogs["operations"]:
            if not op.get("vendor_knowledge"):
                continue
            with self.subTest(operation=op["operation_id"]):
                doc = docs[op["operation_id"]]
                support = json.loads(doc["metadata"]["vendor_support"])
                self.assertEqual({row["vendor"] for row in support["vendors"]}, set(self.spec["vendors"]))
                for row in support["vendors"]:
                    self.assertTrue(row["intent_known"])
                    self.assertIn(row["reason"], doc["page_content"])
                    if row["status"] == "blocked_unverified":
                        self.assertIn(row["vendor"], support["unimplemented_vendors"])
                        self.assertFalse(any(profile["vendor"] == row["vendor"] for profile in support["profiles"]))

    def test_blocked_combinations_cannot_select_a_template(self):
        snapshot = object.__new__(KnowledgeSnapshot)
        snapshot.service = self.service
        snapshot._manifest = {"template_bindings": self.catalogs["template_bindings"]}
        profiles = {"cisco": ("iosxe", "17.9"), "huawei": ("vrp", "V200R024C10"), "juniper": ("junos", "23.4")}
        with patch.object(snapshot, "verify"), patch.object(snapshot, "assert_active"):
            for row in coverage_report(self.catalogs, self.spec)["rows"]:
                vendor = row["vendor"]
                device = {"vendor": vendor, "platform": profiles[vendor][0], "version": profiles[vendor][1]}
                if not row["has_binding"]:
                    with self.subTest(row=row["operation_id"], vendor=vendor), self.assertRaisesRegex(ValueError, "Intent recognized; configuration generation blocked"):
                        snapshot.binding(device, row["operation_id"])
            self.assertEqual(snapshot.binding({"vendor": "cisco", "platform": "iosxe", "version": "17.9"}, "modify_vlan")["vendor"], "cisco")

    def test_unknown_inactive_or_misclassified_operations_stop_coverage(self):
        for change in ({"operation_id": "not_present"}, {"status": "inactive"}, {"category_id": "qos"}):
            catalogs = deepcopy(self.catalogs)
            next(row for row in catalogs["operations"] if row["operation_id"] == "create_vlan").update(change)
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, "missing, inactive or miscategorized"):
                coverage_report(catalogs, self.spec)


if __name__ == "__main__":
    unittest.main()
