# Intent Knowledge Backend Evolution Plan

Date: 2026-09-27  
Status: Phases 1-5 implemented, including the approved SQLite authoring cutover (2026-09-28).  
Scope: Existing V2 -> managed intent knowledge -> schema validation -> Jinja configuration generation.

Progress: start with the [completion audit](../docs/KNOWLEDGE_EVOLUTION_COMPLETION.md)
and [Phase 5 handoff](../docs/KNOWLEDGE_PHASE_5.md). Earlier [Phase 3](../docs/KNOWLEDGE_PHASE_3.md),
[Phase 2](../docs/KNOWLEDGE_PHASE_2.md) and [Phase 1](../docs/KNOWLEDGE_PHASE_1.md)
handoffs record foundation history. The architecture analysis below records the
pre-Phase-1 baseline. Earlier requests retained JSON authority; the subsequent
request to complete the original plan approved the SQLite cutover. JSON remains
seed/import/export data after migration, not a parallel editable authority.

## 1. Recommendation

Evolve the existing system, keeping its planner, inventory resolution, extraction, clarification sessions, validators, retrieval, and renderer. Add a small knowledge-management layer behind the existing `app/catalog.py` interface.

Use a staged hybrid storage approach: JSON remains the authoring authority initially; introduce a transactional authoring repository when management writes are added. Published runtime knowledge becomes an immutable, versioned snapshot. There must never be independently editable database and JSON copies of the same active knowledge.

The central distinction is:

- Category parameter membership: which parameter definitions are available in a domain.
- Operation parameter mapping: which parameters an operation uses, their payload paths, and whether they are required.
- Operation schema/rules: allowable values, nested structures, conditional requirements, cross-field checks, and vendor-specific requirements.

Shared parameters carry identity, meaning, labels, aliases, and data types. They do **not** carry required/optional flags or operation validation policies. Canonical operations describe network behavior, not CLI commands.

## 2. Current Architecture

### Repository Layout

Paths below are relative to `network_rag_catalog_v2/`.

```text
main.py                               Terminal entry point
app/
  catalog.py                          Cached catalog reads and integrity checks
  pipeline.py                         Planning, task validation, clarification, render gate
  planner/                            Intent decomposition and runtime task models
  retrieval/                          Category classification and operation retrieval/selection
  devices/                            Inventory, descriptive target resolution, device checks
  parameters/                         Schema loading, extraction, normalization, validation
  context.py                          Planned values, context rules, source fingerprints
  clarification.py, questions.py      Session persistence and structured questions
  templates/                          Template compatibility, selection, Jinja rendering
  ingest.py                           Operation metadata -> Chroma documents
data/
  catalog/
    categories.json                   Category identities, labels, aliases
    parameters.json                   Global parameter definitions; no category membership
    operations.json                   Operation metadata and schema file references
    context_rules.json                Operation/field context policies
    template_support.json             Global vendor/platform/version compatibility
  operations/<category>/<operation>/schema.json
  templates/<vendor>/<category>/<operation>/template.j2
  inventory/                          Device facts and attribute vocabulary
  planned/parameters.json             Planned parameter values
storage/
  chroma/                             Derived retrieval index
  sessions/                           Persisted clarification plans
tests/                                Catalog, target-resolution, clarification regressions
```

Current data contains six categories, 12 operations, 20 global parameters, and 36 vendor templates. Categories are VLAN, OSPF, BGP, IS-IS, static routing, and interface IPv4 addressing (`ip_address`). The templates cover Cisco, Huawei, and Juniper paths; file presence is not vendor certification.

### Existing Entities and Relationships

```text
Category --category_id--> Operation --schema_path--> Hand-authored JSON Schema
Global Parameter <--property key / x-parameter-id--- Schema properties
Operation + Category + Device vendor -------------> Jinja template path
Device + Operation + Field -----------------------> Planned context rules/values
User request ------------------------------------> Persisted execution plan/tasks
```

Category, operation, and parameter are JSON records, not database entities. Schema and template exist as separate files. Parameter use is implicit in schema properties; there is no explicit category-parameter or operation-parameter mapping entity. Runtime `OperationIntent`, `PlannedTask`, and `ExecutionPlan` models are session state, not knowledge-management records.

### Actual Runtime Flow

