# Knowledge Activation and Prompt Testing Plan

Date: 2026-09-29
Status: The simplified activation was approved and implemented on 2026-09-29.

## Approved Scope and Outcome

The user replaced the separate lab-profile proposal with direct, non-overwriting
addition of synthetic SW1/SW2/SW3 to the current inventory. All six packs were
promoted through SQLite management services and published with Chroma: 44
operations, 78 bindings. Existing public interfaces and R1/R2/R3 were preserved.
No lab-profile flag, separate profile/session system or benchmark framework was built.

The approved verification was focused regressions plus eight live prompt flows.
Both paraphrases exercised RAG; the route paraphrase required explicit operation
correction. See `docs/KNOWLEDGE_ACTIVATION_RESULTS.md` and
`docs/PROMPT_TESTING_GUIDE.md` for evidence and terminal examples.

A subsequent request supplied 35 operation schemas for all three vendors. All
35 IDs were already active. RAG was enriched with actual vendor profile and
parameter support; `docs/REQUESTED_OPERATION_COVERAGE.md` records 54 missing
vendor bindings and first-pass schema differences that are not implemented.

The R0-R5 proposal below is retained as historical design context. Its separate
lab-profile and comprehensive evaluation recommendations were superseded by the
approved concise plan; they are not unfinished activation tasks.

## 1. Objective and Boundaries

Make the existing reviewed knowledge available to the normal terminal pipeline:

```text
Reviewed packs -> SQLite authoring -> compiled schemas/templates/RAG documents
               -> verified Chroma index -> atomic active-release switch

Human prompt -> intent decomposition -> operation proposals/confirmation
             -> inventory target resolution -> schema-based parameter extraction
             -> per-device context checks -> one-field clarification
             -> whole-request validation/conflict confirmation
             -> vendor-specific Jinja configuration previews
```

This is a **generation-only lab rollout**, not network execution or certification.
Freeze knowledge expansion after this rollout: use the existing operations to
measure and improve prompt handling. Do not add categories, operations, vendors,
Ansible, GUI, external integrations, topology inference or business-intent planning.
Preserve public interfaces, SQLite authority and the original operation contracts.

"All operations" means the 44 existing and staged canonical operations, not every
operation on every vendor. Aliases are discovery terms, not duplicate operations.
Unsupported profiles and incomplete context must continue to block rendering.

Previous notes require device-lab acceptance before live publication. Approval of
this plan would explicitly permit local, synthetic-context publication for prompt
evaluation only. It would NOT waive that requirement for deployment use. No
production-safety claim may be inferred from the term `active`.

## 2. Repository Review

### Verified Current State

Read-only inspection confirmed the following on the date above:

| Item | Current workspace | Intended result |
| --- | --- | --- |
| Authoring authority | SQLite | SQLite, unchanged architecture |
| Categories | 6 | 9, preserving BGP, IS-IS and Interface IPv4 Addressing |
| Canonical operations | 12 | 44: original 12 plus staged 32 |
| Template bindings | 36 | 78: original 36 plus staged 42 |
| Active release | `fbd929e928014a4886fbfd69c4019851` | One new indexed release, only after checks |
| Retrieval receipt | Original 12 IDs, Chroma, `ready=true` | Exact set of 44 active operation IDs |
| Default inventory | R1/R2/R3 | Unchanged; separate opt-in synthetic lab context |
| Pack inventory | SW1/SW2/SW3, rehearsal only | Available in the lab context |
| Ollama endpoint | Connection refused at `127.0.0.1:11434` | Running, configured models smoke-tested |

The manifest's existing retrieval receipt is not a fresh live retrieval test.
Recorded previous verification: 226 tests passed and 42 new binding cases rendered
in an isolated rehearsal. Those results do not establish current live-model
accuracy. The suite was not rerun for this planning-only review.

### Existing Components to Reuse

