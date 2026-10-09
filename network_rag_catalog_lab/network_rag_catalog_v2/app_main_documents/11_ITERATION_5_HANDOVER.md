# Iteration 5 — Structured V9 Clarification-Answer Round Trip

Date: 2026-10-09 (Asia/Kuala_Lumpur)

## 1. Iteration identifier and objective

Iteration 5: answer one actual current V9 question per HTTP request through structured GUI controls, preserve V9 validation and persistence, then show the confirmed updated session. No general session reads/resume, corrections, inventory editing or artifact persistence were added.

## 2. Completion status

Completed for the bounded clarification-answer workflow. All 34 focused API tests, frontend lint/build and 13 browser checks (including a real OSPF answer) passed. The 61-method domain regression rerun reproduced only the recorded legacy failures, with no new failing case. This is not a claim that the entire repository baseline is green or all clarification types are certified.

## 3. Files added, modified or removed

Paths are relative to the V9 repository root.

Added:

- `app/workbench/answer_service.py`
- `tests/test_workbench_answers.py`
- `frontend/src/features/chat/ClarificationForm.tsx`
- `frontend/tests/answers.spec.ts`
- `app_main_documents/11_ITERATION_5_HANDOVER.md`

Modified:

- `app/workbench/api.py`
- `app/workbench/planning_models.py`
- `app/workbench/planning_service.py`
- `tests/test_workbench_planning.py`
- `frontend/src/services/planningApi.ts`
- `frontend/src/features/chat/useLocalPlanning.ts`
- `frontend/src/features/chat/PlanningResult.tsx`
- `frontend/src/features/chat/ChatPanel.tsx`
- `frontend/src/components/layout/StatusBar.tsx`
- `frontend/src/styles/workbench.css`
- `frontend/tests/planning.spec.ts`
- `app_main_documents/03_DEVELOPMENT_PROGRESS.md`
- `app_main_documents/04_ARCHITECTURE_DECISIONS.md`

No files removed and no dependencies added/installed. V9 domain/CLI source, inventory, catalog, SQLite authoring, published releases, FYP source and existing domain regression tests were not edited. Pre-existing dirty changes remain the user's changes.

Live verification intentionally retained two normal session files (not source additions):

- `storage/sessions/2cbaabf3-6470-4ed1-b4c9-8da8f665084f.json` — created and answered once for the live OSPF round trip.
- `storage/sessions/2cbbc05c-dd73-47a4-953a-74c8c1dc6598.json` — existing live creation regression.

Deterministic tests use automatically cleaned temporary session directories. Nothing was deployed or sent to network devices.

## 4. Architectural decisions and verified call path

### Actual V9 semantics

Verified in `app/clarification.py`, `app/planner/models.py`, `app/pipeline.py` and `app/questions.py`:

- `apply_answer(session, answer: ClarificationAnswer)` requires `session.next_question` and passes its task identity to `apply_clarification`.
- `ClarificationAnswer` carries `question_id`, integer `revision`, `source_revision`, `kind`, `raw_input` and `selected_ids`. It has no separate answer UUID. This API uses `client_request_id` for transport retry identity; it never replaces V9 question/option IDs.
- `selected_options(question, answer)` validates stable option IDs, duplicates and selection cardinality. `resume_task` performs source/question checks, schema/value/vendor/context validation and evidence/provenance updates.
- `apply_clarification` records acceptance in session history, refreshes the plan through V9's normal request-wide rendering gate, updates status/time and calls the existing atomic `save_session`.
- A rejected answer may return normally and still be saved with `accepted: false`, task feedback and rejection history. Successful function return is not assumed to mean accepted input.
- `load_session()` calls `_plan_from_dict()` (which clears output and task states), then `refresh_plan()`. It is not a passive read and is never used by this adapter. No GET/session-resume endpoint was introduced.

Call path:

```text
Current-question form → typed answer POST → shared PlanningService gate
  → read saved bytes and check expected SHA-256
  → validate/reconstitute current dataclasses without refresh
  → check current question, answer shape/options, runtime/source/context
  → existing apply_answer → apply_clarification → resume_task / refresh_plan / save_session
  → verify saved JSON equals returned V9 serialization, hash saved bytes
  → accepted updated session OR explicit saved rejection → GUI
```

