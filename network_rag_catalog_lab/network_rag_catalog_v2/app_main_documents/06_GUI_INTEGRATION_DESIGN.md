# Iteration 0 — GUI Integration Design

Status: completed architecture audit, 2026-10-08. This document specifies proposed interfaces and implementation boundaries; none of the proposed endpoints, stores or frontend files was implemented in this iteration. The independently verifiable deliverable is this design together with [05_FYP_REUSE_AUDIT.md](05_FYP_REUSE_AUDIT.md).

Paths are relative to the V9 project root unless linked relative to this document. Existing sources are linked; the project structure and API sections explicitly describe future additions. Product scope and deferred capabilities remain governed by `00_PRODUCT_VISION.md`.

## 1. Verified V9 integration interfaces

### Application/session entry points

| Existing source and callable | Input → output | Dependencies and integration constraints |
|---|---|---|
| [main.py](../main.py) CLI | Arguments/interactive input → formatted terminal session | Uses shared clarification functions. Keep available; never launch through subprocess as the GUI API. |
| [app/clarification.py](../app/clarification.py): `create_session(prompt, *, verbose=False)` | Prompt string → `ClarificationSession` | Calls `run`, sets UUID/timestamps/history, saves JSON immediately. Blocking function; creation may invoke local models and retrieval. |
| Same source: `session_to_dict(session)` | Session → JSON-compatible dict | Includes `schema_version: 2`, plan, history and pending questions. No top-level session revision, request ID or generated-artifact identity exists. |
| Same source: `load_session(session_id)` | UUID-shaped string → refreshed `ClarificationSession` | Reads JSON, accepts saved plan schema versions 1/2, clears old task configurations, refreshes/revalidates and may render. Updates in-memory timestamp; does not itself save. This is a resume primitive, not a passive GET. |
| Same source: `save_session(session)` | Session → no return value | Writes a UUID-named temporary file then replaces the session JSON atomically. Atomic replacement does not provide cross-request locking or optimistic concurrency. |
| Same source: `apply_answer(session, answer)` | `ClarificationAnswer` → mutated/saved session | Requires the session's current next question. Delegates to `apply_clarification(session, task_id, reply, *, verbose=False)` and then `resume_task`. It is not an arbitrary parallel question-answer API. |
| Same source: `apply_correction(session, task_id, path, reply)` | Task ID, field path, textual replacement → mutated/saved session | Uses `correct_task`; accepted corrections invalidate dependent evidence/configs as appropriate. Rejections may return task feedback rather than throw. |
| Same source: `confirm_session_order(session)` | Session → mutated/saved session | Calls plan-level confirmation of the listed conflicting task order. Does not accept a client-supplied reorder. |
| [app/pipeline.py](../app/pipeline.py): `run(prompt, *, verbose=True)` | Prompt → `ExecutionPlan` | Reloads and validates catalog/context; splits intents and per-device bindings, then refreshes the full plan. Pass `verbose=False` from service. |
| Same source: `refresh_plan(plan, *, render_complete=True)` | Existing plan → refreshed plan | Request-wide validation/confirmation gate: no task configurations are published until every task is valid and conflicts are resolved. Render results are staged before assignment. |
| Same source: `resume_task(task, reply, *, verbose=False)`, `correct_task(task, path, reply)` | Task plus answer/correction → replacement task | Lower-level building blocks; use session functions for normal API writes so history/save behavior is retained. |
| Same source: `plan_to_dict(plan)` | Plan → dict | Dataclass serialization preserves task identity and evidence fields. |

### Domain services behind those entry points

