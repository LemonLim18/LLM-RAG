# AI Handoff: V2 Core

## Purpose

This is a planning and rendering lab, not an execution system. It converts one
human request into independent network-operation tasks, validates each task
against inventory, and renders only when the complete request validates.

The primary and secondary context-aware revision plans are implemented. Read
`docs/CONTEXT_AWARE_REVISION.md` for the concise current contract and limits.

## Current Flow

`prompt -> evidenced intents -> catalog/RAG operation -> per-device bindings -> extraction + context + validation -> question queue -> whole-request gate -> rendered preview`

`needs_clarification` is a normal state. It must never render a template.
Complete bindings are `validated` while siblings remain incomplete. Tasks become
`rendered` only after atomic publication of all rendered configurations; the
request/session then becomes `ready`. `needs_confirmation` handles cross-task
resource conflicts. A failed render exposes no partial configurations.

## Core Files

- `app/pipeline.py`: planning, validation gates, continuation of one task.
- `app/questions.py`: structured questions/answers and explicit selection commands.
- `app/context.py`: permitted planned lookup, record validation and source fingerprints.
- `app/parameters/fields.py`: nested field paths and strict active-field parsing.
- `app/clarification.py`: JSON-backed session state for terminal/UI reuse.
- `main.py`: terminal entry point, interactive clarification, session resume.
- `app/catalog.py`: catalog loading and consistency checks.
- `app/parameters/parameter_extractor.py`: untrusted LLM output plus explicit-value fallback.
- `app/parameters/normalizer.py`: deterministic netmask/CIDR and literal parameter normalization.
- `app/devices/inventory.py`: inventory loading and compatible resolution API.
- `app/devices/target_query.py`: original-text descriptions and grounded attribute extraction.
- `app/devices/target_resolver.py`: all-constraint matching, ranked suggestions, and descriptive correction.
- `data/inventory/attributes.json`: attribute paths, labels, weights, and approved value aliases.
- `app/devices/context_validator.py`: capability/interface checks and suggestions.
- `data/catalog/context_rules.json`: scoped lookups, resource keys and conflict pairs.
- `data/planned/parameters.json`: versioned sample candidates, always confirmed.
- `data/catalog/template_support.json`: lab platform/release allowlist, not certification.

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
Junos BGP requires `peer_group`; it is never derived from a description/default.

## Safety Rules

- Never let the LLM choose a device, vendor, or template.
- Keep only parameter values grounded in user text.
- Preserve parameter provenance in `PlannedTask.parameter_provenance`.
- Ground planner target references against the original user text.
- Ask clarification for missing, ambiguous, invalid, or unsupported context.
- Normalize known aliases such as `Eth1/1`; do not guess unknown interfaces.
- Never use a ranking score to waive a contradictory device attribute.
- Singular ambiguous descriptions ask; explicit plural groups may select many.
- Preserve `target_queries` and `target_resolution` through session roundtrips.
- Target replies bypass parameter extraction; each interactive turn asks one field of one task.
- Device management/version evidence must not become operation parameter values.
- Accepted replies follow parse -> normalize -> validate -> update. Rejected
  replies never enter parameter state. A mask is not an address; interface slash
  components are not prefixes. Interface aliases require complete boundaries.
- Preserve partial nested items. Each interface's missing area has its own path
  and item ID. No implicit area copying between interfaces/devices.
- Use `ClarificationAnswer` + `apply_answer` for future UI calls; keep supplied
  question/source revisions. `apply_correction` is the explicit edit API.
- `1` is a literal; `select 1` is an option. Multi-selection uses `select 1,2`.
- Scope all planned context by device/operation/dependencies. Conflicting facts
  cannot be overridden; allowed planned changes require explicit confirmation.
- Recheck sources on resume/answer/render. Invalidate selected planned values
  on context/dependency changes and never publish stale rendered artifacts.
- Exact catalog phrases avoid model calls. Nonliteral model operation proposals
  require confirmation; bounded repair never authorizes guessed targets/values.

See `docs/DEVICE_RESOLUTION.md` for supported phrases, refinement semantics, and
known language limits. Inventory edits do not need a RAG-index rebuild.

## Terminal Usage

```bash
python -m app.ingest
python main.py "Configure OSPF on R2" --interactive
python main.py --resume SESSION_ID --interactive
python -m unittest discover -s tests -v
```

Sessions are saved under `storage/sessions/` and are intentionally ignored by Git.
The model and embeddings are configured in `app/config.py`.
The existing interpreter is `..\..\.venv\Scripts\python.exe` from this folder.
Use `--resume SESSION --edit TASK FIELD VALUE` for completed-session edits.
Legacy sessions migrate and revalidate; unknown future versions fail explicitly.

## Regression Coverage

`tests/test_clarification_flow.py` exercises the real deterministic extraction,
question, validation and rendering path with reproducible model failures. It
covers masks/prefixes, interface boundaries, shared/mixed device scope, nested
fields, independent vendor requirements, typed options/custom answers, source
changes, planned conflicts, correction, migration and atomic rendering failures.
The full suite also smoke-renders all existing vendor templates. These tests do
not certify CLI on actual NOS releases or measure local-model accuracy.

## Current Scope Boundary

Do not add Ansible execution, topology/current-state discovery, or intent-based
business outcomes here yet. The next work inside this scope is to broaden the
catalog safely and improve deterministic parsers/suggestions using tests.
