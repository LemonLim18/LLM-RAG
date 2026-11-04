# H05 reasoning reliability — closing engineering decision, 2026-11-04

**Close the current investigation without another prompt change. Preserve the implementation, keep the candidate OFF and H05 blocked from promotion.** No general reliability improvement has been demonstrated. H02's separately verified focused success remains preserved in commit `8406d4516b1ffff8ead9bd583002e25c9165a4a9`.

## Failure boundary

| Dimension | Demonstrated finding | Limit of that finding |
|---|---|---|
| Model knowledge | PD-02 correctly distinguishes aggregate counters, sampled ingress traffic and a transaction-matched post-egress TAP observation; server processing/reply remain unknown | One explicit comparison is not reliable open-ended recommendation generation |
| Applying the knowledge | Latest original-question H05 assigns counters or flow logs the shared purpose of verifying the specific poll's transmission; the existing instruction already prohibits that counter inference | Inconsistent application is observable; the hidden model cause is unknown |
| Structured output | Latest H05 has nine schema-valid claims; PD-02 has three, with valid identifier types and selectors | Valid JSON and bindings do not validate the diagnostic purpose |
| Mechanical coverage | Eight H05 operands are supported; its routing declaration is category-incompatible. All three PD-02 claims use `interface_oper_status` for counter/flow/packet assertions and remain uncheckable | Uncheckable means not certified, not automatically false. Supported operands do not certify surrounding advice |
| Final release | Both responses retain model prose with `QUALIFIED_UNVERIFIED` and `semantic_certified=false` | The qualification is honest but does not remove or correct an overbroad recommendation; no user-harm or label-effectiveness study was performed |
| Evaluation | Original H05 requires two technically useful passive artifacts with defensible purposes; PD-02 asks for an explicit comparison and one follow-up artifact | Do not demand particular names, an extra application-health verdict, boilerplate caveats or advice the question never requested |

H05's raw recommendation says an “Interface packet counter or flow log snapshot” could “verify if poll packets are successfully transmitted outbound.” That specific-exchange attribution is unsupported for aggregate counters. The packet already contains the counter limitation and complete material operands; no transport loss, timeout or truncation explains this response. Its 5.48s generation completed with STOP and 2,180 of 8,192 output tokens.

PD-02 supplies a useful positive control: the raw comparison preserves the actual egress observation instead of withholding everything. Its advice then groups a server-side capture and application log under determining processing/reply generation. A capture can establish matching packet observations; internal processing and silent processing require different support. The log option is useful, but the shared purpose remains qualified. This is not a claim that supplied records already prove processing, and it is not sufficient evidence to declare a universal lack of network knowledge.

Evidence: H05 `tmp/phase-g/iterations/20261104-h02-checkpoint-h05-layer-repair/h05-layer-test/H-05/{live-result,review}.json`; PD-02 `tmp/phase-g/iterations/20261104-h05-passive-evidence-diagnosis/prepared-PD-02/{live-result,review}.json`. Both current result hashes match their recorded reviews. The existing repair/diagnosis reports, eight saved-response reviews, six offline contrasts, frozen requests and historical scores remain unchanged. The contrasts are not six model results; repeated H05 generations are not independent generalization cases. Reviews are source-derived and implementation-assistant graded, not blinded.

## Engineering options

| Option | Benefit | Risk | Cost and evidence needed |
|---|---|---|---|
| **A. Preserve and document — selected now** | Stops an unsupported prompt-tuning loop and preserves verified H02 behavior and valid reasoning | Existing unverified advice can still be wrong; default-OFF candidate status does not make the baseline infallible | Documentation only. Current failures justify non-promotion, not another implementation |
| **B. Explicit recommendation task — future experiment only** | Could make each artifact's observation, diagnostic purpose and material limits easier to apply | May add verbosity or structurally complete but still wrong advice. Current instructions already request purposes/limits; PD-02 is not a matched demonstration that a reformulation improves H05 | Low-to-moderate bounded experiment cost. Needs a distinct missing-task-formulation hypothesis and separately authorized frozen matched open-ended tasks with positive controls, fixed evidence/model settings and raw/final grading |
| **C. Release assurance — next separately scoped investment** | Can determine how unverified recommendations should be presented or reviewed before broader exposure | Over-restriction could suppress valid counter/trace advice; labels alone may provide little protection. No universal prose validator is justified | Start with a read-only product-safety review. Establish actual user-facing representations and scope of verification, using correct/qualified/incorrect saved recommendations. Any later implementation needs a concrete requirement and false-suppression checks |

