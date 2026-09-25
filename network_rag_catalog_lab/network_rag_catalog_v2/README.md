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

Descriptions such as `the Penang edge Juniper router` now resolve using those
attributes together. `the KL core router` asks which device; `KL core routers`
selects the explicitly requested group. Conflicting attributes block rendering.
The terminal accepts refinements such as `the Huawei one` and shows the matching
inventory facts. See [DEVICE_RESOLUTION.md](docs/DEVICE_RESOLUTION.md) for the
data contract, centrally governed aliases, supported examples, and limits.

The sample inventory is deliberately shaped like a future source-of-truth record. It includes stable device IDs, external source references, Ansible connection fields, monitoring labels, capabilities and interface records. It is still local JSON, but it can later be backed by NetBox, PostgreSQL, Redis cache, Ansible inventory or monitoring APIs without changing the pipeline contract.

### 3. Vendor selection is deterministic

The target resolver returns canonical devices. Their inventory records determine vendor/platform/version. The template selector then selects:

`vendor / category / operation_id / template.j2`

The LLM does not choose the Jinja file.

### 4. ChromaDB remains an operation-discovery layer

One catalog operation is one retrieval document. ChromaDB helps map natural language to a logical operation. It is not the source of truth for inventory or live device state.

### 5. This lab stops before execution

The result is a validated configuration preview. No device is modified. Template
rendering tests are not device/NOS certification.

### Context-aware clarification revision

All intents are collected before asking questions. Each resolved operation/device
binding owns its parameters, evidence, questions and state. A complete binding
becomes `validated`; no configurations are published until the whole request
passes validation. Then tasks become `rendered` and the request becomes `ready`.

Missing/invalid fields receive one structured question at a time, with scoped
inventory or planned choices and custom input. Local planned data lives in
`data/planned/parameters.json`; `data/catalog/context_rules.json` explicitly
permits each operation's lookups. Sample records are candidates requiring
confirmation, not live facts or automatically applied defaults.

Exact catalog phrases bypass model/retrieval calls. Other phrasing uses the
existing discovery stages and asks for confirmation of a model-proposed
operation. Parsing/selection repairs are bounded. See
[CONTEXT_AWARE_REVISION.md](docs/CONTEXT_AWARE_REVISION.md) for the API contract,
examples, revision behavior and remaining limits.

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

produces a validated VLAN binding and an incomplete OSPF binding. Neither renders
until OSPF has validated interfaces, areas and its vendor-required process ID.

## Run

Use the existing Python environment with the project dependencies installed. In
this Windows workspace, from the v2 folder, that is:

```powershell
..\..\.venv\Scripts\python.exe -m app.ingest
```

Make sure Ollama has:

```text
qwen2.5:1.5b
nomic-embed-text
```

Otherwise, rebuild the index whenever `data/catalog/operations.json` changes:

```bash
python -m app.ingest
```

Run a single operation:

```bash
python main.py "Create VLAN 100 named STAFF on Core Router 1."
```

### Terminal clarification mode

The terminal uses a persisted clarification session, so its state model can later
be exposed by a web UI without changing the core pipeline.

```bash
python main.py "Configure OSPF on R2" --interactive
```

The system asks one field of one task at a time and does not render until its
values are validated. For the interfaces question, reply:

```text
GigabitEthernet0/0/0 in area 0
```

For the subsequent process-ID question, reply `100`.

Choose an offered option with `select 1`, or multiple interfaces with
`select 1,2`. Bare numbers are literal values. Custom input is always available;
`value 100` explicitly enters a literal. Use `more` or `filter TEXT` for large
option lists. To leave and resume later:

```bash
python main.py --resume SESSION_ID --interactive
```

Correct an accepted field using `edit TASK_ID FIELD_PATH VALUE` during a pending
conversation, or `--resume SESSION_ID --edit TASK_ID FIELD_PATH VALUE`. Nested
paths include `interfaces[0].area`. Conflicting operations require correction or
explicit `confirm order`. An edit invalidates old outputs and rechecks the request.

Use `--no-interactive` to print the session JSON without waiting for input.
The final output is structured session data; it is deliberately not sent to any
network device.

### Included operation catalog

Each category now has at least two safe planning/rendering operations:

| Category | Operations |
|---|---|
| VLAN | create, delete |
| OSPF | configure, remove from interface |
| BGP | configure, remove neighbor |
| IS-IS | configure, disable interface |
| Static routing | configure, remove route |
| Interface IPv4 | configure, remove address |

Catalog terminology is centralized in:

- `data/catalog/categories.json`
- `data/catalog/operations.json`
- `data/catalog/parameters.json`

Stable IDs are used in code and schemas. A senior engineer can change display
names, aliases, and clarification wording in these catalog files without
renaming the internal IDs.

See `docs/CATALOG_GOVERNANCE.md` for the add/change/retire workflow and
`docs/TEST_PROMPTS.md` for ready-made terminal tests.

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
- Vendor-specific required fields remain in schemas. Junos OSPF has no numeric
  process ID; Junos BGP now requires an explicit peer group. Template compatibility
  is restricted by `data/catalog/template_support.json` to the lab inventory
  releases; it is not a claim of release-certified CLI syntax.
