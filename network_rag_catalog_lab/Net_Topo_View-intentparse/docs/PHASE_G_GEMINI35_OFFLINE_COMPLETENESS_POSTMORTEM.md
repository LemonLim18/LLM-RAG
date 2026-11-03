# Gemini 3.5 offline answer-completeness postmortem

**Executive finding: the investigated omissions and temporal overstatement first occur in Gemini's returned text, despite preserved source operands and original instructions. No new deterministic application defect is demonstrated.** The existing release boundary preserves those answers under an explicitly unverified label; it neither completes missing prose from auxiliary claims nor certifies unrestricted deductions.

**One recommended next action: No justified code change yet.** Existing frozen inputs, raw outputs, component-level grading and release traces are sufficient to locate these failures. No repair, prompt/schema experiment, additional ledger, model comparison or activation is implemented or launched.

Investigation date: 2026-11-02. Scope: read-only examination of saved artifacts, plus in-memory deterministic parsing/checker/release replay. The only new project file is this requested report. No continuation or historical report is rewritten.

## A. Experimental facts and scope

| Saved result | Reconciled finding |
|---|---|
| Dispatch attempts | Exactly 12 entries, one per frozen case/arm; no retry |
| Provider completion | 12 HTTP 200 responses, all `finishReason: STOP` |
| Valid structured cores | 11; H-06 control contains invalid JSON |
| Whole-response adequacy | Control 4/6; candidate 2/6, preserving frozen grading |
| Adequate raw prose | Control 5/6 including one diagnostic string from invalid JSON; candidate 2/6 |
| Adequate prose in valid cores / adequate released answers | Control 4/6; candidate 2/6 |
| Record-clock equality | Control 18/18; candidate 22/22, independently rechecked against saved source records |
| Current candidate status | OFF; reasoning-contract and interpretation candidates also remain OFF |

The claim denominators differ. 18/18 versus 22/22 is not an improvement rate, proof of complete binding validity, or a causal comparison of reasoning. Incorrect identifier types and unsupported claim categories are separate diagnostics. The malformed H-06 control has no parsed complete object, executed claim review or released answer. Its recoverable answer string does not become a successful response.

The registry SHA256 remains `d8dbe4f0d70c5dce1d5ec182b71b216b87cc066b9003f5ff18330d6f941a62a4`. Every saved model-message/schema pair matches its frozen pair; every recorded provider body matches the frozen serialized body and its hash. All original questions match fixture questions and pair inputs. Every packet's `reader_results` equals the authorized frozen operands, with `omissions: []`, available sources and `truncated: false`. Packets range from 5,184 to 13,278 characters, below 64,000. Valid answer fields range from 625 to 1,383 characters, below their 12,000-character allowance.

These are **fixed-evidence reasoner-role comparisons**, not live planner/reader/gateway journeys. Their `planning_proposal_not_authority` is `{}` and their recorded planner/registered-reader counts are zero. The actual handoff is fixture request/results → frozen `pair.inputs` → saved reasoner messages → provider wire. No Gemini 3.1 execution, fresh source query or end-to-end browser result is invented to fill that boundary.

Primary evidence: [frozen registry][registry], [live report][live-report], [full grading][grading], [dispatch ledger][dispatch], [freeze manifest][byte-freeze] and the per-cell files linked below. Their original scores and bytes are unchanged. One stochastic generation per arm cannot establish that the annotation caused every paired difference.

## B. Evidence trace and first divergence

| Case | Evidence present? | Request preserved? | Raw model failure? | Release defect? | Proven cause |
|---|---|---|---|---|---|
| H-01 candidate | Yes: event message and configuration both contain MTU 1500 | Exact restoration question and both original clauses reach the wire | Answer omits 1500; claims and assessment include it | No text deletion; omission survives unchanged | Model answer-field omission with adequate operands; not source loss |
| H-02 candidate | Yes: separate first-observed and record timestamps for both owners | Exact observation/order/causality questions retained | Correct arithmetic followed by “actually occurred earlier” | No downstream insertion; semantic overstatement is not detected | Raw temporal scope overstatement under strict reading; wording ambiguity retained |
| H-04 candidate | Yes: two conflicting 06:40 captures and later 07:10 shutdown | Question explicitly asks what each observation establishes | Answer mentions a later state without naming shutdown; third claim names it | No deletion of a correct raw sentence | Model omission of a definite later observation |
| H-05 both | Yes: routes, up ports, modeled forward unknown and return delivered, source limitations | Exact modeled-path and two-passive-artifact requests retained | Both omit the frozen rubric's explicit model-versus-measured-response caveat | No correct caveat removed | Model scope-qualification omission against the frozen rubric; not a lost literal subquestion |
| H-06 control | Yes; otherwise equivalent frozen inputs | Exact question reaches the provider | Returned JSON contains unquoted `-timestamp:` | Parser rejects correctly; no final answer exists | Invalid completed provider/model output; no extraction or truncation defect shown |

