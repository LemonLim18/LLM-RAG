import json
from ..config import BASE_DIR, DATA_DIR, TEMPLATES_DIR, TEMPLATE_BINDINGS_FILE
from ..catalog import get_operation
from ..knowledge.models import TemplateBinding
from ..knowledge.runtime import current_snapshot, safe_path, snapshot_request


def template_binding(device: dict, operation_id: str):
    snapshot = current_snapshot()
    if snapshot:
        return snapshot.binding(device, operation_id)
    from ..config import runtime_mode
    if runtime_mode() == "files":
        # Direct template paths are the lab contract; no binding entity needed.
        return None
    operation = get_operation(operation_id)
    knowledge = operation.get("vendor_knowledge", {}).get(device["vendor"], {})
    if knowledge.get("status") == "blocked_unverified":
        raise ValueError(f"No declared template compatibility for {operation_id} / {device['vendor']}. "
                         f"Intent recognized; configuration generation blocked: {knowledge['reason']}")
    if operation.get("schema_source") != "registry":
        return None
    for raw in json.loads(TEMPLATE_BINDINGS_FILE.read_text(encoding="utf-8")):
        binding = TemplateBinding.model_validate(raw)
        if (binding.operation_id == operation_id and binding.operation_version == operation.get("version", 1)
                and binding.vendor == device["vendor"] and binding.platform == device["platform"]
                and str(device["version"]) in binding.versions):
            return binding.model_dump()
    raise ValueError(f"No declared template compatibility for {operation_id} / {device['vendor']} {device['platform']} {device['version']}.")


@snapshot_request
def select_template(device: dict, operation_id: str):
    binding = template_binding(device, operation_id)
    if binding:
        snapshot = current_snapshot()
        path = safe_path(snapshot.root, binding["artifact_path"]) if snapshot else safe_path(BASE_DIR, binding["template_path"])
        if not path.is_file():
            raise FileNotFoundError(f"Declared template is missing: {path}")
        return path
    from ..config import runtime_mode
    if current_snapshot() is None and runtime_mode() == "files":
        operation = get_operation(operation_id)
        path = safe_path(TEMPLATES_DIR, f"{device['vendor']}/{operation['category_id']}/{operation_id}/template.j2")
        if not path.is_file():
            raise ValueError(f"No reviewed template for {operation_id} / {device['vendor']}. "
                             "The intent is available to RAG, but configuration generation is not implemented for this vendor.")
        return path
    support = json.loads((DATA_DIR / "catalog" / "template_support.json").read_text(encoding="utf-8"))["vendors"]
    versions = support.get(device["vendor"], {}).get("platforms", {}).get(device["platform"], [])
    if str(device["version"]) not in versions:
        raise ValueError(f"No declared template compatibility for {device['vendor']} {device['platform']} {device['version']}.")
    category = get_operation(operation_id)["category_id"]
    path = TEMPLATES_DIR / device["vendor"] / category / operation_id / "template.j2"
    if not path.exists():
        raise FileNotFoundError(
            f"No template for {device['hostname']} / {operation_id}: {path}"
        )
    return path
