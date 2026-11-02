# Phase G — Completeness-first evidence investigation

2026-10-27. **Bounded implementation and evaluation finished. REVISE; KEEP DEFAULT OFF.** No new G4/G5/G6/G11 acceptance is claimed. This is the closeout of Problems A–G in `main_implementation_idea/7_problems_to_fix.md` and the attached completeness-first mission.

The source-coverage/context/continuation mechanisms are integrated and tested. One real draft → server-driven extra read → revised Gemini explanation occurred. **Complete-task quality did not improve:** the frozen diagnostic paired comparison scores control **4/8**, enhanced **0/8**. The new typed-claim/release path suppressed useful answers and increased structured-output failures. Post-cohort corrections recover the narrow browser case on both assistants but do not replace those scores. Ordinary behavior, the previous evidence harness, and Approach A remain unchanged/off.

## Preservation and scope

Before editing, saved `tmp/phase-g/iterations/20261027-completeness-first/preservation-before.json`: HEAD, staged-entry manifest,41 ordinary-table hashes including attachment BLOB hashes,1923 knowledge-release files,239 historical JSON traces, credential/root environment hashes and source hashes. Final comparison PASS for all of these. HEAD remains `8a7f86ce4e4d7c12d2e0565bfa53ab64f4ca756d`; active V9 release remains `7a14a351e52b49aeb87f65d1192f0937`, with341 immutable active artifacts intact. No staging, commit, publication, deployment, model installation, sibling V9 edit or device action occurred.

Only the reused disposable5174/8001pair ran. It is stopped. Ordinary5173/8000was not restarted. Browser retained the same two unsaved test tabs and visible `no vlan 120` text; no editor Save/Accept/Undo/reload was performed. This is visible-state preservation, not a new hash claim for all ordinary editor buffers. Actual cloud bodies exclude that editor text. Credential remains one setting in ignored `backend/.env`, unchanged and loaded by fresh processes; task text/log/JSON scan finds no copy of its value.

An initial preservation-script mismatch used the wrong serialization for BLOBs and the raw index instead of the baseline staged-entry manifest. `preservation-method-first.json` preserves that diagnostic. Repeating the original algorithms (documented in `preservation-after.json`) matches all41tables and `git ls-files --stage`; no data/index repair was performed.

## Implemented changes A–G

| Part | Change in the existing architecture | Actual verification and limits |
|---|---|---|
| A: broad discovery | Existing IntentPlan gains investigation breadth. Original restrictions override it. Server reconciles incomplete proposals with seven relevant operational families: inventory, topology, state, configuration, syslog, telemetry, incidents. Coverage attributes model, original-request and server-added reads separately. | CF-01 and CF-05 enhanced inspect all seven; narrow/restricted cases keep their permitted families. Source availability, zero matches, failures, partial retrieval and omissions stay distinct. Broad scan is scoped, not arbitrary tenant/file discovery. |
| B: coverage over minimum reads | Relevant optional needs can execute under the profile. Same reader with genuinely different validated category/scope/limit remains eligible; equivalent covered queries are rejected. Original-clause/source operands are reconciled rather than erased by model refinements. | Actual syslog narrowing after a truncated initial read retrieves the referenced event. No-read advice executes zero new tools. Reader success and model self-assessment do not certify outcome fulfilment. |
| C: network context | A compact authorized inventory overview plus detailed implicated ports, addresses, VRFs and documented endpoints accompanies raw records. Planned inventory identity and observed state are separate. Context limits disclose remaining IDs. | Source tests include duplicated port names, wrong owner/address/VRF negatives, forward/return branches and planned/observed disagreement. Actual inventory-receipt/port binding was corrected after the cohort. Unrestricted prose relationships remain uncertified. |
| D: time and artifacts | Existing configuration operands are grouped by device/vendor/VRF; adjacent compatible captures produce lexical diffs with IOS interface/router stanza or Junos set-path context. Running-observation intervals differ from saved artifacts. Events are associated through actual references, not temporal coincidence. | Frozen CF-05 provides12:00running no-shutdown,14:00running shutdown,11:00staged file and13:00verified/applied event. Same-device context and timezone ordering pass deterministic tests; complete live temporal explanation remains partial/withheld. No universal CLI semantic parser added. |
| E: post-draft investigation | Existing reasoner answer is internal draft. Deterministic review runs after `answer`, checks source coverage and unread typed dependencies, validates additional reads through existing registry/authorization, then sends updated evidence and feedback to the same3.5reasoner. | Live CF-01 first chose `answer`; server review found `optical-order-212`, performed the actual supplementary read, and Gemini revised its explanation. Final task still failed release. This is a live mechanism pass, not a complete diagnosis pass. |
| F: evidence classes | Source records carry operational, event, running-config, saved-config, inventory/topology, derived-analysis and simulated-context classes. Claim-dependent checks inspect declared source-owned operands, identity, value, direction, source class and provenance. | Wrong owner/value, config-as-oper-health, routes-as-session-health, modeled branches-as-measured-loss, unverified activation time and physical-scope negatives are tested. Claim extraction, arbitrary prose and causal completeness are NOT universally verified. The new declaration/release contract needs revision. |
| G: request-wide budget | Default-OFF consented profile version2:360s total,90s planner,120s reasoner,90s initial reads,60s supplemental reads,5s adequacy,24reader calls,3retrieval rounds,5role calls. All share one monotonic request clock; no transport retry/substitution. | Limits and manifest invalidation tested. Live enhanced maximum52.40s. Quota waits consume the same clock. Packet cap stays64000characters and per-inference72000; duplicate metadata compacted, raw source operands retained. |

