# Gemma 4 31B capability evaluation — 2026-10-25

**Recommendation A — KEEP GEMINI 3.8 in its existing disabled experimental configuration. Do not replace it with Gemma.** Gemma authenticated and generated small test responses, but the requested capability cohort was predominantly unavailable. This is evidence against replacement **at the tested service conditions**, not proof that Gemma's underlying reasoning is worse. No application integration, model switch, billing activation or Phase G acceptance was performed.

## Scope and frozen design

The experiment reused all six exact synthetic H01–H06 evidence packets, original user instructions, source identities, expected outcomes and application JSON schemas from `docs/PHASE_G_HYBRID_GEMINI_EVALUATION.md`. Historical Gemini and Qwen outputs were reused; **no new Gemini3.8 or Qwen inference calls** were made. Original results were neither overwritten nor rescored to make Gemma pass.

Before inference, four additional source-derived synthetic conditions were frozen with expected outcomes. IP prefix/next-hop relationships were checked deterministically, and N03 captured the actual existing `planning.propose` messages and IntentPlan schema without executing a model or reader. Expectations were authored/reviewed by the implementation assistant against separate source records before inference, not by a blinded external reviewer.

- **N01:** Palm→Quartz→Reef, TCP443/VRFblue. A route exists, but Quartz egress is admin-up/oper-down; return direction was not tested. Explain the scoped immediate failure without inventing shutdown or physical cause.
- **N02:** Vale saved/current addresses and descriptions differ; syslog source is ERROR. Fulfill both comparison and missing-log/next-check outcomes, without inventing change timing or operational health.
- **N03:** Actual IntentPlan classification of a current-versus-backup comparison plus interface-state context, explicitly excluding syslog and engineering writes. Preserve both information needs and configuration scope `both`.
- **N04:** Contextual advice for Alder Ethernet7/1 with an inventory address, stale down observation and failed current-state reader. Recommend two specific read-only questions without collecting or declaring current up/down.

Frozen inputs/expectations: `tmp/phase-g/iterations/20261025-gemma4-31b/manifest.json` and `packets/`. The manifest hash, every packet hash and original historical-evidence hashes were verified after inference. New conditions are scored separately; reruns are not new independent conditions.

## API access and request format

Google's model metadata request returnedHTTP200 for **`gemma-4-31b-it`**, version001, with `generateContent` and `countTokens` advertised,262144 input/32768 output limits and thinking support. The existing credential was read from ignored `backend/.env`; it was never printed, copied into source, request bodies, logs, reports or backups.

The official `generateContent` endpoint was used, not the current Gemini provider's Interactions transport. Original system text went through `systemInstruction`; user/assistant messages became `contents` with user/model roles. No remote tools, files, cache identities, cloud conversation IDs or ordinary application records were supplied. [Official Gemma API documentation](https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api) documents the endpoint and `minimal`/`high` thinking controls.

| Probe | Actual outcome | API seconds | Interpretation |
|---|---|---:|---|
| Model metadata |HTTP200|0.46| Authentication and model discovery pass |
| Plain synthetic connectivity |HTTP200, exact COGNISHIELD_GEMMA_READY|23.74| Actual generation permission confirmed |
| Small strict `responseJsonSchema` probe |HTTP500 INTERNAL|0.57| Full provider schema enforcement **unverified**, not established unsupported |
| Small `responseMimeType: application/json` probe |HTTP200, valid JSON matching local schema|36.03| JSON-mode request accepted; does not establish complete provider schema enforcement |

Because the strict probe failed, the cohort explicitly used JSON MIME mode plus a **single fixed appendix containing the unchanged application schema**, with complete local validation. The original system instructions remain intact before that declared transport appendix, and every non-system message is exact. This provider-specific difference was frozen before cohort inference; it is not an exact full-system-prompt match to Gemini's server-enforced schema path. No application schema or obligation was weakened, no malformed output repaired, and no prompt tuned after failures.

Provider-enforced schema support remains unresolved. Valid JSON, full local application-schema validity, provider enforcement and technical correctness are scored separately.

## Original six historical cases — minimal thinking

All six were attempted once, sequentially, temperature0, `thinkingLevel:minimal`, output allowance2048 and120-second inference deadline. No500/503 retry loop was used.

| ID | Condition | Gemma result | API seconds | Complete-task assessment |
|---|---|---|---:|---|
| H01 | Route present/down egress/failed trace |HTTP500 INTERNAL|9.44| No answer; reasoning not assessable |
| H02 | Planned device/port ownership |HTTP500 INTERNAL|0.95| No answer; relationship reasoning not assessable |
| H03 | Saved config plus unavailable syslog |HTTP503 high demand|23.44| No answer; multi-outcome reasoning not assessable |
| H04 | Published OSPF requirements versus saved CLI |HTTP200, valid application JSON|75.01| **Partial**, correct mapping but incomplete limitations |
| H05 | Interface states plus failed-hop explanation |HTTP500 INTERNAL|1.41| No answer; causal reasoning not assessable |
| H06 | Contextual next-check recommendations |HTTP500 INTERNAL|1.03| No answer; advisory quality not assessable |

