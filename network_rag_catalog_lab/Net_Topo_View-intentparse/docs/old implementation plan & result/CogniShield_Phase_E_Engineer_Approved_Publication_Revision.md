# CogniShield — Phase E: Complete Multi-Vendor Publication and Evidence-Grounded AI Convergence

> **REVISION — Senior-engineer-authorized publication policy (2026-10-18).** This revision supersedes any clause in this plan that makes online vendor-document verification, independent semantic certification, device/emulator testing, or full Ansible validation a prerequisite for **publishing engineer-approved native configuration knowledge**. Publication and proof of vendor/device conformance are different decisions. Codex must implement this policy throughout E1–E4 and E10, not merely append a disclaimer.
>
> **Approval authority:** An authenticated user with the project's authorized senior knowledge-review/publish role may approve a precise operation + vendor + platform/version scope, template content/version hash, parameter contract, assumptions/prerequisites, known limitations and release target. Obtain explicit human approval; never invent a senior sign-off or infer it from a template's existence. If an earlier approval truly applies to that same content/version/scope, reuse its auditable record rather than require reapproval purely because public references are absent. If content has changed materially, reapproval is required.
>
> **Mandatory engineering-publication gates:** distinct identity and binding, valid schema/field relationships and safe parameter handling, deterministic successful template compilation/rendering on representative valid inputs, validation of required/invalid inputs and unauthorized access, runtime operation/binding lookup for its declared profile, immutable release/manifest/index integrity, authenticated activation and rollback, and an explicit authorized senior-engineer sign-off. These tests verify **application operability and review authority**, not the external factual truth of every CLI command. A reviewed method that fails the structural/runtime gates must be repaired so the software can use it; absence of public documentation must not block it.
>
> **Optional, independent certification dimensions:** official vendor documentation, independent semantic comparison, a second engineer's technical assessment, real hardware/virtual NOS conformance and contained genuine Ansible playbook validation. Report each as `VERIFIED`, `NOT_VERIFIED`, `FAILED`, `NOT_RUN`, or `NOT_APPLICABLE`. None automatically vetoes *knowledge publication* after valid senior approval; however a demonstrably unsafe command, conflicting permissions or material risk identified during review must be surfaced to the approver for explicit resolution, not silently waived.
>
> **Truthful labels and safeguards:** an approved binding without independent vendor evidence is `ENGINEER_APPROVED_NOT_INDEPENDENTLY_CERTIFIED`, not `VENDOR_VERIFIED` or `DEVICE_TESTED`. It may be selected and rendered through the ordinary **published V9 knowledge release**, but the output and UI must show its trust status and any documented caveats. Authoring/publishing is not device deployment. No automatic device configuration, privileged SSH, autonomous execution, implicit Save or bypass of Studio review/authorization. Genuine Ansible variants remain separately gated.
>
> **141/141 completion meaning:** all 141 operation-vendor combinations must be structurally operable, individually approved (or explicitly awaiting human approval), published in a reachable immutable release and tested for rendering. Codex must do the implementation and provide a batch review/sign-off experience, but cannot counterfeit approver identities or waive user action. If any approval remains outstanding, the final count is honestly lower than 141 and the exact pending actions are listed. A public internet source is **never** itself a required approval.


**Status:** Implementation-ready continuation specification, **not** a report of implemented changes.  
**Prepared:** 2026-10-18  
**Target checkout:** the latest `Net_Topo_View-intentparse` working tree and its already integrated V9 knowledge services.  
**Execution intent:** Submit this file to Codex in **Code/Work implementation mode**. Inspect actual checkout first; do not replace implementation with another proposal.  
**Source of truth for existing work:** `docs/evaluations/PHASE_D_RESULTS.md`, `docs/evaluations/phase_d_vendor_coverage.json`, `docs/evaluations/phase_d_execution_review.json`, `docs/UI_RESTORATION_HANDOVER.md` (or the exact latest numbered handover), the actual source, published release manifest, immutable run artifacts and Git status.

---

## Executive mandate and non-negotiable distinction

The purpose of **Phase E** is to **finish Phase D's failed and incomplete gates**. It is **not Phase D from scratch** and must not introduce a new LangGraph, knowledge catalog, SQLite authority, generic RAG index, editor, or simulator. Continue from the actual protected dirty tree, reuse the existing V9 APIs, and make measurable progress on every outstanding row and failed evaluation.

### Primary end state

1. **All 47 operations × Cisco IOS-XE, Juniper Junos and Huawei VRP = 141 distinct, tracked vendor-operation candidates must reach final resolution.** The explicit objective is **141 structurally valid, senior-engineer-approved, published and runtime-renderable bindings**. Independent vendor documentation and external semantic/device certification are separate, optional labels—not publication prerequisites. **Do not stop at auditing, reviewing, parsing Jinja, building offline candidates or reporting the old 64 translation gaps.** Implement missing contracts, mappings, validation and native syntax.
2. **Reusable generic vendor rendering is encouraged** as an engineering *implementation mechanism*: canonical typed network intents → vendor/platform-specific normalizers and CLI emitters → V9 templates/bindings. It is **not** permission to falsely label commands as vendor-certified, conceal incomplete behavior or skip explicit engineering review. An engineer may nevertheless approve a best-effort, documented vendor method for publication with honest uncertainty labels, even without independent public references. If a complete vendor-native equivalent cannot be established, expose the limitation to the authorized reviewer; the reviewer can approve a clearly scoped best-effort native rendering as an engineer-reviewed method, without calling it independently vendor-certified. An unsupported metadata entry alone does not count toward the 141 renderable-binding target. Attempt documented alternative native implementations before declaring incompatibility. The 141 target is a knowledge-publication and rendering demonstration, **not** a guarantee of 141 independently correct or device-tested implementations; never fabricate an approval or certification.
3. The new **real-model planning and synthesis paths** must outperform, or demonstrably match while materially improving a predeclared task-completion measure, the B3 baseline on genuine untouched tests before default enablement. **Do not count deterministic fallback as successful LLM reasoning.**
4. The **central development simulation** must become a reusable validation laboratory, with coherent multi-vendor scenario generation, independent expected outcomes, protocol/forwarding conformance and reproducible model/tool traces.
5. Resolve remaining **response/UI and integration failures**, especially browser Copy, normal external-mode parity, limited LLM answers, routing rubric defects, missing playbook-tooling certification and incomplete release retrieval readiness, without weakening owner permissions or editor review.
6. Produce a **senior-engineer-approved new ordinary immutable release**, update its active pointer through the existing management APIs, prove runtime retrieval/compatibility/rendering in ordinary and isolated acceptance modes, and preserve a proven rollback. Authorized **knowledge publication** is in scope. Physical network writes, SSH configuration, deployment, autonomous remediation and automatic file saving are **not**.

**Completion discipline:** Distinguish `IMPLEMENTED`, `STATIC_CHECKED`, `RENDER_TESTED`, `ENGINEER_APPROVED`, `PROFILE_SEMANTICS_CERTIFIED`, `CANDIDATE_PUBLISHED`, `ORDINARY_ACTIVE`, `DEVICE_TESTED`, `ANSIBLE_VARIANT_VERIFIED` and `INCOMPATIBLE` in the coverage ledger. One status must never stand in for another. Do not mark the phase complete when a gate is blocked or unverified; continue independent tasks, preserve evidence and report an exact remaining-work queue.

---

## 0. Evidence-derived starting state: preserve, don't reinterpret

The October 18 Phase D files state:

| Measure | Recorded checkpoint | Meaning / remaining work |
|---|---|---|
| Coverage | **141 distinct candidates, 47 canonical operations, 47 each for Cisco/Juniper/Huawei** | The candidate list is comprehensive, but only statically reconciled. |
| Existing ordinary V9 | **44 operations, 78 bindings**, release `0690966eb003499380e960a98d1e418f` | Currently active; retains earlier semantic uncertainties. |
| Separate acceptance candidate | **47 operations, 81 bindings**, release `27725812f27742ea95422fed1fd85e40` | Only isolated activation/rollback tested. Not ordinary active. Retrieval `ready:false` must not be represented as production-ready indexing. |
| Candidate native runtime tests | **11 PASS / 130 NOT RUN** | PASS only for narrow fixture combinations, not full semantic certification. |
| Full Phase D semantic/profile certification | **0/141** | All rows still need the complete independent verification ladder, including previously published copies. |
| Reference remediation | **9 editable reference fixes** | Existing publication cannot be inferred from these source edits. |
| Knowledge gaps | **63 rows unavailable in ordinary published binding**, 78 previously active | Fix all missing contracts and binding dependencies, without importing isolated test state. |
| Deterministic/affected tests | **121 test methods + 34 additional subtests passed** | Not equivalent to whole-system or vendor certification. |
| Model source selection | Fresh matched **6/8 candidate vs 6/8 baseline** | No measured improvement, more inference calls/time in candidate. |
| Historical 52-case benchmark | Candidate **14/52 → 19/52**; legacy **19/52** | Existing rubric has known source-set/fixture defects; all 52 are exposed regressions, not unseen holdouts. |
| Target intelligence gates | Routing **≥90%**, answer adequacy **≥85%** | Not reached; full independently graded M0/M1/M2/M3 evaluation incomplete. |
| Model | Ollama **`qwen2.5:1.5b`**, actual local CPU inference | Misclassified prompts, invented routes, confused OSPF router IDs, overclaimed operational health, repeated/uncited prose and timed out. |
| New AI feature switches | `COGNISHIELD_AI_PLANNING=0`, `COGNISHIELD_AI_SYNTHESIS=0` | Disabled in ordinary mode; do not enable globally before gates. |
| Development simulator | `development/network_model.py`, 3 new mixed scenarios, typed forwarding/ACL/VRF/protocol/metrics | Bounded 32 hops/branch, 16 branches; partial unknown. Full protocol/packet conformance not certified. |
| UI | Shared Markdown/color, Copy and contextual Review in Studio | Browser clipboard read/paste blocked by virtual clipboard; external normal-mode parity untested. |
| Ordinary app | Standard **5173 frontend / 8000 backend**, Ollama **11434**, development simulation off | Preserve normal user data, source revisions and app behavior. |
| Protected staged baseline | 52-file original staged patch, index SHA `d6aa68e47ae3b44449d1f832404ad925a373791b845ec064d067b8e8b028d7f8` | Never reset, re-stage or commit it automatically. |
| Ordinary SQLite | Integrity and foreign keys OK; one pre-existing `ansible_chat_sessions` hash differs at checkpoint | Preserve discrepancy; do not assume timestamp-only or overwrite newer conversation rows. |

**Existing files/modules to inspect and reuse:** `backend/scripts/phase_d_audit.py`, `backend/scripts/phase_d_knowledge.py`, `backend/scripts/evaluate_phase_d.py`, `backend/llm/orchestration/planning.py`, `synthesis.py`, `engine.py`, `verification.py`, `adapters.py`, `development/network_model.py`, `backend/development/scenario.schema.json`, `backend/development/scenarios/`, existing `KnowledgeService`, `/knowledge/edit`, `/template`, `/validate`, `/render`, `/build`, `/activate`, `local_providers/knowledge_worker.py`, `AssistantMarkdown.tsx`, `assistantCode.ts`, `EngineeringHandoffAction.tsx`, the actual frontend studio components and `gateway_handoff.py`. **Verify actual source paths rather than assuming every path fragment belongs under the same directory.**

Existing continuation/acceptance assets (if still present; verify ownership and file identity before reuse): `tmp/phase-d/preservation-final.json`, `ordinary-runtime-final.json`, `conversation-isolation-final.json`, `source-delta.json`, `tmp/phase-d/acceptance-knowledge`, `tmp/phase-d/acceptance-scenario.json`, `tmp/stabilization-20261017/acceptance.db`, `tmp/phase-d/final-affected-regressions.xml`, `tmp/phase-d/d5-browser/`. Never transplant an acceptance DB, release, pointer or conversation into ordinary data.

### Implementation order