| Existing source and callable | Input → output | Integration meaning |
|---|---|---|
| [app/planner/intent_planner.py](../app/planner/intent_planner.py): `plan_intents(prompt)` | Text → ordered `OperationIntent` list | Deterministic literal-operation path plus bounded model repair/fallback; preserves source spans and uncertain scope. The UI must not split intents itself. |
| [app/retrieval/category_classifier.py](../app/retrieval/category_classifier.py): `classify_category(prompt)` | Text → category ID | Catalog lookup first; otherwise Ollama classification constrained to known categories. |
| [app/retrieval/operation_retriever.py](../app/retrieval/operation_retriever.py): `retrieve_operation_candidates(prompt, category, k=3)` | Text/category → candidate dictionaries | Chroma distances, descriptions and vendor support; published mode checks release/version/category metadata. Distances are not probabilities. |
| [app/retrieval/operation_selector.py](../app/retrieval/operation_selector.py): `select_operation(prompt, category, candidates)` | Text/candidates → active operation ID | Exact catalog phrases or constrained model selection; unresolved selection raises. Pipeline marks model-proposed operations for confirmation. |
| [app/parameters/parameter_extractor.py](../app/parameters/parameter_extractor.py): `extract_parameter_result(prompt, schema, *, existing_parameters=None, requested_fields=None)` | Text/schema → `ExtractionResult` | Includes parameters, provenance, candidates, missing/provided fields and diagnostics. Pipeline retains parameter evidence but does not currently persist every retrieval distance or extraction diagnostic. Do not invent missing trace data in the UI. |
| [app/parameters/schema_loader.py](../app/parameters/schema_loader.py): `load_schema(operation_id, devices=None)` | Operation/optional target devices → schema | Canonical extraction vocabulary versus vendor-specific requirements are distinct. |
| [app/parameters/validator.py](../app/parameters/validator.py): `validate_parameter_result(params, schema)` | Structured parameters → `ValidationResult(valid, issues)` | JSON Schema and semantic parameter checks. It does not validate arbitrary manually edited vendor configuration text. |
| [app/devices/context_validator.py](../app/devices/context_validator.py): `normalize_parameters_for_device(params, device)`, `validate_device_context(operation_id, category, params, devices)` | Parameters/device records → normalized parameters / issue list | Inventory interface aliases, capabilities and operation policies. Vendor compatibility cannot be inferred from a dropdown selection alone. |
| [app/devices/inventory.py](../app/devices/inventory.py): `load_inventory()` | No arguments → list of device dictionaries | Uncached read of the configured JSON file. No CRUD/revision repository exists. |
| [app/devices/target_query.py](../app/devices/target_query.py): `extract_target_queries(text, inventory, *, reply=False, allow_llm=False)`, `parse_description(text, inventory, *, allow_llm=False)`, `load_attributes()`; [app/devices/target_resolver.py](../app/devices/target_resolver.py): `resolve_queries(queries, inventory=None)`, `resolve_intent_targets(target_refs, inventory=None)` | Descriptions/constraints → devices, evidence and issues (or typed resolution error) | Vocabulary is built from inventory and attribute definitions. Every stated constraint must match; ambiguous or conflicting selectors do not silently choose a device. |
| [app/templates/template_selector.py](../app/templates/template_selector.py): `select_template(device, operation_id)`, `template_binding(device, operation_id)` | Target/operation → template path / optional binding | Honors explicit blocked vendor knowledge. Published bindings enforce vendor/platform/version; direct-file mode uses reviewed vendor template presence plus explicit blocks, so its guarantees are not identical. |
| [app/templates/renderer.py](../app/templates/renderer.py): `render(device, operation_id, params)` | Validated target/parameters → configuration string | Jinja StrictUndefined and template contracts; the plan layer owns the request-wide gate. Do not expose bypass rendering of unvalidated tasks. |
| [app/context.py](../app/context.py): `source_revision()`, `context_revision()` | Current sources → content-derived revision strings | Inventory/planned JSON participates in context revision; in file mode JSON/Jinja under data contributes to source revision. Changes invalidate old answers/evidence. |
| [app/knowledge/runtime.py](../app/knowledge/runtime.py): `snapshot_scope`, `snapshot_request`, `current_snapshot`, `active_snapshot` | Request context → optional verified knowledge snapshot | ContextVar pins a release per call; validates integrity and current pointer. Published authority failure must not trigger silent file fallback. |
| [app/knowledge/authority.py](../app/knowledge/authority.py): `authority(base)`; [app/config.py](../app/config.py): `runtime_mode()` | Base directory / environment → authoring authority / runtime mode | Authoring `json`/`sqlite` is distinct from runtime `files`/`published`. Expose both, without mutating either. |

[app/api/contracts.py](../app/api/contracts.py) has strict Pydantic knowledge-authoring envelopes, not workbench endpoints. Reuse its strict-contract approach, not authoring operations or migrations. [requirements.txt](../requirements.txt) currently includes V9 libraries and Pydantic but does not declare FastAPI/Uvicorn; those belong to a later backend iteration.

### Identity and state that transport must preserve

[app/planner/models.py](../app/planner/models.py) and [app/questions.py](../app/questions.py) are the transport baseline:

- Task identity is `PlannedTask.intent_id`. Per-device splitting can produce values such as `intent-1:dev-r1`; preserve those opaque IDs and the separate `logical_intent_id`, `device_id` and `scope_device_ids`.
- Task `revision` is an integer; `source_revision`, `context_revision`, `knowledge_snapshot_id` and `runtime_authority` describe evidence context. They are not interchangeable with a new session concurrency token.
- Questions retain `question_id`, `task_id`, `binding_id`, `device_id`, `field_path`, `item_id`, `revision`, `source_revision`, `issue_type`, `expected_schema`, `dependencies`, `multiple`, `allow_custom`, wording and labels.
- Options retain `option_id`, typed `value`, label, explanation, source reference/revision and any override metadata. Send option IDs, never displayed option numbers.
- `ClarificationAnswer(question_id, revision, source_revision, kind='custom', raw_input='', selected_ids=[])` has no separate answer UUID. A proposed API `answer_id` is transport metadata and must not be substituted for its question/option IDs.
- Preserve task `parameters`, `parameter_provenance`, `parameter_evidence`, `candidates`, `planning_issues`, `issues`, `feedback`, `source_spans`, `target_queries`, `target_resolution`, `confirmations`, `item_ids`, `operation_candidates`, `target_devices`, `configs` and clarification history. Preserve plan issues and intent order.
- Plan states observed: `collecting`, `needs_clarification`, `needs_confirmation`, `validated`, `ready`, `failed`. Task states also include `rendered`. `ready` means configuration preview ready, never deployed.

`apply_answer` checks the current question ID, and `resume_task` checks question revision/source revision and live source changes. Rejections can be recorded as feedback and rejected history while still returning a session. A successful function return is not sufficient evidence that an answer was accepted.

## 2. Proposed project structure and frontend ownership

The following paths are **new proposals**, not existing modules:

```text
frontend/                         # new V9 workbench, separate from FYP reference
  src/
    app/                          # App, WorkbenchProvider, reducer and shared types
    components/layout/            # WorkbenchLayout, ResizeHandle, StatusBar
    features/explorer/            # synthetic devices / later sessions and artifacts
    features/workspace/           # tabs, Monaco configuration and later diff view
    features/chat/                # messages, input, later structured clarification
    features/activity/            # output, diagnostics, local activity
    fixtures/                     # explicitly labelled shell mock data
    services/                     # later HTTP client and session/inventory adapters
    styles/                       # scoped workbench tokens and layout CSS
app/workbench/                    # later FastAPI composition, isolated from app/api authoring
  api.py                          # application factory and local-only composition
  contracts.py                    # strict versioned transport envelopes
  routes/                         # sessions, inventory, artifacts, runtime
  services/                       # session coordination, artifacts, availability
  repositories/                   # saved-session read view, artifact/draft persistence
app/devices/repository.py          # later JSON inventory writes shared through existing file
storage/workbench/                # later artifact/draft metadata and recoverable backups
```

