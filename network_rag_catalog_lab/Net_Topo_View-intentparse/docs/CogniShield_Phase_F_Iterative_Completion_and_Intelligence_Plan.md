# CogniShield — Phase F: Iterative Completion, Native-Output Quality, and Evidence-Grounded Assistant Intelligence

**Status:** Implementation specification; no source code or live runtime has been changed by this document.  
**Baseline:** Phase E reports dated 2026-10-18; validate against the actual working tree before execution.  
**Scope:** Finish the unfinished Phase E work without redoing its completed 141-binding publication.  
**Primary model:** Installed `qwen2.5:1.5b` for conversation/planning/synthesis; `nomic-embed-text` for embeddings. No stronger model, automatic download, fine-tuning, or competing knowledge engine required.  
**Operating rule:** **Implement → run the relevant tests → inspect actual outputs → diagnose → correct → retest → record evidence, for EVERY change batch.** An iteration is not complete when code compiles; it is complete only when its user-visible behavior and regression gates pass, or when a specifically documented blocker remains.

---

## Executive mandate

CogniShield has already achieved the principal Phase E publication target at the **application runtime** level: **47 catalog operations × three vendor bindings = 141/141 published native bindings** in immutable release `f0e33c357dd54988ba7e651d813c76a7`, with manifest SHA-256 `9b0cb20f114b3878e1055bbc9488f6afb9ce40e5560142942301882cc6096e9c`. The Phase E reports describe 142 positive rendering fixtures, 1,638 invalid-input checks, 141 profile checks, a 47-document retrieval index and five real retrieval smokes. Authenticated **Publish Release / Activate** is the engineer's authorizing action; no separate signature form, internet confirmation, independent semantic certification, real-device test, or Ansible certification blocks native publication. These results are **not** evidence that every emitted command is device-correct or that every natural-language Studio workflow works.

Phase F must therefore **preserve, inspect, correct and actually use** this catalog while completing the unresolved systems work: simulator conformance; implicit/compound intent understanding; model-led tool planning and adaptive investigation; faithful, natural LLM reasoning; full Ansible Studio workflows; browser and external-source parity; reproducible holdout evaluation; and final system acceptance. Do **not** reset/recreate the 141 templates, require a second approval ceremony, backfill invented engineer assessments, or downgrade user-enabled AI features as an easy workaround.

### Non-negotiable success outcomes

1. **Publication stability:** active 141/141 V9 bindings persist across restarts; correct individual native-output defects via new authoring revisions and legitimate V9 releases, not by editing immutable packs or silently substituting unsupported target profiles.
2. **Real source selection:** the assistant understands unfamiliar, implicit and multi-part intentions; routes each information need to appropriate **authorized** tools; distinguishes conceptual questions, published knowledge, actual network observations, documents, simulation and Monaco buffer content.
3. **Adaptive investigation:** bounded, useful follow-up reads occur when they can resolve real uncertainty; model plans are checked for missing sources; no unsupported causal conclusions.
4. **Natural, grounded synthesis:** the actual `qwen2.5:1.5b` produces better explanations when capable; facts, uncertainties and proposed fixes remain auditable; verified fallback is not miscounted as successful model reasoning.
5. **Studio engineering behavior:** full unsaved-editor context; correct V9 operation selection, parameters, clarification, compatible profile and reviewable output; exact-base edit proposals with Accept/Reject/Undo and explicit Save. No autonomous application to devices.
6. **Simulation and integration evidence:** independent mixed-vendor conformance, realistic negative/ambiguous cases, controlled normal/external adapter checks and human-realistic browser tests.
7. **Continuous correction:** no “tests mostly pass” completion claims. Every failing assertion must be understood and fixed, or recorded as a genuine, narrowly scoped external blocker; after a fix, the original failure, neighboring cases and full affected suite must be rerun.

---

## 0. Authoritative evidence, chronology, and exact starting state

Read these artifacts in the actual repository and compare their hashes, revisions and paths against the uploaded copies:

| Artifact | Use | Important interpretation |
|---|---|---|
| `docs/PHASE_E_RELEASE_AND_RUNTIME_REPORT.md` | **Newest top-section** release and user-requested workflow evidence | Later lines are **historical**, and still say publication is pending; do not revert to that state. |
| `docs/evaluations/PHASE_E_RESULTS.md` | Current outcomes, earlier unsuccessful model evaluations, browser evidence | Later historical `PLANNING=0` and `SYNTHESIS=0` instructions are superseded by the newest user-requested enabled mode. |
| `docs/PHASE_E_IMPLEMENTATION_CHECKPOINT.md` | Preservation, active runtime, named source changes, remaining tasks | Treat its latest top section as the resume anchor. |
| `docs/evaluations/phase_e_stage_state.json` | E0–E10 stage status | E0–E4 verified; E5–E9 in progress; E10 blocked. |
| `docs/evaluations/phase_e_vendor_progress.json` | 141 fingerprints, platform coverage, fixture scope, caveats | 141 `ordinary_active=true`, but legacy `implementation_status` still says `AWAITING_HUMAN_APPROVAL`: this is a stale ledger field, not a current blocker. |
| `docs/evaluations/phase_e_cases.json` | 141 application-level cases + additional cases | Existing positive expected outputs **may repeat native template defects**; they are not independent vendor oracles. |
| `docs/evaluations/phase_e_holdouts_v1.json` | Original frozen 60 single-turn routing prompts | Exposed after first run; use as regression, **not fresh holdout**. |
| `docs/evaluations/phase_e_vendor_coverage.csv` | Coverage table | Cross-check unique `(operation_id, vendor, platform, version)` identities and active release status. |
| Phase D results / handover / baseline coverage | Historical failure origins and architectural constraints | Reference, not instructions to recreate Phase D. |

**Verified-from-Phase-E-report baseline:**

- `ordinary_active_release=f0e33c357dd54988ba7e651d813c76a7`; previous rollback release `0690966eb003499380e960a98d1e418f`.
- `operations=47`, `bindings=141`, `profiles=141`, reported `positive_fixtures=142`, `negative_checks=1638`.
- Authenticated admin's Publish/Activate action is the only required method-level human authorization (plus real structural/render/security integrity checks).
- `COGNISHIELD_AI_ENGINE=langgraph_b3`, `COGNISHIELD_AI_PLANNING=1`, `COGNISHIELD_AI_SYNTHESIS=1` in the user-requested ordinary configuration; Ollama conversation model `qwen2.5:1.5b`. **These are feature settings, not proof of model quality.**
- Phase E routing **candidate 52/60 (86.7%)** versus **prior baseline 57/60 (95%)** on the frozen first-run source/workflow routing set. Previous 90% threshold by itself would permit a regression; Phase F must not.
- Answer adequacy ≥85% **not independently established**. Some actual model calls timed out around 30s, made unsupported claims or were rejected by source/factual guards. One browser compound request fell back to deterministic verified inventory/topology despite a real model planning call.
- Current 141-binding fixture coverage is narrower than full positive branch paths, real device conformance, genuine Ansible validation and all 141 natural-language Studio journeys.
- Simulation has partial seeded mixed-vendor scenarios; broader forwarding/protocol/performance and negative conformance not complete.
- Whole-response Copy UI/utility tests passed, but browser virtual clipboard paste returned empty; real OS clipboard/manual paste and controlled normal/external adapter parity remain unproven.
- Browser Draft Change Summary internal scroll was already verified; retain it and do not spend Phase F rebuilding it.
- 52-file original staged patch hash reported `d6aa68e47ae3b44449d1f832404ad925a373791b845ec064d067b8e8b028d7f8` (recalculate actual current tree); 16 legacy chat rows previously showed a fingerprint change during UI mounting, and later browser navigation with corrected autosave showed stable fingerprints. **Never call the historical mutation “timestamp-only” without exact before-images.**