### H-01: MTU 1500 is available but absent from the answer

Trace: [H-01 candidate][h01-candidate], SHA256 `040b3ce62da1b65e324f723f1dabd13e6803de034a44919ab726cf978b913a2c`.

1. `/model_messages/1/content`, decoded as JSON, retains `original_user_instruction`: “Explain the verified MTU restoration on NacreDist Ethernet2/7.” It also retains the timing, delay and payload-recovery questions. The question does not literally say “quote the MTU value”; including the restored value is a frozen required component of explaining the restoration, not a new post-result criterion.
2. `/reader_results/0/data/records/0` is `h01-mtu-ack`: `message: Verified MTU restoration to 1500 on Ethernet2/7`, `effective_at: 2026-10-28T08:04:00Z`, record `timestamp: 2026-10-28T08:17:00Z`, `applied: true`, `verification_status: verified`.
3. `/reader_results/1/data/records/0` is `h01-followup`: `config_text: interface Ethernet2/7\n mtu 1500`, observed/captured at `2026-10-28T08:22:00Z`. Owners remain device 5101/interface 51017 throughout the input.
4. The packet, saved message and provider body preserve both operands exactly. There is no truncation, supplementary projection, omission list entry or planner rewrite.
5. The schema permits a coherent `answer` of 1–12,000 characters; it contains no rule excluding numeric configuration values. The actual answer is only 924 characters. Its opening says the restoration is documented, then gives the three times, correct 13/18-minute delays and a correct payload-recovery limitation, but never states 1500.
6. Raw `/claims/0/statement`, `/claims/1/statement` and `/outcome_assessments/0/assessment` explicitly contain 1500. This demonstrates access and representation in the returned object, not proof that the user-facing answer included it.
7. Both raw auxiliary claims use numeric IDs where string IDs are required. `parse_decision` reports `MODEL_CONTRACT_ERROR` for those declarations without discarding the core. It does not delete 1500 from the answer: that value was absent before parsing.
8. `/release_decision/unchanged_model_prose` is true, `withheld_spans` is empty and `semantic_certified` is false. Replaying composition exactly reproduces the incomplete released answer.

**Application-cause verdict: NOT PROVEN.** Automatically copying every auxiliary statement into prose would be a different composition policy, not correction of demonstrated text loss; historical outputs include false or inconsistent auxiliary statements. No such change is made.

### H-04: a later observation is represented in claims but not explained

Trace: [H-04 candidate][h04-candidate], SHA256 `1aacf163a15cbd4c62e4163627977132b4a07840fabb09e732641836ba02929a`.

The original question asks to reconcile both collectors “and the later capture” and “What is established at each observation”. One intact `request-1` contains all of that text; grouping it does not remove any requirement.

| Exact source ID | Record time | Exact configuration operand |
|---|---|---|
| `h04-observer-a` | `2026-10-28T06:40:00Z` | `interface Ethernet4/8\n no shutdown` |
| `h04-observer-b` | `2026-10-28T06:40:00Z` | `interface Ethernet4/8\n shutdown` |
| `h04-later` | `2026-10-28T07:10:00Z` | `interface Ethernet4/8\n shutdown` |

All three records retain MarshAccess/device 5211/interface 52118, collector identity and timestamps. The raw answer explains the conflict, leaves 06:55 and exact transition unknown, and denies measured-health proof. Its reference to “a later state at 07:10” does not say what that state was. `/claims/2/statement` does: “Synthetic-collector-a reports interface Ethernet4/8 is shutdown at 07:10.” The assessment similarly omits that affirmative later state while discussing uncertainty.