Do not import the FYP runtime into this structure. New modules call V9 Python functions directly. Existing `app/api/contracts.py` remains the knowledge-authoring boundary.

```text
App → WorkbenchProvider
  WorkbenchLayout
    ExplorerPanel                  left: devices, later sessions/tasks/artifacts
    WorkspacePanel                 center: tabs + configuration/task review
      EditorTabs
      ConfigurationEditor          Monaco; separate model per open document
      ConfigurationDiff            later original-versus-draft comparison
    ChatPanel                      right: messages + composer + later question form
    ActivityPanel                  bottom: output / diagnostics / activity
    StatusBar                      local demo / runtime availability / provenance
```

Use React Context plus a reducer initially. Shared state owns active device/session/task/document IDs, tab order, in-memory draft content, messages, activity entries and panel sizes. Monaco owns model/view internals; the reducer owns document content and dirty state. Server responses become authoritative domain snapshots when integration is added. No second browser inventory database. Avoid Redux or another store until a concrete need appears.

Use CSS Grid for left/center/right with a bottom region, minimum dimensions and bounded pointer-driven splitters. Splitters require keyboard arrow support, focus indicators and `role="separator"` with orientation/value attributes. Monaco uses automatic layout/resize observation and explicit model URIs. At narrow widths, collapse side panels deliberately while preserving access to chat/explorer; do not shrink the editor to zero.

## 3. Service boundaries and operation lifecycle

The proposed FastAPI factory mounts only local workbench routers. A SessionService coordinates existing V9 session functions; InventoryService validates/persists V9-compatible records; ArtifactService preserves originals/drafts; RuntimeService reports independent model, retrieval and knowledge health.

V9 calls are synchronous, include disk access, and may invoke models repeatedly. Run them in a worker thread, never directly on the async event loop. Initial backend proposal: one local service process with a bounded operation queue and one V9 worker. Serialize V9 calls and inventory writes through a shared service gate because catalog reloads use process-global state. This is deliberately modest local capacity; thread safety and throughput are implementation checks.

For potentially slow session mutations return a proposed `202 Operation` (`operation_id`, request ID, state, session ID when known). Poll `GET /api/v1/operations/{operation_id}` until `succeeded` or `failed`; successful operation result contains `SessionEnvelope`. Queue limits return 503. An accepted mutation must not be submitted twice merely because a browser timeout occurred. Maintain a durable request-ID/result journal before reporting acceptance; after restart, reconcile incomplete operations with saved session hashes and mark unresolved outcomes `interrupted`, requiring reload. This journal/recovery is later backend work, not Iteration 1.

Do not claim progress stages that V9 does not emit. A queued/running indicator is sufficient. Cancellation of an HTTP request does not terminate an in-flight Python/model call. The current engine has no cancellation API; initial UI “close” only closes the view. True session cancellation requires a separately verified service policy.

### Read versus resume and concurrency

- A proposed SavedSessionRepository reads and validates stored JSON **without** `load_session`. `GET` returns the saved preview with `freshness: current | stale | unknown` calculated from available source revisions. It never claims a stale stored configuration is current.
- Explicit `POST .../resume` calls `load_session`, captures refreshed state, then `save_session`; it can invalidate questions and artifacts. Capture existing originals before refresh can replace configurations.
- Define `session_revision` as an opaque SHA-256 digest of the exact persisted session bytes, exposed as an ETag and in the envelope. This handles existing CLI-written sessions without adding an incompatible core dataclass field. It is a concurrency token, not a sequential counter.
- Every mutation checks `expected_session_revision` under the service gate, refreshes current V9 context, and validates the supplied task/question/source revisions against refreshed data before applying an answer or correction. Stale data returns 409 and the refreshed session. After saving, compute and return the new session token, even if only rejected-answer history changed.
- `answer_id` identifies a submitted answer; `client_request_id` provides request idempotency. Keep their mapping/result in the workbench journal, not in `ClarificationAnswer`. Reusing a request ID with a different payload returns 409.
- Atomic file replacement plus service serialization protects service-owned writes. The existing CLI does not participate in that lock. Initially prohibit simultaneous CLI and GUI mutation of the **same session**; detect externally changed hashes on the next request and return 409. This is not cross-process transactional safety. A later shared lock/repository change must be scoped and regression-tested before simultaneous writers are supported.

### Proposed HTTP contract

All paths below are new proposals under `/api/v1`, with strict Pydantic request validation. IDs are opaque strings. Session-writing requests include `client_request_id` and `expected_session_revision` except creation. Slow mutations return `Operation`; GETs return resources directly. Plan/task fields are retained losslessly alongside typed envelopes.

