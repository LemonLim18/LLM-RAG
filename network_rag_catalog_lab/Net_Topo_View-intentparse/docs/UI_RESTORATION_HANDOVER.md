# Current implementation handover — 22 October 2026

Phase G is **incomplete**. G1, G2 and G3 are complete. G3 has individually accepted all 24 development sources through JSON editing, GUI editing, scenario activation and both assistants' authorized gateway paths. Source acceptance does not establish model reasoning quality.

The original handover was moved into [the historical archive](<old implementation plan & result/UI_RESTORATION_HANDOVER.md>). That history is preserved. This file restores the current handover entry point requested by the implementation specification. The authoritative changing counters are in [the stage ledger](evaluations/phase_g_stage_state.json), [native journey matrix](evaluations/phase_g_studio_141_results.json) and [continuation checkpoint](PHASE_G_CONTINUATION_CHECKPOINT.md).

## Full-stage ledger

| Stage | Status at this checkpoint | Acceptance boundary |
|---|---|---|
| G0 | BLOCKED | Current preservation passes. The original pre-change frozen benchmark/index baseline cannot be reconstructed or backdated. |
| G1 | COMPLETE | Source registry and normalized provenance/status protocol accepted. |
| G2 | COMPLETE | Versioned JSON/scenario authoring foundation, complete starters and lifecycle tooling accepted. |
| G3 | COMPLETE | All 24 individual source acceptances and standard-browser complete-source activation accepted. |
| G4 | IN PROGRESS | General semantic/planning and fresh routing benchmarks remain open; native extraction failures remain visible. |
| G5 | IN PROGRESS / quality gate failed | Exposed unsupported claims and weak synthesis remain. Verified fallback is not model reasoning. |
| G6 | IN PROGRESS | New hand-defined forwarding conformance increment accepted separately; full causal-answer/variant matrix remains open. |
| G7 | IN PROGRESS | 42/141 unique native journeys pass after explicit engineer review. Full browser, negative/multi-operation, extensibility and genuine Ansible gates remain open. |
| G8 | IN PROGRESS / browser gate failed | Coordinated editing implemented and actual-model API case passes. Two browser model patch requests fail safely. Group-review controls have not yet received real browser acceptance. |
| G9 | IN PROGRESS | Reuse G3 document/source proofs; full ordinary-mode parity, restart and contextual integration remain open. |
| G10 | IN PROGRESS | Protected buffers, standard server recovery and app-level clipboard proofs retained. Full service/UX and OS clipboard gates remain open. |
| G11 | IN PROGRESS | Permanent exposed evaluations retained. Full frozen unseen intelligence benchmark remains reserved and NOT RUN. |
| G12 | NOT RUN | Final integration cannot close while these acceptance failures remain. |

## Changes and evidence in this continuation

### G3 closure

All source reviews and final complete-starter browser/export proof are indexed by `tmp/phase-g/iterations/20261022-G3-source-acceptance-resume/G3-stage-acceptance-review.json`. The final source counts are 24/24, without counting a shared multi-source turn multiple times as independent model successes. The earlier 18/24, 22/24 and 23/24 checkpoints remain historical.

### G7 actual native journeys

`backend/scripts/evaluate_phase_g_native.py` drives authenticated shared gateway requests, the existing owned V9 review session, explicit parameter/target/template correction, revision-checked confirmation and actual unsaved native rendering. It checks exact fixture output, target, release, digest, no hidden saving and no device execution. Expected outputs come from the existing engineer-approved regression fixtures; they are not independent vendor/device certification or unseen intelligence tests.

The frozen 141 specifications are in `docs/evaluations/phase_g_native_journey_cases_v1.json`. Original failures and corrected reruns remain under `tmp/phase-g/iterations/20261022T082839.745087Z-G7-native-journeys-2a3cb6/`.

Confirmed defects and corrections:

- Two first attempts timed out. Timed stack traces confirmed V9 was waiting on an uncapped streaming model response for JSON planning. `backend/local_providers/v9_worker.py` now configures the existing ChatOllama transport with JSON output, 1,024 generated tokens, 8,192 context tokens and a 45-second read timeout. V9 interpretation, schema/context validation and rendering remain authoritative.
- The evaluator initially invented an unreviewed model-family name. Controlled scenarios now reuse recorded planned profiles; their explicitly authored capabilities and resources remain development facts. Huawei VRP 8 is not silently renamed to the different version demanded by some existing resource policies.
- The evaluator reached the application’s 40-draft retention limit. It now reuses one evaluator-owned draft with optimistic revision checks. No application retention limit was increased and no ordinary scenario was removed.
- New bounded worker observations preserve actual model replies/counts and separate transport success from semantic correctness. The evaluator now captures the initial worker body before review overwrites it. Earlier traces lacking these observations must not be assigned invented model-call counts.

`backend/scripts/preflight_phase_g_native.py` exercised all 141 bindings through actual V9 review in batches under existing device/draft limits. The unchanged raw traces were regraded after correcting an evaluator mistake: a V9 task status of `validated` is a successful individual preflight, not a blocked task. Original classifications remain preserved. The corrected result is 68 eligible and 73 blocked. These preflights receive **zero native-journey or model-reasoning credit**.

The 73 include controlled-source prerequisite gaps, invalid fixture choices, and genuine catalog/context-profile conflicts. For example, some Huawei bindings target VRP 8 while the relevant resource policy demands another exact recorded version. An OSPF stub-area fixture selects backbone area 0. Do not disable those checks or label these combinations accepted. Some source gaps can be repaired through truthful controlled scenario authoring; policy/schema conflicts require their proper reviewed integration path.

A critical limitation remains: the first audited positive journeys did not contain an exact complete parameter set before review. Some requests were fragmented into parameter-only intents; others lost values. Final correct native output after explicit engineer correction is useful workflow evidence, **not reliable one-shot understanding**. G4/G5 remain open.

The active release has zero published validated Ansible variants. Native CLI files and editable reference wrappers do not count as genuine Ansible coverage. The approved pinned validation profile remains a separate prerequisite; no heavyweight dependency/model or unsafe validator was installed.

### G8 related files and guarded coordinated edits

`backend/llm/gateway_workspace.py` reuses `AuthoringStore` for bounded static YAML/Ansible references: literal `vars_files`, task/playbook includes/imports, local roles and `include_vars`. It does not evaluate dynamic Jinja or fetch remote paths. Transitive/circular references, missing files, path escape and source budgets remain explicit. Open Monaco snapshots override saved text only for relevant authorized references. Unrelated stale open tabs do not impose revision dependencies or enter model context.

