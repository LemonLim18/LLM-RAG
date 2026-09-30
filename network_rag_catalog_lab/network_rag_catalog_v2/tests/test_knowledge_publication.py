from copy import deepcopy
import json
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from jinja2 import Environment, StrictUndefined, UndefinedError

from app import catalog
from app.clarification import _plan_from_dict
from app.context import source_revision
from app.knowledge.runtime import active_pointer, active_snapshot, snapshot_scope
from app.parameters.schema_loader import load_schema
from app.pipeline import _finalize_task, refresh_plan, resume_task, plan_to_dict
from app.planner.models import ExecutionPlan
from app.templates.renderer import _prepare_context, render
from app.templates.template_selector import select_template
from knowledge_fixtures import KnowledgeFixture


class KnowledgePublicationTests(KnowledgeFixture, unittest.TestCase):
    def test_retrieval_documents_declare_actual_vendor_contracts(self):
        from app.knowledge.models import TemplateBinding
        from app.knowledge.publication import build_documents
        from app.knowledge.schema_compiler import compile_schema
        operations = self.service.list_operations()
        schemas = {operation.operation_id: compile_schema(self.service, operation.operation_id) for operation in operations}
        bindings = [TemplateBinding.model_validate(row) for row in self.read("template_bindings")
                    if row["operation_id"] != "create_vlan" or row["vendor"] == "cisco"]
        documents = {row["id"]: row for row in build_documents(operations, schemas, "test-release", self.service, bindings)}
        support = json.loads(documents["create_vlan"]["metadata"]["vendor_support"])
        self.assertEqual(support["unimplemented_vendors"], ["huawei", "juniper"])
        self.assertEqual([row["vendor"] for row in support["profiles"]], ["cisco"])
        ospf = json.loads(documents["configure_ospf"]["metadata"]["vendor_support"])
        profiles = {row["vendor"]: row for row in ospf["profiles"]}
        self.assertIn("process_id", profiles["cisco"]["required_parameters"])
        self.assertNotIn("process_id", profiles["juniper"]["required_parameters"])
        self.assertIn("Vendor support and operation-specific parameters", documents["create_vlan"]["page_content"])

    def test_conditional_requirement_uses_normal_clarification_and_render_gate(self):
        rules = self.read("operation_rules")
        root = next(row for row in rules if row["operation_id"] == "create_vlan" and row["field_path"] == "")
        root["keywords"]["x-conditional-required"] = [{"field": "vlan_id", "equals": 20, "required": ["name"]}]
        self.write("operation_rules", rules)
        snapshot = self.publish()
        with snapshot_scope(snapshot):
            task = self.task(snapshot, {"vlan_id": 20})
            plan = refresh_plan(ExecutionPlan("Create VLAN 20 on R1", tasks=[task]))
            self.assertEqual(plan.status, "needs_clarification")
            self.assertEqual(plan.tasks[0].questions[0]["field_path"], "name")
            self.assertFalse(plan.tasks[0].configs)
            plan.tasks[0] = resume_task(plan.tasks[0], "STAFF")
            self.assertEqual(refresh_plan(plan).status, "ready")
            self.assertIn("STAFF", plan.tasks[0].configs[0]["configuration"])

    def test_each_supported_profile_has_a_hashed_effective_schema(self):
        snapshot = self.publish()
        for binding in snapshot.manifest["template_bindings"]:
            path = binding["schema_artifact"]
            self.assertIn(path, snapshot.manifest["artifacts"])
            with snapshot_scope(snapshot):
                from app.parameters.schema_loader import _add_catalog_metadata, load_schema
                self.assertEqual(load_schema(binding["operation_id"], [{"vendor": binding["vendor"]}]),
                                 _add_catalog_metadata(snapshot.read_json(path)))
        self.assertIn("process_id", snapshot.schema("configure_ospf", "cisco")["required"])
        self.assertNotIn("process_id", snapshot.schema("configure_ospf", "juniper")["required"])

    def task(self, snapshot, params=None):
        with snapshot_scope(snapshot):
            return _finalize_task(intent_id="one", request_text="create VLAN on R1", category="vlan",
                operation_id="create_vlan", parameters=params or {}, parameter_provenance={}, target_refs=["R1"])

    def test_release_loads_compiled_schemas_templates_and_metadata_after_draft_edits(self):
        first = self.publish(verify_legacy=True)
        with snapshot_scope(first):
            revision = source_revision()
            schema = load_schema("create_vlan")
            parameters = self.read("parameters")
            parameters[0]["display_name"] = "Draft label"
            self.write("parameters", parameters)
            self.assertEqual(source_revision(), revision)
            self.assertEqual(load_schema("create_vlan"), schema)
            self.assertNotEqual(catalog.load_parameters()[0]["display_name"], "Draft label")
        second = self.publish()
        with snapshot_scope(second):
            self.assertEqual(catalog.load_parameters()[0]["display_name"], "Draft label")
        with snapshot_scope(first), self.assertRaisesRegex(ValueError, "release changed"):
            source_revision()

    def test_template_outputs_match_all_36_existing_profiles(self):
        snapshot = self.publish(verify_legacy=True)
        samples = {
            "create_vlan": {"vlan_id": 20, "name": "STAFF"}, "delete_vlan": {"vlan_id": 20, "name": "STAFF"},
            "configure_ospf": {"process_id": 100, "router_id": "10.0.0.1", "interfaces": [{"name": "Ethernet1/1", "area": "0"}]},
            "remove_ospf_interface": {"process_id": 100, "interface": "Ethernet1/1", "area": "0"},
            "configure_bgp_neighbor": {"local_as": 65000, "neighbor_ip": "10.0.0.2", "remote_as": 65001, "peer_group": "PEERS"},
            "remove_bgp_neighbor": {"local_as": 65000, "neighbor_ip": "10.0.0.2", "remote_as": 65001, "peer_group": "PEERS"},
            "configure_isis_interface": {"process_id": 1, "process_name": "CORE", "interface": "Ethernet1/1", "level": "level-2"},
            "disable_isis_interface": {"process_id": 1, "process_name": "CORE", "interface": "Ethernet1/1"},
            "configure_static_route": {"destination": "10.20.0.0/24", "next_hop": "10.0.0.2"},
            "remove_static_route": {"destination": "10.20.0.0/24", "next_hop": "10.0.0.2"},
            "configure_interface_ip": {"interface": "Ethernet1/1", "address": "10.0.0.1", "prefix_length": 24},
            "remove_interface_ip": {"interface": "Ethernet1/1", "address": "10.0.0.1", "prefix_length": 24},
        }
        env = Environment(undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True)
        with snapshot_scope(snapshot):
            for binding in self.read("template_bindings"):
                device = {"hostname": "test", "vendor": binding["vendor"], "platform": binding["platform"], "version": binding["versions"][0]}
                text = (self.base / binding["template_path"]).read_text(encoding="utf-8")
                params = samples[binding["operation_id"]]
                expected = env.from_string(text).render(**_prepare_context(params)).strip() + "\n"
                with self.subTest(operation=binding["operation_id"], vendor=device["vendor"]):
                    self.assertEqual(render(device, binding["operation_id"], params), expected)
            with self.assertRaises(UndefinedError):
                render({"hostname": "R1", "vendor": "cisco", "platform": "iosxe", "version": "17.9"}, "create_vlan", {})

    def test_failed_index_build_leaves_previous_release_and_no_ready_claim(self):
        first = self.publish()
        with self.assertRaisesRegex(RuntimeError, "embedding unavailable"):
            self.publish(mode="chroma", index_builder=lambda *_: (_ for _ in ()).throw(RuntimeError("embedding unavailable")))
        self.assertEqual(active_snapshot(self.releases).release_id, first.release_id)
        with self.assertRaisesRegex(ValueError, "complete release"):
            self.publish(mode="chroma", index_builder=lambda *_: {})
        self.assertEqual(active_pointer(self.releases)["release_id"], first.release_id)

    def test_failed_validation_stale_publish_and_lock_preserve_activation(self):
        first = self.publish()
        with self.assertRaisesRegex(ValueError, "Stale publication"):
            self.publish(expected_release=None)
        (self.releases / ".publication.lock").touch()
        with self.assertRaisesRegex(ValueError, "publication is in progress"):
            self.publish()
        (self.releases / ".publication.lock").unlink()
        rows = self.read("template_bindings")
        rows[0]["template_path"] = "../outside.j2"
        self.write("template_bindings", rows)
        with self.assertRaisesRegex(ValueError, "unsafe template"):
            self.publish()
        self.assertEqual(active_pointer(self.releases)["release_id"], first.release_id)

    def test_contract_change_requires_version_then_sessions_revalidate(self):
        first = self.publish()
        task = self.task(first, {"vlan_id": 20})
        with snapshot_scope(first):
            plan = refresh_plan(ExecutionPlan("create VLAN 20 on R1", tasks=[task]))
            self.assertEqual(plan.status, "ready")
            saved = plan_to_dict(plan)
        rows = self.read("operation_parameters")
        next(row for row in rows if row["operation_id"] == "create_vlan" and row["field_path"] == "name").update(required=True, required_order=1)
        self.write("operation_parameters", rows)
        bindings = self.read("template_bindings")
        for binding in bindings:
            if binding["operation_id"] == "create_vlan":
                binding["input_contract"]["optional_defaults"].pop("name", None)
        self.write("template_bindings", bindings)
        with self.assertRaisesRegex(ValueError, "version bump"):
            self.publish()
        self.bump("create_vlan")
        second = self.publish()
        with snapshot_scope(second):
            restored = refresh_plan(_plan_from_dict(saved))
            self.assertEqual(restored.status, "needs_clarification")
            self.assertEqual(restored.knowledge_snapshot_id, second.release_id)
            self.assertEqual(restored.tasks[0].questions[0]["field_path"], "name")
            self.assertFalse(restored.tasks[0].configs)

    def test_retirement_and_stale_answers_cannot_use_old_release(self):
        first = self.publish()
        task = self.task(first)
        rows = self.read("operations")
        next(row for row in rows if row["operation_id"] == "create_vlan")["status"] = "inactive"
        self.write("operations", rows)
        second = self.publish()
        with snapshot_scope(second):
            updated = resume_task(task, "20")
            self.assertIn("changed", updated.feedback)
            self.assertFalse(updated.configs)
            self.assertEqual(updated.questions[0]["field_path"], "operation_id")
            with self.assertRaises(KeyError):
                load_schema("create_vlan")

    def test_inventory_changes_still_invalidate_questions_and_missing_release_fails(self):
        snapshot = self.publish()
        task = self.task(snapshot)
        with snapshot_scope(snapshot), patch("app.context.DATA_DIR", self.base / "data"):
            initial = source_revision()
            path = self.base / "data/inventory/devices.json"
            path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            self.assertNotEqual(source_revision(), initial)
        with snapshot_scope(None):
            plan = ExecutionPlan("old", tasks=[task], knowledge_snapshot_id=snapshot.release_id)
            self.assertEqual(refresh_plan(plan).status, "failed")
            self.assertFalse(plan.tasks[0].configs)

    def test_retrieval_uses_one_release_and_rejects_mixed_metadata(self):
        seen = []
        def builder(release_id, documents):
            seen.extend(documents)
            return {"release_id": release_id, "collection": "knowledge_" + release_id,
                    "ids": sorted(doc["id"] for doc in documents), "embedding_model": "test"}
        snapshot = self.publish(mode="chroma", index_builder=builder)
        from app.retrieval.operation_retriever import retrieve_operation_candidates
        document = next(doc for doc in seen if doc["id"] == "create_vlan")
        vectorstore = SimpleNamespace(similarity_search_with_score=lambda *args, **kwargs: [(SimpleNamespace(metadata=document["metadata"]), 0.1)])
        with snapshot_scope(snapshot), patch("app.retrieval.operation_retriever.get_vectorstore", return_value=vectorstore):
            self.assertEqual(retrieve_operation_candidates("VLAN", "vlan")[0]["operation_id"], "create_vlan")
            self.assertIn("Parameter contract", document["page_content"])
            document["metadata"]["release_id"] = "wrong"
            with self.assertRaisesRegex(ValueError, "different knowledge"):
                retrieve_operation_candidates("VLAN", "vlan")

    def test_chroma_builder_stages_separate_collection_and_verifies_documents(self):
        from app.ingest import build_release_index
        release_id = "a" * 32
        metadata = {"operation_id": "create_vlan", "category": "vlan", "operation_version": 1, "release_id": release_id}
        docs = [{"id": "create_vlan", "page_content": "reviewed document", "metadata": metadata}]
        vectorstore = MagicMock()
        vectorstore.get.side_effect = [{"ids": []}, {"ids": ["create_vlan"], "metadatas": [metadata], "documents": ["reviewed document"]}]
        with patch("app.ingest.Chroma", return_value=vectorstore) as constructor, patch("app.ingest.CHROMA_DIR", self.root / "chroma"):
            receipt = build_release_index(release_id, docs)
        self.assertEqual(receipt["collection"], "knowledge_" + release_id)
        self.assertEqual(constructor.call_args.kwargs["collection_name"], receipt["collection"])
        vectorstore.delete.assert_not_called()
        vectorstore.add_documents.assert_called_once()

    def test_source_change_during_build_aborts_and_offline_never_queries_old_index(self):
        first = self.publish()
        def builder(release_id, documents):
            rows = self.read("categories")
            rows[0]["description"] = "concurrent edit"
            self.write("categories", rows)
            return {"release_id": release_id, "collection": "knowledge_" + release_id,
                    "ids": sorted(doc["id"] for doc in documents), "embedding_model": "test"}
        with self.assertRaisesRegex(ValueError, "sources or active release changed"):
            self.publish(mode="chroma", index_builder=builder)
        from app.vectorstore import get_vectorstore
        with snapshot_scope(first), self.assertRaisesRegex(ValueError, "offline"):
            get_vectorstore()

    def test_changed_published_artifact_fails_integrity_check(self):
        snapshot = self.publish()
        path = snapshot.root / "schemas/create_vlan.json"
        path.write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "artifact changed"):
            active_snapshot(self.releases)

    def test_release_change_during_render_publishes_no_partial_configs(self):
        first = self.publish()
        task = self.task(first, {"vlan_id": 20})
        def activating_render(*args):
            self.publish()
            return "vlan 20\n"
        with snapshot_scope(first), patch("app.pipeline.render", side_effect=activating_render):
            plan = refresh_plan(ExecutionPlan("create VLAN 20", tasks=[task]))
            self.assertEqual(plan.status, "failed")
            self.assertFalse(plan.tasks[0].configs)

    def test_incomplete_sibling_keeps_request_wide_gate_closed(self):
        snapshot = self.publish()
        complete = self.task(snapshot, {"vlan_id": 20})
        incomplete = self.task(snapshot)
        incomplete.intent_id = "two"
        with snapshot_scope(snapshot), patch("app.pipeline.render") as rendering:
            plan = refresh_plan(ExecutionPlan("two VLANs", tasks=[complete, incomplete]))
            self.assertEqual(plan.status, "needs_clarification")
            rendering.assert_not_called()
            self.assertFalse(any(task.configs for task in plan.tasks))

    def test_new_operation_can_declare_one_vendor_and_reuse_existing_pipeline(self):
        for name in ("operations", "operation_parameters", "operation_rules", "template_bindings"):
            rows = self.read(name)
            copies = [deepcopy(row) for row in rows if row["operation_id"] == "create_vlan" and (name != "template_bindings" or row["vendor"] == "cisco")]
            for row in copies:
                row["operation_id"] = "provision_vlan"
                if name == "operations":
                    row.update(display_name="Provision VLAN", aliases=["provision vlan"], schema_path="")
            self.write(name, rows + copies)
        snapshot = self.publish()
        with snapshot_scope(snapshot):
            task = _finalize_task(intent_id="new", request_text="Provision VLAN on R1", category="vlan",
                operation_id="provision_vlan", parameters={}, parameter_provenance={}, target_refs=["R1"])
            self.assertEqual(task.questions[0]["field_path"], "vlan_id")
            task = resume_task(task, "20")
            plan = refresh_plan(ExecutionPlan("Provision VLAN 20 on R1", tasks=[task]))
            self.assertEqual(plan.status, "ready")
            self.assertIn("vlan 20", plan.tasks[0].configs[0]["configuration"])
            with self.assertRaisesRegex(ValueError, "No declared template compatibility"):
                select_template({"vendor": "juniper", "platform": "junos", "version": "23.4"}, "provision_vlan")


if __name__ == "__main__":
    unittest.main()
