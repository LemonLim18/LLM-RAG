from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from app.config import BASE_DIR
from app.devices.context_validator import normalize_parameters_for_device, validate_device_context
from app.knowledge.management import KnowledgeManagementService
from app.knowledge.pack_review import install_reviewed_assets, prepare_request, read_pack
from app.knowledge.runtime import active_snapshot, snapshot_scope
from app.parameters.schema_loader import load_schema
from app.parameters.validator import validate_parameter_result
from app.templates.renderer import render
from knowledge_fixtures import KnowledgeFixture


PACKS = BASE_DIR / "knowledge_packs"
EXAMPLES = {
    "modify_vlan": ({"vlan_id": 20, "vlan_status": "suspend"}, "state suspend"),
    "rename_vlan": ({"vlan_id": 20, "new_vlan_name": "EMPLOYEES"}, "name EMPLOYEES"),
    "set_interface_description": ({"interface": "GigabitEthernet1/0/1", "description": "User port"}, "description User port"),
    "set_interface_admin_state": ({"interface": "GigabitEthernet1/0/1", "admin_up": False}, " shutdown"),
    "configure_access_port": ({"interface": "GigabitEthernet1/0/1", "vlan_id": 20}, "switchport access vlan 20"),
    "configure_trunk_port": ({"interface": "GigabitEthernet1/0/1", "allowed_vlans": [1, 10, 20], "native_vlan": 1}, "switchport mode trunk"),
    "assign_vlan_to_trunk_port": ({"interface": "GigabitEthernet1/0/2", "allowed_vlans": [30]}, "switchport trunk allowed vlan add 30"),
    "configure_trunk_allowed_vlans": ({"interface": "GigabitEthernet1/0/2", "allowed_vlans": [1, 20]}, "switchport trunk allowed vlan 1,20"),
    "set_native_vlan": ({"interface": "GigabitEthernet1/0/2", "native_vlan": 10}, "switchport trunk native vlan 10"),
    "configure_loopback_interface": ({"interface": "Loopback99", "address": "192.0.2.99", "prefix_length": 32}, "ip address 192.0.2.99 255.255.255.255"),
    "configure_port_channel": ({"aggregate_interface": "Port-channel5", "member_interfaces": ["GigabitEthernet1/0/3", "GigabitEthernet1/0/4"], "lacp_mode": "active"}, "channel-group 5 mode active"),
}


