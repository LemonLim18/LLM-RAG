# Approach A integration reconciliation — 2026-10-25

**Decision: REVISE. Retain the integration corrections experimentally; keep `COGNISHIELD_AI_OUTCOMES` disabled by default.** The tested request/reference/source paths improve. Qwen reasoning and semantic release safety remain inadequate. No Phase G stage closes.

## Exact first-loss map and implemented corrections

| Failure | Responsible path before correction | Correction |
|---|---|---|
| Advisory binding | `planning.propose` required outcome fields but supplied incompatible examples; `requested_contract` trusted empty retrieve; `engine.after_resolve` returned END; gateway composed without owned context. | Consistent wire examples in the same planner. Original explicit speech acts constrain proposals, including context-prefaced imperatives. Contracted no-reader routes compose inside the graph. Existing owned-reference resolution overrides a missing model history flag. Advice invokes no reader. |
| Mandatory evidence | A whole-request singleton source correction reassigned configuration to syslog; later contract reconstruction trusted mutated needs. Splitting clauses also lost a device mentioned in another clause. | Bind whole-request and clause-specific source minima before refinement. Reapply through `RequestedContract.execution_queries` afterward and at the graph boundary. Preserve both capture scopes. Model source proposals cannot erase the original operands. |
| End-to-end authority | Accepted nonempty clauses were called answered; missing-source prose could contradict receipts; new fallback aggregation could discard a correct verified comparison. | Use response_proposed/limited/records_delivered and explicit NOT_CERTIFIED semantic status. Keep verified scoped fallbacks. Existing reader rendering owns requested read results and unavailable-source limits; raw Qwen text stays archived and remaining interpretation stays separately graded. |

Runtime changes are confined to existing `request_contract.py`, `planning.py`, `engine.py`, `synthesis.py`, `gateway_references.py`, and `gateway.py`. Earlier `gateway_routing.py`/AgentState integration is preserved. No second planner, framework, dependency, store, schema migration, renderer authority, V9 change or model change.

Current flow: original request/constraints → one requested-outcome contract → existing model/source proposals → reconcile original dependencies → existing authorized readers → primary evidence projection/per-outcome receipts → reader-owned direct results plus model interpretation → existing factual/citation checks → proposed/limited/read-delivered dispositions → existing gateway response.

Original text is retained unchanged. Action/source normalization is bounded grammar and existing source resolution, not universal natural-language understanding. Advisory capability descriptions come from the existing source registry filtered by server-authorized tools; these remain suggestions, never invocations. Original publication, engineer approval, exact-base editing, conversation ownership and immutable release boundaries remain intact.

## Paired actual-Qwen comparison

Eight unique conversations:4original failures/4newly frozen wording variants, balanced across both assistants. Known scenario families reused. Baseline is the failed first Approach A implementation enabled in the evaluator, not the legacy pre-Approach-A arm. Expectations were independently checked against raw fixture fields: shutdown state, source availability, saved command values and capture times. Implementation-assistant authorship/grading is disclosed; not external blind certification or fresh G11 qualification.

| Measure | Failed Approach A baseline | First reconciled run |
|---|---:|---:|
| Correct workflow |3/8|6/8|
| Minimum required reader instances obtained |5/8|7/8|
| Adequate complete tasks |2/8|3/8|
| Adequate Qwen-written reasoning |0|0|
| Chat calls including actual setup turns |19|20|
| Median conversation time |35.55s|55.17s|

Reader matching is not semantic source-selection accuracy. Sequential arms, warmup/load and timeouts confound latency; no statistical/causal improvement claimed. All recorded calls useqwen2.5:1.5b, temperature0,8192context,512outputtokens. Existing call/tool/round/input/wall budgets remain unchanged.