### Request and response contract

Entry point remains `app.workbench.api:app`. New route:

```text
POST /api/v1/planning/sessions/{session_id}/answers
{
  "client_request_id": "new UUID for this answer attempt",
  "expected_session_revision": "64-character SHA-256 from last confirmed result",
  "answer": {
    "question_id": "actual current V9 question ID",
    "revision": 1,
    "source_revision": "actual question source revision",
    "kind": "selection",
    "raw_input": "",
    "selected_ids": ["actual option ID"]
  }
}
```

The route validates a UUID session path. `AnswerRequest` and `AnswerInput` forbid extra fields. Only `selection` and `custom` are accepted; unknown kinds are 422. Custom requires nonblank text and no option IDs; selection requires IDs and no custom text. Text is limited to 8,000 characters; at most 100 option IDs can be submitted. Existing V9 `selected_options` decides whether IDs and cardinality are valid. Custom text is allowed only when the actual question permits it. Text is passed to V9 unchanged; a literal `1` is not converted to an option index. Clients cannot specify authoritative operations, parameter maps or field updates.

`AnswerResponse` extends the existing complete `PlanningResponse` with `accepted: true` and `answered_question_id`. It retains session identity, all tasks, evidence/provenance, questions, issues, authority and configuration output, plus the SHA-256 of the newly saved bytes. Task/question revisions remain V9's own revisions, not substitutes for the saved-session hash.

Errors use HTTP status and `detail.code/message/client_request_id/current_session`:

| Condition | Response |
|---|---|
| Missing session | 404 `SESSION_NOT_FOUND` |
| Changed saved bytes | 409 `STALE_SESSION` |
| Wrong current question / question revision | 409 `QUESTION_NOT_CURRENT` / `STALE_QUESTION` |
| Changed inventory/source/runtime/snapshot | 409 `STALE_SOURCE`; no refresh/write |
| No eligible current question | 409 `SESSION_NOT_ANSWERABLE` |
| Legacy or incompatible saved payload | 409 `UNSUPPORTED_SESSION_VERSION` / `INVALID_SAVED_SESSION` |
| Invalid option / disallowed custom input | 422 `INVALID_OPTION` / `CUSTOM_NOT_ALLOWED`; no write |
| V9 semantic rejection | 422 `V9_ANSWER_REJECTED`, actual feedback and `current_session` containing the complete saved rejected result and its new revision |
| Invalid request shape or kind | FastAPI/Pydantic 422 validation response; V9 not called |
| In-flight duplicate / conflicting reused UUID | 409 `REQUEST_IN_PROGRESS` / `REQUEST_ID_CONFLICT` |
| Another mutation running / cache capacity reached | 503 `PLANNER_BUSY` / `REQUEST_CAPACITY` |
| Propagated model/transport failure | 503 `LOCAL_SERVICE_UNAVAILABLE` |
| Other mutation/persistence failure | 500 `V9_PLANNING_FAILED`; acceptance is not claimed |

The distinction between a no-write precheck rejection and V9's saved semantic rejection is deliberate. The GUI adopts `current_session` only when supplied by the backend for the same session. It does not infer a value was accepted from local input or advance the plan optimistically.

### Passive restoration and stale-write protection

Only version-2 saved sessions are supported by this answer workflow. `SessionPayload` validates the file and reuses V9's `ExecutionPlan`/task/intent dataclasses. A `ClarificationSession` is constructed with its original IDs, timestamps, status, plan and history. Equality with `session_to_dict()` is required before mutation, including derived pending questions. Unknown/incompatible data is rejected rather than dropped or migrated. This internal read exists only inside the answer operation, not as a public retrieval API.

All prechecks and application run under the same process-local mutation gate used by creation. Before V9 is called, the adapter verifies saved bytes again and checks the active snapshot/authority, source revision and inventory/planned-context revision inside V9's `snapshot_scope()`. Existing V9 validation runs again during the actual answer. There is no separate frontend semantic engine or validation bypass.

