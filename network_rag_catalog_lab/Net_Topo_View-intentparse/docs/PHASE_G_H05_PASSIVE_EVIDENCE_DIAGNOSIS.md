# H05 passive-evidence reasoning diagnosis — 2026-11-04

**Decision: no prompt or application change.** The latest H05 error is a demonstrated mismatch between an artifact's granularity and the conclusion assigned to it. Some earlier grading expectations need qualification, but they do not excuse the latest specific-poll overclaim. The offline investigation below completed six contrasts and eight saved-response reviews with zero new generations. A subsequently authorized single PD-02 call passed the focused evidence comparison, with qualified advice and uncheckable auxiliary categories; see the final section. No general model-reliability score or Phase G acceptance is claimed.

The exact current instruction already says: “aggregate interface counters alone do not identify a specific traffic exchange or application response.” Its SHA256 remains `4f29e110db484a44b3cd3af50a84e6a6241564356dccef0b2a7c3b90cc73edfe`. Repeating that rule would add no demonstrated missing information.

## What the evidence establishes

The five saved H05 responses use identical question and reader operands. The latest packet contains the route, up-port records, forward **unknown** because neighbor resolution is unavailable, and return **modeled delivered**. No actual counter sample, flow log or application response was supplied. The model was asked to recommend two passive artifacts and explain their purposes, without executing collection. It therefore had to describe plausible evidence capabilities accurately, rather than infer a poll result from nonexistent measurements.

