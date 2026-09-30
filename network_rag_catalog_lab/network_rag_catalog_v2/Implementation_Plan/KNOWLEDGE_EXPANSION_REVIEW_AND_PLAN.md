# Knowledge Expansion: Architecture Review and Implementation Proposal

Date: 2026-09-28
Status: implementation recorded for Phases 0, A, B1/B2, C, D1/D2 as review-only
packs; no live activation. The proposal below is retained as the design baseline.

## Implementation Update (2026-09-29)

The user approved completion through the remaining domain phases, with validated
packs only and no changes to the live SQLite catalog or active release. See
`docs/KNOWLEDGE_EXPANSION_COMPLETION.md` for the exact canonical decisions, supported
profiles, code changes, rehearsal procedure and remaining acceptance work.
`docs/KNOWLEDGE_EXPANSION_VERIFICATION.md` records final verification.
There is no Phase E in this plan. Hardware/lab certification, expanded live-model
evaluation and indexed rollout remain acceptance gates, not implied by pack tests.

## 1. Executive Decision

The Phase 1-5 knowledge architecture is a suitable foundation for this expansion.
Keep its category/parameter/operation entities, schema compiler, template bindings,
SQLite authority and publication workflow. Do not rebuild them.

However, importing records alone will not make all proposed operations work safely
from natural language. The existing runtime is strongest on the original routing,
VLAN and interface-address shapes. Primitive lists, optional-value extraction,
logical-interface creation, ACL/QoS resource references and some cross-field rules
need bounded extensions or explicit unsupported outcomes.

Recommendation: **Option B, existing management services**, fed by reviewed,
version-controlled change packages. Reuse existing import/export for recovery;
do not introduce a second importer or bypass services with direct SQL writes.

Deliver the six requested domains incrementally, not all vendors and all commands
in one release. Every requested operation must have a disposition and support
matrix, but a reviewed unsupported profile is preferable to invented syntax.

### Review Scope and Evidence

- Inspected the implemented Python modules, authoritative SQLite catalog, current
  seed layouts, inventory, templates, earlier registry document and evolution plan.
- The separate file titled "Knowledge Expansion Task" was not found in the
  workspace; this review treats the **38 operations in the current user request**
  as the expansion proposal. The older category registry is supporting context,
  not authorization to import its larger operation list.
- Read-only database inspection confirms 6 categories, 20 parameter definitions,
  22 memberships, 12 operations, 38 mappings, 51 rule nodes and 36 template bindings.
- Current declared profiles are Cisco/iosxe/17.9, Huawei/vrp/8 and
  Juniper/junos/23.4. These are lab declarations, not hardware certification.
- Previous completion evidence records 168 passing tests. This review did not
  rerun the suite, invoke the LLM, migrate data or publish a release.
- Small read-only function probes confirmed the list-extraction, number-answer,
  handler-registration and new-interface limitations described below.
- This document is the only intended file change in this review.

## 2. Current Architecture

### Storage and Components

```text
Reviewed management request / local CLI
                    |
     app/api/contracts.py + knowledge/management.py
       metadata, references, impact, expected revision
                    |
              authority.py
           /                \
 JSON adapter             SQLite authoring (this workspace)
 before migration        transactional catalog + audit
                              |
       Category ---- CategoryParameter ---- ParameterDefinition
          |
       Operation / current OperationVersion
          |                         |
       OperationParameterMapping    OperationSchemaRule
          |                         |
          +------ schema_compiler --+
                         |
                 compiled JSON Schema
                         |
       TemplateBinding: operation/version + vendor/platform/OS
                         |
       publication: validate -> stage -> compile -> build Chroma
                         |
                 atomic active-release pointer
                         |
        immutable metadata / schemas / templates / retrieval
```

| Element | Actual implementation |
| --- | --- |
| Category | `Category` record: stable ID, display name, aliases, description, active/inactive status; no parent-category hierarchy |
| Shared parameter | `ParameterDefinition`: stable ID, meaning/label, primitive or container type, aliases, question wording, optional registered normalizer; operation policies are excluded |
| Category membership | `CategoryParameter`: category/parameter ID pair; definitions are not duplicated per category |
| Operation | Stable globally unique ID, one owning category, version, status, aliases/use cases and explicit schema authority |
| Parameter mapping | Operation/version, category membership, full payload path, position, required flag and required order |
| Rules | Separate schema nodes retain bounds, enums, item shapes, vendor requirements and supported conditional/cross-field policies |
| Schema generation | `compile_schema` combines shared types, mappings and rules; unsupported constructs fail instead of being silently dropped |
| Template binding | Explicit operation/version and vendor/platform/version-list contract, source path and declared inputs; optional defaults may only be null |
| Publication | Stages all catalog schemas/templates plus release-specific retrieval; verifies artifacts and activates one pointer only on success |
| Runtime | Public `app/catalog.py`, schema loader and renderer use request-pinned published knowledge, not live database drafts |
| Management | Typed requests/results; batched edits, impact, previews, validation, import/export, retirement, transactions and audit through CLI/service |

SQLite lives at `storage/knowledge/catalog.sqlite3`; the authority marker is
`storage/knowledge/authority.json`. Managed JSON files are seed/export shapes,
not a parallel authoring authority. Jinja source assets, inventory and planned
context remain files. Historical authoring is in audit snapshots; runtime versions
are immutable releases, not independently editable operation-version branches.

### Current Runtime Flow

```text
Prompt -> evidenced intent decomposition and target descriptions
       -> exact catalog phrase OR category -> retrieval -> proposed operation
       -> inventory resolution + per-operation schema extraction
       -> per-device bindings
       -> schema/domain/device/planned-context checks
       -> one-field questions: options + custom answer + revalidation
       -> all tasks valid and any resource conflicts resolved?
            no: retain session, render nothing
            yes: compatible vendor templates -> staged configuration previews
```

Category classification is not an obligatory first step: exact operation phrases
bypass it. Inventory and planned context have their own revision checks. Semantic
retrieval proposals require confirmation; the LLM does not choose executable syntax.

