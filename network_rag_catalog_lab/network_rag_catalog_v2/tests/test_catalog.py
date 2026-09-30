import unittest
from unittest.mock import patch

from app.catalog import load_operations, validate_catalog
from app.devices.context_validator import normalize_parameters_for_device, validate_device_context
from app.devices.inventory import TargetResolutionError, find_user_target_candidates, resolve_targets
from app.parameters.normalizer import normalize_value, prefix_length_from_text
from app.parameters.parameter_extractor import ExtractionResult, extract_parameter_result
from app.parameters.schema_loader import load_schema
from app.parameters.validator import validate_parameter_result, validate_parameters
from app.pipeline import _finalize_task, resume_task
from app.planner.intent_planner import plan_intents
from app.planner.models import PlannedTask
from app.knowledge.runtime import snapshot_scope


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(snapshot_scope(None))
        for target in ("app.llm.llm", "app.planner.intent_planner.llm", "app.parameters.parameter_extractor.llm"):
            self.enterContext(patch(target)).invoke.return_value.content = "null"

    def test_catalog_has_two_or_more_operations_per_category(self):
        validate_catalog()
        counts = {}
        for operation in load_operations():
            self.assertEqual(operation["status"], "active")
            self.assertGreaterEqual(operation["version"], 1)
            counts[operation["category_id"]] = counts.get(operation["category_id"], 0) + 1
        self.assertTrue(all(count >= 2 for count in counts.values()))

    def test_alias_resolves_to_canonical_device(self):
        devices = resolve_targets(["core router 1"])
        self.assertEqual([d["hostname"] for d in devices], ["R1"])
        self.assertEqual(devices[0]["vendor"], "cisco")

    def test_multiple_aliases_resolve_without_duplicates(self):
        devices = resolve_targets(["R1", "core router 1", "R2"])
        self.assertEqual([d["hostname"] for d in devices], ["R1", "R2"])

    def test_group_reference_resolves_to_multiple_devices(self):
        devices = resolve_targets(["core routers"])
        self.assertEqual([d["hostname"] for d in devices], ["R1", "R2"])

    def test_schema_accepts_valid_vlan(self):
        schema = load_schema("create_vlan")
        validate_parameters({"vlan_id": 100, "name": "STAFF"}, schema)

    def test_schema_rejects_unknown_parameter(self):
        schema = load_schema("create_vlan")
        with self.assertRaises(ValueError):
            validate_parameters({"vlan_id": 100, "made_up": True}, schema)

    def test_schema_rejects_missing_required_parameter(self):
        schema = load_schema("configure_bgp_neighbor")
        with self.assertRaises(ValueError):
            validate_parameters({"local_as": 65000}, schema)

    def test_validation_result_reports_missing_null_required_parameter(self):
        schema = load_schema("configure_ospf", resolve_targets(["R2"]))
        result = validate_parameter_result({"process_id": None, "interfaces": None}, schema)
        self.assertFalse(result.valid)
        self.assertEqual([issue.type for issue in result.issues], ["MISSING", "MISSING"])

    def test_context_validation_rejects_unknown_interface(self):
        schema = load_schema("configure_interface_ip")
        validate_parameters({"interface": "GigabitEthernet1/1", "address": "10.1.1.1", "prefix_length": 24}, schema)
        devices = resolve_targets(["R1"])
        issues = validate_device_context(
            "configure_interface_ip",
            "ip_address",
            {"interface": "GigabitEthernet1/1", "address": "10.1.1.1", "prefix_length": 24},
            devices,
        )
        self.assertEqual(issues[0]["type"], "INVALID_INTERFACE")

    def test_context_normalizes_interface_alias_for_device(self):
        devices = resolve_targets(["R1"])
        params = normalize_parameters_for_device({"interface": "Eth1/1"}, devices[0])
        self.assertEqual(params["interface"], "Ethernet1/1")

    def test_unknown_interface_returns_ranked_suggestions(self):
        devices = resolve_targets(["R1"])
        issues = validate_device_context(
            "configure_interface_ip",
            "ip_address",
            {"interface": "GigabitEthernet1/1"},
            devices,
        )
        self.assertIn("Ethernet1/1", issues[0]["suggestions"])

    def test_unknown_target_returns_suggestions_without_selecting_one(self):
        with self.assertRaises(TargetResolutionError) as raised:
            resolve_targets(["core router 9"])
        self.assertEqual(raised.exception.code, "TARGET_NOT_FOUND")
        self.assertIn("R1", raised.exception.suggestions)

    def test_unknown_device_phrase_is_preserved_for_clarification(self):
        self.assertEqual(find_user_target_candidates("Create VLAN 100 on Router 9"), ["Router 9"])

    def test_site_and_role_group_resolves_to_multiple_devices(self):
        devices = resolve_targets(["KL core routers"])
        self.assertEqual([device["hostname"] for device in devices], ["R1", "R2"])

    def test_prefix_normalization_accepts_explicit_netmask(self):
        self.assertEqual(prefix_length_from_text("Use netmask 255.255.255.0"), 24)
        self.assertIsNone(prefix_length_from_text("Ethernet1/1"))
        self.assertEqual(prefix_length_from_text("/24"), 24)
        self.assertEqual(prefix_length_from_text("255.255.255.0", allow_bare_netmask=True), 24)

    def test_address_normalization_splits_cidr_host_value(self):
        value, _ = normalize_value(
            "address",
            "192.0.2.10/24",
            {"type": "string"},
            "Assign 192.0.2.10/24 to Ethernet1/1",
        )
        self.assertEqual(value, "192.0.2.10")

    def test_explicit_catalog_plan_does_not_need_the_llm(self):
        with patch("app.planner.intent_planner.llm") as llm:
            intents = plan_intents(
                "Create VLAN 100 on R1 and remove static route to 10.20.0.0/16 via 192.168.1.1 on R3"
            )
        llm.invoke.assert_not_called()
        self.assertEqual(len(intents), 2)

    def test_explicit_parameters_do_not_need_the_llm(self):
        schema = load_schema("configure_interface_ip")
        with patch("app.parameters.parameter_extractor.llm") as llm:
            result = extract_parameter_result("Configure 192.0.2.1/24 on Ethernet1/1", schema)
        llm.invoke.assert_not_called()
        self.assertEqual(result.parameters["address"], "192.0.2.1")
        self.assertEqual(result.parameters["prefix_length"], 24)

    def test_vendor_specific_ospf_process_requirement(self):
        r2_schema = load_schema("configure_ospf", resolve_targets(["R2"]))
        r3_schema = load_schema("configure_ospf", resolve_targets(["R3"]))
        params = {"interfaces": [{"name": "ge-0/0/0", "area": "0"}]}
        self.assertFalse(validate_parameter_result(params, r2_schema).valid)
        self.assertTrue(validate_parameter_result(params, r3_schema).valid)

    def test_incomplete_task_does_not_block_independent_validation(self):
        ready = _finalize_task(
            intent_id="intent-1",
            request_text="Create VLAN 100 on R1",
            category="vlan",
            operation_id="create_vlan",
            parameters={"vlan_id": 100},
            parameter_provenance={"vlan_id": "user"},
            target_refs=["R1"],
        )
        pending = _finalize_task(
            intent_id="intent-2",
            request_text="Configure OSPF on R2",
            category="ospf",
            operation_id="configure_ospf",
            parameters={"interfaces": None},
            parameter_provenance={},
            target_refs=["R2"],
        )
        self.assertEqual(ready.status, "validated")
        self.assertEqual(ready.configs, [])
        self.assertEqual(pending.status, "needs_clarification")

    def test_numbered_interface_reply_uses_offered_suggestion(self):
        task = PlannedTask(
            intent_id="intent-1",
            request_text="Configure 192.0.2.1/24 on GigabitEthernet1/1 on R1",
            category="ip_address",
            operation_id="configure_interface_ip",
            parameters={"interface": "GigabitEthernet1/1", "address": "192.0.2.1", "prefix_length": 24},
            target_refs=["R1"],
            status="needs_clarification",
            issues=[{
                "type": "INVALID_INTERFACE",
                "field": "interface",
                "message": "R1 has no interface named 'GigabitEthernet1/1'.",
                "suggestions": ["Ethernet1/1", "Loopback0"],
            }],
        )
        extraction = ExtractionResult(parameters={}, provided_fields=[], missing_fields=[], provenance={})
        with patch("app.pipeline.extract_parameter_result", return_value=extraction):
            resumed = resume_task(task, "select 1")
        self.assertEqual(resumed.status, "validated")
        self.assertEqual(resumed.parameters["interface"], "Ethernet1/1")

    def test_clarification_updates_only_the_current_field(self):
        task = _finalize_task(
            intent_id="intent-1",
            request_text="Configure an interface IP on Router 1",
            category="ip_address",
            operation_id="configure_interface_ip",
            parameters={"interface": "Ethernet1/1", "address": None, "prefix_length": None},
            parameter_provenance={},
            target_refs=["R1"],
        )
        empty = ExtractionResult(parameters={}, provided_fields=[], missing_fields=[], provenance={})
        with patch("app.pipeline.extract_parameter_result", return_value=empty):
            rejected_mask = resume_task(task, "255.255.255.0")
            addressed = resume_task(rejected_mask, "192.168.1.1")
            complete = resume_task(addressed, "255.255.255.0")
        self.assertIsNone(rejected_mask.parameters["address"])
        self.assertEqual(addressed.parameters["address"], "192.168.1.1")
        self.assertEqual(complete.parameters["prefix_length"], 24)
        self.assertEqual(complete.status, "validated")

    def test_verified_planner_target_is_retained_from_original_prompt(self):
        from app.devices.target_query import extract_target_queries
        from app.devices.target_resolver import resolve_queries
        from app.devices.inventory import load_inventory
        queries = extract_target_queries("Help configure an IP interface on Router 1", load_inventory())
        self.assertEqual([device["hostname"] for device in resolve_queries(queries)["devices"]], ["R1"])


if __name__ == "__main__":
    unittest.main()
