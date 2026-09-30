# Catalog Governance

Exactly one backend owns authoring: JSON before migration, SQLite afterward.
This workspace is migrated. Stable IDs identify meaning; change display labels
instead of IDs. See the [completion audit](KNOWLEDGE_EVOLUTION_COMPLETION.md) and
[Phase 5](KNOWLEDGE_PHASE_5.md) for management request formats and recovery.

## Authority

- Shared parameter definitions own identity, type, label, aliases and clarification
  text. They contain no operation required/optional flags or validation policies.
- Category membership is only category/parameter ID pairs.
- Registry operations use operation-specific mappings, ordered required flags,
  nested rule nodes and vendor overlays. The compiler derives JSON Schemas.
- Existing per-operation schemas remain migration evidence. Legacy-authority
  operations retain their earlier behavior; migrated operations do not read these
  files as validation authorities.
- Template bindings declare the operation version, vendor/platform/OS support and
  inputs. A file existing on disk does not enable support or certify device syntax.
- Published releases freeze metadata, contracts, context policies, templates and
  retrieval. Inventory/planned data remain separately revision-checked facts.

## Local Management

Publish a reviewed baseline before management writes. Use
`python -m app.knowledge.cli inspect` to obtain the current revision, then submit
strict edit requests with `expected_revision`, `actor`, `reason` and `changes`.
Dry-run reports impact without changing files. Batch related changes together;
do not update contract versions one file at a time through separate requests.

Supported operations include category/parameter metadata edits, memberships,
operation lifecycle, scoped contract replacement, context-policy replacement,
schema previews, validation, export/import and explicit publication.

Deletion never cascades. Referenced definitions and memberships cannot be removed;
previously published identities cannot be deleted. Retire operations/categories
instead, then publish. Retiring a category requires retirement of active children.
An incomplete inactive operation can be authored incrementally but blocks full
publication until completed or deleted. Do not automatically import unresolved
target-document definitions from the migration manifest.

## Add or Change an Operation

1. Review behavior and assign a stable operation ID and owning category.
2. Define/reuse typed parameters and expose them through category membership.
3. Create an inactive registry operation; author its mappings, rule nodes and
   explicit template bindings. Paths are full payload paths such as
   `interfaces[].name`, not flattened bare keys.
4. Keep parameter IDs/types separate from operation policy. Use
   `x-required-by-vendor` for reviewed vendor requirements. Named handlers are
   code-reviewed allowlisted functions, not uploaded Python.
   For conditional fields, object rules support `dependentRequired` and
   `x-conditional-required: [{"field": "vlan_id", "equals": 20, "required": ["name"]}]`.
   References are local object properties; missing values produce field questions.
   Arbitrary schema composition or uploaded validation code remains unsupported.
5. Add reviewed standalone Jinja assets under `data/templates/`. Declare exact
   supported profiles and complete input contracts. Optional nulls do not authorize
   invented values; keep StrictUndefined and all-task validation gates.
6. Define approved lookup fields and conflict resource keys in
   `context_rules.json`. Do not expose unrelated inventory facts as configuration.
7. Preview/validate the draft, review affected operations and activate only when
   its contract/templates are complete. Increment the operation version for
   contract, template or category changes; all scoped records must match it.
8. Publish with reviewed revision/release IDs. Indexed publication creates a new
   collection and only activates on successful verification. Offline publication
   explicitly disables semantic retrieval; it cannot reuse stale indexes.

Central labels/aliases propagate through published metadata and retrieval documents
without changing machine IDs or payload keys. Display edits do not require a
schema version bump, but still require publication to change live requests.

## Context and Runtime Safety

Planned records require `id`, `device_id`, `operation_id`, `field`, `value`,
`kind`, `source_ref`, and `revision`. Their `when` clauses scope dependencies.
Candidates are suggestions; intended-assignment conflicts require explicit
confirmation and an approved override policy. Facts cannot be overridden by a
clarification answer. No user answer edits authoritative records.

Old sessions revalidate against active knowledge and current inventory/planned
context. Stale answers, revoked operations and changed interfaces must not reuse
old rendered configurations. Retained releases serve audit, not retirement bypass.

Management writers require a baseline release and a cooperative local lock.
SQLite commits catalog changes and audit rows in one transaction; the legacy JSON
adapter uses recoverable journals. A missing SQLite authority marker/database or
active release must not fall back to seed files. Follow recovery guidance before
removing any stale lock. Audit actor names are not authentication.
Do not run concurrent database writers through OneDrive or multiple hosts. Back
up a quiescent database with its authority marker and reviewed assets separately.

## Review Boundary

No GUI, HTTP server, PostgreSQL integration, Ansible execution, topology
integration or automatic target-document import is included. Review model behavior
and vendor templates in a real lab. Add authentication/authorization and stronger
operational controls before exposing management beyond a trusted local terminal.
