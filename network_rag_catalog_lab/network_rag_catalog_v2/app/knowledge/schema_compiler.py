"""Compile the reviewed, limited schema vocabulary without dropping constraints."""

from copy import deepcopy

from jsonschema import Draft202012Validator, FormatChecker

from .migration import schema_parameter_references
from .rule_registry import NORMALIZATION_HANDLERS, validate_handler_ids, validate_object_requirements


def compile_schema(service, operation_id: str) -> dict:
    operation = next((row for row in service.list_operations(True) if row.operation_id == operation_id), None)
    if operation is None:
        raise KeyError(f"Unknown operation: {operation_id}")
    mappings = service.list_operation_parameters(operation_id)
    rules = service.list_operation_rules(operation_id)
    service.validate_operation_records(mappings, rules, operations=[operation])
    definitions = {row.parameter_id: row for row in service.list_parameters()}
    for definition in definitions.values():
        if definition.normalizer and definition.normalizer not in NORMALIZATION_HANDLERS:
            raise ValueError(f"Unknown normalization handler: {definition.normalizer}")
    fields = {row.field_path: row for row in mappings}
    nodes = {row.field_path: row for row in rules}
    visited = set()

    def build(path):
        if path not in nodes:
            raise ValueError(f"Missing schema node: {operation_id}:{path}")
        visited.add(path)
        schema = deepcopy(nodes[path].keywords)
        # Unknown JSON Schema assertions are otherwise silently ignored by validators.
        allowed = set(Draft202012Validator.VALIDATORS) | {
            "$schema", "title", "description", "examples", "default", "readOnly", "writeOnly",
            "deprecated", "x-parameter-id", "x-required-by-vendor", "x-validation-handlers", "x-conditional-required",
        }
        if set(schema) - allowed:
            raise ValueError(f"Unsupported schema keywords at {path}: {sorted(set(schema) - allowed)}")
        if "format" in schema and schema["format"] not in FormatChecker.checkers:
            raise ValueError(f"Unsupported schema format at {path}: {schema['format']}")
        if path in fields:
            identity = fields[path].parameter_id
            schema["type"] = definitions[identity].value_type
            if path.rsplit(".", 1)[-1] != identity:
                schema["x-parameter-id"] = identity
        for keywords, types in (
            ({"minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf"}, {"integer", "number"}),
            ({"minLength", "maxLength", "pattern", "format"}, {"string"}),
            ({"minItems", "maxItems", "uniqueItems"}, {"array"}),
            ({"minProperties", "maxProperties", "additionalProperties", "dependentRequired"}, {"object"}),
        ):
            if keywords.intersection(schema) and schema.get("type") not in types:
                raise ValueError(f"Schema keyword does not apply to {schema.get('type')} at {path}.")
        if schema.get("type") == "object":
            children = sorted((row for row in mappings if row.field_path.rpartition(".")[0] == path), key=lambda row: row.position)
            schema["properties"] = {row.field_path.rsplit(".", 1)[-1]: build(row.field_path) for row in children}
            required = sorted((row for row in children if row.required), key=lambda row: row.required_order)
            if required:
                schema["required"] = [row.field_path.rsplit(".", 1)[-1] for row in required]
        elif schema.get("type") == "array":
            schema["items"] = build(path + "[]")
        if "x-validation-handlers" in schema and path:
            raise ValueError("Validation handlers must be bound at the operation root.")
        validate_object_requirements(schema)
        return schema

    compiled = build("")
    if visited != set(nodes):
        raise ValueError(f"Unreachable schema rules for {operation_id}: {sorted(set(nodes) - visited)}")
    references = schema_parameter_references(compiled, list(definitions.values()))
    service.validate_schema_membership(operation.category_id, references)
    vendor_rules = compiled.get("x-required-by-vendor", {})
    if not isinstance(vendor_rules, dict) or any(
        not isinstance(fields, list) or any(not isinstance(field, str) or field not in compiled["properties"] for field in fields)
        for fields in vendor_rules.values()
    ):
        raise ValueError(f"Invalid vendor requirements for {operation_id}")
    validate_handler_ids(compiled)
    return compiled
