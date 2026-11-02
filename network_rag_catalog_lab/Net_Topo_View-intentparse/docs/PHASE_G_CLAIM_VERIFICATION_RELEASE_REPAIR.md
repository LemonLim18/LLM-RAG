# Phase G — Claim verification, correction and release repair

2026-10-29. BOUNDED REPAIR FINISHED — RETAIN REPAIRS; KEEP COMPLETENESS DEFAULT OFF. No new Phase G stage closes. Original 4/8 control versus 0/8 enhanced scores are frozen, not rescored. Audit: `tmp/phase-g/iterations/20261029-claim-release-repair/`. Curated result: `docs/evaluations/phase_g_claim_release_repair_result.json`.

## Pre-edit forensic diagnosis

No application source had been edited when the following replay was recorded. `forensic-current-replay.json` traces every enhanced CF-01–08provider response, exact original record packet, core/auxiliary parsing, present checker result and old release. It references immutable original files by SHA256and JSONpointer. Source-derived judgments are implementation-assistant graded, independently checkable, not blinded/external.

| Case / requested outcome | Actual evidence / missing material | Original prose and claim correspondence | Parsing / binding / real contradiction | Correction and final release | First causal boundary / still current? |
|---|---|---|---|---|---|
|CF-01 broad failed flow, no-shutdown, captures, inspection purpose|All7families; initial8logrows truncated; typed optical-order-212reference unresolved, then actual syslog read supplies inspection intent.|Initial draft incorrectly says no inspection purpose and overstates what equal artifacts exclude. Revised prose incorporates purpose and distinguishes physical uncertainty. Claims are paraphrases, not exact answer spans.|Core JSON valid in all3reasoner responses; third has auxiliary schema errors. Current hop binding is fixed; event-message string under incident_occurred cannot be mechanically certified. No contrary event fact is established.|Server follow-up justified and useful. Subsequent whole-answer regeneration for insufficient event support is unjustified; an invalid revision ends in whole-answer withholding.|Initial evidence gap/model premature completion; final failure primarily checker/correction/release. Event insufficiency-as-conflict and auxiliary coupling remain.|
|CF-02 state-only port states/prefix and significance|Actual named port admin up, oper down,10.71.2.1/30; no config/log reads needed.|Useful correct explanations through all4drafts. Declared prefix sometimes categorized as oper-state but explicitly uses prefix field.|All core/auxiliary JSON valid. Old checker compared prefix to down. Current declared-field fix supports all claims; no actual source contradiction.|Four revisions were unnecessary, final withheld because of old false conflicts.|Historical field-selection defect already fixed; do not repeat it. Current classification/release design still conflates other unsupported metadata with contradiction.|
|CF-03 state-only egress policy, return delivery, BGP limitation|State contains exact Transit702/Ethernet1/2 egress deny and delivered return; no BGP session observation.|Raw prose locates correct fault and does not invent BGP state. Auxiliary numeric device/port identifiers violate string contract.|JSON/core valid; full contract invalid solely in auxiliary declarations. No source contradiction is proven by numeric metadata.|Provider rejects whole output before decide can preserve its valid core. No answer is released.|Current auxiliary/core schema coupling. Preserve strict identifier typing; validate auxiliary fields independently.|
|CF-04 inventory/planned peer ownership, prefixes and VRFs|Inventory and planned links contain both same-named ports, distinct VRFs and actual different-named peer.|First prose correctly describes owners, addresses, VRFs and planned-not-operational limit. Peer declaration uses an uncheckable free string without field.|First core/auxiliary valid; current receipt-to-port fix supports address claims. Peer string remains insufficient, not contradicted. Second response is malformed JSON.|Unnecessary correction turns useful prose into invalid JSON; prior core then withheld.|Receipt binding historical fix exists. Current insufficiency-as-conflict and final-release policy remain defective.|
|CF-05 running history, staged file, exact applied-event versus observation window|Current/running12:00and14:00, staged saved11:00, verified applied13:00, full directional calculation.|Main event/commands/hop facts correct; temporal description less precise than required and wording risks conflating staged description differences with applied changes. Prose repeated across revisions.|All4core/auxiliary outputs parse. Current failed-hop alias fix works. Two drafts still get false identity conflicts because a device-wide config has no port ID; absence is not a different known owner.|Unnecessary repeated correction does not improve prose and ends withheld.|Remaining config-granularity binding defect plus genuine partial temporal interpretation; not solely model or solely checker.|
|CF-06 link/state disagreement, counters and model scope|Topology/state returned; telemetry was wrongly filtered to its identically named category, excluding actual counter row.|Prose correctly reports no counter in actual packet but cannot perform requested loss calculation; declared state claims supported.|Valid core/claims; no contradiction needed. Current family-permission fix already exists.|Partial released answer accurately describes missing supplied counter but task remains incomplete.|Historical source-filter defect already fixed; do not manufacture missing counter evidence into the old packet.|
|CF-07 config/state with unavailable logs and OSPF caveat|Current interface text/state and unavailable syslog reach model.|Raw explanation has correct settings/availability but does not clearly resolve no-shutdown/route versus adjacency; optional vrf field contains invalid JSON syntax.|Entire JSON document malformed, not merely a typed auxiliary value. No valid parsed core exists.|Explicit incomplete result is appropriate; do not salvage arbitrary malformed JSON or count it as successful reasoning.|Model core serialization failure remains; preserve raw response and report separately from semantic error.|
|CF-08 owned-context advice, no new reads|Prior owned configuration retained; no new readers execute.|Useful proposed checks, but overclaims physical/framing health from recorded state. No auxiliary claims due advisory contract.|Core/JSON valid; nothing declared enables a typed verifier to certify unrestricted advice.|Partial unverified prose released. No justification to claim semantic verification or infer physical health.|Demonstrated model capability/reasoning limit, not a source-loss or composition defect.|