| Method/path | Request | Response / V9 boundary |
|---|---|---|
| `POST /sessions` | `{prompt, mode: "local_v9", client_request_id}` | 202 operation → `SessionEnvelope`; calls `create_session(prompt, verbose=False)`. Reject blank/oversized text before calling V9. |
| `GET /sessions/{session_id}` | None | 200 saved `SessionEnvelope` + ETag; passive saved JSON read, freshness indication. |
| `POST /sessions/{session_id}/resume` | Mutation header fields | 202 → refreshed/saved envelope; calls `load_session`, then `save_session`. |
| `POST /sessions/{session_id}/answers` | Mutation fields plus `answer_id`, `task_id`, and `answer` below | 202 → envelope with `{answer_id, accepted, feedback}`; validate task ownership and call `apply_answer` with the exact dataclass fields. |
| `POST /sessions/{session_id}/corrections` | Mutation fields plus `task_id`, `task_revision`, `source_revision`, `field_path`, `raw_input` | 202 → envelope and acceptance result; calls `apply_correction`. Raw replacement text is required by today's function. Do not invent a general JSON Patch semantic. |
| `POST /sessions/{session_id}/confirm-order` | Mutation fields plus `source_revision`, `ordered_task_ids` and task revisions | 202 → envelope; list must exactly equal the current proposed order before `confirm_session_order`. Reordering is not implemented by this function. |
| `GET /sessions/{session_id}/plan` | None | Saved plan plus session revision/freshness; no independent rendering call. |
| `GET /sessions/{session_id}/tasks/{task_id}` | None | Saved task with evidence, issues, compatibility summary and artifact references; verify ownership. |
| `GET /sessions/{session_id}/artifacts` | None | Generated-artifact metadata/content references for that session, with current/superseded state. |
| `GET /inventory/devices` | Optional text/site/vendor filters | `{inventory_revision, devices, provenance: "synthetic"}` from the shared JSON source. |
| `GET /inventory/devices/{device_id}` | None | `{inventory_revision, device}`; stable string ID. |
| `POST /inventory/devices` | `{expected_inventory_revision, device: DeviceInput}` | 201 device + new revision after atomic validation/write. Server allocates immutable ID. |
| `PUT /inventory/devices/{device_id}` | `{expected_inventory_revision, device: DeviceInput}` | 200 merged permitted fields + revision; immutable ID, preserve opaque legacy metadata. |
| `DELETE /inventory/devices/{device_id}` | Expected inventory revision via `If-Match` | 200 `{deleted_device_id, inventory_revision, stale_session_ids}` or 409 if protected references exist. |
| `GET /artifacts/{artifact_id}` | None | Immutable original, provenance, validation snapshot and task/device context. |
| `PUT /artifacts/{artifact_id}/draft` | `{expected_draft_revision, base_original_hash, content}` | Saved draft + new revision, always its own validation status. Null expected revision creates the first draft. |
| `GET /artifacts/{artifact_id}/draft` | None | Draft or 404; no fallback that overwrites the original. |
| `GET /runtime/status` | None | Availability/authority response below; no index ingestion, publication or model generation. |
| `GET /operations/{operation_id}` | None | Transport job state/result/error; separate namespace from V9 catalog operation IDs. |

Example answer request (illustrative opaque IDs, not repository records):

```json
{
  "client_request_id": "request-uuid",
  "expected_session_revision": "sha256-of-saved-session",
  "answer_id": "answer-uuid",
  "task_id": "intent-1:dev-r1",
  "answer": {
    "question_id": "question-id-from-server",
    "revision": 3,
    "source_revision": "source-revision-from-server",
    "kind": "selection",
    "raw_input": "",
    "selected_ids": ["option-id-from-server"]
  }
}
```

For a custom answer, send `kind: "custom"`, raw text and an empty selected-ID list. A literal `1` remains a value, not “option one.” GUI forms may display all questions but initially enable only the server's current next question.

`SessionEnvelope` is proposed as `{api_version: 1, session_revision, session: session_to_dict_payload, mode, fixture_id, freshness, inventory_revision, artifact_refs, last_submission}`. `mode` is `local_v9` or `replay`; shell-only mocks do not pretend to be saved sessions. `fixture_id` is null for local V9. Task vendor compatibility summary must expose the actual mode, schema/template checks and original issues, with `supported | blocked | unknown`; do not upgrade missing checks to “supported.”

`RuntimeStatus` reports independently:

- `service`: local composition ready/unavailable and permitted mode.
- `llm`: reachable/model_available/unknown, configured model name, observed time and error code.
- `embeddings`: model availability separately from generation availability.
- `retrieval`: ready/stale/offline/unavailable/unknown, model/index metadata and reason.
- `knowledge`: configured runtime mode, effective runtime authority, authoring authority, active snapshot ID, context/source revisions and validity.
- `inventory`: synthetic provenance and current revision.

[app/llm.py](../app/llm.py) constructs ChatOllama with a 30-second client timeout; [app/embeddings.py](../app/embeddings.py) constructs OllamaEmbeddings; [app/vectorstore.py](../app/vectorstore.py) checks collection/catalog or release metadata and can reject missing/stale indices. Exact catalog requests can avoid semantic retrieval, but incomplete extraction can still call a model. There is no existing unified availability function. Implement bounded read-only probes and report `unknown` when verification was not performed. Merely connecting to Ollama does not prove the required models or index exist. Do not use ingestion as a health check.

### Errors and state changes

Proposed error envelope: `{error: {code, message, retryable, details}, request_id, current_session?}`. Preserve structured V9 issues in `details`; sanitize transport exceptions rather than exposing tracebacks or credentials.

| Condition | HTTP/result handling | User behavior |
|---|---|---|
| Unknown session/task/device/artifact | 404 (or failed operation with equivalent code) | Keep current view; show resource missing. |
| Malformed request/unsupported field path/invalid answer value | 422 / `ANSWER_REJECTED` | Show server feedback without losing the entered value; render refreshed question if supplied. |
| Session/question/task/source/inventory/draft changed | 409 / specific stale code | Reload current state and require explicit review; never auto-replay the old selection. |
| V9 needs clarification/confirmation | Successful domain result | Present question/order confirmation; not a transport failure. |
| Unsupported vendor/operation or request-wide validation issue | Domain issues with blocked preview | Explain the actual issue and keep original parameter evidence. No substitute command. |
| Render/context failure | Session `failed` plus plan issues | Suppress current-preview claims; retain historical originals clearly marked stale/superseded. |
| Model/index unavailable | 503 if no session result; otherwise preserve V9's partial/clarification result | Offer explicit replay mode or retry. No silent fixture substitution. |
| Interrupted job, uncertain timeout outcome | Operation `interrupted`; retryability explicit | Reload/result lookup before issuing another mutation. |

Adapter prechecks provide stable stale-error codes without parsing English feedback. Existing free-text V9 rejections that cannot be classified reliably map to a generic rejected-submission code while retaining the message. A future typed V9 error refactor is separate work.

## 4. Shared demo inventory

