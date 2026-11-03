# Phase G — Offline answer-component coverage instrumentation

**Delivered: evaluation-only coverage diagnostics for 42 preserved outputs; no reasoner, source, transport or release behavior changed.** This implements the measurement milestone in the supplied research. It does not reverse the postmortem's finding that no new deterministic runtime defect was demonstrated, and does not establish improved Gemini deductions.

Date: 2026-11-02 (Asia/Kuala_Lumpur). The attachment's external research citations were not needed to implement these local diagnostics and are not treated here as verified external findings.

## Scope and exact files

- [Evaluator](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/scripts/evaluate_answer_components.py): standard-library-only CLI for immutable saved artifacts. No application imports, environment loading, planner, provider or source readers.
- [Evaluation registry](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/docs/evaluations/phase_g_answer_component_coverage_v1.json): 12 condition definitions, 37 component definitions, 42 hash-pinned trace references, source operands, original oracle references and separately attributed prior human judgments. Registry SHA256: `428542262e7503037166080bff628636b594b60e35e78dd059ad1afe9d5c40f7`.
- [Focused tests](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/tests/test_answer_component_coverage.py): literal/provenance boundaries, malformed JSON, ambiguity, false-positive controls, and actual frozen-cohort regressions.
- [Final replay output](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261102-answer-component-coverage/coverage-final.json): separate signals for raw answer, claims, assessments, optional outcomes, original release and the previously saved current release.
- [Preservation before](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261102-answer-component-coverage/preservation-before.json) and `preservation-after.json`: existing-state fingerprints and final comparison.
- The existing continuation checkpoint receives one append-only entry. No historical report, input, output, score, schema, prompt or oracle is changed.

“All saved outputs” in this bounded implementation means all 18 reasoning-contract, 12 interpretation and 12 timestamp-contract outputs discussed in the supplied research. It does **not** mean every earlier G0–G12 benchmark, conversation or experimental trace in the repository. The registry states this explicitly. The six RC conditions repeat across 30 responses; the six H conditions add six arrangements. These are **42 saved generations, not 42 independent generalization conditions**.

The registry is retrospective and authored with access to the prior reviews. It is evaluation instrumentation, not a preregistered or blinded experiment. Its predicates must never be injected into the runtime or counted as unseen model validation.

## What is measured, and what is not

| Dimension | Instrumented result | Limit |
|---|---|---|
| Source operands | Exact record-ID/field/value/type checks, including existing owner, time and provenance fields | Returned operand presence is not successful reasoning or live retrieval acceptance |
| Request preservation | Original question equality and traceable original clause text | Text retention does not prove intent comprehension |
| Answer-component coverage | Literal mentions or a same-sentence association signal | Mentions do not establish polarity, correct owner, entailment or complete task adequacy |
| Unsupported inferences | Frozen prohibited conclusions and attributed human observations | No automatic universal incidence rate or claim of zero violations |
| Whole-response quality | Original source-grounded grades remain inspectable and unchanged | No new automatic adequacy score |
| Raw versus release | Fields and original/current saved releases assessed separately | Auxiliary text cannot fill a missing user-facing answer retrospectively |

Probe states are deliberately limited:

- `REQUIRED_LITERAL_ABSENT`: a required literal such as 1500 is absent; numeric word boundaries prevent 15000 from matching.
- `MENTION_CANDIDATE`: a lexical mention was found. **This is not COVERED, CORRECT or PASS.**
- `UNBOUND_MENTIONS`: required literals occur, but the simple same-sentence probe does not associate them. It requires human review.
- `HUMAN_REVIEW_REQUIRED`: recommendations, causation, scope, uncertainty, paraphrases or other semantic requirements cannot be reliably classified by this probe.
- `UNAVAILABLE`: there is no answer/release to assess; this is not a source-missing inference.

Negated, quoted, wrong-owner or out-of-context statements can contain the expected words. Tests preserve that fact instead of pretending the lexical probe can resolve it. Same-sentence matching may miss a legitimate cross-sentence paraphrase; its output is a review signal, not an omission verdict. Broad semantic predicates therefore stay human-only.

