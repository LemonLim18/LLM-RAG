import json
from pathlib import Path
from .catalog import get_operation

def load_schema(operation_id):
    # Get to the directory: network_rag_catalog/ then retrieve the schema_path field value from the operations.json file using the get_operation function using the operation_id deduced
    # For example, if operation_id is "configure_ospf", the get_operation function will return the schema path: /data/operations/ospf/configure_ospf/schema.json from the operations.json file
    # With that, the p = network_rag_catalog/data/operations/ospf/configure_ospf/schema.json
    p=Path(__file__).resolve().parents[1]/get_operation(operation_id)['schema_path']
    # Then, this will read the schema.json file at the path p and return the content as a dictionary
    return json.loads(p.read_text())


# The returned schema dict helps to define what parameters are expected (required and optional)
# as well as the constraint properties of each parameters