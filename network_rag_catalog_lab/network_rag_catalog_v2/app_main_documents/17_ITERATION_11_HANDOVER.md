# Iteration 11 — Persistent Generated Configuration Documents

## 1. Iteration identifier and objective

Deliver one explicit, restart-safe IDE workflow: capture a backend-confirmed, device-specific V9 configuration as an immutable original, discover it in Explorer and reopen it read-only in Monaco. Planning remains preview-only until **Save to Workspace** is explicitly chosen.

## 2. Completion status

**Completed (2026-10-09).** The capture → Explorer → read-only Monaco workflow is implemented and verified, including isolated backend-process/browser-context restart. All 85 workbench backend tests, frontend lint/build and 33 deterministic browser regressions pass; two opt-in live-AI tests were skipped. The separate unmocked persistence/restart browser test also passes.

No drafts, DiffEditor, AI modifications, knowledge authoring, device operations or next iteration were implemented. No dependencies were installed or updated and no Git commit was created.

## 3. Files added, modified or removed

Paths below are relative to `network_rag_catalog_v2/`.

Added:

- `app/workbench/generated_originals.py` — typed capture, bounded discovery/detail, identity, integrity and storage.
- `frontend/src/services/originalsApi.ts` — typed transport and safe failure/uncertainty presentation.
- `frontend/src/features/workspace/useSavedOriginals.ts` — provider-owned response cache, explicit capture/read and request-race guards.
- `frontend/src/features/workspace/SavedOriginalViewer.tsx` — isolated read-only original Monaco document.
- `frontend/src/features/explorer/SavedOriginals.tsx` — backend-backed configuration discovery and refresh.
- `tests/test_workbench_originals.py` — deterministic isolated storage/API/restart/failure tests.
- `tests/workbench_original_server.py` — test-only backend with temporary session/artifact storage, no AI runtime imports.
- `frontend/tests/saved-originals.spec.ts` — four deterministic actual-Monaco interaction tests.
- `frontend/playwright.originals.config.ts` and `frontend/original-integration/persistence.spec.ts` — unmocked restart test.
- `app_main_documents/17_ITERATION_11_HANDOVER.md` — this handover.

Modified:

- `.gitignore` — ignore persisted workbench originals.
- `app/workbench/api.py` — three typed original routes, safe errors and no-store responses.
- `app/workbench/planning_service.py` — capture shares the existing single-process mutation gate.
- `frontend/src/app/WorkbenchProvider.tsx` and `frontend/src/app/types.ts` — integrate original response cache and existing workspace selection.
- `frontend/src/features/explorer/ExplorerPanel.tsx` — embed Saved Originals without replacing inventory.
- `frontend/src/features/workspace/GeneratedConfigurationViewer.tsx` — explicit capture action and confirmed/error feedback.
- `frontend/src/features/workspace/WorkspacePanel.tsx` — one active saved-original view alongside samples/plan/transient preview.
- `frontend/src/components/layout/StatusBar.tsx` — iteration label.
- `frontend/src/styles/workbench.css` — small scrollable Explorer section and shared provenance presentation.
- `tests/test_workbench_planning.py` — exact mutation-route assertion now includes the authorized original POST; still rejects additional mutations.
- `frontend/tests/workbench.spec.ts` — scope the unchanged offline-inventory assertion to the inventory list because Explorer now has a separate originals error.
- `app_main_documents/03_DEVELOPMENT_PROGRESS.md`, `app_main_documents/04_ARCHITECTURE_DECISIONS.md` — tracker/risks and AD-039/040.

No source files removed. The interrupted sandbox test's verified temporary fixture directory was cleaned up; it contained only this iteration's test session. Prior dirty/untracked Iteration 10 files were preserved. In particular, reducer, TaskReviewPanel, generatedPreview helper and prior generated-preview tests were not changed in this iteration. The preview viewer was already untracked from Iteration 10 and is listed above as modified, not newly invented here. Historical FYP and the optional vision document remain untouched.

