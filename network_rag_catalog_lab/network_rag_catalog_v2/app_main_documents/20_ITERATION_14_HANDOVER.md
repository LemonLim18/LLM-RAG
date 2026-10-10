# Iteration 14 — V9-authoritative editing of the active working document

## 1. Iteration identifier and objective

Deliver one real Local V9 instruction → bounded proposal → native inline review → explicit Accept/Reject → separate Ctrl+S workflow for the active working file. Preserve immutable originals, V9 sessions, shared inventory, knowledge authority and the CLI. No new planning sessions are created by document editing.

## 2. Completion status

**Completed (2026-10-10)** for the bounded SW1/Cisco VLAN-name proposal workflow. All 118 workbench backend checks, 20 new edit browser checks, 20 existing review checks, 40 established browser regressions, both edit and existing review save/restart integration checks, lint/build and CLI help pass. Two optional live planning/OSPF browser tests were skipped. Separately, actual configured model inference succeeded for two successive unsaved-base edits. Iteration 15 was not started.

## 3. Files added, modified or removed

Paths relative to the repository root; this is not a claim that all pre-existing Git changes belong to Iteration 14.

Added:

- `app/document_edits.py` — small V9-owned interpretation and bounded patch/render adapter.
- `app/workbench/edit_models.py`, `app/workbench/edit_service.py` — typed compute-only boundary and read/recheck coordination.
- `frontend/src/services/editApi.ts` — bounded transport and source-response verification.
- `frontend/src/features/chat/useDocumentEdit.ts` — instruction/pending/error handling and existing proposal staging.
- `tests/test_workbench_edits.py` — isolated production-adapter tests with controlled interpretation.
- `tests/workbench_edit_server.py` — isolated real API test server; only interpretation is doubled.
- `tests/workbench_edit_smoke.py` — explicit real configured-model smoke with temporary documents.
- `frontend/edit-tests/document-edit.spec.ts`, `frontend/playwright.edits.config.ts` — 20 actual-Monaco producer tests.
- `frontend/edit-integration/persistence.spec.ts`, `frontend/playwright.edit-integration.config.ts` — real API/save/backend-and-browser restart test.
- `app_main_documents/20_ITERATION_14_HANDOVER.md`.

Modified:

- `app/workbench/api.py` — one synchronous worker-thread proposal route; existing routes retained.
- `frontend/src/features/chat/ChatPanel.tsx`, `ChatInput.tsx` — explicit Edit active file mode, context, feedback and bounded instruction input.
- `tests/test_workbench_planning.py` — exact authorized POST-route assertion includes the new compute-only endpoint.
- `app_main_documents/03_DEVELOPMENT_PROGRESS.md`, `04_ARCHITECTURE_DECISIONS.md`.

Source files removed: none. One verified temporary synthetic-session fixture left by the interrupted sandbox test was cleaned up; it was test-owned and reproducible, not user session data. No dependencies, commits, historical FYP edits, core planner/clarification/persistence refactors, inventory/catalog data changes, generated-artifact writes or new database.

## 4. Architectural decisions and reasons

### Verified existing V9 contracts and supported scope

`create_session()` creates a new persisted plan; `apply_answer()` mutates an existing pending question. Neither is an arbitrary working-file editor. They are **not** called or disguised as edit operations. The new bounded adapter lives in `app/document_edits.py` and reuses `app.llm.llm`, `catalog.get_operation()`, `parameters.schema_loader.load_schema()`, `parameters.validator.validate_parameter_result()`, `devices.inventory.load_inventory()`, `devices.target_query.parse_description()`, `devices.target_resolver.resolve_queries()`, `devices.context_validator.validate_device_context()` and `templates.renderer.render()`.

The actual catalog has `rename_vlan`, category `vlan`, requiring `vlan_id` and `new_vlan_name` for Cisco. Its Cisco template renders `vlan <id>`, ` name <name>`, ` exit`. The existing `c9300_vlan_rename_v1` policy additionally requires a reviewed hardware/NOS profile, declared capability policy, source references and recorded VLAN facts. **R1/VLAN 100 does not qualify.** The existing synthetic SW1 (`lab-sw1`, Catalyst 9300, IOS XE 17.9) has the reviewed facts and VLAN 20 `STAFF`. Accordingly the verified demonstration uses **SW1/VLAN 20**, not invented R1/VLAN 100 facts. No policy, capability or inventory record was weakened to pass the example.

The existing `extract_parameter_result()` is a schema-filling service that may bypass inference for deterministic literals and retain deterministic extraction when the model is unavailable. That is valid for its existing callers but insufficient for this iteration's explicit real-model edit interpretation/failure contract. The narrow new interpreter therefore calls the same configured V9 model directly and retains existing schema/device/render validators, rather than changing or weakening the established extractor.

