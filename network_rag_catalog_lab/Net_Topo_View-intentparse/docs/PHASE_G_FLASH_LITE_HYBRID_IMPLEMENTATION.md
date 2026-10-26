# Flash-Lite hybrid replacement — 2026-10-26

**HYBRID PARTIAL. Retain the scoped experimental provider; Approach A: KEEP DISABLED.**

The generateContent adapter, exact-message cloud consent and synthetic-source authorization work through the real authenticated Floating and Studio gateway. Simple positive controls remain local. Meaningful blocked-egress, ownership and unavailable-source explanations work in selected cases. Remaining routing, local-Qwen factual, outcome-projection and interpretation failures prevent a broader quality claim. No Phase G stage is closed by this experiment.

## Effective configuration and credential

The existing ignored backend/.env was preserved byte-for-byte. It has exactly one GEMINI_API_KEY entry, and fresh backend processes loaded it successfully. No credential value was copied into source, reports, request traces or backups. Root .env loads first, then backend/.env, both override=False; process environment remains authoritative. Git ignores backend/.env and the runtime usage ledger.

Root .env now explicitly selects:

    COGNISHIELD_LOCAL_OLLAMA_MODEL=qwen2.5:1.5b
    GEMINI_MODEL=gemini-3.5-flash-lite
    COGNISHIELD_AI_HYBRID=1
    COGNISHIELD_AI_HYBRID_SECONDS=120
    COGNISHIELD_AI_HYBRID_CALLS=1
    COGNISHIELD_AI_HYBRID_INTERPRET=0
    COGNISHIELD_AI_OUTCOMES=0
    COGNISHIELD_AI_HYBRID_THINKING=low
    COGNISHIELD_AI_HYBRID_OUTPUT_TOKENS=8192
    COGNISHIELD_AI_HYBRID_RPM=15
    COGNISHIELD_AI_HYBRID_INPUT_TPM=250000
    COGNISHIELD_AI_HYBRID_RPD=500

Nine reviewed content digests are operator-allowlisted: three frozen evaluation variants and the six existing C1 scenario definitions. The digest seals the entire canonical scenario plus activated source pack. Editing source bytes/revision invalidates approval. IDs alone and model-generated content cannot enable remote inference. Root .env.example stays hybrid0 with an empty allowlist. Ordinary sources/scenario selection were not changed. Gemini3.8 remains explicit rollback only; zero new3.8 requests were made.

Actual fresh test-backend processes recorded qwen2.5:1.5b, gemini-3.5-flash-lite, hybrid1, planning0, the isolated DB and a loaded credential. Approach A was toggled only in the separate disposable ON process; root remains0. The ordinary 5173/8000 pair was not started/restarted; no application or browser state was migrated for this experiment.

## Integrated changes

- backend/llm/gemini_provider.py: one existing provider domain supports model-specific transports, full schema validation, completion/usage parsing, safe error categories, request clock, one concurrent cloud call and persistent bounded quota accounting. Flash-Lite uses official generateContent contents, systemInstruction, responseJsonSchema and thinkingLevel=low. Thought parts do not become final answers. Gemini3.8 keeps typed Interactions history/storefalse.
- backend/llm/gateway_api.py: strict authenticated hybrid-context and owner approval endpoints. Approval binds owner, surface, conversation, exact request and current owned history, expires after120seconds and is consumed once. Auditors/other owners, stale revisions, private history, editor context and uploaded files cannot opt in.
- backend/llm/orchestration/engine.py: existing outcome-advisory branch may select the approved provider; no new planner, tools or state authority. It did not repair Approach A's advisory failure.
- backend/llm/orchestration/synthesis.py: existing narrow flow check rejects an already-traversed incoming edge being labelled the blocked egress and unsupported forward-to-return sequencing. Source labels survive published-contract rebinding. A separately labelled server validation-boundary footer distinguishes mapping from V9 compatibility/full parameter validation and historical capture from current activation. This does not certify arbitrary prose.
- frontend/src/services/ai.ts, frontend/components/SharedInventoryChat.tsx and frontend/components/ansible/AnsibleChatPanel.tsx: separate Cloud · synthetic action obtains exact-message consent before the normal turn API. Ordinary Enter/Send remains local. Studio cloud requests do not snapshot the editor or related buffers; uploads/selections disable that action.
- .env.example and ignored root .env: existing configuration conventions only; no new credential store or dependency.
- backend/tests/test_phase_g_flash_lite_provider.py and test_phase_g_hybrid.py: transport/schema/error/owner/revision/quota/relationship positive and negative regressions, including explicit mocked3.8 rollback.
- backend/tests/test_shared_ai.py: repaired an outdated authorization test fixture. The instruction now explicitly binds the active unsaved file; its first mocked inference is the patch, not a classifier response. Exact-base proposal, unsaved-comment and unchanged saved-file assertions remain.
- backend/scripts/evaluate_phase_g_flash_lite_integration.py and docs/evaluations/phase_g_flash_lite_integration_v1.json: frozen synthetic two-arm real-HTTP evaluation plus separately labelled failure injection.

