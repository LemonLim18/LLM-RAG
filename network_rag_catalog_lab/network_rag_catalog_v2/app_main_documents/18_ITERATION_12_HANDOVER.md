# Iteration 12 — Native Editable Configuration Workspace

## 1. Objective and completion status

**Completed.** Implementation and browser verification performed on 2026-10-09; final build/backend verification and handover completed on 2026-10-10 after interrupted tool runs. This is Iteration 12, continuing the already-completed Iteration 11 original store.

**Delivered outcome:** A confirmed device-specific V9 output opens as a normal editable working file without requiring a manual Save Original step. The engineer edits in Monaco, saves with Ctrl+S, restarts the backend/browser, and reopens the persisted text from Explorer. The captured original remains immutable. One central editor is active, not a permanently split comparison view.

No core V9, inventory, catalog, session-persistence, creation-receipt or historical FYP behavior was changed. No dependencies were installed/upgraded and no Git commit was made. DiffEditor, AI proposals, knowledge management, execution and Iteration 13 remain unimplemented.

## 2. Architecture and source-to-document flow

The existing planner/clarification functions save a V9 session. Its confirmed API response contains `plan.tasks[]`, identified by `intent_id`; `logical_intent_id` associates device-expanded tasks. A selected task's `configs[index]` supplies the explicit device identity and text. Existing task review and transient Monaco preview still derive content from the provider-owned confirmed response.

The normal working-file opener performs two operations:

1. Reuse Iteration 11's `POST /api/v1/workbench/artifacts/generated-originals` with session ID, exact saved-byte revision, task ID, device ID and configuration index. **No configuration text is submitted as source authority.** The existing passive saved-session validator and capture association checks remain authoritative.
2. Pass the confirmed original ID to the new working-document POST. The backend verifies the stored original using `read_original()`, then creates or reopens its one default working document. A successful response is adopted into the provider-owned working-buffer hook and opened in Monaco.

The concepts remain distinct:

- **A — V9 saved session:** the engine's existing snapshot, untouched by working saves.
- **B — generated original:** the immutable archive from one verified snapshot, still separately readable.
- **C — working document:** separately persisted editable text referencing B; always unvalidated/not deployed.
- **D — pending AI modification:** future work, not implemented or represented by speculative endpoints.

Single-output automatic opening runs only from successful user creation/answer callbacks: session `ready`, no pending questions, exactly one task, one nonempty configuration and one matching target. Multiple outputs require explicit selection through shared Open in Editor actions in chat/task review. Historical restore and passive reads never create documents. Transient previews and saved originals offer Open for Editing. Engineers therefore do not need to manually archive an original before editing, while the same verified original-capture boundary is retained internally.

## 3. API, schema, storage and revisions

Backend entry point remains `app.workbench.api:app`. New routes:

| Method/path | Request | Confirmed response |
|---|---|---|
| POST `/api/v1/workbench/working-documents` | `{original_id}` | `OpenWorkingResponse`: API version 1, `created` (201) or `reopened` (200), full document |
| GET `/api/v1/workbench/working-documents` | None | `WorkingList`: API version, limit, deterministic verified metadata list |
| GET `/api/v1/workbench/working-documents/{document_id}` | Bounded document ID | Full `WorkingDocument` |
| PUT `/api/v1/workbench/working-documents/{document_id}` | `{expected_revision: UUID, content: string}` | Full saved `WorkingDocument` with new revision |

Strict Pydantic models reject extra fields. Domain failures return safe `{detail: {code, message}}` errors without filesystem paths; malformed transport data receives FastAPI 422. Domain outcomes include missing (404), stale/corrupt/identity conflict (409), content too large (413), and busy/storage/capacity failure (503). Responses are `Cache-Control: no-store`. Local CORS adds PUT to the existing bounded origin configuration.

Storage is `STORAGE_DIR/workbench/working_documents`, normally `storage/workbench/working_documents`, excluded from Git. One version-1 JSON record contains:

- `document_id`: `working-` plus the verified original ID's 64-hex digest suffix.
- `original`: the existing safe `OriginalMetadata` projection, including source session/revision/task/device/index, logical intent, operation/category, device metadata and historical authority.
- Exact working `content`, its UTF-8 SHA-256, `encoding: utf-8`.
- A persisted UUID `revision`, monotonic `save_sequence`, UTC creation/update timestamps.
- `validation: unvalidated`, `deployment: not_deployed`.
- A SHA-256 of canonical serialized record fields excluding the record hash itself.

