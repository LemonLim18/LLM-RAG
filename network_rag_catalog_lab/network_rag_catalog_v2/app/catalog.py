"""Central catalog access and consistency checks.

Stable IDs are the machine contract. Display names and aliases are editable
metadata, so prompts, terminal questions, retrieval documents, and a future UI
all use the same wording.
"""

from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path
import re

from jsonschema import Draft202012Validator

from .config import CATALOG_FILE, CATEGORIES_FILE, INVENTORY_FILE, PARAMETERS_FILE, TEMPLATES_DIR


@lru_cache(maxsize=None)
def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _items(path: Path) -> list[dict]:
    return deepcopy(_read_json(path))


def load_categories() -> list[dict]:
    return _items(CATEGORIES_FILE)


def load_operations(include_inactive: bool = False) -> list[dict]:
    operations = _items(CATALOG_FILE)
    if include_inactive:
        return operations
    return [operation for operation in operations if operation.get("status", "active") == "active"]


def load_parameters() -> list[dict]:
    return _items(PARAMETERS_FILE)


def reload_catalog() -> None:
    """Refresh catalog data after an in-process administrator edit."""
    _read_json.cache_clear()


def _get_by_id(items: list[dict], id_key: str, item_id: str) -> dict:
    for item in items:
        if item[id_key] == item_id:
            return item
    raise KeyError(f"Unknown {id_key}: {item_id}")


def get_category(category_id: str) -> dict:
    return _get_by_id(load_categories(), "category_id", category_id)


def get_operation(operation_id: str) -> dict:
    return _get_by_id(load_operations(), "operation_id", operation_id)


def get_parameter(parameter_id: str) -> dict:
    return _get_by_id(load_parameters(), "parameter_id", parameter_id)


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
    categories = load_categories()
    operations = load_operations(include_inactive=True)
    parameters = load_parameters()

    def assert_unique(items: list[dict], key: str, label: str) -> None:
        values = [item.get(key) for item in items]
        duplicates = sorted({value for value in values if values.count(value) > 1})
        if None in values or duplicates:
            raise ValueError(f"Invalid {label} catalog IDs: {duplicates or 'missing ID'}")

    assert_unique(categories, "category_id", "category")
    assert_unique(operations, "operation_id", "operation")
    assert_unique(parameters, "parameter_id", "parameter")
    category_ids = {item["category_id"] for item in categories}
    parameter_ids = {item["parameter_id"] for item in parameters}
    parameter_types = {
        item["parameter_id"]: item.get("value_type")
        for item in parameters
    }
    inventory = json.loads(INVENTORY_FILE.read_text(encoding="utf-8"))
    vendors = {device["vendor"] for device in inventory}

    for operation in operations:
        status = operation.get("status", "active")
        if status not in {"active", "inactive"}:
            raise ValueError(
                f"Operation {operation['operation_id']} has invalid status '{status}'."
            )
        if not isinstance(operation.get("version", 1), int) or operation.get("version", 1) < 1:
            raise ValueError(f"Operation {operation['operation_id']} has an invalid version.")
        if operation.get("category_id") not in category_ids:
            raise ValueError(
                f"Operation {operation['operation_id']} references unknown category "
                f"{operation.get('category_id')}."
            )
        schema_path = Path(__file__).resolve().parents[1] / operation["schema_path"]
        if not schema_path.exists():
            raise ValueError(f"Operation {operation['operation_id']} schema does not exist: {schema_path}")
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        unknown = _schema_parameter_ids(schema) - parameter_ids
        if unknown:
            raise ValueError(
                f"Operation {operation['operation_id']} uses undefined parameter IDs: "
                f"{', '.join(sorted(unknown))}"
            )
        for field, schema_type in _schema_parameter_types(schema).items():
            catalog_type = parameter_types.get(field)
            if catalog_type and schema_type and catalog_type != schema_type:
                raise ValueError(
                    f"Operation {operation['operation_id']} uses type '{schema_type}' for {field}, "
                    f"but the central parameter catalog specifies '{catalog_type}'."
                )
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


def _schema_parameter_ids(schema: dict) -> set[str]:
    names = set(schema.get("properties", {}))
    for property_schema in schema.get("properties", {}).values():
        if property_schema.get("type") == "object":
            names.update(_schema_parameter_ids(property_schema))
        elif property_schema.get("type") == "array":
            names.update(_schema_parameter_ids(property_schema.get("items", {})))
    return names


def _schema_parameter_types(schema: dict) -> dict[str, str]:
    types = {
        field: property_schema.get("type")
        for field, property_schema in schema.get("properties", {}).items()
    }
    for property_schema in schema.get("properties", {}).values():
        if property_schema.get("type") == "object":
            types.update(_schema_parameter_types(property_schema))
        elif property_schema.get("type") == "array":
            types.update(_schema_parameter_types(property_schema.get("items", {})))
    return types
