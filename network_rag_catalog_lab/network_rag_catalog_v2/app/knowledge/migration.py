"""Read-only schema evidence and membership backfill; never rewrites source data."""

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import TYPE_CHECKING, Sequence

from jsonschema import Draft202012Validator, SchemaError

from .models import CategoryParameter, ParameterDefinition

if TYPE_CHECKING:
    from .services import KnowledgeService


@dataclass(frozen=True)
class SchemaParameterReference:
    field_path: str
    parameter_id: str
    value_type: str
    explicit_reference: bool


# These structures need a reviewed resolver, not a partial recursive import.
_UNSUPPORTED_STRUCTURES = {
    "$ref", "$dynamicRef", "allOf", "anyOf", "oneOf", "not", "if", "then", "else",
    "dependentSchemas", "patternProperties", "prefixItems", "contains",
    "unevaluatedItems", "unevaluatedProperties",
}


def schema_parameter_references(schema: dict, parameters: Sequence[ParameterDefinition]) -> list[SchemaParameterReference]:
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise ValueError(f"Invalid operation schema: {exc.message}") from exc
    definitions = {parameter.parameter_id: parameter for parameter in parameters}
    references = []

    def walk(node, path: str, *, field: str | None = None):
        location = path or "<root>"
        if not isinstance(node, dict):
            raise ValueError(f"Schema at '{location}' needs an explicit typed schema for membership review.")
        unsupported = _UNSUPPORTED_STRUCTURES.intersection(node)
        if unsupported:
            raise ValueError(f"Unsupported schema structure at '{location}': {sorted(unsupported)}; review before backfill.")
        if isinstance(node.get("additionalProperties"), dict):
            raise ValueError(f"Dynamic properties at '{location}' need review before backfill.")
        value_type = node.get("type")
        if not isinstance(value_type, str):
            raise ValueError(f"Schema at '{location}' needs one explicit type; missing/union types require review.")
        if field is None and "x-parameter-id" in node:
            raise ValueError(f"Anonymous schema at '{location}' has x-parameter-id; review before backfill.")
        if field is not None:
            parameter_id = node.get("x-parameter-id", field)
            if not isinstance(parameter_id, str) or parameter_id not in definitions:
                raise ValueError(
                    f"Unknown parameter {parameter_id!r} at '{location}'; use a registered ID or explicit x-parameter-id. "
                    "Aliases are not inferred."
                )
            parameter = definitions[parameter_id]
            if value_type != parameter.value_type:
                raise ValueError(
                    f"Parameter '{parameter_id}' at '{location}' has schema type '{value_type}', "
                    f"but the registry specifies '{parameter.value_type}'."
                )
            references.append(SchemaParameterReference(path, parameter_id, value_type, "x-parameter-id" in node))
        if "properties" in node and value_type != "object":
            raise ValueError(f"Properties at '{location}' require an explicit object type.")
        for name, child in node.get("properties", {}).items():
            if not name or any(token in name for token in (".", "[", "]")):
                raise ValueError(f"Property {name!r} at '{location}' has an ambiguous field path; review before backfill.")
            walk(child, f"{path}.{name}" if path else name, field=name)
        if value_type == "array":
            walk(node.get("items"), f"{path}[]")
        elif "items" in node:
            raise ValueError(f"Items at '{location}' require an explicit array type.")

    if not isinstance(schema, dict) or schema.get("type") != "object":
        raise ValueError("Operation schema must declare an object root for membership backfill.")
    walk(schema, "")
    return references


def build_category_parameter_backfill(service: "KnowledgeService", base_dir: Path) -> dict:
    """Propose the schema-used membership subset, with full-path evidence."""
    service.validate_metadata()
    parameters = service.list_parameters()
    pairs = set()
    evidence = []
    for operation in service.list_operations(include_inactive=True):
        path = base_dir / operation.schema_path
        schema = json.loads(path.read_text(encoding="utf-8"))
        try:
            references = schema_parameter_references(schema, parameters)
        except ValueError as exc:
            raise ValueError(f"Operation {operation.operation_id}: {exc}") from exc
        for reference in references:
            pairs.add((operation.category_id, reference.parameter_id))
            evidence.append({
                "operation_id": operation.operation_id, "category_id": operation.category_id,
                "schema_path": operation.schema_path, **asdict(reference),
            })
    memberships = [CategoryParameter(category_id=category, parameter_id=parameter) for category, parameter in sorted(pairs)]
    service.validate_category_parameters(memberships)
    return {
        "memberships": [record.model_dump() for record in memberships],
        "evidence": evidence,
    }


def main() -> None:
    import argparse
    from ..config import BASE_DIR, CATALOG_FILE, CATEGORIES_FILE, PARAMETERS_FILE
    from .file_repository import FileKnowledgeRepository
    from .services import KnowledgeService
    from .authority import authority
    from .sqlite_repository import SQLiteKnowledgeRepository

    repository = SQLiteKnowledgeRepository(BASE_DIR) if authority(BASE_DIR) == "sqlite" else FileKnowledgeRepository(
        categories_file=CATEGORIES_FILE, operations_file=CATALOG_FILE, parameters_file=PARAMETERS_FILE,
    )
    service = KnowledgeService(repository)
    parser = argparse.ArgumentParser(description="Read-only catalog migration previews.")
    parser.add_argument("--operations", action="store_true", help="Preview operation mappings and rules instead of memberships.")
    parser.add_argument("--compare", action="store_true", help="Compare operation records with retained legacy migration schemas.")
    args = parser.parse_args()
    if args.operations and args.compare:
        parser.error("Choose either --operations or --compare.")
    if args.compare:
        service.validate_metadata()
        service.validate_category_parameters()
        service.validate_operation_records()
        reports = [service.compare_operation_schema(operation.operation_id, json.loads((BASE_DIR / operation.schema_path).read_text(encoding="utf-8")))
                   for operation in service.list_operations(True) if operation.schema_path]
        print(json.dumps(reports, indent=2))
        if any(not report["matches"] for report in reports):
            raise SystemExit(1)
    else:
        report = build_operation_backfill(service, BASE_DIR) if args.operations else build_category_parameter_backfill(service, BASE_DIR)
        print(json.dumps(report, indent=2))


def build_operation_backfill(service: "KnowledgeService", base_dir: Path) -> dict:
    from .operation_contracts import project_operation_schema

    service.validate_metadata()
    service.validate_category_parameters()
    mappings, rules = [], []
    parameters = service.list_parameters()
    for operation in service.list_operations(True):
        schema = json.loads((base_dir / operation.schema_path).read_text(encoding="utf-8"))
        try:
            service.validate_schema_membership(operation.category_id, schema_parameter_references(schema, parameters))
            projected = project_operation_schema(operation, schema, parameters)
        except ValueError as exc:
            raise ValueError(f"Operation {operation.operation_id}: {exc}") from exc
        mappings.extend(projected["operation_parameters"])
        rules.extend(projected["operation_rules"])
    service.validate_operation_records(mappings, rules)
    return {"operation_parameters": [row.model_dump() for row in mappings], "operation_rules": [row.model_dump() for row in rules]}


if __name__ == "__main__":
    main()