**Source-quality red flags to reproduce first:** the uploaded `phase_e_cases.json` includes Cisco `configure_ospf` fixture output `router-id 192.0.2.200 interface GigabitEthernet1/0/5` on one CLI line, and Huawei `configure_ospf` fixture output `router-id 192.0.2.200interface GigabitEthernet0/0/5`. These may signal concatenation/context handling bugs in authored Jinja or generated fixtures. Do not assume every other operation is broken, but do **not** call a self-matching fixture proof of native syntax correctness. The 141-row ledger also exposes stale `implementation_status` values after activation.

**Repository instructions:** inspect the actual working tree, not an older archive. Phase E named files include `backend/local_providers/knowledge_review.py`, `knowledge_worker.py`, `knowledge_lifecycle.py`, `phase_e_methods.py`, `phase_e_knowledge.py`, `backend/llm/gateway_knowledge.py`, `gateway_diagnostics.py`, shared LangGraph planning/synthesis modules, `backend/development/seeded.py`, `frontend/components/ansible/NativeGenerationReview.tsx`, Knowledge Engineering review UI, and Monaco workspace integration. Resolve real paths by search first; do not create duplicated modules merely because a report path differs from current source.

---

## 1. Mandatory iterative engineering protocol — apply to *every* task

This is the most important change versus the previous implementation run. Codex must not implement several milestones and discover defects only in a final pass.

### 1.1 One small change, one measured test cycle

For every behavior change or logically coupled patch batch, execute the following loop **synchronously**:

1. **Baseline:** write the intended user behavior, exact existing failing example, expected tool/source/response, affected files and *initial failing test*. Preserve an input/output trace **before** changing implementation.
2. **Hypothesis:** identify whether cause is parser/routing, reference resolution, missing tool, inaccurate reader result, retrieval/index, V9 schema/template, model prompt/output, verification, UI state, timing, or test infrastructure. Do not patch a downstream string to hide an upstream source error.
3. **Implement smallest coherent fix:** preferably general logic with typed contracts and existing architecture; don't hardcode a particular test prompt/device/site.
4. **Fast checks immediately:** formatting/lint/static type, one or more targeted unit tests and exact reproduced case. Inspect actual assertions, return values and logs; a green process exit with ignored warnings is not enough.
5. **Integration check in the same iteration:** run the real V9 runtime/worker, gateway/graph, scenario engine, or UI path appropriate to the change; include at least one positive, negative and ambiguity/failure case. Use the active release or an isolated correctly published test release as appropriate.
6. **Inspect output, not just status:** review rendered CLI/newline structure, selected tools and authorization, resolved device/profile, model-generated text and factual citations, UI buffer/revision, model calls and fallback reason, latency and error messages. Compare to independently constructed expectations.
7. **Fix before advancing:** if a test fails or a user-visible response is wrong, determine root cause, add a reproducing regression, correct the implementation **and flawed fixtures where relevant**, rerun affected unit/integration/UI tests and verify the original failure no longer occurs. **Do not continue to unrelated changes while local failures remain.**
8. **Neighbor/regression sweep:** run nearby operations, adjacent intent categories, saved/unsaved editor cases, unsupported profiles, security boundaries and existing application tests that could be affected.
9. **Write durable evidence:** update one atomic iteration record with pre-change failure, patch summary, commands, real results, artifacts, remaining risk and next step. Only then mark the small item `PASS`. If truly externally blocked, mark `BLOCKED` with reproduction and alternatives, **not `PASS`**.
10. **Checkpoint for resume:** preserve uncommitted work, temporary reports and hashes. Start the next item only after the preceding work is either passed or has an explicit, bounded blocker with unaffected work queued.

**Pseudocode of required control flow:**

```text
for each prioritized issue_or_feature:
    reproduce_or_define_acceptance_with_new_test()
    while not meets_acceptance:
        inspect_actual_result_and_trace()
        classify_root_cause()
        implement_small_fix()
        run_fast_checks()
        run_real_component_integration()
        if failure:
            record_failure_with_raw_evidence()
            continue      # FIX NOW, not in a hypothetical later phase
        run_neighbor_regressions()
        if regression:
            record_failure_with_raw_evidence()
            continue
        record_verified_result()
    proceed_to_next_item()
```

### 1.2 Failure taxonomy and appropriate response

| Failure | Correct response | Incorrect shortcut |
|---|---|---|
| Expected fixture repeats malformed command | Independently review command structure; correct implementation **and** expected output, then re-render active candidate | Update expected text to match existing wrong template without independent check |
| Wrong knowledge/profile/device | Fix entity and platform constraints, clarify if unresolved, test two similar devices | Silently relabel R1/R2 as IOS-XE 17.9 to make a fixture pass |
| Wrong source/tool | Fix typed information needs/source planner and tool descriptor; rerun compound and negative cases | Add a keyword rule for the specific holdout sentence |
| Model invents OSPF facts/routes/cause | Improve evidence packaging and model task; add factual verifier and honest uncertainty; rerun exact M1/M2 | Hardcode a canned answer or report verifier fallback as LLM success |
| Retrieval lacks necessary source | Add authorized reader/second retrieval when justified, or report unavailable; inspect scope and freshness | Claim source contains facts it does not have |
| Test harness gives a false red/green | Independently isolate environment, correct harness and rerun both candidate and baseline | Delete/relax failing test, fabricate manual PASS, or score a known exposed case as holdout |
| Browser virtual clipboard inaccessible | Run permitted real OS clipboard paste or declare external test BLOCKED; verify actual app Clipboard API separately | Call browser toast alone a paste success or automatically disable Copy |
| Ollama timeout/concurrency contention | Compare isolated warm/serial runs, inspect budgets and token payload, optimize deterministic evidence and fallback | Raise budgets without limit or remove model-call trace |
| V9 Chroma/embedding build timeout | Respect existing bounded batching, lock ownership and serial load; retry safely with audit | Delete live lock, touch immutable artifacts or weaken release integrity |
| Stage/DB drift | Halt change, inspect exact pre/post hashes and owner process, preserve data and recover via approved lifecycle | `git reset`, blind DB restore, manual `active.json` edits |

### 1.3 Minimum evidence record for every iteration

Use `tmp/phase-f/iterations/<timestamp>-<issue-id>/` and a machine-readable `result.json` plus readable `README.md` containing:

```json
{
  "issue_id": "F1-OSPF-HUAWEI-NEWLINE",
  "source_revision_before": "<git tree/index hashes>",
  "source_revision_after": "<git tree/index hashes>",
  "expected_behavior": "router-id and interface are separate CLI statements",
  "baseline_actual": "<exact original rendered output>",
  "hypothesized_cause": "<source/template/fixture/worker>",
  "changes": ["<actual files and intent>"],
  "tests": [
    {"command": "<actual command>", "exit_code": 0, "result": "PASS", "artifact": "<path>"}
  ],
  "integration": {"actual_output": "<redacted trace>", "result": "PASS"},
  "regressions": {"result": "PASS", "count": 0},
  "human_or_environment_blockers": [],
  "status": "PASS",
  "remaining": []
}
```

Never invent a test count, result, caller identity, command, timestamp, source citation or screenshot. Preserve failure attempts before subsequent fixes; do not overwrite evidence with only the final green run. If a change takes longer than the Codex quota, complete this record first so a later run can resume exact work.

