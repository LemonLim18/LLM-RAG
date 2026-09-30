from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from app.knowledge import rule_registry
from app.knowledge.runtime import snapshot_scope
from app.knowledge.schema_compiler import compile_schema
from app.parameters.parameter_extractor import extract_parameter_result
from app.parameters.schema_loader import load_schema
from app.parameters.validator import ValidationIssue, validate_parameter_result
from knowledge_fixtures import KnowledgeFixture


def node(kind, identity, *aliases, **rules):
    return {"type": kind, "x-parameter": {"parameter_id": identity,
            "display_name": identity.replace("_", " "), "aliases": list(aliases)}, **rules}


def contract(properties, required=()):
    return {"type": "object", "properties": properties, "required": list(required), "additionalProperties": False}


class ExpansionExtractionTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(snapshot_scope(None))
        self.model = self.enterContext(patch("app.parameters.parameter_extractor.llm"))
        self.model.invoke.return_value.content = "null"
        self.schema = contract({
            "allowed_vlans": node("array", "allowed_vlans", "allowed vlans", items={"type": "integer", "minimum": 1, "maximum": 4094}),
            "dscp_values": node("array", "dscp_values", "dscp values", items={"type": "integer", "minimum": 0, "maximum": 63}),
            "member_interfaces": node("array", "member_interfaces", "members", items={"type": "string"}),
        }, ["allowed_vlans"])

    def test_primitive_lists_are_field_scoped_and_keep_zero(self):
        result = extract_parameter_result("allowed vlans 10,20; dscp values 0 and 46; members Ethernet1/1, Ethernet1/2", self.schema)
        self.assertEqual(result.parameters, {"allowed_vlans": [10, 20], "dscp_values": [0, 46],
                                             "member_interfaces": ["Ethernet1/1", "Ethernet1/2"]})
        self.assertTrue(validate_parameter_result(result.parameters, self.schema).valid)
        self.assertEqual(set(result.provenance.values()), {"deterministic_user"})
        self.model.invoke.assert_not_called()

    def test_json_lists_and_boolean_items_preserve_false(self):
        schema = contract({"flags": node("array", "flags", "flags", items={"type": "boolean"})}, ["flags"])
        for text in ("flags [false, true]", "flags false, true"):
            with self.subTest(text=text):
                self.assertEqual(extract_parameter_result(text, schema).parameters, {"flags": [False, True]})
        self.model.invoke.assert_not_called()

    def test_model_cannot_steal_other_field_values_or_shorten_explicit_lists(self):
        self.model.invoke.return_value.content = '{"parameters":{"allowed_vlans":[10,20]}}'
        result = extract_parameter_result("dscp values 10,20", self.schema)
        self.assertIsNone(result.parameters["allowed_vlans"])
        self.assertEqual(result.parameters["dscp_values"], [10, 20])
        result = extract_parameter_result("allowed vlans 10,20,30", self.schema)
        self.assertEqual(result.parameters["allowed_vlans"], [10, 20, 30])

    def test_ranges_units_disjunctions_and_bad_item_types_do_not_partially_extract(self):
        self.model.invoke.return_value.content = '{"parameters":{"allowed_vlans":[10]}}'
        for value in ('10-20', '10 or 20', '10 to 20', '10 Mbps', '[10, "20"]', '[10, true]', '10,unknown'):
            with self.subTest(value=value):
                result = extract_parameter_result("allowed vlans " + value, self.schema)
                self.assertIsNone(result.parameters["allowed_vlans"])

    def test_explicit_out_of_range_values_reach_schema_validation(self):
        result = extract_parameter_result("allowed vlans -1,4095", self.schema)
        self.assertEqual(result.parameters["allowed_vlans"], [-1, 4095])
        self.assertFalse(validate_parameter_result(result.parameters, self.schema).valid)

    def test_repeated_collection_values_need_clarification(self):
        result = extract_parameter_result("allowed vlans 10,20; allowed vlans 30,40", self.schema)
        self.assertIsNone(result.parameters["allowed_vlans"])
        self.assertEqual(result.candidates[0]["values"], [[10, 20], [30, 40]])

    def test_nested_json_preserves_leaf_association_and_missing_required_fields(self):
        entry = contract({"classifier": {"type": "string"}, "rate": {"type": "integer"},
                          "enabled": {"type": "boolean"}}, ["classifier", "rate"])
        schema = contract({"terms": node("array", "terms", "terms", items=entry)}, ["terms"])
        values = [{"classifier": "voice", "rate": 10, "enabled": False}, {"classifier": "data", "rate": 20}]
        prompt = "terms " + json.dumps(values)
        self.model.invoke.return_value.content = json.dumps({"parameters": {"terms": list(reversed(values))}})
        result = extract_parameter_result(prompt, schema)
        self.assertEqual(result.parameters["terms"], values)
        self.model.invoke.assert_not_called()
        result = extract_parameter_result('terms [{"classifier":"voice"}]', schema)
        issues = validate_parameter_result(result.parameters, schema).issues
        self.assertEqual([(issue.type, issue.field) for issue in issues], [("MISSING", "terms[0].rate")])

    def test_nested_prose_cannot_be_reassembled_into_unproven_objects(self):
        schema = contract({"rule": node("object", "rule", "rule", properties={
            "source": {"type": "string"}, "destination": {"type": "string"}})}, ["rule"])
        self.model.invoke.return_value.content = '{"parameters":{"rule":{"source":"B","destination":"A"}}}'
        result = extract_parameter_result("source A destination B", schema)
        self.assertIsNone(result.parameters["rule"])
        result = extract_parameter_result('rule {"source":"A","destination":"B"}', schema)
        self.assertEqual(result.parameters["rule"], {"source": "A", "destination": "B"})

    def test_duplicate_json_keys_cannot_silently_choose_the_last_value(self):
        schema = contract({"rule": node("object", "rule", "rule", properties={"rate": {"type": "integer"}})}, ["rule"])
        self.model.invoke.return_value.content = '{"parameters":{"rule":{"rate":20}}}'
        result = extract_parameter_result('rule {"rate":10,"rate":20}', schema)
        self.assertIsNone(result.parameters["rule"])

    def test_optional_description_is_extracted_after_required_fields_are_complete(self):
        schema = contract({"vlan_id": node("integer", "vlan_id", "vlan"),
                           "description": node("string", "description", "description")}, ["vlan_id"])
        self.model.invoke.return_value.content = '{"parameters":{"description":"WAN uplink"}}'
        result = extract_parameter_result("VLAN 20 description WAN uplink", schema)
        self.assertEqual(result.parameters, {"vlan_id": 20, "description": "WAN uplink"})
        self.model.invoke.assert_called_once()
        self.model.reset_mock()
        result = extract_parameter_result('VLAN 20 description "WAN uplink"', schema)
        self.assertEqual(result.parameters["description"], "WAN uplink")
        self.model.invoke.assert_not_called()

    def test_absent_optional_fields_do_not_call_model_or_create_questions(self):
        schema = load_schema("create_vlan")
        result = extract_parameter_result("Create VLAN 20 on R1", schema)
        self.assertEqual(result.parameters, {"vlan_id": 20})
        self.assertFalse(result.candidates)
        self.model.invoke.assert_not_called()

    def test_unresolved_optional_value_is_a_question_not_silent_omission(self):
        schema = contract({"description": node("string", "description", "description")})
        result = extract_parameter_result("description WAN uplink", schema)
        self.assertEqual(result.candidates[0]["type"], "UNRESOLVED_VALUE")
        self.assertEqual(result.candidates[0]["field"], "description")
        self.assertLessEqual(self.model.invoke.call_count, 2)

    def test_truncated_description_is_not_accepted(self):
        schema = contract({"description": node("string", "description", "description")})
        self.model.invoke.return_value.content = '{"parameters":{"description":"WAN"}}'
        result = extract_parameter_result("description WAN uplink", schema)
        self.assertNotIn("description", result.parameters)
        self.assertEqual(result.candidates[0]["type"], "UNRESOLVED_VALUE")

    def test_quoted_description_cannot_set_unrelated_fields(self):
        schema = contract({"description": node("string", "description", "description"),
                           "admin_up": node("boolean", "admin_up", "enable"),
                           "vlan_id": node("integer", "vlan_id", "vlan")})
        result = extract_parameter_result('description "enable VLAN 99"', schema)
        self.assertEqual(result.parameters, {"description": "enable VLAN 99"})
        self.assertFalse(result.candidates)
        self.model.invoke.assert_not_called()

    def test_false_optional_value_is_not_lost(self):
        schema = contract({"admin_up": node("boolean", "admin_up", "administrative state")})
        result = extract_parameter_result("administrative state false", schema)
        self.assertIs(result.parameters["admin_up"], False)
        self.model.invoke.assert_not_called()

    def test_requested_fields_do_not_leak_values_or_ambiguities(self):
        result = extract_parameter_result("allowed vlans 10,20; allowed vlans 30; dscp values 0,46", self.schema,
                                          requested_fields=["dscp_values"])
        self.assertEqual(result.parameters, {"dscp_values": [0, 46]})
        self.assertFalse(result.candidates)

    def test_pipeline_asks_for_unresolved_optional_then_resumes(self):
        from app.pipeline import _process_intent, resume_task
        from app.planner.models import OperationIntent
        text = "Configure BGP neighbor 192.0.2.2 local AS 65001 remote AS 65002 description WAN uplink on R1"
        task = _process_intent(OperationIntent("phase-zero", text, target_text="R1"))[0]
        self.assertEqual(task.status, "needs_clarification")
        self.assertEqual(task.questions[0]["field_path"], "description")
        self.assertIn("could not be safely extracted", task.questions[0]["wording"])
        self.assertFalse(task.configs)
        updated = resume_task(task, "WAN uplink")
        self.assertEqual(updated.status, "validated")
        self.assertEqual(updated.parameters["description"], "WAN uplink")

    def test_baseline_golden_prompts_and_model_call_budget(self):
        cases = json.loads((Path(__file__).parent / "fixtures/phase0_extraction_prompts.json").read_text(encoding="utf-8"))
        for case in cases:
            with self.subTest(case=case["id"]):
                self.model.reset_mock()
                self.model.invoke.return_value.content = json.dumps(case.get("model_response"))
                schema = load_schema(case["operation_id"], [{"vendor": "cisco"}])
                result = extract_parameter_result(case["prompt"], schema)
                self.assertEqual(result.parameters, case["parameters"])
                self.assertEqual(self.model.invoke.call_count, case["model_calls"])

    def test_invalid_optional_literal_is_validated_not_silently_omitted(self):
        schema = contract({"description": node("string", "description", "description")})
        result = extract_parameter_result('description "unsafe;command"', schema)
        self.assertEqual(result.parameters["description"], "unsafe;command")
        self.assertTrue(any(issue.type == "UNSAFE_VALUE" for issue in validate_parameter_result(result.parameters, schema).issues))


