from .category_classifier import classify_category
from .operation_retriever import retrieve_operation_candidates
from .operation_selector import select_operation
from .schema_loader import load_schema
from .parameter_extractor import extract_parameters
from .validator import validate_parameters
from .inventory import get_devices
from .renderer import render

def run(prompt,targets):
    print('\n[1] CATEGORY CLASSIFICATION'); category=classify_category(prompt); print('    ',category)
    print('\n[2] CHROMADB OPERATION RETRIEVAL'); candidates=retrieve_operation_candidates(prompt,category,3)
    for x in candidates: print(f"    {x['operation_id']} | score={x['score']:.4f}")
    if not candidates: raise ValueError('No operation candidates')
    print('\n[3] OPERATION SELECTION'); operation=select_operation(prompt,category,candidates); print('    ',operation)
    print('\n[4] SCHEMA RETRIEVAL'); schema=load_schema(operation); print('    operation:', schema.get('operation', operation)); print('    parameters:', list(schema.get('parameters', {}).keys()))
    print('\n[5] PARAMETER EXTRACTION'); params=extract_parameters(prompt,schema); print('    ',params)
    print('\n[6] SCHEMA VALIDATION'); validate_parameters(params,schema); print('    PASSED')
    print('\n[7] LOCAL INVENTORY + DETERMINISTIC TEMPLATE SELECTION'); devices=get_devices(targets)
    for d in devices: print(f"    {d['hostname']} -> {d['vendor']}/{d['platform']}/{d['version']}")
    print('\n[8] RENDERED CONFIGURATION')
    for d in devices: print(f"\n--- {d['hostname']} ---\n{render(d,operation,params)}")
