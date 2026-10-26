# Gemini 3.5 Flash-Lite controlled evaluation — 2026-10-25

**Recommendation: TEST FLASH-LITE FURTHER. Keep the current Qwen2.5 + Gemini3.8 experimental architecture unchanged and disabled for ordinary remote inference.** Flash-Lite is substantially more usable in this small service window than the prior Gemma run, but one causal relationship failure and an incomplete comparison prevent a readiness recommendation. This is a bounded direct-inference experiment, not gateway integration or G4/G5/G6/G11 acceptance.

## Gemma failure investigation — read-only

No additional Gemma request was made. The eight server errors in the ten-case minimal-thinking cohort classify as follows:

| Original Gemma case | HTTP | Provider numeric code | Provider status | Observed failure stage |
|---|---:|---:|---|---|
| H01 |500|500|INTERNAL| Provider error response; no completed model output |
| H02 |500|500|INTERNAL| Provider error response; no completed model output |
| H03 |503|503|UNAVAILABLE| Provider reports high demand; no completed output |
| H05 |500|500|INTERNAL| Provider error response; no completed model output |
| H06 |500|500|INTERNAL| Provider error response; no completed model output |
| N01 |503|503|UNAVAILABLE| Provider reports high demand; no completed output |
| N02 |503|503|UNAVAILABLE| Provider reports high demand; no completed output |
| N03 |500|500|INTERNAL| Provider error response; no completed model output |

The remaining minimal cases were H04 (completed but partial) and N04 (local `TimeoutError` at120.01seconds, without a recorded complete HTTP status). The latter is **not an HTTP504 returned by Google**. No400/422 contract rejection,429 quota error or authentication/billing rejection was recorded in that cohort.

Separately, the prior strict-schema probe and high-thinking H01 each returned500; high H04 completed. Across the earlier15 generation attempts including probes, this totals7HTTP500,3HTTP503,1local timeout and4HTTP200. Probe failures are not additional independent reasoning cases.

HTTP classification is not a diagnosis of Google's hidden backend. A500 could include an internal request-handling bug; the record does not reveal whether inference began or why it failed. A503 explicitly reports high demand. Neither proves inferior Gemma reasoning or exhaustion of the16K quota. The previous120second timeout might have completed later; the current relaxed testing allowance cannot answer that retrospectively, and no Gemma rerun was authorized here.

Exact records, hashes and stage classifications: `tmp/phase-g/iterations/20261025-flash-lite-35/gemma-failure-classification.json`. All original Gemma traces remain unchanged.

## Flash-Lite API and frozen experiment

The existing ignored backend credential authenticated against model metadata (HTTP200), and **`gemini-3.5-flash-lite`** returned exact `COGNISHIELD_FLASH_LITE_READY` in1.45seconds. The actual response identifies `gemini-3.5-flash-lite`; discovery advertises version `3.5-flash-lite-07-2026`, generateContent and structured capabilities. This is real generation access, not model-list availability alone.

