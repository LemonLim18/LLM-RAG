# Controlled Qwen3.5 capability experiment — 2026-10-25

**Decision: RETAIN BASELINE. Bounded experiment finished; no application integration is admitted.** Qwen3.5 improves several core relationships and field extractions, but complete-answer adequacy does not improve in the matched set. Unsupported statements, incomplete requested outcomes, and timing failures remain. Approach A remains disabled by default. No G4/G5/G6/G11 acceptance or ordinary promotion is implied.

**Ordinary-model warning:** configuration was and remains `auto`. A final read of the unchanged discovery function resolves it to `qwen3.5:4b`, following the user's installation and changed tag order. This experiment did not activate or pin an ordinary model. Explicitly select `qwen2.5:1.5b` in the existing model selector when baseline behavior is wanted. Do not mistake unchanged configuration text for a stable effective auto selection.

## Frozen design and intended changes

Before inference, twelve distinct synthetic historical gateway packets and source-derived expectations were frozen in `tmp/phase-g/iterations/20261025-controlled-qwen35/manifest.json` (SHA256 `3ca285d3554c9281af778d636dac7669283b2cb4d89f0630a99b59eb62cdf7e8`). Original packet hashes, exact messages, schemas, assistant surface and origin trace are retained. No original evidence is overwritten. These exposed conditions receive no unseen-generalization credit. Expectations were checked against the authoritative records by the implementation assistant; this is not independent external certification.

| ID | Condition | Original surface | Stage |
|---|---|---|---|
| M01 | Route present, down egress and failed forwarding | Studio | Synthesis |
| M02 | Healthy two-direction delivery and reverse-scope limits | Floating | Synthesis |
| M03 | Return-path endpoints, stopping device and no-route reason | Studio | Synthesis |
| M04 | Two planned links with exact device/port ownership | Floating | Synthesis |
| M05 | Available saved configuration plus unavailable syslog; two outcomes | Studio | Synthesis |
| M06 | Published OSPF requirements mapped to saved commands and unknowns | Floating | Synthesis |
| M07 | Contextual advice without collection; incomplete destination scope disclosed | Floating | Advisory |
| M08 | Equal captures, distinct timestamps, no unobserved-interval inference | Floating | Synthesis control |
| M09 | Proposed document timers establish neither present use nor non-use | Studio | Document control |
| M10 | Unsaved OSPF/BGP buffer, field roles and markers; no changes | Studio | Editor explanation |
| M11 | Read operational state and explain failed modeled hop | Floating | Structured planning |
| M12 | Unrelated Python slicing question excludes ambient engineering sources | Floating | Routing control |

Matched arms: `qwen2.5:1.5b` and `qwen3.5:4b` with `think:false`. Both use unchanged messages/schemas, context8192, output512, temperature0 and identical explicit sampling options. Explicit options override differing model-file defaults. Streaming is normalized to retain partial output. The historical document/editor allowance was768; the matched comparison deliberately uses512 on both models. Thinking-on512 is a separately scored three-case subset M01 / M05 / M06. Optional, separately labelled allowances are off1024 on M01 / M05 / M06 and on1536 on M01/M06; no results from these arms replace matched512 scores.

The evaluator makes one sequential call per condition, no automatic retries, with a hard30/60/120-second simple/moderate/complex wall. Those measurements are isolated inference, not full gateway latency. The API's combined generated-token count is retained; absent separate thinking/final token counters remain unknown, with the two output fields retained independently. No estimated character counts are presented as tokens.

Initial code addition: only `backend/scripts/evaluate_phase_g_model_comparison.py`, an audit-only explicit-action replay utility. No application imports, ordinary database writes, new dependencies, model downloads or global configuration. Full manual answer review remains necessary: schema success is not semantic completion.

Conditional integration, only after credible comparison results: reuse gateway and model adapters with explicit experimental model selection and a request-scoped monotonic deadline capped at120-seconds, shared across planning, readers, synthesis and optional repair. Reserve answer time, decline retries that cannot fit, and distinguish provider failure/incomplete generation from completed rejected content. Keep existing defaults and Approach A off. Do not add a planner or modify V9. Any measured larger-token setting must remain explicitly experimental.

