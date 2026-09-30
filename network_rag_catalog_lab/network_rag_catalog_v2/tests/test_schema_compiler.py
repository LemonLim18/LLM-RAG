import json
import unittest
from unittest.mock import patch

from app import catalog
from app.knowledge.runtime import snapshot_scope
from app.knowledge.schema_compiler import compile_schema
from app.parameters.schema_loader import _add_catalog_metadata, _apply_vendor_requirements, load_schema
from app.parameters.validator import validate_parameter_result
from knowledge_fixtures import KnowledgeFixture


class SchemaCompilerTests(KnowledgeFixture, unittest.TestCase):
    def test_conditional_and_dependent_requirements_are_field_scoped(self):
        rows = self.read("operation_rules")
        root = next(row for row in rows if row["operation_id"] == "create_vlan" and row["field_path"] == "")
        root["keywords"]["x-conditional-required"] = [{"field": "vlan_id", "equals": 20, "required": ["name"]}]
        self.write("operation_rules", rows)
        schema = compile_schema(self.service, "create_vlan")
        self.assertTrue(validate_parameter_result({"vlan_id": 21}, schema).valid)
        issues = validate_parameter_result({"vlan_id": 20}, schema).issues
        self.assertEqual([(issue.type, issue.field) for issue in issues], [("MISSING", "name")])
        self.assertTrue(validate_parameter_result({"vlan_id": 20, "name": "STAFF"}, schema).valid)
        root["keywords"].pop("x-conditional-required")
        root["keywords"]["dependentRequired"] = {"vlan_id": ["name"]}
        self.write("operation_rules", rows)
        issues = validate_parameter_result({"vlan_id": 21}, compile_schema(self.service, "create_vlan")).issues
        self.assertEqual([(issue.type, issue.field) for issue in issues], [("MISSING", "name")])

    def test_invalid_condition_references_and_normalizers_are_rejected(self):
        from copy import deepcopy
        original = self.read("operation_rules")
        for keywords in ({"dependentRequired": []}, {"dependentRequired": {"name": "vlan_id"}},
                         {"x-conditional-required": [{"field": "absent", "equals": 20, "required": ["name"]}]},
                         {"x-conditional-required": [{"field": "vlan_id", "equals": "20", "required": ["name"]}]}):
            rows = deepcopy(original)
            next(row for row in rows if row["operation_id"] == "create_vlan" and row["field_path"] == "")["keywords"].update(keywords)
            self.write("operation_rules", rows)
            with self.subTest(keywords=keywords), self.assertRaises(ValueError):
                compile_schema(self.service, "create_vlan")
        self.write("operation_rules", original)
        definitions = self.read("parameters")
        definitions[0]["normalizer"] = "unreviewed_python_handler"
        self.write("parameters", definitions)
        with self.assertRaisesRegex(ValueError, "Unknown normalization handler"):
            compile_schema(self.service, "create_vlan")

    def test_nested_conditions_preserve_paths_and_boolean_identity(self):
        from app.knowledge.rule_registry import required_fields
        schema = {"type": "object", "properties": {"entries": {"type": "array", "items": {
            "type": "object", "properties": {"enabled": {"type": "boolean"}, "description": {"type": "string"}},
            "x-conditional-required": [{"field": "enabled", "equals": True, "required": ["description"]}]}}}}
        issues = validate_parameter_result({"entries": [{"enabled": True}]}, schema).issues
        self.assertEqual([(issue.type, issue.field) for issue in issues], [("MISSING", "entries[0].description")])
        item = schema["properties"]["entries"]["items"]
        self.assertEqual(required_fields(item, {"enabled": 1}), [])

    def test_all_legacy_effective_contracts_are_preserved(self):
        profiles = [None, [{"vendor": "cisco"}], [{"vendor": "huawei"}], [{"vendor": "juniper"}],
                    [{"vendor": value} for value in ("cisco", "huawei", "juniper")]]
        with snapshot_scope(None), patch.object(catalog, "_knowledge", self.service):
            for op in self.service.list_operations():
                legacy = json.loads((self.base / op.schema_path).read_text(encoding="utf-8"))
                compiled = compile_schema(self.service, op.operation_id)
                self.assertTrue(self.service.compare_operation_schema(op.operation_id, compiled)["matches"])
                for devices in profiles:
                    with self.subTest(operation=op.operation_id, devices=devices):
                        self.assertEqual(load_schema(op.operation_id, devices),
                                         _add_catalog_metadata(_apply_vendor_requirements(legacy, devices)))

    def test_registry_is_authoritative_and_legacy_files_are_only_evidence(self):
        rules = self.read("operation_rules")
        next(row for row in rules if row["operation_id"] == "create_vlan" and row["field_path"] == "vlan_id")["keywords"]["maximum"] = 100
        self.write("operation_rules", rules)
        with snapshot_scope(None), patch.object(catalog, "_knowledge", self.service):
            self.assertFalse(validate_parameter_result({"vlan_id": 101}, load_schema("create_vlan")).valid)
            self.assertTrue(validate_parameter_result({"vlan_id": 101}, load_schema("delete_vlan")).valid)
        with self.assertRaisesRegex(ValueError, "Legacy schema comparison failed"):
            self.publish(verify_legacy=True)

    def test_missing_items_unknown_keywords_handlers_and_vendor_rules_fail_closed(self):
        original = self.read("operation_rules")
        mutations = [
            ("interfaces", {"unknown_assertion": True}),
            ("", {"x-validation-handlers": ["import_os"]}),
            ("", {"x-required-by-vendor": {"cisco": ["absent"]}}),
            ("interfaces", {"allOf": [{"maxItems": 1}]}),
            ("router_id", {"format": "ipvv4"}),
        ]
        for field, update in mutations:
            rows = json.loads(json.dumps(original))
            next(row for row in rows if row["operation_id"] == "configure_ospf" and row["field_path"] == field)["keywords"].update(update)
            self.write("operation_rules", rows)
            with self.subTest(update=update), self.assertRaises(ValueError):
                compile_schema(self.service, "configure_ospf")
        rows = [row for row in original if not (row["operation_id"] == "configure_ospf" and row["field_path"].startswith("interfaces[]"))]
        self.write("operation_rules", rows)
        with self.assertRaises(ValueError):
            compile_schema(self.service, "configure_ospf")

    def test_required_nested_vendor_and_network_validation_remain_enforced(self):
        with snapshot_scope(None), patch.object(catalog, "_knowledge", self.service):
            ospf = load_schema("configure_ospf", [{"vendor": "cisco"}])
            issues = validate_parameter_result({"interfaces": [{"name": "Ethernet1/1"}]}, ospf).issues
            self.assertTrue({"process_id", "interfaces[0].area"} <= {issue.field for issue in issues})
            for value in (True, -1, "10", 4095):
                self.assertFalse(validate_parameter_result({"vlan_id": value}, load_schema("create_vlan")).valid)
            for address in ("255.255.255.0", "224.0.0.1", "10.0.0.0"):
                self.assertFalse(validate_parameter_result({"interface": "Ethernet1/1", "address": address, "prefix_length": 24}, load_schema("configure_interface_ip")).valid)


if __name__ == "__main__":
    unittest.main()
