# Gemini 3.5 answer-integrity candidate — offline implementation

**IMPLEMENTED OFFLINE — NOT YET LIVE-VALIDATED.** The existing reasoner now has a single cohesive, default-OFF instruction candidate addressing answer omissions, time semantics, evidence ownership, passive advice, auxiliary consistency and JSON formatting. No additional model, call, schema, verifier or stage was added. This is an actual change to instruction assembly, not another evaluation-only deliverable.

Date: 2026-11-02, Asia/Kuala_Lumpur. Current task authority is attachment `dafdaf93-d397-42d9-b940-9eecbbe718ec`. It authorizes implementation and offline verification only. No cloud inference or new consent approval was performed.

## Application changes

1. [model_roles.py](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/model_roles.py:55): `answer_integrity_mode()` accepts only `off|candidate`, defaults OFF, and rejects invalid values with 422. Candidate mode requires the existing Google/Gemini 3.5 Flash-Lite evidence-reasoner identity. It rejects stacking with the old obligations/relationships, temporal-interpretation, timestamp-description or Approach A experiments. It does not modify any model assignment. `consent_manifest()` adds version, exact instruction and SHA256 only in candidate mode; OFF adds no fields. Changed candidate text or settings invalidates old role-bound consent. A flag alone cannot authorize inference.
2. [role_reasoning.py](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/orchestration/role_reasoning.py:22): `ANSWER_INTEGRITY_CANDIDATE` contains the instruction below. `decide()` conditionally appends it once to the existing system message immediately before the same existing model call. The old messages remain an exact prefix. Evidence packet, schema, parser, source validation and release functions are unchanged.

[AST boundary proof](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261102-answer-integrity-offline/source-boundary-proof.json) confirms that only existing `consent_manifest()` and `decide()` change, with one new mode helper and one constant. No existing classes, source-claim types, packet builder, tool authorization or other functions change. [Task-only patch](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261102-answer-integrity-offline/task-only-source.patch) is relative to the existing dirty source preimages, not Git HEAD. Both preimages are preserved in this audit. No unrelated staged or unstaged changes were reverted.

New supporting file: [test_answer_integrity_candidate.py](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/tests/test_answer_integrity_candidate.py). Other new files are audit/report material only.

## Exact final instruction

Candidate constant SHA256: `dc352a9f84350b9ea9f51fe06133eb116ac51e878de939915e72e16408900527`. It contains 2,927 characters/407 words; the two separating newlines add 2,929 system-instruction characters total. Actual tokenizer overhead, model quality, latency and API usage are NOT_MEASURED. No output-token or context-admission limit is changed.

```text
Source-grounded answer integrity

Your `answer` is the complete user-facing response. Before producing the required JSON, identify every explicit question, requested comparison, required fact, requested uncertainty explanation, and requested next diagnostic action. Address each one directly in `answer`. Do not rely on `claims`, `assessment`, `outcomes`, or other auxiliary fields to supply information omitted from `answer`. Include material source-supported values, configuration states, owners, interfaces, policies, directions, and timestamps when needed to answer the question. Be concise, but never shorten an answer by deleting a requested fact.

Interpret time by the meaning of its source field. Keep first-observed, occurred, effective-at, record-written, and captured-at times distinct. A first observation does not prove actual onset. A snapshot proves only what was observed at its capture time; absence of a change record does not establish continuity between observations. Conflicting observations remain conflicting. State verified effective changes at their effective times, and do not invent intermediate states or transitions. Compute intervals using the relevant event or observation times, not unrelated record timestamps.

Preserve evidence ownership and scope. Keep each device, interface, VRF, policy, source record, traffic class, and forward or return direction attached to its actual evidence. Distinguish modeled forwarding, filtering, and delivery from verified deployed state, physical interface status, and measured application response. Do not turn an unknown into a denial, a success, or a confirmed outage.

When the question requests a next diagnostic step, recommend the most relevant permitted passive evidence and state which unresolved uncertainty it would resolve. Do not omit the recommendation merely because current evidence is insufficient. Do not propose active changes when only read-only or passive analysis is allowed.

Make the final prose, structured claims, assessments, and outcomes mutually consistent. For `SourceClaim.timestamp`, use the cited source record's `timestamp`, or `captured_at` only if `timestamp` is absent; express event or effective time through the appropriate supported source field and value. Use only real source identifiers and schema-permitted values. Do not add unsupported claims to make the response appear complete.

Return exactly one valid JSON object conforming to the supplied schema. Quote every key and string, escape strings correctly, use valid field types, and include no Markdown fences or surrounding commentary outside the JSON object; Markdown within the `answer` string remains permitted by the existing instructions. Before finalizing, check that the `answer` covers all explicit requests, that no claim exceeds the evidence, that the JSON is valid, and that auxiliary fields do not contradict the answer. Do not output this check.
```