### 1.4 Test cadence: frequent but proportionate

- **Every edit batch:** targeted tests, a negative/edge input and inspected functional output.
- **Every graph/model change:** candidate-versus-legacy paired cases with real selected sources, call budgets, fallback reason and answer text; at least one multi-turn case.
- **Every knowledge/schema/template change:** exact V9 preview, independent golden oracle, invalid-input rejection, incompatible-profile rejection, and if published, actual immutable pointer/index/runtime check.
- **Every Studio frontend change:** TypeScript/build (where affected), component tests, actual unsaved-buffer browser path, Accept/Reject/Undo/Save boundaries and a screen/DOM result.
- **Every milestone:** complete affected regression suite and at least one actual browser or gateway workflow.
- **Before final signoff:** full feasible application/backend/frontend/security/E2E/holdout matrix, including a cold service restart, rollback dry-run in isolation, data-integrity comparison and repeated tests under representative CPU limits.

Record timeouts/unstable behavior as such. Do not silently run the same leaking test until it happens to pass; identify flaky causes and demonstrate stability.

---

## F0 — Protect the completed Phase E system and establish a truth-based baseline

**Purpose:** do not lose the achievement while chasing AI quality.

**Implementation tasks:**

1. Inspect Git working tree, staged/unstaged/untracked diff, pre-existing 52-file staged index, branch/HEAD, user-specific repository instructions. Record actual index-tree digest, including the historical SHA above only if it still matches.
2. Read and verify current `.env`/`.env.example` *without printing secrets*; ensure model identities, planning/synthesis enabled status, dev simulation selection and native release values match user's latest decisions. Preserve feature flags; test fallback rather than disabling them to pass acceptance.
3. Read actual V9 `active` pointer and manifest, verify 47 schemas/141 distinct bindings/profile versions and release-specific 47-document retrieval index. Run five retrieval smokes and one complete preview per vendor. Verify 142 fixtures if inexpensive; keep original artifacts.
4. Record immutable rollback anchors, SQLite integrity/foreign keys and table fingerprints/counts (ordinary inventory, links, configuration captures, jobs, conversations, turns, checkpoints, authoring revisions, publications). Preserve before-images where allowed; no blanket snapshot restoration.
5. Inspect running frontend/backend/Ollama owner processes and port reservation on Windows. Don't stop a process without checking ownership. Use existing normal start scripts and adapters.
6. Compare `phase_e_stage_state.json` to actual current state. Make a Phase F checklist; treat E5–E10 as work remaining. Don't use stale historical “approval pending” language.
7. Freeze all **Phase F new evaluation prompts and expected evidence/answers** before running model on them. Preserve test ownership and content hashes; separate exposed Phase E 60 from new blind Phase F.

**Immediate acceptance:** verified publication, current flags, source/data fingerprints and rollback anchor; `tmp/phase-f/F0-baseline.json` exists; **zero** ordinary configuration/device writes. If active release mismatches, first diagnose real mismatch—do not overwrite state to make the report agree.

---

## F1 — Correct the now-published native-output defects and strengthen the quality oracle

**Priority:** very high; do not repeat authoring all 141 or require external certification to publish a corrected template.

### F1.1 Reproduce and repair the known OSPF formatting defects

- Extract exact active V9 bindings/schema, source Jinja, compiled rendered outputs, context and inputs for `configure_ospf:cisco:iosxe:17.9` and `configure_ospf:huawei:vrp:8`.
- Determine whether the recorded concatenation comes from the **actual active render**, from Phase E's independently stored expected fixture, or both. Do not assume the report's expected output is runtime truth without replay.
- For Cisco, the OSPF router process/ID and `interface` context must be represented as unambiguous separate CLI statements. For Huawei, `router-id ...` must not join `interface ...` without a line break. Avoid guessing exact device syntax solely from the fixture; have the authorized engineering method reviewed or use the already accepted structured CLI contract.
- Fix Jinja whitespace control/loops/templates, normalized input and/or golden fixtures as the reproduced cause warrants. Verify 1+ interfaces, missing optional router ID, and missing required area/process with independent expected formatting.
- Perform analogous spot inspections for Junos OSPF, Cisco/Huawei static route, Junos qualified next-hop removal, Huawei IS-IS process, VLAN name/delete, LACP, ACL ordering, QoS rate conversion and AAA operations—prior Phase D/E risk families, not presumed current bugs.
- Test exact output **and** structural CLI invariants (command separation, scopes, balance, correct interface and process association, no Jinja residue, no accidental newlines between tokens). Checks must not reduce to the same template generating both actual and expected.

### F1.2 Extend representative tests to actual conditional behavior

For each of 141 bindings, record presence/absence of meaningful conditional branches and input forms. Expand test coverage proportionally, with risk-based depth for route removal, ACL deletion, QoS and protocol operations. Minimum: one valid representative per binding, invalid required/unknown/boundary tests, incompatible profile, and branches for optional fields (including explicit null vs absent). Higher-risk methods: multi-item, escaping/newline injection, command-context boundaries, deletion prerequisites and parameter coercion checks. Reconcile `142` versus `141` as documented fixture multiplicity, not an arithmetic error.

### F1.3 Reconcile statuses honestly

- `phase_e_vendor_progress.json` currently reports 141 active and engineer-authorized but also carries 141 legacy `AUTHORED_RENDER_TESTED_AWAITING_HUMAN_APPROVAL` statuses. Update derived ledgers/report generation to distinguish **current activation status**, **publication authorization**, **optional independent certification**, **Studio E2E coverage**, and **original Phase E preparation history**. Preserve history, do not falsify old records.
- Engineer publication remains through authenticated `Publish Release`/`Activate`, without a second sign-off form and without mandatory internet/device verification. Keep semantic/device/Ansible certification explicitly separate.
- If template correction changes authoritative knowledge, create a **new valid immutable release** through existing authoring/Validate/Publish lifecycle, maintain rollback, and rerun active metadata/index/profile/renderer tests. Never edit release `f0e33...` in place. Publication authorization must be authentic; do not inject forged admin activity.

**Exit tests:** both original OSPF cases fail-before/pass-after if defects reproduce; 141 distinct bindings remain renderable and authorized, full negative suite and Chroma index pass; verified new active release if publication is needed; no mistaken “device-certified” claim. If known expected fixtures prove wrong but active templates are correct, fix tests only and record that distinction.

---

## F2 — Finish independent mixed-vendor simulation conformance (remaining E5)

**Architecture:** retain `backend/development/network_model.py`/current scenario engine, `backend/development/scenarios/`, schema, `backend/development/seeded.py` and existing authorized scenario selection. No second simulator, second inventory SoT, arbitrary packet emulator or unbounded LLM planning loop.

### F2.1 Reproducibility and source integrity

- Seeded scenario generation must be deterministic for identical `(seed, variant, schema revision)` and produce a stable scenario hash. Validate import, create, edit, activate, evaluate, export, reset, and state isolation; activation never changes ordinary real inventory.
- Store **ground truth in test-only oracle**; model-visible observations include only the available, stale, conflicting or missing sources allowed in the scenario. The model must not receive diagnosis labels hidden in scenario metadata.
- Explain provenance for inventory vs simulated snapshot, configuration vs operational observations, and saved vs running vs unknown. Refuse to claim a simulated observation proves a real physical device condition.

### F2.2 Independent forwarding oracle

