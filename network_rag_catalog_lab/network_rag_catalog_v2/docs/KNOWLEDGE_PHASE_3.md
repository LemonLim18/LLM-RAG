# Knowledge Backend: Phase 3 Handoff

Historical Phase 3 record. [Phase 4](KNOWLEDGE_PHASE_4.md) now promotes the
reviewed mappings/rules to registry authority; [Phase 5](KNOWLEDGE_PHASE_5.md)
adds JSON-backed management. The comparison-only behavior below describes Phase 3.

## Scope and Authority

The current 12 operations now have 38 explicit parameter mappings and 51
schema-node rule records. These were backfilled from existing schemas, not from
LLM guesses or the incomplete target document. All six categories, 20 shared
parameter definitions, 22 category memberships, operation IDs/versions, original
schema files, and 36 templates remain in place.

Every current operation declares:

```json
{"schema_source": "legacy", "mapping_mode": "compare"}
```

These are additive metadata keys in `operations.json`; old records without them
still default to legacy authority and no comparison. `schema_source="compiled"`
is rejected in this phase. JSON remains authoritative, and the original
operation `schema.json` files remain the ONLY source of runtime requirements,
types, constraints, nested structure, and vendor requirements.

The new files are **comparison records**, not a second executable schema source:

- A coherent candidate edit can produce a comparison difference while runtime
  continues using the original schema. Making a field optional in a candidate
  does not remove the runtime requirement, including during clarification.
- Malformed records, dangling references, duplicate paths, invalid ordering,
  missing comparison files, and stale operation versions fail validation rather
  than triggering automatic repair or promotion.
- When comparison matches, metadata enrichment uses the mapped canonical IDs.
  When it differs, enrichment retains the authoritative schema's IDs. Candidate
  edits cannot redirect parameter identity or inject defaults into task values.

## Data Model

`data/catalog/operation_parameters.json` records:

| Field | Meaning |
| --- | --- |
| `operation_id`, `operation_version` | The current operation version being compared |
| `category_id`, `parameter_id` | An existing category-parameter membership |
| `field_path` | Stable payload path, such as `interfaces[].name` |
| `position` | Zero-based depth-first property order within the operation |
| `required` | Base requirement in the containing object, not a global parameter rule |
| `required_order` | Position in that object's required list; null for optional fields |

An array item's required fields apply within each item. Marking
`interfaces[].name` required does not by itself require the `interfaces` array;
the parent mapping and array rules retain that distinction. Vendor-specific
requirements remain separate from base required flags.

`data/catalog/operation_rules.json` records operation/version, `field_path`, and
`keywords`. Root uses an empty path; anonymous array items use `interfaces[]`.
Keywords retain limits, enums, formats, annotations, `additionalProperties`,
array bounds, and the existing root `x-required-by-vendor` overlay. Named property
types come from shared definitions; root/anonymous-node types remain in rules.
Property structure and ordered requirements are represented by mappings, not
duplicated as `properties`, `items`, or `required` blobs inside rule keywords.

This preserves the important distinction:

```text
configure_ospf / interfaces[].name -> canonical interface
create_vlan   / name              -> canonical name (VLAN name)
```

## Backend Changes

- Typed models/repository/service now expose operation mappings and rules, with
  version, membership, duplicate-path, parent-node, and ordering checks.
- `app/knowledge/operation_contracts.py` projects legacy schemas into comparable
  records and reports differences. It does not reconstruct runtime schemas,
  publish releases, execute templates, or implement a schema compiler.
- `migration.py` provides read-only backfill and comparison commands, including
  inactive operation evidence and global dangling-record checks.
- `schema_loader.py` continues loading the original schema and vendor overlays.
  Central display names now take precedence over stale property titles. Existing
  payload keys and template inputs are not renamed.
- Normalization, field parsing, extraction contracts, and question metadata use
  canonical parameter identity from enriched schema metadata. For example,
  nested interface aliases resolve to payload key `name`, not a new key
  `interface`. Ambiguous aliases or duplicate semantic slots do not get arbitrary
  deterministic bindings.
