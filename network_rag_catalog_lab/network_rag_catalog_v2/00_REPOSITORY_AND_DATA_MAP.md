# Repository and Data Map

The terminal entry point is `main.py`. The current default is
`NETWORK_RAG_RUNTIME=files`: catalog JSON, per-operation `schema.json`, inventory
JSON, direct Chroma documents, and vendor Jinja templates under `data/`.
`NETWORK_RAG_RUNTIME=published` selects the retained SQLite authoring and
published-release reader. These modes share much of the planner and validation
code, but **direct-file edits are not automatically synchronized to SQLite or
published releases**. See [runtime instructions](docs/DIRECT_RUNTIME.md) and
[three-vendor examples](docs/THREE_VENDOR_PROMPTS.md).

## Architecture Evolution

### Evidence and sequence

The original `network_rag_catalog/` still exists beside v2. Git commit
`676084d` is the first v2 implementation; `166ba53` adds completeness and
clarification gating; `3ccab11` strengthens clarification; `1fdaa3c` adds
context-aware planning and resolution. These commits prove code changes, but
commit names alone do not prove every design motivation. The Phase 1–5
[evolution plan](Implementation_Plan/INTENT_KNOWLEDGE_EVOLUTION_PLAN.md) and
[handoffs](docs/KNOWLEDGE_PHASE_1.md) describe the later intent. Most later
knowledge/backend and direct-file changes remain **uncommitted in this checkout**.
Their order below comes from those handoffs and current source, not a reconstructed
Git commit sequence. A stated cause marked **inference** is an architectural
explanation, not a proven incident report.

The stages overlap: multi-intent planning appeared in the *first* v2 commit,
before persistent clarification and the normalized knowledge backend. The
current direct-file runtime is a deliberate return to the original learning
workflow **after** the SQLite/publication work, not an earlier stage.

```text
V1 direct pipeline (original sibling project)
  -> first V2: multi-intent planner and per-intent targets (676084d)
  -> clarification, validation, context and descriptive targets
     (166ba53, 3ccab11, 1fdaa3c, later uncommitted work)
  -> knowledge Phases 1-3: typed reads, category membership, mappings/rules
  -> Phase 4: compiled schemas, bindings, immutable releases and indexed retrieval
  -> Phase 5: management service and SQLite authoring
  -> expansion packs/rehearsals and activation
  -> CURRENT DEFAULT: direct files + direct Chroma for terminal prompting;
     managed/published path retained separately
```

### 1. Single operation to intent planning and device bindings

**WHY IT EXISTS:** One request can describe several actions with different
targets. This is supported by the first v2 commit; the precise failing user
prompt that prompted it is not recorded in Git.

**WHAT THE OLD SYSTEM DID:** V1 `app.pipeline.run(prompt, targets)` classified
the entire prompt once, extracted one parameter object, then rendered the same
operation/parameters for all targets. See the [V1 pipeline](../network_rag_catalog/app/pipeline.py)
and `git show 676084d:network_rag_catalog_lab/network_rag_catalog_v2/app/pipeline.py`.

**FAILURE/LIMITATION OF OLD APPROACH:** `Create VLAN 100 on R1; configure OSPF
on R2` needs two schemas, two operations and distinct target sets. A single
operation cannot represent that cleanly.

**CURRENT SOLUTION:** [plan_intents](app/planner/intent_planner.py) produces
`OperationIntent`s; [PlannedTask and ExecutionPlan](app/planner/models.py)
preserve scope; [pipeline._process_intent](app/pipeline.py),
[_split_bindings](app/pipeline.py) and [refresh_plan](app/pipeline.py) resolve and
validate each binding, then stage outputs behind a request-wide render gate.