Test with separately calculated expected results (not expected results derived by calling the simulator under test): IPv4 longest-prefix routing; preference/metric ties; recursive next-hop and missing resolution; per-hop ingress and egress ACL ordering/defaults; VRF isolation/explicit leaks; deterministic ECMP branch enumeration; 1–N-hop paths and asymmetric/return routes; loops, unreachable cases, path/branch budgets (32 hops/16 branches if unchanged); malformed/cyclic data and unknown state. Include both deliberately working and failing routes.

### F2.3 Protocol and performance scenarios

Add or complete OSPF and BGP mismatch examples: interface/timer/area/AS/peer state/prerequisites, transitive causes, observed state vs configured intent. Add QoS/congestion comparisons using timestamps, rate units, dropped packets and stale/missing telemetry; distinguish correlation from causal proof. Test existing Phase E seeded variants **healthy, shutdown, return-route, ACL, OSPF timer, BGP AS, conflict** plus new composed variants; extend only within declared simulator semantics. IPv6, NAT, stateful ACLs and complete protocol state machines remain `UNSUPPORTED`/`UNKNOWN` unless actually implemented.

### F2.4 Cross-surface consumption

Use the SAME scenario's facts through authorized tools in Floating AI, Studio read-only investigation, graph verification and UI. Demonstrate contradictory telemetry vs syslog and unavailable source. The assistant should request additional evidence only when useful; otherwise explain uncertainty and next diagnostic step.

**Exit:** independent per-scenario truth records; reproducible CLI/JSON reports; each scenario correct for known/simulated cases and `UNKNOWN` where unsupported; no ordinary inventory mutation; fresh mixed-vendor multi-turn investigations captured and manually inspected. Test oracle independence in code review.

---

## F3 — Fix implicit intent, compound routing and adaptive source planning (remaining E6)

**Primary failure to improve:** 52/60 model-routing candidate vs 57/60 previous path on the first frozen evaluation. The original 60 are now exposed regressions; do not score them as untouched holdouts again.

### F3.1 Trace actual B3 graph before changing it

Map and instrument the current graph path, e.g. request understanding → reference resolution → authorized tool selection → execution → evidence sufficiency → optional follow-up → fact verification → response composition. Inspect actual registry names, input/output contracts and mode constraints; Phase F may rename internal nodes only if necessary, but must not install a second competing agent or rely on arbitrary tool execution.

### F3.2 Typed intent goals, not keyword buckets

Improve typed representation of objectives, subgoals, referenced entities, time ranges, source authority, requested action/output, evidence needs and editor context. Allow one utterance to contain multiple independent needs and dependencies. Important negative distinction: a conceptual OSPF question ≠ a published OSPF contract question ≠ actual R1 OSPF state ≠ a request to generate OSPF code. Also distinguish topology relationships from inventory attribute lookups, saved snapshots from running state, source absence from negative operational fact, and reviewing code from modifying a document.

Test genuine paraphrases, typographical mistakes, implicit goals, pronouns and ellipsis: “Why did that uplink stop advertising yesterday?”, “How about its return path?”, “Same check on the other edge”, “What if I only want the config?”, and “Could you fix the open file but keep OSPF?”. Preserve prior turn evidence/source freshness and owner-bound history; ask for clarification if device/time/current capture cannot be resolved safely.

### F3.3 Authorization-constrained adaptive investigation

- Planner may propose **typed information needs**, not arbitrary Python/SSH commands. Tool registry verifies authorization and scope before execution.
- Validate that proposed plan covers *all* required sources for a compound question. If incomplete, repair once within budget or use explicit verified fallback to fill required authorized reads. Trace omissions distinctly from model success.
- Support one or a few bounded decision-dependent follow-up tool rounds only when a relevant information gap exists (e.g. BGP peer down → compare config, state, recent syslog and interface). No infinite loop or “always call all tools.”
- Distinguish `AVAILABLE`, `MISSING`, `STALE`, `CONFLICTING`, `UNSUPPORTED`, `ERROR`, `SIMULATED`, and `NOT_QUERIED`. A tool error must not become “zero incidents.”
- Keep real dev and ordinary source/permission boundaries and exact editor source revisions; Floating AI read-only; Studio writes only as proposals.

### F3.4 Scoring improvements and nonregression requirement

- Preserve 60 original Phase E cases as **regression suite**. Fix all reproducible missed topology/published-contract/compound/editor-selection cases without constructing prompt-specific exceptions.
- Create **new frozen Phase F holdouts** before running model: suggested ≥120 independently curated cases including all source groups and ≥30 compound/implicit/multi-turn cases. Independently review answerable source expectations and allowed equivalent reads. Include adversarial irrelevant sources and cases requiring no tool.
- Run paired baseline (previous router with same current sources/tools) vs updated candidate using identical input, seeded evidence, devices, time window, model warmup and CPU resource budget. Keep source selection vs content answer vs permission result as separate scores.
- **No regression gate:** on original 60, candidate must recover at least 57/60 (original baseline); target >57/60 where feasible. On new frozen benchmark target ≥90% as stipulated in Phase E **and** no material source-group regression versus matched baseline; aspire to ≥95% if possible. Scores below target are reported FAILED, not reinterpreted. Consider per-category recall/precision and confidence, not only headline total.
- Independently check one actual end-to-end user request per major category; a mock `selected_tools` list is not enough.

**Exit:** model planner and hybrid fallback correctly select sources for unfamiliar intent, with traceable typed goals/authorization; the candidate's fresh-case accuracy passes the gate, or a precise model-capacity blocker is documented without presenting Phase F as completed.

---

## F4 — Make `qwen2.5:1.5b` synthesis faithful, causal and useful (remaining E7)

**Goal:** meaningful language assistance, not just attractive formatting around deterministic tool facts. Model is intentionally unchanged.

### F4.1 Establish a reliable real-model evaluation design

Run separate **M0** no tools/model-only, **M1** same model given verified curated evidence, **M2** full authorized B3 orchestration, and **M3** deterministic verified fallback. Use real Ollama, not mocked completions, and identical case/source conditions for comparisons. Record model invocation count, prompt/response tokens when available, elapsed time, timeouts, source IDs, hallucinations, rejected claims, fallback usage, and user-relevant quality. Do not equate M3 correctness to M2 model reasoning.

Use independently graded tasks spanning: general concepts, protocol explanation, topology causality, saved/current configuration difference, ACL and reachability, BGP/OSPF fault hypotheses, partial telemetry, contradictory sources, unknown source, multi-turn “why?” follow-ups, natural Studio explanation/edit planning and incomplete V9 parameters. Freeze expected evidence/claim list before inference; blind graders to model arm when practicable.

### F4.2 Improve model input and output, not model size

- Assemble concise, **typed fact tables/evidence packets** with canonical device IDs, vendor/platform, source availability, capture time, operational vs intended vs simulated status, relationships, units, and citations. Avoid raw source dumps and overwhelming 1.5B context.
- Use staged prompts for planning vs synthesis, constrained output schemas with robust parsing/repair, clear source-local claims, and explicit unanswered questions; keep calls bounded and cancellation/timeouts functional.
- Add verified intermediate calculations for route selection, subnet, interface, rate, timestamps and AS/peer role; let the model interpret but never modify computed facts. Do not universalize narrow guards: add domain-appropriate, testable verifiers for frequent network facts and claim-support/uncertainty.
- Natural response contract: answer first; important evidence; likely explanations versus confirmed causes; missing/contradictory facts; targeted next check or Studio handoff if appropriate. No generic filler or repeated “cannot verify” when evidence is adequate.
- For model-only general questions where no tools are relevant, avoid irrelevant network tool calls. Preserve ordinary conversational tone and context without injecting private network facts.