## 4. Architectural decisions and reasons

### Actual source-to-document flow

V9's existing planner renders task-specific dictionaries into `PlannedTask.configs[]`; unchanged session persistence serializes the plan into version-2 JSON. `intent_id` is the task identity, while `logical_intent_id` connects expanded device tasks. Existing planning/answer/recovery responses enter provider-owned `useLocalPlanning` state. Iteration 10 selects a tuple of session ID, saved-byte revision, task ID, device ID and config-entry index and directly projects that confirmed output into read-only Monaco.

Iteration 11 submits **only that tuple**, never client configuration text. `PlanningService.capture_original()` acquires the existing busy gate and calls the small workbench store. The existing `get_saved_session()` performs one bounded-path read and shared lossless version-2 validation; its exact-byte SHA-256 must equal the requested revision. Capture requires exactly one task, a valid indexed config, exactly one matching resolved target, consistent config/task device identity and nonempty source configuration text. Conflicting hostname/vendor/platform/version metadata rejects capture. Metadata comes from the config, falling back only to its verified saved target when omitted; missing metadata remains null. No current inventory lookup or semantic inference occurs.

The gate excludes API creation, answers and registration while capture reads/publishes. It neither adds session mutation nor calls the side-effecting `load_session()`. Capturing historical output is allowed; it is not a source-freshness certification.

### Four distinct authorities

- **A — V9 saved session:** existing authoritative engine snapshot, which may advance after an answer.
- **B — Generated original:** separate immutable workspace document captured from a verified A snapshot. Implemented here.
- **C — Working document:** future independently persisted editable content referencing B. Not implemented.
- **D — Pending AI modification:** future proposal separate from accepted C. Not implemented.

Only A/B exist now. Original IDs permit future references without speculative draft records, patch protocols, virtual filesystems or execution stores. The optional long-term vision was found under `app_main_documents/Important Main Idea Folder/KNOWLEDGE_MANAGEMENT_AND_AGENTIC_IDE_VISION.md`, read as background, and does not authorize senior knowledge-management work.

### API contracts

All routes use `/api/v1/workbench/artifacts/generated-originals`:

| Method | Route suffix | Typed result |
|---|---|---|
| POST | collection | `CaptureResponse`: `api_version: 1`, `outcome: created` (201) or `already_saved` (200), full `artifact` |
| GET | collection | `OriginalList`: `api_version: 1`, `limit: 128`, metadata-only `artifacts[]` in ascending artifact-ID order |
| GET | `/{artifact_id}` | Verified `GeneratedOriginal`, including exact configuration string and recorded provenance |

POST requires `session_id` (UUID), `expected_session_revision` (64 lowercase hexadecimal characters), `task_id`, `device_id` (nonempty bounded strings), and `config_index` (strict nonnegative integer, zero-based). Extra fields including client configuration text are forbidden. Typed UUID/digest/shape failures return 422; missing sessions/originals 404; stale revision, bad association, unsupported/malformed source or corrupt/inconsistent original 409; oversized capture 413; storage/capacity/busy failures 503. Errors expose safe codes/messages, not raw exceptions or paths. Core source-reader error codes are retained. GET and capture responses use `Cache-Control: no-store`. No update/delete route exists.

### Original record schema and identity

Storage: configured `app.config.STORAGE_DIR / workbench / generated_originals / {artifact_id}.json`. The default is `storage/workbench/generated_originals/`; it is not sessions, inventory, SQLite or the knowledge catalog. No second planning database is introduced.

Version-1 record fields:

- `schema_version: 1`, `kind: generated_original`, `artifact_id`.
- `source`: session UUID, exact `session_revision`, `task_id`, `device_id`, `config_index`.
- Nullable `logical_intent_id`, `operation_id`, `category`, `hostname`, `vendor`, `platform`, `version` from verified saved records.
- Exact `configuration`; `content_encoding: utf-8`; `content_sha256`.
- UTC timezone-bearing ISO `captured_at`.
- `authority`: recorded plan/task runtime authority, knowledge snapshot ID, source revision and context revision. Empty/missing values are retained, not replaced by current authority.
- `validity: historical_not_checked`; `record_sha256`.