The frozen paired run exposed residual context-preface, singular-command source and mixed-source status defects. One final grouped correction addressed these using the same action/source grammar, authorized source descriptions and reader-owned outcome rendering. Only4affected cases were rerun:workflow4/4;requiredreaders4/4across2mixed-source requests;0readerson2advice turns;complete-task1/4(reader projection, quality warning);adequateQwenreasoning0/4. These exposed reruns do not replace the paired8scores or the earlier4/12versus2/12 first-pilot scores. No finalfull8or120/30qualification.

## Individual six-dimension reviews

Workflow, source selection, evidence completeness, model reasoning, verifier behavior, fallback safety and whole-task adequacy are recorded separately below and in the JSON report. Source success never earns model-reasoning credit. All adequate answers in this continuation come from verified factual calculation/read projection; zero adequate Qwen reasoning.

### Baseline8

| Case | Workflow / source | Evidence | Model / verifier / fallback | Task |
|---|---|---|---|---|
|G-A-RECON-01|FAIL / NO_READS_BUT_NO_SCOPED_RECOMMENDATIONS|MISSING_OWNED_CONTEXT|General-response bypass gives generic advice. V=NO_CONTRACTUAL_GENERAL_ANSWER_CHECK; F=NOT_APPLICABLE_OR_INADEQUATE|FAIL|
|G-A-RECON-02|FAIL / MISSING_CONFIGURATION|INCOMPLETE|Single syslog source replaces saved-capture operand. V=unavailable_sources_fallback; F=NOT_APPLICABLE_OR_INADEQUATE|FAIL|
|G-A-RECON-03|FAIL / STATE_INSTEAD_OF_CAPTURES|INCOMPLETE|Accepted invented capture equality, zero interval and delivery claims from state evidence. V=repaired_literal_checks_passed; F=NOT_APPLICABLE_OR_INADEQUATE|FAIL|
|G-A-RECON-04|PASS / PASS|COMPLETE_FOR_SCOPED_FLOW|Model timeouts; scoped deterministic delivery/reverse assessment answers with verbosity warning. V=unavailable_fallback; F=SAFE_SCOPED_FACTUAL_FALLBACK|PASS|
|G-A-RECON-05|FAIL / UNRELATED_UNTYPED_ADVICE|MISSING_OWNED_CONTEXT|Generic SQL injection/XSS testing advice includes destructive SQL text; no SQL or device action executed. V=NO_CONTRACTUAL_GENERAL_ANSWER_CHECK; F=NOT_APPLICABLE_OR_INADEQUATE|FAIL|
|G-A-RECON-06|FAIL / MISSING_CONFIGURATION|INCOMPLETE|Log-only failure erases explicitly requested saved command text. V=unavailable_sources_fallback; F=NOT_APPLICABLE_OR_INADEQUATE|FAIL|
|G-A-RECON-07|PASS / PASS|COMPLETE_TWO_CAPTURES|Existing typed comparison preserves timestamps/equality and unobserved-interval limitation. V=capture_interval_scope_fallback; F=SAFE_SCOPED_FACTUAL_FALLBACK|PASS|
|G-A-RECON-08|PASS / PASS_WITH_EXTRA_READERS|COMPLETE_STATE_AND_FLOW|Accepted route-sufficient conclusion contradicts down-interface/failed-flow records. V=literal_checks_passed; F=NOT_APPLICABLE_OR_INADEQUATE|FAIL|

### First reconciled8