No new planner, evidence database, RAG index, provider, dependency or autonomous engineering agent was added. `investigation_support.py` is a343-line pure helper used inside the existing graph, not an independent workflow/service. Prior contracts/state are reused rather than introducing Approach A or another outcome authority.

## Exact integration points

- `backend/llm/model_roles.py`: profile configuration, versioned exact-consent manifest and execution-failure categories.
- `backend/llm/gemini_provider.py`: consent-scoped role envelope/deadline and actual role-call ceilings. Only server-approved synthetic requests can use the profile; ordinary Send remains local.
- `backend/llm/orchestration/planning.py`: existing IntentPlan breadth and relevant optional reads.
- `backend/llm/orchestration/engine.py`: breadth reconciliation, scope expansion from actual typed forwarding relationships, initial bounded reads, deterministic post-draft review, same-reasoner correction and final conflict/limitation handling.
- `backend/llm/orchestration/investigation_support.py`: coverage, network map, artifact comparisons, seven evidence classes, declared-operand checks and post-draft proposals.
- `backend/llm/orchestration/evidence_harness.py`: existing ledger/provenance/guidance reused when completeness is enabled; historical harness stays separately OFF.
- `backend/llm/orchestration/role_reasoning.py`: existing decision schema gains declared claims in this profile; same answer/need-more contract, raw operands, review feedback, lossless metadata/schema/query deduplication and real query-equivalence validation.
- `backend/llm/orchestration/model.py`: consented call allowance also reaches the adapter; the old two-synthesis-call cap no longer silently defeats the five-call envelope. Single-call context cap unchanged.
- `backend/llm/orchestration/adapters.py`, `state.py`: bounded stage time and distinct failed invocation receipts; investigation state remains in existing graph/result contracts.
- `backend/llm/orchestration/request_contract.py`, `gateway_references.py`: original no-read/source-prohibition/discourse boundaries preserved; negative-preface stripping does not erase a following positive read.
- `backend/development/source_registry.py`, `backend/local_providers/development.py`: structurally typed legacy category fallback; explicit categories take priority, unknown/free-text rows are not guessed.
- `backend/llm/gateway_network.py`: existing published reader respects its validated limit and records retrieval truncation, retaining V9 retrieval authority.
- `frontend/src/services/ai.ts`: existing Cloud·synthetic consent describes the actual expanded envelope. No new editor control or engineering authority.
- `.env.example`: default-OFF profile and documented bounds. Actual root/backend environment files unchanged.
- `backend/tests/test_completeness_investigation.py`, `test_completeness_sources.py`: positive/negative mechanism, scope, receipt, source, time and budget coverage.
- `backend/scripts/freeze_completeness_investigation.py`, existing `evaluate_multi_model_qualification.py`: frozen synthetic fixtures/oracles and paired authenticated evaluation, with capped actual cloud dispatch and preserved exact messages/results.

## Control and data flow

`authenticated gateway + exact synthetic owner consent → existing SemanticRoute/IntentPlan → original-source restriction enforcement → server breadth/coverage reconciliation → existing authorized readers → raw records + scoped network map + artifact diffs → Gemini3.5draft → deterministic post-draft review → validated additional reads and/or bounded same-reasoner correction → declared-operand compatibility → qualified/unverified response or withheld interpretation`.

Each draft records its decision, actual source coverage, outcome self-assessments, unread references, typed conflicts, validated/rejected proposals and continuation initiator. `server_post_draft` and model-selected `need_more_evidence` are not conflated. No second planning inference or independent reviewer model is introduced. Source status and outcome self-assessment remain proposals/receipts, not semantic completion certificates.

