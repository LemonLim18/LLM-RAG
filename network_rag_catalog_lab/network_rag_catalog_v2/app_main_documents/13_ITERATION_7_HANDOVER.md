# Iteration 7 — Passive Saved-Session Retrieval and Safe Recovery

Date: 2026-10-09

## 1. Iteration identifier and objective

Iteration 7 delivers passive retrieval of one known V9 saved session and explicit workbench restoration after reload or an ambiguous answer outcome. Retrieval preserves historical state and performs no planning, refreshing, answer application or rendering.

Recovery of a creation whose session ID never reached the browser is a different problem. It is not solved by this iteration.

## 2. Completion status

**Completed** for the assigned known-session recovery boundary. Eight new backend tests, 34 existing workbench API regressions, frontend lint/build and 17 deterministic browser tests pass. Two optional live AI tests were skipped. No live inference, full domain-baseline rerun or separate manual visual inspection is claimed.

## 3. Files added, modified or removed

Paths are relative to the V9 repository root.

Added:

- `app/workbench/saved_sessions.py`
- `tests/test_workbench_recovery.py`
- `frontend/src/features/chat/SessionRecovery.tsx`
- `frontend/src/features/chat/recoveryMetadata.ts`
- `frontend/tests/recovery.spec.ts`
- `app_main_documents/13_ITERATION_7_HANDOVER.md`

Modified:

- `app/workbench/api.py`
- `app/workbench/planning_models.py`
- `app/workbench/answer_service.py`
- `frontend/src/services/planningApi.ts`
- `frontend/src/features/chat/useLocalPlanning.ts`
- `frontend/src/features/chat/ChatPanel.tsx`
- `frontend/src/features/chat/PlanningResult.tsx`
- `frontend/src/features/workspace/TaskReviewPanel.tsx`
- `frontend/src/app/workbenchReducer.ts`
- `frontend/src/components/layout/StatusBar.tsx`
- `frontend/src/styles/workbench.css`
- `app_main_documents/03_DEVELOPMENT_PROGRESS.md`
- `app_main_documents/04_ARCHITECTURE_DECISIONS.md`

No pre-existing file was removed. No dependency was installed or added. V9 domain/CLI, inventory, SQLite, knowledge releases and persisted user sessions were unchanged. Existing Iteration 5/6 dirty changes were preserved; the Git diff includes those earlier changes and must not all be attributed to Iteration 7. Tests use temporary session directories and their ordinary fixture cleanup.

## 4. Architectural decisions and reasons

### Passive route and typed contract

Entry point remains `app.workbench.api:app`.

```text
GET /api/v1/planning/sessions/{session_id}
HTTP 200; Cache-Control: no-store
{
  api_version: 1,
  mode: "local_v9",
  inventory_source: "synthetic",
  origin: "saved_session",
  session_revision: "SHA-256 of the exact bytes read",
  freshness: "not_checked",
  mutation_eligibility: "not_checked",
  session: SessionPayload
}
```

`SavedSessionResponse` shares `SessionSnapshot` and the existing `SessionPayload` with `PlanningResponse`. Existing creation/answer response contracts retain `client_request_id`; GET deliberately has no such field because V9 session persistence does not record it. The existing V9 `ExecutionPlan` dataclasses remain authoritative.

FastAPI validates the UUID path parameter before reading. The storage helper also validates identity, constructs the canonical UUID filename only under configured `app.config.SESSIONS_DIR`, and rejects a resolved path outside that directory. There is no arbitrary file path input or session directory scan.

Typed error bodies use `detail.code/message`:

| Condition | Result |
|---|---|
| Malformed UUID | FastAPI 422 validation response |
| Missing session file | 404 `SESSION_NOT_FOUND` |
| Unsupported session or plan schema version | 409 `UNSUPPORTED_SESSION_VERSION` |
| Malformed, lossy or inconsistent saved state | 409 `INVALID_SAVED_SESSION` |
| File access/storage failure | 503 `SESSION_STORAGE_UNAVAILABLE` |

Storage/validation errors expose neither local paths nor upstream exception text. Error responses also disable caching. The synchronous GET runs in FastAPI's worker pool.

### Exact persistence/read strategy

`read_saved_bytes()` returns one `(path, bytes)` snapshot. `validate_saved_payload()` parses that same snapshot, rejects duplicate JSON keys/nonfinite values and unsupported versions, validates the existing typed payload, and requires lossless JSON-value serialization. It checks session identity/status consistency, unique task/question identities and the saved pending-question sequence. The SHA-256 comes from those same bytes, with no second read to race against the response.

This validator is extracted from the Iteration 5 answer restoration boundary and reused there. Answer processing still constructs `ClarificationSession`, checks `session_to_dict()` equality, and performs all existing saved/question/source/runtime/context checks under the existing mutation coordinator before applying an answer. No validation bypass is introduced.