The existing `document.read` and `document.propose` capabilities now coordinate related files. Optional `related_editors` preserve the original empty-request serialization for legacy idempotency. Floating rejects automatic editor/related-editor context. Studio proposals retain per-file model identity, exact base/digest and saved revision; cached bundles recheck every affected saved revision. A read-only revision endpoint supports the final UI acceptance check.

Studio has per-file diff navigation, Accept All/Reject All and coordinated Undo. The centralized Monaco buffer transaction rejects stale bases and rolls back earlier file changes if a later application fails. Save remains separate. This implementation is integrated; its full browser acceptance is still open.

Actual-model evaluation: `tmp/phase-g/iterations/20261022T093103.114515Z-G8-real-workspace-6ff55f/actual.json` passes the two-file instruction with qwen2.5:1.5b, the real shared LangGraph and authorized proposal tool. The model changed the authoritative variable and requested marker while preserving every other byte. No file was saved. This is one exposed successful model patch, not a broad reasoning benchmark.

Browser requests in conversations `2a856e20-15f7-4c22-97a3-c6a64a74fac1` and `cfd108ad-629a-4507-87f8-9e3e5fe89a48` failed safely. The second retained raw attempt shows qwen putting a variable-file anchor into the playbook patch and proposing an unchanged variable file. The exact-base guard rejected both attempts. No valid browser proposal was available to test group Accept/Reject/Undo; those actions remain NOT RUN. The correction loop was stopped rather than relaxing anchors or claiming a GUI pass.

Two explicitly named empty browser fixture files were created using New File. Their source content stayed unsaved. `G8-state-preservation.json` proves pre-existing authoring/audit rows and every other ordinary business table unchanged, with only those two empty fixture records and authorized AI history writes added. All test and protected editor buffers remained exact. Model failures, source hashes, screenshots and original/corrected test logs are retained in the continuation audit directory.

### G6 conformance increment

Sixteen hand-defined forwarding cases exercise the existing authorized `network.state` reader on both surfaces: healthy multihop, administrative/operational down, missing/incomplete routes, discard, negative/unavailable neighbor resolution, longest-prefix and preference selection, forwarding loop, ingress/egress policy, recursive next hop, subnet incompatibility and VRF isolation. Expected outcomes are private evaluator files, excluded by the existing oracle path guard.

The first VRF fixture was invalid because its requested endpoint VRF was unrecorded. The corrected fixture records RED endpoints and keeps UNKNOWN/UNKNOWN for missing RED tables. Its obsolete reason assertion was separately corrected, with v1/v2 originals retained. Fifteen cases pass in the full corrected run, and the affected VRF case passes its focused rerun: **16 unique cases / 32 authorized reader invocations**, not 31 unique successes. No simulator code was changed. No LLM was called and no full G6 reasoning acceptance is inferred.

## Tests run now

- Affected backend release suite: **255 passed, 10 subtests passed**, 59.99 seconds. Earlier 85/134/etc. suites overlap and must not be added.
- Monaco transaction tests: **4 passed**, including second-file failure rollback and stale-base rejection. These are model-unit tests, not browser acceptance.
- Latest V9 observer suite: **11 passed**. Transport success is explicitly not semantic correctness.
- TypeScript build validation: PASS.
- Independent conformance: 15 full-run passes plus the corrected affected VRF pass; 16 unique cases. Original collection/fixture/assertion failures remain archived.
- Actual qwen coordinated-edit API case: PASS. Two actual browser coordinated-edit requests: FAIL safely. Do not turn these heterogeneous exposed cases into a claimed general reasoning rate.

## Preservation and runtime

HEAD remains `6e8597c08315e96887ed91004f4ebf418ca600bb`. The former 52-file staged checkpoint is historical because that existing user commit incorporated it; the current index remains empty. The original patch archive retains SHA256 `d6aa68e47ae3b44449d1f832404ad925a373791b845ec064d067b8e8b028d7f8`.

Active release remains `7a14a351e52b49aeb87f65d1192f0937`, manifest SHA256 `bdb1cad94c4275081ce9b9aaaa3bbfadd9b38a73b201f67277aa1d7be69694b5`, with 47 operations, 141 native bindings and 341 integrity-checked artifacts. No publication, sibling V9 source edit, model download, automatic commit/stage or device action occurred.

The protected 204-LF-character buffer retains SHA256 `b4c9fe532f11100c172b383f5766de4cb5e0ae5cd165378b258395ca83a93632`. Browser clipboard proof is separate from unverified OS clipboard support. The only app pair remains 5173/8000, launcher session 47270 / backend PID 20048 at this checkpoint; verify ownership freshly before restart. Ollama remains the existing process/model.

## Exact continuation

The native evaluator stopped at its explicit source-pin boundary after 42 successful unique journeys. Resume it using the command in `PHASE_G_CONTINUATION_CHECKPOINT.md`; reuse its database/draft and existing PASS records. Do not duplicate or count successful reruns as new cases.

Current browser work is the controlled three-vendor native generation slice. The imported scenario is `G7-BROWSER-CONTROLLED-20261022`; ordinary sources were disabled before activation and must be restored after the browser slice. Cisco OSPF review is pending; target/router ID have been explicitly corrected and Apply Changes was clicked. Inspect the actual browser state before the next action. Preserve every unsaved tab, including the two G8 fixtures.

Then finish remaining eligible G7 cases and proper fixes for the rejected cohorts; keep G8’s browser model failure open, and proceed with every remaining G4–G6/G9–G12 acceptance gate. The frozen unseen benchmark remains NOT RUN. Do not declare Phase G complete from these partial increments.


## Actual browser continuation — 23 October 2026

G1–G3 remain complete. G7 now has 59/141 unique native journeys at this checkpoint; the compatible batch continues in the existing disposable workspace. Representative three-vendor browser acceptance passes: prior Cisco OSPF, new Juniper static route and Huawei BGP. Each used real Studio/V9 review, explicit confirmation, exact native output and unsaved Monaco creation. The model still needed target/parameter correction; no one-shot extraction claim. The prior pending review dialog did not survive page recovery, so Juniper was reopened through a new actual Studio turn. Duplicate binding checks add browser evidence only.

