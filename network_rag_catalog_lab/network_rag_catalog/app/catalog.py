import json
from .config import CATALOG_FILE,CATEGORIES_FILE

def load_categories(): return json.loads(CATEGORIES_FILE.read_text())
def load_operations(): return json.loads(CATALOG_FILE.read_text())
def get_operation(operation_id):
    for x in load_operations():
        if x['operation_id']==operation_id:return x
    raise KeyError(operation_id)
