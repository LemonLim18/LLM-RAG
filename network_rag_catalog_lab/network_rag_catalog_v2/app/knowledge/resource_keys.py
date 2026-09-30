"""Typed composite identities for new context rules; legacy keys stay unchanged."""

from ..parameters.fields import get_value, schema_at


def validate_composite_keys(rule, schema):
    constants = rule.get("resource_constants", [])
    if not isinstance(constants, list) or any(type(value) not in (str, int, bool) for value in constants):
        raise ValueError("Resource constants must be reviewed scalar identities.")
    keys = rule.get("composite_keys", [])
    if not isinstance(keys, list):
        raise ValueError("Composite resource keys must be an array.")
    for key in keys:
        if (not isinstance(key, dict) or set(key) != {"kind", "fields"} or not isinstance(key["kind"], str)
                or not key["kind"] or not isinstance(key["fields"], list) or not key["fields"]
                or any(not isinstance(path, str) or "[]" in path for path in key["fields"])):
            raise ValueError("Invalid composite resource identity.")
        for path in key["fields"]:
            if schema_at(schema, path).get("type") not in {"string", "integer", "boolean"}:
                raise ValueError("Composite identities require scalar fields.")


def composite_values(rule, params):
    result = set()
    for key in rule.get("composite_keys", []):
        values = [get_value(params, path) for path in key["fields"]]
        if all(type(value) in (str, int, bool) for value in values):
            result.add((key["kind"], tuple((type(value).__name__, value) for value in values)))
    return result
