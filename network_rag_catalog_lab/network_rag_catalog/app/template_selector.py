from pathlib import Path
from .config import TEMPLATES_DIR
from .catalog import get_operation

def select_template(device,operation_id):
    category=get_operation(operation_id)['category']
    p=TEMPLATES_DIR/device['vendor']/category/operation_id/'template.j2'
    if not p.exists(): raise FileNotFoundError(f'No template for {device} / {operation_id}: {p}')
    return p
