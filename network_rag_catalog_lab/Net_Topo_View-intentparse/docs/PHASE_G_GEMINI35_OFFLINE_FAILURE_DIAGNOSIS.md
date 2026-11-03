# Gemini 3.5 offline reasoning-failure diagnosis

**Decision: No application repair justified. No production behavior changed.** This offline investigation found reproducible completed model deduction/fulfilment errors, an underspecified temporal claim interface, and known limits of narrow release checks. It found no new current mechanical defect that meets the authorized repair gate. Gemini 3.5 Flash-Lite remains the required reasoner; no alternative model is proposed or evaluated.

Audit: `tmp/phase-g/iterations/20261102T094917Z-gemini35-offline-failure-diagnosis/`. All artifacts below are audit-only; no new model-visible evidence representation is introduced.

## Scope, historical cohorts and actual inventory

The original 18 reasoning-contract outputs and subsequent 12 temporal-instruction outputs are present, hash-verified and separately indexed. These are 30saved completions of 6 reused conditions, not30independent generalization cases. No source, oracle, input, provider output or original grade was rewritten.

| Historical cohort | Raw prose adequacy | Whole-response consistency | Status |
|---|---|---|---|
| Original18: control / obligations / relationships | 4/6;2/6;3/6 | Original structured-inconsistency flags retained; no new pooled score | Frozen |
| Subsequent12: control / candidate | 3/6;4/6 | Adequate consistent whole response3/6;3/6 | Frozen |

The original live release3/6,1/6,0/6and prior updated-verification replay4/6,2/6,3/6remain separate. Five correct explanations were recovered by the earlier repair; this task does not rediscover those fixes as new work. The later live result includes its frozen RC-01control sensitivity and RC-05candidate structured inconsistency; no fresh adequacy scoring is performed here.

Read these exact artifacts:

- [Thirty-output inventory](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261102T094917Z-gemini35-offline-failure-diagnosis/30-output-inventory.json): every original question, requested clause, exact system text, packet hash, admitted records/provenance, response-schema pointer, raw JSON, assessments/claims/outcomes, checker result, final reply and frozen grading pointer. Each file reference includes SHA256 and JSON pointer.
- [Complete failure matrix](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261102T094917Z-gemini35-offline-failure-diagnosis/failure-classification-matrix.json), with [readable matrix](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261102T094917Z-gemini35-offline-failure-diagnosis/failure-classification-matrix.md): all 30rows, including source availability, first divergence, missing requirement, unsupported inference, cross-field conflict, historical versus current checker behavior, classification, confidence and minimal action.
- [Priority boundary traces](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261102T094917Z-gemini35-offline-failure-diagnosis/priority-boundary-traces.json): all 15RC-02/04/05outputs traced independently through request, clauses, exact evidence, instructions/schema, raw prose/auxiliary fields, review and release.
- [Complete output inspection text](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261102T094917Z-gemini35-offline-failure-diagnosis/complete-output-review.txt): all 30 raw answers and their auxiliary assessments/claims, without regenerating them.
- [Current-release replay summary](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261102T094917Z-gemini35-offline-failure-diagnosis/current-release-replay-summary.json), with per-output `release-replays/` files.

Missing artifacts: **none of the requested30outputs**. All 30 model-message/schema pairs equal their actual frozen arm; admitted packets equal saved `decision.input_packet`; the preserved provider wire final content equals saved raw JSON. Each Google wire contains the actual evidence packet and system instruction plus the exact application schema instruction. Original provider completion isSTOP 30/30, not timeout or incomplete generation.

These cohorts are fixed-evidence reasoner experiments. They did not invoke Gemini 3.1 planning or replay complete authenticated gateway investigations. The request interpretation available here is the exact original question and server clause representation. No historical planner trace is fabricated. This diagnosis establishes what reached Gemini and what release did, not broad source-selection acceptance.

## Earliest failure summary