Canonical record encoding is `json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')`. Artifact ID is `original-` plus SHA-256 of canonical `{schema_version: 1, source: {...}}`. Content digest is separately SHA-256 of the **exact configuration string encoded UTF-8**, with no added BOM, trimming, LF/CRLF conversion or JSON quoting. A source BOM, mixed line endings, Unicode, trailing spaces and trailing newline remain preserved. `record_sha256` hashes canonical complete record fields except itself, covering provenance and content together.

Same coordinates and exact saved revision yield the same ID across restarts. Different revisions/entries/devices/tasks cannot silently share an original. Timestamp is not part of identity. Repeat capture verifies the existing file and compares all stable source/content fields before returning its original timestamp/content. It does not rewrite or accumulate duplicates. If the source session has changed, an old expected revision conflicts even if an older original exists; that older original remains independently accessible by list/detail.

### Persistence and failure boundaries

1. Validate saved source/revision/association and derive identity.
2. If an original already exists, verify schema, identity, both digests and stable source fields; return it unchanged or reject inconsistency.
3. Enforce bounds; serialize before publication.
4. Exclusively create a random sibling `.tmp`, require a complete write, flush and `os.fsync`, then close.
5. Publish with **atomic no-clobber `os.link(temp, final)`**, tested on this local Windows filesystem. Unlike replacing a destination, this refuses an existing original. A competing existing destination is verified instead. No overwrite fallback exists on unsupported filesystems.
6. Read/verify the published record before reporting success; unlink the exact owned temporary in `finally` when possible.

Pre-publication write/flush/fsync/serialization/link failures leave no partial final JSON. If publication succeeded but verification/response delivery failed, the original may exist: report uncertainty, then use passive discovery. A repeat explicit capture with unchanged source returns the same verified record. GET remains usable after source session revision changes and does not reread that session.

The directory is bounded to 128 entries including orphan temporaries; each record is at most 2 MiB. At capacity new captures reject rather than evict. Listing validates every final record and returns no configuration bodies; unexpected entries or any invalid final record fail the collection explicitly. `.tmp` remnants are never listed or automatically repaired/deleted and count toward capacity. Listing during publication may transiently hit the capacity boundary because the temporary and final hard link coexist. Detail remains independently readable by known valid ID. There is no search, pagination, history browser or retention manager.

Canonical IDs and resolved storage checks reject path traversal/redirection. Integrity hashes detect accidental corruption, not a privileged attacker who rewrites content and hashes. The supported coordination boundary is **one application instance/process**, not cross-process session CAS or CLI coordination. Atomic no-clobber publication is a filesystem primitive, not an end-to-end multi-worker transaction or exactly-once execution guarantee. Hard-link support is required. File fsync does not prove directory-metadata durability after sudden power loss; OneDrive reconciliation, external writers, disk loss and filesystem-specific semantics are not certified. No production remote multi-user guarantee is made.

### Explorer, Monaco and uncertainty behavior

`useSavedOriginals` caches only confirmed API responses in the provider, independent of the Local V9 plan. Reducer view selection is reused; no second execution-plan store or browser-persisted full documents are added. The collection is fetched on mount and explicit Refresh; successful capture triggers a collection refresh. A failed post-save refresh reports a discovery error without denying the separately confirmed save. User selection fetches detail and opens the single central editor; sequence guards prevent a late earlier read replacing a newer selection.

Original models use `inmemory://v9-original/{artifact_id}/configuration`, distinct from `inmemory://v9-preview/...` and `inmemory://demo/...`. Both Monaco `readOnly` and `domReadOnly` are set; no change handler, save-back action or draft exists. Original models are disposed on view/document switch and rebuilt from the confirmed detail response; samples retain their independent reducer content/model identities. Ordinary Monaco line-ending presentation may normalize mixed line endings internally; persisted text/digests are never derived from the Monaco model. No editing or normalization is written back.

