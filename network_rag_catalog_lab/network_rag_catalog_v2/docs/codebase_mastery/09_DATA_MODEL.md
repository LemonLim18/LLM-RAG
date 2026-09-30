# Data model and identity

## Entity relationships

```text
Category(category_id) 1---N Operation(operation_id, category_id, version)
      |                            | 1---N OperationParameterMapping
      | N---N ParameterDefinition   |           (field_path -> parameter_id, required/order)
      | via CategoryParameter       | 1---N OperationSchemaRule(field_path -> keywords)
      |                            | 1---N TemplateBinding(vendor/platform/versions)
      |                            | 1---0/1 ContextPolicy (context_rules.operations[ID])
      |                            | 1---N VendorIntentKnowledge (embedded per vendor)
      |                            |
      +-------- membership --------+

Inventory Device(id, hostname, aliases, attributes, capabilities, interfaces/resources)
   + TargetAttribute(attribute ID -> device paths, aliases, weight)
   + PlannedRecord(device_id, operation_id, field, value, source_ref, revision, kind)

AuthoringRevision -> PublicationRelease(release_id, manifest, schemas,
                                        template artifacts, Chroma collection)
OperationIntent -> PlannedTask(logical ID, operation_id, device_id, params,
                               evidence, issues, revision) -> ExecutionPlan
ExecutionPlan -> ClarificationSession(session_id, history, persisted JSON)
```

`CategoryParameter` is membership, **not** requiredness. `OperationParameterMapping.required` and `required_order` are operation/version specific. `OperationSchemaRule.keywords` supplies bounds/format/conditional requirements and handler IDs. A root rule uses `field_path=''`; nested paths may use `[]` placeholders. `schema_compiler.compile_schema` combines them for published releases. In direct files mode, `schema.json` is the runtime schema; mappings may exist for comparison/management but do not replace it automatically.

`Operation.version` protects contract changes across published releases. `TemplateBinding` references operation ID+version and a vendor/platform/version list, reviewed source template path and input contract. In files mode, directory path rather than binding row selects the template. `VendorIntentKnowledge.status` distinguishes intent recognition from verified generation support in published mode. `context_rules.json` maps operation IDs to planned/inventory fields, resource keys, conflicts and policy IDs; it is not the same as JSON Schema.

Device `id` is the durable binding key; hostname/aliases are human selectors. `attributes.json` defines how descriptive words map to inventory fields. Planned records scope values to `(device_id, operation_id, field)` and optional dependencies; their `kind` distinguishes fact, candidate and intended assignment. `target_query` produces evidence-bearing constraints; `target_resolver` either proves a unique/full match or returns clarification issues. A `PlannedTask` holds selected device ID(s), operation ID, params, provenance, candidates, questions and status. A `ClarificationSession` persists the full plan but reloads/revalidates on resume.

The release manifest records source digest, authoring backend/revision, schema paths, template bindings/hashes, retrieval collection/model and artifact hashes. `active.json` points to one release, not a mutable catalog view. `KnowledgeSnapshot` reads the release; SQLite remains an authoring store. Direct-mode Chroma instead uses `catalog_revision` to bind index content to current direct files.

## Referencing rule of thumb

Use stable IDs (`category_id`, `parameter_id`, `operation_id`, `device.id`, `release_id`) across layers. Display names/aliases are human-facing and editable. A schema field may have a different name from its canonical parameter ID (`interfaces[].name` can carry `x-parameter-id='interface'`); do not infer identity from the last path segment alone. Vendor/platform/version is a support profile, not an operation ID. Never treat a retrieved document, LLM JSON or a nearby-looking inventory candidate as an authoritative foreign key without rechecking the relevant source.