Run **E0 immediately**; then **E1/E2/E3** to close catalog coverage in progressive cohorts. **E3** (engineer approval and technical publication readiness; independent certification separately) runs as soon as each cohort has renderable templates. **E4** (publication/index/activation) uses approved and structurally tested cohorts only and ends with a full-catalog acceptance. **E6** scenario conformance and **E7/E8** model intelligence can proceed in parallel in separate source areas, retaining common snapshots/tests. **E9** UI/integrations and **E10** final acceptance follow affected dependencies. Preserve an independent durable checkpoint after every cohort; if usage runs out, the next Codex session must resume from recorded state, not repeat earlier completed work.

---

# E0 — Read-only preflight, protected baseline and work registry

**Goal:** Prevent implementation damage and establish an honest repeatable baseline.

1. Inspect `git status --short`, staged diff, unstaged diff, untracked source, branch/HEAD and latest handover. Verify the protected index hash. Do not stage, reset, clean or amend it. Check for user edits made since the handover and reconcile them instead of clobbering them.
2. Inspect actual source/virtual environments, V9 integration, authored SQLite/workspaces and active release without starting automatic migrations or changing pointers. Verify ordinary DB ownership, hashes, integrity/foreign keys and current 5173/8000/11434 processes. The Phase D preserved `ansible_chat_sessions` hash discrepancy must remain disclosed; collect row-level safe before-images now for any future authorized migrations.
3. Record the current `phase_d_vendor_coverage.json` **141 record identities**, existing template and binding SHA-256 values, operation/profile pair and original findings. Freeze this as `phase_e_baseline_vendor_coverage.json`; future revisions append structured remediation evidence rather than silently replacing or losing old findings.
4. Read all retained failed model traces and browser evidence. Distinguish reproducible product bugs from benchmark rubric bugs, model limitations and automation-environment limitations.
5. Create `docs/evaluations/phase_e_cases.json`, `phase_e_vendor_progress.json`, `PHASE_E_RESULTS.md`, `PHASE_E_IMPLEMENTATION_CHECKPOINT.md` and an ignored run root such as `tmp/phase-e/`. Use stable IDs and immutable timestamped run folders, not an overwritten latest-only JSON. The `phase_e_vendor_progress.json` schema must have 141 persistent row IDs from day one.
6. Run focused safe baseline regression, TypeScript/build, historical source-set routing and accepted runtime reader checks **once** with distinct results. Don't waste time rerunning identical passing tests unless affected code changes. Use the existing actual Ollama model and compare under matched environment/resources.
7. Add a machine-readable stage-state tracker with `not_started/in_progress/blocked/verified`, source revisions, dependency gates, coverage and links to original failures. No stage is marked verified from absence of an exception.
8. Maintain one disposable acceptance composition, reuse declared workspaces, standard 5173/8000 when required and stop owned processes only. Windows OneDrive permissions, Ollama reserved ports, reload process propagation and browser settings require truthful error classification; do not open random alternate ports.

**E0 gate:** Protected Git staging unchanged; ordinary release/inventory not touched; all 141 rows imported without loss; D-stage shortcomings reproducible or preserved; clear reproducible commands and durable checkpoint written.

---

# E1 — Make all 141 vendor-operation candidates actionable knowledge work items

## E1.1 Upgrade the coverage ledger into an executable work queue

For every `(operation_id, vendor, declared platform/version, output_variant)` produce a stable record with:

- Canonical semantic effect and preconditions; whether it creates, changes, removes, attaches or detaches configuration.
- Vendor CLI mode/hierarchy and platform/version applicability; existing reference path/hash and active binding path/hash.
- Parameter types/requiredness, default/derived fields, format normalization, nested fields, canonical-to-vendor mapping and special-case dependencies.
- Existing config/state required to safely implement the operation; what may be resolved from authorized inventory/configuration, and what must be clarified.
- Engineer-reviewed command specification, approved positive/negative output examples, delete/rollback and idempotency behavior; optional vendor documentation/version/section as additional independent certification evidence.
- Candidate authoring revision, compiler/validator result, compiled manifest binding, retrieval lookup, V9 runtime finalization/target selection, native rendering and final API/UI result.
- Engineer-approved method and known limitations; optional independent semantic test class/vendor source evidence; remaining unknowns and exact failure category.
- `static`, `candidate runtime`, `engineer approved`, `independent semantic certified`, `published`, `active` and `device tested` statuses as separate fields.

Repair scripts must be **idempotent**, inspect current authoring revision before edits, refuse stale hashes, avoid duplicate operations/bindings, and be safe to resume after an interruption. Each command should accept a single operation/vendor or an explicit small batch; it must never silently skip unknown rows.

## E1.2 Contract-authoring rules

- Use **one canonical operation** with vendor-specific normalized realizations where semantics match; introduce a semantic variant, platform capability or conditional required parameter if differences are material.
- Do not insert arbitrary vendor parameters into universal `GlobalParameter` if the constraint belongs in `OperationSchemaRule` or vendor-specific mapping. Retain V9's intended `OperationParameterMapping`, `OperationSchemaRule`, `TemplateBinding` separation.
- Persist changes via authoritative `KnowledgeService` and `SQLiteAuthoringStore` transactions; validate entity relationships and versioned referential integrity. No hand-edit of immutable published artifacts.
- Resolve missing 63 ordinary bindings, including Junos and Huawei draft translations, using real vendor contracts; reconstruct missing management operation contracts already begun in isolated acceptance, then test that no old `lab_label`/VLAN v3 isolation contract leaks across.
- Reference-only source files remain drafts until their exact authored source, compiled binding, review approval, and runtime smoke tests pass. Do not conflate 77 reference copies, existing 78 bindings, and 141 engineer-approved publishing goals.
- Record inherited configuration preconditions (`existing protocol process`, `logical interface`, `AAA settings`, `routing instance`, `class-of-service objects`, `VLAN name`, `policy object`) in the binding/schema and in review/clarification. Do not silently fabricate or treat another operation's outputs as already deployed.

## E1.3 Generic vendor-native syntax framework — specific meaning of “generic”

Implement **reusable grammar, normalizers and scoped command emitters inside the existing V9 authoring/compiler/rendering system**. Avoid a new template engine or a magic “any vendor” CLI fallback.

Canonical request → typed logical operation + normalized fields → vendor capability/profile and state checks → vendor-native render contract → existing Jinja/binding → validated native configuration.

Allowed reusable components (if absent): prefix/netmask conversions; strict interfaces/subinterfaces; local vs remote AS; OSPF area normalization; device-specific wildcard; VLAN name lookup; ordered ACL terms and direction; policy/rate units, shaping vs policing semantics; hierarchical CLI context; create/update/delete inverse; safe quoting/escaping; sanitized banner delimiters; exact device-specific references.

Use **a small number of shared family renderers**, not 141 copy-pasted branches. But **each of 141 combinations retains its own tested native emitter/binding** and declared profile. Generic rendering must still produce a known Junos `set/delete` hierarchy for a Junos profile, IOS-XE configuration commands for Cisco, and VRP system-view commands for Huawei as supported. Reject ambiguous, unmapped or semantically incompatible operations with a precise typed clarification/error rather than using the nearest CLI dialect.

A generic abstraction that represents a policy attachment or VLAN modification is useful; a made-up generic CLI statement is not. A published `unsupported/needs_authoritative_review` metadata record can explain absence; it is **not** executable template publication and cannot pass the 141/141 executable target.

## E1.4 Work scheduling and completion

Batch by **dependency graph**, not solely filename order. Select cohorts that can produce full reversible round-trips and needed prerequisite objects, then move to protocol/policy/security complexity. Work on every row, not just the easiest. If a vendor's feature appears absent or requires a best-effort substitute, record the limitation and seek senior engineer approval of the precise method; no external documentation is required for approval, and an unsupported metadata row alone never counts as a renderable binding.

**E1 gate:** Every 141 candidate has a concrete authoring task, owner, proposed vendor-scoped syntax or engineer-reviewed best-effort variant, explicit dependencies, approval status and repeatable test ID. Progress report shows implementation counts by vendor and operation family rather than merely “review required.”

---

# E2 — Full vendor-family implementation, without blanket “unverified” deferrals

## E2.1 Priority cohorts

| Cohort | Canonical operations | Core completion problems |
|---|---|---|
| **A — VLAN/interface/access/trunk** | `create_vlan`, `delete_vlan`, `modify_vlan`, `rename_vlan`, `set_native_vlan`, `assign_vlan_to_trunk_port`, `configure_access_port`, `configure_trunk_port`, `configure_trunk_allowed_vlans`, `configure_interface_ip`, `remove_interface_ip`, `configure_loopback_interface`, `set_interface_admin_state`, `set_interface_description` | Junos VLAN ID↔name reverse lookup; physical↔logical interface and family; VRP trunk/access/PVID context; real Cisco IOS-XE capabilities and interface inventory; deletes/rollbacks. |
| **B — Static and default routes** | `configure_static_route`, `remove_static_route`, `add_default_route`, `add_floating_static_route` | Preserve Phase D Cisco/VRP mask and Junos CIDR fixes; route preference/AD/distance; exact remove symmetry; next-hop/device/VRF context; `0/0`, `/32`, malformed host-bits cases. |
| **C — OSPF and IS-IS** | `configure_ospf`, `enable_ospf_process`, `assign_interface_to_ospf_area`, `create_ospf_area`, `advertise_network`, `set_ospf_router_id`, `configure_passive_interface`, `remove_ospf_interface`, `configure_ospf_redistribution`, `configure_isis_interface`, `disable_isis_interface` | Cisco process vs Junos area/interface hierarchy vs VRP numeric process/area; Junos logical interface/family ISO and NET for IS-IS; advertised-network and policy semantics; root ID and redistribution source dependency; passive interface equivalence. |
| **D — BGP** | `configure_bgp_neighbor`, `remove_bgp_neighbor` | Neighbor context, AS roles, peer-group requirements, address-family activation, existing group vs new group, exact deletion and no accidental route advertisement. |
| **E — ACL and filtering** | `create_acl`, `add_acl_rule`, `modify_acl_rule`, `delete_acl_rule`, `apply_acl_to_interface` | IOS-XE wildcard/sequence and VRP `acl` rule IDs vs Junos firewall/filter terms; order, action, prefixes, ports, protocols, interface family/direction, default action, reversible edit and existing-policy conflicts. |
| **F — QoS, scheduling and LAG** | `create_qos_policy`, `create_classifier`, `classify_by_dscp`, `configure_policing`, `configure_shaping`, `configure_scheduler`, `apply_qos_policy_to_interface`, `configure_port_channel` | Junos class-of-service classifiers/forwarding classes/schedulers and family/policer attachments; Huawei classifier/behavior/policy dependencies; correct rate units, burst, ingress/egress, LACP mode/aggregation. |
| **G — Management security** | `configure_login_banner`, `configure_exec_timeout`, `configure_login_lockout` | Separate authentication classes/VTY ranges and timeout units; IOS-XE fixture limited to VTY 0–4; Junos login-class and timeout scope; Huawei AAA policy/security behavior needs actual vendor verification, no placeholder lockout string. |

Implement per cohort in dependency order, using cross-operation fixtures to establish prerequisites and do not silently modify out-of-scope device state. Within the same vendor, shared data normalization should be reused across operations, not copied again. Ensure both existing 78 bindings and missing 63 receive full tests.

## E2.2 Concrete remediation rules from Phase D findings

**Junos VLAN:** If an operation is expressed by VLAN ID but native deletion/rename needs a VLAN name, use an authoritative actual/configured VLAN mapping or request clarification. A default synthetic name is not acceptable. Test duplicate IDs, missing names and stale mapping. Bind the chosen name to the reviewed operation and redo resolution after target correction.

**Junos interfaces and IS-IS:** Validate `.0` logical unit or declared logical unit and family `iso`/`inet` as relevant. Model NET and area prerequisite separately; declaring level or adjacency is not achieved by merely printing `set protocols isis level`. Differentiate new process, existing process and interface attachment. Verify removal reverses only intended lines.

**Huawei process identity:** Use validated numeric OSPF/IS-IS process identity and intended interface/context. Never map arbitrary `process_name` or unqualified `isis enable` to an unrelated instance. Check VRP release-specific grammar and explicit process existence.

**OSPF variations:** Cisco process ID is not equivalent to Junos or VRP process notions; OSPF network statement semantics are not uniform. Handle interface-based vs network-prefix advertisements, router ID, area types, passive interface, redistribution policy and removal individually.

