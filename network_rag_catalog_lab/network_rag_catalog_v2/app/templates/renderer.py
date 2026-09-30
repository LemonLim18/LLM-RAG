import ipaddress
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from .template_selector import select_template, template_binding
from ..knowledge.rule_registry import derive_template_value
from ..knowledge.runtime import snapshot_request


def _prepare_context(params: dict, contract: dict | None = None) -> dict:
    context = dict(params)
    if contract is not None:
        for key, value in contract["optional_defaults"].items():
            context.setdefault(key, value)
        for key, handler in contract["derived"].items():
            context[key] = derive_template_value(handler, context)
        return context
    # Optional values are explicitly present so StrictUndefined remains useful.
    for key in ("router_id", "description", "preference", "admin_up", "name"):
        context.setdefault(key, None)
    if "prefix_length" in context:
        context["netmask"] = str(ipaddress.IPv4Network(f"0.0.0.0/{context['prefix_length']}").netmask)
    return context


@snapshot_request
def render(device: dict, operation_id: str, params: dict) -> str:
    path = select_template(device, operation_id)
    binding = template_binding(device, operation_id)
    contract = binding["input_contract"] if binding else None
    from ..config import runtime_mode
    from ..knowledge.runtime import current_snapshot
    if current_snapshot() is None and runtime_mode() == "files":
        from ..parameters.schema_loader import load_schema
        from ..parameters.validator import validate_parameter_result
        from ..knowledge.rule_registry import TEMPLATE_DERIVATIONS
        schema = load_schema(operation_id, [device])
        validate_parameter_result(params, schema).raise_for_errors()
        contract = {"optional_defaults": {key: None for key in schema["properties"] if key not in schema["required"]},
                    "derived": {key: spec[0] for key, spec in TEMPLATE_DERIVATIONS.items() if spec[1] in params}}
    env = Environment(
        loader=FileSystemLoader(str(path.parent)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return env.get_template(path.name).render(**_prepare_context(params, contract)).strip() + "\n"
