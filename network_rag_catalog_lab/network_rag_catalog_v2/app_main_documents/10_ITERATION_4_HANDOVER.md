# Iteration 4 — Structured V9 Planning Session Creation

Date: 2026-10-08

## 1. Identifier and objective

Iteration 4 delivers one workflow: an explicitly selected Local V9 prompt travels from the existing React workbench through FastAPI to V9's existing session creator, and the returned structured session is displayed without answering questions or executing devices.

## 2. Completion status

Completed for the bounded creation workflow. New API tests and browser checks pass, including real browser-to-V9 creation. The pre-existing broader regression set remains non-green; this is not a claim that all V9 operations or the entire roadmap are operational. The final baseline comparison is recorded in section 5.

## 3. Exact files added, modified or removed

Paths below are relative to the V9 repository root.

Added:

- `app/workbench/planning_models.py`
- `app/workbench/planning_service.py`
- `tests/test_workbench_planning.py`
- `tests/manual_workbench_readiness.py`
- `frontend/src/services/planningApi.ts`
- `frontend/src/features/chat/useLocalPlanning.ts`
- `frontend/src/features/chat/PlanningResult.tsx`
- `frontend/tests/planning.spec.ts`
- `app_main_documents/10_ITERATION_4_HANDOVER.md`

Modified:

- `app/workbench/api.py`
- `frontend/src/services/runtimeApi.ts`
- `frontend/src/app/types.ts`
- `frontend/src/app/WorkbenchProvider.tsx`
- `frontend/src/features/chat/ChatInput.tsx`
- `frontend/src/features/chat/ChatPanel.tsx`
- `frontend/src/components/layout/WorkbenchLayout.tsx`
- `frontend/src/components/layout/StatusBar.tsx`
- `frontend/src/styles/workbench.css`
- `frontend/tests/workbench.spec.ts`
- `app_main_documents/03_DEVELOPMENT_PROGRESS.md`
- `app_main_documents/04_ARCHITECTURE_DECISIONS.md`

No files removed. No dependencies installed or added. Existing dirty runtime/catalog/test files were preserved, not attributed to this iteration. No V9 engine, CLI, inventory JSON, SQLite authoring, knowledge release, FYP source or existing domain regression test was edited.

Live verification intentionally created normal V9 session JSON files under `storage/sessions/` (not source changes):

- `storage/sessions/3d70a30e-9a04-4db7-be67-437fbd1dedb2.json` — first browser smoke, ready.
- `storage/sessions/4150a2d4-bf2d-464c-b4e4-e00c7ad2d651.json` — final browser smoke, ready.
- `storage/sessions/7ff0ee1f-988f-4646-940a-6a37c783d104.json` — instrumented paraphrase probe, needs clarification.

They are retained, not deleted. Deterministic backend tests use temporary session directories which their fixtures clean up.

## 4. Architecture and implementation decisions

### API contract and reused interfaces

Entry point remains `app.workbench.api:app`. Only one mutation was added:

```text
POST /api/v1/planning/sessions
{
  "prompt": "Create VLAN 100 named STAFF on R1",
  "mode": "local_v9",
  "client_request_id": "client-generated UUID"
}
```

`PlanningRequest` forbids extra fields, requires a string prompt trimmed to 1–8,000 characters, accepts only `local_v9`, and validates the request UUID. Invalid requests return 422 before V9 is called.

HTTP 200 returns `PlanningResponse`:

```text
{api_version: 1, mode: "local_v9", inventory_source: "synthetic",
 client_request_id, session_revision, session: SessionPayload}
```

`SessionPayload` preserves `session_id`, timestamps, status, history, schema version, pending questions, and the full plan. Its plan type reuses the existing `ExecutionPlan` / `PlannedTask` / `OperationIntent` dataclasses rather than defining another planner model. JSON-level equality with `session_to_dict()` and saved JSON is tested, including task/question/option IDs, revisions, parameters, evidence, target resolution, issues, config fields and authority. `session_revision` hashes the exact saved file bytes; it is an observation token, not an implemented concurrency API.

The adapter lazily calls verified `app.clarification.create_session(prompt, verbose=False)` and `session_to_dict(session)`. V9's creator already calls `run`, assigns the session UUID, and atomically saves the session through `save_session`. The adapter does not call `load_session`, replace persistence or launch `main.py`. V9's snapshot decorator runs inside the worker and retains the existing runtime/knowledge semantics.