### F4.3 Repair known real-model failure classes

Exact cases to reproduce: wrong OSPF router-ID requirement, fabricated static route, fake all-operational claim, syslog availability contradiction, missing citations, wrong BGP AS association, miss on permitted additional reader, high inference latency/30-second timeout, unsupported confident root cause, and rejected synthesis with unhelpful fallback. For each, root-cause trace: retrieval vs prompt/evidence packing vs model capacity vs verifier. Fix general causes, rerun original and adjacent variants, and preserve raw outputs.

### F4.4 Better fallback and time budgets

- User explicitly enabled planning and synthesis. **Do not flip both flags off simply to make benchmarks look good.** Failed model paths must be visibly attributed and safely fall back without fabricating a successful model result.
- Compare warm and cold model starts and serial vs competing workloads. Reduce unnecessary model calls, repeated context and broad retrieval; enforce bounded stage budget and timeouts. Keep cancellation support and friendly partial-evidence responses.
- If a resource or CPU limit makes a scenario impossible, mark unsupported/fallback, report median/p95 latency and trace it; propose a later stronger model only as an optional future experiment, not a current dependency.

### F4.5 Independent answer-quality gates

Score factual correctness, completeness, relevance to intent, evidence support/citations, useful interpretation, qualified causal explanation, ambiguity handling, instruction compliance, and latency. **At least 85% adequate M2 answers on fresh independently graded cases** is the original Phase E quality target; additionally require no critical fabricated network commands/operational states in accepted answers and no authorization violation. Report per-domain score, unsupported model answers, **M2 model-generated acceptance rate**, **M3 fallback rate**, and confidence interval where possible. Do not hide M0/M1/M2 failures behind M3.

**Exit:** user-visible improvement demonstrated with real unseen questions and independent evidence-grounding checks. If 1.5B cannot meet target, label this gate FAILED / model-limited and preserve the safe assistant rather than claiming general LLM intelligence.

---
## F5 — Prove Ansible Studio actually uses all 141 published methods (remaining E8)

**Distinction:** V9 publishing 141 bindings does not mean every operation has been exercised from a user's natural-language Studio request, and **native vendor CLI is not the same as a certified Ansible playbook**. Preserve both truths.

### F5.1 Actual user workflow, not only isolated renderer calls

For all 47 canonical operations × Cisco IOS-XE 17.9, Juniper Junos 23.4 and Huawei VRP 8, run a **controlled compatible-profile Studio journey**:

```text
natural-language request
  → intent + requested action recognition
  → target resolution / compatibility
  → V9 published operation retrieval/selection
  → schema-driven parameter extraction
  → clarification for missing/ambiguous fields
  → exact native V9 preview on selected profile
  → trustworthy status/caveat/provenance
  → user-reviewed, UNSAVED Studio draft
  → no autonomous Save/deployment
```

Start with machine-driven gateway/Studio API journey tests for all 141 (real services, deterministic fixtures) then representative actual browser journeys for every risk family and each vendor. Avoid claiming 141 browser-user journeys unless actually executed. Introduce tool-test isolation where an ordinary recorded R1/R2 lacks target IOS-XE 17.9 compatibility; use a controlled compatible test inventory, **never change real recorded device identity to make the gate pass**.

### F5.2 Correct prompt/parameter/target behavior

Test explicit and implicit requests, aliases, existing objects, unknown vendor/version, missing parameters, multiple operations and requests mixing read and generation. Example: “For the compatible edge Junos device, add an OSPF area and make the static return path; explain what assumptions you used.” Both operations must be separate validated tasks, with correct per-operation parameters and explicit clarification for unavailable facts. Platform required fields must come from the active compiled profile schema, not guessed defaults. Preserve typed derivation and exact unit conversion for QoS.

Test source-confidence boundaries: a config generator can propose an implementation based on engineer-published knowledge but cannot claim physical device acceptance; when target profile is incompatible, clarify or select another legitimate target, **not relabel**. When a command’s semantics are only engineer-published, show that level honestly but do not block ordinary native preview due to missing external certification.

### F5.3 Unsaved editor edits and handoff

- Send actual current Monaco text, selection, file identity and buffer revision to the shared gateway. Reject stale or cross-owner proposals. Preserve line endings, indentation, unrelated BGP/OSPF sections, Unicode and comments.
- Review proposed diff against exact base; Accept/Reject/Undo; Save only on explicit user action. Verify rejected proposals leave the unsaved buffer untouched, accepted proposal modifies only intended portion, undo restores, and new subsequent edits invalidate old revision proposals.
- Floating AI **Review in Ansible Studio** must create only an authorized, contextual, *unsent* Studio draft; it must not trigger a hidden generation request or record an unintended engineering turn. No duplicate gateway/client autosave history writes.
- Draft Change Summary must remain bounded/scrollable; focus management and narrow/mobile layouts must still work.

### F5.4 Add genuine Ansible playbook checks in the correct lane

Native V9 CLI publication does **not** imply `ansible-playbook --syntax-check` success. Inspect existing playbook variants; independently test available safe playbooks with a contained local validation runner, valid YAML, variable handling, task/module mapping, idempotency where feasible and no real device connectivity. If Ansible tooling is not installed, present `NOT_RUN_TOOL_UNAVAILABLE` rather than a fabricated pass. Never gate already authorized **native** publication on absent playbook tooling. Keep playbook generation/certification clearly labelled and independently evaluable.

### F5.5 Demonstrate knowledge authoring remains data-driven

In **isolated temporary authoring workspace only**, define a new operation absent from the original 47 (e.g. `configure_ntp_server`), assign parameters, let V9 compile JSON Schema, add one compatible vendor template, preview, Validate, use authenticated publication flow, activate isolated immutable test release and retrieve/render through Studio. No hardcoded new runtime Python case. This validates the intended senior engineer workflow without altering the ordinary 141 baseline. Restore only isolated test state, not live authoring DB.

**Exit:** actual gateway-through-V9 positive/negative/profile checks for 141 combinations, representative controlled browser workflows for all three vendors and key categories, exact revision-safe editor operations, no device write, no duplicate conversation writes, optional Ansible checks honestly classified, and a verified isolated brand-new-operation workflow.

---

## F6 — Finish source availability, document handling and assistant modes

### F6.1 Evidence versus source failure contract

Define a shared tool-observation envelope with device/source IDs, observed_at/captured_at, current-vs-saved-vs-planned, auth scope, mode, freshness, `AVAILABLE|MISSING|STALE|CONFLICTING|ERROR|UNSUPPORTED|NOT_QUERIED`, citations and coverage. Keep original raw evidence retrievable for audit. This prevents “no logs returned” from becoming “there were no logs” or “device is healthy”. Do not erase known facts because one other source is unavailable.

### F6.2 Normal and simulated operating modes

Compare the same permissible questions in isolated **development simulation** and genuine **ordinary mode** with real configured readers. Where a service (InfluxDB, SDN controller, syslog, live network) is not available, verify an honest source-unavailable answer rather than inventing results. Do not claim full real-network awareness from planned topology, imported captures or synthetic telemetry. Validate exact source mode banners and user-visible provenance in both Floating AI and Studio.

### F6.3 Documents, PDF/OCR, diagrams and attachments