**BENEFIT:** Mixed operations and devices can be identified; unresolved tasks
remain attached to their own intent. **COMPLEXITY COST:** Intent boundaries,
scope inheritance, per-device copies, ordering conflicts and whole-request
blocking are additional states. **COULD IT BE SIMPLER?:** Yes for one operation
per prompt; no for the stated mixed-intent goal. The planner's model/fallback
combination can still missegment free-form text. **IF I REMOVED IT:** Mixed
requests would need manual splitting, and one extracted parameter set could be
rendered against the wrong operation or device.

### 2. Bare device names to inventory-grounded target queries

**WHY IT EXISTS:** V1 looked up lowercase hostnames; early v2 recovered exact
hostnames/display names/aliases. Later user requests explicitly asked for
descriptions such as `the Penang edge Juniper router`. The detailed scoring
design is in current source and the earlier context-resolution notes, rather
than a separate committed change proving each heuristic.

**WHAT THE OLD SYSTEM DID:** [V1 get_devices](../network_rag_catalog/app/inventory.py)
indexed only `hostname.lower()`. First-v2
`_discover_explicit_targets` (commit `676084d`) added normalized exact aliases.

**FAILURE/LIMITATION OF OLD APPROACH:** `Router 1` could fail when only `R1`
was recorded; `Penang edge Juniper router` contains attributes, not a hostname.
Choosing the first vaguely similar device would hide a vendor/site conflict.

**CURRENT SOLUTION:** [extract_target_queries and parse_description](app/devices/target_query.py)
use [inventory attributes](data/inventory/attributes.json) and literal evidence;
[resolve_queries](app/devices/target_resolver.py) checks constraints against
[devices.json](data/inventory/devices.json), ranks suggestions, and reports zero,
one or multiple matches. The model may label evidence but does not authoritatively
select a device.

**BENEFIT:** Names, roles, sites, vendors and supported characteristics can
resolve a device or produce a specific correction question. **COMPLEXITY COST:**
An attribute vocabulary, cardinality rules, confidence/ambiguity handling and
inventory freshness now matter. **COULD IT BE SIMPLER?:** Explicit inventory
aliases suffice for a small fixed lab; attribute matching is justified by the
descriptive-reference requirement. **IF I REMOVED IT:** Descriptive prompts
would fail or select an unverified device; conflicts such as “Cisco R3” would be
hard to surface.

### 3. LLM-only extraction to explicit evidence and provenance

**WHY IT EXISTS:** User-supplied transcripts reported invented OSPF process,
interface and area values; a netmask entered for one question became an address,
and an interface slash overwrote a `/24` prefix. These are reported failures in
the request history; the current code shows the resulting safeguards.

**WHAT THE OLD SYSTEM DID:** [V1 extract_parameters](../network_rag_catalog/app/parameter_extractor.py)
asked the LLM for a JSON object and parsed it. First v2 still relied mainly on
the model's “do not invent” instruction (commit `676084d`).

**FAILURE/LIMITATION OF OLD APPROACH:** A well-formed invented value can pass
type validation. Generic prompt-wide regexes can associate `255.255.255.0`
with `address`, or parse the slash in `Ethernet1/1` as a CIDR length.

**CURRENT SOLUTION:** [extract_parameter_result](app/parameters/parameter_extractor.py)
combines model proposals with [field-scoped literal evidence](app/parameters/evidence.py),
[normalization](app/parameters/normalizer.py), allowed schema fields and
`ExtractionResult.provenance`. [pipeline._refresh_task](app/pipeline.py) retains
accepted/rejected candidates and source evidence; [validate_parameter_result](app/parameters/validator.py)
checks completeness and schema constraints.

**BENEFIT:** Missing values remain missing and model output cannot by itself
become a validated configuration value. **COMPLEXITY COST:** Field-specific
parsers and evidence rules must evolve with new parameter shapes; natural prose
may need clarification even when a stronger model could infer it. **COULD IT BE
SIMPLER?:** A null-only extraction contract plus required-field validation
would solve omissions, but would not prove that a non-null value came from the
right field. **IF I REMOVED IT:** Hallucinated or cross-field values could again
reach a template while appearing schema-valid.