Ordinary sources restored; all unsaved tabs retained. Protected 204-character buffer hash unchanged, active release and all 341 artifacts intact, original patch archive and empty index unchanged. Ordinary non-AI tables and pre-existing authoring, audit and evidence rows match the saved baseline. Only owned AI results/V9 sessions and preview audit entries changed. Detailed proof: `tmp/phase-g/iterations/20261023-G7-resume`.

G6 gained twelve independent ECMP/ACL/protocol/metric cases. First run: 10 passed, two evaluator selector errors. Corrected existing telemetry query: all 12 passed, with independent expectations unchanged. Total 28 unique deterministic cases / 56 authorized surface reads, no model credit. Full G6 causal-answer gate stays open. The new compound/negative G7 evaluator is implemented but not yet executed; serialize it after the native batch. G0 baseline, G4–G6, G8–G12 remain open or blocked as recorded in the updated Oct23 progress audit and checkpoint. No automatic commit, publication, model download or device action.


## Continued G7/G9 verification — 2026-10-23T00:29:59.376411+00:00

G7 currently 79/141 verified native journeys;32-case new compatible batch running. All141 reviewed source fixtures reconcile to100ready/41blocked, zero preflight journey credit. Explicit planned prerequisites fixed missing VLAN/ACL/QoS/OSPF and creation-target collisions; V9 policies and immutable methods unchanged. Original quota413 and evaluator summary error retained; same disposableSQLite with bounded new scenario-state files, no quota increase or data deletion. Three-vendor compound and five negative API checks pass; no active validated Ansible variants.

G9 ordinary named-port bug fixed across resolver, LangGraph identity binding, query contract and telemetry providers. Actual first scoped reads exposed label swapping and omitted values; full review corrects the raw numeric-only observer. Shared ordinary metric projection/label verification prevents that unsafe output. Both actual corrected responses use exact factual fallback. Correct model repair wording was initially falsely rejected; replay regression fixed, not credited as a new model success. Normal mode could read legacy simulated JSON; reproduced with actual registered reader and blocked using existing mode authority. Full G9 gate remains open.

Evidence and exact next command/state are in `tmp/phase-g/iterations/20261023-G7-resume` and the latest top checkpoint.220affected tests passed before final normal-mode guard; its selected isolation test passes, final combined rerun pending. All prior failed results remain. Browser ordinary-mode cold restart and exact protected204LFbuffer passed. Standard server currently predates final two small corrections and must be refreshed before browser claims. No new fullstage closure or broad reasoning score.


# Current verified continuation — 2026-10-23T02:02:34.936872+00:00

**G1–G3 COMPLETE. G7:109/141 unique native journeys PASS;32Huawei compatibility blockers. No new full-stage closure.** The109artifacts have been rechecked against exact frozen expected output, V9 ready/release metadata, explicitconfirmation, no-save and no-execution flags. Five valid positive V2 inputs retain original V1 negatives. Three-vendor browser slice and actual compound+five rejection checks pass. Active validated Ansible variants:0. These are reviewed native workflow results, not one-shot extraction/model-reasoning or device certification. Raw119executions are not119unique passes. Proof:`tmp\phase-g\iterations\20261023-G7-resume/109-native-journeys-review.json`.

G0 historical pre-change freeze remains BLOCKED; current preservation passes. G4–G6/G8–G12remain open.221affectedtestsPASS; G10revisionpresentation16tests+3subtestsPASS(overlap). G6private independent deterministic28cases/56readsPASS; actual causal both-assistant10case evaluation now running session50047, log`tmp\phase-g\iterations\20261023-G7-resume/G6-causal-model.log`; prose and model-vs-fallback review pending. Do not claim source-only checks are causal-quality acceptance.

Fresh browser access succeeds. App servers had stopped; restored exactly5173/8000 launcher64530/backend10312 with latest source. Ollama20988unchanged. Reload browser at safe boundary and verify exact protectedbufferSHA b4c9fe532f11100c172b383f5766de4cb5e0ae5cd165378b258395ca83a93632. Ordinary sources were restored before interruption. Existing active release7a14a351e52b49aeb87f65d1192f0937/index/archive/user records remain protected. No commit/stage/publication/download/save/device action.

Next: inspect causal evaluator outputs, independently grade complete answers, preserve failures and continue next feasible opengate. G8two browser patch-source failures remain safe and unaccepted; do not repeat exposedprompt loop. G10history review-modal rehydration remains a distinct open defect. Huawei conflicting contracts require proper authoring correction, not false profilefacts or sibling edits.

---



# Verified stage closure — 2026-10-23T03:51:36.228109+00:00

**G10 COMPLETE/PASS** under its specified allowance for a documented external OSclipboard BLOCKED result. G1–G3 remain COMPLETE. No OSclipboard success is claimed; exact browser-session whole-answer/code/UnicodeCopy passes in both assistants. Latest ownedV9review revision2/routerID198.51.100.144 reopens after reload; stale scenario reviews reject; Escape returns focus; exact204LFbuffer unchanged; no saved-file/business/active341artifact/index changes or runningturns.237affectedbackendtestsPASS, TypeScriptPASS; overlapping34+3subtest and11flow runs are not summed. Proof:`tmp\phase-g\iterations\20261023-G7-resume/G10-stage-acceptance-review.json`.

G7 is109/141 verified unique native journeys;32Huawei compatibility blockers remain, zero activevalidatedAnsiblevariants. G8browser coordinatedpatch class remains safely failed. G0 historicalfreeze remainsblocked. G4/G5/G6/G9/G11/G12 remainopen.

G6actual20unique cases:20correct source reads but6released qwen answers were incorrect despite literal checks. Original reports retained; latest corrected coverage uses4adequatemodelanswers and16fallbacks. Unknown-flow class exhausted2corrections; bothunknowndirections now return scoped calculatedfacts/time/nextread with zero synthesis calls. No freshbenchmark/humanrating credit. Newexplicit-generation+negativeeditor-clause browserprompt wrongly routed to explanation; archived underG4, no prompt-tuning loop.

Current app launcher97363/backend21708,5173/8000; Ollama20988untouched. Ordinarysources active, all unsavedtabs retained. Current nextindependent gate:G9scannedPDF and real persisted-reference/revision continuation, reusing earlier document/OCRsource results. Continue all mandatoryopengates; no commit/stage/publication/download/deviceaction.

---



# Safe continuation — 2026-10-23T04:32:30.605528+00:00