H04 correctly maps `interfaces[].name/area`, process20, router ID198.19.213.1 and GigabitEthernet0/1 area0. It correctly explains vendor-conditional process_id and cites publishedS1 versus savedS2. It does not generate configuration. However, it omits the original expected limitations concerning **current deployment and full parameter/compatibility validation**. Stating vendor/version uncertainty alone does not fulfill the whole requested explanation. This is incomplete model-written interpretation, not fabricated network facts.

Historical delivered adequacy is therefore **0/6**, with **only1/6 completed answers available for semantic review**. Five provider failures must not be called five instances of incorrect completed reasoning. Gemini's preserved6/6 qualified adequate results and Qwen's preserved0/6 results remain unchanged.

## New holdouts and high-thinking checks

| ID | New frozen condition | Minimal-mode outcome | API seconds |
|---|---|---|---:|
| N01 | Multihop oper-down despite admin-up and installed route |HTTP503 high demand|41.46|
| N02 | Saved/current comparison plus missing logs and unexecuted next check |HTTP503 high demand|39.20|
| N03 | Actual existing IntentPlan compound source selection |HTTP500 INTERNAL|1.14|
| N04 | Contextual stale/current-unknown advisory |Timeout|120.01|

All four new conditions lack completed answers. These are **0/4 delivered tasks and0/4 assessable semantic responses**, not evidence of four reasoning errors. No post-output prompt changes or additional holdout substitutions were made.

Exactly two separately labelled high-thinking reruns were frozen and executed, with unchanged original packets/schemas and an8192-token allowance because thinking shares the output budget:

| Historical rerun | High-mode outcome | API seconds | Assessment |
|---|---|---:|---|
| H01 |HTTP500 INTERNAL|1.15| No causal answer; thinking benefit not assessable |
| H04 |HTTP200, valid application JSON|50.95| Same missing deployment/full-validation limitations; partial |

High H04 reports1545 input,214 final-answer and881 thinking tokens. Minimal H04 reports1545 input and235 final-answer tokens. Generated thinking receives **no correctness credit**. Neither mode was token-truncated. The single high sample finishing faster does not establish that thinking improves latency; service timing and output allowance differ. No improvement in complete-task adequacy was observed. Original minimal failures remain intact.

## Three-model comparison

| Measure | Qwen2.5 1.5B — preserved | Gemini3.8 Flash — preserved | Gemma4 31B — this run |
|---|---|---|---|
| H01–H06 complete-task adequacy |0/6|6/6, three scope qualifications|0/6 delivered; only1/6 completed for review |
| Causal interpretation | Existing completed errors retained | Correct interpretation on H01/H05; calculated evidence already states failures | No completed causal answer; not assessable |
| Source relationships | Existing owner/port errors retained | H02 endpoint pairs and H04 mapping correct | H04 S1/S2 and values correct; topology case unavailable |
| Unsupported facts | Existing failures in original reviews | Scope qualifications retained; not universally verified | No detected unsupported fact in the two limited H04 answers; omissions remain |
| Structured output | JSON validity did not establish quality |6/6 selected direct answers schema-valid | Two H04 answers schema-valid locally; provider enforcement unresolved; N03 planning unavailable |
| Latency | Five paired isolated replay records10.39–23.49s; sixth came from earlier gateway stage | Six direct answers4.29–31.04s | Completed H04 answers75.01/50.95s; one120.01s timeout |
| Reliability | Historical complete answers could still be wrong |6/6 direct completions; separate earlier gateway cloud synthesis4/7 completions | Unique1/10 conditions returned an answer; repeats do not increase unique coverage |
| Quota suitability | Local resource limits |20RPD as user-reported; not newly verified |30RPM/16KinputTPM/14400RPD as user-observed; usable availability not demonstrated |

These are exposed historical inputs, different service windows, different endpoints/schema transports and different thinking controls. Qwen used512 output tokens; Gemini2048; Gemma minimal2048/high8192. The historical Qwen errors normally stopped below512, but that does not eliminate every experimental confound. No larger-parameter-count or higher-quota intelligence claim is justified.

## Quota, latency and usage

There were **15 real generation attempts plus one model-metadata GET**: three probes, ten minimal cases and two high reruns. Generation outcomes including probes: **4HTTP200,7HTTP500,3HTTP503 and1timeout**. No actual429, authentication denial or billing restriction was observed. Real503 messages explicitly report high demand;500 messages are generic internal errors. Those are not evidence that the16K input allowance was exhausted.

The sequential quota ledger records actual reported input usage; failed/unknown usage retains a conservative serialized-body-character reservation. The highest observed rolling reservation was **14,962 tokens**, below16,000; peak generation starts in61seconds were3, below30RPM. The account's other clients and project-wide usage are not observable with this credential and are not claimed as known. Failed-request input usage remains unknown. No quota stress test or14,400/day throughput validation was performed.

