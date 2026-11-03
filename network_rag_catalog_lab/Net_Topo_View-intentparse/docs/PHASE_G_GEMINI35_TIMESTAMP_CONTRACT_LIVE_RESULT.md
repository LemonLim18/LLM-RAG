# Gemini 3.5 timestamp-contract live comparison

**KEEP OFF — candidate failed.** All 12 authorized attempts completed at the provider;11passed core JSON validation. The candidate did not demonstrate better timestamp binding and regressed on complete answer fulfilment. No production promotion, further API call or application change follows from this result.

Audit: `tmp/phase-g/iterations/20261102T123607Z-timestamp-contract-live/`. Complete source-checked adjudication: [full-answer-grading.json](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261102T123607Z-timestamp-contract-live/full-answer-grading.json). Structured public summary: [phase_g_gemini35_timestamp_contract_live_result.json](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/docs/evaluations/phase_g_gemini35_timestamp_contract_live_result.json).

## Authorization and preflight

The current user attachment explicitly authorizes only the frozen H-01–H-06comparison: one Gemini 3.5Flash-Lite call per OFF/candidate cell, maximum12 attempts including failures, no retries, no additional models, planners, retrieval or promotion. It does not reuse prior exhausted approvals.

Before dispatch, verified unchanged full hashes:

- Registry `docs/evaluations/phase_g_gemini35_timestamp_contract_v1.json`: `d8dbe4f0d70c5dce1d5ec182b71b216b87cc066b9003f5ff18330d6f941a62a4`.
- Exact-byte manifest `tmp/phase-g/iterations/20261102T104614Z-timestamp-contract-experiment/exact-byte-freeze.json`: `5d12a9c7173daffd1da1a225bf749ad6d82bc4deabac9c46dcae2f2c19bbcbc4`.
- Candidate description: `e2f1f6a1eb5c93ef09d729e5dac5d9a195ef3a35781c143e095d432b152a5afb`.

All six case/oracle/pair hashes,12schema/body byte files, all 110 runtime source hashes, exact OFF/candidate messages, schemas and consent manifests matched. The only schema delta remained `/$defs/SourceClaim/properties/timestamp/description`. Every actual dispatched HTTP body subsequently matched its frozen byte file exactly. No prompt, data ordering, claim requirement, field/type, low-thinking setting,8192 output allowance, sampling option or checker was changed.

Initial quota check:99 retained rows,50 within24 hours,0requests in the last61seconds, room for all 12 attempts under500RPD. Existing ignored `backend/.env` credential loaded without output/copying; both environment files remain hash-identical.

The new bounded evaluation runner uses existing `approve_hybrid_request`, `HybridRequest.create`, role-model binding and `generate_role('evidence_reasoner')`. A zero-dispatch preflight checks fresh exact consent for all 12 cells. Six owned synthetic conversations are created in the existing disposable evaluation database, with scenarios sealed only under this audit's `scenario-state/` files. Actual dispatch mints fresh consent again; old preflight permission is not reused. Exact request, source revision and description/model manifest are bound. Editor/uploads/private history are absent. No registered reader executes; the frozen sources are authored synthetic evidence, not newly collected observations.

This tests the existing consented role adapter plus unchanged offline release replay. It is **not** a full authenticated HTTP gateway journey, routing evaluation, browser acceptance or production deployment. Model roles and ordinary defaults are not activated or reconfigured globally.

## Execution and provider results

Executed the exact frozen alternating order, sequentially, concurrency one. **12 attempts,12 HTTP200/STOPprovider completions,11 valid core responses,0provider availability/authentication/quota errors,0timeouts,0retries.** H-06control is a completed generation with malformed JSON, not a timeout or inferior causal reasoning inferred from noncompletion. It was not repaired, retried or released.