**ACL and firewall:** IOS-XE ACL vs Junos firewall filter vs Huawei ACL are not text-equivalent. Define logical match/action/order interfaces, translate to vendor-native objects and attachment contexts, then verify semantics including implicit default and delete by rule identity. Reject NAT/stateful firewall requests not represented in these operations.

**QoS:** Verify policing/shaping units, scheduler/classifier dependencies, VRP classifier/behavior/policy object chain, Junos CoS/per-interface attachment and whether every step is a single operation or a reviewed prerequisite. Test both native rendering and selected target capability.

**LACP / channel:** Confirm dynamic active/passive/static modes, link aggregation membership and exact interface contexts for all three vendors, including existing-bundle conflict and detach behavior. No silent fallback from LACP to manually aggregated static links.

**Security:** Banner delimiter escaping; IOS-XE lockout/quiet mode/recovery behavior; Junos `login-class` timeout and user/class selection; VRP AAA behavior scoped to release. No guessed global lockout commands or automation that could lock engineers out. Validate effects through independent references and test fixtures; retain manual review notice where physical behavior is unverified.

**Existing route fix:** Re-run actual standard runtime after new candidate and verify the old ordinary CIDR defect is absent; source-only repaired references or isolated previews do not count. Use three-vendor add/remove symmetry and route constraints.

**Partial operation semantics:** Where the canonical operation asks more than one vendor-native command can achieve, use an explicit ordered transaction of native commands in the same binding or reviewed multi-task dependency chain. Do not mark a partial command that ignores required fields as successful.

## E2.3 Runtime matching and clarification

For every operation/vender/profile:

- V9 category/operation retrieval should find the operation without relying on a specific training prompt string; use existing published requirements/retrieval and confirm runtime availability.
- Target resolver must use the authorized inventory snapshot; vendor, platform, OS version, capability and actual interface names must be exact. Ordinary R1/R2 retain Cisco IOS identities; don't relabel to IOS-XE.
- Missing values trigger parameter clarification; correction of device/vendor invalidates dependent interface, parameter, previous preview and release selection while preserving independent values.
- Generated configuration must be displayed as a reviewed **unsaved** Monaco artifact only after V9 finalization and confirmation; no deployment or automatic Save.
- For multi-operation requests, preserve siblings and dependencies, reject an incomplete whole request rather than dropping unsupported tasks, and maintain clear native-versus-genuine-playbook variants.

**E2 gate:** Complete an actionable, structurally consistent and renderable candidate for each of the 141 combinations with positive/negative V9 input tests. Uncertain command semantics must be disclosed to senior reviewers, not automatically used to block their publication decision. Do not mark unapproved knowledge as approved.

---
# E3 — Senior-engineer approval, mandatory application checks and optional independent certification

**Goal:** Convert reference templates into structurally sound, usable, auditable **engineer-approved published knowledge**. External semantic/document/device certification is optional and separately labeled. This removes the excessive Phase D gate while retaining technical publication integrity.

## E3.1 Publication readiness versus optional independent certification

**Do not require an internet citation or a physical lab test as a prerequisite when the authorized senior engineer has approved the method.** Apply the checks below to all 141 candidates. Track each result independently.

| Gate | Scope | Required to publish? |
|---|---|---|
| **K0 — Identity/scope** | Stable canonical operation, vendor, declared platform/version, template/contract hash and intended effect | **Yes** |
| **K1 — Contract/relationships** | Correct input types, required fields, mappings, dependent objects and internal referential integrity | **Yes** |
| **K2 — Compilation/structural correctness** | Jinja parses, strict undefined behavior, safe derivations, compiled schemas/artifacts, no missing variables | **Yes** |
| **K3 — Representative rendering** | Operation-specific reviewed valid-input example compiles and produces nonempty expected output; clarify prerequisites and limitations | **Yes, technical execution; independent semantic certification optional** |
| **K4 — Core negative/security tests** | Invalid/missing inputs, access denial, target/vendor mismatch, dangerous injection/escaping and unauthorized effects fail appropriately | **Yes** |
| **K5 — Authorized senior-engineer sign-off** | Authenticated reviewer identity, approval timestamp, operation/vendor/platform scope, content hash, approved method and caveats | **Yes** |
| **K6 — Actual V9 operation execution path** | Retrieve → select → resolve → clarify → validate → select binding → render reviewed unsaved output for compatible fixture | **Yes** |
| **K7 — Publication/runtime integrity** | V9 immutable build and manifest, retrieval/index readiness for configured method, active pointer/caches, rollback and API smoke checks | **Yes** |
| **K8 — Independent vendor semantic/doc review** | Official vendor Internet manuals, independent grammar/effect comparison, additional expert evidence | **No; separate certification status** |
| **K9 — Hardware/virtual NOS conformance** | Physical or emulated device accepts and performs intended configuration | **No; separate device-tested status** |
| **K10 — Genuine Ansible variant certification** | Maintained collection, scoped module semantics, independent contained syntax/check environment | **No; separate output-variant status** |

A binding passing **K0–K7 is authorized for ordinary V9 knowledge publication** even when K8–K10 are NOT RUN or fail to establish external certification, provided that unresolved material risks are clearly disclosed in the approval and no mandatory application security gate fails. A failed K8 means an engineering correctness concern, not an automatic publication-service veto; obtain explicit reviewer resolution of known material conflict and preserve the finding. The UI and result metadata must distinguish `ENGINEER_APPROVED_NOT_INDEPENDENTLY_CERTIFIED` from `VENDOR_VERIFIED` and `DEVICE_TESTED`.

Do not let Codex auto-approve its own template work. Provide efficient batch review UI/API with actual authenticated approval and audit logs. A prior approval may be reused only when it covers the unchanged source/contract hashes and exact version/profile scope. Never fabricate approvals merely to achieve 141/141.

## E3.2 Test quality

- At minimum per combination: representative success, minimum/maximum/boundary values, missing/invalid fields, wrong platform or version, missing preconditions, exact inverse/remove semantics where relevant, and relevant injection/property-based cases. Different conditional branches require separate positive fixtures; one happy path is insufficient.
- Build expected representative output from the **approved engineering specification**, independently of the code under test; do not generate the expected output with the same rendering function. Store the approved expected output and actual diff. Official vendor documentation can be attached for higher certification but is not required for engineer-authorized publication.
- Inspect actual configuration context: Junos hierarchical `set/delete`, VRP process/undo contexts, Cisco interface/router/policy scopes. Make every expected output explicit about whether config mode wrappers are present and which service applies them.
- Contract fixtures must include realistic prerequisites: existing ACL/VLAN/routing process/policy, real interface list and device capability. Do not change R1/R2 vendor/version values to pass tests. Avoid the earlier route-only fixture claiming unsupported IS-IS; construct a compatible declared test profile with recorded interfaces/capabilities.
- Validate no hidden side effects: rendering is pure; no device commands, credentials, unauthorized edits, file saves, model-generated command fallback or SQLite contamination.
- Test both individual operation and multi-operation composition for categories where dependency/order is essential, with exact failure if one sibling is unsupported.
- Keep **native CLI** and **true Ansible variants** separately certified. A YAML wrapper around CLI is not by itself a verified playbook. Native knowledge completion must not be unnecessarily blocked by absent Linux/WSL Ansible, yet the app must not falsely advertise certified Ansible variants.

## E3.3 Scalability and verification independence

Write one **table-driven test harness** that consumes the 141-row ledger, not 141 ad hoc scripts or manually repeated clicks. Generate a persistent case skeleton for each row and fill independently reviewed expected CLI, negative cases and documentation. Group runs by dependency cohort and vendor to keep iteration time bounded. The evaluator must output `PASS`, `FAIL`, `BLOCKED`, or `NOT_RUN` for each gate and never substitute “test file exists” for a pass.

Where a maintained vendor-native parser or a virtual NOS can be used in a controlled sandbox, integrate it as an **additional validator**. A parser cannot establish semantic equivalence alone, and a single CLI grammar version does not certify all firmware versions. For Huawei VRP, declare the reviewer-approved profile and known grammar uncertainty. Do not silently mislabel another vendor's syntax as independent Huawei verification. External authoritative grammar checks are encouraged but not mandatory for engineer-approved publication.

Guard reference-document retrieval against broken links; archive reference identities and concise evidence notes in the repository without copying proprietary manuals wholesale. When vendor documentation is unavailable or ambiguous, record this and seek explicit engineer sign-off on the method. Do not claim `VENDOR_VERIFIED` merely because no error occurred; nevertheless do not block authorized reviewed publication for lack of Internet evidence.

## E3.4 Completion mathematics

Daily progress report by vendor:

| Vendor | Total rows | K0–K4 application-ready | K5 engineer-approved | K6 runtime | K7 ordinary-active | K8 external semantics (separate) | K9 device (separate) | K10 Ansible (separate) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Cisco IOS-XE | 47 | ... | ... | ... | ... | ... | ... | ... | ... |
| Juniper Junos | 47 | ... | ... | ... | ... | ... | ... | ... | ... |
| Huawei VRP | 47 | ... | ... | ... | ... | ... | ... | ... | ... |
| **Total** | **141** | ... | ... | ... | ... | ... | ... | ... | ... |

Never display `141 passed` for K0–K2 only. The final publication goal is **141/141 K0–K7 engineer-approved and runtime-active bindings**. Independent vendor-semantic certification, device testing and Ansible-variant testing are reported alongside publication, not substituted for it. Missing approvals remain transparently pending rather than forged; content conflicts are disclosed to the reviewer for a conscious decision.

**E3 gate:** Each of 141 has reproducible structural/render/runtime checks and its authorized approval record or an explicit awaiting-approval state. K3/K5 independent vendor-document/semantic checks are recommended certification work, not publication blockers after valid senior approval. Physical-device and Ansible certifications remain separate.

---

# E4 — Fix knowledge publication, retrieval readiness and active release consistency

**Goal:** The real runtime must consume newly engineer-approved and technically usable vendor templates, instead of indefinitely using the same ordinary 44/78 release or an offline acceptance candidate.

1. Inspect V9's actual publication/index architecture first: authoring revisions, schema compiler, template binding, manifest, immutable release, release-specific retrieval artifacts, index readiness marker, active release pointer, worker/gateway lifecycle and runtime snapshot caching. The Phase D candidate has `ready:false`; ascertain what the flag actually means and which retrieval methods need it. Do not falsely claim a ready Chroma service if only offline lexical lookup exists.
2. Use existing authoritative `/knowledge/edit`, `/template`, `/validate`, `/render`, `/build`, `/activate` services or their KnowledgeService equivalents. Do not mutate an immutable release, copy isolated acceptance SQLite into ordinary, or rebuild a duplicate vector index. Correct compiler/authoring code defects (including the repaired preview derivation and deadlock) at source, preserving atomicity and revision checks.
3. **Publish through successive senior-engineer-approved and structurally/runtime-validated cohort releases** rather than waiting with all repairs unactivated or forcing an unreviewed 141-row release. Each candidate release includes previous working bindings plus newly approved and structurally validated ones; all existing working bindings must be regression-tested. Ordinary activation requires its own complete scoped gates and an authorized explicit release transition; prior release retained. Staged progress never permits deleting old working bindings without equivalence tests.
4. Before activating any release, verify its actual operation counts and binding identities; category references; schema/profile artifacts; source-to-release immutability and checksums; retrieval/index readiness for configured runtime; allowed platform versions; compatible test device resolution; invalid-value rejection; worker direct rendering and authenticated CogniShield runtime selection. Record release ID and active pointer before/after.
5. After activation, **restart/refresh the correct worker and gateway caches** without disrupting user data. Exercise the exact same operation through: KnowledgeService published manifest → V9 worker → CogniShield Studio review → confirmed native unsaved output. Confirm the output corresponds to the **new** release manifest/hash; stale old bindings must not be reported active.
6. Verify all required operation candidates can be found by the appropriate retrieval path (including published OSPF parameter questions that the real routing benchmark missed); clarify how ordinary published-knowledge Q&A differs from engineering operation generation.
7. For incompatible ordinary Cisco IOS inventory, keep the compatibility rejection. Create explicit authorized **acceptance-only devices** for Cisco IOS-XE 17.9, Junos 23.4 and Huawei VRP 8 with truthful interfaces/capabilities; do not relabel R1/R2 or graft foreign platform onto active inventory.
8. Check partial release resilience: build failure, manifest corruption, index-not-ready, worker timeout, stale active pointer, failed post-activation smoke or cache mismatch must leave or restore a known-good release through existing atomic activation/rollback. Don't attempt ad hoc SQLite replacements or pointer file edits.
9. Maintain a separate `reviewed published candidate` versus `ordinary active release` journal; never use “candidate exists” as a completion verdict.
10. At final completion, prove **47 canonical operations / 141 engineer-approved published and runtime-renderable native bindings** (or disclose individual pending human approvals and structural/runtime failures), with one active ordinary release manifest or documented compatible versioned releases and an explicit active pointer. Write a rollback rehearsal record.