Exceptions return the established `detail` envelope with typed `code`, `message`, `client_request_id`: 409 for request-ID conflict/in-progress; 503 for busy/capacity or propagated model/transport failure; 500 for other V9/adaptation/persistence failures. Exception bodies are not sent to the browser. V9 itself can catch retrieval/model failures and return a genuine `needs_clarification` session with task feedback; that state and feedback are preserved, not reclassified as a ready result or replaced with a mock. A focused test verifies this distinction.

Existing passive GET routes still do not probe AI. CORS adds POST only to the existing configured local origins. No extra endpoint, session read, answer, correction, execution or inventory write is mounted.

### Worker, duplicates, timeouts and persistence

The current scope uses a worker-backed synchronous response, not the larger future 202/polling/journal design proposed in Iteration 0. FastAPI dispatches the synchronous endpoint to its thread pool. A single `PlanningService` per application serializes V9 creation because catalog reloads use process-global state. Other planning requests are rejected as busy, not queued; health remains responsive during a blocked worker (tested).

- A UUID identifies one prompt. Completed results and errors are retained in memory; a repeated ID/prompt returns the same outcome without another V9 call. A different prompt with that ID returns 409. An in-flight duplicate returns 409.
- Up to 256 accepted IDs are retained without eviction; capacity returns 503. This is a bounded local process cache, **not durable exactly-once processing**. Use one Uvicorn process, without reload/multiple workers during a request. Restart clears deduplication; do not blindly retry an old request after restart.
- The UI guards submission immediately with a ref and disables its Local V9 composer while pending. It never retries automatically. Retry reuses the same ID and prompt. Cached failures remain failures; after checking the outcome, the explicit New request control allocates a new ID for another attempt.
- The browser waits up to 120 seconds. Timeout, disconnect, panel hiding or browser closure does not cancel the Python worker. The worker may still complete and persist a session. A timed-out response means unknown outcome, not failed/cancelled execution. Same-process retry can return in-progress or the retained completed result.
- Existing model calls have their own bounds (the configured ChatOllama client has a 30-second timeout), but repeated calls and embedding operations have no adapter-wide hard deadline/cancellation. A stuck worker can keep creation busy; inspect outcomes before restart.
- Creation saves V9's original session under `storage/sessions/<uuid>.json` before success. Failures during/after save may leave a file even if HTTP returns an error. Errors cannot prove that nothing was persisted. There is no crash recovery journal or retrieval endpoint in this iteration.
- Browser state retains the latest submission/result only, survives panel hiding, and resets on page reload. Before reloading a pending request, record its displayed request ID; inspect saved JSON as a plain file when needed, not through the refreshing `load_session()` function.

### Frontend behavior

`planningApi.ts` is the typed POST client using the existing configured base URL. `useLocalPlanning` is a small feature hook owned by the provider so toggling the panel cannot accidentally discard an in-flight request or enable duplicate work. It does not implement a V9 state machine.

The Copilot offers separate Demo mock and Local V9 buttons; default remains explicit demo. Local results display the actual session/status/authority, per-task operation and stable identity, target/vendor/platform, parameters, V9 feedback, validation issues and read-only config output when present. Expandable views retain the complete evidence/revision/question/option data. Pending questions display their actual wording/IDs and explain that answers are unsupported. `ready` means preview-ready, never deployed. Monaco still edits only its separate static samples; no original/draft synchronization or backend artifact storage was added.

## 5. Tests, commands and verified outcomes

All Python commands used only the required workspace venv. The normal sandbox failed before launching a shell (`setup refresh had errors`); approved unsandboxed commands were used. No alternate interpreter or dependency installation was used.

From the V9 root:

```powershell
$projectPython = 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv\Scripts\python.exe'
& $projectPython -m unittest tests.test_workbench_api tests.test_workbench_planning -v
& $projectPython main.py --help
```

Final results: **19/19 passed** (8 existing API plus 11 new planning tests); CLI help exited 0. Coverage includes actual HTTP validation, full serialization/persistence parity, stable IDs/questions, invalid input, propagated and V9-caught failures, idempotency/conflicts, busy/capacity behavior, health responsiveness, real deterministic V9 creation with process/network execution guards, and absence of other mutation endpoints.