- Context lookups already use operation-scoped full payload paths and loaded
  schemas, so `app/context.py` needed no rewrite. Pipeline orchestration, runtime
  domain validators, session formats, and the all-task render gate are unchanged.

The service caches only legacy projections, keyed by schema content, operation
category/version, and parameter IDs/types. Candidate records are read/compared
on each call; a changed candidate cannot inherit an old successful comparison.
Reload clears the projection cache, and schema changes also invalidate its key.
This cache is not an immutable publication snapshot or a concurrency mechanism.

## Review Commands and APIs

From the V2 directory with the existing environment:

```powershell
& ..\..\.venv\Scripts\python.exe -m app.knowledge.migration --operations
& ..\..\.venv\Scripts\python.exe -m app.knowledge.migration --compare
```

`--operations` prints proposed mappings/rules without overwriting files.
`--compare` prints per-operation results with `matches` and field-path-specific
legacy/candidate differences. It exits with code 1 on drift; malformed data also
fails. No argument retains the Phase 2 membership-preview behavior. Neither
command imports target-document operations or writes data.

Additional dictionary APIs, alongside all existing catalog functions:

```python
from app.catalog import load_operation_parameters, load_operation_rules
from app.catalog import compare_operation_schema

mappings = load_operation_parameters("configure_ospf")
rules = load_operation_rules("configure_ospf")
# raw_schema is the original JSON, before metadata/vendor enrichment:
report = compare_operation_schema("configure_ospf", raw_schema)
```

Omit the operation ID to list all rows. Inactive operations remain reviewable
without becoming selectable for normal planning. Returned dictionaries are
defensive copies. Existing file-repository constructors still work; the new
optional paths default beside `operations.json`.

For a candidate requirement edit, keep `required` and `required_order` coherent
and update sibling required ordering if necessary. Run comparison and review
the differences; do not assume editing a comparison file changed runtime.
An approved legacy-schema change must still follow governance and be compared
with updated candidate records. Automatic promotion is explicitly deferred.

## Verification

- Before changes: 95 tests passed.
- New focused tests: 18 passed.
- Full suite after changes: 113 tests passed.
- All 12 operation comparisons match their original schemas.
- Independent pre-mapping loader parity covers every operation with unresolved,
  each individual vendor, and combined vendor profiles. Existing clarification
  regressions and all vendor-template smoke tests also pass.
- Focused coverage includes local required-flag edits, nested order/identity,
  vendor/range drift, cache invalidation, duplicate/stale/dangling records,
  read-only previews, comparison exit status, mapped aliases/netmasks,
  central-label propagation, and malformed source markers.

```powershell
& ..\..\.venv\Scripts\python.exe -m unittest discover -s tests -p test_operation_mappings.py -v
& ..\..\.venv\Scripts\python.exe -m unittest discover -s tests -q
```

No dependencies, database, GUI, API server, new network operations, Ansible, or
execution integration were added. No live-model accuracy or vendor-device
certification was performed. Existing source fingerprints include these new
files and markers: saved sessions revalidate on their next interaction, even
for comparison-only edits. Draft/runtime isolation is later publication work.

## Limitations and Next Review

Phase 3 compares the current operation version only; it is not historical-version
storage or a multi-user authoring service. Comparisons are structural projections,
not proofs that a network behavior or Jinja template is correct. Unsupported
legacy references, composed/conditional schemas, type unions, or uncertain
parameter identities block backfill instead of being inferred. Domain parsers
still support the existing operation vocabulary; mapping a novel parameter does
not automatically implement new domain logic.

Phase 4 requires separate approval: compile effective schemas from reviewed
contracts, introduce explicit template bindings and reviewed rule handlers,
publish consistent knowledge/retrieval snapshots, and handle session/version
migration before changing schema authority. The target document's unresolved
types, missing parameters, and overlapping behaviors remain review items.

See [the evolution plan](../Implementation_Plan/INTENT_KNOWLEDGE_EVOLUTION_PLAN.md),
[the manifest](../data/catalog/migration_manifest.json), and
[Phase 2 history](KNOWLEDGE_PHASE_2.md). Stop here before Phase 4.
