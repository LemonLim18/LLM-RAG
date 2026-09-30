# Knowledge Expansion Phase 0

Date: 2026-09-28
Scope: runtime readiness and decision record only; stopped before Phase A.

## Outcome

Implemented the bounded extraction and registry fixes from
`Implementation_Plan/KNOWLEDGE_EXPANSION_REVIEW_AND_PLAN.md`.
No categories, parameters, operations, schemas or templates were added to the
authoring catalog, and no release was published. SQLite remains authoritative.
The existing 12 operations, 36 bindings and public function signatures remain.

Active release retained: `fbd929e928014a4886fbfd69c4019851`.
Before/after SHA-256 checks found all 257 files under `data/`,
`storage/knowledge/` and `storage/catalog_releases/` unchanged, including the
database, authority marker, active pointer, templates and retrieval artifacts.
No full-catalog export/import was needed for this code-only change.

## Implemented Changes

| File | Change |
| --- | --- |
| `app/parameters/evidence.py` | Schema/alias-scoped literal evidence for primitive lists, typed JSON objects/arrays and quoted strings; preserves item grouping and excludes literal contents from unrelated field discovery |
| `app/parameters/parameter_extractor.py` | Includes mentioned optional fields in extraction; skips model only when relevant fields are accounted for; uses collection-level evidence rather than prompt-wide scalar assembly; unresolved optional input becomes a clarification candidate |
| `app/pipeline.py` | Preserves extraction-specific question wording in both initial planning and operation-confirmation paths |
| `app/knowledge/rule_registry.py` | Keeps all three mandatory handlers; allows additional code-reviewed callbacks through an explicit registry, rejects unknown/duplicate IDs, replacements and non-callable handlers |
| `app/knowledge/services.py` | Checks category parameter aliases using the same punctuation/case normalization as extraction; rejects aliases without searchable characters |
| `tests/test_expansion_readiness.py` | Focused extraction, validation, compiler, alias and clarification-resume regressions |
| `tests/fixtures/phase0_extraction_prompts.json` | Six repeatable golden prompts against existing operation contracts, with expected parameters and model-call budgets |

### Evidence and Clarification Contract

- `allowed vlans 10,20` and `allowed vlans [10,20]` preserve the complete list.
  Lists also support explicit `and` separators; strings/booleans have strict item
  types. Separate labelled fields with semicolons when using this literal syntax.
- A DSCP list cannot supply a missing VLAN list merely because its numbers occur
  in the prompt. A proposed subset does not replace the complete explicit list.
- Nested structured values require labelled JSON with canonical payload keys.
  Leaf values remain attached to their original object/item; missing nested
  required fields are handled by the existing validator. Duplicate JSON keys
  and wrong item types do not produce a partially accepted collection.
- Existing OSPF natural-language interface/area parsing remains available.
  This change does not introduce generic nested-prose understanding.
- Quoted descriptions are extracted without a model. Unquoted explicitly
  labelled descriptions can use the bounded model path and must match field
  evidence; a truncated prefix is not accepted as the complete description.
- Quoted strings and JSON contents are excluded from unrelated deterministic
  field discovery: `description "enable VLAN 99"` cannot enable a port or set
  VLAN 99. Use quotes when description boundaries are ambiguous.
- Mentioned optional fields that remain unresolved produce `UNRESOLVED_VALUE`
  questions. Absent optional fields do not create questions or model calls.
  Custom replies still pass through the existing field-scoped validator.
- Explicit false/zero values survive extraction. Invalid but explicitly typed
  values, such as VLAN -1 or unsafe description punctuation, reach schema/domain
  validation and are blocked; no value is silently clipped to fit a constraint.
- Ranges, units and disjunctions are not guessed or partly consumed by the new
  list parser. Unsupported input remains unresolved for clarification.
- Existing `requested_fields` limits also apply to ambiguity candidates and new
  optional-input questions; replies cannot affect unrelated fields.

`ADDITIONAL_VALIDATION_HANDLERS` is deliberately empty in production for Phase 0.
Future handlers must be implemented and reviewed in Python, then explicitly
bound by a reviewed operation root. Callbacks receive `(parameters, schema)`
and return existing `ValidationIssue` objects with answerable field paths.
There are no dynamic imports, uploaded handlers, catalog-defined Python or
new handler-argument language. Tests register a temporary handler only inside
isolated test fixtures and prove mandatory string safety still executes.

## Canonical Decisions Retained

These are constraints for subsequent pack implementation, not active catalog
records or certification of new operations. The proposal's parameter-selection
tables remain the detailed design; unresolved behavior below still needs review.

| Proposed domain | Canonical disposition |
| --- | --- |
| VLAN | Preserve `create_vlan` and `delete_vlan`; `modify_vlan` and `rename_vlan` need narrow patch/identity semantics; `assign_vlan_to_access_port` is a discovery alias for future `configure_access_port`; `assign_vlan_to_trunk_port`, `configure_trunk_allowed_vlans` and `set_native_vlan` belong to Interface |
| Interface | New `set_interface_description`, `set_interface_admin_state`, `configure_access_port`, `configure_trunk_port`; reuse existing `configure_interface_ip` for `assign_ip_address`; hold `configure_loopback_interface` and `configure_port_channel` until scoped creation/member validation exists |
| Static Routing | Reuse `configure_static_route` for `add_static_route` and `remove_static_route` for `delete_static_route`; `add_default_route` is a distinct specialization; `add_floating_static_route` needs explicit preference and a qualified backup claim |
| OSPF | Preserve existing compound `configure_ospf`; separately review `enable_ospf_process`, `set_ospf_router_id`, `create_ospf_area`, `assign_interface_to_ospf_area`, `advertise_network`, `configure_passive_interface`, `configure_ospf_redistribution`, without reusing conflicting aliases or inventing cross-vendor equivalence |
| ACL | Review one IPv4 family for `create_acl`, `add_acl_rule`, `modify_acl_rule`, `delete_acl_rule`, `apply_acl_to_interface`; modify means complete rule replacement initially, not missing-match-as-any |
| QoS | `create_qos_policy`, `create_classifier`, `classify_by_dscp`, `configure_scheduler`, `configure_shaping`, `configure_policing`, `apply_qos_policy_to_interface` remain gated on explicit object relationships, treatment scope and profile support |

