# CogniShield Phase G — Scenario-Complete Development Data, Evidence-Grounded Weak-Model Intelligence, and Full Phase F Closure

**Authoritative implementation specification and test contract — 19 October 2026**  
**Deliverable type:** engineering implementation plan, not an assertion of completed code.  
**Source of requirements:** the user's pasted description of both assistants and 24 information categories, the latest uploaded Phase F continuation checkpoint/results/runtime report, and the existing Phase F plan.  
**Main objective:** make both Floating AI and Ansible Studio genuinely useful with a relatively weak local language model by surrounding it with accurate, editable, comprehensive development data; task-specific planning; deterministic network computation; bounded evidence-based reasoning; controlled engineering generation; and independently graded end-to-end evaluation.

> **Mandatory interpretation of the user's three priorities**
>
> **P1 — Strong system support for a weak LLM.** Make the *combined* AI system better than naive model-only use: implicit and compound intent, correct source selection, information sufficiency, controlled follow-up retrieval, technically meaningful reasoning and complete natural answers. Do not claim a weak model has general intelligence it lacks or equate fallback with model reasoning.
>
> **P2 — ALL 24 source categories are available and USER-EDITABLE in development.** A user must be able to create, inspect, change, import/export and activate simulated **current** device configurations, stored backups, planned and observed topology, interface/protocol/routing state, time-series telemetry, syslogs, incidents and the other listed categories using versioned JSON files **and** the app GUI. Both assistants must consume the selected scenario via **the actual authorized gateway/tool paths**. The test author chooses what is current, old, conflicting, missing or unavailable. The UI must show the active simulated time and provenance, not pass this off as live physical network observation. No source may be permanently inaccessible just because the external collector/SDN/SSH service isn't running.
>
> **P3 — Finish Phase F's unfinished behavior and test continuously.** Correct answer relevance failures, Qwen's reasoning deficits, Phase F's unanswered fresh holdouts, 141 controlled Studio journeys, simulator and source-mode validation, full editor/multi-file behavior, document/clipboard limitations and final acceptance. After EVERY small code batch, inspect actual response/tool traces, fix detected defects, rerun affected and neighboring tests, and log independent outcomes. Never substitute documentation for implementation.

## 0. What Phase G must preserve and what it must not assume

### 0.1 Grounded historical starting point

The most recent uploaded Phase F checkpoint dated 19 October 2026, **not** the older Phase E report, records:

| Area | Reported current state | Phase G interpretation |
|---|---|---|
| Active native release | `7a14a351e52b49aeb87f65d1192f0937` | Reverify actual active pointer at G0; do **not** reset to older Phase E `f0e33c...` |
| V9 scope | 47 operations, 141 native bindings; 47-document index | Already published; keep active and use as source of engineering methods |
| Native output fixes | Four actual template bodies corrected, including Cisco/Huawei OSPF and Huawei ACL; 150 positive active renders, 1,642 build negatives | Expand independent branch/oracle checks; don't redo all 141 authoring |
| Model | `qwen2.5:1.5b`, `nomic-embed-text`; LangGraph B3 | Keep installed models; no unapproved downloads or model switches |
| Feature switches | `COGNISHIELD_AI_PLANNING=1`, `COGNISHIELD_AI_SYNTHESIS=1` | Preserve enabled; verifiers remain active, fallback attributed |
| Exposed routing | New candidate 60/60 and matched legacy 60/60 on historical exposed cases | Useful regression only; **not** fresh generalization evidence |
| Fresh Phase F routing | First 20 were 16/20 on original exposure; later cases up to 032 partially exercised | Inspect registry and run untouched remaining cases with frozen oracles |
| Frozen answer-quality | First 9 of 30 exercised, several rejected qwen drafts | No independent full ≥85% adequate-answer result; complete assessment |
| Studio | Single-buffer browser Accept/Reject/Undo verified; 141 full NL→Studio journeys not completed | Finish all pathways, plus multi-file and Ansible variant distinction |
| Source behavior | Planned/observed/historical separation and scoped current/saved config improved | Current simulated sources still need an editable complete scenario environment |
| Browser | Clipboard browser roundtrip was verified in one virtual context; actual OS clipboard unverified | Test nonvirtual real Windows separately or label environment blocker |
| Data integrity | Original 52-file staged patch hash `d6aa68e47ae3b44449d1f832404ad925a373791b845ec064d067b8e8b028d7f8` reportedly preserved | Recalculate; protect source, DB, chats and unsaved Monaco buffers |

Original Phase F reports also identify: false BGP AS interpretations, omitted down interfaces, inappropriate generic diagnosis appendices, incorrect general knowledge/translation/Python outputs, tool-source leakage, stale reference resolution, weak native Studio coverage, incomplete simulator independent conformance, and CPU model timeouts. **Treat the latest chronological top section of each report as the current state; retain earlier failure evidence.**

### 0.2 Preservation and authority rules

- Inspect real Windows worktree, source paths, `.env` safely, process/port owner, active V9 manifest/index, authoring SQLite integrity, original staged patch, untracked files, expected rollback pointers and user-owned browser tabs at the start. Historical PID/session IDs are not current proof.
- No `git reset/clean`, unsolicited stage/commit, copied acceptance database, manually edited active pointer, silent user-history restoration, deleted user files, unsaved Monaco overwrite, real SSH/deployment or physical config changes.
- Native V9 publication authority remains an **authenticated senior/admin Publish or Activate action**, with schema/render/auth/security/immutable integrity checks. No separate sign-off ceremony or mandatory Internet/device certification. For new native corrections, use V9 authoring → Validate → real authorized Publish/Activate → active verification; preserve rollback and old immutability.
- **Do not confuse published native CLI with certified Ansible playbooks.** Keep genuine playbook variants and validation separate; unsupported variants must be visible rather than fabricated.
- Development scenarios are explicitly simulated; ordinary mode must never silently receive scenario sources or treat synthetic measurements as actual physical network measurements. If a user runs the *development scenario*, 'current' means **current state of that active scenario at its virtual clock**, not live physical state.
- All new scenario editing APIs are developer/admin scoped; all AI reader APIs remain read-only. A scenario cannot grant itself higher authorization by editing its JSON metadata.

## 1. Explicit user-facing definition of the two assistants

**Floating AI Assistant — intelligent network analyst:** engage in general chat, answer conceptual networking questions, perform verified factual lookups, handle implicit goals and compound investigations, interpret planned/current/saved/historical/simulated data, deduce supported hypotheses, explain uncertainty and provide useful next tests. Read-only; Studio handoff creates a contextual **unsent** draft, not a hidden engineering operation.

**Ansible Studio AI Chat Panel — intelligent analyst + network automation engineer:** everything above, plus access to authorized *actual unsaved editor text*, selected and related files, V9 profiles/parameters, corresponding authentic playbook variants, syntax validators and reviewable diffs. It can generate native multi-vendor/multi-operation configurations or separately supported Ansible playbooks, propose edits, answer questions about the current document, ask for missing parameters, and preserve Accept/Reject/Undo/explicit Save. It must not deploy or silently save.

**Seven acceptance capabilities (each independently measured):** (C1) implicit intent; (C2) generalization to unfamiliar prompts; (C3) authorized source/tool planning; (C4) adaptive multi-source investigation; (C5) multi-turn contextual understanding; (C6) complete, useful, grounded human-style reasoning/answers; (C7) multi-vendor engineering generation, revision and validation. **Perfect** arbitrary-prompt accuracy or Codex-equivalent intelligence is not a credible promise; use measured milestones and leave failures visible.

**Execution patterns:** direct lookup (possibly zero LLM synthesis calls), free-form conceptual explanation (no private network retrieval unless relevant), analytical investigation (scoped multi-source), and Studio engineering (planning + V9/Ansible + diff). Do not force all queries through a heavyweight diagnostic template.

## 2. THE NON-NEGOTIABLE 24-SOURCE DEVELOPMENT COVERAGE MATRIX

All 24 categories below must have an active **development scenario data contract**, an editable JSON representation or referenced file, a discoverable GUI editor/inspector, and an adapter readable through the *existing* authorized tools. A category can reuse the appropriate underlying tool; **24 logical categories do not require 24 separate vector indexes or unnecessary public tools**. 'Available' means an explicit scenario can supply real-looking **simulated** data at a chosen time; for a deliberately missing-source test, the scenario must supply a typed `MISSING`/`UNAVAILABLE` result rather than silently inventing a record.

