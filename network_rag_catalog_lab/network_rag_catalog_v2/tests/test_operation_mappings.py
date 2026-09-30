from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from app import catalog
from app.config import BASE_DIR, CATALOG_DIR, INVENTORY_FILE
from app.knowledge.file_repository import FileKnowledgeRepository
from app.knowledge.migration import build_operation_backfill
from app.knowledge.models import Operation, OperationParameterMapping, OperationSchemaRule
from app.knowledge.operation_contracts import project_operation_schema
from app.knowledge.services import KnowledgeService
from app.parameters.fields import parse_answer
from app.parameters.normalizer import canonicalize_parameter_keys, deterministic_values, explicit_alternatives
from app.parameters.parameter_extractor import _contract, _filter_to_schema
from app.parameters.schema_loader import _add_catalog_metadata, load_schema
from app.parameters.validator import validate_parameter_result


class OperationMappingTests(unittest.TestCase):
    def setUp(self):
        from app.knowledge.runtime import snapshot_scope
        self.enterContext(snapshot_scope(None))
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.data = {}
        for name in ("categories", "parameters", "operations", "category_parameters", "operation_parameters", "operation_rules"):
            self.data[name] = json.loads((CATALOG_DIR / f"{name}.json").read_text(encoding="utf-8"))
            if name == "operations":
                for operation in self.data[name]:
                    operation.update(schema_source="legacy", mapping_mode="compare")
            (self.root / f"{name}.json").write_text(json.dumps(self.data[name]), encoding="utf-8")
        self.repository = FileKnowledgeRepository(categories_file=self.root / "categories.json",
                                                   parameters_file=self.root / "parameters.json",
                                                   operations_file=self.root / "operations.json")
        self.service = KnowledgeService(self.repository)
        override = patch.object(catalog, "_knowledge", self.service)
        override.start()
        self.addCleanup(override.stop)

    def write(self, name, records):
        (self.root / f"{name}.json").write_text(json.dumps(records), encoding="utf-8")
        self.service.reload()

    def schema(self, operation_id):
        operation = next(row for row in self.data["operations"] if row["operation_id"] == operation_id)
        return json.loads((BASE_DIR / operation["schema_path"]).read_text(encoding="utf-8"))

    def test_backfill_is_repeatable_read_only_and_matches_all_current_records(self):
        before = {path.name: path.read_bytes() for path in self.root.glob("*.json")}
        result = build_operation_backfill(self.service, BASE_DIR)
        self.assertEqual(result["operation_parameters"], self.data["operation_parameters"])
        self.assertEqual(result["operation_rules"], self.data["operation_rules"])
        self.assertEqual((len(result["operation_parameters"]), len(result["operation_rules"])), (38, 51))
        self.assertEqual(result, build_operation_backfill(self.service, BASE_DIR))
        self.assertEqual({path.name: path.read_bytes() for path in self.root.glob("*.json")}, before)
        for operation in self.data["operations"]:
            report = catalog.compare_operation_schema(operation["operation_id"], self.schema(operation["operation_id"]))
            self.assertTrue(report["matches"])
            self.assertEqual(report["schema_source"], "legacy")

    def test_effective_schemas_match_pre_mapping_loader_for_all_vendor_profiles(self):
        metadata = {row["parameter_id"]: row for row in self.data["parameters"]}

        def legacy_enrich(schema):
            schema = deepcopy(schema)
            for field, node in schema.get("properties", {}).items():
                parameter = metadata[node.get("x-parameter-id", field)]
                node.setdefault("title", parameter["display_name"])
                node["x-parameter"] = deepcopy(parameter)
                if node.get("type") == "object":
                    schema["properties"][field] = legacy_enrich(node)
                elif node.get("type") == "array":
                    node["items"] = legacy_enrich(node["items"])
            return schema

        devices = json.loads(INVENTORY_FILE.read_text(encoding="utf-8"))
        for operation in self.data["operations"]:
            for targets in [None, *([device] for device in devices), devices]:
                with self.subTest(operation=operation["operation_id"], targets=targets):
                    expected = self.schema(operation["operation_id"])
                    required = list(expected.get("required", []))
                    for device in targets or []:
                        for field in expected.get("x-required-by-vendor", {}).get(device["vendor"], []):
                            if field not in required:
                                required.append(field)
                    expected["required"] = required
                    self.assertEqual(load_schema(operation["operation_id"], targets), legacy_enrich(expected))

    def test_required_change_is_operation_local_and_cannot_weaken_runtime_schema(self):
        rows = deepcopy(self.data["operation_parameters"])
        field = next(row for row in rows if row["operation_id"] == "create_vlan" and row["field_path"] == "vlan_id")
        field.update(required=False, required_order=None)
        self.write("operation_parameters", rows)
        catalog.validate_catalog()  # Valid shadow edits are reviewable, not published.
        report = catalog.compare_operation_schema("create_vlan", self.schema("create_vlan"))
        self.assertFalse(report["matches"])
        self.assertEqual(report["differences"][0]["field_path"], "vlan_id")
        self.assertTrue(catalog.compare_operation_schema("delete_vlan", self.schema("delete_vlan"))["matches"])
        self.assertIn("vlan_id", load_schema("create_vlan")["required"])
        self.assertFalse(validate_parameter_result({}, load_schema("create_vlan")).valid)

    def test_rule_and_vendor_drift_is_reported_but_never_used_for_validation(self):
        rows = deepcopy(self.data["operation_rules"])
        next(row for row in rows if row["operation_id"] == "create_vlan" and row["field_path"] == "vlan_id")["keywords"]["maximum"] = 1
        next(row for row in rows if row["operation_id"] == "configure_ospf" and not row["field_path"])["keywords"]["x-required-by-vendor"] = {}
        self.write("operation_rules", rows)
        self.assertFalse(catalog.compare_operation_schema("create_vlan", self.schema("create_vlan"))["matches"])
        self.assertFalse(catalog.compare_operation_schema("configure_ospf", self.schema("configure_ospf"))["matches"])
        self.assertTrue(validate_parameter_result({"vlan_id": 20}, load_schema("create_vlan")).valid)
        self.assertIn("process_id", load_schema("configure_ospf", [{"vendor": "cisco"}])["required"])
        self.assertNotIn("process_id", load_schema("configure_ospf", [{"vendor": "juniper"}])["required"])

    def test_nested_required_flags_order_and_rules_are_preserved(self):
        mappings = {row["field_path"]: row for row in catalog.load_operation_parameters("configure_ospf")}
        self.assertEqual(mappings["interfaces[].name"]["parameter_id"], "interface")
        self.assertEqual((mappings["interfaces[].name"]["required_order"], mappings["interfaces[].area"]["required_order"]), (0, 1))
        self.assertFalse(mappings["process_id"]["required"])
        rules = {row["field_path"]: row["keywords"] for row in catalog.load_operation_rules("configure_ospf")}
        self.assertEqual(rules["interfaces"], {"minItems": 1})
        self.assertEqual(rules["interfaces[]"], {"type": "object", "additionalProperties": False})
        self.assertEqual(rules["interfaces[].name"]["x-parameter-id"], "interface")
        schema = self.schema("configure_ospf")
        schema["properties"]["interfaces"]["items"]["required"].reverse()
        projected = project_operation_schema(self.service.get_operation("configure_ospf"), schema, self.service.list_parameters())
        name = next(row for row in projected["operation_parameters"] if row.field_path == "interfaces[].name")
        self.assertEqual(name.required_order, 1)

    def test_projection_retains_nonstructural_keywords_and_blocks_unsupported_shapes(self):
        schema = self.schema("create_vlan")
        schema["properties"]["name"].update(description="Reviewed annotation", examples=["STAFF"], default="REVIEW_ONLY")
        projected = project_operation_schema(self.service.get_operation("create_vlan"), schema, self.service.list_parameters())
        keywords = next(row.keywords for row in projected["operation_rules"] if row.field_path == "name")
        self.assertEqual(keywords["default"], "REVIEW_ONLY")
        self.assertEqual(keywords["examples"], ["STAFF"])
        self.assertNotIn("type", keywords)
        for mutation in ({"allOf": [{"type": "object"}]}, {"required": ["absent"]},
                         {"x-required-by-vendor": {"cisco": ["absent"]}}):
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                project_operation_schema(self.service.get_operation("create_vlan"), {**schema, **mutation}, self.service.list_parameters())

    def test_mapping_integrity_rejects_duplicate_unknown_and_stale_references(self):
        mutations = [
            {"operation_id": "absent"}, {"operation_version": 999}, {"category_id": "ospf"},
            {"parameter_id": "absent"}, {"position": 999}, {"field_path": "missing_parent.name"},
        ]
        for mutation in mutations:
            rows = deepcopy(self.data["operation_parameters"])
            rows[0].update(mutation)
            self.write("operation_parameters", rows)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.service.validate_operation_records()
        self.write("operation_parameters", self.data["operation_parameters"] + [self.data["operation_parameters"][0]])
        with self.assertRaisesRegex(ValueError, "Duplicate operation mapping"):
            self.service.validate_operation_records()

    def test_rule_integrity_and_required_order_cannot_be_ambiguous(self):
        original = self.data["operation_rules"]
        for rows in (original + [original[0]], original[1:],
                     [dict(original[0], field_path="absent[]"), *original[1:]]):
            self.write("operation_rules", rows)
            with self.assertRaises(ValueError):
                self.service.validate_operation_records()
        self.write("operation_rules", original)
        mappings = deepcopy(self.data["operation_parameters"])
        next(row for row in mappings if row["field_path"] == "interfaces[].area")["required_order"] = 0
        self.write("operation_parameters", mappings)
        with self.assertRaisesRegex(ValueError, "required-field order"):
            self.service.validate_operation_records()

    def test_models_reject_coercion_structural_rules_and_early_authority_switch(self):
        mapping = self.data["operation_parameters"][0]
        for mutation in ({"required": "true"}, {"required": False}, {"operation_version": True},
                         {"position": -1}, {"field_path": "interfaces[0].name"}):
            with self.subTest(mutation=mutation), self.assertRaises(ValidationError):
                OperationParameterMapping.model_validate({**mapping, **mutation})
        for key in ("properties", "items", "required"):
            with self.assertRaises(ValidationError):
                OperationSchemaRule.model_validate({**self.data["operation_rules"][0], "keywords": {key: []}})
        with self.assertRaises(ValidationError):
            Operation.model_validate({**self.data["operations"][0], "schema_source": "compiled"})

    def test_missing_comparison_file_is_not_silently_rebuilt(self):
        (self.root / "operation_rules.json").unlink()
        self.service.reload()
        with self.assertRaises(FileNotFoundError):
            load_schema("create_vlan")
        self.assertEqual(len(build_operation_backfill(self.service, BASE_DIR)["operation_rules"]), 51)
        self.assertFalse((self.root / "operation_rules.json").exists())

    def test_inactive_operations_are_reviewable_without_becoming_selectable(self):
        operations = deepcopy(self.data["operations"])
        operations[0]["status"] = "inactive"
        self.write("operations", operations)
        self.assertTrue(catalog.compare_operation_schema("create_vlan", self.schema("create_vlan"))["matches"])
        self.assertEqual(len(catalog.load_operation_parameters("create_vlan")), 2)
        with self.assertRaises(KeyError):
            catalog.get_operation("create_vlan")

    def test_new_reads_and_reports_are_defensive(self):
        rows = catalog.load_operation_rules("create_vlan")
        rows[0]["keywords"].clear()
        self.assertTrue(catalog.load_operation_rules("create_vlan")[0]["keywords"])
        report = catalog.compare_operation_schema("create_vlan", self.schema("create_vlan"))
        report["differences"].append({"bad": True})
        self.assertTrue(catalog.compare_operation_schema("create_vlan", self.schema("create_vlan"))["matches"])
        for reader in (catalog.load_operation_parameters, catalog.load_operation_rules):
            with self.assertRaises(KeyError):
                reader("absent")

    def test_projection_cache_never_hides_schema_or_candidate_changes(self):
        schema = self.schema("create_vlan")
        self.assertTrue(catalog.compare_operation_schema("create_vlan", schema)["matches"])
        schema["properties"]["vlan_id"]["maximum"] = 4000
        self.assertFalse(catalog.compare_operation_schema("create_vlan", schema)["matches"])
        self.assertTrue(catalog.compare_operation_schema("create_vlan", self.schema("create_vlan"))["matches"])
        rules = deepcopy(self.data["operation_rules"])
        rules[0]["keywords"]["additionalProperties"] = True
        self.write("operation_rules", rules)
        self.assertFalse(catalog.compare_operation_schema("create_vlan", self.schema("create_vlan"))["matches"])

    def test_comparison_cli_fails_on_drift_and_orphan_records(self):
        from app.knowledge.migration import main

        rules = deepcopy(self.data["operation_rules"])
        rules[0]["keywords"]["additionalProperties"] = True
        self.write("operation_rules", rules)
        with patch("sys.argv", ["migration", "--compare"]), \
             patch("app.knowledge.services.KnowledgeService", return_value=self.service), \
             patch("sys.stdout", StringIO()) as output:
            with self.assertRaises(SystemExit) as raised:
                main()
            self.assertEqual(raised.exception.code, 1)
            self.assertFalse(json.loads(output.getvalue())[0]["matches"])
            self.write("operation_rules", self.data["operation_rules"])
            mappings = deepcopy(self.data["operation_parameters"])
            mappings.append({**mappings[0], "operation_id": "absent"})
            self.write("operation_parameters", mappings)
            with self.assertRaisesRegex(ValueError, "Unknown/stale operation"):
                main()

    def test_nested_metadata_and_extraction_use_canonical_identity_without_renaming_keys(self):
        item_schema = load_schema("configure_ospf")["properties"]["interfaces"]["items"]
        self.assertEqual(_contract(item_schema)["properties"]["name"]["display_name"], "interface")
        self.assertEqual(canonicalize_parameter_keys({"port": "Ethernet1/1"}, item_schema), {"name": "Ethernet1/1"})
        values, _ = _filter_to_schema("on Ethernet1/1 in area 0", {"port": "Ethernet1/1", "area": "0"}, item_schema)
        self.assertEqual(values, {"name": "Ethernet1/1", "area": "0"})
        self.assertNotIn("vlan name", item_schema["properties"]["name"]["x-parameter"]["aliases"])

    def test_mapped_normalization_and_ambiguity_preserve_payload_paths(self):
        schema = {"type": "object", "properties": {"mask": {"type": "integer", "x-parameter-id": "prefix_length"},
                                                    "port": {"type": "string", "x-parameter-id": "interface"}}}
        self.assertEqual(parse_answer("255.255.255.0", "mask", schema["properties"]["mask"]), 24)
        values = deterministic_values("on Ethernet1/1 using netmask 255.255.255.0", schema)
        self.assertEqual((values["port"][0], values["mask"][0]), ("Ethernet1/1", 24))
        self.assertEqual(explicit_alternatives("on Ethernet1/1 or Ethernet1/2", schema)["port"], ["Ethernet1/1", "Ethernet1/2"])
        self.assertNotIn("mask", deterministic_values("on Ethernet1/1", schema))

    def test_duplicate_semantic_slots_do_not_get_arbitrary_alias_or_fallback_binding(self):
        schema = {"properties": {"first": {"type": "string", "x-parameter-id": "interface"},
                                  "second": {"type": "string", "x-parameter-id": "interface"}}}
        self.assertEqual(canonicalize_parameter_keys({"port": "Ethernet1/1"}, schema), {})
        self.assertEqual(canonicalize_parameter_keys({"first": "Ethernet1/1"}, schema), {"first": "Ethernet1/1"})
        self.assertEqual(deterministic_values("on Ethernet1/1", schema), {})

    def test_shared_display_name_propagates_and_overrides_stale_schema_title(self):
        parameters = deepcopy(self.data["parameters"])
        next(row for row in parameters if row["parameter_id"] == "interface")["display_name"] = "Network port"
        self.write("parameters", parameters)
        schema = load_schema("configure_ospf")
        self.assertEqual(schema["properties"]["interfaces"]["items"]["properties"]["name"]["title"], "Network port")
        raw = {"properties": {"name": {"type": "string", "x-parameter-id": "interface", "title": "Stale title"}}}
        self.assertEqual(_add_catalog_metadata(raw)["properties"]["name"]["title"], "Network port")
        self.assertEqual(load_schema("configure_interface_ip")["properties"]["interface"]["title"], "Network port")
        self.assertEqual(self.schema("configure_ospf")["properties"]["interfaces"]["items"]["required"], ["name", "area"])


if __name__ == "__main__":
    unittest.main()
