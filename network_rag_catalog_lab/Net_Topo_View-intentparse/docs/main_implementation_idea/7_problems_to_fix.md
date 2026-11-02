# Phase G — Completeness-First, Evidence-Driven Network Investigation Architecture

## Mission and architectural direction

Continue developing my existing Network RAG / CogniShield AI Network Engineering Assistant.

Repository:

`C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\network_rag_catalog_lab\Net_Topo_View-intentparse`

**I authorize a comprehensive, but controlled, architectural improvement covering Problems A–G described below.**

The previous implementations focused heavily on strict planning contracts, minimum reader selection, optional-reader suppression, model self-assessment and evidence metadata.

Although these features improved structural compliance, they have not produced the level of technical correctness, completeness and reliability I want.

I want to adjust the architectural priorities.

My main objective is:

**Given a network engineering question, investigate the relevant available sources thoroughly, understand the network as a whole, identify the correct technical cause, pursue missing information automatically when possible, and produce a complete, evidence-grounded answer.**

I value correct diagnosis, comprehensive coverage and reliability above minimizing reader calls or achieving the shortest response time.

Excessive but relevant authorized retrieval is generally preferable to missing evidence that could materially affect the diagnosis.

However, this permission must never override authentication, source authorization, explicit user prohibitions, privacy controls, read-only restrictions or engineering-action safeguards.

The system should operate more like a capable network engineer who investigates, cross-checks sources, compares historical information, examines topology, verifies conclusions and continues investigating when necessary.

## Existing architecture to preserve

Keep the successful model-neutral design:

- Qwen2.5 1.5B for ordinary local requests.
- Gemini 3.1 Flash-Lite for approved complex G4 planning.
- Existing LangGraph workflow.
- Existing registered, authorized network readers.
- Gemini 3.5 Flash-Lite for G5/G6 interpretation and causal reasoning.
- Existing provider-neutral model-role architecture.
- Existing authenticated gateway.
- Existing V9 network knowledge, inventory and engineering-operation safeguards.
- Existing Floating AI and Ansible Studio.
- Existing synthetic owner consent and persistent provider quota ledger.

Preserve the original successful model-neutral integration behavior, especially MN-01, MN-02 and MN-03.

These demonstrated useful planning, source retrieval, configuration/state correlation and technically correct selected-case explanations.

Do not replace the architecture simply because later qualification cases exposed deficiencies.

Improve it.

The lower-level implementation, graph routing, evidence contracts, reader budgets and timeout policies may be modified where justified by these requirements.

## Historical evidence to inspect

Read:

1. `docs/PHASE_G_MODEL_NEUTRAL_MULTI_MODEL_ARCHITECTURE.md`
2. `docs/PHASE_G_MODEL_NEUTRAL_CONTINUATION.md`
3. `docs/PHASE_G_MULTI_MODEL_G4_G6_QUALIFICATION.md`
4. `docs/PHASE_G_MULTI_MODEL_INTELLIGENCE_IMPROVEMENT.md`
5. `docs/PHASE_G_EVIDENCE_AWARE_HARNESS_ENGINEERING.md`
6. Relevant G4/G5/G6 requirement and acceptance documents.
7. Preserved raw successful MN integration traces.
8. Original 30-case qualification traces.
9. Latest 12-case and six-paired-case evaluation traces.

Inspect the current actual implementation before modifying code.

The evidence-aware harness currently remains default-OFF because its paired evaluation produced no demonstrated improvement: 2/6 complete tasks in both control and enhanced arms.

Reuse existing code where it is useful.

Do not assume the current harness is adequate merely because its regression tests pass.

---

# PART A — Broad Investigations Must Scan Across Available Authorized Sources

## Problem A: Incomplete source discovery and wrong reader selection

Current behavior sometimes relies too heavily on Gemini 3.1 selecting a minimal reader set.

The planner can miss relevant sources, select an inappropriate reader family or leave material information unexamined.

My preferred engineering behavior is:

**For broad network investigation requests, inspect all available authorized reader families relevant to the investigation scope rather than aggressively minimizing reads.**

A network engineer routinely checks multiple sources because a fault may not be obvious from the first record.

I do not want the system to sacrifice evidence coverage merely to satisfy a strict minimum-reader policy.

## A1. Introduce breadth-aware investigation modes

Reuse the existing intent router and request contract.

Distinguish, at minimum:

### Narrow targeted investigation

Example:

"Show R1 GigabitEthernet0/1's current administrative and operational state."

The query is specific.

The system may use a small targeted reader set because the user only asks for specific information.

### Broad comprehensive investigation

Example:

"Investigate why R1 cannot reach R3. Find the root cause and explain the incident."

The question is broad.

The system should proactively inspect all relevant registered and authorized reader families, potentially including:

- Operational state.
- Event and incident records.
- Current/running configuration.
- Historical/saved configurations.
- Inventory and topology.
- Available derived analysis.
- Available simulated or modeled results.

Only actual registered, applicable source capabilities may be executed.

A reader category that does not exist, is unavailable or is prohibited must not be fabricated.

### Explicit source-restricted investigation

Example:

"Investigate R1 using operational state only. Do not query configuration."

The explicit restriction overrides broad scanning.

### Explicit no-read advisory

Example:

"Without retrieving any new records, tell me how I could troubleshoot a down interface."

No new readers should execute.

Use permitted already-owned context and appropriately qualified advice.

## A2. Broad classification policy

Do not require exact phrases or benchmark keywords.

Use the existing semantic intent framework and actual original-request meaning.

If a request asks for a root cause, incident investigation, comprehensive diagnosis or an unexplained connectivity failure, treat it as requiring broad evidence coverage unless its scope is explicitly narrowed.

When classification is uncertain and the user has authorized a general investigation, favor comprehensive but scope-bounded retrieval over silently omitting potentially important relevant sources.