V9 retains its original atomic save. The response builder checks that saved JSON equals `session_to_dict(updated)` before returning a revision. It does not write its own session representation. Errors after a save still can leave a persisted outcome; no failed HTTP response is proof that disk was unchanged.

### Coordination, retries and remaining boundaries

- The existing single `PlanningService` per application now gates both creation and answering. The method/payload/session identity is included in the request fingerprint. A UUID cannot be reused for a different mutation. Completed outcomes and errors are published to the cache before the worker is released.
- Retention remains bounded to 256 accepted request IDs total, without eviction. Identical retries return the original response/error without invoking V9 again—even after the saved revision has advanced. This is a cached historical operation result, not a fresh session read.
- Concurrent new mutations return busy rather than queue. A same-ID pending retry returns in-progress. Health remains responsive because synchronous handlers run in FastAPI's thread pool.
- The browser never automatically retries and immediately guards against double submission. Retry retains the exact answer UUID, session, saved revision, question revisions and answer payload. On a known validation rejection, the user must explicitly review/edit; submitting then uses a new UUID and the latest confirmed revision.
- Both POST clients wait up to 120 seconds. Timeout/disconnect does not stop Python or undo a save. An unknown outcome keeps the last confirmed result and disables new answer submission; same-process same-ID retry is offered. Model/persistence/stale-state failures remain blocked for review rather than silently generating another request.
- Use one Uvicorn process without reload while requests are running. Restart/multiple workers lose or split the cache/gate. The disk hash will reject an old revision after a persisted mutation, but there is no durable request-result journal and no exactly-once recovery claim.
- The CLI does not participate in this lock. Concurrent CLI edits, another server process, or external inventory/catalog writes during a request are unsupported. Prechecks and post-save comparison detect some changes but do not create an interprocess compare-and-swap. Do not mutate the same session or its runtime inputs outside this single service while it is working.

### GUI controls

