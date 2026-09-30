from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from app import catalog
from app.config import BASE_DIR, CATALOG_FILE, CATEGORIES_FILE, INVENTORY_FILE, PARAMETERS_FILE, TEMPLATES_DIR
from app.knowledge.file_repository import FileKnowledgeRepository
from app.knowledge.models import Category, Operation, ParameterDefinition
from app.knowledge.services import KnowledgeService
from app.knowledge.runtime import snapshot_scope
from app.parameters.schema_loader import load_schema
from app.templates.template_selector import select_template


class KnowledgeRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(snapshot_scope(None))
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.files = {name: Path(directory.name) / f"{name}.json" for name in ("categories", "operations", "parameters")}
        self.data = {
            "categories": [{"category_id": "vlan", "display_name": "VLAN", "aliases": ["vlan"]}],
            "operations": [{
                "operation_id": "create_vlan", "category_id": "vlan", "display_name": "Create VLAN",
                "schema_path": "data/operations/vlan/create_vlan/schema.json",
            }],
            "parameters": [{"parameter_id": "vlan_id", "display_name": "VLAN ID", "value_type": "integer"}],
        }
        for name, records in self.data.items():
            self.write(name, records)
        self.repository = self.make_repository()
        self.service = KnowledgeService(self.repository)

    def write(self, name, records):
        self.files[name].write_text(json.dumps(records), encoding="utf-8")

    def make_repository(self):
        return FileKnowledgeRepository(
            categories_file=self.files["categories"], operations_file=self.files["operations"],
            parameters_file=self.files["parameters"],
        )

    def test_typed_records_preserve_legacy_defaults_and_omitted_keys(self):
        self.assertIsInstance(self.service.get_category("vlan"), Category)
        self.assertIsInstance(self.service.get_parameter("vlan_id"), ParameterDefinition)
        operation = self.service.get_operation("create_vlan")
        self.assertIsInstance(operation, Operation)
        self.assertEqual((operation.status, operation.version), ("active", 1))
        self.assertEqual(operation.to_legacy_dict(), self.data["operations"][0])
        self.service.validate_metadata()

    def test_extension_metadata_roundtrips_for_each_record_kind(self):
        for name, records in self.data.items():
            records[0]["future_metadata"] = {"labels": ["keep"]}
            self.write(name, records)
            loaded = getattr(self.repository, f"list_{name}")()
            self.assertEqual([record.to_legacy_dict() for record in loaded], records)

    def test_ids_are_frozen_and_returned_mutable_metadata_is_isolated(self):
        self.data["categories"][0]["future_metadata"] = {"labels": ["keep"]}
        self.write("categories", self.data["categories"])
        category = self.service.get_category("vlan")
        with self.assertRaises(ValidationError):
            category.category_id = "renamed"
        category.aliases.append("not persistent")
        category.model_extra["future_metadata"]["labels"].clear()
        self.assertEqual(self.service.get_category("vlan").to_legacy_dict(), self.data["categories"][0])

    def test_cache_changes_only_after_explicit_reload(self):
        self.assertEqual(self.service.get_category("vlan").display_name, "VLAN")
        updated = deepcopy(self.data["categories"])
        updated[0]["display_name"] = "Virtual LAN"
        self.write("categories", updated)
        self.assertEqual(self.service.get_category("vlan").display_name, "VLAN")
        self.service.reload()
        self.assertEqual(self.service.get_category("vlan").display_name, "Virtual LAN")

    def test_invalid_reload_fails_without_stale_fallback_and_recovers_after_fix(self):
        self.service.list_categories()
        self.files["categories"].write_text("{broken", encoding="utf-8")
        self.service.reload()
        with self.assertRaisesRegex(ValueError, "Invalid JSON catalog"):
            self.service.list_categories()
        self.write("categories", self.data["categories"])
        self.assertEqual(self.service.get_category("vlan").display_name, "VLAN")

    def test_missing_file_does_not_use_stale_cache_after_reload(self):
        self.service.list_parameters()
        self.files["parameters"].unlink()
        self.service.reload()
        with self.assertRaises(FileNotFoundError):
            self.service.list_parameters()

    def test_invalid_shapes_and_records_are_rejected_with_file_context(self):
        for raw in ({}, None, "array expected", [None], [1], [[]]):
            with self.subTest(raw=raw):
                self.write("categories", raw)
                self.repository.reload()
                with self.assertRaises(ValueError) as raised:
                    self.repository.list_categories()
                self.assertIn(str(self.files["categories"]), str(raised.exception))

    def test_model_validation_is_strict_without_coercion_or_new_lifecycle_states(self):
        invalid = [
            ("categories", "category_id", None), ("categories", "category_id", ""),
            ("categories", "category_id", "../vlan"), ("categories", "category_id", 1),
            ("categories", "display_name", "   "), ("categories", "aliases", "vlan"),
            ("categories", "aliases", [" "]), ("categories", "aliases", [1]),
            ("operations", "version", True), ("operations", "version", "2"),
            ("operations", "version", 1.5), ("operations", "version", 0),
            ("operations", "status", "draft"), ("operations", "schema_path", ""),
            ("parameters", "value_type", "enum"), ("parameters", "value_type", None),
        ]
        for name, key, value in invalid:
            with self.subTest(name=name, key=key, value=value):
                records = deepcopy(self.data[name])
                records[0][key] = value
                self.write(name, records)
                self.repository.reload()
                with self.assertRaises(ValueError):
                    getattr(self.repository, f"list_{name}")()

    def test_duplicate_ids_are_rejected_for_each_catalog(self):
        for name in self.data:
            with self.subTest(name=name):
                self.write(name, self.data[name] * 2)
                self.service.reload()
                with self.assertRaisesRegex(ValueError, "catalog IDs"):
                    self.service.validate_metadata()
                self.write(name, self.data[name])

    def test_unknown_category_and_conflicting_inactive_alias_are_rejected(self):
        other = {**self.data["operations"][0], "operation_id": "delete_vlan", "category_id": "missing"}
        self.write("operations", [other])
        with self.assertRaisesRegex(ValueError, "unknown category missing"):
            self.service.validate_metadata()
        other.update(category_id="vlan", display_name="Delete VLAN", status="inactive", aliases=[" CREATE VLAN "])
        self.write("operations", [self.data["operations"][0], other])
        self.service.reload()
        with self.assertRaisesRegex(ValueError, "multiple owners"):
            self.service.validate_metadata()

    def test_inactive_filtering_and_missing_id_errors_match_legacy_facade(self):
        inactive = {**self.data["operations"][0], "operation_id": "delete_vlan", "display_name": "Delete VLAN", "status": "inactive"}
        self.write("operations", [self.data["operations"][0], inactive])
        with patch.object(catalog, "_knowledge", self.service):
            self.assertEqual(catalog.load_operations(), self.data["operations"])
            self.assertEqual(catalog.load_operations(True), [self.data["operations"][0], inactive])
            for getter, key, value in ((catalog.get_operation, "operation_id", "delete_vlan"),
                                       (catalog.get_category, "category_id", "missing"),
                                       (catalog.get_parameter, "parameter_id", "missing")):
                with self.assertRaises(KeyError) as raised:
                    getter(value)
                self.assertEqual(raised.exception.args[0], f"Unknown {key}: {value}")
            self.assertEqual(catalog.parameter_label("not_registered"), "not registered")

    def test_facade_returns_defensive_dicts_and_reload_updates_schema_labels(self):
        with patch.object(catalog, "_knowledge", self.service):
            category = catalog.get_category("vlan")
            category["aliases"].append("must not leak")
            self.assertEqual(catalog.load_categories(), self.data["categories"])
            self.data["parameters"][0]["display_name"] = "Virtual LAN identifier"
            self.service.list_parameters()
            self.write("parameters", self.data["parameters"])
            catalog.reload_catalog()
            self.assertEqual(catalog.get_parameter("vlan_id"), self.data["parameters"][0])
            self.assertEqual(load_schema("create_vlan")["properties"]["vlan_id"]["title"], "Virtual LAN identifier")

    def test_repository_instances_do_not_share_cache(self):
        self.repository.list_categories()
        self.data["categories"][0]["display_name"] = "Virtual LAN"
        self.write("categories", self.data["categories"])
        other = self.make_repository()
        self.assertEqual(other.list_categories()[0].display_name, "Virtual LAN")
        self.assertEqual(self.repository.list_categories()[0].display_name, "VLAN")


class CatalogCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(snapshot_scope(None))

    def test_all_authoritative_records_roundtrip_through_public_facade(self):
        catalog.reload_catalog()
        for file, loader, getter, key in (
            (CATEGORIES_FILE, catalog.load_categories, catalog.get_category, "category_id"),
            (CATALOG_FILE, lambda: catalog.load_operations(True), catalog.get_operation, "operation_id"),
            (PARAMETERS_FILE, catalog.load_parameters, catalog.get_parameter, "parameter_id"),
        ):
            with self.subTest(file=file):
                expected = json.loads(file.read_text(encoding="utf-8"))
                self.assertEqual(loader(), expected)
                for record in expected:
                    if record.get("status", "active") == "active":
                        self.assertEqual(getter(record[key]), record)
        catalog.validate_catalog()

    def test_schemas_match_legacy_reads_for_all_existing_vendor_profiles(self):
        operations = {item["operation_id"]: item for item in json.loads(CATALOG_FILE.read_text(encoding="utf-8"))}
        parameters = {item["parameter_id"]: item for item in json.loads(PARAMETERS_FILE.read_text(encoding="utf-8"))}
        devices = json.loads(INVENTORY_FILE.read_text(encoding="utf-8"))
        for operation_id in operations:
            for target in [None, *([device] for device in devices), devices]:
                with self.subTest(operation=operation_id, target=target):
                    actual = load_schema(operation_id, target)
                    with patch("app.parameters.schema_loader.get_operation", side_effect=lambda key: deepcopy(operations[key])), \
                         patch("app.parameters.schema_loader.get_parameter", side_effect=lambda key: deepcopy(parameters[key])):
                        expected = load_schema(operation_id, target)
                    self.assertEqual(actual, expected)

    def test_template_paths_and_operation_discovery_are_unchanged(self):
        operations = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
        devices = json.loads(INVENTORY_FILE.read_text(encoding="utf-8"))
        expected_terms = set()
        for operation in operations:
            if operation.get("status", "active") != "active":
                continue
            for phrase in [operation["display_name"], *operation.get("aliases", [])]:
                expected_terms.add((phrase.strip().lower(), operation["operation_id"]))
            self.assertTrue((BASE_DIR / operation["schema_path"]).is_file())
            for device in devices:
                self.assertEqual(select_template(device, operation["operation_id"]),
                                 TEMPLATES_DIR / device["vendor"] / operation["category_id"] / operation["operation_id"] / "template.j2")
        self.assertEqual(set(catalog.operation_terms()), expected_terms)
        categories = json.loads(CATEGORIES_FILE.read_text(encoding="utf-8"))
        for category in categories:
            for phrase in [category["category_id"], *category.get("aliases", [])]:
                self.assertEqual(catalog.category_for_text(phrase), category["category_id"])


if __name__ == "__main__":
    unittest.main()