Never interpret broad investigation as authorization to inspect unrelated users, tenants, scenarios, devices or files.

## A3. Build an authorized source coverage plan

For broad investigations, enumerate every applicable registered reader family within the approved scenario and device scope.

Record for each source family:

- Available and authorized.
- Available but prohibited for this request.
- Not registered.
- Temporarily unavailable.
- Queried successfully.
- Queried with zero matching results.
- Query failed.
- Not queried because of a documented budget or scope limitation.

The objective is not merely to retrieve a certain number of records.

It is to determine whether the relevant source families have actually been inspected.

If the user requests comprehensive investigation, missing coverage must remain visible.

Do not silently mark missing evidence as complete.

## A4. Read comprehensively without causing uncontrolled data collection

When a source family is authorized and relevant, execute an appropriate initial read.

For large topologies or source collections:

- Begin with a scoped summary/index or available filtering capability.
- Expand into relevant devices, interfaces, time windows and records.
- Use pagination where provided.
- Preserve all discovered relevant references.
- Do not silently discard records because of output limits.

If the source is very large, use bounded progressive discovery instead of indiscriminately transferring the entire database.

A broad investigation should cover all relevant source families, but it need not retrieve every unrelated record in those sources.

## A5. Do not let Gemini omit mandatory broad coverage

Gemini 3.1 should still plan and prioritize investigation.

However, its proposed plan is not necessarily the entire investigation.

The backend should reconcile the proposed plan against the source coverage requirements.

For a broad request, authorized source families omitted by Gemini may be added through the server's existing validated reader pathway.

Attribute these as server-added coverage reads rather than falsely reporting that Gemini selected them.

Preserve Gemini's planned reads and allow useful additional reads.

A wrong initial plan should not unnecessarily prevent the system from gathering enough evidence.

## A6. Acceptance requirements

Demonstrate that broad requests investigate the relevant available authorized source families.

Demonstrate that narrow requests remain efficient.

Demonstrate that explicit source restrictions and no-read instructions remain effective.

Do not score an extra authorized, materially relevant reader as a complete-task failure solely because the same diagnosis might have been possible with fewer reads.

Continue measuring unnecessary reader usage separately as an efficiency metric.

---

# PART B — Completeness First; Additional Evidence Is Preferable to Missing Evidence

## Problem B: Strict optional-reader suppression and incomplete reader plans

The previous required/optional distinction helped prevent unnecessary reads but sometimes left the system without information it needed.

I do not want the system to be so strict that a useful reader cannot execute merely because Gemini classified it as optional.

**Missing material information is a greater problem than an extra authorized, relevant read.**

## B1. Relax soft reader-selection restrictions

Inspect current:

- Required/optional planning.
- Reader eligibility.
- Source-only enforcement.
- Duplicate-reader handling.
- Outcome-to-reader mapping.
- Evidence sufficiency and reader hint generation.

Allow the investigation workflow to add or execute useful supplemental reads when:

- The source is registered.
- The source is authorized.
- The target and parameters are valid.
- The requested information is relevant to the original question.
- The query is not a redundant identical read unless a different time/scope justifies it.

Do not reject a useful read solely because it was not in Gemini's first minimal plan.

Do not reject a read solely because it was originally classified optional.

A repeated reader with different valid parameters, source categories or time ranges must remain eligible.

## B2. Clarify what may be bypassed

I authorize bypassing or relaxing **soft planning restrictions**, such as:

- Optional-reader suppression.
- Overly aggressive minimum-reader optimization.
- Heuristics that discourage useful additional evidence.
- Unnecessary one-time-reader constraints when a distinct query is needed.

I do NOT authorize bypassing:

- Authentication.
- Owner permissions.
- Scenario permissions.
- Source authorization.
- Explicitly forbidden reader families.
- Target scope.
- Cloud consent.
- Read-only restrictions.
- Quota enforcement.
- Credential privacy.
- V9 engineering safeguards.

Do not weaken security in the name of comprehensive retrieval.

## B3. Make the original requested outcomes authoritative

The user request must remain the source of truth for what needs to be answered.

A planner cannot silently drop the maintenance question, historical comparison, specific interface ownership or other requested outcomes.

Maintain an outcome-to-evidence coverage representation.

The system must distinguish:

- Outcome adequately addressed.
- Outcome partially addressed.
- Material fact still missing.
- Available source not queried.
- Source queried but inconclusive.
- Source unavailable.
- Outcome cannot be established from permitted evidence.

Do not treat successful tool execution as proof that the outcome is correctly answered.

## B4. Prefer investigation over premature completion

When an additional authorized read could materially improve a broad investigation, allow it.

When no further relevant evidence exists, produce the strongest correctly qualified answer possible.

Do not keep executing unrelated readers merely to reach a numerical retrieval target.

Do not invent missing values.

## B5. Acceptance requirements

Reproduce incomplete-plan cases where the planner initially misses relevant evidence.

Verify that the system can recover by executing a legitimate supplemental read.

Verify that all user-requested outcomes are retained.

Verify that forbidden or unrelated sources remain excluded.

---

# PART C — Inventory-Aware, Topology-Aware Interpretation and Validation

## Problem C: Device/interface ownership errors and incomplete network context

Gemini has previously misattributed interface addresses, device ownership and forwarding relationships even when source records were correct.

I want the AI to understand the network from a higher-level view before and during technical interpretation.

**Inventory and topology should become first-class context for interpreting and validating network evidence.**

## C1. Reuse the existing inventory and topology sources

Inspect existing:

- SQLite inventory.
- Device registry.
- Interface records.
- Device roles and locations.
- Vendor/platform metadata.
- Registered interface addresses.
- Planned/documented topology.
- Available observed adjacency information.
- Existing topology model and readers.
- Existing target-resolution and entity-ownership logic.