**Decision:** Retain [data/inventory/devices.json](../data/inventory/devices.json) as the initial persisted authority, with a new validated JSON repository around writes. This directly matches `load_inventory()` and avoids a second database or a generated mirror. The browser holds a response cache only. SQLite authoring and published knowledge remain separate and untouched.

### Device model

Use V9's current names and string identity:

- Required: immutable `id` (server assigned on create), `hostname`, `kind`, `vendor`, `platform`, `version` as a string, `site`, `role`, `interfaces`, and `capabilities.features`.
- Editable descriptive fields: `display_name`, `aliases: string[]`, `location`, `tags: string[]`, optional `management_ip` and `primary_ip4`, and a recorded administrative `status`. All are synthetic inventory facts, not live measurements.
- Interface entry: `name`, `aliases: string[]`, `type`, `enabled`, `role`, optional `neighbor: {device, interface} | null`. Validate names/aliases for per-device collisions and neighbor references. Preserve any additional existing interface attributes required by V9 policies.
- Capability data: category/operation feature IDs and `interface_name_style`; keep canonical V9 vendor tokens such as `cisco`, `huawei`, `juniper`, with separate platform/version. Do not copy FYP tokens such as `cisco_ios` into the vendor field.
- Existing `source_refs`, `ansible` and `monitoring` metadata is preserved opaquely on updates; it does not enable integrations. The GUI neither collects credentials nor treats those fields as runnable instructions. Future external IDs belong to a separate mapping boundary.

Validation rejects duplicate immutable IDs, case-insensitive hostnames and ambiguous identity aliases, malformed addresses and invalid field shapes. Capability declarations cannot override template/schema compatibility. New unsupported platform/version combinations may be stored with `compatibility: unknown/blocked`, but cannot be advertised as renderable. Do not silently expand supported capabilities.

### CRUD and propagation

1. Read current bytes, validate the expected inventory revision and entire proposed list under the service mutation gate.
2. Apply only allowed fields; preserve opaque legacy metadata. Validate identity and reference integrity before writing.
3. Save a recoverable previous copy under proposed `storage/workbench/inventory_backups/`; write a sibling `.tmp` file and atomically replace `devices.json`. Keep backups outside `data/inventory`, since JSON there participates in context hashes.
4. Return `inventory_revision = SHA256(exact inventory bytes)` and invalidate GUI response caches. The revision is not V9's broader `source_revision`.
5. Subsequent V9 `load_inventory()` calls read the new records. `target_query.vocabulary()` builds names/sites/roles from those records using [data/inventory/attributes.json](../data/inventory/attributes.json); normal new devices do not require retraining or Chroma re-ingestion. New kinds of searchable fields may require an explicitly scoped attribute-schema change.

Changes to the existing JSON location also change V9 context/source hashes. On the next explicit session resume, V9 re-resolves targets, refreshes parameter evidence, and can ask for target confirmation if binding/group membership changed. Old question revisions are rejected. The GUI flags saved sessions stale immediately when their recorded inventory revision differs; it must not resume them automatically behind the user.

Deleting or renaming a device must not silently rewrite old sessions. Preserve the stable ID on edits, retain historical device snapshots in artifacts, and force explicit session revalidation. References from other devices' neighbor entries or [data/planned/parameters.json](../data/planned/parameters.json) block deletion with a structured 409 list until a separate explicit edit resolves them. Renaming with neighbor references is similarly blocked unless an explicit atomic reference update is designed. Existing session references alone can become stale; list affected sessions in the deletion result. V9's group membership and missing-device behavior needs targeted tests before enabling CRUD.

Initial service serialization covers concurrent GUI edits and planning calls. Out-of-band edits remain detectable by hash checks, but are not fully transactional with the CLI. Do not claim a pinned inventory snapshot across multiple uncached reads; implementing shared snapshot/lock support is a later compatibility task if concurrent writers are required.

Future NetBox integration can implement the same inventory boundary with explicit import/sync conflict policy and external-ID mapping. Do not maintain two competing authorities or schedule automatic synchronization in this milestone.

## 5. Monaco generated artifacts and working drafts

V9 currently returns inline configuration dictionaries within tasks; it does not assign persistent artifact IDs or manage free-form drafts. The following are proposed workbench records stored outside knowledge data/releases:

| Record | Fields and rules |
|---|---|
| `GeneratedArtifact` | Immutable `artifact_id`, `session_id`, saved session revision, `task_id`, logical intent ID, task revision, `device_id`, device snapshot, operation/vendor/platform/version, source/context/inventory revisions, knowledge snapshot/authority, exact content, content hash, creation time, provenance mode/fixture ID and validation snapshot. |
| `WorkingDraft` | `draft_id`, `artifact_id`, `base_original_hash`, exact content/hash, opaque draft revision, update time, `validation: unvalidated | passed | failed | stale` with validator identity and validated content hash if such a validator later exists. |
| `EditorDocument` | UI-only model URI, artifact/draft ID, session/task/device keys, title, active state, cursor/view state and dirty flag. Original and draft use different model URIs. |

Store originals as create-once JSON records in proposed `storage/workbench/artifacts/` and drafts in `storage/workbench/drafts/`, with temporary-file replacement for draft saves and optimistic concurrency. Artifact identity includes session/task/device plus generation context and content hash; identical reads do not generate duplicates, and regenerated output under changed context becomes a new original. Preserve prior originals and their drafts as superseded records.

Before a service mutation refreshes V9 outputs, preserve the prior saved originals; after a ready result, capture new outputs. A crash between core session save and artifact capture must be recoverable by scanning the saved session and completing deterministic capture on the next request. Durable coordination and legacy-session bootstrap need implementation tests. Never overwrite core session files with draft text.

Per-device tabs are grouped under task/intent. A device with two intents has two distinct documents; key by artifact ID, not hostname. Opening an original is read-only. “Edit draft” derives a working draft from that exact original. Closing a dirty tab requires save/discard/cancel behavior once persistence exists; Iteration 1 can retain drafts in memory and label reload loss explicitly.

