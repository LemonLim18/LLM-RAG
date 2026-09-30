# Knowledge Backend: Phase 1 Handoff

Date: 2026-09-27

Status: Phase 1 implemented and verified. Stop here for review before Phase 2.

Historical checkpoint: Phase 2 was subsequently approved and implemented. Read
[KNOWLEDGE_PHASE_2.md](KNOWLEDGE_PHASE_2.md) for current capabilities and the new
review boundary before Phase 3. The rest of this note records Phase 1 only.

## What Changed

The existing catalog now reads through a small, read-only knowledge layer:

```text
Existing planner / extraction / questions / schema and template loaders
    -> app/catalog.py (unchanged public functions and dictionary payloads)
    -> KnowledgeService (typed reads, active filtering, metadata integrity)
    -> KnowledgeRepository protocol
    -> FileKnowledgeRepository (cached JSON reads, typed validation, copies)
    -> Existing categories.json / parameters.json / operations.json
```

- `app/knowledge/models.py`: Pydantic `Category`, `ParameterDefinition`, and
  `Operation` records, using the already-installed dependency.
- `repository.py`: read-only storage contract, independent of paths and runtime
  inventory/template concerns.
- `file_repository.py`: per-instance cache, validation with file/record context,
  defensive copies, and explicit cache clearing.
- `services.py`: list/get operations, active-operation filtering, duplicate-ID
  checks, operation alias ownership, and operation-category reference checks.
- `app/catalog.py`: compatibility facade; existing schema, parameter-type,
  vendor-required-field, and template checks remain here.
- `app/config.py`: names the existing catalog directory; resolved file paths
  are unchanged.
- `data/catalog/migration_manifest.json`: pending domain decisions and the
  compatibility policy. It does not import or activate new operations.

## Preserved Contracts

JSON remains authoritative. The original six categories, 12 operations, 20
parameters, operation schemas, and 36 vendor templates were not edited.

All existing public catalog function signatures remain available. List/get
functions still return dictionaries/lists, not Pydantic objects. Dictionary
values, ordering of records/aliases, and omitted optional keys are preserved.
Missing operation status/version still mean active/version 1 internally; the
facade does not insert those keys into legacy records that omitted them.
Inactive operations remain excluded by default and unavailable through
`get_operation()`. Missing lookups retain their `KeyError` contract.

Existing schema requirements, vendor overlays, literal operation matching,
parameter extraction, inventory checks, clarification/session behavior, and
the request-wide render gate are unchanged. No new model calls are introduced.

New metadata validation rejects malformed records early: IDs must be lowercase
snake-case identifiers beginning with a letter; labels/alias entries must be
nonblank strings; versions must be positive integers, not booleans or numeric
strings; status remains active/inactive. Parameter types use JSON Schema type
names, not the incomplete target document's `enum`/`list` shorthand.

Unknown extension metadata is preserved for compatibility but has no new
operational meaning. Shared definitions still do not define required fields or
operation validation rules. Those remain in the existing operation schemas.

Typed record fields are frozen against direct assignment. Nested metadata on
returned copies is caller-owned and cannot mutate the cache. This is not a
database immutability or authorization mechanism: manual JSON edits are still
possible and must follow the stable-ID policy.

## Editing and Reloading

Keep the existing editing workflow: edit the JSON, call
`app.catalog.reload_catalog()`, validate the catalog, and rebuild retrieval when
operation metadata changes. `pipeline.run()` already reloads and validates.
No new setup, package installation, database, or data migration is required.

The repository caches reads until reload, just as the old facade did. A bad file
after reload raises an error instead of falling back to an old valid record.
Fixing the file allows a subsequent read to recover. This is not atomic
multi-file publication or a concurrent authoring service; those are later work.

The migration manifest is a review checklist, not a second source of truth.
Keep its missing types, undefined parameters, overlapping behaviors, naming
conversions, destructive-operation semantics, and vendor exceptions unresolved
until reviewed. Do not synthesize missing definitions from parameter names.

The existing source fingerprint includes every JSON file under `data/`, including
this new manifest. Its addition or edits can require existing sessions to
revalidate; separating draft/reference changes from published runtime knowledge
is deferred to Phase 4. No session is silently migrated by this change.

## Verification

Using the existing root `.venv` interpreter, from the V2 directory:

```powershell
& ..\..\.venv\Scripts\python.exe -m unittest discover -s tests -p test_knowledge_repository.py -v
& ..\..\.venv\Scripts\python.exe -m unittest discover -s tests -q
```

- Baseline before changes: 62 tests passed.
- New focused tests: 16 passed.
- Full suite after changes: 78 passed.
- Focused checks compare every original catalog record with the public facade,
  all 12 operation schemas against legacy raw reads for unresolved, individual,
  and combined device profiles, and all 36 vendor template paths.
- Cache reload/isolation, strict metadata validation, duplicate IDs, alias
  conflicts, inactive filtering, and label propagation are covered. The existing
  suite still checks clarification regressions and smoke-renders all templates.

These checks do not measure live local-model accuracy, certify vendor CLI, or
prove production readiness. No live-model or vendor-device integration test was
performed.

## Remaining Work

1. Phase 2, only after approval: category-parameter membership, explicit nested
   reference reconciliation, and reviewed shared definitions. Preserve BGP,
   IS-IS, and existing OSPF interface-object representation.
2. Phase 3: explicit operation parameter mappings and rules, compared with
   existing schemas before changing their authority.
3. Phase 4: schema compilation, per-operation template support, consistent
   knowledge snapshots, staged retrieval publication, and session migration.
4. Phase 5: management writes/CLI, transactional authoring storage, and API-ready
   contracts. No frontend is part of this sequence yet.

Known issues intentionally left for their planned phases include flattened
nested schema-name checking, hardcoded schema titles resisting central label
edits, global template support, and delete-before-rebuild retrieval indexing.
There is no new CRUD service, membership registry, compiler, release system,
database, API server, or operation expansion in Phase 1.

Read [the evolution plan](../Implementation_Plan/INTENT_KNOWLEDGE_EVOLUTION_PLAN.md)
for the next phase and [the manifest](../data/catalog/migration_manifest.json)
for decisions that must not be guessed. Do not begin Phase 2 without review.
