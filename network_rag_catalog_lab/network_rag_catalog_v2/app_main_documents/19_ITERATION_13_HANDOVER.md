# Iteration 13 — Native Monaco Inline Change Review

## 1. Iteration identifier and objective

Deliver one frontend outcome: review an active working document's changes in a temporary, single-pane native Monaco inline comparison, then accept a whole pending proposal into the editable buffer or reject it without changing accepted text. Existing explicit save remains separate. Manual Review Changes compares unsaved text with the **last confirmed saved working text**, not the immutable original.

The explicit Iteration 13 assignment supersedes the narrower original-versus-working comparison recommendation in the Iteration 12 handover. No real AI editing producer, backend proposal endpoint, document database, knowledge editor or execution is authorized or implemented.

## 2. Completion status

**Completed**, verified 2026-10-10. Native inline whole-proposal acceptance/rejection and last-saved manual review are independently tested in real Monaco. All 20 focused review checks, 40 existing browser regressions, the unmocked save/restart check, 97 backend regressions, lint/build and CLI help pass. Two optional live-AI tests were skipped. No real AI editing, backend contract change or Iteration 14 implementation is included.

## 3. Files added, modified or removed

Added:

- `frontend/src/features/workspace/changeReview.ts`
- `frontend/src/features/workspace/WorkingTextEditor.tsx`
- `frontend/src/features/workspace/InlineChangeReview.tsx`
- `frontend/review-harness/ReviewHarness.tsx`
- `frontend/review-tests/helpers.ts`
- `frontend/review-tests/inline-review.spec.ts`
- `frontend/review-integration/persistence.spec.ts`
- `frontend/vite.review.config.ts`
- `frontend/playwright.review.config.ts`
- `frontend/playwright.review-integration.config.ts`
- `app_main_documents/19_ITERATION_13_HANDOVER.md`

Modified:

- `frontend/src/features/workspace/useWorkingDocuments.ts`
- `frontend/src/features/workspace/WorkingEditor.tsx`
- `frontend/src/app/WorkbenchProvider.tsx`
- `frontend/src/styles/workbench.css`
- `app_main_documents/03_DEVELOPMENT_PROGRESS.md`
- `app_main_documents/04_ARCHITECTURE_DECISIONS.md`

Removed: none. No dependencies installed or changed. No historical FYP, backend/Python, catalog, inventory, session, original-store or working-store source changes. Pre-existing dirty/untracked Iteration 10–12 files were preserved; their Git status must not be attributed to this iteration. No commits were made.

## 4. Architectural decisions and reasons

### Existing authority and integration map

The existing V9 planner produces persisted session task/config records. Existing capture verifies source coordinates and creates an immutable original; existing working creation derives one stable working document from that original. Existing GET/PUT responses remain the authority for saved working content and revision. None of these contracts changes.

`WorkbenchProvider` owns `useWorkingDocuments`. Its existing tab map owns each confirmed saved record and independent accepted in-memory content. The reducer still selects the workspace view only; it does not duplicate working text, planning state or proposal content. `WorkingEditor` selects the active document, exposes review/save controls and retains the normal `WorkingTextEditor` while displaying `InlineChangeReview` in the same central surface.

The new internal path is:

`proposalBase(documentId)` → a future producer's `ChangeProposal` → `stageProposal()` → native inline review → explicit `acceptProposal()` / `rejectProposal()` → existing working buffer → **separate user Ctrl+S** → existing revision-checked PUT.

Only the deterministic test server currently supplies proposals. No production UI pretends that the Local V9 chat produces edits. Manual Review Changes is directly available in normal development/production.

### Minimal proposal schema and safety

`ChangeProposal` contains `proposalId`, `documentId`, `baseRevision`, `baseBufferEpoch`, exact `baseContent`, exact `proposedContent`, `source` and optional `description`. `PendingReview` adds `pending`/`stale` status and an optional reason. Staging returns `staged`, `no_change` or `refused`; user actions return `accepted`, `rejected` or `refused`. Review state is transient, one pending proposal per document, with no localStorage or backend persistence.

The hook reads its latest synchronous tab refs. It checks the current active document, workspace visibility, connected Monaco editor identity, saved UUID revision, monotonic buffer epoch and exact accepted text. Each actual content change—including undo, redo and A→B→A—advances the epoch. Saved-revision changes also invalidate a pending proposal. Staging during a save or unresolved save conflict is refused. Staging never opens/selects a document and never replaces an existing pending proposal. Acceptance repeats guards and verifies the current pending proposal ID; arbitrary merging is not performed. Caller input is copied to prevent later producer mutation.

