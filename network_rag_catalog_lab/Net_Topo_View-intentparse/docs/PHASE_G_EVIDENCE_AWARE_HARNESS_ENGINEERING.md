# Phase G — Evidence-aware harness engineering

2026-10-27, Asia/Kuala_Lumpur. **Bounded milestone FINISHED. Retain the harness as a default-OFF experiment; no demonstrated complete-task improvement.** Provider observability is retained. No original G4/G5/G6/G11 gate closes; live MN4 remains unverified.

## Decision and complete-answer results

Six frozen, distinct synthetic conditions were run through the real authenticated gateway in two arms, not substituted with historical scores. Control used the corrected architecture; enhanced enabled only the three metadata components. Same scenario digest/revision, roles, thinking, output schemas, authorization, 120-second deadline and three-call ceiling. Remote planning is the existing direct Gemini3.1 role; legacy optional refinement and Approach A remain0. Gemini3.5 performs evidence reasoning. Ordinary unapproved Send remains Qwen2.5.

| Metric | Control | Enhanced |
|---|---:|---:|
| All attempted user tasks |6|6|
| Fully adequate, complete task/model explanation |**2/6**|**2/6**|
| Completed reasoner interpretations |6|5|
| Adequate conditional on completed interpretation |2/6|2/5|
| Correct required/allowed reader set executed |5/6|4/6|
| Completed evidence coverage for a supported answer/limitation |5/6|4/6|
| Materially missing event/intent evidence |1|1|
| Unnecessary executed readers |1knowledge lookup|1incident lookup|
| Significant incorrect/incomplete model answers |4|3|
| Provider failures, included in task denominator |0|1planner timeout|
| Completed raw prose retained in final composition |6/6|5/5|
| Factual fallback credited as reasoning |0|0|
| Need-more decisions / actual supplementary rounds |0/0|0/0|
| Causal subset adequate (EH01/02/03/05) |1/4|1/4overall;1/3completed|
| Median/max full request seconds |30.864/38.461|29.779/36.977|

These small assistant-graded results do not establish statistical improvement, decline or mechanism uselessness. Conditional quality does not replace the all-attempt denominator. The failed enhanced planner never received harness evidence. Independent planner nondeterminism remains: plans were not cached or fixed between arms. Actual reader operands are identical for EH01/02/04/06; EH03has no enhanced read because of timeout; EH05chooses different incorrect extra readers. Those differences cannot be attributed solely to reasoning metadata.

| Condition | Control full-answer review | Enhanced full-answer review |
|---|---|---|
| EH01: disabled spare while preferred service succeeds; state-only |PARTIAL. Delivered/preferred-path reasoning correct, but forward narrative swaps Transit/Meadow interface addresses.|PARTIAL. Main mechanism correct, but return narrative swaps the same owners/addresses. Extra topology proposal is server-filtered, not a precise raw plan.|
| EH02: TCP delivery versus selectively filtered UDP ECMP; no telemetry |ADEQUATE. Correct policy/owner, successful other branch and returns; no measured-loss percentage.|ADEQUATE. Same supported scoped explanation. No claim that metadata alone caused this success.|
| EH03: saved/current VRF values and unavailable event logs |UNSUPPORTED interpretation: exact values correct, then says active VRF changed between artifact timestamps. A saved artifact is not established prior running state.|TIMEOUT at planning, approximately35seconds, before readers/reasoner. No reasoning verdict.|
| EH04: planned design versus down observed link |ADEQUATE concise planned-design and separately reported observation/time; no claim of physical deployment/cause.|ADEQUATE with clearer explicit design/deployment boundary.|
| EH05: downstream operational fault plus referenced inspection purpose |PARTIAL. Wrong knowledge reader, event never read; a pointer is treated as inspection intent, missing the actual purpose.|PARTIAL. Wrong incident reader. Ledger exposes the missing event and validated syslog/config-change hints, but the model chooses answer and never reads the actual inspection purpose.|
| EH06: owned-context advice, no collection |PARTIAL:0reads and useful checks, but promises interface_state error/MTU/framing information and routing_table proof of protocol exchange beyond those source contracts.|PARTIAL:0reads and useful checks, but overgeneralizes route presence to control-plane functioning and interface-down to a non-routing diagnosis. No actual cause was established.|

