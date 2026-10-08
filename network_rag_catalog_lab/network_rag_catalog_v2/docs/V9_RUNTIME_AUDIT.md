# V9 runtime intent audit — 2026-10-08

The original runtime could not guarantee that vendor adaptation preserved the
user's canonical intent. The failure was present in data, extraction order,
capability enforcement and evidence reuse. The changes accompanying this report
restore state-only `modify_vlan`, retain excluded explicit parameters as blocking
evidence, reset operation-dependent state, expose runtime authority and prioritize
the proposed operation in clarification.

## Evidence and request path

Read-only inspection found the exact examples in local saved sessions:

- `4f14ac59-fc06-433c-b457-53b3fbb8dadb`: Huawei state request became description;
  `knowledge_snapshot_id` was empty.
- `d579812b-b143-413c-ba4c-e2ef96ff2434`: operation changed from rename to modify;
  VLAN ID evidence still named `rename_vlan`; snapshot ID was empty.

Both are direct-file sessions. Older sessions of the rename prompt also exist
with published snapshot IDs; those do not establish the authority used by the
two failing examples. The current default is `NETWORK_RAG_RUNTIME=files`.

The actual entry path is `main.main` → `clarification.create_session` →
`pipeline.run` → `intent_planner.plan_intents` → `pipeline._process_intent`.
Exact catalog wording takes `_explicit_operation`; otherwise category
classification, top-three retrieval and model operation selection run.
Target queries resolve through inventory; `_split_bindings` produces per-device
tasks. `_refresh_task` loads schemas, checks parameters and device/context policy,
builds evidence and questions. `refresh_plan` releases configurations only when
all bindings validate and cross-task conflicts are resolved. `render` then uses
`select_template` and the effective schema. Clarification goes through
`apply_answer`/`apply_clarification` → `resume_task` → `_refresh_task` →
`refresh_plan`; explicit edits use `correct_task` and the same boundary.

## Findings, fixes and regression coverage

### 1. Vendor semantic substitution — modeling bug

Before the fix, `data/catalog/operations.json` described `modify_vlan` as both
state-only and vendor-dependent description modification. Its direct schema
`data/operations/vlan/modify_vlan/schema.json` replaced Huawei's properties with
`vlan_id, description` and Juniper's with those plus `current_vlan_name`.
`schema_loader._apply_vendor_requirements` applied each profile with `dict.update`,
replacing both properties and required fields. The matching Jinja templates
contained description commands. `test_native_vendor_runtime` explicitly expected
the Huawei description output: the substitution was deliberate implementation,
but violated the canonical operation contract.

`_process_intent` previously loaded the already narrowed vendor schema before
extracting values. `_refresh_task` therefore found a missing description, and
`questions.build_questions` used its parameter metadata to ask for one. Once
answered, every local validation step accepted the wrong operation semantics.
Direct template selection also returned before checking `vendor_knowledge`.

Fix: retain the existing stable `modify_vlan` ID with state-only semantics;
remove the two description templates; declare Huawei/Juniper `blocked_unverified`;
enforce that block during template selection and before dependent questions.
This means an equivalent implementation is unreviewed, not that vendor hardware
is proven incapable of changing VLAN state. No hardware claim or command was
invented. The schema's `x-semantic-fields: [vlan_status]` requires profiles to
preserve that input and direct templates to consume it.

Regression: state requests on SW2/SW3 retain `vlan_status=suspend`, expose the
support block, never ask for description and cannot render, including inside a
mixed request. Cisco still renders `state suspend`; direct `render` also blocks
Huawei/Juniper. The 114 vendor fixtures now represent 112 supported combinations
and two expected blocks.

### 2. Runtime authority divergence — intentional modes, accidental semantic drift

`config.runtime_mode` defaults to files. `knowledge.runtime.current_snapshot`
does not open a release in that mode. `catalog.knowledge_service` uses the direct
file repository; `load_schema` reads physical schemas; template selection uses
vendor/category/operation paths rather than managed binding records.
`_refresh_task` and `refresh_plan` assigned an empty snapshot ID because there
was no snapshot. That blank value is correct, including for successful renders.

SQLite's authority marker controls managed authoring, independently of the runtime
mode. Its `modify_vlan` operation and field mappings still described VLAN state
only. The active release `44d6ad1355b44a6c9a91624d9ee31512` likewise contained only
`vlan_id, vlan_status` and blocked unreviewed Huawei/Juniper support. The direct
file changes had bypassed those reviewed bindings and publication checks.
Existing `DIRECT_RUNTIME.md` explicitly recorded the earlier development switch
to files and that later direct edits were not synchronized with SQLite/releases.

Fix: plans, tasks and CLI output now expose `runtime_authority`. Direct files
remain the development runtime authority; SQLite remains managed authoring;
published requests still use immutable snapshots and record their release IDs.
The retained source fallback for an unmigrated published-mode installation is
labeled `authoring_files`. No release ID is fabricated for direct mode.

Reconciliation gate: `python -m app.knowledge.runtime_audit --check` compares
descriptions, schema assertions and vendor template content across files, managed
authoring and an active release, without writing to any of them. Scope it with
`--operation modify_vlan` to verify this correction; that scoped check passes
against the actual local SQLite database and active release. Whole-catalog
differences in 29 other operations still require review because later direct native contracts were never
promoted to managed knowledge. The audit does not equate direct template paths
with managed platform/version eligibility and explicitly reports that limitation.
Use the existing versioned management/publication workflow for an authorized
future promotion; do not automatically copy differences or publish them.

Regression: direct sessions retain a blank release ID and identify files;
the audit detects schema/vendor drift and performs no writes. Existing published
snapshot tests continue to cover release pinning and artifact integrity.