The old0/8does not mean Gemini produced zero useful explanations: four cases are dominated by framework loss (01/02/04/06),05has framework and interpretation issues,03is an auxiliary contract error,07is invalid JSON,08has a real advisory error. These classes overlap; they are not additive percentages or counterfactual success scores.

## Exact current repair boundary

1. `interpret_rest` validates the full reasoner schema, then `model_roles.validate_result` validates it again, and `EvidenceDecision` parses claims with the answer. Independent auxiliary failure destroys the valid core before the graph can assess it.
2. `compatible_claims` includes insufficient support and incompatible source classes in `conflicts`; whole-device config scope can become CONTRADICTED_IDENTITY. Generic event strings/peer prose are not mechanically checkable but enter the same bucket as a source-owned wrong state.
3. `engine.evaluate` regenerates for every conflict; `engine.compose` withholds all prose for any unlocatable conflict. A failed revision can retain a prior core, but its stale review is not explicitly rebound/recomputed against the current evidence.

Targeted changes will separate the six requested verdicts, parse auxiliary claims independently while keeping decision/answer/source/query/clause contracts strict, correct scope ambiguity, and gate correction/withholding only on definite contradictions. Noncertified metadata will remain visible under the existing unverified preview. The same model, graph, readers, A–G coverage, budget and authorization remain. No prose keyword verifier or second planner is proposed.

## Checklist

- [x] Pre-edit preservation and actual eight-case forensic replay.
- [x] Distinguish already fixed historical failures from reproducible present defects.
- [x] Freeze two source-derived conditions before inference; preserve unchanged-build comparison.
- [x] Minimal correction; positive/negative regressions and zero-cloud original-response replays.
- [x] Bounded actual gateway and both-assistant browser checks: 18/32 cloud attempts.
- [x] Complete-answer grades, preservation, stopped disposable services and handover.

## Implemented changes and control flow

The server still owns the original instruction, reader permissions, source identities, budgets and exact synthetic consent. There is one existing LangGraph, no additional planner, reviewer, network parser, RAG index or dependency. Broad coverage, distinct supplementary reads, inventory/topology relationships, artifact comparison, evidence classes and automatic post-draft acquisition remain in place.

