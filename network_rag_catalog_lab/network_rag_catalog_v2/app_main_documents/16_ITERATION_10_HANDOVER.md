# Iteration 10 — Read-only V9 Configuration Viewing in Monaco

Date: 2026-10-09

## 1. Iteration identifier and objective

Iteration 10 delivers exactly one outcome: explicitly open a backend-confirmed, device-specific V9 configuration in a clearly labelled read-only Monaco document. Plan review, clarification, recovery, synthetic registration and independent editable samples remain available. No backend, artifact storage, drafts, diff, execution or refresh feature is added.

## 2. Completion status

**Completed.** The frontend-only viewing workflow and required lifecycle protections are implemented. Lint, production build and all 29 deterministic browser tests pass, including 7 new Monaco-viewing tests; 2 optional live-AI tests were skipped. No backend contract or runtime changes were needed. No live inference verification is claimed.

## 3. Files added, modified or removed

Paths relative to the V9 repository root.

Added:

- `frontend/src/features/workspace/GeneratedConfigurationViewer.tsx`
- `frontend/src/features/workspace/generatedPreview.ts`
- `frontend/tests/generated-preview.spec.ts`
- `app_main_documents/16_ITERATION_10_HANDOVER.md`

Modified:

- `frontend/src/app/types.ts`
- `frontend/src/app/workbenchReducer.ts`
- `frontend/src/app/WorkbenchProvider.tsx`
- `frontend/src/features/workspace/TaskReviewPanel.tsx`
- `frontend/src/features/workspace/WorkspacePanel.tsx`
- `frontend/src/components/layout/StatusBar.tsx`
- `frontend/src/styles/workbench.css`
- `app_main_documents/03_DEVELOPMENT_PROGRESS.md`
- `app_main_documents/04_ARCHITECTURE_DECISIONS.md`

None removed. No dependencies added/installed, no Git commit, no FYP changes. The pre-existing workspace-root untracked `README.md` is untouched. No backend/V9/CLI source, inventory, session persistence, creation receipt, catalog or knowledge-release change belongs to this iteration. Existing test files were not weakened or modified; new coverage is isolated in one spec.

## 4. Architectural decisions and reasons

### Verified source-to-Monaco data flow

`WorkbenchProvider` owns `useLocalPlanning().state.result`, the confirmed `SessionSnapshot`. Creation, successful clarification, saved rejection responses and explicit saved-session/creation-outcome recovery already update that same state. This iteration does not change their HTTP clients or contracts.

`WorkbenchProvider` synchronizes session ID, saved revision and task IDs into the reducer. The reducer stores only presentation coordinates, not a duplicate plan or configuration. `TaskReviewPanel` selects a task by `plan.tasks[].intent_id`; `logical_intent_id` separately links device-expanded tasks to their originating intent. It renders actual `configs[]` entries belonging to that task.

An **Open read-only in Monaco · output N** action records the selected session/revision/task/device/entry coordinates and activates **V9 preview**, a third workspace view next to Samples and V9 Plan Review. `GeneratedConfigurationViewer` resolves those coordinates against the current provider-owned result on every render. Its Monaco `value` is exactly the selected entry's `configuration` string: no trimming, formatting, command interpretation, concatenation, sample substitution or semantic validation.

The inspected existing producer `app/pipeline.py` appends one configuration dictionary for each task target with `device_id`, `hostname`, `vendor`, `platform`, `version`, `parameters` and `configuration`. `PlannedTask.configs` and the existing frontend contract permit multiple entries. No new backend artifact ID or transport field was needed.

| Viewer fact | Existing source |
|---|---|
| Session and saved revision | `result.session.session_id`, `result.session_revision` |
| Task, logical intent, operation, status | `plan.tasks[].intent_id`, `logical_intent_id`, `operation_id`, `status` |
| Device association | That task's `configs[index].device_id`, checked against `target_devices[].id` and non-null `task.device_id` |
| Device label/vendor/platform | The selected configuration entry's returned metadata; absence says Not reported |
| Content | That exact entry's `configuration` string |
| Runtime/source authority | Existing `plan.runtime_authority` and `knowledge_snapshot_id`, without current-authority probing |
| Historical/unverified presentation | Existing `localPlanning.state.historical` |

The action is absent for missing/empty/non-string content or a missing/mismatched explicit device association. Existing plaintext plan review remains inspectable, but the viewer does not guess identity from hostname, task list position, explorer selection or sample IDs. Multiple entries for one device are distinguished by their snapshot-scoped entry index. No other task's configuration is searched as a fallback.

### Presentation identity and model lifecycle

Presentation selection is `{sessionId, sessionRevision, taskId, deviceId, configIndex}`. Monaco path is:

```text
inmemory://v9-preview/<encodeURIComponent(JSON.stringify([sessionId, sessionRevision, taskId, deviceId, configIndex]))>/configuration
```

The encoded tuple avoids delimiter collisions. Device-expanded tasks use their distinct actual task IDs, not just logical intent. The entry index is valid only within that exact saved revision; it is not a persistent artifact identity. Reordering/replacing output under a new revision cannot silently reuse an old entry index.

