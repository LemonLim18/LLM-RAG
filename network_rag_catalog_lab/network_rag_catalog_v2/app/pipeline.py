"""Planning pipeline with deterministic validation before rendering."""

from dataclasses import asdict
import json
import re

from .catalog import get_parameter, validate_catalog
from .devices.context_validator import (
    find_explicit_interface_names,
    normalize_parameters_for_device,
    validate_device_context,
)
from .devices.inventory import (
    TargetResolutionError,
    find_explicit_group_references,
    find_explicit_target_references,
    find_user_target_candidates,
)
from .devices.target_resolver import resolve_intent_targets
from .parameters.parameter_extractor import (
    extract_parameter_result,
    merge_parameters,
)
from .parameters.schema_loader import load_schema
from .parameters.validator import ValidationIssue, validate_parameter_result
from .planner.intent_planner import plan_intents
from .planner.models import ExecutionPlan, PlannedTask
from .retrieval.category_classifier import classify_category
from .retrieval.operation_retriever import retrieve_operation_candidates
from .retrieval.operation_selector import select_operation
from .templates.renderer import render


def _log(verbose: bool, message: str = "") -> None:
    if verbose:
        print(message)


def _issue_to_dict(issue: ValidationIssue) -> dict:
    return {"type": issue.type, "field": issue.field, "message": issue.message}


def _top_level_field(field: str) -> str:
    return re.split(r"[.\[]", field, maxsplit=1)[0]


def _clarification_question(issue: dict) -> str:
    issue_type = issue["type"]
    field = _top_level_field(issue["field"])
    if issue_type == "MISSING_TARGET":
        return "Which target device or inventory group should this operation use?"
    if issue_type in {"TARGET_NOT_FOUND", "AMBIGUOUS_TARGET", "TARGET_RESOLUTION"}:
        suggestions = issue.get("suggestions", [])
        if suggestions:
            numbered = "; ".join(f"{index + 1}. {name}" for index, name in enumerate(suggestions))
            return f"{issue['message']} Choose one target: {numbered}."
        return issue["message"]
    if issue_type == "MISSING":
        try:
            return get_parameter(field).get("clarification") or f"What value should I use for {field}?"
        except KeyError:
            return f"What value should I use for {field}?"
    if issue_type == "INVALID_INTERFACE":
        suggestions = issue.get("suggestions", [])
        if suggestions:
            numbered = "; ".join(f"{index + 1}. {name}" for index, name in enumerate(suggestions))
            return f"{issue['message']} Did you mean: {numbered}?"
        return issue["message"]
    return f"Please correct {field}: {issue['message']}"


def _resolve_task_devices(target_refs: list[str]) -> tuple[list[dict], list[dict]]:
    if not target_refs:
        return [], [{
            "type": "MISSING_TARGET",
            "field": "target_refs",
            "message": "No target device was specified.",
        }]
    try:
        return resolve_intent_targets(target_refs), []
    except TargetResolutionError as exc:
        return [], [{
            "type": exc.code,
            "field": "target_refs",
            "message": str(exc),
            "suggestions": exc.suggestions,
        }]
    except Exception as exc:
        return [], [{
            "type": "TARGET_RESOLUTION",
            "field": "target_refs",
            "message": str(exc),
        }]


def _phrase_in_text(phrase: str, text: str) -> bool:
    normalized_phrase = re.sub(r"[^a-z0-9]+", " ", phrase.lower()).strip()
    normalized_text = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
    return bool(
        normalized_phrase
        and re.search(rf"(?<![a-z0-9]){re.escape(normalized_phrase)}(?![a-z0-9])", normalized_text)
    )


def _ground_target_refs(request_text: str, planner_refs: list[str]) -> list[str]:
    """Keep only target references present in the user request.

    Canonical hostnames are recovered from exact inventory aliases; textual group
    references such as ``core routers`` are retained only when the user wrote
    that exact group phrase. This prevents a weak planner from inventing a
    target that later passes inventory resolution by coincidence.
    """
    exact = find_explicit_target_references(request_text)
    groups = [
        *find_explicit_group_references(request_text),
        *(reference for reference in planner_refs if _phrase_in_text(reference, request_text)),
    ]
    candidates = find_user_target_candidates(request_text)
    return list(dict.fromkeys([*exact, *groups, *candidates]))


