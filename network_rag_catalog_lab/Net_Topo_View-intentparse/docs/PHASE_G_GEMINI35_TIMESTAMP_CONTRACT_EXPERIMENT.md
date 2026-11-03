# Gemini 3.5 temporal claim contract experiment

**OFFLINE PREPARATION COMPLETE. LIVE COMPARISON NOT RUN — FRESH AUTHORIZATION REQUIRED.** One description-only candidate is implemented behind a new default-OFF switch. No actual inference, cloud request, registered reader or quota reservation occurred. No reasoning improvement or Phase G acceptance is claimed.

Audit: `tmp/phase-g/iterations/20261102T104614Z-timestamp-contract-experiment/`. Required model remains Gemini 3.5 Flash-Lite. Gemini 3.1 planning and local Qwen roles are unchanged and uninvoked. This is not a new reasoning layer.

## Verified contract and narrow hypothesis

[SourceClaim](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/orchestration/role_reasoning.py) currently defines `timestamp` as `str|None`, `default=None`, `max_length=80`. It has no description in the base Pydantic model. Generated OFF field schema:

```json
{"anyOf":[{"maxLength":80,"type":"string"},{"type":"null"}],"default":null,"title":"Timestamp"}
```

[Current source checking](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/backend/llm/orchestration/investigation_support.py) first resolves source IDs and ownership. When a claim provides `timestamp`, it filters candidate records using that record's `timestamp`, or `captured_at` only when the `timestamp` key is absent. Explicit null does not fall back. Timestamps are parsed and compared as instants; a differently formatted equivalent instant is not a different field role. This selector remains optional.

Only after record binding does the checker interpret `field` and `value` according to category. For a verified, applied configuration event, an explicit `effective_at` assertion selects the actual event field, while claim `timestamp` binds the event record's own timestamp. Substituting effective time into record binding can make an otherwise correct fact uncheckable. Changing record matching to accept any timestamp would weaken source identity; no such change is made.

**Important implementation limit:** arbitrary event-time properties are not supported by every category. The incident checker supports exact message or verified presence under its existing narrow contract; `first_observed` is not automatically mechanically verified. H-02 intentionally preserves that limitation. Its source-derived semantic oracle can recognize correct first-observed prose/claims while the unchanged checker correctly returns insufficient support. No assertion receives verification credit merely for copying a timestamp.

The earlier 30-output diagnosis demonstrated missing field documentation and model cross-field disagreement. It did not prove that this ambiguity caused RC-02continuity inference or RC-04advice omission. Original raw4/6,2/6,3/6 and subsequent prose3/6,4/6 / consistent-whole3/6,3/6 remain frozen. This candidate tests **interface clarity**, not a presumed general reasoning repair.

## Exact single candidate

Flag: `COGNISHIELD_AI_SOURCECLAIM_TIMESTAMP_EXPERIMENT=off|candidate`, default `off`. Neither failed experiment flag is reused; both stay OFF.

Exact candidate description:

> Timestamp of the cited source record used to bind that record (timestamp, or captured_at when timestamp is absent). This selector is not necessarily the event's occurrence, first-observed or application-effective time. State the asserted time using the corresponding source field and value where supported by the claim category; do not substitute that event-time value for the record-binding timestamp.

Candidate adds exactly one JSON property:

```text
/$defs/SourceClaim/properties/timestamp/description
```

It does not add or remove response fields, change types/defaults/requiredness, demand extra claims, change source values, append a system paragraph, add outcome objects or alter checking/release. The base SourceClaim class remains unchanged; the description is applied to a freshly generated invocation schema only when that contract is present.

The phrase “where supported by the claim category” prevents the description from promising verification capabilities the code does not have. The fallback wording reflects actual absent-key behavior. There are no case IDs, names, timestamps, answers, snapshot/advice rules, causality or VRF instructions in this description.

## Actual source changes and consent

Only two existing application files differ from the task-start dirty preimages:

1. `backend/llm/orchestration/role_reasoning.py`: one description constant and a conditional assignment in `decide()` to the existing SourceClaim schema. Existing system messages, packet building, validation and release are unchanged.
2. `backend/llm/model_roles.py`: `sourceclaim_timestamp_mode()` validates `off|candidate` with422for unknown values. Candidate mode binds version, mode, schema pointer, exact text and its SHA256 in the existing consent manifest. OFF adds no manifest fields.

No alternative planner/model/provider, dependencies or schema wrappers were added. Existing classes and other functions are AST-identical. All108other runtime-source hashes match, including request interpretation, readers, entity resolution, simulation, packet admission/dependency_view_v3, supplementary retrieval, typed checks and release. The new offline freezer and23compatibility tests are evaluation support, not another application architecture.

An OFF request's schema, messages and manifest match the task-start preimage byte-for-byte under the same settings. Candidate messages and evidence packet are exactly OFF. Removing the one description property yields the exact OFF schema. No field type, required list or claim count changes.

The existing full validated-JSON adapter serializes the complete schema as the existing second systemInstruction part. Twelve intercepted, zero-network adapter serializations show the exact description survives there. The first system message and user content are unchanged. This is an **offline serialization proof**, not a Google acceptance or inference result. A noncomprehensive schema with no SourceClaim remains unaffected; the experiment applies to the existing complex reasoner profile.

Current consent binds model/profile settings and this description delta. Per-case full schema/message/wire hashes are frozen separately and must be checked by future evaluation dispatch. The consent mechanism is not misrepresented as a universal automatic hash of every dynamic schema. Changing the candidate or text invalidates the existing role binding; old OFF approval fails with403. A flag alone cannot authorize cloud inference.

## Six new evaluation-only conditions and oracles

[Registry](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/docs/evaluations/phase_g_gemini35_timestamp_contract_v1.json) and `fixtures/H-XX/case.json` freeze each exact question, scenario, source provenance, required components, prohibited assertions, expected bindings and positive/negative controls. All cases validate through the existing Scenario model. These are new arrangements, not renamed RC inputs. The implementing assistant authored and source-checked them; grading is independently checkable, **not blinded or externally adjudicated**.

| Case | Surface represented | Distinct arrangement | Frozen required conclusions |
|---|---|---|---|
| H-01 | studio | Delayed MTU audit plus separate confirming capture and two elapsed-time outcomes; not logging-buffer interpolation. | Verified effective MTU1500at08:04; event record08:17; follow-up configuration08:22.; Recording delay13minutes; capture18minutes after effective event.; Positive applied event established; no measured payload recovery time. |
| H-02 | floating | Two incidents have reversed reporting order; compares source delays, no CRC/cooling coincidence. | Ravine first observed21:04; Plateau21:08, four minutes later.; Ravine recorded21:19(delay15minutes), Plateau21:10(delay2minutes).; Reporting order reverses observation order; no cross-site causal or live protocol-state proof. |
| H-03 | studio | Cross-device equal operands and a date rollover compete for source binding; original scenarios had one-device chronology. | Both effective2026-10-27T23:50Z.; Vale acknowledgement2026-10-28T00:03Z:13minutes; Brook2026-10-27T23:56Z:6minutes.; Equal values/effective times do not make the owner/record timestamps interchangeable; later acknowledgement not later activation. |
| H-04 | floating | Same-time source conflict plus later observation, unlike original monotonic buffers/verified change event. | Same06:40observation time contains conflicting no shutdown/shutdown commands; retain both sources.; 07:10capture records shutdown;06:55and exact transition remain unknown.; Recorded commands do not establish physical oper status. |
| H-05 | studio | Known-up interfaces with unresolved neighbor and asymmetric modeled results; recommendations must address a different gap than historical unknown-port case. | Forward unknown due to unresolved/unknown next-hop resolution, despite route and port-up records; return modeled delivered.; Two distinct passive recommendations with discriminating purpose, e.g.recorded neighbor-resolution and packet/application response evidence; no execution.; Model delivery is not measured application response; do not recommend merely proving already-recorded port-up as the sole next step. |
| H-06 | floating | Two simultaneous UDP service classes, transit egress denial and reverse delivery; not the original source-egress before/after or return-ingress TLS case. | Trap forward fails atTransitHub5302Ethernet2/9egress53022hub-trap-filter/deny-traps; return delivered.; Log forward and return delivered. Transit forward ingressEthernet2/1(53021), egressEthernet2/9(53022), owned byTransitHub inmonitor.; Positive modeled policy consequence established; no real deployment/application-outage proof. |