The raw latest answer recommends an “Interface packet counter or flow log snapshot … to verify if poll packets are successfully transmitted outbound.” It assigns different artifacts an unjustified common capability. Counters may describe aggregate activity/errors; they do not identify the named exchange. Even standard output-packet counters require care: `ifHCOutUcastPkts` includes transmission requests that may not have been sent. [RFC 2863, interface definitions](https://www.rfc-editor.org/rfc/rfc2863.html#section-6)

A flow record describes traffic at an observation point over an interval. Its keys, sampling, direction and location determine what it can establish; it is not automatically a per-transaction egress or application receipt. [RFC 7011, terminology](https://www.rfc-editor.org/rfc/rfc7011.html#section-2)

The explicit limitation reaches Gemini. The completed response is not truncated: HTTP200/STOP, 2,180 of 8,192 output tokens, 5.48s, 13,278 evidence characters within 64K. Valid identifiers and eight supported typed operands do not certify the advice. The wrong recommendation is already in the raw response and survives release as `QUALIFIED_UNVERIFIED`; no application-side evidence loss or prose replacement caused it. Hidden model causation is unknown. Compression of alternatives into an overbroad shared purpose is plausible, not proven.

## Offline contrast set

Versioned registry: `docs/evaluations/phase_g_h05_passive_diagnostic_contrasts_v1.json`, SHA256 `90a51c54d6d0e350c37e42563c6c484586e4c33d84623db5f0d49315e6fe31dc`. Six authored synthetic conditions contain explicit records, known/unknown facts, useful passive artifacts, their limits, incorrect examples and minimum criteria. Source-derived and independently checkable; implementation-assistant reviewed, not blinded. **These are not six Gemini results.**

| Contrast | Necessary distinction |
|---|---|
| PD-01 | Useful aggregate deltas/error trends versus identifying a particular DNS request |
| PD-02 | Sampled ingress flow versus a positively matched post-egress TAP frame; application reply remains unknown |
| PD-03 | Selected route and unrelated BGP/other-VRF neighbor versus the intended IPv4 neighbor binding |
| PD-04 | IPv6 `STALE` retains a mapping without recent reachability confirmation; it is not a proven failure |
| PD-05 | Positive bidirectional model versus unobserved packet/application exchange |
| PD-06 | Positively recorded request, server processing and reply arrival versus unknown client consumption |

PD-03 follows the routing/address-resolution distinction in [RFC 826](https://www.rfc-editor.org/rfc/rfc826.html); PD-04 uses [RFC 4861 §7.3.2](https://www.rfc-editor.org/rfc/rfc4861.html#section-7.3.2). Neither adds simulator or reader capabilities. All proposed artifacts remain conditional requests, not claims that records exist or were collected.

## Applying the distinctions to saved outputs

| Saved response | Separate diagnostic finding |
|---|---|
| H05 Round 1 control | Genuine specific-UDP-transmission overclaim from interface statistics |
| H05 Round 1 candidate | Drop-cause advice is underspecified: reason-coded drop data could help; generic aggregate counters cannot establish unresolved-adjacency cause |
| First corrected H05 | Correctly limits counters to activity and denies exchange/application proof. A plain cumulative snapshot still needs a rate/prior sample for “incrementing.” Separate wrong return-origin declaration caused withholding |
| Deferred H05 retest | Genuine OSPF/BGP-versus-MAC conflation; independently, numeric identifiers invalidate the declarations |
| Latest H05 | Identifiers/direction/layer distinction improve, but the counter-or-flow specific-poll overclaim remains |
| RC04 control | Correct uncertainty, but omits the explicitly requested next advice |
| RC04 candidate | Valid differently worded passive advice targeting missing interface status |
| H06 candidate | Positive modeled-scope control; no advice was requested, so none is missing |

Exact original questions, raw answers, source/message hashes, parser/checker/release findings and notes are in `saved-response-contrast-review.json` in the audit. These repeated H05 conditions are not independent generalization evidence. Historical scores are unchanged.

Do not reject counters merely for being counters; their use for aggregate activity/errors is legitimate. Do not require a particular second artifact or a standalone measured-application caveat when the original question only asks about a model. Conversely, a requested artifact's purpose must be technically defensible. These question-aligned qualifications are a separate diagnostic interpretation, not rewritten historical passes. One saved answer can articulate the counter limit while a later answer violates it: the evidence supports inconsistent application of the boundary, not a proven universal lack of networking knowledge.

## Smallest justified next action

Leave the instruction, schema and checker unchanged. One future **PD-02 evidence-appraisal diagnostic** could distinguish boundary knowledge under an explicit comparison from failure to apply it while generating open-ended advice. It must retain both negative limits and the positive matched-TAP conclusion. A pass would demonstrate one explicit appraisal, not reliable spontaneous H05 advice; a failure would strengthen the fixed-model capability limitation. No automatic follow-up campaign is justified.

The complete request/wire/schema/scenario is frozen at `prepared-PD-02/one-call-freeze.json`, SHA256 **`aba34102caead0930607f54bb354b58377781f03270dd14560a682212ef6267f`**. Same Gemini 3.5 Flash-Lite, low/8192/validated JSON and unchanged candidate instruction; 6,848 evidence characters. Maximum one future dispatch, no retries/planner/new retrieval. Existing exact synthetic consent and persistent quota remain mandatory. **Authorization pending; no call or reservation occurred.** No new execution framework was added.

**Verification:** registry structure, record identities, deltas and scope controls pass offline checks; 48 focused existing tests pass in 3.25s for OFF-path/wire/consent, identifier fidelity and directional ownership. The earlier 136 tests and 17 replays remain historical results and are not added to this count. Application source/tests, model roles, credentials, ordinary SQLite, quota, V9, H02/RC05 and frozen evidence remain unchanged; experimental flags OFF, Git HEAD/index preserved. Only this report, the contrast registry, audit artifacts and an appended continuation entry were created. No prompt rewrite, model generation, staging, commit, device action, UI/editor interaction or activation.

Audit: `tmp/phase-g/iterations/20261104-h05-passive-evidence-diagnosis`. See `failure-reconstruction.json`, `saved-response-contrast-review.json`, `contrast-offline-checks.json`, `prepared-test-summary.json`, `offline-tests.log` and `preservation-after.json`.

## Authorized PD-02 diagnostic completed — 2026-11-04

The user explicitly authorized one call for freeze `aba34102caead0930607f54bb354b58377781f03270dd14560a682212ef6267f`. Exact input, schema, instruction, runtime and settings matched. The task-only driver reused the existing synthetic consent, role adapter, shared quota and release functions: **HTTP200/STOP, 2.96s, 4,485 input /811 output tokens**, no retries, planner or readers. No application code changed.

**Focused evidence comparison PASS:** Gemini correctly distinguishes aggregate counters from datagram identity, recognizes the 1-in-100 flow as an ingress observation without sequence identification or egress proof, positively identifies `seq-214` in the post-egress TAP, and leaves server processing/reply unknown. This demonstrates that it can articulate the boundary under explicit contrast. It does not prove reliable application during open-ended H05 recommendation generation.

**Whole response QUALIFIED, not a strict full-task pass:** the recommendation groups “a passive server-side packet capture or application response log” under determining processing and reply generation. A scoped capture can establish packet observations; it does not directly expose internal processing or distinguish silent processing from no processing. A suitable application audit can. The log is a useful recommendation, but the shared purpose needs qualification. This is not a fabricated assertion that the supplied records already show processing. Likewise, “400 packets out” loosely labels a transmission-request counter; the key aggregate-versus-specific distinction is nevertheless correct. No extra verbatim caveat or artifact name was imposed for grading.

All three claims have valid identifier types and selectors, but use `interface_oper_status` for counter/flow/packet assertions. All remain mechanically uncheckable under the unchanged claim contract; none receives verification credit. The correct comparison and qualified advice survive release unchanged with `QUALIFIED_UNVERIFIED`, not semantic certification or factual fallback. Literal backslash-n formatting also originates in the raw response and is retained.

**Stop here.** The single authorization is consumed. No prompt refinement, schema/checker expansion, additional model call or promotion follows. Original H05 scores remain unchanged. Existing 48 focused tests and earlier regressions remain applicable because application code was unchanged. One quota reservation was added; protected state and experimental OFF defaults are preserved. This was a frozen synthetic reasoner/release diagnostic, not browser/full-gateway or G4–G6/G11 acceptance.

Exact authorization, driver attestation, wire, raw/provider/final response, rubric review and quota receipts: `prepared-PD-02/` in the audit. Final preservation proof: `preservation-after-pd02-live.json`.