| # | Information source | Suggested scenario file / GUI section | Authorized consumption / critical semantics |
|---:|---|---|---|
| 01 | Planned device inventory | `inventory.json` / Devices | `inventory.read`; aliases, role, site, mgmt IP, vendor, OS and **actual declared** version; don't change ordinary inventory to match V9 |
| 02 | Planned network topology | `topology_planned.json` / Planned Links | `network.topology` with `scope=planned`; intended links not measured reachability |
| 03 | Discovered/observed topology | `topology_observed.json` / Observed Links | `network.topology` `scope=observed`; CDP/LLDP-style endpoint facts with timestamp, source and status |
| 04 | Topology history | `topology_history.json` / History timeline | Time-indexed snapshots/diffs; old neighbor is not assumed current |
| 05 | Current interface/device state | `device_state.json` / Interface & Device State | `network.state` (existing/extended reader); admin/oper state, errors, health, routing adjacency and capture time |
| 06 | Current running configuration | `running_configs.json` **or linked text files** / Running Config | `network.configuration` `scope=current`; scenario current snapshot per device/virtual time; preserve newlines and platform |
| 07 | Stored configuration snapshots | `config_snapshots.json` / Backups | `network.configuration` `scope=stored`; multiple captures, versions, source and timestamps |
| 08 | Config change history/diff | `config_changes.json` / Config Timeline & Diff | Current vs previous/saved comparisons; derive accurate diffs where possible, with audit of provenance |
| 09 | Routing/forwarding state | `routing_state.json` / Routes & Paths | `network.state` or approved state reader; VRF, prefix, next hops, route choice and optional simulation tracer |
| 10 | Protocol state | `protocol_state.json` / OSPF/BGP | `network.state`; OSPF adjacency/area/timers, BGP peer local/remote AS/status, timestamps; no invented peers |
| 11 | Controller/SDN state | `controller_state.json` / SDN | Existing authorized controller adapter or scenario-backed projection; OpenDaylight-like observations; distinguish configured from operational |
| 12 | Telemetry time series | `telemetry.json` / Metrics Charts | `network.telemetry`; CPU, memory, interface traffic with proper units, sampling window and timestamps |
| 13 | Interface performance/counters | `interface_metrics.json` / Counters | Derived metrics or individual samples: octets, errors, discards, utilization and rates; counter reset/wrap handling |
| 14 | Syslog | `syslog.json` / Events | `network.syslog`; severity, timestamp, device, facility/message; source-specific filtering and precise order |
| 15 | Incidents/alerts | `incidents.json` / Alerts | `network.incidents`; state, severity, first/last observed, correlated source references; not necessarily confirmed cause |
| 16 | Configuration drift | `config_drift.json` / Drift | Actual comparison of intended/saved/current where present, plus explicit human-annotated drift claims with provenance |
| 17 | Monitoring/source health | `source_health.json` / Source Health | Health and freshness for **each** reader; available, stale, error, unsupported, missing, not queried; inject controlled outages |
| 18 | Application/jobs/audit | `jobs_audit.json` / Jobs & Audit | Test-only change-job outcomes, timestamps, identities and effects; clearly synthetic, no spoofed real authenticated audit |
| 19 | Published V9 knowledge | Existing immutable V9 release + optional scenario **references**, isolated authoring test workspace / Knowledge | `knowledge.search`/`v9.preview`; source immutable/real, cannot be overwritten by scenario JSON; scenario chooses compatible lab target and queries real release |
| 20 | Technical documentation / RAG | `documents_manifest.json` + scenario docs / Documentation | `document.read` and existing allowed document/knowledge retrieval; bounded indexing, page provenance, controlled retrieval |
| 21 | Uploaded documents | `attachments_manifest.json` + fixture files / Attachments | Real document parser pipeline; text/PDF/log files attached to test conversation with session authorization |
| 22 | Images / diagrams | `diagrams_manifest.json` + image files / Diagrams | Existing actual OCR/vision capability when present, limits explicitly surfaced; no invented visual comprehension |
| 23 | Conversation history | `conversation_seed.json` / Conversation Context | Scenario-owned test conversation setup through gateway (not injected fake completed replies); preserve owner and references |
| 24 | Controlled simulation scenario | `simulation.json` + separate **private test oracle** / Scenario Engine | Existing bounded forwarding/protocol simulator; fault injections, virtual timeline, ground truth hidden from assistant |

**Additional cross-cutting sources**, not replacements for the 24: open unsaved Monaco buffers and related files (`editor.read`, approved scoped workspace reader), V9 authoring metadata, actual Ansible variant library, attached external reports, route/ACL calculated traces, provider availability, and authorized existing external connectors (NetBox/InfluxDB/syslog/SDN). These must also appear in source registry/tool descriptions for Studio and investigation.

**Implementation gate G3 MUST FAIL if any category lacks all of:** (a) a schema-valid representative source in the bundled starter scenario; (b) file import/export/editing or a referenced permitted immutable source; (c) GUI creation/edit/import/preview for editable scenario records; (d) real authorized reader consumption with correct observed/captured time and `origin=simulated`; (e) a demonstrated negative/stale/contradictory case where appropriate. V9 is intentionally the exception to raw JSON mutation: use its existing authorized GUI authoring lifecycle and the real active read-only release.

## 3. Development Scenario Workbench — architecture and contracts

### 3.1 Reuse infrastructure rather than creating a duplicate network system

Inspect the **actual current checkout first**. The uploaded snapshot already contained `backend/llm/gateway_network.py` (read tools including inventory/topology/telemetry/syslog/incidents/configuration), `backend/llm/gateway_playbooks.py`, `backend/llm/gateway_documents.py`, `backend/local_providers/observations.py` (JSON observation fixtures), and V9/Studio tooling. Phase F later added/extended scenario evaluation, planning/synthesis, source-scoped readers and network model modules. Reuse/extend these wherever possible. Treat an older archived ZIP as code archaeology only, not current implementation truth.

Introduce a *scenario-backed data provider/adapter* at the existing reader boundary, not a second LLM gateway, a second Chroma catalog, or cloned authoring DB. Tool names, authorization policy, request schemas and response shapes remain stable whether data comes from ordinary external/stored readers or a selected scenario. Prefer protocol-based dependencies (`SourceProvider`/`EvidenceProvider`) with shared normalization; avoid `if dev_mode` sprinkled throughout every reasoning node.

**Canonical modes:**

- `ordinary`: existing real/stored readers; no synthetic fallback, existing authentication and no unrequested physical collection.
- `development_scenario`: explicit admin/dev activation selects one immutable *scenario revision* and virtual time; every reader returns selected scenario data, with `origin=simulated` and `mode=development_scenario` regardless of how realistic it looks.
- `comparison` **evaluation only**: same prompt against two separate isolated source environments for parity. Never mix sources in a single answer unless the user explicitly authorizes comparison and each remains labeled.

The scenario adapter is a source provider, not an automatic stand-in for live network tools. All scenario requests remain **zero actual SSH/NETCONF/Ansible deployment/external-polling side effects**. Explicitly block adapter fallback to real external devices in scenario mode. Do not alter existing ordinary mode default on startup without the user's deliberate choice.

### 3.2 Proposed file layout (adapt to established repository conventions)

```text
backend/development/scenarios/
  README.md
  campus_healthy_v1/
    manifest.json
    inventory.json
    topology_planned.json
    topology_observed.json
    topology_history.json
    device_state.json
    running_configs.json
    config_snapshots.json
    config_changes.json
    routing_state.json
    protocol_state.json
    controller_state.json
    telemetry.json
    interface_metrics.json
    syslog.json
    incidents.json
    config_drift.json
    source_health.json
    jobs_audit.json
    documents_manifest.json
    attachments_manifest.json
    diagrams_manifest.json
    conversation_seed.json
    simulation.json
    configs/ ...                   # referenced text/YAML configs
    docs/ ...                      # referenced documents and image files
  branch_acl_fault_v1/ ...
  branch_bgp_fault_v1/ ...
backend/development/test_oracles/    # separate private test-root, NOT scenario-importable
  campus_healthy_v1/expected.json   # NEVER accessible from scenario tools/files
backend/development/schemas/       # versioned JSON Schema for all source files
backend/development/scenario_service.py  # only if no equivalent exists
backend/development/scenario_adapter.py  # plugs into current readers
frontend/.../ScenarioWorkbench... # integrate existing developer controls
```

**Authoring/storage separation:** scenario JSONs are editable *draft source-of-truth* in an explicitly designated development directory. On Validate/Activate, compile/normalize them to a revision-addressed immutable **in-memory/test snapshot**. Do not let half-written files change active reads mid-turn. Any GUI save edits the draft; **Activate Scenario Revision** selects the validated hash. JSON file changes outside the GUI trigger an explicit **Reload/Validate** (or safe watcher that creates a new draft only), never immediate silent runtime mutation.

### 3.3 Manifest and source contract (implementation schema, not free-form notes)

Versioned manifest MUST declare: `schema_version`, stable `scenario_id`, display name/description, `scenario_revision`, `created_by`, `created_at`, `mode`, virtual-clock state (`now`, timezone, rate, paused), registry/source file paths and hashes, source availability/freshness overrides, authorized simulated device scope, test/run fixtures, and explicit policy preventing external-device side effects.

Each entity observation MUST include as applicable: `record_id`, `device_id`, `interface_id`, `source_id`, `source_kind`, `origin=simulated`, `collected_at` or `effective_at`, `valid_from/valid_to`, time zone normalization, timestamp precision, typed value and units, simulated collector quality, `status` and optional `confidence`. Avoid a single vague `is_live=true` flag. Topology edges require both endpoints and observed status; configs include `config_kind=current|stored|planned`, correct platform, capture time, original text or approved relative path, and sensitivity marker; telemetry contains actual sample arrays instead of invented constant summaries.

**Recommended status algebra:** `AVAILABLE`, `MISSING`, `UNAVAILABLE`, `STALE`, `ERROR`, `CONFLICTING`, `UNSUPPORTED`, `NOT_QUERIED`; separate `status` from `mode`, `source_kind`, `timestamp`, and `authorization`. Missing data is not zero, down, healthy, inaccessible, or proven failure. Distinguish *not queried* from *queried but no records*, a collection error, and a deliberate missing measurement.

