# Intent Knowledge Evolution: Completion Audit

Date: 2026-09-28

## Outcome

Phases 1-5 of [the plan](../Implementation_Plan/INTENT_KNOWLEDGE_EVOLUTION_PLAN.md)
are implemented within its backend-only scope. This completes the original SQLite
destination, not merely the earlier JSON-authoritative adaptation. It does not
claim perfect natural-language understanding or certified device configurations.

The existing planner, extraction, inventory resolution, clarification sessions,
validation, retrieval and Jinja renderer remain in place. Public runtime entry
points and existing operation IDs, payload paths and vendor contracts are retained.

```text
Local CLI / future API contracts
  -> management validation, dependency checks and impact report
  -> SQLite draft + transactional audit (JSON adapter before migration)
  -> compile schemas + support-profile artifacts + reviewed template bindings
  -> stage release + build matching Chroma collection
  -> atomic active-release pointer
  -> existing prompt / inventory / clarification / validation / rendering pipeline
```

## Acceptance Evidence

| Phase | Implemented result | Verification |
| --- | --- | --- |
| 1: Catalog foundation | Typed records, read/write repository contracts, stable IDs, defensive readers and compatibility facade | `test_knowledge_repository.py`, `test_catalog.py` |
| 2: Category parameters | 22 explicit memberships across six categories; 20 shared definitions; nested paths resolve explicit identities | `test_category_parameters.py`; OSPF `interfaces[].name` maps to `interface` |
| 3: Operation mappings | 38 mappings and 51 operation rule nodes for 12 operations; independent required flags and centrally published labels | `test_operation_mappings.py`; 12 retained legacy comparisons match |
| 4: Schema publication | Registry compilation, conditional/vendor requirements, allowlisted handlers, 36 explicit template/profile artifacts, immutable releases and matching retrieval; stale sessions revalidate | `test_schema_compiler.py`, `test_knowledge_publication.py`; all 36 legacy rendered outputs compared |
| 5: Management and persistence | Typed requests/results, CLI, lifecycle/dependency checks, previews, atomic edits/audit, foreign keys, stale revisions, import/export, explicit SQLite migration and recovery | Shared nine-test management contract runs against JSON and SQLite; storage and migration regressions |

A test-only `provision_vlan` operation demonstrates definition/mapping/schema ->
missing-field clarification -> rendering without a planner-specific rewrite, and
declares Cisco-only support. No unreviewed production operation was activated.

## Previously Missing

1. The earlier Phase 5 deliberately stopped at JSON management because previous
   instructions required JSON authority. SQLite storage/migrations, foreign-key
   enforcement and file/database behavioral equivalence were therefore absent.
2. Phase 4 applied vendor requirements at load time but did not publish a separate
   hashed effective schema artifact for every declared support profile.
3. Conditional-required rules lacked an explicit reviewed contract connected to
   field-scoped clarification. Object rules now support `dependentRequired` and
   equality-based `x-conditional-required`; invalid references/types are rejected.
4. The interrupted completion run left the database adapter in code, with an
   indexed JSON baseline activated, but no workspace SQLite cutover or final notes.

The resumed work performed the cutover and publication, corrected stale authority
documentation, isolated unit fixtures from live releases/models/transient locks,
and ensured schema comparison uses the request's catalog rather than seed files.
Migration and storage also fail closed on missing authority/database/runtime
pointers; a committed-but-unactivated first migration can resume safely.

## Current Workspace

- Authoring: `storage/knowledge/catalog.sqlite3` (schema version 1).
- Authority selector: `storage/knowledge/authority.json`.
- Original catalogs: preserved unchanged as JSON seeds, with a migration backup
  under `storage/knowledge/json-backup-*.json`.
- Runtime: `storage/catalog_releases/active.json`; completed SQLite-backed indexed
  release `fbd929e928014a4886fbfd69c4019851`.
- Retrieval: `knowledge_fbd929e928014a4886fbfd69c4019851`, built using installed
  `nomic-embed-text`; published receipt verifies all 12 operation documents.
