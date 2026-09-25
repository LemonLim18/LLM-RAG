from dataclasses import dataclass, field
import ipaddress
import re
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from .fields import leaf_values


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
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(params),
        key=lambda error: str(list(error.path)),
    )
    for error in errors:
        path = ""
        for part in error.path:
            path += f"[{part}]" if isinstance(part, int) else ("." if path else "") + part
        path = path or "<root>"
        if error.validator == "required" or any(issue.field == path and issue.type == "MISSING" for issue in issues):
            continue
        issues.append(
            ValidationIssue(
                type="SCHEMA",
                field=path,
                message=error.message,
            )
        )
    issues.extend(_network_value_issues(params))
    interface_items = params.get("interfaces")
    if isinstance(interface_items, list):
        seen_names = set()
        for index, item in enumerate(interface_items):
            if not isinstance(item, dict) or not isinstance(item.get("name"), str):
                continue
            name = item["name"].casefold()
            if name in seen_names:
                issues.append(ValidationIssue("CONFLICT", f"interfaces[{index}].name", "Each interface must appear only once in this operation."))
            seen_names.add(name)
    for path, value in leaf_values(params):
        if isinstance(value, str) and (any(ord(ch) < 32 or ord(ch) == 127 for ch in value) or any(ch in value for ch in ';{}"\\')):
            issues.append(ValidationIssue("UNSAFE_VALUE", path, "Control characters and configuration delimiters are not permitted."))
        field = path.rsplit(".", 1)[-1]
        if field == "area" and value is not None:
            try:
                if not isinstance(value, str):
                    raise ValueError
                if value.isdigit():
                    if not 0 <= int(value) <= 4294967295:
                        raise ValueError
                else:
                    ipaddress.IPv4Address(value)
            except ValueError:
                issues.append(ValidationIssue("NETWORK_VALUE", path, "OSPF area must be a 32-bit unsigned decimal or dotted IPv4 value."))
        if field in {"name", "peer_group", "process_name"} and isinstance(value, str) and not re.fullmatch(r"[A-Za-z0-9_./:-]+", value):
            issues.append(ValidationIssue("NETWORK_VALUE", path, "Use an identifier without spaces or configuration punctuation."))
    return ValidationResult(valid=not issues, issues=issues)


def _network_value_issues(params: dict) -> list[ValidationIssue]:
    """Validate network literals independently of LLM output and templates."""
    issues = []
    for field in ("address", "neighbor_ip", "next_hop", "router_id"):
        value = params.get(field)
        if value in (None, ""):
            continue
        try:
            address = ipaddress.IPv4Address(value)
            masks = {str(ipaddress.IPv4Network(f"0.0.0.0/{prefix}").netmask) for prefix in range(33)}
            if not isinstance(value, str) or address.is_unspecified or address.is_multicast or address.is_reserved or address.is_loopback or str(address) in masks:
                raise ValueError
        except (ValueError, TypeError):
            issues.append(ValidationIssue("NETWORK_VALUE", field, f"'{value}' is not a valid IPv4 address."))
    if isinstance(params.get("prefix_length"), int) and isinstance(params.get("address"), str):
        try:
            interface = ipaddress.IPv4Interface(f"{params['address']}/{params['prefix_length']}")
            if interface.network.prefixlen < 31 and interface.ip in {interface.network.network_address, interface.network.broadcast_address}:
                issues.append(ValidationIssue("NETWORK_VALUE", "address", "Address is the network or broadcast address for this prefix."))
        except ValueError:
            pass
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