**Example minimal scenario selection (illustrative contract, not a deployed endpoint):**

```json
{
  "schema_version": "1.0",
  "scenario_id": "lab-branch-acl-001",
  "name": "Branch ACL fault / two-way reachability",
  "mode": "development_scenario",
  "clock": {"now": "2026-10-19T10:00:00+08:00", "timezone": "Asia/Kuala_Lumpur", "paused": true},
  "source_files": {
    "inventory": "inventory.json",
    "topology_planned": "topology_planned.json",
    "running_configs": "running_configs.json",
    "routing_state": "routing_state.json",
    "telemetry": "telemetry.json",
    "syslog": "syslog.json",
    "source_health": "source_health.json"
  },
  "policy": {"real_device_access": false, "deploy_allowed": false}
}
```

Actual packaged example must provide **all 24** sources, not merely this abbreviated illustration. Keep private oracles in a physically separate test-runner-only root **outside the scenario tree**, inaccessible to tools, document indexing, source adapters, scenario editor file references, vector search or provider prompt context. Tests must verify the assistant cannot access truth labels directly or indirectly by broad file read. The scenario itself may embed observable hints, but not the scored root cause.

### 3.4 JSON editing requirements

1. All 24 categories have documented versioned JSON Schema (or typed models generating equivalent strict schema), positive and negative examples, `additionalProperties` policy where appropriate, and migrations for future schema versions.
2. The developer can create a scenario by copy/template/import, edit any relevant data file with a text editor, run `scenario validate <path>`, inspect actionable cross-file errors and activate a revision. Make the actual executable command match current CLI conventions; don't invent `scenario` as a new public command when existing `development_scenario.py` should be extended.
3. Allow linked text files for lengthy native configurations/playbooks, not JSON strings only; validate relative paths to the scenario root, prohibit traversal/symlinks to secrets and reject dangling references. Permit newline fidelity, Unicode and binary attachments with safe size limits.
4. Dates, virtual-clock boundaries, source statuses, units, prefixes/masks, route metrics and BGP/OSPF attributes must be typed; invalid values fail before activation with exact `filename`/JSON pointer/why.
5. Cross-file validation checks device IDs, endpoint ports, route next hops, reference integrity, timestamp order and known incompatible states. A *deliberately conflicting observations* test is allowed only if marked as multiple different source claims, not silently forced consistent.
6. Store revisions with hash, edit audit, authorization and diff; support import/export **whole scenario bundles** and per-source JSON. No secrets or ordinary production data should be bundled by accident; sanitize exports.
7. Never overwrite ordinary inventory, user conversations, actual audit, V9 authoring or immutable releases when loading or changing a scenario.

### 3.5 The actual GUI Scenario Workbench (non-optional)

Implement an accessible **Development → Scenario Workbench** or integrate into existing developer environment selection. User workflows:

- **Select / Create / Duplicate / Import / Export** scenarios, select base scenario, inspect revision/time and activate/deactivate with an explicit confirmation. Show persistent **SIMULATED DATA — scenario ID / revision / virtual time** banner in both assistants while selected.
- **All Sources** overview: 24-category grid with enabled/available/missing/stale/error counts, record count, last effective timestamp, editor action, source adapter verification status, and simple "Ask AI using this scenario" smoke test. There must be no source-only-in-JSON with no GUI path.
- **Schema-driven forms** with add/remove/edit row, device selection, protocol-specific state, timestamps, units, routing/prefix fields, event severity, configuration text Monaco editor; **Advanced JSON tab** for every source and import/export. Provide inspect/diff/undo for draft changes.
- **Topology editor**: graphical links plus underlying table/JSON, planned versus observed toggle, both endpoint names spelled exactly. Support repeated snapshots and observed-link removal/down state without changing planned graph.
- **Current config and snapshot manager**: per-device current simulated running config at selected virtual time, saved captures with time and label, exact diff, multiple backups; ability to make a change at T1 without mutating historical captures.
- **Telemetry chart and event timeline**: edit/add CPU/memory/traffic/error samples and source-health outages; virtual-clock play/pause/seek and time-window queries. Unit conversion and sample freshness visible.
- **OSPF/BGP/routing/controller panels**: edit OSPF/BGP neighbor states/IDs/timers/AS, route tables and forwarding, controller operational state; show logical consistency warnings and permit intentional contradictory source observations.
- **Incidents/drift/audit panel**: edit simulated alerts, jobs, command drift and collector status, clearly labeled test data—not actual job/audit history.
- **Documents, diagrams, context**: upload controlled fixtures, view extraction limits, seed model-visible prior conversation via actual test turns, preview attached docs and source-scoped permissions.
- **Scenario-runner panel**: test questions in Floating and Studio, show actual selected tool calls/results, parsed goals, evidence packet, LLM responses, citations, rejected claims and fallback, with side-by-side expected oracle visible **only to test author**, not AI. An ordinary user-facing assistant must never see private expected diagnosis.
- **Save Draft → Validate → Activate Revision → Inspect AI → Edit → New Revision**; hot switch must close old run scope and pin in-flight turns to their starting revision. Provide undo/deactivate/revert-to-prior-scenario revision without rewriting user history or global configuration.

The Workbench is not complete merely because one JSON editor exists. Demonstrate **file edit → validate → activate → real gateway read → model response**, AND **GUI edit → validate → activate → real gateway read → model response** for *each of all 24 source categories*.

## 4. Scenario time, consistency, isolation and evidence contracts

### 4.1 One active revision and one virtual clock per evaluation

At request entry, capture `scenario_id`, `revision_hash`, `virtual_now`, `mode`, `request_owner`, source-auth scope and allowed effect types. Keep this **read consistency token** pinned for every graph node and follow-up tool call in that user turn. A concurrent editor activation creates revision R+1 for *new turns*, never mixes half of R and R+1 inside an existing answer.

Scenarios need a timeline of events: e.g., at 09:00 link up; at 09:15 ACL changed; at 09:18 packet drops began; at 09:20 BGP stayed up. When virtual clock moves, the adapter selects state `effective_at <= clock` and preserves historical captures. Support explicit past-time queries against historical snapshots and source freshness. When a source timestamp conflicts with virtual clock (future sample), exclude or mark it invalid. Repeatable test runs freeze time; optional replay advances deterministic ticks without real timers being required for unit tests.

### 4.2 Deterministic facts versus edited claims

- User-entered **measurements** (counter sample, BGP peer state, syslog, configuration at time T) remain observed *scenario data*. A parser does not automatically overwrite these to match a calculated expectation.
- Computable **derived facts** (subnet membership, calculated rates, longest-prefix route, forwarding path, config diff, time windows) come from deterministic functions over the selected scenario; annotate inputs and assumptions.
- Independently computed **simulator traces** (ACL order, return path, VRF, static routing, bounded OSPF/BGP rules) are separate modeled predictions, not a device observation. If they disagree with manually entered state, expose `CONFLICTING` and ask the assistant to discuss the discrepancy.
- **Private test oracle** includes expected root causes, required evidence, prohibited conclusions and assessment rubric; it never becomes model-visible metadata or an exposed `document.read` file.

### 4.3 An auditable `EvidenceEnvelope`

Canonical tool return design (adapt to existing gateway models, do not break old clients):

```json
{
  "tool": "network.configuration",
  "source_id": "scenario:lab-branch-acl-001:running-config",
  "mode": "development_scenario",
  "origin": "simulated",
  "scenario_id": "lab-branch-acl-001",
  "scenario_revision": "sha256:...",
  "virtual_now": "2026-10-19T10:00:00+08:00",
  "coverage": {"devices": ["LAB-R1"], "scope": "current", "queried": true},
  "status": "AVAILABLE",
  "captured_at": "2026-10-19T09:55:00+08:00",
  "record_ids": ["cfg-r1-t0955"],
  "data": {"device": "LAB-R1", "config_kind": "current", "text": "hostname LAB-R1\ninterface GigabitEthernet0/1\n description Uplink"},
  "warnings": [],
  "citation_keys": ["S1"]
}
```

**Safety rules:** never put full configs/secrets into global logs; tool calls must redact credentials while preserving nonsecret diagnosis-relevant lines. Record deterministic source hashes and compact citations; point UI to authorized original records when the user expands evidence. Preserve `MISSING` vs `UNAVAILABLE` vs `STALE` and `NOT_QUERIED`. Protect against prompt injection in syslogs, document text, config comments and uploaded file names: these are **untrusted evidence**, not system instructions or tool execution requests.

### 4.4 Cross-mode parity and injection tests

Use the same actual source adapter interface for ordinary and development modes with independent sources. Verify that queries return equivalent normalized fields, statuses and citation semantics for identical known data (but different `origin`). Scenario mode must make no calls to configured external devices, even if InfluxDB, NetBox or OpenDaylight happens to be reachable; ordinary mode must not read user-edited scenario JSON implicitly. Include tenant/owner-bound activations, no cross-scenario cache leakage, change-of-mode reference invalidation, and cancellation during revision switch.

## 5. Weak-model intelligence architecture: make the *system* do more

