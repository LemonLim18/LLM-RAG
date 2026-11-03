# Gemini 3.5 answer-integrity live result

**LIVE-TESTED — FAILED; KEEP OFF.** The original candidate materially improved this Round1sample, but neither the original nor the single revised candidate satisfies all targeted requirements. The revised candidate also regresses on completed cases. No ordinary activation or PhaseGacceptance follows.

Date:2026-11-02, Asia/Kuala_Lumpur. [Full audit](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261102T153500Z-answer-integrity-live/round-1/grading.json), [Round2grading](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261102T153500Z-answer-integrity-live/round-2/grading.json), [quota/usage](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261102T153500Z-answer-integrity-live/usage-and-quota.json). These are source-derived original frozen human oracles, implementation-assistant graded, nonblinded and not externally adjudicated. No model grader. The exposed12conditions and repeated control generations are not independent holdout evidence.

## A. Before versus after

PASS means strict user-facing answer adequacy, including the existing frozen caveats. AMBIGUOUS is not counted as a pass. Invalid/noncompleted responses cannot count as successfully released answers. Whole-response consistency is tracked separately.

| Case | R1 control | R1 candidate | R2 control | R2 revised candidate | Finding |
|---|---|---|---|---|---|
| RC-01 | FAIL | PASS | PASS | PASS | R1 candidate corrects wrong-year/scope output; both R2 answers scoped correctly. |
| RC-02 | AMBIGUOUS | PASS | PASS | AMBIGUOUS | R1 candidate correct; R2 adds ambiguous matches-prior-state inference. |
| RC-03 | FAIL (invalid JSON) | PASS | PASS | AMBIGUOUS | R1 candidate correct; R2 return egress wording is ambiguous after ingress denial. |
| RC-04 | FAIL | PASS | PASS | FAIL | R1 requested advice restored; R2 conflates advice with forbidden collection again. |
| RC-05 | FAIL | FAIL | FAIL | FAIL | Not corrected:4to5minute occurrence range persists instead of5minute observation interval. |
| RC-06 | FAIL (invalid JSON) | PASS | FAIL (invalid JSON) | PASS | Candidate preserves positive modeled policy consequence in both rounds; controls malformed. |
| H-01 | PASS | PASS | PASS | PASS | Required MTU/times present in both new arms; historical omission not reproduced. |
| H-02 | PASS | PASS | FAIL | PASS | Candidate prose sound; wrong auxiliary record selectors persist. |
| H-03 | PASS | PASS | PASS | FAIL | R1 correct; R2 wrongly says Brook six-minute interval crosses midnight. |
| H-04 | FAIL | PASS | NOT RUN | HTTP503 / no answer | R1 later shutdown restored; revised candidate call received503, not a reasoning failure. |
| H-05 | FAIL | FAIL | NOT RUN | NOT RUN | R1 caveat still missing; no R2 result after provider stop. |
| H-06 | PASS | PASS | NOT RUN | NOT RUN | R1 directional positives correct; no R2 result after provider stop. |


H02's old strict/permissive reading is preserved. R1candidate and R2candidate prose explicitly limit actual interruption order, so their answer fields pass. R2control instead says first observations demonstrate actual interruption order; the strict reading fails, while an informal first-observed reading remains a documented sensitivity. Both candidate arms still use first-observed times as the source-record timestamp on auxiliary claims, so their whole binding assessment fails despite correct prose.

H05's explicit modeled-versus-measured application caveat is the unchanged frozen rubric requirement, not an invented separate verbatim user subquestion. Both R1arms offer two passive artifacts but omit that caveat. Generic interface counters cannot alone identify the requested application's response; no easier counter-only criterion was substituted. R2did not reach H05.

H01candidate R1gives13minutes effective-to-record,5minutes record-to-capture and18minutes effective-to-capture. Its alternative capture-delay label is recorded, but correctly named endpoints and the required18minutes are explicit; this is not graded as wrong arithmetic. RC02R1control's mixed cannot-infer/likely-remained wording, RC02R2candidate's matches-prior-state aside, and RC03R2candidate's though-blocked egress wording are explicitly AMBIGUOUS under the strict gate rather than silently upgraded or treated as definite new modeled facts.

## B. Actual numbers