### Source Map

References are V2-relative paths and current line anchors for review:

| Files / anchors | What to inspect |
| --- | --- |
| `app/knowledge/models.py:27`, `:32`, `:49`, `:58`, `:93`, `:105`, `:126` | Existing entity contracts |
| `app/knowledge/services.py:146`, `:180` | Membership and alias integrity |
| `app/knowledge/management.py:62`, `:115`, `:207`, `:261` | Candidate validation, changes, draft edits and publication |
| `app/knowledge/schema_compiler.py:11`, `migration.py:25` | Compiler and unsupported schema vocabulary |
| `app/knowledge/publication.py:45`, `:127` | Template validation and release activation |
| `app/knowledge/runtime.py:71`, `:81` | Vendor schema loading and exact template-profile selection |
| `app/parameters/parameter_extractor.py:63`, `:92`, `:141` | Evidence filtering and extraction fast path |
| `app/parameters/fields.py:60`, `normalizer.py:113` | Typed clarification and existing deterministic parsers |
| `app/devices/context_validator.py:50`, `:67` | Interface normalization and capability/existence checks |
| `app/context.py:78`, `app/pipeline.py:349`, `:372` | Context options, conflict detection and whole-request gate |

## 3. Feasibility and Gap Analysis

| Requirement | Current Support | Missing Component | Required Change |
| --- | --- | --- | --- |
| Add category | Supported by management and database | Reviewed Interface/ACL/QoS definitions and actual device support facts | Add records/memberships; keep legacy categories |
| Add shared parameters | Typed reusable definitions and membership supported | Domain-specific identities, units, enums/item contracts and aliases | Add reviewed definitions; put constraints in operation rules |
| Add operations | Stable IDs, versions, lifecycle and globally checked aliases | Canonical taxonomy and precise mutation semantics | Add records only for genuinely new behavior; reuse existing IDs for equivalents |
| Add mappings | Nested paths, independent required flags, item schemas supported | Mappings for new operations | Service contract replacement; no mapping redesign |
| Generate schemas | Scalars, nested objects/arrays, vendor-required fields, dependency/equality conditions | Some ACL/QoS/no-op/cross-field semantics | Existing schema vocabulary first; reviewed named handlers where necessary |
| Add templates | Standalone operation-level Jinja, declared profiles, strict inputs supported | Reviewed vendor assets and acceptance evidence | Add assets and bindings for supported profiles only |
| Publish knowledge | Immutable releases, exact index identity, atomic activation supported | Expanded catalog performance/coverage evidence | Reuse workflow; test larger documents/index and rollback procedure |
| Extract expanded inputs | Existing field parsers and scalar grounding | Primitive lists, optional fields, ranges/units and complex nested evidence | Narrow parser/filter changes before affected operations go live |
| Validate new resources | Existing interfaces and category feature checks | L2/L3 capability, logical creation, named ACL/QoS resources and members | Add scoped rules/context facts; do not globally relax inventory checks |
| Handle operation dependencies | Listed order and configured resource conflicts | Create/reference validation and composite resource identity | Minimal request-local checks or reject unsupported chains; no execution engine |

### Concrete Runtime Limits Requiring Decisions

1. **Primitive arrays are dropped by LLM filtering.** `_filter_value` keeps array
   elements only when they are dictionaries. Probe: `[10,20]` for `allowed_vlans`
   returns no extracted value. A clarification JSON array does parse successfully.
   Fix evidence-preserving primitive item handling, and do not apply scalar string
   grounding to an entire list/object; validate each leaf and field association.
2. **Optional values can be silently omitted.** If all unconditional required
   fields have deterministic matches, the LLM is skipped even when an explicitly
   supplied optional field lacks a deterministic parser. For example, access-port
   description needs handling even when interface and VLAN are already found.
   Test this path explicitly; do not call the model unnecessarily when no such
   text exists, and do not invent values for absent optional fields.
3. **Generic domain handlers are not freely pluggable yet.** `validate_handler_ids`
   requires exactly the three legacy handlers; adding `acl_rules_v1` is rejected.
   Extend that existing registry to retain mandatory safety checks and allow
   explicit, code-reviewed additional IDs with validated arguments where needed.
   Only `ipv4_prefix_length` normalization and `ipv4_netmask_v1` template derivation
   are currently registered; registering a new name alone does not implement it.
4. **Device checks recognize specific payload shapes.** They validate `interface`
   and OSPF `interfaces[].name`, not arbitrary `member_interfaces[]`. A new
   `Loopback99` is rejected as nonexistent. Creation needs an operation-scoped
   policy, approved logical-interface naming/capability evidence and collision
   checks; existing-interface operations must continue requiring inventory matches.
5. **Inventory does not prove switching or ACL/QoS support.** Current feature
   lists are broad routing categories and interfaces lack reviewed switchport,
   aggregation and policy-support facts. Do not mark every router `interface`,
   `acl` or `qos` capable merely to make prompts pass.
6. **Schema expressiveness is deliberately bounded.** `oneOf`, `anyOf`, `if/then`,
   references and dynamic schema structures are rejected. Keep fixed typed payloads
   and existing conditional-required rules; express protocol-specific combinations
   and "at least one change" via reviewed handlers rather than redesigning the compiler.
   Domain errors must identify a real answerable field; a root-only error currently
   becomes an operation-selection question, which is unsuitable for an empty patch.
7. **Some checks use literal payload keys.** IPv4/area/identifier checks do not
   automatically follow every new parameter mapping. Reuse existing keys when
   semantically equal; bind explicit checks for new source/destination prefixes,
   member lists and reference names instead of assuming type validation is enough.
8. **Context suggestions are not a generic resource registry.** Inventory options
   currently enumerate interfaces; planned lookup is field-scoped. ACL existence,
   policy/classifier links and LAG membership are not known simply because a user
   names them. Extend approved local facts/checks only where needed, with provenance.
9. **Cross-task resources are flattened string sets.** ACL name and rule ID would
   be compared as independent strings, producing false conflicts across different
   ACLs/rules. Add typed composite keys through existing context rules, preserving
   legacy behavior, before multi-operation ACL/QoS workflows are enabled.
