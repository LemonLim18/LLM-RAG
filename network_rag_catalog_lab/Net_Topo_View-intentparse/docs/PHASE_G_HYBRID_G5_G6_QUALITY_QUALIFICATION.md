# Phase G — fresh hybrid G5/G6 quality qualification

**Decision: G5/G6 IMPROVING BUT INCOMPLETE. Neither stage is qualified; G11 remains unaccepted.** Bounded repairs and validation finished on2026-10-26. Original frozen results remain unchanged. The existing experimental hybrid stays scoped to approved synthetic development requests; remoteG4 and ApproachA remainOFF.

## Original qualification results

| Measure | Qwen-local | Hybrid |
|---|---:|---:|
| Full-task adequate | 1/30 (3.3%) | 7/30 (23.3%) |
| Adequate causal explanations | 0/16 | 5/16 |
| Adequate raw network explanations | 0 | 11 (all Flash-Lite) |
| Qualified but incomplete final answers | 1 | 3 |
| Partial final answers | 26 | 19 |
| Critically unsafe final releases | 2 | 1 (written by local Qwen) |
| Median gateway time | 69.81s | 9.55s |
| p95 gateway time, nearest rank | 79.35s | 52.34s |
| Longest gateway turn | 90.23s | 72.13s |
| Scored requests over120s | 0 | 0 |

G5 still requires at least26/30 adequate complete tasks and no accepted critical false operational/certification/deployment claims. It misses the adequacy threshold by19cases and fails the safety gate. G6 independently requires supported causal explanations, safeUNKNOWN/UNSUPPORTED behavior and the conformance matrix;5/16 adequate hybrid causal explanations is insufficient. Good retrieval, JSON or fallback is not qualification. The single adequate local final answer is arithmetic, not network reasoning.

The hybrid shows selected task improvement, but local planning still sometimes chooses unwanted readers and keeps difficult interpretation local. Of20scored Flash-Lite completions,11raw answers were adequate; only6became fully adequate complete gateway tasks. One additional adequate hybrid task was local arithmetic. Original hybridGQ-13 did not use cloud and released a false local success claim. No promotion or unrestricted-prompt claim follows.

## Frozen registry and grading integrity

Registry:`docs/evaluations/phase_g_hybrid_quality_qualification_v1.json`; SHA256`cca14963414bceaabe9866b707a6467328555602bf097730a0e492763b2783b2`. It contains30distinct authored conditions,16causal conditions,12compound/contextual conditions and2local controls, split15Floating/15Studio. Synthetic data uses a five-device dual-path network, explicit current/saved captures, typed flows, VRFs, policies, protocols, missing samples and source dependencies. Oracle fields never enter runtime scenarios or model packets.

Expectations were authored from source records and crosschecked against deterministic calculations and immutable published schemas before inference. This is **source-derived, independently checkable, implementation-assistant graded—not external or blinded evaluation**. It does not fulfill an independent human-certification requirement by itself. Every full answer has a retained rationale; supplementaryA–Jdimension adjudication distinguishes comprehension, coverage, attribution, facts, causal explanation, outcomes, unsupported assertions, uncertainty, usefulness and release safety. Qualified/partial/fallback outputs are not rounded up to adequate.

All60original authenticated gateway turns and original review hashes verify. Six additional setup turns establish owned follow-up references and are not scored as independent conditions. One setup made an approved cloud call; its usage is separate. Original scores are never replaced by post-repair replays. A documented registry typo calls the inventory capability`network.inventory`; the actual registered reader`inventory.read`is the correct control. The registry remains untouched, and no reader-selection penalty is assigned for that evaluator typo. Output scope is still graded strictly.

## Complete-answer matrix

Cells show **raw initial synthesis / final task**. “No synthesis” and “Projection” earn no model-reasoning credit; “Timeout” is provider noncompletion, not completed wrong reasoning. Hybrid-arm raw text can still be Qwen when the selector stays local. Raw repaired outputs and intermediate clauses remain inspectable in traces.