**Base model policy:** maintain `qwen2.5:1.5b` and existing `nomic-embed-text` as the mandated Phase G baseline. Never install or switch a stronger model without explicit authorization. This plan is about improving the **whole assistant**, not fine-tuning or magically increasing parameter count. Optionally describe a separate, user-approved comparison with 4B/9B models only after a legitimate baseline is preserved and measured.

### 5.1 Typed `GoalSpec` before tool execution

A goal spec should represent: `goals[]` (e.g. answer fact, explain concept, compare state, diagnose, generate artifact, edit existing artifact), `entities[]` with verified IDs, `temporal_scope`, `environment_mode`, `source_preferences/constraints`, `artifact_type`, `allowed_effects`, `must_preserve`, `uncertainties`, `response_style`, `context_refs` and `required_output_claims`. Let the model propose **small structured fields**, not arbitrary executables or unrestricted tools. A schema/parser and deterministic authority resolver reject invalid combinations or request clarification.

Examples of genuinely distinct questions:

- “Why do routers need OSPF IDs?” → conceptual response; no network reads required.
- “What OSPF fields does the Junos V9 operation require?” → active V9 schema and profile; no live OSPF state.
- “Show R1's running OSPF configuration *in this simulated scenario*” → `network.configuration(current, LAB-R1)` plus optional precise section extraction.
- “Investigate OSPF flaps between LAB-R1 and LAB-R2 at 09:15” → scoped protocol state + syslogs + topology observed + interface state and timestamps; follow-up metrics only if relevant.
- “Change BGP neighbor only in the unsaved file” → Studio editor read + exact-base proposal; **no `v9.preview` unless generating a *new* operation is needed**.

Avoid prompt-specific keyword patches. To route implicit paraphrases, model should produce typed information needs, while a small deterministic source-authority table resolves those needs to valid tools. Multi-goal requests may require a dependency graph with independent subgoals. Resolve pronouns/reference correction and negation using explicit conversational semantics rather than arbitrary substring replacement.

### 5.2 Source authority resolution and minimal retrieval

For every information need, define authoritative sources, relevant alternative sources, timestamp requirements and disallowed substitutions. E.g. current config → scenario current-config adapter only; stored backup is **not** a valid replacement for current, but can be suggested as secondary context. Planned topology supports design but not measured reachability. Telemetry cannot establish a BGP neighbor without a protocol-state record; syslog is an event clue, not the current state. Inspect source-health before expensive follow-up calls.

Planning policy: (a) retrieve required sources, (b) execute and normalize evidence, (c) evaluate sufficiency, (d) make at most a bounded number of **decision-dependent follow-up calls**, (e) synthesize/clarify/respond. All tool selection is server-authorized and bounded by budget/latency/visibility. Avoid “collect all 24 every time,” which can overwhelm 1.5B context and obscure relevant information.

### 5.3 Compact model evidence packet instead of raw dumps

Before model synthesis, build a concise, typed **case file**:

```text
Question: Why did LAB-R1 lose reachability to LAB-R3 at 09:18?
Scope: scenario=lab-branch-acl-001 revision=... time=09:18, simulated
Entities: LAB-R1, LAB-R2, LAB-R3
Facts:
 F1 [S1,09:18] planned graph LAB-R1 -> LAB-R2 -> LAB-R3; not a reachability test
 F2 [S2,09:18] observed LAB-R2 interface Gi0/2 admin=up, oper=up
 F3 [S3,09:16] egress ACL denies 10.10.10.0/24 -> 203.0.113.0/24
 F4 [S4,09:17] scenario forwarding trace drops at LAB-R2 Gi0/2 ACL rule 20
 F5 [S5,09:18] syslog says ACL policy updated; source simulated
Missing: independently observed physical packet capture
Answer goal: explain strongest supported simulated cause; avoid declaring real network failure
```

The case file includes actual source IDs and claims; no private oracle root-cause label. Use token-budget-aware ranking, deduplication and provenance, preserving contradictory source records. Retrieve full raw evidence on demand, not blindly in every synthesis prompt. Keep citations tied to records, not invented `[S1]` references without a fetched source.

### 5.4 Hybrid deterministic reasoning + bounded model interpretation

Let deterministic components handle what they do well: subnet math, prefix masks, route longest-prefix, interface ownership, AS role association, simple ACL match ordering, config diffs, hop/path enumeration, counters/rate units, time comparisons, test provenance and schema validation. Let the model explain **why the computed and observed facts matter**, compare non-computational hypotheses, judge next useful observations and write a coherent conclusion.

Use scoped reasoning tasks rather than one massive instruction: `understand-goal`, `choose-information-needs`, `interpret-evidence`, `write-answer`; skip optional stages for direct lookups. Model output contract can be `answer`, `supported_claim_ids`, `hypotheses[]`, `missing_evidence[]`, `next_steps[]`, `need_more_information`, `uncertainty`. Repair a malformed model response at most once within budget; log real model calls, rejected drafts and fallback path. Do not silently put predetermined oracle answer into model prompt.

### 5.5 Factual **and relevance/completeness** verification

Existing factual guards have prevented hallucinations, but Phase F showed the assistant can attach a generic "no root cause" paragraph to a simple configuration question. Add **intent-relative answer quality checks**:

- Verify answer starts with response to user’s latest objective; each subsequent paragraph relates to it. No unsolicited diagnosis template for direct config/inventory queries.
- If user asks for **current scenario configuration**, return the actual scenario current config with device ID/capture time. If no current record but stored exists, say current unavailable and name the stored alternative accurately; do not say no records exist when other scoped records do.
- If user asks "show", give the requested records or selected text, not hide all content under an expandable summary. If user asks "why", present evidence-supported relationships and a useful inference; do not merely dump rows.
- Verify model claims against cited evidence: device/interface binding, router ID ≠ process ID misconception, BGP AS roles, timestamps, source mode, route/action, measured vs planned state, absent ≠ failed, no contradictory "no link" after path exists.
- Verify **necessary answer components** against typed `GoalSpec` (required config content, explanation, evidence caveat, missing fields, requested output type), while allowing diverse natural-language wording. Do not require irrelevant source tables or a fixed literary style.
- For underdetermined questions, lead with what *is known*, plausible discriminating hypotheses and one or two concrete missing observations; do not falsely imply root cause.
- Fallback must answer the original question when possible. An unrelated generic diagnostic disclaimer is itself a failing response. Attribute model acceptance/repaired synthesis/deterministic projection distinctly in traces and evaluations.

### 5.6 Latency and weak-model constraints

Baseline all prompt stages and observed timeouts on local CPU/GPU. Measure model-only versus full graph, warm/cold, serial under no build contention and representative load separately. Reduce token context, unnecessary rereads and redundant planning/synthesis calls; cache immutable source summaries **by scenario revision, virtual time, auth scope and source IDs**. Never cache a synthetic answer into ordinary mode or across users. Support cancellation, finite tool round/call budgets, a bounded verifier repair, degraded but **relevant** factual fallback, and honest model-limit reporting. Avoid blanket timeout inflation and endless retry loops.

**Optional later experiment, NOT phase dependency:** with explicit user permission, compare a feasible 4B/9B model against frozen Phase G cases under equal resource budgets, without downloading automatically. Report answer adequacy, fallback rate, prompt latency and memory. No speculative hardware assumption.

## 6. Ansible Studio intelligence and engineering requirements

### 6.1 Mode distinction and available tools

Studio AI shares the same conversation/goal-planning/evidence-reader logic as Floating AI. It additionally receives **authorized current Monaco buffer, selection, path, language, dirty flag, revision/digest, resolved imports and neighboring related files**, plus V9 metadata, parameter compiler/preview and actual Ansible variant/syntax validators. It should not assume the saved file equals the unsaved editor text.

Studio should support:

1. General conversation/calculation, networking concepts and technical questions without unnecessary editor/source reads.
2. Questions about the open unsaved file (“what does this OSPF section do?”), plus compare to previously saved content if explicitly requested.
3. Knowledge questions against *actual published* V9 profiles (“which fields are required for Junos static route?”).
4. Native CLI generation using V9 operation/profile resolution, typed input extraction, clarification, Jinja template rendering and ordinary supported output boundaries.
5. Genuine Ansible playbook generation using a **separately registered and validated Ansible variant**, with correct network collection/modules where supported; YAML syntax, variables and workspace integration. Missing variant = `UNAVAILABLE_VARIANT` or clearly unverified draft, **never falsely certified playbook**.
6. Multi-vendor/multi-operation plans: partition tasks by compatible platform and operation; collect target metadata, schema requirements and missing values, then compose only compatible artifacts; avoid copying Cisco CLI into Junos devices.
7. Safe single-/multi-file edits: resolve linked `group_vars`, `host_vars`, roles, includes/imports, inventory and docs within the authorized workspace; propose per-file exact-base diffs and a coordinated review bundle. Accept/Reject/Undo per-file or atomic group with conflict detection; explicit Save only; rollback of partial acceptance.
8. Troubleshooting existing playbooks: parse YAML structures, identify invalid variables/roles/module names, explain expected behavior, suggest minimal changes, independent syntax check where actual tool installed; no deployment.
9. Clarification and safety: avoid invented interfaces, next hops, neighbor IPs, vendor versions and device state; preserve unrelated OSPF/BGP content and comments.
10. Read-only Floating → Studio contextual **unsent draft** with evidence citations and source mode, but no surprise actual generation or editor write.

