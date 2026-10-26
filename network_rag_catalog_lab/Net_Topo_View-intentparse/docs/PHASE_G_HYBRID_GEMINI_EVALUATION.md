# Controlled hybrid Qwen + Gemini evaluation — 2026-10-25

**Decision: RETAIN EXPERIMENTAL, disabled for ordinary users. Stop this bounded experiment.** Gemini shows meaningful improvement on selected preserved evidence packets, but cloud availability, gateway advisory composition and complete workflow coverage are inadequate for promotion. This experiment closes no G4, G5, G6 or G11 acceptance gate.

## Credential, model and actual connection

The existing ignored `backend/.env` contains exactly one `GEMINI_API_KEY` entry. Fresh backend loading accesses it. The credential is absent from tracked/staged diffs, this audit's text artifacts, and this report. No secret backup was created. Root `.env` contains no duplicate credential value. Google's real model-list request authenticates with HTTP200.

Discovery is not generation permission: the listed `gemini-2.5-flash` returns404 saying it is unavailable to new users. The actually working model is **`gemini-3.8-flash`**, through the official stateless **Interactions REST API**. A real synthetic connectivity request returned `COGNISHIELD_READY`, HTTP200, in59.56seconds, using10 input/6 output tokens. Previous30/60second generateContent timeouts remain archived. No SDK installation or additional model download was needed; REST uses the existing httpx dependency. The legacy SDK-only provider remains separate and was not selected.

Real calls used API-key headers, `store:false`, temperature0 and thinking level `low`. No remote tools, remote conversation identity, user credentials in prompts, or ordinary application content were sent. Google's storage/data-use policies remain those of the account; `store:false` is not a claim that Google never processes or logs data.

