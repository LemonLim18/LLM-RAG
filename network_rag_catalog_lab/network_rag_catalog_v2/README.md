# Network RAG Catalog Lab v2

This is the revised version of the original `network_rag_catalog` learning lab.

The original MVP proved this lower-level pipeline:

`prompt -> category -> ChromaDB operation retrieval -> operation selection -> schema -> parameter extraction -> validation -> vendor template -> rendered config`

Version 2 adds the missing orchestration layer needed for realistic requests:

`one user request -> N operation intents -> N target sets -> vendor-aware rendering`

It also separates natural-language device references from authoritative inventory records.

## What changed

### 1. One request can contain many operations

Instead of:

```python
run(prompt, ["R1"])
```

use:

```python
run(prompt)
```

The planner creates independent `OperationIntent` objects. Each intent then goes through the existing RAG/schema/template pipeline independently.

### 2. Targets are resolved against inventory

The LLM is allowed to extract a human reference such as `core router 1`, but it is **not trusted to invent a canonical hostname**.

The target resolver maps:

`core router 1 -> R1 -> Cisco IOS-XE 17.9`

Inventory contains hostname, display name, aliases, role, site, location, vendor, platform, version and management IP.

The sample inventory is deliberately shaped like a future source-of-truth record. It includes stable device IDs, external source references, Ansible connection fields, monitoring labels, capabilities and interface records. It is still local JSON, but it can later be backed by NetBox, PostgreSQL, Redis cache, Ansible inventory or monitoring APIs without changing the pipeline contract.

### 3. Vendor selection is deterministic

The target resolver returns canonical devices. Their inventory records determine vendor/platform/version. The template selector then selects:

`vendor / category / operation_id / template.j2`

The LLM does not choose the Jinja file.

### 4. ChromaDB remains an operation-discovery layer

One catalog operation is one retrieval document. ChromaDB helps map natural language to a logical operation. It is not the source of truth for inventory or live device state.

### 5. This lab stops before execution

The result is an execution-ready plan containing rendered configurations. No device is modified. A future approval/Ansible layer can consume this plan.

## Architecture

```text
USER REQUEST
    |
    v
INTENT PLANNER
    |
    +---- Intent 1 ----+
    |                  |
    |             category classifier
    |                  |
    |             ChromaDB retrieval
    |                  |
    |             operation selector
    |                  |
    |             schema loader
    |                  |
    |             parameter extraction
    |                  |
    |             deterministic validation
    |                  |
    |             target resolver
    |                  |
    |             authoritative inventory
    |                  |
    |             vendor/platform/version
    |                  |
    |             deterministic template selector
    |                  |
    |             Jinja2 rendering
    |                  |
    +---- Intent 2 ----+  ...
                         |
                         v
                 EXECUTION PLAN
                         |
                   approval gate
                         |
                      Ansible
                         |
                       devices
```

## Important responsibility split

| Component | Responsibility |
|---|---|
| Intent planner | Split one request into independent logical intents and extract human target references |
| Category classifier | Determine the broad operation category |
| ChromaDB | Retrieve semantically relevant operation candidates |
| Operation selector | Choose one operation only from retrieved candidates |
| JSON Schema | Define the formal parameter contract |
| Parameter extractor | Map natural language into structured parameters |
| Validator | Deterministically reject invalid/missing values before rendering |
| Target resolver | Map human device references to canonical inventory devices |
| Inventory | Authoritative device, capability and interface metadata |
| Context validator | Reject unsupported operations and device/interface mismatches |
| Template selector | Select the exact known template |
| Jinja2 | Render vendor-specific configuration |
| Future approval/Ansible layer | Diff, approve and execute |

## Missing information behavior

The LLM is treated as an untrusted parser. Parameter extraction may only keep values that are explicitly grounded in the user's request. If required values are missing, the task is returned as `needs_clarification` and no Jinja template is rendered.

For example:

```text
Create VLAN 100 named STAFF on R1 and configure OSPF on R2
```

produces a ready VLAN task, but the OSPF task asks for `process_id` and `interfaces` instead of inventing them.

## Run

Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Make sure Ollama has:

```text
qwen2.5:1.5b
nomic-embed-text
```

Build the operation catalog index:

```bash
python -m app.ingest
```

Then run a single-operation request:

```bash
python main.py "Create VLAN 100 named STAFF on Core Router 1."
```

A multi-operation, multi-device example:

```bash
python main.py "Create VLAN 100 named STAFF on R1 and R2, configure OSPF process 100 on Gi0/0 in area 0 on Core Router 1, and add a static route to 10.20.0.0/16 through 192.168.1.1 on Edge Router 1."
```

The final output is a structured JSON execution plan. It is deliberately not sent to any network device.

## Test target resolution without the LLM

```bash
python -c "from app.devices.inventory import resolve_targets; print(resolve_targets(['core router 1']))"
```

## Tests

```bash
python -m unittest discover -s tests -v
```

## Limitations of this lab

- `qwen2.5:1.5b` is a small local model; its planning/extraction quality is intentionally not production-grade.
- The Jinja templates are architecture/demo templates, not release-certified production templates for every NOS and Ansible collection.
- The current inventory is a JSON file. A real platform would normally query NetBox or another authoritative inventory source.
- The current version renders configuration but does not run Ansible.
- Target resolution intentionally asks for clarification rather than guessing when multiple devices are plausible.
- Some logical operations are not perfectly semantically identical across vendors. For example, Junos OSPF does not use a Cisco-style numeric OSPF process ID. Production metadata should therefore include vendor/platform compatibility and parameter mapping rather than silently assuming complete equivalence.