`ClarificationForm` renders only the first pending question (V9's current question), with actual wording, field, task/question IDs, option labels and explanations. Single choices use radio buttons; multiple choices use checkboxes. When permitted, the user can explicitly select custom input; literal text or structured JSON text goes to V9 for parsing/validation. A question with neither usable options nor custom permission is explicitly unsupported, not silently transformed.

The provider-owned hook retains the confirmed session through pending/error states and panel toggles. Form, new-plan submission and repeat-answer actions are disabled during mutation. A confirmed response updates the plan, fields, evidence, next question or ready configuration. Only the user's explicit next submission advances further. Pending/other questions remain inspectable. No correction, resume or history browser exists.

Validation errors allow explicit review/edit; stale/unknown outcomes are clearly distinguished. Last-entered custom text is retained through an ordinary same-question validation rejection. Errors do not turn into mock replies. The separate demo mode, API inventory and independent Monaco sample documents continue working. Generated output remains read-only session text; no artifact/draft synchronization was introduced.

## 5. Verification commands and outcomes

All Python execution used the workspace venv below. Sandbox shell startup still failed with `setup refresh had errors`; approved escalated commands were used, not an alternate interpreter. No dependency install was required.

From the V9 repository root:

```powershell
$projectPython = 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv\Scripts\python.exe'
& $projectPython -m unittest tests.test_workbench_api tests.test_workbench_planning tests.test_workbench_answers -v
```

Result: **34/34 passed** (8 passive API, 11 creation/adapter, 15 answer tests). The new tests use real V9 creation/answer/serialization/persistence with deterministic model doubles and temporary session storage. They cover successful custom values, actual OSPF selection and next questions, stable identities/provenance, saved revision advancement, stale hashes/questions/source, malformed/legacy restoration, invalid kinds/options, duplicate/conflicting requests, locks in both directions, health during mutation, V9 rejection persistence, model/save failures and absence of subprocess/device network activity or inventory/catalog changes. No mock test is presented as live inference evidence.

Final documentation verification passed: all 20 listed paths resolve (18 source/document paths plus two retained live sessions), the five checked backend/test files parse, Markdown fences are balanced and changed handover/governance documents contain no trailing whitespace or unfinished verification placeholders. `git diff --check` exited 0. The scoped diff contains no V9 domain, inventory or knowledge-source edit; no commit was made.

Initial new-test failures were test/adapter issues resolved in this iteration: the fixture incorrectly assumed VLAN name was required (it is optional); it now asks for the actual required missing VLAN ID. A malformed stored payload originally returned generic 500; it now returns specific 409 without rewriting. Tests were not weakened to bypass V9 validation.

CLI verification, run from `frontend/`:

```powershell
& 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv\Scripts\python.exe' ..\main.py --help
```

Result: exit 0, existing plan/resume/interactive/edit flags retained. Core CLI files were not modified.

Frontend checks, from `frontend/`:

```powershell
npm.cmd run lint
npm.cmd run build
$env:RUN_LIVE_V9='1'
npm.cmd run test:e2e -- --reporter=line
Remove-Item Env:RUN_LIVE_V9
```

Results: lint passed (also rerun after adding the browser test file); production build passed with 2,320 modules and the existing large Monaco chunk warning. **13/13 Playwright checks passed**, including 5 new deterministic answer browser tests, 1 new live answer test, and the 7 existing shell/creation checks including live creation. Deterministic browser coverage checks stable-option submission, pending state, retained plan, next question, literal numeric custom input, ready output, stale blocking, exact same-ID transport retry, rejection/new-revision handling, mock separation, inventory and Monaco. This is automated browser verification; no separate manual visual inspection was claimed.

### Legacy regression comparison

The following bounded unchanged V9 suite was run:

```powershell
@'
import io, unittest
from collections import Counter
names = ['tests.test_runtime_intent_integrity','tests.test_native_vendor_runtime','tests.test_file_runtime','tests.test_target_resolution','tests.test_clarification_flow']
result = unittest.TextTestRunner(stream=io.StringIO()).run(unittest.defaultTestLoader.loadTestsFromNames(names))
print('REGRESSIONS', result.testsRun, 'failures', len(result.failures), 'errors', len(result.errors), flush=True)
for case, trace in result.failures:
    print('FAIL', case.id(), trace.splitlines()[-1][:220], flush=True)
for error, count in Counter(trace.splitlines()[-1] for _, trace in result.errors).items():
    print('ERROR', count, error, flush=True)
raise SystemExit(not result.wasSuccessful())
'@ | & 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv\Scripts\python.exe' -u -
```

Result: **61 methods; 2 assertion failures and 192 template-example subcase errors**, exactly matching the recorded Iteration 4 failures in these five modules. The other 58 methods passed. The command correctly exited 1. The failures remain `TargetResolutionTests.test_unique_attributes_and_aliases` (Huawei matches R2 and SW2), `ClarificationFlowTests.test_unknown_version_and_context_changes_cannot_reuse_output` (expected ValueError not raised), and `ClarificationFlowTests.test_all_existing_vendor_templates_render_complete_examples` (32 missing example keys across six devices). No new failing case was observed and no unrelated historical test, catalog or inventory fix was attempted. Runtime-intent, native-vendor and file-runtime suites passed, alongside the remaining target/clarification cases. The isolated ingestion test uses a test double; its printed indexing line is not a rebuild of the local runtime index.

### Actual local readiness and browser answer evidence

Executed this read-only readiness probe from the V9 root:

```powershell
@'
from app.config import OLLAMA_LLM_MODEL, OLLAMA_EMBED_MODEL, runtime_mode
from app.llm import llm
from app.embeddings import embeddings
from app.vectorstore import get_vectorstore
print('CONFIG', runtime_mode(), OLLAMA_LLM_MODEL, OLLAMA_EMBED_MODEL, flush=True)
print('INFERENCE', repr(llm.invoke('Reply with exactly OK.').content), flush=True)
print('EMBEDDING', len(embeddings.embed_query('Iteration 5 readiness probe')), flush=True)
vs = get_vectorstore()
print('INDEX', len(vs.get(include=[])['ids']), flush=True)
print('RETRIEVAL', [r.metadata.get('operation_id') for r in vs.similarity_search('configure OSPF', k=2)], flush=True)
'@ | & 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv\Scripts\python.exe' -u -
```

Observed on 2026-10-09: file runtime, configured LLM `qwen2.5:1.5b`, embedding model `nomic-embed-text`; actual inference returned `OK`, actual embedding length was 768, the existing 44-record index passed V9 compatibility checks, and semantic retrieval returned `configure_ospf` and `remove_ospf_interface`. No ingestion/publication or service management was performed. Passive API health remains `not_checked` for AI.

The real browser submitted `Configure OSPF on the Penang edge Juniper router` through unmocked FastAPI/V9. It received session `2cbaabf3-6470-4ed1-b4c9-8da8f665084f`, identified `dev-r3` / Juniper, and displayed current `interfaces` question `999879095610ba36`. The browser selected actual option `4eaa1cddf9a1884a` (`ge-0/0/0`) and submitted it once. HTTP 200 confirmed acceptance, the same session identity and a new saved revision:

```text
b4d7d80727c2ed7a9de08513905abab36277912cc443455f04c3748380f615b3
```

The saved file independently confirmed `interfaces: [{name: "ge-0/0/0"}]`, `accepted: true`, and provenance `context:inventory:dev-r3:interfaces:ge-0/0/0`. V9 remained `needs_clarification` and returned `interfaces[0].area`; no automatic second answer was sent. This verifies one actual option-selection round trip, not every question type. The deterministic custom-VLAN-ID test verifies progression to ready, while the separate live creation regression returned ready configuration. Inference/retrieval were exercised separately; no claim is made that every clarification step invokes either service.

## 6. Remaining issues and risks

- Process-local locking/idempotency only; no durable journal, multi-worker support, cross-process CLI lock or cancellation. Timeout can leave a successfully saved result unseen by the browser.
- Stale source/session conflicts deliberately stop this workflow. General retrieval/resume/reload recovery is not implemented; do not bypass stale guards or replay old answers blindly.
- Version-1/malformed/incompatible saved sessions are not migrated. Published-runtime/source checks exist, but the live round trip was file-mode only.
- `selection` and `custom` transport kinds are supported through existing V9 semantics; only the explicitly tested option/value workflows are verified. The GUI is a generic control, not a complete schema-form generator.
- V9 may persist rejected history/feedback. Errors after persistence can still leave changed disk state; the UI must retain uncertainty rather than assume rollback.
- Existing legacy failures, catalog drift, Monaco bundle size and inherited dependency advisories remain outside this iteration.

## 7. Next single recommended iteration

**Iteration 6 — Multi-task plan review:** make an existing returned multi-intent/multi-device session easier to inspect by task/target, preserving validation/evidence and read-only generated previews. Keep this a bounded presentation deliverable; do not combine general session history/resumption, corrections, inventory CRUD or draft persistence. Iteration 6 has not begun.

## 8. Exact reproduction and launch instructions

Backend PowerShell (one worker, no reload):

```powershell
Set-Location 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\network_rag_catalog_lab\network_rag_catalog_v2'
$projectPython = 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv\Scripts\python.exe'
& $projectPython -m uvicorn app.workbench.api:app --host 127.0.0.1 --port 8000
```

Frontend in another PowerShell:

```powershell
Set-Location 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\network_rag_catalog_lab\network_rag_catalog_v2\frontend'
npm.cmd run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:5173/`, choose Local V9, submit the OSPF request above, read the actual current question and select one offered interface. Submit once. Confirm the pending indicator and disabled form; then inspect the confirmed next area question, parameters, task identity and session result. Do not assume the question order if model/runtime behavior differs: controls come from the actual result. For a text-to-ready example, use `Create VLAN named STAFF on R1`, then enter a valid VLAN ID when V9 asks for it.

Monaco sample edits remain unrelated in-memory examples. Switching to Demo mock must not send an answer. Stop the backend during a request to see the unknown outcome warning; only same-ID retry against the same process is offered. Do not restart and blindly resubmit. Use ordinary file inspection—not V9's refreshing `load_session()`—to diagnose an ambiguous saved outcome.

To rerun deterministic browser tests without generating live sessions, omit `RUN_LIVE_V9` and run `npm.cmd run test:e2e -- --reporter=line`; both live tests will be explicitly skipped. Run the backend commands in section 5 from the V9 root. Stop after this iteration.