Official references: [Interactions](https://ai.google.dev/gemini-api/docs/interactions-overview), [thinking controls](https://ai.google.dev/gemini-api/docs/thinking), [pricing](https://ai.google.dev/gemini-api/docs/pricing).

## Frozen direct comparison

Six distinct, exposed synthetic conditions were frozen before Gemini inference, reusing exact preserved user instructions, context, evidence identities and JSON schemas from earlier Qwen runs. Baseline raw Qwen answers are reused, not regenerated or repaired. Original source hashes, credential-free wire packets, raw answers, usage and complete-answer review are preserved under `tmp/phase-g/iterations/20261025-hybrid-gemini-resume/packets`, `direct`, and `direct-full-answer-review.json`.

| Case | Condition | Preserved Qwen2.5 | Raw Gemini | Reasoning credit |
|---|---|---|---|---|
| H01 | Route present, down egress, failed forward/return | Inadequate | Qualified adequate | Correct dependency/causal interpretation; simulated/calculated scope |
| H02 | Two intended links and correct device/port ownership | Inadequate | Adequate | Factual relationship binding; no causal credit |
| H03 | Saved commands plus unavailable syslog | Inadequate | Qualified adequate | Both outcomes and absence-of-evidence limit; not novel diagnosis |
| H04 | Published OSPF requirements versus saved CLI | Inadequate | Adequate | Actual field mapping and remaining vendor/current-state/validation limitations |
| H05 | Interface states plus failed-hop explanation | Inadequate | Adequate | Both clauses and correct causal relationship |
| H06 | Contextual recommendations without collection | Inadequate | Qualified adequate | Concrete unexecuted read-only questions; no unique-best-check claim |

**Selected-case adequacy: Gemini6/6 versus historical Qwen0/6; three Gemini results carry explicit scope qualifications.** Only H01/H05 test causal interpretation, and their source already includes calculated forwarding results. This demonstrates interpretation of those records, not independent discovery of arbitrary root causes. Fact repetition, JSON validity, fallback and source retrieval receive no causal-reasoning credit. Review was performed by the implementation assistant against the frozen records, not a blinded external reviewer.

Gemini6/6 completed with schema-valid JSON,4.29–31.04seconds (median7.00seconds), and135–334 final output tokens. No repair or factual fallback was used in this direct arm. One phrase in H03 about zero log records must be read as zero **returned** observations, not proof that no events occurred. H06 lacks destination/service scope, so its recommendations are useful candidates rather than a certified optimal sequence.

Declared comparison limitation: Gemini allowed2048 output tokens, Qwen512. All completed Gemini answers fit within334 tokens; the selected Qwen baseline failures ended normally below512. This reduces a truncation explanation, but does not turn the comparison into a perfectly controlled model-only or unseen-generalization experiment. The original Qwen results and prior frozen Phase G scores are unchanged.

## Existing gateway integration and real API results

The integration reuses Shared Gateway → existing SemanticRoute/IntentPlan → LangGraph authorized readers → existing evidence projection → existing synthesis/verification. No second planner, RAG, source store, renderer or engineering authority was added. Both assistant surfaces use the existing authenticated API router with disposable synthetic SQLite and real Ollama/Gemini calls. This was **authenticated ASGI API testing, not browser acceptance**; no frontend or browser storage was touched.

Twelve gateway executions span10 case IDs, including duplicate surfaces, one injected failure and two corrective reruns. They are not12 independent generalization conditions. The original failures remain beside their corrected runs. Detailed separate workflow/source/evidence/reasoning/release/task grades and raw-to-final comparisons are in `docs/evaluations/phase_g_hybrid_gemini_result.json` and the ignored `gateway-full-answer-review.json`.

| Journey | Actual result | End-to-end seconds | Attribution |
|---|---|---:|---|
| Floating route/down-interface explanation | Correct causal core, scope-overstatement warning |64.70| Gemini synthesis; scope footer is deterministic |
| Studio route/down-interface explanation | Adequate explanation; unnecessary knowledge reader |83.84| Gemini synthesis; G4 reader efficiency not passed |
| Floating saved configuration + unavailable logs, original | Safe records after cloud timeout |94.18| Fallback, not completed reasoning |
| Studio same compound question, original | Adequate explanation preserving both sources |25.57| Gemini synthesis after local-plan fallback |
| Floating arithmetic |133, no readers/cloud |8.25| Local Qwen |
| Studio arithmetic |20, no readers/cloud |4.53| Local Qwen |
| Injected cloud429 | Safe factual fallback, no hidden causal retry |4.25| Mocked quota failure only; not actual quota evidence |
| Floating compound corrected rerun | Adequate answer; planning got real demand503 |72.58| Gemini synthesis, original failure not replaced |
| Studio compound corrected rerun | Planning and synthesis timeouts; safe records |118.03| Fallback, incomplete task |
| Studio published requirements + saved CLI | Correct two readers, cloud timeout, incomplete mapping |94.80| Fallback; direct H04 success is not gateway acceptance |
| Floating topology relationships | Local Qwen swapped peers; verifier rejected, exact table |15.28| Factual fallback, no Qwen reasoning credit |
| Floating ask-next follow-up | Unrequested telemetry read, no advisory deliverable |6.78| Existing workflow failure; not repaired by switching synthesis model |

Of seven **real cloud synthesis calls**, four completed and three timed out. Completed cloud responses were valid JSON. For all four, the model's raw answer equals the verifier's candidate and remains an exact prefix of the released answer. Two causal answers gained only a192-character server-owned scope footer; the two compound explanations were released unchanged. There is no evidence of framework corruption of those completed Gemini interpretations.

One completed Floating causal answer says “complete traffic disruption” despite a scoped ICMP forwarding record. The added footer discloses the actual test scope but does not universally certify the prose. It is scored as a partial/scope-warning result, not unconditional complete-task success. The Studio causal answer is adequate but source selection includes unrequested knowledge. Raw text, literal-check acceptance and reviewer task adequacy remain separate.

Remote G4 refinement is **not verified**. Two initial calls failed400 because the adapter used chat-role objects where Interactions requires typed `user_input`/`model_output` steps. That general API mapping was corrected, preserving every original message and schema. The two corrected actual planning calls then produced one explicit high-demand503 and one30-second timeout, not completed semantic decisions. The optional refinement flag stays0. No prompt tuning or new planner was introduced.

Two remaining integration limitations are deliberately retained: with Approach A off, the existing advisory request can bypass composition and read telemetry; a single-reader topology lookup remains local and can fall back after Qwen relationship errors. The new provider cannot fix those pathways merely by existing. This bounded task did not restart the Approach A/B architecture work.

## Authorization, model selection and deadline budget

Ordinary root `.env` now explicitly selects **`qwen2.5:1.5b`**, replacing `auto` as requested. A fresh real runtime query confirms Qwen2.5 active; Qwen3.5 remains installed. The ordinary backend was not restarted, so this verifies fresh-process configuration rather than a reloaded running server.

All new flags default off in `.env.example`:

```dotenv
COGNISHIELD_AI_HYBRID=0
GEMINI_MODEL=gemini-3.8-flash
COGNISHIELD_AI_HYBRID_SECONDS=120
COGNISHIELD_AI_HYBRID_CALLS=1
COGNISHIELD_AI_HYBRID_INTERPRET=0
```

`COGNISHIELD_AI_OUTCOMES` remains0. Setting the hybrid flag alone is insufficient: remote admission also requires an ephemeral **server-owned approval of the exact owner, surface, conversation, complete request and owned-history digest**, an active synthetic scenario, no editor/related-editor/upload context, and simulated/published evidence provenance. No client flag or checkpoint grants that approval. The evaluator creates those approvals in its disposable database object; no ordinary user-facing cloud activation or GUI selector was added.

Simple chat, arithmetic and ordinary single-source facts stay local. Complex synthesis is selected using existing validated plan/outcome information, not a new complexity classifier. Optional remote interpretation refines the same schema and is subject to the same existing plan validation; it is disabled by default.

An approved experimental request has one monotonic deadline capped at120seconds from gateway entry. Local model stages remain capped30seconds. Optional remote planning is capped30seconds and reserves45seconds. Synthesis is capped90seconds and leaves2seconds for finalization, or less if the request clock requires. Cloud concurrency is1 and queue time consumes the same budget. Default maximum is one remote call; a separately enabled planning experiment permits at most two. No retry loop is added. Authentication/permission/billing/not-found/quota errors latch out further provider calls within the request. Completed remote synthesis, provider failure and semantic rejection are distinct; a failed remote interpretation does not become a network fact. Remote synthesis never triggers a hidden local causal rewrite.

All measured gateway requests returned below120seconds, but several did so with incomplete factual fallback. Deadline compliance is not task success. Simple cases met30seconds; successful complex model-written explanations took25.57–83.84seconds. The118.03second timeout result demonstrates the shared budget, not usable complex reasoning. Google cold/warm model residency is not observable here; the59.56second initial connectivity probe and later durations are reported as sequence observations, not a controlled cold/warm comparison.

## Usage, quota, billing and safety

Known successful responses across the connectivity probe, six direct packets and four completed gateway generations report **21,815 input tokens,2,709 output tokens,0 thought tokens and0 cached tokens**. At Google's published standard paid prices of$0.75/M input and$3.75/M output, the known-usage estimate is **$0.02652**. This is not an account invoice or total-charge guarantee: failed/timed-out generations can incur additional unreported usage, and account free-tier/discount/billing status was not queried. No actual401/403/429/billing error was observed. One429 was intentionally injected; real503 explicitly reported high demand.

Data access, exact facts, source receipts and limited network calculations remain authoritative. Gemini receives no SSH, SQL, file-write, publication or deployment tool. V9 schema/template/target/review authority is unchanged. Existing factual verification remains limited and cannot certify every causal sentence. This report does not label literal checks as universal semantic validation.

## Source changes and focused tests

- `backend/llm/gemini_provider.py`: official stateless REST transport and ephemeral approved-request scope in the existing provider domain; error redaction, bounded calls/deadline, source/complexity admission and metadata.
- `backend/llm/gateway.py`: activate the approved scope around the existing request and record separate hybrid diagnostics; unapproved/default-off behavior retains existing path.
- `backend/llm/orchestration/model.py`: existing local planner with optional same-schema interpretation, selective cloud synthesis, existing count/input budgets, no hidden repair.
- `backend/llm/orchestration/engine.py`: existing graph uses the request clock, admits synthesis only after authorized evidence, and reports local512/cloud2048 allowances.
- `.env.example`: explicit Qwen baseline and disabled experimental settings. Root `.env` only pins the local model; credential stays in ignored `backend/.env`.
- `backend/tests/test_phase_g_hybrid.py`, `backend/scripts/evaluate_phase_g_gemini_hybrid.py`, `backend/scripts/evaluate_phase_g_hybrid_gateway.py`: focused synthetic policy/transport tests and explicit bounded evaluators.

Latest hybrid plus existing model-diagnostics suite: **19 PASS** (overlapping earlier16/17 runs are not added). The affected shared gateway/network/intelligence/B3 suite produced **97 PASS,1 FAIL** in18.15seconds. The failure is the legacy editing test expecting a proposal but receiving clarification; it also reproduces using the saved exact pre-hybrid gateway. Its mocked routing-response sequence no longer matches the existing deterministic edit route. This is retained as a pre-existing regression/test-contract discrepancy, not hidden or fixed in this experiment. Original outputs and the pre-hybrid reproduction are archived.

API tests include actual owner-isolation rejection. Unit checks cover exact request/history/owner/surface approvals, private-context exclusion, source provenance, simple-local behavior, shared budget/call limits, few-shot schema/message preservation, error redaction, quota latch, incomplete generation and no hidden local repair. They verify implementation safeguards, not model intelligence.

## Preservation, rollback and next decision

Final read-only checks confirm unchanged HEAD93f5f45, staged index, ordinary SQLite tables (integrity ok), active release `7a14a351e52b49aeb87f65d1192f0937` and all341 immutable artifacts. No UI/editor operation, saved buffer, normal conversation, server restart, model download, commit, staging, publication or deployment occurred. No new browser/OS-clipboard pass is claimed. Exact proof: `tmp/phase-g/iterations/20261025-hybrid-gemini-resume/preservation-after.json`.

Immediate rollback is to leave/set `COGNISHIELD_AI_HYBRID=0` and remove ephemeral evaluation approvals; ordinary defaults already do this. Keep the requested explicit Qwen2.5 baseline. No schema migration or knowledge rollback is needed. `tmp/phase-g/iterations/20261025-hybrid-gemini-resume/hybrid-only.patch` records only this integration relative to the pre-experiment dirty sources, and `pre-hybrid-source` retains those nonsecret source versions. Review incremental reversal against current hashes before applying it; do not reset the repository or overwrite later/user changes. Root `.env` and secret files are not backed up in this patch.

**Retain the disabled implementation for further authorized synthetic testing. Do not promote it or declare broader Phase G reasoning acceptance.** A next separately authorized task should establish reliable cloud availability/structured planning and address the existing advisory composition boundary; no universal verifier, Approach B, model download or broad benchmark is justified by this small run alone. This task stops at this checkpoint.
