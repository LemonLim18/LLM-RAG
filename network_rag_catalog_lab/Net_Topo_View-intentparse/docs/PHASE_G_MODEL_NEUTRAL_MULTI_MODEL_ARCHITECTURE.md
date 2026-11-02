# Model-neutral experimental intelligence — implementation and acceptance

2026-10-26. Specification: `main_implementation_idea/Phase_G-Hybrid-Pluggable-Model.md`.

**Implemented and activated for explicitly approved synthetic development. Acceptance remains partial.** This is not acceptance of G4/G5/G6/G11. The original local1/30 versus hybrid7/30 qualification, causal0/16 versus5/16 and its original failures remain unchanged. Approach A is OFF. No new30/120-case benchmark was run.

## Execution and modified components

`authenticated exact-request consent → existing gateway → existing LangGraph → complex_planner → existing authorized readers → evidence_reasoner → optional supplementary reads → final evidence_reasoner → unverified preview`.

- `backend/llm/model_roles.py`: logical roles, normalized inference request/result, capability checks, Google/Ollama transports and opt-in OpenAI Responses adapter. No new model registry, SDK, database, planner or dependency.
- `backend/llm/gemini_provider.py`: one shared Google generateContent transport for3.1/3.5; owner consent binds role models, output/schema/thinking settings, verifier mode, refinement permission, request/history and scenario revision. Shared project and per-model quota reservations remain in the existing persistent ledger.3.8 is rejected; its Interactions runtime branch is removed. Historical reports are preserved.
- `orchestration/model.py`, `planning.py`, `engine.py`, `state.py`: an approved complex request dispatches directly to3.1. It does not first ask Qwen for a plan. The same IntentPlan/SemanticRoute and graph execute the resulting validated read proposals. Existing local and V9 engineering paths remain.
- `orchestration/role_reasoning.py`: full relevant reader records, parsed/raw configuration operands, directions, dependencies, source IDs, timestamps and limitations; typed `answer`/`need_more_evidence`; strict validation of supplementary proposals; separate synthetic-preview release.
- `gateway_network.py`: server-validated supplementary parameters enter the existing readers and authorization checks. `gateway.py`: actual reasoner model attribution and explicit unverified/no-engineering-authority release metadata.
- Both assistant components and `frontend/src/services/ai.ts`: existing Cloud·synthetic consent control describes the actual roles, structured-output mode and unverified scope. The ordinary Send action remains separate.
- `backend/scripts/evaluate_model_roles.py`, two new focused test files and the existing provider tests: disposable authenticated acceptance and mocked protocol/graph tests. The provider tests were migrated from the explicitly retired3.8 transport; historical evaluation files were not rewritten.

## Effective roles and structured output

| Role | Provider/model | Output allowance | Thinking |
|---|---|---:|---|
| local_default | Ollama/qwen2.5:1.5b |512(socket) | existing local controls |
| complex_planner | Google/gemini-3.1-flash-lite |2048 |low |
| evidence_reasoner | Google/gemini-3.5-flash-lite |8192 |low |

Ordinary conversation retains the existing local provider allowances; the512limit describes the role socket, not every historical local-chat path. Complex eligibility reuses existing scoped investigation, advisory, compound and comparison information, including comparisons between current/saved records on the same reader. A basic one-device explanation remains local.

Google3.1's small structured connectivity request succeeded in10.28s. The full planning constrained grammar returned HTTP400 INVALID_ARGUMENT in the first three gateway requests. Two isolated schema diagnostics also failed. These are request-contract failures, not failed model reasoning. The original packets and errors are retained.

The experimental roles therefore explicitly use **validated_json**: supported JSON MIME output with the complete schema in the schema instruction, followed by unchanged JSONSchema and Pydantic validation before execution. This is not native constrained-schema compliance; malformed or contract-invalid output is still rejected. There is no automatic transport retry. Strict `json_schema` transport remains selectable and currently incompatible with the tested full planning grammar. The role manifest and UI consent disclose this difference.