| Class | Required information in input? | Earliest demonstrated divergence | Current application contribution |
|---|---|---|---|
| RC-02snapshot continuity | Yes: all captures, verified effective event, original08:00question and point-observation boundary | Raw model inference; in obligation arm also an explicit wrong structured conclusion | Checker validates individual observations/effective fields, not interpolation in prose. No continuity instruction or source interval forces the error. |
| RC-04passive recommendation | Yes: original question and request-1explicitly request next passive evidence | Raw answer omission, followed by self-assessment that misses it | Grouped clause coverage is structural only. Zero additional_readsdoes not prohibit recommending evidence in answer. No deterministic contradiction or schema compulsion found. |
| RC-05time roles / inconsistent output | Yes: first_observed12:30, record timestamp12:31, CRCsample12:35 | Old answers first err in prose; latest candidate prose correct, first disagreement appears in auxiliary claim/assessment | Temporal claim selector is poorly documented; incident verifier has deliberately limited fields. Unsupported claims remain unverified, not certified; release is not a prose-consistency verifier. |

## RC-02 — point observations do not establish continuity

### Exact source and request boundary

Request: “Explain CedarEdge logging-buffer chronology from all captures and the verified change event. Can you infer the value at08:00 or the exact later reversion time? State what the08:25application establishes and what remains unknown. Use configuration and syslog only.”

Example exact trace: `tmp/phase-g/iterations/20261102-gemini35-interpretation/live-results/RC-02-candidate.json`.

Inside its decoded `model_messages/1/content` (also `decision/input_packet`):

| JSON pointer | Actual source fact |
|---|---|
| `/reader_results/0/data/records/0` | `rc2-2`, running capture11:00, `logging buffered12000` |
| `/reader_results/0/data/records/1` | `rc2-1`, running capture09:00, `logging buffered24000` |
| `/reader_results/0/data/records/2` | `rc2-0`, running capture07:00, `logging buffered12000` |
| `/reader_results/1/data/records/0` | `rc2-applied`, `applied:true`, `verification_status:verified`, `effective_at:08:25`, record `timestamp:08:26` |

The actual command strings contain a space before their numeric values; the compact table above is descriptive, not a replacement operand. Exact literals remain in the inventory. Original raw record order is11:00,09:00,07:00, then separate event reader; every answer under review sorts those captures correctly. Reverse source order is not demonstrated to cause the unsupported intermediate-state inference.

The default request clause groups the whole question into request-1but does not remove any text. The earlier obligation/relationship arms retain more explicit original spans. No source states a continuous observation interval. The model-visible `evidence_type_boundaries.current` explicitly says **“Current capture at its recorded time/context; not continuous observation.”** The historical boundary similarly requires its own transition evidence. The system instruction warns artifact differences do not establish exact activation times. The candidate adds an explicit no-interpolation instruction; it still fails in the later run.

The navigation index labels all `kind=running_configuration` as `current`, including historical point captures whose raw `current` isfalse. That label is semantically coarse, but its adjacent current boundary means current **at the capture time**, and raw timestamps/flags remain present. It does not encode a continuous interval or08:00value. This is potential presentation ambiguity, not proof of an incorrect computed state. No index, record ordering, temporal metadata or transport change is justified here.

### Saved outputs differ; no regeneration

- Original control `.../20261102-evidence-reasoning-contract/live-results/RC-02-off.json`, decoded raw `/answer`: **“Based on the 07:00 configuration and the absence of recorded changes prior to 08:25, we can infer that the value at 08:00 was 12000.”** The trace contains normal spaces; the exact sentence is retained in the raw inventory. First unsupported step is treating absence of records as continuity. The assessment repeats it. Declared claims cover07:00/09:00/11:00and the real effective event; none actually declares the08:00interpolation.
- Original obligations arm `/raw(decoded)/outcomes/1/conclusion`: **“The buffer value at 08:00 can be inferred as 12000, but the exact later reversion time is not recorded in syslog.”** with `status:established`; the answer hedges “cannot be directly observed.” Historical PARTIAL_AMBIGUOUS remains unchanged. Additional structured fields did not eliminate the bad deduction.
- Original relationships arm explicitly says discrete captures do not permit08:00or exact-reversion inference. Its correct prose was historically suppressed for invalid optional relationship navigation; the completed checker repair retains it now.
- Subsequent control correctly says **“We cannot precisely infer the exact value at 08:00 from the configuration captures alone”**. Same default instruction/schema/evidence as the original control, different completed answer. Its coarse reversion interval is noted in the original grading, not newly rescored.
- Subsequent candidate says **“We can infer that at 08:00:00Z the buffer remained at 12000 (matching the 07:00 configuration state, as no change events are recorded prior to 08:25).”** The wrong inference appears despite the explicit anti-continuity paragraph. Its auxiliary timestamp selector also uses08:25instead of the record's08:26; current checker reports that binding uncheckable.