| Measure | R1control | R1candidate | R2control | R2candidate |
|---|---:|---:|---:|---:|
| Dispatched |12|12|9|10|
| Provider HTTP200/STOP completions |12|12|9|9|
| Valid JSON / application core |10|12|8|9|
| Strict final-answer PASS |4/12|10/12|6/9|4/9 completed pairs|
| Ambiguous answer fields |1|0|0|2|
| Whole-response consistency PASS |4/12|9/12|6/9|3/9 completed pairs|
| Reported input tokens |57,746|64,214|43,108|48,886|
| Reported output tokens |12,522|12,989|8,522|8,566|

**43 actual dispatches**,42HTTP200model completions,1HTTP503provider failure. **39valid JSON/application cores**,36responses also have strictly valid auxiliary declaration shapes. Three completed control generations have malformed JSON: R1RC03, R1RC06, R2RC06. No invalid JSON was repaired/retried. All39valid raw answer bodies survive release intact; no factual fallback or complete-prose replacement earns reasoning credit. Numeric auxiliary-ID schema errors are separate from materially false source statements; whole consistency requires truthful source binding, not every auxiliary operand being mechanically certifiable.

R2stopped on **H04candidate Google HTTP503 / code503 / UNAVAILABLE**, message “This model is currently experiencing high demand.” No model answer exists for that cell. The remaining five scheduled cells (H04control, H05both, H06both) were not dispatched. Five authorized calls remain unused; no failed-cell replacement or automatic retry was made. This is an external availability blocker, not inferior reasoning inferred from noncompletion.

Total reported usage on42completed provider responses: **213,954input /42,599output tokens**. Usage for503is not reported; the adapter's conservative admission reservation remains in the ledger. No fabricated zero-token/price conclusion is made. No billing change or paid-cost estimate. All42HTTP200responses finishSTOP, including the three malformed model outputs; none is a token-cap or timeout result.

Peak shared rolling61secondwindow: **15requests**,84,442finalized-input-plus-error-reservation units; reconstructed conservative admission peak93,037, below150,000. Ledger retained62before→85after:43new rows,20normal expired rows already older than24hours before first send; surviving42prior records exact. Old62rows remain archived in the task's preservation-before file. Existing15RPM/150KinputTPM/500RPDcontrols remained authoritative. No ledger reset/reconstruction occurred.

Longest wire duration9.45seconds; largest measured role-request duration9.94seconds. Every attempted request remains within its120secondenvelope. These are fixed-evidence reasoner/consent/release timings, **not full application planning/retrieval latency**. Same Gemini3.5Flash-Lite, low thinking,8192output allowance, validatedJSON/fullschema in both arms. Thought-token counters are not reported; normalized zero does not establish no thinking.

## C. Exact correction and what it did

R1used the existing instruction SHA256 `dc352a9f84350b9ea9f51fe06133eb116ac51e878de939915e72e16408900527`. After full R1grading was preserved, only the final self-check sentences of the same instruction constant were replaced. The specific evidence was RC05's incorrect clock-range synthesis, H05's still-omitted modeled/application distinction and H02's wrong typed selectors/IDtypes. [Rationale](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261102T153500Z-answer-integrity-live/revision-rationale.md) and [exact source diff](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261102T153500Z-answer-integrity-live/instruction-revision.patch).

The replacement is:

```text
Before finalizing, reconcile the answer with the source fields rather than with your assessments. For each elapsed time, name both endpoint time roles and subtract those specific values; do not combine different clock roles into an unqualified occurrence-time range. For a delivered or failed path, state explicitly whether the result is modeled or measured and whether it establishes the requested application outcome. For each optional claim, keep its source-record selector separate from its asserted field/value, and use the identifier types required by the schema. Omit an optional declaration that cannot be represented faithfully rather than inventing a binding. Put each requested conclusion or source-supported limitation directly in `answer`, check JSON validity and cross-field consistency, and do not output this check.
```

