from dataclasses import dataclass, field
import json
import re
from typing import Any

from ..catalog import parameter_label
from ..llm import llm
from .evidence import grounded_scalar, literal_candidates, mask_literals, mentioned_fields
from .normalizer import (
    canonicalize_parameter_keys,
    deterministic_values,
    normalize_value,
    prefix_length_from_text,
    explicit_alternatives,
    parameter_identity,
    parameter_metadata,
)


@dataclass
class ExtractionResult:
    parameters: dict[str, Any]
    provided_fields: list[str] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)
    provenance: dict[str, str] = field(default_factory=dict)
    candidates: list[dict] = field(default_factory=list)
    diagnostics: list[str] = field(default_factory=list)


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
    if schema_type in {"object", "array"}:
        # Never assemble a collection from unrelated prompt-wide scalar matches.
        explicit = literal_candidates(prompt, field, schema)
        if len(explicit) == 1 and json.dumps(value, sort_keys=True) == json.dumps(explicit[0], sort_keys=True):
            return explicit[0], "user"
        return None, None

    normalized, source = normalize_value(field, value, schema, prompt)
    if normalized is None or not _text_has_value(prompt, normalized, parameter_identity(field, schema)):
        return None, None
    return normalized, source


def _explicit_values(prompt: str, schema: dict) -> dict:
    values = deterministic_values(mask_literals(prompt), schema)
    strict_preference = "expansion_network_v1" in schema.get("x-validation-handlers", [])
    if strict_preference:
        values.pop("preference", None)
    for field, node in schema.get("properties", {}).items():
        evidence = re.sub(r"\bmetric\s+\d+\b", "", prompt, flags=re.I) if strict_preference and field == "preference" else prompt
        literals = literal_candidates(evidence, field, node)
        if len(literals) == 1:
            values[field] = (literals[0], "deterministic_user")
        elif len(literals) > 1:
            values.pop(field, None)
    return values


def _filter_to_schema(
    prompt: str,
    raw_params: dict,
    schema: dict,
    allowed_fields: set[str] | None = None,
) -> tuple[dict, dict[str, str]]:
    properties = schema.get("properties", {})
    canonical = canonicalize_parameter_keys(raw_params, schema)
    params: dict[str, Any] = {}
    provenance: dict[str, str] = {}
    fallback = _explicit_values(prompt, schema)
    for field, field_schema in properties.items():
        if allowed_fields is not None and field not in allowed_fields:
            continue
        candidate = canonical.get(field)
        value, source = _filter_value(prompt, candidate, field_schema, field)
        if (field == "preference" and "expansion_network_v1" in schema.get("x-validation-handlers", [])
                and field not in fallback):
            value, source = None, None
        if field in fallback:
            value, source = fallback[field]
        elif value is not None and field_schema.get("type") not in {"object", "array"}:
            # A literal's presence is insufficient to bind it to a scalar field.
            # Accept model interpretations only with nearby catalog field wording.
            if not grounded_scalar(prompt, field, field_schema, value):
                value, source = None, None
        if value is not None:
            params[field] = value
            provenance[field] = source or "user"
        elif allowed_fields is None and field in schema.get("required", []):
            params[field] = None
    return params, provenance


def _contract(schema: dict) -> dict:
    properties = {}
    for field, field_schema in schema.get("properties", {}).items():
        try:
            metadata = parameter_metadata(field, field_schema)
        except KeyError:
            metadata = {}
        properties[field] = {
            "display_name": metadata.get("display_name") or parameter_label(field),
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
    mentioned = mentioned_fields(prompt, schema)
    requested = requested_fields or list(dict.fromkeys([
        *schema.get("required", []),
        *(field for field in schema.get("properties", {}) if field in mentioned),
    ]))
    system = f"""You are a strict network-operation parameter parser.
Extract only values explicitly stated in the current user message.
Never invent, assume, infer, guess, or use a value from an example.
Return null for a required value absent from the current user message.
Include optional values when explicitly supplied; omit absent optional values.
Return JSON only: {{\"parameters\": {{}}}}.

Parameter contract:
{json.dumps(contract, indent=2)}

Existing validated values (context only; do not repeat unless the user repeats them):
{json.dumps(existing, indent=2)}
Fields currently requested: {json.dumps(requested)}
"""
    raw_params: dict = {}
    deterministic = _explicit_values(prompt, schema)
    fields_to_extract = requested
    diagnostics = []
    if not all(field in deterministic for field in fields_to_extract):
        for attempt in range(2):
            try:
                repair = "\nPrevious output was not a parameter object. Return the required JSON object; unknown values must be null." if attempt else ""
                raw = llm.invoke([("system", system + repair), ("human", prompt)]).content.strip()
                data = _parse_json(raw)
                candidate = data.get("parameters", data) if isinstance(data, dict) else None
                if not isinstance(candidate, dict):
                    raise ValueError("Expected a parameter object.")
                filtered, _ = _filter_to_schema(prompt, candidate, schema)
                canonical = canonicalize_parameter_keys(candidate, schema)
                unsupported = [key for key, value in canonical.items() if value is not None and filtered.get(key) is None]
                if unsupported and attempt == 0:
                    system += "\nThe following proposed fields lack supported, field-specific user evidence: " + ", ".join(unsupported) + ". Repair once using only quoted user information; otherwise return null."
                    continue
                raw_params = candidate
                break
            except (ValueError, TypeError, AttributeError):
                diagnostics.append("Model returned an invalid extraction object.")
            except Exception:
                diagnostics.append("Model unavailable; retained deterministic extraction.")
                break

    allowed_fields = set(requested_fields) if requested_fields else None
    params, provenance = _filter_to_schema(prompt, raw_params, schema, allowed_fields)
    candidates = []
    alternatives = explicit_alternatives(mask_literals(prompt), schema)
    for field, node in schema.get("properties", {}).items():
        literals = literal_candidates(prompt, field, node)
        if len(literals) > 1:
            alternatives[field] = literals
    for field, values in alternatives.items():
        if allowed_fields is not None and field not in allowed_fields:
            continue
        params[field] = None
        provenance.pop(field, None)
        candidates.append({"field": field, "type": "AMBIGUOUS", "values": values, "evidence": prompt, "source": "user"})
    required = schema.get("required", [])
    for field in schema.get("properties", {}):
        if (field in mentioned and field not in required and params.get(field) is None
                and (allowed_fields is None or field in allowed_fields)
                and not any(candidate["field"] == field for candidate in candidates)):
            candidates.append({"field": field, "type": "UNRESOLVED_VALUE", "values": [],
                               "evidence": prompt, "source": "user",
                               "message": f"You mentioned {contract['properties'][field]['display_name']}, but its value could not be safely extracted. Please specify it."})
    return ExtractionResult(
        parameters=params,
        provided_fields=sorted(provenance),
        missing_fields=[field for field in required if params.get(field) is None],
        provenance=provenance,
        candidates=candidates,
        diagnostics=diagnostics,
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
