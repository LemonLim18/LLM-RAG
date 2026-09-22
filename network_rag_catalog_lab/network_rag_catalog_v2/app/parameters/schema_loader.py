import json
from pathlib import Path
from ..catalog import get_operation


def load_schema(operation_id: str):
    path = Path(__file__).resolve().parents[2] / get_operation(operation_id)["schema_path"]
    return json.loads(path.read_text())
