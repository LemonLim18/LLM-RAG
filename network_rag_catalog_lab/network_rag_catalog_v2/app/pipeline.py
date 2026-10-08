"""Collect and validate per-device bindings; render only a complete request."""

from copy import deepcopy
from dataclasses import asdict
import json

from .catalog import get_operation, load_operations, reload_catalog, validate_catalog
from .context import context_conflicts, context_revision, rules, source_revision, validate_context_catalog
from .knowledge.runtime import current_snapshot, snapshot_request
from .devices.context_validator import normalize_parameters_for_device, validate_device_context
from .devices.inventory import load_inventory
from .devices.target_query import extract_target_queries, parameter_request, parse_description
from .devices.target_resolver import TARGET_ISSUES, refine_queries, resolve_queries
from .parameters.fields import get_value, leaf_values, parse_answer, schema_at, set_value
from .parameters.parameter_extractor import extract_parameter_result
from .parameters.schema_loader import load_schema
from .parameters.validator import validate_parameter_result
from .planner.intent_planner import plan_intents
from .planner.models import ClarificationAnswer, ExecutionPlan, PlannedTask
from .questions import answer_from_text, build_questions, selected_options
from .retrieval.category_classifier import classify_category
from .retrieval.operation_retriever import retrieve_operation_candidates
from .retrieval.operation_selector import _explicit_operation, select_operation
from .templates.renderer import render
from .templates.template_selector import select_template


def _unsupported_parameters(params, schema, path=""):
    """Keep explicit values visible when a vendor contract excludes their fields."""
    if isinstance(params, dict):
        for key, value in params.items():
            field = f"{path}.{key}" if path else key
            child = schema.get("properties", {}).get(key)
            if child is None and value is not None and schema.get("additionalProperties") is False:
                yield field, value
            elif child is not None:
                yield from _unsupported_parameters(value, child, field)
    elif isinstance(params, list):
        for index, value in enumerate(params):
            yield from _unsupported_parameters(value, schema.get("items", {}), f"{path}[{index}]")


def _runtime_authority(snapshot):
    from .config import runtime_mode
    return "published" if snapshot else "files" if runtime_mode() == "files" else "authoring_files"


def _validation(task, params, schema):
    issues = [vars(issue) for issue in validate_parameter_result(params, schema).issues]
    issues += validate_device_context(task.operation_id, task.category, params, task.target_devices)
    return issues


def _record_candidate(task, issue, value):
    task.candidates = [candidate for candidate in task.candidates if candidate["field"] != issue["field"]]
    task.candidates.append({**issue, "value": value, "source": "user", "evidence": task.request_text,
                            "device_id": task.device_id, "operation_id": task.operation_id, "validation": "rejected"})