The schema imposes no prohibition on stating the later shutdown. All source bodies fit admission; the 625-character answer is not length-capped. Multiline CLI declarations are uncheckable by the exact-line configured-command operand check, not judged source-false. The current policy retains the full answer with a limitation notice; it does not remove the third claim from an already complete answer.

**First loss:** answer generation, not retrieval, input transformation or release. The candidate's repeated timestamp formatting is cosmetic and is not the grading basis. A coarse clause and a nonempty `limited` assessment are not semantic coverage certificates.

### H-05: preserve the distinction between user wording and rubric coverage

Traces: [H-05 control][h05-control] and [H-05 candidate][h05-candidate].

The exact original question is:

> LumenProbe has a complete route toward ArchiveSink and every supplied port record is up. Explain whether the modeled UDP 161 poll and reverse path are established, identifying the remaining evidence gap. Recommend two distinct passive artifacts to request next and explain what each could resolve. Do not execute new reads, collection or tests; use only the supplied state.

**Literal-request finding:** the user explicitly asks about *modeled* paths, the remaining gap, two passive artifacts and their purposes. It does **not** separately ask “Does modeled delivery establish measured application response?” The frozen oracle nevertheless explicitly requires that limitation. That safety/interpretive criterion is preserved as frozen, but failure against it is not evidence that orchestration dropped an explicit application-response clause. The prior report's “requested distinction” should be understood as a frozen grading requirement, not a verbatim user subquestion. No original grade or oracle is altered here.

Material evidence is present in `/reader_results/0/data/records`: `h05-poll-model` has `derived: true`, `assessment.forward.status: unknown`, reason `next-hop neighbor resolution unavailable`, and `assessment.return.status: delivered`. Both directions have `modeled_only: true`. The limitation is “Declared IPv4 stateless forwarding only; no NAT, IPv6, dynamic protocol emulation or physical packet test.” `evidence_type_boundaries.modeled` also says this is a declared calculation, not measured traffic or physical certification. No application response measurement is supplied.

The exact question survives into four original-text clauses, including separate recommendation and purpose clauses. Both raw answers explain the unresolved forward neighbor and modeled reverse result and propose two passive artifacts with purposes. Thus **neither H-05 arm omits passive advice**. Control offers ARP/neighbor records and counter logs or flow telemetry; candidate offers ARP/ND and counters. Aggregate counters alone cannot isolate this application flow; that usefulness limit and the unnecessary IPv6 ND alternative are already noted in the saved review.

Both answers use modeled framing but never explicitly say the delivered reverse model is not a measured application response. Both pass structural clause coverage, with `remaining_requirements: []`. Release retains the exact prose. The schema permits uncertainty and recommendations; `additional_reads.maxItems: 0` prevents execution proposals, not recommendations in the answer.

**Shared mechanism with RC-04:** a requested or rubric-required component can be absent from prose while IDs and assessments look complete. The mechanisms differ in severity: RC-04 later arms omit explicitly requested advice; H-05 supplies the advice and misses an explicit frozen scope caveat. It would be inaccurate to merge them into a repeated no-advice failure. If “modeled” is accepted as an implicit sufficient caveat, each arm gains one adequate case; this preserved sensitivity does not eliminate H-01/H-04 regressions or change KEEP OFF.

No schema/instruction or deterministic transformation is proven to compel the H-05 omission. Positive H-06 prose under the same general contract explicitly distinguishes a modeled consequence from a deployed outage, showing that this kind of qualification is permitted.

### H-02: observation order versus interruption onset

Trace: [H-02 candidate][h02-candidate], SHA256 `89242556e27df8f8aa229778c78e9f2a5dd5342cc26de9b797d1498b16bdc833`.

| Owner / source record | `first_observed` | Record `timestamp` | Reporting delay |
|---|---|---|---:|
| RavineWAN / `h02-ravine` | `2026-10-28T21:04:00Z` | `2026-10-28T21:19:00Z` | 15 minutes |
| PlateauWAN / `h02-plateau` | `2026-10-28T21:08:00Z` | `2026-10-28T21:10:00Z` | 2 minutes |

The exact question asks which site first observed the interruption, compares both time roles, and asks whether record order proves interruption order or causation. The candidate correctly reports all times, delays and reversed record-writing order. It then says:

> …does not establish the chronological order of the interruptions—which actually occurred earlier at RavineWAN—nor does it prove that one caused the other.

