from pathlib import Path
from .config import TEMPLATES_DIR
from .catalog import get_operation

# This is used to pick the correct jinja template file for a given device to be filled out with parameters
def select_template(device,operation_id):
    # get the desired operation's category from the catalog
    category=get_operation(operation_id)['category']
    # construct the path to the template file based on the DATA_DIR/templates/template/{vendor}/{category}/{operations_id}/template.j2 
    p=TEMPLATES_DIR/device['vendor']/category/operation_id/'template.j2'
    if not p.exists(): 
        raise FileNotFoundError(f'No template for {device} / {operation_id}: {p}')
    return p