GET does not import `app.clarification` or `app.pipeline`: those modules transitively construct the Ollama client. The passive helper uses only the response models and V9 data-only dataclasses. It verifies the same pending-question priority ordering used by `ClarificationSession.pending_questions`; the answer path's additional serializer equality check and tests guard their agreement. It never calls `load_session`, `create_session`, `apply_answer`, `refresh_plan`, `save_session`, rendering, context revision probes or retrieval.

No mutation lock is acquired for GET. V9's existing atomic file replacement lets a read observe one saved version; this does not coordinate concurrent writers or prove an in-flight mutation has finished. A GET may precede a later save. Current validity is deliberately not assessed. Old source/context hashes, authority, release identity, ready/rendered status and configurations remain historical facts.

### Frontend restoration and timeout behavior

`SessionRecovery` appears only in Local V9 mode and provides a UUID input, explicit restore action, clear-reference action and an action to read the currently known session's latest saved state. Nothing is fetched or replayed automatically on page load.

The existing provider-owned planning hook adopts the validated GET response. The existing reducer safely synchronizes selected task identity and opens central plan review, including an empty returned plan. The same task details and clarification form render the restored payload. Monaco samples, inventory and Demo mock remain independent. Read errors retain the existing displayed session and allow another read.

The UI labels recovered results as historical, with freshness and mutation eligibility unverified. Saved ready/rendered output is not presented as newly validated. Explicit subsequent answers still use the returned saved revision and actual pending question IDs through the existing answer endpoint. A stale catalog/inventory remains inspectable; answer mutation may reject it under existing checks. No resume or refresh action exists.

Browser storage key: `v9.session-recovery.v1`. Its minimal metadata contains the latest confirmed session UUID/revision and an `answerUncertain` flag. While creation is unconfirmed it may also contain its client request UUID as a warning reference. It stores no prompt, answer text, plan, history, credentials or generated configuration. Storage access is guarded; if writes are unavailable the UI instructs the user to retain the UUID for manual entry. Clear-reference removes the remembered session metadata without deleting the saved session; a separate unresolved-creation warning is retained when applicable.

| Recovery case | Implemented behavior and evidence limit |
|---|---|
| Known session after browser/backend restart | Explicit GET restores its saved state and compares its revision with the remembered revision when available. |
| Lost answer response, detailed answer still in memory | Compare new entries in the relevant task's saved `clarification_history` with the complete submitted answer: question/source/task revision, kind, literal input and stable selected IDs. One matching entry with an explicit accepted/rejected flag confirms that V9 recorded that answer outcome. |
| Hash changed without matching answer evidence | Display the changed snapshot and retain uncertainty. A changed revision cannot identify its cause; new answers remain blocked. |
| Reload during/after uncertain answer | The uncertainty flag survives, but full answer evidence is deliberately not persisted locally. Inspection is possible; conclusive request attribution and automatic continuation are unavailable. |
| Creation timeout with only client request UUID | Existing V9 files have no durable request-to-session mapping. No arbitrary scan, probable match or automatic replay occurs. An older remembered session is explicitly unrelated. Same-process manual retry remains the prior limited facility; do not retry after restart. |

Even exact recorded-answer evidence does **not** prove which HTTP request caused it: V9 does not persist the client request UUID. The UI states that distinction. Restoration never repeats an answer or creates a session. Request-based durable outcome recovery, interprocess coordination and session resume remain deferred (AD-032/AD-033).

## 5. Tests run, exact commands and outcomes

All Python execution, including the fresh-interpreter subprocess test, used the workspace virtual environment. Its standard library paths may reflect the environment's base installation; no alternate interpreter was invoked.

From the V9 root:

```powershell
& 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv\Scripts\python.exe' -m unittest tests.test_workbench_recovery -v
& 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv\Scripts\python.exe' -m unittest tests.test_workbench_answers tests.test_workbench_planning tests.test_workbench_api -q
```

Results: **8/8 new recovery tests passed**, then **34/34 existing API tests passed**. The passive tests use sessions created with V9's real dataclasses and `save_session`, in isolated temporary storage. They verify:

- Entire saved payload equality, historical configurations/authority, exact SHA-256 and unchanged `st_mtime_ns`/file bytes.
- Guards against writes, refresh, planning, answering, model calls, retrieval, context probes and subprocess/device network calls during GET.
- Invalid IDs, missing files, sanitized storage failures, path escape rejection, malformed/duplicate-key/nonfinite JSON, unsupported versions, unknown fields and inconsistent identities/questions/status.
- Only one byte read for the response and its hash.
- A **new Python process** with a new FastAPI application can retrieve the same persisted session; `app.clarification`, `app.pipeline`, `app.llm`, `app.embeddings` and `app.vectorstore` remain absent from `sys.modules` after that GET.

Existing regressions exercise actual V9 creation/answer semantics with controlled AI doubles, stale revisions/source protection, shared mutation coordination, duplicates, persistence failures, inventory and passive runtime endpoints. GET depends on neither Ollama availability nor a request-cache entry.

From `frontend/`:

```powershell
npm.cmd run lint
npm.cmd run build
npm.cmd run test:e2e -- --reporter=line
npm.cmd run test:e2e -- tests/recovery.spec.ts --reporter=line
```

Results: **lint passed**, **TypeScript/Vite build passed** (2,323 modules), **17 browser tests passed, 2 skipped**. The five new browser tests cover explicit reload restoration of multiple tasks/pending questions, minimal persisted metadata and clearing, exact accepted-answer evidence after response loss, uncertain changed revisions across reload, read errors retaining existing state, unknown-ID creation limitations, no automatic GET/POST replay, Monaco edit retention, inventory and Demo mock separation. Existing planning, answer, review and shell checks also passed. The two opt-in live AI checks were skipped because `RUN_LIVE_V9` was unset. These are automated Chrome checks, not a separate manual visual inspection.

Lint/build were rerun after two small state fixes: restoring an empty plan opens review, and a new answer attempt clears the prior recovery message. The full browser run exercised that updated source. Final review also strengthened the uncertainty guard: an invalid UUID or clearing the remembered reference cannot unblock the currently uncertain session. An inconclusive read retains in-memory answer evidence so a later explicit GET can recognize a delayed save. Both behaviors were added to the recovery tests; the final five-test recovery subset plus lint/build passed. `git diff --check` passed.

Initial verification issues were resolved: a model-call guard patched a Pydantic instance method incorrectly (fixed to patch the class method); Windows resolved the initial recovery helper/component names ambiguously (helper renamed to `recoveryMetadata.ts`); one test variable needed `const`. No test assertion was weakened to bypass V9 behavior. A sandboxed backend run stalled on its first local HTTP test and was interrupted; approved runs outside the sandbox used the same required venv. Its one generated temporary fixture and empty temporary directory were verified and removed; no user session was deleted.

Existing broad domain failures from Iteration 5 (2 assertion failures and 192 template-example subcase errors) were **not rerun or repaired**. They remain documented historical baseline issues. The existing Monaco large-chunk build warning remains. No new failure remains in the tests run for this iteration.

## 6. Remaining issues and risks

- Unknown-ID creation recovery is unsolved: no durable client-request mapping exists, and a browser restart does not make creation retry safe.
- Exact answer history identifies a recorded answer, not its HTTP request. Missing/ambiguous evidence remains blocked; restoring a snapshot is not proof that an in-flight worker has stopped.
- Reload retains only minimal metadata. Full answer evidence is intentionally discarded, which limits post-reload outcome attribution.
- Freshness/eligibility are not checked by GET. Old sessions may display saved output but fail subsequent mutation checks. Explicit refresh/resume is absent.
- Process-local locking and 256-entry deduplication remain unchanged; no multi-worker/CLI coordination, journal, cancellation or exactly-once guarantee exists.
- Invalid/legacy payloads are rejected without migration or repair. Browser storage is per origin and may be unavailable or cleared.
- No real Ollama workflow was exercised in this iteration. Passive retrieval was verified independently; Iteration 5 remains the latest recorded live inference/clarification evidence.

## 7. Suggested next iteration

**Iteration 8 — Bounded durable creation-outcome lookup by client request ID.** Define and implement the smallest durable creation receipt/mapping that can identify the resulting session after response loss/restart, with explicit crash-window and retry behavior and focused recovery tests. Do not claim exactly-once execution without evidence. Keep corrections, inventory CRUD, history browsing, artifacts and cross-process coordination outside that single deliverable. This is a recommendation only; Iteration 8 has not begun.

## 8. Exact reproduction and verification instructions

Backend PowerShell (one process; no reload during mutations):

```powershell
Set-Location 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\network_rag_catalog_lab\network_rag_catalog_v2'
$projectPython = 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv\Scripts\python.exe'
& $projectPython -m uvicorn app.workbench.api:app --host 127.0.0.1 --port 8000
```

Frontend in a second PowerShell:

```powershell
Set-Location 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\network_rag_catalog_lab\network_rag_catalog_v2\frontend'
npm.cmd run dev -- --host 127.0.0.1
```

1. Open `http://127.0.0.1:5173/` and choose Local V9. Enter a known saved session UUID and click **Restore saved session**, or create a normal session once to establish the remembered reference.
2. Reload the browser, choose Local V9 and verify that the UUID is remembered but no session has been fetched automatically. Click restore. Confirm the historical notice, original task/question identities and read-only generated output where present.
3. Stop/restart the backend only when no mutation is running. Restore the same UUID again. Ollama is not required for this GET; its absence must not prevent inspection.
4. Edit a Monaco sample, switch to plan review and back, and confirm the independent in-memory edit remains. Use **Clear recovery reference** to remove the remembered session pointer; no saved file is deleted.
5. Use the deterministic browser suite for response-loss scenarios. It verifies matching saved-answer evidence and persistent uncertainty without intentionally interrupting a real user mutation.

The commands in section 5 reproduce backend, build and browser checks. No session history browsing or V9 resume is implemented. Stop after Iteration 7.