**E4 gate:** At least one newly engineer-approved, structurally/render-validated cohort is demonstrably activated in ordinary runtime; existing working bindings remain intact. Final publication gate is 141 individually approved and renderable combinations active via V9. Missing public documentation or absent device conformance alone never blocks activation; missing human approval or broken core V9/runtime invariants does.

---

# E5 — Independent network-simulator conformance and unlimited scenario *variety* (not unbounded execution)

**Goal:** Complete the Phase D simulation's verification and scenario-authoring gaps so Codex can systematically discover model failures in novel network environments without inventing observations or modifying physical devices.

## E5.1 Preserve centralized authority and editable data

Continue using the existing server-controlled development mode:

```dotenv
COGNISHIELD_DEV_SIMULATION=1
COGNISHIELD_DEV_STATE=tmp/development-network/state.json
```

Document exact current file paths after inspecting the code:

```text
backend/development/scenarios/          # versioned bundled scenarios
backend/development/scenario.schema.json # machine-readable authoring schema
backend/development/network_model.py     # typed modeled network semantics
tmp/development-network/state.json       # selected/editable development state
tmp/phase-d/acceptance-scenario.json     # historical isolated acceptance fixture
docs/development/SCENARIO_AUTHORING.md    # developer guide; verify exact path
```

In **acceptance only**, set the mode to `1`, restart the existing dev composition and use authenticated developer controls. Restore simulation off on ordinary startup after acceptance. Do not allow the chat model, uploaded file, arbitrary tool parameters or browser user code to enable simulation or write real inventory. Never publish scenario-generated facts as real-live telemetry.

## E5.2 Authoring and generated-data workflow

Implement a documented, repeatable CLI and API/GUI path using existing scenario manager:

**Describe → generate structured JSON → schema validate → dependency validate → save new version → select/activate → inspect actual source projections → run prompts → capture actual model/tools/claims → compare independent ground truth → archive results → reset state.**

Require exact names for CLI subcommands derived from the actual source; provide `--help` and copyable PowerShell examples. Validate referential integrity of devices, links, neighbor interfaces, routing table IDs/VRFs, protocol neighbors, ACL attachments, syslog timestamps, telemetry units/source availability and expected path states. Prevent repeated writes if schema invalid or active test users exist without version negotiation.

Crucially, store **expected diagnoses and scoring oracles outside model-visible scenario records**, preferably in the evaluation registry. Test that the LLM cannot read them via tools, documentation/context or error text. Generation should support controlled random seeds and deterministic replay; holdout cases require new names, prefix ranges, vendor combinations and fault mechanisms not copied from examples.

## E5.3 Fill forwarding-model verification gaps

Use independently calculated expected outcomes for:

- Longest-prefix match, multiple same-prefix choices, administrative preference and local/connected route precedence when modeled.
- Recursive next-hop resolution, unreachable next hops, forwarding loops, blackholes, asymmetric return paths, route additions/removals and route-table freshness.
- ECMP path alternatives, one failed branch, different return flow, partial probe scope and route resolution truncation (32 hops, 16 branches). Distinguish `all modeled paths` from `some path` and `unknown due to truncation`.
- VRF isolation, intended route-leaking direction, wrong table selection and leakage policies.
- Ordered stateless ACL permit/deny/default, ingress versus egress, source/destination ports, L4 protocol context, rule-order changes and unset/unknown state. Stateful ACL/firewall, NAT, IPv6, tunnels and policy-based routing must return explicit unsupported/unknown until implemented and independently tested.
- Physical vs logical interfaces and per-vendor route/name parsing; don't silently normalize typoed stored source names into imagined devices.

Use a small independent reference evaluator or double-written test oracle, not assertions produced from `network_model.py` itself. External/lab conformance against a virtual NOS is permitted only with appropriate licensing/authorization and cannot be claimed where no virtual devices ran.

## E5.4 OSPF/BGP and congestion meaningful investigations

For OSPF: valid and invalid router IDs (uniqueness, not forced equality), area mismatch, hello/dead mismatch, authentication discrepancy, passive interface, interface state, 2-Way/DROther legitimacy, MTU uncertainty, DR/BDR nuance, route absence vs neighbor state and stale observations.

For BGP: AS mismatch, Idle/Connect/Active/Established, source/update-source address, peer reachability, TCP 179 reachability evidence when modeled, address-family activation, route acceptance/advertisement, filter/route-policy changes, and `Established` with zero accepted routes. Avoid diagnosing one cause from session state alone.

For congestion: directional utilization, queue drops, errors, reset counters, missing time samples, inconsistent timestamps, service response and independent observer agreement. A high-percent utilization alarm does not prove congestion causation by itself.

Create multi-vendor **mixed Cisco–Junos–VRP** examples with unrelated names and nontrivial topologies, plus healthy, single-fault, multiple-fault, stale, contradictory, unavailable and deceptive symptom controls. Prior three scenarios `MIXED-PATH-001`, `PROTOCOL-MIXED-001`, `PERFORMANCE-MIXED-001` remain regression fixtures; new unseen scenarios must be distinct.

## E5.5 State machine scope and graceful unknowns

Do not claim a complete packet, OSPF, BGP, LACP, TCP, NAT, IPv6, stateful firewall or queueing simulator from typed synthetic observations alone. If a capability is requested but not fully modeled, either integrate a separately verified conformance backend under existing dev-only permissions, or return a precisely scoped **unknown/unsupported** result with relevant observations and suggested decisive checks. The assistant can discuss the theoretical protocol, but it cannot claim simulated proof for unsupported dynamics. Document what is actually modeled, including topology size limits and source freshness.

**E5 gate:** Validated schema/examples and CLI workflow; independently passing healthy/negative/contradictory multi-hop, ACL, VRF, ECMP, OSPF/BGP and congestion cases; scenario source isolation; unseen scenario generation; honest unknown behavior; no ordinary data contamination.

---
# E6 — General-purpose intent understanding and adaptive, authorized tool orchestration

**Goal:** Deliver the intended **understand intent → resolve scope → select useful tools → interpret evidence → decide whether additional reads help → verify → explain** pipeline for unfamiliar, compound and follow-up requests, without trusting small-model action parameters or granting new permissions.

## E6.1 Reproduce and repair specific Phase D mistakes first

1. Preserve Phase D failed examples verbatim as regressions: published OSPF requirements question omitted `knowledge.search`; recorded-topology paraphrase selected inventory instead of topology; `Core-Birch` / `Edge-Cedar` explicit names wrongly filtered as roles; classifier selected nonexistent attachment mode; compound investigation had relevant readers but invalid answer; additional-read trial requested nothing useful. The two device/attachment bugs were already fixed, so verify their regressions instead of reimplementing the same guards.
2. Build a **source-capability equivalence map**: one reader may internally resolve inventory identities while fetching topology; the rubric must not demand a redundant `inventory.read` call if equivalent authorized facts were obtained. General conceptual questions do not require live-network reads. Review a reader's scope, evidence and fulfilled information need, not only exact tool-set equality.
3. Fix contextual benchmark setup: a follow-up about a previous proposal or investigation must be preceded by an actual authorized prior turn containing corresponding results. Missing setup is a test-fixture failure, not an automatic AI failure. Recheck tool authorization separately from routing prediction—denied proposed tool is not evidence of a successful unauthorized execution.
4. Retain original 52 exposed regression cases and their historic scores unchanged. Create **new fresh holdouts** after rubric correction; don't rename exposed cases “holdout” or optimize to test IDs/fixtures.

## E6.2 Typed intent representation, not a single rigid classifier

Handle multiple simultaneously active intents with priority/order and source constraints:

- General greeting, arithmetic, explanation and conceptual networking.
- Read/uploaded-document summarization, selected pages, OCR uncertainty, current attachment ownership.
- Inventory, planned topology, observed topology and actual interface references.
- Current running configuration (only if an active authorized source is available), stored backup and historical diff.
- Time-scoped live/simulated/stored telemetry, syslogs, incident/anomaly history.
- Multi-source causal diagnosis, competing hypotheses, contradictions and further evidence decisions.
- Published V9 operation requirements and legitimate configuration creation/removal.
- Current unsaved Monaco buffer explanation, selected code, exact-base edit proposal, proposal correction and previous-diff explanation.
- Compound conversation + network question; document + network investigation; config compare + edit proposal, with permission-bound subtask separation.

Record typed `intent_goals`, `entities`, `source_requirements`, `temporal_scope`, `preferred_response`, `allowed_effect`, `confidence`, `information_gaps`, and `required_clarification`. One user request can legitimately contain several information requirements. The general language model proposes a plan; the **server** validates tools, entity identities, provider availability, allowed surfaces, source modes and side effects.

Keep the existing semantic embedding/structured classifier and narrow, demonstrably useful high-confidence guards. A model cannot create a tool from a string, assume access to an unavailable document, manufacture an interface, infer privilege from phrasing, or choose V9 template syntax directly. V9 still selects engineering operation/schema/vendor compatibility; the general LLM routes to `v9.preview` only under approved Studio review.

## E6.3 Tool sufficiency and graph scheduling

Maintain a capability catalog referencing existing LangChain `StructuredTool` → server-owned `ToolRegistry.invoke` adapters, with typed schemas, auth, source mode, context/freshness, time range, effect and error classification. Add a thin adapter only for a genuinely missing capability; no raw shell, unmediated SQL, open URL fetch, device SSH or alternate RAG.

The planner should decide whether a request needs zero readers, one reader, several concurrent independent readers, a follow-up query or user clarification. Do not force an inventory sweep for a greeting or an unrelated document query. Order dependent reads (resolve device → fetch its interface/protocol state; retrieve prior backup → calculate diff). Allow selective authorized **additional** reads when they can distinguish competing hypotheses, and avoid repeatedly querying the same unavailable reader in one turn.

Current three-model-call / eight-tool / 120-second ceilings were carried forward in Phase D. Measure the execution profile and replace a rigid three-call blanket with **bounded per-stage budgets** for classification, planning/refinement and synthesis, a strict shared token/cost/time cap, cancellation and deduplication. Concurrency only where safe; never turn the graph into an unbounded loop. Preserve B3/Phase C deterministic success for exact lookups and no unnecessary model latency.

Improve failures gracefully:

| Failure | User-visible and orchestration behavior |
|---|---|
| Unknown/ambiguous device or pronoun | Focused clarification listing authorized candidates; never guess a target. |
| Wrong platform/profile or absent V9 binding | Precise compatibility/knowledge-coverage result; optional reviewed next step, no CLI hallucination. |
| Missing current configuration collector | State **current unavailable**; offer properly labeled stored snapshot if appropriate, never substitute silently. |
| Syslog/telemetry missing/stale | Preserve unavailability/time scope; don't infer healthy/faulty. |
| Conflicting measurements | Present disagreement, origin and decisive follow-up checks; no fabricated consensus. |
| Missing uploaded document or OCR diagram text | Request source/reselect file; describe partial coverage, don't pretend spatial/diagram understanding. |
| Invalid model plan or tool args | Reject, retry only within bounded stage and authorized schema; otherwise safe correct baseline. |
| Model timeout/provider disconnect | Return verified partial facts/status and user follow-up, not success claim. |
| Graph budget exhaustion | Return verified partial answer and explicit unread sources/limits; no infinite loop. |
| Stale revision while investigating | Re-read authorized source where possible, identify new epoch, revalidate later action. |
| Denied document or capability | Refuse action with scoped authorization explanation, no suggested bypass. |
| Studio edit disagreement/stale base | Discard proposal, request refreshed diff/review; never autoapply old patch. |
| V9 mixed-task incomplete | Preserve all tasks and clarify/stop the entire generation; never drop unsupported siblings silently. |

