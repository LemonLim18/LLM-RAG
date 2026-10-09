# Iteration 8 — Durable Creation-Outcome Lookup

Date: 2026-10-09

## 1. Iteration identifier and objective

Iteration 8 provides one outcome: explicitly recover a recorded planning creation using its original client request UUID after response loss/restart, without blindly invoking V9 again. Interrupted outcomes that cannot be proved remain indeterminate. No answer journal, inventory editing, refresh/resume, artifact persistence or device execution is introduced.

## 2. Completion status

**Completed** for the bounded single-workbench-process contract. The final backend run passed 57 tests (15 new receipt tests plus 42 existing regressions). Frontend lint/build and 19 deterministic automated Chrome checks passed; two opt-in live-AI tests were skipped. CLI help passed. Exactly-once execution and complete recovery of every interrupted creation are explicitly **not** claimed.

## 3. Files added, modified or removed

Paths below are relative to the V9 repository root.

Added:

- `app/workbench/creation_receipts.py`
- `tests/test_workbench_creation_receipts.py`
- `app_main_documents/14_ITERATION_8_HANDOVER.md`

Modified:

- `app/workbench/api.py`
- `app/workbench/planning_models.py`
- `app/workbench/planning_service.py`
- `frontend/src/services/planningApi.ts`
- `frontend/src/features/chat/useLocalPlanning.ts`
- `frontend/src/features/chat/SessionRecovery.tsx`
- `frontend/src/features/chat/ChatPanel.tsx`
- `frontend/src/components/layout/StatusBar.tsx`
- `frontend/tests/planning.spec.ts`
- `frontend/tests/recovery.spec.ts`
- `app_main_documents/03_DEVELOPMENT_PROGRESS.md`
- `app_main_documents/04_ARCHITECTURE_DECISIONS.md`

No source file removed; no dependencies added or installed. V9 core, CLI, inventory records, catalog, SQLite, published releases and existing user sessions were not modified. Existing dirty/untracked Iteration 5–7 changes were preserved; the full Git diff is not solely this iteration's work. Tests use isolated temporary storage.

## 4. Architectural decisions and reasons

### Verified original sequence and new receipt sequence

The unchanged `app.clarification.create_session(prompt, *, verbose=False)` first calls `run`, then allocates a UUID, constructs the session, refreshes its status, calls `save_session`, and returns. It has **no predetermined/reserved session-ID argument**. `save_session` writes a sibling temporary JSON file and replaces the session file atomically. `session_response` compares serialized output with saved JSON and hashes the saved bytes before HTTP serialization.

New sequence:

1. FastAPI validates `PlanningRequest`; the existing `PlanningService` gate checks same-ID payload identity, durable receipts and process-local state.
2. For a new accepted request, publish a durable `accepted` receipt **before importing/invoking the creator**.
3. Call unchanged V9 `create_session` directly. Planning, UUID allocation and V9 atomic session save remain V9-owned.
4. Construct the existing typed response; use the passive saved-session reader to verify the actual saved identity, prompt/mode fingerprint and creation timestamp.
5. Atomically publish `completed` with the actual saved UUID. Publish the process-local outcome and release the shared creation/answer gate.
6. FastAPI serializes the response and the browser receives it. Losing this response does not lose an already published receipt.

| Failure boundary | Observable result and replay policy |
|---|---|
| Before accepted receipt publication | No V9 invocation by this attempt. Lookup is unknown if no record exists; unknown is not general proof that earlier side effects never happened. |
| After accepted publication, before V9 invocation | Current process reports in-progress while active; after interruption/restart, indeterminate and no replay. |
| Creator import fails normally, before invocation | A safely established terminal error is persisted when storage permits. No replay. If error publication fails, retain uncertainty. |
| During V9 or session save | A thrown exception cannot prove no save occurred. Retain accepted receipt; once no active request is known, report indeterminate. |
| After session save, before completed receipt publication | **Explicitly tested unresolved window:** the saved session exists but lookup reports indeterminate. Fresh-backend same-ID POST is rejected, not executed. No session scan or guess. |
| After completed publication, before HTTP/browser acknowledgement | Completed association survives a fresh backend and can be recovered using two passive GETs. |
| Receipt/session damaged, missing or inconsistent | Corrupt/inconsistent association is not a success and cannot authorize replay. Missing receipt alone is unknown. |

### Storage and validation

`CreationReceipt` is a strict-extra-field Pydantic model with version 1, canonical request UUID, local_v9 mode, SHA-256 fingerprint of normalized prompt/mode, and accepted/completed/terminal_error state. Completed records require session UUID and creation timestamp; terminal records contain only the allowlisted `CREATOR_UNAVAILABLE` code. The normalized prompt already follows existing `PlanningRequest` trimming/length rules. The hash avoids duplicating prompt text; it is not encryption or a tamper-proof signature.