**Completed stages:G1,G2,G3,G10. G7:109/141unique nativejourneys,32Huawei policy/profile blockers;0activevalidatedAnsiblevariants. PhaseG incomplete.** G9new actualmemory across2separateOSprocesses restores bothassistantinterface refs, rereads changed192.0.2.88, isolates14arithmetic and otherowner404. Actual scannedPDFWindowsOCR reads88/12/48,page1onboth, followupsproposed. Normal-modegateway branch refuses validlocalJSONCPU97.375 with livereads0; no physicalcollection. Firstuploadedcfg4answers had wrongBGProuterID/deviceupload assertions despite literalPASS. ExistingMonacoCLIguard nowreused insharedverify_ocr_answer;61tests+7subtestsPASS and corrected4actualresponses use labelledliteralreconstruction. Source/metadataandmodelcredit distinct. ScannedFloatingunrequestedglossremainsqualitylimitation; no fullG9closure. Review:`tmp\phase-g\iterations\20261023-G7-resume/G9-continuity-full-review.json`.

Current G8: independentreference-only browsercase producesvalidanchor2fileproposal, butaddsduplicateplaybookcomments despitenochangeinstruction. Rejectedall; exactmain/varsbaselinepreserved. FirstobserverswitchedMonacotooquickly and copiedprotectedbuffer; wrongobserverretained, correctedbaselineverified viafreshDOMbeforecopy. No contentchanged. Storedproposal+failure:`G8-reference-original-failure.json`;Rejectproof:`G8-reference-reject-proof.json`. No Accept/Undo credit. Nextfix isapplication-level explicitpreservation inexistingvalidate_edit_intent/propose_related, not another exposedpromptrewrite.

Standard app97363/backend21708 on5173/8000 isrunning, butpredates uploadedfileguard; loadthat testedfixatnextsafeownedrestart. Browser2/tab1phaseGTab, activeG8main, protected204LFtabretained, ordinarysources. NewG9evaluations reuse tmp/g7-native-47236e/app.db andone disabledg9scenario store; no ordinaryDBfixtureswritten. seed/resume refs areg9-continuity-reference.json. FrozenV1hash2ad1c5ee18d7f2961b4b5a7cac3bf092c41b7c92dd600719ada370d928ceb8e6verified, normalV2/configV3separate. No newdependencies/models/publication/stage/commit/savedfiles/deviceactions. Continueallopengates.

---



# Safe continuation — 2026-10-23T05:07:56.806287+00:00

Completed full stages: **G1,G2,G3,G10**. G7 remains **109/141**;32Huawei profile/policy conflicts and0activevalidatedAnsiblevariants retained. G8 reference-only browser edit now PASS: correct unsaved var-file patch in1qwen attempt, active playbook unchanged, RejectAll proof reused, AcceptAll/Undo exact, no save. A real application bug omitted restored inactive tabs without Monaco models; fixed using existing open-tab content/URI, bounded8. New5frontendtransactiontests andTypeScriptPASS;139affectedbackendtests+7subtestsPASS, overlaps not added. Original two-changed-file browser rerun still fails model file-assignment safely. FullG8 **FAILED**, not complete; correction loop ended. Raw proposals/red/green proofs preserved under `tmp\phase-g\iterations\20261023-G7-resume`.

Prototype ZIP inspected read-only from Downloads; no archive code executed or unpacked. Its builder.py561–587 DOES include hosts;inventory.py40–154 supplies inventory and Vault credential references, runner supplies inventory separately. G8hosts/vars_files were a synthetic edit fixture, not nativeoutput or credentials. Findings:`tmp\phase-g\iterations\20261023-G7-resume/prototype-inventory-architecture.json`. Preserve validtargetselector and keepconnectioncredentialsoutsidegeneratedcode.

G4generalized scope correction: exclusive registered source constraints precede generic path→topology hints; extra model readers still rejected. Source-health subject no longer mistaken for unresolved document pronoun.139affectedtests+7subtestsPASS; real-model retest pending. Not modelreasoning credit.

Current standard launcher58844/backend29648,5173/8000;Ollama20988 unchanged. Ordinarysourcesactive,protected204LFbuffer and all17tabs retained; finalpreservation recheck pending. Next execute existing frozenF cohorts with optional --continue-on-failure, preserving per-case failures rather than another microfix loop. This flag changesexecutionorderonly, no acceptance criteria. FreshG11≥120/≥30 cohorts still required separately. No commits/staging/publication/newmodel/deviceaction.

---



# Frozen evaluation continuation — 2026-10-23T07:37:54.909410+00:00

Completed full stages remain **G1, G2, G3, G10**. G0 historical baseline BLOCKED; G7 109/141,32Huawei contract blockers,0validatedAnsiblevariants; G8 two-changed-file browser case FAILED. No new fullstage closure.

Historical120 candidate completed: **101/120 routing/workflow PASS**,19FAIL. Compound12/30, othergroups89/90; no answerqualitycredit. Matchedlegacy session70102 runs in `tmp\phase-g\iterations\20261023-G7-resume/G4-frozen-120-legacy.log`; inspect final result before retry. Historical30 M2fullreview14adequate/30(4modeltext,10fallback/direct). M0/M1/M3fullreviews3/11/6adequate of29executed;one case NOTRUN afterrealsetupfailure. Noexternalhumanrevieworfreshgatecredit. Evidence:`tmp\phase-g\iterations\20261023-G7-resume/G4-complete-frozen120-candidate-review.json` and `G5-frozen-30-comparison-arm-review.json`.

Freshspecs frozenbeforeinference: `docs/evaluations/phase_g_fresh_routing_v2.json` SHA91c820af570052694ec645307390a12d202018f7bb79a580c4841a18d9b33d90(120,existingcomplete24sourcebundle); `phase_g_fresh_quality_v1.json` SHA733ed224b95f55fb389c35d0ce4a1434a7986f1e2cbc647a5c60ea5b2228bc5a(30,newprompts/editor/PDF/rubrics). BothNOTRUN. Evaluator --registry validatescontainedinput,uniqueIDs,scenarios and realownedbundleactivation;20focusedtestsPASS. Sourcecredit requires returnedreader envelopes,not a modelplan.

Confirmed applicationdefect: genericcontextbounder turnslarge publishedcontracts intoopaqueJSONexcerpts, thenprovenanceverificationrejectsthem. Repeatedread verificationmatches toolname instead of readidentity. Three redtests retained. Next: finish legacyruntimeboundary,retain typedcontract andbindverifytoactualevidenceIDs,keep tamperchecks;affectedtests+actualread;thenfreshcohorts. Noindividualpromptrepairloop.