### 6.2 Multi-file safety/authorization protocol

**Inspect → plan → request only necessary files → cross-file reference resolution → construct exact-base patches → validate → show diff → user Accept/Reject/Undo → optional explicit Save.** File reads must be path-scoped and owner-authorized; no arbitrary filesystem tool available to model. JSON/YAML imports use a bounded dependency traversal with cycle handling and path-traversal prevention. If a variable is defined in a different file, explain where and propose changing the authoritative location, not duplicate a conflicting value in a playbook. Preserve newline style, Unicode, ordering/comments and unrelated sections. Validate the entire proposed bundle against fixed base hashes before any application.

When required Ansible tooling is unavailable, run what can be safely run (parser/schema/static lint) and mark deeper validation `NOT_RUN_TOOL_UNAVAILABLE`, never call it pass. Real playbook execution and network deployment remain forbidden.

### 6.3 Published knowledge and future operation authoring

Preserve the 141 current native bindings; support new senior-authored operation/category/parameter/schema/template via existing V9, and an isolated *brand-new* sample method smoke proving data-driven extensibility. A development scenario may select a compatible test device for V9 and call actual published renderer, but cannot alter production release by editing JSON. If a new native operation must be published to ordinary, honor authenticated Publish/Activate action and immutable audit. Keep certification independent.

## 7. The exact user examples Phase G must fix

### 7.1 R2 management address

Prompt: **“Show R2's management IP from stored inventory only.”**  
Expected: one concise inventory-backed address and citation; no topology/current config/LLM investigation or diagnosis. Preserve the correct `192.168.1.251` result in ordinary mode where original inventory has it. In development scenario, return scenario's own declared address with `simulated` provenance, not ordinary R2 by mistake.

### 7.2 R1–R2 evidence-only communication investigation

Prompt: **“Find the supported cause of any communication problem between R1 and R2 using recorded evidence only. Do not assume that missing measurements mean a failure.”**  
Expected when only planned graph and stale/simulated records exist: no confirmed current physical failure; summarize the evidence and relevant limitations concisely. Do not equate missing link state with down and do not include irrelevant table dumps unless user requests raw records.

Expected in **a deliberately active scenario with adequate simulated current evidence**: if interface down, ACL deny, return-route absence or OSPF mismatch is actually evidenced, produce a meaningful simulated finding—**do not repeat generic "no current measurements" when the developer has authored available scenario state**. Distinguish demonstrated simulated cause from hypothesized real-world cause.

### 7.3 R1 current configuration

Prompt: **“What is the current configuration for R1?”**  
Expected in development scenario: *return the scenario's actual current config* (or relevant full/selected content according to question), timestamp, platform and provenance. If a stored snapshot also exists, do not substitute it automatically. After user changes `running_configs.json`, validates and activates R+1, the same prompt should return the **new** content; old time/version remains queryable.

Expected ordinary without current capture: “I have no verified current running-config capture for R1”; if stored backups exist, mention the specific available snapshots and ask if user wants them. **Do not append root-cause diagnosis or claim there are no backups if a current-only query omitted them.**

### 7.4 Implicit, multi-turn and editing probes

- “The branch has been slow today. Figure out what's changed.” → time and branch resolution, task decomposition, relevant telemetry/syslog/config/state, optional targeted follow-up; no blanket source flood.
- “How about the return path?” → preserve previous path target/time and read relevant reverse-path evidence.
- “Same investigation, but yesterday” → shift temporal scope correctly, preserve target, compare timestamped records.
- “Explain BGP AS numbers in simple words” → no unnecessary private source reads; correct explanation.
- “Change only the BGP neighbor in this open file; keep OSPF.” → exact unsaved diff; safe Accept/Reject/Undo.
- “Use the `group_vars` value in the playbook and update the right file” → bounded cross-file reference and coordinated proposal.
- “Configure OSPF area 1 and a backup route on Cisco IOS-XE and Junos edge devices” → two vendors/two operations, compatible test inventory, V9 previews and supported Ansible variants, with missing-field clarification.
- “Explain the uploaded diagram” → only what OCR/vision actually supports; never invent unreadable connections.
- A system-looking instruction embedded in syslog/document/config comment → treated as untrusted evidence; cannot make the assistant ignore restrictions or deploy.

## 8. Remaining Phase F limitations explicitly absorbed into Phase G

| Phase F unfinished work | Phase G required resolution and objective proof |
|---|---|
| F1 native formatting and branch/oracle audit | Audit risk families + relevant conditional branches with **independent** expected CLI, negative/profile checks; correct approved methods via actual V9 publication; 141 remain active |
| F2 simulator independent conformance | Test 1–N hop LPM/ECMP/VRF/ACL, symmetric/asymmetric return paths, loops, protocol mismatches, congestion and explicit unsupported behavior; ground truth independent of implementation |
| F3 fresh routing and source-scope | Finish frozen Phase F 120-case first-exposure/matched comparisons, retain exposed failures; introduce a NEW Phase G holdout after repairs; prove correct scope and reader selection across all 24 categories |
| F4 local Qwen failures and quality gate | Complete 30 frozen quality probes (M0/M1/M2/M3), then brand-new Phase G blind cases; measure accepted model reasoning, repair vs fallback, unsupported claims and human-rated adequacy ≥85% or explicitly blocked |
| F5 all 141 Studio natural-language journeys | Actual shared gateway/V9 positive/negative journeys 47×3 with compatible isolated scenario targets; representative real browser per vendor/risk; no fake playbook certification |
| F5 complex Studio editing | Real multi-file reference parsing, revision-safe proposals, conflict handling, Accept/Reject/Undo, explicit Save; no network deploy |
| F6 current/saved/simulation/document modes | Complete scenario-backed current/saved/plan/observed data, normal-vs-dev isolation, docs/PDF/OCR/images, owner/context history continuity |
| F7 clipboard, service restart and UI parity | Browser exact multi-block copy plus actual Windows clipboard readback where permitted; classify external-tool block precisely; source-mode banner, scroll/accessibility, restarts/timeouts/cancellation |
| F8 independent benchmark and registries | Independent oracle isolation, 24-source matrix, ≥120 unseen routing tasks, ≥30 answer-quality tasks, permission tests, per-turn evaluator traces and reproducibility |
| F9 system acceptance | All phase gates, integrity, snapshot/pointer preservation, clean report and no false “complete” when model capacity prevents quality gate |

**Important:** Do not artificially require all Phase F pending work to finish *before* G scenario authoring starts. Establish the editable source environment early because it is necessary to run meaningful model tests. Track historical Phase F gates and new Phase G gates separately in a unified checkpoint.

## 9. Mandatory implementation cycle for EVERY source/AI/UI change

**Mandatory loop:** `reproduce → capture failing raw result → define independently expected result → hypothesize source → smallest coherent implementation → targeted static/unit check → actual gateway/runtime test → inspect model/tool/user output → fix cause → add regression → rerun adjacent and full affected checks → archive evidence → proceed`.

Never mark a batch complete just because Python/TypeScript compiles or HTTP returns 200. A response is incomplete if the correct data were fetched but the final text is wrong, too vague, irrelevant, unreasonably slow or misleading. **Do not defer fixable failures to another Phase H.** Genuine missing hardware capability, unavailable OS/browser permission, or 1.5B model limitation may remain explicitly `BLOCKED` after bounded, documented attempts; continue unrelated feasible work and preserve raw failed outputs.

Each iteration records immutable before/after artifacts under `tmp/phase-g/iterations/<timestamp>-<issue-id>/`:

```json
{
  "issue_id": "G3-CURRENT-CONFIG-LAB-R1",
  "starting_mode": "development_scenario",
  "scenario_id": "lab-branch-acl-001",
  "scenario_revision_before": "sha256:...",
  "scenario_revision_after": "sha256:...",
  "prompt": "What is the current configuration for LAB-R1?",
  "initial_tool_trace": "original-tool-trace.json",
  "initial_answer": "original-answer.txt",
  "independent_expected_claims": ["current config visible", "timestamped", "simulated label"],
  "root_cause": "actual discovered cause, not a guess",
  "patch_summary": ["real affected files"],
  "targeted_tests": [{"command": "actual command", "status": "PASS", "artifact": "junit.xml"}],
  "integration": {"selected_tools": ["network.configuration"], "final_answer": "corrected-answer.txt", "status": "PASS"},
  "model_attribution": "MODEL_ACCEPTED | MODEL_REPAIRED | VERIFIED_FALLBACK | DIRECT_FACT | FAILED",
  "neighbor_regression": "PASS",
  "data_integrity": "PASS",
  "status": "VERIFIED"
}
```

Use exclusive files for repeated attempts and keep first red runs. Print secret-free paths/checksums, not model-visible private oracles. Source authoring and scenario activation are intentional writes only to the selected development workspace. Actual ordinary user data and immutable release remain unchanged except valid existing authenticated release lifecycle operations.

**Cadence:** every batch targeted test + real reader; every AI behavior change paired model-gateway test and actual answer inspection; every scenario source addition two-way GUI/JSON tests and a read through actual graph; every editor change unsaved browser Accept/Reject/Undo; every milestone full affected suite and user-visible examples; before overall completion independent held-out benchmark + production-like restart + integrity/hash comparison.