```text
User input
  -> pipeline.run: reload and validate catalog/context
  -> planner: decompose request into logical intents and target scopes
  -> for each intent:
       extract descriptive target queries -> authoritative inventory resolution
       exact active operation phrase?
         yes -> use catalog operation
         no  -> classify category -> retrieve Chroma candidates -> select operation
                -> require confirmation of proposed operation
       load operation schema + catalog metadata + applicable vendor requirements
       extract explicit parameters; retain provenance and ambiguous candidates
       split resolved multi-device intent into per-device tasks
       validate types/values, inventory compatibility, planned-context conflicts
       gather structured clarification questions where necessary
  -> terminal asks one active question; validate reply; update/revalidate task
  -> all tasks validated + cross-task conflicts resolved?
       no  -> preserve session; no completed configuration output
       yes -> select compatible templates -> StrictUndefined Jinja rendering
              -> stage outputs -> recheck source revision -> publish ready result
```

Important implementation details:

- Category detection is not always a mandatory first stage: exact catalog operation phrases bypass retrieval/classification.
- Target resolution begins before operation selection. Initial parameter extraction happens once per logical intent; values are then copied into device bindings and validated per device. It is not independent initial extraction for each device.
- `schema_loader.py` enriches hand-authored schemas with global parameter metadata and `x-required-by-vendor`. Cisco/Huawei OSPF require a process ID; Junos does not through this overlay.
- Extraction, normalization, and network validation still include field-specific Python behavior. Adding a catalog row alone does not add arbitrary domain understanding.
- `ingest.py` indexes operation metadata and use cases, not the complete operation schema. The LLM extractor receives the selected schema separately.
- Source fingerprints detect data/template changes, but there is no immutable knowledge release. Session revision checks are useful and should remain.

### Strengths to Preserve

Stable catalog IDs, centralized labels/aliases, schema checks, descriptive inventory matching, field-scoped clarification, explicit option/custom-answer handling, persisted partial tasks, per-device validation, vendor compatibility checks, and an all-task render gate already provide useful foundations. Jinja uses known templates rather than model-generated executable syntax.

This is still a guarded prototype: neither the current catalog nor the proposed registry can guarantee correct interpretation of every natural-language request or correct network behavior without domain-specific validation and template verification.

## 3. Gap Analysis

| Area | Current implementation | Desired state | Required change |
| --- | --- | --- | --- |
| Category | Metadata records; operations reference category IDs | Managed category lifecycle and shared parameter membership | Add category-parameter relation and dependency-aware create/edit/retire rules |
| Parameter management | One global registry; fields linked implicitly; some parser logic hardcoded | Reusable typed definitions exposed by category, with stable identity | Add membership, explicit path references, alias scoping, and registered parsers |
| Operation model | Metadata, integer version, status, schema path | Versioned behavior definition with explicit parameter selection | Add operation versions, parameter mappings, rule bindings, draft/publication workflow |
| Schema handling | Hand-authored per-operation files; types repeated in registry/schema | Effective schemas compiled from mappings and operation rules | Add compiler, vendor overlays, immutable artifacts, migration equivalence checks |
| Template generation | Vendor/category/operation filesystem convention; global support list | Explicit operation-version/template compatibility contract | Add template bindings without rewriting Jinja or introducing an execution adapter |
| Retrieval consistency | Mutable Chroma collection; operation/category metadata | Retrieval derived from the same published snapshot used by runtime | Version documents/index builds and activate only complete releases |
| Management readiness | Cached reads and file editing; no management transactions | Storage-independent services with validation, revisions, audit, structured errors | Add service/repository boundary and management CLI before GUI/API transport |

Concrete issues to address during migration:

1. `catalog.py` flattens nested schema property names for type checks. OSPF `interfaces[].name` explicitly refers to parameter `interface`, but raw-name checks also associate it with global `name` (VLAN name). Use full paths and explicit references, not bare nested keys.
2. `schema_loader.py` uses `setdefault` for titles. A hardcoded schema title can resist a central display-name change. Published titles should derive from registry metadata unless an explicit, documented override is supported.
3. Catalog validation requires every active operation to have templates for every vendor in current inventory. Replace this with declared per-operation support; unsupported operation/device combinations must still be rejected before rendering.
4. `ingest.py` removes old records before rebuilding. A failed rebuild can leave retrieval incomplete. Stage a new index and switch the published reference only after success.
5. The renderer inserts a fixed list of optional fields and derives netmasks. Preserve this behavior during migration, then make template input contracts explicit; do not blindly rename parameters in templates.

## 4. Reconcile the Target Document Before Import