## Inspected runtime before changes

- `lab_config` and `local_providers.chat.runtime` select the existing Ollama endpoint and model. Current `.env` uses `COGNISHIELD_LOCAL_OLLAMA_MODEL=auto`; auto selects the first installed conversational tag. New tag order therefore poses a pre-existing implicit-promotion risk. The experiment uses explicit model names and does not edit `.env` or restart ordinary servers.
- `gateway.turn` owns conversation/idempotency and wraps the request in240seconds. LangGraph `engine.run` uses120-seconds for Floating and210for Studio. `RoutingModel` uses30-seconds per inference, context8192/output512, with existing shared call/input/round limits.
- The existing LangChain adapter supports `reasoning`, translated to Ollama `think`, but does not currently set it. Generic/document generation uses the separate existing OllamaProvider path and different output/time limits. Model-specific thinking is not currently controlled there either.
- Existing synthesis performs a bounded repair for both provider failures and invalid content, using the same correction wording. This conflates a timeout without a draft with semantic rejection. Deterministic read/capture/flow fallbacks and V9 authority remain intact.
- Ollama0.40.2 advertises Qwen3.5 thinking/tools/vision and Qwen2.5 completion/tools. Qwen3.5 local artifact digest `d8b0f5e9760cd1682034f292d7ef72ec46f432149be0df7574bf2d6e92e38c04`, Q4_K_M,4.2B,3,324,173,934 disk bytes. Baseline digest `65ec06548149b04c096a120e4a6da9d4017ea809c91734ea5631e89f96ddc57b`,Q4_K_M,1.5B. Model catalogue context limits are not the configured8192 experiment window.
- Installed langchain-ollama1.1.0,ollama0.6.3,langgraph1.2.15,httpx0.28.1. No package changes.
- Read-only preservation snapshot: `tmp/phase-g/iterations/20261025-controlled-qwen35-preservation/before.json`. HEAD93f5f45, existing dirty tree/index retained, ordinary SQLite hashed by table, active release `7a14a351e52b49aeb87f65d1192f0937` and341 artifacts verified. No fresh browser-buffer claim; no UI operation performed.

## Execution/review status

All calls are finished. Exactly32 generative calls: original12 × 2, supplementary positive control1 × 2, thinking512x3, thinking1536x1, and two separately labelled resource/budget checks. Empty-message request-local unloads and metadata reads are not generative tests. No overlapping rerun is counted as a new condition.

### Oracle/input correction, without replacing evidence

Full inspection found that historical M08's packet contains only one visible current configuration row, with `total:2,truncated:true`. Its original expectation incorrectly assumed two visible captures. The original packet, oracle and answers are retained. Neither model can complete a two-capture comparison from that input. Qwen2.5 nevertheless invented temporal continuity; Qwen3.5 recognized the absent visible operand, though its categorical wording about the whole dataset overlooked truncation. This is a historical packet/projection and evaluation limitation, not a newly reproduced current-application defect.

Before its inference, M13 was frozen as a distinct positive conversation/arithmetic control: `Hello again. What is 19 multiplied by 7?` Both models answer133 accurately, without private context. Supplement manifestSHA256 `babe412b41385099c5ec4f3f2b7d08b084c3aeeb5f44717c1c90e843f0f3e38e` preserves the parent freeze hash. The validated score set has12 conditions: original set minus M08 plus M13. M08 remains an additional missing-evidence control; it is not silently replaced or credited as a completed comparison.

M01 oracle clarification also preserves the evidence rather than over-penalizing the model: a return branch ending at Granite-End with an ingress-down reason supports a device-level stopping inference. A precise interface identity is not supplied. The real unsupported OSPF Established-versus-Full assertion and physical-versus-simulated attribution remain failures.

### Matched full-answer results

