"""Project legacy schemas for comparison only; never compile executable schemas."""

from copy import deepcopy
import json

from .migration import schema_parameter_references
from .models import Operation, OperationParameterMapping, OperationSchemaRule, ParameterDefinition


def project_operation_schema(operation: Operation, schema: dict, parameters: list[ParameterDefinition]) -> dict:
    references = {ref.field_path: ref for ref in schema_parameter_references(schema, parameters)}
    mappings = []
    rules = []

    def walk(node, path=""):
        required = node.get("required", [])
        properties = node.get("properties", {})
        if any(field not in properties for field in required):
            raise ValueError(f"Required fields at '{path or '<root>'}' must have explicit property definitions.")
        keywords = {key: deepcopy(value) for key, value in node.items() if key not in {"properties", "items", "required"}}
        if path in references:
            keywords.pop("type")  # Named property types come from shared definitions.
        if "x-required-by-vendor" in keywords:
            vendors = keywords["x-required-by-vendor"]
            if path or not isinstance(vendors, dict) or any(
                not isinstance(fields, list) or any(not isinstance(field, str) or field not in properties for field in fields)
                for fields in vendors.values()
            ):
                raise ValueError("Vendor requirements must reference declared root properties.")
        rules.append(OperationSchemaRule(operation_id=operation.operation_id, operation_version=operation.version,
                                         field_path=path, keywords=keywords))
        for field, child in properties.items():
            child_path = f"{path}.{field}" if path else field
            reference = references[child_path]
            mappings.append(OperationParameterMapping(
                operation_id=operation.operation_id, operation_version=operation.version,
                category_id=operation.category_id, parameter_id=reference.parameter_id,
                field_path=child_path, position=len(mappings), required=field in required,
                required_order=required.index(field) if field in required else None,
            ))
            walk(child, child_path)
        if node.get("type") == "array":
            walk(node["items"], path + "[]")

    walk(schema)
    return {"operation_parameters": mappings, "operation_rules": rules}


def compare_projection(operation: Operation, expected: dict, mappings: list[OperationParameterMapping], rules: list[OperationSchemaRule]) -> dict:
    differences = []
    for kind, actual_records in (("operation_parameters", mappings), ("operation_rules", rules)):
        legacy = {row.field_path: row.model_dump() for row in expected[kind]}
        actual = {row.field_path: row.model_dump() for row in actual_records}
        for path in sorted(legacy.keys() | actual.keys()):
            if json.dumps(legacy.get(path), sort_keys=True) != json.dumps(actual.get(path), sort_keys=True):
                differences.append({"kind": kind, "field_path": path, "legacy": legacy.get(path), "candidate": actual.get(path)})
    return {"operation_id": operation.operation_id, "operation_version": operation.version,
            "schema_source": operation.schema_source, "matches": not differences, "differences": differences}
