from copy import deepcopy
import json
import os
import unittest
from unittest.mock import patch

from app.config import BASE_DIR
from app.knowledge.runtime import snapshot_scope


class NativeVendorRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, {"NETWORK_RAG_RUNTIME": "files"}))
        self.enterContext(snapshot_scope(None))
        from app.catalog import reload_catalog
        reload_catalog()
        self.devices = {d["hostname"]: d for d in json.loads((BASE_DIR / "data/inventory/devices.json").read_text())}
        self.cases = json.loads((BASE_DIR / "tests/fixtures/vendor_runtime_cases.json").read_text())

    def case(self, operation, vendor):
        return next(row for row in self.cases if row["operation_id"] == operation and row["vendor"] == vendor)

    def test_all_114_contracts_context_and_rendering(self):
        from app.parameters.schema_loader import load_schema
        from app.parameters.validator import validate_parameter_result
        from app.devices.context_validator import validate_device_context
        from app.templates.renderer import render
        self.assertEqual(len(self.cases), 114)
        for row in self.cases:
            with self.subTest(operation=row["operation_id"], vendor=row["vendor"]):
                device, params = self.devices[row["device"]], row["parameters"]
                if row["operation_id"] == "modify_vlan" and row["vendor"] != "cisco":
                    with self.assertRaisesRegex(ValueError, "generation blocked"):
                        render(device, row["operation_id"], params)
                    continue
                result = validate_parameter_result(params, load_schema(row["operation_id"], [device]))
                self.assertTrue(result.valid, result.issues)
                self.assertEqual(validate_device_context(row["operation_id"], row["category"], params, [device]), [])
                output = render(device, row["operation_id"], params)
                self.assertTrue(output.strip())
                self.assertNotIn("None", output)
                self.assertNotIn("{{", output)

    def test_all_native_prompts_extract_and_reach_ready(self):
        from app.pipeline import run
        for target in ("app.llm.llm", "app.planner.intent_planner.llm", "app.parameters.parameter_extractor.llm"):
            self.enterContext(patch(target)).invoke.return_value.content = "null"
        for row in self.cases:
            if row["vendor"] == "cisco":
                continue
            with self.subTest(operation=row["operation_id"], vendor=row["vendor"]):
                plan = run(row["prompt"], verbose=False)
                if row["operation_id"] == "modify_vlan":
                    self.assertEqual(plan.status, "needs_clarification")
                    self.assertTrue(any(issue["type"] == "UNSUPPORTED_OPERATION" for issue in plan.tasks[0].issues))
                    self.assertFalse(plan.tasks[0].configs)
                    continue
                self.assertEqual(plan.status, "ready", [(t.operation_id, t.issues, t.feedback) for t in plan.tasks])
                self.assertEqual(len(plan.tasks), 1)
                self.assertEqual(plan.tasks[0].operation_id, row["operation_id"])
                self.assertEqual(plan.tasks[0].parameters, row["parameters"])
                self.assertEqual(plan.tasks[0].target_devices[0]["hostname"], row["device"])

    def test_native_command_semantics(self):
        from app.templates.renderer import render
        expected = [
            ("rename_vlan", "juniper", "rename vlans STAFF to EMPLOYEES"),
            ("create_classifier", "juniper", "code-points [ 101110 100010 ]"),
            ("configure_scheduler", "huawei", "qos queue 4 wrr weight 20"),
            ("configure_shaping", "huawei", "qos lr cir 100000 kbps"),
            ("configure_policing", "juniper", "family inet policer input NEW_POLICER"),
            ("advertise_network", "juniper", "area 0 interface ge-0/0/5.0"),
        ]
        for op, vendor, fragment in expected:
            row = self.case(op, vendor)
            self.assertIn(fragment, render(self.devices[row["device"]], op, row["parameters"]))

    def test_conflicting_context_remains_rejected(self):
        from app.devices.context_validator import validate_device_context
        edits = [
            ("rename_vlan", "juniper", {"current_vlan_name": "WRONG"}),
            ("modify_acl_rule", "juniper", {"next_rule_id": 999}),
            ("configure_port_channel", "juniper", {"aggregate_interface": "ae99"}),
            ("configure_scheduler", "huawei", {"queue_id": 20}),
            ("configure_shaping", "huawei", {"rate_bps": 999999999999}),
            ("advertise_network", "juniper", {"network_interfaces": ["ge-0/0/99"]}),
            ("configure_ospf_redistribution", "juniper", {"route_policy": "UNKNOWN"}),
        ]
        for op, vendor, change in edits:
            row = deepcopy(self.case(op, vendor))
            row["parameters"].update(change)
            with self.subTest(op=op, vendor=vendor):
                self.assertTrue(validate_device_context(op, row["category"], row["parameters"], [self.devices[row["device"]]]))

    def test_missing_native_field_clarifies_before_mixed_request_renders(self):
        from app.pipeline import run, resume_task, refresh_plan
        for target in ("app.llm.llm", "app.planner.intent_planner.llm", "app.parameters.parameter_extractor.llm"):
            self.enterContext(patch(target)).invoke.return_value.content = "null"
        plan = run('Create VLAN 100 named TEST on SW2; rename vlan, vlan_id 20, new_vlan_name "EMPLOYEES" on SW3', verbose=False)
        self.assertEqual(plan.status, "needs_clarification")
        self.assertFalse(any(t.configs for t in plan.tasks))
        self.assertEqual(plan.tasks[1].questions[0]["field_path"], "current_vlan_name")
        self.assertTrue(plan.tasks[1].questions[0]["options"])
        plan.tasks[1] = resume_task(plan.tasks[1], "STAFF")
        refresh_plan(plan)
        self.assertEqual(plan.status, "ready", [(t.issues, t.feedback) for t in plan.tasks])


if __name__ == "__main__":
    unittest.main()