Storage derives solely from existing `app.config.SESSIONS_DIR`: default `storage/sessions/.creation_requests/<request-uuid>.json`. It is already covered by the session-storage Git ignore. No independent configuration or session database is added. UUID-only paths and resolved-location checks reject redirects; bounded reads reject oversized, truncated, duplicate-key, nonfinite, unsupported or inconsistent data. Public errors are sanitized.

Each receipt is at most 4,096 bytes. At 1,024 directory entries (including orphan temporary files), new acceptance returns `RECEIPT_CAPACITY`; prior records are never evicted. A write can temporarily add one sibling temp file. Writes use exclusive temporary-file creation, flush/fsync, then `os.replace`; ordinary cleanup removes only that exact temporary file. Counting is bounded. External filesystem tampering and multiple writers are outside this local single-process guarantee.

V9's session file remains authoritative. Completed lookup calls existing `get_saved_session`, retaining its lossless version-2 validation, historical authority and exact-byte revision. Identity checks compare UUID, recorded creation timestamp and request fingerprint. Later answers may legitimately change saved revision, history and configurations; lookup returns the current validated saved revision rather than rejecting every answer as receipt drift. No original full-session duplicate is retained.

### New passive API

```text
GET /api/v1/planning/requests/{client_request_id}
HTTP 200; Cache-Control: no-store
CreationOutcome {
  api_version: 1,
  client_request_id: UUID,
  status: unknown | in_progress | completed | terminal_error | indeterminate | corrupt,
  message: string,
  session_id: UUID | null,
  session_revision: string | null,
  error_code: string | null
}
```

Only completed outcomes include a verified session ID/revision. Corrupt states include a safe error code. Missing records return unknown, not a misleading failed/cancelled result. Invalid UUIDs return FastAPI 422; inaccessible receipt/session storage returns sanitized 503 `detail.code/message`, also no-store. Neither outcome GET nor session GET imports Ollama or calls planning, answers, `load_session`, refresh, render or save. Lookup briefly uses the coordinator lock to inspect active state, not to run a mutation.

Creation POST retains its existing request/response model. Identical completed POSTs validate the durable receipt and return saved state without another V9 call, even after restart; this may be a later historical saved revision, not freshly planned output. Conflicting prompt content returns 409; unsupported modes are rejected by existing 422 request validation. Accepted-but-inactive receipts return 409 `CREATION_INDETERMINATE`. Current-process original errors can still be returned from the cache, but cannot cause re-execution. Corrupt/missing confirmed receipts cannot be overridden by cached success. Creation UUIDs cannot be reused for answer operations. Durable state is checked before cached creation success; the cache is not the receipt authority.

### Frontend recovery

The existing unconfirmed UUID is shown with **Check creation outcome**. This explicit GET is available after reload; no startup polling, POST replay or silent replacement UUID is added. All outcome states are displayed honestly. Completion triggers a separate existing saved-session GET; only that validated result is adopted into provider-owned planning state, with historical labels, real task/question identities and safe central review selection. An unrelated remembered session is never substituted.

Lookup or saved-session errors retain the unconfirmed request reference and existing state. Successful adoption clears only the resolved creation uncertainty; prior uncertain answer state for that same session stays blocked. Browser metadata still contains only identifiers, revision and uncertainty flags—not prompts, plans or configurations. The previous creation retry button now directs the user to passive lookup. Explicitly starting a new request remains a warned, separate operation. Monaco samples, inventory, mock chat and clarification components remain independent.

## 5. Tests run, exact commands and outcomes

From the V9 repository root, using only the required venv (including the fresh-interpreter test):

```powershell
& 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv\Scripts\python.exe' -m unittest discover -s tests -p 'test_workbench_creation_receipts.py' -v
& 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv\Scripts\python.exe' -m unittest discover -s tests -p 'test_workbench_*.py' -v
& 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv\Scripts\python.exe' main.py --help
git diff --check
```

The initial focused receipt run passed 13 tests. After adding missing-receipt/cache and storage-boundary cases, the final combined run passed **57/57** (15 receipt + 42 prior workbench tests). CLI help exited 0. Coverage includes actual V9 dataclass/save files under temporary storage, completed consistency, repeated requests, payload/mode conflicts, before/during/after-save failures, terminal import failure, corrupted/oversized receipts, path escapes, bounded capacity, sanitized access errors, unchanged GET bytes/mtime, latest saved revision, no execution, and the shared creation/answer gate. One test launches a **fresh Python interpreter/application** against the same files and asserts that `app.clarification`, `app.pipeline`, `app.llm` and `ollama` were not imported during completed lookup. Fresh-app POST replay also proves the creator was called once. Failure injection models interruption; it is not a physical power-loss test.

From `frontend/`:

```powershell
npm.cmd run lint
npm.cmd run build
npm.cmd run test:e2e
npm.cmd run test:e2e -- tests/recovery.spec.ts
```

Lint and TypeScript/Vite production build passed (2,323 modules); the existing large Monaco chunk warning remains. **19 automated Chrome tests passed, 2 opt-in live tests skipped**. Receipt-specific browser checks simulate response loss/restart using deterministic routes, restore using only the creation UUID, retain minimal browser metadata, disable duplicate lookup, display all outcome states, reject an invalid saved response, preserve samples/inventory/mock mode, and prove no automatic POST. Existing answer, multi-task review, known-ID recovery and shell regressions also passed. These are browser interaction tests, not a separate manual visual inspection or live inference verification. Lint/build and all **7 recovery browser tests** passed again after final UUID-validation and status-label changes.

The sandboxed backend/Playwright attempt stalled resolving the venv's Miniconda base; it was interrupted. The sandboxed build failed with EPERM on an existing OneDrive source path. Approved outside-sandbox reruns used the **same project venv** and passed. Its verified empty temporary test directory was removed; no user data was removed. No alternate Python or package install was used. The final source has no observed failing focused check. The broad domain baseline (2 assertion failures and 192 template-example subcase errors from Iteration 5) was not rerun or repaired; core V9 interfaces were unchanged. Live Ollama/RAG checks were not run; Iteration 5 remains the latest recorded live evidence.

Documentation verification: all 15 added/modified paths listed here resolve; updated documents have balanced Markdown fences and no trailing whitespace. `git diff --check` passed. No commit was made.

## 6. Remaining issues and risks

- No exactly-once guarantee. The post-save/pre-receipt window is safe against automatic replay but remains indeterminate and may leave an unassociated saved session.
- Support is one workbench process, no reload during mutation, and no concurrent CLI/source writers. Atomic replacement does not coordinate multiple Uvicorn workers claiming one new UUID. Answer deduplication remains process-local.
- Tested durability is process/application restart on intact local storage. V9's own save does not fsync; Windows directory durability, disk loss, power failure, OneDrive conflict copies and external tampering are not certified. Back up receipts and sessions together.
- Requests created before this iteration have no receipt. Missing/deleted receipts cannot prove no prior creation, and there is no backfill, guessing, automatic cleanup or receipt repair. Capacity exhaustion deliberately blocks new accepted work; retention policy needs separate authorization.
- Current catalog/inventory freshness remains not_checked for retrieved historical state. A read may precede a concurrent answer save; lookup does not resume or revalidate a plan. Browser storage can be unavailable/cleared and retains only the latest unconfirmed creation UUID.
- Existing catalog/test drift, Monaco bundle size and inherited dependency advisories remain outside scope. No live inference was exercised by these deterministic tests.

## 7. Suggested next iteration

**Iteration 9 — Add-only synthetic demo-device registration into the existing shared inventory.** One typed registration mutation and GUI form, atomic persistence to the existing JSON authority, stable identity and expected-revision/conflict checks, and proof that the same record becomes discoverable through the inventory API and V9 target resolver. No edit/delete, new inventory database, NetBox, discovery, execution or artifact work. This is a recommendation only; no next iteration was started.

## 8. Exact reproduction/verification instructions

Backend PowerShell (single process; omit reload/multiple workers):

```powershell
Set-Location 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\network_rag_catalog_lab\network_rag_catalog_v2'
& 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv\Scripts\python.exe' -m uvicorn app.workbench.api:app --host 127.0.0.1 --port 8000
```

Frontend in another PowerShell:

```powershell
Set-Location 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\network_rag_catalog_lab\network_rag_catalog_v2\frontend'
npm.cmd run dev -- --host 127.0.0.1
```

1. Open `http://127.0.0.1:5173/`, choose Local V9. An unconfirmed creation displays its request UUID and **Check creation outcome**. Reload preserves that reference but sends no recovery request automatically.
2. Check the outcome. A completed receipt opens the historical Plan Review only after successful saved-session retrieval. Unknown/indeterminate outcomes remain explicit; do not create a replacement merely because lookup could not prove completion.
3. Inspect a recorded UUID directly without running AI:

```powershell
$creationRequestId = Read-Host 'Recorded creation request UUID'
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/planning/requests/$creationRequestId"
```

4. Stop/restart an idle backend and repeat lookup. Completed associations should retain their identity; incomplete accepted records remain indeterminate. Do not intentionally interrupt real user work to test crash windows: the receipt tests inject them in temporary storage.
5. Stop manually launched services before the Playwright suite (it owns ports 8000/5173). Use the exact tests in section 5 for repeatable before/during/after-save failures and browser response-loss cases without Ollama or persistent user-session changes.

Stop after Iteration 8. No general answer-outcome journal, session resumption, inventory mutation or generated-artifact feature was implemented.