Treat the supplied document as the intended domain model, not a complete executable specification. Do not automatically publish all listed operations.

| Issue | Decision needed |
| --- | --- |
| ACL, QoS, static-routing, and OSPF parameter type cells are empty | Confirm types before publication; do not guess them from names |
| `enum` and `list` are underspecified | Define primitive types plus operation enum rules, array item structures, and units where relevant |
| Operations reference absent shared parameters | Add definitions/memberships after review; see examples below |
| Equivalent-looking operations occur under VLAN and Interface | Choose one canonical behavior owner and discovery aliases, or document genuinely different semantics |
| Existing BGP and IS-IS are absent from the target | Preserve both; absence is not a removal instruction |
| Existing `ip_address` category is narrower than Interface | Add Interface deliberately; defer category moves until reference migration is explicit |
| Some target operations differ from existing behavior | Keep separate IDs/versions until semantic equivalence is established |

Missing membership/definition examples: VLAN `mode`; Interface `native_vlan`, `threshold`, `action`, `prefix_length`; ACL `description`, `conditions`, `zone`; QoS `description`, `match_conditions`, `scheduler`, `priority`, `burst_size`, `direction`; OSPF `metric`.

Do not conflate parameters solely because they have the same spelling. Existing `interfaces` means an OSPF array of objects with interface name and area, not a generic list of interface strings. `action` and `mode` may also need distinct semantic identities across domains. Reuse one definition only when meaning and representation agree.

Compatibility decisions:

- Keep current IDs and payload keys initially. Desired labels such as VLAN name can change without renaming the current `name` field.
- `address`/`ip_address`, `area`/`area_id`, and `destination`/`destination_prefix` need scoped mappings, not global text replacement.
- `prefix_length` and `subnet_mask` require a validated representation conversion; `admin_up` and `admin_state` require an explicit boolean/enum conversion. These are not simple synonyms.
- Route preference and route metric are not interchangeable merely because an existing alias suggests that.
- Existing `configure_ospf` configures interfaces as well as a process; it is not simply the target's `enable_ospf_process`.
- Existing static-route removal identifies destination and next hop. Target deletion by destination alone may affect multiple routes. Existing interface-IP removal also has a narrower selector than the target's optional-address removal. Do not silently broaden destructive semantics.
- Preserve current vendor-required fields, including Juniper VLAN-name requirements, while refining the logical operation model.

## 5. Target Architecture

### Backend Components

```text
Management CLI now / GUI API later
              |
              v
Knowledge services: Categories | Parameters | Operations | Schemas/Publication
              |
              v
Repository contract -> JSON initially -> transactional authoring storage later
              |
              v
Validate draft -> compile schemas -> verify template bindings -> build RAG index
              |
              v
Immutable knowledge snapshot + atomic active-release pointer
              |
              v
Existing planner -> extractor -> inventory/context/clarification -> validator
              |
              v
Existing request-wide render gate -> compatible Jinja templates
```

Keep these as modules in the current Python application, not separate microservices.

### Entity Relationship Model

```text
Category 1 -------- * CategoryParameter * -------- 1 ParameterDefinition
Category 1 -------- * Operation 1 ---------------- * OperationVersion
OperationVersion 1 - * OperationParameterMapping * - 1 CategoryParameter
OperationVersion 1 - * OperationRuleBinding
OperationVersion 1 - * CompiledSchema (derived, per support profile)
OperationVersion 1 - * TemplateBinding
KnowledgeSnapshot ---- pins category/parameter/operation revisions,
                       compiled schemas, template hashes, retrieval build
```

| Entity | Minimum responsibility |
| --- | --- |
| Category | Stable ID, label, aliases, description, status, edit revision |
| ParameterDefinition | Stable ID, meaning, primitive/container type, label, aliases; no operation constraints |
| CategoryParameter | Category membership; foreign keys and uniqueness; no required/optional/validation policies |
| Operation / OperationVersion | Canonical behavior identity, owner category, description/examples, draft/published version |
| OperationParameterMapping | Version, category-parameter reference, payload field path, required flag, presentation order |
| OperationRuleBinding | Field/cross-field constraints, nested shape, conditional/vendor requirements, named context/normalization/domain rules |
| CompiledSchema | Generated JSON Schema, operation version, support profile, content hash |
| TemplateBinding | Operation version, vendor/platform/version support, Jinja reference/hash, input contract |
| KnowledgeSnapshot | Immutable release manifest and derived artifact references |