The full-answer rubric is strict about reader capability claims even in otherwise useful advice. This is source-derived, independently checkable but **implementation-assistant graded, not blinded/external**. Original prompts, expectations, actual records and raw answers are available for independent review. Model self-assessments marked unsupported interpretations supported; they are not certificates.

## Preserved baseline and exact changes

Starting HEAD `8a7f86ce4e4d7c12d2e0565bfa53ab64f4ca756d`, dirty worktree preserved. Prior12-task scores remain2/12, with7provider failures; old30-task scores remain unchanged. Existing original-clause identities, required/optional needs, query receipts, source permissions, record index and supplementary graph branch are reused. No second planner, RAG store, inference stage, semantic verifier or diagnostic expert system was introduced.

| Component | Changes and existing functionality reused |
|---|---|
| `backend/llm/orchestration/evidence_harness.py` |Pure bounded metadata functions. Reuses response_obligations, registry source aliases, reader_constraints, current record index inputs and validate_additional. No IO, inference, execution or state store.|
| `role_reasoning.py` |Enriches the existing packet after credential-line redaction; preserves raw operands, Slabels, full instruction, original clauses and explicit64000-character failure. Adds failure receipt to existing preview diagnostics. Does not rewrite model prose.|
| `engine.py` |Passes at most3validated reader hints only with remaining call/tool/time budget. Final/advisory paths expose no executable hints. Uses existing error/decision receipts; no new graph nodes.|
| `model_roles.py` |Binds harness version and each component flag to exact owner consent. Adds execution-failure classification, explicitly NOT a semantic verdict.|
| `gemini_provider.py` |Adds classified role-failure receipt to the existing trace, retaining original HTTP/provider category and elapsed time. No transport, schema, role, token budget or retry change.|
| `.env.example` |Documents default-OFF master and independently disableable components. Existing root.env and ignored backend.env are unchanged.|
| Existing evaluation runner |Adds paired toggling with alternating condition order and per-arm role bindings; real API/readers/consent unchanged. Corrected suffixed-file completion counting after the cohort; original mistaken0count receipt is retained, and the seal records12actual files.|
| Evaluation/testing additions |Freeze helper, zero-cloud packet comparison helper, focused harness tests, six source cases plus frozenv1/v2registries and curated result. No expected answer enters runtime/model messages.|

### Retrieval ledger authority

Each existing original clause retains its identity/text, explicit source names, associated receipt-row references, missing reader families, restrictions, requested temporal scope and validated target IDs. Request-scope relevance beyond explicit source naming is labelled unknown, not guessed. Shared receipt entries contain actual evidence IDs, record IDs, availability, source statuses and truncation. Typed depends_on/change_event_ref fields expose actual references; a missing reference has unknown location unless the reader supplied explicit unavailable-dependency metadata.

Statuses describe retrieval only: evidence available, partially retrieved, source not queried, unavailable, or relationship unknown. No returned source, citation, nonempty clause or model assessment proves a conclusion. Prior owned advisory context remains in the existing advisory packet and is not mislabelled a new observation. The ledger does not solve causal relationships or certify per-clause relevance.

### Selective reader guidance

Candidates come from original required needs or typed event references. Event references offer actual syslog/config-change catalog capabilities as **possible locations**, not invented lookup results. Existing registry schemas, target/interface ownership, original source/time constraints, query deduplication and backend validation are reused. Free-text names cannot expand targets; prohibited, duplicate and known-unavailable queries are excluded. Distinct current/historical or category queries on one reader remain possible.

At most3options are shown, further bounded by remaining tool/call/time budget. Hints are never executed by this helper. Schemas are shared once per offered reader, replacing two copies of the entire registry in enhanced reasoning packets. Other model proposals still require the same authorization boundary. The real model independently retains answer/need_more choice.

