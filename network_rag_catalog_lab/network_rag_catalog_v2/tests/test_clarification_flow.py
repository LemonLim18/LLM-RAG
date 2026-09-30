"""End-to-end regressions using real parsing, validation, context and templates."""

from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
from io import StringIO
import tempfile
import unittest
from unittest.mock import patch

from app.clarification import apply_answer, apply_correction, create_session, load_session, save_session
from app.context import validate_context_catalog
from app.devices.context_validator import find_explicit_interface_names
from app.devices.inventory import load_inventory
from app.parameters.parameter_extractor import extract_parameter_result
from app.parameters.schema_loader import load_schema
from app.parameters.validator import validate_parameter_result
from app.pipeline import _finalize_task, confirm_order, correct_task, refresh_plan, resume_task, run
from app.planner.models import ExecutionPlan
from app.questions import answer_from_text
from app.knowledge.runtime import snapshot_scope


class ClarificationFlowTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(snapshot_scope(None))
        # Exercise every deterministic boundary while making model failure reproducible.
        for target in ("app.parameters.parameter_extractor.llm", "app.planner.intent_planner.llm", "app.llm.llm"):
            model = self.enterContext(patch(target))
            model.invoke.return_value.content = "null"

    def task(self, operation="configure_interface_ip", params=None, target="R1"):
        return _finalize_task(intent_id="intent-1", request_text="test request", category="ip_address",
                              operation_id=operation, parameters=params or {}, parameter_provenance={}, target_refs=[target])

    def test_transcript_field_isolation_and_invalid_state_unchanged(self):
        task = self.task(params={"interface": "Ethernet1/1", "prefix_length": 24})
        invalid = resume_task(task, "255.255.255.0")
        self.assertEqual(invalid.parameters, task.parameters)
        self.assertTrue(invalid.feedback)
        task = resume_task(invalid, "192.0.2.1")
        self.assertEqual(task.status, "validated")
        changed = correct_task(task, "interface", "Ethernet1/1")
        self.assertEqual(changed.parameters["prefix_length"], 24)
        invalid = correct_task(changed, "interface", "GigabitEthernet0/0/1")
        self.assertEqual(invalid.parameters, changed.parameters)
        self.assertEqual(invalid.configs, [])
        prefix = self.task(params={"interface": "Ethernet1/1", "address": "192.0.2.1"})
        self.assertEqual(resume_task(prefix, "255.255.255.0").parameters["prefix_length"], 24)
        self.assertEqual(resume_task(prefix, "/24").parameters["prefix_length"], 24)
        self.assertNotIn("prefix_length", resume_task(prefix, "Ethernet1/1").parameters)

    def test_complete_interface_boundaries(self):
        device = load_inventory()[0]
        self.assertEqual(find_explicit_interface_names(device, "Ethernet1/10"), [])
        self.assertEqual(find_explicit_interface_names(device, "Eth1/1"), ["Ethernet1/1"])
        task = self.task(params={"interface": "Ethernet1/10", "address": "192.0.2.1", "prefix_length": 24})
        self.assertIsNone(task.parameters["interface"])
        self.assertEqual(task.questions[0]["issue_type"], "INVALID_INTERFACE")

    def test_invalid_supplied_values_are_checked_with_missing_fields(self):
        result = validate_parameter_result({"interface": "Ethernet1/1", "address": "255.255.255.0"}, load_schema("configure_interface_ip"))
        self.assertTrue(any(issue.type == "MISSING" for issue in result.issues))
        self.assertTrue(any(issue.type == "NETWORK_VALUE" for issue in result.issues))
        for address, prefix, valid in [("192.0.2.0", 24, False), ("192.0.2.0", 31, True), ("192.0.2.0", 32, True), ("224.0.0.1", 24, False)]:
            with self.subTest(address=address, prefix=prefix):
                result = validate_parameter_result({"interface": "Ethernet1/1", "address": address, "prefix_length": prefix}, load_schema("configure_interface_ip"))
                self.assertEqual(result.valid, valid)

    def test_nested_partial_items_remain_and_areas_do_not_leak(self):
        task = run("Configure OSPF process 100 on R1 using Ethernet1/1 and Loopback0", verbose=False).tasks[0]
        self.assertEqual(task.parameters["interfaces"], [{"name": "Ethernet1/1"}, {"name": "Loopback0"}])
        self.assertEqual(task.questions[0]["field_path"], "interfaces[0].area")
        first_id = task.questions[0]["item_id"]
        task = resume_task(task, "0")
        self.assertEqual(task.questions[0]["field_path"], "interfaces[1].area")
        self.assertNotEqual(task.questions[0]["item_id"], first_id)
        task = resume_task(task, "1")
        self.assertEqual([item["area"] for item in task.parameters["interfaces"]], ["0", "1"])

    def test_shared_and_separate_operation_device_bindings(self):
        for prompt, expected in [
            ("Create VLAN 20 and configure OSPF on R1 and R2", [("create_vlan", "R1"), ("create_vlan", "R2"), ("configure_ospf", "R1"), ("configure_ospf", "R2")]),
            ("Create VLAN 20 and configure OSPF on R1; create VLAN 30 on R2", [("create_vlan", "R1"), ("configure_ospf", "R1"), ("create_vlan", "R2")]),
        ]:
            with self.subTest(prompt=prompt):
                plan = run(prompt, verbose=False)
                self.assertEqual([(task.operation_id, task.target_devices[0]["hostname"]) for task in plan.tasks], expected)
                self.assertTrue(all(not task.configs for task in plan.tasks))

    def test_per_device_answers_and_vendor_requirements(self):
        plan = run("Configure OSPF on R1 and R3", verbose=False)
        r1, r3 = plan.tasks
        r1 = resume_task(r1, "select 1")
        r1 = resume_task(r1, "0")
        self.assertEqual(r1.questions[0]["field_path"], "process_id")
        r3 = resume_task(r3, "select 1")
        r3 = resume_task(r3, "1")
        self.assertEqual(r3.status, "validated")
        self.assertEqual(r3.parameters["interfaces"][0]["name"], "ge-0/0/0")
        self.assertEqual(r1.parameters["interfaces"][0]["area"], "0")

    def test_select_and_literal_numbers_have_distinct_meanings(self):
        params = {"interfaces": [{"name": "Ethernet1/1", "area": "0"}]}
        task = self.task("configure_ospf", params)
        self.assertEqual(task.questions[0]["options"][0]["value"], 100)
        self.assertEqual(resume_task(task, "1").parameters["process_id"], 1)
        self.assertEqual(resume_task(task, "select 1").parameters["process_id"], 100)
        for reply in ["-1", "1a", "65536", "select 99"]:
            invalid = resume_task(task, reply)
            self.assertEqual(invalid.parameters, task.parameters)
            self.assertTrue(invalid.feedback)

    def test_planned_choices_are_scoped_and_never_silently_accepted(self):
        validate_context_catalog()
        task = self.task(params={"interface": "Ethernet1/1"})
        question = task.questions[0]
        self.assertEqual(question["field_path"], "address")
        self.assertEqual(question["options"][0]["value"], "192.0.2.1")
        self.assertNotIn("address", task.parameters)
        self.assertTrue(question["options"][0]["source_ref"].startswith("lab-design:"))
        loopback = self.task(params={"interface": "Loopback0"})
        self.assertEqual(loopback.questions[0]["options"], [])

    def test_whole_request_gate_and_atomic_render_failure(self):
        plan = run("Create VLAN 20 on R1; configure OSPF on R2", verbose=False)
        self.assertEqual(plan.tasks[0].status, "validated")
        self.assertTrue(all(not task.configs for task in plan.tasks))
        plan = run("Create VLAN 20 on R1; create VLAN 30 on R2", verbose=False)
        self.assertEqual(plan.status, "ready")
        with patch("app.pipeline.render", side_effect=["vlan 20", ValueError("bad template")]):
            refresh_plan(plan)
        self.assertEqual(plan.status, "failed")
        self.assertTrue(all(not task.configs for task in plan.tasks))

    def test_stale_answers_and_invalid_session_replies(self):
        with tempfile.TemporaryDirectory() as directory, patch("app.clarification.SESSIONS_DIR", Path(directory)):
            session = create_session("Configure interface IP on R1")
            question = session.next_question
            answer = answer_from_text(question, "select 1")
            apply_answer(session, answer)
            with self.assertRaises(ValueError):
                apply_answer(session, answer)
            restored = load_session(session.session_id)
            self.assertEqual(restored.plan.tasks[0].parameters["interface"], "Ethernet1/1")
            before = deepcopy(restored.plan.tasks[0].parameters)
            apply_answer(restored, answer_from_text(restored.next_question, "255.255.255.0"))
            self.assertEqual(restored.plan.tasks[0].parameters, before)
            current = restored.plan.tasks[0]
            answer = answer_from_text(current.questions[0], "192.0.2.1")
            with patch("app.pipeline.source_revision", return_value="changed"):
                rejected = resume_task(current, answer)
            self.assertEqual(rejected.parameters, current.parameters)
            self.assertIn("changed", rejected.feedback)

    def test_conflicting_parameters_and_unsupported_operations_remain_recoverable(self):
        task = run("Create VLAN 20 or 30 on R1", verbose=False).tasks[0]
        self.assertEqual(task.questions[0]["issue_type"], "AMBIGUOUS")
        self.assertEqual([option["value"] for option in task.questions[0]["options"]], [20, 30])
        with patch("app.pipeline.classify_category", side_effect=ValueError("unsupported")):
            plan = run("Create VLAN 20 on R1; do something unknown on R2", verbose=False)
        self.assertEqual(plan.tasks[0].status, "validated")
        self.assertEqual(plan.tasks[1].questions[0]["field_path"], "operation_id")
        self.assertEqual(plan.status, "needs_clarification")

    def test_cross_task_conflicts_require_confirmation_or_correction(self):
        plan = run("Create VLAN 20 on R1; delete VLAN 20 on R1", verbose=False)
        self.assertEqual(plan.status, "needs_confirmation")
        self.assertTrue(all(not task.configs for task in plan.tasks))
        confirm_order(plan)
        self.assertEqual(plan.status, "ready")
        plan.tasks[0] = correct_task(plan.tasks[0], "vlan_id", "30")
        refresh_plan(plan)
        self.assertEqual(plan.status, "ready")

    def test_model_null_and_invented_numeric_binding(self):
        schema = load_schema("configure_ospf", [load_inventory()[0]])
        with patch("app.parameters.parameter_extractor.llm") as model:
            model.invoke.return_value.content = '{"parameters":{"process_id":2,"interfaces":[{"name":"Ethernet0","area":"254"}]}}'
            extraction = extract_parameter_result("Configure OSPF on R2", schema)
        self.assertIsNone(extraction.parameters["process_id"])
        self.assertIsNone(extraction.parameters["interfaces"])

    def test_planned_conflicts_require_an_explicit_override(self):
        record = {"id": "planned-process", "device_id": "dev-r1", "operation_id": "configure_ospf", "field": "process_id", "value": 100,
                  "kind": "intended_assignment", "source_ref": "design:core", "revision": 1}
        def records(operation, device, path, params):
            return [record] if path == "process_id" else []
        with patch("app.context.matching_records", side_effect=records):
            task = self.task("configure_ospf", {"process_id": 200, "interfaces": [{"name": "Ethernet1/1", "area": "0"}]})
            self.assertIsNone(task.parameters["process_id"])
            self.assertEqual(task.questions[0]["issue_type"], "CONTEXT_CONFLICT")
            self.assertTrue(task.questions[0]["options"][0]["override"])
            confirmed = resume_task(task, "select 1")
            self.assertEqual(confirmed.parameters["process_id"], 200)
            self.assertEqual(confirmed.status, "validated")
            record["kind"] = "fact"
            task = self.task("configure_ospf", {"process_id": 200, "interfaces": [{"name": "Ethernet1/1", "area": "0"}]})
            self.assertFalse(any(option.get("override") for option in task.questions[0]["options"]))
            self.assertEqual(resume_task(task, "200").status, "needs_clarification")

    def test_juniper_bgp_group_is_required_not_invented(self):
        task = self.task("configure_bgp_neighbor", {"local_as": 65000, "neighbor_ip": "192.0.2.2", "remote_as": 65001}, "R3")
        self.assertEqual(task.questions[0]["field_path"], "peer_group")
        task = resume_task(task, "TRANSIT")
        plan = refresh_plan(ExecutionPlan("request", tasks=[task]))
        self.assertEqual(plan.status, "ready")
        self.assertIn("group TRANSIT", plan.tasks[0].configs[0]["configuration"])
        self.assertNotIn("EBGP-PEER", plan.tasks[0].configs[0]["configuration"])

    def test_explicit_edit_revalidates_dependent_planned_values(self):
        task = self.task(params={"interface": "Ethernet1/1"})
        task = resume_task(task, "select 1")
        task = resume_task(task, "select 1")
        self.assertEqual(task.status, "validated")
        changed = correct_task(task, "interface", "Loopback0")
        self.assertIsNone(changed.parameters["address"])
        self.assertIsNone(changed.parameters["prefix_length"])
        self.assertEqual(changed.status, "needs_clarification")

    def test_legacy_session_migration_revalidates_incomplete_old_ready_tasks(self):
        from app.clarification import _plan_from_dict
        old = {"original_prompt": "Configure OSPF on R1", "tasks": [{
            "intent_id": "old", "request_text": "Configure OSPF on R1", "operation_id": "configure_ospf",
            "category": "ospf", "parameters": {"process_id": 100}, "target_refs": ["R1"],
            "status": "ready", "configs": [{"configuration": "unsafe old output"}]}]}
        plan = refresh_plan(_plan_from_dict(old))
        self.assertEqual(plan.status, "needs_clarification")
        self.assertEqual(plan.tasks[0].configs, [])
        self.assertEqual(plan.tasks[0].parameters["process_id"], 100)

    def test_multiple_interfaces_can_be_selected_without_shared_area_guess(self):
        task = self.task("configure_ospf", {"process_id": 100})
        task = resume_task(task, "select 1,2")
        self.assertEqual([item["name"] for item in task.parameters["interfaces"]], ["Ethernet1/1", "Loopback0"])
        self.assertEqual([q["field_path"] for q in task.questions], ["interfaces[0].area", "interfaces[1].area"])

    def test_three_shared_operations_and_parameter_alternatives(self):
        plan = run("Create VLAN 20, configure OSPF and configure BGP neighbor on R1 and R2", verbose=False)
        self.assertEqual(len(plan.tasks), 6)
        self.assertEqual([task.device_id for task in plan.tasks], ["dev-r1", "dev-r2"] * 3)
        task = run("Configure interface IP 192.0.2.1 or 192.0.2.2 prefix 24 on R1 using Ethernet1/1", verbose=False).tasks[0]
        self.assertIsNone(task.parameters["address"])
        self.assertEqual(task.questions[0]["issue_type"], "AMBIGUOUS")

    def test_unknown_version_and_context_changes_cannot_reuse_output(self):
        from app.templates.template_selector import select_template
        device = deepcopy(load_inventory()[0])
        device["version"] = "unreviewed-version"
        with self.assertRaises(ValueError):
            select_template(device, "create_vlan")
        plan = run("Create VLAN 20 on R1", verbose=False)
        with patch("app.pipeline.source_revision", return_value="changed"), patch("app.pipeline.validate_context_catalog", side_effect=ValueError("invalid context")):
            refresh_plan(plan)
        self.assertEqual(plan.status, "failed")
        self.assertTrue(all(not task.configs for task in plan.tasks))

    def test_all_existing_vendor_templates_render_complete_examples(self):
        from app.catalog import load_operations
        examples = {
            "create_vlan": {"vlan_id": 20, "name": "STAFF"}, "delete_vlan": {"vlan_id": 20, "name": "STAFF"},
            "configure_ospf": {"process_id": 100, "interfaces": []},
            "remove_ospf_interface": {"process_id": 100, "area": "0"},
            "configure_bgp_neighbor": {"local_as": 65000, "neighbor_ip": "192.0.2.2", "remote_as": 65001, "peer_group": "TRANSIT"},
            "remove_bgp_neighbor": {"local_as": 65000, "neighbor_ip": "192.0.2.2", "remote_as": 65001, "peer_group": "TRANSIT"},
            "configure_isis_interface": {"level": "level-2", "process_name": "CORE"},
            "disable_isis_interface": {"process_name": "CORE"},
            "configure_interface_ip": {"address": "192.0.2.1", "prefix_length": 24},
            "remove_interface_ip": {"address": "192.0.2.1", "prefix_length": 24},
            "configure_static_route": {"destination": "198.51.100.0/24", "next_hop": "192.0.2.2"},
            "remove_static_route": {"destination": "198.51.100.0/24", "next_hop": "192.0.2.2"},
        }
        from app.templates.renderer import render
        for device in load_inventory():
            for operation in load_operations():
                with self.subTest(device=device["hostname"], operation=operation["operation_id"]):
                    params = deepcopy(examples[operation["operation_id"]])
                    schema = load_schema(operation["operation_id"], [device])
                    if "interface" in schema["properties"]:
                        params["interface"] = device["interfaces"][0]["name"]
                    if "interfaces" in params:
                        params["interfaces"] = [{"name": device["interfaces"][0]["name"], "area": "0"}]
                    params = {key: value for key, value in params.items() if key in schema["properties"]}
                    self.assertTrue(validate_parameter_result(params, schema).valid)
                    self.assertTrue(render(device, operation["operation_id"], params).strip())

    def test_terminal_loop_asks_one_scoped_question_and_rejects_mask_address(self):
        from main import _interactive_loop
        with tempfile.TemporaryDirectory() as directory, patch("app.clarification.SESSIONS_DIR", Path(directory)):
            session = create_session("Configure interface IP on R1")
            output = StringIO()
            with patch("builtins.input", side_effect=["select 1", "255.255.255.0", "192.0.2.1", "255.255.255.0"]), patch("sys.stdout", output):
                session = _interactive_loop(session, False)
            self.assertEqual(session.status, "ready")
            self.assertIn("Answer not accepted", output.getvalue())
            self.assertIn("Custom answer", output.getvalue())
            self.assertIn("ip address 192.0.2.1 255.255.255.0", session.plan.tasks[0].configs[0]["configuration"])

    def test_inventory_group_membership_changes_require_review(self):
        plan = run("Create VLAN 20 on core routers", verbose=False)
        inventory = deepcopy(load_inventory())
        added = deepcopy(inventory[0])
        added.update(id="dev-r4", hostname="R4", aliases=["Router 4"])
        inventory.append(added)
        with patch("app.devices.target_resolver.load_inventory", return_value=inventory):
            refresh_plan(plan)
        self.assertEqual(plan.status, "needs_clarification")
        self.assertTrue(all(not task.configs for task in plan.tasks))
        self.assertIn("membership changed", plan.tasks[0].questions[0]["wording"])

    def test_reordered_nested_items_retain_identity(self):
        task = self.task("configure_ospf", {"process_id": 100, "interfaces": [{"name": "Ethernet1/1"}, {"name": "Loopback0"}]})
        old_ids = deepcopy(task.item_ids)
        changed = correct_task(task, "interfaces", '[{"name":"Loopback0"},{"name":"Ethernet1/1"}]')
        self.assertEqual(changed.item_ids["interfaces[0]"], old_ids["interfaces[1]"])
        self.assertEqual(changed.item_ids["interfaces[1]"], old_ids["interfaces[0]"])

    def test_unknown_coordinated_action_is_not_swallowed_by_known_operation(self):
        from app.planner.intent_planner import plan_intents
        intents = plan_intents("Create VLAN 20 on R1 and reboot R2")
        self.assertEqual(len(intents), 2)
        self.assertEqual(intents[1].request_text, "reboot R2")
        self.assertEqual(len(plan_intents("Configure OSPF on R1 and R2 using Loopback0 in area 0")), 1)
        self.assertEqual(len(plan_intents("Create VLAN 20 on R1 and shutdown R2")), 2)

    def test_proposed_shared_target_can_be_confirmed_without_changing_identity(self):
        task = self.task("create_vlan", {"vlan_id": 20})
        task.planning_issues = [{"type": "TARGET_UNRESOLVED", "field": "target_refs", "message": "Confirm shared scope"}]
        plan = refresh_plan(ExecutionPlan("request", tasks=[task]))
        confirmed = resume_task(plan.tasks[0], "R1")
        self.assertEqual(confirmed.status, "validated")


if __name__ == "__main__":
    unittest.main()