| Component | Targeted change |
|---|---|
| `backend/llm/model_roles.py` | A server-authored schema marker separates auxiliary `claims` validation from strict response-core validation. It cannot relax decisions, answers, queries or source contracts. Profile version becomes 3 to invalidate old exact-consent envelopes; the existing limits remain unchanged. |
| `backend/llm/gemini_provider.py` | The same validation boundary is used at the provider adapter. Invalid whole JSON/core still fails; raw output and sanitized diagnostics are retained. Prompts continue to request the complete declaration schema. |
| `backend/llm/orchestration/role_reasoning.py` | `DecisionCore` is validated first; each optional claim is then strictly typed independently. Numeric IDs are not silently coerced. Invalid auxiliary declarations and unknown auxiliary references generate `MODEL_CONTRACT_ERROR` diagnostics; unknown authoritative core sources and invalid executable queries still fail closed. |
| `backend/llm/orchestration/investigation_support.py` | Separate the six verdicts below; preserve source-owned device/interface/VRF/time/direction facts; avoid turning a device-wide artifact's absent port identifier into a different known owner. Event paraphrases and missing bindings remain unverified. Add a narrow release receipt and preserve previously established contradictions when an unchanged assertion survives a revision that drops its declaration. |
| `backend/llm/orchestration/engine.py` | Bind each review to its draft fingerprint. Recompute prior-core review after a failed revision against the current evidence. Only definite contradictions justify factual correction. Retain useful valid prose with explicit limitations; withhold a contradicted assertion only when its exact complete sentence can be isolated safely, otherwise withhold the interpretation. |
| Tests | New `backend/tests/test_claim_release_repair.py`; one existing missing-port expectation in `test_completeness_investigation.py` now distinguishes unknown membership from a proven different owner. Actual wrong-owner/state negative tests remain rejecting. |

The six internal verdicts are `SUPPORTED`, `CONTRADICTED`, `INSUFFICIENT_EVIDENCE`, `NOT_MECHANICALLY_CHECKABLE`, `VALIDATOR_ERROR` and `MODEL_CONTRACT_ERROR`. They are not interchangeable. An internal checker exception is not a factual contradiction; missing evidence is not evidence of falsehood. Claim validation checks declared operands, not every proposition in the surrounding prose.

Correction/release flow is now:

`strict JSON/core → independent auxiliary validation → source-owned operand checks → acquire justified missing evidence → bounded correction of definite contradiction → fingerprinted recheck → preserve/qualify or safely withhold → auditable release receipt`.

Every interpretation still carries the synthetic-development/unverified label. `semantic_certified=false` is explicit, including when every auxiliary operand passes. Retrieval receipts and model clause assessments are not semantic completion proofs.

## Zero-cloud replay and regression results

`forensic-current-replay.json` preserves the pre-edit classification; `forensic-repaired-replay.json` parses the **same original outputs** with the repair. Seven cases contain a valid recoverable core; CF-07's entire malformed JSON remains invalid. CF-04's malformed second draft remains invalid while its earlier valid core is retainable. CF-03's numeric auxiliary identifiers remain invalid, with separate diagnostics instead of destruction of the valid answer core. No original score changes and no inference was rerun for this replay.

This is **not 7/8 successful reasoning**. CF-01's premature absence/continuity wording, CF-05's temporal incompleteness, CF-06's originally missing counter and CF-08's advisory overclaim remain quality findings. The replay does not insert evidence absent from an original packet, complete omitted outcomes or certify arbitrary paraphrases.

The final affected suite executed **159 tests, all passing**, in 25.91 seconds (`regression-final.xml` and `.log`). The earlier 158-pass rerun overlaps and is not added. The original first run's missing-inventory-port expectation failure is retained with its correction. Coverage includes:

- Valid prose with malformed optional metadata; invalid JSON, core decisions, sources and executable queries still rejected.
- Whole-device artifacts versus port observations; correct prefixes, owner aliases, VRFs, timestamps and scoped ECMP branches; genuine wrong state/owner still contradicted.
- Missing evidence, event paraphrases, conflicting observations and validator exceptions separated from definite contradiction.
- No unnecessary model revision for auxiliary errors; genuine contradiction correction receives exact source facts.
- Failed revision retains a safe earlier core; known false prior text remains withheld even if the revised auxiliary declaration disappears.
- Exact safely removable sentences versus unlocatable contradictions, bounded graph execution and adjacent hybrid authorization contracts.

These are application regression results, not intelligence acceptance.

## New frozen matched gateway comparison

Registry: `docs/evaluations/phase_g_claim_release_repair_v1.json`; hash and freeze timestamp: `freeze-receipt.json`. The source-derived deterministic oracle is stored separately in `source-oracle.json` and is not sent to the model. Expectations are independently checkable but implementation-assistant graded, **not externally graded or blinded**.

Both arms enable the existing completeness experiment only in disposable approved contexts. “Baseline” here means **unrepaired completeness code**, not ordinary Qwen-only operation or the historical 4/8 control. Both retain Qwen local, Gemini 3.1 Flash-Lite planning and Gemini 3.5 Flash-Lite reasoning with the same low-thinking/output settings. Input instructions, fixtures, restrictions and grading are matched. Optional model-selected reads differ, so this is not an identical-packet model-capability comparison.

| New condition | Unrepaired | Repaired | Complete-answer assessment |
|---|---|---|---|
| CVR-01, Floating, broad three-device UDP investigation | 22.10s; 5 cloud calls; 8 reader operations; ADEQUATE | 17.01s; 3 cloud calls; 9 reader operations; PARTIAL | Both identify forward Meadow ingress and return Meadow egress, the correct owner, administrative versus operational readiness and actual work purpose. The repaired draw does not explicitly establish the added reference-comment delta against the saved capture and calls the reference a change-event reference without an established applied event. It additionally selects an optional published-knowledge read. |
| CVR-02, Studio, state-only equal addresses on two owners in distinct VRFs | 37.87s; 2 calls; 1 reader; PARTIAL | 13.21s; 2 calls; 1 reader; ADEQUATE | Both retain exact owners, prefixes, VRFs and states. The baseline implies a conflicting assignment from equal addresses despite distinct VRFs. The repaired draw correctly says equal addresses alone establish neither conflict nor delivery. No prohibited inventory/topology/config/log read executes. |

**Complete-task adequacy: 1/2 before and 1/2 after. No demonstrated quality improvement.** All four answers contain model-written interpretation, no deterministic factual fallback. Raw-versus-final prose is preserved rather than replaced by raw tables. Correct declared operands and evidence completeness do not make the two partial answers adequate.

The repaired broad request executes all seven operational families. Its first eight syslog rows omit the purpose referenced in running configuration; the existing server post-draft mechanism independently adds a syslog read, retrieves `review-rx-729`, and the revised model answer incorporates the actual receive-power-margin review purpose and lack of completed repair. This mechanism passes before and after repair. The repair stops treating its uncheckable declaration as a reason for repeated factual regeneration: four reasoner drafts before versus two after in this condition. One observation is not a general latency or reasoning-quality estimate.

Full axis-separated grades, source identities, raw messages, declarations, intermediate reviews and release receipts are in `paired-complete-answer-review.json` and the four unchanged case traces. All new cores/auxiliary declarations happen to be valid; the malformed-auxiliary recovery demonstration therefore comes from historical-output replay and regressions, not invented live failure credit. No new live declared definite contradiction required correction.

## Actual browser acceptance and local controls

Fresh browser initialization initially reproduced the tool asset error, `failed to write kernel assets … (os error 3)`. On continuation `cua.rewriteDocumentation()` succeeded. A subsequent `createBrowserTab('iab','http://127.0.0.1:5174/')` returned `net::ERR_CONNECTION_REFUSED` because the disposable pair had stopped. The first server recovery encountered Vite's sandbox directory-access error. The same existing pair was restarted with approved sandbox escalation; no browser setting, profile, editor state, dependency or ordinary service was reset.