def _refresh_task(task: PlannedTask, revision: str | None = None) -> PlannedTask:
    revision = revision or source_revision()
    task.configs = []
    if task.source_revision and task.source_revision != revision:
        task.revision += 1
        task.confirmations = {}
        for candidate in task.candidates:
            if candidate["type"] == "CONTEXT_CONFLICT":
                task.parameters = set_value(task.parameters, candidate["field"], candidate["value"])
        task.candidates = [candidate for candidate in task.candidates if candidate["type"] != "CONTEXT_CONFLICT"]
        # Context-derived decisions require reconfirmation after source changes.
        for path, provenance in list(task.parameter_provenance.items()):
            if provenance.startswith("context:") and not provenance.startswith(("context:inventory:", "context:schema:")):
                task.parameters = set_value(task.parameters, path, None)
                task.parameter_provenance.pop(path, None)
    task.source_revision = revision
    snapshot = current_snapshot()
    task.knowledge_snapshot_id = snapshot.release_id if snapshot else ""
    task.runtime_authority = _runtime_authority(snapshot)
    task.context_revision = context_revision()
    if not task.target_queries and task.target_refs:
        task.target_queries = [parse_description(ref, load_inventory()) for ref in task.target_refs]
    resolution = resolve_queries(task.target_queries)
    task.target_resolution = resolution["evidence"]
    devices = resolution["devices"]
    target_issues = resolution["issues"]
    membership = sorted(device["id"] for device in devices)
    if task.scope_device_ids and membership and membership != task.scope_device_ids and task.device_id:
        target_issues = [{"type": "TARGET_CONFLICT", "field": "target_refs",
                          "message": "Inventory group membership changed. Confirm the target(s) for this binding before proceeding."}]
    elif not task.scope_device_ids and membership:
        task.scope_device_ids = membership
    if task.device_id and devices:
        devices = [device for device in devices if device["id"] == task.device_id]
        if not devices:
            target_issues = [{"type": "TARGET_CONFLICT", "field": "target_refs", "message": "The previously selected device no longer matches this binding. Confirm a target."}]
    task.target_devices = devices
    if len(devices) == 1:
        task.device_id = devices[0]["id"]
        task.target_resolution = [
            {**evidence, "selected": [candidate for candidate in evidence["selected"] if candidate["device_id"] == task.device_id]}
            for evidence in resolution["evidence"]
            if any(candidate["device_id"] == task.device_id for candidate in evidence["selected"])
        ]
    issues = [*task.planning_issues, *target_issues]
    try:
        operation = get_operation(task.operation_id)
        task.category = operation["category_id"]
        schema = load_schema(task.operation_id, devices)
    except (KeyError, ValueError, OSError) as exc:
        task.operation_id = ""
        task.category = ""
        task.parameter_evidence = {}
        task.confirmations = {}
        task.item_ids = {}
        issues.insert(0, {"type": "UNRESOLVED_OPERATION", "field": "operation_id", "message": "Choose a supported operation. " + str(exc)})
        schema = None
    if schema:
        for field in list(task.parameters):
            if task.parameters[field] is None and field not in schema.get("required", []):
                task.parameters.pop(field)
        if len(devices) == 1:
            normalized = normalize_parameters_for_device(task.parameters, devices[0])
            for path, value in leaf_values(normalized):
                if value != get_value(task.parameters, path):
                    task.parameter_provenance[path] = "inventory_normalization"
            task.parameters = normalized
        unsupported = list(_unsupported_parameters(task.parameters, schema))
        for candidate in task.candidates:
            try:
                schema_at(schema, candidate["field"])
            except ValueError:
                unsupported.append((candidate["field"], candidate.get("values", candidate.get("value"))))
        boundary_issues = []
        target = ", ".join(f"{d['hostname']} / {d['vendor']} {d['platform']}" for d in devices) or "unresolved target"
        for field, value in unsupported:
            boundary_issues.append({"type": "PARAMETER_UNSUPPORTED_FOR_VENDOR", "field": "operation_id",
                                    "requested_field": field, "value": value, "device_id": task.device_id,
                                    "message": f"Explicit parameter {field}={value!r} is not supported by {task.operation_id} for {target}. Choose an operation that implements the requested intent or explicitly correct the target."})
        for device in devices:
            try:
                select_template(device, task.operation_id)
            except (FileNotFoundError, ValueError) as exc:
                boundary_issues.append({"type": "UNSUPPORTED_OPERATION", "field": "operation_id", "message": str(exc)})
        issues.extend(boundary_issues)
        # Capability/semantic mismatches must be resolved before asking for
        # vendor-native inputs or mutating the user's explicit parameters.
        validation = [] if boundary_issues else _validation(task, task.parameters, schema)
        for issue in validation:
            if issue["type"] in {"MISSING", "UNSUPPORTED_OPERATION"}:
                continue
            path = issue["field"]
            if path == "<root>":
                issues.append({"type": "UNRESOLVED_OPERATION", "field": "operation_id", "message": issue["message"]})
                continue
            value = get_value(task.parameters, path)
            if value is not None:
                _record_candidate(task, issue, value)
                task.parameters = set_value(task.parameters, path, None)
                task.parameter_provenance.pop(path, None)
            else:
                issues.append(issue)
        issues.extend(issue for issue in validation if issue["type"] == "UNSUPPORTED_OPERATION")
        if not boundary_issues:
            issues.extend(candidate for candidate in task.candidates if get_value(task.parameters, candidate["field"]) is None)
            issues.extend(vars(issue) for issue in validate_parameter_result(task.parameters, schema).issues if issue.type == "MISSING")
        if len(devices) == 1 and not boundary_issues:
            for issue in context_conflicts(task.operation_id, devices[0], task.parameters, task.confirmations, revision):
                _record_candidate(task, issue, issue["value"])
                task.parameters = set_value(task.parameters, issue["field"], None)
                issues.insert(0, issue)
    # Dependent parameter questions wait until operation and targets are grounded.
    blockers = [issue for issue in issues if issue["field"] == "operation_id" or issue["type"] in TARGET_ISSUES]
    task.issues = blockers or issues
    accepted_evidence = {}
    for path, value in leaf_values(task.parameters):
        if value is None:
            continue
        previous = task.parameter_evidence.get(path)
        root = path.split("[", 1)[0].split(".", 1)[0]
        source = task.parameter_provenance.get(path, task.parameter_provenance.get(root, "user"))
        validation_state = "blocked" if any(issue["type"] in {"UNSUPPORTED_OPERATION", "PARAMETER_UNSUPPORTED_FOR_VENDOR"} for issue in issues) else "accepted"
        if schema is None:
            validation_state = "unvalidated"
        same_context = previous and all(previous.get(key) == expected for key, expected in {
            "value": value, "source": source, "operation_id": task.operation_id,
            "device_id": task.device_id, "source_revision": revision, "validation": validation_state,
        }.items())
        evidence = previous if same_context else {
            "value": value, "source": source, "source_revision": revision,
            "evidence": task.clarification_history[-1] if source.startswith(("clarification", "context:")) and task.clarification_history else task.request_text,
            "device_id": task.device_id, "operation_id": task.operation_id, "validation": validation_state,
        }
        accepted_evidence[path] = evidence
    task.parameter_evidence = accepted_evidence
    task.status = "needs_clarification" if task.issues else "validated"
    task.questions = build_questions(task)
    task.clarification_questions = [question["wording"] for question in task.questions]
    return task