**Conclusion:** the first semantic failure is in model-generated deduction. Inputs support uncertainty and a definite positive08:25application; neither the schema nor an application calculation forces an exact08:00answer. Internal attention, evidence ordering and instruction salience remain hypotheses. The sources establish an effective event, not continuous state before or after it. No new source read is warranted to reinterpret the facts already present.

### Current effective-time checker

[Source scope and field selection](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/orchestration/investigation_support.py:256) first bind an optional `timestamp` to the record timestamp, then select the declared value field. For a valid `configuration_change_time` claim, verified/applied `field=effective_at` returns08:25while record binding remains08:26. The historical timestamp-substitution defect is already fixed. A wrong effective value is a contradiction; an08:25selector against08:26record is **NOT_MECHANICALLY_CHECKABLE**, not a false claim of contradiction. The valid positive event remains supported. Broad prose interpolation is outside this typed check.

## RC-04 — advice is different from execution

Request: “CedarEdge has a route toward IrisExit. Does that prove service on TCP8443in violet is working in both directions? Explain the routing fact, modeled uncertainty and most useful passive evidence to request next. Read state only and do not collect or test anything.”

Exact trace: `tmp/phase-g/iterations/20261102-gemini35-interpretation/live-results/RC-04-control.json` and `RC-04-candidate.json`.

- `/decision/input_packet/requested_clauses/0/text` preserves **“most useful passive evidence to request next”**. Request-2retains the no-collection restriction. [Existing clause splitting](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/orchestration/request_contract.py:71) groups coordinated noun-phrase outcomes; it does not strip the advice text.
- `/reader_results/0/data/records/0` contains the modeled flow with forward/return`unknown`; records1/2contain the endpoint routes; records3–6have actual admin/oper`unknown`. This supports a qualified explanation and useful advice; it does not establish a delivered or failed service.
- The exact system message separately says **“An advisory request asks for recommendations, not execution; use answer with no additional_reads.”** It also says never request active collection/tests. There is a potential natural-language tension around “request” and data collection, but passive advice is expressly distinguished. No demonstrated instruction says to omit a recommendation.
- Frozen schema permits arbitrary coherent answer text up to12,000 characters and `supported|limited|unresolved` assessments. It fixes `decision=answer` and `additional_reads.maxItems=0` because this experiment forbids new retrieval. That constrains **execution proposals**, not advice in answer prose. The schema does not require a known interface state or forbid qualified next checks.
- The source-policy block lists allowed`state`and all readers denied by “do not collect or test anything”; `supplementary_permitted:false` is explicit. These are restrictions on new query execution. Existing supplied records remain available. `advisory_only:false` reflects a mixed explain-plus-advice request, not prohibition of advice. It is not necessary or authorized to change the source policy to diagnose this omission.
- Both later raw replies explain routing/unknown operational status, then stop with “no additional tests are executed” / “no active tests or collection were performed.” **Neither gives the requested passive recommendation.** Their assessments mark request-1supported without noticing its missing suboutcome. Provider STOP confirms a completed answer, not truncation; no timeout occurred.

Earlier control `.../20261102-evidence-reasoning-contract/live-results/RC-04-off.json` under the identical control messages/schema does give advice: **“the most useful next step is to examine passive interface or telemetry state if permitted”**. The old obligations and relationships answers also give passive suggestions. These positive examples refute a claim that the schema makes advice impossible. They do not isolate why later generations omit it.

[Assessment validation](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/orchestration/role_reasoning.py:336) enforces one valid ID per original clause, not complete semantic coverage of every noun phrase. [Post-draft review](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/orchestration/investigation_support.py:475) checks source coverage/dependencies and declared claims, labels self-assessments as proposals, and expressly provides no semantic completeness certificate. It cannot mechanically infer that “supported” is wrong because advice is missing. These experiments ran the reasoner/claim/release path, not that full post-draft graph; no invented full-gateway success or failure is attributed to it.