Engineering review found a legacy availability edge: a failed whole reader without per-category statuses could remain a different-query candidate. A two-line exclusion and regression were added AFTER the frozen cohort/browser;66affectedtests pass. No scores were overwritten and no extra cloud rerun was performed. Browser proofs cover the frozen build; this metadata-only negative branch has deterministic final-build evidence, not a new browser claim.

### Evidence type and provenance

The existing record index gains source-derived modeled/planned/saved/current/historical/observed/unknown labels and actual scenario origin. A small source-row map marks unavailable/planned/observed data where the reader establishes it. Shared definitions distinguish measurements from modeled branches, artifacts from event windows and design from operational proof. Saved configuration is explicitly a saved artifact, not prior running state. Unknown types stay unknown. Direction, VRF, branch and peer operands remain unchanged in raw records. No answer-phrase rejection, hidden diagnosis or semantic repair was added. Semantic preview remainsOFF with the visible unverified label.

## Offline analysis, costs and provider findings

`offline-final.json` reconstructs all5completed historical reasoning packets exactly in control mode. Raw records and source IDs are identical after enhancement. In MNI09the actual missing reference becomes visible with validated syslog/config-change options; this does not establish the event content or a better answer.

| Component alone,5preserved packets | Context delta | Pure serialization median range |
|---|---:|---:|
| Baseline |0|2.05–7.37ms|
| Ledger |+1791to2255characters|6.45–10.38ms|
| Guidance/schema deduplication |−17974to−14336characters|2.27–6.41ms|
| Provenance |+909to2053characters|2.03–7.94ms|
| All metadata together |−15056to−10643characters|6.22–11.20ms|

These are three local serialization samples per packet/mode, not inference benchmarks or capability-validation timings. Use `metadata-overhead-v2.json`; the earlier timing file incorrectly included inactive hints in control/component inputs and is retained but excluded from comparisons. No character-to-token conversion is asserted. Actual model token usage is below.

Actual live reasoner packet sizes: control25012–48925characters (median34420); enhanced10855–29195(median26397). These distributions include different planning/provider outcomes, so they are not themselves a causal token-efficiency estimate. All fit64000without silent fact truncation.

Historical planner input sizes overlap: successes27015–27220characters;503s27021–27712; timeout26991. Same validated-JSON schema/settings, sequential concurrency1.503median4.10seconds/max10.52, successesmedian7.24/max13.65, one planning timeout35.02. There is no demonstrated size/schema/concurrency cause or evidence that retry reliably recovers. The35-second stage reservation is distinct from the120-second request deadline.

No retry was added: spending the third call could eliminate supplementary/final interpretation. No provider substitution. Runtime failures distinguish provider unavailable, dispatched timeout, admission timeout/quota, request deadline, invalid response schema/role contract and rejected reader proposals. Completed semantic planning/reasoning errors require source-derived review; trace classification does not pretend to detect arbitrary incorrect prose.

This task: **26actualcloudattempts**,23paired+3browser;24HTTP200and2planner timeouts,0HTTP503/429,0retries. Different provider availability today cannot be credited to metadata.12/14plannerattempts completed and12/12reasonercalls completed. All24completed responses satisfy the unchanged role schema; this is not24successful user tasks.

Reported usage across completed calls:239405inputtokens,10429outputtokens,3647reportedthoughttokens. Planner:111294input/2183output/3647thought; reasoner:128111input/8246output/0reportedthought. Error usage unknown; conservative reservations retained. Actual provider tokens are not overwritten by estimates. No billing action; API monetary cost unavailable.

Shared observed peak5requests/61seconds and55456input-or-reservation units/61seconds, under15RPM/150KTPM. Final rolling24-hour ledger222/500. Persistent locked project/per-model admission remains authoritative; usage outside this app is unknown. Shared task ceiling44was below the authorized54; unused allowance is not permission to continue testing.