| Component | Actual responsibility and important constraint |
| --- | --- |
| `app/knowledge/pack_review.py` | Reads reviewed assets, rejects conflicting records, prepares idempotent service requests and rehearses in a disposable project. It has no live promotion command. |
| `app/knowledge/management.py` | Revision-checked dry-run/apply/export/validate/publish. Pack JSON is input, not a second live authority. |
| `app/knowledge/publication.py` | Compiles schemas, validates bindings/context rules, snapshots assets, builds retrieval documents, indexes and verifies before atomically changing `active.json`. |
| `app/ingest.py` | Builds a release-specific Chroma collection; its top-level `ingest()` also publishes. Do not run it as a second ingestion step after publication. |
| `app/knowledge/runtime.py` | Loads immutable artifacts and binds one release per request; changed release/context forces revalidation. |
| `app/vectorstore.py`, `app/retrieval/` | Reads the active collection, checks embedding-model identity and candidate release/version metadata; retrieval is category-filtered, currently top three. |
| `app/planner/intent_planner.py` | Uses catalog-backed splitting first; model decomposition has bounded repair and verbatim evidence checks. Complex scope needs confirmation. |
| `app/pipeline.py` | Exact phrases bypass semantic retrieval. Other selections use category classification, RAG and a model proposal requiring confirmation. Splits device bindings and gates rendering across the whole request. |
| `app/parameters/`, `app/devices/`, `app/context.py` | Grounded extraction, schema validation, inventory/resource checks and permitted context suggestions. Missing facts are not invented. |
| `main.py`, `app/clarification.py` | Persistent, one-question terminal flow with selection, custom input, explicit edits and session resume. |

### Concrete Gaps Before Prompt Testing

1. Packs are review-only; neither SQLite nor the active index contains the 32 new
   operations. Editing seed JSON or merely starting Ollama cannot activate them.
2. SW1/SW2/SW3 are not runtime inventory. New operations need their explicit
   capabilities/resources; do not copy capability claims onto R1/R2/R3.
3. Inventory, planned data and context hashing currently use module-imported
   paths. There is no coherent terminal lab-profile selector or profile-bound
   session identity. Patching one config variable after import is insufficient.
4. Some pack prompts are extractor fixtures, not full-pipeline examples. For
   `modify vlan; vlan_id 20; vlan_status "suspend" on SW1`, the current fallback
   planner produces three intents. Several pack tests call `_process_intent()`
   directly, bypassing this step. A live model might repair it, but that has not
   been demonstrated and must not be a test assumption.
5. No expanded-index benchmark currently proves paraphrase selection, multi-intent
   coverage or weak-model latency. Literal catalog phrases can pass without RAG.
6. Publication does not include inventory/planned files, and template installation
   is separate from SQLite transactions. Rollout must track these independently.

## 3. Exact Activation Scope

| Pack, in dependency order | New operations | New bindings |
| --- | ---: | ---: |
| VLAN | 2 | 2 |
| Interface | 9 | 17 |
| Static Routing | 2 | 4 |
| OSPF | 7 | 7 |
| ACL | 5 | 5 |
| QoS, after ACL's shared direction definition | 7 | 7 |
| Total additions | 32 | 42 |

Read the operation sets from each pack manifest during implementation; verify
their union against the approved receipt rather than maintaining another catalog.
Preserve the original 12 operations, 36 bindings and their existing aliases.
Retain the bounded semantics in `docs/KNOWLEDGE_EXPANSION_COMPLETION.md`.

| Synthetic test profile | New-operation coverage |
| --- | --- |
| SW1: Catalyst 9300, IOS XE 17.9 | All 32 additions, subject to operation-specific facts |
| SW2: CE6800, VRP V200R024C10 | Physical description/admin state, additive trunk VLAN membership, native VLAN |
| SW3: EX4300, Junos 23.4 ELS | Same four, plus default/floating routes |

These are candidate generation profiles, not certified devices. No fallback to
another vendor, version or model is allowed to make a test pass.

## 4. Implementation Phases

Use rollout labels R0-R5 to avoid confusing this work with expansion Phases A-D.

### R0. Capture and Rehearse the Approved Baseline

**Work**

- Inspect SQLite, active release, pack hashes and existing dirty-worktree changes.
  Stop on unexpected divergence; preserve unrelated user changes.
- Export the management bundle, record active manifest/collection and copy matching
  template/schema assets and inventory/planned files to a timestamped local backup.
  Export includes hashes, not asset contents. Use SQLite's backup mechanism or a
  quiesced backup, not a blind copy of an open database/WAL.
- Record all pack metadata and asset hashes, authoring/context revisions, model
  identifiers and intended generation-only purpose in a rollout receipt.
- Rehearse all six packs with existing services; run focused tests serially.
- Check Ollama availability and configured `qwen2.5:1.5b` / `nomic-embed-text` model
  availability. Perform a small chat and embedding request. Do not silently change
  models or download replacements; report missing prerequisites.

**Files/services:** existing management/export, `pack_review`, publication tests;
new local receipt/backup under ignored `storage/` and a short rollout runbook.

**Gate:** candidate set is exactly 44 operations / 78 bindings / 9 categories;
baseline 12 contracts remain equivalent; live authority/release/context unchanged.

