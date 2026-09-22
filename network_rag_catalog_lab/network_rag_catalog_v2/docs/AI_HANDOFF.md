# AI Handoff: V2 Core

## Purpose

This is a planning and rendering lab, not an execution system. It converts one
human request into independent network-operation tasks, validates each task
against inventory, and renders only tasks with complete validated context.

## Current Flow

`prompt -> intents -> category -> RAG candidates -> operation -> schema -> extraction -> target resolution -> validation -> vendor template -> plan`

`needs_clarification` is a normal state. It must never render a template.

## Core Files

- `app/pipeline.py`: planning, validation gates, continuation of one task.
- `app/clarification.py`: JSON-backed session state for terminal/UI reuse.
- `main.py`: terminal entry point, interactive clarification, session resume.
- `app/catalog.py`: catalog loading and consistency checks.
- `app/parameters/parameter_extractor.py`: untrusted LLM output plus explicit-value fallback.
- `app/parameters/normalizer.py`: deterministic netmask/CIDR and literal parameter normalization.
- `app/devices/inventory.py`: authoritative device/group resolution and suggestions.
- `app/devices/context_validator.py`: capability/interface checks and suggestions.

## Catalog Rules

`data/catalog/categories.json`, `operations.json`, and `parameters.json` own
all editable names, aliases, and clarification wording. Keep machine IDs stable.
Each operation has a JSON Schema and one template per current inventory vendor.
Run `python -m app.ingest` after operation-catalog changes.
For a future long-running UI process, call `app.catalog.reload_catalog()` after a
catalog edit, then rebuild the retrieval index.
Read `docs/CATALOG_GOVERNANCE.md` before changing catalog IDs or adding an operation.

Schemas may declare `x-required-by-vendor`. Base requirements apply to all
targets; vendor requirements are added only after inventory resolution. Example:
Cisco/Huawei OSPF requires `process_id`; Junos does not.

## Safety Rules

- Never let the LLM choose a device, vendor, or template.
- Keep only parameter values grounded in user text.
- Preserve parameter provenance in `PlannedTask.parameter_provenance`.
- Ground planner target references against the original user text.
- Ask clarification for missing, ambiguous, invalid, or unsupported context.
- Normalize known aliases such as `Eth1/1`; do not guess unknown interfaces.

## Terminal Usage

```bash
python -m app.ingest
python main.py "Configure OSPF on R2" --interactive
python main.py --resume SESSION_ID --interactive
python -m unittest discover -s tests -v
```

Sessions are saved under `storage/sessions/` and are intentionally ignored by Git.
The model and embeddings are configured in `app/config.py`.

## Current Scope Boundary

Do not add Ansible execution, topology/current-state discovery, or intent-based
business outcomes here yet. The next work inside this scope is to broaden the
catalog safely and improve deterministic parsers/suggestions using tests.