### 3. Operation confirmation order — UI bug

`_process_intent` already had ranked retrieval candidates, but passed them only
to `select_operation`. They were discarded afterward. `build_questions` built
`operation_id` options by iterating `load_operations()` in catalog order, applying
only device feature filtering. `main._print_question` then paged eight choices
at a time. Neither retrieval rank nor the proposed operation affected that order.

Fix: persist `operation_candidates`; sort the proposal first, then retrieved
candidates in rank order, then remaining catalog choices. Label the first option
`Confirm Rename VLAN (proposed)` for a rename proposal. Retain all alternatives
and the existing explicit `select N` protocol.

Regression: a rename proposal with modify ranked above it still puts rename
first, then modify/create; selecting the first option confirms rename. Bare
numbers remain literal network values, as the CLI intentionally specifies.

### 4. Stale evidence after operation override — provenance bug

`resume_task`'s `path == operation_id` branch did re-extract parameters using the
new operation and replace provenance/candidates. It reset confirmations, but left
`parameter_evidence` and `item_ids`. `_refresh_task` reused a previous evidence
record whenever its value equaled the current value. A VLAN ID of 20 therefore
kept `operation_id=rename_vlan` after being revalidated for `modify_vlan`.
The observed mixed provenance was real; the normal override path did revalidate
parameters, so the mixed record alone does not prove validation was skipped.

Fix: overrides reset evidence, item identities, confirmations, questions and
operation candidate context. Evidence reuse now also requires matching operation,
device, source, source revision and validation state. Compatible values explicitly
present in the original request are re-extracted under the new contract;
operation-specific values disappear only after the human selects the replacement
operation. Historical clarification records remain available. The invalid-operation
fallback also clears binding evidence and marks retained values unvalidated.

Regression: both the operation question and explicit edit paths rebind VLAN ID
evidence; incompatible rename parameters/provenance are absent; new state evidence
has the correct operation; stale saved evidence is repaired during refresh;
target changes rebind device evidence.

### 5. Explicit parameters disappearing — extraction-boundary bug

The state value did not disappear in Jinja or when merging the description answer.
It had already been excluded by `parameter_extractor._filter_to_schema`, which
iterates schema properties, and by `normalizer.canonicalize_parameter_keys`,
which recognizes only keys/aliases in that schema. JSON Schema's
`additionalProperties: false` could not detect a value it never received.

Fix: extract using canonical/all-profile field vocabulary first, including
recursively merged object/array shapes. Validate separately for each device.
`pipeline._unsupported_parameters` detects excluded explicit fields, including
nested fields. The original value remains in parameters/evidence with a blocking
`PARAMETER_UNSUPPORTED_FOR_VENDOR` issue naming the field, value and target.
Dependent parameter questions and rendering wait for an explicit operation or
target correction. Fields invalidated by normal value validation still follow
the existing rejected-candidate clarification path.

Regression: a synthetic future vendor profile removing an explicit name while
requiring description now blocks with the original name intact. Repeated refresh
cannot erase the issue. Nested native QoS fields remain extractable from the
combined vocabulary and are still validated against each device's actual schema.

### 6. Operation boundaries — normalize the existing ID

Keep `create_vlan` for creation and `rename_vlan` for identity/name changes.
Keep `modify_vlan` state-only to preserve existing IDs, aliases, bindings, context
policies and managed history. A later display-label change to “Modify VLAN State”
is optional; creating a replacement ID is not necessary for this fix.
If VLAN description editing is wanted, add a separate reviewed operation such as
`set_vlan_description`, with its own mappings, templates and context policy.
The current rename implementations use Huawei `name` and Junos object rename;
they should not silently gain description behavior either.

Schema annotations, explicit-parameter retention and capability gates enforce
structural invariants. They cannot prove that arbitrary future template text has
the correct networking meaning. Adding or changing vendor support still requires
semantic review and concrete vendor command regressions. This audit fixes the
reported substitution; it is not certification of every direct vendor contract.

## Validation

28 focused tests passed: ten intent-integrity tests, three audit tests, seven
direct-file tests and eight existing compatibility/clarification/vendor tests.
They include 32 added-operation prompt examples, the 114 vendor contract cases
(112 render and two block), proposal ordering, override evidence, OSPF requirements,
numeric answers, inventory/context choices and multi-device rendering gates.
Additional Cisco/Huawei/Juniper native QoS prompt checks reached ready with exact
fixture parameters. A smoke test against the actual active published snapshot
rendered Create VLAN on R1 and recorded its release ID. Read-only revalidation of
the old Huawei saved session blocked its previous description output.

The broad suite is not green. Broad exploratory runs were stopped after identifying
repeated older-fixture failures. Four representative tests were then compared in
the working tree and a temporary export of unchanged HEAD: both produced 195
errors, comprising 192 missing example entries, one existing alias-collision
error and two publication/management vendor-binding contradictions. After fixing
`modify_vlan`, the first reported contradictory operation moves to `rename_vlan`.
Those broader fixture/data reconciliation problems are not hidden or marked passing.
The final focused file-runtime run passed after fixing recursive extraction of
vendor-specific nested QoS inputs discovered during verification.

Deterministic tests mock model responses; they do not measure live retrieval/model
accuracy or execute configurations on devices. The configured Ollama endpoint
`127.0.0.1:11434` refused connections, so no embeddings were refreshed. Catalog
content changed: after starting the existing configured service, run
`python -m app.ingest` in files mode before testing paraphrase retrieval.
Exact catalog operation prompts do not require that retrieval index.

SQLite, the active pointer, immutable releases and existing saved sessions were
only inspected, not edited or republished. Removed templates are recoverable from
Git history. Historical stored outputs are revalidated on resume and cannot bypass
the corrected capability gate.
