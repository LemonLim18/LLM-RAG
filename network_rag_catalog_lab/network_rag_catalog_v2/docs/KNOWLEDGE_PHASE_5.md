# Knowledge Backend: Phase 5 Handoff

Status: original Phase 5 completed on 2026-09-28, including approved SQLite
authority migration. Earlier JSON-only management is retained for unmigrated
projects. See [completion evidence](KNOWLEDGE_EVOLUTION_COMPLETION.md).
No GUI or HTTP server exists; management is a trusted-local backend.

## Backend Model

```text
CLI / future authenticated API
  -> strict request/result contracts
  -> knowledge management service + dependency/impact checks
  -> selected authoring store: SQLite transactions / JSON before migration
  -> explicit validate / preview / publish
  -> immutable Phase 4 runtime release
  -> existing intent, clarification, validation and rendering pipeline
```

- `app/api/contracts.py`: typed edit/import/publication envelopes, entity changes,
  complete operation-contract inputs, versioned catalog exports, structured issues
  and results. Results contain `ok`, `revision`, `data`, `issues`, and `warnings`.
- `app/knowledge/management.py`: create/edit/retire categories; create/edit
  parameters; assign/unassign memberships; create/edit/retire operations; replace
  operation mappings/rules/template bindings coherently; preview, validate,
  impact/dry-run, export/import and publication use cases.
- `app/knowledge/document_repository.py`: defensive candidate-document reads
  through the existing repository contract, tested against file-backed reads.
- `app/knowledge/authoring_store.py`: exclusive local writer lock, expected-revision
  checks, atomic replacement of individual JSON files, multi-file journal and
  rollback/recovery. It records actor, reason, before/after contents and revisions.
- `app/knowledge/sqlite_repository.py`, `migrations/001_authoring.sql`: normalized
  identity/relationship tables, foreign keys, transactional catalog and audit
  writes, monotonic generation revisions, typed repository parity and migration.
- `app/knowledge/authority.py`: one explicit backend, selected by
  `storage/knowledge/authority.json`; malformed/missing migrated state fails closed.
- `app/knowledge/cli.py`: JSON request files and JSON results, exit 0 for success,
  1 for rejected operations. Existing `main.py` and public runtime APIs remain.

## First Use

Use the existing environment from the V2 directory. Inspecting or validating does
not require a publication and does not alter catalog contents.

```text
python -m app.knowledge.cli inspect
python -m app.knowledge.cli validate
python -m app.knowledge.cli preview-schema configure_ospf --vendor cisco
```

Before the first management write, publish the reviewed baseline, choosing either
normal indexed publication or deliberate offline mode:

```text
python -m app.knowledge.publication --verify-legacy
python -m app.knowledge.publication --offline --verify-legacy
```

Run only the mode wanted. This workspace already has an activated indexed release
and has been migrated to SQLite. Fresh clones must first publish, then migrate:

```text
python -m app.knowledge.cli migrate-sqlite reviewed-migration.json
```

The migration request contains `expected_revision` from `inspect`, `actor` and
`reason`. Migration validates the complete catalog, stores a JSON backup,
transactionally imports all eight managed documents, verifies equality and then
atomically switches authority. It does not delete JSON seeds or change public
runtime signatures. Existing managers select the new backend on their next call.
After migration, direct managed JSON edits are ignored, and the JSON writer
rejects writes. All authoring changes are drafts until successful publication.

An edit request has this shape, with the revision returned by `inspect`:

```json
{
  "expected_revision": "<current revision>",
  "actor": "senior-engineer",
  "reason": "Clarify category description",
  "changes": [{
    "entity": "category",
    "action": "update",
    "entity_id": "vlan",
    "values": {"description": "Reviewed VLAN operations"}
  }]
}
```

```text
python -m app.knowledge.cli apply reviewed-change.json --dry-run
python -m app.knowledge.cli apply reviewed-change.json
python -m app.knowledge.cli validate
python -m app.knowledge.cli publish reviewed-publication.json
```

Publication requests require `expected_revision`, `expected_release` (null for
initial publication), `actor`, `reason`, and `mode` (`chroma` or `offline`). A stale
draft revision or release ID rejects the request instead of overwriting new work.
`inspect` returns both current values. The optional CLI `--project PATH` precedes
the subcommand and selects another local project root.

## Editing Contracts

Entity/action combinations:

| Entity | Actions | Values |
| --- | --- | --- |
| category | create, update, retire, delete | Category metadata |
| parameter | create, update, delete | Shared definition, no operation rules |
| operation | create, update, retire, delete | Operation metadata |
| membership | assign, unassign | category_id and parameter_id |
| contract | replace | version, mappings, rules, templates |
| context_rules | replace | Complete reviewed context-rules document |