**Conclusion:** observed model fulfilment error plus a known completeness-check limitation. Coarse segmentation and broad “never request active collection” wording may increase difficulty, but neither is proven to cause the omission. There is no request-text loss or response-schema constraint to repair. No new ledger, checklist, source read, phrase guard or prompt paragraph is added.

## RC-05 — correct prose can disagree with auxiliary output

Exact latest candidate trace: `tmp/phase-g/iterations/20261102-gemini35-interpretation/live-results/RC-05-candidate.json` (SHA256`db5137b6ad4af6fd0f86f38d27c5088538ff4c9a91bf8fa107a082013c33a246`).

Inside the exact packet:

| Pointer | Meaning |
|---|---|
| `/reader_results/1/data/records/0/first_observed` | Warning first observed12:30 |
| `/reader_results/1/data/records/0/timestamp` | Incident record timestamp12:31 |
| `/reader_results/0/data/records/0/timestamp` | CRC sample12:35;18errors in a60second sample |
| `/reader_results/2/data/source_available` | Syslog explicitlyfalse; empty records are not proof of no reset |

The first-observed-to-sample difference is five minutes; record-to-sample is four. Neither establishes the onset time of the CRC problem, an error trend, or a causal relation. The first-observed value is present in the actual source record in every arm, even though generic navigation timestamp entries emphasize12:31. That salience hypothesis is not an isolated presentation-effect finding.

The earlier 18 outputs for this case and the later control use12:31as occurrence and a four-minute lead. Each first goes wrong in raw temporal interpretation, before any checker or composition. Cooling-as-established-cause and no-reset-from-missing-syslog are not asserted; those valid limitations must be preserved alongside the wrong chronology.

The latest candidate has a different boundary:

1. Raw JSON `/answer`: **“first observed at 2026-11-02T12:30:00Z, incident timestamp 2026-11-02T12:31:00Z”** and sample12:35. Prose correctly separates the times and withholds causation/reset conclusions.
2. Raw JSON `/claims/0/statement`: **“Cabinet cooling warning incident occurred on CedarEdge at 2026-11-02T12:31:00Z.”** It declares `field:timestamp`, `value:12:31`, record binding12:31. That statement changes record-writing time into occurrence despite the correct prose.
3. `/outcome_assessments/0/assessment`: **“The cooling warning occurred at 2026-11-02T12:30:00Z / 12:31:00Z”** conflates the roles. A nonempty `supported` assessment does not resolve the disagreement.
4. `/typed_review/claim_compatibility/claims/0`: `status:INSUFFICIENT_SUPPORT`, `verdict:INSUFFICIENT_EVIDENCE`, `actual_values:[]`. It is **not SUPPORTED**, not a contradiction finding and not a semantic verification certificate.
5. `/final_answer` retains correct answer prose, adds an unverified/verification-limits notice and does not insert the wrong auxiliary sentence. The raw claim and assessment remain inspectable in audit data, without authority. No incorrect verified classification or new prose suppression is demonstrated here.

### Existing schema and checker design

[SourceClaim](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/orchestration/role_reasoning.py:30) independently asks for a free-text statement, category, source IDs, record-scope timestamp, field and scalar value. [OutcomeAssessment](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/orchestration/role_reasoning.py:23) separately asks for an assessment; the free answer is yet another generated field. The older contract adds outcomes as a fourth place, but is OFF. There is **no schema invariant tying the semantic content of those strings together**. Repeated output locations and the observed disagreement are demonstrated. The hypothesis that duplication causes the reasoning error is not established; the original control also misinterprets timestamps without the additional outcomes layer.

The source selector `timestamp` has no descriptive text in the actual schema—only nullable string/maxLength80. The implementation requires it to match record timestamp before evaluating `field/value`, but “bind...time” in the instruction does not fully explain this distinction. That is a confirmed **underspecified interface**, not a demonstrated need to alter current matching: accepting arbitrary event time as record identity could admit wrong bindings. Current08:25/08:26uncheckability follows the actual existing implementation. A future description-only clarification is the smallest bounded design item; it would change model-facing instructions and cannot be called an offline-proven reasoning repair.