| Measure | Qwen2.5 1.5B | Qwen3.5 4B, thinking off |
|---|---:|---:|
| Original frozen12 conditions adequate, with M08defect disclosed |2/12|2/12|
| Validated12 conditions adequate, including supplementary M13 |3/12|3/12|
| Adequate model answers among10 valid answer conditions |2/10|2/10|
| Strictly adequate causal explanations |0/3|0/3|
| Raw routing/planning conditions correct within their original allowance |1/2|1/2|
| Valid final JSON among10 schema-constrained calls, including M08 |9/10|8/10|
| Timeouts among13matched calls |0/13|2/13|
| Token-limit endings among13matched calls |1/13|0/13|
| Median isolated inference, all 13 calls |11.44s|35.28s|
| Median isolated inference, validated12 conditions |11.39s|39.56s|

These are raw model outputs, with no factual repair, deterministic reconstruction or fallback credited. Reader/evidence selection is held fixed for answer packets. Two routing/planning packets test raw proposals only; they are not authenticated reader invocations. Full gateway workflow/source-selection accuracy and user-request latency are **NOT MEASURED** here. Both assistant surfaces are represented by their original actual gateway packets. No actual browser acceptance or new live-network capability is claimed.

| Condition | Baseline | Qwen3.5 off | Full-answer finding |
|---|---|---|---|
| M01route versus failed flow |FAIL|FAIL; causal core improves|Baseline says route sufficient. New model correctly connects down egress to failure, but calls OSPF Established instead of Full and describes simulation as physical.|
| M02healthy bidirectional flow |FAIL, token512incompleteJSON|TIMEOUT119.51s|No completed model answer to credit. Partial output remains archived.|
| M03 return ownership |FAIL|LIMITED, not counted PASS|Baseline reverses return destination. New model finds Granite-End/no-route correctly, but adds an unrecorded egress-interface stopping detail and omits scope qualification. Original system/user directional scope tension is disclosed.|
| M04planned port ownership |FAIL|FAIL, partial improvement|New model preserves Willow ports/planned attribution but omits Granite-End's explicitly requested port.|
| M05available config/unavailable logs |FAIL|FAIL, source relationship improves|Baseline denies available configuration. New model separates availability correctly, but summarizes instead of displaying the requested saved commands. Normal stop, not token exhaustion.|
| M06published mapping |FAIL|FAIL|New model quotes process 20 then denies explicit process-ID configuration and invents implicit defaults; confuses schema fields with native CLI. Historical/current distinction is correct.|
| M07advisory |FAIL|FAIL, more concrete suggestions|New questions are less circular, but incorrectly treat traffic/utilization evidence as confirmation of forwarding and overstate protocol observations. Missing destination scope prevents a uniquely best-check oracle.|
| M08capture control |ORACLE/INPUT DEFECT|ORACLE/INPUT DEFECT|Baseline overclaims continuity; new model identifies missing visible capture, with dataset-absence wording warning. Not in complete-evidence score.|
| M09proposed document values |PASS|PASS|Both preserve proposed22/88timers and establish neither present use nor non-use.|
| M10unsaved editor |FAIL|FAIL, field extraction improves|New model extracts correct OSPF/BGP values, but first says KEEP_BASELINES is missing then quotes it, invents marker implications and line numbers.|
| M11operational compound plan |FAIL, wrong reader plan|TIMEOUT29.51s|No completed new plan in original30-second stage allowance. Separate warm check below is not substituted.|
| M12unrelated Python routing |PASS|PASS|No private sources, editor, attachments or clarification.|
| M13arithmetic positive control |PASS|PASS|Correct133, no irrelevant engineering context.|

Sensitivity: crediting the limited M03 return answer would raise Qwen3.5 to4/12valid conditions and1/3 causal explanations. It would not remove the explicit protocol/process-ID/marker contradictions or incomplete command/port outcomes. The conservative integration decision does not rest on that one grading judgment. Improvements in causal core or field extraction are real partial observations, not full-task reasoning successes.