| Case | Arm | Provider | Application contract | Request seconds | Input tokens | Final output tokens |
|---|---|---|---|---:|---:|---:|
| H-01 | control | 200 / STOP | Valid core | 4.125 | 3521 | 1031 |
| H-01 | candidate | 200 / STOP | Valid core | 3.745 | 3601 | 1030 |
| H-02 | candidate | 200 / STOP | Valid core | 4.178 | 3250 | 1207 |
| H-02 | control | 200 / STOP | Valid core | 3.950 | 3170 | 901 |
| H-03 | control | 200 / STOP | Valid core | 3.330 | 3173 | 826 |
| H-03 | candidate | 200 / STOP | Valid core | 3.238 | 3253 | 846 |
| H-04 | candidate | 200 / STOP | Valid core | 3.304 | 3461 | 872 |
| H-04 | control | 200 / STOP | Valid core | 5.080 | 3381 | 946 |
| H-05 | control | 200 / STOP | Valid core | 6.270 | 5951 | 2309 |
| H-05 | candidate | 200 / STOP | Valid core | 6.692 | 6031 | 2262 |
| H-06 | candidate | 200 / STOP | Valid core | 4.264 | 5386 | 894 |
| H-06 | control | 200 / STOP | INVALID_STRUCTURED_OUTPUT: malformed JSON | 3.823 | 5306 | 829 |

H-06control raw output contains unquoted `-timestamp:` in its claim object. The existing unchanged validator raises502/`INVALID_STRUCTURED_OUTPUT`; the actual Google HTTP status is200. No parsed whole JSON, claim verification or final answer exists for that cell. Its wire response and raw bytes are retained. For diagnosis only, the already well-formed `/answer`string is read with JSONDecoder.raw_decode; this does not reconstruct a valid response or feed release. The displayed prose is technically adequate, but the task did not complete through the contract.

Every attempted cell preserves exact messages/schema/body hashes, model/settings, raw provider response, usage, raw JSON text, parsed JSON when valid, answer/claims/assessments, checker/release where reached, source revision, consent and quota hash. No malformed response is replaced by synthetic success. Traces are `cells/H-XX-control.json` / `H-XX-candidate.json`; dispatches are independently recorded before send in `dispatch-ledger.jsonl`.

## Grading method and four separate outcomes

All criteria/oracles were frozen before inference. They are source-derived and independently checkable, implementation-assistant graded, not blinded or externally adjudicated. No Gemini or other LLM graded outputs. No source oracle was edited. These six new arrangements remain distinct from the historical six; no pooled success/failure rate is calculated.

**Raw prose adequacy includes one explicitly diagnostic string from malformed control H-06.** That observation is not executable model success. Report both prose quality and valid-response adequacy. Whole-response adequacy requires complete user-facing prose and truthful, mutually consistent substantive declarations. Numeric-ID schema errors are tracked as structured contract failures, not falsely called wrong device ownership or wrong causal prose. Malformed whole JSON cannot pass whole-response or release. Uncheckable but source-true declarations are not automatically semantic lies.

| Measure | Control | Description candidate |
|---|---:|---:|
| Adequate raw answer prose, including diagnostic string | 5/6 | 2/6 |
| Adequate prose in valid core response | 4/6 | 2/6 |
| Adequate whole response | 4/6 | 2/6 |
| Adequate released answer | 4/6 | 2/6 |
| Core JSON valid | 5/6 | 6/6 |
| Parsed raw claim record-clock values correct |18/18|22/22|
| Strict-shape SourceClaim declarations |10/18|16/22|
| Invalid auxiliary declarations / affected cells |8 /2|6 /2|
| False material auxiliary source assertions identified |0|0|
| Unsupported continuity conclusions |0|0|
| Unsupported physical cause / activation |0|0|
| Other unsupported temporal conclusion |0|1(H-02)|
| Passive-recommendation omissions |0|0|
| Factual fallbacks / false suppression / incorrect certification found |0 /0 /0|0 /0 /0|

Clock equality above is a narrow observation: it does not override invalid types, wrong category, missing event-time declaration, broad receipt references or semantic claims. No corrected clock formatting is counted as network-engineering intelligence. Complete JSON and additional supported scalars similarly do not establish adequacy.

## Paired complete-answer assessment