Monaco `DiffEditor` receives original and draft text with separate stable model URIs and the original side read-only. Preserve line order, repeated commands and exact saved bytes; do not use line sets or normalize away meaningful whitespace to decide equality. Dispose models/listeners when their ownership ends and preserve undo/view state while switching open tabs.

Generated validation means **V9 parameter/context/template checks passed at generation under the recorded authority**, not validation on a device. Current file mode and published mode have different compatibility checks; expose that distinction. Any edit creates an unvalidated draft even when the original passed. A later draft validator may mark a particular draft hash passed for a named validation scope; subsequent edits invalidate that result. Monaco syntax highlighting does not confer validation. There is no existing V9 arbitrary-config-text validator to reuse.

## 6. End-to-end flow and demo modes

```text
User prompt → typed client → FastAPI SessionService → create_session/run
  → V9 planning/retrieval/target resolution/parameter validation
  → persisted session + structured questions OR ready generated configurations
  → operation result → GUI task workspace and current-question form

Answer with IDs/revisions → concurrency + source prechecks → apply_answer
  → refresh whole plan → save session → capture immutable originals → GUI preview

Inventory form → InventoryService → atomic devices.json replacement
  → next V9 inventory read sees new records → old sessions flagged stale

Monaco edit → separate WorkingDraft → draft store
  → original/draft DiffEditor; no change to V9-generated source
```

Three explicitly labelled modes are required:

1. **Shell mock (Iteration 1):** Bundled synthetic records, sample configurations, local messages and activity. No HTTP client or AI calls; every mock reply says it is a demonstration. State resets on refresh. No generated/validated claims.
2. **Local V9 (later):** Real local Python session functions with configured Ollama and Chroma when available. Show independent generation, embedding/index and knowledge status. Deterministic V9 fallback remains real V9 behavior, but do not claim model/RAG participation without evidence; current persisted trace cannot prove every call.
3. **Replay (later):** An explicit fixture choice with fixture ID/version, synthetic inventory snapshot, recorded provenance and ordered allowed transitions. A ReplaySessionAdapter emits the same GUI envelopes from fixtures. Unexpected answers are rejected as outside the recording. Use separate replay session/storage identities and never mutate live V9 sessions or inventory. Original recorded validation is historical, not current-runtime validation.

Unavailable services offer a user-selected replay path; they never silently convert a local V9 request into a successful fixture. Runtime status must not publish releases, rebuild embeddings or call external infrastructure. No SSH, NetBox, Ansible/Terraform, telemetry or remote device actions are mounted.

## 7. Risks and implementation verification gates

The five highest-priority architectural risks are:

1. **Session refresh and concurrency:** Load re-renders, task feedback is not an exception, and no whole-session CAS exists. Verify passive GET, explicit resume, duplicate submission recovery, stale question/source handling, and external CLI-change detection before integration.
2. **Mutable inventory and stale evidence:** Multiple uncached reads and group membership changes can invalidate bindings mid-workflow. Verify atomic JSON replacement, delete/reference constraints, new-device discovery, and stale-session behavior in both runtime modes.
3. **FYP side effects and dependency coupling:** Startup and inventory writes can activate live integrations. Reuse only the classified presentation pieces; test the new composition without importing FYP services or optional executors.
4. **Artifact provenance and validation:** Inline regenerated outputs currently have no durable artifact identity; edited command text has no V9 validator. Verify immutable originals, crash recovery, draft isolation, per-document models and honest validation labels.
5. **Runtime readiness and baseline uncertainty:** Model/index availability, knowledge authority and catalog drift are separate failure sources. Historical baseline failures remain unresolved; test contracts with isolated deterministic fixtures and perform live local verification only when services are available.

Additional implementation checks: Windows atomic-replace/backup behavior under OneDrive; process/thread ContextVar handling; local Monaco worker assets; accessibility of splitters/tabs; dependency versions and ownership/licensing for copied assets; and request size/queue limits. These are explicit verification gates, not claims that the implementation already works. No full FYP security or dependency audit was attempted.

### Existing regression sources inspected (not executed)

- [tests/test_clarification_flow.py](../tests/test_clarification_flow.py): stale answer/session round trip, numeric values versus selections, nested item identity, request-wide render gate and correction behavior.
- [tests/test_target_resolution.py](../tests/test_target_resolution.py): ambiguity/conflict, duplicate aliases, new inventory vocabulary, management-IP isolation and session target evidence.
- [tests/test_runtime_intent_integrity.py](../tests/test_runtime_intent_integrity.py): unsupported vendor intent retention, proposal ordering, correction/evidence rebinding and saved evidence refresh.
- [tests/test_native_vendor_runtime.py](../tests/test_native_vendor_runtime.py): vendor contracts, command semantics and mixed-request blocking.

These supply future regression targets; their current pass/fail status was not measured. Prior stabilization claims remain attributed to [docs/V9_RUNTIME_AUDIT.md](../docs/V9_RUNTIME_AUDIT.md).

## 8. Exact next iteration — VS Code-inspired workbench shell

**Single deliverable:** A browser-launchable local React/TypeScript workbench with all four regions and a functional Monaco editor, driven entirely by labelled in-memory mock content.

### Expected new files

All paths below are planned, not created by this audit:

```text
frontend/package.json
frontend/package-lock.json
frontend/index.html
frontend/vite.config.ts
frontend/tsconfig.json
frontend/tsconfig.app.json
frontend/tsconfig.node.json
frontend/eslint.config.js
frontend/.gitignore
frontend/README.md
frontend/src/main.tsx
frontend/src/vite-env.d.ts
frontend/src/app/App.tsx
frontend/src/app/WorkbenchProvider.tsx
frontend/src/app/workbenchReducer.ts
frontend/src/app/types.ts
frontend/src/components/layout/WorkbenchLayout.tsx
frontend/src/components/layout/ResizeHandle.tsx
frontend/src/components/layout/StatusBar.tsx
frontend/src/components/icons/RouterIcon.tsx
frontend/src/components/icons/ServerIcon.tsx
frontend/src/features/explorer/ExplorerPanel.tsx
frontend/src/features/workspace/WorkspacePanel.tsx
frontend/src/features/workspace/EditorTabs.tsx
frontend/src/features/workspace/ConfigurationEditor.tsx
frontend/src/features/workspace/monacoSetup.ts
frontend/src/features/chat/ChatPanel.tsx
frontend/src/features/chat/ChatInput.tsx
frontend/src/features/activity/ActivityPanel.tsx
frontend/src/fixtures/workbenchDemo.ts
frontend/src/styles/workbench.css
frontend/tests/workbench.spec.ts
frontend/playwright.config.ts
```

Update progress and decisions only as actual implementation evidence warrants. Small organization adjustments are acceptable if recorded; adding backend features is not.

### Reuse and dependency budget

Reuse ChatInput and the two SVG assets with the minor adaptations in the audit. Adapt layout/editor options visually from AnsibleStudioView/PlaybookEditor, but write new controllers, document types, splitters and state. No imports may reach back into the FYP source tree.

Runtime dependencies: React, React DOM, `@monaco-editor/react`, explicit `monaco-editor` for local worker/assets, and Lucide icons if used by the reused input. Development dependencies: TypeScript, Vite/React plugin, React/Node types, ESLint and the relevant TypeScript/React plugins, plus Playwright for one real-browser smoke suite. Pin compatible versions in the new lockfile during the implementation iteration; FYP declaration ranges are reference evidence only. No Tailwind/DaisyUI, AI SDK, topology engine, xterm, backend package, or state-library dependency is needed. Use scoped CSS and a fixed local Monaco theme. Dependency installation belongs to the explicitly assigned implementation scope, never this audit.

### In scope

- Four visible regions with explorer selection, device/task-labelled editor tabs, chat composer and output/activity tabs.
- Two or more synthetic device examples and clearly labelled sample vendor configuration documents.
- Editable Monaco working copies with undo/redo and stable model identity; tab switching preserves in-memory content and view state.
- Read-only sample originals retained in fixture/state; editable copies labelled unvalidated. Persistence and diff UI are deferred.
- In-memory chat echo and a fixed, explicitly mock response; local activity for selection/edit/chat events.
- Bounded resizable panels with keyboard access and a sensible minimum-size layout.
- Visible “Local mock — no AI/backend connection; changes reset on reload” notice.
- A local-bundled Monaco setup with loading/error UI; actual browser verification.

### Out of scope

Real V9/FastAPI integration, session or inventory persistence, inventory CRUD, model selection, replay engine, semantic validation, topology visualization, artifact service, persistent drafts, diff workflow, authentication, live connectivity and deployment.

### Acceptance criteria and verification

1. From `frontend/`, `npm run dev -- --host 127.0.0.1` opens a usable workbench; README states prerequisite versions and local URL. Production build succeeds with TypeScript checking.
2. All four regions are present at 1440×900 and remain usable at 1280×720; side panels can be resized within bounds by pointer and keyboard without obscuring the central editor.
3. Selecting either synthetic device opens/selects its correct sample configuration. Typing into Monaco, undo/redo, switching tabs and switching back retain that document's in-memory changes without altering its original.
4. Chat submission produces a labelled mock reply and activity entry; empty/IME-in-progress input is not submitted incorrectly.
5. Output/activity tabs display local events. No control claims measured connectivity, real AI generation or validation.
6. Reload intentionally resets mock state. No inventory, session or draft persistence has been introduced.
7. Browser network inspection confirms assets/workers load locally and no calls are made to V9, Ollama, NetBox or other external services. No missing Monaco-worker or uncaught console error occurs.
8. Type checking/build, lint and the focused browser smoke test pass; failures and environment limitations are recorded truthfully.

Planned package scripts/commands: `npm run build` (`tsc -b && vite build`), `npm run lint`, and `npm run test:e2e` (Playwright). The smoke suite covers region presence, real Monaco edit/tab retention, mock chat, splitter interaction and absence of external/service requests; do not rely solely on a mocked Editor component. Browser binaries, if absent, must be handled within the authorized implementation setup. No FYP backend test collection is needed. This is planning only: none of these commands ran in Iteration 0.

## 9. Iteration 0 handover

1. **Identifier/objective:** Iteration 0; source-grounded V9/FYP integration and selective-reuse design.
2. **Completion status:** Completed for the bounded documentation deliverable. Proposed implementation behavior remains unverified until its assigned iteration.
3. **Files:** Added `05_FYP_REUSE_AUDIT.md` and this document; updated `01_ARCHITECTURE.md`, `03_DEVELOPMENT_PROGRESS.md`, `04_ARCHITECTURE_DECISIONS.md`. No files removed. Pre-existing dirty-worktree changes preserved.
4. **Decisions:** New V9-root frontend and isolated FastAPI composition; small presentation reuse; existing JSON inventory authority; explicit saved-read/resume semantics; opaque concurrency tokens; immutable originals and separately validated drafts; explicit mock/local/replay provenance. Reasons and feasibility gates appear above.
5. **Verification:** Documentation/source-path and declared-function checks only; exact reproducible commands and outcomes follow. No application imports, runtime tests, builds, installations, migrations, AI calls or FYP test collection. Historical baseline results were not rerun or relabelled.
6. **Remaining issues:** The five risks and implementation gates above, including historical non-green tests, Ollama availability and unrelated catalog drift. None blocks producing this design; all limit implementation-readiness claims.
7. **Suggested next iteration:** Only the shell scope in section 8.
8. **Reproduction:** Open the linked source at the specified functions and compare to the tables. Run the read-only verification commands below from the V9 root. Then stop; this report is not an instruction to begin implementation.