Only substantive adaptation from the user-proposed block: its final “no Markdown” phrase now forbids Markdown fences or surrounding commentary **outside the JSON object**, while permitting Markdown within the `answer` string as required by the existing system instructions. Removing the bold presentation markers around the heading/passive-evidence phrase is not a behavioral change. No benchmark names, times, MTU values, source IDs or topology answers enter the instruction.

This is a single suffix in one existing generation call, not an always-on critic, hidden revision call or new semantic checker. The private check is requested as generation behavior and never interpreted as an application certificate.

## OFF-path equivalence and candidate isolation

The focused tests capture `decide()` at its existing model-generation boundary using saved synthetic inputs. The model stub raises before inference; no actual completion is obtained.

- All six RC control and all six H control requests reproduce the exact frozen messages and response schemas and the current task's dirty preimages with the new flag OFF. Where compared as strings, message/schema serialization is byte-identical. Default-unset consent is also identical to the preimage.
- Candidate mode changes only the system suffix once. Original question, clauses, source record bodies/IDs, source ordering, evidence packet, user context, schema and existing synthesis purpose remain identical. Inputs remain unmutated, and packets remain below the existing 64K guard.
- Three representative pairs also pass through the actual existing Google adapter's serialization with an explicit noncredential, mocked quota function and intercepted `send`. OFF matches preimage wire bodies exactly. Candidate wire bodies differ only in the first system-instruction text, not schema or user evidence. No socket send, quota write or provider request occurs.
- All roles/settings remain unchanged: local Qwen2.5 1.5B/512 output tokens; upstream Gemini 3.1 Flash-Lite planner/2048; Gemini 3.5 Flash-Lite reasoner/8192, low thinking, validated JSON. Existing request-wide and per-role budget code remains unchanged. The capture tests retain the already-frozen 120-second experimental profile; no ordinary budget is silently increased.
- The candidate cannot be used with a configured Qwen, Gemini 3.1 or OpenAI reasoner, cannot stack older candidate flags, cannot reuse old exact-request/role consent, and does not bypass authorization when configuration alone is enabled.
- Valid saved positive answers still parse/release unchanged under the candidate wiring. Invalid JSON remains invalid; unknown authoritative sources still reject. The release-checker authority has not expanded.
- A negative wiring test deliberately returns the old H01 omission from a model stub: the omission remains. The instruction does not invent missing text or make a populated `supported` assessment correct. That test prevents a mocked old answer from being presented as proof of improved generation.

## Tests actually executed

| Run | Result | Scope |
|---|---:|---|
| Candidate + release checks | 83 passed, 3.01s | 37 new candidate checks and 46 existing release regressions |
| Affected combined run | **125 passed, 4.60s** | Above plus 23 existing timestamp and 19 interpretation checks |

Counts overlap and are not added as unique successes. [Affected log](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261102-answer-integrity-offline/affected-tests.log); [focused log](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261102-answer-integrity-offline/focused-tests-unsandboxed.log); [offline result](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261102-answer-integrity-offline/offline-result.json). No broad benchmark was run.

The first run had harness errors: an overbroad `socket.socket.connect` mock prevented Windows asyncio from constructing its local self-pipe via `socketpair`. Its isolated traceback and interrupted-run record are preserved. After that mock was removed, the sandboxed test invocation stalled before producing results; that own test session was stopped. Both completed runs were executed outside the sandbox so Windows could create its internal event-loop socketpair. Provider `send`, ordinary connection helpers, quota update and registered readers remain fail-closed mocks, except adapter serialization's own zero-network interception. No missing browser permission or application outage is inferred from those test-environment problems. These were harness changes only, not reasoner repairs or semantic failures.

## Fresh-process configuration check