### Thinking and output allowance

Ollama request bodies explicitly carry `think:false` on all 13off calls, which return no thinking output. Thinking subset bodies carry `think:true`, and return a distinct nonempty `message.thinking` field. The installed model advertises thinking; `api/show` did not expose separate thinking-level metadata. The exercised boolean behavior, not a name-based assumption, verifies the mode.

| Configuration | Cases | Final answers | End condition | Inference time |
|---|---:|---:|---|---|
| Thinking on,512 tokens |M01 / M05 / M06|0/3|All finish with`done_reason:length`,512total generated tokens, empty final content|49.66/47.84/49.29s|
| Thinking on,1536 tokens, separate configuration |M06only|0/1|119.51second timeout, no final content|119.51s|

The512 thinking limit demonstrably prevents final answers in this subset. A1536allowance still does not yield a final answer within the complex target in the tested case. The timeout has no final token counters; no1536-token exhaustion is asserted. API total generation counts are preserved; the API does not provide separate thinking/final token counters here. Separate fields/character counts are logged without pretending characters are tokens. Raw thinking is retained in the ignored audit only; its presence/length is not reasoning-quality credit.

Off-mode wrong answers generally stopped normally below512 tokens. An off1024extension was therefore **NOT RUN**: more output space would not explain those completed contradictions or omissions. No automatic larger-output or thinking profile is enabled.

### Latency, residency and the120-second request target

Cold baseline M01:2.86 s load,18.91 s prefill,1.70 s decode,total23.49s. Cold Qwen3.5 M01:9.25 s load,56.01 s prefill,22.13 s decode,total87.43s. Two-model residency left about414 MiB OS free during the early new-model arm. The completed baseline's1.37 GB cache was released with a request-local empty-message`keep_alive:0` call. That is not a model deletion or global setting change; the timing confound is retained.

Two separate exposed calibrations were declared before execution:

- M02off512with baseline no longer resident completes validJSONin34.38s. It reuses5,126 of 5,130prompt tokens; this is a warm-cache result, **not proof that memory unloading alone caused the improvement**. Its final explanation still overstates a calculated trace as returned ICMP traffic and symmetric routing configuration. Core modeled delivery is correct; full release-safe interpretation is not established.
- M11off512with a separately allowed60-second planning stage completes in7.16s, reusing1,386 of 1,390prompt tokens. The final plan includes required state/topology but adds inventory. This demonstrates minimum source coverage with redundant retrieval proposals, not exact minimal source selection. Because actual completion is below30-seconds with extensive caching, improvement cannot be attributed to the60-second allowance itself.

The original matched scores/timeouts are unchanged. These two checks are not new conditions. Timing is substantially cache/residency dependent. It is incorrect either to promise the120-second full-request target or to declare every complex request impossible on this hardware from the cold traces.

`elapsed_ms` measures isolated inference, not packet preparation, metadata/schema processing, gateway planning+readers+synthesis+verification or browser delivery. **No actual gateway end-to-end120-second acceptance is claimed.** The stage replay uses30/60/120-second targets with a0.5second inference margin and no retries; it is not an installed request-wide application budget. In particular,M11's initial30-seconds is a planning-stage allowance, not a claim that its full compound task is simple.

The proposed coherent integration budget, deliberately **not installed after admission failed**, is one monotonic deadline bound at gateway entry and propagated to graph/provider calls. Cap the whole complex request at120-seconds; reserve answer time before planning, bound readers by remaining time, leave response-finalization margin, and admit optional repair only if its measured cost fits. Initial planning ceiling30-seconds, reader allowance up to 5seconds, answer uses only remaining time minus 2seconds, optional repair only when at least30-seconds remains. Simple/moderate30/60targets may be selected from existing route/outcome information without a new classifier. Do not add stage ceilings together as an entitlement to exceed the shared deadline. Provider timeout, token-limited incomplete output and completed semantic rejection must remain separate outcomes. Existing production30/120/210/240limits and retry behavior remain unchanged because no profile was admitted.

