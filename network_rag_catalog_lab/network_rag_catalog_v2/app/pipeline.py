from dataclasses import asdict
import json

from .planner.intent_planner import plan_intents
from .planner.models import ExecutionPlan, PlannedTask
from .retrieval.category_classifier import classify_category
from .retrieval.operation_retriever import retrieve_operation_candidates
from .retrieval.operation_selector import select_operation
from .parameters.schema_loader import load_schema
from .parameters.parameter_extractor import extract_parameters
from .parameters.validator import validate_parameters
from .devices.inventory import load_inventory
from .devices.target_resolver import resolve_intent_targets
from .templates.renderer import render


def _discover_explicit_targets(text: str) -> list[str]:
    """Recover inventory references that the planner may have omitted.

    This is intentionally not fuzzy guessing. We only look for exact normalized
    hostname/display-name/alias strings that are already present in inventory.
    """
    import re
    inventory = load_inventory()
    normalized = re.sub(r"[^a-z0-9]+", " ", text.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    matches = []
    for device in inventory:
        candidates = [device.get("hostname", ""), device.get("display_name", "")]
        candidates += device.get("aliases", [])
        for candidate in candidates:
            c = re.sub(r"[^a-z0-9]+", " ", str(candidate).lower())
            c = re.sub(r"\s+", " ", c).strip()
            if c and re.search(rf"(?<![a-z0-9]){re.escape(c)}(?![a-z0-9])", normalized):
                matches.append(device["hostname"])
                break
    return list(dict.fromkeys(matches))


def _process_intent(intent, index: int) -> PlannedTask:
    print(f"\n{'=' * 72}\nINTENT {index}: {intent.request_text}\n{'=' * 72}")

    print("\n[1] CATEGORY CLASSIFICATION")
    category = classify_category(intent.request_text)
    print("    ", category)

    print("\n[2] CHROMADB OPERATION RETRIEVAL")
    candidates = retrieve_operation_candidates(intent.request_text, category, 3)
    for candidate in candidates:
        print(f"    {candidate['operation_id']} | distance={candidate['distance']:.4f}")
    if not candidates:
        raise ValueError(f"No operation candidates for intent {intent.intent_id}")

    print("\n[3] OPERATION SELECTION")
    operation = select_operation(intent.request_text, category, candidates)
    print("    ", operation)

    print("\n[4] SCHEMA RETRIEVAL")
    schema = load_schema(operation)
    print("    ", schema.get("title", operation))

    print("\n[5] PARAMETER EXTRACTION")
    params = extract_parameters(intent.request_text, schema)
    print("    ", json.dumps(params, indent=2))

    print("\n[6] SCHEMA VALIDATION")
    validate_parameters(params, schema)
    print("    PASSED")

    target_refs = intent.target_refs or _discover_explicit_targets(intent.request_text)
    print("\n[7] TARGET RESOLUTION")
    print("    references:", target_refs)
    devices = resolve_intent_targets(target_refs)
    for device in devices:
        print(
            f"    {device['hostname']} -> "
            f"{device['vendor']}/{device['platform']}/{device['version']}"
        )

    print("\n[8] DETERMINISTIC TEMPLATE SELECTION + RENDERING")
    configs = []
    for device in devices:
        config = render(device, operation, params)
        configs.append({
            "device_id": device["hostname"],
            "vendor": device["vendor"],
            "platform": device["platform"],
            "version": device["version"],
            "configuration": config,
        })
        print(f"\n--- {device['hostname']} ({device['vendor']}) ---\n{config}")

    return PlannedTask(
        intent_id=intent.intent_id,
        request_text=intent.request_text,
        category=category,
        operation_id=operation,
        parameters=params,
        target_refs=target_refs,
        target_devices=devices,
        configs=configs,
    )


def run(prompt: str) -> ExecutionPlan:
    """Plan and render a complete multi-operation, multi-device request.

    This function deliberately stops before device execution. Its output is an
    execution-ready plan that can later feed an approval gate and Ansible runner.
    """
    print("\n" + "#" * 72)
    print("REQUEST")
    print(prompt)
    print("#" * 72)

    print("\n[0] INTENT PLANNING")
    # plan_intents() basically split the prompt into multiple intents, each intent is a logical operation with its own request_text and target_refs. The planner will return a list of OperationIntent objects, each representing an independent network operation intent.
    intents = plan_intents(prompt)
    # Output: List of OperationIntent objects
    for intent in intents:
        print(f"    {intent.intent_id}: {intent.request_text}")
        print(f"    targets: {intent.target_refs or '[planner found none]'}")

    if not intents:
        raise ValueError("The planner produced no operation intents.")

    # ExectionPlan is a constructor that creates an ExecutionPlan container with the original prompt and the list of intents.
    plan = ExecutionPlan(original_prompt=prompt, intents=intents)

    # __process_intent() is a function that takes an OperationIntent object and an index, and returns a PlannedTask object. It performs the following steps for each intent:
    # 1. Classify the category of the intent's request_text.
    # 2. Retrieve operation candidates from the RAG catalog based on the intent's request
    # 3. Select the best operation from the candidates.
    # 4. Load the schema for the selected operation.
    # 5. Extract parameters from the intent's request_text based on the schema.
    # 6. Validate the extracted parameters against the schema.
    # 7. Resolve the target devices based on the intent's target_refs.
    # 8. Render the configuration for each device based on the operation and parameters.
    # The resulting PlannedTask object is appended to the ExecutionPlan's tasks list.
    # _process_intent() is the core function from the v1 pipeline.py, now we just call it sequentially 
    for index, intent in enumerate(intents, 1):
        plan.tasks.append(_process_intent(intent, index))
    # Together with intent sequence, the index is inputted as 1,2,3 ... to the _process_intent() function
    # The final output is an ExecutionPlan object with the PlannedTask object for each intent appended as the task list.

    print("\n" + "#" * 72)
    print("EXECUTION PLAN READY — NO DEVICE CHANGES HAVE BEEN MADE")
    print("#" * 72)
    print(json.dumps(plan_to_dict(plan), indent=2))
    return plan


"""
ExecutionPlan will look like this:

ExecutionPlan
│
├── original_prompt
│     └── "Create VLAN 100 ... OSPF on R2"
│
├── intents
│     │
│     ├── Intent 1
│     │     └── "Create VLAN 100 named STAFF on R1"
│     │
│     └── Intent 2
│           └── "Configure OSPF on R2"
│
└── tasks (Output of _process_intent() for each intent)
      │
      ├── Task 1
      │     ├── operation = create_vlan
      │     ├── target = R1
      │     ├── parameters = VLAN 100, STAFF
      │     ├── template = Cisco VLAN template
      │     └── config = ...
      │
      └── Task 2
            ├── operation = configure_ospf
            ├── target = R2
            ├── parameters = ...
            ├── template = Cisco OSPF template
            └── config = ...


PlannedTask will look like this:

PlannedTask(
    task_id="task-1",
    intent_id="intent-1",
    operation_id="create_vlan",
    target="R1",
    parameters={
        "vlan_id": 100,
        "name": "STAFF"
    },
    template="cisco/create_vlan/template.j2",
    rendered_config="vlan 100\n name STAFF"
)
"""


def plan_to_dict(plan: ExecutionPlan) -> dict:
    return asdict(plan)