Test a readable-text PDF, scanned-text PDF, noisy image, multi-page partial upload, no attachment, stale attachment reference, two-file conflict, and an image/diagram that the local installed stack cannot interpret reliably. Ensure authoritative `document.read` only when relevant, bounded extraction and correct page citations; no hallucinated image comprehension or false “page 4 says” if page cannot be parsed. Reuse existing reader/OCR capability and mark unsupported languages or image understanding honestly. Test owner/session boundaries and upload failure cleanup.

### F6.4 Multi-turn history durability

Compare first request, follow-up with pronouns, corrected target, source availability change and mode switch. Owner-bound checkpoints and historical turns must remain coherent across frontend refresh, backend restart and cancelled model call. Test stale reference invalidation and contradictory new evidence.

**Exit:** normal-vs-sim evidence separation correct, document/attachment limitations degrade gracefully, source errors never become fabricated healthy facts, multi-turn context survives expected lifecycle.

---

## F7 — Close browser/UX, clipboard, service reliability and Windows-specific issues (remaining E9)

### F7.1 Whole response Copy

- Verify shared Markdown renderer, whole-response Copy preserves full Markdown/text including fenced code, indentation, CRLF, Unicode and multi-block answers. Per-code Copy must copy only corresponding block. Clipboard denied/unavailable must show appropriate error rather than “Copied”.
- Use ordinary utility/component tests for exact clipboard API calls, then **real Windows clipboard** read-back/paste in a permitted nonvirtual browser/manual test. Record `clipboard-write` and `Ctrl+V` result, including content/hash, independent of toast. If the only available browser uses a virtual clipboard that cannot paste despite accepted API writes, preserve that test `BLOCKED_ENVIRONMENT` and report real OS test `NOT_RUN` until actually performed. Do not change product code purely to appease a broken virtual clipboard harness.

### F7.2 Normal/external-service adapter parity

Test ordinary frontend on its proper ports, correct backend and Ollama owner processes; source provider unavailable, timeout and recovery; app refresh; pending requests; static build/production serve; **actual** connected external source only when existing configuration/authorization makes it available. Simulated mode must not silently mask external-service failures.

### F7.3 UI consistency and accessibility

Preserve optional collapsed template-check panel, 32rem Draft Change Summary maximum/24rem scrolling, Markdown/code syntax styling, narrow floating panel, theme contrast, keyboard navigation/Escape, mobile overflow, text wrapping for long native config, and screen-reader/labeled error states. Test actual viewport scroll with keyboard and mouse; confirm page scroll does not become trapped.

### F7.4 Backend/cancel/restart resilience

- A slow model must be cancellable, recover to source-grounded fallback when permitted and leave no orphaned owner-bound turn/partial editor update.
- Avoid concurrent Ollama model and Chroma full-build contention in latency benchmarks; repeat under representative load separately. Respect approved per-stage maximum calls/context/wall time and clear timeouts with source continuity.
- Resolve retries and locks according to actual process ownership, journal state and active pointer; no indiscriminate deletion. Verify old frontend/server listener recovery only with owner check; a closed browser error tab does not prove browser access is disabled.
- Ensure fresh browser navigation leaves ordinary SQLite table hashes identical for non-mutating operations; authorized assistant turn history should mutate only its intended tables.

**Exit:** responsive UI, correctly scoped copy behavior, meaningful failures, stable history/buffer, normal-mode tests run where providers exist, no environment limitation mislabeled fixed product code.

---

## F8 — Verification matrix, independent benchmarks and failure-driven corrections

### F8.1 Separate coverage axes (never combine them into one deceptive score)

| Axis | Evidence required | Current known limit |
|---|---|---|
| Published V9 methods | active manifest, exact profile/binding, Chroma, runtime preview | 141/141 already reported PASS |
| Native-output quality | independent reviewed expected outputs + branch/negative tests | only supplied fixtures broadly PASS; possible OSPF malformed oracle |
| Device certification | actual vendor platform/device acceptance | NOT_VERIFIED / NOT_RUN; not prerequisite for publication |
| Real Ansible playbooks | separate executable/syntax/integration validation | not implied by native CLI |
| Intent routing | matched baseline, frozen unseen prompts, actual selected tools | 52/60 vs 57/60 previous |
| Adaptive investigation | whether chosen follow-up read changes inference correctly | incomplete / fallback-heavy |
| LLM reasoning/synthesis | independently graded real M0/M1/M2, fallback tracked | 85% target not established |
| Simulator | independent truth/oracle in mixed-vendor paths | partial conformance |
| Studio E2E | real request → V9 → clarified reviewed unsaved preview | all-binding journeys not run |
| Frontend and Copy | real interaction + actual clipboard readback where possible | virtual clipboard BLOCKED; scroll verified |
| Ordinary data integrity | compare pre/post snapshots for allowed mutations | previous protected stage intact, historical session fingerprint delta |

### F8.2 Acceptance suite composition

Build a reusable `docs/evaluations/phase_f_cases.json` and immutable `phase_f_holdouts_v1.json` with per-case: `id`, `assistant`, `scenario`, `starting_state`, `prompt(s)`, `required/allowed/prohibited tools`, `authorized effects`, `expected_observations`, `independent_expected_claims`, `clarification`, `uncertainty`, `mode`, `source timestamps`, `permitted fallback`, and a stable hash. Include paired negative cases and cross-vendor swaps. A route-only rubric should not require unnecessary inventory reads; a source-equivalent legitimate tool must not be penalized if it provides identical authorized facts.

**Suggested minimum new benchmark groups:** 20 conceptual/no-tool; 20 inventory/topology; 20 protocol/config/history; 15 documents and attachment edge cases; 15 Studio read/edit/generate; 30 implicit/compound/multi-turn/investigation. Totals ≥120; actual distribution can increase for balanced vendors, but freeze before first model run and disclose decisions. Add ≥30 realistic scenario-rich answer-adequacy tasks (not necessarily the same as routing prompts) and ≥10 permission/adversarial cases. Avoid synthetic prompt templates differing only in one device name as evidence of generalization.

### F8.3 Test against correctness and useful behavior

For each end-to-end case, capture:

```text
input / resolved user context / allowed scope
→ source/tool intent plan (model vs deterministic origin)
→ tool requests and actual observations + timestamps
→ whether follow-up retrieval was justified and used
→ independent factual claim checklist
→ emitted draft with source citations
→ verifier decisions, rejection/repair/fallback
→ final answer or proposal, response latency
→ user-visible UI / buffer / release effects
```

No source fabrication, no unauthorized changes, no cross-owner leakage. Grade prompt compliance, correctness, useful inference, uncertainty, tool sufficiency, and exact-effect boundaries independently.

### F8.4 Meaningful acceptance thresholds

- **Knowledge:** 141 active distinct bindings remain; all verified software compilation/render/negative/profile tests pass. Corrected known OSPF line format through actual active runtime; any future native edit has new valid release and rollback. No claim of Internet/device certification if absent.
- **Routing:** historical exposed 60 ≥57/60 after repairs; fresh ≥120 cases ≥90% source routing and no material regression against matched legacy baseline. More stringent improvement goal >57/60 historic and >paired baseline fresh; report uncertainty.
- **Adaptive reads:** predefined information-gap cases show expected targeted follow-up or targeted clarification, not blind overretrieval or false source-confidence.
- **Model synthesis:** independently assessed real-model full agent M2 ≥85% adequate on untouched cases, no critical unsupported operational claims accepted, with actual M2-vs-M3/fallback attribution. If unattainable on 1.5B, gate remains failed and is reported honestly while factual safety stays strong.
- **Simulation:** independently verified expected forwarding/ACL/VRF/protocol/performance results and explicit unknown/bounded behavior.
- **Studio:** all 141 controlled real-service generation journeys pass at least gateway/Studio integration level; representative per-vendor browser E2E passes; exact-base buffer safety and no unauthorized device writes.
- **UX:** browser completion for accessible paths, genuine clipboard roundtrip or well-evidenced environmental blocker, normal-mode adapters verified or documented source availability gaps.
- **Data:** verified staged checkpoint and protected data preserved, no accidental Save/deploy/commit. No fatal security/authorization regressions.

