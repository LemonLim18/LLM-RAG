# Phase C engineering evaluation — 2026-10-17

This is a bounded development-simulation milestone, not physical-device certification or general network emulation. Stable specifications are in `phase_c_cases.json`; timestamped raw runs, original failures, screenshots and JUnit reports remain ignored under `tmp/phase-c/`. Credentials, SQLite binaries and private conversations are excluded from source control.

## Milestone sequence and reuse

C1 was verified before C2; C2 API/browser acceptance was completed before C3. Existing inventory_snapshot, NetworkReader, JsonObservations, DatabaseManager projections, V9 inventory and published planning/finalization, shared authorization and the B3 LangGraph were extended. No second SoT, RAG, renderer, agent framework or database migration was introduced. The 52-file staged post-B3 checkpoint remains unchanged; Phase C is unstaged/untracked.

C1 adds six versioned central definitions, an explicitly server-enabled manager and authenticated developer controls. Current running configuration, captured history, interface events, planned/observed topology, distinct metrics, scoped probes, availability and dependency edges share one scenario revision. JSON state persists across restart; ordinary database rows are never populated from scenarios. Production/external mode cannot fall back to development data. Explicit Reset adopts a bundled scenario revision; persisted edits are not silently upgraded.

C2 conversational correction and structured controls update the same owned V9 task/session. Device changes re-resolve scoped interface identity; rejected values are retained as V9 candidates and shown for correction. Operation changes reload schemas; stale scenario/review revisions and unsupported profiles block confirmation. The development fixture explicitly models the existing C9300/IOS-XE 17.9 physical_interface_v1 contract with planned capability facts. This is a test assumption, not certification of actual hardware. Native output and verified Ansible variants remain separate.

C3 extends the existing understand → resolve → authorize → retrieve → assess → verify → compose graph. Seven read capabilities, at most three rounds/eight tool calls, and existing owner-bound checkpointing remain. A typed hypothesis contains scope, supporting/contradicting record references, missing observations, qualification, dependency-deduplicated support and a useful next check. Deterministic IP-prefix and complete-table checks operate on fresh structured observations. Conflicting sources/revisions, partial state and missing decisive observations cannot certify a diagnosis. Current configuration comparison reuses the existing narrow literal fact reader; this is not a universal vendor parser. No probabilities or model-written measurements are invented.

## Matched scenario results

The same HTTP prompt was used for all six: “Investigate whether R1 can communicate with R2 and identify any issues.” Actual shared gateway, local semantic embeddings, authorized readers and LangGraph were used.

| Scenario (bundled revision 2) | Observed assessment | Outcome |
| --- | --- | --- |
| HEALTHY-001 | Successful scoped ICMP observation; mutually on-link prefixes; no invented failure | PASS |
| FAULT-IFDOWN-001 | Administrative/operational shutdown on the declared path; cause confirmed within simulation | PASS |
| FAULT-SUBNET-001 | Mutually off-link prefixes with failed direct-link test; cause confirmed within simulation | PASS |
| FAULT-ROUTE-001 | Complete source table lacks destination route; routing explanation strongly supported, broader causation unconfirmed | PASS |
| CONFLICT-001 | Current observers disagree; definitive diagnosis withheld | PASS |
| UNKNOWN-001 | Insufficient observations; candidate explanations and decisive next reads, no confirmed failure | PASS |

Primary live HTTP artifact: `http-C3-20261017-152511-f67a0f/results.json`. The staged B3 assessor was evaluated on identical returned records; it remained insufficient-for-confirmed-root-cause in all six because it required physical live evidence. This is a matched-data assessment comparison, not a latency comparison of two running applications. Network samples took 206–1,425 ms including HTTP, using seven tools/two rounds and zero conversational synthesis calls for the initial full investigations. Local nomic embeddings supplied semantic routing; exact diagnostics were calculated from verified records. Actual qwen2.5:1.5b arithmetic took 6,883 ms, returned 12, and used zero network tools. These samples do not establish universal model intelligence or performance.

Actual HTTP follow-ups passed: supporting evidence, other sources, routing alternative, preceding changes, most likely cause, next check, rejection of an unsupported user assertion that an interface recovered, refreshed diagnosis after a source revision change, explicit R2 scope and unrelated arithmetic. Actual browser acceptance additionally exercised healthy/shutdown/conflict/unknown observations, source disclosures and a persisted investigation after controlled backend restart. Studio uses the same authorized scenario evidence without automatic generation/edit/save.

## C2 browser/API evidence

