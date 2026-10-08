"""Transport-neutral question/answer contract for terminal and future UI clients."""

from hashlib import sha256
import json
import re

from .catalog import get_operation, load_operations
from .context import candidate_valid, parameter_options
from .devices.inventory import load_inventory
from .devices.target_resolver import TARGET_ISSUES
from .parameters.fields import get_value, schema_at, tokens
from .parameters.normalizer import parameter_metadata
from .parameters.schema_loader import load_schema
from .planner.models import ClarificationAnswer


def _id(value) -> str:
    return sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()[:16]


def build_questions(task) -> list[dict]:
    questions = []
    schema = load_schema(task.operation_id, task.target_devices) if task.operation_id else {}
    order = schema.get("required", []) + [key for key in schema.get("properties", {}) if key not in schema.get("required", [])]
    def priority(issue):
        if issue["field"] == "operation_id":
            return (0, 0)
        if issue["type"] in TARGET_ISSUES:
            return (1, 0)
        root = tokens(issue["field"])[0]
        return (2, order.index(root) if root in order else len(order))
    seen = set()
    for issue in sorted(task.issues, key=priority):
        path = issue["field"]
        identity = (path, issue.get("query_index"))
        if identity in seen:
            continue
        seen.add(identity)
        options = []
        expected = {"type": "string"}
        multiple = False
        dependencies = []
        wording = issue["message"]
        if issue["type"] in TARGET_ISSUES:
            candidates = issue.get("candidates", [])
            if not candidates:
                candidates = [{"hostname": d["hostname"], "label": f"{d['hostname']} ({d['site']}, {d['role']}, {d['vendor']})"} for d in load_inventory()]
            for candidate in candidates:
                options.append({"value": candidate["hostname"], "label": candidate["label"], "source_ref": "inventory:" + candidate["hostname"], "explanation": "Confirm this device; selection replaces the unresolved description."})
            multiple = issue["type"] == "MISSING_TARGET" or any(q.get("cardinality") == "many" for q in task.target_queries)
        elif path == "operation_id":
            ranked = list(dict.fromkeys([task.operation_id, *task.operation_candidates]))
            operations = sorted(load_operations(), key=lambda op: ranked.index(op["operation_id"])
                                if op["operation_id"] in ranked else len(ranked))
            for operation in operations:
                if task.target_devices and any(operation["category_id"] not in d.get("capabilities", {}).get("features", []) for d in task.target_devices):
                    continue
                options.append({"value": operation["operation_id"], "label": operation["display_name"], "source_ref": "catalog:" + operation["operation_id"], "explanation": operation["description"]})
                if issue["type"] == "OPERATION_PROPOSAL" and operation["operation_id"] == task.operation_id:
                    options[-1]["label"] = "Confirm " + operation["display_name"] + " (proposed)"
        else:
            expected = schema_at(schema, path)
            multiple = expected.get("type") == "array"
            dependencies = ["target_refs"]
            if task.target_devices:
                options = parameter_options(task.operation_id, task.target_devices[0], path, task.parameters, task.source_revision)
            field = tokens(path)[-1]
            try:
                metadata = parameter_metadata(field, expected)
                wording = metadata.get("clarification", wording) if issue["type"] == "MISSING" else wording
            except KeyError:
                pass
            if path.startswith("interfaces["):
                parent = path.rsplit(".", 1)[0]
                name = get_value(task.parameters, parent + ".name")
                if field == "name":
                    wording = "Which interface should this entry use?"
                elif name:
                    wording = f"{name}: {wording}"
                    dependencies.append(parent + ".name")
            if path in {"address", "prefix_length"}:
                dependencies.append("interface")
            if issue.get("allow_override"):
                options.insert(0, {"value": issue["value"], "label": f"Confirm proposed change: {issue['value']}", "source_ref": "user:proposed-change", "explanation": "Explicit override of the planned assignment.", "override": True})
            for value in issue.get("values", []):
                if not task.target_devices or candidate_valid(task.operation_id, task.target_devices[0], path, value, task.parameters):
                    options.append({"value": value, "label": str(value), "source_ref": "user:original-request", "explanation": "Alternative explicitly present in the request."})
            suggestions = issue.get("suggestions", [])
            options.sort(key=lambda option: suggestions.index(option["value"]) if option["value"] in suggestions else len(suggestions))
            for value in expected.get("enum", []):
                options.append({"value": value, "label": str(value), "source_ref": f"schema:{task.operation_id}:{path}", "explanation": "Allowed schema value."})
        for option in options:
            option.setdefault("source_revision", task.source_revision)
            option["option_id"] = _id([path, option["value"], option["source_ref"]])
        item_path = path.rsplit(".", 1)[0] if "[" in path else None
        if item_path:
            task.item_ids.setdefault(item_path, _id([task.intent_id, item_path, task.revision]))
        question = {"question_id": _id([task.intent_id, identity, task.item_ids.get(item_path)]),
                    "task_id": task.intent_id, "binding_id": task.intent_id, "device_id": task.device_id,
                    "field_path": path, "item_id": task.item_ids.get(item_path), "issue_type": issue["type"],
                    "wording": wording, "expected_schema": expected, "dependencies": dependencies,
                    "revision": task.revision, "source_revision": task.source_revision,
                    "options": options, "multiple": multiple, "allow_custom": True}
        question["operation_id"] = task.operation_id
        question["operation_label"] = get_operation(task.operation_id)["display_name"] if task.operation_id else "Choose operation"
        question["device_label"] = ", ".join(device["hostname"] for device in task.target_devices) or "Target unresolved"
        questions.append(question)
    return questions


def answer_from_text(question: dict, reply: str) -> ClarificationAnswer:
    answer = ClarificationAnswer(question["question_id"], question["revision"], question["source_revision"])
    if reply.lower().startswith("select "):
        parts = re.split(r"\s*,\s*|\s+", reply[7:].strip())
        if not parts or any(not part.isdigit() for part in parts):
            raise ValueError("Use select followed by option numbers, for example select 1 or select 1,2.")
        if any(not 1 <= int(part) <= len(question["options"]) for part in parts):
            raise ValueError("That option number is not available.")
        answer.kind = "selection"
        answer.selected_ids = list(dict.fromkeys(question["options"][int(part) - 1]["option_id"] for part in parts))
    else:
        answer.raw_input = reply[6:] if reply.lower().startswith("value ") else reply
    return answer


def selected_options(question: dict, answer: ClarificationAnswer) -> list[dict]:
    if answer.kind != "selection":
        return []
    lookup = {option["option_id"]: option for option in question["options"]}
    if not answer.selected_ids or len(set(answer.selected_ids)) != len(answer.selected_ids) or any(key not in lookup for key in answer.selected_ids):
        raise ValueError("Answer contains an unavailable option.")
    if len(answer.selected_ids) > 1 and not question["multiple"]:
        raise ValueError("Select exactly one option for this field.")
    return [lookup[key] for key in answer.selected_ids]