## 10. Ordered Phase G stages and acceptance gates

### G0 — Resume, audit, preserve, and baseline both assistants

**Actions:** read latest actual checkout and Phase F evidence; classify historical versus current claims; inventory code boundaries; verify V9 `7a14...` *or diagnose real current pointer*, 141 bindings, editor buffers, SQLite integrity and protected staged hash. Record enabled planning/synthesis and Ollama identity; observe running Windows service owners before restarting. Freeze *new* Phase G eval cases/expected evidence **before the new changes see them**. Capture baseline four-turn R1/R2 conversation and representative Studio explanation/generation through actual gateway, including tool logs, source origin, final answer and model-vs-fallback attribution.

**Gate G0:** `docs/evaluations/phase_g_baseline.json` exists with source revision, active release, hashes, runtime flags, service ownership, original failure responses, preserved user-state fingerprints and frozen new evaluation registry hash. No unauthorized writes.

### G1 — Source registry and normalized evidence protocol

**Actions:** enumerate actual existing authorized tools/readers, their contracts and providers; map all 24 categories without inventing tool functionality. Implement one source registry with ownership, source type, freshness/temporal semantics, allowed query/filter shapes, ordinary vs scenario providers, minimum citations and per-reader authorization. Normalize return statuses and source provenance in the existing LangGraph gateway, including source errors and not-queried. Add sealed scenario-revision context to every read and source inspector.

**Tests:** 24 declared categories resolve to owned readers or scoped V9/document/session capability; direct current vs stored, planned vs observed, simulation vs ordinary, missing vs error; no cross-tenant records. Two fresh multi-source prompts show correct tool contracts. Preserve old client payload compatibility or migrate all callers explicitly.

**Gate G1:** source registry coverage matrix 24/24 mapped; all source status/authority tests pass; actual gateway returns correct typed envelopes.

### G2 — Scenario JSON schemas, starter data, virtual time and CLI authoring

**Actions:** version and validate all schema files; build at least **three complete editable example scenarios** (healthy, confirmed ACL/route/interface fault, stale/conflicting evidence). Each has values for all 24 source categories (some intentionally explicit unavailable only in negative scenarios), relevant documentation and related file refs, correct cross-file IDs/time, hidden independent expected outcomes. Support create/clone/import/export/validate/diff/revision activate/rollback and virtual-clock seek. Add controlled scenario state provider behind current reader boundary; **no actual device reads** in simulated mode.

**Tests:** JSON edit T1 R1 current config → Validate → Activate → actual `network.configuration` current returns T1 content; alter at T2 → history still shows T1, current shows T2. Similar representative test for observed topology, BGP state, metrics, syslog and source-health error. Validate all scenarios under external JSON editing and permission/invalid-field checks. Test deterministic replay and snapshot immutability.

**Gate G2:** strict valid all-category JSON, CLI authoring/import/export, frozen revision/time, true test-oracle isolation, zero ordinary data effects; current simulated config is actually answerable.

### G3 — Complete the 24-category GUI Scenario Workbench (HIGHEST PRIORITY)

**Actions:** implement all source editors and overview, proper use of existing frontend patterns/Monaco, source type forms and JSON Advanced view. Allow create/update/delete, linked files, source status/timestamp overrides, scenario time, preview/diff and explicit activation. Dashboard shows 24 source health states and how each is read. Provide actual scenario-runner in UI that asks the *same* Floating or Studio gateway, not a special hardcoded mock response. Display evidence trace for engineer/tester and user-facing simulated provenance.

**Mandatory 24×2 black-box matrix:** for each source category, (A) edit JSON externally, validate/activate, question actual assistant and verify changed source/answer; (B) modify same category using GUI, validate/activate, verify subsequent gateway read/response. Include source-specific negative and temporal versions. V9 category uses existing Knowledge Engineering GUI/isolated V9 authoring and scenario target selection—not arbitrary JSON overwrites of published knowledge. Attachments and conversation category must use existing parser/seed-turn flows, not fake model-visible transcript text.

**Gate G3:** 24/24 development source categories demonstrably queryable; 24/24 GUI entry/modify paths; 24/24 file/JSON entry paths except protected immutable V9 through authorized lifecycle; 24 source selection and provenance tests; all available in standard development browser after ordinary authenticated mode selection.

### G4 — Intent goals, source selection and adaptive investigation

**Actions:** improve model-proposed typed goals and deterministic source-authority mapping, compound dependency handling, entity/time reference repair, explicit negation, no-tool conceptual route, current vs stored and provenance separation. Build sufficiency/uncertainty checks using source envelope and bounded follow-up reads. Prevent tool fanout into unrelated categories. Real model-assisted plans must be distinguished from corrected/rejected ones.

**Tests:** original historical Phase E 60 as regression; finish Phase F frozen cases not yet tested, preserving their original results; new unseen Phase G prompts with all 24 source groups, ≥30 realistic multi-turn/implicit/compound; observed/planned scope; errors/missing/contradictions. Pair same-model baseline and new planner under pinned scenario revision, CPU budget and timestamps.

**Gate G4:** exposed historic regression ≥60/60 matched current baseline where previously reached, fresh routing ≥90% with no significant source-category drop against matched baseline (aspire ≥95%), zero unauthorized effects. Trace selected model plans, any server correction and every actual tool call. Failing exact holdout moves to regression; tune only on exposed copy, then evaluate a new untouched holdout for generalization.

### G5 — Evidence case-file reasoning and human-quality answer composer

**Actions:** build bounded typed evidence case file, deterministic calculations, evidence sufficiency and synthesis output contract, factual validator, **intent-relevance** and completeness scoring, latency controls, answer-first human-readable style. Eliminate generic irrelevant root-cause appendices. Model gets natural explanatory responsibility; verified fallback is useful and correctly attributed. One bounded repair where effective, not repeated blind retries. General questions use concise general prompts and no irrelevant network sources.

**Tests:** replay exact 4-turn R2/investigation/R1 config sequence; active scenario known-cause faults versus deliberately unknown/stale cases; OSPF IDs, BGP AS, interface ownership, route choice, Python/translation general knowledge; compare M0 model-only/M1 curated evidence/M2 full agent/M3 verified fallback using the actual installed Qwen and independent expectations. Freeze ≥30 **fresh** factual/answer-quality cases and grade the full prose, not just routing or HTTP status. Include time-to-first-answer, median/p95, fallbacks and provider call counts.

**Gate G5:** ≥85% *real M2 answer adequacy* on untouched independently assessed cases, **no critically false operational/certification/deployment claims accepted**, safe refusals to unsupported conclusions, fallback rate separately reported; every current-scenario direct configuration query retrieves actual authored config, not “no record”. If 1.5B proves incapable after bounded systematic improvements, mark G5 `FAILED_MODEL_CAPACITY` with exact evidence, not a fabricated pass; continue other stages.

### G6 — Simulator conformance and independent root-cause datasets

**Actions:** integrate existing model with scenario JSON/timeline, without replacing it. Independently grade IPv4 LPM/ECMP, static/recursive next hop, VRF, ingress/egress ACL order, return paths, unreachable, loop budgets, OSPF/BGP modeled mismatches, congestion trends and source conflict. Use healthy/control and several fault variants with ground truth hidden from graph; no full virtual NOS claim. If scenario manually injects contradictory protocol measurements, mark conflict rather than rewriting them.

**Tests:** at least ten independent fault/healthy cases × variants/negative samples; use actual source readers and both assistants; measured versus simulated and expected versus observed facts distinguishable. The assistant infers the supported cause and relevant uncertainty from evidence rather than a leaked label.

**Gate G6:** independent conformance matrix, case-specific causal explanations and fail-safe `UNKNOWN/UNSUPPORTED` where appropriate, no answer-key leakage, identical scenario-derived evidence for both assistants.

### G7 — Ansible Studio 141 published-native journeys and complex generation

**Actions:** execute all 47 × 3 (141) **controlled compatible-profile** NL request → target → V9 operation → schema parameter extraction/clarification → renderer → reviewable UNSAVED Studio draft; include malformed/missing inputs and multi-operation cross-vendor cases. Keep real R1/R2 inventory identity unchanged; use scenario test devices that truthfully match IOS-XE 17.9, Junos 23.4, VRP 8. Develop real Ansible playbook variant selection and composed YAML validation separate from native CLI. Test data-driven new isolated V9 operation without hardcoding.

**Tests:** one positive per binding plus relevant negative/profile checks and conditional branch risk-family samples; actual real-service paths not just fixture renderer. Representative browser Studio generation for all three vendors and major operation categories. Multi-file references, missing-module honest status, no device write, no hidden Save.

**Gate G7:** 141/141 controlled **gateway→Studio→V9** journeys pass, with per-case trace and artifact; source/parameter/profile/clause exactness. Independent playbook lane reports real supported/unsupported variant counts and truthful validation; no universal Ansible certification claim.

### G8 — Ansible Studio editor/multi-file references and Floating handoff

**Actions:** implement safe authorized related-file reader and import resolution, multi-file patch bundle, conflict/transaction review, Accept/Reject/Undo and explicit Save, exact unsaved base/revision, correct comments/formatting preservation. Studio can explain any selected code, general questions and schema before choosing edit/generation path. Floating handoff contextual, unsent and owner/scope checked.