A blocker does not vanish by lowering acceptance criteria. If model-capacity prevents ≥85%, leave `F4=FAILED_OR_BLOCKED_MODEL_CAPACITY` and `Phase F complete=false`; deliver all other verified improvements plus a precisely scoped future model-upgrade suggestion if useful.

---

## F9 — Final acceptance, controlled rollout and handover (remaining E10)

### F9.1 Ordered final proof sequence

1. Cold-start ordinary app using its existing local start mechanism; inspect Ollama and both B3 flags in diagnostics.
2. Confirm active V9 release/manifest/index/141 bound profiles and engineer-authorized lifecycle; record prior release anchor.
3. Validate original malformed OSPF samples via **actual currently active V9 rendering** plus independent oracle. Correct/publish first if still broken.
4. Perform cross-vendor static, OSPF, BGP, VLAN, ACL/QoS, IS-IS and management-security samples, including negative schema/profile cases.
5. Run all 141 controlled compatible-profile natural-language Studio generation journeys; record any failures and fix until targeted cases and whole affected suite pass.
6. Run representative actual browser Studio revisions and Floating→Studio unsent handoff; ensure no save/deploy, correct history, safe Undo/Reject.
7. Run new frozen routing/intent benchmark with equal baseline/candidate environment; inspect every missed case, classify, fix generic causes and **rerun on a genuinely new holdout** after any tuning. Preserve original first-run result unchanged.
8. Run real qwen M0/M1/M2/M3 benchmark serially with model-only, curated evidence, full B3 and fallback distinctions. Inspect exact user-visible text and unsupported claims. Correct and retest during run, not only after aggregate scoring; score untouched holdout only once for final claim.
9. Run independent multi-vendor simulator conformance and normal-vs-sim provenance checks; verify real adapters where available and honest unavailability otherwise.
10. Run TypeScript/build, backend regression/security/fixture suites, UI interactions, real source/clipboard checks possible in environment, restart/recovery, isolation and SQLite consistency.
11. Verify no stage/commit/reset, no modified immutable old release, no copied acceptance DB, no physical network effect and no lost ordinary session. Record exact git index and DB/table deltas from F0.
12. Update one concise authoritative Phase F report and checkpoint; categorize outcomes by evidence and limitations. Do not bury newest results under a historical status section without clear chronology.

### F9.2 Rollout behavior

Use isolated test workspaces for correction drafts and acceptance releases, but **do not conflate isolated success with ordinary activation**. If a native template changes, an authorized engineer Publish/Activate action may create a new ordinary immutable release, with expected-active guard and rollback. If AI planning/synthesis remain enabled per user preference, retain verifiers and fallback even if quality is still subtarget; show diagnostics/risk status without silently reversing `.env`. No background deployment, real SSH or device configuration.

### F9.3 Required final artifacts

| Artifact | Minimum content |
|---|---|
| `docs/PHASE_F_IMPLEMENTATION_RESULTS.md` | Executive outcomes, what changed and passed, remaining failures, user-visible before/after examples, source revisions |
| `docs/PHASE_F_RUNTIME_AND_RELEASE_REPORT.md` | current immutable V9 pointer/hash, counts, lifecycle audit, new authoring revisions, rollback, app flags, service mode |
| `docs/evaluations/phase_f_case_registry.json` | frozen cases, clean scoring definitions, independent truth, exposed/holdout split |
| `docs/evaluations/phase_f_routing_results.json` | 60 historic vs matched baseline + new holdout, per case tool requirements, model calls and timing |
| `docs/evaluations/phase_f_model_quality.json` | M0/M1/M2/M3 true scores, accepted/rejected claims, fallback and adequacy per case |
| `docs/evaluations/phase_f_native_output_audit.json` | 141 matrix, output anomalies, fixed test or template, reviewer status, branch coverage, release state |
| `docs/evaluations/phase_f_simulator_conformance.json` | independently expected paths/behaviors, known/unknown and source/seed hashes |
| `docs/evaluations/phase_f_studio_141_results.json` | real controlled service journey results, actual profile, clarification, preview and no-save proof |
| `docs/evaluations/phase_f_stage_state.json` | F0–F9 per-stage PASS/FAIL/BLOCKED/NOT_RUN with evidence links |
| `docs/PHASE_F_CONTINUATION_CHECKPOINT.md` | exact last passing iteration, working tree state, known blockers, commands to resume, next minimal fix |
| `tmp/phase-f/iterations/*` | raw outputs, screenshots, junit, logs, profiler/call traces, original red tests, subsequent green reruns |

If repository conventions use different directories, respect their existing layout. Keep ignored heavy run artifacts out of the staged code unless user asks; cite exact paths/hashes in reports. Avoid markdown links to files that do not exist. Do not automatically commit or stage unrelated changes.

### F9.4 Unfinished-work tracker and stop conditions

Each issue uses `NOT_STARTED → REPRODUCED → PATCHED → TESTING → VERIFIED` or `BLOCKED`/`FAILED`; every transition has timestamped evidence. An entire stage is not `VERIFIED` until its compulsory end-to-end paths pass. **Phase F is complete only when every mandatory stage passes**; if an inherently small-model reasoning limit remains, report that limitation plainly and do not create deceptive 100% completion. Work on independent non-blocked stages may continue, but no untested patches should accumulate.

---

## 2. Priority order, dependencies and efficient iteration batches

| Order | Cohort | Why first | Exit before next dependent cohort |
|---|---|---|---|
| 1 | F0 preserve + inspect baseline | prevents accidental damage to published catalog/data | pointer, data, flags, staged hash and tests recorded |
| 2 | F1 reproduce OSPF/fixture issues + quality oracle | avoids calling flawed command renders correct | independent native samples and existing 141 regressions pass |
| 3 | F3 source-selection specific failures + typed traces | wrong source blocks useful LLM reasoning | legacy 60 recovered and basic cross-source integrations pass |
| 4 | F2 scenario oracle expansion | supplies controlled varied evidence to test adaptive investigations | independent forwarding/protocol facts available |
| 5 | F4 model synthesis and evidence improvements | can now test real model on correct selected evidence | fresh M0/M1/M2/M3 evidence, correction loop and adequate responses |
| 6 | F5 Studio all-binding journeys | makes published knowledge user-visible and reviewable | 141 controlled journeys, editor safety, browser samples |
| 7 | F6 normal/sim/doc/multi-turn modes | stops hallucinated source claims | provenance, unavailable/partial source tests pass |
| 8 | F7 UI/clipboard/stability | closes actual browser usage and failure handling | genuine browser tests or explicit environmental blocker |
| 9 | F8/F9 final freeze/complete acceptance | verifies no isolated feature broke whole system | final evidence, flags and data integrity pass |

F2 and F3 may run in parallel only if their environments and files are isolated; **do not concurrently run real qwen synthesis benchmarks and heavy release embedding/builds** when latency comparison matters. Work may iterate back to earlier stages after a failing cross-boundary test. A milestone is never marked green merely because its implementation task was attempted.

---

## 3. Concrete evaluation journeys to run and repair

