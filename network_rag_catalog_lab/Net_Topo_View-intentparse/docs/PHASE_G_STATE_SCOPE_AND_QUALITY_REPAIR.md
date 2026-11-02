# Phase G — State scope and remaining quality repair

2026-10-29. **Bounded repair complete; reasoning qualification remains incomplete.** Audit: `tmp/phase-g/iterations/20261029-state-scope-repair/`. Completeness, Approach A and the previous harness remain OFF by default. Previous scores, including4/8versus4/8, remain frozen.

## Stage 0 — Current boundary before editing

The retained repairs are current-request routing eligibility, singular/plural address recognition, consecutive running-history comparisons, and independent core/auxiliary claim release. The preceding eight-task experiment and both browser checks are complete and stopped. Its exact results and raw traces are preserved in the reliable-investigation audit, alongside earlier original MN and qualification evidence.

`preservation-before.json` records HEAD/staged entries, ordinary tables, knowledge artifacts, current source hashes and429historical JSON records. `state-scope-before.json` preserves the exact failed query and six returned rows. At that preservation boundary, no new cloud inference had run.

Confirmed first loss: `SemanticRoute.interface_refs` and retrieval metadata retain7031; `network_context` forwards that override only for telemetry. `NetworkReader.read` also rejects interface scoping for all other domains. Finally, `ScenarioManager.result` filters interface references only on telemetry. Fixing the caller alone would therefore produce an unsupported-reader result; fixing the reader alone would still receive an unrestricted query.

The six rows are not six identical observations. Three authored observations and three model-derived interface observations have distinct record identities and provenance. Correct one-interface scoping should retain the two legitimate observations for that interface. Exact repeated source records may be deduplicated; equal values across different identities/sources/times must not be collapsed. The current factual table hides record/source identities, making distinct observations look redundant.

Intended coherent change: extend the existing state-reader scope contract, validate canonical IDs against the selected devices/current scenario, propagate scope through the existing adapter, filter records before limit/projection, preserve related typed records and all provenance, and expose record/source identity in the existing factual renderer. No new router, database, planner or verifier.

## Gates

- [x] Stage0 preservation/reconciliation and exact failed receipt.
- [x] Stage1 positive/negative source regressions; both authenticated gateways and actual browser paths respect interface scope.
- [x] Stage2 distinguish evidence/projection/interpretation/evaluation causes for temporal and advisory failures; independent fixture/expectations.
- [x] Stage3 inspect actual provider JSON configuration, raw malformed response and supported bounded repair options; preserve strict core validation.
- [x] Stage4 freeze/run small matched end-to-end checks only after preceding focused gates.
- [x] Stage5 browser, quota, preserved state and stopped disposable services.
- [x] Stage6 final findings, decisions and exact continuation.

Diagnosis and validation are complete with the limitations below. Only reader-scope and source-policy behavior are accepted; reasoning quality and native-schema compatibility remain open. No original Phase G stage closes from this task.

## Focused diagnosis and decisions

Stage1 is verified by `stage1-acceptance.json`, seven real scoped state invocations, both authenticated surfaces and actual browser controls. The late direct-role binding correction is covered by focused graph tests; its real-Gemini check is part of the bounded cohort, not assumed from mocks.

The independent temporal fixture `SCOPE-TIME-812` has running description/MTU changes, an unapplied staged shutdown, an applied MTU event04:20 and operational observations03:50up/04:50down. The first actual answer correctly preserves that distinction and the strongest observation bracket. No temporal prompt or validator change was needed. RI04 remains historically PARTIAL; no old score is changed.

Advisory RI08 is a model interpretation limitation: correct owned context and explicit no-read instructions reach the reasoner, but it overstates what counters establish. The new initial advisory attempt failed at planning with503UNAVAILABLE. A separately authorized diagnostic completed with zero reads and correct owned references, but still overstates causal separation from generic error counters. This remains PARTIAL, not a repaired reasoning success. Existing instructions already require discriminating checks and qualified causes, so another wording guard is not justified.

RI07's whole malformed JSON cannot be repaired by ignoring auxiliary claims. Current transport requests JSON MIME and app-validates the full core; the exact native-schema probe returned400INVALID_ARGUMENT before inference. The provider supplied no detailed reason. Native schema support exists officially but this particular schema is not demonstrated compatible. Keep strict rejection and explicit incomplete results; no unsafe JSON salvage, model change or automatic transport retry. Offline tests cover valid quoted prose, whole malformed JSON, invalid core/query/source types and independent auxiliary diagnostics.

