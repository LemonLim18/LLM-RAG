import json
from .config import INVENTORY_FILE

# Retrieve the inventory of target devices in JSON format
def get_devices(names):
    data=json.loads(INVENTORY_FILE.read_text()); 
    # for each entry inside the devices.json, create a dictionary with the hostname (r1) as the key (since x['hostname'].lower()) and the :x as the value which contains the actual entry of the device
    index={x['hostname'].lower():x for x in data} # contains all the device information
    missing=[n for n in names if n.lower() not in index]
    if missing: 
        raise KeyError(f'Missing devices: {missing}')
    return [index[n.lower()] for n in names]
