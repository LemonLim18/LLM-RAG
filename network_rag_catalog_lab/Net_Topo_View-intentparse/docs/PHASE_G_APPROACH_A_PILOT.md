# Approach A bounded pilot — 2026-10-24

## Intended change recorded before implementation

Keep one requested-outcome contract in existing request_contract/IntentPlan/SemanticRoute/AgentState; original prompt and source constraints remain authoritative, model outcome interpretations are proposals. Derive execution from that contract; advice-only outcomes must not initiate readers. Bind returned evidence to each outcome before projection; never globally hide another outcome's records. Track per-outcome answered/limited/fallback/unfulfilled status without claiming semantic certification. Reuse existing synthesis and factual verification; preserve permission, V9, editor and checkpoint boundaries. Gate the pilot behind COGNISHIELD_AI_OUTCOMES=1, default off. No new inference stages, dependencies, budgets, provider settings or production data writes.

## Paired comparison

12 conversations: four causal/source cases (healthy/down/unavailable/conflict), four advice continuations, four compound cases (published+capture, interface+flow, available+unavailable readers, temporal comparison). Balanced Floating/Studio. Exact registry: docs/evaluations/phase_g_approach_a_pilot_v1.json. Existing independently field/arithmetic-checked fixtures reused; implementation-assistant authored/graded, not external blind and not new G11 qualification. Baseline runs before runtime edits; candidate runs identical requests/scenarios/model/budgets after focused tests. Both failures and successes are immutable audit records. Full-answer review separates workflow, evidence, Qwen reasoning, verifier, fallback safety and whole-task adequacy. Original user instructions and all earlier scores remain unchanged.

## Completion boundary

Stop after these 12 paired conversations and focused regressions. No broad120/30 benchmark, automatic release activation, stage closure, source publication, model changes or protected data/editor writes. Baseline and final preservation fingerprints and exact wire inputs/outputs retained under ignored tmp/phase-g/iterations.

## Decision — REVISE; keep the pilot disabled

The paired pilot did **not** improve complete-task performance. Baseline4/12 conversations were adequate; candidate2/12. There are11 distinct prompt/scenario/surface conditions because02/10 repeat the same condition; unique-condition results are4/11 versus2/11. Do not count that repeat as fresh generalization. All adequate answers in both arms are verified factual/fallback paths: **zero adequate Qwen-written reasoning answers**. This is an implementation-assistant graded feasibility study, not external blind certification or G11 qualification.

| Measure | Baseline | Approach A candidate |
|---|---:|---:|
| Adequate complete conversations |4/12|2/12|
| Adequate Qwen-written reasoning |0|0|
| Advice-only final turns with no new readers |0/4|4/4|
| Useful contextual advice |0/4|0/4|
| Actual primary interface-state rows in compound composer packet |0|3|
| Conversation-level chat calls, including setup |25|29|
| Median conversation latency |9.92s|22.39s|
| Minimum execution checks (not task success) |12/12|9/12|

Latency is descriptive: arms ran sequentially, setup model responses differ, and hardware load/warmup were not randomized. No statistical improvement or causal latency estimate is claimed. Both arms usedqwen2.5:1.5b, temperature0,8192context and512outputtokens on every recorded chat call. Graph call/tool/round/deadline/input budgets and existing provider configuration were unchanged. No new inference stage or framework was added.

## Implementation actually tested

- Existing `request_contract.py`: original immutable instruction, server-owned clause IDs, model action/need associations marked as proposals; source receipts and per-outcome disposition, fallback origin and explicit `NOT_CERTIFIED` semantic status.
- Existing `IntentPlan`/`SemanticRoute`: optional requested outcomes in the same planning call. Present reads and future-check recommendations are different actions. Partial/malformed outcome lists cannot erase clauses. Existing source registry, permissions and effect guards still own execution.
- Existing `AgentState`/graph: per-outcome result metadata; typed advisory-only composition has no reader edge and carries only owned prior references/gaps. No new checkpoint schema or database.
- Existing synthesis: preserve primary state observations before duplicate assessments; attach actual evidence by outcome; retain scoped source fallback per outcome. Typed recommended reads are unexecuted suggestions, never capability calls.
- Gateway: consumes a graph-prepared advisory answer through the existing response path. No frontend, V9, model, deployment, editor, dependency or ordinary-data changes.