**Tests:** one file unchanged after Reject, accepted BGP change only, Undo returns exactly, stale edit rejected, two files referencing variable corrected in authoritative location, cross-file stale digest fails safely, unauthorized path rejected, partial acceptance rollback, no duplicate conversation persistence. Test in real browser with pending unsaved files.

**Gate G8:** source-aware multi-file Studio workflow independently passes, reviewer controls work, no accidental save/deployment and browser data integrity remains correct.

### G9 — Documents, external/ordinary parity, and multi-turn continuity

**Actions:** complete and verify document uploads/PDF/OCR/images within real supported modalities; protect against prompt injection and path traversal; seeded multi-turn scenario context and owner boundaries; external provider availability/quality/freshness in ordinary mode, development scenario equivalent from editable source files. Test controller/telemetry/syslog and current config separately rather than using generic no-data banners. No source priority confusion when user changes scope mid-conversation.

**Gate G9:** text/scanned PDF, diagram limitations, stale attachment, multiple docs, uploaded config; conversation memory restart and updated reference; source errors distinguish missing; ordinary mode never uses simulated truth and simulated mode never queries actual devices.

### G10 — UI, operating system, service stability and profiling

**Actions:** preserve bounded Draft Change Summary scroll, whole-answer Copy and per-code Copy with Markdown/Unicode/newlines, source inspector, scenario banner, responsive modes, focus/keyboard, disclosure state. Test proper Windows clipboard readback separately from virtual browser, and Ollama timeout/cancel/restart. Test scenario read-consistency during edits and mode switches and workload contention (embedding build vs model inference serial where comparison matters). Enforce no loops and no orphaned turns.

**Gate G10:** browser UX and ordinary app restart pass; real OS clipboard either tested true PASS or documented external test BLOCKED with other app-level clipboard checks green; source/revision/time labels remain accurate; no unintended ordinary DB mutations.

### G11 — Independent evaluation and continuous regression acceptance

**Actions:** build `phase_g_source_matrix.json`, `phase_g_case_registry.json`, `phase_g_holdouts_v1.json`, per-case gateway source/answer/editor traces, and original-red/final-green evidence. Preserve exposed vs held-out distinction, human/independent expectation authorship, model attribution and per-source access matrix. Re-run paired legacy/current/full-model and baseline Qwen-only under pinned scenarios. Reject scoring based only on green JUnit count.

**Mandatory tests:** all 24 source categories JSON+GUI+real gateway; ≥120 fresh route/source cases with compound/multi-turn; ≥30 independently graded meaningful quality cases; adversarial owner/security tests; stale/conflicting/unavailable variation; 141 Studio paths; independent simulator; model-only vs with-evidence vs full graph vs fallback; exact sample conversation quality. Include per-domain failure rates, calibration, current/source freshness, false unsupported claims and response latency.

**Gate G11:** machine-readable independent coverage and results; no hidden first-run failure; no oracle leakage; per-capability C1–C7 measured and non-regression accepted.

### G12 — Release-safe final verification and handover

**Actions:** cold restart, active V9 release/index/141 bindings check, developer scenario activation/pin and all 24 source retrieval, Floating/Studio end-to-end tests, UI import/export/time travel, test oracle inaccessible, no external device calls, correct prompt/answer behavior, full affected backend/frontend/security suites, non-AI DB fingerprint and staged hash comparison, report blockages accurately. All tests should be documented with actual commands and original stdout/JSON artifacts.

**Gate G12:** no mandatory stage misleadingly marked PASS, preserved ordinary state, usable scenario editor and actual assistants, complete reports and reproducible resume checkpoint. If G5 model quality is failed, overall Phase G remains **partially complete** even if editable development-data milestone fully succeeds. Do not weaken thresholds after seeing results.

## 11. Dependency order and incremental delivery milestones

| Priority | Stages | Concrete user-visible outcome | Why it cannot wait |
|---:|---|---|---|
| 0 | G0 | Baseline verified and personal data protected | Avoid breaking completed Phase F work |
| 1 | G1–G2 | JSON scenario source contracts, current/saved topology/config/telemetry/protocol inputs and actual gateway adapters | Makes meaningful AI testing possible without unavailable external services |
| 2 | G3 | GUI editing for **every** category, timeline and activating a scenario | User's explicit highest-priority requirement |
| 3 | G4–G5 | Weak-model tool planning, evidence case files, relevance and meaningful answer quality | Direct cause of current disappointing assistant behavior |
| 4 | G6 | Independent healthy/fault simulation and explanation checks | Prevents diagnosis claims based on false oracle |
| 5 | G7–G8 | 141 V9 Studio journeys, real Ansible support boundaries and multi-file safe revision | Closes largest Studio capability gap |
| 6 | G9–G10 | Documents, mixed sources, UI/clipboard, context, latency and restarts | Reliability for actual usage |
| 7 | G11–G12 | Independent system benchmark and final handover | Proves real improvement rather than large patch count |

**Parallelization:** allow independent staged source editors, schema fixtures and separate analysis/tests to progress in isolated files, but avoid concurrent destructive ordinary DB operations, two active scenario switches in the same test namespace, or simultaneous heavy Ollama benchmarking and full Chroma builds. Use independent test workspaces and deterministic scenario revision pinning.

## 12. Definitive acceptance criteria and scoring

| Axis | Minimum acceptance evidence | Gate |
|---|---|---|
| Developer source availability | **24/24** model-visible categories have complete scenario-provider coverage; intended unavailable test states explicitly typed | Hard |
| JSON editability | 24-category source file import/edit/validate/activate/retrieval paths, with immutable V9 handled by its authorized lifecycle | Hard |
| GUI editability | 24-category overview and real browser Create/Edit/Preview/Activate workflows, no placeholder buttons | Hard |
| Current simulated configs | Live-in-scenario config for test device returned on actual chat request, changes after revision activation, history preserved | Hard |
| Planned vs observed topology | Contradictory snapshots and temporal changes correctly queried with origin/time | Hard |
| Telemetry/protocol/logs | Timestamped simulated metrics/syslog/OSPF/BGP/routes/controller independently editable and read through authorized gateway | Hard |
| Scenario correctness | Test-only private oracle inaccessible to LLM; deterministic replay, source isolation and no real device access | Hard |
| Native V9 continuity | 47 operations/141 compatible bindings on actual active immutable release; independent verified risk outputs | Hard |
| Source routing | Historic exposed nonregression and ≥90% fresh correctness with no significant source-class regression | Hard |
| Answer quality | ≥85% independently adequate **actual full-agent M2** on fresh cases; separately disclose verified fallback | Hard; may fail model-capacity |
| Hallucination/safety | 0 accepted critical unsupported root causes, device state, commands, auth claims or deployment effects in scored tests | Hard |
| Studio native | 141 controlled NL→actual gateway→V9→reviewable output journeys; real browser sample | Hard |
| Ansible variant | Correct separate lane with genuine parser/syntax checks when tooling exists, honest unsupported/not-run otherwise | Hard distinction; tool absence can be BLOCKED |
| Multi-file editor | Scoped related-file refs, exact-base coordinated diffs, conflict guard, Accept/Reject/Undo/explicit Save | Hard |
| Reasoning attribution | MODEL_ACCEPTED, MODEL_REPAIRED, VERIFIED_FALLBACK, DIRECT_FACT, FAILED recorded; M0/M1/M2/M3 separate | Hard |
| Runtime preservation | Original staged checkpoint/user DB, chats, inventory, unsaved buffers and V9 release/rollback intact | Hard |
| Latency | Real median/p95 against current measured hardware, bounded CPU/Ollama calls, cancellation; no invented fixed SLA | Measure and report, regression gate |

**Interpretation of "better performance than a weak model is capable of":** quantify the *system uplift* by comparing `qwen2.5:1.5b` alone (M0), the same model with curated relevant facts (M1), full CogniShield orchestrated reasoning (M2), and factual deterministic fallback (M3), holding data/cases constant. Show both end-to-end success gain and rate at which the **model actually synthesizes** correct results. The whole system can outperform a model-only baseline on structured network tasks without claiming that Qwen's general reasoning weights have improved.

## 13. Required test scenarios (minimum starter set)

**S-HEALTHY-ALL-SOURCES:** three compatible fictional lab devices, healthy interfaces/BGP/OSPF, routes and return paths present, matching planned/observed links, current configs, older backups, normal telemetry, benign syslogs, no active faults, source health green, a few legitimate historical incidents, readable docs/diagram and seeded context; 24 categories available. Asking "find fault" should report no supported fault, not hallucinate one.

**S-ACL-BLOCKS-RETURN:** designed path LAB-R1→LAB-R2→LAB-R3, all links currently up, route forward present, scenario ACL at LAB-R2 denies return traffic, relevant config and simulator trace, concurrent logs/metrics; answer should explain ACL as simulated supported cause *if* trace demonstrates it, distinguish unmeasured physical results.

**S-BGP-AS-MISMATCH:** neighbors and config specify conflicting peer AS values, observed session Idle/Active, syslog corroboration, unrelated interfaces healthy, old backup had matching AS; answer should give actual local/remote AS mapping and change time, not swap roles.

**S-OSPF-TIMER-MISMATCH:** configured hello/dead mismatch, observed adjacency down or stuck, matching interface state and logs; avoid router ID/process ID confusion.

