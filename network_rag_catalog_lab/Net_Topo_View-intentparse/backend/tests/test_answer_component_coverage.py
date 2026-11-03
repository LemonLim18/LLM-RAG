"""Offline evaluator tests. Run with unittest; no application conftest/imports."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("answer_component_evaluator",
    ROOT / "backend/scripts/evaluate_answer_components.py")
evaluator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluator)


class ProbeTests(unittest.TestCase):
    def probe(self, text, *literals, kind="literal"):
        return evaluator.mention_probe(text, {"kind": kind, "alternatives": [list(literals)]})

    def test_numeric_boundaries(self):
        self.assertEqual(self.probe("MTU 15000", "1500")["signal"], "REQUIRED_LITERAL_ABSENT")

    def test_markdown_numeric_mention_is_not_certification(self):
        result = self.probe("MTU **1500**", "1500")
        self.assertEqual(result["signal"], "MENTION_CANDIDATE")
        self.assertEqual(result["semantic_status"], "NOT_ASSESSED")

    def test_negation_is_not_certified_by_mention(self):
        self.assertEqual(self.probe("The MTU is not 1500", "1500")["semantic_status"], "NOT_ASSESSED")

    def test_wrong_owner_does_not_earn_a_semantic_pass(self):
        self.assertEqual(self.probe("OtherRouter has MTU 1500", "1500")["semantic_status"], "NOT_ASSESSED")

    def test_conjunction_across_sentences_is_unbound(self):
        self.assertEqual(self.probe("Later at 07:10. Earlier it was shutdown.",
            "07:10", "shutdown", kind="same_sentence")["signal"], "UNBOUND_MENTIONS")

    def test_positive_linked_literal_and_paraphrase_remain_candidates(self):
        for text in ["At 07:10 the capture says shutdown.", "Shutdown was recorded at 07:10."]:
            self.assertEqual(self.probe(text, "07:10", "shutdown", kind="same_sentence")["signal"], "MENTION_CANDIDATE")

    def test_quoted_or_denied_state_is_not_automatically_accepted(self):
        self.assertEqual(self.probe("At 07:10 'shutdown' is not established.",
            "07:10", "shutdown", kind="same_sentence")["semantic_status"], "NOT_ASSESSED")

    def test_time_not_interchangeable(self):
        self.assertEqual(self.probe("At 06:40 shutdown", "07:10", "shutdown",
            kind="same_sentence")["signal"], "REQUIRED_LITERAL_ABSENT")

    def test_human_only_never_infers_a_missing_advice_answer(self):
        for text in ["No tests performed", "Recommend reviewing existing neighbor records"]:
            self.assertEqual(evaluator.mention_probe(text, {"kind": "human_only"})["signal"], "HUMAN_REVIEW_REQUIRED")

    def test_invalid_probe_is_rejected(self):
        for probe in [{"kind": "literal", "alternatives": [[]]},
                      {"kind": "literal", "alternatives": [[""]]}, {"kind": "semantic_model"}]:
            with self.assertRaises(evaluator.ArtifactError):
                evaluator.mention_probe("text", probe)

    def test_unavailable_answer_is_not_a_missing_component(self):
        self.assertEqual(evaluator.mention_probe(None, {"kind": "human_only"})["signal"], "UNAVAILABLE")

    def test_strict_json_no_repair_or_duplicate_keys(self):
        for text in ['{"answer":"a", -timestamp: "x"}', '{"answer":"a","answer":"b"}', '{"answer":NaN}']:
            with self.assertRaises(ValueError):
                evaluator.strict_json(text)

    def test_diagnostic_answer_does_not_construct_an_object(self):
        raw = '{"answer":"correct diagnostic text", -timestamp: "x"}'
        self.assertEqual(evaluator.diagnostic_answer(raw), "correct diagnostic text")
        with self.assertRaises(ValueError):
            evaluator.strict_json(raw)

    def test_rfc_pointer_escapes_and_invalid_indexes(self):
        self.assertEqual(evaluator.pointer({"a/b": {"~": [1]}}, "/a~1b/~0/0"), 1)
        for p in ["/a~1b/~0/-1", "/a~1b/~0/01", "/a~2b"]:
            with self.assertRaises(evaluator.ArtifactError):
                evaluator.pointer({"a/b": {"~": [1]}}, p)

    def test_source_operand_types_are_not_coerced(self):
        packet = {"reader_results": [{"status": "success", "data": {"records": [{"id": "r1", "kind": "state", "up": True}]}}]}
        result = evaluator.source_requirement(packet, {"record_id": "r1", "pointer": "/up", "expected": 1})
        self.assertEqual(result["status"], "OPERAND_MISMATCH")

    def test_duplicate_record_ids_remain_ambiguous(self):
        packet = {"reader_results": [{"data": [{"id": "r", "kind": "state", "value": 1},
                                                {"id": "r", "kind": "state", "value": 2}]}]}
        self.assertEqual(evaluator.source_requirement(packet,
            {"record_id": "r", "pointer": "/value", "expected": 1})["status"], "MISSING_OR_AMBIGUOUS_RECORD")

    def test_unavailable_envelope_cannot_supply_confirmed_operands(self):
        packet = {"reader_results": [{"status": "success", "data": {"source_available": False,
            "records": [{"id": "r", "kind": "state", "value": 1}]}}]}
        self.assertEqual(evaluator.source_requirement(packet,
            {"record_id": "r", "pointer": "/value", "expected": 1})["status"], "UNAVAILABLE_SOURCE_WITH_RECORD")

    def test_no_external_execution_boundary(self):
        for event in ["socket.connect", "socket.getaddrinfo", "subprocess.Popen", "os.system", "sqlite3.connect"]:
            with self.assertRaises(RuntimeError):
                evaluator.block_external_execution(event, ())


class SavedArtifactTests(unittest.TestCase):
    def test_artifact_missing_hash_drift_and_path_boundaries(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            root = Path(folder)
            self.assertTrue(root.resolve().is_relative_to(ROOT / "tmp"))
            file = root / "saved.json"
            file.write_text('{"a":1}', encoding="utf-8")
            ref = {"path": "saved.json", "sha256": evaluator.sha256(file)}
            artifacts = evaluator.SavedArtifacts(root)
            self.assertEqual(artifacts.read(ref), {"a": 1})
            file.write_text('{"a":2}', encoding="utf-8")
            with self.assertRaises(evaluator.ArtifactError):
                artifacts.read(ref)
            for path in ["missing.json", "../outside.json", str(file.resolve()), ".env", ".env.json"]:
                with self.assertRaises(evaluator.ArtifactError):
                    artifacts.read({"path": path, "sha256": "unused"})

    def test_human_attribution_requires_real_excerpts(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            root = Path(folder)
            self.assertTrue(root.resolve().is_relative_to(ROOT / "tmp"))
            p = root / "review.json"
            p.write_text('{"review":"prior"}', encoding="utf-8")
            review = {"status": "COVERED", "reason": "previous review", "basis": {
                "path": "review.json", "sha256": evaluator.sha256(p)},
                "excerpts": [{"field": "answer", "text": "1500"}]}
            with self.assertRaises(evaluator.ArtifactError):
                evaluator.attributed_review(evaluator.SavedArtifacts(root), review,
                    {"claims": [{"statement": "MTU 1500"}]}, "No number here")


class FrozenCohortTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = ROOT / "docs/evaluations/phase_g_answer_component_coverage_v1.json"
        # Any accidental network use fails this actual saved-output replay.
        with patch.object(socket.socket, "connect", side_effect=AssertionError("offline only")) as connect:
            cls.result = evaluator.evaluate(ROOT, cls.registry)
            connect.assert_not_called()
        cls.rows = {r["identity"]: r for r in cls.result["rows"]}

    def component(self, identity, key):
        return next(c for c in self.rows[identity]["components"] if c["id"] == key)

    def test_full_declared_inventory_not_42_independent_cases(self):
        s = self.result["summary"]
        self.assertEqual(s["saved_outputs"], 42)
        self.assertEqual(s["distinct_registered_conditions"], 12)
        self.assertEqual(s["cohorts"], {"reasoning_contract_18": 18, "temporal_instruction_12": 12, "timestamp_contract_12": 12})
        self.assertEqual(s["semantic_adequacy"], "NOT_AUTOMATICALLY_SCORED")

    def test_h01_omission_is_not_hidden_by_auxiliary_value(self):
        c = self.component("timestamp_contract_12/H-01/candidate", "restored-mtu")
        self.assertEqual(c["raw_answer"]["signal"], "REQUIRED_LITERAL_ABSENT")
        self.assertEqual(c["auxiliary"]["claims"]["signal"], "MENTION_CANDIDATE")
        self.assertEqual(c["human_review"]["status"], "OMITTED")
        control = self.component("timestamp_contract_12/H-01/control", "restored-mtu")
        self.assertEqual(control["raw_answer"]["signal"], "MENTION_CANDIDATE")

    def test_h04_association_requires_review_not_global_substring_success(self):
        c = self.component("timestamp_contract_12/H-04/candidate", "later-shutdown")
        self.assertEqual(c["raw_answer"]["signal"], "UNBOUND_MENTIONS")
        self.assertEqual(c["human_review"]["status"], "OMITTED")
        self.assertEqual(c["auxiliary"]["claims"]["signal"], "MENTION_CANDIDATE")

    def test_h02_ambiguity_is_preserved_not_machine_regraded(self):
        c = self.component("timestamp_contract_12/H-02/candidate", "onset-and-causality-limitation")
        self.assertEqual(c["human_review"]["status"], "AMBIGUOUS")
        self.assertEqual(c["raw_answer"]["signal"], "HUMAN_REVIEW_REQUIRED")
        row = self.rows["timestamp_contract_12/H-02/candidate"]
        self.assertEqual(row["historical_grade_unchanged"]["whole_response_grade"], "INCORRECT_UNSUPPORTED_ONSET")

    def test_h05_advice_not_conflated_with_rubric_caveat(self):
        for arm in ["control", "candidate"]:
            prefix = "timestamp_contract_12/H-05/" + arm
            self.assertEqual(self.component(prefix, "passive-artifacts")["human_review"]["status"], "COVERED")
            caveat = self.component(prefix, "model-versus-measured-response")
            self.assertEqual(caveat["human_review"]["status"], "OMITTED")
            self.assertIn("not_separate_literal_subquestion", caveat["basis"])

    def test_rc04_old_positive_and_later_omissions_remain_distinct(self):
        for arm in ["control", "candidate"]:
            c = self.component("temporal_instruction_12/RC-04/" + arm, "passive-recommendation")
            self.assertEqual(c["human_review"]["status"], "OMITTED")
        c = self.component("reasoning_contract_18/RC-04/off", "passive-recommendation")
        self.assertEqual(c["human_review"]["status"], "COVERED")

    def test_positive_controls_not_labeled_missing_by_mention_probes(self):
        for cid in ["H-03", "H-06"]:
            c = self.rows["timestamp_contract_12/" + cid + "/candidate"]
            self.assertTrue(all(x["human_review"]["status"] == "COVERED" for x in c["components"]))
            self.assertFalse(any(x["raw_answer"]["signal"] == "REQUIRED_LITERAL_ABSENT" for x in c["components"]))

    def test_h06_invalid_json_is_never_a_successful_released_answer(self):
        row = self.rows["timestamp_contract_12/H-06/control"]
        self.assertEqual(row["structured_output"], "INVALID_JSON_OR_ANSWER")
        self.assertEqual(row["raw_prose_scope"], "DIAGNOSTIC_STRING_ONLY_NOT_RELEASABLE")
        self.assertFalse(row["original_release_exists"])
        self.assertEqual(row["semantic_complete_task_score"], "NOT_COMPUTED")

    def test_exact_request_and_operands_have_separate_status(self):
        s = self.result["summary"]
        self.assertTrue(s["all_exact_requests"])
        self.assertTrue(s["all_checked_source_operands_present"])
        self.assertTrue(s["all_packets_within_limit"])
        self.assertEqual(s["json_objects_with_answer"], 41)
        self.assertIn("NOT_REEXECUTED", s["schema_validation"])
        self.assertEqual(s["unsupported_inference_incidence"], "HUMAN_REVIEW_REQUIRED_NOT_AUTOMATICALLY_COMPUTED")
        self.assertFalse(self.result["runtime_integration"])
        self.assertFalse(self.result["promotion"])

    def test_duplicate_outputs_fail_closed(self):
        spec = json.loads(self.registry.read_text(encoding="utf-8"))
        spec["outputs"].append(copy.deepcopy(spec["outputs"][0]))
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            self.assertTrue(Path(folder).resolve().is_relative_to(ROOT / "tmp"))
            file = Path(folder) / "registry.json"
            file.write_text(json.dumps(spec), encoding="utf-8")
            with self.assertRaises(evaluator.ArtifactError):
                evaluator.evaluate(ROOT, file)


if __name__ == "__main__":
    unittest.main()
