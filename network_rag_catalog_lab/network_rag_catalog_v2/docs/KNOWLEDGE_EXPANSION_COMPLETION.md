# Knowledge Expansion: Staged Completion and Review Notes

Subsequent status: the packs have now been activated for generation-only terminal
testing. See [activation results](KNOWLEDGE_ACTIVATION_RESULTS.md). The staged-only
statements below describe the earlier preparation milestone, before approval.
The [coverage audit](REQUESTED_OPERATION_COVERAGE.md) records remaining vendor gaps.

Date: 2026-09-29
Scope: Phase 0, A, B1/B2, C, D1 and D2 of
`Implementation_Plan/KNOWLEDGE_EXPANSION_REVIEW_AND_PLAN.md`.
There is no Phase E in that plan. Its taxonomy section E describes ACL, delivered
under D1; taxonomy section F describes QoS, delivered under D2.

## Status and Authority

The code and reviewable packs are implemented for the bounded profiles below.
This is NOT a live expansion rollout or device certification.

- User instruction retained: prepare validated packs; leave the live catalog alone.
- SQLite remains the workspace authoring authority.
- The original 12 operations and 36 vendor bindings remain the live baseline.
- Isolated rehearsal adds 32 operations and 42 bindings: 44 operations, 78 bindings
  and nine categories in the disposable candidate release.
- Existing public pipeline, schema loader, renderer and management entry points
  remain; no alternate database, schema compiler, GUI or execution engine was added.
- Pack records, templates and demonstration inventory live under
  `knowledge_packs/`, not the live `data/` tree.
- No new live release, index or inventory was activated.

## Phase Disposition

| Phase | Implemented candidate scope |
| --- | --- |
| 0 | Field-scoped primitive/structured extraction, optional preservation, required safety handlers and normalized alias collision checks; see the historical Phase 0 note |
| A | VLAN state mutation and numeric-identity rename with inventory/collision checks; retain existing create/delete |
| B1 | Physical description/admin state, access/trunk setup, additive/replacement allowed lists and native VLAN |
| B2 | Narrow Cisco loopback creation and routed LACP aggregation with explicit member facts |
| C | Default/floating routes and seven separate OSPF operations; retain legacy static/OSPF/BGP/IS-IS/IP contracts |
| D1 | Named extended IPv4 ACL creation, exact add/replace/delete ACE, and routed-interface attachment |
| D2 | DSCP classifiers, exact match-list replacement, bandwidth policy/class scheduling, dedicated shaping/policing and policy attachment |

All 38 proposed names have a disposition: 32 new canonical operations, five
existing operations reused, and `assign_vlan_to_access_port` remains a discovery
alias of `configure_access_port`, not a duplicate executable record.

## Support Matrix

Every new binding also requires the corresponding code-reviewed
`capabilities.validated_policies` entry and source-referenced local facts.
Matching a vendor string alone is insufficient.

| Profile | Candidate new-operation bindings |
| --- | --- |
| Cisco Catalyst 9300, IOS XE 17.9 | All 32 new operations, within the restrictions below |
| Huawei CE6800, VRP V200R024C10 | Physical interface description/admin state; additive VLAN membership and native VLAN on an existing trunk |
| Juniper EX4300, Junos 23.4 ELS | The same four interface operations, plus default/floating IPv4 routes |
| Other combinations | No fallback binding; unsupported until separately reviewed |

These are documentation-informed candidate profiles, not proof that every model,
license, patch release or hardware variant accepts the generated commands.
Huawei's exact-release command coverage and all profiles' physical-device behavior
still need lab acceptance before live publication. Existing legacy bindings are
preserved, not newly certified by these additions.
Command references and evidence limits are in
[`knowledge_packs/SOURCES.md`](../knowledge_packs/SOURCES.md).

## Canonical Decisions

- Keep existing IDs: `configure_interface_ip`, `configure_static_route`,
  `remove_static_route`, `create_vlan` and `delete_vlan`.
- Interface owns switchport behavior. Shared types stay in the parameter registry;
  required flags, bounds, item shapes and enums remain operation rules.