| Case | Workflow / source | Evidence | Model / verifier / fallback | Task |
|---|---|---|---|---|
|G-A-RECON-01|PASS / RECOMMENDED_READER_SEMANTICS_FAIL|OWNED_CONTEXT_RESTORED_CATALOG_INCOMPLETE|Typed advice path retains subject; inventory recommendation wrongly promises operational evidence; no useful discriminating check. V=advisory_proposed; F=NOT_APPLICABLE_OR_INADEQUATE|FAIL|
|G-A-RECON-02|PASS / PASS|COMPLETE_AVAILABLE_AND_UNAVAILABLE_RECEIPTS|Model acknowledges instead of showing configuration and falsely calls unavailable syslog retrieved. Reader citations pass. V=literal_checks_passed; F=NOT_APPLICABLE_OR_INADEQUATE|FAIL|
|G-A-RECON-03|PASS / PASS_WITH_EXTRA_INVENTORY|COMPLETE_TWO_CAPTURES|Existing interval fallback now receives both captures; timestamped equality/limitation correct. V=capture_interval_scope_fallback; F=SAFE_SCOPED_FACTUAL_FALLBACK|PASS|
|G-A-RECON-04|PASS / PASS_WITH_EXTRA_INVENTORY|COMPLETE_FOR_SCOPED_FLOW|Two answer-stage timeouts; same safe scoped model-calculation fallback. V=unavailable_fallback; F=SAFE_SCOPED_FACTUAL_FALLBACK|PASS|
|G-A-RECON-05|FAIL / UNREQUESTED_READS_FOR_ADVICE|CONTEXT_REFERENCE_PRESENT_WRONG_ACTION|Context preface hides recommendation speech act; performs inventory/topology/configuration reads. V=literal_checks_passed; F=NOT_APPLICABLE_OR_INADEQUATE|FAIL|
|G-A-RECON-06|FAIL / MISSING_SINGULAR_COMMAND_TEXT_SOURCE|INCOMPLETE|Existing source grammar recognizes commands but misses command; log-only result persists. V=unavailable_sources_fallback; F=NOT_APPLICABLE_OR_INADEQUATE|FAIL|
|G-A-RECON-07|PASS / PASS|COMPLETE_TWO_CAPTURES|Verified comparison survives outcome fallback accounting; no model inference for interpretation. V=capture_interval_scope_fallback; F=SAFE_SCOPED_FACTUAL_FALLBACK|PASS|
|G-A-RECON-08|PASS / PASS_WITH_EXTRA_READERS|COMPLETE_STATE_AND_FLOW|Qwen repeats route-sufficient conclusion despite failed flow; existing verifier accepts. No new causal guard added. V=repaired_literal_checks_passed; F=NOT_APPLICABLE_OR_INADEQUATE|FAIL|

### Final4exposed reruns

| Case | Workflow / source | Evidence | Model / verifier / fallback | Task |
|---|---|---|---|---|
|G-A-RECON-01|PASS / RECOMMENDED_READER_SEMANTICS_FAIL|OWNED_CONTEXT_AND_AUTHORIZED_CATALOG_COMPLETE|No new reads. Inventory recommendation promises reachability; all queries are circular. Complete metadata did not produce useful recommendations. V=advisory_proposed; F=NOT_APPLICABLE_OR_INADEQUATE|FAIL|
|G-A-RECON-02|PASS / PASS|COMPLETE_AVAILABLE_AND_UNAVAILABLE_RECEIPTS|Verified source projection supplies exact saved text and no-observation limitation. Circular model sentence remains as quality warning; requested facts/limits are present without crediting Qwen. V=outcome_reconstructed; F=SAFE_SOURCE_PROJECTION; model-quality warning|PASS_WITH_QUALITY_WARNING|
|G-A-RECON-05|PASS / RECOMMENDATIONS_INSUFFICIENT|OWNED_CONTEXT_AND_AUTHORIZED_CATALOG_COMPLETE|No new reads. Two typed but generic inventory/topology suggestions fail to distinguish the operational uncertainty. V=advisory_proposed; F=NOT_APPLICABLE_OR_INADEQUATE|FAIL|
|G-A-RECON-06|PASS / PASS|COMPLETE_AVAILABLE_AND_UNAVAILABLE_RECEIPTS|Read projection supplies exact saved text/unavailability. Remaining model explanation contradictorily says syslog is available while logs are unavailable; verifier does not reject. V=outcome_reconstructed; F=SAFE_READ_PROJECTION; contradictory model interpretation remains|FAIL|

