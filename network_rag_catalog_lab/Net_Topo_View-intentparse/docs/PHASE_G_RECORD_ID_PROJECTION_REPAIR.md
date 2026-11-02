# Phase G — Source-record-ID projection repair

Date: 2026-11-01, Asia/Kuala_Lumpur. HEAD: `8a7f86ce4e4d7c12d2e0565bfa53ab64f4ca756d`, preserving the preexisting dirty working tree.

**PASS — the narrow record-ID delivery milestone.** Authenticated Floating and Studio requests now receive exact authorized interface-state record identities in their final responses, with the associated device/interface, observation, source, origin, scope and timestamp. Both actual browser paths were verified. This does not close or improve a broader G4/G5/G6/G11 reasoning gate.

Audit: `tmp/phase-g/iterations/20261101-record-id-projection/`. Frozen cases: `docs/evaluations/phase_g_record_id_projection_v1.json`. Curated results: `docs/evaluations/phase_g_record_id_projection_result.json`. The source-derived expectations are independently checkable but implementation-assistant graded, not blinded.

## First proven loss and correction

The registered reader and accepted interface-scoping logic already returned `observer-2211` from `synthetic-authored-recorder` and `model-interface-2211` from `declared_interface_observation`, both owned by Peregrine/interface2211. The historical API/browser failures remain unchanged in the preceding audit directory.

The first loss was `interface_observations()` in `backend/llm/orchestration/synthesis.py`. Its compact factual dictionary retained interface name, state, prefix and time but omitted `row.id`, source and origin. The subsequent interface-specific passage therefore supplied Qwen with two indistinguishable state observations. Final composition only projected time and citation labels; neither is the underlying record identity.

Before changing application code, two disposable-source tests reproduced missing IDs in the factual projection and final answer. An initial setup attempt failed before either test because the deeply nested Windows SQLite backup path was too long. That error and the successful short-path reproductions are preserved separately: `before.xml` has two setup errors; `before-short-path.xml` has two actual assertion failures.

Only one application module changed:

- `interface_observations()` now retains actual record ID, device/interface IDs, source, origin, category, requested scope, scenario/read revision, current/historical designation, VRF and observation time. Exact identified repeats can combine their citation labels; distinct IDs, sources, values, times or revisions remain separate. Unidentified records are not assumed duplicates.
- Existing flat and nested `sources[].data.records` envelopes are supported without borrowing another source's origin/citation. Failed child envelopes cannot supply stale values. This prevents a new false “no observations” statement on an existing wrapped source contract.
- The existing scoped synthesis passage includes those public identity/provenance fields when the original request explicitly asks for record/observation IDs, identifiers, identities or references. The existing model instructions, structured output schema, inference settings and budgets remain unchanged. Ordinary non-ID passages and the existing eight-observation concise projection remain available. Explicit provenance requests do not silently discard the ninth returned identity; reader limits still bound retrieval.
- The existing public `synthesize()` composition boundary appends **Source record identities — returned facts** for an explicit ID request, on accepted and fallback answers alike. Each entry uses the reader's own ID and associates its source/owner/scope/state/time on that same entry. A missing ID is marked **ID not recorded**; no returned observations produces an explicitly unavailable identity statement.
- The appended section is labelled as reader projection in the trace (`display_source_record_ids_added`, `source_record_identity_origin`). It is not a fallback answer presented as model reasoning, and it does not certify arbitrary model prose. Correct model explanations remain intact beside it.

The field selector controls an output field from the original request; it neither selects a tool nor introduces a second intent/planning authority. No new reader, store, agent, schema migration, dependency, cloud call or engineering action was added. Source-policy, authorization, canonical interface resolution and P4 invocation identity are unchanged. Invocation UUIDs and `[S1]` citation labels are never substituted for a source record ID in this section.

## Before and after evidence

For the unchanged request:

> Using recorded state only, show Peregrine GigabitEthernet3/0/1 administrative and operational status with record identity. Do not read any other sources.

| Boundary | Before | After |
|---|---|---|
| Registered reader | Two correct source IDs and their provenance present | Same records, owner, scope and simulated timestamp |
| Factual projection | ID/source/origin discarded | Actual per-record public fields retained |
| Qwen-visible passage | Two identical state/time descriptions | Both exact IDs and their provenance included as untrusted source data |
| Raw Qwen answer | State summary, no IDs | Still a state summary, no IDs in the observed target runs |
| Final answer | Correct state/time/citation, incomplete requested result | State explanation plus exact reader-owned identity entries; narrow task complete |

The authored entry is labelled **Authored/recorded observation**; the modeled entry is labelled **Modeled observation** based on the returned simulation category, not an ID-prefix guess. Both retain simulated origin and observed scope, administrative down/operational down, `2026-10-31T22:00:00Z`, device221/interface2211 and the recorded interface spelling. They are not independent physical confirmations or a root-cause finding.

This is an application projection/composition correction. The new successful final answers do **not** demonstrate that Qwen learned to copy all requested identities or improved causal reasoning. The raw outputs make that limitation visible.

`before-after-boundaries.json` checks the historical and final Floating API traces directly: actual reader rows are identical; system instructions and output schema are identical; both source IDs are absent from the old synthesis input and present in the new input. Qwen still omits them from its raw answer, while the final answer contains both. This isolates the repaired projection/composition mechanism from a prompt-contract or model-setting change.

## Tests and actual application verification

`backend/tests/test_interface_record_identity.py` adds21 focused cases within the final **212-pass affected suite**. Coverage includes:

- Actual scoped registered reads on both assistant surfaces; exact source IDs/provenance reaching the model input and final response.
- Valid model prose retained; ordinary questions and explicit ID omissions remain concise.
- Same interface with independent authored/modeled observations; similarly named ports on different devices; historical and different-interface records.
- Exact repeats versus distinct source/time/value observations; more than eight requested identities.
- Absent identities, exact punctuation/case/backticks, nested source origins/citations and unavailable child envelopes.
- Wrong device/interface ownership rejection, denied reader permission and no-read advice remaining unexecuted.
- Existing state-scope, P4 receipt, synthesis, source-contract and advisory regressions.

Completed evidence: `focused.xml`19PASS, `positive-preservation.xml`20PASS, `affected.xml`210PASS, final `final-affected.xml`212PASS including all21 focused cases. These overlapping runs are not summed. All tests use new short disposable temp paths; no old test directory was reused or deleted.

Real application testing reused the previous disposable database on8001 and the existing frontend on5174. The server asserts the actual database path before use. Cloud inference, multi-model experimentation, completeness, Approach A, legacy interpretation and the old harness were all OFF in these child processes. Ordinary environment files were not edited. All actual inference used `qwen2.5:1.5b` with unchanged local settings.

| Final-source target check | Result | Measured duration |
|---|---|---|
| Authenticated Floating API | PASS: exact two IDs, correct association, one scoped state reader | 18.75s HTTP;18.45s graph |
| Authenticated Studio API | PASS: same complete identity delivery | 9.61s HTTP;9.56s graph |
| Actual Floating browser send | PASS: exact IDs visible in final response; stored new turn and DOM verified | 9.12s graph |
| Actual Studio browser send | PASS: same complete identity delivery | 4.44s graph |

Browser durations are backend graph times, not separately measured DOM-render totals. Initial runs are also retained; confirmations repeat the same condition and do not add independent generalization cases. There are four unique target surface/transport combinations, eight target executions including confirmation, plus four API control executions. All24 observed local model calls are recorded. **Zero new cloud dispatches.**

Initial ordinary follow-ups did not force an identity section from old conversational context. Floating's first model draft omitted the named interface and passed after the existing bounded repair. Studio's two drafts failed the same requirement and its final response used the existing factual fallback. Those do not earn successful reasoning credit.

Both advisory follow-ups executed zero readers and clearly labelled suggestions as not collected. Their advice largely restated which records to ask for rather than supplying a useful new diagnostic discriminator. No-read safety passes; advisory usefulness remains partial/unqualified. This limitation was recorded without a prompt-tuning loop.

Anonymous access returned401 and another owner's conversation404 without inference. HTTP path/method correlation now identifies background `/api/v1/ai/inventory` calls separately from conversation turns; they are not attributed to the graph. Sequential API turns share a conversation path, so their per-turn observations and prompt identity also participate in attribution. Every target turn has exactly one `network.state` result with canonical device221/interface2211 and no other selected reader.

Screenshots and complete DOM snapshots are in `browser/`; raw model/reader/request traces are in `runtime-traces.json` and `confirmation/runtime-traces.json`. Browser stored turns are saved alongside their correlated request paths. The source hash and registry hash were frozen for final confirmation in `confirmation/source-receipt.json`. First runs, failed tests and final confirmations are all separate.

## Preserved decisions and remaining acceptance

- P4 receipt/coverage changes remain byte-identical to the start of this task.
- Previous low5/8 versus medium6/8 results remain unchanged; low stays active.
- Failed canonical layout remains inactive/current layout retained. Native/core-wire schema transport was not activated; validated JSON/full remains unchanged.
- Completeness, Approach A and the old harness remain OFF by default and throughout this local-only test.
- No P1/P2 rerun, broad30-case qualification, model switch or new Gemini availability probe occurred.
- The previous Gemini3.1 HTTP503 remains a provider noncompletion before tool execution, not a reasoning failure. Broad multi-source investigation, actual source-owned supplementary retrieval, running/staged comparison, directional reasoning and the approved complex-cloud/browser path remain unverified in that integration batch. This repair does not unblock or claim those gates. A later cloud continuation needs new exact synthetic consent, available provider service and its own bounded authorization.
- No broader G4/G5/G6/G11 or other full Phase G stage is newly accepted.

## Preservation and rollback

`preservation-before.json` records the current baseline, including the already documented27 missing old quota/usage fixtures. They were not reconstructed. The final audit compares804 protected source/report/evidence files,41ordinary SQLite tables,1,923knowledge files including all341 active immutable artifacts, both environment files, the quota ledger and Git HEAD/index. Only this synthesis change and the explicitly updated continuation document are allowed existing-file deltas. New code is limited to the focused test file; new audit utilities, frozen cases, results and this handover are separately reviewable. The original frozen evaluations/MN integrations and previous model scores are not overwritten.

The selected disposable scenario revision did not change. The acceptance services are stopped after testing; ordinary5173/8000 and Ollama were not restarted. Existing unsaved acceptance drafts remained in the DOM, and no editor text, Accept/Reject/Save, close-tab, profile reset or device operation was performed. This is not a new full byte-hash proof of ordinary editor models.

**Final preservation passed against the current baseline:** no unexpected protected-file changes, unchanged ordinary tables/HEAD/index/environment files/cloud quota ledger and unchanged knowledge hashes. The inherited27missing temporary fixtures remain explicitly listed in `preservation-final.json`. The host listener check for5174/8001 returned `[]` in `ports-after-stop.json`. No commits, staging, publication or deployment occurred.

Review `source-change.diff` against `synthesis-before.py` to roll back only this task's hunks if necessary. **Do not copy the whole before-file over newer user work or reset Git.** No ordinary database rollback, migration, release activation or credential edit is required. Reverting the fix restores the original incomplete record-ID behavior; tests and prior failure evidence should remain available.

Final decision: **retain the narrow projection/composition repair**. Stop this bounded task. Remaining reasoning, provider and broader Phase G work require their own continuation scope.