Generated models use a namespace separate from existing `inmemory://demo/...` sample models. The generated `Editor` is keyed by its path and uses `keepCurrentModel={false}`, `saveViewState={false}`. Switching away, choosing another output or closing/invalidation disposes the generated editor/model. Returning to an unchanged selected preview recreates it from the same confirmed response. Only one generated preview is open at a time; no hidden generated-tab registry or model history is introduced.

The sample editor and its reducer-owned in-memory content remain unchanged. Sample model switching retains the prior established behavior; preview lifecycle code never looks up, mutates or disposes sample paths. Unsaved content survives switching between views, and samples remain editable after viewing read-only output.

### Updates, invalidation and historical state

- A changed saved revision or replacement session clears preview selection, opens the existing plan review and shows an explicit closed-preview notice. Even unchanged text requires an explicit reopen against the new snapshot; there is no automatic generation comparison or migration of entry indexes.
- Same-session task selection remains governed by existing reducer logic. The viewer independently rechecks current session/revision/task/config/device before rendering, so it cannot show the old output during the render before the provider synchronization effect runs.
- If creation clears the confirmed result while pending, the viewer cannot render its old content. Missing/withdrawn or inconsistently associated output yields an unavailable message, never an empty fabricated configuration.
- A passive restore enters the same provider state with `historical: true`. The viewer displays **Saved historical state · current validity not checked**. Identical saved snapshots can be reopened without claiming revalidation.
- Inventory registration or explicit reload of a changed inventory revision uses the existing `noteInventoryChange` behavior. The result itself is retained and its viewer immediately receives the historical label; configuration content and saved revision are not changed.
- Successful explicit answers continue to use V9's confirmed result and existing freshness semantics. `ready`/`rendered` are reported as V9 statuses, never deployment. Viewing never submits an answer or refreshes the session.

### Read-only and provenance guarantees

Monaco has both `readOnly: true` and `domReadOnly: true`; there is no generated-document `onChange`, sample update action, save callback or HTTP request. Typing/paste are tested against the real editor/model. Metadata explicitly identifies V9-generated, read-only, preview-only/non-deployed content and distinguishes it from editable samples and separately persisted artifacts.

The original response string remains authoritative and untouched. Monaco is a text presentation model, not a byte archive: the tests verify exact uniform CRLF and LF strings, repeated lines and trailing newlines. Mixed line-ending/BOM archival fidelity is not claimed as a persistence feature; no text is serialized back to V9 at all. Network CLI syntax coloring is the existing lightweight presentation grammar, not vendor validation.

No backend source or contract changed. Artifact capture, editable derivatives, draft validation, diff, history, backend model calls and any execution remain intentionally deferred. No FYP investigation/reuse was necessary for this presentation boundary.

## 5. Tests run, exact commands and outcomes

Working directory:

```powershell
Set-Location 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\network_rag_catalog_lab\network_rag_catalog_v2\frontend'
npm.cmd run lint
npm.cmd run build
npm.cmd run test:e2e -- tests/generated-preview.spec.ts --grep 'real Monaco' --reporter=line
npm.cmd run test:e2e -- tests/generated-preview.spec.ts --reporter=line
npm.cmd run test:e2e -- --reporter=line
```

Final results: **lint passed**; **TypeScript/Vite build passed** (2,326 modules); **29 browser tests passed, 2 skipped** in 56.3 seconds. Seven of the passing cases are new preview tests. Before adding the compact pending-to-ready case, the focused read-only check passed 1/1, the initial preview subset passed 6/6, and the initial full suite passed 28 with 2 skipped. Final lint was rerun after the last test addition. The production source was unchanged after its passing final build.

The screenshot captured by the compact-desktop test was visually inspected: the actual syntax-highlighted Monaco surface, explicit read-only/provenance controls, explorer, Copilot and activity panel are visible and usable at 1280×720. This is inspection of a deterministic automated-browser screenshot, not a separate live-model/manual workflow. The reproducible image is written under Playwright's ignored `test-results/generated-preview-pending--be37e-ion-at-compact-desktop-size/read-only-preview.png`.

Seven new deterministic browser tests cover:

1. Actual rendered Cisco Monaco content and model/options; typing and clipboard paste leave it unchanged; sample editing, original sample content and separate namespaces survive view switches; two device-specific tasks of one intent and a second intent/device output have distinct identities. Opening/closing/switching previews produces no API mutation.
2. Multiple entries, including repeated-device entries, use distinct snapshot paths; pending/no-output and malformed/mismatched association cases cannot open fabricated documents; generated models are disposed when hidden.
3. Same-session confirmed answer revision closes the old model and displays only new output after explicit reopen. This includes an intentionally adversarial transport fixture with retained output alongside a question; it does not claim V9's current request-wide renderer normally emits that combination.
4. A normal no-output/pending-question fixture becomes ready after an explicit confirmed answer and opens its newly returned configuration. Compact 1280×720 viewport checks real editor width/height and captures a screenshot.
5. Explicit same-session reads withdrawing/reordering configs invalidate old selection. New-session replacement cannot retain the prior session's output.
6. Explicit historical restoration after reload uses the saved response, labels it unverified and does not automatically GET/replay mutations. Reopening a preview causes no extra request.
7. Explicit inventory-revision reload marks the still-open preview historical without changing its content, path or saved revision; no inventory POST occurs in this check.

