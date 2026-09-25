import json
from ..config import DATA_DIR, TEMPLATES_DIR
from ..catalog import get_operation


def select_template(device: dict, operation_id: str):
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