Read literally, “actually occurred earlier” asserts onset order. Earlier detection at one site does not establish which actual interruption began first at two sites. No `occurred_at`, coverage interval or synchronized onset measurement establishes that order. The statement also sits awkwardly beside its own denial that record order establishes chronology.

**Grading ambiguity retained:** this could be informal shorthand for “was first observed earlier”, given its accurate preceding sentences. The conservative frozen judgment treats it as an unsupported onset assertion. The permissive reading raises candidate adequacy from 2/6 to 3/6; it still leaves the clear H-01/H-04 regressions. The answer does not claim one site caused the other.

The overstatement is already in raw `/answer`; it is not in the source data or added during release. Auxiliary assessments use first-observed order. Numeric device IDs invalidate the four auxiliary declarations, leaving no valid typed claims for this cell; that produces a notice, not a corrected chronology. A valid timestamp scalar would still not prove the meaning of “occurred”. The released text remains explicitly unverified.

### H-06: malformed JSON is a separate completed-output failure

Trace: [H-06 control][h06-control], SHA256 `cf4d3894af05c739f6b5efc52a3d733ebe04782d3f5c7352463a4aa63a0cadf3`.

- Google returned HTTP 200, one text part, `finishReason: STOP`; reported output is 829 tokens against `maxOutputTokens: 8192`. A capped or unfinished generation is not evidenced.
- That single saved provider text, extracted using the current provider's non-thought-part concatenation and `.strip()`, exactly equals saved `raw`.
- It contains `-timestamp: "2026-10-28T18:00:00Z",` with an unquoted key. `json.loads` deterministically fails at line 29, column 7, character 2236: `Expecting property name enclosed in double quotes`.
- The object continues past the bad key and ends with its remaining claim and closing braces. There is no evidence of local truncation or content-part loss.
- The wire requests `responseMimeType: application/json` and supplies the full application schema as the existing system-instruction part. It uses the working validated-JSON transport, not a native `responseJsonSchema` guarantee. No HTTP request-contract rejection occurred; the same contract yielded 11 valid cores.
- `gemini_provider.interpret_rest` correctly raises local 502 / `INVALID_STRUCTURED_OUTPUT`; Google HTTP status remains 200. This is not a provider 502/503, quota failure or semantic contradiction finding.
- No repair/retry occurred and no final answer exists. Diagnostic extraction of the already well-formed answer string is only a prose-quality observation.

**Proven cause:** invalid JSON in completed returned provider/model content. A local parser/extraction defect is not shown. The provider's internal generation/serialization process is not observable, so no claim about hidden model internals is made.

## C. Existing contract and cross-experiment recurrence

### Code-backed answer contract

| Requirement | Current instruction / enforcement | Actual limitation |
|---|---|---|
| All explicit outcomes | `decide()` says “Fulfil every original requested outcome” and answer each outcome, significance and limitations | `OutcomeAssessment` ID/cardinality checks establish identifier coverage, not the presence of each semantic subanswer |
| Definite source facts | Ownership, source, time and original instruction remain authoritative; no blanket-uncertainty requirement | No guarantee every material supplied scalar is repeated in prose; H-01/H-04 show this gap |
| Time semantics | Source-scope/time instructions; optional timestamp description distinguishes record selector from event/observation/effective time | A correct selector does not validate first-observed-to-onset inference; older temporal-instruction candidate is OFF |
| Modeled versus measured | Instructions forbid physical observations from simulated records; typed `scope` separates authority; input boundaries label calculations | No exhaustive semantic comparison of every prose sentence with that scope |
| Prose/auxiliary consistency | All fields are expected to be source-grounded; instructions label self-assessments as proposals | The schema has separate free-text answer, statement and assessment fields with no semantic cross-field invariant |
| Structured validity | Core JSON/schema strict; auxiliary claims independently diagnosed | Invalid JSON remains unrecoverable; valid core prose is not discarded solely for invalid optional IDs |

Exact boundaries: [`response_obligations`][request-code] preserves unsplit text rather than dropping it; [`evidence_packet`][packet-code] retains original request/reader operands and fails closed above 64K; [`decide` instructions and schema][decide-code] and [assessment/source checks][assessment-code] enforce structural contracts; [`parse_decision`][parse-code] separates valid core from auxiliary errors. [`compatible_claims`][claims-code] checks declared operands, [`release_interpretation`][release-code] withholds proven contradictions or adds notices, and [`preview`][preview-code] adds the unverified label. [Graph composition][engine-code] reuses these boundaries. The live runner [replays this specific release subset][runner-code]; it does not execute the full graph's source-coverage/post-draft machinery.