Only Cisco IOS XE files with verified VLAN-operation provenance are supported. The specific existing policy decides eligible hardware/version/VLANs; the platform label alone does not grant support. The source operation's category is checked against current V9 knowledge. Other vendors, missing/replaced devices, stale device metadata and unsupported policy contexts fail explicitly. This is not a new universal intent engine.

The configured real model interprets one natural-language instruction into a strict structured `Interpretation`: outcome, operation, VLAN ID, new name, optional stated old name and target description. Native Ollama schema-constrained output is used through the existing `app.llm.llm` object, retaining its configured model/temperature/client timeout. It sees the instruction, bounded current VLAN/name lines, safe device identity/platform metadata and the actual enriched operation schema; it receives no credentials or arbitrary internal paths. Current-buffer lines are marked untrusted data. No regex-only answer or mock fallback exists in production.

The operation is already scoped by the active VLAN document, so this workflow uses **exact catalog/schema/template lookup**, not Chroma operation search. It does not initialize embeddings, ingest knowledge or claim semantic retrieval readiness. Model-produced parameters must occur literally in the instruction and satisfy V9 schema and device policy. Explicit conflicting inventory references are rejected; model-extracted target descriptions must be literal and resolve uniquely to the active device through V9. Missing values return clarification-required, not inferred defaults or fabricated session progression.

### Source → proposal → accepted buffer

1. `useDocumentEdit` captures `working.proposalBase(id)`: document ID, confirmed saved UUID revision, buffer epoch and exact current accepted text, including unsaved manual/previously accepted edits.
2. Backend reads `read_document()` and its independently verified `read_original()`. Embedded original metadata must match exactly. The immutable original is the captured source association; the originating V9 session need not be refreshed or rewritten, and later session changes do not replace this document's provenance.
3. Under the existing `PlanningService.mutate_working_document()` gate, verify revision, current device/metadata, catalog operation/schema and source revision. Pin the existing knowledge snapshot ContextVar for published mode. No write occurs despite the gate method's historic name.
4. Release the gate. Invoke the configured model for structured interpretation only, not whole-file generation. An independent nonblocking per-application edit lock permits one edit inference at a time; duplicate simultaneous requests return `EDIT_BUSY`.
5. Reacquire the shared gate. Re-read document/original; compare saved revision, runtime mode, source revision and logical inventory content. Validate parameters/device policy; render through the existing V9 Jinja path and check the expected narrow rename grammar. Recheck source revision before returning.
6. Locate exactly one top-level existing VLAN stanza and one indented name token. Refuse absent/duplicate/ranged declarations, duplicate names, unknown nested grammar, multiline banner/macro/certificate contexts and conflicting stated old names. Replace **only that name token** with the V9-rendered value. Unrelated lines, whitespace, BOM and newline characters are not re-rendered or normalized.
7. Frontend verifies response document/revision/exact-base UTF-8 digest. It passes the captured base and proposed text to existing `stageProposal()`; it does not write accepted content directly. Existing revision/epoch/exact-text/active-editor guards remain authoritative. A navigation/mode generation guard also rejects switching away and back while waiting.
8. Native inline review uses Iteration 13 unchanged. Accept modifies only the buffer and retains undo; Reject changes nothing. A later instruction captures the newly accepted buffer. Only explicit existing Ctrl+S/Save persists via the unchanged revision-checked PUT.

No second working store, planner, artifact, pending-proposal database, general agent framework, save shortcut or frontend network-semantic interpretation was introduced. Sample/original/preview identities and Monaco lifecycle remain unchanged.

### API contract and failure handling

`POST /api/v1/workbench/working-documents/{document_id}/propose-edit`

Request: `{expected_revision: UUID, current_content: string, instruction: string}`. Document IDs use the existing `working-<64 hex>` validator. Extra authoritative context fields are forbidden. Instruction: nonblank, at most 2,000 characters. Buffer: at most 65,536 characters **and** 64 KiB UTF-8; this intentionally narrower AI limit does not reduce the existing 1-MiB working-file storage limit.

Typed `EditResponse`: API version, document ID, base revision, SHA-256 of exact UTF-8 base text, transient proposal UUID, outcome (`proposal`, `no_change`, `clarification_required`, `unsupported`), safe message, proposed content when applicable, operation/parameters/evidence and observed runtime/model/source authority. `validation: bounded_operation_only`, `deployment: not_deployed` are explicit. `direct_files` has no invented release ID. A proposal UUID is not a persisted artifact/request-journal identity.

Input/schema/target/block failures are 422; missing files 404; stale/corrupt/association conflicts 409; invalid structured model output 502; model/context/storage/busy failures 503. Existing safe storage errors retain their codes. No raw upstream exception or filesystem path is returned. Responses have `Cache-Control: no-store`. Sync FastAPI routing runs expensive work off the event loop; model calls are outside the global mutation gate.