@snapshot_request
def _finalize_task(*, intent_id, request_text, category, operation_id, parameters,
                   parameter_provenance, target_refs, target_queries=None,
                   clarification_history=None, verbose=False, **extra) -> PlannedTask:
    """Compatibility entry point: finalizes collection, never renders a task."""
    queries = target_queries if target_queries is not None else [parse_description(ref, load_inventory()) for ref in target_refs]
    task = PlannedTask(intent_id, request_text, category, operation_id, deepcopy(parameters), target_refs,
                       parameter_provenance=deepcopy(parameter_provenance), target_queries=queries,
                       clarification_history=clarification_history or [], logical_intent_id=intent_id, **extra)
    return _refresh_task(task)


def _split_bindings(task: PlannedTask) -> list[PlannedTask]:
    if task.planning_issues:
        return [_refresh_task(task)]
    resolution = resolve_queries(task.target_queries)
    if resolution["issues"] or len(resolution["devices"]) <= 1 or task.device_id:
        return [_refresh_task(task)]
    bindings = []
    for device in resolution["devices"]:
        binding = deepcopy(task)
        binding.intent_id = f"{task.intent_id}:{device['id']}"
        binding.device_id = device["id"]
        binding.logical_intent_id = task.logical_intent_id or task.intent_id
        bindings.append(_refresh_task(binding))
    return bindings


def _process_intent(intent, index=1, verbose=False) -> list[PlannedTask]:
    queries = extract_target_queries(intent.target_text or intent.request_text, load_inventory(), allow_llm=True)
    task = PlannedTask(intent.intent_id, intent.request_text, "", "", {}, [query["text"] for query in queries],
                       target_queries=queries, logical_intent_id=intent.intent_id, planning_issues=deepcopy(intent.issues),
                       source_spans=deepcopy(intent.source_spans))
    try:
        # Exact active catalog phrases work without embeddings or a model service.
        operation = _explicit_operation(intent.request_text, load_operations())
        proposed_operation = operation is None
        if operation is None:
            category = classify_category(intent.request_text)
            retrieved = retrieve_operation_candidates(intent.request_text, category, 3)
            task.operation_candidates = [candidate["operation_id"] for candidate in retrieved]
            operation = select_operation(intent.request_text, category, retrieved)
        task.operation_id = operation
        task.category = get_operation(operation)["category_id"]
        # Extract against the canonical/all-profile vocabulary before applying
        # the selected vendor's validation contract in _refresh_task.
        schema = load_schema(operation)
        extraction = extract_parameter_result(parameter_request(intent.request_text, queries), schema)
        task.parameters, task.parameter_provenance = extraction.parameters, extraction.provenance
        task.candidates = [{**candidate, "message": candidate.get("message", f"Several explicit values were supplied for {candidate['field']}. Choose one.")} for candidate in extraction.candidates]
        if proposed_operation:
            task.planning_issues.insert(0, {"type": "OPERATION_PROPOSAL", "field": "operation_id",
                                           "message": f"The model proposes {get_operation(operation)['display_name']}. Confirm the intended catalog operation."})
    except Exception as exc:
        task.feedback = "Operation resolution needs clarification: " + str(exc)
    return _split_bindings(task)


