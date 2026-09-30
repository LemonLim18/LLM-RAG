"""Central catalog access and consistency checks.

Stable IDs are the machine contract. Display names and aliases are editable
metadata, so prompts, terminal questions, retrieval documents, and a future UI
all use the same wording.
"""

import json
from pathlib import Path
import re

from .config import CATALOG_FILE, CATEGORIES_FILE, CATEGORY_PARAMETERS_FILE, INVENTORY_FILE, PARAMETERS_FILE, TEMPLATES_DIR
from .knowledge.file_repository import FileKnowledgeRepository
from .knowledge.migration import schema_parameter_references
from .knowledge.services import KnowledgeService


_knowledge = KnowledgeService(FileKnowledgeRepository(
    categories_file=CATEGORIES_FILE,
    operations_file=CATALOG_FILE,
    parameters_file=PARAMETERS_FILE,
    category_parameters_file=CATEGORY_PARAMETERS_FILE,
))


def knowledge_service():
    from .knowledge.runtime import current_snapshot
    snapshot = current_snapshot()
    return snapshot.service if snapshot else _knowledge


def load_categories() -> list[dict]:
    return [record.to_legacy_dict() for record in knowledge_service().list_categories() if record.status == "active"]


def load_operations(include_inactive: bool = False) -> list[dict]:
    return [record.to_legacy_dict() for record in knowledge_service().list_operations(include_inactive)]


def load_parameters() -> list[dict]:
    return [record.to_legacy_dict() for record in knowledge_service().list_parameters()]


def load_category_parameters(category_id: str | None = None) -> list[dict]:
    return [record.model_dump() for record in knowledge_service().list_category_parameters(category_id)]


def parameters_for_category(category_id: str) -> list[dict]:
    return [record.to_legacy_dict() for record in knowledge_service().parameters_for_category(category_id)]


def load_operation_parameters(operation_id: str | None = None) -> list[dict]:
    return [record.model_dump() for record in knowledge_service().list_operation_parameters(operation_id)]


def load_operation_rules(operation_id: str | None = None) -> list[dict]:
    return [record.model_dump() for record in knowledge_service().list_operation_rules(operation_id)]


def compare_operation_schema(operation_id: str, schema: dict) -> dict:
    """Compare against the request's catalog without consulting stale seed data."""
    return knowledge_service().compare_operation_schema(operation_id, schema)


def reload_catalog() -> None:
    """Refresh catalog data after an in-process administrator edit."""
    _knowledge.reload()


def get_category(category_id: str) -> dict:
    return knowledge_service().get_category(category_id).to_legacy_dict()


def get_operation(operation_id: str) -> dict:
    return knowledge_service().get_operation(operation_id).to_legacy_dict()


def get_parameter(parameter_id: str) -> dict:
    return knowledge_service().get_parameter(parameter_id).to_legacy_dict()


def parameter_label(parameter_id: str) -> str:
    try:
        return get_parameter(parameter_id)["display_name"]
    except KeyError:
        return parameter_id.replace("_", " ")


def category_for_text(text: str) -> str | None:
    """Return a catalog category only when an explicit catalog alias appears."""
    normalized = text.lower()
    for category in load_categories():
        terms = [category["category_id"], *category.get("aliases", [])]
        if any(
            re.search(rf"(?<![a-z0-9]){re.escape(term.lower())}(?![a-z0-9])", normalized)
            for term in terms
        ):
            return category["category_id"]
    return None


def operation_terms() -> list[tuple[str, str]]:
    """Return deterministic operation phrases ordered from most to least specific."""
    terms: list[tuple[str, str]] = []
    for operation in load_operations():
        values = [operation["display_name"], *operation.get("aliases", [])]
        for value in values:
            value = value.strip().lower()
            if value:
                terms.append((value, operation["operation_id"]))
    return sorted(set(terms), key=lambda item: len(item[0]), reverse=True)


def validate_catalog() -> None:
    """Fail early when a catalog edit leaves a broken reference behind."""
    from .knowledge.runtime import current_snapshot
    from .knowledge.schema_compiler import compile_schema
    snapshot = current_snapshot()
    if snapshot:
        snapshot.verify()
        return
    from .config import runtime_mode
    if runtime_mode() == "files":
        from .file_runtime import validate_files
        validate_files()
        return
    _knowledge.validate_metadata()
    _knowledge.validate_category_parameters()
    operations = load_operations(include_inactive=True)
    parameters = _knowledge.list_parameters()
    inventory = json.loads(INVENTORY_FILE.read_text(encoding="utf-8"))
    vendors = {device["vendor"] for device in inventory}

    for operation in operations:
        status = operation.get("status", "active")
        if operation.get("schema_source") == "registry":
            compile_schema(_knowledge, operation["operation_id"])
            continue
        schema_path = Path(__file__).resolve().parents[1] / operation["schema_path"]
        if not schema_path.exists():
            raise ValueError(f"Operation {operation['operation_id']} schema does not exist: {schema_path}")
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        try:
            references = schema_parameter_references(schema, parameters)
            _knowledge.validate_schema_membership(operation["category_id"], references)
        except ValueError as exc:
            raise ValueError(f"Operation {operation['operation_id']}: {exc}") from exc
        unknown_vendor_fields = {
            field
            for fields in schema.get("x-required-by-vendor", {}).values()
            for field in fields
            if field not in schema.get("properties", {})
        }
        if unknown_vendor_fields:
            raise ValueError(
                f"Operation {operation['operation_id']} has undefined vendor-required parameters: "
                f"{', '.join(sorted(unknown_vendor_fields))}"
            )
        if status != "active":
            continue
        for vendor in vendors:
            template = TEMPLATES_DIR / vendor / operation["category_id"] / operation["operation_id"] / "template.j2"
            if not template.exists():
                raise ValueError(
                    f"Operation {operation['operation_id']} is missing the {vendor} template: {template}"
                )
    if any(operation.get("mapping_mode") == "compare" for operation in operations):
        _knowledge.validate_operation_records()
    if any(operation.get("schema_source") == "registry" for operation in operations):
        from .config import BASE_DIR, TEMPLATE_BINDINGS_FILE
        from .knowledge.publication import _sources, validate_bindings
        schemas = {op["operation_id"]: compile_schema(_knowledge, op["operation_id"]) for op in operations}
        validate_bindings(json.loads(TEMPLATE_BINDINGS_FILE.read_text(encoding="utf-8")), _knowledge, schemas, _sources(BASE_DIR))