Google documents both structured-output complexity errors and the need for application validation: [official structured-output reference](https://ai.google.dev/gemini-api/docs/structured-output). No claim of universal model interchangeability is made.

OpenAI uses stateless Responses requests with `store:false`, supported messages, exact schema, bounded output, normalized usage/refusal/incomplete/error handling, quota reservation and concurrency1. Only mocked protocol tests ran; no OpenAI credential or live request was used. Select a registered model, `THINKING=off` and `SCHEMA_MODE=json_schema`. Actual compatibility of the complete graph schemas with OpenAI remains unverified; its strict-schema restrictions must be checked before live use. [Official Responses structured-output documentation](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses).

## Evidence, refinement and preview boundaries

The reasoner receives actual scoped tool operands instead of the old shortened prose projection. The packet contains the original instruction and owned context; a planning proposal does not replace them. Raw/parsed records, exact identities and provenance remain inspectable. Credential-line redaction operates on record leaves, retaining unrelated operands and explicit redaction receipts. Inputs exceeding64000 characters fail explicitly rather than silently truncating mandatory records.

The existing graph permits one supplementary round, at most3proposed readers, within8total tool calls and3role calls. Proposals must name registered authorized read capabilities, pass their real parameter schemas, preserve target/time/interface restrictions, cite known receipts and respect source exclusions. Active collection, engineering actions, unknown targets, unrelated targets and repeated readers are denied. **Repeated readers are currently conservatively denied even with different parameters**; this limits some refinements and is not claimed as comprehensive adaptive investigation.

One120s monotonic request deadline covers planning, tools, quota waits, reasoning and continuation. Planning is capped at35s and reserves downstream time; subsequent calls use only the remainder. No independent120s-per-call clocks or hidden model retries are introduced.

The default experimental semantic mode is `off`. Model prose is preserved beneath **Unverified AI interpretation — synthetic development mode**. `report_only` retains prose with diagnostics; `enforced` keeps the earlier factual reconstruction available. Authentication, source authorization, schema/citation/receipt integrity, V9 contracts, editor review, file-write and device-action controls remain active. A structurally verified record does not certify the model's causal explanation.

## Functional evaluation and actual limitations

Frozen registry: `evaluations/phase_g_model_neutral_functional_v1.json`; receipt and all raw traces: `tmp/phase-g/iterations/20261026-model-neutral/`. Source-derived, independently checkable, implementation-assistant graded; not blinded/external grading. Six turns cover five distinct functional conditions; the two assistant surfaces repeating the causal question are not independent generalization cases.

| Case | Actual corrected gateway behavior | Complete-task review |
|---|---|---|
|MN-01 Floating |3.1plan → state/configuration →3.5; R1Gi0/1 down/shutdown, correct R2peer, simulated failed reachability |Adequate selected-case explanation |
|MN-02 Studio |Same role flow and ownership; no edit/generation/save |Adequate selected-case explanation |
|MN-03 Studio |Both current and saved text plus explicitly unavailable syslog; shutdown/no-shutdown comparison and unknowns |Adequate selected-case explanation |
|MN-04 Floating follow-up |Two advisory recommendations, no source-reader execution |Partial: insufficient prioritization relative to the known fault; no reasoning-quality pass |
|MN-05 ordinary conversation |Qwen answers23;0cloud calls |Local positive control |
|MN-06 simple inventory |Correct R2interface addresses;0cloud calls |Deterministic factual control, not model reasoning |

The registry's MN-01 expectation mentions a saved/current comparison although its prompt requests current configuration only. That extra expectation is an authoring defect; it earns no unsolicited extra-read requirement. The frozen registry remains unchanged and no formal score is inferred from this functional set.

Root-cause corrections preserved alongside original failures:

1. Native provider grammar incompatibility: explicit validated-JSON mode, original application validation retained.
2. A role plan offered logical category filters absent from an older scenario contract; these yielded empty records. Planning now offers only categories exposed by the active source contract. The corrected real reads return the actual records.
3. Advisory citations can be actual owned receipt IDs, prior-turn source labels or unambiguous returned record IDs. The first integration rejected valid references. Those bindings are now checked against actual authorized context rather than treating arbitrary values as sources. Original failed browser output is retained; its raw-output replay passes. The final browser retest now preserves those valid references without executing readers. Diagnostic usefulness remains partial; structural binding is not semantic completion.
4. Serialized whole-packet redaction could erase unrelated fields. Leaf-level redaction preserves packet structure and records omissions.

Additional browser evidence: Studio's actual consent control returned the correct comparison with separate capture times and the unavailable-syslog caveat; Floating displayed the unverified model explanation. A different Floating prompt omitted its requested topology read and selected syslog: **model planning/task-completion failure**, not a passing source/workflow gate. The saved-capture continuation condition retrieved state in the initial plan. **No live model has yet exercised `need_more_evidence` through the second graph round.** That branch passes the real-graph/mocked-inference test; no live refinement pass is claimed.

An existing retained draggable Floating launcher can overlap the narrow Studio footer. Keyboard activation reaches the actual consent control. No browser permission/profile reset or editor action was used.

## Tests, quota and preservation

-125affected tests passed;117preserved B1/B2/B3/planning tests passed in a separate suite. Latest new role/socket/graph suite:30passed. Overlapping reruns are not added together.
-TypeScript application-project check passed (`-p frontend/tsconfig.app.json`), not merely the empty root solution config. CR-aware Git whitespace check passed. Earlier failed tests and the duplicated-import UI failure remain in audit logs with corrected runs.
-Actual corrected complex gateway requests took8.05–11.10s; arithmetic10.79s, simple inventory0.55s. Raw3.5prose survived composition in the successful interpretation cases. These selected cases do not establish G5/G6 accuracy or a120s-load guarantee.
-Final quota receipts:37new reservations, including one sandbox connectivity reservation without HTTP dispatch;36actual Google calls,5HTTP400 grammar failures. Per-model reservations:3.1=22,3.5=15. Shared rolling24h ledger121. Observed peak8requests/60s and97199input tokens or conservative reservations/60s; limits15RPM/150KTPM/shared500RPD. The final browser retest used6cloudcalls across3approved requests;2ordinary Send controls used0cloudcalls. Known response-token totals are in the audit; failed-request token use is unknown and conservatively reserved. Calls outside this application are unknown.
-Preservation audit passed for HEAD/index, all41ordinary tables, integrity, the active release `7a14a351e52b49aeb87f65d1192f0937`,341immutable artifacts plus manifest/pointer, the ignored single-key credential file and all60historical frozen traces/registry/review. No credential copies detected in the audit.
-The ordinary5173/8000pair was not restarted. Only disposable5174/8001was used. No editor input, Save, Accept, Undo, publication, staging, commit, device execution or model installation occurred. Visible retained draft tabs/content remained present; no fresh hash of the inaccessible ordinary editor buffers is claimed.

## Enable, rollback and continuation

Root `.env` now sets `COGNISHIELD_AI_MULTI_MODEL_EXPERIMENT=1`, the two configured Google roles, `EVIDENCE_REFINE=1`, `MULTI_MODEL_CALLS=3`, verifier=`off` and explicit validated-JSON mode. `.env.example` keeps the experiment and hybrid OFF. Approach A remains0; the older optional3.5 planning-refinement flag remains0 and does not disable the new direct role planner. API metadata distinguishes these modes.

Flags alone grant no external access. A server-approved exact synthetic scenario fingerprint, engineer/admin owner and exact request/history approval are all required. Editor buffers, uploads and unapproved source/history remain excluded. Use the existing Cloud·synthetic action after inspecting its role/scope tooltip; ordinary Send stays local.

For an isolated reproducible workspace, run `backend/.venv-m0/Scripts/python.exe -B backend/scripts/evaluate_model_roles.py --name NEW-UNUSED-RUN --skip-turns --serve`. It imports only the frozen synthetic fixture into its disposable DB, seals that revision for this process, serves the real app on5174/8001and never changes ordinary scenario selection. Write that run directory's `STOP` file afterward. Do not reuse a run name that would overwrite earlier evidence. Non-`--skip-turns` executes the six bounded functional cases; it does not run a broad benchmark.

Immediate local-only rollback: set `COGNISHIELD_AI_HYBRID=0` and `COGNISHIELD_AI_MULTI_MODEL_EXPERIMENT=0`, restart the owned backend. To retain the earlier Qwen-planned/3.5-synthesized scoped experiment, disable only `MULTI_MODEL_EXPERIMENT` and retain its existing synthetic consent controls. **Gemini3.8is retired and is not a rollback option.** Changing roles, thinking, schema mode, verifier/refinement policy or the scenario invalidates outstanding approvals.

Continue from `PHASE_G_MODEL_NEUTRAL_CONTINUATION.md`. Retain this experiment; do not promote ordinary inference, activate Approach A, claim original Phase G acceptance or launch a broad benchmark. The latest advisory identity/browser retest is complete. The next evidence gate is a genuinely model-requested supplementary round, without tuning individual prompts or weakening source identity checks.

## Final browser closeout

`tmp/phase-g/iterations/20261026-model-neutral/browser-final-v5/acceptance-review.json`:5actual browser-originated turns on final Google-path code. Studio comparison, Floating causal explanation and both local controls pass their selected functional checks. The advisory answer now survives structural citation binding and executes0readers, but remains partly circular and receives no complete-task reasoning pass. All3raw cloud interpretations survive composition exactly below the unverified label. The cloud payloads contain no retained-editor sentinel; both draft tabs and visible editor content remain. Keyboard use was required for the overlapping launcher hit target. Both5174/8001listeners were stopped. No live supplementary-round pass is claimed.

Later local-socket usage normalization, thinking-capability rejection and same-reader comparison eligibility have focused regression evidence; they do not earn additional live-model quality credit. Source hashes, original failures, reruns, screenshot/DOM evidence, quota receipts and exact continuation state remain in the audit and checklist.

Measured provider usage across31completed responses: 195172input tokens, 5872final-output tokens and 3511reported thinking tokens. This deduplicates per-case and combined traces;5HTTP400request token charges are unknown. No billing change or cost claim.

Interpretation limits: the initial plan retains the existing domain/source-scope/category contract and server entity/query resolver; this milestone does not add general per-outcome multi-target scheduling. The generic provider400did not identify an exact unsupported schema keyword, so grammar complexity is a plausible cause, not a vendor-confirmed diagnosis. The legacy graph field `provider_limitation` can also contain a structural output/citation rejection; use the raw provider response and scope trace to classify that case rather than calling it cloud downtime.


## Latest bounded qualification — 2026-10-26T13:34:36.352840+00:00

Task finished; no new full stage accepted. G4/G5/G6 remain FAILED, MN4 LIVE NOT VERIFIED. Original new cohort30: G5 **5/30** (requires26/no criticalfalseclaims); G6 **8/18** adequate causal; rawmodelexplanations13/30; extra-readerconditions19/30; sourceconformance18cases/bothsurfacesPASS. Original54cloudattempts include5HTTP503and1timeout. No originalneed_moredecisions; diagnosticpending-readwithoutactualexecution is not a livepass.

Shared source-only enforcement, effectivequeryidentity/same-reader lists, roleeligibility and savedCLIversusprotocolstate binding are corrected.134affectedtestsPASS;18sourceconformancePASS,separateassertionsnotcombined. Bounded3conditionpostfixregistry and9additionalcloudcalls retained; correctedconfigurationreplayreadsactualsavedvalues. Browseravailable; bothcloudUIrequestsBLOCKEDprovider503/timeout; twoordinaryQwencontrolsPASS0cloud. No currentliveadvisory/fullcloudbrowserpassclaimed. Disposable5174/8001stopped.

Report:`docs/PHASE_G_MULTI_MODEL_G4_G6_QUALIFICATION.md`; result:`docs/evaluations/phase_g_multi_model_g4_g6_result.json`; audit:`tmp/phase-g/iterations/20261026-multi-model-qualification`. PreservationPASS:HEAD/index/41tables/343releasefiles/credential/60old+30newtraces. Total63cloudattempts;shared184rolling24h;peak9RPM/122115input-or-reservationTPM within15/150K/500ceilings. SemanticverifierOFF,ApproachA0,ordinaryQwen2.5 and exactsyntheticconsent retained.

Safe stopping state: no process to resume. Do not rerun/rescore the frozen cohort after sourcechanges. Keep originalfailedresults. LiveMN4 requires a genuinely requested authorized secondread plusfinalmodelinterpretation; mockedtests and an unexecutedpendingmessagecannotcloseit. Await nextuserauthorization before newcloudtests or broaderdevelopment. Nextrecommendedreview: planner/sufficiency limits and provideravailability, not per-promptguards. G7remains113/141with28upstreamcompatibilityblockers; allotheroriginalstagestatusesunchanged.

---


The qualified execution shape remains one SemanticRoute/IntentPlan, one LangGraph and the existing capability registry. The latest correction adds actual query receipts and typed ToolStep arguments, not a second planner or store. User source restrictions bound the proposed domains; source aliases do not replace a role's typed need merely because a protocol word appears in saved CLI. The reasoner can propose a schema-valid, relevant, distinct query using returned typed relationships. The server validates/deduplicates it before at most one read round and one final call. Raw model prose remains unverified; no quality promotion follows from source or schema conformance.


## Bounded intelligence-improvement closeout — 2026-10-26

**Task finished; no new full Phase G stage closes.** Report: `docs/PHASE_G_MULTI_MODEL_INTELLIGENCE_IMPROVEMENT.md`. Result: `docs/evaluations/phase_g_intelligence_improvement_result.json`. Audit: `tmp/phase-g/iterations/20261026-intelligence-improvement/`.

Within the existing roles, implemented required/optional needs, original-clause self-assessment with source identity checks, a record identity index, actual query/budget context and the shared logs/syslog restriction alias. No new planner, semantic verifier or inference stage. Semantic modeOFF, Approach A0and model settings remain unchanged. The affected suite passed165tests; twelve new source checks verified both surfaces. These are not intelligence scores.

New frozen holdout: **2/12fully adequate**,2partial,1unsupported ECMP loss claim,6planner503s and1planner timeout; **2/7causal adequate**. All five completed model explanations survive composition, but their self-assessments do not certify correctness. Zero unnecessary readers executed in the five tasks reaching readers; raw planning is still imperfect. No `need_more_evidence` decision or live supplementary round occurred. Original30-case5/30and8/18scores remain unchanged.

Browser works: both actual approved role flows display partial answers; the advisory gets503with zero reads; two ordinary Qwen controls pass with zero cloud calls. Disposable5174/8001are stopped. Total22cloud attempts are within the44-call allowance; observed shared peaks5RPM/118798input-or-reservationTPM are below configured ceilings. Final ledger196rolling24-hour reservations includes expiry of older entries.

Preservation passes for HEAD/index,41ordinary tables,343release files,145historical JSONs, root.env, credential and new frozen outputs. Two visible unsaved tabs remain; no editor input or save occurred. No commit, publication, deployment or model change.

No active process remains. Await next authorization. Recommended next work: provider reliability for a matched contract/sufficiency comparison, not a broad cycle or per-case guards. Formal statuses remain G4/G5/G6/G11FAILED; G0historical BLOCKED; G7113/141BLOCKED; G1–G3/G8/G9/G10/G12PASS within prior scopes.

---



## Evidence-aware harness closeout — 2026-10-27

**Bounded task FINISHED; no new full PhaseGstage closes.** See `docs/PHASE_G_EVIDENCE_AWARE_HARNESS_ENGINEERING.md` and `docs/evaluations/phase_g_evidence_harness_result.json`. Audit: `tmp/phase-g/iterations/20261027-evidence-harness/`.

Default-OFF pure metadata ledger, selective validated reader hints/schema deduplication and provenance labels integrate into the existing reasoner packet. Source facts unchanged; current consent binds all flags/version. Provider failure receipts retained; no retry/new planner/state store/semantic verifier. ExistingQwen/3.1/3.5roles,3calls/120seconds/quota/permissions/V9remain unchanged. ApproachA0, semanticOFF.

Frozen6pairedconditions: control2/6fullyadequate, enhanced2/6; conditional2/6versus2/5completedreasoners. Enhancedplanner times out once. Original outputs and frozenv1authoring failure/v2correction retained. Both arms still have relationship/advisory mistakes and miss referenced event intent. Guidance is visible but ignored;0need_moredecisions/0supplementaryrounds. MN4LIVE NOT VERIFIED. No reasoning improvement claimed from smaller packets/JSON/reader success.

187affectedtestsPASS; final35andpost-review66PASS overlap, not summed.18sourcecases bothsurfacesPASS (6new+12prior). Five exact zero-cloud historical replays preserve facts/IDs and reduce total context10.6–15.1Kcharacters after removing duplicate schemas. Final legacy whole-reader-unavailable hint exclusion was added after the cohort, tested without extra inference; paired scores unchanged.

Actualbrowser: enabled/recovered initial Vite navigationtimeout; Studio cloud planner timeout; Floating reaches bothrolesandallmetadata but qualityFAILS(no-shutdown/absentlogs/intentclaims). Both ordinarySend arithmetic controlsPASSonQwen0cloud;2unsavedtabs/visiblecontentretained, no editoractions/fullordinarybufferhashclaim.26totalGoogleattempts(23paired+3browser),24HTTP200/2timeouts,0retries/503/429. Peak5RPM/55456input-or-reservationTPM; rollingday222/500atclose. No ordinaryapp restart.

PreservationPASS:HEAD/index,41ordinarytables,1923releasefilesincludingactive341artifacts,194historicalJSONs,credentialandroot.envunchanged; no credentialcopies. Disposable5174/8001STOPPED, no runningturns. No commit/stage/publication/deployment/modelinstall/deviceaction.

Recommendations:ledger/provenanceKEEPexperimentalOFF;guidanceREVISEandkeepOFF;operationalclassificationKEEP. No process or cohort to resume. Do not rescore/repeat frozen cases or activate harness automatically. Future controlled tests require newauthorization. FormalG4/G5/G6/G11gatesunchanged; G7113/141blocked by28compatibilitycontracts.

---

### Optional evidence metadata contract

`orchestration/evidence_harness.py` derives retrieval-only coverage and index provenance from existing state; it does not persist a parallel plan or infer conclusions. `engine.py` supplies hints validated by the existing supplementary query authorization. `role_reasoning.py` serializes metadata after source redaction and before the unchanged64000character boundary. Shared schemas replace duplicated full reader schemas.

New default-OFFmaster: `COGNISHIELD_AI_EVIDENCE_HARNESS=0`. Component switches `COGNISHIELD_AI_HARNESS_LEDGER/GUIDANCE/PROVENANCE` default1onlywithinmaster1. Existing server consent manifest binds version/flags, so prior approvals cannot authorize a changed packet. These flags grant no source authorization. Ordinary/rootconfigurationunchanged. Observability classifies execution errors without semantic verdicts; no retry. See the closeout report for provenance limits, post-cohort availability edge correction and the2/6versus2/6failure to establish quality improvement.


## Completeness-first bounded task closeout — 2026-10-27T04:01:44.233174+00:00

**Finished: REVISE / KEEP DEFAULT OFF. No new full Phase G stage closes.**

Report: `docs/PHASE_G_COMPLETENESS_FIRST_EVIDENCE_INVESTIGATION.md`. Curated results: `docs/evaluations/phase_g_completeness_first_result.json`. Audit: `tmp/phase-g/iterations/20261027-completeness-first`.

Implemented within the existing roles and graph: broad authorized source coverage, original restrictions, network ownership/context, compatible artifact diffs, deterministic post-draft follow-up for typed references, limited source-operand compatibility and a separately consented profile (version 2: 360 seconds, 24 reads, 3 rounds, 5 role calls). The 64K packet and 72K single-inference caps remain. No new planner, RAG system or dependency.

The live CF-01 sequence was draft(answer) → server-triggered syslog read → revised real Gemini explanation. Final compatibility/JSON failed; this was a mechanism pass and a complete-task failure. Frozen diagnostic scores: control 4/8 adequate, enhanced 0/8. Exact MN references: MN-01 schema failure; MN-02 pass; MN-03 provider 503. Historical scores remain unchanged.

Post-cohort shared binding corrections pass 143 affected tests. Both actual narrow cloud browser reruns pass; ordinary Send arithmetic stays on Qwen with zero cloud calls on both surfaces. This does not establish improved broad causal reasoning. Total: 69 cloud calls (19 + 46 + 4); 62 HTTP 200, six HTTP 503, one timeout. Retained-ledger peak: 11 requests and 144880 accounted input units per 61 seconds; rolling-day count 231 at close. No provider retry, substitution or billing activation.

Preservation passes for HEAD/staged entries, 41 ordinary tables, 1923 knowledge files including 341 active artifacts, 239 historical JSON traces, credential and root environment. No credential copies. Two unsaved test tabs and visible content retained; no editor actions or full ordinary-buffer hash claim. Acceptance servers 5174/8001 are stopped; the ordinary pair was untouched.

Effective defaults: completeness OFF, Approach A OFF, previous harness OFF, legacy remote interpretation OFF. Existing approved model-neutral roles remain. No commit, staging, publication, deployment or device action.

No active cohort/process remains. Future authorized work should reconcile declared claims with release handling without suppressing correct prose or certifying unsupported causes, then use a genuinely new small holdout. Do not rerun the completed cohort, raise the packet cap, automatically activate completeness or start broad G11 qualification.

---