The official generateContent REST interface was used, not a copy of the existing Gemini3.8 Interactions body. Original system text maps exactly to `systemInstruction`, original user/assistant text to user/model `contents`, and unchanged schemas to `responseJsonSchema` with JSON MIME. Sampling parameters were omitted and every request ends in the original user turn. [Official API changes](https://ai.google.dev/gemini-api/docs/generate-content/whats-new-gemini-3.6) document deprecated sampling controls and prefill restrictions; the [model page](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite) lists structured-output support.

Ten cases were frozen before inference:

- C00: minimal synthetic connectivity.
- S01: separate schema/field-obligation probe, including unavailable evidence represented as false and no source claims.
- H01–H06: exact preserved authoritative evidence, original user instructions, conversation references, schemas and expected outcomes from the Gemini3.8 comparison.
- S02: preserved actual IntentPlan packet M11, requiring operational records and failed-hop interpretation without a write.
- S03: preserved semantic-routing control M12, a general Python question that should not inherit editor/files/history.

Historical Gemini3.8 and Qwen answers were reused; no new calls were made to either model. No new case-specific wording, schema relaxation, answer repair or response-driven grading criterion was introduced. Full-answer grading is by the implementation assistant against preserved source-derived expectations, not a blinded external certification. The cases are exposed and receive no new generalization credit.

The six reasoning cases request `low` thinking; the four connectivity/structured/routing probes request `minimal`. All reasoning/planning allowances are8192 tokens to leave room for complete output. Historical Gemini used2048 and Qwen512. Final outputs stopped normally far below the new allowance; nevertheless, allowance, endpoint and service-window differences remain confounds. Historical requests contained temperature0, while the new API omits deprecated controls; actual cross-model sampling equivalence is not established.

## Complete-answer results

| Case | Preserved expected task | Flash-Lite review | API seconds |
|---|---|---|---:|
| H01 | Route exists but down egress prevents modeled delivery | **Qualified adequate:** correct route/egress dependency and source binding; exact ICMP/VRF scope remains implicit |1.44|
| H02 | Both intended links with each device's own port | **Adequate:** both pairs correct; recorded inventory qualifiers and no physical-implementation proof |1.29|
| H03 | Show saved commands despite unavailable logs, explain limit | **Qualified adequate:** exact CLI and separate historical/unavailable-source limitation; terse interpretation |1.28|
| H04 | Map published OSPF fields and explain remaining uncertainties | **Partial:** correct mapping and unverified current activation, but incomplete compatibility/full-validation caveat |1.36|
| H05 | Interface states and the specific failed hop | **Failed:** correct state facts followed by inconsistent hop localization and an unsupported sequence |1.42|
| H06 | Useful contextual read-only recommendation, without collection | **Qualified adequate:** a relevant unexecuted state question; destination/service scope remains unspecified |0.91|

**Selected-case complete-task adequacy:4/6 including three qualified answers.** The preserved Gemini3.8 result remains6/6 including three qualifications; Qwen remains0/6. Qualified H01 uses the same implicit recorded-scope tolerance as the historical Gemini assessment, rather than imposing a new literal ICMP/VRF wording requirement after inference. H03/H06 are useful factual/advisory replies, not demonstrations of independent causal discovery.

H04 correctly identifies process20, router ID198.19.213.1 and GigabitEthernet0/1 area0, and explains conditional process_id requirements. It does not generate configuration or claim the saved capture is current. It still omits unresolved target compatibility and the distinction between mapped CLI text and a fully validated operation-parameter object. Those were required in the original expected outcome; correct field extraction is not complete comparison fulfilment.

H05 fulfils its first outcome by naming up/down states correctly. Its second says **“The modeled path fails between Spruce-Start and Willow-Relay”**, even though the supplied calculation places the blocked egress on **Willow-Relay ge-0/0/1.0 toward Granite-End**. Its “subsequent ingress failure” wording also treats separately recorded forward and return results as a temporal/causal sequence. The interface name is correct, but the surrounding explanation does not reliably fulfil the requested specific-hop relationship. All decisive facts reached the model; this is not a newly demonstrated retrieval/projection loss.

H02's “active in inventory” wording is supported by this specific packet: the recorded device is active and interfaces contain up administrative/operational/status fields. The answer explicitly withholds physical implementation proof. That is a source-bound record statement, not evidence of live measurements or generic reachability.

H06 proposes `network.state` for Spruce-Start with a rationale about absent fresh evidence. It does not execute that question, claim current health or misuse an inventory address as a measurement. It remains a broad candidate, not a uniquely best diagnostic sequence without a destination/service.

Only H01/H05 assess causal interpretation; one succeeds with a scope qualification and one fails. The calculated source already describes the modeled fault, so even H01 is interpretation of authoritative calculations, not autonomous discovery of arbitrary root causes. Repeating factual records earns no causal-reasoning credit.

## Structured output, planning and release-safety observations

All nine schema-bearing replies were syntactically valid JSON and satisfied the complete unchanged local schemas. The API accepted the schema configuration. This verifies compatibility in these samples, not every possible schema constraint or the truth of the prose. C00 was plaintext, so JSON validation is not applicable rather than a failure.

S01 returns exactly the required status/boolean/empty-array values. S02 and S03 also parse through the current application `IntentPlan` and `SemanticRoute` Pydantic types:

- S02 chooses read-only answer with state and topology needs, preserving both requested outcomes and avoiding generation/edit/clarification. It unnecessarily adds inventory for “administrative records”; source efficiency/alignment is only partial. These are **model-proposed readers**, not actual authorized reader executions.
- S03 correctly chooses general answer with editor, attachments and history all false. No unrelated document or engineering context is requested.

A read-only replay of the existing narrow forwarding checker returns no errors for both correct H01 and problematic H05. The existing published-field checker similarly returns no errors for incomplete H04. These helpers do not universally verify causal localization or complete task obligations. No new guard was added and no raw answer repaired to turn a failure into a success. The replay is not full gateway release testing.

## Reliability, time and usage

Exactly **10 cloud inference requests and1 metadata GET** were made to Flash-Lite; there were no retries. All10 inference requests returnedHTTP200 with STOP and a final answer. Nine were schema-bearing, all9 passed local schema validation. There were no400/422,429,500/503 or local timeout responses in this new run. HTTP completion is scored separately from the two inadequate reasoning answers and partial planning source choice.

API latency across all10: **0.76–1.45seconds, median1.33seconds**. All10 finished within the original120second target. The requested relaxed testing policy was implemented as a **300second test-only hard ceiling**; no response needed the extension. Existing application deadlines were not changed. Initial quota pacing is recorded separately; these figures are direct API latency, not full shared-gateway or UI end-to-end timing. No controlled cold/warm or hardware comparison was performed.

Known usage: **13,019 input tokens and1,304 final output tokens**,14,323 reported total. Requests specified low/minimal as declared, but responses do not report a thoughts-token count. Zero summed reported thinking tokens must not be treated as proof that no internal reasoning occurred.

The sequential ledger uses reported prior input usage, a conservative next-body reservation and at least4.1seconds between starts. Peak starts in61seconds were9; peak conservative input reservation was20,724, below the user-observed15RPM/250KinputTPM allowance. Only10 of the stated500 daily requests were made by this experiment. Other account activity and actual project quota/billing are not observable from these traces; no throughput/RPD stress test is claimed. No billing, purchase, tool-grounding or quota-change API was called.

## Comparison and decision

| Measure | Qwen2.5 — preserved | Gemini3.8 — preserved | Flash-Lite — new |
|---|---|---|---|
| Selected H01–H06 adequate tasks |0/6|6/6 qualified|4/6, three qualified |
| Causal interpretation | Completed failures retained | H01/H05 supported within recorded scope | H01 supported; H05 relationship/sequence failure |
| Source roles and relationships | Prior failures retained | Selected link/contract mappings correct | H02/H03 correct; H04 incomplete caveat; H05 inconsistent localization |
| Schema validity versus truth | Valid JSON did not ensure correctness |6/6 selected direct schema-valid |9/9 schema-bearing valid, including two inadequate answers |
| Direct API latency | Five isolated matched replays10.39–23.49s; sixth came from an earlier gateway stage | Six selected answers4.29–31.04s | Ten requests0.76–1.45s |
| Availability in sampled window | Local successful inference could still reason incorrectly |6/6 direct completions; prior separate gateway synthesis4/7 |10/10 completions in this small sample |
| Quota | Local resources | User-reported20RPD, not rechecked | User-observed15RPM/250KinputTPM/500RPD; not independently certified |

The reliability and speed are promising for further controlled evaluation, especially typed routing/extraction. They do not establish parity with Gemini3.8 on multi-source reasoning, and the known semantic-verifier gap makes an immediate engineering interpretation switch unjustified. No fallback path was involved in this experiment; every reviewed answer is raw model text. No G4/G5/G6/G11 gate closes from this selected small set.

A future separately authorized experiment should use new frozen relationships/compound comparisons and an actual synthetic authenticated gateway path, checking whether correct raw interpretations survive and whether incomplete/incorrect ones are safely withheld. Any later transport integration should stay in the existing provider domain, preserve the owner/source/privacy approval gate and request-wide budget, and adapt the generateContent message/schema/usage fields explicitly. Merely replacing the current model string or assuming schema validity certifies the answer is insufficient. No new planner, runtime guard, provider switch or implementation is proposed for automatic execution now.

## Preservation, evaluator and evidence

Only the standalone `backend/scripts/evaluate_phase_g_flash_lite.py`, sanitized evaluation results and documentation were added. Five offline adapter check groups pass: exact schema/message preservation and API controls; incomplete/schema-invalid/thought separation; provider-error redaction with no retry; interrupted-request replay rejection; persistent12-call experiment ceiling. These are mocked harness checks, not AI-quality evidence. A reporting-only aggregation error initially tried to count plaintext's inapplicable schema value; it was corrected without changing any model output or grade criterion, and its record is retained. No unrelated application regression suite was rerun because application code did not change.

Frozen profiles and originals: `tmp/phase-g/iterations/20261025-flash-lite-35/manifest.json`, `packets/`. Raw responses/timing/usage: `results/C00.json`, `S01.json`, `H01.json`…`H06.json`, `S02.json`, `S03.json`. Full grades: `full-answer-review.json`; current-helper replay: `existing-contract-verifier-replay.json`; pacing: `quota-events.jsonl`; actual console sequence: `probe.log`, `cohort.log`. Credential values and headers are absent.

Curated result: `docs/evaluations/phase_g_flash_lite35_result.json`. State proof: `tmp/phase-g/iterations/20261025-flash-lite-35/preservation-before.json` and `preservation-after.json`.

Qwen2.5 remains the explicit local baseline; the current Gemini3.8 provider/model, disabled hybrid flag and disabled Approach A remain unchanged. Ordinary SQLite, protected source/config/editor state, all prior evidence, Git HEAD/index and the active341-artifact V9 release are preserved. No ordinary service restart, browser/editor operation, commit, staging, publication, deployment, model download or billing activation occurred. Editor buffers were protected by leaving UI/editor APIs and browser storage untouched; no fresh buffer-hash or browser acceptance is claimed. No runtime rollback is necessary because nothing was activated or replaced.

**Stop at this evaluation checkpoint. Continue using the existing Gemini3.8 experimental configuration unchanged; await authorization before any Flash-Lite integration or switch.**
