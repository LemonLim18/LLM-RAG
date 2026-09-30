"""Eight explicit live checks for the approved catalog activation."""

import argparse
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.catalog import load_operations
from app.clarification import apply_answer, create_session, load_session
from app.config import BASE_DIR
from app.knowledge.authoring_store import _atomic_json
from app.knowledge.runtime import active_snapshot
from app.pipeline import retrieve_operation_candidates
from app.questions import answer_from_text
from app.retrieval.operation_selector import _explicit_operation

CASES = [
    {"id": "vlan_paraphrase", "prompt": 'Give the VLAN a different label: vlan_id 20, name "ENGINEERING" on SW1',
     "bindings": [("rename_vlan", "SW1")], "parameters": {"vlan_id": 20, "new_vlan_name": "ENGINEERING"}, "rag": True},
    {"id": "interface", "prompt": 'Set interface description, interface "GigabitEthernet1/0/1", description "User port" on SW1',
     "bindings": [("set_interface_description", "SW1")], "parameters": {"interface": "GigabitEthernet1/0/1", "description": "User port"}},
    {"id": "routing_paraphrase", "prompt": 'For static routing, send unmatched IPv4 traffic through next_hop "192.0.2.2" with preference 200 on SW1',
     "bindings": [("add_default_route", "SW1")], "parameters": {"next_hop": "192.0.2.2", "preference": 200}, "rag": True},
    {"id": "ospf", "prompt": 'Enable OSPF process, process_id 200, router_id "192.0.2.200" on SW1',
     "bindings": [("enable_ospf_process", "SW1")], "parameters": {"process_id": 200, "router_id": "192.0.2.200"}},
    {"id": "acl", "prompt": 'Create ACL, acl_name "NEW_ACL", description "Reviewed policy" on SW1',
     "bindings": [("create_acl", "SW1")], "parameters": {"acl_name": "NEW_ACL", "description": "Reviewed policy"}},
    {"id": "qos", "prompt": 'Create classifier, classifier_name "NEW_CLASS", dscp_values [46,34], match_mode "any" on SW1',
     "bindings": [("create_classifier", "SW1")], "parameters": {"classifier_name": "NEW_CLASS", "dscp_values": [46, 34], "match_mode": "any"}},
    {"id": "clarification_resume", "prompt": "Configure OSPF on R2", "resume": True,
     "bindings": [("configure_ospf", "R2")], "parameters": {"process_id": 100, "interfaces": [{"name": "GigabitEthernet0/0/0", "area": "0"}]}},
    {"id": "mixed_targets", "prompt": 'Create VLAN 100 named STAFF on R1 and R2; set interface description, interface "GigabitEthernet1/0/1", description "User port" on SW1',
     "bindings": [("create_vlan", "R1"), ("create_vlan", "R2"), ("set_interface_description", "SW1")]},
]


def bindings(session):
    return [(task.operation_id, device["hostname"]) for task in session.plan.tasks for device in task.target_devices]


def check(case):
    started = time.monotonic()
    report = {"id": case["id"], "prompt": case["prompt"], "passed": False, "questions": []}
    session = None
    try:
        if case.get("rag"):
            assert _explicit_operation(case["prompt"], load_operations()) is None, "Paraphrase took literal shortcut"
        with patch("app.pipeline.retrieve_operation_candidates", wraps=retrieve_operation_candidates) as retrieval:
            session = create_session(case["prompt"])
            report["retrieval_calls"] = retrieval.call_count
        report["session_id"] = session.session_id
        report["initial_status"] = session.status
        report["initial_bindings"] = bindings(session)
        report["initial_selection_matches"] = sorted(bindings(session)) == sorted(case["bindings"])
        if not report["initial_selection_matches"]:
            assert case.get("rag") and session.next_question and session.next_question["field_path"] == "operation_id", f"Unexpected initial bindings: {bindings(session)}"
            assert len(session.plan.tasks) == 1
            assert [device["hostname"] for device in session.plan.tasks[0].target_devices] == [case["bindings"][0][1]]
        if case.get("rag"):
            assert report["retrieval_calls"] > 0, "RAG was not exercised"
        if case.get("resume"):
            assert session.status == "needs_clarification"
            session = load_session(session.session_id)
        for _ in range(8):
            question = session.next_question
            if question is None:
                break
            assert not any(task.configs for task in session.plan.tasks), "Incomplete request produced config"
            path = question["field_path"]
            if path == "operation_id":
                answer = case["bindings"][0][0]
            elif path in case.get("parameters", {}):
                value = case["parameters"][path]
                answer = value if isinstance(value, str) else json.dumps(value)
            else:
                raise AssertionError(f"Unexpected clarification: {path}")
            report["questions"].append({"field": path, "answer": answer, "options": len(question["options"])})
            session = apply_answer(session, answer_from_text(question, answer))
            assert not any(task.feedback for task in session.plan.tasks), [task.feedback for task in session.plan.tasks]
        assert session.status == "ready", session.status
        assert sorted(bindings(session)) == sorted(case["bindings"])
        for task in session.plan.tasks:
            expected = case.get("parameters")
            if expected is None:
                expected = ({"vlan_id": 100, "name": "STAFF"} if task.operation_id == "create_vlan"
                            else {"interface": "GigabitEthernet1/0/1", "description": "User port"})
            assert task.parameters == expected, task.parameters
            assert task.configs and all(config["configuration"].strip() for config in task.configs)
        report["passed"] = True
    except Exception as exc:
        report["error"] = str(exc)
    if session:
        report["final_status"] = session.status
        report["tasks"] = [{"operation": task.operation_id, "devices": [device["hostname"] for device in task.target_devices],
                            "parameters": task.parameters, "issues": task.issues, "feedback": task.feedback,
                            "configs": task.configs} for task in session.plan.tasks]
    report["seconds"] = round(time.monotonic() - started, 3)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=[case["id"] for case in CASES])
    args = parser.parse_args()
    reports = []
    for case in CASES:
        if args.case and args.case != case["id"]:
            continue
        report = check(case)
        reports.append(report)
        print(json.dumps({key: report.get(key) for key in ("id", "passed", "seconds", "retrieval_calls", "initial_selection_matches", "error", "questions")}), flush=True)
    result = {"release_id": active_snapshot().release_id, "cases": reports}
    destination = BASE_DIR / "storage/catalog_authoring" / ("activation-smoke" + ("-" + args.case if args.case else "") + ".json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    _atomic_json(destination, result)
    raise SystemExit(0 if all(report["passed"] for report in reports) else 1)


if __name__ == "__main__":
    main()