No V9, source registry, model registry, SQLite schema or planner replacement was introduced. Existing deterministic calculations, exact-base editing, authorization and review authority remain in place.

## Connectivity, schema and quota results

One real small provider connectivity call passed: STOP, valid unchanged JSON schema,1.168seconds,16input/13finaltokens. Fourteen subsequent real cloud synthesis calls completed, seven per paired arm. All14 parsed against the unchanged application schema. No cloud timeout, incomplete generation, HTTP429,500/503, authentication or billing error occurred in this small real cohort. Schema success is not factual success.

Total real cloud usage:15 inference requests,24,358input and3,242final tokens. Reported thought-token count was0; low was sent and accepted, but internal thinking depth is not independently observable. Output cap8192 is an explicit bounded cloud allowance, not a change to local Qwen's512. No result approached that cap.

Cloud median inference: OFF1.851seconds, ON1.841seconds; observed range1.465–2.271seconds. End-to-end turn POSTs, including local planning/tools/composition (separate consent/context HTTP timings and GUI latency are not included): OFF0.252/9.768/61.332seconds minimum/median/maximum; ON0.173/13.736/55.111seconds. All22 requests stayed below120seconds; OFF's long case ended in local synthesis fallback, not useful model success. Google cold/warm residency and other account-client usage were not measurable.

A final focused Unicode-byte reservation check passed alongside provider regressions. Input pacing reserves serialized UTF-8 bytes before dispatch and records returned input tokens afterward; this is a conservative local estimate, not an account-wide tokenizer. The shared runtime ledger observed at most4 reservations/61seconds, including injected failures conservatively reserved without reaching Google. Caps cannot exceed15RPM/250K inputTPM/500RPD and can be lowered. One cloud semaphore and a cross-process file lock prevent concurrent ledger oversubscription. Quota waits consume the same request clock; requests that cannot fit are rejected before dispatch. The ledger is local enforcement, not proof of account-wide remaining quota or future availability. No billing was activated and no invoice cost is inferred from token counts.

## Frozen paired acceptance review

Expectations were source-derived and checked before inference. This is a small controlled integration cohort using familiar failure families with changed synthetic names/addresses, not an unseen intelligence benchmark. Seven conversations per arm contain11turns; C7 duplicates C2's first condition across surfaces and adds no generalization credit. Prompts/settings/scenario bytes match between arms. Existing H01–H06 records and scores remain unchanged.

| Criterion | Approach A OFF | Approach A ON |
|---|---:|---:|
| Full-task adequate, including qualified C1 ON record presentation | 7/11 | 4/11 |
| Excluding duplicate C7 condition | 6/10 | 4/10 |
| Workflow/source-scope correct | 10/11 | 9/11 |
| Necessary evidence delivered to reader/model path | 10/11 | 10/11 |
| Completed cloud calls / unchanged schema valid | 7/7 | 7/7 |
| Correct raw cloud interpretation, separate from final task | 5/7 | 5/7 |
| Adequate causal cloud explanation | C2 and repeated C7 | neither; false conflict claim |