Do not create a second inventory database.

Do not make Gemini invent topology from memory.

Construct a network-context representation from actual authorized inventory and topology records.

## C2. Build a scoped network context map

For an authorized network investigation, supply a useful structured network overview.

It should represent:

- Device identifiers.
- Device names.
- Roles.
- Vendor/platform.
- Interface ownership.
- Interface addresses where known.
- VRF memberships where recorded.
- Documented connected endpoints.
- Topology link identity.
- Source and timestamp.
- Whether a connection is documented/planned or operationally observed.

For broad investigations, provide a compact overview of the authorized scenario's full device inventory and topology.

Also provide a more detailed subgraph around the implicated devices and forwarding path.

For large inventories, use hierarchical/paginated context rather than silently truncating the graph.

The model must be able to request more relevant inventory details when needed.

## C3. Distinguish inventory truth from operational truth

Inventory describes what the management system records.

It does not necessarily prove that a physical link is currently operational.

For example:

Inventory:

`R1 Gi0/1 → R2 Gi0/1`

Running configuration:

`R1 Gi0/1: no shutdown`

Current operational state:

`R1 Gi0/1: down/down`

The model must understand:

- Inventory expects connectivity to R2.
- Configuration says the interface is administratively enabled.
- Operational state says the interface is currently down.

There is no necessary contradiction.

Do not claim the interface is operationally up because the configuration contains `no shutdown`.

Do not claim the physical link is operational because the inventory lists an adjacency.

## C4. Validate device and interface relationships

Use actual structured records to validate factual identity relationships.

Examples:

- Is this interface owned by the claimed device?
- Does this address belong to the claimed interface in the relevant evidence?
- Is the peer endpoint associated with the correct device?
- Is the interface part of the correct VRF?
- Does this route's next hop correspond to the identified forwarding direction?
- Is the named connection planned, observed or merely documented?

When authoritative structured records establish an exact relationship, Gemini's explanation must not silently swap ownership.

If the structured source records conflict or are stale, preserve the disagreement instead of arbitrarily selecting one as universally true.

## C5. Give Gemini high-level and detailed context

The reasoning input should include both:

1. A concise network-wide overview.
2. Detailed evidence for the actual investigation targets.

Avoid flooding the model with every interface field on every unrelated device when a graph summary would suffice.

Preserve stable entity IDs and links to the detailed underlying records.

## C6. Acceptance requirements

Test:

- Wrong interface ownership.
- Swapped interface addresses.
- Forward versus reverse path.
- Transit device versus endpoint device.
- Multiple interfaces with similar names.
- VRF-specific identities.
- Planned versus observed adjacency.
- Inventory records that disagree with current state.
- Multi-hop routing and ECMP.

The system should preserve correct relationship attribution and report uncertainty when source identities cannot be reconciled.

---

# PART D — Temporal Investigation Through Snapshot Comparison and Configuration Diffs

## Problem D: Unsupported historical conclusions and insufficient change investigation

I want the system to investigate configuration and operational history systematically.

Time should act as an initial search boundary.

Configuration comparison should then help pinpoint the relevant commands and changes.

The system should compare snapshots to identify what differs, examine relevant event records and determine whether the difference is associated with the network problem.

Do not merely compare timestamp strings and assume a causal transition.

## D1. Preserve configuration artifact identity

For each configuration artifact, retain:

- Device identity.
- Configuration source kind.
- Saved versus running versus historical running.
- Capture timestamp.
- Configuration revision or snapshot identity.
- Vendor/platform.
- Interface and protocol context.
- Actual raw configuration.
- Parsed structure when available.
- Source provenance.
- Known relationship to other snapshots.

Do not assume that two files represent the same operational state just because they belong to the same device.

Do not compare different devices or contexts as though they are successive revisions of the same configuration.

## D2. Historical search strategy

For questions such as:

"When did the routing problem appear, and what configuration change caused it?"

Use this workflow:

1. Identify affected devices and network outcomes.
2. Identify the approximate incident time window.
3. Discover available saved, historical and running configuration snapshots.
4. Select compatible snapshots covering or surrounding the window.
5. Compare changes across snapshots.
6. Identify interface, route, VRF, BGP, OSPF, ACL or related configuration differences.
7. Correlate those differences with available operational observations.
8. Examine actual change events and incident records.
9. Explain the most strongly supported causal relationship.
10. Clearly qualify any unestablished transition time or root cause.

Time narrows the investigation.

Configuration differences identify candidate modifications.

Event records and observed network behavior help establish whether and when a modification actually took effect.

## D3. Implement generalized configuration comparison

Reuse available parsers and vendor-aware configuration knowledge.

Where practical:

- Normalize relevant configuration structure.
- Identify added statements.
- Identify removed statements.
- Identify changed values.
- Preserve interface/protocol/VRF ownership.
- Avoid losing command context through naive line comparison.
- Retain raw lines and original source references.
- Support relevant Cisco IOS-XE and Junos representations according to the actual registered environment.

Do not invent vendor behavior.

Where no reliable parser exists, provide a transparently limited textual diff with original source context.

Do not claim semantic equivalence merely because two configurations have superficially similar lines.

## D4. Treat saved and running configuration correctly

A saved configuration is an artifact of what was stored or captured.

It is not automatically proof of what the device was actively running at the capture time.

A running-configuration snapshot is evidence of the running configuration at its documented capture time.

For example:

Saved artifact at 09:00:

`VRF = BLUE`

Current running configuration at 11:00:

`VRF = RED`

The records prove that the two artifacts differ.

They do not automatically prove that an active VRF transition occurred between 09:00 and 11:00.

To establish the historical transition, inspect actual historical running-state observations or trustworthy change-event evidence.

This distinction must be preserved even while implementing richer snapshot diffs.

## D5. Pinpoint candidate causes without inventing certainty

