# Knowledge Expansion Verification

Date: 2026-09-29

## Final Results

| Check | Result |
| --- | --- |
| Full compatibility suite, final serial run | **226 tests passed**, 117.201 seconds |
| Focused expansion suite | **23 tests passed**, including routing-context and malformed-suggestion regressions |
| Isolated SQLite pack rehearsal | All six packs applied and published offline in a disposable project |
| Candidate release | **44 operations / 78 vendor bindings** |
| New supported-binding cases | **42 validated and rendered** through `--check-cases` |
| Live-data preservation | **257/257 protected files unchanged** by SHA-256 comparison |
| Live authority | SQLite; `storage/knowledge/catalog.sqlite3` unchanged |
| Live active release | `fbd929e928014a4886fbfd69c4019851`, unchanged |
| Whitespace check | `git diff --check` passed |

Protected paths: `data/`, `storage/knowledge/` and
`storage/catalog_releases/`. No protected files were added, removed or modified.
The repository had unrelated existing changes before this task; this audit does
not claim that the whole working tree equals HEAD or that those changes are ours.

## Regressions Covered

- All original catalog contracts retained, matching-pack reapplication is a no-op,
  conflicting records/assets rejected, and modified template bytes fail hash review.
- Every new Cisco operation; Huawei/Juniper interface subsets; Juniper qualified
  next hops; unsupported profiles have no fallback template.
- Primitive and nested input evidence, optional values, explicit false/zero,
  deterministic labelled prompts with unavailable/malformed model responses.
- Scoped clarification, typed replies, context suggestions, and whole-request
  render blocking until incomplete tasks are valid.
- Prefix/route preference/next-hop rules; OSPF process/area/interface facts;
  bounded redistribution and default-routing-context restrictions.
- ACL protocol/port/prefix rules, collisions, complete replacement and exact
  deletion; separate ACLs using the same rule number do not falsely conflict.
- QoS rates/units/direction/actions, old DSCP-list confirmation, references,
  attachment protection, queue capacity and nested policy terms.
- Forward retirement creates a new candidate release; failed/stale publication
  preserves the current pointer.

## Test Execution Note

One intermediate 226-test attempt overlapped the separate rehearsal command.
Three source-mode clarification checks encountered the expected authoring lock:
two errors and one assertion failure. The source snapshot uses that lock even
though it does not mutate catalog records. After the rehearsal exited, the full
suite was rerun serially and all 226 passed. Do not run those two commands
concurrently; no locking safeguard was weakened to make tests pass.

## Not Verified

- Physical network-device syntax/behavior, license restrictions or traffic impact.
- Exact Huawei CE6800 description/admin command coverage and lab acceptance.
- Live local-LLM accuracy/latency or expanded Chroma retrieval quality.
- Live catalog activation, device execution, GUI, monitoring or topology.

The deterministic tests and successful rendering do not prove model accuracy,
vendor certification, production readiness or equivalence to a stronger model.
See `KNOWLEDGE_EXPANSION_COMPLETION.md` for contracts, limits and rollout gates.