def next_clarification(task: PlannedTask) -> dict | None:
    return task.issues[0] if task.issues else None


def next_clarification_prompt(task: PlannedTask) -> tuple[str, str]:
    if not task.questions:
        task.questions = build_questions(task)
    question = task.questions[0] if task.questions else None
    return (question["field_path"], question["wording"]) if question else ("", "")


def _reject(task, message, answer=None):
    rejected = deepcopy(task)
    rejected.feedback = message
    if answer:
        rejected.clarification_history.append({"answer": asdict(answer), "accepted": False, "reason": message})
    return rejected


@snapshot_request
def resume_task(task: PlannedTask, reply: str | ClarificationAnswer, *, verbose=False) -> PlannedTask:
    if task.knowledge_snapshot_id and current_snapshot() is None:
        return _reject(task, "Published knowledge is unavailable; restore the active release before continuing.")
    if task.status == "collecting":
        task = _refresh_task(deepcopy(task))
    if task.status != "needs_clarification":
        raise ValueError("This task has no pending question; use an explicit correction.")
    if not task.questions:
        task = _refresh_task(deepcopy(task))
    question = task.questions[0]
    try:
        answer = answer_from_text(question, reply) if isinstance(reply, str) else reply
        if (answer.question_id, answer.revision, answer.source_revision) != (question["question_id"], question["revision"], question["source_revision"]):
            raise ValueError("Stale answer: reload the current question.")
        if source_revision() != question["source_revision"]:
            reload_catalog()
            updated = _refresh_task(deepcopy(task))
            return _reject(updated, "Source context changed. Review the refreshed question before answering.", answer)
        options = selected_options(question, answer)
        if answer.kind not in {"custom", "selection"}:
            raise ValueError("Unknown answer kind.")
        updated = deepcopy(task)
        path = question["field_path"]
        source = "clarification_user"
        if question["issue_type"] in TARGET_ISSUES:
            text = " and ".join(option["value"] for option in options) if options else answer.raw_input
            issue = next(issue for issue in task.issues if issue["field"] == path)
            queries = (extract_target_queries(text, load_inventory(), reply=True, allow_llm=True)
                       if task.device_id and len(task.scope_device_ids) > 1
                       else refine_queries(task.target_queries, issue, text, allow_llm=True))
            confirming_scope = any(issue["type"] in TARGET_ISSUES for issue in task.planning_issues)
            if not queries or (queries == task.target_queries and not confirming_scope and not options):
                raise ValueError("No new device evidence found; select an option or describe a device.")
            updated.target_queries = queries
            updated.target_refs = [query["text"] for query in queries]
            updated.device_id = None
            updated.scope_device_ids = []
            updated.planning_issues = [issue for issue in updated.planning_issues if issue["type"] not in TARGET_ISSUES]
            updated.confirmations = {}
            updated.parameter_evidence = {}
        elif path == "operation_id":
            operation = options[0]["value"] if options else answer.raw_input.strip()
            try:
                metadata = get_operation(operation)
            except KeyError:
                matched = _explicit_operation(operation, load_operations())
                metadata = get_operation(matched or operation)
            updated.operation_id = metadata["operation_id"]
            updated.planning_issues = [issue for issue in updated.planning_issues if issue["field"] != "operation_id"]
            updated.category = metadata["category_id"]
            schema = load_schema(updated.operation_id)
            extraction = extract_parameter_result(parameter_request(task.request_text, task.target_queries), schema)
            updated.parameters = extraction.parameters
            updated.parameter_provenance = extraction.provenance
            updated.candidates = [{**candidate, "message": candidate.get("message", "Choose one explicitly supplied value.")} for candidate in extraction.candidates]
            updated.confirmations = {}
            updated.parameter_evidence = {}
            updated.item_ids = {}
            updated.operation_candidates = []
            updated.questions = []
            updated.clarification_questions = []
        else:
            schema = load_schema(task.operation_id, task.target_devices)
            if options:
                value = [item for option in options for item in option["value"]] if question["multiple"] else options[0]["value"]
                source = "context:" + ",".join(option["source_ref"] for option in options)
            else:
                value = parse_answer(answer.raw_input, path, schema_at(schema, path))
            proposed = set_value(task.parameters, path, value)
            if len(task.target_devices) == 1:
                proposed = normalize_parameters_for_device(proposed, task.target_devices[0])
            old_errors = {(issue["type"], issue["field"], issue["message"]) for issue in _validation(task, task.parameters, schema) if issue["type"] != "MISSING"}
            errors = [issue for issue in _validation(task, proposed, schema) if issue["type"] != "MISSING" and (issue["type"], issue["field"], issue["message"]) not in old_errors]
            if errors:
                raise ValueError("; ".join(issue["message"] for issue in errors))
            updated.parameters = proposed
            if isinstance(value, list):
                old_items = get_value(task.parameters, path, []) or []
                identities = {item.get("name"): task.item_ids.get(f"{path}[{index}]") for index, item in enumerate(old_items) if isinstance(item, dict)}
                updated.item_ids = {key: identity for key, identity in task.item_ids.items() if not key.startswith(path + "[")}
                for index, item in enumerate(value):
                    identity = identities.get(item.get("name")) if isinstance(item, dict) else None
                    if identity:
                        updated.item_ids[f"{path}[{index}]"] = identity
            updated.parameter_provenance[path] = source
            updated.candidates = [candidate for candidate in task.candidates if candidate["field"] != path and not candidate["field"].startswith(path + "[")]
            if options and options[0].get("override"):
                updated.confirmations[path] = {"value": value, "source_revision": task.source_revision}
            if question["issue_type"] == "CONTEXT_CONFLICT" and not options:
                conflict = next(issue for issue in task.issues if issue["field"] == path)
                if conflict.get("allow_override"):
                    updated.confirmations[path] = {"value": value, "source_revision": task.source_revision}
        updated.revision += 1
        updated.feedback = ""
        updated.clarification_history.append({"answer": asdict(answer), "field": path, "accepted": True,
                                              "source": source, "updated_fields": [path]})
        return _refresh_task(updated)
    except (ValueError, KeyError, TypeError, IndexError) as exc:
        return _reject(task, str(exc), locals().get("answer"))