The consolidated focused suite passes87tests. Earlier OS-temp permission errors and deep SQLite backup-path failures are retained; a fresh shorter workspace temp directory passes. No prompts, provider implementation, model roles, production schema, dependencies or defaults changed. Detailed classifications and trace paths: `stage2-3-findings.json`.

## Final application changes

| Component | Minimal correction |
|---|---|
| `gateway_network.py` | Forward canonical interface references for state as well as telemetry. Validate IDs against selected devices/current scenario; invalid/unknown/wrong-owner references do not widen. Existing state filtering matches direct records and typed relationship context before limiting. Deduplicate only exact identified records, retaining distinct source/time/value observations. |
| `local_providers/development.py` | Apply the same existing-reader scope to authored and modeled state results before sorting/limiting. No ordinary SQLite writes or new store. |
| `gateway_findings.py` | Show record/source identity in the factual state renderer so distinct authored/model observations are inspectable. |
| `orchestration/engine.py` | Preserve server-resolved device/interface subjects through direct approved role planning. Original explicit reader restrictions take precedence over domains inferred by the reference resolver. |
| `gateway_routing.py` | Apply the existing source-policy contract before exact-attribute fast paths and fallback; a requested prefix is not permission to substitute inventory for state. Correct state-only plans survive; plans adding prohibited sources still reject/fall back safely. |
| Existing evaluator | Add an opt-in diagnostic `--state-scope-reference` parameter ablation. It disables only the adapter override and uses actual auth, readers and providers. It is not a historical-code baseline and does not fabricate tool output. |

The source-policy defect was discovered **after** freezing the paired cohort. Both original narrow plans correctly chose state; the server falsely compared them with inventory inferred while resolving attributes. `boundary-before.xml` and `local-source-policy.log` preserve those reproductions. Explicit policy is now the single authority in those paths. No prompt tuning or new planner was added.

Latest validation:115affected tests passed before the final ordinary-route boundary normalization;49targeted local-policy/graph/scope tests passed after it. Earlier127source/network checks and87focused checks overlap and are not summed. The15new transport controls cover both modes, quoted valid prose, malformed whole JSON, invalid decisions/queries/source types, auxiliary-only errors and native400 no-retry behavior. Tests use disposable databases; original OS-temp/deep-backup failures are retained beside the successful short-path reruns.

## Frozen comparison and separate correction evidence

Registry: `docs/evaluations/phase_g_state_scope_matched_v1.json`; SHA256 `b949106843bff90f532a6a60208bd0a7300d7253d0f4815ed26831834c0c749c`. Four paired real gateway conditions plus one offline transport control. Reused authorized synthetic worlds and source-derived expectations, implementation-assistant graded; not blinded or an unseen-world benchmark.

| Condition | Parameter-loss reference | Initially repaired arm | First failure boundary |
|---|---|---|---|
| Narrow interface state | Framework rejection | Framework rejection | Correct state-only plans falsely rejected by the shared source-policy/identity-domain check; repaired separately, original scores retained. |
| Broad multi-device investigation | PARTIAL | PARTIAL | Evidence and relationships present, but model calls simulated operational state an established physical/operational cause. Repaired arm also adds an unnecessary knowledge read. |
| Temporal captures/events | QUALIFIED ADEQUATE | PARTIAL | The latter answer attributes WAN-B to the unobserved02:00 staged time. Correct interval/event sections do not excuse that unsupported historical value. |
| No-read advisory | Provider timeout | Provider timeout | Planning noncompletion at about90seconds, zero new readers; no reasoning judgment. |
| Offline JSON/provider control | PASS | PASS | Strict core retained in both modes; no real malformed cloud response invented for credit. |

Frozen complete-task results are **1/4 versus0/4**. This does not establish a causal quality regression from interface scoping: the narrow check never executed, model sampling/planning differ, and the experiment is small. It demonstrates **no quality advancement**. Earlier4/8versus4/8 and every original score remain unchanged.