[The incident checker](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/orchestration/investigation_support.py:379) accepts exact`message` or verified-event presence for its documented limited operands; it does not mechanically evaluate an arbitrary occurrence-time statement using`summary`, `timestamp` or`first_observed`. The CRC declaration is also miscategorized as`interface_oper_status` with`field:crc_errors`, outside that category's explicit field allowlist. Both return insufficient support; this does not mean the records are absent or the actual18error scalar is false.

Adding a scalar check for “timestamp equals12:31” would still not establish that the word **occurred** is justified. It could incorrectly bless an interpretation merely because it copied a field. Conversely, declaring the whole correct answer false because optional claims are malformed would reintroduce repaired false suppression. The current limited/non-certifying classification is correct within its scope. Its inability to resolve free prose semantics is a release-policy limitation, not a newly reproducible mechanical bug.

**Conclusion:** completed Gemini cross-field inconsistency; an ambiguous existing temporal selector contract; deliberately limited verification and release. No application function is proven to have converted a correct event fact into the wrong time or falsely certified that occurrence statement. No claims are removed and no scalar/time validator is added.

## Controls and current verification

- **RC-01:** source metadata`current:false`is an artifact property, not proof of device inactivity. Original control and later candidate preserve application uncertainty. Old obligations and later control overstate non-application; old relationships also changes2026to2016and contradicts its own output. These are model errors, not newly inferred historical score changes.
- **RC-03:** exact MicaCore forward ingress22021/egress22022and return ingress stop22022, distinct violet/default VRF and no live/protocol proof remain in correct controls. Integer auxiliary interface IDs are schema errors, not wrong path prose; current core/auxiliary separation preserves correct text. Old obligations' broad device lists omit required interfaces; filling an outcome ID does not cure it.
- **RC-06:** all five raw responses preserve the positive before/after modeled egress-deny consequence at CedarEdge11011and distinguish it from physical deployment/outage proof. Original control and relationships had historical false successful-interface contradictions, already repaired. Current release retains all five explanations; it does not collapse supported modeled outcomes into unknown.

The 30 offline replays use original raw outputs, original frozen schemas and admitted records, with provider/model/reader/network execution blocked. **Current reviews match saved current reviews30/30; current released text matches30/30; all 30 raw answer bodies remain present.** For the earlier 18, “saved current” means the previous explicitly labelled updated-verification replay; the original live-withheld answers remain original historical artifacts. This is neither 30new model successes nor a new repaired-verification score.

No current declared incident occurrence claim is wrongly certified. Exact positive effective times and successful traversal scopes remain supported; genuine wrong declared scalar/owner/time/VRF/direction cases remain blocked by existing regressions. Remaining wrong prose survives under an unverified label because its actual deduction is not expressed as a checkable typed contradiction. That is a real user-answer quality limitation, not a successful semantic release guarantee.

**Existing focused regressions:46 passed,0 failed,0.90 seconds.** These are the unchanged `test_release_checker_scope_repair.py` positive/negative tests. No new application tests or artificial test count were created. The prior 153 affected pass remains historical evidence, not rerun or added to 46. The 30 artifact replays are separately counted compatibility observations, not unit-test or intelligence scores.

## Thirty-output classification index

Each row below preserves its historical prose grade. Full fields and exact files are in the linked inventory/matrix; classification annotations are new diagnosis, not regrading.