### 4. Schema validation to device, resource and planned-context checks

**WHY IT EXISTS:** JSON Schema can say `interface` is a string; it cannot prove
that `GigabitEthernet1/0/1` exists on the selected Juniper device or that a
VLAN/ACL/policy is present. Domain expansion made resource state especially
important. The broad rationale is an architectural inference; the missing and
conflicting inventory examples are explicit in the project plans and prompts.

**WHAT THE OLD SYSTEM DID:** [V1 validator](../network_rag_catalog/app/validator.py)
checked parameter structure before vendor template selection; the V1 inventory
was a hostname lookup. Early v2 added per-device context checks, committed in
`166ba53`.

**FAILURE/LIMITATION OF OLD APPROACH:** `vlan_id: 20` is a valid integer even if
VLAN 20 is absent; attaching an ACL over an existing different ACL can be
syntactically valid but operationally wrong.

**CURRENT SOLUTION:** [validate_device_context](app/devices/context_validator.py)
normalizes/checks interfaces and capabilities;
[operation_policies](app/devices/operation_policies.py),
[resource_policies](app/devices/resource_policies.py) and
[vendor_policies](app/devices/vendor_policies.py) check operation-specific facts.
[context_conflicts](app/context.py) compares explicit values with planned records
from [planned parameters](data/planned/parameters.json) and
[context rules](data/catalog/context_rules.json). [parameter_options](app/context.py)
offers evidence-backed answers.

**BENEFIT:** Impossible interfaces, unsupported profiles and conflicting planned
attachments become clarification/blockers. **COMPLEXITY COST:** Source-referenced
inventory and policy code must be maintained; synthetic fixture facts do not
certify physical devices. **COULD IT BE SIMPLER?:** A typed inventory lookup
handles interface existence, but ACL/QoS/routing preconditions need some
operation-aware checks. **IF I REMOVED IT:** Correctly typed parameters could
render commands for the wrong interface, existing resource or unsupported mode.

### 5. Missing-field errors to structured clarification sessions

**WHY IT EXISTS:** Early clarification listed multiple questions but accepted
one free-text reply for the whole task. A reply intended as a netmask could
populate the address field. Persistence was also requested so a user could
answer later without restarting the original plan.

**WHAT THE OLD SYSTEM DID:** V1 raised or printed validation failures.
Commit `166ba53` returned `needs_clarification` with questions but did not yet
have today's question/answer/session contract. Commit `3ccab11` strengthened
clarification; exact subsequent refinements are uncommitted.

**FAILURE/LIMITATION OF OLD APPROACH:** `Configure OSPF on R2` cannot safely
render until required values arrive; “Router 1” should answer the target field,
not be reparsed as arbitrary operation parameters.

**CURRENT SOLUTION:** [build_questions and answer_from_text](app/questions.py)
attach `task_id`, `field_path`, expected schema, options, source and revision to
each question. [resume_task and correct_task](app/pipeline.py) update one field
then revalidate. [ClarificationSession, save_session and load_session](app/clarification.py)
persist partial plans; [main.py](main.py) exposes selection/custom/edit/resume.

**BENEFIT:** Device and parameter questions are answerable one at a time;
accepted fields are retained, stale answers rejected, and rendering waits for
the whole request. **COMPLEXITY COST:** Question identity, revisions, history
and session migration enlarge the state machine. **COULD IT BE SIMPLER?:** A
single synchronous loop suffices for one-shot CLI use; persistence and a future
UI require a durable, transport-neutral contract. **IF I REMOVED IT:** Follow-up
answers could be applied to the wrong field/task, and an interrupted session
would lose validated partial work.

### 6. Implicit vendor paths to explicit bindings and profiles

**WHY IT EXISTS:** More operations are not necessarily supported on every
vendor/platform/version; file existence does not state an input contract or
reviewed support. Phase 4 explicitly introduced bindings. Later three-vendor
expansion also required different native parameter sets. The need for exact
hardware certification is *not* established by the repository.

