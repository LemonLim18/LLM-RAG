"""Scoped local context lookups and revision tracking for clarification evidence."""

from hashlib import sha256
import json
import re

from .catalog import get_operation, load_operations
from .config import DATA_DIR
from .devices.context_validator import normalize_parameters_for_device, validate_device_context
from .devices.inventory import load_inventory
from .parameters.fields import get_value, schema_at, set_value
from .parameters.schema_loader import load_schema
from .parameters.validator import validate_parameter_result


def source_revision() -> str:
    digest = sha256()
    for path in sorted(DATA_DIR.rglob("*")):
        if path.is_file() and path.suffix in {".json", ".j2"}:
            digest.update(str(path.relative_to(DATA_DIR)).encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()[:20]


def rules() -> dict:
    return json.loads((DATA_DIR / "catalog" / "context_rules.json").read_text(encoding="utf-8"))


def canonical_path(path: str) -> str:
    return re.sub(r"\[\d+\]", "[]", path)


def matching_records(operation: str, device: dict, path: str, params: dict) -> list[dict]:
    spec = rules()["operations"].get(operation, {})
    if canonical_path(path) not in spec.get("planned_fields", []):
        return []
    records = json.loads((DATA_DIR / "planned" / "parameters.json").read_text(encoding="utf-8"))["records"]
    result = []
    for record in records:
        if (record["device_id"], record["operation_id"], record["field"]) != (device["id"], operation, canonical_path(path)):
            continue
        dependencies = record.get("when", {})
        def scoped(dependency):
            index = re.search(r"\[(\d+)\]", path)
            return dependency.replace("[]", f"[{index.group(1)}]" if index else "[]")
        if all(get_value(params, scoped(key)) == value for key, value in dependencies.items()):
            result.append(record)
    return result


def candidate_valid(operation: str, device: dict, path: str, value, params: dict) -> bool:
    schema = load_schema(operation, [device])
    proposed = normalize_parameters_for_device(set_value(params, path, value), device)
    issues = [vars(issue) for issue in validate_parameter_result(proposed, schema).issues]
    issues += validate_device_context(operation, get_operation(operation)["category_id"], proposed, [device])
    return not any(issue["type"] != "MISSING" and (issue["field"] == path or issue["field"].startswith(path + "[") or issue["field"].startswith(path + ".")) for issue in issues)


def parameter_options(operation: str, device: dict, path: str, params: dict, revision: str) -> list[dict]:
    choices = []
    permitted = rules()["operations"].get(operation, {})
    if canonical_path(path) in permitted.get("inventory_fields", []):
        for item in device.get("interfaces", []):
            value = [{"name": item["name"]}] if path == "interfaces" else item["name"]
            choices.append({"value": value, "label": f"{item['name']} ({item.get('role', 'interface')})",
                            "source_ref": f"inventory:{device['id']}:interfaces:{item['name']}",
                            "source_revision": revision, "explanation": "Recorded interface on this device.", "kind": "fact"})
    for record in matching_records(operation, device, path, params):
        choices.append({"value": record["value"], "label": str(record["value"]),
                        "source_ref": record["source_ref"], "source_revision": str(record["revision"]),
                        "record_id": record["id"], "explanation": "Confirm recorded " + record["kind"] + ".", "kind": record["kind"]})
    return [choice for choice in choices if candidate_valid(operation, device, path, choice["value"], params)]


def context_conflicts(operation: str, device: dict, params: dict, confirmations: dict, revision: str) -> list[dict]:
    from .parameters.fields import leaf_values
    issues = []
    for path, value in leaf_values(params):
        if value is None:
            continue
        planned = [record for record in matching_records(operation, device, path, params) if record["kind"] in {"fact", "intended_assignment"}]
        if not planned or all(record["value"] == value for record in planned):
            continue
        if confirmations.get(path) == {"value": value, "source_revision": revision} and all(record["kind"] != "fact" for record in planned):
            continue
        issues.append({"type": "CONTEXT_CONFLICT", "field": path, "value": value,
                       "allow_override": rules()["operations"].get(operation, {}).get("allow_plan_override", False) and all(record["kind"] != "fact" for record in planned),
                       "message": f"{path}={value} differs from recorded context ({', '.join(str(record['value']) for record in planned)}). Confirm a planned value or explicitly confirm your proposed change."})
    return issues


def validate_context_catalog() -> None:
    configuration = rules()
    devices = {device["id"]: device for device in load_inventory()}
    operations = {operation["operation_id"]: operation for operation in load_operations(include_inactive=True)}
    for operation, rule in configuration["operations"].items():
        if operation not in operations or any(other not in operations for other in rule.get("conflicts_with", [])):
            raise ValueError(f"Unknown operation in context rules: {operation}")
        if operations[operation].get("status", "active") != "active":
            continue
        schema = load_schema(operation)
        for path in rule.get("inventory_fields", []) + rule.get("planned_fields", []):
            schema_at(schema, path.replace("[]", "[0]"))
    records = json.loads((DATA_DIR / "planned" / "parameters.json").read_text(encoding="utf-8"))["records"]
    seen = set()
    for record in records:
        if not {"id", "device_id", "operation_id", "field", "value", "source_ref", "revision", "kind"} <= record.keys():
            raise ValueError("Planned record is missing required source or scope fields.")
        if record["id"] in seen or record["kind"] not in {"fact", "candidate", "intended_assignment"}:
            raise ValueError(f"Invalid planned record: {record['id']}")
        seen.add(record["id"])
        if type(record["revision"]) is not int or record["revision"] < 1 or not record["source_ref"]:
            raise ValueError(f"Invalid planned source: {record['id']}")
        device = devices[record["device_id"]]
        operation = record["operation_id"]
        if operation not in operations:
            raise ValueError(f"Unknown planned operation: {operation}")
        if operations[operation].get("status", "active") != "active":
            continue
        if record["field"] not in configuration["operations"].get(operation, {}).get("planned_fields", []):
            raise ValueError(f"Unapproved planned lookup: {record['id']}")
        params = {}
        schema = load_schema(operation, [device])
        for dependency, value in record.get("when", {}).items():
            path = dependency.replace("[]", "[0]")
            schema_at(schema, path)
            params = set_value(params, path, value)
        path = record["field"].replace("[]", "[0]")
        if not candidate_valid(operation, device, path, record["value"], params):
            raise ValueError(f"Invalid planned value: {record['id']}")
        dependency_issues = validate_parameter_result(params, schema).issues
        if any(issue.type != "MISSING" for issue in dependency_issues) or validate_device_context(operation, operations[operation]["category_id"], params, [device]):
            raise ValueError(f"Invalid planned dependencies: {record['id']}")