Canonical classes are claim-dependent, not a global confidence score. Running configuration can support an exact command; it cannot support operational link health. Saved configuration does not establish active state. A declared forwarding calculation can establish its own modeled verdict, not physical packet loss. Verified/applied events can support recorded application time; snapshot timestamps alone yield only an observation interval. Event references are associations, not causal proof. A root-cause paragraph receives no certification merely because its other scalar claims match.

## Freeze and grading

Registry: `docs/evaluations/phase_g_completeness_first_v1.json`. Receipt: audit `freeze-receipt.json`; source oracle: `source-expectations.json`. Eight distinct synthetic conditions cover the requested15categories, including broad discovery, narrow/restricted reads, ownership ambiguity, conflicting topology/state, history, referenced event refinement, unavailable sources, provider/contract failure and no-read advice. Three exact MN reference replays are additional regression references, not independent generalization.

Expected facts/prohibited claims/source requirements were frozen before inference. Source-derived, independently checkable, implementation-assistant graded; not blinded or externally graded. `paired-v2` repeats that registry after integration repairs, so it is a diagnostic comparison on exposed conditions. No original pilot, model-neutral,30-case or prior harness score is replaced. Extra authorized relevant reads are efficiency observations, not automatic failures.

An adequate task must answer all requested outcomes correctly or with the appropriate source-scoped limitation. Correct lookup values, JSON,200status, self-assessed supported clauses and safe fallback are scored separately from useful model reasoning.

## Original integration failures and bounded corrections

`paired-v1` attempted14arms before being stopped:19actual cloud calls. Broad evidence exceeded the64Kpacket limit because metadata/schemas were duplicated. A legacy adapter cap still permitted only two synthesis calls. Correct claim paraphrases were rejected by an exact-substring requirement. Five503responses and one planner timeout also occurred. All raw failures remain archived.

Repairs retained the64Kcap: remove duplicated navigation/schema/query/default metadata and use compact JSON, retaining raw reader values. A preserved CF-01packet probe reduced to61380characters; no mandatory records were silently cut. Adapter limits now follow the exact consent manifest. Literal statement wording is no longer a validity criterion; it is used only to locate a safe withholding span. Knowledge list coverage/limits and legacy typed-category filtering were also fixed. Numeric/string schema errors remain failures rather than being silently coerced to claim success.

The later complete paired cohort exposed additional shared binding failures. After the cohort, corrected:

1. The declared scalar field is not overwritten by a category default (a prefix cannot be compared to `oper_status`).
2. Failed-hop ownership is resolved from the actual directional failure branch, not the originating device on the parent flow. Forward/return and wrong-hop negative checks remain.
3. Authorized inventory receipt IDs bind their actual structured port records, without importing unrelated inventory as evidence.
4. A source-family permission list is not turned into an identically named subtype filter. In CF-06, allowing telemetry had incorrectly excluded interface counters.

These changes have positive/negative regressions. The narrow browser rerun succeeds on both surfaces. **They do not rescore the frozen cohort or establish a corrected broad-causal success.** Unsupported event-intent declarations, incomplete claim fields, strict JSON failures and unlocatable conflicts can still cause useful prose to be withheld. No phrase-based OSPF/VRF/ECMP answer guard or benchmark diagnosis was added.

## Complete-answer results

| Condition | Control | Enhanced | First consequential boundary |
|---|---|---|---|
| CF-01 broad failure + artifact + inspection intent | Partial | Withheld | Control misses transit operands/event purpose. Enhanced retrieves all families and referenced event, but new claim checks/revision contract block final release. |
| CF-02 narrow state/prefix | Adequate | Withheld | New checker compared a prefix to a category-default status. Corrected post-cohort; both browser reruns pass. |
| CF-03 route versus egress policy; return; BGP limit | Adequate | Invalid structured output | Useful raw explanation, but numeric identifiers violate the declared string schema. |
| CF-04 ownership/VRF/planned peer | Adequate | Withheld | Inventory receipt/port binding unsupported by the initial checker; revision schema also fails. |
| CF-05 running history versus staged file | Partial | Withheld | Control lacks the tight latest12:00–14:00running interval. Enhanced false failed-hop identity conflict; raw temporal description remains less precise than required. |
| CF-06 conflicting link/state; measured loss | Adequate | Partial | New family/category binding excluded counters; no2.5%calculation. |
| CF-07 config/state/unavailable logs/OSPF | Incorrect | Invalid structured output | Control wrongly says no-shutdown brings operational state up. Enhanced malformed JSON; released limitation does not complete the task. |
| CF-08 contextual no-read advice | Partial | Partial | Both execute zero new readers; advice still overstates reader/physical-health implications. |

