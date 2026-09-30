# Knowledge Backend: Phase 4 Handoff

Status: implemented. This note records the original JSON-authoritative Phase 4
milestone. The [completion audit](KNOWLEDGE_EVOLUTION_COMPLETION.md) supersedes its
authority/activation/test status: Phase 5 now includes SQLite and indexed releases.

## Authority and Compatibility

The existing 12 operations now declare `schema_source: registry` and
`mapping_mode: none`. JSON remains authoritative: shared parameter types plus
operation mappings/rules compile the schema. Existing `schema.json` files are
retained migration evidence, not editable runtime authorities for these operations.
Unmigrated `legacy` / `compare` records retain the earlier behavior.

Operation IDs, payload keys, vendor requirements, nested OSPF structure, parameter
provenance, terminal questions, and public `load_schema()` / `render()` signatures
are preserved. No templates were rewritten or new production operations enabled.

## Implementation

- `schema_compiler.py` reconstructs object/array contracts with ordered required
  flags and vendor overlays. Unknown rules/formats, incompatible keyword types,
  missing items, unreachable nodes, and invalid parameter membership fail closed.
- `rule_registry.py` exposes named, code-reviewed handlers for existing network
  values, duplicate interfaces, safe strings, and derived netmasks. No catalog
  Python imports or executable validator uploads are supported.
- `template_bindings.json` explicitly binds all 36 current operation/vendor
  templates to operation versions, platforms, exact OS versions and input
  contracts. New operations may support only a reviewed subset of vendors.
  Optional template inputs may receive null, never invented configuration values.
- `publication.py` validates JSON, compiles schemas, checks standalone Jinja
  inputs, stages templates/documents, builds a new release-specific Chroma
  collection, then atomically replaces `active.json`. Old indexes are not deleted.
  A failed validation/index build or changing source leaves the previous release
  active. Contract/template/category changes require an operation version bump.
- `runtime.py` pins catalog metadata, schemas, context policies, templates, and
  retrieval to one release per request. Hash checks detect changed artifacts.
  Inventory and planned-data revisions remain separate live context checks.
- Plans/tasks persist `knowledge_snapshot_id` and `context_revision`. Old session
  fields still load. Resume revalidates against the current release; stale answers
  and retired operations cannot reuse old artifacts. Retained releases are for
  audit, not a bypass around retirement.
- The all-task render gate, staged configuration outputs, and `StrictUndefined`
  remain. A release/context change during rendering returns no partial configs.

## Publish and Run

From the V2 directory with the existing environment:

```text
python -m app.knowledge.migration --compare
python -m app.knowledge.publication --verify-legacy
python main.py
```

The initial publication checks retained legacy contracts. `python -m app.ingest`
now publishes a complete indexed release rather than replacing the old index.
Subsequent reviewed schema changes should not be forced to equal legacy evidence.

For a deliberate local run without embeddings:

```text
python -m app.knowledge.publication --offline --verify-legacy
```

An offline release declares retrieval unavailable. Literal catalog operations and
clarification remain available; semantic retrieval never silently uses an older
index. No real release was activated during development verification: tests use
temporary releases. Without an active release the existing direct-source path is
available for literal operation tests, but registry semantic retrieval requires
publication. Management writes require a baseline release to isolate drafts.

## Verification and Limits

The Phase 4 suite passed 130 tests before the later management changes. Focused
coverage compares all 12 effective schemas across unresolved, individual-vendor,
and mixed-vendor profiles, plus all 36 rendered outputs against the original
templates. It checks required/nested validation, independent task blocking,
stale answers, retirement, corrupted artifacts, failed publication, source changes
during builds/renders, and a test-only single-vendor operation through clarification.

Chroma staging is unit-tested using a fake backend; live Ollama/Chroma service
integration and device acceptance are not certified. Index embedding-model names
are pinned, but changes to a model's underlying weights require operator review.
Artifact hashes detect accidental edits, not a malicious administrator rewriting
both manifests and pointers. Old releases and abandoned stages/indexes are retained;
garbage collection and automatic rollback are intentionally not implemented.