Repeated open from the same original returns the existing working document **without resetting edits**. Different originals produce different document identities even when their text is identical. The initial working text exactly copies the verified original. Every successful save, including unchanged text and A→B→A, generates a new UUID revision and increments the sequence. Revision comparison is not based on content hash, so old requests cannot pass merely because the content returned to an earlier value.

Limits: 1 MiB UTF-8 content; 8 MiB serialized record; 128 directory entries including orphan temporaries. Listing is bounded and deterministic; no eviction, automatic repair, migration, deletion or general filesystem browsing. Identifiers and paths are checked, redirected/symlink storage is rejected, and records are validated for schema, identity, hashes and timezone-aware timestamps. Existing corrupt records are not overwritten. Working reads remain independent of later source-session revision changes.

### Atomicity and concurrency boundaries

Create/save use the existing `PlanningService` process mutation gate, also used by planning, answers, original capture and inventory registration. New creation uses an exclusive sibling temporary, complete serialization/write, flush/fsync and atomic no-clobber hard-link publication. Save checks the expected revision, writes/fsyncs a sibling temporary, rechecks the stored revision, then uses atomic `os.replace`. The resulting stored record is read and verified before confirmation. Temporary cleanup is best effort.

Pre-publication failures leave the previous document intact; response failure after publication can be ambiguous. Fresh-process GET exposes the persisted revision/content, and replaying an old save revision is rejected. Create identity is restart-stable and idempotent; saves are not durable exactly-once requests. The final recheck does **not** provide cross-process compare-and-swap. Use one backend worker; independent writers, power loss, OneDrive synchronization and privileged external tampering are not guaranteed. No V9 planner/model/retrieval import is needed for working reads or saves.

## 4. Native Explorer/editor behavior and recovery

Configurations → **Working Files** lists actual backend records, with passive refresh and task/device/output labels. Saved Originals remains available below it. `useWorkingDocuments` owns only working-response/buffer state; it is not another plan store. Each open file has its confirmed saved record and independent current text, dirty state and save status. Reopening an already-open document preserves that buffer. A delayed open may populate the cache but cannot steal a newer navigation choice. A delayed save updates the confirmed baseline without replacing edits made while the request was pending.

The editor uses `inmemory://v9-working/{document_id}/configuration`, separate from sample, transient-preview and saved-original namespaces. Working tabs include a short document identity to distinguish otherwise identical labels. Monaco is genuinely editable; auto-indentation is disabled to avoid adding unwanted whitespace to pasted CLI text. Models are disposed on view switches, while provider-owned text survives. Undo/cursor history across model disposal is not retained.

Ctrl+S/Command+S and Save operate only on the active working document. Samples and originals have no working save binding. Pending saves are guarded synchronously; edits may continue. Dirty working text triggers a browser before-unload warning but is **not** persisted in localStorage. Browser/backend restart recovers saved content through Explorer, not unsaved buffers or a stored full plan.

Stale or uncertain saves retain local text and block blind retry. **Inspect saved state** performs GET only. The engineer can inspect the returned revision/text and explicitly choose to retain local text against the observed revision or discard it after confirmation. Equal content is reported as observed equality, not proof of which HTTP request wrote it. A concurrent later change still fails the next expected-revision check.

Original capture and working creation are deliberately two operations, not a transaction. If capture succeeds but creation fails, the original remains discoverable; opening it for editing reuses that baseline. An uncertain create can be investigated through passive Working Files refresh. No automatic mutation retry, replacement source ID or fake success occurs. Historical/current-validity-not-checked labels persist regardless of whether working text equals the original. Nothing implies deployment, current device state or vendor certification.

## 5. Focused FYP engineering reference

Inspected only relevant historical frontend paths under `app_main_documents/Net_Topo_View-intentparse/frontend/`:

- `components/ansible/PlaybookEditor.tsx`: callback-driven tabs, change/save controls and Monaco.
- `components/ansible/AnsibleFileTree.tsx`: API-backed discovery and file-opening callbacks.
- `views/AnsibleStudioView.tsx`: shared `handleFileOpen`, dirty tab content and `handleSave` routing.
- `components/ansible/AnsibleChatPanel.tsx`: generated-path/file links through an open callback.
- `components/ansible/JobStatusBar.tsx`: coupled approval/deploy/output/SSH behavior, intentionally excluded.