The schema's `answer` minimum length is 1, not semantic completion. `remaining_requirements: []`, nonempty assessments and all valid clause IDs coexist with H-01/H-04 omissions. This is a known verification limitation, not a new false certificate: traces explicitly set `semantic_certified: false` and describe assessments as model proposals.

### Compact recurrence matrix

Classes: **A** proven deterministic application defect; **B** model-generated reasoning/fulfilment failure with adequate input; **C** limited semantic checking/release; **D** unresolved attribution, missing evidence or generation variability. A historical resolved defect is not a current repair opportunity.

| Failure class | Original reasoning-contract 18 outputs | Later temporal-instruction 12 outputs | New timestamp 12 outputs | Classification |
|---|---|---|---|---|
| Unsupported snapshot continuity | RC-02 control infers 08:00 from 07:00 plus absent changes; obligations outcome also overstates; relationship prose qualifies correctly | RC-02 control leaves 08:00 unknown; candidate repeats unsupported continuity despite explicit instruction | H-04 both retain unknown 06:55/transition; omission of later shutdown is a different issue | B + C; D for why generations differ |
| First-observed versus record time | RC-05 arms use 12:31 record time instead of 12:30 first-observed for chronology | Control repeats error; candidate prose separates times but auxiliary statement says occurred 12:31 | H-02 both preserve source clocks; candidate overstates onset order in prose | B + C; correct binding alone insufficient |
| Requested passive recommendations | RC-04 control gives qualified passive advice; other arms include advice or borderline path wording | Both RC-04 arms omit explicitly requested advice while saying supported | H-05 both provide two suggestions and purposes | B + C; not a universal no-read/schema prohibition |
| Incomplete despite available operands | RC-03 obligations gives broad device lists rather than requested owned ports; populated outcomes do not cure it | RC-04 omission survives release | H-01/H-04 correct scalar/state appears in auxiliary output but not prose | B + C |
| Correct prose versus wrong auxiliary claim | Extra output fields show disagreement in several original arms | RC-05 candidate prose correct, occurrence claim/assessment inconsistent | No materially false auxiliary assertion identified in the new review; H-01/H-04 show omission across fields instead | B + C; not new interface success |
| Malformed structured output | All 18 saved cores valid | All 12 saved cores valid | H-06 control has raw unquoted `-timestamp:`; correctly withheld | B for returned output; parser failure closed correctly |
| Wrong prose survives release | RC-02/RC-05 errors unverified, not certified | RC-02 candidate/RC-05 control errors and RC-04 omissions survive | H-02 strict overstatement and H-01/H-04/H-05 omissions survive | C, quality gap distinct from false verification |
| Historical false suppression | Effective-time lookup, successful-interface scope and fatal optional navigation caused earlier incorrect withholding | Prior checker repairs already recover valid prose | All 11 valid cores retain raw prose with unchanged checker/release results | A, already corrected; no newly reproduced defect |

The previous 18 and 12 outputs were located; all 30 parse locally. All 390 historical file/hash references in the existing inventory verify, with **no missing requested artifact**. Existing inventories preserve exact source packets, schemas, provider text, grading and current/historical releases. Their original scores remain separate: original raw 4/6, 2/6, 3/6; later raw 3/6 versus 4/6 but whole response 3/6 versus 3/6. They are reused exposed conditions, not independent new samples. Neither pooling them nor rescoring them is justified.

Positive evidence matters: the original RC-04 control gives advice under the same control messages/schema that later omitted it; H-03 both answers preserve ownership and midnight arithmetic; H-06 candidate preserves justified modeled policy consequences and real-world limits. These observations refute claims that the contract makes complete advice or positive scoped conclusions impossible. They do not identify attention, sampling, schema complexity or internal reasoning as the causal explanation for variability.

## D. Proven defects versus hypotheses and release boundary

