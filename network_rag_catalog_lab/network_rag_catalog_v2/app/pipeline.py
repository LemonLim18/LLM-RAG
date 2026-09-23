"""Planning pipeline with deterministic validation before rendering."""

from dataclasses import asdict
import ipaddress
import json
import re

from .catalog import get_parameter, validate_catalog
from .devices.context_validator import (
    find_explicit_interface_names,
    normalize_parameters_for_device,
    validate_device_context,
)
from .devices.inventory import load_inventory
from .devices.target_query import extract_target_queries, parameter_request, parse_description
from .devices.target_resolver import TARGET_ISSUES, refine_queries, resolve_queries
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
    if issue_type in TARGET_ISSUES:
        suggestions = issue.get("suggestions", [])
        if suggestions:
            labels = {candidate["hostname"]: candidate["label"] for candidate in issue.get("candidates", [])}
            numbered = "; ".join(f"{index + 1}. {labels.get(name, name)}" for index, name in enumerate(suggestions))
            return f"{issue['message']} Choose a device or refine the description: {numbered}."
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


def next_clarification(task: PlannedTask) -> dict | None:
    """Return the single issue the user should answer next.

    Target grounding comes first because device-specific schemas and interface
    validation are meaningless until the target is authoritative.
    """
    if not task.issues:
        return None
    return next((issue for issue in task.issues if issue["type"] in TARGET_ISSUES), task.issues[0])


def next_clarification_prompt(task: PlannedTask) -> tuple[str, str]:
    issue = next_clarification(task)
    if not issue:
        return "", ""
    return _top_level_field(issue["field"]), _clarification_question(issue)


def _finalize_task(
    *,
    intent_id: str,
    request_text: str,
    category: str,
    operation_id: str,
    parameters: dict,
    parameter_provenance: dict[str, str],
    target_refs: list[str],
    target_queries: list[dict] | None = None,
    clarification_history: list[dict] | None = None,
    verbose: bool = False,
) -> PlannedTask:
    if target_queries is None:
        inventory = load_inventory()
        target_queries = [parse_description(ref, inventory) for ref in target_refs]
    resolution = resolve_queries(target_queries)
    devices, issues = resolution["devices"], resolution["issues"]
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
            target_queries=target_queries,
            target_resolution=resolution["evidence"],
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
        target_queries=target_queries,
        target_resolution=resolution["evidence"],
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

    target_queries = extract_target_queries(intent.request_text, load_inventory(), allow_llm=True)
    resolved = resolve_queries(target_queries)
    schema = load_schema(operation_id, devices=resolved["devices"])
    _log(verbose, f"\n[4] PARAMETER EXTRACTION ({schema.get('title', operation_id)})")
    extraction = extract_parameter_result(parameter_request(intent.request_text, target_queries), schema)
    _log(verbose, json.dumps(extraction.parameters, indent=2))

    target_refs = [query["text"] for query in target_queries]
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
        target_queries=target_queries,
        verbose=verbose,
    )


def _strict_reply_value(reply: str, field: str) -> dict:
    """Parse scalar clarification answers only for the field currently asked."""
    value = reply.strip()
    if field == "prefix_length":
        from .parameters.normalizer import prefix_length_from_text
        prefix = prefix_length_from_text(value, allow_bare_netmask=True)
        return {field: prefix} if prefix is not None else {}
    if field in {"address", "neighbor_ip", "next_hop", "router_id"}:
        # A next hop/address must be a host address, never a CIDR or netmask.
        if "/" in value:
            return {}
        try:
            address = ipaddress.IPv4Address(value)
        except ipaddress.AddressValueError:
            return {}
        if str(address) in {"0.0.0.0", "255.255.255.255"} or value in {
            "255.0.0.0", "255.255.0.0", "255.255.255.0", "255.255.255.128",
            "255.255.255.192", "255.255.255.224", "255.255.255.240", "255.255.255.248",
            "255.255.255.252", "255.255.255.254",
        }:
            return {}
        return {field: str(address)}
    if field == "destination":
        try:
            network = ipaddress.IPv4Network(value, strict=False)
        except ValueError:
            return {}
        return {field: str(network)} if "/" in value else {}
    return {}


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
    current_issue = next_clarification(task)
    current_field = _top_level_field(current_issue["field"]) if current_issue else ""
    reply, _ = _resolve_numbered_selection(reply, task)
    target_queries = task.target_queries or [parse_description(ref, load_inventory()) for ref in task.target_refs]
    if current_issue and current_issue["type"] in TARGET_ISSUES:
        queries = refine_queries(target_queries, current_issue, reply, allow_llm=True)
        return _finalize_task(
            intent_id=task.intent_id, request_text=task.request_text, category=task.category,
            operation_id=task.operation_id, parameters=dict(task.parameters),
            parameter_provenance=dict(task.parameter_provenance),
            target_refs=[query["text"] for query in queries], target_queries=queries,
            clarification_history=[*task.clarification_history, {
                "reply": reply, "field": "target_refs", "updated_fields": ["target_refs"],
            }], verbose=verbose,
        )
    extraction = extract_parameter_result(reply, schema, existing_parameters=task.parameters, requested_fields=[current_field])
    parameters = merge_parameters(task.parameters, extraction.parameters, schema)
    target_refs = list(task.target_refs)

    devices = resolve_queries(target_queries)["devices"]
    contextual = _contextual_clarification_values(reply, task, devices, [current_field])
    strict_value = _strict_reply_value(reply, current_field)
    # Inventory-normalized interface selections and strict scalar values are the
    # only reply values allowed to cross the clarification boundary.
    parameters = merge_parameters(parameters, {**contextual, **strict_value}, schema)

    provenance = dict(task.parameter_provenance)
    provenance.update({field: f"clarification_{source}" for field, source in extraction.provenance.items()})
    provenance.update({field: "clarification_inventory_alias" for field in contextual})
    provenance.update({field: "clarification_user" for field in strict_value})
    history = [*task.clarification_history, {
        "reply": reply,
        "field": current_field,
        "updated_fields": sorted(set(extraction.provided_fields) | set(contextual) | set(strict_value)),
    }]
    return _finalize_task(
        intent_id=task.intent_id,
        request_text=task.request_text,
        category=task.category,
        operation_id=task.operation_id,
        parameters=parameters,
        parameter_provenance=provenance,
        target_refs=target_refs,
        target_queries=target_queries,
        clarification_history=history,
        verbose=verbose,
    )


def _resolve_numbered_selection(reply: str, task: PlannedTask) -> tuple[str, str | None]:
    """Turn a terminal answer such as ``2`` into an offered inventory value."""
    if not reply.strip().isdigit():
        return reply, None
    index = int(reply.strip()) - 1
    current_issue = next_clarification(task)
    if not current_issue or not current_issue.get("suggestions"):
        return reply, None
    suggestions = current_issue["suggestions"]
    if not 0 <= index < len(suggestions):
        return reply, None
    selected = suggestions[index]
    if current_issue["type"] in TARGET_ISSUES:
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
