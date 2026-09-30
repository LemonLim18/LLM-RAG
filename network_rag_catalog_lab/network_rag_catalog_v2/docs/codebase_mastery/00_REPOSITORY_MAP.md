# Repository map

Scope: this checkout of `network_rag_catalog_v2`, inspected statically. Runtime truth comes from source, not older design notes. Start with `01_RUNTIME_CALL_GRAPH.md`, then keep this map beside the code. `NETWORK_RAG_RUNTIME` defaults to `files` (`app/config.py:runtime_mode`); `published` is an optional, different read path. SQLite can be authoring authority without being the live runtime source in files mode.

## Where to look

| Path | Role | Edit manually? |
|---|---|---|
| `main.py` | CLI, interactive questions, resume/edit commands | Only for terminal behavior |
| `app/pipeline.py` | Orchestration, task state, validation/render gate | Only for engine behavior |
| `app/planner/` | Split a request into operation clauses and task dataclasses | For intent-scoping behavior |
| `app/retrieval/` | Category classification, Chroma candidates, bounded operation selection | For retrieval/selection behavior |
| `app/parameters/` | Schema loading, extraction/evidence, normalization, field parsing, validation | For generic parameter behavior |
| `app/devices/` | Inventory, target query/resolver, interface and device/resource policies | For target/policy engine behavior |
| `app/questions.py`, `app/clarification.py` | Question contract and durable sessions | For clarification behavior |
| `app/templates/` | Binding/path selection and Jinja rendering | For rendering engine behavior |
| `app/catalog.py`, `app/file_runtime.py`, `app/context.py` | Catalog facade, direct-file validation/index documents, planned/inventory context | For behavior; data is elsewhere |
| `app/knowledge/` | Typed catalog, repositories, schema compiler, management, publication, release runtime, pack tooling | For knowledge backend changes |
| `app/api/contracts.py` | Backend request/response models, not an HTTP server | For future API contracts |
| `app/config.py`, `app/llm.py`, `app/embeddings.py`, `app/vectorstore.py`, `app/ingest.py` | Paths, Ollama, Chroma access and ingestion | For model/index configuration |
| `data/catalog/*.json` | Direct-mode operation/category/parameter/rule metadata; some also seed/compatibility data for publication | Yes in direct mode; **not** as a substitute for SQLite management writes |
| `data/operations/<category>/<operation>/schema.json` | Direct-mode operation schema; legacy comparison asset in publication | Yes in direct mode; generated compiled schema is elsewhere |
| `data/templates/<vendor>/<category>/<operation>/template.j2` | Reviewed source templates | Yes, followed by direct reindex or publish as appropriate |
| `data/inventory/devices.json`, `attributes.json` | Device facts and target attribute vocabulary | Yes; inventory is a local stand-in for a source of truth |
| `data/planned/parameters.json` | Planned candidate/fact/assignment records | Yes, with care for source/revision fields |
| `knowledge_packs/` | Staged/reviewed expansion inputs; not automatically live | Only when curating a pack |
| `storage/chroma/` | Generated vector indexes | No; regenerate through `app.ingest`/publication |
| `storage/sessions/` | Generated clarification session JSON | No normal manual editing |
| `storage/catalog_releases/` | Immutable published snapshots plus `active.json` | No; publication owns this |
| `storage/knowledge/` | Authoring SQLite database/authority marker when initialized | No raw edits; management service owns this |
| `tests/` | Focused behavioral and compatibility tests | Yes when behavior changes |
| `docs/`, `Implementation_Plan/`, `tools/` | Notes/plans, operational helpers | Not runtime authority; verify against source |
| sibling `network_rag_catalog/` | Earlier prototype, useful historical comparison | Not part of v2 runtime |

## Source -> derived -> runtime

```text
FILES MODE (default)
data/catalog + data/operations/schema.json + data/templates
    -> app/file_runtime.file_documents -> app.ingest.ingest_files
    -> storage/chroma/network_operation_catalog
    -> app.catalog / schema_loader / template_selector / vectorstore

PUBLISHED MODE (NETWORK_RAG_RUNTIME=published)
management API/CLI -> SQLite authoring (or JSON authority in unmigrated copies)
    + reviewed schema/template source assets
    -> schema_compiler + publication validation
    -> immutable storage/catalog_releases/<id>/ + knowledge_<id> Chroma
    -> active.json -> KnowledgeSnapshot -> runtime reads

Both modes also read local inventory and planned context from data/.
```

The split matters: the currently present `data/catalog/template_bindings.json` participates in the publication backend, but `template_selector.template_binding` returns `None` in files mode and `select_template` uses the directory convention. `schema_loader.load_schema` similarly reads `schema.json` in files mode and release artifacts in published mode. Do not assume an edit to one path updates the other.

## Five trace maps

- Control: `main.main -> clarification.create_session -> pipeline.run -> ...`.
- Data: `OperationIntent -> PlannedTask -> ExecutionPlan -> ClarificationSession`.
- Knowledge: catalog ID -> schema -> context rule -> vendor template, with source mode recorded.
- State: source revision, task revision, confirmations, accepted candidates, session JSON, release pointer.
- Failure: unresolved operation/target/value, invalid device context, cross-task conflict, rendering failure.

For the causal history, see the existing root `../../00_REPOSITORY_AND_DATA_MAP.md`; its chronology includes architectural inferences where Git cannot prove motive. The rest of this set documents current code first.
