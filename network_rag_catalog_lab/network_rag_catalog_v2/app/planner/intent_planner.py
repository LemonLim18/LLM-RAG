"""Evidence-preserving planning with bounded repair and explicit target scope."""

import json
import re

from ..catalog import load_operations, load_parameters, operation_terms
from ..devices.inventory import load_inventory
from ..devices.target_query import extract_target_queries, parse_description
from ..llm import llm
from ..parameters.schema_loader import load_schema
from .models import OperationIntent


def _operation_hits(prompt):
    hits = []
    for term, operation in operation_terms():
        for match in re.finditer(rf"(?<![\w]){re.escape(term)}(?![\w])", prompt, re.I):
            hits.append((match.start(), match.end(), operation))
    selected = []
    for hit in sorted(hits, key=lambda value: (value[0], -(value[1] - value[0]))):
        if not selected or hit[0] >= selected[-1][1]:
            selected.append(hit)
    return selected


def _fallback_plan(prompt: str) -> list[OperationIntent]:
    inventory = load_inventory()
    intents = []
    # Share trailing targets only within an explicit coordinated group.
    for group_match in re.finditer(r"[^;\n]+", prompt):
        group = group_match.group()
        hits = _operation_hits(group)
        starts = [0] + [hit[0] for hit in hits[1:]]
        if len(hits) <= 1:
            starts += [match.end() for match in re.finditer(r"\b(?:and|then)\s+(?=(?:configure|create|delete|remove|add|enable|disable|assign|set)\b)", group, re.I)]
        # Keep unknown coordinated actions as unresolved intents instead of
        # swallowing them into a known operation's device description.
        identities = [name for device in inventory for name in [device["hostname"], device.get("display_name", ""), *device.get("aliases", [])] if name]
        for conjunction in re.finditer(r"\b(?:and|then)\s+", group, re.I):
            prior = [hit for hit in hits if hit[0] < conjunction.start()]
            fields = load_schema(prior[-1][2])["properties"] if prior else {}
            aliases = [alias for parameter in load_parameters() if parameter["parameter_id"] in fields for alias in parameter.get("aliases", [])]
            tail = re.split(r"\band\b|\bthen\b", group[conjunction.end():], maxsplit=1, flags=re.I)[0].strip()
            parameter_clause = any(re.match(rf"{re.escape(alias)}(?!\w)", tail, re.I) for alias in aliases)
            interface_clause = bool(re.match(r"(?:GigabitEthernet|Ethernet|Eth|GE|ge-|Loopback|Lo)\d", tail, re.I))
            identity_clause = any(re.match(rf"{re.escape(name)}(?!\w)", tail, re.I) for name in identities) or bool(re.match(r"(?:router|switch|firewall)\s+\d+|(?:r|sw|fw)\d+\b", tail, re.I))
            description = parse_description(tail, inventory)
            if tail and not parameter_clause and not interface_clause and not identity_clause and description["unresolved"]:
                starts.append(conjunction.end())
        starts = sorted(set(starts))
        batch = []
        for index, start in enumerate(starts):
            end = starts[index + 1] if index + 1 < len(starts) else len(group)
            text = re.sub(r"(?:[, ]*\b(?:and|then)\b\s*)$", "", group[start:end].strip(), flags=re.I).strip(" ,")
            if not text:
                continue
            position = group_match.start() + group.find(text, start)
            intent = OperationIntent(f"intent-{len(intents) + len(batch) + 1}", text)
            intent.source_spans = [{"kind": "operation", "start": position, "end": position + len(text), "text": text}]
            if extract_target_queries(text, inventory):
                intent.target_text = text
            batch.append(intent)
        waiting = []
        for intent in batch:
            if not intent.target_text:
                waiting.append(intent)
                continue
            queries = extract_target_queries(intent.target_text, inventory)
            shared = " and ".join(query["text"] for query in queries)
            offset = prompt.find(shared, group_match.start())
            for pending in waiting:
                if offset >= 0:
                    pending.target_text = "on " + shared
                    pending.source_spans.append({"kind": "shared_targets", "start": offset, "end": offset + len(shared), "text": shared})
            waiting = []
        intents.extend(batch)
    return intents or [OperationIntent("intent-1", prompt.strip())]