These are **test designs**, not assertions that ordinary network devices currently have the requested state. Use controlled compatible inventories and independent ground truth where needed.

| Journey | Prompt | Expected observable behavior |
|---|---|---|
| Implicit outage | “The branch has been unstable since yesterday. Find out what's changed.” | resolve branch/time, inspect authorized current/saved captures, logs/telemetry/state as available; distinguish absence/staleness; compare explanations; ask clarification if underdetermined |
| Tool-vs-concept | “Why does OSPF need a router ID?” | general conceptual explanation; don't claim to read live OSPF or V9 unless user requests published contract |
| Published schema | “What inputs does the published OSPF operation need for Junos?” | `knowledge.search`/actual active V9 profile, not real router state or automatic code generation; name required and optional fields accurately |
| Topology paraphrase | “How does Core-Birch reach Edge-Cedar?” | topology/path-specific source, correct identity references; don't interpret device name as role filter |
| Compound | “Compare saved BGP config to peer state and recent syslogs; what seems wrong?” | configuration + protocol state + syslog, all scoped, decision-dependent follow-up; evidence-qualified causes |
| Conflicting evidence | “Logs say the link dropped, but counters still look normal. Which is right?” | temporal/source comparison; don't invent definite answer without freshness or link identity |
| Missing reader | “Show me this morning's live CPU and syslog for R2.” | use actual readers; if disconnected, explicitly separate unavailable from healthy/zero records |
| Mixed simulated fault | “Why can't the VRF client reach the external prefix but other VLANs can?” | correct independent VRF/ACL/return path oracle, targeted evidence and unknown if unsupported |
| Studio multi-op | “On the compatible Junos edge add OSPF area 1 and a backup static route.” | two operation tasks, parameter clarification and exact released templates; no automatic Save/device action |
| Studio unsaved edit | “Change only the BGP neighbor to 192.0.2.44; don't touch OSPF.” | exact current Monaco text + selected revision; diff proposal; Accept/Reject/Undo; unrelated lines byte-identical |
| Studio ambiguous | “Fix the BGP issue in this file.” | inspect editor, identify plausible issue and ask for missing intended behavior; no arbitrary rewrite |
| Floating handoff | “Prepare a reviewed correction in Studio, but don't apply it.” | contextual unsent draft; no engineering turn generated prematurely, no saved file/device write |
| NTP extensibility | “Create a new NTP operation as senior authoring knowledge.” | isolated new category/op/mappings/schema/template/preview/authorized publish without new runtime code |
| Real model fallback | model outputs wrong OSPF uniqueness or static route | verifier rejects unsupported claim, returns useful correct/evidence-limited answer, records model failure instead of success |
| Device incompatible | R1 recorded IOS version differs from published IOS-XE17.9 binding | clarification/incompatibility, not inventory spoofing or unapproved generic fallback |
| Clipboard | Copy a multi-code-block response and paste | exact text roundtrip in real clipboard; virtual automation blocker reported separately |

For each journey: create a *positive*, an *ambiguity*, and an *adversarial/negative* sibling where appropriate; inspect precise selected sources and final user-visible behavior. If a journey fails, **fix it in the same iteration** and retest rather than recording the journey as “implemented.”

---

## 4. Explicit scope exclusions and truthfulness safeguards

- Do not promise unrestricted/general intelligence, perfect implicit intent or production-grade network diagnosis from a 1.5B local model. Improve and measure the combined system; do not pretend orchestration alters model weights.
- Do not install a stronger model; comparison may be noted as a future option only.
- Do not require internet/vendor documentation, device testing or separate engineer sign-off before **authorized native V9 publication**. They can remain optional evidence labels and separate certification paths.
- Do not deploy configurations or run device-changing commands. Floating AI remains read-only; Studio only proposes/edits reviewed local buffers.
- Do not imply 141 native command paths are certified **Ansible playbooks** or physical-device configs.
- Do not introduce a second source-of-truth, vector catalog, agent framework, duplicated review database or runtime compiler.
- Do not silently mutate or reclassify ordinary R1/R2 platform/version data to make published profiles match.
- Do not weaken authorization, sandbox, schema or immutable-release integrity to satisfy a test.
- Do not use retrieved private files or fabricated web sources as verification in place of actual repo/runtime checks.
- Do not auto-commit, reset, stage unrelated files, overwrite protected histories, or conceal earlier failing evaluations.

---

## 5. Codex implementation directive — executable instruction

> **Read this entire document and the current Phase E reports, then execute it directly.** This is not a request for another proposal, tutorial or documentation-only change.
>
> **First protect the real current state**: the 141 active V9 bindings, authenticated simple Publish/Activate authority, the user's enabled planning/synthesis on `qwen2.5:1.5b`, 52-file staged checkpoint, ordinary SQLite conversations/inventory, existing unsaved Monaco buffers, old immutable rollback release and Windows services.
>
> **Implement all remaining F0–F9 work in small coherent batches. After EACH update, run the actual relevant tests and inspect real results. If any test, CLI rendering, model decision, browser action or source/data-integrity check fails, reproduce the root cause, fix it immediately, add a regression and rerun it plus affected neighboring tests before moving on.** Do not defer repair to final acceptance; do not weaken tests, revise scoring after seeing holdout output or relabel fallback as model success.
>
> **Do not rebuild/reapprove all 141 native operations:** they are already published. Reproduce the suspicious Cisco/Huawei OSPF golden outputs, verify whether the active runtime really emits them, correct actual defects through the existing V9 authoring and authenticated Publish/Activate lifecycle, then recheck 141 coverage. Keep external certification optional and unchanged native publication authorization.
>
> Prioritize true end-to-end intelligence improvements: implicit/multiple intent identification; correct authorized source selection; useful bounded adaptive tool calls; actual `qwen2.5:1.5b` evidence-grounded synthesis with natural explanations, meaningful uncertainty and factual guards; schema-driven multi-operation Studio generation; actual unsaved Monaco diff reviews; mixed-vendor simulator conformance; normal-vs-development sources; documents; browser resilience and genuine clipboard checks.
>
> **Honest baseline:** original Phase E candidate routing 52/60 versus 57/60 legacy; original 60 now exposed regression cases; independent ≥85% real M2 answer adequacy not established. A passed targeted rerun is not a new holdout improvement. Retain new model flags enabled as requested, but always verify/reject unsound model outputs and report fallback separately. No stronger model download.
>
> Persist `tmp/phase-f/iterations/` evidence after each passing or blocked patch. Maintain a live issue table (`PASS/FAILED/BLOCKED/NOT_RUN`), stage evidence, actual commands, copied error traces and reproducible checkpoints. Run actual service/browser/renderer acceptance, not mocks alone. Never claim tests were performed if they were not.
>
> Only finish when all mandatory F0–F9 gates have actual evidence, and produce the Phase F results, release report, evaluations and checkpoint specified above. If a small-model or external-browser limitation remains despite genuine repair attempts, clearly report it as unfinished rather than declaring completion. **Implement and test now.**

---

## 6. Definition of “finished”

This iteration is finished when an unfamiliar user can express a network engineering goal without naming specific tool calls, both assistants reliably determine the right sources, retrieve and analyze relevant evidence without fabricating facts, present a natural explanation or safe Studio proposal, and the **actual active** V9 release correctly supplies engineer-published native methods for the compatible platform. This outcome must be demonstrated with **new unseen tasks, independent expectations, actual model calls, runtime/service/browser evidence, and repaired regressions**—not simply asserted from test fixture counts.

The correct final result is **a working, measured assistant with explicit boundaries**, not the label “unrestricted LLM.”