Control median planning8.387s, reasoning20.773s, tools0.007s, other gateway composition/projection0.923s. Enhanced planning4.552s, reasoning22.176s, tools0.007s, other0.945s. Failed planner included in timing. All measured requests stay below120seconds. No reliable end-to-end speed improvement is claimed from6pairs.

## Tests, live MN4 and browser

- Initial focused run:125PASS/1FAIL (ledger missed the existing saved-configuration alias). Failure retained. Shared alias reuse corrected it.
- Corrected focused suite126PASS; affected final suite187PASS; final envelope35PASS; post-review66PASS. These overlap and are NOT added as unique successes.
- Source conformance18cases, each through BOTHauthorizedsurfaces:6new plus12prior cases. No model intelligence inferred.
- Mocked real graph verifies valid supplementary proposal→authorized actual reader→updated evidence→final inference; same-reader distinct queries, duplicates, forbidden/unknown tools, target scope, source availability and advice no-read boundaries are covered.
- Live model made0need_moredecisions in12pairedturns and2browsercloudrequests. EH05enhanced sees the available missing-event hints but still answers without the record. **MN4LIVE NOT VERIFIED.** No synthetic code converted answer to a read or forced branch coverage.
- No frontend change; prior API/editor contracts reused. CR-aware whitespace check passes. No broad30/120qualification was launched.

Browser capability works. Initial createBrowserTab timed out during Vite startup; recovered the same actual tab and inspected the running page. This was neither disabled permission nor an unavailable browser. One disposable5174/8001pair only; ordinary5173/8000was not restarted.

Actual Studio cloud request: exact Cloud·synthetic consent; planner timeout, no reasoner/read. **Browser cloud completion BLOCKED by provider**, not browser tooling. No repeated retry for a screenshot.

Actual Floating cloud request: real3.1→configuration/state/incidents→3.5, all three metadata components and validated syslog/config-change hints reach the model; raw prose survives. **Integration works, answer quality FAILS**: incorrectly says no-shutdown ensures operational-up and conflates unread logs with empty incident records; misses the referenced inspection purpose. No full-quality pass claimed.

Ordinary browser Send: Studio19+23=42, Floating16+27=43, both actualQwen2.5with0cloudcalls. Two retained unsaved tabs and visible no-vlan120content remain unchanged; no editor input, refresh, Save, Accept, Undo, generation or device action. That editor content is absent from all cloud bodies. Full ordinary-origin unsaved-buffer hashes are not accessible and are not claimed. Screenshots/DOM, actual model packets, source reads and provider wires are retained under the audit.

## Independent engineering review and explicit A–G conclusions

This is an implementation-assistant review against independently checkable source records, not external certification.

| Component | Functional value / security / quality evidence | Recommendation |
|---|---|---|
| Evidence ledger |Actual missing references/availability and clause identity are clearer; only receipt authority, no new reads. Adds~1.8–2.3Kcharacters and bounded milliseconds. Clause relevance remains coarse; model ignores a visible material gap.|**KEEP EXPERIMENTAL, defaultOFF.** Retrieval visibility established; no reasoning promotion.|
| Reader guidance |Actual permitted schemas/queries visible; backend still decides. Major duplicate-context reduction. Possible event locations remain uncertain; model ignores valid hints and no live supplementary cycle occurs.|**REVISE before activation; keepOFF.** Retain tested code for future authorized controlled evaluation, not more speculative readers.|
| Provenance |Raw values/IDs unchanged; clear artifact/model/design boundaries with~0.9–2.1Kcharacters. ECMP/planned cases pass in both arms; enhanced temporal case never reaches model. Other unsupported claims remain.|**KEEP EXPERIMENTAL, defaultOFF.** No demonstrated reduction in unsupported inference.|
| Failure observability/no-retry |Distinct execution categories and unchanged original provider statuses; no model/token overhead or extra authority. Preserved failures, no hidden retries/substitution. Doesn't repair provider availability.|**KEEP.** Low-cost operational benefit, no improved reliability claim.|