- Keep `address`/`prefix_length` and boolean `admin_up`. Do not store competing
  netmask/prefix authorities or reuse OSPF object lists as LAG member lists.
- `modify_vlan` currently changes only state, requiring `vlan_status`.
  An empty modification is never executable. Rename uses a separate operation.
- Trunk addition preserves existing membership; replacement is explicitly named.
  Initial replacement requires the recorded or explicit native VLAN to remain.
- New routing operations reject noncanonical IPv4 CIDRs and do not reinterpret
  `metric` as route preference. Legacy preference parsing is preserved; its old
  metric alias is a known compatibility limitation, not silently migrated.
- `enable_ospf_process` requires an explicit router ID to produce meaningful
  persistent configuration. Existing broad OSPF aliases remain untouched.
- `create_ospf_area` is restricted to a new non-backbone stub area.
- `advertise_network` selects addressed interfaces for OSPF; it is not arbitrary
  route injection. Redistribution accepts only connected/static sources with a
  confirmed bounded default-deny route policy, explicit metric and metric type.
- `create_acl` requires a description and creates a persistent remark at sequence
  1; ACE IDs start at 10. Attaching a remark-only ACL is rejected.
- ACL replacement requires the entire rule. Missing prefixes/actions never mean
  permit-any. Transport ports require TCP/UDP; deletion never widens to an ACL.
- QoS uses DSCP-only match-any classifiers and absolute bandwidth policies.
  `configure_scheduler` means a known policy/class bandwidth treatment, not a
  fictional portable standalone scheduler. Inputs are integer bps/bytes; bandwidth
  must be a whole number of kbps and is converted deterministically.
- DSCP replacement requires `previous_dscp_values`, offered from inventory and
  cross-checked before generating the exact removal command.
- Shaping creates a dedicated egress class-default policy; policing creates a
  dedicated ingress policy with explicit burst and excess-drop action. Both need
  unused policy names and must not replace another interface attachment.

## Context and Safety

The planned fixture is `knowledge_packs/fixtures/devices.json`: SW1/SW2/SW3.
It is explicitly demonstration data, not discovered state. Existing R1/R2/R3
records are not relabelled as switching/security/QoS capable.

Routing/resource operations require `resources.complete=true`, a source reference,
and appropriate typed collections. Routing additionally requires an explicit
default routing context, including relevant interface facts.

| Facts | Used for |
| --- | --- |
| `vlans`, interface mode/native/allowed list | Identity, rename collisions and trunk checks |
| Interface addresses, enabled state, routing context | Direct next-hop evidence and OSPF selectors |
| `routes`, explicit primary preference | Floating-route comparison; no backup claim without a primary |
| `ospf_processes`, areas and interface membership | Existing process/area and membership checks |
| `route_policies` with bounded prefixes/source/default deny | Limited redistribution |
| `acls`, ACE IDs/kinds, interface ACL bindings | Exact mutations and non-overwriting attachments |
| `classifiers`, `qos_policies`, attachment facts | Explicit policy/class relationships |
| Queue count, speed, supported direction | Queue/rate/capacity validation |
| LAG capability, owner, address/service emptiness, MTU/speed/duplex | Safe bounded member selection |

Missing/invalid inputs still use one-field questions, typed custom answers and
source-backed choices. Suggestions are not automatic intent defaults. Invalid
values are revalidated; partial or conflicting requests produce no configurations.
Malformed resource snapshots fail closed instead of yielding configuration.

Typed composite keys distinguish (ACL name, rule ID), (interface, direction) and
policy identities. Different ACLs using rule 10 do not falsely conflict. Legacy
resource checks remain supported, including interactions with new route operations.
Conflicts use the existing review/ordering workflow, not an execution planner.

Same-request create/use chains are deliberately unsupported: creating NEW_ACL in
one task does not make it an existing confirmed ACL for another task. Update the
reviewed planned context explicitly before a later request. No device state is
changed by successful generation.

## Rehearsal and Test Commands

Run from `network_rag_catalog_lab/network_rag_catalog_v2` with the existing venv:

