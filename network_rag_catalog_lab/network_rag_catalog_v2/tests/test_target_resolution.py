import json
import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch

from app.clarification import _plan_from_dict
from app.devices.inventory import load_inventory, resolve_targets, TargetResolutionError
from app.devices.target_query import extract_target_queries, parameter_request, parse_description
from app.devices.target_resolver import resolve_queries
from app.pipeline import _finalize_task, next_clarification_prompt, plan_to_dict, resume_task, run
from app.planner.intent_planner import plan_intents
from app.planner.models import ExecutionPlan


class TargetResolutionTests(unittest.TestCase):
    def resolve(self, prompt, inventory=None):
        inventory = load_inventory() if inventory is None else inventory
        queries = extract_target_queries(prompt, inventory)
        return resolve_queries(queries, inventory)

    def task(self, description):
        return _finalize_task(
            intent_id="intent-1", request_text="Create VLAN 20 on " + description,
            category="vlan", operation_id="create_vlan", parameters={"vlan_id": 20},
            parameter_provenance={"vlan_id": "user"}, target_refs=[description],
        )

    def test_unique_attributes_and_aliases(self):
        cases = {
            "the Penang edge Juniper router": ["R3"],
            "the Cisco core router in Kuala Lumpur": ["R1"],
            "the branch router": ["R3"],
            "Huawei": ["R2"],
            "edge router 1": ["R3"],
            "the router named R1": ["R1"],
            "core routers": ["R1", "R2"],
            "R1 and R2": ["R1", "R2"],
            "the router with management IP 10.0.0.12": ["R2"],
            "routers with management subnet 10.0.0.0/24": ["R1", "R2", "R3"],
            "routers supporting IS-IS": ["R3"],
            "the router running IOS-XE version 17.9": ["R1"],
            "the router with GigabitEthernet0/0/1": ["R2"],
        }
        for phrase, expected in cases.items():
            with self.subTest(phrase=phrase):
                result = self.resolve("Create VLAN 20 on " + phrase)
                self.assertFalse(result["issues"], result["issues"])
                self.assertEqual([device["hostname"] for device in result["devices"]], expected)

    def test_missing_ambiguous_conflicting_and_unknown_never_select(self):
        cases = {
            "Create VLAN 20": "MISSING_TARGET",
            "Create VLAN 20 on the KL core router": "AMBIGUOUS_TARGET",
            "Create VLAN 20 on one of the core routers": "AMBIGUOUS_TARGET",
            "Create VLAN 20 on the Cisco router in Penang": "TARGET_CONFLICT",
            "Create VLAN 20 on Cisco R2": "TARGET_CONFLICT",
            "Create VLAN 20 on the router at site:Cisco": "TARGET_NOT_FOUND",
            "Create VLAN 20 on Router 9": "TARGET_NOT_FOUND",
            "Create VLAN 20 on the London Cisco router": "TARGET_UNRESOLVED",
            "Create VLAN 20 on non Cisco routers": "TARGET_UNRESOLVED",
            "Create VLAN 20 on Cisco or Juniper routers": "TARGET_UNRESOLVED",
        }
        for prompt, code in cases.items():
            with self.subTest(prompt=prompt):
                result = self.resolve(prompt)
                self.assertEqual(result["devices"], [])
                self.assertEqual(result["issues"][0]["type"], code)

    def test_ambiguity_refinement_retains_context_without_parameter_llm(self):
        pending = self.task("the KL core router")
        with patch("app.pipeline.extract_parameter_result") as parameters:
            ready = resume_task(pending, "the Huawei one")
        parameters.assert_not_called()
        self.assertEqual(ready.status, "validated")
        self.assertEqual([device["hostname"] for device in ready.target_devices], ["R2"])
        fields = {item["field"] for item in ready.target_queries[0]["constraints"]}
        self.assertTrue({"site", "role", "vendor"} <= fields)
        self.assertEqual(ready.parameters, {"vlan_id": 20})

    def test_conflict_correction_and_numbered_choice(self):
        conflict = self.task("the Cisco router in Penang")
        self.assertEqual(conflict.configs, [])
        ready = resume_task(conflict, "Juniper")
        self.assertEqual(ready.status, "validated")
        self.assertEqual(ready.target_devices[0]["hostname"], "R3")
        numbered = resume_task(self.task("core router"), "select 2")
        self.assertEqual(numbered.target_devices[0]["hostname"], "R2")

    def test_duplicate_alias_stays_ambiguous(self):
        inventory = deepcopy(load_inventory())
        inventory[1]["aliases"].append("router 1")
        result = self.resolve("Create VLAN 20 on router 1", inventory)
        self.assertEqual(result["issues"][0]["type"], "AMBIGUOUS_TARGET")

    def test_new_inventory_attributes_require_no_code_changes(self):
        inventory = deepcopy(load_inventory())
        inventory[0].update(site="Johor", role="distribution", tags=["finance"])
        result = self.resolve("Create VLAN 20 on the Johor distribution finance router", inventory)
        self.assertEqual([device["hostname"] for device in result["devices"]], ["R1"])

    def test_unsupported_model_values_cannot_choose_device(self):
        proposals = [{"field": "site", "value": "Penang", "evidence": "London"},
                     {"field": "name", "value": "R3", "evidence": "R3"},
                     {"field": [], "value": {}, "evidence": None}]
        with patch("app.devices.target_query._llm_constraints", return_value=proposals):
            query = parse_description("London router", load_inventory(), allow_llm=True)
        result = resolve_queries([query])
        self.assertFalse(result["devices"])
        self.assertIn("London", query["unresolved"])

    def test_null_or_unavailable_model_preserves_known_constraints(self):
        for response in [SimpleNamespace(content="null"), SimpleNamespace(content="bad json")]:
            with patch("app.llm.llm") as llm:
                llm.invoke.return_value = response
                query = parse_description("London Cisco router", load_inventory(), allow_llm=True)
            self.assertTrue(any(item["value"] == "cisco" for item in query["constraints"]))
            self.assertFalse(resolve_queries([query])["devices"])

    def test_rewritten_planner_output_does_not_drop_target_context(self):
        original = "help to configure an ip interface on the Penang Juniper router"
        with patch("app.planner.intent_planner.llm") as llm:
            llm.invoke.return_value.content = json.dumps({"intents": [{"request_text": "configure interface ip", "target_refs": ["R1"]}]})
            intents = plan_intents(original)
        self.assertEqual(intents[0].request_text, original)

    def test_two_operations_keep_their_own_device_constraints(self):
        prompt = "Create VLAN 20 on the Penang edge Juniper router and create VLAN 30 on the KL Cisco router"
        with patch("app.pipeline.retrieve_operation_candidates", return_value=[{"operation_id": "create_vlan", "distance": 0.0}]), patch("app.parameters.parameter_extractor.llm") as llm:
            plan = run(prompt, verbose=False)
        llm.invoke.assert_not_called()
        self.assertEqual([task.target_devices[0]["hostname"] for task in plan.tasks], ["R3", "R1"])
        self.assertEqual([task.parameters["vlan_id"] for task in plan.tasks], [20, 30])

    def test_session_roundtrip_keeps_queries_and_suggestions(self):
        pending = self.task("KL core router")
        restored = _plan_from_dict(json.loads(json.dumps(plan_to_dict(ExecutionPlan("request", tasks=[pending]))))).tasks[0]
        self.assertEqual(next_clarification_prompt(restored), next_clarification_prompt(pending))
        self.assertEqual(resume_task(restored, "Huawei").target_devices[0]["hostname"], "R2")

    def test_public_resolver_uses_same_singular_ambiguity_rules(self):
        with self.assertRaises(TargetResolutionError):
            resolve_targets(["core router"])

    def test_management_ip_cannot_become_configured_ip(self):
        prompt = "Configure IP address on the router with management IP 10.0.0.12"
        queries = extract_target_queries(prompt, load_inventory())
        self.assertNotIn("10.0.0.12", parameter_request(prompt, queries))
        with patch("app.pipeline.retrieve_operation_candidates", return_value=[{"operation_id": "configure_interface_ip", "distance": 0.0}]), patch("app.parameters.parameter_extractor.llm") as llm:
            llm.invoke.return_value.content = 'null'
            task = run(prompt, verbose=False).tasks[0]
        self.assertEqual(task.target_devices[0]["hostname"], "R2")
        self.assertIsNone(task.parameters.get("address"))
        self.assertEqual(task.status, "needs_clarification")


if __name__ == "__main__":
    unittest.main()