**A — Ledger:** clearer factual retrieval gaps than self-assessment alone, demonstrated offline and EH05. Not semantic support.

**B — Guidance:** Gemini has concrete validated relevant reader options; their presence is demonstrated, their successful selection/use is not. MN4staysopen.

**C — Evidence types:** classification is faithful and context cheaper overall. Reduced unsupported inference is not established: both arms pass ECMP/planned cases; temporal paired inference is interrupted, ownership/advisory errors persist.

**D — Provider reliability:** observed503s are actualproviderUNAVAILABLE; overlapping input sizes do not establish an application cause. Today has2timeouts/no503s, with no retry or completion repair. Deadlines/quota remain intact.

**E — End-to-end:** no demonstrated improvement:2/6versus2/6. Conditional2/5is diagnostic only. Neither fallback, JSON nor reader success receives reasoning credit.

**F — Complexity:** one pure helper and existing call-site/trace extensions; no independent state/planner/LLM stage. Shared schemas replace duplicated registry content. Retain experimental code, keep metadata disabled pending meaningful evidence; retain operational tracing. No further prompt tuning authorized by this task.

**G — Remaining limits:** G4misidentifies event readers and may propose excluded sources; G5/G6still make ownership, temporal and advisory overclaims with correct facts; sufficient-evidence decisions ignore explicit gaps; provider planning timeouts remain; raw prose is preserved correctly, including wrong prose. Source packets, not composition, explain neither away. No universal semantic verification claim.

## Preservation, configuration and exact continuation

PreservationPASS: HEAD/index unchanged; all41ordinarytablehashes unchanged/integrityOK; all1923release-treefiles unchanged including active release7a14a351e52b49aeb87f65d1192f0937and341immutableartifacts;194historicalJSONs unchanged; credential/root.envhashes unchanged; exactlyoneGit-ignoredGemini-keysetting, no credential copies in new text artifacts. Existing dirty work and prior source fixes retained. No commit/stage/push/publication/deployment/modelinstall/deviceexecution. Both disposable ports stopped and no running turns remain.

Configuration: existing Qwen/3.1/3.5roles unchanged. New master `COGNISHIELD_AI_EVIDENCE_HARNESS=0` by default. Component switches `COGNISHIELD_AI_HARNESS_LEDGER`, `..._GUIDANCE`, `..._PROVENANCE` default1onlyinsideanexplicitlyenabledmaster. Runtime root.env was NOT activated/edited. For a future isolated authorized experiment, set master1in that process; use component0for ablation and obtain fresh exact synthetic owner consent. Any flag/version change alters the existing consent manifest, invalidating stale approvals. It grants no source permission.

Immediate rollback: leave/unset master or set0and restart only the owned experimental backend if one is running. Ordinary/model-neutral defaults remain available. Local-only rollback remains existing HYBRID=0/MULTI_MODEL_EXPERIMENT=0withowned-backendrestart; no model replacement. ApproachA0, semanticverifierOFF, roles/call/deadline/quota unchanged.

Primary evidence: `tmp/phase-g/iterations/20261027-evidence-harness/`: preservation-before/final; freeze-v2/source-expectations-v2; source-conformance.xml; regression-final.xml; post-review.xml; offline-final.json; metadata-overhead-v2.json; paired-v1/EH-NN-{control,enhanced}.json; full-answer-review.json; matched-analysis.json; browser-review.json; quota-latency.json; completion-seal.json. Original unusedv1freeze, firstfailedtests, helper errors/receipts and all original raw answers remain.

**Safe stopping point:** no process or evaluation to resume. Do not rerun/rescore these frozen tasks or silently enable metadata. Future work requires new authorization, preferably a small dependency/sufficiency evaluation with genuine typed event-source bindings and provider availability controls, not more exposed-prompt tuning or another planner. Original G4/G5/G6/G11qualification requirements remain unchanged; formalG5stillrequires26/30withno criticalfalseclaims. G7remains113/141with28compatibilityblockers. No PhaseGstageclosureisclaimed.