| Case | Control raw | Candidate raw | Control whole | Candidate whole | Binding result | Regression? |
|---|---|---|---|---|---|---|
| H-01 | ADEQUATE | PARTIAL | ADEQUATE | PARTIAL | Both record clocks correct; candidate effective_atoperand present but invalid IDs/category. | Yes |
| H-02 | ADEQUATE | INCORRECT_UNSUPPORTED_ONSET | ADEQUATE | INCORRECT_UNSUPPORTED_ONSET | Raw clocks correct; both numeric-ID errors; candidate overstates occurrence order. | Yes |
| H-03 | ADEQUATE | ADEQUATE | ADEQUATE | ADEQUATE | Both correct owner/date rollover and valid bindings; no gain. | No |
| H-04 | ADEQUATE | PARTIAL | ADEQUATE | PARTIAL | Both three clocks correct; candidate omits later shutdown from prose. | Yes |
| H-05 | PARTIAL | PARTIAL | PARTIAL | PARTIAL | Both clocks correct; candidate fixes sampled interface-IDtypes, not scope caveat. | No; shared limitation |
| H-06 | ADEQUATE_DIAGNOSTIC_PROSE_INVALID_JSON | ADEQUATE | INVALID_JSON_NOT_RELEASABLE | ADEQUATE | Control JSONinvalid; candidate valid with correct directional result. | No |

### H-01 — correct timing, missing user-facing configuration value

Sources establish MTU1500, verified effective08:04, audit08:17and follow-up08:22. Delays13and18minutes are correct in both arms; both withhold measured payload-recovery time. **Control includes1500; candidate answer never states the restored value.** Candidate claims/assessment contain1500, proving it reached and was interpreted by the model but omitted from its answer field. Final composition retains that omission; it did not erase correct model prose.

The candidate places record selector08:17and effective_at08:04correctly in a structured claim. However, it emits integer device/interface IDs, which the strict schema rejects, and calls an effective-time event a `configured_command`. Both candidate claims lose auxiliary verification credit. Control clocks are also correct but it declares no effective_atoperand; its event-as-command and multiline CLI value remain uncheckable. A better selected field in one unusable declaration is not valid binding or reasoning promotion.

This failure is a frozen required-component omission, not a new demand invented after inference: the H-01oracle explicitly requires “Verified effective MTU1500at08:04.” Raw prose and auxiliary material are graded separately; inspectable metadata does not fill the user-visible omission.

### H-02 — chronology arithmetic correct, onset overstatement

Both arms correctly report Ravine first-observed21:04, Plateau21:08, record times21:19/21:10and delays15/2minutes. Both reject record-writing order as causal evidence.

Candidate then says the interruptions **“actually occurred earlier at RavineWAN”** The records provide first-observed times, not independently measured onset at each site. That phrase promotes observation order into actual occurrence order. The strict source-grounded grade is incorrect; the exact text and alternative interpretation are retained in the grading sensitivity. Control avoids that claim.

Both controls and candidates use correct clock selectors/values on manual inspection, but numeric device IDs invalidate every auxiliary declaration. Candidate additionally uses the parent receipt ID instead of exact record IDs; its owner plus timestamp still points to the intended source, so this is not fabricated evidence, but it does not satisfy the requested record-declaration discipline. No new time-binding advantage appears.

**Sensitivity:** reading “actually occurred” colloquially as “was first observed” would raise candidate raw/whole/released adequacy2/6→3/6. This does not erase H-01/H-04regressions or change the failed gate. No alternative score replaces the strict recorded grade.

### H-03 — both arms correct; no candidate gain

Both retain equal effective23:50time, Brook23:56record/6minute delay and Vale00:03next day/13minute delay, correct ownership and no later-activation inference. Both emit valid record timestamp declarations with correct source IDs/owners/values. The statement also mentions the correct effective time, but typed support of `field:timestamp` certifies only that scalar, not all prose. There is no demonstrated improvement on this case.

### H-04 — no continuity invention, but later observation omitted