The validated proposed text limit is 1 MiB UTF-8, matching working storage. Proposal ID/source/description are bounded to 128/120/1,000 characters. IDs remain local proposal identities, not fabricated V9 task or artifact IDs. Source/description are escaped UI text, not provenance certification.

### Monaco lifecycle and acceptance

The installed Monaco 0.57.0 and React wrapper 4.7.0 were inspected locally. The wrapper's controlled `value` path can call `setValue` for a read-only editor. Therefore the retained working editor uses an initial `defaultValue`, direct model change subscription and deliberate undoable reconciliation, not a controlled preview value.

The working model keeps `inmemory://v9-working/{document_id}/configuration`. During review it stays mounted, hidden and read-only. The native DiffEditor has separate disposable `inmemory://v9-review/{document_id}/{encoded review identity}/base` and `/proposed` models; `renderSideBySide: false`, both sides read-only, no revert gutter/menu, and whitespace differences included. Monaco shows deletions inline, additions and separated change regions. The narrow original line-number gutter is not a second text pane. There is only one visible central editor surface.

Accept synchronously unlocks only the hidden working editor after all hook guards, brackets `executeEdits` with undo stops, and restores its prior view/cursor. Monaco itself refuses `executeEdits` while read-only, so this brief programmatic unlock is necessary. Uniform LF/CRLF changes use undoable `pushEOL` in the same undo group. Model change callbacks are suppressed only during that synchronous commit; the hook then changes accepted text once and advances its epoch. React returns the same editor/model to ordinary editable mode. No save API is called.

Reject removes only the proposal. Accepted manual edits, saved revision and undo stack remain unchanged. A stale proposal stays inspectable with acceptance disabled; rejection does not restore its obsolete base over newer text. Entering/closing manual review changes neither accepted text nor saved state. Ctrl+S and Save are unavailable while reviewing; close/accept/reject before saving.

Leaving the working workspace or switching documents disposes editor/review models as before; provider-owned accepted text and pending proposal state survive navigation. Reopening reconstructs from that state. Undo/cursor history is retained across review within the same working editor, **not** across an editor disposed by document/view navigation or browser reload. Originals, samples and V9 previews retain separate namespaces and behavior.

### Exactness and limitations

Acceptance supports empty content, Unicode, preserved BOM and uniform LF/CRLF content. A changed leading BOM, mixed EOLs or bare CR is refused rather than silently normalized. Monaco's temporary display may normalize such text for rendering, but the proposal retains the exact string and cannot be accepted through this path. This is not a network-configuration validator.

The UI retains historical/current-validity-not-checked, unvalidated and not-deployed labels. A source label does not imply real AI generation, semantic validity or deployment. Original and saved V9 state are not changed by staging, review, accept or reject.

## 5. Tests, exact commands and outcomes

Run from the repository root using the required venv:

```powershell
& 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv\Scripts\python.exe' -m unittest discover -s tests -p 'test_workbench*.py'
& 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv\Scripts\python.exe' main.py --help
git diff --check
```

- Workbench backend regression: **97 passed**, 121.395 seconds. Logged injected planning failures are expected negative cases. No new Python test or core V9 change was needed.
- CLI help: passed. This does not verify live inference.
- Whitespace check: passed. Documentation references and Markdown structure were also checked before handover.

From `frontend/`, with manual services on ports 8000/5173 stopped:

```powershell
npm run lint
npm run build
npx playwright test --config playwright.review.config.ts
npx playwright test --config playwright.review-integration.config.ts
npx playwright test
```

- ESLint: passed. TypeScript/Vite production build: passed (2,338 modules; main chunk approximately 3.077 MB / 816 KB gzip). Existing >500 KB bundle warning remains; no dependency upgrade or unrelated splitting work.
- Focused review browser suite: **20 passed** in 1.1 minutes. Covers actual Monaco models/options, additions/deletions/replacements, multiple regions, empty/Unicode/BOM/LF/CRLF content, whole accept/undo/redo, manual-review baseline, no-op/invalid/oversize input, wrong/inactive documents, conflicting/late proposals, saved-revision and buffer-epoch ABA checks, external model changes, pending/uncertain saves, model disposal, view navigation, samples/originals, mock chat and registration independence. Explicit cursor/model-identity and pending-proposal reload checks pass. The native-inline screenshot was visually inspected: one central comparison surface, red deleted and green added lines, and visible whole-proposal controls.
- Established browser regressions: **40 passed, 2 skipped**, 2.1 minutes on the final unchanged sequential run. Both skips are opt-in live-AI checks, not evidence of inference/RAG readiness.
- Unmocked review/save/restart integration: **1 passed**, 17.4 seconds for the run (12.7 seconds test body). Actual FastAPI storage and fresh backend/browser restart, not mocked persistence.
- Normal production assets were checked for `__reviewTest` and test-producer strings: no matches. No test bridge is imported by the normal main entry or build configuration.