The cases differ in source relationships and requested work: delayed event plus follow-up capture, inverted cross-site reporting order, equal-valued cross-device events across midnight, same-time source disagreement, unknown neighbor despite known-up interfaces, and two simultaneous UDP classes with different results. H-04/H-05measure whether unrelated raw failures regress; the description is not claimed to fix them.

H-01 and H-03source arithmetic is independently checked with datetime subtraction. H-02ordering/delays are similarly checked. H-04retains distinct collector identities and both command strings; no conflict is resolved by list order or majority. H-05/H-06modeled facts come from the existing pure `assess_flow` implementation, with fixed independently readable expected dispositions/owner/direction asserted against the inputs. This invokes no registered reader, physical collection or device operation, and changes no simulator code.

The H-06forward trap denial is at TransitHub egress53022inmonitor, while the distinct UDP514flow delivers and both reverse calculations deliver. The oracle checks the actual policy destination port162, direction and owning interface. It distinguishes modeled consequence from deployed outage proof. H-05has all ports up but an unknown next-hop resolution; repeating interface-up advice alone would fail its requested diagnostic purpose.

The frozen model inputs contain only the question, accepted-shaped source envelopes, simulated Evidence identities, source records and existing packet metadata. They **do not contain the grading oracle**. Sources are openly labelled authored synthetic fixtures; no executed-reader receipt or consent is fabricated. Future cloud use still requires exact server-approved synthetic scope. No ordinary scenario or database is modified during preparation.

## Frozen input and exact byte evidence

Registry SHA256:

```text
d8dbe4f0d70c5dce1d5ec182b71b216b87cc066b9003f5ff18330d6f941a62a4
```

Description SHA256: `e2f1f6a1eb5c93ef09d729e5dac5d9a195ef3a35781c143e095d432b152a5afb`.

[Exact byte manifest](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261102T104614Z-timestamp-contract-experiment/exact-byte-freeze.json) SHA256: `5d12a9c7173daffd1da1a225bf749ad6d82bc4deabac9c46dcae2f2c19bbcbc4`. It contains paths/hashes for all12 actual adapter request-body byte files and12 provider-schema byte files. The registry already binds each complete pair/schema/body object and source oracle; this companion records exact serialization bytes without rewriting the registry. Future approval/run must retain both freezes and verify their relationship.

The comparison changes the schema annotation inside the existing schema instruction, not the reasoner's ordinary system message. All question bytes, source operands/order, raw provenance, response constraints and generation settings are identical between arms. Per-case `pair.json` has full exact hashes; these prefixes are for display only.

| Case | Packet characters | Packet SHA prefix | OFF schema SHA | Candidate schema SHA | Conservative input bytes OFF / candidate |
|---|---:|---|---|---|---:|
| H-01 | 6488 | 91aa76fbd00e | fcfdddd9f511 | 2d19df547407 | 15616 / 16041 |
| H-02 | 5279 | 4e38f92c067b | dd4238a09e43 | d1f0fe051552 | 14257 / 14682 |
| H-03 | 5184 | 4acf62a315c9 | dd4238a09e43 | d1f0fe051552 | 14144 / 14569 |
| H-04 | 5973 | 89bc4323604b | dd4238a09e43 | d1f0fe051552 | 15006 / 15431 |
| H-05 | 13278 | 88370e4f400f | b581c90f1ae7 | ab00f5695a24 | 23385 / 23810 |
| H-06 | 11530 | 27dfaed68466 | dd4238a09e43 | d1f0fe051552 | 21358 / 21783 |