**Complete-task adequacy: control4/8, enhanced0/8.** All four adequate control explanations are model-written, but this does not prove novel causal discovery independent of the deterministic calculations provided. There is no adequate enhanced released causal explanation in the frozen comparison. Useful raw enhanced prose sometimes became an inadequate/withheld final response; that is a framework/declaration release issue, not evidence that Gemini cannot reason at all. Other raw responses still contain unsupported inferences, so preserving all prose unconditionally is not a valid repair.

MN references: MN-01invalid structured response; MN-02adequate source-bound explanation; MN-03planner503. Historical original successes remain intact. This task does **not** establish that all three flows retain current live success. No provider retries were made to manufacture those passes.

Full independent dimension notes, exact trace hashes and final grades: audit `full-answer-review.json`; curated copy `docs/evaluations/phase_g_completeness_first_result.json`. Fallback/withholding safety earns no complete-task or reasoning credit.

## Representative live trace

Exact request and all stages: audit `representative-trace.json`, backed by `paired-v2/CF-01-enhanced.json`.

1. Original request asks for Harbor→Meadow failure, all relevant sources, affected hop/no-shutdown, artifact comparison and recorded inspection purpose, separating modeled failure from unproven physical cause.
2. Real Gemini3.1plans configuration/state/syslog. Server adds scoped inventory/topology/telemetry/incidents; actual forwarding relationships supply Transit rather than trusting free-text target invention.
3. Authorized initial reads retrieve actual current/saved configurations, state/model records, planned/observed context and the first8syslog rows. The log result explicitly says truncated; none is `optical-order-212`.
4. Network context preserves Transit Ethernet1/2ownership; artifacts preserve saved-versus-running identity. Exact raw operands reach real Gemini3.5.
5. First Gemini draft chooses **answer**, identifies operational down despite administrative up, but says inspection purpose is absent. Its self-assessment incorrectly claims completion.
6. Deterministic post-draft review finds the actual `current-702.change_event_ref=optical-order-212` unresolved. It proposes a registered syslog-category read with limit100. The server validates source permission, target, distinct scope and schema.
7. Actual extra `network.syslog` read returns `optical-order-212`: inspect the receive optical path after alarms; intent only, not completed repair/confirmed physical cause.
8. The same Gemini3.5revises its explanation to include that purpose and limits. No new planner/reviewer model is used.
9. Initial typed checks falsely bind the path-level source owner instead of the nested failed hop and cannot establish the declared event-message operand. Another revision is invalid JSON.
10. Final release withholds the interpretation. **Automatic refinement mechanism PASS; complete-task FAIL.** Post-cohort directional binding tests correct the first issue; no successful post-fix broad live answer is claimed.

Exactly one server-driven supplemental read is observed in this cohort; it is not attributed to a Gemini `need_more_evidence` choice. Deterministic graph tests also cover model-requested and forbidden/duplicate proposals. Automatic semantic completeness of every outcome remains unproved.

## Actual browser acceptance and local controls

Fresh built-in browser access succeeds. Initial Vite navigation timed out; binding the already-loaded acceptance tab recovered it. This was not a permission-disabled failure. The app used disposable5174/8001, authenticated admin and explicit Cloud·synthetic consent. Tooltip exposes360s/24reads/3rounds/5calls and validated-JSON/unverified scope.

- Studio and Floating each run the narrow state/prefix case after the binding correction. Both execute only `network.state`, use3.1planning/3.5reasoning, preserve admin up/oper down/prefix10.71.2.1/30, give a useful limited explanation, and retain prohibited config/log labels. Two role calls each. These are exposed acceptance reruns, not two new independent conditions.
- Ordinary Send arithmetic in both returns42via `qwen2.5:1.5b`, with zero sources and zero cloud calls. No editor text appears in any cloud request body.
- Both unsaved tab identities and visible no-vlan content remain; no editor or V9 generation action was performed.

Proof: audit `browser-review.json`, `browser-studio-cloud.txt/png`, `browser-floating-cloud.txt/png`, `browser-final.txt/png`, and actual persisted disposable gateway turns/model packets. Screenshots show the rendered result, not only an HTTP receipt.

## Runtime, context, provider and quota results

Logical roles unchanged: Qwen2.5:1.5B ordinary local, Gemini3.1Flash-Lite complex planner (2048output tokens,low thinking), Gemini3.5Flash-Lite reasoner (8192output tokens,low thinking). Google uses supported JSON MIME plus application validation of the full schema (`validated_json`), not a claim of native constrained-schema reliability.