The separate integration test uses the existing `tests.workbench_working_server` with a dedicated `v9-working-browser-review-*` temporary directory. It restores a real saved V9 session, opens its real original/working file, stages only the proposal through test instrumentation, accepts in the actual editor and saves through real Ctrl+S/PUT. A fresh backend interpreter and browser context reopen the saved result; original/session/inventory bytes and session mtime must remain unchanged. It asserts exactly two existing create/capture POSTs and one save PUT, no planning/answer/execution mutation. No mocked artifact/working endpoint or Ollama is involved.

`vite.review.config.ts` instruments the test entry to mount `ReviewHarness` under the actual provider. The normal Vite config and production main entry never import it. Test controls are not a public production API or fake AI feature. All test storage cleanup validates the exact owned temporary path.

### Failures found during implementation

Early focused tests found Monaco's read-only guard blocking programmatic acceptance; the hidden-buffer commit was corrected. Empty models' default Windows EOL required undoable EOL selection. New selectors initially matched both inline deleted view zones and modified text, or assumed a nonexistent CSS class/zero-width gutter; they were corrected against the installed Monaco implementation. No existing regression assertions were weakened. An initial isolated integration launch correctly rejected a temporary-directory prefix outside the existing server allowlist; the test now uses the existing safe prefix, without weakening that guard.

An early full regression run had 39 passes, two live skips and one 30-second initial `page.goto` timeout while a build was also running. The subsequent **unchanged**, sequential full run passed all 40 deterministic cases (the initial case completed in 3.3 seconds); no timeout/assertion was relaxed. Initial sandbox command startup failed with a setup-helper error, so approved verification used the project venv outside that failing sandbox. No global Python or Miniconda interpreter was used. A lint-only unused initialization was removed. No targeted failing check remains.

## 6. Remaining issues and risks

- No real AI edit generation, per-hunk acceptance, proposal persistence, automated semantic validation, deployment or background saves. One pending proposal per document; reject before staging another.
- Pending proposals and unsaved accepted buffers are lost on reload. Only explicit successful save persists text. Existing before-unload protection remains best effort.
- Existing working-save single-process coordination, stale/uncertain save inspection and cross-process/OneDrive/power-loss limitations are unchanged. Review acceptance does not prove the server revision is still current; the existing PUT revision check decides that.
- No cross-document undo, model history after disposal, durable proposal outcomes or automatic rebase/merge.
- Mixed/bare-CR EOL and BOM-change acceptance limitations are explicit above. Large diffs have bounded computation; no custom diff algorithm or semantic interpretation is introduced.
- Existing broad catalog baseline (2 assertion failures / 192 example-subcase errors), Monaco bundle-size warning and previously documented dependency advisories are not repaired or recertified. No dependency install/upgrade, live inference/embedding/RAG readiness check or full historical domain-suite rerun is claimed.

## 7. Next single recommended iteration

**Iteration 14 — one real V9-authoritative follow-up instruction produces a guarded proposal for the active working document.** Reuse the current document's ID/revision/epoch/base snapshot, existing original/session provenance, V9 runtime authority/model configuration and typed error boundaries; return proposed text to this staging hook, not directly to the accepted buffer or save API.

First verify whether existing V9 planning/clarification functions can safely express the requested follow-up. They are not a generic arbitrary-text editing API; do not silently route arbitrary document edits through `apply_answer`, rewrite sessions or claim existing validation covers edited text. If insufficient, separately bound and approve a minimal V9-owned edit-interpretation adapter grounded in current operation/inventory/vendor constraints. Acceptance/rejection and later explicit save remain user-controlled. No general agent tools, automatic retries, multi-document edits, execution or knowledge-authoring UI. This is a recommendation only; Iteration 14 has not started.

## 8. Reproduction and verification instructions

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

Open `http://127.0.0.1:5173`, select an existing Working File or use the existing confirmed-output opener. Edit its text and choose Review Changes. Verify inline additions/deletions against the last confirmed save. Close Review to continue editing; Ctrl+S remains a separate explicit persistence action. Original and sample documents stay independent. There is no production button generating a fake AI edit.

For deterministic pending-proposal verification, stop manual services and run the focused review command above. Its explicit test-only Vite configuration injects proposals through the same hook and real Monaco control; tests click the real Accept/Reject buttons. For real persistence/restart, run the separate review-integration command. Neither requires Ollama, real devices, catalog changes or user inventory/session writes. Do not run the two browser configurations concurrently: both own ports 8000/5173.