Largest packet13,278/64,000characters. Candidate description adds425serialized request-body bytes per case; packet admission is unaffected. Actual token difference is **not measured**. Low thinking,8192 maximum output tokens, validatedJSON/fullschema and unchanged120-second request envelope are frozen. Temperature, top-p and seed remain unspecified by the current adapter; provider defaults are not claimed deterministic. Qwen and planner are not invoked.

## Predeclared grading and decision

Grade the entire output against source-grounded requirements, using no LLM grader. Record separately:

- **Raw answer:** all requested conclusions/advice, correct owner/direction/time, source limitations, no unsupported continuity/activation/cause or invented observations.
- **Structured claims:** actual source/record/owner and record timestamp, correct category-supported field/value, truthful semantic statement and consistent assessments. For H-01/H-02/H-03, missing temporal declarations are NOT_DEMONSTRATED, not automatic binding success. Any emitted temporal declaration in other cases must also be correct.
- **Whole response:** substantive prose, claims and assessments must all be mutually consistent and source-grounded. Model-supported labels do not override the oracle. Correct prose with an incorrect material auxiliary statement does not pass whole-response adequacy.
- **Released response:** preserve correct explanations, retain unsupported assertions as unverified, avoid false suppression and never mislabel unsupported prose as verified. Adequate fallback/JSON/citations are not model reasoning.

Existing `claims` remain optional in the application schema; the grading requirement does not add fields or force extra generation. H-02 correct first-observed declarations can be semantically sound yet mechanically unverified under the current category; that is an expected checker limit, not a negative model grade or permission to call it verified.

Candidate gates: correct record/event distinction in all applicable cases; no paired-control whole-adequacy regression; no regression on H-06supported modeled/directional result; no new unsupported activation/causal assertion; no incorrect verified claim or new false suppression. Record H-04continuity and H-05advice failures separately. A binding-only improvement without better raw deductions is **interface clarity**, not demonstrated reasoning improvement. Correcting one case while introducing other incorrect deductions fails. Six exposed-after-freeze samples remain preliminary, not production acceptance.

The rubric is human-reviewable: check each required component against named source IDs/fields or the frozen calculation; flag every prohibited conclusion; compare each substantive declaration with that evidence and with answer prose. Ambiguous wording must retain an explicit reason and evidence pointer, not silently earn adequacy. No semantic NLP grading proxy or universal verifier is introduced.

## Offline verification

- Initial focused run:22 passed,0 failed,2.92seconds.
- Affected schema/consent/graph/delivery/no-read/release suites: **176 passed,0 failed**,11.02seconds.
- Final focused run after explicit serialized-byte checks: **69 passed,0 failed**,2.38seconds:23 new timestamp tests plus46 existing release-checker checks. Counts overlap; do not sum them as unique successes.
- All six OFF inputs and manifests reproduce the task-start preimages. All six candidates differ only at the intended description property and consent metadata. Provider serialization preserves it; no new system paragraph is inserted.
- Tests preserve real contradiction rejection, positive effective events, absent-timestamp captured_atfallback, wrong effective values, and incident support limitations. Configuration-only cloud dispatch remains403without existing exact consent.
- All30 historical outputs were replayed offline:30 current checker reviews and30 current released answers exactly match prior saved current behavior. Original raw JSON, original live releases, grades and earlier repaired replay are unchanged. This is not30 new model successes or a new score.

Logs and proofs are in `focused-tests.log`, `affected-tests.log`, `final-focused-tests.log`, `source-oracle-checks.json`, `historical-replay/`, `historical-replay.log`, `freeze-receipt.json` and `preservation-before-handover.json`. The copied replay utility's original labels are retained under `unchanged-utility-summary.json`; the new summary explicitly distinguishes unchanged checker/release from this task's two gated schema/consent changes.

All actual provider/model/reader/network calls: **zero**. Mock adapter serialization uses a dummy noncredential, an intercepted send that raises before a socket, and mocked quota functions returning no actual reservation. Nothing contacts Google, local Qwen or the planner. No new standalone app or backend is started.

## Future experiment proposal — not executed

