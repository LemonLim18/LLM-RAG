# AI Handoff: V2 Core

## Latest Runtime State: 2026-09-29

LATEST USER REQUEST: Huawei and Juniper must each have all 38 requested operations,
without another knowledge-pack/publication workflow. Implemented directly in data/.
Requested coverage is now Cisco 38/38, Huawei 38/38, Juniper 38/38; total runtime
44 operations, 44 schema files, 132 templates. Read MULTIVENDOR_RUNTIME.md and
THREE_VENDOR_PROMPTS.md first.

Default NETWORK_RAG_RUNTIME=files. Native schema profiles select per-device
parameters; all requested vendor_knowledge metadata now says generation_supported.
Do not confuse this with hardware certification or identical semantics.
SW2/SW3 contain explicitly synthetic native resources for every example; original
R1/R2/R3 facts are unchanged. Safety and clarification gates remain.

The optional SQLite/published backend, old packs, mapping records and immutable
releases are not synchronized with this direct-file revision. Do not run a
publication or migration to 'fix' that distinction. Ingest direct files only.
The user requested no further unnecessary tests/expansion after completion.

## Retained History (Superseded Coverage Counts)

The approved activation is implemented: 44 operations, 78 bindings, nine categories,
and six inventory devices. R1/R2/R3 are preserved; SW1/SW2/SW3 are synthetic facts.
Read `KNOWLEDGE_ACTIVATION_RESULTS.md` and `PROMPT_TESTING_GUIDE.md` first.
`REQUESTED_OPERATION_COVERAGE.md` audits the user's later 38-operation proposal:
all IDs exist; 54 Huawei/Juniper combinations still have no executable binding.
RAG documents expose actual profile support and per-vendor parameter requirements.
Do not claim that three-vendor knowledge visibility means three-vendor rendering.

`app.knowledge.pack_promote` defaults to isolated rehearsal; `--apply` requires
actor/reason, captures SQLite/assets/context backup and applies through services.
It does not publish. Reapplication is idempotent; differing records are rejected.
Promotion backup: `storage/catalog_authoring/activation/ab8af4967e154de789a8c029262dfebd/`.
Latest retained published release: `44d6ad1355b44a6c9a91624d9ee31512`.
Its publication completed before the direct-file redirection; default runtime does not use it.

Parser fixes accept comma/conjunction boundaries only before registry field names
and exclude operation labels from field evidence. A category preface such as
"For static routing," no longer replaces a later explicit target.
The live model required operation correction for the default-route paraphrase;
clarification completed it safely. Do not report perfect model interpretation.

The counts and staged-only descriptions below are historical implementation notes.

## Purpose

This is a planning and rendering lab, not an execution system. It converts one
human request into independent network-operation tasks, validates each task
against inventory, and renders only when the complete request validates.

The shared core workflow from both revision plans is implemented; full production
conformance is not proven. Start with [REVISION_NOTES.md](REVISION_NOTES.md) for
changes, capabilities, usage and verification limits. Read
`docs/CONTEXT_AWARE_REVISION.md` for the technical contract.

## Knowledge Evolution: Phases 1-5 Complete

Read [KNOWLEDGE_EVOLUTION_COMPLETION.md](KNOWLEDGE_EVOLUTION_COMPLETION.md) first,
then [KNOWLEDGE_PHASE_5.md](KNOWLEDGE_PHASE_5.md). This workspace now uses SQLite
authoring; fresh clones use JSON seeds until explicitly migrated. Do not edit
managed seed JSON expecting it to change SQLite or the published runtime.
The existing 12 operations now use `schema_source: registry`, `mapping_mode: none`.
38 mappings, 51 rule records, 22 memberships and shared types compile contracts;
36 explicit template bindings preserve current vendor outputs. Original schemas
are retained comparison evidence. No production operation/template was added.