The raw cloud interpretation count includes factual mapping, source-limit and relationship explanations; it is not a causal-reasoning score. Arithmetic and exact inventory projection earn no network-reasoning credit. Raw correctness is not retained-answer correctness: ON's correct mapping is lost in outcome projection.

- C1 OFF returns actual saved commands and correctly explains unavailable syslog. Its next no-read advisory request nevertheless invokes inventory/state, losing the original source limitation. ON performs no reads but fails to produce the recommendations; its first answer duplicates factual sections.
- C2/C7 OFF correctly connect Basalt-Transit ge-0/0/1.0 down/down to the declared failed forward egress, with explicit modeled scope. ON incorrectly calls distinct forward/return failures contradictory. C2's follow-up stays on local Qwen: OFF times out and returns safe tables; ON repairs into incorrect owner/interface assignments. Literal checks do not certify those prose relationships.
- C3 OFF raw Flash-Lite wrongly makes router_id vendor-required; the existing published-schema check rejects it. The factual fallback is safe but does not perform the requested mapping. ON raw mapping is correct, but outcome projection substitutes records for the explanation. Its simple quote follow-up reads knowledge unnecessarily and uses cloud; OFF stays local but Qwen falsely denies the recorded process20.
- C4 arithmetic and exact names/prefixes remain local in both arms. The interface answer is an authoritative factual projection, not model reasoning.
- C5 OFF withholds a forwarding verdict because state is unavailable and topology planned. ON also limits its conclusion but unnecessarily reads inventory despite the explicit only-state/topology instruction.
- C6 retains both intended endpoint/port pairs and correct prefixes. Supplied inventory explicitly contains the recorded up states/default VRF, so those additional facts are supported; no physical link test is established.

Machine-readable per-case workflow/evidence/model/verifier/final-answer review is in docs/evaluations/phase_g_flash_lite_hybrid_result.json. Full original and released answers, exact source identities, schemas, provider bodies and intermediate contracts remain in the ignored arm_off/arm_on traces. No headers/credential values were captured.

**Approach A remains0.** Its source receipts and structural clauses still do not establish semantic task completion. This run does not justify controlled ON retention beyond the completed disposable comparison, much less ordinary activation. No Approach B or broader outcome redesign was attempted.

## H04/H05 release handling and remaining limits

H04 remains a failed condition in the original4/6 direct-model cohort. The server can now state that mapping is not V9 target compatibility/full parameter-object validation and that historical text does not establish current activation. That added boundary receives no model credit. The C3 OFF schema error is rejected; ON still loses a correct raw mapping during projection.

H05's original wrong-hop/sequencing draft now fails the bounded relationship check. Positive H01 prose is preserved. Real OFF C2/C7 correctly locate the blocked egress. Injecting the old failure class through BOTH authenticated surfaces rejects the model conclusion and returns scoped facts, not a fabricated diagnosis. This does not prove a universal semantic verifier: ON's false-conflict reasoning and local owner/negative-configuration claims still escape selected literal checks. They are retained as failures; Approach A is disabled and no G4/G5/G6/G11 acceptance is claimed.

Optional remote G4 refinement remains0. Historical Flash-Lite structured planning had an extra-reader limitation; this task verifies synthesis transport/schema compatibility, not complete remote planning. There is no separate planner or newly granted tool authority.

## Fault, regression and browser checks

