import ipaddress
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from .template_selector import select_template


def _prepare_context(params: dict) -> dict:
    context = dict(params)
    # Optional values are explicitly present so StrictUndefined remains useful.
    for key in ("router_id", "description", "preference", "admin_up", "name"):
        context.setdefault(key, None)
    if "prefix_length" in context:
        context["netmask"] = str(ipaddress.IPv4Network(f"0.0.0.0/{context['prefix_length']}").netmask)
    return context


def render(device: dict, operation_id: str, params: dict) -> str:
    path = select_template(device, operation_id)
    env = Environment(
        loader=FileSystemLoader(str(path.parent)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return env.get_template("template.j2").render(**_prepare_context(params)).strip() + "\n"