`python -m app.knowledge.migration --operations` previews mappings/rules;
`--compare` reports drift and exits 1 when differences exist. Neither writes
files. The manifest's unresolved target definitions are not import instructions.
Publication stages schemas/templates/retrieval and switches one active pointer.
CLI/transport-neutral contracts support local audited edits, revision checks,
recovery, previews and publication. SQLite transactions, foreign keys, migration,
backup and authority-switch recovery are implemented. JSON and SQLite run the
same management contract tests. Runtime never reads an unpublished database draft.
Conditional required fields use the normal field-scoped clarification gate;
every supported template profile has a hashed effective schema artifact.
The completion audit records current tests, live-index checks and remaining limits.
No HTTP server, GUI, device execution or vendor certification was added.

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
- `app/catalog.py`: compatible dictionary access and schema/template checks.
- `app/knowledge/`: typed records, compilation/publication, local managed authoring.
- `app/knowledge/migration.py`: read-only membership/operation previews and comparisons.
- `app/knowledge/operation_contracts.py`: projection/comparison, not a runtime compiler.
- `data/catalog/category_parameters.json`: category membership, not operation requirements.
- `data/catalog/operation_parameters.json`, `operation_rules.json`: registry contract seed/export shapes.
- `app/knowledge/runtime.py`: request-scoped release adapter; separate live context checks.
- `app/knowledge/management.py`, `authority.py`, `sqlite_repository.py`, `cli.py`: managed authoring, explicit authority and recovery.
- `app/api/contracts.py`: strict, transport-neutral request/result models.
- `app/parameters/parameter_extractor.py`: untrusted LLM output plus explicit-value fallback.
- `app/parameters/normalizer.py`: deterministic netmask/CIDR and literal parameter normalization.
- `app/devices/inventory.py`: inventory loading and compatible resolution API.
- `app/devices/target_query.py`: original-text descriptions and grounded attribute extraction.
- `app/devices/target_resolver.py`: all-constraint matching, ranked suggestions, and descriptive correction.
- `data/inventory/attributes.json`: attribute paths, labels, weights, and approved value aliases.
- `app/devices/context_validator.py`: capability/interface checks and suggestions.
- `data/catalog/context_rules.json`: scoped lookups, resource keys and conflict pairs.
- `data/planned/parameters.json`: versioned sample candidates, always confirmed.
- `data/catalog/template_bindings.json`: reviewed operation/platform/version/input contracts.
- `data/catalog/template_support.json`: retained compatibility path for unmigrated operations.

## Catalog Rules

Category, operation and parameter records own all editable names, aliases, and
clarification wording. Use management services; keep machine IDs stable.
Each operation compiles a JSON Schema and declares its supported template profiles.
Its schema parameters must also be exposed by the owning category in
`category_parameters.json`. This file contains only ID pairs, not types, labels,
required flags, or value rules. Shared definitions are reused without copying.
Current operation mappings/rules are authored in SQLite, while active runtime
reads immutable published artifacts. Draft edits do not change published requests.
Run `python -m app.knowledge.cli inspect` / `validate` / `preview-schema` for review.
Management writes require an initial release; use revision-checked request files
and explicit publication. `python -m app.ingest` publishes with a new Chroma index,
never deletes the old index first. Registry retrieval cannot use the legacy index.
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

Knowledge expansion Phase 0 (2026-09-28) is a code-only readiness revision;
see `docs/KNOWLEDGE_EXPANSION_PHASE_0.md` for decisions, tests and remaining work.
Field-scoped literal evidence now handles primitive arrays and labelled nested
JSON, preserves explicitly mentioned optional inputs, and asks when those inputs
cannot be grounded. New validation callbacks are code-reviewed only; all existing
safety handlers remain mandatory. Category aliases use extraction normalization.
That Phase 0-only boundary is historical. Phases A, B1/B2, C, D1/D2 are now
implemented as review-only packs under `knowledge_packs/`; the plan has no Phase E.
See `docs/KNOWLEDGE_EXPANSION_COMPLETION.md` and its verification note first.
The candidate release has 44 operations/78 bindings (32/42 added); the live
12-operation/36-binding SQLite baseline and active release remain unchanged.
Rehearse with `python -m app.knowledge.pack_review --check-cases`; this uses temporary
SQLite and offline publication only. Do not activate packs without separate approval.
Only documented profile subsets are supported. Same-request create/use chains,
device-lab certification and expanded live-model/index benchmarks remain pending.
Live-model benchmarking remains pending because Ollama was offline during review.

Do not add Ansible execution, topology/current-state discovery, or intent-based
business outcomes here yet. Phases 1-5 are implemented with explicit SQLite authority;
review local publication and management before further expansion. Do not activate the target document's
new operations in the live catalog without explicit rollout approval.