Contract replacement requires all records to use the selected operation ID and
version; use the existing JSON record shapes. It replaces only that operation's
rows in the three catalogs and sets registry authority. Shared metadata changes
do not rename payload keys. `preview-schema` exposes the compiled draft, optionally
with one supported vendor's requirements.

New operations default to inactive. An incomplete inactive draft may be authored
incrementally, with a warning, but cannot be published until completed or deleted.
The current authoring catalog is one draft workspace, not independent draft
branches or partial per-operation publishing. Activation uses an operation update
to `status: active` after its contract/templates are complete and reviewed.

Deletion never cascades. Referenced parameters/memberships/categories cannot be
removed; any previously published identity is retained even after retirement.
Planned-context references also block operation deletion. Retiring a category
requires its active operations to be retired in the same batch or beforehand.
Review impact reports; shared metadata reports all operations conservatively.

## Export, Audit and Recovery

`python -m app.knowledge.cli export` returns a version-1 bundle under `data.bundle`.
Import requests contain `expected_revision`, `actor`, `reason`, and `bundle`.
Use `python -m app.knowledge.cli import reviewed-import.json`. Imports run the same
validation and published-identity protections as edits.

Exports contain managed catalog documents and hashes of the required existing
schema/template assets, not arbitrary executable template uploads. Restore those
assets separately from source control before importing; mismatched assets reject
the import. The migration manifest and inventory/planned data are not management
entities and are not overwritten by imports.

SQLite data, authority marker and original JSON backup are under
`storage/knowledge/`. Audit rows atomically store actor/reason, generation,
before/after revisions and catalog contents. Current normalized tables hold the
current draft version; historical drafts remain in audit snapshots and published
versions in immutable releases. JSON-only projects retain journals under
`storage/catalog_authoring/`. Publication manifests also record actor/reason,
backend and authoring revision. These are not authenticated or tamper-proof logs.
Published requests keep using the previous immutable release during draft edits.

```text
python -m app.knowledge.cli recover
```

SQLite rolls back interrupted transactions on reopening; `recover` checks database
and foreign-key integrity. For JSON, recovery rolls back a prepared transaction or
completes cleanup for a committed one without overwriting unrelated edits.
If migration committed but its final authority switch failed, retry the exact
migration request: only an unchanged, generation-one migration with matching
audit/source records can resume. Unknown or changed databases are never overwritten.
Missing authority/database state requires recovery, never a silent JSON fallback.
A hard process crash may leave
`data/catalog/.authoring.lock`; it records the writer PID. Verify the writer has
stopped before manually removing this lock, then recover. Do not delete journals
or pending markers to bypass recovery. A lock on another host/cloud-sync conflict
cannot be safely diagnosed automatically. If the active release pointer is lost
after cutover, restore a verified pointer or explicitly republish; do not run seed
JSON as production runtime. Local storage and releases are Git-ignored. Back up
the database/marker together while writers are stopped, plus releases and assets;
an exported catalog bundle is portable metadata, not a full runtime/index backup.

## Verification and Remaining Work

Final compatibility run: **168 tests passed**. The
[completion audit](KNOWLEDGE_EVOLUTION_COMPLETION.md) records legacy comparisons,
live checks and activation. Management tests isolate temporary projects and model
responses; source-compatibility tests use retained seed data. Do not run workspace
authoring/publication concurrently with that source-mode verification.

Focused tests cover management lifecycle/dependencies, scoped contract updates,
draft/live separation, previews, strict requests, stale revisions, JSON CLI exit
codes, metadata export/import, repository equivalence, exact-byte rollback,
interrupted writes, and refusal to overwrite external edits. The same nine
management tests run against JSON and SQLite. Additional coverage checks SQL
foreign keys, transaction/audit rollback, authority isolation, migration recovery,
conditional clarification and hashed support-profile schemas. Original runtime
regressions and Phase 4 schema/template comparisons remain in the suite.

Remaining work:

- Validate templates against the actual device/OS combinations. No lab/device
  certification or external execution was performed.
- Review target-document definitions still listed in `migration_manifest.json`.
- Authoring coordination is local/single-host. SQLite is transactional but not a
  multi-host database. Do not synchronize a live database between OneDrive writers.
- New domain semantics still require reviewed schemas, handlers and templates.
  Small-model interpretation accuracy is not guaranteed by this registry.
- Add authentication, authorization, stronger audit retention and operational
  controls before exposing management over a network. No server/frontend,
  Ansible, topology, or external-tool integration was added.