Suppose a route disappeared after an ACL modification.

The system should determine whether:

- The ACL actually applies to the traffic.
- The relevant interface and VRF match.
- The change was applied to running configuration.
- The relevant observed failure occurred after the change.
- There are competing possible causes.
- The evidence demonstrates causation or only correlation.

Do not call every configuration difference a root cause.

## D6. Acceptance requirements

Test:

- Same-device snapshot comparison.
- Different-device mismatch prevention.
- Saved versus running distinction.
- Historical running-to-running transition.
- Multiple configuration revisions.
- Relevant versus unrelated diffs.
- Approximate incident time windows.
- Verified change-event correlation.
- Missing history.
- Contradictory historical records.
- Vendor-aware interface/protocol changes.

---

# PART E — Automatic Post-Answer Evidence Investigation

## Problem E: Gemini prematurely chooses answer instead of investigating further

This is a major architectural change I want.

Currently, Gemini 3.5 can select:

- `answer`
- `need_more_evidence`

However, it repeatedly selects `answer` even when material requested information is missing and an authorized source could provide it.

**I do not want the investigation to stop solely because Gemini thinks its first answer is sufficient.**

I want an automatic post-draft evidence investigation cycle.

This should behave more like an engineering agent that checks its own preliminary findings, looks for missing context, retrieves additional evidence when justified, and then produces a stronger final answer.

## E1. Redefine the first Gemini answer as an internal draft

For complex investigations, the first Gemini 3.5 response should ordinarily be treated as:

`DRAFT_INTERPRETATION`

not immediately:

`FINAL_ANSWER`

This draft contains:

- Proposed technical explanation.
- Covered user outcomes.
- Referenced supporting evidence.
- Remaining uncertainty.
- Relevant unresolved dependencies.
- Potentially unsupported claims.

The user should not receive an overconfident preliminary explanation as a certified final result.

## E2. Run an automatic post-draft adequacy check

After the first draft, the workflow should automatically assess:

- Have all original requested outcomes been addressed?
- Were applicable broad-investigation source families covered?
- Are important source references still unread?
- Is there a material missing operational, historical or incident record?
- Does the explanation contradict authoritative typed relationships?
- Are claimed numerical values supported by measurements?
- Are claimed historical transitions supported by appropriate evidence?
- Is the remaining uncertainty honestly described?
- Could another authorized reader materially improve the conclusion?

This check must occur even if Gemini returned `answer`.

The model's choice must not be the sole determinant of investigation completion.

Reuse the existing evidence ledger, receipts, source classifications, outcome contracts and LangGraph.

## E3. Automatically pursue justified missing evidence

When the post-draft check identifies a grounded, material missing dependency with an available authorized reader, the system should:

1. Identify the missing evidence requirement.
2. Resolve the reader through the existing registry.
3. Validate the source and parameters.
4. Check source permissions and scope.
5. Execute the supplemental query.
6. Add the returned evidence to the existing investigation state.
7. Ask Gemini 3.5 to revise its interpretation.
8. Run the adequacy check again.

This should happen automatically within the approved investigation, without requiring the user to manually rephrase the question.

Do not automatically query irrelevant sources when no meaningful information gap exists.

## E4. Stop using Gemini's answer/need_more choice as the only control

Retain compatibility with the existing typed model contract if practical.

Gemini may still explicitly request more evidence.

But the graph must also support:

`draft answer → independent adequacy assessment → necessary authorized additional read → revised answer`

A server-driven additional read must be traceable as server-driven, not falsely described as Gemini independently selecting `need_more_evidence`.

The distinction matters for evaluation but should not prevent the system from becoming a better investigator.

## E5. Preserve useful draft answers

Do not discard correct explanations simply because some unrelated optional evidence remains missing.

Maintain the valid portions of the interpretation.

Additional evidence should update or qualify the explanation when necessary.

Do not blindly concatenate repeated model answers.

Do not replace a correct explanation with a raw source dump.

## E6. Define safe stopping conditions

An investigation may finish when:

- Requested outcomes are supported adequately; or
- Remaining limitations are explicitly and correctly explained; or
- No further relevant authorized evidence is obtainable; or
- The bounded investigation budget is exhausted.

If a critical question remains unresolved, say so.

Do not claim success merely because the final iteration produced valid JSON.

Do not loop indefinitely.

Use a bounded number of investigation and reasoning rounds, with budgets adjusted under Part G.

## E7. Make the investigation automatic but evidence-driven

The adequacy gate must not simply call another LLM that says "check again."

Use actual source receipts, typed relationships, original outcomes and available authorized readers.

Where a gap requires semantic interpretation and cannot be determined reliably, preserve uncertainty instead of inventing a deterministic conclusion.

The system should not automatically collect arbitrary data merely because the model's draft sounds uncertain.

## E8. Acceptance requirements

Demonstrate a real complex request in which:

1. Gemini initially produces a draft.
2. The draft omits a materially required answer.
3. The application recognizes a grounded missing dependency.
4. An authorized supplemental reader executes.
5. Gemini receives the new evidence.
6. The final answer improves and addresses the original requirement.

Also test:

- No additional reads needed.
- No additional reader available.
- Source prohibited.
- Query returns zero results.
- Multiple pending dependencies.
- Duplicate-read prevention.
- Correct early finalization.
- Bounded stopping.
- Preserved source provenance.

Differentiate genuine Gemini-requested refinement from server-driven refinement.

The system's end-to-end adequacy matters most, but reported MN4 metrics must identify which behavior actually occurred.

---

# PART F — Network Evidence Classes and Claim–Evidence Compatibility

## Problem F: Gemini overstates what a source proves

I want a structured evidence authority framework.

However, evidence authority should be evaluated relative to the type of claim being made.

The system should not blindly assume that one globally higher-ranked source proves every statement.

