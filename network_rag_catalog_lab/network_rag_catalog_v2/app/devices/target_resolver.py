"""Authoritative constraint matching. Scores rank suggestions, never waive conflicts."""

from copy import deepcopy
import ipaddress

from .inventory import TargetResolutionError, load_inventory
from .target_query import extract_target_queries, load_attributes, parse_description, values_at


TARGET_ISSUES = {"MISSING_TARGET", "TARGET_NOT_FOUND", "AMBIGUOUS_TARGET", "TARGET_CONFLICT", "TARGET_UNRESOLVED", "TARGET_RESOLUTION"}


def _matches(device: dict, constraint: dict, attributes: dict) -> bool:
    field, expected = constraint["field"], constraint["value"]
    spec = attributes.get(field)
    if not spec:
        return False
    values = [value for path in spec["paths"] for value in values_at(device, path)]
    if field == "management_ip":
        try:
            network = ipaddress.ip_network(expected, strict=False)
            return any(ipaddress.ip_address(value) in network for value in values)
        except ValueError:
            return False
    canonical = {alias.casefold(): value.casefold() for value, aliases in spec.get("aliases", {}).items() for alias in aliases}
    normalize = lambda value: canonical.get(value.casefold(), value.casefold())
    return normalize(expected) in {normalize(value) for value in values}


def _label(device: dict) -> str:
    facts = [device.get(field) for field in ("site", "role", "vendor", "platform", "version")]
    return f"{device['hostname']} ({', '.join(str(value) for value in facts if value)})"


def resolve_queries(queries: list[dict], inventory: list[dict] | None = None) -> dict:
    inventory = load_inventory() if inventory is None else inventory
    attributes = load_attributes()
    devices, issues, evidence = [], [], []
    if not queries:
        issues.append({"type": "MISSING_TARGET", "field": "target_refs", "message": "No target device was specified."})
    for index, query in enumerate(queries):
        constraints = query.get("constraints", [])
        candidates = []
        for device in inventory:
            matched, conflicts = [], []
            score = 0
            for constraint in constraints:
                field = constraint["field"]
                if _matches(device, constraint, attributes):
                    matched.append(constraint)
                    score += attributes[field]["weight"]
                else:
                    actual = [v for p in attributes.get(field, {}).get("paths", []) for v in values_at(device, p)]
                    conflicts.append({**constraint, "actual": actual})
            candidates.append({"hostname": device["hostname"], "device_id": device.get("id", device["hostname"]),
                               "label": _label(device), "score": score, "matched": matched, "conflicts": conflicts})
        candidates.sort(key=lambda candidate: (-candidate["score"], candidate["hostname"]))
        complete = [candidate for candidate in candidates if not candidate["conflicts"] and constraints]
        if query.get("unresolved"):
            code = "TARGET_UNRESOLVED"
            reason = "Please clarify these device characteristics: " + ", ".join(query["unresolved"]) + "."
        elif not constraints:
            code, reason = "MISSING_TARGET", "Please describe a device by name, site, role, vendor, or another inventory attribute."
        elif not complete:
            individually_known = all(any(_matches(device, item, attributes) for device in inventory) for item in constraints)
            code = "TARGET_CONFLICT" if individually_known else "TARGET_NOT_FOUND"
            description = ", ".join(f"{item['field']}={item['value']}" for item in constraints)
            reason = f"No device matches all requested characteristics: {description}."
        elif len(complete) > 1 and query.get("cardinality") != "many":
            code, reason = "AMBIGUOUS_TARGET", "Several devices match this description. Which one should receive this operation?"
        else:
            selected = {candidate["hostname"] for candidate in complete}
            devices.extend(device for device in inventory if device["hostname"] in selected)
            evidence.append({"query_index": index, "description": query["text"], "selected": complete,
                             "explanation": "Selected devices satisfy every stated inventory constraint."})
            continue

        choices = complete if code == "AMBIGUOUS_TARGET" else candidates[:3]
        if choices and code in {"TARGET_NOT_FOUND", "TARGET_CONFLICT"}:
            closest = choices[0]
            differences = "; ".join(f"{item['field']} is {', '.join(item['actual']) or 'not recorded'} (requested {item['value']})" for item in closest["conflicts"])
            reason += f" Closest candidate: {closest['label']}. {differences}."
        issues.append({"type": code, "field": "target_refs", "message": reason, "query_index": index,
                       "suggestions": [candidate["hostname"] for candidate in choices], "candidates": choices})
    unique = {device["hostname"]: device for device in devices}
    return {"devices": list(unique.values()) if not issues else [], "issues": issues, "evidence": evidence}


def resolve_intent_targets(target_refs: list[str], inventory: list[dict] | None = None) -> list[dict]:
    inventory = load_inventory() if inventory is None else inventory
    queries = [parse_description(ref, inventory) for ref in target_refs]
    result = resolve_queries(queries, inventory)
    if result["issues"]:
        issue = result["issues"][0]
        raise TargetResolutionError(issue["type"], ", ".join(target_refs), issue["message"], issue.get("suggestions"))
    return result["devices"]


def refine_queries(queries: list[dict], issue: dict, reply: str, *, allow_llm: bool = False) -> list[dict]:
    """A descriptive answer refines the active selector; explicit names replace it."""
    inventory = load_inventory()
    replacements = extract_target_queries(reply, inventory, reply=True, allow_llm=allow_llm)
    if not replacements:
        return deepcopy(queries)
    index = issue.get("query_index", 0)
    updated = deepcopy(queries)
    if index >= len(updated):
        return updated + replacements
    incoming = replacements[0]
    explicit_name = any(item["field"] == "name" for query in replacements for item in query["constraints"])
    if len(replacements) == 1 and not explicit_name:
        old = updated[index]
        changed = {item["field"] for item in incoming["constraints"]}
        incoming["constraints"] = [item for item in old["constraints"] if item["field"] not in changed] + incoming["constraints"]
        incoming["cardinality"] = old["cardinality"]
        # Unrecognized qualifiers cannot disappear through an unrelated answer.
        incoming["unresolved"] = list(dict.fromkeys(old.get("unresolved", []) + incoming["unresolved"]))
        incoming["text"] = old["text"] + "; clarification: " + reply
    updated[index:index + 1] = replacements
    return updated