Opt-in: `COGNISHIELD_AI_OUTCOMES=1` in the evaluator process only. Default remains0; no `.env` or running-server setting was changed. This is experimental, not a promoted intelligence release. Do not enable it for ordinary use based on these results.

## Case-by-case acceptance

W=workflow/source choice; E=actual evidence supplied; Q=Qwen reasoning; V=verifier; F=fallback safety; T=complete task. Full original answers, exact wire packets and these six separate dimensions are retained in `paired-decision-report.json` at the audit path below.

| Case | Baseline T → candidate T | Candidate observed result |
|---|---|---|
|01 healthy directional assessment|PASS → FAIL|W/E fail: only topology, missing state. V/F safely withhold a forwarding diagnosis. Q incomplete; no delivery assessment.|
|02 fault/interface+flow|FAIL → FAIL|Relevant state retrieved (extra topology). E now contains3primary state rows. Q omits requested states/port and attributes ingress failure to Granite-End without a supported ingress-owner record; V accepts. No fallback safety credit.|
|03 unavailable operational evidence|PASS → PASS|W/E correct unavailable receipt. V/F preserve source limitation, no invented failure. No Qwen reasoning.|
|04 conflicting OSPF observations|PASS → PASS|W/E correct peer values/conflict. Existing V/F preserve disagreement and unverified prerequisites. Excessive raw disclosure remains. No Qwen reasoning.|
|05 advice/unknown/Floating|FAIL → FAIL|No new reads, but action=retrieve, history=false. Prior subject/uncertainty disappear in downstream general answer. Generic Q, no outcome verification.|
|06 advice/unknown/Studio|FAIL → FAIL|Same no-reader benefit but generic advice/context loss. Typed advisory composer not selected.|
|07 advice/failed flow|FAIL → FAIL|No new reads, but no concrete scoped diagnostic checks or rationale. Same action/context failure.|
|08 advice/conflicting peers|FAIL → FAIL|No new reads, but prior peer conflict is not used; generic response.|
|09 published+saved comparison|FAIL → FAIL|W/E contain both authoritative sources. Q still omits literal mapping and remaining unknowns. V accepts; `answered` metadata is not semantic proof.|
|10 repeated02 condition|FAIL → FAIL|Same preserved primary states, same incomplete/unsupported model attribution. Repeatability evidence only.|
|11 available capture+unavailable syslog|FAIL → FAIL|W/E regress: model omits one need, global source identity correction replaces configuration with syslog. Per-outcome fallback repeats log unavailability under every clause, safely avoiding invented configuration but misbinding sources. Baseline instead released an incorrect OSPF area.|
|12 temporal capture comparison|PASS → FAIL|W/E regress to inventory. Q invents equality and continuity without captures; V rejects both drafts. F is safe inventory, but cannot answer the task.|

## What improved, and what did not

**Demonstrated architectural benefit:** primary interface rows survive composition (3versus0), and source/outcome receipts make losses inspectable. The corrected packet is smaller7091versus8609characters in02/10. Four advice follow-ups perform no new readers. However, none selects the dedicated typed advisory synthesis path; that path is demonstrated only by injected-model real-gateway tests, not actual-Qwen acceptance.

**Demonstrated complete-evidence model limitation:**02/10 receive all requested Willow-Relay interface states but omit them (normalstop,105tokens);09 receives published requirements and saved command text but omits the mapping/limits (normalstop,114tokens). These are not512token truncation or retrieval-success proofs. Return-path ingress ownership also remains ambiguous at the existing raw calculation boundary; do not attribute that whole error solely to Qwen.

**Architectural limitations/regressions:**