def _ambiguous_scope(prompt: str) -> bool:
    return bool(re.search(r"\b(?:it|them|those|former|latter|respectively|except|excluding|instead|not|don't)\b", prompt, re.I))


def _validated_model_plan(data, prompt: str) -> list[OperationIntent]:
    if not isinstance(data, dict) or not isinstance(data.get("intents"), list) or not data["intents"]:
        raise ValueError("Return an object with a nonempty intents list.")
    intents, covered = [], []
    for index, item in enumerate(data["intents"], 1):
        if not isinstance(item, dict) or not isinstance(item.get("request_text"), str):
            raise ValueError("Each intent needs an exact request_text quote.")
        text = item["request_text"]
        start = prompt.find(text, covered[-1][1] if covered else 0)
        if not text or start < 0:
            raise ValueError("Operation quotes must be verbatim and ordered.")
        end = start + len(text)
        if len(_operation_hits(text)) > 1:
            raise ValueError("Separate each explicit operation.")
        target = item.get("target_text", "")
        if not isinstance(target, str) or (target and target not in prompt):
            raise ValueError("Target text must be an exact original quote.")
        intent = OperationIntent(f"intent-{index}", text, target_text="on " + target if target else "")
        intent.source_spans = [{"kind": "operation", "start": start, "end": end, "text": text}]
        if target:
            offset = prompt.find(target)
            intent.source_spans.append({"kind": "proposed_targets", "start": offset, "end": offset + len(target), "text": target})
            if target not in text:
                intent.issues.append({"type": "TARGET_UNRESOLVED", "field": "target_refs",
                                      "message": f"Confirm the proposed shared targets '{target}' for: {text}"})
        intents.append(intent)
        covered.append((start, end))
    remaining = prompt
    for start, end in reversed(covered):
        remaining = remaining[:start] + " " * (end - start) + remaining[end:]
    if re.sub(r"\b(?:and|then)\b|[\s,;.]", "", remaining, flags=re.I):
        raise ValueError("Preserve the complete request, including all qualifiers.")
    return intents


def plan_intents(prompt: str) -> list[OperationIntent]:
    fallback = _fallback_plan(prompt)
    complex_scope = _ambiguous_scope(prompt)
    if not complex_scope and all(len(_operation_hits(intent.request_text)) == 1 for intent in fallback):
        return fallback
    catalog = [{"id": op["operation_id"], "name": op["display_name"], "description": op["description"]} for op in load_operations()]
    system = ('Split every operation using ordered, non-overlapping verbatim request_text quotes covering the whole request. '
              'Keep qualifications and negations. target_text is an exact quote of the target description explicitly associated '
              'with this operation; absent/uncertain targets use an empty string. Never invent devices or values. '
              'Return JSON {"intents":[{"request_text":"...","target_text":"..."}]}. Catalog: ' + json.dumps(catalog))
    intents = fallback
    for attempt in range(2):
        try:
            raw = llm.invoke([("system", system), ("human", prompt)]).content
            intents = _validated_model_plan(json.loads(raw), prompt)
            break
        except (ValueError, TypeError, AttributeError) as exc:
            system += "\nRepair only this issue, preserving original evidence: " + str(exc)
        except Exception:
            break
    if complex_scope:
        for intent in intents:
            intent.issues.append({"type": "TARGET_UNRESOLVED", "field": "target_refs",
                                  "message": "Confirm exactly which devices should receive this indirectly scoped operation: " + intent.request_text})
            if re.search(r"\b(?:not|don't|instead)\b", intent.request_text, re.I):
                intent.issues.insert(0, {"type": "OPERATION_PROPOSAL", "field": "operation_id",
                                         "message": "This clause contains a negation or correction. Explicitly select the operation you actually want, or leave it unresolved: " + intent.request_text})
    return intents