**WHAT THE OLD SYSTEM DID:** [V1 select_template](../network_rag_catalog/app/template_selector.py)
constructed `templates/<vendor>/<category>/<operation>/template.j2`.
First v2 kept vendor selection largely path-based.

**FAILURE/LIMITATION OF OLD APPROACH:** A Cisco-style scheduler bandwidth
contract cannot simply be reused for Huawei WRR or a Junos scheduler map;
similarly Junos OSPF has no Cisco process ID. A path alone does not describe
those requirements.

**CURRENT SOLUTION:** Managed mode declares
[template_bindings.json](data/catalog/template_bindings.json) through
`TemplateBinding`/`TemplateInputContract` in [models.py](app/knowledge/models.py);
[validate_bindings](app/knowledge/publication.py) and
[KnowledgeSnapshot.binding](app/knowledge/runtime.py) check compatibility.
Direct mode uses `x-vendor-profiles` in individual schemas through
[_apply_vendor_requirements](app/parameters/schema_loader.py) and path selection
through [select_template](app/templates/template_selector.py). Exact platform
gating in direct mode comes from device policy/inventory checks, not binding
rows.

**BENEFIT:** One canonical operation can ask for native vendor inputs and use
the correct Jinja file; managed releases can declare reviewed profile bounds.
**COMPLEXITY COST:** Two support-description mechanisms now coexist. Template
presence, profile schema and inventory policy can disagree unless checked.
**COULD IT BE SIMPLER?:** For the present lab, schema profiles plus paths and
inventory checks are sufficient; binding entities chiefly serve the managed
publication goal. **IF I REMOVED IT:** Removing the bindings alone would not
break default direct mode; published mode would lose exact compatibility and
template input contracts. Removing vendor profiles/paths would break direct
three-vendor generation.

### 7. Hand-authored schemas to shared definitions, mappings and compiler

**WHY IT EXISTS:** The [Phase 2](docs/KNOWLEDGE_PHASE_2.md) and
[Phase 3](docs/KNOWLEDGE_PHASE_3.md) handoffs explicitly target centralized
parameter names/types and operation-specific required flags for engineer-led
management. The plans also document a concrete nested collision:
`configure_ospf.interfaces[].name` means an interface, while
`create_vlan.name` means a VLAN name.

**WHAT THE OLD SYSTEM DID:** Each operation had a hand-authored `schema.json`.
`parameters.json` held shared labels, but usage/required flags were implicit in
schema properties. Editing a type/label across operations required careful
manual reconciliation.

**FAILURE/LIMITATION OF OLD APPROACH:** Flattening nested property names can
link OSPF `name` to the VLAN-name definition. A future GUI cannot safely mark
`description` required for one operation and optional for another without a
separate operation mapping.

**CURRENT SOLUTION:** [ParameterDefinition, CategoryParameter,
OperationParameterMapping and OperationSchemaRule](app/knowledge/models.py)
are stored in [parameters](data/catalog/parameters.json),
[category memberships](data/catalog/category_parameters.json),
[operation mappings](data/catalog/operation_parameters.json) and
[operation rules](data/catalog/operation_rules.json).
[KnowledgeService.validate_operation_records](app/knowledge/services.py)
checks relations; [compile_schema](app/knowledge/schema_compiler.py) generates
managed schemas; [schema_parameter_references](app/knowledge/migration.py)
resolves full paths. Phase 3 compared records to old schemas before Phase 4
made compiled schemas authoritative **in published mode**.

**BENEFIT:** Shared definitions and per-operation requirements can be edited
independently; nested field identities are explicit. **COMPLEXITY COST:** To
understand a managed operation, follow multiple records and the compiler.
**COULD IT BE SIMPLER?:** Yes for manually curated direct schemas; the full
normalization was driven mainly by the later GUI/knowledge-management goal.
**IF I REMOVED IT:** Current default direct-file schema loading would still
work, but centralized management, compiled published schemas and membership
checks would not. Direct schemas would again need manual synchronization.