**Priority:** A now; C before any broader promotion. C is a separate question about assurance, not a claim to have improved model reasoning. B remains an optional future capability experiment, not the next wording tweak. No B/C implementation, new model, planner, agent, verifier, schema field or prompt rule is authorized or added here.

Reopen development only for a reproducible application defect, a demonstrated user-facing assurance requirement, or a separately scoped and authorized experiment with independently checkable expectations. For B, require improvement in complete open-ended recommendations across independent tasks, including correct positive conclusions and permitted counter use; compare the unchanged baseline with the proposed task formulation. Track raw reasoning, release preservation, unsupported claims and false suppression separately. An explicit-comparison pass, valid schema, source read or filtered answer alone cannot justify promotion. Existing Phase G thresholds and independent gates remain unchanged.

## Documented recommendation acceptance criterion

Review a recommendation against the **actual question**, asking:

1. **Observation:** What can this artifact directly record, at what material subject, granularity, time and observation point?
2. **Inference:** Does the proposed diagnostic purpose reasonably follow from that observation, with material assumptions kept distinct from established facts?
3. **Unknowns:** Are relevant limits retained, rather than inferring an individual exchange from aggregate data, an application action from packet presence alone, or absence from incomplete observations?
4. **Usefulness:** Does it address the requested uncertainty and number/distinctness of contributions without merely rechecking an already established fact? Complementary artifacts may address the same uncertainty; they need not resolve different gaps unless the question requires that.
5. **Permission:** Is it a permitted passive artifact to request, with availability unassumed and recommendation distinct from execution?

Accept equivalent wording and justified positive findings. Require only limits material to the requested conclusion, not a fixed format, artifact list or extra caveat sentence. Useful aggregate activity/error advice is acceptable. A suitably correlated response may reasonably support a conditional application-level inference; an application log is not mandatory for every diagnosis. Do not confuse that inference with direct knowledge of internal processing, or treat an absent response as proof that processing never occurred. A useful recommendation with materially ambiguous scope is **qualified**; an explicit unsupported capability, omitted required outcome or forbidden action is **inadequate**. If artifact capabilities are unspecified, record that uncertainty instead of inventing either support or falsity. This is a human review criterion, **not a runtime validator or semantic certificate**.

## Preservation and documentation checkpoint

This closeout changes only this report and appends the continuation checkpoint. No new Gemini inference, registered-source retrieval, test generation, prompt/schema/checker/release change or protected-data mutation occurs. Current model roles and OFF defaults are preserved. Existing 136-test/17-replay and later 48-test results remain historical, overlapping evidence; no redundant regression campaign is run for a documentation-only decision. Closeout verification checks file hashes, evidence integrity, configuration, documentation scope and Git HEAD/index.

The existing dirty `backend/llm/orchestration/role_reasoning.py` paragraph belongs to the earlier H05 experiment. It is preserved unchanged by this task and **must not enter a documentation-only commit**. The JSON contrast registry is an evaluation fixture, so exclude it from this strict documentation-only checkpoint; it can be considered separately if an evaluation-artifact commit is later requested. Do not force-add ignored audit data, quota, SQLite or environment files. Raw audit evidence stays local; a docs-only commit is not a portable benchmark bundle.

Recommended subject: **`docs(reasoner): close H05 investigation and record promotion limits`**.

Safe Markdown whitelist, project-relative for the proposed Git commands:

- `docs/PHASE_G_H05_NETWORK_REASONING_REPAIR.md`
- `docs/PHASE_G_H05_PASSIVE_EVIDENCE_DIAGNOSIS.md`
- `docs/PHASE_G_H05_REASONING_RELIABILITY_DECISION.md`
- `docs/PHASE_G_CONTINUATION_CHECKPOINT.md` — its uncommitted additions are H05/PD-02 continuation history and this closing decision.

For review only; **not executed**:

```powershell
git add -- docs/PHASE_G_H05_NETWORK_REASONING_REPAIR.md docs/PHASE_G_H05_PASSIVE_EVIDENCE_DIAGNOSIS.md docs/PHASE_G_H05_REASONING_RELIABILITY_DECISION.md docs/PHASE_G_CONTINUATION_CHECKPOINT.md
git --no-optional-locks diff --cached --name-only
git --no-optional-locks diff --cached --check
```

No staging or commit was performed. H05 is not promoted; no G4/G5/G6/G11 gate closes. The prompt-tuning investigation is closed at this evidence-backed limitation. Further work requires a new authorized scope.

Audit: `tmp/phase-g/iterations/20261104-h05-reliability-closeout/{evidence-integrity-check,preservation-before,preservation-after}.json`.