| Case | Surface | Condition | Local | Hybrid |
|---|---|---|---|---|
| GQ-01 | floating | healthy routed flow | Timeout / Partial | Partial / Partial |
| GQ-02 | studio | oper-down transit | Timeout / Partial | Incorrect / Partial |
| GQ-03 | floating | admin-down/current CLI | Timeout / Partial | Adequate / Adequate |
| GQ-04 | studio | return route missing | Timeout / Partial | Adequate / Adequate |
| GQ-05 | floating | transit route missing | Timeout / Partial | Partial / Partial |
| GQ-06 | studio | partial routing table | Timeout / Partial | Adequate / Adequate |
| GQ-07 | floating | discard route | Timeout / Partial | Partial / Partial |
| GQ-08 | studio | forwarding loop | Timeout / Partial | Adequate / Partial |
| GQ-09 | floating | ECMP partial loss | Timeout / Partial | Incorrect / Partial |
| GQ-10 | studio | VRF scope missing | Timeout / Partial | Adequate / Adequate |
| GQ-11 | floating | recursive next hop | Timeout / Partial | Partial / Partial |
| GQ-12 | studio | egress ACL / reverse flow | Timeout / Partial | Adequate / Adequate |
| GQ-13 | floating | incomplete policies | Unsafe / Unsafe | Unsafe / Unsafe |
| GQ-14 | studio | benign OSPF2-Way | Timeout / Partial | Timeout / Partial |
| GQ-15 | floating | conflicting OSPF observations | No synthesis / Partial | No synthesis / Partial |
| GQ-16 | studio | BGP AS mismatch | No synthesis / Partial | No synthesis / Partial |
| GQ-17 | floating | saved CLI / logs unavailable | Partial / Partial | Adequate / Partial |
| GQ-18 | studio | current versus saved + advice | Incorrect / Partial | Incorrect / Partial |
| GQ-19 | floating | published OSPF mapping | Incorrect / Partial | Qualified / Qualified |
| GQ-20 | studio | two-device OSPF identifiers | Timeout / Partial | Adequate / Partial |
| GQ-21 | floating | planned versus observed link | Incorrect / Partial | Qualified / Qualified |
| GQ-22 | studio | historical events / continuity | Unsafe / Unsafe | Qualified / Partial |
| GQ-23 | floating | traffic sample gap / advice | Timeout / Partial | Incorrect / Partial |
| GQ-24 | studio | incident source dependency | No synthesis / Partial | No synthesis / Partial |
| GQ-25 | floating | owned saved-config follow-up | Timeout / Partial | Adequate / Partial |
| GQ-26 | studio | next-check advice, no reads | Partial / Partial | Partial / Partial |
| GQ-27 | floating | pair follow-up advice, no reads | Timeout / Partial | Adequate / Partial |
| GQ-28 | studio | backup versus current | Partial / Partial | Adequate / Adequate |
| GQ-29 | floating | arithmetic control | Control / Adequate | Control / Adequate |
| GQ-30 | studio | inventory-only control | Projection / Qualified | Projection / Qualified |

## Evidence, providers and framework boundaries

Both arms use the real shared HTTPgateway on disposable8001, signed ownerJWTs, conversation ownership, normal LangGraph and authorized source readers. Hybrid requests use the existing exact-message/history/scenario-revision consent API and process-local operator allowlisting of frozen synthetic bytes. No source result or inference was mocked in the original cohort. Ordinary editor/uploads/conversations were not sent remotely.

Required-reader presence is30/30in both arms, but **that is not source-selection accuracy**: advisory cases expected no reads yet executed readers, sources were added despite exclusions, and some operands were missing. Selected reader sets match26/30pairs. Both have a synthesis packet25/30; exact model-visible evidence matches20pairs, including the same typed data, labels and order. Other pairs must not be treated as pure model comparisons. Five conditions have both completed local synthesis and Flash-Lite on identical evidence:GQ-17,19,21,22,28. Their raw local results are respectively partial, incorrect, incorrect, unsafe, partial; Flash-Lite is adequate, qualified, qualified, qualified, adequate. This supports a limited content advantage, not general causal certification.

Flash-Lite actually handlesGQ-01–12,17,19–22,25,27,28. Other scored hybrid conditions remain local or use pre-inference factual boundaries. Ordinary arithmetic and exact inventory stay local. GQ-14 adds an unnecessary published read and times out locally. GQ-15/16/24 use protocol/historical-event fallback without synthesis. GQ-18and23 stay local despite requiring substantial interpretation. RemoteG4 remains disabled; noG4planning improvement is claimed.