Saved originals are independent of later plan replacement, clarification or inventory changes. Transient preview invalidation remains unchanged. Original provenance is always labelled historical/current validity not checked, not deployed, not a draft/sample/template. `ready`/`rendered` never implies execution. A fresh browser can discover originals without restoring a plan or typing an artifact ID.

Capture disables repeat submission while pending. Confirmed new and duplicate outcomes have different messages. Stale source, association, corruption and storage failures retain explicit codes. Network/timeout/unexpected confirmation is `OUTCOME_UNCERTAIN`, not success; no automatic retry occurs. **Refresh Saved Originals** performs only GET, allowing inspection of an already committed record. Capture uses a 15-second browser timeout; aborting the HTTP wait does not cancel server work. There is no claim that a missing list item proves no side effect, especially while a request may still be pending or storage is unavailable.

## 5. Tests run, exact commands and outcomes

Backend commands from repository root, always using the project venv:

```powershell
& 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv\Scripts\python.exe' -m unittest tests.test_workbench_originals -v
& 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv\Scripts\python.exe' -m unittest discover -s tests -p 'test_workbench*.py' -q
& 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv\Scripts\python.exe' main.py --help
```

- Focused original tests: 14 passed before the final recorded-target-metadata test was added; all 15 are included in the final green combined run below.
- Final workbench regression run: **85 passed in 51.790 seconds** (70 existing checks plus 15 new originals checks). Intermediate 81- and 84-test green runs preceded the final additions.
- CLI help: exit 0, existing planning/resume/edit CLI options unchanged. This is compatibility smoke evidence, not fresh LLM inference.
- Tests cover exact CRLF/LF/BOM/Unicode/whitespace, task/device/entry identity, multiple outputs, stale/malformed sources, capture idempotence, source changes, fresh interpreter, post-publication uncertainty, same-process concurrency, partial-write/flush/fsync/link/serialization faults, corruption/collision checks, bounds, list/detail equality, passive reads and unchanged source/inventory bytes/timestamps. Fresh-process capture replay/list asserts no clarification/pipeline/Ollama/Chroma imports. Forbidden runtime/network/execution entry points are guarded. All mutation tests use temporary storage.

Frontend commands from `frontend/`:

```powershell
npm run lint
npm run build
npx playwright test tests/saved-originals.spec.ts
npm run test:e2e
npx playwright test --config playwright.originals.config.ts
```

- Lint: pass, no suppressed rules.
- TypeScript/Vite production build: pass, existing >500-kB Monaco chunk warning remains (approximately 3.06 MB uncompressed main JS). No dependency changes.
- Four focused browser tests: pass, real Monaco model content/options, typing/paste protection, samples, explicit capture, pending/duplicate behavior, reload, loss/error discovery and multiple originals.
- Full established browser suite: **33 passed, 2 skipped**. Existing clarification, recovery, multi-task review, registration, Monaco sample, transient preview, mock-mode and offline behavior pass. The skipped tests are the two opt-in live-AI checks; no live inference/RAG claim is made.
- Isolated unmocked Chrome → actual FastAPI test: **1 passed**. A real version-2 serialized test session is prepared without LLM imports. The browser restores it, captures through the real endpoint, then its context is closed and the child backend killed/restarted with the same temporary storage. A fresh browser context discovers and opens the same original through Explorer; detail equals the pre-restart record. One artifact file exists, only the explicit capture POST occurred, source session bytes/mtime and actual inventory bytes remain unchanged. Test-owned directories/processes are cleaned up. This tests filesystem persistence and full application/browser-context restart, not a physical machine power failure or fresh inference.
- The unmocked restarted-original screenshot was visually inspected: single central editor, Explorer original row, separate demo chat/inventory and historical/read-only labels are visible. Actual Monaco is additionally checked through its live models/options, not a styled text substitute.
- Final documentation verification: 25 referenced source paths exist; `git diff --check` passes. The unmocked restart test was rerun after the final backend metadata change and passed again (1 test, 7.3 seconds including startup). No real workspace original directory was created by these tests.