Known successful usage: **3,178 input,471 final-answer and881 thinking tokens**,4,530 total. Failed requests expose no usage receipt, so this is not total actual processing. [Published Gemma pricing](https://ai.google.dev/gemini-api/docs/pricing) lists free input/output tokens; no billing activation, purchase or invoice query occurred. The user's observed free-tier quota is not independently certified by those price listings.

Each experimental inference, including any permitted429 retry/backoff, was capped at120seconds. Initial quota pacing occurred before dispatch and is reported separately. The slowest full case including that pacing was the120.01second timeout (approximately13ms cleanup overhead); H04 minimal was111.57seconds including36.56seconds pacing, and high110.75seconds including59.80seconds pacing. **These are standalone API/evaluator measurements, not full shared-gateway end-to-end latency.** No model-provider timeout is classified as semantic-verification failure.

## Integration feasibility without switching

The successful H04 drafts parse through the **current PublishedAnswerDraft Pydantic model** and pass the existing limited published-field checker with the actual sourceS2 text. Read-only replay: `existing-verifier-readonly-feasibility.json`. Both still fail full-task review. This demonstrates compatibility of those two shapes and the limits of literal checking, not full assistant acceptance or a guarantee of semantic completeness. Actual IntentPlan feasibility remains unverified because N03 returned500.

A future authorized integration would require only these focused changes, **none implemented now**:

1. Add a generateContent transport branch in the existing provider domain, mapping original messages, `systemInstruction`, JSON response mode, thinking controls and `usageMetadata` correctly. Merely changing the current Interactions model string is not the tested path.
2. Pass the existing approved-request remaining deadline and shared remote-call budget; retain exact owner/surface/request/history approval and synthetic-source/privacy restrictions. Use existing authorization and source readers; no new planner.
3. Validate every output against unchanged IntentPlan/AnswerDraft contracts. Until provider schema enforcement is verified, treat schema-shaped JSON as instruction following plus local validation. No implicit field repair or relaxed contract.
4. Preserve source IDs and current V9/Monaco/review authority. Keep provider failures distinct from unsupported model conclusions; do not release partial generation or fabricate a diagnosis.
5. Apply bounded project/model request pacing if admitted, then test the actual authenticated gateway and independent complete-task cases before considering replacement. Current15 calls do not validate project-scale quota behavior.

The material blocker is provider reliability, followed by insufficient completed semantic samples and unverified planning/schema enforcement. No application redesign, additional model, task-decomposition system or narrow phrase validator is warranted from this run.

## Evaluator checks, preservation and artifacts

Only one standalone evaluator and sanitized evaluation documents were added. `backend/scripts/evaluate_phase_g_gemma4.py` requires explicit `--probe` or `--run`; it has no route into ordinary gateway activation. Five offline check groups verify exact message/schema preservation, quota admission, bounded429 recovery/redaction/thought separation, schema/truncation rejection and final retry-status reporting. An offline review found stale429 status could survive a later successful retry; the evaluator metadata was corrected and tested. No real429 occurred, and no real case result was changed. The original offline log remains. CLI no-argument refusal and syntax checks also pass. These harness tests are not model-intelligence evidence, and unrelated application suites were not rerun.

Final preservation passes: **171 protected source/config files unchanged**, including the current Gemini provider, model adapter, gateway, frontend and both `.env` files;64 previous audit files unchanged; ordinary SQLite tables/integrity unchanged; HEAD93f5f45/index unchanged; active release `7a14a351e52b49aeb87f65d1192f0937` and all341 artifacts unchanged. Qwen2.5 remains explicit, Qwen3.5 remains installed, hybrid and Approach A remain0. No browser/editor operation, service restart, credential copy, commit, staging, knowledge publication, device execution or billing activation occurred.

Primary artifacts under `tmp/phase-g/iterations/20261025-gemma4-31b/`:

- `model-access.json`, `connectivity.json`, `strict-schema-probe.json`, `json-mime-probe.json`: real API access and structure tests.
- `manifest.json`, `transport-profile.json`, `high-profile.json`, `packets/`: pre-inference expectations, settings and immutable input hashes.
- `minimal/H01.json` … `minimal/N04.json`, `high/H01.json`, `high/H04.json`: raw request bodies, responses, usage, timing and failures; credentials excluded.
- `quota-events.jsonl`, `minimal.log`, `high.log`: pacing and exact execution sequence.
- `full-answer-review.json`, `existing-verifier-readonly-feasibility.json`: separate model, contract and task grades.
- `offline-evaluator-checks.json`, `offline-retry-final-status-correction.json`: mocked harness checks, no model credit.
- `preservation-before.json`, `preservation-after.json`: state protection evidence.

Curated machine report: `docs/evaluations/phase_g_gemma4_31b_result.json`.

**Keep the current Gemini experimental provider unchanged and disabled.** Gemma may merit a later availability retest if separately authorized, but this run does not justify replacement or experimental integration. The underlying broad reasoning capability remains largely unmeasured. Stop here and await authorization.