Runtime launcher24090/backend24232,5173/8000;Ollama20988unchanged. Freshbrowserworks;all17tabs andprotected204LFbufferexacthashPASS. `G11-current-preservation.json` confirms141bindings,341artifacts,intactindex/archive,SQLiteintegrityok andzerotablechangesversuslastG12proof. NoSave/stage/commit/publication/deviceaction.

---



# Frozen routing cohort complete — 2026-10-23T09:09:28.152941+00:00

Current stage: **G4/G11**. Completed full stages: **G1, G2, G3, G10**. No new full-stage closure.

- Fresh120 candidate: **86 PASS /34 FAIL**; matched legacy: **71 PASS /49 FAIL**. Candidate uplift15 workflow passes,12.5 percentage points. G4 fails its90% gate. No answer-quality inference.
- Runtime446-file freeze and registry unchanged through both cohorts. Original answers, plans, source/evidence and errors retained in `tmp/phase-g/iterations/20261023-G7-resume/G11-fresh120-matched-review.json`.
- Confirmed application defects: typed documentation lists reached dictionary-only gap planning, record disclosure and AS-role verification; available ambient files biased unrelated questions; a capture comparison could authorize unsupported interval-stability prose. One shared correction passes **287 affected tests**; original red results retained. This is application verification, not fresh reasoning success.
- Six exposed class replays run in session67570, `tmp/phase-g/iterations/20261023-G7-resume/G4-exposed-shared-boundary-replay.log`. Reuse completed cases; do not rerun the entire routing cohort or count these as unseen.
- Next untouched30-case quality spec: `docs/evaluations/phase_g_fresh_quality_v3.json`, SHA87c24c9cfcb80b3c8b91496b6aa437cfd1db4ec523446ab69c9e5e9b1d42b8a1. Frozen before inference. Raw M1 gets independently specified transit context and no verifier repair/fallback; M0/M2/M3 remain separately attributed. Runtime freeze `tmp/phase-g/iterations/20261023-G7-resume/G11-quality-runtime-freeze.json`. Do not edit runtime/spec during the quality cohort.
- G0 historical baseline BLOCKED; G7 **109/141**,32Huawei contract/profile conflicts;0active validated Ansible variants. G8 original two-changed-file browser case safely FAILED; reference-only Accept/Undo proof retained. G6/G9/G11/G12 remain open. G5 model-quality hard gate unproven.
- Browser access works, tab2 preserved, all17unsaved tabs retained. Standard pair launcher8907/backend17112 uses the earlier runtime until an owned reload; Ollama20988 untouched. Protected204LFbuffer proof and ordinaryDB/active141binding/341artifact/index preservation PASS. No stage, commit, Save, publication, model download or device action.

Continue the existing scope after the quality cohort: remaining G6 independent causal cases, G9 gate review, G12 preservation/integration; keep genuine FAIL/BLOCKED conditions explicit. Do not claim PhaseG complete.

---



# Verified continuation checkpoint — 2026-10-23T10:19:48.423468+00:00

**Complete stages: G1, G2, G3 and G10. Current: G6 extended conformance / G9 context acceptance. Phase G remains incomplete.**

| Stage | Status | Exact remaining gate |
|---|---|---|
| G0 | BLOCKED | Current preservation passes; original pre-change freeze absent, cannot backdate. |
| G1–G3 | COMPLETE | Source protocol,24-source JSON/revisions and24/24 GUI/both-assistant acceptance reused. |
| G4 | FAILED | Fresh120candidate86/120 versuslegacy71/120; below90%. |
| G5 | FAILED | Fresh30full-task M2adequacy5/30;24FAIL+1invalid-contextBLOCKED. Four direct/review/reconstruction answers, one simple model negative lookup;0adequate causal reasoning. |
| G6 | IN PROGRESS |28deterministiccases/56readspass. Extendedactual protocol/metric source defects corrected;16case/surface reruns pending full-answer review. |
| G7 | BLOCKED |109/141nativejourneys;32Huawei contract/profile conflicts;0activevalidatedAnsiblevariants. |
| G8 | FAILED | Reference-only coordinated Accept/Undo passes; original two-changed-file browser assignment fails safely. |
| G9 | IN PROGRESS | Document/page/editor shared binding fixed; new actual content replays and retained restart/OCR/isolation proof awaiting criterion closure. |
| G10 | COMPLETE | Existing UI/service acceptance, browserclipboardPASS; OSclipboard externalBLOCKEDexception retained. |
| G11 | IN PROGRESS | Fresh120+30 executions and full reviews complete; required intelligence/engineering acceptance still fails. |
| G12 | IN PROGRESS | Current ordinaryDB/341artifact/index/protectedbuffer preservation PASS; final integration/report pending. |

Fresh quality comparisons: M0=2/30adequate, rawunrepairedM1=2/30, M2=5/30, M3=1/30. SevenM1additional factual/code partials explicitly recorded, not full task passes. No external blind human reviewer claimed. Source workflow successes and fallback do not earn reasoning credit. Original sevencritical failures retained. Frozen specs/runtime unmodified through execution; postcohort fixes are exposed only. Reports:`tmp\phase-g\iterations\20261023-G7-resume/G11-fresh30-full-answer-review.json` and`G11-fresh120-matched-review.json`.

One grouped safety/context correction passes293tests+7subtests. Shared path/protocol routing increment passes295+7 and124focused source/conformance checks, overlapping runs not summed. Saved original state/direction/scope/protocol drafts reject under bounded verifier; this is not universal semantic certification. Actual document replays preserve uploaded note, second/third page values and honest missingpage9; Floating editor-snapshot request remains403bydesign. No full30 rerun or score rewriting.

G6 first20extendedcase/surface outputs:8correctsource paths,12protocolrequests wronglyreturned inventory; separate4metric paths read CPU samples rather than interface series. Original answers retained. Corrected8variant/16surface run session26486 at`tmp\phase-g\iterations\20261023-G7-resume/G6-extended-corrected-8.log`. Next: inspect exact records AND fullprose, record remaining failures, then G9browser/criterion audit and G12integration. Do not open another exposed-prompt tuning loop.

Standard app launcher22395/backend29396,5173/8000; Ollama20988untouched. Server loaded document/safety fixes before latest source-domain edits; reload ownedpair once before final browser acceptance. Fresh browser tab1/browser2 works;17unsavedtabs retained. Protected204LFbuffer SHA b4c9fe532f11100c172b383f5766de4cb5e0ae5cd165378b258395ca83a93632 unchanged. OrdinaryDBintegrityOK, zeroordinarytableschanged, active release7a14a351e52b49aeb87f65d1192f0937/141bindings/341artifacts and index/archivedpatch unchanged. Existing userHEAD6e8597c incorporated historical52-file checkpoint; indexempty. No commit, stage, Save, publication, download or device action.