class VlanInterfacePackTests(KnowledgeFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.baseline = self.publish()
        self.manager = KnowledgeManagementService(self.base, releases_dir=self.releases)
        result = self.manager.migrate_sqlite({"expected_revision": self.manager.inspect().revision,
                                            "actor": "test", "reason": "Rehearse on SQLite authority"})
        self.assertTrue(result.ok, result)
        self.original = self.manager.store.snapshot()["catalogs"]
        self.packs = [read_pack(PACKS / domain) for domain in ("vlan", "interface")]
        for pack in self.packs:
            install_reviewed_assets(pack, self.base)
            request = prepare_request(self.manager, pack, actor="test", reason="Reviewed pack rehearsal")
            before = self.manager.inspect().revision
            result = self.manager.apply(request, dry_run=True)
            self.assertTrue(result.ok, result)
            self.assertEqual(before, self.manager.inspect().revision)
            result = self.manager.apply(request)
            self.assertTrue(result.ok, result)
        state = self.manager.inspect()
        result = self.manager.publish({"expected_revision": state.revision,
            "expected_release": state.data["active_release"]["release_id"],
            "actor": "test", "reason": "Offline isolated publication", "mode": "offline"})
        self.assertTrue(result.ok, result)
        self.snapshot = active_snapshot(self.releases)
        self.enterContext(snapshot_scope(self.snapshot))
        self.inventory = self.base / "data/inventory/devices.json"
        self.original_inventory = json.loads(self.inventory.read_text(encoding="utf-8"))
        self.device = json.loads((PACKS / "fixtures/devices.json").read_text(encoding="utf-8"))[0]
        self.inventory.write_text(json.dumps(self.original_inventory + [self.device]), encoding="utf-8")
        self.enterContext(patch("app.devices.inventory.INVENTORY_FILE", self.inventory))
        self.enterContext(patch("app.context.DATA_DIR", self.base / "data"))

    def issues(self, operation, params, device=None):
        device = device or self.device
        values = normalize_parameters_for_device(params, device)
        return validate_device_context(operation, "vlan" if operation in {"modify_vlan", "rename_vlan"} else "interface", values, [device])

    def test_every_binding_compiles_validates_and_renders(self):
        for operation, (params, expected) in EXAMPLES.items():
            with self.subTest(operation=operation):
                schema = load_schema(operation, [self.device])
                self.assertTrue(validate_parameter_result(params, schema).valid)
                self.assertEqual(self.issues(operation, params), [])
                output = render(self.device, operation, params)
                self.assertIn(expected, output)
                self.assertNotIn("None", output)
        self.assertEqual(len(self.snapshot.manifest["schemas"]), 23)
        self.assertEqual(len(self.snapshot.manifest["template_bindings"]), 55)

    def test_original_catalog_contracts_remain_and_reapplication_is_noop(self):
        after = self.manager.store.snapshot()["catalogs"]
        for name in ("operations", "operation_parameters", "operation_rules", "template_bindings"):
            originals = {row["operation_id"] for row in self.original["operations"]}
            self.assertEqual([row for row in after[name] if row["operation_id"] in originals], self.original[name])
        for pack in self.packs:
            self.assertIsNone(prepare_request(self.manager, pack, actor="test", reason="No-op check"))
        self.assertEqual(self.manager.inspect().data["authority"], "sqlite")
        for original in self.original["operations"]:
            self.assertTrue(self.snapshot.service.compare_operation_schema(original["operation_id"], self.snapshot.schema(original["operation_id"]))["matches"])

    def test_conflicting_pack_never_overwrites_engineer_changes_or_assets(self):
        pack = deepcopy(self.packs[0])
        pack["changes"][0].values["display_name"] = "Unreviewed label"
        with self.assertRaisesRegex(ValueError, "conflicts"):
            prepare_request(self.manager, pack, actor="test", reason="Conflict check")
        pack = deepcopy(self.packs[0])
        path = next(iter(pack["assets"]))
        before = (self.base / path).read_bytes()
        pack["assets"][path] = b"wrong template"
        with self.assertRaisesRegex(ValueError, "Conflicting template"):
            install_reviewed_assets(pack, self.base)
        self.assertEqual((self.base / path).read_bytes(), before)

    def test_unsupported_vendor_hardware_and_unknown_capability_fail_closed(self):
        params = EXAMPLES["configure_access_port"][0]
        for change in ({"vendor": "huawei"}, {"model_family": "unknown"}, {"capabilities": {"features": ["interface"]}}):
            device = {**deepcopy(self.device), **change}
            with self.subTest(change=change):
                self.assertTrue(any(issue["type"] == "UNSUPPORTED_OPERATION" for issue in self.issues("configure_access_port", params, device)))
        with self.assertRaises(ValueError):
            render({**self.device, "vendor": "juniper", "platform": "junos", "version": "23.4"}, "configure_access_port", params)

    def test_vlan_edit_identity_collision_noop_and_reserved_range(self):
        self.assertTrue(self.issues("rename_vlan", {"vlan_id": 20, "new_vlan_name": "USERS"}))
        self.assertTrue(self.issues("modify_vlan", {"vlan_id": 1002, "vlan_status": "active"}))
        self.assertTrue(self.issues("modify_vlan", {"vlan_id": 55, "vlan_status": "active"}))
        result = validate_parameter_result({"vlan_id": 20}, load_schema("modify_vlan"))
        self.assertEqual(result.issues[0].field, "vlan_status")
        device = deepcopy(self.device)
        device["capabilities"]["vtp_mode"] = "server"
        self.assertTrue(self.issues("rename_vlan", EXAMPLES["rename_vlan"][0], device))

    def test_add_and_replace_semantics_and_optional_isolation(self):
        additions = render(self.device, "assign_vlan_to_trunk_port", EXAMPLES["assign_vlan_to_trunk_port"][0])
        replacement = render(self.device, "configure_trunk_allowed_vlans", EXAMPLES["configure_trunk_allowed_vlans"][0])
        self.assertIn("vlan add", additions)
        self.assertNotIn("vlan add", replacement)
        access = load_schema("configure_access_port")
        self.assertNotIn("description", access["required"])
        self.assertIn("description", load_schema("set_interface_description")["required"])
        self.assertTrue(self.issues("configure_trunk_allowed_vlans", {"interface": "GigabitEthernet1/0/2", "allowed_vlans": [20]}))
        self.assertTrue(self.issues("assign_vlan_to_trunk_port", {"interface": "GigabitEthernet1/0/1", "allowed_vlans": [20]}))

    def test_new_logical_name_allowed_only_by_creation_operation(self):
        params = EXAMPLES["configure_loopback_interface"][0]
        self.assertFalse(self.issues("configure_loopback_interface", params))
        self.assertTrue(self.issues("set_interface_description", {"interface": "Loopback99", "description": "test"}))
        self.assertTrue(self.issues("configure_loopback_interface", {**params, "interface": "GigabitEthernet1/0/99"}))
        device = deepcopy(self.device)
        device["interfaces"].append({"name": "Loopback99", "type": "ethernet"})
        self.assertTrue(self.issues("configure_loopback_interface", params, device))

    def test_lag_members_and_aliases_are_device_scoped(self):
        params = deepcopy(EXAMPLES["configure_port_channel"][0])
        params["member_interfaces"] = ["Gi1/0/3", "Gi1/0/4"]
        self.assertFalse(self.issues("configure_port_channel", params))
        for members in (["Gi1/0/3", "GigabitEthernet1/0/3"], ["GigabitEthernet1/0/99"], ["GigabitEthernet1/0/1"]):
            self.assertTrue(self.issues("configure_port_channel", {**params, "member_interfaces": members}))
        for key, value in (("speed_mbps", 100), ("aggregate", "Port-channel7"), ("ip_addresses", ["192.0.2.5/24"]), ("service_bindings", None)):
            device = deepcopy(self.device)
            device["interfaces"][3][key] = value
            self.assertTrue(self.issues("configure_port_channel", params, device))

    def test_inventory_suggestions_and_missing_native_vlan_clarification(self):
        from app.context import parameter_options
        from app.pipeline import _finalize_task, resume_task
        options = parameter_options("configure_port_channel", self.device, "member_interfaces", {}, "test")
        self.assertEqual([row["value"] for row in options], [["GigabitEthernet1/0/3"], ["GigabitEthernet1/0/4"]])
        device = deepcopy(self.device)
        device["interfaces"][0].pop("native_vlan")
        self.inventory.write_text(json.dumps(self.original_inventory + [device]), encoding="utf-8")
        task = _finalize_task(intent_id="test", request_text="test", category="interface", operation_id="configure_trunk_port",
                              parameters={"interface": "GigabitEthernet1/0/1", "allowed_vlans": [1, 20]}, parameter_provenance={}, target_refs=["SW1"])
        self.assertEqual(task.questions[0]["field_path"], "native_vlan")
        self.assertEqual(resume_task(task, "1").status, "validated")

    def test_canonical_phrases_work_across_category_keywords_and_render_gate(self):
        from app.pipeline import _process_intent, refresh_plan, resume_task
        from app.planner.models import ExecutionPlan, OperationIntent
        prompt = "Assign VLAN to access port interface GigabitEthernet1/0/1 VLAN 20 on SW1"
        tasks = _process_intent(OperationIntent("one", prompt, target_text="SW1"))
        self.assertEqual(tasks[0].operation_id, "configure_access_port")
        self.assertEqual(tasks[0].status, "validated")
        other = _process_intent(OperationIntent("two", "Modify VLAN 20 on SW1", target_text="SW1"))
        plan = ExecutionPlan(prompt, tasks=tasks + other)
        refresh_plan(plan)
        self.assertEqual(plan.status, "needs_clarification", plan.issues)
        self.assertFalse(any(task.configs for task in plan.tasks))
        plan.tasks[1] = resume_task(plan.tasks[1], "active")
        refresh_plan(plan)
        self.assertEqual(plan.status, "ready")

    def test_primitive_member_resource_conflicts_are_symmetric(self):
        from app.pipeline import _cross_task_issues
        from app.planner.models import PlannedTask
        left = PlannedTask("left", "test", "interface", "configure_port_channel", EXAMPLES["configure_port_channel"][0], [], device_id="lab-sw1")
        right = PlannedTask("right", "test", "interface", "configure_access_port", {"interface": "GigabitEthernet1/0/3", "vlan_id": 20}, [], device_id="lab-sw1")
        self.assertTrue(_cross_task_issues([left, right]))
        self.assertTrue(_cross_task_issues([right, left]))

    def test_unknown_policy_and_wrong_field_binding_block_publication(self):
        from app.knowledge.publication import _validate_context_rules
        schemas = {name: self.snapshot.schema(name) for name in EXAMPLES}
        with self.assertRaisesRegex(ValueError, "Unknown device policy"):
            _validate_context_rules({"operations": {"modify_vlan": {"device_policy": "load_python"}}}, schemas)
        with self.assertRaisesRegex(ValueError, "requires"):
            _validate_context_rules({"operations": {"modify_vlan": {"device_policy": "c9300_loopback_v1"}}}, schemas)


if __name__ == "__main__":
    unittest.main()