Qwen completes7initial synthesis responses; local inference diagnostics record35TimeoutError calls across synthesis/repair. Hybrid records4localTimeoutError calls. Cloud returns20/20scored completions, HTTP200/STOP, parseable schema-shaped outputs; zero cloud429/5xx/timeouts. Schema validity is not factual correctness. Qwen temperature0/context8192/output512/30scall timeout versus Flash-Lite lowthinking/output8192 with provider-specific controls is disclosed. This is current-application usability comparison, not equal-token capacity comparison. Loaded Qwen resource snapshot reports1,367,647,190bytes and0VRAMbytes (CPU inference), context8192.

Measured cloud inference median2.46s,p953.20s,max4.41s. Local planning median5.68s versus5.09s in hybrid; median authorized-reader time7.42ms versus7.53ms. Median synthesis-stage time31.65s versus2.46s; median repair31.47s versus0. Per-case timings are retained. Residual timing includes verification, composition, HTTP and checkpoint overhead; it is **not** an independently instrumented pure-verifier duration. Every scored gateway turn stays below120s; this does not establish adequacy or universal deadline compliance under other workloads.

## First failure boundaries and bounded repairs

1. **Evidence relationship loss / interpretation:** Endpoint-scoped state reads omit detailed transit rows. Old forwarding trails listed completed egress steps but not the next failed ingress; GQ-02/09mislocalized the return fault. Existing typed calculation now carries failure location, device/interface ownership, ingress/egress, admin/oper values and VRF when established. Generic lookup stops have a device/VRF but no invented interface. Projection retains these operands, source references and modeled scope. Outcomes, branches, route selection and physical semantics are unchanged. The assessment consumer was updated to distinguish policy locations from general interface/lookup locations; its initially missed policy-only assumption caused a retained diagnosticKeyError, now covered by nine location-variant regressions.

2. **False verifier rejection / lost obligations:** GQ-08raw correctly explains the loop and working reverse path; an auxiliary topology reader became a mandatory citation because the user mentioned a path/relationship. Required citations now distinguish named sources from relational wording. Every actual context-backed source label remains available; orphan evidence IDs are excluded. Exact factual/citation validation remains. Incidental returned flow evidence no longer requires transit/return exposition in an unrelated saved-configuration explanation. Claims that actually discuss the flow still undergo factual checks.

3. **Unsafe verifier acceptance:** GQ-13both arms receiveUNKNOWNforwarding due incomplete policy observations but Qwen declares communication successful. The existing all-UNKNOWNsafe projection is now selected from typed outcomes rather than one composition lane's wording. It preserves the actual missing prerequisite (policy, routing or other recorded reason), without calling the model or turning unavailability into success/failure. Separate successful configuration outcomes are not suppressed by an unknown-flow result. Healthy, failed and partial flows remain distinct controls. This does not certify arbitrary prose or all mixed-source claim forms.

4. **False AS-role rejection:** GQ-17raw Flash-Lite correctly maps savedCLI and unavailable syslog, but the checker only recognized structured operational peers. It now reuses the existing bounded literalCLIextractor for device-bound configuredASfacts, without creating an operational observation or vendor parser. Local-only questions do not require every remoteASin the evidence. Wrong-owner/role values remain negative tests. Unsupported command families remain uncertified.

5. **Temporal inference and projection:** GQ-22local invents interface transitions and continuous availability from points; the original false answer is retained. A bounded interval-evidence check rejects affirmative uninterrupted-availability claims from discrete states/events while retaining qualified comparisons and recommendations. Syslog fallback now separates explicit event_time from record timestamp. No generic trend/causal-sequence verification is claimed; established forward/reverse point-time checks remain in place.

6. **Follow-up source execution:** Negative“other sources”wording triggered contextual investigation and broad source expansion. Routing now applies the existing positive-request view before follow-up detection. Advice recognizes the prospective“obtain”speech act and a discourse preface;“next”restores owned reference identities without executing earlier readers. Several interfaces on one owner no longer make“that same device”ambiguous. When the latest instruction forbids other readers, a widened model proposal is rejected and the existing resolved-read fallback is used. Present retrieval and genuine multi-source requests remain supported; no second planner or ApproachAactivation was introduced.