Documentation/scope checks resolved all 24 listed paths (21 source/document paths and 3 retained live sessions), parsed the four new Python files, and verified balanced Markdown fences and no trailing whitespace. `git diff --check` for the scoped paths returned 0; because much of this workbench is already untracked, explicit path/content checks are the meaningful additional verification. The initial path-check script treated session basenames as root files; correcting them to repository-relative paths made the check pass.

The unchanged pre-implementation baseline command was:

```powershell
& $projectPython -m unittest tests.test_workbench_api tests.test_runtime_intent_integrity tests.test_native_vendor_runtime tests.test_file_runtime tests.test_target_resolution tests.test_clarification_flow -v
```

Result: 69 test methods; 2 failing assertions and 192 erroring template-example subcases, across three legacy methods. The other 66 methods passed. Specifically:

- `TargetResolutionTests.test_unique_attributes_and_aliases`: the `Huawei` case expects a unique match but the actual inventory contains both R2 and SW2; V9 correctly reports ambiguity.
- `ClarificationFlowTests.test_unknown_version_and_context_changes_cannot_reuse_output`: expects a `ValueError` that the current file-runtime path does not raise.
- `ClarificationFlowTests.test_all_existing_vendor_templates_render_complete_examples`: the legacy examples mapping lacks 32 operation keys across six devices (192 `KeyError` subcases).

These failures existed before the adapter was added. No test was weakened or historical catalog repaired. Runtime-intent protections, native-vendor tests, file-runtime tests, remaining target-resolution checks and remaining clarification checks are exercised in this bounded set; a complete repository/FYP test collection was intentionally not attempted.

Final comparison: **79 methods, the same 2 assertion failures and the same 192 missing-example subcase errors; no new failing case.** This rerun included the original six modules plus the 10 new planning tests present when it started. One additional V9-caught-retrieval test was subsequently added and passed in the final 19-test API run above. The baseline runner exited 1, correctly reflecting unresolved existing failures rather than treating them as passes. Exact summarized rerun command (no test behavior or assertions changed):

```powershell
@'
import io, unittest
from collections import Counter
modules = ['tests.test_workbench_api', 'tests.test_workbench_planning', 'tests.test_runtime_intent_integrity', 'tests.test_native_vendor_runtime', 'tests.test_file_runtime', 'tests.test_target_resolution', 'tests.test_clarification_flow']
suite = unittest.defaultTestLoader.loadTestsFromNames(modules)
result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
print('FINAL_REGRESSION', result.testsRun, 'tests', len(result.failures), 'failures', len(result.errors), 'errors', flush=True)
for test, trace in result.failures:
    print('FAILURE', test.id(), trace.splitlines()[-1][:600], flush=True)
for message, count in Counter(trace.splitlines()[-1] for _, trace in result.errors).items():
    print('ERROR_GROUP', count, message, flush=True)
raise SystemExit(not result.wasSuccessful())
'@ | & 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv\Scripts\python.exe' -u -
```

Running it against the final tree now collects 80 methods because of that last additional passing test. This does not retroactively change the observed 79-test result.

From `frontend/`:

```powershell
npm.cmd run lint
npm.cmd run build
$env:RUN_LIVE_V9='1'
npm.cmd run test:e2e -- --reporter=line
Remove-Item Env:RUN_LIVE_V9
```

Final results: lint passed; production build passed (2,319 modules; existing large Monaco chunk warning remains); **7/7 Playwright checks passed**, including the opt-in real backend/V9 browser smoke. The first run had two new test-selector collisions with Monaco alert nodes; scoping assertions to Copilot resolved them. Browser coverage checks multi-target structured results, pending/duplicate prevention, stable question IDs, separate mock mode, errors/retries, unknown transport outcomes, retained pending state after panel toggling, plus the original Monaco edits/tabs/inventory/filter/layout/unavailable-backend regressions. This is automated real-browser verification, not a separate manual visual inspection. Without `RUN_LIVE_V9=1`, the live smoke is explicitly skipped; deterministic browser cases do not prove live AI.

### Actual Ollama and retrieval verification