### 8. Direct editing to repository and management services

**WHY IT EXISTS:** Phase 1 wanted typed, stable catalog reads without changing
public call sites; Phase 5 wanted engineer edits, dependency checks, previews,
audit and an eventual API. Those are documented objectives, not evidence that
direct JSON editing had already corrupted this catalog.

**WHAT THE OLD SYSTEM DID:** `app/catalog.py` read JSON directly; an editor
could change catalog files and rebuild Chroma. There was no transaction across
category, operation, mapping, rule and binding changes.

**FAILURE/LIMITATION OF OLD APPROACH:** Adding an operation can leave dangling
parameter IDs or a template binding for the wrong version. A GUI should not
write several files and hope they remain coherent if interrupted.

**CURRENT SOLUTION:** [KnowledgeRepository and AuthoringRepository](app/knowledge/repository.py)
define read/write boundaries; [FileKnowledgeRepository](app/knowledge/file_repository.py)
and [KnowledgeService](app/knowledge/services.py) validate typed reads.
[catalog.py](app/catalog.py) remains the dictionary-returning facade.
[KnowledgeManagementService.apply/preview_schema/import_catalog/export](app/knowledge/management.py)
uses typed [API contracts](app/api/contracts.py) and a selected authoring store.

**BENEFIT:** Future UI/API clients can request coherent edits with structured
errors while old runtime callers keep their interface. **COMPLEXITY COST:**
Repository, service, facade and authoring layers duplicate some navigation and
must agree on authority. **COULD IT BE SIMPLER?:** A single validated JSON edit
command would be enough for this terminal lab; service boundaries principally
serve concurrent management and future API integration. **IF I REMOVED IT:**
Default direct reads could remain, but managed edits, impact checks and future
API integration would need replacing.

### 9. JSON authoring to SQLite authority

**WHY IT EXISTS:** The original evolution plan proposed transactional storage;
the [completion audit](docs/KNOWLEDGE_EVOLUTION_COMPLETION.md) says earlier
Phase 5 deliberately stayed JSON-authoritative because of prior instructions,
then a later request approved the SQLite cutover. The cutover is documented in
handoffs but is not a committed Git transition in this checkout.

**WHAT THE OLD SYSTEM DID:** [JsonAuthoringStore](app/knowledge/authoring_store.py)
provided file locks, expected revisions and a journal/rollback around JSON
documents. Before that, manual file edits had no coherent write transaction.

**FAILURE/LIMITATION OF OLD APPROACH:** Cross-document edits such as “retire a
parameter and remove all mappings” require coordinated revision, audit and
reference constraints. A JSON journal can implement this, but grows bespoke
recovery code.

**CURRENT SOLUTION:** [SQLiteAuthoringStore.commit and migrate_to_sqlite](app/knowledge/sqlite_repository.py)
use [001_authoring.sql](app/knowledge/migrations/001_authoring.sql) for tables,
foreign keys, transactions and audit; [authority](app/knowledge/authority.py)
selects the managed backend. `storage/knowledge/catalog.sqlite3` is the managed
authoring database; catalog JSON can be exported/seeded.

**BENEFIT:** Atomic multi-record authoring, revision checks and relational
constraints. **COMPLEXITY COST:** Migration, database backup/recovery and
distinct direct-file/published authority rules. **COULD IT BE SIMPLER?:** Yes:
the JSON store already supported a small trusted-local workflow; SQLite mainly
helps the later management scale. **IF I REMOVED IT:** Default direct-file
prompting would continue; managed SQLite drafts, audit and publish-from-database
would need migration or replacement.

### 10. Mutable runtime files/index to draft, publish and snapshots