@snapshot_request
def correct_task(task: PlannedTask, path: str, reply: str) -> PlannedTask:
    """Explicit edits use the same validation boundary and invalidate old artifacts."""
    editable = deepcopy(task)
    editable.status = "needs_clarification"
    if path == "target_refs":
        editable.issues = [{"type": "MISSING_TARGET", "field": path, "message": "Choose replacement target devices."}]
    elif path == "operation_id":
        editable.issues = [{"type": "UNRESOLVED_OPERATION", "field": path, "message": "Choose the replacement operation."}]
    else:
        schema_at(load_schema(task.operation_id, task.target_devices), path)
        editable.issues = [{"type": "CORRECTION", "field": path, "message": f"Enter the corrected {path}."}]
    editable.questions = build_questions(editable)
    edited = resume_task(editable, reply)
    if edited.feedback:
        return _reject(task, edited.feedback)
    if path in {"target_refs", "interface", "interfaces"} or path.endswith(".name"):
        for dependent, provenance in list(edited.parameter_provenance.items()):
            if dependent != path and provenance.startswith("context:") and not provenance.startswith(("context:inventory:", "context:schema:")):
                edited.parameters = set_value(edited.parameters, dependent, None)
                edited.parameter_provenance.pop(dependent, None)
        edited.confirmations = {}
        _refresh_task(edited)
    edited.configs = []
    return edited


def _cross_task_issues(tasks):
    issues = []
    registry = rules()["operations"]
    def resources(task):
        from .knowledge.resource_keys import composite_values
        result = composite_values(registry.get(task.operation_id, {}), task.parameters)
        result.update(str(value) for value in registry.get(task.operation_id, {}).get("resource_constants", []))
        for path in registry.get(task.operation_id, {}).get("resource_keys", []):
            if path.endswith("[]"):
                result.update(str(item) for item in task.parameters.get(path[:-2], []) if item is not None)
            elif "[]" in path:
                root, child = path.split("[].")
                result.update(str(item.get(child)) for item in task.parameters.get(root, []) if isinstance(item, dict) and item.get(child) is not None)
            elif get_value(task.parameters, path) is not None:
                result.add(str(get_value(task.parameters, path)))
        return result
    for index, left in enumerate(tasks):
        for right in tasks[index + 1:]:
            if left.device_id != right.device_id or not resources(left).intersection(resources(right)):
                continue
            if (right.operation_id in registry.get(left.operation_id, {}).get("conflicts_with", [])
                    or left.operation_id in registry.get(right.operation_id, {}).get("conflicts_with", [])
                    or (left.operation_id == right.operation_id and left.parameters != right.parameters)):
                issues.append({"type": "CROSS_TASK_CONFLICT", "tasks": [left.intent_id, right.intent_id],
                               "message": f"{left.intent_id} and {right.intent_id} propose conflicting changes to the same resource. Correct a task or explicitly confirm their listed order."})
    return issues