---



# G9 verified stage closure — 2026-10-23T12:52:53.591771+00:00

**Completed: G1, G2, G3, G9 and G10. Phase G is incomplete.** G9's nine criteria passed: existing document/OCR/page retrieval, both actual browser assistants, source-bound follow-ups, unsaved editor identity, durable reference refresh, ownership and ordinary/simulation isolation. Proof: `tmp\phase-g\iterations\20261023-G7-resume/G9-stage-acceptance-review.json`. Actual controlled browser turns and screenshots are retained. Proposed-only documents establish neither current use nor non-use; their final answers use a labelled source-insufficiency fallback. No model-reasoning credit or general vision claim.

G0 is blocked by the missing original historical freeze; current preservation passes. G4 routing failed86/120 (legacy71/120). G5 fresh quality failed5/30 adequate full tasks with0adequate causal reasoning. G6 extended actual source checks20/24, explanations inadequate; metric logical-source filtering is the next service defect. G7 remains109/141 with32Huawei contract conflicts and0activevalidatedAnsiblevariants. G8's original two-file model test fails safely; reference-only Accept/Undo passes. G11 evaluation infrastructure/results exist but quality acceptance fails. G12 final integration is open. Implemented does not mean accepted.

Current next work: repair the shared source-contract mismatch for modeled metric series without relabelling their provenance; run affected authorized-reader and real-gateway checks; finish final integration and preservation. Do not rerun or alter frozen scores, reset/stage/commit, change active V9 artifacts, download models or execute device actions. Standard app5173/8000, ordinary sources, retained17unsavedtabs/protected204LFbuffer. Prior failures and bounded correction limits remain in force.

---



# Verified continuation and acceptance report — 2026-10-23T13:16:40.782159+00:00

**Completed stages: G1, G2, G3, G9, G10 and G12 (release-safety/handover only). Phase G is partially complete.** “Implemented” never means the original acceptance gate passed.

| Stage | Implementation and acceptance |
|---|---|
| G0 | Partial/BLOCKED: current preservation passes; original pre-change frozen registry and fully attributed baseline are missing. Cannot backdate. |
| G1 | COMPLETE: authorized source registry and normalized protocol. |
| G2 | COMPLETE: 24-source JSON, revision, clock and CLI foundation. |
| G3 | COMPLETE: all 24 sources individually accepted through JSON, GUI, activation and both assistants; actual proofs reused. |
| G4 | Implemented, FAILED acceptance: fresh routing 86/120 (71.7%), matched legacy 71/120; required-tool recall 105/126; 20 unexpected of 129 selected instances; no-tool cases 12/23. |
| G5 | Implemented, FAILED acceptance: fresh full-task M2 adequacy 5/30 (24 FAIL, 1 invalid-context BLOCKED), below 85%. Four factual/review paths and one simple model negative lookup; zero adequate causal model explanations. Original implementation defects and residual model limits are distinguished. |
| G6 | Implemented, FAILED acceptance: 28 independent deterministic cases / 56 authorized reads pass. Corrected extended evidence covers 24 unique case/surface pairs; causal prose still fails. The latest four metric cases retrieve calculations correctly but all release factual fallback. |
| G7 | Partial, BLOCKED acceptance: 109/141 native Studio-to-V9 journeys; 32 Huawei profile/policy conflicts. All 141 bindings are active, which does not establish 141 successful journeys. Zero active validated Ansible variants. No compatibility bypass or knowledge change. |
| G8 | Partial, FAILED acceptance: reference-only real-model and GUI Reject/Accept All/Undo pass; the original two-file qwen anchor-to-file assignment fails safely. No further exposed wording loop. |
| G9 | COMPLETE: nine document/OCR/page/reference/restart/ordinary-isolation criteria verified; proposed documents establish neither use nor non-use on devices. No general vision or model-quality claim. |
| G10 | COMPLETE: actual browser, restart, review, copy and service gate; external OS clipboard remains blocked under the specification's explicit exception. |
| G11 | Evaluation implemented, FAILED acceptance: fresh 120-case routing and 30-case full-answer cohorts finished; original failures retained. Intelligence, engineering and causal non-regression criteria are unmet. No external blind human assessment claimed. |
| G12 | COMPLETE for release-safe verification and honest partial handover, not overall Phase G acceptance. Current authenticated runtime, 373 affected tests, unchanged frontend and reused UI proofs, 141 bindings / 341 artifacts, ordinary data and index preserved; zero running turns. Fresh browser-tool failure is disclosed. |

This continuation repaired two confirmed shared-service root causes. First, the simulation source was incorrectly assumed to have one reader although its typed data spans state and telemetry. The registry now declares compatible readers and record kinds, reused by planning, input validation, restored references and status/capture projection. Second, metric synthesis discarded computed utilization/reset/correlation fields and cut off correlated series after eight rows. Those typed facts and dependencies now reach actual model inputs; the existing global input budget remains enforced. The factual fallback formats calculations readably. No new database, parser, model, RAG pipeline or device capability was introduced. Original failures are archived and frozen benchmark scores are unchanged.

Evidence: `tmp\phase-g\iterations\20261023-G7-resume/G9-stage-acceptance-review.json`, `tmp\phase-g\iterations\20261023-G7-resume/G12-stage-acceptance-review.json`, `tmp\phase-g\iterations\20261023-G7-resume/G6-metric-contract-full-answer-review.json`. Final affected suite: 373 PASS; adjacent scenario suite: 91 PASS. Overlapping earlier 131/115/372 runs are not added. Current runtime API: both assistants return R2's stored management IP 192.168.1.251, then answer 7+8=15 without network/editor/attachment context; another owner's GET returns 404. API checks are not browser acceptance. All four metric reruns have correct records and actual model inputs, but incorrect/unavailable model prose and factual fallback: no reasoning-quality credit. The seven original source-contract failures and first projection failure remain preserved.