The browser waits up to 45 seconds; the existing Ollama client timeout is 30 seconds per client operation, with a 512-token output bound. HTTP abort is **not** server cancellation. Late inference can finish, but this endpoint cannot persist or accept its result. No automatic retry, replacement instruction, new session or save occurs. A fresh explicit request may recompute a proposal; no durable exactly-once or result-recovery guarantee is claimed. One application/process is supported; independent CLI/multi-worker writers and source change-then-revert during inference remain outside the coordination guarantee.

The right panel distinguishes Demo mock, Local V9 planning and Edit active file. Current file identity is visible; samples/originals/inactive working views cannot submit. Pending requests disable duplicate sending while leaving Monaco usable. Errors retain local content. Clarification-required asks for a complete new instruction; no answer/resume engine is invented. The last interpretation is labelled with its own document ID, not silently reassigned after navigation.

### Validation and historical boundaries

The new name operation is checked against current V9 knowledge/device constraints; the **whole working document remains historical, unvalidated and not deployed**. This is not running-config discovery, vendor certification, current inventory synchronization or global edited-config validation. Unknown file grammar is refused rather than rewritten. Existing mixed-EOL/BOM-change Monaco acceptance limitations remain explicit. Model interpretation quality is not guaranteed for every phrasing; invalid/unavailable output is an error, never a synthetic successful edit.

## 5. Tests, exact commands and outcomes

From repository root, always using the provided venv:

```powershell
& 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv\Scripts\python.exe' -m unittest tests.test_workbench_edits -q
& 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv\Scripts\python.exe' -m unittest discover -s tests -p 'test_workbench*.py' -q
& 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv\Scripts\python.exe' -m tests.workbench_edit_smoke
& 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv\Scripts\python.exe' main.py --help
git diff --check
```

From `frontend/`, sequential browser suites with ports 8000/5173 free:

```powershell
npm run lint
npm run build
npx playwright test --config playwright.edits.config.ts
npx playwright test --config playwright.edit-integration.config.ts
npx playwright test --config playwright.review.config.ts
npx playwright test --config playwright.review-integration.config.ts
npx playwright test
```

Results:

- Final focused backend run: **21 passed** (5.106 seconds). Final combined run: **118 passed** (101.961 seconds), comprising all 97 existing checks plus 21 edit checks. Expected injected planning-error logs are not failed tests. Coverage includes valid exact proposals, unsaved second bases, no-ops, BOM/CRLF/whitespace preservation, wrong/missing identities, corrupt originals, invalid/oversized inputs, missing parameters, unsupported edits, schema/evidence/target/device-policy failures, duplicate/ambiguous/multiline blocks, model timeout/malformed output, concurrent edit rejection, a real save during inference followed by stale rejection, changed source revision, current R1/VLAN100 rejection, and unchanged protected bytes/timestamps/source digest.
- New actual-Monaco browser suite: **20 passed**; final rerun 39.0 seconds. Real review/buffer isolation, accept/reject, explicit save, pending double-submit prevention, current unsaved and successive accepted bases, no-change/clarification/unsupported results, transport/errors, wrong response identity, navigation/mode/ABA/save races and prior proposal refusal are covered.
- Established browser suite: **40 passed, 2 skipped** (1.7 minutes). Planning, clarification, recovery, multi-device review, registration, inventory, samples, originals and working files remain intact. Skips are the optional live planning/OSPF checks, separate from the actual edit-inference smoke below.
- Existing native inline-review suite: **20 passed** (59.3 seconds), including undo/redo, cursor/model identity, disposal, stale proposal handling and exactness constraints.
- New browser/real-API/edit/save/restart integration: **1 passed**, rerun after final UI/parser changes (13.8 seconds including startup). Existing review/save/restart integration: **1 passed** (8.9 seconds including startup). No API/storage mocks in either; the new test doubles only model interpretation, while the old test injects a test proposal.
- Final `npm run lint`: pass. Final TypeScript/Vite build: pass, 2,340 modules, 12.34 seconds; main JS 3,081.45 kB / 817.43 kB gzip. Existing >500-kB Monaco warning remains, not a new failing check.
- CLI `main.py --help`: exit 0. Whitespace check: pass; all three changed documents have no trailing whitespace. Production assets contain no `__reviewTest` or controlled-test-producer strings. No broad historical catalog-suite or published-mode end-to-end rerun is claimed.
- Visually inspected the new isolated test's inline-review screenshot: one central real Monaco diff, exact STAFF/ENGINEERING deletion/addition, explicit SW1 working-file context, guarded proposal controls, separate save, Explorer and all three Copilot modes. Browser tests additionally inspect actual editor state; this is not a static-text substitute.