Retained concepts: one opening path for chat/tree/editor actions, dirty document tabs, explicit in-editor save, confirmed backend discovery. Rejected: arbitrary path writes, template/schema routing, job-path parsing, unconditional dirty clearing after asynchronous saves, approval/deploy controls, Ansible jobs and SSH output. **No prototype code was copied.** Stable source-derived identities and revision-checked native working records fit V9 better than the prototype's path/controller architecture. The supplied screenshot informed interaction goals, not authorization for execution or reproducing its navigation.

## 6. Files added, modified and removed

All paths below are relative to the V9 repository root. Pre-existing Iteration 10/11 dirty/untracked changes were preserved; this list describes Iteration 12 additions/edits, not every item in `git status`.

Added:

- `app/workbench/working_documents.py`
- `tests/test_workbench_working_documents.py`
- `tests/workbench_working_server.py`
- `frontend/src/services/workingApi.ts`
- `frontend/src/features/workspace/useWorkingDocuments.ts`
- `frontend/src/features/workspace/GeneratedWorkingAction.tsx`
- `frontend/src/features/workspace/WorkingEditor.tsx`
- `frontend/src/features/explorer/WorkingFiles.tsx`
- `frontend/tests/working-documents.spec.ts`
- `frontend/playwright.working.config.ts`
- `frontend/working-integration/persistence.spec.ts`
- `app_main_documents/18_ITERATION_12_HANDOVER.md`

Modified:

- `.gitignore`
- `app/workbench/api.py`, `app/workbench/planning_service.py`
- `tests/test_workbench_planning.py` (exact authorized mutation-route assertion)
- `frontend/src/app/WorkbenchProvider.tsx`, `frontend/src/app/types.ts`
- `frontend/src/components/layout/StatusBar.tsx`
- `frontend/src/features/chat/useLocalPlanning.ts`, `frontend/src/features/chat/PlanningResult.tsx`
- `frontend/src/features/explorer/ExplorerPanel.tsx`
- `frontend/src/features/workspace/WorkspacePanel.tsx`, `TaskReviewPanel.tsx`, `GeneratedConfigurationViewer.tsx`, `SavedOriginalViewer.tsx`
- `frontend/src/styles/workbench.css`
- `frontend/tests/saved-originals.spec.ts`, `frontend/tests/workbench.spec.ts`
- `app_main_documents/03_DEVELOPMENT_PROGRESS.md`, `app_main_documents/04_ARCHITECTURE_DECISIONS.md`

Removed: none. `workbenchReducer.ts` already had prior changes; no new reducer modification was needed in Iteration 12. Original storage/serialization and the core V9 engine remain unchanged. No dependencies added.

## 7. Verification commands and outcomes

From the V9 repository root, using only the project venv:

```powershell
& 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv\Scripts\python.exe' -m unittest tests.test_workbench_working_documents -v
& 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv\Scripts\python.exe' -m unittest discover -s tests -p 'test_workbench*.py'
& 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv\Scripts\python.exe' main.py --help
git diff --check
```

- Focused working tests: **12 passed**. Cover exact initial text/provenance, independent identities, empty/Unicode/BOM/line-ending saves and limits, missing/corrupt records, repeated open after edit, ABA/same-content stale rejection, partial-write/flush/fsync/replace faults, partial original/create failure, fresh-interpreter retrieval, process-gate concurrent writes and passive/protected-source checks.
- Full workbench suite: **97 passed** (85 existing plus 12 new). Final resumed rerun on 2026-10-10: 97 tests in 53.172 seconds, exit 0. Logged planning failures are deliberately injected test cases, not failed tests.
- CLI help: passed, existing arguments remain available. This is a compatibility smoke check, not live inference verification.
- Diff whitespace check: passed during implementation and final review. All three changed governance/handover documents passed explicit trailing-whitespace and balanced-code-fence checks; all five FYP source references were verified to exist.

From `frontend/`:

```powershell
npm run lint
npm run build
npx playwright test
npx playwright test --config playwright.working.config.ts
```

- ESLint: passed, including the new frontend/test files.
- TypeScript/Vite production build: passed; final resumed build on 2026-10-10 transformed 2,335 modules in 28.78 seconds. Existing Monaco main chunk remains about 3.07 MB (813 KB gzip), with the existing >500 KB warning; no dependency/bundle optimization was attempted.
- Established browser regression suite: **40 passed, 2 skipped**, including 7 new working-file checks. Covers actual Monaco, automatic single-output opening, explicit multi-device links, dirty buffers, Ctrl+S, independent samples/originals, reload discovery, pending/late-save protection, stale/lost saves, passive recovery, partial capture/create failure, confirmed-answer completion and late-navigation protection. Existing inventory, clarification, review, recovery, mock chat and preview checks pass.
- Separate unmocked test: **1 passed**. A temporary real version-2 VLAN session is restored through FastAPI, automatically captured by Open in Editor, edited from `SALES` to `ENGINEERING`, and saved using real Ctrl+S/PUT. A fresh backend interpreter and fresh browser context reopen the working file through Explorer. Original/session/inventory bytes stay unchanged; session mtime stays unchanged. Exactly capture POST, working POST and save PUT occur; no planning/answer/execution mutation. No Ollama is required. The restarted-editor screenshot was visually inspected.