- Model: Gemini 3.5 Flash-Lite only, low thinking,8192 allowance, current adapter/schema/release.
- Six cases × OFF/candidate, exactly one call per cell, **maximum12 dispatch attempts**, failures included, **no retries**. No extra planning, retrieval, second pass, private/editor data or other model.
- Order: H01OFF/candidate; H02candidate/OFF; H03OFF/candidate; H04candidate/OFF; H05OFF/candidate; H06candidate/OFF. Alternating is not randomization/blinding.
- Input budget: offline exact bodies reserve14,144–23,810bytes per call under the existing conservative quota algorithm; total210,082body-byte reservations across12calls. These are **not tokenizer counts**. Actual input tokens are NOT_MEASURED; no token-count API was called. Worst-case output allowance12×8192=98,304tokens; this is a ceiling, not expected usage or extra allocation.
- Use the unchanged persistent quota ledger; freshly inspect capacity immediately before a future authorized run. Ceilings15RPM/150KinputTPM/500RPD, sequential/concurrency-one and request-wide120seconds. Total byte reservations are not a per-minute spend claim; pacing and actual-token updates remain authoritative. Stop on quota/authentication/provider unavailable failures without retry or model switch. Invalid/noncompleted output is a failed cell, not reasoning success.
- Fresh explicit user approval must name the exact registry and candidate. Then use existing owned disposable synthetic conversations and exact request/history/scenario-revision/role consent. Seal only these new fixture scenarios using existing ScenarioManager/authorization machinery, verify no editor/uploads/private context, and check frozen schema/message/wire/source hashes before dispatch. No approval has been minted in this task.
- Existing live runners name exhausted older registries and must not be reused blindly. This iteration prepares all exact inputs/oracles/bytes, but intentionally contains **no live dispatcher command or automatic activation**. A separately authorized execution must use the existing adapter/consent/quota path and enforce this12attemptfreeze; no manual provider bypass is allowed.

**LIVE COMPARISON NOT RUN — FRESH AUTHORIZATION REQUIRED.** Old18/12callpermissions are exhausted and not reused. Current99ledgerrows/hash are preserved, not a promise of future quota availability. The new registry's pending status remains truthful; no unused calls may trigger automatic work.

## Preservation, rollback and continuation

[Preservation proof](C:/Users/limmi/OneDrive/Desktop/LLM_RAG_Practice/network_rag_catalog_lab/Net_Topo_View-intentparse/tmp/phase-g/iterations/20261102T104614Z-timestamp-contract-experiment/preservation-before-handover.json): HEAD840031451e954809f2817adf78d800bc6548c2d4, logical/binary Git index unchanged; all 42 ordinary table fingerprints, both environment hashes,99 quota entries/hash, all 1,923 knowledge files/341 active artifacts and release7a14a351e52b49aeb87f65d1192f0937match. All 940 historical protected artifacts/tests match before the requested checkpoint append; source changes are exactly the two approved schema/consent files. All 27 inherited missing fixtures remain absent. No services, browser/editor, Ollama, device, staging, commit, publication or deployment actions. Unsaved buffers are untouched; no fresh browser readback is claimed.

`task-only-source.patch` and `source-before/` preserve only this task's delta against the already-dirty baseline. Leave `COGNISHIELD_AI_SOURCECLAIM_TIMESTAMP_EXPERIMENT` unset or`off` to restore exact old invocation behavior; no environment edit or restart was performed. Keep `COGNISHIELD_AI_REASONING_CONTRACT=off`, `COGNISHIELD_AI_REASONER_INTERPRETATION_EXPERIMENT=off`, Approach A and other ordinary experiment defaults unchanged/OFF. To remove source changes later, review the task-only patch and remove only this gate/description/consent addition; never reset mixed-history files or discard earlier repairs.

**Recommendation: worth one separately authorized comparison as an interface-clarity hypothesis; retain default OFF.** Model-visible effect and compatibility are established offline. Correct deduction, reduced omissions and consistent whole answers are NOT_MEASURED. RC-02continuity, RC-04advice omission and RC-05independent prose/claim disagreement remain unsolved. Do not bundle another hypothesis, increase thinking, change models or launch another experiment. G4/G5/G6/G11remain unaccepted.