## E6.4 Model independence and routing metrics

Use `qwen2.5:1.5b` to test actual class/plan/tool proposal quality and capture model-decision metadata, separately from deterministic decisions. Do not assume the model is capable because it advertises tool support; earlier native tool output used incorrect argument keys. Implement strict typed schema and source/effect validation, and exercise malformed/refused/offline/provider-unsupported cases.

Create a sealed **fresh holdout** split large and diverse enough to avoid interpreting 6/8 as proof: target at least **60 unfamiliar independent prompts**, stratified across general/document/network/engineering/compound/adversarial no-effect classes, with new device names, vendors and topology. Reserve some for multi-turn trajectories requiring real preceding state. Predeclare scoring methods, equivalence classes, confidence bounds and target prior to running; avoid repeatedly tuning against a supposedly untouched set.

Target **≥90% correct authorized information-need fulfillment / intent routing** on that stratified fresh benchmark, with no critical unauthorized write and no meaningful regression in exact-value accuracy. Report both micro and per-class macro measures, errors and CI, plus cost/latency under a matched baseline. Do not hide one class's failures behind hundreds of easy greetings.

**E6 gate:** The genuinely new planner fulfills sources/intents more reliably than B3 on untouched representative tasks or explicitly remains disabled; known Phase D errors are corrected; all permissions and source provenance remain enforced. Passing this gate is not a claim that arbitrary language is always understood.

---

# E7 — Improve actual qwen reasoning, adaptive evidence decisions and answer synthesis

**Goal:** Convert accurate source retrieval into concise, insightful, correct answers that address the user's problem. Validate independent model contributions instead of hiding failure beneath deterministic fallback.

## E7.1 Explicit M0/M1/M2/M3 evaluation arms

Evaluate the **same network facts and user task**, using independently defined expected answers, across:

- **M0 — model only:** no application investigation tools. Tests basic language comprehension, conceptual networking, hypotheses and request recognition; cannot claim current network facts.
- **M1 — model + fixed evidence:** model receives verified, bounded facts selected by evaluator, not live tools; tests evidence interpretation, AS/OSPF semantics, causal qualification, reconciliation and accurate prose.
- **M2 — full LangGraph agent:** model may propose typed goals/tools and conditional additional reads, server enforces auth; tested end-to-end through real gateway using existing data reader tools.
- **M3 — existing deterministic assessor/B3 fallback:** exact source facts, verified calculations and safe bounded conclusions without crediting an LLM for model reasoning. This is a correctness baseline, not an inferior alternative to be deleted.

Each run must capture provider name/version, actual model ID, prompt/context snippets with sensitive content removed, source epoch, tool calls/returns, planning decisions, inference count, rejected first answer, accepted/withheld answer, wall time, token/resource measures if available and failure category. Distinguish model-generated content from server-rendered exact records.

## E7.2 Address observed reasoning failures

- OSPF router IDs are expected to be **unique**, not identical; assess address uniqueness, adjacency and area/timers separately. Test conflicting neighbor IDs and healthy distinct router IDs.
- A route must not be claimed unless present in the authorized routing facts or explicitly stated as a *hypothetical*. Factual verification covers exact destination/next-hop/VRF and timing, not only citation presence.
- `BGP Established` does not imply usable routes; `OSPF Full` does not imply end-to-end forwarding; no telemetry does not mean no failure; a stored capture does not equal a current running config.
- Avoid overclaiming all network paths healthy from one probe or a narrow simulated record. Distinguish configuration discrepancy, operational observation, correlated symptom, hypothesis and confirmed cause.
- When data sources conflict, the model must identify the disagreement and request useful disambiguating evidence rather than output both facts as though consistent.
- Unsupported physical/real-time claims must be caught by post-synthesis verification; keep model's natural explanatory structure rather than reverting to raw record dumps when a repairable sentence is wrong.
- Correct uncited prose, internal source hashes and repetitive tool dumps. Evidence citations should be human readable yet trace back to exact owner-authorized records.

## E7.3 Natural answer-generation contract

Default answer quality is **question-first and evidence-grounded**, not mechanically templated. For a short question, give a short answer. For a difficult investigation, generally cover:

1. The direct answer or current best-supported finding.
2. The most relevant verified facts and why they matter to the user's engineering question.
3. Likely causes versus alternatives, with appropriate certainty and their basis.
4. What was actually checked and which information is missing/stale/unavailable.
5. A targeted next diagnostic check or safe reviewed edit when warranted.
6. Optional expandable detailed records and citations—don't lead with raw JSON.

Do not force fixed phrases such as “Based on what I learned” or claim private thought, verification or measurements that did not happen. Do not treat fluent text, verbosity, Markdown or a plausible summary as evidence of technical correctness. When user explicitly requests full raw output, supply it with correct provenance and no lossy summary substitution.

Use the existing `orchestration/synthesis.py` with evidence pack: typed immutable source facts, user goal and scope, causal facts verified deterministically, hypotheses tagged inference, availability/truncation status, relevant published contract and source labels. Keep credentials, opaque permission IDs, test oracles and unpublished drafts out of LLM context. Apply post-generation factual validation with targeted correction/repair or final safe fallback; record the difference and reason.

## E7.4 Adaptive investigation tests

Create cases where additional data **changes the answer**, not just increases call count:

- Ambiguous route failure; inspect exact next-hop/return route/VRF and discriminate alternative causes.
- OSPF neighbor Down with contradictory configuration vs state; check timer/area/auth and freshness.
- BGP Idle with multiple potential causes; decide on peer reachability, AS and state sources; do not make a single-cause assertion without evidence.
- Packet loss after configuration changes with telemetry and syslog gaps; retrieve historical change and compare timestamps without inventing a live reading.
- Topology mismatch between planned and observed paths; distinguish them explicitly.
- Multi-vendor QoS/classifier/policy symptoms requiring actual vendor-specific configuration context.

For each, verify the model's **chosen next information need and whether that decision improved the final answer**. A model decision selecting no extra reader when useful evidence remains should be scored accordingly, not credited merely for consuming one inference call.

## E7.5 Benchmarks and policy for enabling features

Target at least **85% answer adequacy** on a blinded, case-independent sample, with domain-expert rubric for correctness, relevance, causal qualification, evidence citations, completeness and usability. Use rubric items that penalize fabricated routes/protocol semantics severely; unauthorized actions and unsafe invented config are critical failures. Human or independent blinded evaluation is preferred; an LLM judging itself is not an independent truth oracle.

Compare matched baseline/candidate with the same factual sources, measured time budget and model. Re-run with several independent seeds/replicates for small model instability; preserve failure traces. Publish per-class results rather than aggregate alone. Flag unacceptable overhead (e.g. fourfold latency without improved success) as a failure to address through caching/budget/fast deterministic routing—not an automatic reason to add more inference calls.

Keep `COGNISHIELD_AI_PLANNING` and `COGNISHIELD_AI_SYNTHESIS` **off by default** until predeclared 90% routing / 85% adequacy gates and factual safety regressions pass. Enable incrementally in controlled simulation/evaluator, then rollout behind server flags. If `qwen2.5:1.5b` cannot meet the gates despite improvements, **report that model limitation**; do not lower thresholds, fake performance or silently replace with deterministic records and declare model success. An optional stronger installed model can be benchmarked through the existing Ollama/provider adapter **only with separate user approval for model download/activation**.

**E7 gate:** Demonstrated genuine improvement in M1/M2 reasoning and user-facing adequate answers, with measured safety/latency and independent evaluation. Defaults change only after passing the relevant gates.

---

# E8 — Ansible Studio engineering quality and genuine playbook validation

**Goal:** Make the newly published native knowledge truly useful in Studio while addressing the separate, previously excluded verified Ansible-playbook path.

## E8.1 Preserve authoritative split

- Studio selects engineering intent, current Monaco snapshot/selection and source/document attachments through the shared gateway and graph.
- V9 retains category/operation, parameters, schema, vendor, target, source revision and template/render authority.
- Exact address substitutions may use a deterministic guarded patch; open-ended edits may be model-assisted, but all changes use current-document identity, anchors, revision, lock and diff review. Reject malformed/unsupported suggestions rather than quietly editing adjacent code.
- One engineer-reviewed native output per operation/device binding; compound tasks never silently drop an invalid sibling. No automatic confirmation or Save.
- Floating remains read-only; **Review in Ansible Studio** explicitly transports authorized evidence to a separate **unsent** Studio draft after freshness/ownership checks.

## E8.2 Extend mixed-vendor Studio E2E tests

Create compatible acceptance-only Cisco IOS-XE, Junos and VRP devices and test all 47 canonical operations, with samples from every vendor in the UI/HTTP boundary (full 141 through API harness). Include missing parameters, vendor correction, target/interface invalidation, stale release, unsupported profile, multi-operation dependencies, document context switching, parent instruction with exclusions (“change BGP but not OSPF”), exact-base modification and corrupted model output. Confirm actual buffer remains unsaved until engineer takes explicit actions.

## E8.3 Genuine Ansible variants (separate certification)

Phase D reports **no published genuine playbook variants and no proven contained Ansible worker**. Address this as a separate optional/output-mode deliverable:

1. Inventory existing playbook variant abstractions, FQCN/module requirements, dependency pins and combined-YAML validator. Do not treat a mocked validator as contained validation.
2. Establish a genuinely contained, reproducible Ansible validation environment suitable for the host (on Windows this may require a user-approved WSL/Linux container or equivalent); document its permissions, isolation and what was actually executed. Do not automatically install large dependencies or device-facing drivers without authorization.
3. Use maintained collections/modules for supported IOS-XE, Junos and Huawei variants. Verify actual provider collection availability and module semantics; if VRP lacks supported maintained tooling for a particular operation, keep verified **native CLI** as the usable output and mark **genuine Ansible variant unavailable**. Don't claim that native and playbook are equivalent.
4. Validate YAML, dependencies, host targeting, task order, idempotency intent, variable quoting, schema and `ansible-playbook --syntax-check` and/or appropriate contained dry-run where safe and available. Never execute against physical devices without separate authorization.
5. Publish certified playbook variants through existing V9 variants only if the supported schema and runtime can actually select them. Unsupported playbook variants should not block native operation coverage, but must remain clearly labeled, not “all Ansible supported.”

**E8 gate:** Native generation and guarded editing work end-to-end on the new active vendor bindings. Playbook capability has honest, independent conformance and availability labels; no unsafe remote action.

---
# E9 — Finish UI/browser, clipboard, normal-mode adapters, document and resilience acceptance

**Goal:** Eliminate or precisely classify the remaining visible weaknesses instead of treating unit tests as browser proof.

## E9.1 Browser Copy and presentation

Phase D observed: Copy button clicked, browser Clipboard API promise resolved, UI displayed `Copied`, yet Work/browser automation's virtual clipboard returned empty and paste failed. **This alone does not prove the actual application Copy is broken.**

1. Reproduce in the same browser and in a standard nonvirtual browser session if available, with permission/environment metadata (secure context, Clipboard API, active focus, document visibility). Inspect actual Markdown/code selection and `navigator.clipboard.writeText` result and the host virtual clipboard bridge separately.
2. Add deterministic utility tests for exact Unicode/CRLF/Markdown fenced code bytes and `writeText` resolve/reject paths. Check multiple answers, clarification/error replies, zero-length replies, tables, nested code fences, source descriptions, light/dark themes, narrow-screen and screen-reader announcements.
3. Verify visual UI uses the same original Markdown payload rather than DOM-copied buttons, timestamps and collapsed source metadata. Preserve distinct whole-answer Copy and per-code-block Copy.
4. If standard browser clipboard succeeds but automation virtualization fails, keep UI acceptance **environment-blocked** with a documented reproducible manual paste procedure; do not mark product defect or product acceptance proven by unit tests. If Clipboard API itself fails, report truthful failure and offer a user-initiated select-and-copy fallback; no fictitious `Copied` state.
5. Preserve existing Monaco static lexer/colors in light and night, safe escaped tokens, no raw user HTML/script, no extra editor instances and CSS responsiveness. Normal-mode Floating must use the same renderer, not its historical older one.