Implement two complementary mechanisms:

1. **Network Evidence Classes**
2. **Claim–Evidence Compatibility Matrix**

## F1. Canonical Network Evidence Classes

Use the following proposed evidence model, adapting implementation names only when necessary for compatibility with existing source contracts.

```python
class EvidenceClass(str, Enum):
    OPERATIONAL_STATE = "operational_state"
    EVENT_RECORD = "event_record"
    RUNNING_CONFIGURATION = "running_configuration"
    SAVED_CONFIGURATION = "saved_configuration"
    INVENTORY_TOPOLOGY = "inventory_topology"
    DERIVED_ANALYSIS = "derived_analysis"
    SIMULATED_SCENARIO = "simulated_scenario"
```

The intended troubleshooting precedence is:

### P1 — Operational State Evidence

Examples:

- Actual interface status.
- OSPF neighbor state.
- BGP session state.
- Measured counters.
- Measured telemetry.

Primarily supports claims about observed operational behavior at the recorded time and scope.

### P1 — Event and Incident Evidence

Examples:

- Syslogs.
- Verified incident reports.
- SNMP traps.
- Change-event records.
- Alert history.

Primarily supports claims about recorded events, incident timelines and documented changes.

An unverified syslog and a corroborated incident record must not automatically receive identical evidential authority.

### P2 — Running Configuration Evidence

Examples:

- Current running configuration.
- Active device configuration captured from the registered source.

Supports claims about the device's reported configuration at capture time.

Does not by itself prove physical operational health.

### P3 — Historical or Saved Configuration Evidence

Examples:

- Configuration backups.
- Startup configuration.
- Archived snapshots.

Supports claims about stored configurations and differences between artifacts.

Does not automatically prove historical running state.

### P4 — Inventory and Topology Evidence

Examples:

- SQLite inventory.
- NetBox.
- Registered device/interface records.
- Documented topology.

Supports device identity, recorded ownership, documented connections and management relationships.

Does not automatically prove current operational reachability.

### P5 — Derived or Analytical Evidence

Examples:

- Correlations.
- Anomaly scores.
- Computed metrics.
- Inferred root causes.

Supports conclusions only to the extent that the underlying inputs and analytical assumptions justify them.

### P6 — Simulated or Hypothetical Evidence

Examples:

- Simulated forwarding.
- Digital twins.
- Hypothetical link failures.
- Predicted impact.

Supports statements about modeled behavior under its declared assumptions.

Does not automatically establish actual observed operational behavior.

## F2. Keep retrieval status separate from evidence class

These must not become evidence classes:

- Not queried.
- Unavailable.
- Query failed.
- Queried with zero results.
- Partially retrieved.
- Source prohibited.

A failed query is not a low-authority event record.

It is a retrieval-status outcome.

## F3. Carry source-derived evidence metadata

Where available, evidence artifacts should retain:

```json
{
  "artifact_id": "R1-IFACE-001",
  "evidence_class": "operational_state",
  "source": "interface_state",
  "device": "R1",
  "captured_at": "2026-10-27T09:00:00+08:00",
  "observation": {
    "interface": "GigabitEthernet0/1",
    "operational_status": "down"
  },
  "supports_claims": [
    "interface_operational_status_at_capture"
  ],
  "does_not_establish": [
    "historical_status_transition",
    "root_cause_of_failure",
    "permanent_interface_failure"
  ]
}
```

This is a conceptual target representation.

Do not force every existing reader to fabricate fields it does not possess.

Where source provenance is unknown, mark it unknown.

Do not mutate raw source records merely to conform to a new schema.

A normalized evidence envelope may reference the original immutable source payload.

## F4. Claim-dependent evidence authority

For every material technical claim, evaluate the evidence using:

- Authority.
- Directness.
- Freshness.
- Coverage.
- Provenance.
- Verification status.
- Device/interface/time scope.
- Relevant source limitations.

A P1 record about one interface does not automatically override a configuration record about another interface.

A direct running-configuration observation is more authoritative for the claim "this command is configured" than a generic incident summary.

A directly measured operational state is more authoritative for "this interface was operationally down at capture time" than the inventory.

Do not collapse all evidence into a single numerical credibility score.

## F5. Claim–Evidence Compatibility Matrix

Implement a source-aware compatibility mechanism for at least the following claim categories.

| Claim | Appropriate supporting evidence |
|---|---|
| Interface operationally up/down | Relevant operational-status observation |
| Interface administratively enabled/disabled | Applicable configuration or authoritative administrative-state observation |
| OSPF adjacency established | Relevant OSPF neighbor-state evidence |
| BGP session established | Relevant BGP session-state evidence |
| Device/interface/address ownership | Relevant validated inventory and/or source-owned interface records |
| Configuration contains a command | Actual relevant configuration |
| Configuration changed at a time | Historical running-state comparison or trustworthy change-event evidence |
| Link currently operational | Actual relevant operational observation |
| Incident occurred | Appropriate event/incident evidence |
| No incident occurred | Sufficient authoritative scoped coverage, often difficult to establish conclusively |
| Measured packet loss percentage | Relevant measured data and justified calculation |
| Simulated path failure | Actual modeled/simulated forwarding evidence |
| Root cause | Correlated relevant evidence supporting the causal mechanism |

The matrix should be general enough to work across different network scenarios.

Do not implement one special-case rule for each benchmark sentence.

## F6. Distinguish contradictions from complementary facts

Example:

Inventory:

`R1 Gi0/1 → R2`

Configuration:

`no shutdown`

Operational state:

`down/down`

Correct interpretation:

- Expected adjacency to R2.
- Administratively enabled.
- Operationally down.

These records are complementary, not necessarily contradictory.

An explanation claiming that `no shutdown` guarantees operationally up must be identified as unsupported.

## F7. Validate important claims before final release