- Audit: SQLite `authoring_audit` stores before/after catalogs and generation;
  release manifests record publication actor/reason and authoring revision.
- Inventory, planned context, and reviewed Jinja source assets remain local files.
  They are not duplicate authorities for the eight managed catalog documents.

Draft edits do not affect runtime until publication. Old sessions must revalidate
against the active release and separately revisioned inventory/planned context.
No configuration was executed on a network device.

## Verification

Final run: **168 tests passed** in 131 seconds using the existing environment
(`python -m unittest discover -s tests -q`). This includes the added conditional
clarification/render-gate regression. `git diff --check` and relative links in all
seven updated overview/handoff documents pass. Read-only comparison against SQLite confirms 12/12 unchanged
legacy contracts. Real indexed publication and semantic retrieval succeeded using
the installed local embedding model; `create_vlan` ranked first for a staff VLAN
creation query.

The preceding interrupted verification had an `AUTHORING_BUSY` failure because
a real workspace publication was running alongside source-mode compatibility
tests. This was the intended lock protection, not a catalog corruption. Temporary
fixtures no longer copy transient authoring locks; the final suite ran without
concurrent workspace authoring and passed. Do not edit/publish seed fixtures while
running the source-compatibility suite.

Live smoke checks used the published SQLite-backed release with local
`qwen2.5:1.5b` available, without mocked model responses:

| Prompt / reply | Observed result |
| --- | --- |
| `Create VLAN 100 named STAFF on R1 and R2` | Ready; separate Cisco/Huawei configuration previews |
| `Configure OSPF on R2` | Missing interfaces/process ID stay null; clarification, no rendering |
| `Create VLAN 20 on the KL core router` | Ambiguous target question, no rendering |
| Reply `the Huawei one` | Resolves R2 and reaches ready |
| `Configure IP address 10.10.10.1/24 on GigabitEthernet1/0/1 on R1` | Invalid interface question; `/24` preserved, no rendering |
| `Create VLAN 20 and configure OSPF on R1; create VLAN 30 on R2` | Correct three operation/device bindings; incomplete OSPF keeps the whole-request render gate closed |

These are bounded integration checks, not a statistical model-quality evaluation.
Deterministic fast paths remain intentional; no claim that every prompt invoked
the model or that a small model now has large-model capabilities.

## Use and Recovery

From the V2 directory, use the existing environment:

```powershell
& ../../.venv/Scripts/python.exe -m app.knowledge.cli inspect
& ../../.venv/Scripts/python.exe -m app.knowledge.cli validate
& ../../.venv/Scripts/python.exe -m app.knowledge.cli preview-schema configure_ospf --vendor cisco
& ../../.venv/Scripts/python.exe -m app.knowledge.cli export
& ../../.venv/Scripts/python.exe -m unittest discover -s tests -q
```

Use [Phase 5 request formats and recovery guidance](KNOWLEDGE_PHASE_5.md) for
edits, imports, publication and migration of a fresh clone. Storage/releases are
Git-ignored: cloning source does not clone this workspace's database, audit or
index. A fresh clone starts from JSON and needs explicit publication/migration.
Do not remove the authority marker to revert storage or edit seed JSON expecting
it to update SQLite. Back up a quiescent database and marker together, plus reviewed
assets/releases; portable catalog export does not include the complete index.

## Deliberate Boundaries

- No GUI, HTTP service, Ansible/execution, topology or external-system adapters;
  the plan explicitly excludes them.
- Authentication/authorization and stronger operational controls are required
  before network exposure. Local actor names are not authenticated identities.
- SQLite is single-host authoring, not multi-host/cloud-sync coordination. Avoid
  concurrent writers against a live database synchronized through OneDrive.
- Review the unresolved domain definitions in `migration_manifest.json` before
  adding ACL/QoS/Interface behaviors. The plan explicitly forbids guessing types,
  merging different semantics or automatically importing the target document.
- Complex new parsing/domain rules still need reviewed handlers and tests;
  arbitrary JSON Schema composition and uploaded Python are not supported.
- Vendor templates need lab verification on real NOS releases. A complete
  knowledge-management foundation is not proof of production network safety.
