# Three-operation knowledge extensibility verification

**PASS for the requested isolated authoring-to-generation scope — 2026-10-14.** All three new operations were authored in Knowledge Engineering, published through V9, selected using actual Chroma retrieval/local Qwen, clarified and generated through the original Ansible Studio. No deployment, user database replacement, sibling V9 edits or automatic commit occurred.

## Knowledge created through the GUI

Category: `management_plane_security`. Complete current CogniShield authoring/published operation descriptions and aliases were reviewed first; no equivalent operations were found and no substitutions were needed. Before-state evidence: `tmp/extensibility/catalog-before.json`.

All six reusable definitions were assigned to the category. Each operation selected only its own mappings; reusable presets were explicitly applied to its rules. V9 generated the schemas; no engineer-authored schema files were substituted.

| Operation | Selected global parameters and compiled constraints |
| --- | --- |
| `configure_login_banner` | Required `login_banner_text`: string, 1–240 characters, printable ASCII excluding `#` and control characters |
| `configure_exec_timeout` | Required `exec_timeout_minutes`: integer 1–60; optional `exec_timeout_seconds`: integer 0–59, default annotation 0 |
| `configure_login_lockout` | Required `login_block_seconds`: integer 1–3600; `login_failure_attempts`: integer 1–10; `login_failure_window_seconds`: integer 1–3600 |

All three generated schemas reject additional properties. Contract/template versions are 3; applicability is `cisco / iosxe / 17.9`. Templates were written and saved in the existing Monaco IDE. Their first Jinja comment declares `format=native_cli`, `language=ios`, `extension=.cfg`; the worker reads this metadata from the frozen published asset. The declaration parser supports other formats without operation cases, while the current Cisco Ansible wrapper explicitly requires native CLI.

Frozen files under `tmp/m4/k/storage/catalog_releases/c90cf63a5f9342528c5014125778c233/`:

| Operation | Generated schema | Frozen Jinja asset |
| --- | --- | --- |
| Banner | `schemas/configure_login_banner.json` | `templates/79/template.j2` |
| Timeout | `schemas/configure_exec_timeout.json` | `templates/80/template.j2` |
| Lockout | `schemas/configure_login_lockout.json` | `templates/78/template.j2` |

Authoring paths and binding input contracts are preserved in `tmp/extensibility/published-manifest.json`. The timeout template supplies 0 when optional seconds are absent; JSON Schema defaults alone do not insert runtime values.

## Publication and runtime evidence

GUI validation passed with zero reported warnings/errors. GUI publication/activation produced **`c90cf63a5f9342528c5014125778c233`**. Previous release **`3ee58ee401954856a53cc2ceb71aae1c`** remains intact for rollback. Manifest SHA-256: `769d7a9c5c57705945aa24f8c8165cb4efde49dd6b5c4b0df93418fe214980f8`.

Before publication all three operations were absent from active runtime despite being compiled in the authoring workspace (`tmp/extensibility/draft-isolation.json`). After publication the immutable schemas, frozen templates and release-specific Chroma collection `knowledge_c90cf63a5f9342528c5014125778c233` contained the new operations. Embeddings used local `nomic-embed-text`. Backend restarts retained the authoring data, active pointer, sessions and generated packages.

Three paraphrased GUI requests used the new release and local `qwen2.5:1.5b`, with human confirmation of each catalog operation:

| GUI job | Request/result | Actual successful model calls |
| --- | --- | --- |
| 3, banner | “Display a pre-authentication warning notice to remote users on MGMT-SW-A” → `banner login #` / `Authorized personnel only` / `#` | 6, zero failed |
| 4, timeout | “Disconnect idle remote terminal sessions after 5 minutes on the management-switch” → `line vty 0 4` / ` exec-timeout 5 0` | 6, zero failed in corrected walkthrough |
| 5, lockout | “Temporarily reject remote sign-ins for 120 seconds after 3 failed attempts within 60 seconds on MGMT-SW-A” → `login block-for 120 attempts 3 within 60` | 7, zero failed |

Evidence: `tmp/extensibility/{banner-rag,timeout-rag-retest,lockout-rag}.json`. No static model answers, new hardcoded operation recognizers or old IntentParser fallback were used.

## Clarification, inventory and original GUI