The post-draft adequacy phase from Part E should also check source-groundable technical assertions.

Prioritize:

- Device/interface ownership.
- Numerical measurements.
- Temporal claims.
- Current operational claims.
- Protocol-state claims.
- Simulated versus measured behavior.
- Inventory/planned versus observed connectivity.
- Incident/event assertions.

Where structured facts definitively contradict a draft claim, do not simply accept the claim because Gemini marked it `supported`.

When possible, return the exact source conflict to the existing reasoner for correction during the bounded investigation loop.

Preserve a correct original explanation.

Do not re-enable the prior brittle wording-based semantic verifier.

Do not silently replace the answer with source dumps.

## F8. Avoid pretending to verify unrestricted natural language

Some causal statements cannot be mechanically checked.

In such cases:

- Preserve the statement's evidence references.
- State that the claim could not be independently verified.
- Avoid claiming that a structured citation proves every part of the sentence.
- Allow qualified reasoning rather than making unsupported absolute assertions.

The claim compatibility mechanism should provide strong guarantees only for genuinely source-checkable relationships.

## F9. Acceptance requirements

Test:

- `no shutdown` plus operational down.
- A route existing without proof of protocol health.
- Wrong device/interface ownership.
- Measured versus modeled ECMP outcomes.
- Correct actual measured loss.
- Saved/current timestamp comparisons.
- Verified historical changes.
- Planned topology versus live observations.
- Unread logs versus verified absence of matching events.
- Genuine unresolved uncertainty.

Include positive tests that ensure correct differently worded explanations are not rejected.

---

# PART G — Relax Timeouts and Prioritize Reliable Answers

## Problem G: Planning timeout and excessive speed constraints

I am willing to allow the system more time to investigate and reason.

I am currently working with free-tier cloud models.

I understand the provider may sometimes be slow or unavailable.

**I prefer a slower, comprehensive and technically correct result over a fast but incomplete or incorrect answer.**

Therefore, review and revise the current timeout and execution-budget design.

## G1. Inspect existing timing constraints

Current reported limits include:

- Approximately 35-second planning-stage reservation.
- 120-second overall request deadline.
- Three total cloud role calls.
- One supplementary reader round.
- Eight total reader calls.

These may be too restrictive for the expanded investigation strategy.

Do not preserve them merely because they were the earlier experimental defaults.

## G2. Introduce configurable investigation budgets

Provide explicit configuration for:

- Planner stage timeout.
- Initial reader execution budget.
- Reasoner timeout.
- Post-draft adequacy checking.
- Supplementary retrieval budget.
- Maximum investigation rounds.
- Maximum reader operations.
- Overall user-request deadline.

The budgets should be compatible with the gateway, HTTP clients, frontend and test environment.

Do not increase backend timeouts while leaving frontend/proxy timeouts so short that users still receive premature failures.

For an initial experimental profile, consider a multi-minute total deadline, such as 300–480 seconds, and a larger planning reservation than 35 seconds.

Determine precise values from actual endpoint behavior, API capabilities and frontend constraints rather than blindly hardcoding these examples.

## G3. Increase reader capacity when broad source coverage requires it

An eight-call ceiling may prevent a comprehensive investigation across multiple devices and source families.

Allow a configurable, bounded higher reader limit for approved comprehensive investigations.

Consider an initial experimental ceiling around 24 reader operations, subject to actual environment and source characteristics.

Narrow tasks should not automatically consume the larger budget.

Use query deduplication, caching within the request and progressive filtering.

## G4. Allow a bounded automatic continuation cycle

If automatic evidence refinement requires additional reasoning calls beyond the previous three-call ceiling, support a separately consented experimental budget.

For example:

- One planner call.
- Initial reasoner call.
- One or more bounded updated reasoner calls after material new evidence.

An initial ceiling of up to five or six actual cloud dispatches per approved request may be considered if supported by the real quota ledger and exact consent contract.

Do not increase cloud calls unnecessarily.

Do not add a second planning LLM merely to spend available quota.

Every provider attempt, including a retry, must count toward the applicable budget.

## G5. Handle free-tier availability responsibly

Retain:

- Persistent quota admission.
- Project-level limits.
- Per-model limits.
- Rolling-day accounting.
- Request ownership and consent.
- Actual provider-failure receipts.

Investigate transient HTTP 503 behavior and timeouts.

Use a bounded retry/backoff policy only when technically justified and enough deadline/quota budget remains.

Longer timeouts may help slow successful inference but do not inherently fix provider-unavailable responses.

Do not retry indefinitely.

Do not activate billing.

Do not secretly change models.

Do not bypass free-tier limits.

## G6. Preserve answer quality as the primary metric

Record:

- Complete-task correctness.
- Technical causal correctness.
- Evidence coverage.
- Missing outcomes.
- Unsupported claims.
- Additional reads required.
- Investigation rounds.
- Provider failures.
- Latency.
- Quota consumption.

Do not count faster responses as an improvement when they are less complete or less accurate.

Do not count slow responses as superior merely because they used more evidence.

---

# Integrated Architecture — Required Target Workflow

Implement the improvements using the existing authenticated gateway, provider-neutral roles, authorized reader registry and LangGraph.

The intended complex-investigation workflow is:

```text
USER QUESTION
    |
    v
AUTHENTICATION / SCOPE / EXACT CONSENT
    |
    v
INTENT ROUTING
    |
    +--> Ordinary request
    |        |
    |        v
    |     Existing local workflow
    |
    +--> Approved complex investigation
             |
             v
     PRESERVE ORIGINAL REQUESTED OUTCOMES
             |
             v
     BUILD INVENTORY / TOPOLOGY CONTEXT
             |
             v
     GEMINI 3.1 — INVESTIGATION PLANNING
             |
             v
     CLASSIFY BREADTH AND SOURCE COVERAGE
             |
             v
     RECONCILE PLAN WITH AUTHORIZED READERS
             |
             v
     INITIAL COMPREHENSIVE / TARGETED READS
             |
             v
     READER RECEIPTS + RAW SOURCE RECORDS
             |
             v
     NETWORK EVIDENCE CLASSIFICATION
             |
             v
     SOURCE / TOPOLOGY / SNAPSHOT CORRELATION
             |
             v
     GEMINI 3.5 — DRAFT INTERPRETATION
             |
             v
     AUTOMATIC POST-DRAFT ADEQUACY CHECK
             |
             +--> Material evidence missing?
             |           |
             |          YES
             |           |
             |           v
             |    AUTHORIZED ADDITIONAL READ
             |           |
             |           v
             |    UPDATE EVIDENCE
             |           |
             |           v
             |    GEMINI 3.5 REINTERPRETATION
             |           |
             |           +--> Recheck adequacy
             |
             +--> No material actionable gap
                         |
                         v
              CLAIM–EVIDENCE COMPATIBILITY
                         |
                         +--> Correctable source conflict
                         |        |
                         |        v
                         |   Bounded correction
                         |   using actual evidence
                         |
                         v
                  FINAL ANSWER
                         |
                         v
              USER + SOURCE REFERENCES
              + HONEST LIMITATIONS
```

The adequacy check should run after each draft or revised interpretation, within the approved budget.

The claim-grounding check may be integrated into this adequacy step; do not create redundant independent verification pipelines.

Do not create a second autonomous agent system.

The existing LangGraph should remain the single orchestration graph.

---

# End-to-End Reference Example

Use the following concept to guide implementation, but do not hardcode it.

## Original question

"Investigate why R1 cannot communicate with R3. Check all relevant available sources, identify the fault, compare relevant configuration history, and tell me whether maintenance is involved."

## Initial inventory

R1 → R2 → R3.

R1 GigabitEthernet0/1 is documented as connected to R2.

## Source records

Operational state:

`R1 Gi0/1: down/down`

Running configuration:

`R1 Gi0/1: no shutdown`

Saved configuration:

A historical saved artifact contains a different interface-related setting.

Incident records:

A change/event reference exists.

Topology:

The R1–R2 connection is documented.

## Intended investigation

1. Classify the question as broad.
2. Enumerate all relevant authorized reader families.
3. Retrieve operational, configuration, topology and relevant incident/history evidence.
4. Build a device/interface ownership map.
5. Distinguish current operational state from intended configuration and planned adjacency.
6. Compare compatible historical snapshots.
7. Identify relevant configuration differences.
8. Correlate event records and incident windows.
9. Prepare a technical explanation.
10. Automatically check whether maintenance purpose, causal mechanism or other requested information remains unresolved.
11. Retrieve additional authorized evidence when materially necessary.
12. Verify claim–evidence compatibility.
13. Produce a correct, qualified final answer.

The correct outcome may be:

"The interface is observed operationally down while administratively enabled. The inventory documents an expected connection to R2. These facts identify the affected interface but do not by themselves establish whether the cause is physical, transceiver-related, remote-side, maintenance-related or another mechanism."

Further authorized event/operational evidence may resolve that uncertainty.

Do not invent a definitive root cause when evidence remains insufficient.

---

# Implementation Strategy

## Stage 0 — Baseline inspection and preservation

Inspect the real current code and dependencies.

Snapshot existing Git HEAD/index, ordinary SQLite tables, immutable V9 release, credentials, historical traces and relevant protected editor state.

Do not reset unrelated changes.

Document which components are already implemented.

Avoid parallel contracts and duplicated state.

## Stage 1 — Breadth-aware planning and completeness-first retrieval

Implement Parts A and B.

Demonstrate comprehensive authorized source coverage on broad prompts.

Demonstrate narrow and explicit restricted cases.

## Stage 2 — Inventory-aware interpretation

Implement Part C.

Build/reuse the network context map and source-grounded entity ownership validation.

## Stage 3 — Historical snapshot investigation

Implement Part D.

Add reliable compatible-snapshot discovery, comparison and change correlation using existing readers and parsers.

## Stage 4 — Automatic post-draft investigation

Implement Part E within the existing LangGraph.

Verify the automatic missing-evidence continuation independently from Gemini's model-generated `need_more_evidence` choice.

## Stage 5 — Evidence authority and factual compatibility

Implement Part F.

Reuse existing provenance structures.

Do not rebuild the old semantic verifier.

## Stage 6 — Configurable time and query budgets

Implement Part G.

Ensure all relevant backend, provider and frontend timeouts are compatible.

Preserve quota and consent safeguards.

## Stage 7 — Integration and regression

Preserve earlier successful MN cases.

Run tests targeting each newly implemented mechanism.

Check both Floating AI and Ansible Studio.

---

# Required Evaluation Design

Do not use regression-test counts as evidence of improved intelligence.

Evaluate actual complete-task quality.

## Test categories

Create independently source-checkable synthetic cases covering:

1. Broad investigation requiring multiple reader families.
2. Narrow investigation requiring few readers.
3. Explicitly prohibited source.
4. Broad multi-device diagnosis.
5. Inventory ownership ambiguity.
6. Planned topology versus operational state.
7. Current/saved/historical configuration diffs.
8. Confirmed versus unconfirmed historical changes.
9. An event reference requiring a supplemental read.
10. A request whose initial evidence is already sufficient.
11. Operationally down interface despite `no shutdown`.
12. Route existence without proof of routing-protocol health.
13. Modeled path failure without measured packet-loss data.
14. Provider delay, timeout or availability failure.
15. No-read advisory instruction.

Ensure expected source facts and scoring criteria are frozen before live model inference.

## Required comparison

Compare:

- Existing corrected architecture.
- Enhanced completeness-first architecture.