A fresh Python process loaded the existing environment via `lab_config` and read only the selected flags/model configurations. It reported new flag OFF; old interpretation, timestamp and reasoning-contract flags OFF; Approach A false. Local Qwen and upstream planner/reasoner roles match the identities and budgets above. No credential value was printed, copied or placed in these traces. Both environment files were untouched.

Keep `COGNISHIELD_AI_REASONER_ANSWER_INTEGRITY` **unset or `off`**. There was no environment-file write, backend restart or ordinary activation. Candidate mode is available only for a future explicitly authorized controlled evaluation, with fresh role-bound synthetic consent. No live dispatcher, approved conversation or new provider reservation was created in this task.

## Prospective behavior, not passed quality gates

[prospective-acceptance.json](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261102-answer-integrity-offline/prospective-acceptance.json) retains hash-pinned references to the original RC/H oracles and all twelve requested criteria. The original inputs, human grades and strict/permissive readings are not rewritten.

| Condition | Required future user-facing behavior |
|---|---|
| H01 | Include MTU1500, effective08:04/record08:17/capture08:22 and source-derived delays; no measured payload-recovery inference |
| H02 | Preserve owner/time roles and reporting arithmetic; first-observed order is not proven onset/cause; retain existing ambiguity in historical scoring |
| H03 | Brook/Vale ownership, date rollover, respective6/13minute delays; later acknowledgment is not later activation |
| H04 | Both conflicting06:40captures and affirmative07:10shutdown, unknown06:55/exact transition, no measured-health claim |
| H05 | Two relevant passive artifacts with purposes, unknown neighbor despite up ports, explicit model-versus-measured-response caveat |
| H06 | Valid whole JSON, trap versus log flows, independent directions, VRF, exact ingress/egress owner and policy outcome |
| RC01 | Running versus staged artifact and unresolved activation/non-activation |
| RC02 | No08:00state inference from07:00capture/absent logs; positive verified08:25application preserved |
| RC03 | Positive forward result, return ingress denial, owned ports, VRF isolation and protocol/live limitations |
| RC04 | Actually include requested passive next-evidence advice without new collection |
| RC05 | First observed12:30, record12:31, sample12:35, five-minute observation interval; no cause/reset invention and requested passive checks |
| RC06 | Retain definite modeled egress-deny consequence and location; separate from deployed outage proof |

H05's explicit measured-response caveat is a frozen rubric requirement, not a separate literal user subquestion. H02's historical ambiguity remains recorded. The 80 previously unreviewed component instances remain unreviewed; no automatic success/failure labeling is added.

A future comparison needs fresh explicit authorization and a fixed budget, unchanged/frozen evidence and questions, positive and negative controls, independent review of actual answer completeness/support/time/direction/ownership/JSON and whole-response consistency, and no material positive-control regression. Valid auxiliary fields cannot fill missing prose. No call count, future inference or promotion is authorized by this offline implementation itself.

## Limits, preservation and rollback

This change expresses the desired behavior more directly at the actual reasoner boundary. It cannot guarantee attention, causal validity, full-answer coverage, cross-field consistency, perfect JSON or improved reliability. No model answer was generated by this task, so raw deduction, omission rates, hallucination rates and quality benefit remain unmeasured. The existing narrow release safeguards do not become a universal semantic verifier. G4/G5/G6/G11 remain unaccepted.

The final preservation record verifies unchanged HEAD/index, ordinary DB file and42tables, both environment/credential hashes, quota ledger, original frozen inputs/outputs/oracles/scores, other runtime modules, all1,923knowledge files and341active artifacts under release `7a14a351e52b49aeb87f65d1192f0937`. The only existing files intentionally changed are the two application files and an append-only checkpoint entry; all original checkpoint bytes remain. The inherited27missing temporary fixtures remain absent. No services, browser/editor/Ollama interaction, new conversations, device action, staging, commit, publication or deployment. Unsaved buffers are untouched; no fresh browser readback is claimed.

Rollback is already active operationally: leave the flag unset/OFF to obtain exactly the pre-candidate invocation. To remove implementation later, review the task-only patch against the saved dirty preimages and remove only this addition. Never reset/overwrite the mixed-history source files or discard the original evidence. Existing consent cannot be silently reused after switching mode or changing instruction text.

**Code-complete status: IMPLEMENTED OFFLINE — NOT YET LIVE-VALIDATED.** All experimental flags remain OFF. Stop before any cloud call; no additional experiment, stronger model or new reasoning layer is launched.