- Banner: V9 explicitly asked **Login Banner Text**; answering **Authorized personnel only** resumed validation and generation.
- Timeout: V9 asked **“Several devices match this description. Which one should receive this operation?”** The original picker showed only **MGMT-SW-A/B**. Selecting **A** resolved the authoritative SQLite target, then answering **Exec Timeout Minutes = 5** reached the review modal and generation.
- Lockout: the schema wizard asked **Login Block Seconds**, **Login Failure Attempts**, **Login Failure Window Seconds**. Answers **120 / 3 / 60** reached review and generation.
- Model limitation: timeout and lockout values were not reliably extracted from the paraphrases; the schema-driven clarification collected them explicitly. This verifies successful clarified generation, not perfect one-shot parameter extraction.
- All jobs use SQLite device **3 / MGMT-SW-A**, a controlled planned **C9500-24Y4C / IOS-XE 17.9** fixture. MGMT-SW-B supplies controlled ambiguity. These are inventory fixtures, not physically tested switches.
- Original interpretation/parameter review and generated comparison dialogs passed for all three. Each package contains `playbook.yml`, `native_config.cfg`, `v9_review.md`, `preview_modal_dialog.md` under `playbooks/generated/job_3`, `job_4`, `job_5`. All folders/files appeared in original Explorer; all three native outputs opened in Monaco. The Ansible wrappers target MGMT-SW-A and use `cisco.ios.ios_config` with `src: native_config.cfg`.

Screenshots: `tmp/extensibility/{publication,banner-review,banner-monaco,timeout-ambiguity,timeout-review,timeout-monaco,lockout-review,lockout-monaco}.jpg`.

## Corrections and verification

Two discovered integration defects were corrected, each with one affected browser retest:

1. `backend/local_providers/authoring.py`: the original file suffix allowlist rejected generated `.cfg` reads. Now an additional suffix is accepted only for the exact generated path registered in a persisted V9 job manifest with that extension. Unregistered paths and traversal remain rejected.
2. `backend/local_providers/v9_studio.py`: AMBIGUOUS_TARGET was displayed as a terminal error. The adapter now exposes V9's exact candidate devices through the original target picker; runtime validation still blocks unresolved/unsupported generation.

Other iteration changes: new `artifact_metadata.py`, save-time declaration validation in `knowledge_worker.py`, frozen metadata/output propagation in `v9_worker.py`, metadata-based artifact naming in `v9_studio.py`; new artifact and presentation regression tests. No frontend redesign was needed.

Actual verification results:

- `test_artifact_metadata.py`: **2 passed** (earlier in this iteration).
- `test_v9_studio_presentation.py`: **2 passed**; sandbox temporary-SQLite access initially failed, then authorized isolated execution passed.
- `test_v9_studio_bridge.py`: **passed once**: clarification, corrections, invalid parameter, artifacts, ownership, audit, restart and blocked execution.
- Frontend TypeScript/Vite build: **passed once**, 3947 modules, 35.70s; inherited CSS `@property` and chunk warnings. Initial sandbox EPERM was resolved by authorized execution. No subsequent frontend changes required another build.
- `tmp/extensibility/verify_acceptance.py`: **passed**. Verified all frozen artifact hashes, old/new operation visibility, active release/index identity, exact Jinja rendering, schema values, Ansible wrapper, three persisted jobs, four saved files per job, target identity and audit records. Rejected banner delimiter `#`, timeout 61, failure count 11 and unsupported IOS-XE 99.1 with HTTP 422; no extra jobs or release changes.
- Scoped `git diff --check`: passed.

Detailed final evidence: **`tmp/extensibility/acceptance-results.json`**. The syntax check comprises reviewed Cisco command forms, schema ranges, StrictUndefined Jinja rendering and existing Ansible YAML safety validation. It is not a Cisco device parser or execution test. Cisco references: [login block](https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9500/software/release/17-9/configuration_guide/sec/b_179_sec_9500_cg/configuring_login_block.html), [EXEC timeout](https://www.cisco.com/c/en/us/td/docs/ios/fundamentals/command/reference/cf_book/cf_d1.html), [banner](https://www.cisco.com/c/en/us/td/docs/ios/fundamentals/command/reference/cf_book/cf_a1.html).

## Scope and stop point

No incomplete acceptance checks remain within this isolated single-operation/single-target IOS-XE generation scope. Real SSH, hardware dry-run, deployment, multi-target/vendor expansion and guaranteed LLM extraction are not claimed. Runtime continues to reject unsupported compatibility rather than weakening policies.

Test environment: frontend **5175**, backend **8001**, `tmp/m4/app.db`, knowledge `tmp/m4/k`, runner `tmp/m4/serve.py`. This release is activated only in that isolated test workspace; ordinary user data and its active release were not replaced. Verify processes before using old PIDs after interruption.

**STOP: the requested three-operation verification and handover are complete. No further iteration started.**