**Browser access is available and both assistants were actually exercised.** This supersedes the earlier tooling-BLOCKED state; authenticated API testing is not being substituted for browser proof.

- Floating: exact CVR-01 synthetic consent → 3 cloud calls → seven operational source families plus optional knowledge and the server supplementary log read → rendered, model-written answer. Correct scoped stops, added reference comment, purpose and physical uncertainty: ADEQUATE.
- Studio: same exact request, separately owned synthetic consent → 3 cloud calls → eight source reads including supplementary syslog → rendered model prose with actual artifact difference and purpose. The answer compresses forward ingress/return egress together instead of clearly mapping them: QUALIFIED/PARTIAL. This is mechanism acceptance, not complete-task quality certification.
- Both displayed the explicit unverified interpretation/verification-limit notices and inspectable sources. The repeated CVR-01 condition adds browser-path evidence, **not another independent generalization case**.
- Fresh Floating API arithmetic uses Qwen and returns 42 with no cloud call. Fresh Studio browser arithmetic also uses Qwen and returns 42 with no cloud call.
- Retained failure: arithmetic after the Studio network investigation is incorrectly planned by Qwen as telemetry (`information_needs: [{domain: telemetry, question: addition of18 and 24}]`). The gateway reads a source and returns a no-observation limitation instead of 42. No cloud inference occurs. The same arithmetic succeeds in a fresh session. This is a context/routing limitation outside the claim-release repair; it is neither hidden nor repaired by adding wording guards.
- The runner's older unknown-`Kite-Edge` Studio control returns unrelated recorded interfaces. It is a failed control, not proof of local-model reasoning; its original response remains archived.

Evidence: `browser-turns.json`, `browser-acceptance-v2/browser-traces.json`, both rendered DOM exports and screenshots. No editor, Accept, Save, publication or execution action was performed. The existing unsaved tabs were left intact; no full ordinary-buffer hash measurement is claimed.

## Release-safety findings

False positives addressed: malformed optional claims suppressing a valid core; uncheckable event/peer assertions counted as contradiction; device-wide artifacts falsely assigned to another known port; stale draft reviews reused after revisions. Invalid whole JSON and unknown authoritative source identities still fail closed.

False-negative/coverage limits remain: a valid declaration can describe only one operand in a multi-part sentence; an undeclared incorrect causal implication can escape mechanical checking. The baseline conflict implication, incomplete artifact comparison and historical advisory-health overclaim illustrate that gap. Supported operands must never certify the entire paragraph. Live model prose remains explicitly unverified, and complete-task adequacy remains independently assessed. The repair does **not** establish that all unsupported prose will be detected.

Genuine declared contradictions are still corrected or withheld in positive/negative regression graph cases, including failed revisions and dropped declarations. We do not claim a fresh live successful contradiction correction when no such condition occurred in the actual small cohort. Safe fallback/withholding receives no model-reasoning credit.

## Quota, performance and preservation

18 actual cloud attempts against the 32-attempt ceiling: baseline 7, repaired 5, browser 6; zero calls in the failed server-recovery run. All 18 returned HTTP 200 and `STOP`; that establishes provider completion, not answer adequacy. Provider totals: 272,796 prompt tokens, 17,511 final-output tokens, 3,279 reported thinking tokens, 293,586 total tokens. No hidden retries, model substitutions or billing-setting changes.

The persistent ledger's combined peak over a conservative 61-second window was seven requests and 104,246 accounted input units, below 15 RPM/150K input TPM; rolling-day count at close 18/500. These are retained-ledger measurements, not assertions about unrelated account-wide traffic. `quota-accounting.json` contains the receipts.

API wall times were 13.21–37.87 seconds. Browser graph elapsed times were 22.79 seconds Floating and 23.36 seconds Studio; UI/render time is separate. No timeout occurred. The existing consented360-second envelope, five role calls, three rounds and 24 reader operations remain; no budget was expanded in this repair.