Full field paths are essential: `interfaces[].name` can map to the `interface` definition without colliding with top-level VLAN `name`. The owning category must expose every selected parameter. The same parameter can belong to multiple categories through membership rows.

For example, Interface exposes `interface` (string), `vlan_id` (integer), and `description` (string). `configure_access_port` selects those parameters, requires the first two, and leaves description optional. Its operation rules define VLAN bounds and interface-capability checks. Another operation can reuse `description` but require it. Editing one operation's requirement must not alter the other.

Schema generation has one authority: parameter types + mappings + operation rules. Once an operation migrates, its generated schema is read-only output. Do not maintain two editable versions of its requirements.

### Module Responsibilities

| Proposed module/service | Responsibility and existing integration |
| --- | --- |
| `app/knowledge/models.py` | Validated knowledge records and serializable management request/result models |
| `repository.py`, `file_repository.py` | Storage contract and initial file-backed implementation; `app/catalog.py` remains a compatibility facade |
| `services.py`: Category/Parameter services | Membership, label/alias edits, uniqueness, reference checks, impact reporting |
| `services.py`: Operation service | Canonical operation metadata, versions, parameter selection, draft edits |
| `schema_compiler.py` | Compile mappings/rules into effective schemas; `schema_loader.py` remains the runtime entry point |
| `rule_registry.py` | Allowlisted, code-reviewed parsing/context/validation handlers; rules refer to handler IDs and validated arguments |
| `publication.py` | Validate, stage artifacts, activate releases, audit changes, reject stale writes |
| `migration.py` | Backfill legacy files, compare contracts, report unsupported constructs; never silently drop schema constraints |
| `cli.py` | Exercise management services without building a frontend |
| Existing validation/rendering modules | Continue value/device checks and rendering; consume published contracts |

A GUI must not upload arbitrary Python validation code. Complex new domain behavior can require a reviewed handler and tests; a metadata registry does not make every possible network operation no-code. Template changes also need review and controlled paths, not unrestricted template/file access.

## 6. Storage and Publication Decisions

| Option | Advantages | Limitations | Recommendation |
| --- | --- | --- | --- |
| A. Static JSON/YAML | Simple, diffable, existing infrastructure | Weak concurrent edits, referential integrity and audit require application logic | Keep JSON during model migration; no benefit from a YAML conversion |
| B. Database only | Transactions, relationships, concurrent authoring | Premature persistence redesign; templates/indexes still need artifact management | Not the first step |
| C. Hybrid | Transactional authoring plus inspectable exports and immutable runtime artifacts | Requires an explicit single source of truth and publication protocol | Recommended staged destination |

For a local management backend, standard-library SQLite is a reasonable first transactional authoring store. Introduce it in Phase 5 if management writes are implemented; use repository contracts so a later PostgreSQL adapter does not change services. JSON then becomes import/export/seed data, not a second writable authority. Multi-host authoring would need a suitable server database later.

Publication protocol:

1. Edit a draft with `expected_revision`; reject stale concurrent writes.
2. Validate identities, aliases, membership, mappings, rules, support profiles, template references, and compatibility impact.
3. Compile all relevant schemas; stage template artifacts and a versioned retrieval build from that same draft.
4. Activate the complete manifest atomically. If any build step fails, the previous release remains active. Database transactions alone cannot atomically update Chroma and filesystem artifacts.
5. Bind runtime requests and retrieval to one snapshot. Record its ID on sessions; also track inventory/planned-context revision separately.

Old sessions must be explicitly revalidated or migrated when contracts change. Retaining an old snapshot for audit must not bypass operation retirement/revocation or stale inventory checks. Preserve current fail-closed source checks during this transition. Draft edits must not invalidate live sessions before publication.

Derive retrieval documents from operation metadata plus parameter summaries and release/version identifiers. If indexing is unavailable, do not activate a release that claims a ready retrieval index. Exact-ID/literal behavior may retain its existing offline path, without mixing different release versions.

## 7. Phased Implementation and File Impact

The descriptions below preserve the approved evolution direction. Consult the
completion audit and Phase 4/5 handoffs for implemented paths and verification.

### Phase 1: Improve the Current Catalog Model

Deliver typed knowledge records, a repository boundary, stable identity rules, and an explicit target-document reconciliation list. Preserve all existing behavior and records.