def _finalize_task(
    *,
    intent_id: str,
    request_text: str,
    category: str,
    operation_id: str,
    parameters: dict,
    parameter_provenance: dict[str, str],
    target_refs: list[str],
    clarification_history: list[dict] | None = None,
    verbose: bool = False,
) -> PlannedTask:
    devices, issues = _resolve_task_devices(target_refs)
    schema = load_schema(operation_id, devices=devices)
    validation = validate_parameter_result(parameters, schema)
    issues.extend(_issue_to_dict(issue) for issue in validation.issues)
    if not issues and devices:
        issues.extend(validate_device_context(operation_id, category, parameters, devices))

    questions = list(dict.fromkeys(_clarification_question(issue) for issue in issues))
    if issues:
        _log(verbose, "    NEEDS CLARIFICATION")
        for issue in issues:
            _log(verbose, f"    - {issue['field']}: {issue['message']}")
        return PlannedTask(
            intent_id=intent_id,
            request_text=request_text,
            category=category,
            operation_id=operation_id,
            parameters=parameters,
            target_refs=target_refs,
            status="needs_clarification",
            parameter_provenance=parameter_provenance,
            issues=issues,
            clarification_questions=questions,
            clarification_history=clarification_history or [],
            target_devices=devices,
            configs=[],
        )

    configs = []
    for device in devices:
        device_params = normalize_parameters_for_device(parameters, device)
        config = render(device, operation_id, device_params)
        configs.append({
            "device_id": device["hostname"],
            "vendor": device["vendor"],
            "platform": device["platform"],
            "version": device["version"],
            "parameters": device_params,
            "configuration": config,
        })
        _log(verbose, f"\n--- {device['hostname']} ({device['vendor']}) ---\n{config}")

    _log(verbose, "    PASSED")
    return PlannedTask(
        intent_id=intent_id,
        request_text=request_text,
        category=category,
        operation_id=operation_id,
        parameters=parameters,
        target_refs=target_refs,
        status="ready",
        parameter_provenance=parameter_provenance,
        clarification_history=clarification_history or [],
        target_devices=devices,
        configs=configs,
    )


def _process_intent(intent, index: int, verbose: bool) -> PlannedTask:
    _log(verbose, f"\n{'=' * 72}\nINTENT {index}: {intent.request_text}\n{'=' * 72}")
    _log(verbose, "\n[1] CATEGORY CLASSIFICATION")
    category = classify_category(intent.request_text)
    _log(verbose, f"    {category}")

    _log(verbose, "\n[2] OPERATION RETRIEVAL")
    candidates = retrieve_operation_candidates(intent.request_text, category, 3)
    for candidate in candidates:
        _log(verbose, f"    {candidate['operation_id']} | distance={candidate['distance']:.4f}")
    if not candidates:
        raise ValueError(f"No operation candidates for intent {intent.intent_id}")

    _log(verbose, "\n[3] OPERATION SELECTION")
    operation_id = select_operation(intent.request_text, category, candidates)
    _log(verbose, f"    {operation_id}")

    schema = load_schema(operation_id)
    _log(verbose, f"\n[4] PARAMETER EXTRACTION ({schema.get('title', operation_id)})")
    extraction = extract_parameter_result(intent.request_text, schema)
    _log(verbose, json.dumps(extraction.parameters, indent=2))

    target_refs = _ground_target_refs(intent.request_text, intent.target_refs)
    _log(verbose, f"\n[5] TARGET REFERENCES: {target_refs or '[none]'}")
    _log(verbose, "\n[6] VALIDATION + CONTEXT CHECK")
    return _finalize_task(
        intent_id=intent.intent_id,
        request_text=intent.request_text,
        category=category,
        operation_id=operation_id,
        parameters=extraction.parameters,
        parameter_provenance=extraction.provenance,
        target_refs=target_refs,
        verbose=verbose,
    )


def _requested_fields(task: PlannedTask) -> list[str]:
    return list(dict.fromkeys(
        _top_level_field(issue["field"])
        for issue in task.issues
        if issue["type"] in {"MISSING", "SCHEMA", "INVALID_INTERFACE"}
    ))


