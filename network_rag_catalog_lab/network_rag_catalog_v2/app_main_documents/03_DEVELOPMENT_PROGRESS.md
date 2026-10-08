# Development Progress

**Status:** Updated for Iteration 4 structured Local V9 session creation (2026-10-08).

This tracker separates reported historical results from work independently verified in the current iteration. A prior handover claim is not a new test result.

## Iteration status

| Iteration | Deliverable | Status | Evidence and boundary |
|---|---|---|---|
| Pre-Iteration -1 | V9 runtime stabilization | Reported completed; independent verification pending | `docs/V9_RUNTIME_AUDIT.md` reports the stabilization work and 28 passing focused tests. Iteration -1 did not rerun those tests or validate the historical fixes. |
| Iteration -1 | Consolidate authoritative scope, architecture boundaries, engineering protocol, progress tracking, and decisions | Completed | Documentation-only review and consistency checks. No runtime, GUI, database, release, or dependency changes are part of this iteration. |
| Iteration 0 | V9/FYP architecture and selective-reuse audit | Completed | `05_FYP_REUSE_AUDIT.md` and `06_GUI_INTEGRATION_DESIGN.md` record source-backed classifications, callable interfaces, contracts, inventory/artifact design, verification and handover. Documentation only; no runtime tests or historical fix revalidation. |
| Iteration 1 | React workbench shell with a functional Monaco surface | Completed | New root `frontend/` provides the four-region workbench, reducer-driven local state, bundled Monaco worker/language support, independent in-memory tab edits, sample explorer selection, mock chat, simulated activity, and keyboard/pointer splitters. `npm.cmd run lint`, `npm.cmd run build`, and two Playwright browser checks passed. The rendered localhost page was visually inspected. No V9/backend source or persisted inventory was changed. See `07_ITERATION_1_HANDOVER.md`. |
| Iteration 2 | Read-only FastAPI health/runtime authority and frontend connectivity | Completed | `app.workbench.api:app` exposes typed passive health and runtime-status reads. The status bar presents loading, connected, error/disconnected and retry states while mock features stay isolated. Four backend contract tests, frontend lint/build, three Playwright tests, real Uvicorn requests, CLI help and connected/error visual checks passed. No session, planning, inventory, knowledge, or device mutation was added. See `08_ITERATION_2_HANDOVER.md`. |
| Iteration 3 | Read-only shared V9 demo inventory | Completed | Typed list/detail endpoints adapt the existing uncached `load_inventory()` authority and expose six safe synthetic records plus a content revision. The explorer now uses API devices with loading, filtering, selection, details, empty/error and retry states. Eight backend tests, lint/build, three Playwright tests, CLI help and visual inspection passed. No inventory data, target resolver, V9 runtime, AI session or persistence behavior changed. See `09_ITERATION_3_HANDOVER.md`. |
| Iteration 4 | Structured V9 planning-session creation | Completed for the bounded creation workflow | Worker-backed typed POST directly calls V9 creation/serialization, retaining its saved session and all plan/question/evidence fields. Explicit Local V9 chat presents structured results, pending questions and errors, with no mock fallback. 19 API tests, frontend lint/build, 7 browser checks including live creation, CLI help, real inference/embedding/index checks and an instrumented semantic planning smoke passed. Broader legacy failures remain as detailed below. See `10_ITERATION_4_HANDOVER.md`. |

## Proposed sequence after Iteration 4

Each row below is a candidate small iteration, not an active instruction. Scope and ordering may change based on evidence from prior iterations.

1. Render one structured clarification-answer round trip with explicit stale-answer and duplicate handling.
2. Deepen multi-intent/multi-device plan review beyond the current creation-result summaries.
3. Add one coherent local inventory-editing workflow with atomic persistence and V9 target-resolution verification.
4. Persist generated originals and separate editable working drafts, then add Monaco comparison.
5. Add session activity, error presentation, and clearly labelled replay/sample states.
6. Perform local demo integration hardening, targeted regression testing, and reproducibility documentation.

No row authorizes work on the following row, and multiple rows must not be combined merely for convenience.

## Known existing issues and risks