After the shared source-policy correction, the same narrow diagnostic reaches the actual state reader. Reference arguments contain `interface_refs=[]` and return7records; repaired arguments contain `['7031']` and return3records: `port-7031`, `model-interface-7031`, and the whole related `model-table-703-default` routing artifact. Both answers explain the two source-distinct interface observations correctly. The repair earns reader-scope credit, not causal reasoning or new generalization credit. Exact `interface_state` queries return only the two observations. Related typed context is retained whole rather than sliced into a misleading relationship.

## Actual browser acceptance

Earlier Stage1 real browser queries in **both assistants** prove canonical interface scope and two distinct state observations; authenticated API checks also cover owned follow-ups and local arithmetic42without network reads/cloud. Reuse is explicit and not counted as new unique cases.

Four further browser-originated turns were completed through actual controls and exact synthetic cloud consent. Studio and Floating temporal answers correctly preserve running/staged values, the03:50–04:50 observation bracket and recorded04:20event without establishing an exact operational transition/physical cause. Studio used two synthesis calls; this is not claimed as a one-shot success. Valid final model prose survives release unchanged. Studio's advisory makes zero reads but still overstates what persistent line-rate utilization establishes about queuing; it remains PARTIAL. Floating's advisory returns503UNAVAILABLE with zero reads and no completed reasoning; no retry was made. Raw inputs/outputs, read receipts, reviews and final answers are archived in `policy-diagnostic-repaired/browser-traces.json` and `browser-acceptance.json`.

The old tab reached a connection-error data URL before Vite was ready. Browser policy then blocked operations on that URL. A fresh same-origin IAB tab loaded successfully. In the scaled view, mouse locator clicks mis-targeted controls; keyboard activation produced verified intended submissions. No browser settings/profile/security changes were made. Two unsaved native VLAN tabs remain; no editor/change/Accept/Save/Deploy action was used. No stronger full-buffer hash claim is made. Disposable5174/8001services are stopped; ordinary5173/8000were untouched.

## Provider, quota, preservation and decision

32cloud attempts:27HTTP200,2HTTP503,1HTTP400and2no-response timeouts. A separate sandbox connectivity attempt produced no provider response and is preserved. Actual returned usage totals292216input/23995answer/3313thinking tokens. The shared persistent ledger peaks at8requests and120966accounted input tokens per61seconds;96rolling-day reservations, below15RPM/150KinputTPM/500RPD. Reservations may include nonresponses; no billing/cost claim or hidden retry. Existing experimental360second/5role-call/3round/24reader limits were retained, not increased; this is not acceptance of ordinary120second latency. Frozen tasks ended within about91seconds, including failures.

Preservation PASS: HEAD/index unchanged, all41ordinary tables unchanged,1923knowledge files including active341artifacts unchanged,429historical JSON records unchanged, ignored `backend/.env` and preexisting dirty root `.env` byte-identical. Active V9 release remains `7a14a351e52b49aeb87f65d1192f0937`. No credentials occur in scanned audit text. Qwen2.5local, Gemini3.1planner, Gemini3.5reasoner and their current roles are unchanged. Completeness, Approach A, previous harness and legacy optional interpretation remain OFF by default. No schema migration, dependency, publication, stage, commit, push, deployment or device action.

**RETAIN the scope and explicit-source-policy repairs. KEEP completeness OFF.** Root-cause classifications: interface loss and false source-policy rejection were architectural defects; ambiguous temporal/physical/advisory explanations remain model interpretation limitations with complete operands; RI07 is malformed provider JSON and native-schema compatibility remains unresolved;503/timeouts are provider noncompletions. Correct event/observation grading must remain distinct, with no historical rescore. There is no basis to claim whole-system intelligence improvement or close G4/G5/G6/G11.

Next work should be separately authorized and bounded around model-quality/release limitations and supported provider schema compatibility. Do not start another exposed-prompt guard loop or broad benchmark from this checkpoint.

Rollback/recovery: no data migrations or release changes need reversal. Keep the three experiment flags OFF for ordinary operation. To reverse code, review only the scoped changes in the five application modules and corresponding tests; do not `git reset`, restore whole dirty files, or undo the preceding continuity/running-history/claim-release repairs. The evaluator ablation flag is test-only and must not be used by application launchers. Exact schemas, messages, failed outputs, source revisions and comparison freezes remain in the audit for reproduction.

Final housekeeping: syntax validation PASS; no running disposable turns;5174/8001closed. Whitespace check PASS with CRLF recognized as line endings (per-command setting only, no Git configuration or file-format rewrite). The read-only final historical/index/HEAD recheck also passes.