## E9.2 External/ordinary mode parity and actual data sources

Inspect normal-mode (external-service) frontend/backends and adapters, not only local-lab `SharedInventoryChat`.

Test normal-mode UI with **controlled authenticated provider substitutes** where real remote sources are unavailable, plus actual integrations only when configured and authorized. Verify request contracts, errors, correct link/device identities, source freshness, model/provider unavailable statuses, and format parity with local-lab. Do not invent connected InfluxDB, OpenDaylight, NetBox/SoT, syslog or current running config readings. Default remote/live toggles remain off until user configures sources and grants permissions.

Test: planned vs observed topology, stored snapshot vs live current config, real vs simulated syslogs, zero measurements vs collector failure, invalid time range, disconnected collector, partial pagination and stale data, config capture ownership, untrusted document injection and mixed-mode leakage.

## E9.3 Document, vision and file-context degradation

The existing Windows OCR pipeline handles images and PDFs with resource bounds; 11-page reference document yielded text but spatial diagram semantics remain unverified. Ensure relevant actual extracted pages are used; OCR-layout/diagram uncertainty is honest, no random page injection or fake spatial relationships. Do not treat `LightOnOCR` timeout or an installed OCR model's advertised vision label as proof of diagram reasoning. Vision may be tested only with an actually configured capable model, appropriate data security and independent diagram interpretation cases; absence yields a useful bounded answer with coverage caveat.

Studio must preserve unsaved Monaco text, current selection, document version, user edits and source lines, while general conversation omits irrelevant code. No client-supplied model-generated evidence becomes an authoritative network fact.

## E9.4 Handoff and editing acceptance

Retain the contextual **Review in Ansible Studio** action. It appears only for eligible, authorized evidence-bearing replies; no persistent “Preparing Engineering Handoff” form. Test stale inventory epoch, changed configuration, deleted source, unauthorized other-owner evidence, idempotent accept, canceled async, focus restoration, Escape, pointer/keyboard and separate unsent Studio composer. Verify **zero automatic submitted turns, Monaco edits, saves or device actions** on handoff. Preserve exact-base revision and Accept/Reject/Undo/Save separation during subsequent Studio requests.

## E9.5 Windows/runtime recovery

Preserve standard ports **5173 / 8000**, existing Windows `run_local.ps1`, Ollama 11434 service selection and no random alternates. Distinguish listening-port errors, Windows excluded range permission, OneDrive filesystem sandbox, Python child-process ownership, uvicorn reload/CTRL-C propagation, frontend HMR reconnect and browser settings. Stop only processes started by the harness. Avoid unnecessary dependency downloads, model installs and temporary competing servers. Recover from provider outage by reporting `unavailable` without creating new network facts.

**E9 gate:** Shared UI rendering and clipboard result are truthfully verified or independently classified as a known automation blocker; normal-mode adapters exercised; handoff and reviewed Studio actions pass browser/API; no data/authorization leakage; frontend TypeScript and production build pass.

---

# E10 — Full-system regression, publication convergence and release handover

## E10.1 Exit gates (none can be waived by a passing unrelated test)

| Gate ID | Must demonstrate | What does **not** count |
|---|---|---|
| **G-0 Preservation** | Original 52-file staged index unchanged, user data and SQLite integrity checked, any legitimate test changes isolated and audited | Silently resetting worktree or restoring DB over new conversations. |
| **G-1 Candidate coverage** | Exactly 141 candidate IDs, 47 operations × 3 vendors; all have complete native remediation status and supporting evidence | Jinja parse or reference file count alone. |
| **G-2 Engineer-approved publication readiness** | 141 explicit authorized engineer approvals tied to content hashes/profiles, successful V9 structural/render/negative-input and runtime tests; independent semantics tracked separately | 11 narrow fixtures, 78 inherited bindings, missing approvals, compile errors or documentation alone. |
| **G-3 Publication** | New immutable release(s) created through V9 and **ordinary active final catalog** proven through V9 worker/API/UI; safe rollback | Acceptance-only candidate with `ready:false` or stale normal release pointer. |
| **G-4 Simulator** | Editable versioned mock data, scenario generation/replay, independent conformance for routing/ACL/VRF/ECMP/OSPF/BGP/congestion, unknowns disclosed | Simulated outputs that self-grade without independent expectation. |
| **G-5 Intent** | Fresh stratified routing/information-need fulfillment ≥90%, correct effect scope and no critical unauthorized tool calls | Exposed 52-case scores, a single 6/8 run, or a judge that requires redundant reads. |
| **G-6 Reasoning/answers** | Blinded answer adequacy ≥85%, faithful AS/OSPF/routes/status claims, independent M0–M3 comparison and measured adaptive gains | Tool calls alone, safe deterministic fallback counted as model reasoning, or fluent but hallucinated prose. |
| **G-7 Studio safety** | Reviewed edits, V9 multi-operation/clarification, actual active bindings, unsaved preview, correct handoff ownership and stale revision rejection | Proposal text placed into editor/saved/deployed automatically. |
| **G-8 UI parity** | Browser tests for both assistants, modes and accessibility; Copy honestly proven or environment blocker separately documented | Unit clipboard test labeled as full browser round trip. |
| **G-9 Real-world claims** | Device/emulator validation only when actually performed; live sources only when connected; genuine Ansible variants independently certified | Synthetic telemetry labeled live; native CLI called verified Ansible; lab syntax called device-tested. |
| **G-10 Regressions** | Current 121 methods/34 subtests and all newly affected tests pass; retained Phase C/B2/B3 authorization and memory checks, TypeScript/build | Adding historic reruns as new unique passes or deleting failing assertions. |

An implementation can be **partially useful** while a gate remains blocked. The absence of Internet verification alone is **not** such a publication blocker. However, do **not declare Phase E complete** until the mandatory gates truly pass. A documented hard blocker is valuable and honest, not permission to fake missing native syntax or alter user inventory to pass tests.

## E10.2 End-to-end acceptance journeys

**Journey A — ordinary factual lookup and follow-ups:** User asks what interfaces a specific stored router has, asks for first address, switches to a different router, asks “Are you sure?”, then asks an unrelated arithmetic question. Assert exact current stored values, correct references, fresh reread when appropriate and no leaked prior context.

**Journey B — unfamiliar multi-source diagnosis:** New mixed-vendor scenario includes a route omission and stale telemetry with misleading syslog. User asks a broad, unfamiliar problem statement, then requests cross-checks. Assert correct tool selection, explicit evidence gaps, useful additional observations when available and qualified root-cause explanation. Compare M2 to B3 and M3.

**Journey C — new native vendor bindings:** One Cisco IOS-XE, one Junos and one Huawei compatible declared target; pick representative engineer-approved operations from each E2 cohort. Ask with paraphrases, correct targets and parameters, confirm, render and open unsaved Monaco document. Assert active new immutable release identity, exact binding/template hash, expected engineer-approved rendering and visible trust status; independently vendor-verified output is a separately scored certification. Repeat the table-driven API ladder for all 141 combinations.

**Journey D — cascading correction:** Ask interface configuration on R2, correct to R1, retain independent description, invalidate incompatible former interface, request actual matching interface and use only proper profile binding. Correct operation/vendor mid-review; avoid stale constraints and dropped sibling tasks.

**Journey E — guarded Studio edit:** Explain unsaved BGP/OSPF, modify exactly one valid address, reject once, accept once, Undo, do not Save; assert exact source revisions, unrelated code preservation and no network action. Repeat with ambiguous anchor, malformed model patch, stale source and unauthorized owner.

**Journey F — reviewed handoff:** Floating investigates, contextual Review in Studio → recheck ownership/revision → explicit review/accept → separate unsent Studio draft. Assert original Floating remains read-only and no generated config or editor edit occurs automatically.

**Journey G — failure classification:** Missing collector, unavailable current config, stale backup, OCR-only PDF, unsupported native profile, denied tool, model timeout, budget exhaustion and browser clipboard virtualization. Every response must correctly distinguish unsupported, unavailable, incomplete and unauthorized without a fabricated successful answer.

**Journey H — knowledge release rollback:** Activate engineer-approved structurally/runtime-validated candidate with existing publisher, confirm old/new outputs, artificially induce a controlled worker/cache/manifest failure in acceptance only, restore known-good pointer with authorized mechanism, verify every worker and API uses rollback revision; avoid DB copy.

**Journey I — externally connected-mode contract:** Exercise normal remote-service frontend with controlled external adapters and actual configured sources when authorized; compare safe formatting, source provenance and errors with local-lab mode. Never claim tested physical connectivity when only stubs ran.

**Journey J — genuine Ansible availability:** For at least a validated representative vendor operation, verify a real contained Ansible syntax/build if environment supports it. For unsupported vendor modules, the UI must offer certified native CLI clearly separated from unverified playbook variants; do not claim all playbooks are available.

## E10.3 Durable deliverables and run logs

At each end-of-cohort checkpoint append, without overwriting original failures:

- Code diff summary, affected modules, repaired operations/vendors and changed contract/schema IDs.
- New candidate and ordinary release IDs, manifest hashes and pointer changes; rollback rehearsal result.
- Delta coverage counts by engineer-approved publication readiness, optional K3/K5 independent semantic certification, published, ordinary active, physical device test and Ansible variant (always separate).
- Exact tests and CLI commands executed, case IDs, actual expected/observed native configurations, model decisions, tool traces and benchmark measures.
- Scenario definitions/revisions/oracles, source origins/timestamps and performance limits.
- User-visible response examples with requested question, relevant evidence and correctness review.
- Browser screenshots/DOMs and clipboard API/automation environmental classification.
- Git staged-patch hash, isolated DB integrity and ordinary record-diff audit.
- Unresolved failures ordered by root cause, owner and a concrete next command, not a vague list.

Update `docs/evaluations/PHASE_E_RESULTS.md`, `phase_e_vendor_progress.json`, `phase_e_cases.json`, `docs/UI_RESTORATION_HANDOVER.md` and a concise final `PHASE_E_RELEASE_AND_RUNTIME_REPORT.md`. Keep raw data under ignored `tmp/phase-e/`, sanitized version-controlled specs only, no secrets/tokens/credential lines. Report unique test methods separately from subtests and reruns.

## E10.4 Efficient execution and Codex resumption behavior

This is a large multi-session engineering program. **Do not throw every task into an unchecked single change**. Execute dependency-bounded cohorts, test and checkpoint after each. If context/quota/process limits interrupt, leave a machine-readable manifest of the exact next candidate IDs and failed validation, current source hashes, current authoring revision, last passing release pointer and safe resumption command. On resume, inspect current filesystem/working tree and artifacts; continue unfinished rows, not re-audit 141 from zero.

Avoid adding another plan without code. Avoid repetitive model calls for simple static checks. Reuse per-vendor family fixtures and batch independent tests. On failure, fix the underlying contract/source/rubric, rerun a focused case, then perform affected regression and release gate. Never weaken assertions, overwrite failed logs or auto-commit staged and unstaged work.

Stop/ask only when an external physical-device command, new credential/permission, potentially destructive data mutation, unapproved model installation or user-controlled change beyond the authorized scope is genuinely needed. Validated V9 knowledge authoring, publication and activation through the existing API are explicitly authorized when the actual user has the required role and the binding has auditable senior-engineer approval, subject to the structural, authorization, renderer and immutable-release gates above; **not** mandatory external semantic/Internet evidence.

---

# Failure-to-remediation index: Phase D issue → Phase E owner and acceptance