Affected source components:`network_model.py`,existing scenario assessment,`engine.py`,`gateway_references.py`,`gateway_routing.py`,`request_contract.py`,`investigation.py`,`synthesis.py`,`gateway_findings.py`. New code outside those paths is the bounded evaluator, regression file and curated documentation. No model settings, source authorization, V9contracts, templates or release artifacts changed.

## Validation and diagnostic results

Final affected backend suite: **369passed**; syntax checks pass. Earlier58/66/76pass runs had retained failures, one affected run365passed/1failed exposed an orphan-citation regression, and the final context-backed label restriction resolves it. Runs overlap and are not added. No frontend files changed; no new frontend-build acceptance is claimed.

Eight exact-original-output offline replays pass: five correct explanations(GQ-04control,08,17,20,25)survive; both originalUNKNOWNsuccess outputs take scoped fallback; original continuity claim rejects. These use **zero new cloud/local inference** and do not improve the frozen scores or demonstrate new reasoning capability. Original failed replay and corrected replay are retained separately.

Actual authenticated local-Qwen post-repair requests use only configuration forGQ-25(Floating), zero readers forGQ-26(Studio), and zero readers forGQ-27(Floating). Their source-execution boundaries pass. GQ-25's final factual reconstruction still omitsBGP; both advisory answers remain circular/irrelevant, including unsupported proposed hop-limit rationales. They remain task failures, with unverified-advice labels; no prompt-tuning loop followed. Intermediate clarification/extra-reader/consumer failures are retained. No new browser acceptance is claimed for this backend-only continuation.

## Usage, preservation and decision

Original experiment uses21cloudcalls:20scored plus1setup,64929input/4027finaloutputtokens,0reportedthinkingtokens; no diagnostic cloud calls. All four authorized diagnostic generations remain unused. New-traffic peak2requests/61s and7048chargedinput/61s; shared ledger peak9requests/61s and50838chargedinput/61s across known historical/current traffic,84rolling24h reservations at accounting. Ceilings15RPM/150KinputTPM/500RPDare unchanged. Other clients' account activity and monetary billing are not observable; no billing activation occurred. No3.8orothermodelcalls.

Preservation verified: HEAD`8a7f86c`and index unchanged; all41non-internal ordinarySQLite tables unchanged, integrityok; active release`7a14a351e52b49aeb87f65d1192f0937`,341immutable artifacts and all343snapshotted release/manifest/pointer files unchanged; prior audit, original60traces, registry and full-answer review hashes unchanged. Credential file byte-identical, ignored, single entry, fresh-process loaded; no credential copies detected in new text artifacts. Configuration remainsQwen2.5/Flash-Lite/hybrid1/remoteplanning0/outcomes0. No browser/storage/editor operations were performed; prior buffer proofs remain retained, not newly recertified. No commit/stage/push/publication/deployment/device action/model installation.

The repaired hybrid is safer at the demonstrated release boundaries and preserves more correct raw text, but complete-task reasoning remains inadequate. G5/G6do not pass, G11is not ready for certification, and G7remains113/141with28Huawei contract blockers unchanged. Keep ApproachAand remoteG4OFF. No accepted stage is reopened or newly closed.

**Next bounded milestone:** preserve complete source constraints and per-clause operands in the existing plan/evidence path, then test evidence-complete advisory/comparison fulfillment in a small independently authored holdout—not another broad cohort or prompt-specific guard cycle. Measure cloud eligibility, raw explanation and released task fulfillment separately. Source/projection fixes cannot compensate for Qwen's demonstrated completed reasoning errors or CPUtimeouts. Fresh independent qualification is needed before acceptance; this report does not authorize launching it automatically.

Immediate rollback to ordinary local-only operation remains`COGNISHIELD_AI_HYBRID=0`plus restart of the owned backend, retaining explicitQwen2.5and the ignored key. Do not roll back by resetting the dirty worktree. For source recovery review only these repair hunks against the archived pre-qualification patch and preserved historical traces; retain unrelated work. No rollback or ordinary service restart was performed. Stop at this checkpoint.

Curated results:`docs/evaluations/phase_g_hybrid_quality_qualification_result.json`. Full traces, timing packets, original failures, dimension adjudication, replays, JUnit and preservation receipts:`tmp/phase-g/iterations/20261026-hybrid-g5g6-qualification/`.