`preservation-after.json` verifies unchanged HEAD `8a7f86ce4e4d7c12d2e0565bfa53ab64f4ca756d`, staged entries, all 41 ordinary SQLite tables, 1,923 knowledge-release files including all 341 active artifacts, 322 historical JSON records, credential file and root environment. Active release remains `7a14a351e52b49aeb87f65d1192f0937`. The credential remains ignored and was not printed or copied; the new audit text scan found no credential exposure. Existing uncommitted work is preserved. The disposable 5174/8001 pair is stopped; ordinary 5173/8000 was not restarted. No commit, staging, publication, deployment, new model or device operation occurred.

Fresh-process configuration proof is `effective-config-defaults.json`: Qwen2.5 local; existing approved Gemini3.1 planner/Gemini3.5 reasoner roles; completeness OFF, Approach A OFF, previous harness OFF and legacy remote interpretation OFF. Exact synthetic consent is still necessary; a feature flag alone grants no external access.

## Required decisions A–H

**A — Why 0/8?** Auxiliary/core coupling, false conflicts, unnecessary correction and destructive final release compounded missing evidence, malformed whole JSON and actual interpretation failures. The forensic table separates each boundary.

**B — Model versus framework?** CF01/02/04/06 are dominated by framework loss; CF03 by auxiliary serialization/validation coupling; CF05 has both temporal interpretation and binding problems; CF07 is invalid whole JSON; CF08 is an actual advisory reasoning overclaim. These overlap and cannot be converted into a defensible causal percentage or counterfactual score.

**C — What remained after earlier fixes?** Prefix, nested-hop, inventory-receipt and telemetry-family fixes already existed. This task repaired auxiliary validation coupling, missing-scope identity conflicts, verdict classification and revision/release handling. It did not repeat those historical fixes.

**D — Can useful correct prose pass?** Yes: zero-cloud historical cores and real new answers retain original model prose with independent diagnostics and explicit uncertainty. This is demonstrated release behavior, not universal factual certification.

**E — Can real contradictions still be handled?** Positive/negative regressions demonstrate source-owned contradiction correction and withholding, including failed revisions; no fresh live contradiction-correction success is claimed. Unsupported/uncheckable assertions remain unverified, never promoted by schema validity alone.

**F — Automatic supplementary investigation?** Preserved and demonstrated in both matched broad runs and both actual browser paths: the server obtains the referenced purpose beyond the initial truncated syslog page.

**G — Better complete-task performance?** Not demonstrated: 1/2 adequate before and 1/2 after on two new conditions. Browser repetition adds path evidence and one adequate broad answer, not a replacement score or independent condition. Fewer unnecessary revisions in one run is a mechanism result.

**H — Remaining model limitations?** Incomplete artifact comparisons, ambiguous direction phrasing, unsupported VRF/conflict and physical-health implications, malformed core serialization and context-sensitive irrelevant recommendations/reader proposals. Complete evidence, valid clauses and correct operand declarations do not establish adequate reasoning.

## Recommendation, continuation and rollback

**RETAIN the targeted implementation repairs; KEEP COMPLETENESS DEFAULT OFF.** No new full Phase G stage closes. G1–G3 and the previously accepted G8–G10/G12 subwork retain their existing ledger status. G4/G5/G6/G11 remain unaccepted; G7 remains 113/141 with its separate compatibility blockers; G0 historical baseline remains deprioritized and blocked.

The bounded task stops here. Future authorized work should address model/evidence explanation adequacy and context-to-reader alignment using fresh independent conditions, without rescoring this cohort, accumulating phrase guards, enabling completeness automatically or starting a broad qualification prematurely.

Immediate operational rollback is the already-effective `COGNISHIELD_AI_COMPLETENESS=0`; keep `COGNISHIELD_AI_OUTCOMES=0` and `COGNISHIELD_AI_EVIDENCE_HARNESS=0`. Disposable process overrides never changed ordinary environment files. If source rollback is needed, review/reverse only this task's five application-file edits and dedicated test changes against `preservation-before.json`/the frozen baseline manifest; do not reset the mixed working tree or remove earlier uncommitted implementations. Re-enabling a changed profile requires fresh exact synthetic consent. No published release rollback is required because none was modified.