**S-LINK-DOWN:** an intermediate interface specifically down with temporal event and matching loss of path, but don't misattribute the down state to source or destination device.

**S-RETURN-ROUTE-ABSENT:** forward route exists but reverse route absent; distinguish asymmetric reachability from bidirectional proof and label missing route observation as unavailable if it wasn't queried.

**S-CONGESTION:** valid rising traffic/discards and sampled timestamps, no fabricated latency measurement if no latency data; explain correlation versus confirmed bottleneck.

**S-STALE-AND-CONFLICT:** syslog says link down yesterday but current interface says up; stale topology shows old neighbor; controller state differs. Assistant should compare temporal sources and avoid unsupported current outage.

**S-NO-MEASUREMENTS:** all planned and backup data present, current telemetry/protocol unavailable; explain limits, ask for specific next evidence; no presumed failure.

**S-NEW-V9-OPERATION:** isolated authorized NTP new operation, schema generated from parameters, new binding through permitted test publish/activate, compatible scenario device, Studio preview. Ordinary current 141 catalog remains untouched.

Each scenario needs explicit `simulation.json` observable inputs, hidden independent ground truth, reproducible time, positive/negative user prompts, intended source lists and prohibited claims. Provide at least one **user-created from scratch** GUI scenario, not only prebundled seeds. The assistant must work after field edits without adding a new Python branch for a particular device name or test prompt.

## 14. Expected detailed completion artifacts

```text
docs/PHASE_G_IMPLEMENTATION_RESULTS.md
  - chronological user-visible changes, before/after actual assistant answers,
    real model-vs-fallback attribution, failures, remaining limitations

docs/PHASE_G_SOURCE_AND_SCENARIO_WORKBENCH_REPORT.md
  - exact 24-category source registry, JSON+GUI coverage matrix,
    schemas, activation hashes, virtual time and end-to-end tool observations

docs/PHASE_G_RUNTIME_AND_RELEASE_REPORT.md
  - actual active immutable V9 release/index, 141 bindings and rollback,
    Ollama model, flags, source-mode separation, process/restart evidence

docs/PHASE_G_CONTINUATION_CHECKPOINT.md
  - last fully verified iteration, protected stage/DB hashes, live services,
    next actionable failure, commands to resume and blockers

docs/evaluations/phase_g_stage_state.json
  - G0–G12 status PASS/FAILED/BLOCKED/NOT_RUN and evidence references

docs/evaluations/phase_g_source_matrix.json
  - 24 categories, ordinary/scenario tool adapters, GUI+JSON tests,
    stale/error and time-travel cases, source provenance

docs/evaluations/phase_g_case_registry.json
  - frozen routing/quality/editor/permission specs and oracle hashes

docs/evaluations/phase_g_routing_results.json
  - original/exposed and genuinely fresh source-routing scores and traces

docs/evaluations/phase_g_model_quality.json
  - M0/M1/M2/M3 per-case answer scoring, model calls, latency, fallback

docs/evaluations/phase_g_scenario_conformance.json
  - independently computed forwarding/protocol/traces and negative cases

docs/evaluations/phase_g_studio_141_results.json
  - full 47 × 3 actual controlled gateway/V9/Studio journey results

docs/evaluations/phase_g_gui_source_edit_matrix.json
  - 24-category external JSON edit and browser edit/activate/read proofs

tmp/phase-g/iterations/*
  - retained original failing traces, patches, commands, JUnit, reruns,
    approved screenshots, preservation checks, result.json, README.md
```

Do not invent completed files/test results or fake source paths. If actual repository layout differs, reuse its established directories and record resolved locations. Heavy ignored evidence stays out of the protected staged patch. Mark any truly impossible external validation precisely `BLOCKED_ENVIRONMENT`, not PASS or silently NOT RUN.
ADDITIONAL MANDATORY PHASE G ACCEPTANCE REQUIREMENTS

## 15. Additional mandatory Phase G acceptance requirements

1. Prove measurable intelligence improvement using qwen2.5:1.5b.

Evaluate model-only (M0), model with curated evidence (M1), full LangGraph system (M2), and verified fallback (M3) using independently prepared unseen cases. Define the improvement threshold before running the benchmark.

Measure factual correctness, completeness, relevance, technical reasoning, evidence grounding, tool selection, latency, and actual user-visible answer quality. Report model-generated success separately from fallback-assisted success.

2. Independently verify all seven intelligence capabilities.

For C1–C7, define explicit acceptance criteria, independent test datasets, per-capability scores, regression tests, and real browser/gateway verification.

Do not declare overall intelligence acceptance if a critical capability fails, even when aggregate routing accuracy or unit-test coverage is high.

3. Verify genuine Ansible playbook coverage separately from native V9 CLI coverage.

Audit all 141 vendor-operation combinations, recording native CLI availability, supported playbook variants, generation success, YAML validation, Ansible validation where available, and unsupported combinations.

Implement missing capabilities where required by the Phase G specification. Never present raw vendor CLI as an independently validated Ansible playbook.

4. Assess model suitability without changing the approved model.

Retain qwen2.5:1.5b and nomic-embed-text. Evaluate whether the strengthened system meets the seven capability requirements within acceptable latency and hardware resources.

Document any remaining model-capacity limitations and recommend alternative model sizes only when justified by measured failures and available hardware. Do not download, switch, or install another model without explicit user approval.

IMPORTANT: All existing requirements remain mandatory, especially the 24-source editable JSON/GUI Scenario Workbench, actual source consumption by both assistants, unfinished Phase F repairs, complete Studio engineering workflows, preservation safeguards, and implement → test → inspect → fix → retest iterations.

Treat these four additions as formal acceptance gates, not optional suggestions or documentation-only work.

## 16. Exact final demonstration required in the actual browser

1. Open Development Scenario Workbench in standard application. Select **S-HEALTHY-ALL-SOURCES**; confirm 24/24 source panes populated and banner shows scenario/time.
2. Ask Floating AI for LAB-R1 **current** running configuration: correct text and scenario timestamp appear; source inspector proves current-config reader returned it.
3. Use GUI to edit LAB-R1's current config at later virtual time and an external text editor to modify an allowed scenario JSON field, Validate/Activate R+1. Ask again: new value appears, old snapshot still retrievable at old time. No ordinary config DB mutation.
4. Trigger syslog link down, edit observed topology and interface status; ask why a path is failing. Model plans appropriate reads, derives supported simulated explanation or reports uncertainty, never calls physical network.
5. Inject conflict: stale syslog says down but current interface says up. Ask the same question; answer distinguishes current and historical without false certainty.
6. Edit CPU/traffic/error series, OSPF/BGP state, route next hop, incidents, controller operational state and monitoring availability through GUI. Verify each source feeds its actual authorized reader with matching units/time and correct answer.
7. Ask general networking question. Show no irrelevant private/source fanout. Ask compound follow-up with pronouns and temporal scope; inspect source selections and answer completeness.
8. Open Studio with unsaved playbook using `group_vars` and related file. Ask Studio to explain, then propose a limited multi-file correction. Accept/Reject/Undo and Save boundaries operate exactly as stated.
9. Ask Studio for multi-vendor OSPF and static route on compatible **scenario** lab devices. Show distinct V9 native output, schema-driven clarifications and actual Ansible variants where available; unsupported variants labeled honestly.
10. Switch to ordinary mode. Show synthetic metrics/configuration no longer appear and actual unconnected sources are appropriately unavailable. Return to saved scenario and verify no cross-mode history/data leak.
11. Run hidden-oracle and fresh holdout evaluation; print real C1–C7 and M0–M3 scores, model accepted/fallback rate and timings. Show the same weak model's measurable system-level uplift where demonstrated.
12. Cold restart the frontend/backend, repeat direct config and scenario source health checks; verify original protected staged hash, all ordinary non-test records and active immutable V9 release remain unchanged.

**The user-facing definition of completion:** Both assistants answer natural questions against the *user-edited, time-correct development environment* instead of defaulting to missing external measurements; they produce accurate, relevant, well-explained findings, or an evidence-qualified uncertainty; Studio additionally produces proper vendor/operation-specific reviewable artifacts and safe file edits. All 24 source categories are configurable in JSON and GUI and demonstrably retrievable. Phase F open defects and independent evaluations are actually resolved or explicitly reported as still failed. **No fictional 100% intelligence guarantee.**

---

## 17. Codex execution directive

**Read the entire document and actual current repository before source edits; then implement G0–G12, not another proposal.** Start with the complete 24-source **editable** development Scenario Workbench and real reader integration, because the user requires accurate simulated current configuration, topology, telemetry, syslog and protocol data to be available to the LLM during testing. Preserve 141 published native bindings, authenticated engineer publication, user data and existing staged patches. Use installed `qwen2.5:1.5b` and `nomic-embed-text` without downloading new models. Keep planning/synthesis enabled. Complete the unfinished Phase F evidence/quality/Studio/simulator/browser work. After each small patch, run affected tests and actual gateway/GUI/model checks, inspect the final answer—not only green assertions—fix root causes immediately, record first red and final green evidence, and continue. Do not conceal weaker-model limitations with fallback-only success claims. Final status must distinguish completed development-source coverage from model-quality gates still blocked.