Actual cloud dispatch: **69/72ceiling**: initial19, diagnostic46, corrected-browser4. The global run trace already includes its API cohort: per-case requests are not added twice.62HTTP200,6HTTP503UNAVAILABLE,1no-response timeout. Successful HTTP responses still include schema/quality failures. No transport retry, fallback provider, OpenAI call or Gemini3.8call. Three allowed dispatches deliberately unused.

Usage from successful provider receipts:676143input,38813final-output,7413thinking tokens (722369total; cached input included, not added again). Failure/timeout usage is unavailable; quota retains conservative reservations. No billing activation or monetary cost claim.

Retained project quota ledger at close:231rolling-dayGoogle rows, peak61s11requests and144880accounted input tokens/reservation units; ceilings15RPM/150000inputTPM/500RPD. These include retained project traffic, not only this task; older daily rows expire. Admission/concurrency locks remain authoritative.

Paired-v2whole-request latency: control min5.13/median7.46/max10.07s; enhanced min6.11/median9.55/max52.40s. These are distinct profiles with different deadlines/context/claim work, not a latency-isolated model experiment. Largest enhanced reader execution total0.017s; inference/pacing/schema checking dominates. CF-01post-draft review takes milliseconds, not another inference. Exact per-stage receipts and actual timings are in `statistics.json`.

Context costs remain material: compact network/diff/claim data adds complexity and output tokens. Largest initial packet failed explicitly; metadata deduplication brought the preserved probe under64Kwithout dropping source facts. Large future networks may still exceed it; the system must report/narrow scope rather than silently truncate. The single-call72Kcap is unchanged.

Automatic approval review rejected a proposed100Kpacket-cap increase. It was not executed. The safe alternative retained64Kand compacted duplicate metadata. No approval bypass or silent context-budget expansion occurred.

## Tests and limitations

Latest affected regression suite: **143passed in22.13s**, including reused inherited cases; do not add overlapping131/207/232/187/87runs as independent successes. Source conformance covers11frozen conditions on both authorized surfaces. TypeScript passed earlier in this task and frontend did not change afterward. Git whitespace check passes with repository CRLF handling. Original test-authoring/runtime sandbox failures and corrected reruns remain in the audit; no test pass is counted as intelligence.

Important remaining limits:

- Broad retrieval and an actual server-driven continuation work, but the combined profile has not demonstrated better complete-task quality.
- Model self-assessment still says supported while omitting referenced purpose or overclaiming an implication.
- Strict claim declarations can be malformed even when prose is useful; unsupported fields and nonliteral event intent remain difficult to bind safely. The final policy can still suppress an entire answer when a conflicting span cannot be isolated.
- Some wrong prose is outside declared claims; no universal extraction/causal-verification claim is made. The control no-shutdown error and advisory physical-health overclaims remain failures.
- Snapshot comparisons are lexical and context-aware, not vendor-complete semantic equivalence or continuous activation history.
- Exact independent G4/G5/G6/G11 thresholds and G7compatibility work are untouched. This small diagnostic study cannot close them.

## Configuration, rollback and next decision

Keep `COGNISHIELD_AI_COMPLETENESS=0` (actual fresh ordinary-process configuration confirmed). Profile enabled only in the disposable evaluator process with exact fresh synthetic consent. Existing `COGNISHIELD_AI_OUTCOMES=0`, `COGNISHIELD_AI_EVIDENCE_HARNESS=0`, legacy `COGNISHIELD_AI_HYBRID_INTERPRET=0` remain unchanged. Existing model-neutral approved-role architecture remains available.

For a future authorized controlled test, use the existing evaluation utility with `--completeness`, a new audit name and explicit cloud ceiling. It binds the profile version/budgets into consent. Do not reuse stale approvals or point the test at ordinarySQLite. Changing budgets/roles/source revision requires new exact consent.

Immediate feature rollback: set `COGNISHIELD_AI_COMPLETENESS=0` in the intended process environment and restart only that owned process; no SQL rollback/migration or V9 change is needed. Full local-only rollback remains existing `COGNISHIELD_AI_HYBRID=0` with explicit Qwen baseline. Do not reset the dirty tree or revert unrelated changes. Disposable services are already stopped via their STOPfiles; no active run remains.

**Decision: retain the implemented mechanisms experimentally OFF; revise the claim declaration/release integration before promotion.** The next authorized work should isolate correct raw prose lost by typed-field/receipt compatibility and distinguish unsupported/malformed declarations from genuine source contradiction, without another planner, universal semantic verifier or wording guards. Then use a new small frozen holdout, not rescore this cohort. Stop this task here; no broad Phase G benchmark or automatic activation.