**WHY IT EXISTS:** The [evolution plan](Implementation_Plan/INTENT_KNOWLEDGE_EVOLUTION_PLAN.md)
identified an explicit risk: rebuilding a single Chroma collection after
removing old records could leave retrieval incomplete if the build failed.
Separating drafts also prevents an unreviewed edit from changing live schemas
mid-request. This is a design risk documented in the plan, not a proven outage.

**WHAT THE OLD SYSTEM DID:** Edits to catalog/schema/template files were seen
by later reads; `app.ingest` refreshed the normal operation collection. A plan
could observe changed source unless protected by revision checks.

**FAILURE/LIMITATION OF OLD APPROACH:** An operation document for version 2
could be retrieved while the renderer still reads a version 1 template, or a
failed index rebuild could leave some operations missing.

**CURRENT SOLUTION:** [publish and build_documents](app/knowledge/publication.py)
validate/compile, copy assets, build a release-specific index and switch the
active pointer after success. [KnowledgeSnapshot and snapshot_request](app/knowledge/runtime.py)
pin schemas/templates/metadata for one request; [get_vectorstore](app/vectorstore.py)
selects that release's Chroma collection. [refresh_plan](app/pipeline.py)
revalidates sessions and stages outputs against source revisions.

**BENEFIT:** Managed runtime sees a coherent release, and a failed build leaves
the prior one active. **COMPLEXITY COST:** Release storage, manifests, hashes,
index lifecycle, stale-session handling and publication operations. **COULD IT
BE SIMPLER?:** For local prompt experiments, yes: a direct index with a content
hash and manual re-ingest is sufficient. For a managed multi-editor service,
the snapshot boundary is defensible. **IF I REMOVED IT:** Default direct mode
would still run; managed mode could serve mismatched retrieval and render assets.

### 11. Manual operation addition to reviewed knowledge packs

**WHY IT EXISTS:** The later 38-operation expansion needed repeatable staged
review, asset hashes, conflict checks and rehearsal before activation; the
[expansion plan](Implementation_Plan/KNOWLEDGE_EXPANSION_REVIEW_AND_PLAN.md)
records that choice. This was a feature-expansion workflow, not a fundamental
requirement of the original six-operation learning pipeline.

**WHAT THE OLD SYSTEM DID:** An engineer added JSON catalog rows,
`schema.json`, templates, then ran ingestion. There was no package tying those
changes together.

**FAILURE/LIMITATION OF OLD APPROACH:** Adding ACL/QoS operations involves
parameters, mappings, rules, context policies and vendor assets; a partial
manual import could appear selectable before all pieces were ready.

**CURRENT SOLUTION:** [read_pack, prepare_request and rehearse](app/knowledge/pack_review.py)
validate manifests, reviewed assets and idempotent catalog changes;
[promote](app/knowledge/pack_promote.py) uses management transactions and a
backup. The pack sources live under [knowledge_packs](knowledge_packs/).

**BENEFIT:** Reviewable, repeatable expansion with stop-on-conflict behavior.
**COMPLEXITY COST:** Pack format, duplicate asset locations, rehearsals and
promotion state. **COULD IT BE SIMPLER?:** Yes for the present direct-file
prompt-testing phase; editing catalog/schema/template files and ingesting once
is sufficient. **IF I REMOVED IT:** Current default operation generation would
continue; future bulk managed expansion would lose this review/import workflow.

### 12. Return to direct files for the current terminal experiment

**WHY IT EXISTS:** The later user request explicitly preferred
`catalog + schema + template + RAG` for testing the LLM, rather than making
every knowledge addition pass through pack promotion and publication. The
[direct-runtime note](docs/DIRECT_RUNTIME.md) documents this redirection.

**WHAT THE OLD SYSTEM DID:** Immediately before the redirection, the managed
path authored in SQLite, compiled schemas, published an immutable release and
read release-specific Chroma. The earliest V1 direct design was simpler than
both this managed path and today's guarded direct mode.