| Suspected boundary | Exact input/output and deterministic reproduction | Verdict / smallest correction boundary |
|---|---|---|
| Request loss: `request_contract.response_obligations`, `role_reasoning.evidence_packet` | Compare fixture question → `pair.inputs.request` → decoded `model_messages[1].content.original_user_instruction` → provider body for all 12; equal. All source operands also equal. | Current defect NOT PROVEN; no correction boundary selected |
| Truncation/projection: `role_reasoning.evidence_packet` | Packets 5,184–13,278/64,000, `omissions: []`; raw records and exact CLI values retained; generation finish STOP | Evidence-loss contribution NOT PROVEN; leave transport intact |
| Scalar/state stripped from prose: `parse_decision`, `release_interpretation`, `preview` | Reparse saved raw; H-01 answer already lacks 1500, H-04 already lacks later shutdown. Replay all 11 checker/release results exactly; every original answer remains verbatim in final text. | Composition deletion NOT PROVEN; no renderer repair justified |
| Advice forbidden by schema: `decide` schema/instruction assembly | H-05 both and historical RC-04 control include advice while `additional_reads` is empty. Exact system expressly separates recommendation from execution. | Prohibition mechanism NOT PROVEN; do not relax read constraints |
| Self-assessment certifies completion: `decide`, `post_draft` | IDs/count valid despite omissions; saved trace explicitly says proposals, no semantic certification | C: structural coverage cannot certify meaning. No new incorrectly implemented semantic check is demonstrated |
| Onset misstatement inserted downstream: `release_interpretation` | H-02 exact unsupported wording is already in raw `/answer`; final contains it unchanged | B + C; no new statement inserted; no arbitrary prose verifier is proposed |
| JSON extraction/parser: `gemini_provider.interpret_rest` | Saved one-part provider text equals `raw`; `json.loads` fails on the same unquoted key at char 2236 | Parser/extraction defect NOT PROVEN; strict rejection preserved |
| Candidate annotation caused answer loss | One generation per arm; candidate differs only in description, but older identical-control inputs have both successful and failed generations | D: comparative outcome observed; mechanism/causal attribution not established |

All 11 valid current cells were replayed in memory using the current `parse_decision`, `compatible_claims`, `release_interpretation` and `preview`. Each checker result, release decision, final answer and release trace matches its saved counterpart exactly. Auxiliary error paths are compared after ordinary JSON serialization of tuple/list diagnostics; identifiers and claims are not repaired or coerced. The H-06 parser failure is reproduced separately. These are artifact-compatibility observations, not new inference successes or an expanded unit-test score.

During the successful replay, socket connection functions and `sqlite3.connect` were replaced in that child process with fail-closed guards: network attempts 0; database attempts 0. No planner, source reader or model-generation function ran. Separate preservation reads use SQLite read-only/query-only access. The historical 30-output inventory/hash verification is a file read, not another model cohort.

**Release assessment:** raw H-01/H-04 omissions are not false scalar statements; they need task-quality judgment, not contradiction removal. H-02's strict onset overstatement is not declared as a usable contradictory typed operand, and no checker certifies it. Invalid IDs and unsupported claim categories do receive diagnostics. H-06 invalid JSON is caught before release. No new error in H-01–H-06 is introduced by downstream prose composition, and no correct valid-core answer is suppressed. Unverified labeling remains honest but does not make inadequate or misleading prose satisfactory.

Do not interpret these findings as universal release safety. The exact-value/ownership/timestamp checks are worth retaining, but they cannot establish complete prose coverage, causal entailment or semantic consistency across separately generated fields. Relaxing them would not restore omitted content and could reintroduce historical false support. Adding populated outcome objects already failed as a completeness proxy in earlier experiments.

## E. Exactly one next engineering action

**3. No justified code change yet.**

The existing instrumentation already provides the original request, clause text, complete sent operands, wire schema/messages, raw answer/claims/assessments, frozen required components and exact release output. That is sufficient to identify each investigated omission and its earliest observed boundary. Additional coverage instrumentation is therefore not a prerequisite for diagnosing these cases. An empty `remaining_requirements` or populated ID is known to be insufficient, and the report does not mistake either for a semantic guarantee.

No transport, parser or composition transformation is shown to cause the failures. The returned model text is already incomplete, overstates the available temporal evidence, or is invalid JSON. A generic new instruction, schema description, all-claims concatenation or narrow phrase rule would change behavior without a demonstrated causal repair boundary; another prompt/schema experiment would not resolve this forensic uncertainty. Preserve the existing strict authorization and exact-source checks, current valid-prose retention, all original grades, and default-OFF experiments. This recommendation is recorded only; no follow-on action or experiment is implemented.