- **Non-green broad baseline:** Iteration 4 independently reproduced three legacy failing methods before implementation: the unique-Huawei expectation conflicts with R2/SW2 inventory ambiguity; an unknown-version test expects a ValueError not raised in the current file path; and a template-example mapping lacks 32 operation keys for six devices (192 KeyError subcases). The bounded 69-method baseline had 2 assertion failures and those 192 errors, with 66 other methods passing. Do not confuse these with new adapter regressions or claim the complete repository suite is green. See the final comparison and commands in `10_ITERATION_4_HANDOVER.md`.
- **Local Ollama/readiness — verified 2026-10-08:** Connection refusal no longer reproduced. Configured `qwen2.5:1.5b` inference returned `OK`; configured `nomic-embed-text` resolved the installed `nomic-embed-text:latest` and generated 768-dimensional embeddings. V9 validated the existing 44-record Chroma index against catalog IDs/revision/model and performed a semantic query. An instrumented real creation request exercised 5 actual model calls, 1 successful retrieval and 1 query embedding, returning an honest operation-confirmation question. A real browser literal request returned a ready preview. No ingestion/reconciliation was needed. This proves these local creation paths at this time, not all catalog operations, published-mode planning, future availability or clarification progression. Passive health/status continues to report AI `not_checked`.
- **Catalog drift outside the stabilized slice:** The previous handover reports unrelated catalog drift affecting 29 other operations. Those operations were not repaired or retested in Iteration -1.
- **Runtime stabilization verification:** Iteration 4 reran the relevant runtime-intent, native-vendor, direct-file, target-resolution and clarification suites, separating the three legacy failures above. This is fresh evidence for those named checks, not re-certification of every historical fix or the exact historical 28-test handover claim.
- **Inventory mutability:** The GUI and target resolver now share the same uncached JSON authority for reads. CRUD, atomic writes, cross-process coordination, reference checks and stale-session behavior remain unimplemented and untested.
- **FYP reuse quality:** Source audit completed. Small input/icon reuse and layout/editor-pattern adaptation are recommended. Broad controllers, inventory synchronization endpoints and old intent/execution logic are excluded. Dependency/build/security certification remains outside the audit.
- **Monaco completeness:** The shell now builds and loads a local Monaco worker with distinct model paths for each in-memory sample tab. Persistent generated/draft records, DiffEditor integration, arbitrary edited-content validation, and production bundle splitting remain future work. The current production bundle emits a greater-than-500-kB chunk warning.
- **Frontend dependency advisories:** The production dependency audit reports two low-severity DOMPurify advisories inherited through Monaco 0.57.0 and no high-severity production advisory. Do not use a forced downgrade/fix without a separately verified compatibility decision.
- **Contract design:** Creation is now implemented with a saved-byte session hash and lossless V9 payload. Saved-read/resume, answer concurrency and artifact/draft services remain proposals. V9 still lacks whole-session concurrency enforcement and arbitrary edited-configuration validation.
- **Creation retries/timeouts/persistence:** One process serializes V9 creation and retains up to 256 request-ID outcomes without eviction. Deduplication is in-memory only; restart/multiple workers break its guarantee. The frontend's 120-second timeout does not cancel V9, which may still save a session. Same-process manual retry retains the request ID; never blindly resubmit after restart. No durable request journal, crash reconciliation, hard worker cancellation or passive session retrieval is implemented. Inspect saved JSON for ambiguous outcomes; do not use refreshing `load_session()` as a read. Cached errors require an intentional new request to attempt work again.
- **Passive status boundary:** Health/runtime authority is implemented, but it intentionally performs no Ollama, embedding, Chroma, index-freshness, source-revision, inventory-revision or session checks. Those fields remain `not_checked` or absent rather than inferred.
- **FYP test isolation:** Some prototype test files perform external writes at module level. Do not collect that test tree wholesale; the shell needs its own isolated browser smoke tests.
- **Working-tree provenance:** Existing runtime and documentation changes from the prior stabilization work must be preserved and distinguished from changes made in later iterations.

## Current scope guard

The current milestone remains local and demo-only. NetBox, device SSH, Ansible/Terraform execution, live monitoring/discovery/telemetry, production authentication/authorization, server-fleet automation, and live deployment remain deferred until explicitly authorized.

## Latest handover location

Iteration 4's report, exact verification commands, live probe evidence, file inventory, launch instructions and limitations are in `10_ITERATION_4_HANDOVER.md`. The next single recommendation is Iteration 5: one structured clarification-answer round trip with stable IDs and stale/duplicate safeguards. No Iteration 5 implementation has begun.