10. **Discovery can cross category boundaries.** An access-port paraphrase containing
    "VLAN" can be classified into VLAN while its canonical operation belongs to
    Interface. Test this explicitly; use bounded cross-category proposals or better
    classification when needed, never duplicate executable operations to fix retrieval.
    Parameter collision checks should also use the same punctuation normalization
    as extraction, not just case-insensitive comparison.
11. **Profiles currently vary requirements by vendor, not arbitrary hardware.**
    Template selection is exact vendor/platform/version, but effective schema lookup
    selects by vendor and no independent platform-rule overlay exists. Initially
    choose one reviewed hardware/profile scope and a compatible contract. If two
    profiles genuinely need different constraints, return for a narrowly scoped
    design approval; do not pretend file presence provides this support.
12. **`number` clarification is incomplete.** A probe of `1.5` returns a string,
    unlike integer parsing. Prefer integer base units for this proposal; implement
    strict number parsing only if fractional domain values are approved.

These are expansion boundaries, not a reason to discard the Phase 1-5 design.

## 4. Import Strategy

| Option | Advantages | Disadvantages / Risks | Decision |
| --- | --- | --- | --- |
| A: Direct JSON/YAML edits | Easy to review in Git | Managed JSON is no longer authoritative; bypasses revisions/audit; YAML adds an unnecessary format | Do not use as the live write path |
| B: Existing services | Reuses validation, transactions, dependencies, versions, audit and publication | Requests need complete contracts/assets; repeated creates are not idempotent | Recommended |
| C: New importer/migration | Could automate bulk diffing and portability | Duplicates an existing import service, risks destructive whole-catalog replacement and two authorities | No new persistence/import subsystem |

Use reviewed JSON **change packages**, not independently authoritative catalogs.
Suggested future layout: `knowledge_packs/<domain>/` with `manifest.json`,
`changes.json`, prompt cases, expected outputs and a support matrix. These paths
are proposals only. Jinja assets stay under the existing template source tree.

Package application procedure:

1. Export/inspect the selected authority and record expected revision/release.
2. Compare stable IDs against the current draft, preserve unrelated records and
   resolve intentional updates versus existing equivalent records.
3. Validate template assets and hashes, category memberships, aliases, full paths,
   operation versions, vendor support, context rules and representative prompts.
4. Materialize one batch of existing `EntityChange` requests with actor/reason and
   current `expected_revision`; use `apply(..., dry_run=True)` before committing.
5. Import complete coherent batches into an isolated rehearsal project first.
6. Apply approved batches through services; preview/validate all operations and
   explicitly publish the whole catalog only when ready.

If repeatable pack application is useful, a small `app/knowledge/pack_review.py`
can produce diffs and existing request envelopes. It must not write SQL, own a new
schema language, automatically select the newest version or silently overwrite
senior-engineer edits. Reapplication must report already-matching records as a
no-op; conflicting content must require a new reviewed revision.

Existing `import_catalog` is a **complete document replacement**, not a merge.
It checks exact external asset hashes and published-identity protections. Never
feed it a category-only bundle. Incomplete inactive operations can be drafted but
currently block whole-catalog publication; keep unfinished packs outside the
authoritative draft until each publishable batch is coherent.

## 5. Category and Naming Decisions

Retain `vlan`, `ospf`, `static_routing`, `bgp`, `isis` and `ip_address` initially.
Add `interface`, `acl` and `qos`: **nine physical categories**, including the legacy
ones, serve the six requested expansion domains. Removing BGP/IS-IS or moving old
IP operations is not implicit in the proposal.

An operation has one owner. Recommend Interface owns switchport/port behavior;
VLAN owns VLAN objects. Cross-domain discovery is by descriptions/aliases and
bounded retrieval, not duplicate operation identities.

`assign_ip_address` already matches `configure_interface_ip`; keep the latter ID
and its `ip_address` owner in the first release. A later move to Interface would
require an explicit versioned migration of category, membership, capability,
context and template references, not a label-only edit.

### Shared Parameter Registry Proposal

Types below are proposed for review, not imported facts. All enums, bounds,
item structures and required/optional policies remain **operation rules**.

| Domain | Reuse Existing Definitions | Proposed New Definitions / Primitive Types |
| --- | --- | --- |
| VLAN | `vlan_id: integer`, `name: string` meaning VLAN name, `description: string` | `new_vlan_name: string`, `vlan_status: string`; port-related fields belong to Interface unless exposed there for discovery-independent reuse |
| Interface | `interface: string`, `description: string`, `admin_up: boolean`, `vlan_id: integer`, `address: string`, `prefix_length: integer` | `allowed_vlans: array` of integers, `native_vlan: integer`, `member_interfaces: array` of strings, `aggregate_interface: string`, `lacp_mode: string`; `interface_mode: string` only if an approved contract needs it |
| Static Routing | `destination: string`, `next_hop: string`, `preference: integer`; `interface: string` only for an approved interface-qualified route contract | No new parameter is needed for initial default/floating-route contracts; add `route_metric: integer` only after its distinct meaning and vendor behavior are reviewed |
| OSPF | `process_id: integer`, `router_id: string`, `area: string`, `interface: string`, unchanged `interfaces: array` of OSPF objects | `area_type: string`, `network_prefix: string`, `passive: boolean`, `redistribution_source: string`, `source_process_id: integer`, `ospf_metric: integer`, `metric_type: string`, `route_policy: string` as approved |
| ACL | `interface: string`, `description: string` | `acl_name: string`, `acl_rule_id: integer`, `acl_action: string`, `source_prefix: string`, `destination_prefix: string`, `ip_protocol: string`, `source_port: integer`, `destination_port: integer`, `log: boolean`, `direction: string`; `acl_number: integer` only where a reviewed profile requires it |
| QoS | `interface: string`, `description: string`, shared `direction: string` only if ingress/egress meaning is identical | `policy_name: string`, `classifier_name: string`, `dscp_values: array` of integers, `scheduler_name: string`, `forwarding_class: string`, `queue_id: integer`, `bandwidth_bps: integer`, `rate_bps: integer`, `burst_bytes: integer`, `scheduler_priority: string`, `exceed_action: string`, `match_mode: string`, `policy_terms: array` of reviewed fixed objects |

