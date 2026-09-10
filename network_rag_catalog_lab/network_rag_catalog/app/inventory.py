import json
from .config import INVENTORY_FILE

def get_devices(names):
    data=json.loads(INVENTORY_FILE.read_text()); index={x['hostname'].lower():x for x in data}
    missing=[n for n in names if n.lower() not in index]
    if missing: raise KeyError(f'Missing devices: {missing}')
    return [index[n.lower()] for n in names]