Both preserve contradictory06:40collector results and leave06:55/exact transition unknown. No continuity failure occurs in either arm. Control explicitly states the later07:10capture records`shutdown`. Candidate merely says there is a later state at07:10without stating that command; its third auxiliary claim supplies it, but the answer and release do not. This is a user-facing required-outcome omission, not evidence loss. Duplicated timestamp formatting in candidate prose is noted as cosmetic rather than the decisive error.

All six raw clock selectors across both arms match. Multiline CLI scalar declarations remain unverified by the existing exact-line checker; they are source-true strings, not known contradictions. No checker change is made to improve a score.

### H-05 — advice is present, but an oracle limitation is omitted

Both explain known routes/upports, forwardunknownnext-hop resolution and modeled return delivery. Both provide two passive artifacts with purposes and execute none. **The earlier passive-advice omission does not reproduce here.** Candidate also produces correctly typed interface IDs where the sampled control uses integers, a narrow contract improvement without causal attribution to this description.

The frozen oracle separately requires the distinction between modeled delivery and measured application response. Neither answer explicitly gives that caveat. Strict full-task grade is partial for both. Control's alternative flowtelemetry recommendation is potentially discriminating; aggregate interface counters alone cannot establish a specific poll response. Candidate's counters/ARP-NDwording has similar limits and includes an unnecessary IPv6alternative. These recommendations are not classified as a definite executed action or invented measurement.

**Sensitivity:** accepting repeated “modeled” wording as sufficient implied application limitation would add one adequate answer to each arm. H-01/H-04regressions remain, so the decision does not depend on that strict reading.

### H-06 — positive modeled results preserved; malformed control is not a reasoning failure

Both raw prose texts correctly distinguish trap forward denial at TransitHubEthernet2/9egress53022, delivered reverse traffic, UDP514bidirectional delivery, ingress53021/egress53022inmonitor and no deployed-outage proof. Candidate successfully releases that valid explanation. Control's whole JSON is malformed at `-timestamp:` and does not reach release.

This is a structured-generation reliability difference, not proof that the candidate reasoned more accurately about policy. No adequate valid core was falsely suppressed. The raw useful string is retained diagnostically without changing the original failed result.

## Binding, structured consistency and release

Every provided timestamp in the11 parsed raw responses matches its intended record clock:18/18control and22/22candidate. No incorrect-time selector was corrected by the candidate in this sample. H-01adds a correct effective_atfield/valuebut invalid types/category prevent a usable contract declaration. H-02clocks are source-correct in both; all numeric IDs are rejected. H-03valid binding is unchanged. The direct all-applicable valid temporal binding gate is therefore **not demonstrated/passed**, despite correct clock strings.

No semantically false substantive auxiliary source assertion is identified in the parsed outputs; several are malformed or mismapped. Those dimensions are not conflated. The candidate's H-02overstatement first appears in prose, while its assessment remains observation-based. Supported scalar agreement does not certify that inference.

The unchanged release path retains all11 valid core answer bodies exactly, with unverified/auxiliary limitation labels where required. It does not fix omissions or unsupported prose. H-02candidate's onset overstatement remains visible as unverified content; no free-prose verification credit is claimed. Candidate H-06policy-ruleinterpretation is source-correct but only partially mechanically checked. Known incident first_observedlimitations remain unchanged.

No false suppression or incorrectly certified source operand is found. H-06control is a safe structural rejection, not false semantic rejection of a valid response. No automatic fallback, extra correction call, raw-data replacement or prose rewrite is used. All findings are scoped to this bounded role/release experiment.

## Frozen decision gates

| Gate | Result |
|---|---|
| All applicable candidate record bindings/event semantics valid and complete | FAIL / not demonstrated: invalid H-01/H-02declarations and H-02onset overstatement |
| No paired whole-response adequacy regression | FAIL: H-01,H-02(strict),H-04 |
| Preserve positive H-06modeled/directional outcome | PASS |
| No new unsupported physical activation or causal assertion | PASS; separate unsupported temporal observation→occurrence inference remains |
| No incorrectly verified claim found | PASS within reviewed narrow checks |
| No new false suppression | PASS |