| Recorded Phase D limitation/failure | Required repair/verification | Primary stage |
|---|---|---|
| 141 candidates, 0 independent semantic certifications | Complete revised K0–K7 engineer approval + core software validation for publication; independent vendor certification optional | E1–E3 |
| 63 not bound in ordinary release | Actual operation schema/authoring and vendor bindings through KnowledgeService | E1–E2 |
| Only 11 candidate runtime passes | Full 141 V9 finalization, runtime, compatibility, negative tests | E3 |
| Candidate 47/81 still offline | Verify index/retrieval readiness, publish and atomically activate new validated knowledge | E4 |
| Cisco/VRP static-route CIDR defect | Preserve add/remove prefix+mask repairs and test ordinary post-publication runtime | E2–E4 |
| Junos VLAN requires actual name | Validated ID↔name resolution/clarification; no invented names | E2 |
| Junos IS-IS needs logical family/NET; Huawei numeric process | Profile-specific contracts, preconditions, attachment semantics | E2 |
| ACL/QoS/LACP/AAA draft unbound inputs | Native vendor-specific context/parameters/dependencies and semantic review | E2–E3 |
| Unverified true Ansible variants and no contained validator | Separate authentic Ansible collection/toolchain certification and native/variant status | E8 |
| Simulator is bounded synthetic evidence | Independent scenario conformance, proper unknown/truncated behavior; dev-only generator | E5 |
| Protocol and congestion causation not certified | Diverse reviewed state/metrics cases, alternate hypotheses and decisive probes | E5/E7 |
| Wrong Core-Birch role/name filter; missing attachment mode | Preserve fixes and add fresh routing regressions; no unavailable tools | E6 |
| Topology paraphrase + OSPF knowledge source misroutes | Repair intent→information need mapping and true published knowledge retrieval | E6 |
| 52-case rubric errors and exposed “holdouts” | Correct equivalence/fixtures separately; create new untouched holdout suite | E6 |
| Fresh 6/8 unchanged with longer latency | Meaningful model routing improvement/cost cap and confidence/error analysis | E6–E7 |
| OSPF router IDs wrongly said equal | Model/domain explanation verification + explicit contrary healthy cases | E7 |
| Invented route/unsupported all-healthy claims | Immutable source cross-check, causal qualification and targeted repair | E7 |
| Adaptive agent chose no follow-up read | Scenarios where useful additional data is necessary and scored | E6–E7 |
| 85% answer adequacy not measured | Independently graded factual, relevant, clear final answers | E7 |
| Planning/synthesis feature flags off | Controlled rollout only after proper safety/quality gates | E7 |
| Clipboard automation virtual buffer empty | Distinguish app Clipboard API from host bridge, real paste/manual check, truthful status | E9 |
| Normal external-mode browser parity untested | Actual normal-mode frontend with controlled provider contracts/real optional sources | E9 |
| OCR layout/vision limits | Preserve OCR uncertainty; separately evaluate vision only when actual capable model available | E9 |
| Handoff UX/ownership stale-state | Browser tests for contextual review, source revision and unsent draft | E9 |
| Windows process/OneDrive/ports | Stable single acceptance launcher, error diagnostics, owned process cleanup | E0/E9 |
| Ordinary `ansible_chat_sessions` hash discrepancy | Preserve evidence, collect row-level before-images going forward; no blind restore | E0/E10 |
| Previously published 78 bindings lack new certification | Confirm existing binding identity/rendering; reuse valid prior senior approvals where applicable, and record optional certification separately | E3 |

---

# Appendix A — Immutable Phase D 141-row worklist snapshot

This appendix was generated directly from the user-provided `phase_d_vendor_coverage.json` (2026-10-18). It is a **baseline**, not a statement that these rows have passed Phase E. Codex must read the corresponding full JSON row and current checkout before modifying code; all full `findings`, variables, profiles, sha256 and artifact IDs remain authoritative in the JSON. Preserve this snapshot while updating the new Phase E progress ledger.

**Baseline legend:** `P` = a **narrow acceptance native-runtime fixture passed** (not independent semantic certification); `A` = an **existing ordinary published binding**, not newly engineer-review/render certified; `U` = **ordinary runtime binding unavailable**. Every row needs the revised K0–K7 engineer-review publication ladder. Independent vendor-document/device certifications (K8–K10) are optional. A blank issue means no known static finding, not vendor certification.