All named child properties of `policy_terms[]` must also reference registered
definitions exposed by QoS. Anonymous primitive array items use rule nodes; they
do not require a second mapping for the anonymous item itself.

Important naming decisions:

- Keep `name` as the existing VLAN-name identity; display "VLAN name" rather than
  introducing a duplicate `vlan_name` definition. `new_vlan_name` is a distinct
  rename destination, not an alias of the existing resource identifier.
- Keep `address` and `prefix_length`; accept explicit netmask input through the
  existing validated conversion. Do not store both a mask and prefix as competing
  editable authorities. IPv6 needs its own future contract, not IPv4 field reuse.
- Reuse boolean `admin_up` for administrative state; show a friendly label rather
  than adding a second enum representation called `admin_state`.
- Never reuse OSPF `interfaces` as a generic interface string list; use
  `member_interfaces` for aggregation members.
- Keep `destination`/`preference`/`area` IDs and use labels for destination prefix,
  route preference and OSPF area. A mapped path can differ from its shared ID, but
  existing key-sensitive validators must be covered before changing payload paths.
- Existing `preference` aliases/parser accept "metric". Explicitly deprecate or
  disambiguate that wording before adding route or OSPF metrics; report this as a
  reviewed behavior correction, not an invisible rename.
- Avoid global `action`, `mode`, `priority` or `name` catch-all definitions for
  unrelated concepts. ACL action, policer action and scheduler priority differ.
- Scope aliases to the schema/category and also test global operation phrases;
  exact aliases are currently unique even for inactive operations.

### Parameter Selection Example

```text
interface category membership
  interface (string), vlan_id (integer), description (string), admin_up (boolean)
                    |
  configure_access_port
    interface REQUIRED; vlan_id REQUIRED; description OPTIONAL
    operation rules: approved VLAN range; safe description; supported switchport
                    |
  set_interface_description
    interface REQUIRED; description REQUIRED
```

Changing `configure_access_port.description.required` must not change any other
operation. The shared definition carries neither required flags nor VLAN bounds.

## 6. Operation-by-Operation Taxonomy Review

R = required; O = optional; V = required by the reviewed vendor/profile contract.
The selections below intentionally correct underspecified inputs in the proposal.
No missing target, wildcard, interface, policy, metric or direction may be guessed.

### A. VLAN: Existing Category, Mostly New Memberships/Behavior

| Proposed Operation | Disposition and Owner | Proposed Selection / Safety Decision |
| --- | --- | --- |
| `create_vlan` | Keep existing VLAN operation | R `vlan_id`; O `name`; add `description` only with explicit support/version review, not to all templates automatically |
| `modify_vlan` | Too broad without patch semantics | R `vlan_id`; O selected `description`, `vlan_status`; require at least one supported change; route renaming through the explicit rename operation |
| `rename_vlan` | New VLAN behavior, profile-gated | R `vlan_id`, `new_vlan_name`; V existing `name`; resolve current identity from confirmed planned facts, and check references/collisions |
| `delete_vlan` | Keep existing operation | R `vlan_id`; V `name` for existing Juniper contract; preserve exact deletion semantics |
| `assign_vlan_to_access_port` | Discovery phrase for Interface `configure_access_port`, not a duplicate record | R `interface`, `vlan_id`; O `description` |
| `assign_vlan_to_trunk_port` | Distinct additive behavior, owned by Interface | R `interface`, `allowed_vlans`; must preserve other allowed VLANs; do not alias to full replacement |
| `configure_trunk_allowed_vlans` | Explicit replacement on an existing trunk, owned by Interface | R `interface`, `allowed_vlans`; presentation must say replacement; approved empty/all semantics must be explicit |
| `set_native_vlan` | New Interface-owned port behavior | R `interface`, `native_vlan`; validate reviewed port/native-VLAN policy |

The legacy Juniper `create_vlan` template synthesizes `VLAN<id>` if `name` is absent;
this is existing template behavior, not authoritative evidence of an existing VLAN
name. Never reuse that assumption for rename or delete. There is no current VLAN
object inventory that proves dependent references can be renamed safely.

Trunk addition and replacement are genuinely different mutations, not synonyms;
Cisco documents distinct allowed-list operations. Preserve this distinction in
canonical behavior and review the exact target release before enabling a binding.
[Cisco VLAN trunk configuration guide](https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst3850/software/release/3se/consolidated_guide/configuration_guide/b_consolidated_3850_3se_cg/b_consolidated_3850_3se_cg_chapter_010001001.pdf)

### B. Interface: New Category, Reuse Existing Addressing Operations

| Proposed Operation | Disposition | Proposed Selection / Safety Decision |
| --- | --- | --- |
| `set_interface_description` | New | R `interface`, `description`; spaces allowed within reviewed escaping/safety rules; clearing a description needs an explicit separate behavior |
| `set_interface_admin_state` | New using existing boolean identity | R `interface`, `admin_up`; explicit false must not disappear through truthiness tests |
| `configure_access_port` | Canonical access-port operation | R `interface`, `vlan_id`; O `description`; changing L2 mode is explicit behavior, not implied by merely mentioning a VLAN |
| `configure_trunk_port` | New explicit trunk-mode configuration | R `interface`, `allowed_vlans`; O `native_vlan`; distinguish full setup from editing the list on an existing trunk |
| `assign_ip_address` | Reuse `configure_interface_ip` | R existing `interface`, `address`, `prefix_length`; do not duplicate its existing alias or move its category silently |
| `configure_loopback_interface` | Profile-gated logical resource creation/configuration | R approved loopback `interface`, `address`, `prefix_length`; O `description`; an omitted prefix is not automatically /32; nonexistent logical interfaces require the new scoped policy |
| `configure_port_channel` | Broad compound behavior; narrow before publication | R `aggregate_interface`, nonempty `member_interfaces`, `lacp_mode`; O `description`; first scope excludes addressing and VLAN setup, which remain separate operations |

