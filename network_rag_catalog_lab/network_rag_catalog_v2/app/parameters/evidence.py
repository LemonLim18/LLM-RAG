"""Field-scoped literal evidence; unsupported prose remains a clarification."""

import json
import math
import re

from ..catalog import load_parameters, operation_terms
from .normalizer import parameter_identity, parameter_metadata


def mask_literals(prompt: str) -> str:
    """Keep offsets while excluding quoted/structured data from field discovery."""
    masked = list(prompt)
    index = 0
    while index < len(prompt):
        end = 0
        if prompt[index] in '[{"':
            try:
                _, end = json.JSONDecoder().raw_decode(prompt[index:])
            except ValueError:
                pass
        elif prompt[index] == "'":
            quoted = re.match(r"'[^'\r\n]*'", prompt[index:])
            end = quoted.end() if quoted else 0
        if end:
            masked[index:index + end] = " " * end
            index += end
        else:
            index += 1
    return "".join(masked)


def field_terms(field: str, schema: dict) -> list[str]:
    terms = [field, field.replace("_", " "), parameter_identity(field, schema)]
    try:
        metadata = parameter_metadata(field, schema)
        terms.extend([metadata.get("display_name", ""), *metadata.get("aliases", [])])
    except KeyError:
        pass
    return sorted({term for term in terms if term}, key=len, reverse=True)


def value_tails(prompt: str, field: str, schema: dict):
    terms = "|".join(re.escape(term) for term in field_terms(field, schema))
    pattern = rf"(?<![\w])(?:{terms})(?![\w])"
    visible = mask_literals(prompt)
    for term, _ in operation_terms():
        visible = re.sub(rf"(?<!\w){re.escape(term)}(?!\w)", lambda match: " " * len(match.group()), visible, flags=re.I)
    for match in re.finditer(pattern, visible, re.I):
        tail = prompt[match.end():].lstrip()
        yield re.sub(r"^(?:is\b|=|:)\s*", "", tail, count=1, flags=re.I)


def mentioned_fields(prompt: str, schema: dict) -> set[str]:
    return {field for field, node in schema.get("properties", {}).items()
            if next(value_tails(prompt, field, node), None) is not None}


def _ends_value(tail: str) -> bool:
    tail = tail.strip()
    if (not tail or tail in {".", ";"} or tail.startswith("; ")
            or re.match(r"(?:on|for|with|using)\b", tail, re.I)):
        return True
    separator = re.match(r"(?:,|and\b)\s*", tail, re.I)
    if not separator:
        return False
    remaining = tail[separator.end():]
    for parameter in load_parameters():
        identity = parameter["parameter_id"]
        terms = [identity, identity.replace("_", " "), parameter.get("display_name", ""), *parameter.get("aliases", [])]
        if any(term and re.match(re.escape(term) + r"(?!\w)", remaining, re.I) for term in terms):
            return True
    return False


def _matches_shape(value, schema: dict) -> bool:
    kind = schema.get("type")
    if kind == "array":
        return isinstance(value, list) and all(_matches_shape(item, schema.get("items", {})) for item in value)
    if kind == "object":
        properties = schema.get("properties", {})
        return (isinstance(value, dict) and not set(value) - set(properties)
                and all(item is None or _matches_shape(item, properties[key]) for key, item in value.items()))
    if kind == "integer":
        return type(value) is int
    if kind == "number":
        return type(value) is int or (type(value) is float and math.isfinite(value))
    if kind == "boolean":
        return type(value) is bool
    return kind == "string" and isinstance(value, str)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate keys cannot establish unambiguous evidence.")
        result[key] = value
    return result


def _read_literal(tail: str, schema: dict):
    try:
        value, end = json.JSONDecoder(object_pairs_hook=_unique_object).raw_decode(tail)
        if _ends_value(tail[end:]) and _matches_shape(value, schema):
            return value
    except ValueError:
        pass
    if schema.get("type") == "string":
        quoted = re.match(r"'([^'\r\n]*)'", tail)
        if quoted and _ends_value(tail[quoted.end():]):
            return quoted.group(1)
        token = re.match(r"[A-Za-z0-9_./:-]+", tail)
        if token and _ends_value(tail[token.end():]):
            value = token.group()
            if value in schema.get("enum", []) or (schema.get("pattern") and re.fullmatch(schema["pattern"], value)):
                return value
    if schema.get("type") != "array":
        return None
    kind = schema.get("items", {}).get("type")
    token = {"integer": r"-?\d+", "boolean": r"(?:true|false)",
             "string": r"[A-Za-z0-9_./:-]+"}.get(kind)
    if not token:
        return None
    sequence = re.match(rf"{token}(?:\s*(?:,|\band\b)\s*{token})*", tail, re.I)
    if not sequence or not _ends_value(tail[sequence.end():]):
        return None
    parts = re.split(r"\s*(?:,|\band\b)\s*", sequence.group(), flags=re.I)
    if kind == "integer":
        return [int(part) for part in parts]
    if kind == "boolean":
        return [part.lower() == "true" for part in parts]
    return parts


def literal_candidates(prompt: str, field: str, schema: dict) -> list:
    values = []
    identities = set()
    for tail in value_tails(prompt, field, schema):
        value = _read_literal(tail, schema)
        identity = json.dumps(value, sort_keys=True)
        if value is not None and identity not in identities:
            values.append(value)
            identities.add(identity)
    return values


def grounded_scalar(prompt: str, field: str, schema: dict, value) -> bool:
    if not _matches_shape(value, schema):
        return False
    for tail in value_tails(prompt, field, schema):
        literal = _read_literal(tail, schema)
        if literal is not None and type(literal) is type(value) and literal == value:
            return True
        if isinstance(value, str) and tail.casefold().startswith(value.casefold()) and _ends_value(tail[len(value):]):
            return True
    return False