### R1. Provide an Opt-In Lab Context

**Recommended design:** a small local context-profile selector, not another
inventory backend or catalog. Default behavior continues to use today's files.

- Add a `lab` profile containing a reviewed snapshot of R1/R2/R3 plus the existing
  synthetic SW1/SW2/SW3 fixtures. Preserve IDs, aliases and original facts. Retain
  synthetic source references and identify this as planned demonstration data.
- Include the matching original planned-parameter records. Add no automatic
  intended values; existing resource fixtures already supply candidate facts.
- Resolve inventory, planned records and context hashing through the same scoped
  profile. Include profile identity and contents in context revision checks.
- Add a proposed `--context-profile lab` terminal option. Default invocation and
  `run(prompt)` remain backward compatible. Use a scoped context wrapper for
  programmatic tests rather than changing every public function signature.
- Save the profile with sessions; legacy sessions mean the default profile.
  Resume uses the saved profile. Reject an explicit mismatching profile and stale
  answers; validate referenced files before using them. Separate lab session
  storage from existing sessions if needed to keep resume behavior unambiguous.
- Clearly mark lab output as synthetic configuration previews. Group resolution
  must still require confirmation when new lab members make a target ambiguous.
- Do not infer new planned state from generated configuration. Each test starts
  from the recorded snapshot unless an engineer explicitly revises it.

**Affected files:** `main.py`, `app/clarification.py`, `app/context.py`,
`app/devices/inventory.py`; narrowly scoped profile helper, for example
`app/context_profile.py`; profile data and focused profile/session tests.
Do not redesign target resolution, publication, schemas or templates.

**Gate:** default R1/R2/R3 behavior unchanged; lab resolves all six devices; missing
profile data fails closed; session resume never silently changes inventory.

### R2. Close the Full-Pipeline Test Gap Before Live Promotion

- Retain extractor fixtures as such. Add separate end-to-end prompts written as
  complete clauses, with commas/ordinary wording between fields and semicolons
  only between operations. Do not blindly concatenate `cases.json` prompts.
- For every canonical operation, verify a complete request through `run()` and
  the session flow in the disposable candidate release, not only extraction.
- Reuse existing parameter payloads and goldens as expected results. Cover all
  78 supported bindings with schema/context/render checks, distinguishing the
  42 new candidate bindings from preserved legacy support.
- Add shared-target and independently scoped multi-operation cases, missing-field
  questions, optional false/zero/list preservation, invalid input and context
  mismatch. Assert no extra or dropped intents and exact per-device bindings.
- Keep semicolon-separated *operations* working. Change planner/extraction code
  only for demonstrated defects, with narrowly targeted regressions; do not
  introduce unbounded model retries or broad parser refactoring.

**Files:** new `tests/fixtures/activation_prompts.json`,
`tests/test_catalog_activation.py`, and focused additions to existing clarification
tests. Existing planner/pipeline files only if these tests demonstrate a defect.

**Gate:** complete controlled prompts reach the intended validated/rendered
result; incomplete or unsupported cases produce no configuration. Tests run with
deterministic/mocked paths independently from live-model acceptance.

### R3. Promote the Reviewed Packs to SQLite Authoring

- Add a thin explicit promotion entry point, for example
  `app/knowledge/pack_promote.py`, reusing `read_pack`, `install_reviewed_assets`,
  `prepare_request` and `KnowledgeManagementService`. Default to rehearsal/report;
  require an explicit apply action, actor/reason and approved receipt to write.
- Inspect all pack hashes, dependencies and asset conflicts before writes.
  Install reviewed assets without overwriting differing files. Track new paths.
- Apply in the order in Section 3. For each pack, prepare from the *current*
  revision after asset installation, dry-run, then commit that same request.
  Re-read state after each commit; never reuse an earlier revision for all packs.
- Keep the existing per-pack transaction boundaries. A partial run is an
  unpublished draft, not partial runtime activation. Record progress and resume
  matching packs as no-ops; stop on conflicts rather than overwriting them.
- Run complete management validation and compare original contracts. Confirm all
  44 intended operations have active authoring status and complete bindings.
- Do not run publication implicitly from this command. Do not use partial packs
  with full-catalog import, hand-written SQL or managed seed-JSON edits.

**Files/services:** proposed promotion entry point and tests; reviewed assets added
under `data/templates/`; existing SQLite management, no authority migration.

**Gate:** SQLite contains exactly the approved expansion; original contracts and
active release unchanged; repeat application is a no-op and interruption resumes.

### R4. Publish and Verify the Indexed Release