- Both actual authenticated surfaces reject other-owner/auditor approval, stale revisions and uploaded context. Focused tests additionally cover editor/private history, changed-history/body/surface binding, expiry and one-shot approval.
- Injected HTTP429: exactly one attempted cloud transport per surface, safe factual fallback, category RESOURCE_EXHAUSTED with upstream429, no hidden retry/local causal repair or3.8 substitution.
- Injected schema-valid wrong-hop/sequencing answer: both surfaces reject it and retain actual source-backed facts. These four requests made no Google inference and earn no model-quality credit.
- Both additional unapproved complex requests pass through the real Floating/Studio APIs with no cloud scope or dispatch (76.889s/48.192s); their factual fallbacks receive no model-quality credit. The security-only arithmetic continuation also exposed one irrelevant published-knowledge limitation in the OFF arm: no-cloud authorization success is not task success.
- 241 affected tests PASS after the final invalid-container/provider-error checks. The earlier239-test pass overlaps. Earlier48-provider and230-affected runs overlap and are not added. Original temp-directory, long SQLite backup filename and stale edit-test-fixture failures remain archived. TypeScript build PASS. No test thresholds/schema requirements were weakened.
- Three fresh browser operations attempted await cua.getState(); each returned: failed to write kernel assets: The system cannot find the path specified. (os error 3).
  This independently observed browser-tool initialization/assets failure occurs before selecting a website. It does not establish disabled Local browser use, website/session permission failure or local-server connectivity. No browser GUI acceptance or editor-buffer hash check is claimed. No native/browser storage was modified.
- Real authenticated HTTP used the same gateway router/AIGateway/LangGraph/services on one disposable port8001 listener, stopped after every run. It was not a mock HTTP200 harness and did not replace the ordinary backend. The ordinary5173/8000 listeners were absent at the final check; they were not started against protected data.

## Use, enable and rollback

1. Start the existing standard local launcher on5173/8000 after reviewing the configuration; this task did not start it against the ordinary database.
2. In the existing Development Network workbench, explicitly activate a reviewed scenario such as an unchanged C1 library scenario. Do not replace ordinary inventory. Hybrid eligibility requires its exact scenario/source-pack digest in COGNISHIELD_AI_HYBRID_SCENARIOS; an edited/custom variant stays ineligible until an operator reviews its complete content and updates that allowlist.
3. Use a new synthetic-only Floating or Studio conversation. Ordinary Send/Enter stays local. Cloud · synthetic approves this exact message and eligible owned history to Google. Studio excludes automatic editor/related-buffer snapshots; attachments and mixed private histories are denied.
4. An eligible approved message still uses Qwen for simple tasks; existing validated multi-source/comparison/investigation information selects remote synthesis. A cloud button is not blanket authorization, a workflow success guarantee or permission to execute tools. No-read follow-ups and exact saved-config Qwen answers have documented limitations above.
5. Immediate local-only rollback: set COGNISHIELD_AI_HYBRID=0 in root .env or the backend process environment and restart the backend. Keep the credential in its ignored backend/.env; do not delete or duplicate it. Keep COGNISHIELD_AI_OUTCOMES=0 and COGNISHIELD_AI_HYBRID_INTERPRET=0.
6. Explicit cloud rollback, only when wanted: set GEMINI_MODEL=gemini-3.8-flash, optionally restore COGNISHIELD_AI_HYBRID_OUTPUT_TOKENS=2048, set quota ceilings appropriate to that account/model and restart. Its Interactions transport is retained and mocked regression-tested; no real3.8 quota was consumed here. Model changes are never automatic.
7. Existing content digests can be inspected through scenario_approval_context(db) on the existing development manager after operator review; do not print the environment or credential. Selection/revision changes require a fresh exact-message approval. Failed/quota requests do not silently switch providers.

## Preservation and decision

Read-only fingerprints match all42 ordinary SQLite tables; integrityok and zero foreign-key errors. GitHEAD93f5f45/index, the active7a14a351e52b49aeb87f65d1192f0937 pointer, all341 immutable artifacts and144 prior evidence files match the before snapshot. Existing dirty implementation work remains; no stage/commit/reset/publication/deployment/model download/device command occurred. backend/.env is unchanged and ignored. Protected browser buffers were not accessed.

Audit: tmp/phase-g/iterations/20261026-flash-lite-hybrid. Incremental source snapshots/patch and safe configuration/preservation records support rollback without resetting prior dirty work. No secret environment backup exists.

**Retain experimental Flash-Lite, hybrid PARTIAL; Approach A KEEP DISABLED.** Provider/authenticated API integration and selected useful reasoning are demonstrated. Browser acceptance, complete compound/advisory workflows, broad causal quality and the remaining Phase G gates are not established. Stop this bounded milestone; no automatic broader benchmark, promotion or Phase G stage closure.