- Modify: `app/catalog.py`, `app/config.py`, existing `data/catalog/{categories,parameters,operations}.json` only where additive metadata is necessary; `tests/test_catalog.py`.
- Add: `app/knowledge/{__init__,models,repository,file_repository,services}.py`, `tests/test_knowledge_repository.py`, a reviewed migration manifest under `data/catalog/`.
- Risk: stricter readers rejecting current records or cache behavior changing. Accept the legacy format through adapters; keep existing catalog function signatures and returned runtime payloads.
- Acceptance: all existing IDs, aliases, operations, schema loads, and template resolutions remain equivalent. No mass renaming, category deletion, or activation of incomplete target operations.

### Phase 2: Introduce the Category Parameter Registry

Add category membership using existing schemas and explicit references as the migration evidence. Register new target definitions only after types and meanings are reviewed.

- Modify: knowledge models/services, `app/catalog.py`, `tests/test_catalog.py`, and parameter metadata where necessary.
- Add: `data/catalog/category_parameters.json`, `tests/test_category_parameters.py`; implement backfill in new `app/knowledge/migration.py`.
- Risk: nested names, duplicate aliases, and unrelated parameters being merged. Resolve `x-parameter-id` with full paths; flag ambiguity instead of guessing. Preserve the existing OSPF `interfaces` contract.
- Compatibility: existing global parameter IDs remain valid; BGP and IS-IS gain memberships too. New Interface/ACL/QoS records can remain drafts without affecting runtime.
- Acceptance: every existing operation property maps to a defined parameter exposed by its category, including nested fields. Shared records have no operation requirement flags or validation policies.

### Phase 3: Introduce Operation Parameter Mapping

Backfill mappings and operation rules from current schemas. Run in comparison mode before making them authoritative. Use a per-operation schema-source marker during the transition; never guess which representation is authoritative.

- Modify: `data/catalog/operations.json`, knowledge services/migration, `app/parameters/schema_loader.py`, catalog integrity checks; metadata lookup in `parameters/{fields,normalizer,parameter_extractor}.py`, `app/questions.py`, and `app/context.py` where it depends on raw field names.
- Add: `data/catalog/{operation_parameters,operation_rules}.json`, `tests/test_operation_mappings.py`.
- Risk: lost nested requirements, accidental type coercion, aliases changing established payloads. Preserve field paths, representations, optionality, and vendor requirements. Unsupported schema constructs block migration.
- Compatibility: existing `schema.json` stays authoritative until that operation passes comparison. Preserve terminal answer paths, provenance, session payloads, and Jinja input names.
- Acceptance: changing one operation's required flag does not change another; central display-label edits propagate without changing stable IDs or validated values.

### Phase 4: Improve Schema Management

Compile and publish contracts, replacing implicit template support with explicit bindings. Reuse existing validators and renderer; migrate field-specific behavior to named handlers only where needed for the registry.

- Modify: `app/parameters/{schema_loader,validator}.py`, `app/templates/{template_selector,renderer}.py`, `app/{ingest,pipeline,context,clarification,config}.py`, `app/planner/models.py`, and `app/retrieval/operation_retriever.py` for snapshot-consistent loading; existing schemas become legacy migration references, not editable authorities for migrated operations.
- Add: `app/knowledge/{schema_compiler,rule_registry,publication}.py`, `data/catalog/template_bindings.json`, derived `storage/catalog_releases/`, `tests/{test_schema_compiler,test_knowledge_publication}.py`.
- Risk: schema weakening, partial publication, incompatible old sessions, or selection of an unsupported template. Compare effective contracts for every existing operation/vendor profile, stage all artifacts, and require revalidation on incompatible changes.
- Compatibility: preserve `load_schema()` and `render()` entry points with a request-scoped snapshot adapter; retain current source-change checks until replacements are verified. Preserve `StrictUndefined`, clarification boundaries, and the all-task render gate.
- Acceptance: required/nested/vendor validation is equivalent for existing operations; schema/templates/retrieval use one release; failed publication leaves the previous release usable. New operations can declare a supported subset of platforms without enabling unsupported combinations.

### Phase 5: Prepare the API Layer for GUI Integration

Implemented: `management.py` and `cli.py` expose transport-neutral contracts;
`authority.py` selects exactly one authoring backend. `sqlite_repository.py` and
`migrations/001_authoring.sql` provide the original transactional destination.
`authoring_store.py` retains compatible JSON management for unmigrated projects.
The same management contract tests exercise both adapters. The workspace cutover
preserves JSON seed files and a backup; runtime remains on published releases.

