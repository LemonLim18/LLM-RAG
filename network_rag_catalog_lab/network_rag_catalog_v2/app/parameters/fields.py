"""Shared nested-field addressing and strict, question-scoped input parsing."""

from copy import deepcopy
import json
import re

from .normalizer import deterministic_values, prefix_length_from_text


def tokens(path: str) -> list:
    if not re.fullmatch(r"[A-Za-z_]\w*(?:(?:\.\w+)|(?:\[\d+\]))*", path):
        raise ValueError(f"Invalid field path: {path}")
    return [int(index) if index else name for name, index in re.findall(r"([A-Za-z_]\w*)|\[(\d+)\]", path)]


def get_value(params: dict, path: str, default=None):
    value = params
    try:
        for token in tokens(path):
            value = value[token]
        return value
    except (KeyError, IndexError, TypeError):
        return default


def set_value(params: dict, path: str, value) -> dict:
    result = deepcopy(params)
    parts = tokens(path)
    parent = result
    for index, token in enumerate(parts[:-1]):
        if isinstance(parent, dict) and parent.get(token) is None:
            parent[token] = [] if isinstance(parts[index + 1], int) else {}
        if isinstance(parent, list):
            while len(parent) <= token:
                parent.append({})
        parent = parent[token]
    parent[parts[-1]] = value
    return result


def schema_at(schema: dict, path: str) -> dict:
    for token in tokens(path):
        schema = schema.get("items", {}) if isinstance(token, int) else schema.get("properties", {}).get(token, {})
    if not schema:
        raise ValueError(f"Unknown schema field: {path}")
    return schema


def leaf_values(params, path=""):
    if isinstance(params, dict):
        for key, value in params.items():
            yield from leaf_values(value, f"{path}.{key}" if path else key)
    elif isinstance(params, list):
        for index, value in enumerate(params):
            yield from leaf_values(value, f"{path}[{index}]")
    else:
        yield path, params


def parse_answer(text: str, path: str, schema: dict):
    value = text.strip()
    if not value:
        raise ValueError("An answer is required.")
    field = tokens(path)[-1]
    kind = schema.get("type")
    if field == "prefix_length":
        prefix = prefix_length_from_text(value, allow_bare_netmask=True)
        if prefix is not None:
            return prefix
    if kind == "integer":
        if not re.fullmatch(r"-?\d+", value):
            raise ValueError("Enter a whole number; units and other characters are not allowed.")
        return int(value)
    if kind == "boolean":
        choices = {"true": True, "yes": True, "enable": True, "false": False, "no": False, "disable": False}
        if value.lower() not in choices:
            raise ValueError("Enter true/false or enable/disable.")
        return choices[value.lower()]
    if kind in {"array", "object"}:
        try:
            return json.loads(value)
        except ValueError:
            if field == "interfaces":
                parsed = deterministic_values(value, {"properties": {"interfaces": schema}})
                if parsed.get("interfaces"):
                    return parsed["interfaces"][0]
            raise ValueError("Enter a JSON value or explicitly named interfaces.") from None
    return value
