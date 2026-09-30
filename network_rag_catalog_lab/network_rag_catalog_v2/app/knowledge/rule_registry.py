"""Code-reviewed handler IDs only; catalog data can never import Python code."""

from collections.abc import Callable
from ..parameters.expansion_rules import network_rules

VALIDATION_HANDLERS = ("network_values_v1", "unique_interfaces_v1", "safe_strings_v1")
# Extend only in reviewed Python code, never through catalog-supplied import paths.
# Additional callbacks receive (parameters, schema) and return ValidationIssue lists.
ADDITIONAL_VALIDATION_HANDLERS: dict[str, Callable[[dict, dict], list]] = {"expansion_network_v1": network_rules}
NORMALIZATION_HANDLERS = {"ipv4_prefix_length"}

# Output identity, handler and required input are all code-owned.
TEMPLATE_DERIVATIONS = {
    "dscp_codepoints": ("dscp_codepoints_v1", "dscp_values"),
    "huawei_members": ("huawei_members_v1", "member_interfaces"),
    "netmask": ("ipv4_netmask_v1", "prefix_length"),
    "destination_address": ("destination_address_v1", "destination"),
    "destination_mask": ("destination_mask_v1", "destination"),
    "network_address": ("network_address_v1", "network_prefix"),
    "network_wildcard": ("network_wildcard_v1", "network_prefix"),
    "source_address": ("acl_source_address_v1", "source_prefix"),
    "source_wildcard": ("acl_source_wildcard_v1", "source_prefix"),
    "acl_destination_address": ("acl_destination_address_v1", "destination_prefix"),
    "acl_destination_wildcard": ("acl_destination_wildcard_v1", "destination_prefix"),
}


def validate_object_requirements(schema):
    from jsonschema import Draft202012Validator
    from .models import ConditionalRequirement
    properties = schema.get("properties", {})
    conditions = schema.get("x-conditional-required", [])
    dependencies = schema.get("dependentRequired", {})
    if (conditions or dependencies) and schema.get("type") != "object":
        raise ValueError("Conditional requirements belong on an object schema.")
    if not isinstance(conditions, list):
        raise ValueError("x-conditional-required must be an array of reviewed conditions.")
    if not isinstance(dependencies, dict):
        raise ValueError("dependentRequired must be an object of field-name arrays.")
    for raw in conditions:
        rule = ConditionalRequirement.model_validate(raw)
        if rule.field not in properties or any(name not in properties for name in rule.required):
            raise ValueError("Conditional requirement references an undefined local property.")
        if len(set(rule.required)) != len(rule.required) or not Draft202012Validator(properties[rule.field]).is_valid(rule.equals):
            raise ValueError("Invalid conditional required fields or comparison value.")
    for field, required in dependencies.items():
        if (not isinstance(required, list) or any(not isinstance(name, str) for name in required)
                or len(set(required)) != len(required)):
            raise ValueError("dependentRequired values must be unique field-name arrays.")
        if field not in properties or any(name not in properties for name in required):
            raise ValueError("dependentRequired references an undefined property.")


def required_fields(schema, params):
    from jsonschema import Draft202012Validator
    required = list(schema.get("required", []))
    for field, dependencies in schema.get("dependentRequired", {}).items():
        if field in params:
            required.extend(dependencies)
    for rule in schema.get("x-conditional-required", []):
        if rule["field"] in params and Draft202012Validator({"const": rule["equals"]}).is_valid(params[rule["field"]]):
            required.extend(rule["required"])
    return list(dict.fromkeys(required))


def normalize_prefix(value, prompt):
    from ..parameters.normalizer import prefix_length_from_text
    explicit = prefix_length_from_text(prompt)
    if explicit is None:
        return None, None
    try:
        candidate = int(value)
    except (TypeError, ValueError):
        candidate = explicit
    if candidate != explicit:
        return None, None
    return explicit, "derived_from_user_netmask" if "mask" in prompt.lower() else "user"


def validate_handler_ids(schema: dict) -> list[str]:
    handlers = schema.get("x-validation-handlers", list(VALIDATION_HANDLERS))
    if not isinstance(handlers, list) or any(not isinstance(value, str) for value in handlers):
        raise ValueError("Validation handlers must be a list of registered IDs.")
    mandatory = set(VALIDATION_HANDLERS)
    additional = set(ADDITIONAL_VALIDATION_HANDLERS)
    if mandatory & additional or any(not callable(handler) for handler in ADDITIONAL_VALIDATION_HANDLERS.values()):
        raise ValueError("Additional validation handlers cannot replace mandatory handlers and must be callable.")
    if (len(set(handlers)) != len(handlers) or not mandatory <= set(handlers)
            or set(handlers) - mandatory - additional):
        raise ValueError("Unknown or missing mandatory validation handler.")
    return handlers


def validation_issues(params: dict, schema: dict) -> list:
    from ..parameters.validator import _network_value_issues, _unique_interface_issues, _safe_string_issues

    handlers = dict(zip(VALIDATION_HANDLERS, (_network_value_issues, _unique_interface_issues, _safe_string_issues)))
    issues = []
    for name in validate_handler_ids(schema):
        issues.extend(handlers[name](params) if name in handlers else ADDITIONAL_VALIDATION_HANDLERS[name](params, schema))
    return issues


def derive_template_value(handler: str, params: dict):
    spec = next(((name, source) for name, (registered, source) in TEMPLATE_DERIVATIONS.items() if registered == handler), None)
    if spec is None:
        raise ValueError(f"Unknown template derivation: {handler}")
    import ipaddress
    name, source = spec
    if handler == "dscp_codepoints_v1":
        return [format(value, "06b") for value in params[source]]
    if handler == "huawei_members_v1":
        import re
        return [re.sub(r"^(10GE|25GE|40GE|100GE|GE|GigabitEthernet|Eth-Trunk)([0-9])", r"\1 \2", value)
                for value in params[source]]
    network = ipaddress.IPv4Network(f"0.0.0.0/{params[source]}" if source == "prefix_length" else params[source], strict=True)
    return str(network.hostmask if name.endswith("wildcard") else network.netmask if name.endswith("mask") else network.network_address)