LAG member existence, uniqueness, ownership, supported type and aggregate/member
compatibility need explicit validation. Do not treat an aggregate interface as an
ordinary pre-existing physical port or silently create its members.

### C. Static Routing: Existing Category, Preserve Exact Selectors

| Proposed Operation | Disposition | Proposed Selection / Safety Decision |
| --- | --- | --- |
| `add_static_route` | Existing alias of `configure_static_route` | R `destination`, `next_hop`; O `preference`; keep current ID |
| `delete_static_route` | Existing phrase for `remove_static_route` | R `destination`, `next_hop`; prefix-only deletion is broader and must not be silently substituted |
| `add_default_route` | New well-defined specialization | R `next_hop`; O `preference`; literal IPv4 default destination is intrinsic to this operation, not an LLM-filled missing parameter |
| `add_floating_static_route` | New specialization requiring explicit preference | R `destination`, `next_hop`, `preference`; validate that claimed backup preference is consistent with planned primary-route facts, or disclose that the backup property is unverified |

Do not make `metric` an alias for route preference. Keep initial scope IPv4,
default routing context, and IP next hops; VRFs, IPv6, discard and interface-only
routes need separately reviewed contracts. Existing destination validation accepts
host bits with `strict=False`; new route policies must explicitly normalize or
reject non-network CIDRs rather than passing inconsistent vendor representations.

### D. OSPF: Existing Category, Preserve the Existing Compound Operation

| Proposed Operation | Disposition | Proposed Selection / Safety Decision |
| --- | --- | --- |
| `enable_ospf_process` | Separate from `configure_ospf`; profile-gated | V `process_id`; O `router_id`; do not reuse existing "enable ospf"/"create ospf process" phrases without a reviewed alias transition |
| `set_ospf_router_id` | New only where semantic scope agrees | R `router_id`; V `process_id`; reject profiles where the implementation would silently change a broader routing-instance router ID |
| `create_ospf_area` | Underspecified; define meaningful area behavior first | R `area`, approved `area_type`; V `process_id`; do not publish a template that merely enters an empty context or has no persistent effect |
| `assign_interface_to_ospf_area` | New single-interface membership operation | R `interface`, `area`; V `process_id`; preserve `configure_ospf` for its existing interface-array behavior |
| `advertise_network` | Define as OSPF interface/network selection, not arbitrary route injection | R `network_prefix`, `area`; V `process_id`; support only reviewed profile semantics; no guessed interface from a prefix |
| `configure_passive_interface` | New explicit passive-setting behavior | R `interface`, `passive`; V `area`, `process_id`; distinguish suppressing neighbor formation from removing route advertisement |
| `configure_ospf_redistribution` | Broad and high-impact; strict source/policy scope | R `redistribution_source`, reviewed limiting `route_policy`; V source/process identifiers and metric fields; never default to redistributing everything |