def _contextual_clarification_values(
    reply: str,
    task: PlannedTask,
    devices: list[dict],
    requested_fields: list[str],
) -> dict:
    """Resolve only interface aliases explicitly present in a clarification reply."""
    values: dict = {}
    names = []
    for device in devices:
        names.extend(find_explicit_interface_names(device, reply))
    names = list(dict.fromkeys(names))
    if "interface" in requested_fields and len(names) == 1:
        values["interface"] = names[0]
    if "interfaces" in requested_fields and names:
        area = re.search(r"\barea\s+([0-9.]+)\b", reply, re.I)
        if area:
            values["interfaces"] = [{"name": name, "area": area.group(1)} for name in names]
    return values


def resume_task(task: PlannedTask, reply: str, *, verbose: bool = False) -> PlannedTask:
    """Apply one clarification response to one task without replanning the request."""
    if task.status != "needs_clarification":
        return task

    schema = load_schema(task.operation_id)
    requested_fields = _requested_fields(task)
    reply, selected_target = _resolve_numbered_selection(reply, task)
    extraction = extract_parameter_result(
        reply,
        schema,
        existing_parameters=task.parameters,
        requested_fields=requested_fields,
    )
    parameters = merge_parameters(task.parameters, extraction.parameters, schema)
    target_refs = list(task.target_refs)

    target_issue_types = {"MISSING_TARGET", "TARGET_NOT_FOUND", "AMBIGUOUS_TARGET", "TARGET_RESOLUTION"}
    if any(issue["type"] in target_issue_types for issue in task.issues):
        reply_targets = [selected_target] if selected_target else find_explicit_target_references(reply)
        if reply_targets:
            target_refs = reply_targets

    devices, _ = _resolve_task_devices(target_refs)
    contextual = _contextual_clarification_values(reply, task, devices, requested_fields)
    parameters = merge_parameters(parameters, contextual, schema)

    provenance = dict(task.parameter_provenance)
    provenance.update({field: f"clarification_{source}" for field, source in extraction.provenance.items()})
    provenance.update({field: "clarification_inventory_alias" for field in contextual})
    history = [*task.clarification_history, {
        "reply": reply,
        "updated_fields": sorted(set(extraction.provided_fields) | set(contextual)),
    }]
    return _finalize_task(
        intent_id=task.intent_id,
        request_text=task.request_text,
        category=task.category,
        operation_id=task.operation_id,
        parameters=parameters,
        parameter_provenance=provenance,
        target_refs=target_refs,
        clarification_history=history,
        verbose=verbose,
    )


def _resolve_numbered_selection(reply: str, task: PlannedTask) -> tuple[str, str | None]:
    """Turn a terminal answer such as ``2`` into an offered inventory value."""
    if not reply.strip().isdigit():
        return reply, None
    index = int(reply.strip()) - 1
    suggestion_issues = [issue for issue in task.issues if issue.get("suggestions")]
    if len(suggestion_issues) != 1:
        return reply, None
    suggestions = suggestion_issues[0]["suggestions"]
    if not 0 <= index < len(suggestions):
        return reply, None
    selected = suggestions[index]
    if suggestion_issues[0]["type"] in {"TARGET_NOT_FOUND", "AMBIGUOUS_TARGET"}:
        return selected, selected
    return selected, None


def run(prompt: str, *, verbose: bool = True) -> ExecutionPlan:
    """Create a multi-operation plan. This function never changes a device."""
    validate_catalog()
    _log(verbose, "\n" + "#" * 72)
    _log(verbose, "REQUEST")
    _log(verbose, prompt)
    _log(verbose, "#" * 72)

    intents = plan_intents(prompt)
    if not intents:
        raise ValueError("The planner produced no operation intents.")
    plan = ExecutionPlan(original_prompt=prompt, intents=intents)
    for index, intent in enumerate(intents, 1):
        plan.tasks.append(_process_intent(intent, index, verbose))

    _log(verbose, "\n" + "#" * 72)
    _log(verbose, "EXECUTION PLAN READY - NO DEVICE CHANGES HAVE BEEN MADE")
    _log(verbose, "#" * 72)
    _log(verbose, json.dumps(plan_to_dict(plan), indent=2))
    return plan


def plan_to_dict(plan: ExecutionPlan) -> dict:
    return asdict(plan)