Fresh browser reconnection attempted `cua.rewriteDocumentation()` and, after reset, `cua.getTab('1', { browser:'2' })`. Both returned **failed to write kernel assets: The system cannot find the path specified. (os error 3)** before accessing the page. This independently verifies tool initialization failure. Browser-settings disablement, website permission denial and browser connectivity failure are not established. Prior actual G9/G10 GUI proofs are reused; no fresh buffer read or GUI pass is claimed. The last exact protected 204-character LF buffer / 17-tab proof is `G11-resumed-buffer-proof.json`. No editor or saved-file changes were made. All 100 frontend runtime files match the previously frozen, browser-tested build.

Current runtime: launcher 79621 / backend PID 28856 on 5173/8000; Ollama PID 20988 on 11434 untouched. Ordinary mode; no scenario activation on the ordinary database. Active V9 release: 7a14a351e52b49aeb87f65d1192f0937, 141 bindings and 341 verified artifacts. HEAD 6e8597c and the empty Git index are unchanged; the original 52-file patch archive hash d6aa68... is preserved. No staging, commit, publication, model download, Save, deployment or device action. Source changes remain uncommitted.

Exact continuation: recover browser-tool kernel asset initialization before new mandatory GUI acceptance. The next unresolved engineering deliverable is G8's original transaction changing two files; it needs source-bound coordination, not more prompt wording. Its exposed correction limit has been reached. G7's 32 Huawei conflicts cannot pass by editing the read-only sibling V9 repository, immutable releases or device identities. G4/G5/G6/G11 remain failed pending substantive improvements and independently frozen new evaluation after the foundations are ready. Do not count exposed 120/30 cases as fresh, weaken thresholds or mark overall Phase G complete. Preserve current code, proofs and state. Resume commands and complete traces remain in the audit directory above.

---



# G8 source-bound workflow verified — 2026-10-23T14:25:40.562216+00:00

Completed workflow stages: **G1, G2, G3, G8, G9, G10**. G12 release-safety/honest handover remains complete subject to this continuation's final preservation check. Overall Phase G remains **partially complete**. G0 historical baseline remains deprioritized/BLOCKED; G4/G5/G6/G11 acceptance FAILED; G7 remains109/141 with32Huawei conflicts.

G8 original two-file request now passes through actual shared LangGraph/qwen/API and browser with1patch call per successful proposal. Content-addressed exact anchors are bound by the server to authorized unsaved snapshots; explicit refs must match their own source and are never relocated. Existing revision, exact-base, structural, preservation and authorization checks remain. Reject keeps both files byte-equivalent; AcceptAll makes only variable22-to23 and markerBEFORE-toAFTER; coordinatedUndo restores exact baselines; a concurrent manual editor edit causes stale rejection and is preserved. No Save. Protected204LFbuffer hash remains b4c9fe532f11100c172b383f5766de4cb5e0ae5cd165378b258395ca83a93632. All17tabs retained.28focused contracts,140adjacent(overlap),5frontendtransactions,2handoff checks PASS. Ordinary business/saved authoring records, HEAD/index and341V9artifacts unchanged; no running turns. Evidence: `tmp\phase-g\iterations\20261023T140002.093180Z-G8-source-bound-architecture-6a21a0/G8-stage-acceptance-review.json`.

Original wrong-file failures and failed first architectural attempt are preserved. Additional frozen YAML+JSON variant FAILS task completeness: qwen saw both sources but proposed only the main comment change, omitting the JSON peer update. Retained underG4 compound understanding/G5 adequacy; no success credit. G8 closure is the source-aware proposal/review gate, not universal prompt completion. No wording retry or fallback authoring. Frozen120routing and30quality scores unchanged.

Current runtime: standard5173/8000 launcher29302/backend8104, ordinary mode; Ollama20988 unchanged. Fresh built-in browser works; protected tabs restored. Next: remaining G7 contracts/current validator availability, then G12 integration. Do not bypass profiles, mutate active knowledge, download models, stage or commit.

---



# Current verified Phase G continuation — 2026-10-23T14:40:52.460179+00:00

**Newly verified complete: G8's source-aware editing and review workflow.** Completed stages are G1, G2, G3, G8, G9 and G10. G12's release-safety and honest handover gate is verified. **Overall Phase G remains partially complete.** G0's missing historical baseline remains deprioritized and does not block other work.

| Stage | Implementation and verified acceptance |
|---|---|
| G0 | BLOCKED historical baseline; current preservation passes. No backdating. |
| G1 | COMPLETE: authorized source registry and normalized evidence. |
| G2 | COMPLETE: centralized JSON, revisions, virtual time and CLI authoring. |
| G3 | COMPLETE: all 24 sources accepted through JSON, GUI, activation and both assistants. |
| G4 | Implemented; FAILED fresh routing: 86/120, below 90%. Compound task completeness remains deficient. |
| G5 | Implemented; FAILED fresh full-task adequacy: 5/30, below 85%; no adequate substantive causal model explanations. |
| G6 | Implemented; 28 deterministic conformance cases / 56 reads pass. Corrected source projections pass; causal explanation acceptance fails. |
| G7 | PARTIAL/BLOCKED: 113/141 native Studio/V9 journeys pass. Remaining 28 have genuine Huawei binding/policy version conflicts. Active validated Ansible variants: zero. |
| G8 | COMPLETE: source-aware exact-base proposals and multi-file review. Universal compound-instruction completion is not claimed. |
| G9 | COMPLETE: supported document/OCR/page, memory and ordinary/scenario isolation gate. |
| G10 | COMPLETE: UI/service gate, including its documented allowance for an external OS clipboard BLOCKED result. |
| G11 | Evaluations implemented and cohorts finished; acceptance FAILED because routing, reasoning and engineering criteria remain unmet. No external blind human grading claimed. |
| G12 | PASS for release safety, integration and honest partial handover; not overall Phase G acceptance. |

## G8 root cause, correction and actual verification

The old patch protocol required qwen to assign replacement anchors to filenames. Saved failed outputs swapped otherwise valid text between files. A first attempt using source-local inference also failed and remains archived.

The implemented protocol requests exact replacements with optional opaque source references. The server resolves a unique anchor across offered immutable snapshots, then requires its source to be editable and authorized. Explicit mismatched references are rejected; they are never moved to another source. Shared anchors, including anchors in preserved context files, require an unambiguous reference. Every proposed file must pass the existing path, revision, exact-base, structural, intent and overlap checks before one bundle is released. Existing public API and Accept/Reject/Undo/explicit Save behavior remain. Capacity remains one active plus eight related snapshots, with at most eight changed files. No new framework, database, model or renderer was introduced.

