"""Read-only knowledge use cases and catalog metadata integrity checks."""

from collections.abc import Sequence
import json
from typing import TypeVar

from .migration import SchemaParameterReference
from .models import CatalogRecord, Category, CategoryParameter, Operation, OperationParameterMapping, OperationSchemaRule, ParameterDefinition
from .operation_contracts import compare_projection, project_operation_schema
from .repository import KnowledgeRepository


RecordT = TypeVar("RecordT", bound=CatalogRecord)


def _get_by_id(records: Sequence[RecordT], id_field: str, record_id: str) -> RecordT:
    for record in records:
        if getattr(record, id_field) == record_id:
            return record
    raise KeyError(f"Unknown {id_field}: {record_id}")


class KnowledgeService:
    def __init__(self, repository: KnowledgeRepository):
        self.repository = repository
        self._schema_projections: dict[str, tuple[str, dict]] = {}

    def list_categories(self) -> list[Category]:
        return self.repository.list_categories()

    def list_operations(self, include_inactive: bool = False) -> list[Operation]:
        records = self.repository.list_operations()
        return records if include_inactive else [record for record in records if record.status == "active"]

    def list_parameters(self) -> list[ParameterDefinition]:
        return self.repository.list_parameters()

    def list_category_parameters(self, category_id: str | None = None) -> list[CategoryParameter]:
        if category_id is not None:
            self.get_category(category_id)
        records = self.repository.list_category_parameters()
        return records if category_id is None else [record for record in records if record.category_id == category_id]

    def parameters_for_category(self, category_id: str) -> list[ParameterDefinition]:
        memberships = self.list_category_parameters(category_id)
        definitions = self.list_parameters()
        return [_get_by_id(definitions, "parameter_id", record.parameter_id) for record in memberships]

    def list_operation_parameters(self, operation_id: str | None = None) -> list[OperationParameterMapping]:
        if operation_id is not None:
            _get_by_id(self.list_operations(True), "operation_id", operation_id)
        rows = self.repository.list_operation_parameters()
        return rows if operation_id is None else [row for row in rows if row.operation_id == operation_id]

    def list_operation_rules(self, operation_id: str | None = None) -> list[OperationSchemaRule]:
        if operation_id is not None:
            _get_by_id(self.list_operations(True), "operation_id", operation_id)
        rows = self.repository.list_operation_rules()
        return rows if operation_id is None else [row for row in rows if row.operation_id == operation_id]

    def compare_operation_schema(self, operation_id: str, schema: dict) -> dict:
        operation = _get_by_id(self.list_operations(True), "operation_id", operation_id)
        parameters = self.list_parameters()
        signature = json.dumps([operation.category_id, operation.version, schema,
                                [(row.parameter_id, row.value_type) for row in parameters]], sort_keys=True)
        cached = self._schema_projections.get(operation_id)
        if cached is None or cached[0] != signature:
            cached = (signature, project_operation_schema(operation, schema, parameters))
            self._schema_projections[operation_id] = cached
        expected = cached[1]
        mappings = self.list_operation_parameters(operation_id)
        rules = self.list_operation_rules(operation_id)
        self.validate_operation_records(mappings, rules, operations=[operation])
        return compare_projection(operation, expected, mappings, rules)

    def validate_operation_records(
        self, mappings: Sequence[OperationParameterMapping] | None = None,
        rules: Sequence[OperationSchemaRule] | None = None, *, operations: Sequence[Operation] | None = None,
    ) -> None:
        operations = self.list_operations(True) if operations is None else operations
        expected_operations = {operation.operation_id: operation for operation in operations}
        mappings = self.list_operation_parameters() if mappings is None else mappings
        rules = self.list_operation_rules() if rules is None else rules
        memberships = {(row.category_id, row.parameter_id) for row in self.list_category_parameters()}
        parameters = {row.parameter_id: row for row in self.list_parameters()}
        seen = set()
        for kind, rows in (("mapping", mappings), ("rule", rules)):
            for row in rows:
                operation = expected_operations.get(row.operation_id)
                if operation is None or row.operation_version != operation.version:
                    raise ValueError(f"Unknown/stale operation version in {kind}: {row.operation_id} v{row.operation_version}")
                key = (kind, row.operation_id, row.field_path)
                if key in seen:
                    raise ValueError(f"Duplicate operation {kind}: {row.operation_id}:{row.field_path}")
                seen.add(key)
                if kind == "mapping" and (row.category_id != operation.category_id or
                                          (row.category_id, row.parameter_id) not in memberships or row.parameter_id not in parameters):
                    raise ValueError(f"Invalid category parameter mapping: {row.operation_id}:{row.field_path}")
        for operation in operations:
            fields = {row.field_path: row for row in mappings if row.operation_id == operation.operation_id}
            nodes = {row.field_path: row for row in rules if row.operation_id == operation.operation_id}
            if not fields and not nodes and operation.mapping_mode == "none":
                continue
            if "" not in nodes or nodes[""].keywords.get("type") != "object":
                raise ValueError(f"Operation {operation.operation_id} needs an object-root rule.")
            if sorted(row.position for row in fields.values()) != list(range(len(fields))):
                raise ValueError(f"Invalid mapping positions for {operation.operation_id}")
            required_orders = {}
            for path, row in fields.items():
                parent = path.rsplit(".", 1)[0] if "." in path else ""
                if path not in nodes or parent not in nodes:
                    raise ValueError(f"Missing schema rule for {operation.operation_id}:{path}")
                parent_type = parameters[fields[parent].parameter_id].value_type if parent in fields else nodes[parent].keywords.get("type")
                if parent_type != "object":
                    raise ValueError(f"Mapping parent must be an object: {operation.operation_id}:{path}")
                if row.required:
                    required_orders.setdefault(parent, []).append(row.required_order)
            if any(sorted(indices) != list(range(len(indices))) for indices in required_orders.values()):
                raise ValueError(f"Invalid required-field order for {operation.operation_id}")
            for path, row in nodes.items():
                if path in fields:
                    if "type" in row.keywords:
                        raise ValueError(f"Named field types belong to shared definitions: {operation.operation_id}:{path}")
                    if "x-parameter-id" in row.keywords and row.keywords["x-parameter-id"] != fields[path].parameter_id:
                        raise ValueError(f"Conflicting parameter identity: {operation.operation_id}:{path}")
                elif path:
                    parent = path[:-2] if path.endswith("[]") else None
                    parent_type = (parameters[fields[parent].parameter_id].value_type if parent in fields
                                   else nodes[parent].keywords.get("type") if parent in nodes else None)
                    if parent_type != "array" or "type" not in row.keywords:
                        raise ValueError(f"Dangling anonymous rule: {operation.operation_id}:{path}")

    def get_category(self, category_id: str) -> Category:
        return _get_by_id(self.list_categories(), "category_id", category_id)

    def get_operation(self, operation_id: str) -> Operation:
        return _get_by_id(self.list_operations(), "operation_id", operation_id)

    def get_parameter(self, parameter_id: str) -> ParameterDefinition:
        return _get_by_id(self.list_parameters(), "parameter_id", parameter_id)

    def reload(self) -> None:
        self.repository.reload()
        self._schema_projections.clear()

    def validate_category_parameters(self, memberships: Sequence[CategoryParameter] | None = None) -> None:
        from ..parameters.normalizer import normalize_key

        category_ids = {record.category_id for record in self.list_categories()}
        parameters = {record.parameter_id: record for record in self.list_parameters()}
        pairs = set()
        phrase_owners = {}
        records = self.list_category_parameters() if memberships is None else memberships
        for record in records:
            pair = (record.category_id, record.parameter_id)
            if pair in pairs:
                raise ValueError(f"Duplicate category parameter membership: {pair}")
            pairs.add(pair)
            if record.category_id not in category_ids:
                raise ValueError(f"Membership references unknown category: {record.category_id}")
            if record.parameter_id not in parameters:
                raise ValueError(f"Membership references unknown parameter: {record.parameter_id}")
            parameter = parameters[record.parameter_id]
            for phrase in [parameter.parameter_id, parameter.display_name, *parameter.aliases]:
                key = (record.category_id, normalize_key(phrase))
                if not key[1]:
                    raise ValueError(f"Category {record.category_id} parameter alias '{phrase}' has no searchable characters.")
                if key in phrase_owners and phrase_owners[key] != parameter.parameter_id:
                    raise ValueError(
                        f"Category {record.category_id} parameter alias '{phrase}' has multiple owners: "
                        f"{phrase_owners[key]}, {parameter.parameter_id}."
                    )
                phrase_owners[key] = parameter.parameter_id

    def validate_schema_membership(self, category_id: str, references: Sequence[SchemaParameterReference]) -> None:
        allowed = {record.parameter_id for record in self.list_category_parameters(category_id)}
        for reference in references:
            if reference.parameter_id not in allowed:
                raise ValueError(
                    f"Category {category_id} does not expose parameter '{reference.parameter_id}' "
                    f"used at '{reference.field_path}'."
                )

    def validate_metadata(self) -> None:
        categories = self.list_categories()
        operations = self.list_operations(include_inactive=True)
        parameters = self.list_parameters()
        for records, key, label in (
            (categories, "category_id", "category"),
            (operations, "operation_id", "operation"),
            (parameters, "parameter_id", "parameter"),
        ):
            seen = set()
            duplicates = set()
            for record in records:
                value = getattr(record, key)
                if value in seen:
                    duplicates.add(value)
                seen.add(value)
            if duplicates:
                raise ValueError(f"Invalid {label} catalog IDs: {sorted(duplicates)}")

        category_ids = {category.category_id for category in categories}
        inactive_categories = {category.category_id for category in categories if category.status == "inactive"}
        category_phrases = {}
        for category in categories:
            for phrase in [category.category_id, category.display_name, *category.aliases]:
                key = phrase.strip().casefold()
                if key in category_phrases and category_phrases[key] != category.category_id:
                    raise ValueError(f"Category alias '{phrase}' has multiple owners.")
                category_phrases[key] = category.category_id
        phrase_owners = {}
        for operation in operations:
            if operation.category_id not in category_ids:
                raise ValueError(
                    f"Operation {operation.operation_id} references unknown category {operation.category_id}."
                )
            if operation.status == "active" and operation.category_id in inactive_categories:
                raise ValueError(f"Active operation {operation.operation_id} belongs to an inactive category.")
            for phrase in [operation.display_name, *operation.aliases]:
                key = phrase.strip().casefold()
                if key in phrase_owners and phrase_owners[key] != operation.operation_id:
                    raise ValueError(f"Operation alias '{phrase}' has multiple owners.")
                phrase_owners[key] = operation.operation_id
