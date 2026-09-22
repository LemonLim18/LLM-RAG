# The orchestrator for RAG-based network operation. Integrate components like category
# classifier, operation retriever, operation selector, schema loader, parameter extractor,
# validator, inventory, and renderer to process a network operation request.
from .category_classifier import classify_category
from .operation_retriever import retrieve_operation_candidates
from .operation_selector import select_operation
from .schema_loader import load_schema
from .parameter_extractor import extract_parameters
from .validator import validate_parameters
from .inventory import get_devices
from .renderer import render

# Parameters: Prompt request & Target devices list.
# Returns: None. Prints each step's output to the console.
def run(prompt,targets):
    # Step 1: Classify the category of the network operation prompt & return category.
    # Input: prompt // Output: category
    print('\n[1] CATEGORY CLASSIFICATION'); category=classify_category(prompt); print('    ',category)


    # Step 2: Retrieve top-3 operation candidates from the RAG catalog based on the prompt and category.
    # Input: prompt, category, top_k // Output: list of candidates (field info: operation_id, category, description, score)
    print('\n[2] CHROMADB OPERATION RETRIEVAL'); candidates=retrieve_operation_candidates(prompt,category,3)
    for x in candidates: print(f"    {x['operation_id']} | score={x['score']:.4f}")     # Print the top-3 candidates with their operation_id and score. Raise an error if no candidates are found.
    if not candidates: raise ValueError('No operation candidates')


    # Step 3: Select the best operation from candidates based on the prompt, category and candidates list.
    # Input: prompt, category, candidates // Output: selected operation_id
    print('\n[3] OPERATION SELECTION'); operation=select_operation(prompt,category,candidates); print('    ',operation)


    # Step 4: Load the schema for the selected operation from the RAG catalog. 
    # Input: operation_id // Output: Return that specific operation schema dict under the schema path 
    print('\n[4] SCHEMA RETRIEVAL'); schema=load_schema(operation); print('    operation:', schema.get('operation', operation)); print('    parameters:', list(schema.get('parameters', {}).keys()))


    # Step 5: Extract parameters from the prompt based on the schema. 
    # Inputs: prompt, schema // Output: Params to be filled inside the template
    print('\n[5] PARAMETER EXTRACTION'); params=extract_parameters(prompt,schema); print('    ',params)


    # Step 6: Validate the extracted parameters against the schema. 
    # Inputs: params, schema // Output: None
    print('\n[6] SCHEMA VALIDATION'); validate_parameters(params,schema); print('    PASSED')


    # Step 7: Retrieve the detailed information of the target devices from the local inventory based on the provided target device names 
    # Input: targets // Output: list of selected devices with their info
    print('\n[7] LOCAL INVENTORY + DETERMINISTIC TEMPLATE SELECTION'); devices=get_devices(targets)
    for d in devices: print(f"    {d['hostname']} -> {d['vendor']}/{d['platform']}/{d['version']}")


    # Step 8: Render the configuration for each device based on the operation and parameters. 
    # Input: device list, operation, params // Output: Rendered configuration
    print('\n[8] RENDERED CONFIGURATION')
    # For each device, find the config template based on operation and device(used for vendor identification), and fill out with the parameters
    for d in devices: print(f"\n--- {d['hostname']} ---\n{render(d,operation,params)}")