The two opt-in live-AI tests were skipped, not counted as inference/RAG evidence. The independent Iteration 11 restart test and broad historical domain/catalog suite were not rerun. Historical 2 assertion failures / 192 example-subcase errors remain unresolved and are not newly introduced working-document failures.

### Failures encountered and corrected

An early focused test expected an adapter error where Pydantic correctly rejected a surrogate; the assertion was corrected. Accidental imported test-class collection was removed. New browser test syntax and an overly broad alert selector were corrected. An existing connectivity assertion was scoped to its actual status bar rather than racing unrelated loading statuses. Original-only tests now use passive historical restore so they continue proving explicit capture without triggering the newly authorized single-output opening workflow; their no-extra-mutation assertion remains exact. Monaco's default automatic indentation added a space after an entered newline; disabling automatic indentation fixed exact editing behavior. No assertion was suppressed or old workflow removed.

Later verification commands were interrupted. A sandboxed build failed with `EPERM` resolving `src/main.tsx`, and the sandboxed venv launcher stalled with a base-launcher path diagnostic. These were environment/tool failures, not Playwright failures; the already completed 40-pass browser run was collected rather than repeated. The final approved build and full 97-test backend rerun outside that sandbox passed. No global Python/Miniconda command was used; Python commands explicitly use the required venv executable.

## 8. Remaining issues and risks

- Single backend process only; no cross-worker/CLI CAS or power-loss/OneDrive durability guarantee. Integrity hashes do not prevent privileged tampering.
- No durable save-request journal. An uncertain write may have committed; inspect and explicitly reconcile. A lost create response is discoverable/idempotent by original identity, not exactly-once execution.
- Dirty buffers survive view changes but not browser reload; before-unload warning is best effort. No autosave, browser-local document persistence, undo/cursor restoration across disposed models, tab-close/history framework or deletion.
- Source metadata is historical. Working text is never revalidated, deployed or written back into V9. No current catalog/inventory validity claim.
- Bounds/corrupt records can block listing. No automatic repair/cleanup/eviction. Keep originals and working files together in external backups.
- Existing broad-suite catalog failures, dependency advisories, model-readiness limitations and Monaco bundle warning remain outside scope.

## 9. Reproduction and launch instructions

Backend PowerShell window (one worker):

```powershell
Set-Location 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\network_rag_catalog_lab\network_rag_catalog_v2'
& 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv\Scripts\python.exe' -m uvicorn app.workbench.api:app --host 127.0.0.1 --port 8000
```

Frontend PowerShell window:

```powershell
Set-Location 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\network_rag_catalog_lab\network_rag_catalog_v2\frontend'
npm run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:5173`. Submit a Local V9 request through the existing AI path and answer its actual questions if necessary. Once a single complete device output is confirmed, its working editor opens without a manual Save Original step. For multiple outputs, choose the correct Open in Editor link in chat/task review. For a historical saved session, restore it explicitly and choose Open in Editor/Open for Editing; restore alone makes no files.

Edit the working text, observe its dirty dot, and press Ctrl+S. Wait for Saved working content before closing. Stop/restart both services with the same storage, reload, and select the file under Working Files. Inspect the original under Saved Originals: it remains read-only and unchanged. Switching to Samples keeps those documents independent.

For an AI-independent real-backend demonstration, stop manual services occupying ports 8000/5173 and run `npx playwright test --config playwright.working.config.ts` from `frontend/`. It owns a dedicated temporary directory, starts/restarts only its test backend and leaves user session/inventory storage untouched. The standard full browser suite also requires these ports free. Tests remove only their own exact temporary directory.

## 10. Next single recommended iteration

**Iteration 13 — on-demand Monaco Review Changes**, comparing the active working document (including unsaved text) against its immutable original, then returning to ordinary editing without losing edits. No automatic saves, AI proposals, Keep/Undo agent actions, knowledge screens or deployment. This recommendation is not authorization to start it. Stop after Iteration 12.