### Documentation verification commands

Run the following PowerShell block from the V9 root. It verifies every local Markdown source link in the two audit documents, required sections and trailing whitespace. Expected result: `PASS: audit source links and document structure`.

```powershell
$auditDocs = @('app_main_documents/05_FYP_REUSE_AUDIT.md', 'app_main_documents/06_GUI_INTEGRATION_DESIGN.md')
foreach ($doc in $auditDocs) {
    $text = Get-Content -Raw -LiteralPath $doc
    foreach ($match in [regex]::Matches($text, '\]\(([^)]+)\)')) {
        $target = Join-Path (Split-Path $doc) $match.Groups[1].Value
        if (-not (Test-Path -LiteralPath $target)) { throw "Missing source: $target" }
    }
    if ($text -match '(?m)[ \t]+\r?$') { throw "Trailing whitespace: $doc" }
}
$design = Get-Content -Raw -LiteralPath $auditDocs[1]
foreach ($heading in @('## 1.', '## 2.', '## 3.', '## 4.', '## 5.', '## 6.', '## 7.', '## 8.', '## 9.')) {
    if (-not $design.Contains($heading)) { throw "Missing heading: $heading" }
}
Write-Output 'PASS: audit source links and document structure'
```

The source-interface check uses Python's AST parser without importing V9 modules. This exact PowerShell command was run from the V9 root:

```powershell
@'
import ast
from pathlib import Path
expected = {
    'app/clarification.py': 'ClarificationSession create_session session_to_dict load_session save_session apply_answer apply_clarification apply_correction confirm_session_order',
    'app/pipeline.py': 'run refresh_plan resume_task correct_task plan_to_dict confirm_order',
    'app/planner/models.py': 'OperationIntent PlannedTask ExecutionPlan ClarificationAnswer',
    'app/questions.py': 'build_questions selected_options answer_from_text',
    'app/planner/intent_planner.py': 'plan_intents',
    'app/retrieval/category_classifier.py': 'classify_category',
    'app/retrieval/operation_retriever.py': 'retrieve_operation_candidates',
    'app/retrieval/operation_selector.py': 'select_operation',
    'app/parameters/parameter_extractor.py': 'extract_parameter_result ExtractionResult',
    'app/parameters/schema_loader.py': 'load_schema',
    'app/parameters/validator.py': 'validate_parameter_result ValidationResult ValidationIssue',
    'app/devices/context_validator.py': 'normalize_parameters_for_device validate_device_context',
    'app/devices/inventory.py': 'load_inventory',
    'app/devices/target_query.py': 'extract_target_queries parse_description load_attributes',
    'app/devices/target_resolver.py': 'resolve_queries resolve_intent_targets',
    'app/templates/template_selector.py': 'select_template template_binding',
    'app/templates/renderer.py': 'render',
    'app/context.py': 'source_revision context_revision',
    'app/knowledge/runtime.py': 'snapshot_scope snapshot_request current_snapshot active_snapshot',
    'app/knowledge/authority.py': 'authority',
    'app/config.py': 'runtime_mode',
}
count = 0
for filename, symbols in expected.items():
    tree = ast.parse(Path(filename).read_text(encoding='utf-8-sig'))
    declared = {node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
    missing = set(symbols.split()) - declared
    assert not missing, (filename, missing)
    count += len(symbols.split())
print(f'PASS: {count} V9 symbols across {len(expected)} source files; no application imports')
'@ | python -B -
```

Observed result: `PASS: 51 V9 symbols across 21 source files; no application imports`, exit 0. The local Miniconda launcher also printed `Failed to find real location of D:\Miniconda\python.exe`; the AST command nevertheless completed successfully. This verifies declarations, not runtime behavior. Function signatures and control flow were inspected directly in the linked sources.

Documentation link/structure check: passed, 75 local source/document links resolved. Required design sections and whitespace checks passed. `git diff --check -- app_main_documents/01_ARCHITECTURE.md app_main_documents/03_DEVELOPMENT_PROGRESS.md app_main_documents/04_ARCHITECTURE_DECISIONS.md app_main_documents/05_FYP_REUSE_AUDIT.md app_main_documents/06_GUI_INTEGRATION_DESIGN.md` returned exit 0; because these documents reside in an untracked documentation tree, the explicit content checks above are the meaningful whitespace evidence, not Git alone.

Content-hash guard: SHA-256 manifests were compared before and after documentation edits for the application, tests, data and FYP source/configuration files, plus `main.py`, `AGENTS.md`, product vision and iteration protocol (excluding dependency directories and bytecode). Result: **864 before / 864 after; zero changed, added or missing protected files**. This is a scope-preservation check, not additional architectural exploration. The exact manifest command used at both checkpoints was:

```powershell
$roots = @('app','tests','data','app_main_documents/Net_Topo_View-intentparse/frontend','app_main_documents/Net_Topo_View-intentparse/backend')
$paths = @(rg --files $roots -g '*.py' -g '*.ts' -g '*.tsx' -g '*.json' -g '*.sql' -g '*.css' -g '*.j2' -g '!node_modules' -g '!__pycache__' -g '!package-lock.json')
$paths += @('main.py','AGENTS.md','app_main_documents/00_PRODUCT_VISION.md','app_main_documents/02_ITERATION_PROTOCOL.md')
$hashes = foreach ($path in $paths) { $h=Get-FileHash -LiteralPath $path -Algorithm SHA256; [pscustomobject]@{Path=$path; Hash=$h.Hash} }
$hashes | ConvertTo-Json -Compress
```

The two returned manifests were compared by path/hash in tool memory without writing repository files. All five changed documents also passed explicit trailing-whitespace and balanced-code-fence checks. Final review confirmed consistent precedence, scope and historical-result attribution. Iteration 1 remains planned and unstarted.
