from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from app import catalog
from app.config import BASE_DIR, CATALOG_FILE, CATEGORIES_FILE, CATEGORY_PARAMETERS_FILE, OPERATION_PARAMETERS_FILE, OPERATION_RULES_FILE, PARAMETERS_FILE
from app.knowledge.file_repository import FileKnowledgeRepository
from app.knowledge.migration import build_category_parameter_backfill, schema_parameter_references
from app.knowledge.models import CategoryParameter, ParameterDefinition
from app.knowledge.services import KnowledgeService


class CategoryParameterTests(unittest.TestCase):
    def setUp(self):
        from app.knowledge.runtime import snapshot_scope
        self.enterContext(snapshot_scope(None))
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.data = {}
        self.files = {}
        for name, source in (
            ("categories", CATEGORIES_FILE), ("parameters", PARAMETERS_FILE),
            ("operations", CATALOG_FILE), ("category_parameters", CATEGORY_PARAMETERS_FILE),
            ("operation_parameters", OPERATION_PARAMETERS_FILE), ("operation_rules", OPERATION_RULES_FILE),
        ):
            self.files[name] = self.root / f"{name}.json"
            self.data[name] = json.loads(source.read_text(encoding="utf-8"))
            if name == "operations":
                for operation in self.data[name]:
                    operation.update(schema_source="legacy", mapping_mode="compare")
            self.files[name].write_text(json.dumps(self.data[name]), encoding="utf-8")
        self.repository = FileKnowledgeRepository(
            categories_file=self.files["categories"], parameters_file=self.files["parameters"],
            operations_file=self.files["operations"],
        )
        self.service = KnowledgeService(self.repository)

    def write(self, name, records):
        self.files[name].write_text(json.dumps(records), encoding="utf-8")
        self.service.reload()

    def test_memberships_match_read_only_backfill_for_all_existing_operations(self):
        before = {path: path.read_bytes() for path in self.files.values()}
        report = build_category_parameter_backfill(self.service, BASE_DIR)
        self.assertEqual(report["memberships"], self.data["category_parameters"])
        self.assertEqual(len(report["memberships"]), 22)
        self.assertEqual({row["category_id"] for row in report["memberships"]},
                         {"vlan", "ospf", "bgp", "isis", "static_routing", "ip_address"})
        self.assertEqual({row["operation_id"] for row in report["evidence"]},
                         {row["operation_id"] for row in self.data["operations"]})
        self.assertEqual({path: path.read_bytes() for path in self.files.values()}, before)
        self.assertEqual(build_category_parameter_backfill(self.service, BASE_DIR), report)

    def test_nested_ospf_name_is_interface_not_vlan_name(self):
        report = build_category_parameter_backfill(self.service, BASE_DIR)
        evidence = [row for row in report["evidence"] if row["operation_id"] == "configure_ospf"]
        name = next(row for row in evidence if row["field_path"] == "interfaces[].name")
        self.assertEqual(name["parameter_id"], "interface")
        self.assertTrue(name["explicit_reference"])
        self.assertEqual(next(row for row in evidence if row["field_path"] == "interfaces")["value_type"], "array")
        self.assertNotIn("name", [record.parameter_id for record in self.service.parameters_for_category("ospf")])
        self.assertIn("name", [record.parameter_id for record in self.service.parameters_for_category("vlan")])

    def test_membership_rejects_policy_or_duplicate_definition_fields(self):
        row = {"category_id": "vlan", "parameter_id": "vlan_id"}
        self.assertEqual(CategoryParameter.model_validate(row).model_dump(), row)
        for key, value in (("required", True), ("optional", False), ("value_type", "integer"),
                           ("display_name", "ID"), ("aliases", ["id"]), ("validation_rules", [])):
            with self.subTest(key=key), self.assertRaises(ValidationError):
                CategoryParameter.model_validate({**row, key: value})

    def test_shared_definitions_reject_operation_rules_but_keep_metadata(self):
        definition = {"parameter_id": "sample", "display_name": "Sample", "value_type": "integer"}
        for key, value in (("required", True), ("optional", True), ("minimum", 1), ("enum", [1, 2]),
                           ("validation_rules", []), ("format", "ipv4"), ("items", {}), ("default", 1)):
            with self.subTest(key=key), self.assertRaisesRegex(ValidationError, "Operation rules belong"):
                ParameterDefinition.model_validate({**definition, key: value})
        extended = {**definition, "future_metadata": {"owner": "network"}}
        self.assertEqual(ParameterDefinition.model_validate(extended).to_legacy_dict(), extended)

    def test_duplicate_memberships_and_dangling_references_fail(self):
        rows = self.data["category_parameters"]
        cases = [
            (rows + [rows[0]], "Duplicate category parameter"),
            (rows + [{"category_id": "absent", "parameter_id": "interface"}], "unknown category"),
            (rows + [{"category_id": "ospf", "parameter_id": "absent"}], "unknown parameter"),
        ]
        for records, message in cases:
            with self.subTest(message=message):
                self.write("category_parameters", records)
                with self.assertRaisesRegex(ValueError, message):
                    self.service.validate_category_parameters()

    def test_shared_parameter_reuses_central_definition_across_categories(self):
        categories = [row.category_id for row in self.service.list_category_parameters() if row.parameter_id == "interface"]
        self.assertEqual(set(categories), {"ospf", "isis", "ip_address"})
        parameters = deepcopy(self.data["parameters"])
        next(row for row in parameters if row["parameter_id"] == "interface")["display_name"] = "Network port"
        self.write("parameters", parameters)
        for category in categories:
            definition = next(record for record in self.service.parameters_for_category(category) if record.parameter_id == "interface")
            self.assertEqual(definition.display_name, "Network port")

    def test_alias_collisions_are_scoped_to_category_and_include_ids_and_labels(self):
        parameters = deepcopy(self.data["parameters"])
        description = next(row for row in parameters if row["parameter_id"] == "description")
        description["aliases"] = [" PORT "]
        self.write("parameters", parameters)
        self.service.validate_category_parameters()  # BGP has no interface member.
        self.write("category_parameters", self.data["category_parameters"] + [{"category_id": "ospf", "parameter_id": "description"}])
        for alias in (" PORT ", " INTERFACE ", " interface "):
            with self.subTest(alias=alias):
                description["aliases"] = [alias]
                self.write("parameters", parameters)
                with self.assertRaisesRegex(ValueError, "Category ospf parameter alias.*multiple owners"):
                    self.service.validate_category_parameters()

        area = next(row for row in parameters if row["parameter_id"] == "area")
        area["aliases"] = ["port"]
        self.write("parameters", parameters)
        with self.assertRaisesRegex(ValueError, "multiple owners"):
            build_category_parameter_backfill(self.service, BASE_DIR)

    def test_unused_registered_parameters_can_be_exposed_without_altering_schemas(self):
        self.write("category_parameters", self.data["category_parameters"] + [{"category_id": "vlan", "parameter_id": "description"}])
        with patch.object(catalog, "_knowledge", self.service):
            catalog.validate_catalog()
            self.assertIn("description", [row["parameter_id"] for row in catalog.parameters_for_category("vlan")])
            from app.parameters.schema_loader import load_schema
            self.assertNotIn("description", load_schema("create_vlan")["properties"])

    def test_runtime_catalog_gate_rejects_missing_nested_membership(self):
        rows = [row for row in self.data["category_parameters"] if row != {"category_id": "ospf", "parameter_id": "interface"}]
        self.write("category_parameters", rows)
        with patch.object(catalog, "_knowledge", self.service):
            with self.assertRaisesRegex(ValueError, r"Operation configure_ospf:.*interfaces\[\]\.name"):
                catalog.validate_catalog()

    def test_missing_membership_file_never_triggers_silent_auto_backfill(self):
        self.repository.list_category_parameters()
        self.files["category_parameters"].unlink()
        self.service.reload()
        self.service.validate_metadata()  # The Phase 1 API does not depend on memberships.
        with self.assertRaises(FileNotFoundError):
            self.service.list_category_parameters()
        report = build_category_parameter_backfill(self.service, BASE_DIR)
        self.assertEqual(report["memberships"], self.data["category_parameters"])
        self.assertFalse(self.files["category_parameters"].exists())

    def test_new_facade_reads_are_defensive_and_preserve_old_global_results(self):
        with patch.object(catalog, "_knowledge", self.service):
            self.assertEqual(catalog.load_parameters(), self.data["parameters"])
            rows = catalog.load_category_parameters("ospf")
            self.assertTrue(all(row["category_id"] == "ospf" for row in rows))
            rows[0]["parameter_id"] = "mutated"
            parameters = catalog.parameters_for_category("ospf")
            parameters[0]["aliases"].append("must not leak")
            self.assertNotIn("mutated", [row["parameter_id"] for row in catalog.load_category_parameters("ospf")])
            self.assertNotIn("must not leak", catalog.parameters_for_category("ospf")[0]["aliases"])
            for reader in (catalog.load_category_parameters, catalog.parameters_for_category):
                with self.assertRaisesRegex(KeyError, "Unknown category_id: absent"):
                    reader("absent")

    def test_membership_cache_reloads_without_changing_old_constructor_contract(self):
        self.assertEqual(len(self.repository.list_category_parameters()), 22)
        self.files["category_parameters"].write_text("[]", encoding="utf-8")
        self.assertEqual(len(self.repository.list_category_parameters()), 22)
        self.service.reload()
        self.assertEqual(self.repository.list_category_parameters(), [])
        with patch.object(catalog, "_knowledge", self.service), self.assertRaisesRegex(ValueError, "does not expose"):
            catalog.validate_catalog()

    def test_inactive_operation_still_contributes_backfill_evidence(self):
        operations = deepcopy(self.data["operations"])
        next(row for row in operations if row["operation_id"] == "configure_bgp_neighbor")["status"] = "inactive"
        self.write("operations", operations)
        report = build_category_parameter_backfill(self.service, BASE_DIR)
        self.assertIn({"category_id": "bgp", "parameter_id": "description"}, report["memberships"])
        self.assertTrue(any(row["operation_id"] == "configure_bgp_neighbor" for row in report["evidence"]))

    def test_explicit_ids_prevent_bare_name_type_collisions(self):
        schema = {"type": "object", "properties": {
            "name": {"type": "string"},
            "interfaces": {"type": "array", "items": {"type": "object", "properties": {
                "name": {"type": "integer", "x-parameter-id": "vlan_id"},
            }}},
        }}
        references = schema_parameter_references(schema, self.service.list_parameters())
        self.assertEqual([(ref.field_path, ref.parameter_id) for ref in references],
                         [("name", "name"), ("interfaces", "interfaces"), ("interfaces[].name", "vlan_id")])
        schema["properties"]["interfaces"]["items"]["properties"]["name"]["type"] = "string"
        with self.assertRaisesRegex(ValueError, r"Parameter 'vlan_id' at 'interfaces\[\]\.name'.*registry specifies 'integer'"):
            schema_parameter_references(schema, self.service.list_parameters())

    def test_unknown_or_invalid_explicit_ids_never_fall_back_to_names_or_aliases(self):
        for field, property_schema in (
            ("port", {"type": "string"}),  # Alias of interface, not a canonical ID.
            ("name", {"type": "string", "x-parameter-id": "absent"}),
            ("name", {"type": "string", "x-parameter-id": None}),
            ("name", {"type": "string", "x-parameter-id": ["interface", "name"]}),
        ):
            with self.subTest(field=field, schema=property_schema), self.assertRaisesRegex(ValueError, "Unknown parameter"):
                schema_parameter_references({"type": "object", "properties": {field: property_schema}}, self.service.list_parameters())
        references = schema_parameter_references(
            {"type": "object", "properties": {"port": {"type": "string", "x-parameter-id": "interface"}}},
            self.service.list_parameters(),
        )
        self.assertEqual(references[0].parameter_id, "interface")

    def test_unresolved_structures_and_ambiguous_paths_block_partial_backfill(self):
        schemas = [
            {"type": "invalid"},
            {"type": "object", "$ref": "#/$defs/hidden", "$defs": {"hidden": {"type": "object"}}},
            {"type": "object", "allOf": [{"properties": {"name": {"type": "string"}}}]},
            {"type": "object", "additionalProperties": {"type": "string"}},
            {"type": "object", "properties": {"interface": {}}},
            {"type": "object", "properties": {"interface": {"type": ["string", "null"]}}},
            {"type": "object", "properties": {"interfaces": {"type": "array"}}},
            {"type": "object", "properties": {"interfaces": {"type": "array", "items": {"type": "string", "x-parameter-id": "interface"}}}},
            {"type": "object", "properties": {"nested.name": {"type": "string", "x-parameter-id": "interface"}}},
        ]
        for schema in schemas:
            with self.subTest(schema=schema), self.assertRaises(ValueError):
                schema_parameter_references(schema, self.service.list_parameters())

    def test_bad_backfill_reports_operation_and_does_not_overwrite_registry(self):
        operation = deepcopy(self.data["operations"][0])
        operation["schema_path"] = "example_schema.json"
        self.write("operations", [operation])
        (self.root / "example_schema.json").write_text(
            json.dumps({"type": "object", "properties": {"absent": {"type": "string"}}}), encoding="utf-8",
        )
        before = self.files["category_parameters"].read_bytes()
        with self.assertRaisesRegex(ValueError, "Operation create_vlan:.*Unknown parameter"):
            build_category_parameter_backfill(self.service, self.root)
        self.assertEqual(self.files["category_parameters"].read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