class ExpansionRegistryTests(KnowledgeFixture, unittest.TestCase):
    def test_default_contracts_still_require_every_legacy_safeguard(self):
        mandatory = list(rule_registry.VALIDATION_HANDLERS)
        self.assertEqual(rule_registry.validate_handler_ids({}), mandatory)
        for handlers in (mandatory[:-1], mandatory + [mandatory[0]], mandatory + ["unreviewed_v1"], [], "safe_strings_v1"):
            with self.subTest(handlers=handlers), self.assertRaises(ValueError):
                rule_registry.validate_handler_ids({"x-validation-handlers": handlers})

    def test_code_reviewed_extension_compiles_and_returns_field_scoped_issues(self):
        handler = lambda params, schema: [ValidationIssue("DOMAIN", "vlan_id", "Test-only constraint.")]
        with patch.dict(rule_registry.ADDITIONAL_VALIDATION_HANDLERS, {"test_rule_v1": handler}):
            rows = self.read("operation_rules")
            root = next(row for row in rows if row["operation_id"] == "create_vlan" and row["field_path"] == "")
            root["keywords"]["x-validation-handlers"] = [*rule_registry.VALIDATION_HANDLERS, "test_rule_v1"]
            self.write("operation_rules", rows)
            schema = compile_schema(self.service, "create_vlan")
            issues = validate_parameter_result({"vlan_id": 20, "name": "bad;value"}, schema).issues
            self.assertTrue(any(issue.type == "UNSAFE_VALUE" for issue in issues))
            self.assertTrue(any(issue.type == "DOMAIN" and issue.field == "vlan_id" for issue in issues))
            with patch.dict(rule_registry.ADDITIONAL_VALIDATION_HANDLERS, {}, clear=True), self.assertRaises(ValueError):
                validate_parameter_result({"vlan_id": 20}, schema)

    def test_extension_cannot_replace_mandatory_handlers_or_import_code(self):
        for additional in ({"safe_strings_v1": lambda params, schema: []}, {"evil": "os.system"}):
            with patch.dict(rule_registry.ADDITIONAL_VALIDATION_HANDLERS, additional), self.assertRaises(ValueError):
                rule_registry.validate_handler_ids({})

    def test_category_alias_validation_uses_extraction_normalization(self):
        original = self.read("parameters")
        memberships = self.read("category_parameters")
        self.write("category_parameters", memberships + [{"category_id": "ospf", "parameter_id": "description"}])
        for alias in ("router-id", "router_id", "Router ID", "!!!"):
            rows = deepcopy(original)
            next(row for row in rows if row["parameter_id"] == "description")["aliases"] = [alias]
            self.write("parameters", rows)
            with self.subTest(alias=alias), self.assertRaises(ValueError):
                self.service.validate_category_parameters()


if __name__ == "__main__":
    unittest.main()