```powershell
& ../../.venv/Scripts/python.exe -m app.knowledge.pack_review --check-cases
& ../../.venv/Scripts/python.exe -m app.knowledge.pack_review --packs vlan interface --check-cases
& ../../.venv/Scripts/python.exe -m unittest discover -s tests -p test_expansion_packs.py -q
& ../../.venv/Scripts/python.exe -m unittest discover -s tests -q
```

The rehearsal reads the selected authority, copies it into a disposable project,
uses existing service dry-run/apply and SQLite migration, then publishes OFFLINE
inside that project. It is deleted afterward. There is intentionally no live-apply
flag. `--check-cases` validates/renders all 42 added bindings with planned fixtures.
It does not invoke the model, execute devices or certify vendor CLI.
Run rehearsal and compatibility tests serially: taking the source snapshot briefly
holds the authoring lock, and source-mode tests intentionally reject that lock.

Each domain's `cases.json` provides a complete parameter payload and reproducible
labelled prompt. New operations are NOT available through the live `main.py`
until a separately approved apply/publication. Existing terminal clarification
continues to work for the current live operations.

Examples covered by the staged tests:

- Default route with a recorded directly connected next hop: validated.
- Floating route with preference no higher than the primary: clarification.
- ACL rule missing source prefix: ask for that field; no permit-any assumption.
- ACL rule ID already present: require explicit replacement instead of addition.
- Policing burst `-1`, `10Mbps` as a rate, or wrong direction: rejected.
- Existing DSCP list differs from supplied removal values: ask for correction.
- Wrong model/profile, absent policy, unknown port or unsupported LAG facts:
  blocked; no guessed syntax or resource creation.

## Files and Verification

- `app/knowledge/pack_review.py`: reviewed hashes, safe assets, no-op/conflict diff,
  existing management envelopes and disposable rehearsal.
- `app/devices/{operation_policies,resource_policies,resource_options}.py`:
  bounded profile/context checks and suggestions.
- `app/knowledge/resource_keys.py`, `app/pipeline.py`: composite identity and
  retained whole-request rendering gate.
- `app/parameters/expansion_rules.py`, `parameter_extractor.py`: opt-in domain
  rules and scoped metric/preference correction.
- `rule_registry.py`, `models.py`, `publication.py`: allowlisted deterministic
  derived template inputs and publication-time policy/key validation.
- `knowledge_packs/<domain>/`: service changes, contracts, context, template
  hashes, candidate support declarations and prompt cases.
- `tests/test_vlan_interface_packs.py`, `tests/test_expansion_packs.py`:
  profiles, all new bindings, extraction, clarification, resource conflicts,
  unsupported inputs, idempotence and forward retirement.

Latest final verification results are recorded in the companion
`KNOWLEDGE_EXPANSION_VERIFICATION.md` after the final run.

## Remaining Acceptance and Rollback

1. Review these narrowed contracts, especially stub-only areas, exact ACL
   replacement, QoS units/relationships and unsupported vendor combinations.
2. Test CLI syntax and behavior on the exact model/NOS/license profiles. Include
   transient ACL replacement and DSCP-removal effects; golden text is insufficient.
3. Benchmark the actual weak model and expanded retrieval index on varied prose,
   shared/mixed targets, ambiguity and latency. Current tests use deterministic
   extraction and mocked model failure; no strong-model equivalence is claimed.
4. Confirm inventory fact ownership/freshness and explicit empty-vs-unknown
   collections. Completeness is a source assertion, not discovery.
5. After approval, export SQLite and capture active release/context/assets; install
   reviewed assets, prepare a revision-checked batch, dry-run/apply, then perform
   indexed publication and smoke checks. Never import a partial pack as a full
   catalog or edit managed JSON as a live authority.

Until activation, removing the staged packs requires no live database rollback.
After a future activation, use forward compensation: retire unsafe new operations
or version corrected contracts and republish. Do not switch an old active pointer
back or erase published identities. The tests rehearse retirement and verify
failed/stale publication leaves the current release active.

No GUI, Ansible, execution, monitoring, topology inference, IPv6/VRF expansion or
general business-intent solver is included. Production activation and broader
vendor coverage remain explicit follow-up work, not hidden completion claims.