**FAILURE/LIMITATION OF OLD APPROACH:** The managed workflow imposed extra
steps and a separate authority while the user wanted rapid prompt experiments
across all 38 requested operations and three vendors.

**CURRENT SOLUTION:** [runtime_mode](app/config.py) defaults to `files`;
[load_schema](app/parameters/schema_loader.py) reads physical schemas;
[select_template](app/templates/template_selector.py) uses vendor paths;
[validate_files/file_documents](app/file_runtime.py) build direct RAG documents;
[ingest_files](app/ingest.py) updates the fixed collection, and
[get_vectorstore](app/vectorstore.py) checks the catalog hash. The optional
published path remains implemented. In direct mode, SQLite mappings/rules and
template-binding rows are **not** the operative schema/template authority.

**BENEFIT:** Add/revise a direct operation, ingest, and test in the terminal.
**COMPLEXITY COST:** Two modes now exist; a direct edit can diverge from the
managed database and prior release. **COULD IT BE SIMPLER?:** A single direct
mode would be simplest for current work, but deleting the managed path would
discard the later backend investment. **IF I REMOVED IT:** Prompt tests would
again require managed authoring and publication; removing the managed path
instead would affect its API/governance plans, not current terminal generation.

### Synthesis: necessity versus expansion

The original core required category/operation selection, a schema, inventory
identity, a vendor template and validation. Multi-intent planning, evidence
checks, device grounding and field-scoped clarification followed concrete
requirements/failures in this project's prompting workflow. They protect the
current tool even with only a few operations.

Category memberships, operation mappings, a compiler, template-binding
entities, SQLite authoring, immutable releases and packs were introduced mainly
for **later knowledge governance, scaling and safe publication**. They are
reasonable for an engineer-managed platform, but over-engineered for a single
developer testing local RAG prompts. The current direct-file default reflects
that distinction. It does not erase the cost of keeping two authorities. Before
re-enabling managed publication for these new direct edits, the schemas,
bindings and support facts need an explicit reconciliation and review.

### 1. EARLY SYSTEM

```text
V1 human prompt -------------------------+ separate target-name list
      |                                  |
      v                                  v
category classifier                 hostname-only inventory lookup
      |
      v
Chroma top-k operation -> LLM operation choice
      |
      v
per-operation schema.json -> LLM parameter JSON -> schema validation
      |                                         |
      +-----------------------------------------+
                         |
                         v
            templates/<vendor>/<category>/<operation>/template.j2
                         |
                         v
                    rendered config
```

Source: [V1 pipeline](../network_rag_catalog/app/pipeline.py),
[V1 inventory](../network_rag_catalog/app/inventory.py) and
[V1 architecture](../network_rag_catalog/docs/architecture.md).

### 2. CURRENT SYSTEM

```text
                     AUTHORING / GOVERNANCE (optional published mode)
 engineer CLI/future API -> management -> SQLite draft + audit
                                |              |
                  shared params/mappings/rules  reviewed templates/bindings
                                +------> compiler/validation
                                           -> immutable release
                                           -> release-specific Chroma
                                                      |
                                                      v
prompt -> intent planner -> target-query extraction -> inventory resolver
                     |                     |                 |
                     |                     +---- mismatch/ambiguity questions
                     v
           category + operation retrieval/selection
                     |
             selected vendor schema
                     |       default files: schema.json + direct Chroma
                     |       published: compiled release schema + release Chroma
                     v
      literal evidence + bounded LLM extraction + provenance
                     |
      schema + device/resource/planned-context validation
                     |
      persisted field-scoped clarification (repeat until complete)
                     |
       per-device tasks + cross-task checks + whole-request render gate
                     |
           vendor template -> Jinja configuration preview
```

Source: [pipeline](app/pipeline.py), [catalog facade](app/catalog.py),
[direct runtime](app/file_runtime.py), [knowledge runtime](app/knowledge/runtime.py),
[management](app/knowledge/management.py) and [publication](app/knowledge/publication.py).
