"""Canonical intent, vendor boundaries and operation-change regressions."""

import os
import unittest
from unittest.mock import patch

from app.knowledge.runtime import snapshot_scope
from app.parameters.schema_loader import _apply_vendor_requirements, load_schema
from app.pipeline import correct_task, refresh_plan, resume_task, run


class RuntimeIntentIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, {"NETWORK_RAG_RUNTIME": "files"}))
        self.enterContext(snapshot_scope(None))
        for target in ("app.llm.llm", "app.planner.intent_planner.llm", "app.parameters.parameter_extractor.llm"):
            self.enterContext(patch(target)).invoke.return_value.content = "null"

    def test_state_request_is_preserved_and_blocked_for_unreviewed_vendors(self):
        for device in ("SW2", "SW3"):
            with self.subTest(device=device):
                plan = run(f'Modify VLAN, vlan_id 20, vlan_status "suspend" on {device}', verbose=False)
                task = plan.tasks[0]
                self.assertEqual(task.parameters, {"vlan_id": 20, "vlan_status": "suspend"})
                self.assertEqual(task.operation_id, "modify_vlan")
                self.assertEqual(plan.status, "needs_clarification")
                self.assertTrue(any(i["type"] == "UNSUPPORTED_OPERATION" for i in task.issues))
                self.assertTrue(all(q["field_path"] == "operation_id" for q in task.questions))
                self.assertEqual(task.parameter_evidence["vlan_status"]["validation"], "blocked")
                self.assertFalse(task.configs)
                refused = resume_task(task, "this is an example")
                self.assertTrue(refused.feedback)
                self.assertEqual(refused.parameters, task.parameters)
                refresh_plan(plan)
                self.assertFalse(plan.tasks[0].configs)

    def test_cisco_state_and_request_wide_render_gate(self):
        plan = run('Modify VLAN, vlan_id 20, vlan_status "suspend" on SW1', verbose=False)
        self.assertEqual(plan.status, "ready")
        self.assertIn("state suspend", plan.tasks[0].configs[0]["configuration"])
        mixed = run('Create VLAN 100 named STAFF on R1; Modify VLAN, vlan_id 20, vlan_status "suspend" on SW2', verbose=False)
        self.assertEqual(mixed.status, "needs_clarification")
        self.assertFalse(any(t.configs for t in mixed.tasks))

    def test_excluded_explicit_parameter_blocks_instead_of_requesting_substitute(self):
        # Simulate a future vendor profile dropping an explicitly supplied field.
        def narrowed(operation, devices=None):
            schema = load_schema(operation, devices)
            if operation == "create_vlan" and devices and devices[0]["vendor"] == "huawei":
                schema["properties"].pop("name", None)
                schema["properties"]["description"] = {"type": "string"}
                schema["required"] = ["vlan_id", "description"]
            return schema

        with patch("app.pipeline.load_schema", side_effect=narrowed):
            plan = run('Create VLAN, vlan_id 100, name "STAFF" on SW2', verbose=False)
            task = plan.tasks[0]
            issue = next(i for i in task.issues if i["type"] == "PARAMETER_UNSUPPORTED_FOR_VENDOR")
            self.assertEqual((issue["requested_field"], issue["value"]), ("name", "STAFF"))
            self.assertIn("SW2 / huawei vrp", issue["message"])
            self.assertEqual(task.parameters["name"], "STAFF")
            self.assertEqual(task.parameter_evidence["name"]["validation"], "blocked")
            self.assertEqual([q["field_path"] for q in task.questions], ["operation_id"])
            refresh_plan(plan)
            self.assertEqual(plan.tasks[0].parameters["name"], "STAFF")
            self.assertFalse(plan.tasks[0].configs)

    def test_profile_union_retains_canonical_fields_for_extraction(self):
        schema = {"type": "object", "properties": {"state": {"type": "string"}}, "required": ["state"],
                  "x-vendor-profiles": {"example": {"properties": {"description": {"type": "string"}}, "required": ["description"]}}}
        self.assertIn("state", _apply_vendor_requirements(schema, None)["properties"])
        schema["x-semantic-fields"] = ["state"]
        with self.assertRaisesRegex(ValueError, "canonical semantic fields"):
            _apply_vendor_requirements(schema, [{"vendor": "example"}])

    def proposed_rename(self):
        with patch("app.pipeline.classify_category", return_value="vlan"), \
             patch("app.pipeline.retrieve_operation_candidates", return_value=[
                 {"operation_id": "modify_vlan", "distance": 0.1},
                 {"operation_id": "rename_vlan", "distance": 0.2},
                 {"operation_id": "create_vlan", "distance": 0.3}]), \
             patch("app.pipeline.select_operation", return_value="rename_vlan"):
            return run('Give the VLAN a different label, vlan_id 20, new_vlan_name "ENGINEERING" on SW1', verbose=False).tasks[0]

    def test_confirmation_prioritizes_proposal_then_ranked_candidates(self):
        task = self.proposed_rename()
        question = task.questions[0]
        self.assertEqual([o["value"] for o in question["options"][:3]], ["rename_vlan", "modify_vlan", "create_vlan"])
        self.assertEqual(question["options"][0]["label"], "Confirm Rename VLAN (proposed)")
        confirmed = resume_task(task, "select 1")
        self.assertEqual(confirmed.operation_id, "rename_vlan")
        self.assertEqual(confirmed.status, "validated")

    def test_override_revalidates_evidence_and_clears_operation_state(self):
        task = self.proposed_rename()
        task.item_ids = {"old[0]": "old-item"}
        task.confirmations = {"old": {"value": 20}}
        updated = resume_task(task, "select 2")
        self.assertEqual(updated.operation_id, "modify_vlan")
        self.assertEqual(updated.parameters["vlan_id"], 20)
        self.assertNotIn("new_vlan_name", updated.parameters)
        self.assertNotIn("new_vlan_name", updated.parameter_provenance)
        self.assertEqual(updated.item_ids, {})
        self.assertEqual(updated.confirmations, {})
        self.assertEqual(updated.operation_candidates, [])
        self.assertTrue(all(e["operation_id"] == "modify_vlan" for e in updated.parameter_evidence.values()))
        self.assertEqual(updated.questions[0]["field_path"], "vlan_status")
        updated = resume_task(updated, "suspend")
        self.assertEqual(updated.status, "validated")
        self.assertTrue(all(e["operation_id"] == "modify_vlan" for e in updated.parameter_evidence.values()))

    def test_explicit_operation_edit_and_target_edit_rebind_evidence(self):
        plan = run('Rename VLAN, vlan_id 20, new_vlan_name "ENGINEERING" on SW1', verbose=False)
        updated = correct_task(plan.tasks[0], "operation_id", "modify_vlan")
        self.assertEqual(updated.parameter_evidence["vlan_id"]["operation_id"], "modify_vlan")
        updated = correct_task(updated, "target_refs", "SW2")
        self.assertEqual(updated.parameter_evidence["vlan_id"]["device_id"], updated.device_id)
        self.assertFalse(updated.configs)

    def test_refresh_repairs_saved_mixed_operation_evidence(self):
        plan = run('Modify VLAN, vlan_id 20, vlan_status "active" on SW1', verbose=False)
        plan.tasks[0].parameter_evidence["vlan_id"]["operation_id"] = "rename_vlan"
        refresh_plan(plan)
        self.assertEqual(plan.tasks[0].parameter_evidence["vlan_id"]["operation_id"], "modify_vlan")
        self.assertEqual(plan.runtime_authority, "files")
        self.assertEqual(plan.knowledge_snapshot_id, "")
        self.assertEqual(plan.tasks[0].runtime_authority, "files")

    def test_canonical_state_matches_managed_registry(self):
        from app.catalog import knowledge_service
        from app.knowledge.schema_compiler import compile_schema
        direct = load_schema("modify_vlan")
        managed = compile_schema(knowledge_service(), "modify_vlan")
        self.assertEqual(direct["required"], managed["required"])
        self.assertEqual(set(direct["properties"]), set(managed["properties"]))
        self.assertEqual(direct["properties"]["vlan_status"]["enum"], managed["properties"]["vlan_status"]["enum"])

    def test_nested_native_inputs_survive_canonical_extraction(self):
        examples = [
            ('policy_terms [{"classifier_name":"VOICE","bandwidth_bps":20000000}] on SW1', "bandwidth_bps"),
            ('policy_terms [{"classifier_name":"VOICE","behavior_name":"VOICE_BEHAVIOR"}] on SW2', "behavior_name"),
        ]
        from app.parameters.parameter_extractor import extract_parameter_result
        schema = load_schema("create_qos_policy")
        for text, field in examples:
            with self.subTest(field=field):
                result = extract_parameter_result('policy_name "NEW_QOS", ' + text, schema)
                self.assertIn(field, result.parameters["policy_terms"][0])


if __name__ == "__main__":
    unittest.main()