The existing suite covers planning, clarification/retry/rejection, known-session and creation-outcome recovery, plan review, device registration/error handling, sample edits, resizing, mock chat and unavailable-backend behavior. Registration mutations remain controlled test doubles in the standard suite; no real inventory registration was performed for Iteration 10.

Initial issues resolved: TypeScript required an explicit narrowed configuration-record return type. Chrome's native EditContext input is zero-sized, so tests verify the visible `.monaco-editor`/rendered lines plus attached labelled input and actual model/options, rather than incorrectly requiring the native input itself to have size. Importing an unversioned Vite module instantiated a second loader in the test harness; the test now imports the exact versioned resource URL already used by the application. Assertions still compare complete model text and test real typing/paste; no production test hook or mock editor was added.

The sandboxed Vite build hit the existing OneDrive `EPERM realpath` restriction; approved outside-sandbox build/browser runs passed. Playwright starts the existing backend using only `C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv\Scripts\python.exe`, as already configured. No package install or alternate Python interpreter was used.

The existing >500-kB Monaco chunk warning remains (about 3,048 kB uncompressed JS). It is not a new build failure. Backend unit/domain tests and live inference/RAG were not run because neither backend source nor contracts changed. The historical 2 domain assertion failures and 192 template-example errors are not repaired or newly reverified. The optional real creation/clarification tests remain skipped unless explicitly enabled.

Documentation/scope verification: all 13 listed added/modified paths exist; the handover's code fences are balanced; `git diff --check` passes. Final source changes are restricted to the listed frontend files and required documentation. No newly failing check remains. No automatic next-iteration work or Git commit was performed.

## 6. Remaining issues and risks

- One transient selected preview, not a persistent generated-artifact/tab-history system. Reopening from current Plan Review is required after any changed saved revision. Cursor/scroll state for a disposed preview is not retained.
- Displaying returned output does not establish current catalog/inventory validity, model participation, operational safety or deployment. Historical flags use existing confirmed workbench state; this iteration adds no new freshness probe.
- Incomplete legacy config identity remains inspectable in plaintext but cannot open as a device-specific Monaco document without a bounded future compatibility decision.
- Existing session recovery, mutation coordination, receipt, inventory concurrency, broad baseline and dependency-advisory limits remain unchanged. No runtime correctness claim is inferred from deterministic browser fixtures.
- Monaco owns display-model line endings; no archival byte or arbitrary configuration validation guarantee is made. Source session strings are never written or normalized by this feature.

## 7. Suggested next iteration

**Iteration 11 — Bounded immutable generated-original capture.** Design and implement explicit local capture of one confirmed session/task/device configuration with exact content, provenance and revision association, in separate workbench storage, plus read/restart verification. Scope crash behavior and duplicate capture before coding. Do not combine editable drafts, DiffEditor, deployment, inventory editing or session refresh. This is a recommendation only; no Iteration 11 work has begun.

## 8. Exact reproduction/verification instructions

Backend PowerShell (unchanged, single process):

```powershell
Set-Location 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\network_rag_catalog_lab\network_rag_catalog_v2'
& 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv\Scripts\python.exe' -m uvicorn app.workbench.api:app --host 127.0.0.1 --port 8000
```

Frontend in a second PowerShell:

```powershell
Set-Location 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\network_rag_catalog_lab\network_rag_catalog_v2\frontend'
npm.cmd run dev -- --host 127.0.0.1
```

1. Open `http://127.0.0.1:5173/`. Edit a sample, then choose Local V9.
2. Explicitly restore a known saved session containing actual generated configs (no Ollama needed for passive retrieval), or deliberately create a normal Local V9 plan using the existing workflow. Creation requires its normal dependencies and intentionally persists a session; opening a preview does not.
3. Select a task in V9 Plan Review. Under its generated configuration, click **Open read-only in Monaco · output N**. Confirm device/vendor, read-only label and expandable session/task/device/revision provenance.
4. Try typing/pasting. Text must not change. Switch to Samples, confirm the earlier edit remains and continue editing. Return through V9 preview; the source text must remain unchanged.
5. Review another task/output explicitly. Verify its exact device-specific text. Pending or blocked tasks with no output offer no fabricated editor document.
6. After an explicit answer or saved read returns a new revision, verify the prior preview closes with a notice. Reopen from the current task. Historical restoration and known inventory changes must retain the unverified label.
7. Use the deterministic suite in section 5 to reproduce replacement, withdrawn-output and failure-sensitive lifecycle cases without changing actual inventory or invoking Ollama. Keep ports 8000/5173 free before running Playwright because its config owns both servers.

Stop after Iteration 10. No artifact, working-draft or DiffEditor feature is implemented.