Junos requires interface participation to enable OSPF; a process-only operation
must not pretend to provide the same effect there. The recommendation is a
supported-profile subset, not extra invented parameters or an empty success.
[Junos OSPF interface reference](https://www.juniper.net/documentation/us/en/software/junos/cli-reference/topics/ref/statement/interface-edit-protocols-ospf.html)

The current inventory does not contain enough authoritative interface addressing
to resolve arbitrary network-prefix descriptions into interfaces. Keep that
translation unsupported until reviewed local planned facts exist; no topology
engine is proposed. Existing `area` representation and process requirements stay.

### E. ACL: New Category and New Domain Validation

| Proposed Operation | Disposition | Proposed Selection / Safety Decision |
| --- | --- | --- |
| `create_acl` | New, start with one approved IPv4 ACL family | R `acl_name`; O `description`; V explicit numeric identifier if the selected profile requires one; do not synthesize a numeric ID from a name |
| `add_acl_rule` | New, explicit match and action | R `acl_name`, `acl_rule_id`, `acl_action`, `source_prefix`, `destination_prefix`, `ip_protocol`; O ports/log only where supported |
| `modify_acl_rule` | Define full replacement initially, not a partial opaque patch | R same complete rule fields; selected rule must be authoritative/confirmed; no "missing match means any" behavior |
| `delete_acl_rule` | Exact rule deletion | R `acl_name`, `acl_rule_id`; prove the target rule scope; never delete the whole ACL as fallback |
| `apply_acl_to_interface` | New reference binding | R `acl_name`, `interface`, `direction`; verify ACL identity/family, supported attachment, and existing-binding replacement policy |

Use typed match fields, not a free-form `conditions` CLI string. Proposed first
scope is IPv4 with explicit canonical prefixes; a user saying "any" can be
normalized only by an approved field-specific parser. Transport ports require a
compatible protocol; rule IDs are not queue IDs or global priorities. Rule ranges,
named service groups, IPv6 and stateful policy are separate future scope decisions.

Do not give all targets an empty-ACL template if that platform does not retain a
meaningful empty object; omit that binding or use a separately approved complete
ACL creation contract. Reference checks must not confuse a planned candidate with
a confirmed resource or proof that it has already been configured on a device.

### F. QoS: New Category; Object Relationships Must Be Defined

| Proposed Operation | Disposition | Proposed Selection / Safety Decision |
| --- | --- | --- |
| `create_qos_policy` | Define policy contents and references, not just a name | R `policy_name`, reviewed `policy_terms`; O `description`; child classifier/treatment references must be explicit |
| `create_classifier` | Narrow initial match language to DSCP | R `classifier_name`, nonempty `dscp_values`, `match_mode`; avoid an untyped `match_conditions` string |
| `classify_by_dscp` | Change a named classifier's match definition | R `classifier_name`, `dscp_values`; decide replace/add semantics before assigning aliases; classifier is not optional |
| `configure_scheduler` | Scope scheduler to a known policy/class relationship | R `scheduler_name`, `forwarding_class`, `bandwidth_bps`; V queue/mapping references; O `scheduler_priority` where supported |
| `configure_shaping` | Initial scope: explicit interface attachment | R `interface`, `rate_bps`, `direction`; V policy/treatment identifiers; O `burst_bytes` only on supported profiles |
| `configure_policing` | Separate from shaping with explicit excess behavior | R `interface`, `rate_bps`, `exceed_action`, `direction`; V policy/treatment IDs and burst requirements |
| `apply_qos_policy_to_interface` | New policy attachment | R `policy_name`, `interface`, `direction`; check policy type, attachment capability and existing binding |

The proposed list alone does not define classifier -> treatment -> scheduler ->
policy relationships. Use fixed typed `policy_terms[]` references or propose an
explicit association operation for approval; do not silently invent either those
links or vendor-local object names. Required treatment identities must appear in
the support-profile manifest and registry before activation.

This matters because Junos CoS uses classifiers, forwarding classes, queues and
scheduler maps in distinct roles; a single Cisco-shaped policy abstraction cannot
be assumed equivalent without a reviewed translation contract.
[Junos CoS packet-processing model](https://www.juniper.net/documentation/us/en/software/junos/cos/topics/concept/packet-flow-cos-process-cos-config-guide.html)

Prefer integer base units: bps and bytes. Proposed DSCP values are integers 0-63;
operation/profile rules must establish supported subsets, queue IDs, rate ranges,
burst rules and direction. Never infer units from a bare number, confuse bytes
with bits, or describe a rate setting as guaranteed application performance.

## 7. Template Strategy

Keep the existing source convention:

```text
data/templates/<vendor>/<canonical-category>/<canonical-operation>/template.j2
```

For example: `data/templates/cisco/interface/configure_access_port/template.j2`.
The shorter examples in the proposal are naming illustrations, not a second
template layout. Explicit bindings remain authoritative for compatibility; a
directory or filename does not itself enable support.

Rules for expansion:

- One canonical behavior per template; no category-wide mega templates.
- Keep `StrictUndefined`, reviewed standalone assets and explicit input contracts.
  The publisher currently rejects template include/import/extends; do not propose
  macro inheritance without a separate justified change.
- Optional-field branches are appropriate, but "conditionals only for optional
  parameters" is too literal: required `admin_up=false` still needs a deterministic
  rendering branch. Permit small enum/boolean formatting branches and list loops;
  prohibit operation selection, missing-value inference, context discovery or
  safety-policy decisions inside Jinja.
- Only null optional defaults are supplied by the binding. A schema `default`
  is not permission to fabricate user intent. Intrinsic constants of a clearly
  named operation, such as the destination of `add_default_route`, are different.
- All top-level inputs must match the compiled contract, including fields unused
  by one vendor. New derivations require reviewed handler code and tests; do not
  hide complex vendor translation in Jinja expressions.
- Initially declare only verified profile subsets. Retain existing bindings and
  operation versions; bump affected versions when contracts/templates change.
- Verify configuration meaning and mutation scope, not just exact rendered text.
  No template should claim success by producing empty or context-only output.

## 8. Phased Implementation Proposal

Every phase stops for review before the next domain wave. Existing APIs and the
all-task render gate remain. File names below are proposed future changes only.

### Phase 0: Semantic Decisions and Minimal Runtime Readiness

Implementation update (2026-09-28): the code-only readiness revision and decision
record are in `docs/KNOWLEDGE_EXPANSION_PHASE_0.md`. No expansion data or release
was activated. Live-model benchmarking is pending model availability; Phase A
still requires separate approval. The original proposal below remains the scope.

**Deliverables:** canonical operation/disposition matrix; support matrix including
hardware scope; parameter/type/alias decisions; first golden prompt set; bounded
list/optional extraction and domain-rule extension work approved explicitly.

**Files:** proposed `knowledge_packs/manifest.json`, domain manifests and tests;
targeted changes to `app/parameters/{parameter_extractor,normalizer,fields}.py`,
`app/knowledge/rule_registry.py`, `app/knowledge/services.py` as needed for handler
registration and normalized alias checks. Number parsing is optional if all new
quantities use integers. Add focused tests before changing behavior.

**Services:** extraction, validation-handler dispatch, existing knowledge validation;
no category/operation model, database or publication redesign.

**Migration:** none initially; export baseline, preserve active pointer and asset
hashes, classify every requested operation as reuse/new/needs-definition/profile-limited.

**Validation:** primitive arrays, nested object evidence, optional descriptions,
false/zero preservation, forged values and range/unit ambiguity; retain 168-test
baseline plus new regressions. Benchmark small-model candidate/argument accuracy
with a small fixed prompt set rather than relying on test counts alone.

**Rollback:** restore only this approved code patch and rerun compatibility tests;
no catalog was published. Do not reset unrelated working-tree changes.

### Phase A: VLAN Objects

**Deliverables:** preserve create/delete; add narrowly reviewed modify/rename
behavior only on profiles with proven identifiers/reference semantics.

**Files:** `knowledge_packs/vlan/{manifest,changes}.json`, domain prompt/golden
fixtures; applicable `data/templates/<vendor>/vlan/<operation>/template.j2`;
`tests/test_vlan_knowledge_pack.py`; optional named no-op/rename safety handlers.

**Services:** management apply/preview/validate/publish; existing compiler and
bindings. Shared description/status membership is added through service changes.

**Migration:** rehearse package against an export; create new records inactive with
complete contracts, then activate approved rows in a coherent batch. Existing
contract changes require version bumps across mapping/rule/template records.

**Validation:** VLAN IDs, names, no-change modification, rename collisions,
identity mismatch, Juniper deletion name requirements and original outputs.

**Rollback:** before publication, compensate draft edits; after publication, retire
new operations or restore previous behavior in a higher version and republish.

### Phase B1: Existing Interface and Switchport Operations

**Deliverables:** new Interface category, description/admin-state/access/trunk/list/
native-VLAN behaviors; reuse existing IP assignment without moving its identity.

**Files:** `knowledge_packs/interface/`, applicable interface Jinja assets,
`tests/test_interface_knowledge_pack.py`; scoped extensions to
`app/devices/context_validator.py`, `app/context.py`, `app/questions.py` and
`app/parameters/normalizer.py`; bounded discovery changes in
`app/retrieval/category_classifier.py` / `app/pipeline.py` only if cross-domain
paraphrase tests demonstrate the need. Reviewed inventory/planned fixtures are
changed explicitly, never bulk-labelled capable.

**Services:** shared membership, existing field questions, capability checks,
operation discovery and publication.

**Migration:** add approved memberships and service-managed context rules; keep
all original six categories and IDs; disambiguate legacy aliases before activation.

**Validation:** valid/invalid physical interfaces, mode/capability, list parsing,
add versus replace, explicit false, retained optional description, VLAN-keyword
paraphrases, unsupported profiles and incorrect target vendor.

**Rollback:** retire only new Interface operations and republish; existing IP
operations remain untouched; revert any reviewed sample-context change with its
own revision and invalidate affected sessions.

### Phase B2: Logical Interfaces and Aggregation

**Deliverables:** loopback and bounded port-channel operations after creation and
membership semantics are approved; no new execution or topology subsystem.

**Files:** remaining interface pack/templates/tests; approved allowlisted context
rules plus `context_validator.py`/`context.py` extensions for logical targets and
member lists; typed local facts/fixtures for naming and hardware capability.

**Services:** operation-scoped create/reference validation and existing publication.

**Migration:** add only profiles with reviewed naming/resource rules; add explicit
planned facts where authoritative. If request-local create/use chains are allowed,
pass validated proposed resources to the existing plan validation step without
changing inventory or claiming the device was configured.

**Validation:** nonexistent physical port remains rejected; valid new logical
target is accepted only by its creation operation; collision, duplicate member,
cross-device member and incompatible aggregate cases block rendering.

**Rollback:** retire unsupported new creation operations and republish; never
delete physical inventory or assume an inverse device configuration was executed.

### Phase C: Routing Expansion

**Deliverables:** default/floating routes; separate reviewed OSPF behaviors;
preserve BGP/IS-IS and original OSPF/static/IP operation contracts.

**Files:** `knowledge_packs/{static_routing,ospf}/`, corresponding vendor Jinja
assets, `tests/test_routing_knowledge_pack.py`; scoped network/prefix/OSPF handlers
and existing normalizer updates for metric-versus-preference disambiguation.

**Services:** management, rule dispatch, per-device context validation and compiler;
no routing engine, topology inference or packet forwarding simulator.

**Migration:** equivalent add/delete names remain aliases to existing canonical
operations. New compound-sensitive operations receive distinct aliases. Add
approved routing memberships, source/policy facts and exact supported bindings.

**Validation:** default-route meaning, exact next-hop deletion, explicit route
preference, backup-route claims, network-prefix canonicalization, process/area
requirements, router-ID scope and redistribution missing-policy rejection.

**Rollback:** forward compensating versions for changed legacy behavior; retire
new routing operations as required. Never lower operation versions or revive a
retired operation by simply pointing to an old release.

### Phase D1: ACL

**Deliverables:** one explicit IPv4 ACL family and reviewed template profiles,
complete typed rule matching, exact rule mutation and attachment validation.

**Files:** `knowledge_packs/acl/`, ACL Jinja assets and golden cases,
`tests/test_acl_knowledge_pack.py`; new code-reviewed ACL handlers under the
existing parameter validation boundary; targeted composite-key and reference
checks in `app/context.py`, `app/pipeline.py` and published context policies.

**Services:** new registry data through existing management; extended domain checks
and typed resource identity. Existing publisher validates new context policy shape.

**Migration:** approved parameter types and memberships first, complete inactive
operations second, templates/support/reference facts third, then reviewed activation.
Keep incomplete security contracts outside the publishable draft.

**Validation:** absent matches never become permit-any; invalid prefixes/ports,
protocol-port mismatches, rule collisions, full replacement, unknown ACL references,
cross-ACL same-rule-ID isolation, attachment direction and CLI injection attempts.

**Rollback:** retire affected ACL operations and publish a compensating release;
preserve published identities/audit. This changes the generator, not deployed ACLs.

### Phase D2: QoS

**Deliverables:** reviewed DSCP classifier, scheduler/treatment and attachment
contracts with explicit references and units; profile subsets rather than a
fictional universal policy syntax.

**Files:** `knowledge_packs/qos/`, profile-reviewed QoS templates/golden cases,
`tests/test_qos_knowledge_pack.py`; reviewed unit/list/cross-field validators and
local policy-reference facts. Add only justified handlers to the existing registry.

**Services:** parameter validation, reference checks and existing publication;
no application identification, bandwidth optimization or monitoring integration.

**Migration:** approve classifier-policy-scheduler relationships before creating
active operations. Batch all required nested parameter definitions, memberships,
rules and reference records consistently; no orphan classifiers or policies.

**Validation:** DSCP ranges, exact rate/burst units, shaping versus policing,
missing exceed action, missing links, absent queue support, direction/capability
and interface-policy replacement scope; typed nested custom answers remain usable.

**Rollback:** retire newly affected QoS operations, restore behavior through higher
versions, republish, and require old-session revalidation.

### Shared Release and Rollback Procedure

For every wave: rehearse -> diff/dry-run -> reviewed apply -> schema/context/
template tests -> full validation -> indexed publication -> smoke prompts.
Publication is whole-catalog and can fail because of any incomplete draft.

Capture the pre-wave catalog export, active release, reviewed assets and separate
inventory/planned context revision. Exports do not include all asset contents.

- A failed publication already keeps the previous release active; diagnose the
  staged failure before retrying and do not manually patch compiled artifacts.
- An unpublished draft can be corrected through services; remove references before
  deleting never-published rows. Whole-catalog import is only appropriate after
  accounting for matching asset hashes and unrelated intervening edits.
- After publication, use a **forward compensating release**: retire newly unsafe
  operations, retain published identities, and restore old behavior under higher
  contract versions where needed. The existing CLI has no general rollback command.
- Do not simply import an old lower-version bundle or switch `active.json` back:
  version/deletion rules can reject the former, and the latter can bypass retirement.
- Local inventory/planned facts are separately revisioned and not included in
  catalog publication; restoration requires explicit coordinated context review.
- These steps roll back knowledge generation only, never network-device state.

## 9. Testing and Acceptance Strategy

| Area | Required Cases / Pass Condition |
| --- | --- |
| Category creation | Existing VLAN is reconciled, not duplicated; new Interface/ACL/QoS are created once; BGP/IS-IS remain active and unchanged |
| Parameter reuse | One `vlan_id` definition serves VLAN and Interface membership; conflicting meanings never share a generic definition |
| Required isolation | Changing one operation's `required` flag leaves siblings unchanged, including nested fields and vendor overlays |
| Alias integrity | Duplicate/normalized aliases, OSPF process phrases, static-route aliases and IP assignment aliases cannot create duplicate executable behaviors |
| Schema generation | Shared type + mapping + rules -> generated schema -> rejection/acceptance boundaries; unknown keywords/handlers fail |
| Extraction | Primitive lists, ranges, units, nested objects, optional fields, false and zero; invented/ambiguous values stay unresolved |
| Clarification | One active field; suggestions only from allowed schema/context; custom answers validated; wrong units/negative values/invalid enums rejected |
| Device context | Wrong vendor, unsupported port mode, nonexistent physical interface, narrowly approved logical creation, member compatibility |
| Multi-intent targeting | Two operations on two devices versus two on one/one on another; parameter values and corrections do not leak between bindings |
| Resource identity | Same ACL/rule conflicts appropriately; different ACLs with same rule number do not; unmet policy references block without inventing prerequisites |
| Rendering | Each supported binding produces expected nonempty configuration; optional omission and false values work; unsupported profile has no fallback template |
| Publication | Index/schema/template release IDs agree; failed compile/index leaves old release; old sessions revalidate; dry-run never commits |
| Reapplication/recovery | Already-matching package is reported unchanged, conflicting revision rejected, unrelated records preserved, compensating release rehearsed |
| Regression | Original 12 operations/36 bindings remain compatible unless a separately approved correction intentionally changes one |

Keep fast parser/schema/management tests independent of model availability; use
temporary projects and never publish concurrently with source-mode compatibility
tests. Add a small, separately invoked live local-model prompt evaluation measuring
operation selection, device binding, field accuracy, safe clarification and latency.
No average accuracy score may hide a wrong-device or silent-destructive-scope case.

For template approval, record the exact device model/NOS profile, authoritative
command references and lab syntax/behavior evidence. Golden strings alone are not
vendor certification. The reference documents in this review illustrate semantic
differences; they do not certify all currently declared lab profiles.

## 10. Risks and Mitigation

| Risk | Mitigation |
| --- | --- |
| Treating data coverage as domain competence | Gate activation on end-to-end prompt, context, schema and rendering tests |
| Duplicate canonical operations | Publish one owner/ID mapping before creating records; preserve existing aliases unless explicitly migrated |
| Broad delete/modify semantics | Exact selectors, explicit replace/add semantics, no implicit wildcards; complete replacement contracts where prior state is unavailable |
| Under-specified vendor abstractions | Declare supported subsets, review meaningful behavior, never substitute context-only templates |
| Optional data silently lost or arrays rejected | Phase 0 regressions and evidence-preserving parser fixes before dependent operation packs |
| False confidence in planned state | Distinguish confirmed facts, candidates and proposed same-request resources; no discovered-state claim |
| Registry grows beyond weak-model prompt budget | Measure prompt/document sizes and retrieval quality per wave; bounded candidate/context selection only if measured limits require it |
| New handlers weaken safety | Mandatory legacy safeguards remain; new handlers allowlisted and tested; no dynamic imports/uploaded Python |
| Partial expansion blocks publication | Rehearse packs separately and commit only coherent publishable batches |
| Rollback revives unsafe behavior | Compensating forward release, retained identities and session revalidation |
| Database/JSON confusion | Only management writes the selected SQLite authority; pack JSON and seed files are not parallel live stores |
| Scope creep | No GUI, new backend persistence architecture, Ansible, execution, topology or high-level business-intent solver in this expansion |

## 11. Approval Checklist

- [ ] Approve Option B: reviewed packages through existing management services.
- [ ] Confirm the 38-operation list is the scope; provide any separate expansion
  document if it contains additional requirements not in the current request.
- [ ] Preserve legacy IDs/categories, BGP and IS-IS; accept nine physical categories
  initially rather than deleting/moving existing knowledge to force exactly six.
- [ ] Approve Interface as owner of access/trunk/native-VLAN behaviors and the
  reuse of existing static-route/IP operations instead of duplicate records.
- [ ] Approve explicit add/replace/delete scopes, ACL full-rule replacement, and
  no-op modification rejection; identify any required alternative semantics.
- [ ] Approve proposed shared identities/types/base units and the reviewed
  correction of `metric` versus `preference` ambiguity.
- [ ] Select the first exact vendor/platform/hardware/OS profiles per domain;
  accept unsupported bindings where equivalence or facts are not established.
- [ ] Approve the bounded Phase 0 parser/handler extensions and later scoped
  creation/reference/composite-resource checks, with no core architecture rewrite.
- [ ] Decide whether same-request create/use chains are in the first scope or must
  be rejected pending confirmed planned-resource evidence.
- [ ] Approve the QoS object relationships and treatment identities before QoS
  activation; do not leave these implicit in templates.
- [ ] Approve phase-by-phase review gates, indexed release checks, compensating
  rollback and domain/template acceptance evidence.

**Recommended first implementation authorization:** Phase 0 readiness work and
Phase A VLAN reviewable pack only; stop for review before Interface expansion.
The preceding recommendation and unchecked items describe the original review.
Subsequent authorization and current staged implementation are recorded at the
top of this document; the checklist is not evidence of live activation approval.