All 38 proposed names are accounted for above. One canonical operation retains
one owner; no duplicate executable operation is introduced for discoverability.
Existing BGP, IS-IS and IP-address categories/operations remain unchanged. The
future six expansion domains would use nine physical categories, adding only
Interface, ACL and QoS to the existing six; none is added during Phase 0.

### Parameter Decisions

| Reuse / distinction | Decision |
| --- | --- |
| `interface`, `description`, `vlan_id` | Reuse shared definitions across memberships; requirements remain per operation |
| `address`, `prefix_length` | Preserve IDs; netmask is validated input normalization, not a second stored authority |
| `admin_up` | Preserve boolean representation and explicit false; do not add duplicate `admin_state` |
| `name` | Preserve existing VLAN-name meaning; future `new_vlan_name` is a distinct rename destination |
| `interfaces` | Preserve the OSPF object-array meaning; future `member_interfaces` is a different string-array definition |
| `allowed_vlans`, `dscp_values` | Future integer arrays, not CLI strings; bounds and item rules belong to operations |
| Rates and bursts | Future integer base units: bps and bytes; no implicit Mbps conversion or float coercion |
| Preference versus metric | Retain current compatibility behavior in Phase 0; disambiguation/deprecation needs approval before new metric fields activate |
| ACL/QoS identifiers | Use domain-specific identities, not generic overloaded `name`, `action` or `mode` parameters |

New aliases that normalize to the same category-local key now fail authoring
validation even when punctuation differs. This is an intentional integrity
tightening for future edits, not a change to the existing published registry.

## Support Matrix and Approval Holds

| Scope | Cisco / iosxe / 17.9 | Huawei / vrp / 8 | Juniper / junos / 23.4 |
| --- | --- | --- | --- |
| Original operation bindings | Retained unchanged | Retained unchanged | Retained unchanged |
| New VLAN modification/rename | Not enabled | Not enabled | Not enabled |
| New switchport/logical-interface behavior | Not enabled | Not enabled | Not enabled |
| New routing specializations | Not enabled | Not enabled | Not enabled |
| ACL and QoS | Not enabled | Not enabled | Not enabled |
| Exact hardware certification | Not established | Not established | Not established |

Existing inventory declarations and template files are not proof of switchport,
LAG, ACL, queue or policy capabilities. No blanket capability flags were added.
Templates stay operation-level with exact explicit bindings. Optional/boolean
formatting and loops are allowed; resource lookup and safety policy stay outside
Jinja. Unsupported profiles must remain unsupported.

## Verification

- Full compatibility run: **188 tests passed** (168 existing plus the first 20
  Phase 0 tests), in approximately 194 seconds.
- Final focused command: `python -m unittest discover -s tests -p test_expansion_readiness.py -q`.
  Additional golden/safety cases were added after the full run; **23 focused
  tests passed**, including all six golden prompts, in approximately one second.
- Model responses in regressions are mocked, including null, invented values,
  omitted optional fields and exact valid responses. All temporary authoring and
  publication fixtures use temporary projects, not the workspace authority.
- The six golden prompts measure repeatable argument outcomes and model-call
  budgets, not actual language-model accuracy or a larger-catalog benchmark.
- Ollama at `127.0.0.1:11434` refused connections during this run. No model was
  downloaded or started; live local-model accuracy and latency remain unverified.
- No device execution, live CLI certification, GUI or external integration test
  is claimed. `git diff --check` passed.

## Remaining Work and Review Gate

Historical Phase 0 handoff: the later A-D pack implementation supersedes the
phase-stop instructions below. See `KNOWLEDGE_EXPANSION_COMPLETION.md`.

1. Review Phase 0 behavior, particularly unresolved optional-input questions and
   stricter alias collision detection. Approve Phase A separately.
2. For Phase A, choose the first exact hardware/NOS scope and resolve VLAN modify
   fields, rename identifiers/collision/reference handling and unsupported profiles.
3. Rehearse future complete knowledge packs through existing management services;
   keep SQLite authoritative and retain whole-catalog publication/version checks.
   No new pack importer or machine-importable expansion records were needed here.
4. Before Interface/ACL/QoS activation, implement the separately planned scoped
   creation, reference, capability and composite-resource checks. Primitive-list
   readiness alone does not make those domains supported.
5. Resolve additive versus replacement trunk semantics, OSPF alias transitions,
   metric/preference ambiguity, ACL scope and QoS object relationships as described
   in the review. No hidden defaults or universal-vendor claims are approved.
6. Repeat a small live-model prompt evaluation when Ollama is available; compare
   selection, device binding, extraction, clarification and latency per wave.
   General nested prose, range/unit conversion and fractional clarification remain
   future reviewed extensions, not silently enabled by this phase.

Rollback is code-only: revert only the Phase 0 additions/edits after review,
preserving pre-existing work. No database rollback or active-pointer edit is
required. Do not use a whole-worktree reset: the repository already contained
uncommitted Phase 1-5 work before this task.