**Independent live evidence:** `tests.workbench_edit_smoke` used the actual configured `qwen2.5:1.5b`, real catalog/schema/device policies and renderer via the production FastAPI adapter with temporary original/working/session stores and a copy of the unchanged inventory. Both requests returned 200/proposal: SW1/VLAN 20 `STAFF → ENGINEERING`, then the unsaved first proposal buffer `ENGINEERING → FINANCE`. Persisted working text stayed `STAFF`. Direct-file authority/source revision and model name were returned. This is actual inference and exact knowledge lookup, **not** fresh Chroma/embedding/general-planner validation or live device work.

**Isolated browser evidence:** real HTTP → FastAPI → V9 validation/rendering → Monaco Accept → second current-buffer proposal → Ctrl+S → fresh backend interpreter/browser → Explorer reopen. Only model interpretation is doubled and the source session is a deterministic serialized fixture. Storage, APIs, catalog, device policy, rendering and Monaco are real. Original/session/inventory bytes and session mtime remain unchanged; exact requests are two existing capture/open POSTs, two proposal POSTs and one explicit save PUT. Temporary storage/process cleanup is bounded to the test-owned path.

Development findings: initial tests correctly rejected the assumed R1 policy; fixtures were changed to actual supported SW1/VLAN 20 without weakening validation. The first real inference call exposed the installed client's `num_predict` keyword contract; it belongs in `options`. A subsequent unconstrained JSON response failed strict validation. Native schema-constrained output then passed both real-model requests; no permissive fallback parser was added. Sandboxed venv launcher/Git/Node checks stalled or reported a base-interpreter path failure; final checks used the same required venv outside that sandbox, never global Python/Miniconda. Interrupted processes were stopped/collected. No older browser assertions were weakened.

## 6. Remaining issues and risks

- One operation/vendor/profile slice only. Existing catalog drift and the historical broad-suite 2 assertion failures / 192 example errors are not repaired or rerun as a green baseline.
- Exact catalog lookup only; no Chroma/embedding readiness claim. Two successful model interpretations do not certify arbitrary instructions, other vendors, all documents or published-release end-to-end behavior.
- No full-document validation, deployment, model fallback, multi-file edits, durable proposals, per-hunk decisions, clarification resume, automatic rebase, automatic save or proposal journal.
- At most one edit inference per backend application. No multi-worker/CLI coordination or cancellation/exactly-once guarantee. Short shared-gate phases can return busy if another mutation runs before completion.
- Strict source/device checks may refuse historical originals after inventory changes; no refresh/repair or invented compatibility is provided. Missing/corrupt originals block edits even though the independent working text may still be readable.
- Unsaved buffers/proposals are lost on reload. Existing stale/uncertain save inspection and single-process/power-loss/OneDrive limitations remain unchanged.
- Existing Monaco bundle-size warning (about 3.081 MB main JS), dependency advisories and broad catalog failures remain separate from new regression results.

## 7. Next single recommended iteration

**Iteration 15 candidate: bounded model-edit clarification for this same single-file VLAN-name workflow.** First design how a typed missing-value response can collect one value and revalidate the unchanged document base, without borrowing saved-plan answer semantics, autoaccepting, saving or adding another planner. No multi-file agents, extra operation families, knowledge UI or device execution. This is a recommendation only; Iteration 15 is not started.

## 8. Reproduction and verification

Backend, one worker, PowerShell:

```powershell
Set-Location 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\network_rag_catalog_lab\network_rag_catalog_v2'
& 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv\Scripts\python.exe' -m uvicorn app.workbench.api:app --host 127.0.0.1 --port 8000
```

Frontend, another PowerShell window:

```powershell
Set-Location 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\network_rag_catalog_lab\network_rag_catalog_v2\frontend'
npm run dev -- --host 127.0.0.1
```

At `http://127.0.0.1:5173`, open an existing SW1/VLAN working file through Explorer or the existing confirmed-output opener. Its source must be a verified VLAN-operation original matching current SW1 metadata and its buffer must contain one supported VLAN/name block. Choose **Edit active file**. For a VLAN 20 `STAFF` block submit `Rename VLAN 20 from STAFF to ENGINEERING`. Inspect the native inline proposal; accepted text remains STAFF until Accept Changes. Reject leaves it unchanged. After acceptance, submit `Rename VLAN 20 from ENGINEERING to FINANCE`; review again. Ctrl+S is a separate decision, never a side effect of chat or Accept. Reopen the original to confirm it is unchanged.

Do not invent a VLAN 100 inventory fact or use R1 to bypass policy. To verify without modifying real working/session/inventory storage, stop manual servers and run the isolated `playwright.edit-integration.config.ts` test. It owns the temporary SW1 fixture and a deterministic interpreter; use `tests.workbench_edit_smoke` separately for actual local inference. No model download or ingestion is performed. Stop after Iteration 14.