Human judgments have a separate `authority`, reason and hash-pinned prior-review basis. Optional excerpts must exist in the attributed raw field. Historical grades are never replaced by those annotations. H02's conservative old grade and its ambiguity both remain visible.

## Actual replay result

| Measure | Result |
|---|---:|
| Saved outputs processed | 42 |
| Cohort counts | 18 / 12 / 12 |
| Distinct registered condition definitions | 12 |
| Component instances | 125 |
| Hash-verified original artifacts | 68 |
| Exact source operand checks | 794 / 794 present |
| Exact original questions preserved | 42 / 42 |
| Packets within the retained 64K guard | 42 / 42 |
| JSON objects with an answer string | 41 / 42 |
| Literal mention candidates | 17 |
| Required literal absent | 1 |
| Unbound time/state mentions | 1 |
| Human-only raw component probes | 106 |

The 41/42 count is **JSON parsing with an answer string**, not a fresh application-schema certification. Existing saved provider/core diagnostics remain authoritative. H06 control's malformed object stays malformed: the evaluator may read its intact answer string only as `DIAGNOSTIC_STRING_ONLY_NOT_RELEASABLE`. It never repairs the JSON, runs a checker on a synthetic replacement or creates a released answer.

The original 18 responses have both their original release and the already-saved repaired release retained. Their historical suppressed answers are not rewritten as if the original release had succeeded. The evaluator reads those old replay artifacts; it does not rerun or modify release policy.

### The known failure controls

| Case / arm | Machine observation | Separately attributed human finding |
|---|---|---|
| H01 candidate | 1500 absent from raw answer; present in auxiliary claims/assessment | Required restored value omitted |
| H01 control | 1500 mention candidate | Prior complete value explanation retained |
| H04 candidate | 07:10 and shutdown appear but are unbound by the sentence probe; auxiliary claim binds them | Later shutdown observation omitted from the actual explanation |
| H02 candidate | Semantic review required | AMBIGUOUS; strict onset-overstatement grade and permissive first-observed reading preserved |
| RC04 later control and candidate | Semantic review required | Requested passive advice omitted despite nonempty assessments |
| RC04 original control | Semantic review required | Qualified passive recommendation present |
| H05 both | Semantic review required | Two artifacts and purposes present; explicit frozen model-versus-measured-response caveat missing |
| H03 and H06 candidate positives | No automatic missing-literal finding | Prior supported timing/ownership or modeled consequences remain covered |

H05's caveat is explicitly tagged `frozen_safety_caveat_not_separate_literal_subquestion`. H01's restored numeric value is tagged as an explanation requirement rather than a verbatim request to quote the number. These distinctions preserve the postmortem's qualifications instead of making the request appear more explicit than it was.

### Human review coverage is incomplete by design

The final registry carries **45 component judgments** from source-grounded prior reviews: 38 COVERED, six OMITTED and one AMBIGUOUS. The other **80 component instances are NOT_REVIEWED** at this newly disaggregated level. They are not treated as passed, failed, unavailable or semantically complete. Prior whole-answer grades remain available for every response.

The six omission annotations are H01 candidate, H04 candidate, both H05 caveats and both later RC04 advice components. These are retrospective human findings. Only H01 has an automatically conclusive *literal-absence* signal; H04's simple association signal merely directs review. RC04 and H05 require semantic assessment. No new unsupported-inference incidence rate is fabricated from limited annotations.

The instrumentation therefore makes gaps inspectable and repeatable without claiming it has automated arbitrary answer correctness.

## Tests and actual implementation corrections

Final focused run: **30 passed, zero failures/errors**, 1.510 seconds test runtime. The runner includes its own replay of the 42 saved responses, with a fail-closed socket-connect mock. It verifies the successful controls and negative cases above.

