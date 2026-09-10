import json
from pathlib import Path
from .catalog import get_operation

def load_schema(operation_id):
    p=Path(__file__).resolve().parents[1]/get_operation(operation_id)['schema_path']
    return json.loads(p.read_text())