The original two-file request passes through the actual LangGraph/qwen/API path with one patch call. The same browser request also passes with one patch call per proposal. Both expected edits are exact. Reject preserves both files; Accept All changes only the requested unsaved lines; coordinated Undo restores both baselines. Editing the active buffer while inference is pending rejects the stale proposal and preserves the manual edit. A subsequent cold restart and page reload retain all 17 tabs and the exact protected 204-character LF buffer. No Save was clicked.

Verification: 29 focused backend contracts pass, 140 adjacent backend tests pass in a separate overlapping suite, five frontend transaction tests pass, and two handoff ownership/revision/unsent-draft checks pass. All 105 frontend source/test files match the starting snapshot; the prior TypeScript pass is reused. Evidence: `tmp/phase-g/iterations/20261023T140002.093180Z-G8-source-bound-architecture-6a21a0/G8-stage-acceptance-review.json`.

An additional frozen YAML/JSON case **fails task completion**: both actual sources reach qwen, but it proposes only the playbook comment change and omits the JSON peer-address change. No wrong-source edit or automatic application occurs. The original result remains under `tmp/phase-g/iterations/20261023T142051.262402Z-G8-real-workspace-c3d4d5/actual.json`; its specification is `docs/evaluations/phase_g_workspace_json_v4.json`. This is retained under G4/G5 compound-intent adequacy, without a wording retry, authored fallback, fresh benchmark credit or completed-task claim. G8 closure concerns the verified source-binding/review workflow.

## G7 progress and exact remaining dependency

The previous blanket classification of 32 compatibility conflicts was inaccurate. Four bindings already support V200R024C10, but their original fixture named an unrecorded GigabitEthernet port. Separately frozen positive inputs use the existing ce6800 planned profile's recorded `10GE1/0/2`, retaining the original rejected inputs. Actual V9 preflight passes all four. Real qwen Studio → V9 → engineer review → explicit confirmation → native rendering → unsaved output also passes all four, for trunk VLAN addition, interface administrative state, interface description and native VLAN. All 113 unique successful artifacts have been rechecked against exact expected output, device, release, digest and no-save/no-execution flags. This does not establish one-shot parameter extraction. Specification: `docs/evaluations/phase_g_native_positive_variants_v3.json`.

The remaining 28 bindings require VRP `8`, while the upstream reviewed policy requires VRP `V200R024C10` / ce6800. Fresh authorized OSPF router-ID and default-route preflights reproduce that conflict. Resolving it requires a reviewed upstream binding/policy correction. The sibling V9 source remains read-only under AGENTS.md, and the active immutable release is preserved. No alias, relabeling, monkeypatch or compatibility bypass was used.

A fresh WSL probe confirms the existing unprivileged Ubuntu environment has no `ansible-playbook`, `ansible-lint`, `bwrap` or approved pinned validation profile. The actual validator returns unavailable, with syntax/lint not run. No tooling was installed and no genuine Ansible validation or device testing is claimed. Evidence: `G7-current-contract-and-tooling-review.json` in the current audit directory.

## Intelligence and evaluation status

The frozen 120-case routing and 30-case quality cohorts were neither rerun nor rescored. Report fields that still said RUNNING/PENDING were corrected from their existing completed reviews; previous metadata remains preserved. Strict fresh results are M0 2/30, M1 2/30, M2 5/30 (24 FAIL plus one invalid-context BLOCKED), and M3 1/30. M2's adequate results comprise four factual/review/reconstruction paths and one simple model-written negative lookup; none demonstrates adequate substantive causal reasoning. Source correctness, verifier repair and fallback are not counted as model reasoning. These scores do not establish that every residual defect is intrinsic model capacity; no universal impossibility claim or lowered threshold is made.

The seven capabilities remain separately assessed: semantic intent is partial; authorized tool calling and bounded source/document/V9 retrieval are demonstrated; owner-bound memory survives restart and refresh; multi-step causal reasoning is unaccepted; factual verification has concrete successes and retained failures; editor/document/reference context is demonstrated, while compound completion remains partial. The additional G8 JSON omission remains a failed regression.

## Preserved state and exact continuation

The final standard 5173/8000 pair runs under launcher session 8117 / backend PID 3980; existing Ollama PID 20988 is unchanged. Fresh IAB access works. Tab 2 in browser 2 is retained. Development-network simulation is disabled. Final browser checks show Floating retrieving R2's stored management address `192.168.1.251` using only inventory.read, then answering 7+8=15 without sources. Studio also answers 7+8=15 without editor, attachment, network or history context. The running API returns 404 for another owner's request to the controlled Studio conversation.

All 17 editor tabs and the exact protected/playbook/variable buffers remain intact. Protected LF SHA-256: `b4c9fe532f11100c172b383f5766de4cb5e0ae5cd165378b258395ca83a93632`. No pending proposal or running ordinary turn remains. Ordinary business and saved-authoring table fingerprints are unchanged; only controlled AI conversation/evidence/checkpoint records changed. Active release `7a14a351e52b49aeb87f65d1192f0937`, 141 bindings and all 341 artifact hashes are unchanged. HEAD `6e8597c`, empty index and archived 52-file patch SHA `d6aa68...` are preserved. No staging, commit, publication, model download, Save, deployment or device action occurred.

Final evidence is under `tmp/phase-g/iterations/20261023T140002.093180Z-G8-source-bound-architecture-6a21a0/`, especially `G12-current-continuation-acceptance.json`, `G12-final-preservation.json`, `G12-final-browser-runtime-traces.json` and the retained screenshots.

Remaining work is G4 compound-goal completeness and scoped planning, G5/G6 evidence-complete causal explanations, G7's reviewed upstream contract correction and genuine Ansible dependencies, and G11's unmet quality thresholds. Do not rerun exposed cases as fresh, lower thresholds or resume individual wording repairs. Any substantive orchestration correction requires untouched evaluation after its dependencies are ready. G0's historical absence remains deprioritized.

Focused reproduction: `.\backend\.venv-m0\Scripts\python.exe -B -m pytest backend/tests/test_workspace_source_binding.py backend/tests/test_phase_g_workspace.py -q -p no:cacheprovider`. Windows sandbox asyncio restrictions require the approved out-of-sandbox test workflow. The V3 native evaluator cases use `--positive-variants docs/evaluations/phase_g_native_positive_variants_v3.json`; accepted cases skip and original negatives remain. For rollback, revert only this continuation's source-binding hunks using the audit's `source-before.py` and `tests-before.py`; never reset the repository or discard earlier Phase G/context-restoration changes. No rollback was performed.

---

