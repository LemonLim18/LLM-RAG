from dataclasses import dataclass, field
import json
import re
from typing import Any

from ..catalog import parameter_label
from ..llm import llm
from .normalizer import (
    canonicalize_parameter_keys,
    deterministic_values,
    normalize_value,
    prefix_length_from_text,
)


@dataclass
class ExtractionResult:
    parameters: dict[str, Any]
    provided_fields: list[str] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)
    provenance: dict[str, str] = field(default_factory=dict)


def _parse_json(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.S)
        if match:
            return json.loads(match.group(0))
    raise ValueError(f"Cannot parse parameter JSON: {raw}")


def _text_has_value(prompt: str, value: Any, field: str) -> bool:
    if value is None:
        return True
    if field == "prefix_length":
        return prefix_length_from_text(prompt) == value

    prompt_lower = prompt.lower()
    if isinstance(value, bool):
        terms = {
            True: ("true", "yes", "enable", "enabled", "up", "no shutdown"),
            False: ("false", "no", "disable", "disabled", "down", "shutdown"),
        }
        return any(term in prompt_lower for term in terms[value])
    if isinstance(value, (int, float)):
        return bool(re.search(rf"(?<![a-z0-9]){re.escape(str(value))}(?![a-z0-9])", prompt_lower))

    normalized_value = re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()
    normalized_prompt = re.sub(r"[^a-z0-9]+", " ", prompt_lower)
    return bool(
        normalized_value
        and re.search(rf"(?<![a-z0-9]){re.escape(normalized_value)}(?![a-z0-9])", normalized_prompt)
    )


def _filter_value(prompt: str, value: Any, schema: dict, field: str) -> tuple[Any, str | None]:
    schema_type = schema.get("type")
    if value is None:
        return None, None
    if schema_type == "object":
        if not isinstance(value, dict):
            return None, None
        nested, _ = _filter_to_schema(prompt, value, schema)
        return nested, "user"
    if schema_type == "array":
        if not isinstance(value, list):
            return None, None
        filtered_items = []
        item_schema = schema.get("items", {})
        for item in value:
            filtered, _ = _filter_value(prompt, item, item_schema, field)
            if not isinstance(filtered, dict):
                continue
            required = item_schema.get("required", [])
            if any(filtered.get(required_field) is None for required_field in required):
                continue
            filtered_items.append(filtered)
        return (filtered_items or None), ("user" if filtered_items else None)

    normalized, source = normalize_value(field, value, schema, prompt)
    if normalized is None or not _text_has_value(prompt, normalized, field):
        return None, None
    return normalized, source


def _filter_to_schema(prompt: str, raw_params: dict, schema: dict) -> tuple[dict, dict[str, str]]:
    properties = schema.get("properties", {})
    canonical = canonicalize_parameter_keys(raw_params, schema)
    params: dict[str, Any] = {}
    provenance: dict[str, str] = {}
    fallback = deterministic_values(prompt, schema)
    for field, field_schema in properties.items():
        candidate = canonical.get(field)
        value, source = _filter_value(prompt, candidate, field_schema, field)
        if value is None and field in fallback:
            value, source = fallback[field]
        if value is not None:
            params[field] = value
            provenance[field] = source or "user"
        elif field in schema.get("required", []):
            params[field] = None
    return params, provenance


def _contract(schema: dict) -> dict:
    properties = {}
    for field, field_schema in schema.get("properties", {}).items():
        properties[field] = {
            "display_name": parameter_label(field),
            "type": field_schema.get("type"),
            "enum": field_schema.get("enum"),
            "items": field_schema.get("items"),
        }
    return {"required": schema.get("required", []), "properties": properties}


def extract_parameter_result(
    prompt: str,
    schema: dict,
    *,
    existing_parameters: dict | None = None,
    requested_fields: list[str] | None = None,
) -> ExtractionResult:
    contract = _contract(schema)
    existing = existing_parameters or {}
    requested = requested_fields or schema.get("required", [])
    system = f"""You are a strict network-operation parameter parser.
Extract only values explicitly stated in the current user message.
Never invent, assume, infer, guess, or use a value from an example.
Return null for a required value absent from the current user message.
Return JSON only: {{\"parameters\": {{}}}}.

Parameter contract:
{json.dumps(contract, indent=2)}

Existing validated values (context only; do not repeat unless the user repeats them):
{json.dumps(existing, indent=2)}
Fields currently requested: {json.dumps(requested)}
"""
    raw_params: dict = {}
    deterministic = deterministic_values(prompt, schema)
    fields_to_extract = requested or schema.get("required", [])
    if not all(field in deterministic for field in fields_to_extract):
        try:
            raw = llm.invoke([("system", system), ("human", prompt)]).content.strip()
            data = _parse_json(raw)
            candidate = data.get("parameters", data)
            if isinstance(candidate, dict):
                raw_params = candidate
        except Exception as exc:
            print(f"[parameters] LLM extraction unavailable; using explicit-value fallback: {exc}")

    params, provenance = _filter_to_schema(prompt, raw_params, schema)
    required = schema.get("required", [])
    return ExtractionResult(
        parameters=params,
        provided_fields=sorted(provenance),
        missing_fields=[field for field in required if params.get(field) is None],
        provenance=provenance,
    )


def extract_parameters(prompt: str, schema: dict) -> dict:
    """Backward-compatible convenience wrapper for existing callers."""
    return extract_parameter_result(prompt, schema).parameters


def merge_parameters(existing: dict, updates: dict, schema: dict) -> dict:
    """Merge non-null clarification values without overwriting validated context."""
    merged = dict(existing)
    for field in schema.get("properties", {}):
        if field in updates and updates[field] is not None:
            merged[field] = updates[field]
    return merged