Finalcase02passes functionally because the exact saved text and missing-source limitation are projected from authoritative receipts. Its circular model sentence is a quality warning; no Qwen reasoning credit. Finalcase06fails despite correct read projections because the remaining model explanation contradicts syslog availability. No single adequacy label is inferred from nonempty clauses or successful HTTP.

## Remaining limitations and stop decision

- With the actual down-interface and failed-flow records supplied, Qwen still says the route is sufficient. Repair completed normally with3027input/30outputtokens; the verifier accepted it. This is completed wrong reasoning plus a verification limitation, not output truncation or retrieval loss.
- With owned references and authorized capability descriptions, Qwen still proposes irrelevant/circular next checks. No further advice prompt tuning was attempted.
- With available configuration and unavailable syslog clearly supplied, Qwen still writes a contradictory interpretation (normalstop,249outputtokens). Direct read projections are safe; arbitrary interpretive prose is not certified or reliably blocked.
- Other answer-stage calls hit the unchanged30second deadline. Those are recorded as unavailable inference, not completed reasoning failures.
- Binding remains at explicit action/source/tool scope; implicit/unsplit outcomes and unrestricted field/causal semantics are not certified. Metadata response_proposed/limited does not prove semantic completion.

**Do not activate ordinary use.** Retain these integration corrections for review, but revise before promotion because semantic release and model quality remain unaccepted. No further causal phrase guards, stronger model, Approach B or broader Phase G cycle. Stop here and wait for explicit authorization.

## Focused tests and preservation

- Initial107PASS/5FAIL retained: one real cross-clause source loss corrected; four old assertions updated to require original-request binding/proposed-response status instead of misleading prior states.
- Intermediate146/148passing runs overlap. Final affected contract/source/B3 suite156PASS; separate B2owner/checkpoint/topic-switch suite21PASS. Do not add overlapping reruns as unique coverage.
- Mocked gateway tests cover both surfaces, reader permissions, owned context, topic isolation and original source execution. They do not establish Qwen intelligence.
- Actual evaluations use authenticated ASGI gateway paths, disposable SQLite/ScenarioManager and real Ollama. No fabricated setup history; no browser acceptance claimed.
- HEAD/index/ordinarySQLite/active release and341artifact fingerprints match. Active release7a14a351e52b49aeb87f65d1192f0937unchanged. No editor/browser operation, buffer save, ordinary server restart, staging, commit, publication, deployment or download. No fresh UI buffer/hash claim.
- Default flag remains0; only evaluator child processes enabled it. No provider/model/budget/configuration changes. Exact pre-change bytes for7runtimefiles and an incremental patch preserve earlier dirty work. All sessions finished.

## Evidence and rollback

- Baseline8: `tmp/phase-g/iterations/20261024T155433.683577Z-G11-fresh-quality-candidate-03a814`.
- Paired8: `tmp/phase-g/iterations/20261024T161958.804761Z-G11-fresh-quality-candidate-bf1a92`.
- Exposed final4: `tmp/phase-g/iterations/20261024T163531.689698Z-G11-fresh-quality-candidate-b233c5`.
- Full reviews, raw-answer links, exact source/revision/intermediate contract records, oracles, failures, preservation and before/current source bytes: `tmp/phase-g/iterations/20261024T155432Z-approach-a-reconciliation`.
- Registries: `docs/evaluations/phase_g_approach_a_reconciliation_v1.json` and `phase_g_approach_a_reconciliation_corrective_v1.json`; SHA hashes retained. Historical evaluator directory names sayfresh; no unseen generalization credit.

Rollback is configuration-controlled: leaveCOGNISHIELD_AI_OUTCOMESunset/0. Do not reset the tree. If source rollback is authorized, inspect `tmp/phase-g/iterations/20261024T155432Z-approach-a-reconciliation/reconciliation-only.patch` against saved pre-change bytes/current hashes; reverse only these hunks, preserving earlier work. No user data or immutable release rollback needed.
