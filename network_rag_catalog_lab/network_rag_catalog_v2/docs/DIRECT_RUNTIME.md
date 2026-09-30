# Direct Runtime for Prompt Testing

## Current Scope

The normal terminal path now uses:

```text
data/catalog/{categories,operations,parameters,operation_parameters}.json
  -> data/operations/<category>/<operation_id>/schema.json
  -> Chroma operation retrieval / LLM intent selection
  -> schema-guided extraction / field-scoped clarification / inventory validation
  -> data/templates/<vendor>/<category>/<operation_id>/template.j2
```

All 38 requested canonical IDs are present, with six existing IP/BGP/IS-IS
operations preserved: 44 operations, 44 physical schema files and 132 templates.
Required/optional rules remain operation-specific. Existing parameter IDs and
aliases are preserved; for example `address`, `admin_up` and `new_vlan_name`.

`NETWORK_RAG_RUNTIME` defaults to `files`. Runtime schemas are read from the
schema.json paths, not recompiled from SQLite or selected from a release.
Templates are selected by their vendor/category/operation path. Binding records
and vendor-knowledge metadata retained in the repository do not choose templates
on this path. Existing type, inventory, device-policy and whole-request rendering
checks remain; missing data still uses the existing clarification loop.

## Run

From the v2 directory, with the configured Ollama models running:

```powershell
& ../../.venv/Scripts/python.exe -m app.ingest
& ../../.venv/Scripts/python.exe main.py --interactive
```

Ingest after editing catalog/schema/template files, not for every prompt.
This command updates `network_operation_catalog` directly and verifies its
contents. It does not import a pack, edit SQLite, create a release or activate a
pointer. The file hash and embedding model must match at retrieval time, so stale
vectors cannot silently represent changed schemas. Existing published collections
are not overwritten. Models are not downloaded or substituted.

Start a fresh session after this mode switch. Existing file sessions can use the
normal `--resume SESSION_ID --interactive` command. `select 1`, custom answers,
`edit TASK_ID FIELD_PATH VALUE`, and `quit` remain unchanged.

Use `PROMPT_TESTING_GUIDE.md` for complete examples. Commas separate parameter
clauses; semicolons separate operations.

Examples:

```text
Create VLAN 100 named STAFF on R1 and R2
Configure access port, interface "GigabitEthernet1/0/1", vlan_id 20 on SW1
Create classifier, classifier_name "NEW_CLASS", dscp_values [46,34], match_mode "any" on SW1
Configure OSPF on R2
Create VLAN 100 named STAFF on R1; rename VLAN, vlan_id 20 on SW1
```

The last two need clarification; no configuration is returned while a required
answer is unresolved. Catalog phrases can take a deterministic shortcut. Use
natural paraphrases to exercise RAG/model selection, which is not guaranteed to
classify every prompt correctly.

## Vendor Coverage

| Requested operations | Cisco | Huawei | Juniper |
| --- | --- | --- | --- |
| Available to intent retrieval | 38 | 38 | 38 |
| Generation templates | 38 | 38 | 38 |
| Missing requested vendor templates | 0 | 0 | 0 |

All 54 formerly missing vendor templates are implemented. Use
[the three-vendor prompt guide](THREE_VENDOR_PROMPTS.md) for complete examples.
Some operations have different native contracts: Huawei/Juniper VLAN modification
edits description rather than Cisco suspend state; OSPF, ACL and QoS schemas
contain their required native inputs. No vendor falls back to Cisco commands.
Inventory checks and required-value clarification remain intact.

`x-vendor-profiles` in each affected schema selects the per-vendor properties
and required list. Shared parameter definitions provide labels and types; the
schema remains the direct runtime authority. RAG receives these profile contracts.
The older SQLite registry mappings and binding records are not recompiled or
silently synchronized by this file-only revision.

## Preserved Backend and Recovery

SQLite, prior releases, packs and management services were not deleted. Explicit
`NETWORK_RAG_RUNTIME=published` restores the existing published-reader path, but
it does not include later direct-file edits automatically. Do not use publication
commands for this prompt-testing phase. The two data sources are not synchronized.

The initial direct files were mechanically exported from the existing SQLite
catalog and its published schemas, preserving IDs and contracts. Prior data/ was
backed up to `storage/direct_file_backup/d9294d1cba87481ba569cd3e0dbbbbd2/data/`.
The direct-file switch itself did not modify the database or active pointer.
An earlier metadata publication completed immediately before the user redirected
the task; its retained release is `44d6ad1355b44a6c9a91624d9ee31512`.

## Verification and Limits

Seven focused file-mode tests passed, covering all requested IDs, direct schema
files, all 32 added-operation extraction/render examples, optional values,
missing-value clarification, mixed-device association, vendor fallback rejection,
and direct ingestion without publication. Deterministic tests mock the LLM; they
do not measure natural-language accuracy. No full-suite or benchmark campaign.

Actual direct Chroma ingestion completed: 44 stored operation documents, all 38
requested IDs present, matching catalog hashes, and no release selected by the
runtime. One live Qwen test, "Provision a Layer-2 broadcast domain with VLAN ID
100 named STAFF on R1", selected `create_vlan`, preserved both values and the R1
target, and generated `vlan 100` / `name STAFF` after the normal operation
confirmation. This is one successful example, not proof of universal LLM accuracy.

Configuration previews only. Synthetic SW1/SW2/SW3 facts are not discovered device
state; vendor CLI has not been certified on physical hardware. Same-request
resource creation does not automatically update inventory for a later operation.
No Ansible, execution, topology or UI work is introduced here.