| Exact cohort / case / arm | Historical prose grade | First semantic or historical release divergence |
|---|---|---|
| reasoning_contract_18/RC-01/off | ADEQUATE | No material prose failure identified in the frozen review. |
| reasoning_contract_18/RC-01/obligations | PARTIAL | Raw prose upgrades staged/current:falseartifact metadata into definite non-activation at capture/save time. |
| reasoning_contract_18/RC-01/relationships | INCORRECT | Raw prose changes2026source dates to2016; an outcome separately asserts definite non-application. |
| reasoning_contract_18/RC-02/off | INCORRECT | Raw answer infers08:00value12000from07:00snapshot plus absence of recorded changes. |
| reasoning_contract_18/RC-02/obligations | PARTIAL_AMBIGUOUS | Raw answer equivocates on08:00; outcome request-2and assessment explicitly assert08:00value12000. |
| reasoning_contract_18/RC-02/relationships | ADEQUATE | Raw prose adequate; first historical release failure: Historical fatal optional-navigation handling; already corrected. |
| reasoning_contract_18/RC-03/off | ADEQUATE | No material prose failure identified in the frozen review. |
| reasoning_contract_18/RC-03/obligations | PARTIAL | Raw prose substitutes broad device lists for required owned ingress/egress interfaces. |
| reasoning_contract_18/RC-03/relationships | ADEQUATE | Raw prose adequate; first historical release failure: Historical fatal optional-navigation handling; already corrected. |
| reasoning_contract_18/RC-04/off | ADEQUATE | No material prose failure identified in the frozen review. |
| reasoning_contract_18/RC-04/obligations | ADEQUATE | Raw prose adequate; first historical release failure: Historical fatal optional-navigation handling; already corrected. |
| reasoning_contract_18/RC-04/relationships | QUALIFIED_BORDERLINE | Frozen review marks broad control-plane path wording borderline, not a definite delivery verdict. |
| reasoning_contract_18/RC-05/off | INCORRECT | Raw prose uses12:31record timestamp as event occurrence and reports four minutes before12:35sample. |
| reasoning_contract_18/RC-05/obligations | INCORRECT | Raw prose uses12:31record timestamp as event occurrence and reports four minutes before12:35sample. |
| reasoning_contract_18/RC-05/relationships | INCORRECT | Raw prose uses12:31record timestamp as event occurrence and reports four minutes before12:35sample. |
| reasoning_contract_18/RC-06/off | ADEQUATE | Raw prose adequate; first historical release failure: Historical successful-interface false identity conflict; already corrected. |
| reasoning_contract_18/RC-06/obligations | ADEQUATE | No material prose failure identified in the frozen review. |
| reasoning_contract_18/RC-06/relationships | ADEQUATE | Raw prose adequate; first historical release failure: Historical successful-interface false identity conflict; already corrected. |
| temporal_instruction_12/RC-01/control | PARTIAL_UNSUPPORTED_SCOPE | Raw prose upgrades staged/current:falseartifact metadata into definite non-activation at capture/save time. |
| temporal_instruction_12/RC-01/candidate | ADEQUATE | No material prose failure identified in the frozen review. |
| temporal_instruction_12/RC-02/control | ADEQUATE | No material prose failure identified in the frozen review. |
| temporal_instruction_12/RC-02/candidate | INCORRECT | Raw answer infers08:00value12000from07:00snapshot plus absence of recorded changes. |
| temporal_instruction_12/RC-03/control | ADEQUATE | No material prose failure identified in the frozen review. |
| temporal_instruction_12/RC-03/candidate | ADEQUATE | No material prose failure identified in the frozen review. |
| temporal_instruction_12/RC-04/control | PARTIAL | Raw answer omits the requested passive next-evidence recommendation; assessment nevertheless says supported. |
| temporal_instruction_12/RC-04/candidate | PARTIAL | Raw answer omits the requested passive next-evidence recommendation; assessment nevertheless says supported. |
| temporal_instruction_12/RC-05/control | INCORRECT | Raw prose uses12:31record timestamp as event occurrence and reports four minutes before12:35sample. |
| temporal_instruction_12/RC-05/candidate | ADEQUATE | Raw answer prose is correct; claims/0.statement asserts occurred12:31and outcome_assessments/0.assessment merges12:30/12:31. |
| temporal_instruction_12/RC-06/control | ADEQUATE | No material prose failure identified in the frozen review. |
| temporal_instruction_12/RC-06/candidate | ADEQUATE | No material prose failure identified in the frozen review. |

## Proven findings versus hypotheses