After making the pending request ID visible for recovery, the final frontend rerun used `npm.cmd run lint`, `npm.cmd run build`, and `npm.cmd run test:e2e -- --reporter=line` without the live flag. Lint/build passed again; all 6 deterministic browser checks passed and the 1 opt-in live test was explicitly skipped. The successful 7/7 live-enabled run above remains separate evidence; no extra live session was created by this final rerun.

Reproducible opt-in command (creates one normal saved session):

```powershell
& $projectPython -u -m tests.manual_workbench_readiness
```

Observed:

- Config: `files`, LLM `qwen2.5:1.5b`, embeddings `nomic-embed-text`. Installed tags at `http://127.0.0.1:11434` were `qwen2.5:1.5b` and `nomic-embed-text:latest`; the untagged configured embedding name successfully resolved to the installed default tag.
- Actual configured LLM invocation returned `OK`; actual configured embedding generation returned 768 dimensions.
- `get_vectorstore()` passed existing catalog-ID/revision/embedding-model checks; 44 index records were present. Real semantic query results included `create_vlan` and `assign_vlan_to_trunk_port`. No ingestion, index rebuild or publication was performed.
- Instrumented real POST for `Please provision a VLAN numbered 321 named AUDIT on R1.` returned HTTP 200 and a saved `needs_clarification` session. Delegating spies recorded **5 actual LLM calls, 1 successful retrieval with candidates `delete_vlan`, `create_vlan`, `rename_vlan`, and 1 actual query embedding**. V9 selected `create_vlan`/`dev-r1` and required `OPERATION_PROPOSAL` confirmation. Its one pending question was not answered. Returned JSON equalled saved JSON.
- The real browser prompt `Create VLAN 100 named STAFF on R1` returned `ready`, preserved the R1 identity and exposed the `vlan 100` configuration preview. That literal path alone is not evidence of retrieval; the separately instrumented paraphrase is.

This verifies local creation and its real inference/retrieval path now, not every catalog operation, all models, future readiness, published-mode planning or clarification progression. Passive status still honestly reports AI `not_checked`.

## 6. Remaining issues and risks

- The three existing failing regression methods above and unrelated historical catalog drift remain. No broad all-green claim is made.
- Single-process, non-durable request deduplication; outcome ambiguity after restart/timeout; no hard worker cancellation or cross-process coordination.
- Small-model output may need V9 confirmation or deterministic fallback. A returned session does not itself prove every model/RAG step ran. Current per-request call tracing is only in the opt-in probe, not production telemetry.
- No live published-release planning smoke was attempted; direct-files authority was the verified environment. Existing passive published-pointer API tests remain green.
- No session resumption, question answering, inventory editing, draft persistence or device execution. Latest result resets in the browser on reload while saved V9 sessions remain.
- Existing Monaco bundle-size warning and inherited dependency advisories remain outside this iteration.

## 7. Next single recommended iteration

**Iteration 5 — One structured clarification-answer round trip.** For an explicitly selected current session/question, preserve question/task/option IDs, revision/source evidence, reject stale/duplicate answers and call the existing V9 answer boundary. Scope and test the necessary session coordination explicitly before coding. Do not combine corrections, general resumption, inventory CRUD or artifact persistence. Iteration 5 has not begun.

## 8. Exact launch and manual verification

Backend PowerShell:

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

Open `http://127.0.0.1:5173/`, select Local V9, submit the literal smoke prompt above. Confirm pending state followed by the real session/task/target/parameter facts. Expand the read-only configuration preview. Test a request missing parameters to see pending questions with no answer controls. Switch to Demo mock and verify the separate labelled response. Edit/switch Monaco samples throughout. Stop the backend and submit again: an explicit error must appear with no mock fallback. Do not use reload/multiple Uvicorn workers while relying on same-process retry protection.

For direct creation, while the backend is running:

```powershell
$request = @{prompt='Create VLAN 100 named STAFF on R1'; mode='local_v9'; client_request_id=[guid]::NewGuid().ToString()} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/v1/planning/sessions' -ContentType 'application/json' -Body $request
```

Reusing the exact `$request` returns the same result in the same backend process. Do not generate another UUID merely because a response was lost. Use ordinary `Get-Content` on saved JSON for diagnostic inspection, not `load_session()`.