### Resources, safety and limitations

Inspected hardware:i5-13420H,8 cores / 12 threads,16,888,094,720 bytes RAM,IntelUHDgraphics. Ollama reports no GPU offload for either model. Reported loaded sizes:baseline1,367,647,190bytes;new3,355,422,227bytes at context8192. These are Ollama residency estimates, not an OS peak-memory measurement. Only snapshots of free memory/process usage were taken; no fabricated peak or token/s figure is inferred from incomplete calls. Hardware logs and per-call`api/ps`receipts retain the observations.

No model explanation gains verification credit merely from copied values, published citations or deterministic calculations already present in its input. No new validators/phrase guards, source-registry changes, V9 changes, framework/planner, model download, dependency installation or application settings change. All model results are audit-only; no experiment answer is released into ordinary user conversations. Current release-safety limitations remain and are not repaired by a model swap.

The stronger model's more plausible detailed prose can still contain unsupported claims. The factual/citation verifier is not universal semantic certification. Exact generation/schema/source behavior is separate from adequacy, and the selected small exposed set is not a capability-wide failure rate or new G11benchmark. No genuine Ansible generation, editing or network execution was attempted in this study.

### Regression and preservation

- Focused existing model diagnostics: **3 PASS in 1.06 seconds**. These are mocked integration/trace checks, not intelligence evidence. No broad regression or120/30benchmark rerun.
- Deterministic comparison checks: all 13 pairs preserve identical messages/schemas/sampling options; all 13thinking-offrequests carryfalseandreturn no thinking field content. Original packet file hashes and original freeze hash remain intact. No overlapping reruns summed as successes.
- Before/after preservation **PASS**: HEAD93f5f45,index,all ordinary SQLite table fingerprints,active releasepointer,341 artifacthashes,and inspected application/.envbytes unchanged. No browser operation or buffer save; no fresh editor-buffer hash claimed.
- All experiment calls ended; initially empty model residency restored using request-local unloads of evaluation models. Installed model files and server configuration remain intact. No staging,commit,publication,deployment or physical-deviceaction.
- Source changes consist only of this report, the new evaluation utility and sanitized condition registry. Application code is unchanged. No actual-gateway/API or browser regression is claimed: conditional integration failed admission, so there is no new integrated profile to accept.

## Decision and safe continuation

**RETAIN BASELINE.** Neither ordinary use nor a feature-gated application profile is promoted by this result. Qwen3.5 shows partial gains in source relationships, field extraction and causal core, but not a credible complete-answer improvement in the matched set. Thinking512does not produce final answers, and the single1536experiment does not finish before120-seconds. Warm performance is promising but does not establish request-wide latency or release safety.

Keep`COGNISHIELD_AI_OUTCOMES`unset/0. All Phase G stage statuses remain unchanged; no G4/G5/G6/G11acceptance. Stop at this checkpoint. Any future work needs authorization; no Approach B or broader Approach A cycle starts automatically.

Rollback: no application/data/release rollback is needed. Retain the historical failure records and new ignored audit. The added evaluator is opt-in and makes no inference without an explicit`--arm`; deleting it is unnecessary. Do not reset the dirty tree. To repeat an authorized diagnostic, use a new audit arm/folder or a new frozen supplement; existing result files refuse overwrite. For ordinary baseline behavior use the existing explicit model selector, because current`auto`discovery resolves to the newly installed tag. This report does not silently alter that policy.

Evidence root:`tmp/phase-g/iterations/20261025-controlled-qwen35/`; preservation root:`tmp/phase-g/iterations/20261025-controlled-qwen35-preservation/`. Original/final reviews, manifest/supplement, wire bodies, raw final/thinking fields, completion diagnostics, latency and resource/calibration records are retained. No original first-pilot/reconciliation evidence was changed.


API reference: [Ollama thinking controls and separate output fields](https://docs.ollama.com/capabilities/thinking). Local request/response evidence, not public model benchmark claims, establishes the tested behavior.