This is one focused source-reconciliation correction, with no case facts, names, MTU values or timestamps in the prompt. Full final instruction: [final-instruction.txt](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261102T153500Z-answer-integrity-live/final-instruction.txt); SHA256 `8b0c9085d01921491408c77b805d53f89f882dd8f68ae562135809b1cdf885ec`. AST proof confirms that **every function/class is unchanged** by this correction; only `ANSWER_INTEGRITY_CANDIDATE` changes. No schema, flag, role, reader, evidence projection, checker or second pass was added. The revised block remains available only behind the existing default-OFFflag; it is not promoted. R1text, results and grades remain intact.

The correction did **not** demonstrate a reliable benefit. RC05still invents the4to5minute occurrence interval. R2RC04says no passive evidence can be requested because collection is forbidden, despite the original explicit request and advisory instructions. H03incorrectly calls Brook's same-date23:50→23:56interval cross-midnight despite reproducing both correct timestamps. H02numeric IDtypes improve in R2, but the source selectors remain wrong. H05retest is unrun because of503, so no result is claimed for its attempted instruction repair.

These failures first occur in raw model output with the exact required operands present. No application composition loss or new deterministic integration defect was demonstrated. The limited checker retains correct typed facts but does not certify prose completeness, causality or cross-field consistency. No additional phrase guard or universal verifier was added.

## Execution integrity and preservation

Current user attachment expressly authorizes at most48calls in two bounded rounds. All24R1and24prospective R2wire bodies were frozen before each round with original questions, source order, material records, source IDs, unchanged schemas, model controls and source-derived oracles. R1manifest SHA256 `d1d27ee3c495c0fe6d2d6258cfa38df21f04b092178cc79fbeae97db8ca2f075`; R2 `1e63dc15423aca0879f82c49a4009762b348e531ca5e79b5336f905891d0172f`. Actual dispatched bytes match those freezes; R2control bytes remain unchanged from R1. Only the candidate instruction and its required consent binding differ.

The existing exact owner/message/history/source-revision/role consent functions approve each owned disposable synthetic context and check it again at dispatch. Both zero-dispatch preflights pass. No consent bypass or second blanket approval was used. Only the pre-existing disposable evaluation database receives24new owned test conversations (12perround) and the audit receives sealed synthetic scenario state files. No private conversations, editors or uploaded files are sent. No planner or registered reader runs; no endpoint other than Gemini3.5generateContent is permitted. This is **not full authenticated gateway/browser acceptance**.

The minimal evaluation runner reuses existing captures, provider adapter, consent and quota. A zero-dispatch initial freeze stored pretty-printed bodies; exact-byte inspection caught that formatting mismatch before preflight/dispatch. Its offline preimage is retained, and the actual freeze uses HTTPX's exact JSON serialization. No request, oracle or candidate was tuned in response to that harness issue, and it consumed zero provider attempts. There were no automated retries or replacement outputs during either live round.

After the single instruction correction, **125affected offline tests pass** (37candidate,46release,23timestamp,19interpretation; overlapping prior runs not added). All12OFFcontrol messages/schemas reproduce the originals. Provider sends/quota/reader calls are mocked in these offline checks. No unnecessary broad benchmark. The live comparison separately measures actual model quality.

Fresh environment-loaded configuration remains: Qwen2.5:1.5b local, Gemini3.1Flash-Lite planner, Gemini3.5Flash-Lite reasoner; new and old candidate flags OFF; ApproachAfalse. Both environment files/credential hashes unchanged. No ordinary activation, model install, services/browser/editor/Ollama/device action, stage/commit/publication/deployment. The existing index/HEAD, ordinary DB/tables, V9release and341artifacts and all historical cohorts/oracles/grades are protected by the before/after fingerprints. The checkpoint receives only an append, retaining every earlier byte. The80older unreviewed component instances are not newly graded.

## D. Decision and stop

**LIVE-TESTED — FAILED; KEEP OFF.** R1shows a useful sampled improvement but not12/12acceptance, and the revised candidate has new regressions and unresolved clock/binding failures on completed pairs. The503additionally blocks the last five comparisons. A single generation per exposed case/arm does not isolate the prompt's causal effect from generation variability; no statistical or unseen-generalization claim is made.

The retained final revision remains OFF. No third prompt correction, other model, extra call, provider retry or further experiment will run. G4/G5/G6/G11 remain unaccepted. Operational rollback is already in effect through the OFFflag; source preimage and instruction-only patch preserve both tested versions for review without resetting unrelated work.