| Finding | Evidence status | Repair decision |
|---|---|---|
| Correct operands and original requirements reached the model |30 exact packet/schema/wire matches; records and question inspected | Preserve source/retrieval/transport. |
| Unsupported08:00continuity first appears in raw output | Direct excerpts; correct and incorrect answers coexist under exact control inputs | Model deduction failure; no current deterministic patch. |
| RC-04advice omitted despite explicit input | Direct raw answer versus request-1; same control schema has earlier valid advice | Model task omission; grouped structural checks are limited, not proven erroneous. |
| RC-05candidate output is internally inconsistent | Correct answer compared with wrong claims/assessment | Model output inconsistency; do not overwrite good prose. |
| Existing timestamp selector semantics are not described in schema | SourceClaim schema versus `_compatible_operands`record filter | Interface ambiguity demonstrated; impact on model quality unproven. No schema/instruction change authorized as an offline fix. |
| Duplicate temporal interpretations in independent generated fields | Answer, assessment, statement/value fields inspected | Potential design pressure only; no causal proof that removing/altering fields improves reasoning. |
| Index/current/type labels and broad no-read wording may affect attention | Exact fields/instructions exist; explicit time/advice boundaries also exist | Hypotheses, not current source loss or reasoner compulsion. No metadata/policy rewrite. |
| Current checker does not certify all free prose | Explicit non-certifying trace and insufficient-support results | Known semantic-release limit; do not expand to universal validation. |
| Effective-time/successful-path/optional-navigation false suppression | Historical failures reproduced by prior audit; current 30 replay matches repaired behavior and46 regressions pass | Already corrected. Retain repair, do not claim it again. |

No completed wrong response here is caused by provider noncompletion. All 30saved outputs finishSTOP. Raw answers fit their12,000 character allowance; provider8192 output limit was not reached in a capped completion. Thinking was requested low, but thought-token reporting is absent; no hidden thinking-budget inference is justified. No internal model chain of thought is available, and none is fabricated.

## State preservation and what changed

**No application repair justified. No production behavior changed.** Changed files are this requested report, a bounded continuation addition and new audit scripts/results only. There is no source/test/schema/instruction/metadata/reader/provider/configuration change. No services or browser/editor state were touched, so there is no new browser acceptance or buffer-content readback claim.

[Preservation proof](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261102T094917Z-gemini35-offline-failure-diagnosis/preservation-before-handover.json): same HEAD`840031451e954809f2817adf78d800bc6548c2d4`, identical logical index and binary index hash,110 application-source hashes,888 previously protected files before documentation,42 ordinary table inventories/fingerprints, both environment hashes,99 quota entries byte-identical,1,923 knowledge files,341 active artifacts and release`7a14a351e52b49aeb87f65d1192f0937`. Existing 27 missing temporary fixtures remain absent and were not reconstructed. The previous checkpoint is archived byte-for-byte and retained under the new continuation prefix.

Actual model roles, low thinking,8192 allowance, source permissions, 64K guard, dependency_view_v3, supplementary delivery and simulator remain unchanged. `COGNISHIELD_AI_REASONING_CONTRACT` and `COGNISHIELD_AI_REASONER_INTERPRETATION_EXPERIMENT` are unset/OFF in both environment files; ApproachArootsetting remains0and other experimental ordinary defaults remain unset/OFF. Replay parses the historical experimental outputs locally without enabling those experiments or dispatching inference.

New provider calls0; new model calls0; new registered reads0; guarded network connections0; quota writes0; credentials exposed0. No commit/stage/reset/clean/publication/deployment/device action, no alternative reasoner and no new cloud authorization request.

## One smallest next action, not implementation

**Prepare a description-only clarification of the existing `SourceClaim.timestamp` contract:** it selects the cited record's timestamp, while `field/value` declares the event/observation/effective value under discussion. Keep the same fields, matching behavior, role and release authority; do not add output locations or a second pass. This targets the demonstrated08:25/08:26auxiliary binding ambiguity, not the independent08:00deduction or omitted advice.

This report records that proposed direction only. Changing the model-facing schema/instructions would require separately scoped Gemini 3.5evaluation before any claim of benefit; none is launched or requested here. If the interface is clarified later, complete-task/raw-prose quality must still be measured separately because this clarification does not establish a solution to RC-02orRC-04. Do not stack generic prompts, implement a new architecture or seek another model.

**Stop at this diagnosis.** Both experiments stayOFF. Original grades remain frozen. G4/G5/G6/G11remain unaccepted; no formal PhaseGstage is closed by artifact replay or regressions.