**KEEP OFF — candidate failed.** Even the more permissive H-02/H-05readings leave H-01/H-04incomplete compared with control. The direct binding result does not improve because clocks were already correct. A single pair per source condition cannot establish that the schema description caused the regressions, fixed ID types or prevented malformed JSON. This is not statistical reliability evidence and does not justify another prompt variant, repeat or promotion.

The original18and12cohorts, their grades and all 30diagnosis records remain immutable. Do not pool them with this cohort as independent observations. No G4/G5/G6/G11acceptance is claimed.

## Latency, tokens and quota

| Measure | Control | Candidate |
|---|---:|---:|
| Median request seconds |4.038|3.962|
| Maximum request seconds |6.270|6.692|
| Sum request seconds |26.578|25.420|
| Input tokens |24,502|24,982|
| Final output tokens |6,842|7,111|
| Provider reported total tokens |31,344|32,093|

Total input49,484 and output13,953 tokens; provider total63,437. Candidate annotation adds80 reported input tokens per call (480 total). Low thinking and8192 allowance remain on every wire; thought counters are not reported, so normalized zero is not proof that thinking was absent. No output is capped by max tokens; all finishSTOP. No price or billing conclusion is invented and billing configuration is not changed.

Durations cover the existing consented reasoner request and local release replay within the120 secondrequest envelope. There is no planning or reader stage in this fixed-evidence comparison, so this is **not full complex application latency**. All 12are below120 seconds. No cold/warm experimental claim is made.

Quota ledger:99 retained rows before,62 after, comprising12 new reservations plus50 surviving prior rows;49 older entries expire under the existing rolling24hourpolicy. Every expired record was already over24 hours old at first dispatch, every surviving prior record is unchanged, and all99 before rows remain archived in `quota-before.json`. No manual deletion, reconstruction or quota reset occurs.

Peak rolling-minute dispatches12/15; actual input49,484/150,000TPM; reconstructed conservative admission peak65,536/150,000; after-run daily ledger62/500. Conservative peak is computed from the adapter's serialized-byte reservation plus prior finalized actual usage, not treating210,082 frozen bytes as token usage. Shared pacing/ledger enforcement remains authoritative. All 12 authorizedattempts are consumed; no further call or automatic quota request is permitted by this authorization.

## Tests, preservation and final stop

Application runtime remains byte-identical to the frozen110hash manifest. Reuse the already verified176 affected tests and final 69 focused checks (overlapping), plus prior30 unchanged historical replays; no unnecessary broad rerun or new intelligence-test credit. The new runner's zero-dispatch preflight checks all 12exact bodies/schemas/consent cells, and every actual send asserts frozen byte equality and the one-call/order/cap guards. No application source, schema, instruction, checker or oracle was changed after observing outputs.

[Preservation proof](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261102T123607Z-timestamp-contract-live/preservation-before-handover.json) verifies unchanged HEAD840031451e954809f2817adf78d800bc6548c2d4, binary/logical index, all 42 ordinarytable fingerprints, both environment files,1,164 historical protected files before checkpoint append, all 1,923knowledge files/341 active artifacts and active release7a14a351e52b49aeb87f65d1192f0937. Inherited27 missing temporary fixtures remain absent. Only six owned evaluation conversations and six sealed synthetic state files are added in the reused disposable evaluation context.

The new runner is `backend/scripts/evaluate_timestamp_contract_live.py`; no provider bypass or new runtime architecture is added. New files otherwise contain audit/grade/report data. Credential headers/values are not stored; error serialization redacts configured credentials. No service restart, browser/editor/Ollama action, model installation, stage/commit/reset/clean, publication/deployment or device action occurs. No new browser preservation/readback or acceptance is claimed.

Keep `COGNISHIELD_AI_SOURCECLAIM_TIMESTAMP_EXPERIMENT` unset/off and both older experiment flags OFF. They remain ordinary defaults; no environment file was edited. Existing source/retrieval/transport/simulator/release behavior remains authoritative. The description candidate is preserved for reproducibility but not promoted. Stop after this handoff; no new prompt experiment, model comparison or reasoning layer is selected or launched.