## F. Preservation and safe stop

Before the report write, an in-memory snapshot covered **2,669 existing tracked/untracked/protected files**, including all 110 frozen runtime modules, tests, historical artifacts and the prior checkpoint; **1,923 knowledge-release files**, **42 ordinary SQLite table fingerprints** and the ordinary DB file hash; both environment hashes; binary/logical Git index; quota ledger; and active release. No preservation snapshot or new diagnostic dataset is written to disk. Only this requested report is created.

Final comparison verifies all preexisting hashes and table fingerprints unchanged. HEAD remains `840031451e954809f2817adf78d800bc6548c2d4`; active release remains `7a14a351e52b49aeb87f65d1192f0937` with manifest `bdb1cad94c4275081ce9b9aaaa3bbfadd9b38a73b201f67277aa1d7be69694b5` and **341 active artifacts**. The shared quota ledger remains byte-identical at SHA256 `d3371be61a571505fafc6122f0a6de63344467137f8f2fda7bcf3b7b93bb8365`; no reservations, purges or provider calls occur. The inherited 27 missing temporary fixtures remain absent, not reconstructed.

Both environment files leave the reasoning-contract, interpretation and timestamp experiments unset/default OFF. No credential value is printed or copied. No source/test/schema/prompt/checker/oracle/DB/configuration changes, new conversations, source retrieval, services, browser/editor/Ollama operations, staging, commit, reset, publication, deployment or device actions occur. Unsaved buffers are untouched; no fresh browser readback is claimed. No G4/G5/G6/G11 acceptance or experimental promotion follows.

**Investigation complete. Zero new Gemini calls. Stop after this report.**


Additional historical sources: [offline failure diagnosis](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/docs/PHASE_G_GEMINI35_OFFLINE_FAILURE_DIAGNOSIS.md), [interpretation iteration](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/docs/PHASE_G_GEMINI35_INTERPRETATION_ITERATION.md), [timestamp-contract preparation](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/docs/PHASE_G_GEMINI35_TIMESTAMP_CONTRACT_EXPERIMENT.md), [30-output inventory](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261102T094917Z-gemini35-offline-failure-diagnosis/30-output-inventory.json), [cross-experiment classification](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261102T094917Z-gemini35-offline-failure-diagnosis/failure-classification-matrix.json), [prior checker repair summary](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/docs/evaluations/phase_g_release_checker_offline_repair_result.json), and the existing continuation checkpoint (unchanged).

[registry]: C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/docs/evaluations/phase_g_gemini35_timestamp_contract_v1.json
[live-report]: C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/docs/PHASE_G_GEMINI35_TIMESTAMP_CONTRACT_LIVE_RESULT.md
[grading]: C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261102T123607Z-timestamp-contract-live/full-answer-grading.json
[dispatch]: C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261102T123607Z-timestamp-contract-live/dispatch-ledger.jsonl
[byte-freeze]: C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261102T104614Z-timestamp-contract-experiment/exact-byte-freeze.json
[h01-candidate]: C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261102T123607Z-timestamp-contract-live/cells/H-01-candidate.json
[h02-candidate]: C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261102T123607Z-timestamp-contract-live/cells/H-02-candidate.json
[h04-candidate]: C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261102T123607Z-timestamp-contract-live/cells/H-04-candidate.json
[h05-control]: C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261102T123607Z-timestamp-contract-live/cells/H-05-control.json
[h05-candidate]: C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261102T123607Z-timestamp-contract-live/cells/H-05-candidate.json
[h06-control]: C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261102T123607Z-timestamp-contract-live/cells/H-06-control.json
[request-code]: C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/orchestration/request_contract.py:71
[packet-code]: C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/orchestration/role_reasoning.py:202
[decide-code]: C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/orchestration/role_reasoning.py:342
[assessment-code]: C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/orchestration/role_reasoning.py:407
[parse-code]: C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/orchestration/role_reasoning.py:67
[claims-code]: C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/orchestration/investigation_support.py:407
[release-code]: C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/orchestration/investigation_support.py:446
[preview-code]: C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/orchestration/role_reasoning.py:559
[engine-code]: C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/orchestration/engine.py:478
[runner-code]: C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/scripts/evaluate_timestamp_contract_live.py:137