1. The new required outcome schema is not demonstrated in existing few-shot plan examples. All4advice plans use `retrieve` with empty needs; this integration confound prevents treating them as isolated evidence of model incapacity. No prompt repairs were made during or after the frozen candidate.
2. A no-read route with the wrong proposed action still exits into general gateway composition, bypassing outcome completion and reference preservation. The new contract is not yet an end-to-end fulfilment authority on every response path.
3. Tool-level evidence association does not prove field/relationship completeness. Global source refinement can still replace the valid configuration operand with syslog in a compound request. The fallback honestly shows source records but does not correct a wrong association.
4. Structurally accepted model parts can still be semantically wrong/incomplete. `answered` is a model-path disposition with `semantic_completion=NOT_CERTIFIED`; it must not become a completion gate. Correct citations and retained clauses did not solve reasoning.

## Verification and preserved failures

- Initial focused run:51PASS/1FAIL (new test asserted a particular plural word; implementation output was correct). Original log retained.
- A later test edit had a collection SyntaxError; retained and corrected without altering runtime criteria.
- Final affected outcome/source/B2/B3 suite:151PASS. Subsequent focused opt-out/request run75PASS after preserving legacy clause splitting when the pilot is disabled. These runs overlap and are not added as unique coverage. They include ordinary fixture controls plus mock-model integration through both owned assistant surfaces; they do not prove Qwen quality.
- Baseline and candidate each completed12 actual authenticated ASGI gateway conversations using disposable SQLite/ScenarioManager data and real local Qwen. No setup history was fabricated. One paired repeat is disclosed above.
- Expected literals were separately checked against source fields, including down-port state, unavailable state/syslog, actual OSPF area0/router ID198.19.213.1 and capture identity. Not external blind review. No120/30suite or browser acceptance was run.
- Initial sandbox baseline yielded no completed cases; process inspection returned Access denied. Only the two verified evaluator processes were stopped before the authorized rerun. The stall's underlying cause was not established; no ordinary server/Ollama process was stopped.

## Retain/revise boundary

Retain the outcome/evidence observability and primary-record preservation as experimental changes. **Revise before broader implementation or ordinary activation.** First reconcile the model wire contract/examples and reject incomplete read interpretations without losing original context; then scope source binding and composition completion to the original outcomes across all answer paths. This is a recommendation, not further implementation. Do not add another planner, Approach B, phrase-specific validators or a larger model to explain away this failed pilot.

Stop here. No new Phase G stage closes and no earlier failed frozen score is replaced. Further implementation requires explicit authorization.

## Exact execution and preservation references

- Baseline: `tmp/phase-g/iterations/20261024T150654.991164Z-G11-fresh-quality-candidate-3ccfef`.
- Candidate: `tmp/phase-g/iterations/20261024T152118.166815Z-G11-fresh-quality-candidate-631dcf`. The generic evaluator directory name includesfresh; this pilot receives no unseen benchmark credit.
- Decision/initial behaviour/oracles/failed logs/preservation: `tmp/phase-g/iterations/20261024T150603Z-approach-a-pilot`.
- Registry: `docs/evaluations/phase_g_approach_a_pilot_v1.json`; unchanged SHA256`b620dea839c8e9be806fe9a6259fb4c052646c73c800440cd8767ab1f2ca3f6d`.
- HEAD/index/ordinary SQLite fingerprints and active release pointer unchanged;341artifact hashes match. Release`7a14a351e52b49aeb87f65d1192f0937`. No editor/browser operations, saves, server restarts, publication, commits, staging, deployments or downloads. Existing unsaved buffers were not accessed; no fresh UI hash proof is claimed.
- Candidate runtime hashes unchanged during inference. The pilot remains opt-in/defaultoff. Model/provider files and settings unchanged. All evaluator and test sessions from this pilot finished.


## Follow-up — 2026-10-25

Bounded reconciliation: [decision report](PHASE_G_APPROACH_A_RECONCILIATION.md). Original scores unchanged. Paired8baseline2/8→3/8, zero adequateQwenreasoning; final4exposedreruns1/4functionaladequacy fromreaderprojection/qualitywarning, zeroadequateQwenreasoning. Default remains off; semanticrelease unaccepted.