- Quiesce terminal prompting and authoring during rollout. Reconfirm model health,
  source revision, context profile revision and current active release.
- Call `KnowledgeManagementService.publish()` with `mode="chroma"`, fresh
  `expected_revision`, `expected_release`, actor and reason. Publish once.
- Reuse existing compiler, document builder and index verification. Publication
  already switches the pointer only after the release/index is verified.
- Verify exactly 44 active document IDs, 44 compiled operation schemas and 78
  binding/profile artifacts; compare the original contracts. Check document
  category/version/release metadata and the receipt's collection/model identity.
- Query the actual collection, not only the manifest: exercise each category and
  check expected operations are reachable. A document count is not a relevance test.
- Verify runtime loading, offline-model error behavior, stale-session revalidation
  and unsupported profile rejection. A failed build must retain the prior pointer.
- Never activate an offline release as a substitute for RAG readiness. Do not run
  `python -m app.ingest` afterward: that would initiate another publication.

**Files/services:** existing publisher, ingest, vector store and retriever; new
rollout verification/report utility only where needed. Generated artifacts are
not hand-edited. Do not rebuild the publication architecture.

**Gate:** all 44 IDs are active and indexed in the same immutable release; actual
retrieval works. If a blocking operation fails, report incomplete activation,
not silent exclusion of that operation.

### R5. Run Live Prompt Acceptance and Freeze Expansion

- Add a bounded, separately invoked evaluation runner with one recorded request
  at a time, per-case timeout and structured results. Existing model retries stay
  bounded; use a worker-process timeout if needed rather than an infinite wait.
- Reuse expected fixtures but run three distinct tracks:
  1. Complete catalog-phrase prompts for all 44 operations.
  2. Natural paraphrases absent from exact catalog terms, exercising real category
     classification, retrieval and model operation selection.
  3. Interactive anomaly cases and multi-intent/device scope.
- Record expected/actual intent count, operation IDs, device IDs, extracted values,
  proposals/clarifications, final config hashes, release/profile/model identity,
  elapsed time and failure stage. Record whether retrieval/model paths actually
  ran; exact-label success must not be counted as semantic accuracy.
- Use known expected answers for automated clarification cases. Never auto-accept
  arbitrary model proposals merely to obtain `ready`. For manual tests retain
  the existing selection/custom-answer flow.
- Report category routing and retrieval top-three recall separately from model
  selection and field accuracy. The wrong category can hide the correct operation;
  do not immediately increase candidate count or rewrite retrieval without evidence.
- Produce a concise per-operation result table and terminal prompt guide. Mark
  untested/failed paraphrases honestly; do not claim strong-model equivalence.
- Freeze pack membership and release identity for the user-testing period. Fix
  demonstrated pipeline defects separately; contract/template changes require
  version review and another indexed publication. No new knowledge expansion.

**Files:** proposed `tools/evaluate_prompts.py`, reusable prompt fixtures,
`docs/PROMPT_TESTING_GUIDE.md`, `docs/KNOWLEDGE_ACTIVATION_RESULTS.md`; brief updates
to README, AI handoff and pack/completion notes distinguishing staged from active.

**Gate:** controlled cases pass; live paraphrase results and limitations are
reported, terminal clarification has been exercised, and no safety failure is
hidden by an average accuracy score. Unsafe results block lab acceptance and
trigger correction/compensation before testing continues.

## 5. Prompt Acceptance Matrix

| Scenario | Required outcome |
| --- | --- |
| Complete single operation | Correct canonical ID, device, explicitly supplied fields and binding; nonempty preview |
| Paraphrased operation | Actual RAG/model path; confirm model proposal before rendering |
| Two operations on R1 and R2 | Correct logical intents and separate device bindings; no parameter leakage |
| Two operations on R1, another on R2 | No accidental expansion of every operation to both devices |
| Missing target | Ask for the device; inventory options plus custom text |
| Ambiguous role/site/vendor reference | Evidence-backed choices; no arbitrary highest-score device selection |
| Conflicting device/interface description | Explain mismatch; compatible inventory suggestions only |
| Missing required parameter | Permitted schema/context candidates when available, otherwise typed custom answer |
| Netmask answer then interface answer | Preserve correct address/prefix; port slash never becomes a prefix |
| Invalid integer, negative, enum, prefix or list | Reject with actionable field feedback; retain earlier validated values |
| Explicit optional false/zero/list | Preserve it and validate, never silently omit it |
| Invalid capability/resource or unsupported vendor | Block; do not invent support or bypass validation |
| One incomplete task in a larger request | Retain partial state, but emit no configuration for the whole request |
| Conflicting changes to the same resource | Existing ordering/review gate; no silent overwrite |
| Same-request create/use chain | Continue to block unknown prerequisites; generation does not change inventory |
| Resume after release/context change | Revalidate facts and reject stale answers/configuration |
| Model down or malformed response | Safe deterministic fallback where possible; otherwise clarification/error, no invented values |
| Unknown operation or unsupported business intent | Ask/decline unsupported scope, never force an unrelated operation |

