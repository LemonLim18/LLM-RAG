from dataclasses import dataclass, field
import ipaddress
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


@dataclass
class ValidationIssue:
    type: str
    field: str
    message: str


@dataclass
class ValidationResult:
    valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)

    def raise_for_errors(self) -> None:
        if self.valid:
            return
        lines = [f"- {issue.field}: {issue.message}" for issue in self.issues]
        raise ValueError("Schema validation failed:\n" + "\n".join(lines))


def _is_missing(value: Any) -> bool:
    return value is None or value == "" or value == []


def _find_missing_required(params: Any, schema: dict, path: str = "") -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if schema.get("type") != "object" or not isinstance(params, dict):
        return issues

    properties = schema.get("properties", {})
    for field in schema.get("required", []):
        field_path = f"{path}.{field}" if path else field
        if field not in params or _is_missing(params.get(field)):
            issues.append(
                ValidationIssue(
                    type="MISSING",
                    field=field_path,
                    message=f"Required parameter '{field_path}' was not specified.",
                )
            )

    for field, value in params.items():
        subschema = properties.get(field)
        if not subschema:
            continue
        field_path = f"{path}.{field}" if path else field
        if subschema.get("type") == "object":
            issues.extend(_find_missing_required(value, subschema, field_path))
        elif subschema.get("type") == "array" and isinstance(value, list):
            item_schema = subschema.get("items", {})
            for index, item in enumerate(value):
                issues.extend(_find_missing_required(item, item_schema, f"{field_path}[{index}]"))
    return issues


def validate_parameter_result(params: dict, schema: dict) -> ValidationResult:
    issues = _find_missing_required(params, schema)
    if issues:
        return ValidationResult(valid=False, issues=issues)

    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(params),
        key=lambda error: list(error.path),
    )
    for error in errors:
        path = ".".join(map(str, error.path)) or "<root>"
        issues.append(
            ValidationIssue(
                type="SCHEMA",
                field=path,
                message=error.message,
            )
        )
    issues.extend(_network_value_issues(params))
    return ValidationResult(valid=not issues, issues=issues)


def _network_value_issues(params: dict) -> list[ValidationIssue]:
    """Validate network literals independently of LLM output and templates."""
    issues = []
    for field in ("address", "neighbor_ip", "next_hop", "router_id"):
        value = params.get(field)
        if value in (None, ""):
            continue
        try:
            ipaddress.ip_address(value)
        except ValueError:
            issues.append(ValidationIssue("NETWORK_VALUE", field, f"'{value}' is not a valid IPv4 address."))
    destination = params.get("destination")
    if destination not in (None, ""):
        try:
            network = ipaddress.ip_network(destination, strict=False)
            if network.version != 4 or "/" not in str(destination):
                raise ValueError
        except ValueError:
            issues.append(
                ValidationIssue("NETWORK_VALUE", "destination", f"'{destination}' is not a valid IPv4 prefix.")
            )
    return issues


def validate_parameters(params: dict, schema: dict) -> None:
    validate_parameter_result(params, schema).raise_for_errors()
