# Knowledge Activation Results

Date: 2026-09-29

Historical activation report. The user subsequently chose the direct-file runtime;
see `DIRECT_RUNTIME.md`. No release/activation step is needed for terminal testing.
The last retained publication is `44d6ad1355b44a6c9a91624d9ee31512`, completed before
that redirection. The direct runtime reads data/ rather than any published release.

## Runtime

- Prior metadata release: `c652d53a41254791b5c081f02a7263ac`.
- Initial expanded activation: `ad9924d14bde40d5aaeeac3e11dff1b9`.
- Original baseline: `fbd929e928014a4886fbfd69c4019851`.
- SQLite authority; 44 canonical operations, nine categories, 78 template bindings.
- Actual Chroma contents verified: all 44 operation IDs and matching release/vendor metadata.
- Model: `qwen2.5:1.5b`; embeddings: `nomic-embed-text` (768 dimensions).
- R1/R2/R3 preserved; SW1/SW2/SW3 added as source-labelled synthetic planned facts.
- No configuration was executed on a device.

The later request supplied 35 canonical operation IDs, all already active.
The current release enriches their RAG documents with actual vendor support and
per-vendor required/optional fields. It changes no operation contracts or template
support. See [the complete coverage audit](REQUESTED_OPERATION_COVERAGE.md): 54
requested vendor-operation combinations remain unimplemented.

## Changes

`app.knowledge.pack_promote` defaults to isolated rehearsal. Explicit apply backs
up SQLite, exported catalog, assets, context and the baseline release; installs
reviewed assets; uses revision-checked service dry-run/apply per pack; and merges
demo inventory after validation. Matching reapplication is a no-op. Conflicting
identities, aliases, templates and records are rejected. Publication is separate.

Parser evidence now accepts commas/conjunctions before known registry fields and
does not interpret an operation label as its own parameter value. This resolves
the gap between semicolon-heavy extractor fixtures and full terminal requests.
Category-preface target parsing preserves the later explicit SW1 target.
The selector receives a clearer semantic prompt and actual vendor coverage data;
it still accepts only retrieved IDs and requires user confirmation of proposals.

## Focused Verification

- Six promotion/clarification tests passed, including interruption recovery,
  backup integrity, idempotence and full-pipeline examples for all 32 additions.
- Twenty-five parser/selection regressions passed after the follow-up fixes.
- One vendor-document contract regression passed.
- No full-suite rerun was performed for this activation.

The eight live flows were run on the initial expanded release. The later
vendor-document release was verified against actual indexed contents; the model
flows were not repeated after that metadata enrichment.

| Live flow | Result |
| --- | --- |
| Interface description | Correct values/device; configuration generated |
| OSPF process | Correct values/device; configuration generated |
| ACL creation | Correct values/device; configuration generated |
| QoS classifier | Correct values/device and DSCP array; configuration generated |
| Missing OSPF parameters and session resume | No initial config; field-scoped answers completed the request |
| Mixed operations on R1/R2/SW1 | Correct operation-to-device bindings |
| VLAN rename paraphrase | RAG used; rename proposal confirmed, new name clarified, then config generated |
| Default-route paraphrase | RAG used; model proposed generic static route; explicit user correction to default route completed generation |

The first paraphrase attempts failed the strict automatic-selection check. Their
reports were retained. A clearer selector prompt and a target-preface fix allowed
clarification to finish both flows. This is **eight completed workflows with
assistance**, not eight correct autonomous interpretations or a model benchmark.
The route misclassification remains a known model limitation. No incomplete
request produced configuration.

## Recovery and Evidence

Backup and promotion receipt:
`storage/catalog_authoring/activation/ab8af4967e154de789a8c029262dfebd/`.

The directory includes `catalog.sqlite3`, `export.json`, authority marker,
matching catalog/schema/template assets, inventory/planned context, the baseline
release and a hashed receipt. Authoring revision after promotion:
`ad8e0a2e5c152e1c4c4a8735852a9c1221956ba979f6dfd24eb9b41ae1f8f307`.

Raw live evidence: `storage/catalog_authoring/activation-smoke.json`,
`activation-smoke-vlan_paraphrase.json` and `activation-smoke-routing_paraphrase.json`
in the same directory. Current release receipt:
`storage/catalog_authoring/vendor-coverage-release.json`.

Existing failed-publication safeguards retain the previous release. Published
changes use a forward corrective release; do not manually rewind the pointer or
overwrite current SQLite from an old backup. Context restoration is separate.

Start testing with [the terminal guide](PROMPT_TESTING_GUIDE.md). Exact device-lab
acceptance, complete Huawei/Juniper bindings, the user's proposed relaxed schemas
and general weak-model accuracy are not claimed as completed.
