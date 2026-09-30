from contextlib import ExitStack
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from app.config import BASE_DIR
from app.devices.context_validator import normalize_parameters_for_device, validate_device_context
from app.knowledge.pack_review import read_pack, prepare_request, rehearse
from app.knowledge.runtime import snapshot_scope
from app.parameters.schema_loader import load_schema
from app.parameters.validator import validate_parameter_result
from app.templates.renderer import render


PACKS = BASE_DIR / "knowledge_packs"
DOMAINS = ("vlan", "interface", "static_routing", "ospf", "acl", "qos")


class ExpansionPackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stack = ExitStack()
        cls.addClassCleanup(cls.stack.close)
        cls.manager, cls.snapshot, cls.reports = cls.stack.enter_context(rehearse([PACKS / name for name in DOMAINS]))
        cls.devices = json.loads((PACKS / "fixtures/devices.json").read_text(encoding="utf-8"))
        cls.cases = [case for domain in DOMAINS[2:] for case in json.loads((PACKS / domain / "cases.json").read_text(encoding="utf-8"))]
        cls.case_map = {case["operation_id"]: case for case in cls.cases}
        cls.inventory = cls.manager.base / "data/inventory/devices.json"
        original = json.loads(cls.inventory.read_text(encoding="utf-8"))
        cls.inventory.write_text(json.dumps(original + cls.devices), encoding="utf-8")

    def setUp(self):
        self.enterContext(snapshot_scope(self.snapshot))
        self.enterContext(patch("app.context.DATA_DIR", self.manager.base / "data"))
        self.enterContext(patch("app.devices.inventory.INVENTORY_FILE", self.inventory))
        for target in ("app.llm.llm", "app.planner.intent_planner.llm", "app.parameters.parameter_extractor.llm"):
            self.enterContext(patch(target)).invoke.return_value.content = "null"

    def issues(self, operation, parameters, device=None):
        device = device or self.devices[0]
        schema = load_schema(operation, [device])
        category = next(row.category_id for row in self.snapshot.service.list_operations() if row.operation_id == operation)
        values = normalize_parameters_for_device(parameters, device)
        return [vars(issue) for issue in validate_parameter_result(values, schema).issues] + validate_device_context(operation, category, values, [device])

    def params(self, operation):
        return deepcopy(self.case_map[operation]["parameters"])

    def test_all_new_routing_security_qos_contracts_and_golden_commands(self):
        for case in self.cases:
            with self.subTest(operation=case["operation_id"]):
                self.assertEqual(self.issues(case["operation_id"], case["parameters"]), [])
                text = render(self.devices[0], case["operation_id"], case["parameters"])
                self.assertIn(case["expected"], text)
                self.assertNotIn("None", text)
                self.assertFalse(any(line.strip() != "exit" and line.rstrip().endswith(" exit") for line in text.splitlines()))
                self.assertNotIn("{{", text)
        self.assertEqual(len(self.snapshot.manifest["schemas"]), 44)
        self.assertEqual(len(self.snapshot.manifest["template_bindings"]), 78)

    def test_all_additional_vendor_bindings_and_no_fallback(self):
        from test_vlan_interface_packs import EXAMPLES
        for device in self.devices[1:]:
            for operation in ("set_interface_description", "set_interface_admin_state", "assign_vlan_to_trunk_port", "set_native_vlan"):
                params = deepcopy(EXAMPLES[operation][0])
                params["interface"] = device["interfaces"][1]["name"]
                with self.subTest(vendor=device["vendor"], operation=operation):
                    self.assertEqual(self.issues(operation, params, device), [])
                    output = render(device, operation, params)
                    self.assertIn(params["interface"], output)
                    self.assertNotIn(" quit", output.replace("\n quit", ""))
                    if operation == "assign_vlan_to_trunk_port":
                        self.assertNotIn("undo", output)
                        self.assertNotIn("delete", output)
            with self.assertRaises(ValueError):
                render(device, "configure_port_channel", EXAMPLES["configure_port_channel"][0])
        for operation in ("add_default_route", "add_floating_static_route"):
            self.assertEqual(self.issues(operation, self.params(operation), self.devices[2]), [])
            self.assertIn("qualified-next-hop", render(self.devices[2], operation, self.params(operation)))

    def test_reapplication_preserves_authority_and_original_operations(self):
        self.assertEqual(self.manager.inspect().data["authority"], "sqlite")
        for name in DOMAINS:
            self.assertIsNone(prepare_request(self.manager, read_pack(PACKS / name), actor="test", reason="Idempotence"))
        for operation in ("configure_ospf", "configure_bgp_neighbor", "configure_interface_ip", "configure_static_route", "remove_static_route"):
            self.assertIsNotNone(load_schema(operation))

    def test_new_canonical_prompts_extract_all_explicit_fields_without_a_model(self):
        from app.pipeline import _process_intent
        from app.planner.models import OperationIntent
        for case in self.cases:
            with self.subTest(operation=case["operation_id"]):
                tasks = _process_intent(OperationIntent("example", case["prompt"], target_text="SW1"))
                self.assertEqual(tasks[0].operation_id, case["operation_id"])
                self.assertEqual(tasks[0].parameters, case["parameters"], tasks[0].issues)
                self.assertEqual(tasks[0].status, "validated", tasks[0].issues)

    def test_network_prefixes_and_metric_are_not_silently_reinterpreted(self):
        from app.parameters.parameter_extractor import extract_parameter_result
        params = self.params("add_floating_static_route")
        self.assertTrue(self.issues("add_floating_static_route", {**params, "destination": "10.50.0.7/16"}))
        for value in ("::/0", "10.50.0.0/-1", "10.50.0.0/33"):
            self.assertTrue(self.issues("add_floating_static_route", {**params, "destination": value}))
        extracted = extract_parameter_result("next_hop 192.0.2.2; metric 200", load_schema("add_default_route"))
        self.assertNotIn("preference", extracted.parameters)
        self.assertTrue(any(item["field"] == "preference" for item in extracted.candidates))

    def test_floating_routes_require_primary_higher_preference_and_reachable_hop(self):
        params = self.params("add_floating_static_route")
        for change in ({"preference": 10}, {"preference": -1}, {"preference": 255},
                       {"next_hop": "198.51.100.5"}, {"next_hop": "192.0.2.1"}, {"next_hop": "192.0.2.3"},
                       {"destination": "10.60.0.0/16"}):
            self.assertTrue(self.issues("add_floating_static_route", {**params, **change}), change)

    def test_ospf_context_scope_and_no_empty_area(self):
        for operation, changes in {
            "enable_ospf_process": [{"process_id": 100}],
            "set_ospf_router_id": [{"process_id": 999}],
            "create_ospf_area": [{"area": "0"}, {"area_type": "normal"}],
            "assign_interface_to_ospf_area": [{"area": "9"}, {"interface": "GigabitEthernet1/0/1"}],
            "configure_passive_interface": [{"interface": "GigabitEthernet1/0/3"}],
            "advertise_network": [{"network_prefix": "198.51.100.0/24"}],
            "configure_ospf_redistribution": [{"route_policy": "UNKNOWN"}, {"redistribution_source": "bgp"}],
        }.items():
            for change in changes:
                self.assertTrue(self.issues(operation, {**self.params(operation), **change}), (operation, change))
        device = deepcopy(self.devices[0])
        device["resources"]["route_policies"][0]["bounded"] = False
        self.assertTrue(self.issues("configure_ospf_redistribution", self.params("configure_ospf_redistribution"), device))

    def test_acl_never_infers_any_protocol_ports_or_resource_existence(self):
        params = self.params("add_acl_rule")
        for key in ("source_prefix", "destination_prefix", "acl_action"):
            missing = {k: v for k, v in params.items() if k != key}
            self.assertTrue(self.issues("add_acl_rule", missing))
        for change in ({"source_prefix": "any"}, {"ip_protocol": "icmp"}, {"source_port": -1},
                       {"destination_port": 65536}, {"acl_rule_id": 10}, {"acl_name": "ABSENT"},
                       {"acl_name": "STAFF;shutdown"}, {"log": "false"}):
            self.assertTrue(self.issues("add_acl_rule", {**params, **change}), change)
        self.assertTrue(self.issues("create_acl", {"acl_name": "STAFF", "description": "test"}))
        self.assertTrue(self.issues("delete_acl_rule", {"acl_name": "STAFF", "acl_rule_id": 1}))

    def test_acl_replacement_and_delete_only_touch_selected_ace(self):
        output = render(self.devices[0], "modify_acl_rule", self.params("modify_acl_rule"))
        self.assertIn("\n no 10\n 10 permit tcp ", output)
        self.assertNotIn("no ip access-list", output)
        self.assertTrue(self.issues("modify_acl_rule", {"acl_name": "STAFF", "acl_rule_id": 10}))
        output = render(self.devices[0], "delete_acl_rule", self.params("delete_acl_rule"))
        self.assertEqual(output, "ip access-list extended STAFF\n no 10\n exit\n")

    def test_composite_acl_keys_isolate_rule_numbers_and_are_symmetric(self):
        from app.pipeline import _cross_task_issues
        from app.planner.models import PlannedTask
        def task(identity, operation, acl, rule):
            return PlannedTask(identity, "test", "acl", operation, {"acl_name": acl, "acl_rule_id": rule}, [], device_id="lab-sw1")
        left = task("one", "modify_acl_rule", "STAFF", 10)
        for acl, rule, expected in (("STAFF", 10, True), ("GUEST", 10, False), ("STAFF", 20, False)):
            right = task("two", "delete_acl_rule", acl, rule)
            self.assertEqual(bool(_cross_task_issues([left, right])), expected)
            self.assertEqual(bool(_cross_task_issues([right, left])), expected)

    def test_attachments_do_not_replace_other_policies(self):
        for operation, key in (("apply_acl_to_interface", "acl_bindings"), ("apply_qos_policy_to_interface", "qos_bindings"),
                               ("configure_shaping", "qos_bindings"), ("configure_policing", "qos_bindings")):
            params = self.params(operation)
            device = deepcopy(self.devices[0])
            device["interfaces"][-1][key][params["direction"]] = "OTHER"
            self.assertTrue(self.issues(operation, params, device))

    def test_qos_units_ranges_direction_missing_action_and_queue_capacity(self):
        for operation, changes in {
            "create_classifier": [{"dscp_values": [64]}, {"dscp_values": [-1]}, {"dscp_values": [46, 46]}, {"match_mode": "all"}],
            "configure_scheduler": [{"bandwidth_bps": 20000001}, {"bandwidth_bps": -10}, {"policy_name": "ABSENT"}],
            "configure_shaping": [{"direction": "ingress"}, {"rate_bps": "10Mbps"}, {"rate_bps": 2000000000}],
            "configure_policing": [{"direction": "egress"}, {"burst_bytes": 0}, {"exceed_action": "transmit"}],
        }.items():
            for change in changes:
                self.assertTrue(self.issues(operation, {**self.params(operation), **change}), (operation, change))
        missing = self.params("configure_policing")
        missing.pop("exceed_action")
        self.assertTrue(self.issues("configure_policing", missing))
        device = deepcopy(self.devices[0])
        device["capabilities"]["qos_queue_count"] = 1
        self.assertTrue(self.issues("create_qos_policy", self.params("create_qos_policy"), device))

    def test_nested_policy_terms_and_class_references(self):
        params = self.params("create_qos_policy")
        for terms in ([{"classifier_name": "UNKNOWN", "bandwidth_bps": 20000000}],
                      [{"classifier_name": "VOICE"}], params["policy_terms"] * 2):
            self.assertTrue(self.issues("create_qos_policy", {**params, "policy_terms": terms}))
        text = render(self.devices[0], "classify_by_dscp", self.params("classify_by_dscp"))
        self.assertEqual(text, "class-map match-any VOICE\n no match dscp 46\n match dscp 46\n exit\n")

    def test_resource_suggestions_and_one_field_typed_clarification(self):
        from app.context import parameter_options
        from app.pipeline import _finalize_task, resume_task
        choices = parameter_options("delete_acl_rule", self.devices[0], "acl_rule_id", {"acl_name": "STAFF"}, "test")
        self.assertEqual([row["value"] for row in choices], [10])
        params = self.params("configure_policing")
        params.pop("burst_bytes")
        task = _finalize_task(intent_id="test", request_text="test", category="qos", operation_id="configure_policing",
                              parameters=params, parameter_provenance={}, target_refs=["SW1"])
        self.assertEqual(task.questions[0]["field_path"], "burst_bytes")
        self.assertEqual(resume_task(task, "-1").status, "needs_clarification")
        self.assertEqual(resume_task(task, "10000").status, "validated")

    def test_missing_facts_fail_closed_and_same_request_creation_is_not_assumed(self):
        device = deepcopy(self.devices[0])
        device.pop("resources")
        for case in self.cases:
            self.assertTrue(self.issues(case["operation_id"], case["parameters"], device))
        self.assertTrue(self.issues("apply_acl_to_interface", {**self.params("apply_acl_to_interface"), "acl_name": "NEW_ACL"}))

    def test_malformed_facts_and_previous_dscp_mismatch_fail_closed(self):
        for key, value in (("routes", None), ("classifiers", [None]), ("qos_policies", [{"name": "QOS_BASE", "kind": "bandwidth", "classes": None}])):
            device = deepcopy(self.devices[0])
            device["resources"][key] = value
            operation = {"routes": "add_default_route", "classifiers": "create_qos_policy", "qos_policies": "apply_qos_policy_to_interface"}[key]
            self.assertTrue(self.issues(operation, self.params(operation), device))
        self.assertTrue(self.issues("classify_by_dscp", {**self.params("classify_by_dscp"), "previous_dscp_values": [34]}))
        self.assertTrue(self.issues("create_classifier", {**self.params("create_classifier"), "classifier_name": "class-default"}))

    def test_mixed_legacy_route_and_new_qos_resource_conflicts(self):
        from app.pipeline import _cross_task_issues
        from app.planner.models import PlannedTask
        def task(identity, operation, parameters):
            return PlannedTask(identity, "test", "static_routing", operation, parameters, [], device_id="lab-sw1")
        default = task("one", "add_default_route", {"next_hop": "192.0.2.2"})
        removal = task("two", "remove_static_route", {"destination": "0.0.0.0/0", "next_hop": "192.0.2.2"})
        self.assertTrue(_cross_task_issues([default, removal]))
        shaper = task("one", "configure_shaping", {"policy_name": "NEW", "interface": "GigabitEthernet1/0/5", "direction": "egress"})
        policy = task("two", "create_qos_policy", {"policy_name": "NEW", "policy_terms": []})
        self.assertTrue(_cross_task_issues([shaper, policy]))

    def test_incomplete_security_task_blocks_whole_request_rendering(self):
        from app.pipeline import _finalize_task, refresh_plan, resume_task
        from app.planner.models import ExecutionPlan
        def task(identity, operation, category, params):
            return _finalize_task(intent_id=identity, request_text="test", category=category, operation_id=operation,
                                  parameters=params, parameter_provenance={}, target_refs=["SW1"])
        params = self.params("add_acl_rule")
        params.pop("source_prefix")
        plan = ExecutionPlan("test", tasks=[task("route", "add_default_route", "static_routing", self.params("add_default_route")),
                                            task("acl", "add_acl_rule", "acl", params)])
        refresh_plan(plan)
        self.assertEqual(plan.status, "needs_clarification")
        self.assertFalse(any(item.configs for item in plan.tasks))
        self.assertEqual(plan.tasks[1].questions[0]["field_path"], "source_prefix")
        plan.tasks[1] = resume_task(plan.tasks[1], "10.1.0.0/16")
        refresh_plan(plan)
        self.assertEqual(plan.status, "ready", plan.issues)
        self.assertTrue(all(item.configs for item in plan.tasks))

    def test_forward_retirement_and_failed_publication_preserve_release(self):
        from app.knowledge.runtime import active_pointer
        with rehearse([PACKS / "vlan"]) as (manager, snapshot, _):
            request = {"expected_revision": manager.inspect().revision, "actor": "test", "reason": "Forward compensation rehearsal",
                       "changes": [{"entity": "operation", "action": "retire", "entity_id": "modify_vlan"}]}
            self.assertTrue(manager.apply(request).ok)
            publish = {"expected_revision": manager.inspect().revision, "expected_release": snapshot.release_id,
                       "actor": "test", "reason": "Retire staged operation", "mode": "offline"}
            result = manager.publish(publish)
            self.assertTrue(result.ok, result)
            pointer = active_pointer(manager.releases)
            self.assertNotEqual(pointer["release_id"], snapshot.release_id)
            stale = manager.publish(publish)
            self.assertFalse(stale.ok)
            self.assertEqual(active_pointer(manager.releases), pointer)

    def test_reviewed_asset_hash_mismatch_is_rejected(self):
        import tempfile
        import shutil
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "pack"
            shutil.copytree(PACKS / "vlan", root)
            asset = next((root / "assets").rglob("*.j2"))
            asset.write_text("unreviewed", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                read_pack(root)

    def test_wrong_routing_context_and_incomplete_interface_membership_block(self):
        for operation in ("add_default_route", "configure_passive_interface"):
            device = deepcopy(self.devices[0])
            device["resources"]["routing_context"] = "tenant"
            self.assertTrue(self.issues(operation, self.params(operation), device))
        device = deepcopy(self.devices[0])
        device["interfaces"][-1]["routing_context"] = "tenant"
        self.assertTrue(self.issues("add_default_route", self.params("add_default_route"), device))
        self.assertTrue(self.issues("assign_interface_to_ospf_area", self.params("assign_interface_to_ospf_area"), device))

    def test_malformed_suggestions_do_not_break_clarification(self):
        from app.devices.resource_options import resource_options
        for value in (None, [None], [{"name": "STAFF", "rules": None}]):
            device = deepcopy(self.devices[0])
            device["resources"]["acls"] = value
            self.assertEqual(resource_options("acl_delete_v1", device, "acl_rule_id", {"acl_name": "STAFF"}, "test"), [])

    def test_unregistered_derivations_and_composite_keys_cannot_publish(self):
        from app.knowledge.publication import _validate_context_rules
        from app.knowledge.rule_registry import derive_template_value
        with self.assertRaises(ValueError):
            derive_template_value("load_python", {})
        with self.assertRaises(ValueError):
            _validate_context_rules({"operations": {"delete_acl_rule": {"composite_keys": [{"kind": "acl", "fields": ["absent"]}]}}},
                                    {"delete_acl_rule": load_schema("delete_acl_rule")})


if __name__ == "__main__":
    unittest.main()
