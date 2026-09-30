# Knowledge Backend: Phase 2 Handoff

Status: Phase 2 implemented and verified. Stop for review before Phase 3.

Historical checkpoint: Phase 3 was subsequently approved and implemented. Read
[KNOWLEDGE_PHASE_3.md](KNOWLEDGE_PHASE_3.md) for current capabilities and the review
boundary before Phase 4. The remainder of this note records Phase 2 only.

## What Changed

`data/catalog/category_parameters.json` now declares which shared parameter IDs
belong to each existing category. The 22 memberships come from 38 property
references in the 12 existing operation schemas, including nested fields.

| Category | Shared parameter IDs |
| --- | --- |
| VLAN | `name`, `vlan_id` |
| OSPF | `area`, `interface`, `interfaces`, `process_id`, `router_id` |
| BGP | `description`, `local_as`, `neighbor_ip`, `peer_group`, `remote_as` |
| IS-IS | `interface`, `level`, `process_name` |
| Static routing | `destination`, `next_hop`, `preference` |
| Interface IPv4 addressing | `address`, `admin_up`, `interface`, `prefix_length` |

Membership rows contain only `category_id` and `parameter_id`. Labels, aliases,
types, and clarification text stay in `parameters.json`; required/optional flags,
value restrictions, and vendor requirements stay in the operation schemas.
An unused but registered parameter may belong to a category without being added
to any operation's schema or extraction prompt.

### Backend Changes

- `models.py`: adds strict `CategoryParameter` records. Shared parameter
  definitions now reject known JSON Schema assertion keywords and operation-rule
  fields such as `required`, `minimum`, and `validation_rules`; opaque extension
  metadata is still preserved without gaining runtime meaning.
- `repository.py` / `file_repository.py`: add cached, defensive membership reads.
  The optional fourth file argument does not break existing constructors; its
  default is `category_parameters.json` beside the supplied parameter file.
- `services.py`: adds category membership and joined-definition reads, duplicate
  and dangling-reference checks, category-scoped alias ownership, and schema
  coverage validation. Parameter aliases may repeat in different categories,
  but two different members may not claim the same ID/label/alias within one.
- `migration.py`: adds read-only backfill with operation, schema-file, full
  property-path, canonical-ID, and type evidence. It never writes source files.
- `app/catalog.py`: keeps old APIs and adds dictionary wrappers for the new reads.
  Catalog validation now checks membership coverage using full paths and explicit
  references instead of flattening nested property names.

The concrete nested-field correction is:

```text
configure_ospf: interfaces[].name -> interface (explicit x-parameter-id)
create_vlan:   name              -> name      (canonical property ID)
```

OSPF's `interfaces` stays an array of objects, not a generic string list. A raw
property name and its explicit reference are no longer incorrectly treated as
two independent parameter identities. Type checks use the referenced definition.

## Usage and Editing

Existing runtime calls are unchanged. New read-only queries are available:

```python
from app.catalog import load_category_parameters, parameters_for_category

memberships = load_category_parameters("ospf")  # Pairs of stable IDs.
definitions = parameters_for_category("ospf")  # Current shared metadata.
```

`load_category_parameters()` returns all membership rows. Unknown categories
raise `KeyError`; an existing category with no memberships returns an empty list.
All results are defensive copies. A shared label edit is reflected in every
category's joined definitions after `reload_catalog()`.

For a future approved parameter addition: define its meaning/type centrally,
add reviewed category membership, and separately select it in operation schemas
where needed. Use `x-parameter-id` when a payload key intentionally differs from
the canonical ID. Do not place requirements or rules on a membership row.

`validate_catalog()` checks all operation schemas, including inactive ones,
against the registry before normal pipeline planning or ingestion. Removing a
used membership fails with the operation ID and property path. A missing registry
file fails explicitly; runtime never invents membership from schemas as fallback.

### Read-Only Backfill Preview

From the V2 folder, using the existing environment:

```powershell
& ..\..\.venv\Scripts\python.exe -m app.knowledge.migration
```

This prints JSON containing `memberships` and `evidence`. It can run before a
membership file exists and includes inactive operation references. Output is
deterministic for unchanged inputs and must be reviewed, not automatically
imported. It represents only the schema-used subset: a later reviewed category
may expose additional unused parameters which must not be deleted by a rerun.

Backfill accepts exact registered IDs or explicit `x-parameter-id` references.
It does not infer identity from display names, aliases, similar spelling, or
the target document. Unknown IDs, conflicting types, missing/union types,
ambiguous field paths, unresolved references, conditional/composed schemas, and
other unsupported structures block the preview instead of producing a partial
result. Current support covers explicitly typed named properties, nested objects,
and arrays with explicitly typed items. This is not a general schema compiler.
Mechanical evidence cannot prove that an author chose the semantically correct
ID when two concepts happen to have the same type; that still requires review.

## Compatibility and Verification

The original category, parameter, and operation records, all operation schemas,
and all 36 templates remain unchanged. Existing public signatures, dictionary
payloads, active filtering, cache reloads, device resolution, parameter parsing,
clarification, vendor requirements, and the full-request render gate are retained.
JSON remains authoritative; no new dependencies, database, API server, CRUD,
compiler, or operation expansion were added. No RAG rebuild is needed solely for
these unchanged operation documents.

The existing source fingerprint includes the new registry and manifest edits.
Previously saved sessions revalidate on their next interaction; Phase 2 does not
silently migrate or edit them. Atomic multi-file publication remains deferred.

Verification with the existing `.venv`:

- Before changes: all 78 tests passed.
- New focused coverage: 17 tests passed.
- After changes: all 95 tests passed, including Phase 1 schema/payload parity,
  the existing clarification regressions, and vendor-template smoke rendering.
- Backfill command smoke check: 22 memberships, 38 schema references.

```powershell
& ..\..\.venv\Scripts\python.exe -m unittest discover -s tests -p test_category_parameters.py -v
& ..\..\.venv\Scripts\python.exe -m unittest discover -s tests -q
```

Coverage includes read-only/repeatable backfill, OSPF nested identities, shared
definitions, category-scoped ambiguity, dangling/duplicate pairs, invalid policy
placement, missing memberships, defensive copies/reload, and explicit failure
for unsupported schema structures. No live-model accuracy or vendor-device
integration testing was performed; this is not production certification.

## Remaining Work

1. Phase 3, after review: introduce explicit operation parameter mappings and
   rule records, compare them with existing schemas, and preserve existing
   payload keys. Phase 2's evidence report is not an authoritative operation
   mapping or a change of schema authority.
2. Resolve missing types/parameters and overlapping behaviors in the target
   document before adding new Interface, ACL, or QoS definitions. Existing BGP,
   IS-IS, and the narrower `ip_address` category remain intact.
3. Later phases: schema compilation, template bindings, atomic knowledge/RAG
   publication, session compatibility, management writes, and API contracts.

Hardcoded schema titles can still resist central label edits; global template
support, delete-before-rebuild retrieval indexing, and domain-specific parser
logic remain for their planned phases. Do not begin Phase 3 without approval.

See [the evolution plan](../Implementation_Plan/INTENT_KNOWLEDGE_EVOLUTION_PLAN.md),
[the pending-decision manifest](../data/catalog/migration_manifest.json), and
[Phase 1 history](KNOWLEDGE_PHASE_1.md).