The natural R2 → R1 correction retains exactly `Uplink`, rejects the old R2 interface, and offers R1's recorded interfaces. Explicitly selecting GigabitEthernet0/1, revalidating, confirming and opening creates an unsaved native document. BGP remote-AS clarification preserves the independent interface task. Replacing BGP with OSPF replaces its schema fields. Scenario revision changes disable stale confirmation until revalidation; Huawei UNKNOWN remains unsupported. Actual HTTP evaluation also checks shared-name interface ID rebinding and invalid predecessor parameters. No ordinary R1/R2 identities changed.

## Failures retained and corrected

- Named R2 network request misrouted to editing an unrelated README: proposal rejected; the graph now routes that scope to V9 without recognizing operations itself.
- Strict V9 field grammar dropped conversational description assignment: bounded wording normalization retains user values; V9 still extracts/validates. Invalid interface remains a rejected candidate.
- Missing development capability facts blocked the interface operation: explicit modeled planned facts now match the existing published profile; no V9 check was weakened.
- Reopened review did not initially flag scenario change: mount-time revision check now blocks confirmation.
- Developer Reset acted on active state instead of dropdown selection: corrected; failed browser evidence is preserved separately from rerun.
- Follow-up label “Latest request” was parsed as a user latest-only filter, truncating every reader to one row: internal label changed to “Follow-up”, investigation retrieval stays staged and structured state gets a bounded 10,000-character allowance.
- Conflict assessment correctly withheld diagnosis but initially omitted useful alternatives/checks: it now preserves agreed prefix facts, records state disagreements and offers decisive reads. Supporting evidence no longer counts a successful probe as support for shutdown.
- Current simulated configuration/history availability and timestamps needed explicit separation: current-only/history-only queries are scoped, disabled current sources remain unavailable, returned configuration is redacted, and disclosures label current simulated running versus historical capture.
- Early evaluator parameter dictionaries aliased later review changes: fixed by deep-copying captured responses/selection inputs. Those original artifacts are preserved with their limitation documented.
- Restricted-sandbox tests failed on temporary-directory access; authorized reruns passed. Harness import/field-name mistakes are classified separately from application faults.

## Focused verification and limits

The affected B2/B3/C1–C3 suite passed 68 tests plus five subtests. Later focused source-scope tests passed 30 tests; final competing-hypothesis cases passed six tests. These overlap. Including final handoff/intelligence checks, the deduplicated union is 89 backend test methods, counting the renamed missing-prefix case once. Six scenario assertions inside one test method are not six additional unit methods. TypeScript passed. Original failed XML/JSON remains retained; mocked semantic decisions are labeled separately from actual-model HTTP/browser runs.

No new dependencies/models were installed. OCR, uploads, exact-base Monaco proposals, Accept/Reject/Undo, explicit Save and V9 release authority are preserved. Existing focused B2/B3 regressions cover these boundaries; unrelated old generation/OCR suites were not repeated.

Remaining scope: arbitrary routed/ECMP/VRF/ACL forwarding, recursive next hops, congestion causation, complete OSPF/BGP state-machine simulation and general vendor CLI semantics are not certified. Protocol and policy scenarios require explicit reviewed data contracts and new permanent cases. The simulator is a versioned observation model, not a packet/protocol emulator. JSON persistence supports one application writer; multi-process writer arbitration is not claimed. Published Cisco CIDR static-route syntax remains a separate knowledge-quality gate; immutable templates/releases were not changed.

## Operation and rollback

Use the existing launcher on 5173/8000. Development authority requires server local-lab mode plus `COGNISHIELD_DEV_SIMULATION=1`; default remains disabled. Optional `COGNISHIELD_DEV_STATE` must resolve inside this workspace; default is `tmp/development-network/state.json`. Enable the flag in server configuration and restart, then use Development scenarios. UI, model instructions and uploads cannot enable it. Disable the flag/restart to return to ordinary readers without a data migration. Existing B1/legacy engine rollback removes advanced investigation orchestration while retaining reader/UI fixes; B2 also shares the C3 assessment code. Restore never replays pending device/proposal actions; it reauthorizes and reads current sources.

Next milestone is user-directed engineering-quality expansion: review this unstaged source package, add explicit protocol/policy/forwarding contracts and cases as needed, and separately review the known published static-route defect before authoring/publication. No deployment, autonomous operation or publication is authorized by this checkpoint.


Final handoff integration: acceptance/history now use the same authoritative inventory projection instead of direct ordinary-device SQL. Source revisions are checked even when a handoff is prepared after its source turn has already become stale. Old observation payloads are withheld, mode-off crossings are rejected, and shared scenario configuration remains available to authorized engineers while private ordinary snapshots retain ownership filtering. Actual browser review/open succeeded with simulated R1 ID 9101, a distinct Studio conversation and an unsent draft; SQLite confirms zero submitted engineering turns. The original Monaco buffer remained intact. Focused handoff/intelligence checks: 17 passed; final owner/source-revision reruns: two passed each (overlapping, not additive).
