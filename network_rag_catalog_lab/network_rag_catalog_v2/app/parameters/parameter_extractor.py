import json
import re
from typing import Any

from ..llm import llm


def _parse_json(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.S)
        if match:
            return json.loads(match.group(0))
    raise ValueError(f"Cannot parse parameter JSON: {raw}")


def _text_has_value(prompt: str, value: Any) -> bool:
    if value is None:
        return True

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
    if not normalized_value:
        return False
    return bool(
        re.search(
            rf"(?<![a-z0-9]){re.escape(normalized_value)}(?![a-z0-9])",
            normalized_prompt,
        )
    )


def _filter_value(prompt: str, value: Any, schema: dict) -> Any:
    schema_type = schema.get("type")

    if value is None:
        return None

    if schema_type == "object":
        if not isinstance(value, dict):
            return None
        return _filter_to_schema(prompt, value, schema)

    if schema_type == "array":
        if not isinstance(value, list):
            return None
        item_schema = schema.get("items", {})
        filtered_items = []
        for item in value:
            filtered = _filter_value(prompt, item, item_schema)
            if filtered is None:
                continue
            if isinstance(filtered, dict):
                required = item_schema.get("required", [])
                if any(filtered.get(field) is None for field in required):
                    continue
            filtered_items.append(filtered)
        return filtered_items or None

    return value if _text_has_value(prompt, value) else None


def _filter_to_schema(prompt: str, raw_params: dict, schema: dict) -> dict:
    properties = schema.get("properties", {})
    params = {}
    for field, field_schema in properties.items():
        if field in raw_params:
            params[field] = _filter_value(prompt, raw_params[field], field_schema)
        elif field in schema.get("required", []):
            params[field] = None
    return params


def extract_parameters(prompt: str, schema: dict) -> dict:
    contract = {"required": schema.get("required", []), "properties": schema.get("properties", {})}
    system = f"""Extract only parameters stated or directly inferable from the request.
Follow this JSON Schema contract:
{json.dumps(contract, indent=2)}
Return JSON only in this exact shape:
{{
  "parameters": {{}},
  "provided_fields": [],
  "missing_fields": []
}}

Rules:
Extract parameters ONLY when they are explicitly stated in the user's request.
Never invent, assume, infer, guess, or provide default values.
If a required parameter is not explicitly provided, set it to null.
Do not use your general knowledge to fill missing values.
Do not use examples as actual values.
Do not invent missing required values.
Do not add fields outside the contract."""
    raw = llm.invoke([("system", system), ("human", prompt)]).content.strip()
    data = _parse_json(raw)
    raw_params = data.get("parameters", data)
    if not isinstance(raw_params, dict):
        raise ValueError(f"Parameter extraction did not return an object: {raw}")
    return _filter_to_schema(prompt, raw_params, schema)