Additional boundaries tested: changed/missing artifact hashes; path traversal and environment-file exclusion; exact typed source operands; ambiguous reused record IDs; unavailable envelopes containing records; numeric boundaries; negation/quotes/wrong owners not earning semantic success; malformed/duplicate-key JSON; human excerpt attribution; invalid/duplicate output identities; and the offline execution guard.

Initial run: 27 tests passed and two test-fixture operations failed before assertions because the sandbox denied writing/cleanup in its system temporary directory. Both test fixtures were moved to explicitly bounded repository `tmp` directories and their resolved paths checked before cleanup. [Initial failure record](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261102-answer-component-coverage/initial-test-failure.json) is preserved. A later extra availability test makes the final unique suite 30; overlapping runs are **not** added together.

During instrument review, an ambiguous summary name `structured_valid` was replaced with `json_objects_with_answer` to avoid claiming schema validation that the evaluator does not perform. The earlier task-only `coverage-result.json` is retained separately; `coverage-final.json` has the same underlying component signals and original grades with the explicit diagnostic labels. No historical model output or grading oracle was changed.

No broad application regression suite was rerun: the application is unchanged and the new CLI imports no runtime code. These tests establish evaluator behavior, not model intelligence.

## Run and inspect

From the repository root:

```powershell
.\backend\.venv-m0\Scripts\python.exe -B backend/tests/test_answer_component_coverage.py -v

.\backend\.venv-m0\Scripts\python.exe -B backend/scripts/evaluate_answer_components.py --registry docs/evaluations/phase_g_answer_component_coverage_v1.json --output tmp/phase-g/iterations/YOUR_NEW_AUDIT/coverage.json
```

The output must be a new JSON file within `tmp/phase-g/iterations`; exclusive creation refuses to overwrite existing evidence. Hash drift, missing artifacts, duplicate identities or an invalid evaluation registry fail closed. The CLI's audit hook forbids network connections, DNS, child processes, shell execution and SQLite connections. It never imports the app, reads `.env`, calls a model, opens a service or activates an experiment.

For an omission, inspect `rows[].components[]`: the original oracle, its basis, raw-answer signal, auxiliary signals, release signals and attributed human judgment are separate. For unsupported claims, inspect the frozen prohibitions and human observations; do not interpret `HUMAN_REVIEW_REQUIRED` or a missing annotation as absence of hallucination.

This is not a production quality gate. New evaluation conditions can be added only with source-derived expected components, exact saved-artifact references and clearly attributed reviews. A successful pattern match must never be used as a new semantic grade automatically.

## Preservation, status and continuation

The initial snapshot records HEAD `840031451e954809f2817adf78d800bc6548c2d4`, binary/logical index, 2,670 preexisting tracked/untracked/protected files, both environment-file hashes, ordinary DB file and all 42 ordinary table fingerprints, quota ledger, all 1,923 knowledge-release files and release `7a14a351e52b49aeb87f65d1192f0937` / 341 active artifacts. The final preservation comparison is stored separately after this report/checkpoint write. The checkpoint's prior bytes are retained exactly as a prefix; its new entry is the sole permitted change to an existing file.

No provider calls, model inference, new synthetic conversations, source reads, planner calls, quota reservations, service/browser/editor/Ollama actions, environment/default changes, staging, commits, publication, deployment or device operations occur. Runtime modules, old tests, sources, transport, packet admission, policies, simulators and release checks remain unchanged. The 27 inherited missing temporary fixtures remain absent. Unsaved buffers are untouched; no fresh browser preservation proof is claimed.

Reasoning-contract, interpretation and timestamp candidates stay OFF. Approach A, the ordinary hybrid roles and defaults remain unchanged. **No G4/G5/G6/G11 stage is promoted or closed.**

**Measurement milestone complete within the declared 42-output scope.** The remaining limitation is still model deduction/complete-answer reliability and narrow semantic release coverage. This task introduces no reasoning intervention and demonstrates no new raw quality gain. Stop here; no cloud comparison, prompt/schema tuning, production gate or new architectural layer is launched.