Development failures resolved before handover: initial new-hook lint violation; new API-route order expectation; selectors colliding with Monaco accessibility alerts and the new originals offline alert. Existing assertions were scoped to their intended regions without weakening expected behavior or broadening test doubles. Initial sandbox venv tests stalled and Vite realpath failed with EPERM; approved runs outside the sandbox used the same venv and passed. The stalled test was stopped and its owned temporary fixture removed.

Broad legacy catalog/domain suite not rerun or repaired: the previously recorded 2 assertion failures / 192 example errors remain historical baseline limitations, not current new failures. Prior Ollama readiness evidence is not recertified by these deterministic checks. Prior separate unmocked inventory-registration test was not rerun; registration backend/browser regressions were.

## 6. Remaining issues and risks

- Local single-process support only; retain one Uvicorn worker and avoid independent session writers during capture. No cross-process CAS, permission system, hardware power-loss test or privileged-tamper prevention.
- Hard-link publication requires a supporting local filesystem; failure returns safely without replacement. OneDrive-specific reconciliation/durability remains unverified.
- Corruption or exceeded bounds prevents collection discovery; no automatic repair/deletion/migration/eviction. Preserve original files when backing up the workspace. Digests are integrity checks, not vendor certification or signatures.
- No UI confirmation of uncertain POST until a verified artifact is discovered/read. No automatic retry/cancel-server guarantee. Browser list/read cache is not an inventory/catalog freshness check.
- Historical saved versions must pass the existing version-2 validator for capture. Already captured originals remain readable without their source file; no source regeneration or resume is supplied.
- Existing CLI/API external-writer, answer-recovery, interrupted-creation, catalog baseline, dependency advisory and Monaco bundle-size risks remain as in the tracker.
- Drafts, DiffEditor, AI proposals, working-copy validation, knowledge screens/templates/publication, device editing/deletion, synchronization and execution remain unimplemented.

## 7. Suggested next iteration

**Iteration 12 — one persistent editable working document derived explicitly from a saved original.** Keep the immutable original untouched, give the working document its own identity/content/revision and editor model, save/reopen it with optimistic concurrency and honest unvalidated-edit labels. Deliver only that edit/save/restart workflow; no DiffEditor, AI proposals, arbitrary network-semantic validation, knowledge authoring or deployment. This is a recommendation, not authorization to start it.

## 8. Exact reproduction/verification instructions

Backend PowerShell window (one worker; keep storage between restarts):

```powershell
Set-Location 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\network_rag_catalog_lab\network_rag_catalog_v2'
& 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv\Scripts\python.exe' -m uvicorn app.workbench.api:app --host 127.0.0.1 --port 8000
```

Frontend PowerShell window:

```powershell
Set-Location 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\network_rag_catalog_lab\network_rag_catalog_v2\frontend'
npm run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:5173`. Use Local V9 to restore an existing version-2 session containing generated output, or explicitly create/clarify one through the established workflow if AI is available. Select its task and actual device output, **Open read-only in Monaco**, then **Save to Workspace**. Wait for confirmation; select the backend-returned row in **Configurations → Saved Originals**. Inspect source provenance; typing/paste must not edit it. Return to Samples to confirm they remain independently editable.

Close/reload the browser and stop/restart the backend with the same command and storage. Select the same original from Explorer without any session restore or artifact-ID input. It should show the same saved text/provenance and historical/read-only labels. Refresh Saved Originals after an ambiguous capture; do not automatically replan or repeat the POST. No storage is created merely by opening/listing an empty workspace.

For an AI-independent, no-user-session-write demonstration, stop manually running servers on ports 5173/8000 and run `npx playwright test --config playwright.originals.config.ts` from `frontend/`. It creates its own temporary saved session/store and verifies backend/browser-context restart automatically. The standard browser suite also requires these ports free. No dependency installation is needed for this iteration in the current workspace.