| # | Operation | Vendor | Baseline | First recorded gap / next focus |
|---:|---|---|:---:|---|
| 1 | `add_acl_rule` | Cisco IOS-XE | **A** | No specific static finding; independent vendor semantics still unverified |
| 2 | `add_acl_rule` | Juniper Junos | **U** | Unbound reference inputs: acl_action, acl_name, acl_rule_id, destination_port, destination_prefix, ip_protocol, source_port, source_prefix |
| 3 | `add_acl_rule` | Huawei VRP | **U** | Unbound reference inputs: acl_action, acl_destination_address, acl_destination_wildcard, acl_name, acl_rule_id, destination_port, ip_protocol,… |
| 4 | `add_default_route` | Cisco IOS-XE | **A** | No specific static finding; independent vendor semantics still unverified |
| 5 | `add_default_route` | Juniper Junos | **A** | No specific static finding; independent vendor semantics still unverified |
| 6 | `add_default_route` | Huawei VRP | **U** | Unbound reference inputs: next_hop, preference |
| 7 | `add_floating_static_route` | Cisco IOS-XE | **A** | No specific static finding; independent vendor semantics still unverified |
| 8 | `add_floating_static_route` | Juniper Junos | **A** | No specific static finding; independent vendor semantics still unverified |
| 9 | `add_floating_static_route` | Huawei VRP | **U** | Unbound reference inputs: destination_address, destination_netmask, next_hop, preference |
| 10 | `advertise_network` | Cisco IOS-XE | **A** | No specific static finding; independent vendor semantics still unverified |
| 11 | `advertise_network` | Juniper Junos | **U** | Unbound reference inputs: area, ospf_interface |
| 12 | `advertise_network` | Huawei VRP | **U** | Unbound reference inputs: area, network_address, network_wildcard, process_id |
| 13 | `apply_acl_to_interface` | Cisco IOS-XE | **A** | No specific static finding; independent vendor semantics still unverified |
| 14 | `apply_acl_to_interface` | Juniper Junos | **U** | Unbound reference inputs: acl_name, direction, interface |
| 15 | `apply_acl_to_interface` | Huawei VRP | **U** | Unbound reference inputs: acl_name, direction, interface |
| 16 | `apply_qos_policy_to_interface` | Cisco IOS-XE | **A** | No specific static finding; independent vendor semantics still unverified |
| 17 | `apply_qos_policy_to_interface` | Juniper Junos | **U** | Unbound reference inputs: interface, policy_name |
| 18 | `apply_qos_policy_to_interface` | Huawei VRP | **U** | Unbound reference inputs: direction, interface, policy_name |
| 19 | `assign_interface_to_ospf_area` | Cisco IOS-XE | **A** | No specific static finding; independent vendor semantics still unverified |
| 20 | `assign_interface_to_ospf_area` | Juniper Junos | **U** | Unbound reference inputs: area, interface |
| 21 | `assign_interface_to_ospf_area` | Huawei VRP | **U** | Unbound reference inputs: area, interface, process_id |
| 22 | `assign_vlan_to_trunk_port` | Cisco IOS-XE | **A** | No specific static finding; independent vendor semantics still unverified |
| 23 | `assign_vlan_to_trunk_port` | Juniper Junos | **A** | No specific static finding; independent vendor semantics still unverified |
| 24 | `assign_vlan_to_trunk_port` | Huawei VRP | **A** | No specific static finding; independent vendor semantics still unverified |
| 25 | `classify_by_dscp` | Cisco IOS-XE | **A** | No specific static finding; independent vendor semantics still unverified |
| 26 | `classify_by_dscp` | Juniper Junos | **U** | Unbound reference inputs: classifier_name, dscp_values, forwarding_class, previous_dscp_values |
| 27 | `classify_by_dscp` | Huawei VRP | **U** | Unbound reference inputs: classifier_name, dscp_values, previous_dscp_values |
| 28 | `configure_access_port` | Cisco IOS-XE | **A** | No specific static finding; independent vendor semantics still unverified |
| 29 | `configure_access_port` | Juniper Junos | **U** | Unbound reference inputs: interface, vlan_id |
| 30 | `configure_access_port` | Huawei VRP | **U** | Unbound reference inputs: interface, vlan_id |
| 31 | `configure_bgp_neighbor` | Cisco IOS-XE | **A** | No specific static finding; independent vendor semantics still unverified |
| 32 | `configure_bgp_neighbor` | Juniper Junos | **A** | No specific static finding; independent vendor semantics still unverified |
| 33 | `configure_bgp_neighbor` | Huawei VRP | **A** | No specific static finding; independent vendor semantics still unverified |
| 34 | `configure_exec_timeout` | Cisco IOS-XE | **P** | Ordinary authoring operation, mappings/rules and binding must be reconstructed; isolated test artifacts cannot be promoted. |
| 35 | `configure_exec_timeout` | Juniper Junos | **U** | Unbound reference inputs: exec_timeout_minutes, login_class |
| 36 | `configure_exec_timeout` | Huawei VRP | **U** | Unbound reference inputs: exec_timeout_minutes, exec_timeout_seconds |
| 37 | `configure_interface_ip` | Cisco IOS-XE | **A** | No specific static finding; independent vendor semantics still unverified |
| 38 | `configure_interface_ip` | Juniper Junos | **A** | No specific static finding; independent vendor semantics still unverified |
| 39 | `configure_interface_ip` | Huawei VRP | **A** | No specific static finding; independent vendor semantics still unverified |
| 40 | `configure_isis_interface` | Cisco IOS-XE | **P** | Ordinary interface attachment/context requires reviewed separate IP-ISIS and circuit-type commands; candidate fixes do not prove NET/adjacency prerequisites. |
| 41 | `configure_isis_interface` | Juniper Junos | **A** | Junos requires logical-interface/family-ISO/NET context and interface-level semantics; generic set protocols isis level level-2 is not a validated translation. |
| 42 | `configure_isis_interface` | Huawei VRP | **A** | VRP process identity is numeric; generic process_name and unqualified isis enable do not establish attachment to the requested process. Exact supported… |
| 43 | `configure_login_banner` | Cisco IOS-XE | **P** | Ordinary authoring operation, mappings/rules and binding must be reconstructed; isolated test artifacts cannot be promoted. |
| 44 | `configure_login_banner` | Juniper Junos | **U** | Unbound reference inputs: login_banner_text |
| 45 | `configure_login_banner` | Huawei VRP | **U** | Unbound reference inputs: login_banner_text |
| 46 | `configure_login_lockout` | Cisco IOS-XE | **P** | Ordinary authoring operation, mappings/rules and binding must be reconstructed; isolated test artifacts cannot be promoted. |
| 47 | `configure_login_lockout` | Juniper Junos | **U** | Unbound reference inputs: lockout_minutes, login_failure_attempts |
| 48 | `configure_login_lockout` | Huawei VRP | **U** | Unbound reference inputs: reviewed_aaa_lockout_commands |
| 49 | `configure_loopback_interface` | Cisco IOS-XE | **A** | No specific static finding; independent vendor semantics still unverified |
| 50 | `configure_loopback_interface` | Juniper Junos | **U** | Unbound reference inputs: address, description, interface, prefix_length |
| 51 | `configure_loopback_interface` | Huawei VRP | **U** | Unbound reference inputs: address, description, interface, netmask |
| 52 | `configure_ospf` | Cisco IOS-XE | **A** | No specific static finding; independent vendor semantics still unverified |
| 53 | `configure_ospf` | Juniper Junos | **A** | No specific static finding; independent vendor semantics still unverified |
| 54 | `configure_ospf` | Huawei VRP | **A** | No specific static finding; independent vendor semantics still unverified |
| 55 | `configure_ospf_redistribution` | Cisco IOS-XE | **A** | No specific static finding; independent vendor semantics still unverified |
| 56 | `configure_ospf_redistribution` | Juniper Junos | **U** | Unbound reference inputs: metric_type, ospf_metric, redistribution_source, route_policy |
| 57 | `configure_ospf_redistribution` | Huawei VRP | **U** | Unbound reference inputs: metric_type, ospf_metric, process_id, redistribution_source, route_policy |
| 58 | `configure_passive_interface` | Cisco IOS-XE | **A** | No specific static finding; independent vendor semantics still unverified |
| 59 | `configure_passive_interface` | Juniper Junos | **U** | Unbound reference inputs: interface, ospf_area, passive |
| 60 | `configure_passive_interface` | Huawei VRP | **U** | Unbound reference inputs: interface, passive, process_id |
| 61 | `configure_policing` | Cisco IOS-XE | **A** | No specific static finding; independent vendor semantics still unverified |
| 62 | `configure_policing` | Juniper Junos | **U** | Unbound reference inputs: burst_bytes, policy_name, rate_bps |
| 63 | `configure_policing` | Huawei VRP | **U** | Unbound reference inputs: burst_bytes, exceed_action, policy_name, rate_kbps |
| 64 | `configure_port_channel` | Cisco IOS-XE | **A** | No specific static finding; independent vendor semantics still unverified |
| 65 | `configure_port_channel` | Juniper Junos | **U** | Unbound reference inputs: aggregate_interface, lacp_mode, member_interfaces |
| 66 | `configure_port_channel` | Huawei VRP | **U** | Unbound reference inputs: aggregate_id, aggregate_interface, member_interfaces |
| 67 | `configure_scheduler` | Cisco IOS-XE | **A** | No specific static finding; independent vendor semantics still unverified |
| 68 | `configure_scheduler` | Juniper Junos | **U** | Unbound reference inputs: bandwidth_bps, classifier_name, policy_name |
| 69 | `configure_scheduler` | Huawei VRP | **U** | Unbound reference inputs: bandwidth_kbps, classifier_name, policy_name |
| 70 | `configure_shaping` | Cisco IOS-XE | **A** | No specific static finding; independent vendor semantics still unverified |
| 71 | `configure_shaping` | Juniper Junos | **U** | Unbound reference inputs: interface, rate_bps |
| 72 | `configure_shaping` | Huawei VRP | **U** | Unbound reference inputs: direction, interface, rate_kbps |
| 73 | `configure_static_route` | Cisco IOS-XE | **P** | Published destination CIDR is emitted as one CLI argument; use existing destination_address/destination_mask derivations and separate arguments. |
| 74 | `configure_static_route` | Juniper Junos | **P** | No specific static finding; independent vendor semantics still unverified |
| 75 | `configure_static_route` | Huawei VRP | **P** | Published destination CIDR is emitted as one CLI argument; use existing destination_address/destination_mask derivations and separate arguments. |
| 76 | `configure_trunk_allowed_vlans` | Cisco IOS-XE | **A** | No specific static finding; independent vendor semantics still unverified |
| 77 | `configure_trunk_allowed_vlans` | Juniper Junos | **U** | Unbound reference inputs: allowed_vlans, interface, native_vlan |
| 78 | `configure_trunk_allowed_vlans` | Huawei VRP | **U** | Unbound reference inputs: allowed_vlans, interface, native_vlan |
| 79 | `configure_trunk_port` | Cisco IOS-XE | **A** | No specific static finding; independent vendor semantics still unverified |
| 80 | `configure_trunk_port` | Juniper Junos | **U** | Unbound reference inputs: allowed_vlans, interface, native_vlan |
| 81 | `configure_trunk_port` | Huawei VRP | **U** | Unbound reference inputs: allowed_vlans, interface, native_vlan |
| 82 | `create_acl` | Cisco IOS-XE | **A** | No specific static finding; independent vendor semantics still unverified |
| 83 | `create_acl` | Juniper Junos | **U** | Unbound reference inputs: acl_name |
| 84 | `create_acl` | Huawei VRP | **U** | Unbound reference inputs: acl_name, description |
| 85 | `create_classifier` | Cisco IOS-XE | **A** | No specific static finding; independent vendor semantics still unverified |
| 86 | `create_classifier` | Juniper Junos | **U** | Unbound reference inputs: classifier_name, dscp_values, forwarding_class |
| 87 | `create_classifier` | Huawei VRP | **U** | Unbound reference inputs: classifier_name, dscp_values, match_mode |
| 88 | `create_ospf_area` | Cisco IOS-XE | **A** | No specific static finding; independent vendor semantics still unverified |
| 89 | `create_ospf_area` | Juniper Junos | **U** | Unbound reference inputs: area, area_type |
| 90 | `create_ospf_area` | Huawei VRP | **U** | Unbound reference inputs: area, area_type, process_id |
| 91 | `create_qos_policy` | Cisco IOS-XE | **A** | No specific static finding; independent vendor semantics still unverified |
| 92 | `create_qos_policy` | Juniper Junos | **U** | Unbound reference inputs: policy_name, policy_terms |
| 93 | `create_qos_policy` | Huawei VRP | **U** | Unbound reference inputs: policy_name, policy_terms |
| 94 | `create_vlan` | Cisco IOS-XE | **A** | No specific static finding; independent vendor semantics still unverified |
| 95 | `create_vlan` | Juniper Junos | **A** | No specific static finding; independent vendor semantics still unverified |
| 96 | `create_vlan` | Huawei VRP | **A** | No specific static finding; independent vendor semantics still unverified |
| 97 | `delete_acl_rule` | Cisco IOS-XE | **A** | No specific static finding; independent vendor semantics still unverified |
| 98 | `delete_acl_rule` | Juniper Junos | **U** | Unbound reference inputs: acl_name, acl_rule_id |
| 99 | `delete_acl_rule` | Huawei VRP | **U** | Unbound reference inputs: acl_name, acl_rule_id |
| 100 | `delete_vlan` | Cisco IOS-XE | **A** | No specific static finding; independent vendor semantics still unverified |
| 101 | `delete_vlan` | Juniper Junos | **A** | No specific static finding; independent vendor semantics still unverified |
| 102 | `delete_vlan` | Huawei VRP | **A** | No specific static finding; independent vendor semantics still unverified |
| 103 | `disable_isis_interface` | Cisco IOS-XE | **P** | Ordinary interface attachment/context requires reviewed separate IP-ISIS and circuit-type commands; candidate fixes do not prove NET/adjacency prerequisites. |
| 104 | `disable_isis_interface` | Juniper Junos | **A** | Junos requires logical-interface/family-ISO/NET context and interface-level semantics; generic set protocols isis level level-2 is not a validated translation. |
| 105 | `disable_isis_interface` | Huawei VRP | **A** | VRP process identity is numeric; generic process_name and unqualified isis enable do not establish attachment to the requested process. Exact supported… |
| 106 | `enable_ospf_process` | Cisco IOS-XE | **A** | No specific static finding; independent vendor semantics still unverified |
| 107 | `enable_ospf_process` | Juniper Junos | **U** | Unbound reference inputs: router_id |
| 108 | `enable_ospf_process` | Huawei VRP | **U** | Unbound reference inputs: process_id, router_id |
| 109 | `modify_acl_rule` | Cisco IOS-XE | **A** | No specific static finding; independent vendor semantics still unverified |
| 110 | `modify_acl_rule` | Juniper Junos | **U** | Unbound reference inputs: acl_action, acl_name, acl_rule_id, destination_port, destination_prefix, ip_protocol, source_port, source_prefix |
| 111 | `modify_acl_rule` | Huawei VRP | **U** | Unbound reference inputs: acl_action, acl_destination_address, acl_destination_wildcard, acl_name, acl_rule_id, destination_port, ip_protocol,… |
| 112 | `modify_vlan` | Cisco IOS-XE | **A** | No specific static finding; independent vendor semantics still unverified |
| 113 | `modify_vlan` | Juniper Junos | **U** | Unbound reference inputs: vlan_id, vlan_status |
| 114 | `modify_vlan` | Huawei VRP | **U** | Unbound reference inputs: vlan_id, vlan_status |
| 115 | `remove_bgp_neighbor` | Cisco IOS-XE | **A** | No specific static finding; independent vendor semantics still unverified |
| 116 | `remove_bgp_neighbor` | Juniper Junos | **A** | No specific static finding; independent vendor semantics still unverified |
| 117 | `remove_bgp_neighbor` | Huawei VRP | **A** | No specific static finding; independent vendor semantics still unverified |
| 118 | `remove_interface_ip` | Cisco IOS-XE | **A** | No specific static finding; independent vendor semantics still unverified |
| 119 | `remove_interface_ip` | Juniper Junos | **A** | No specific static finding; independent vendor semantics still unverified |
| 120 | `remove_interface_ip` | Huawei VRP | **A** | No specific static finding; independent vendor semantics still unverified |
| 121 | `remove_ospf_interface` | Cisco IOS-XE | **A** | No specific static finding; independent vendor semantics still unverified |
| 122 | `remove_ospf_interface` | Juniper Junos | **A** | No specific static finding; independent vendor semantics still unverified |
| 123 | `remove_ospf_interface` | Huawei VRP | **A** | No specific static finding; independent vendor semantics still unverified |
| 124 | `remove_static_route` | Cisco IOS-XE | **P** | Ordinary removal binding also emits a CIDR as one CLI argument; exact add/remove prefix/mask symmetry is required. |
| 125 | `remove_static_route` | Juniper Junos | **P** | No specific static finding; independent vendor semantics still unverified |
| 126 | `remove_static_route` | Huawei VRP | **P** | Ordinary removal binding also emits a CIDR as one CLI argument; exact add/remove prefix/mask symmetry is required. |
| 127 | `rename_vlan` | Cisco IOS-XE | **A** | No specific static finding; independent vendor semantics still unverified |
| 128 | `rename_vlan` | Juniper Junos | **U** | Unbound reference inputs: new_vlan_name, old_vlan_name |
| 129 | `rename_vlan` | Huawei VRP | **U** | Unbound reference inputs: new_vlan_name, vlan_id |
| 130 | `set_interface_admin_state` | Cisco IOS-XE | **A** | No specific static finding; independent vendor semantics still unverified |
| 131 | `set_interface_admin_state` | Juniper Junos | **A** | No specific static finding; independent vendor semantics still unverified |
| 132 | `set_interface_admin_state` | Huawei VRP | **A** | No specific static finding; independent vendor semantics still unverified |
| 133 | `set_interface_description` | Cisco IOS-XE | **A** | No specific static finding; independent vendor semantics still unverified |
| 134 | `set_interface_description` | Juniper Junos | **A** | No specific static finding; independent vendor semantics still unverified |
| 135 | `set_interface_description` | Huawei VRP | **A** | No specific static finding; independent vendor semantics still unverified |
| 136 | `set_native_vlan` | Cisco IOS-XE | **A** | No specific static finding; independent vendor semantics still unverified |
| 137 | `set_native_vlan` | Juniper Junos | **A** | No specific static finding; independent vendor semantics still unverified |
| 138 | `set_native_vlan` | Huawei VRP | **A** | No specific static finding; independent vendor semantics still unverified |
| 139 | `set_ospf_router_id` | Cisco IOS-XE | **A** | No specific static finding; independent vendor semantics still unverified |
| 140 | `set_ospf_router_id` | Juniper Junos | **U** | Unbound reference inputs: router_id |
| 141 | `set_ospf_router_id` | Huawei VRP | **U** | Unbound reference inputs: process_id, router_id |


**Required reconciliation:** After each cohort, report **141 total unique rows**, plus `engineer approved`, `ordinary active`, `native runtime checked`, `optional independent semantic certified`, `device tested`, and `genuine Ansible variant verified` separately. Preserve Phase D baseline markers. A vendor-semantic disagreement must be disclosed and expressly resolved in the engineer approval; public documentation is not a publication prerequisite.

---

# Execution directive for Codex (included so this file is directly runnable as a task)

**Read this whole file and the four Phase D source documents, inspect the actual current repository, then implement E0 through E10.** This document supersedes repeated exploratory replanning but does not supersede source-derived permission/validation contracts. Start with E0, write the minimal architecture/action map as part of the checkpoint, then make real source changes. Implement in small verifiable batches and proceed autonomously through independent gates. Do not stop after auditing, writing another plan or passing only a small test subset.

**Prioritize making all 141 vendor-operation combinations structurally usable, explicitly senior-engineer approved and published in the ordinary V9 runtime.** Reusable vendor-native renderers and candid best-effort engineer-reviewed methods are allowed, with visible independent-certification status. No public Internet verification is required for knowledge publication; never invent approvals, hide core V9 test failures or claim device-tested semantics without evidence. Continue independent work even when individual engineer approvals remain pending.

In parallel, fix the measured model routing, planning, reasoning, synthesis, simulator-conformance, browser/UI, external-source and playbook limitations. Keep the B3 fallback available until actual blinded evaluation proves the new model-assisted path. Conclude with a factual handover showing exactly what is active, what was proven, what failed, and how to resume. **Do not auto-commit, re-stage the protected work, deploy to devices, change physical network configuration or silently enable production live readers.**