@snapshot_request
def refresh_plan(plan: ExecutionPlan, *, render_complete=True) -> ExecutionPlan:
    try:
        if plan.knowledge_snapshot_id and current_snapshot() is None:
            raise ValueError("Published knowledge is unavailable; restore the active release before continuing.")
        revision = source_revision()
    except (ValueError, OSError) as exc:
        plan.status = "failed"
        plan.issues = [{"type": "CONTEXT_INVALID", "message": str(exc)}]
        for task in plan.tasks:
            task.configs = []
            task.questions = []
            task.status = "failed"
        return plan
    if plan.source_revision != revision:
        reload_catalog()
        try:
            validate_catalog()
            validate_context_catalog()
        except (ValueError, KeyError, OSError, TypeError) as exc:
            plan.status = "failed"
            plan.issues = [{"type": "CONTEXT_INVALID", "message": str(exc)}]
            for task in plan.tasks:
                task.configs = []
                task.questions = []
                task.status = "failed"
            return plan
    plan.source_revision = revision
    snapshot = current_snapshot()
    plan.knowledge_snapshot_id = snapshot.release_id if snapshot else ""
    plan.runtime_authority = _runtime_authority(snapshot)
    plan.context_revision = context_revision()
    plan.issues = []
    tasks = []
    for task in plan.tasks:
        tasks.extend(_split_bindings(task))
    plan.tasks = tasks
    if any(task.status != "validated" for task in tasks) or not tasks:
        plan.status = "needs_clarification"
        return plan
    conflicts = _cross_task_issues(tasks)
    for conflict in conflicts:
        key = "order:" + ":".join(conflict["tasks"])
        signature = json.dumps([(task.intent_id, task.parameters, task.revision) for task in tasks if task.intent_id in conflict["tasks"]], sort_keys=True)
        if not all(task.confirmations.get(key) == {"signature": signature, "source_revision": revision} for task in tasks if task.intent_id in conflict["tasks"]):
            plan.issues.append(conflict)
    if plan.issues:
        plan.status = "needs_confirmation"
        return plan
    plan.status = "validated"
    if not render_complete:
        return plan
    staged = []
    try:
        for task in tasks:
            configs = []
            for device in task.target_devices:
                config = render(device, task.operation_id, task.parameters)
                configs.append({"device_id": device["id"], "hostname": device["hostname"], "vendor": device["vendor"],
                                "platform": device["platform"], "version": device["version"],
                                "parameters": deepcopy(task.parameters), "configuration": config})
            staged.append(configs)
        if source_revision() != revision:
            raise ValueError("Source data changed during rendering. Retry after reviewing current context.")
    except Exception as exc:
        plan.status = "failed"
        plan.issues = [{"type": "RENDER_FAILED", "message": str(exc)}]
        return plan
    for task, configs in zip(tasks, staged):
        task.configs, task.status = configs, "rendered"
    plan.status = "ready"
    return plan


@snapshot_request
def confirm_order(plan: ExecutionPlan) -> ExecutionPlan:
    refresh_plan(plan, render_complete=False)
    for conflict in plan.issues:
        if conflict["type"] != "CROSS_TASK_CONFLICT":
            raise ValueError("This issue cannot be resolved by confirming order.")
        key = "order:" + ":".join(conflict["tasks"])
        selected = [task for task in plan.tasks if task.intent_id in conflict["tasks"]]
        signature = json.dumps([(task.intent_id, task.parameters, task.revision) for task in selected], sort_keys=True)
        for task in selected:
            task.confirmations[key] = {"signature": signature, "source_revision": plan.source_revision}
    return refresh_plan(plan)


@snapshot_request
def run(prompt: str, *, verbose=True) -> ExecutionPlan:
    reload_catalog()
    validate_catalog()
    validate_context_catalog()
    intents = plan_intents(prompt)
    plan = ExecutionPlan(prompt, intents=intents)
    for index, intent in enumerate(intents, 1):
        plan.tasks.extend(_process_intent(intent, index, verbose))
    refresh_plan(plan)
    if verbose:
        print(json.dumps(plan_to_dict(plan), indent=2))
    return plan


def plan_to_dict(plan: ExecutionPlan) -> dict:
    return asdict(plan)
