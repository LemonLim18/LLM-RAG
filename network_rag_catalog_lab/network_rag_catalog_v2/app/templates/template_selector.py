from ..config import TEMPLATES_DIR
from ..catalog import get_operation


def select_template(device: dict, operation_id: str):
    category = get_operation(operation_id)["category_id"]
    path = TEMPLATES_DIR / device["vendor"] / category / operation_id / "template.j2"
    if not path.exists():
        raise FileNotFoundError(
            f"No template for {device['hostname']} / {operation_id}: {path}"
        )
    return path