Safety acceptance is zero observed wrong-device rendering, invented required
values, unsupported-template fallback or rendering of incomplete requests in this
suite. This is a test gate, not a mathematical guarantee for arbitrary language.
Measure accuracy/clarification frequency and latency; agree practical performance
targets after the first laptop baseline instead of promising an invented SLA.

## 6. Terminal Experience After Implementation

The lab-profile flag below is PROPOSED; it does not exist yet. The remaining
interactive commands already exist. Run from the V2 directory with the existing
venv after R4 succeeds:

```powershell
& ../../.venv/Scripts/python.exe main.py --context-profile lab --interactive
```

Example test requests, to be verified in R2/R5 rather than claimed as tested here:

```text
Modify VLAN with vlan_id 20 and vlan_status "suspend" on SW1
Set interface description with interface "GigabitEthernet1/0/1" and description "User port" on SW1
Create VLAN 100 named STAFF on R1 and R2
Configure OSPF on R2
Create VLAN 100 named STAFF on R1; create VLAN 200 named IOT on R2
```

Expected interface: current task/device/field, one question, authoritative options
when available and a custom-answer prompt. Use `select 1` for a choice; a bare
number remains a literal value. `edit TASK_ID FIELD_PATH VALUE` explicitly changes
a prior value; `quit` retains the session; `--resume SESSION_ID --interactive`
resumes using its saved context profile. Noninteractive mode returns session JSON.

The complete guide must cover every canonical operation and supported profile,
with required fields, an expected outcome and useful negative/missing-field cases.
Some operations need structured lists/objects; do not promise that arbitrary prose
will always extract them correctly. Planned context provides facts/options, not
permission to guess the user's desired policy.

## 7. Failure Recovery and Rollback

- Before apply: rehearsal/model failure leaves live authority and release intact.
- During pack apply: keep the old release active; resume reviewed matching packs
  or correct unpublished changes through services. Track asset writes separately.
  Do not remove unrelated files or import a stale whole-catalog export blindly.
- During publication: preserve failed stages for diagnosis; do not edit compiled
  artifacts, manually set `ready` or use an offline release to mask index failure.
- After activation: use forward compensation, retiring unsafe additions or
  publishing corrected higher-version contracts. Preserve published IDs and audit
  history. Do not switch an old pointer back and accidentally revive retired data.
- Context restoration is separate: restore only the reviewed lab profile, advance
  its revision and revalidate sessions. Leave default inventory and user work alone.
- These procedures affect generation only; they do not roll back network devices.

Run rehearsal, tests and authoring/publication commands serially. Source-mode tests
deliberately reject an authoring lock; overlapping snapshots previously caused
lock-related test failures unrelated to catalog correctness.

## 8. Approval and Completion Checklist

- [ ] Approve all existing 32 additions with their bounded semantics, yielding 44
  canonical operations; no additional expansion.
- [ ] Approve generation-only lab publication despite outstanding device-lab
  certification; retain all current support/capability restrictions.
- [ ] Approve opt-in lab context and profile-bound sessions; keep default inventory
  and existing public interfaces unchanged.
- [ ] Approve reviewed SQLite promotion followed by a single Chroma publication;
  no managed JSON authority or manual SQL changes.
- [ ] Approve full-pipeline and separately measured live-model tests, including
  one-question clarification and operation-to-device scope checks.
- [ ] Verify backup/receipt, idempotent resume, stale-write/index-failure safeguards
  and forward-compensation procedure before rollout.
- [ ] Deliver activation receipt, operation/support matrix, prompt guide, measured
  results and unresolved limitations; pause expansion for user testing.

Suggested implementation authorization:

> Implement R0-R5 of this plan for generation-only lab testing. Preserve SQLite
> authority and existing interfaces, promote only the reviewed packs, add the
> opt-in lab context, publish one verified Chroma release and deliver the prompt
> test guide/results. Do not execute configurations or expand knowledge further.

If a prerequisite or safety gate cannot be satisfied, retain the safe prior state
and report precisely what remains. Creating this plan performs none of those
activation steps.