Use the same synthetic questions and source revisions.

Where possible, compare identical model configurations.

Report planning differences separately from reasoning differences.

Preserve historical original scores.

Do not claim that different old and new cohorts demonstrate improvement.

## Quality measurements

Report:

- Fully correct and complete answers.
- Partially correct answers.
- Incorrect answers.
- Unsupported technical claims.
- Source coverage.
- Requested-outcome coverage.
- Correct device/interface attribution.
- Correct temporal interpretation.
- Correct root-cause explanations.
- Useful automatic supplementary reads.
- Unnecessary but authorized reads.
- Prohibited reads attempted or executed.
- Failed queries.
- Provider errors.
- Cloud calls and tokens.
- Total latency.

Treat unauthorized execution and untrue technical conclusions as separate serious problems.

An extra authorized relevant read should be an efficiency observation, not an automatic technical-correctness failure.

## Live automatic evidence refinement

At least one bounded live integration test should attempt to demonstrate the complete automatic post-draft investigation:

- Real Gemini planner.
- Actual authorized initial reader execution.
- Real Gemini reasoner draft.
- Automatic evidence adequacy check.
- Authorized additional reader execution.
- Updated evidence.
- Real Gemini revised explanation.
- Final source-grounded answer.

Record whether the continuation was Gemini-requested or server-driven.

Do not manufacture a live success from mocked inference.

If provider availability prevents the test, report the blocker and retain deterministic evidence separately.

## Preserve earlier successful behavior

Re-run the original successful MN-01/MN-02/MN-03 flows as regression references.

Also create independent variations testing the same architecture without copying benchmark answers.

The objective is to retain the successful intelligence of the original model-neutral system while extending its ability to investigate more complex situations.

---

# Explicit Non-Negotiable Requirements

- Maintain the existing model-neutral architecture.
- Preserve Gemini 3.1 planning and Gemini 3.5 reasoning roles unless separately authorized to change them.
- Retain ordinary local Qwen.
- Reuse existing LangGraph.
- Reuse registered readers.
- Reuse existing inventory and topology.
- Reuse existing source receipts.
- Preserve raw source evidence and timestamps.
- Prioritize complete authorized investigation.
- Automatically assess evidence adequacy after draft reasoning.
- Pursue justified missing evidence automatically.
- Validate important claims against appropriate source classes.
- Increase bounded time and retrieval budgets where required.
- Respect free-tier quotas.
- Preserve explicit source restrictions.
- Preserve read-only behavior.
- Preserve engineering-action boundaries.
- Do not make live configuration changes.
- Do not install new models.
- Do not activate billing.
- Do not activate Gemini 3.8.
- Do not make live OpenAI calls.
- Do not introduce arbitrary extra planning agents.
- Do not create a new inventory database.
- Do not fabricate missing evidence.
- Do not hardcode benchmark diagnoses.
- Do not silently modify frozen results.
- Do not rewrite correct Gemini explanations unnecessarily.
- Do not stage, commit or push Git changes.
- Do not deploy or publish.
- Do not reset the existing dirty worktree.

New experimental flags, role-call budgets, graph contracts and consent manifest versions must be explicitly recorded and tested.

A configuration change that expands cloud calls, timeout exposure or readable source scope must require appropriate fresh exact consent.

Use disposable authorized synthetic development environments.

Stop disposable test services at completion.

---

# Documentation and Handover

Create:

`docs/PHASE_G_COMPLETENESS_FIRST_EVIDENCE_INVESTIGATION.md`

Update the model-neutral continuation checkpoint and relevant architecture documentation.

The report must contain:

1. Original architectural limitations A–G.
2. Changes made for each requested solution.
3. Existing components reused.
4. Exact code modules modified.
5. New investigation state transitions.
6. Broad-reader coverage policy.
7. Relaxed optional-reader handling.
8. Inventory/topology model.
9. Historical snapshot comparison implementation.
10. Automatic post-draft investigation.
11. Evidence class definitions.
12. Claim–evidence compatibility mechanism.
13. Timeout and quota configurations.
14. Deterministic regressions.
15. End-to-end live results.
16. Original MN success preservation.
17. Correctness and completeness results.
18. Remaining errors and unsupported claims.
19. Provider limitations.
20. Model and tool latency.
21. Runtime complexity and context overhead.
22. Source and security preservation.
23. Recommended next steps.

Provide a trace for at least one representative network question showing every meaningful stage:

`user question → intent → planner → reader plan → authorized sources → actual records → network context → first interpretation → adequacy check → additional evidence → revised interpretation → claim compatibility → final answer`

Do not report a stage as successfully executed unless it actually occurred.

Clearly distinguish:

- Fully implemented behavior.
- Deterministically tested behavior.
- Live-model-verified behavior.
- Blocked or unverified behavior.

Do not claim G4/G5/G6 qualification unless the authoritative acceptance requirements have actually been met.

## Final instruction

**Implement the seven architectural improvements I described, emphasizing comprehensive evidence gathering, automatic follow-up investigation, inventory-based understanding, historical comparison and claim-dependent evidence authority.**

Do not optimize the system primarily for minimum reader count or shortest possible latency.

Preserve the successful model-neutral architecture, but improve its ability to behave like a network engineer who checks relevant sources, verifies hypotheses, resolves uncertainty and develops a correct technical explanation.

Where my requested behavior conflicts with a previous soft planning optimization, prefer the new completeness-first behavior.

Where it conflicts with authentication, source authorization, explicit user restrictions, free-tier quotas, privacy or read-only boundaries, preserve the hard boundary and report the limitation.

Complete the implementation, perform bounded end-to-end validation, document genuine results and stop at this milestone.

The ultimate measure of success is:

**Can the system investigate a complex network question more comprehensively, produce a more correct and complete explanation, and avoid unsupported conclusions while remaining authorized and reliable?**