Expose management use cases through transport-neutral request/result contracts and a CLI. Add transactional persistence for authoring writes; do not build the GUI or require an HTTP server in this phase.

- Modify: knowledge services/repository, `app/config.py`, and governance/handoff documentation.
- Add: `app/knowledge/{sqlite_repository,cli}.py`, database migration files, `app/api/{__init__,contracts}.py`, `tests/{test_knowledge_services,test_knowledge_storage}.py`.
- Risk: double authorities, concurrent edit loss, and unsafe cascading deletes. Perform an explicit JSON-to-database authority cutover; use foreign keys, transactions, expected revisions, and audit records. Keep versioned export/import for recovery.
- Compatibility: runtime continues reading published snapshots; existing user-prompt CLI/session behavior is unchanged. No external PostgreSQL/NetBox/Redis integration is needed now.
- Acceptance: create/edit/retire categories, assign parameters, edit operation requirements, preview schema, validate draft, and publish all work without frontend code. File/database behavior is equivalent at the repository contract. Authentication/authorization is required before exposing management over a network.

## 8. Future GUI Contract and Governance

Management services should accept typed requests and return serializable results with stable IDs, revision, field/path-specific errors, dependency impact, and warnings. Examples:

- Category: create BGP if absent, edit its description, or delete an unused draft. Existing BGP must not be duplicated.
- Parameter: register an integer AS-number parameter and assign it to BGP, while distinguishing local from remote AS semantics. Domain bounds belong to each operation's rules.
- Operation: define `configure_bgp_neighbor` or edit its existing draft; choose category parameters; set required/optional flags; preview effective vendor schemas before publication.
- Lifecycle: reject deletion/unassignment while referenced; retire published records instead of cascading deletion through schemas, templates, or session history.

Central display-name changes are metadata edits, while machine-ID, type, meaning, or representation changes require compatibility review and versioning. Type edits must report all affected operations. Category reassignment must account for template/schema paths, RAG metadata, inventory capability categories, context rules, and sessions.

Alias collisions must be checked within the relevant category/operation scope and wherever globally searched. Two labels for one canonical behavior must not create duplicate executable operations. Cross-category discovery can use aliases/tags without changing canonical ownership.

## 9. Focused Verification and Approval Boundary

After implementation is approved, use the existing environment and run the current regression suite once as a baseline. Add focused coverage for:

1. Existing schemas, nested OSPF mappings, and per-vendor required fields surviving migration unchanged.
2. Independent required/optional rules, central label propagation, duplicate aliases, and dangling references.
3. Strict numeric/array/value validation and existing clarification regressions, including netmask-versus-address and interface slash parsing.
4. Failed publication, stale writes, disabled operations, unsupported device profiles, and old-session handling.
5. One approved new operation demonstrating definition -> mapping -> schema -> clarification -> template, without an operation-specific planner rewrite. This still requires a reviewed template and supported domain handlers.

Do not activate the entire target operation list as part of the structural migration. Migrate the existing 12 operations first, then add new behaviors incrementally. Keep Ansible, execution, topology, external tools, frontend code, and operation-adapter redesign outside this plan.

The initial report was based on repository inspection, not execution or vendor-lab
verification. Subsequent verification is recorded in the phase handoffs. Unresolved
target definitions remain review
items and are not automatically imported or activated.

## 10. Evidence and Reading Order

Read the target and implementation files together; older architecture notes describe intent but are not the runtime authority.

- [Target category/parameter/operation model](CogniShield_v2_Category_Parameter_and_Operation_Schema_Registry.md)
- [Catalog loading and integrity checks](../app/catalog.py): `validate_catalog`, `_schema_parameter_ids`, `_schema_parameter_types`.
- [Current runtime](../app/pipeline.py): `run`, `_process_intent`, `_split_bindings`, `resume_task`, `refresh_plan`.
- [Schema loading](../app/parameters/schema_loader.py): metadata enrichment and vendor requirements.
- [Network validation](../app/parameters/validator.py) and [field parsing](../app/parameters/fields.py): existing deterministic behaviors to preserve.
- [Retrieval ingestion](../app/ingest.py), [template selection](../app/templates/template_selector.py), [rendering](../app/templates/renderer.py).
- [Existing revision notes](../docs/CONTEXT_AWARE_REVISION.md) for clarification/context implementation background.

The original planning task added only this review document. Phase 1-5 implementation
is recorded in the linked handoffs. Existing moved plan files and unrelated
working-tree changes are left untouched.
