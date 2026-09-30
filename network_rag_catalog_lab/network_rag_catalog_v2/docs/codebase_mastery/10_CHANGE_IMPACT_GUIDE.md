# Change impact: who owns the decision?

Before editing, establish `NETWORK_RAG_RUNTIME`: files mode uses direct data and `python -m app.ingest` after retrieval-affecting changes; published mode uses management authoring, reviewed assets, `publish(mode='chroma')` and a new immutable release. Never manually edit a release/Chroma/session artifact. A change to inventory or planned context affects both modes' source revision and may invalidate clarification answers.

| Desired change | Source of truth / function | Derived artifact / likely regression |
|---|---|---|
| Add category | Files: `data/catalog/categories.json`; published: `management.apply` Category. `catalog.load_categories`, `category_classifier.classify_category` | Index/release; category filtering, alias collisions, memberships |
| Rename category | Change `display_name`/aliases, **not** stable `category_id`; `catalog.category_for_text` | Reindex/publish; exact classifier/planner wording |
| Add parameter | `parameters.json` or ParameterDefinition via management; membership in `category_parameters.json`; `KnowledgeService.validate_category_parameters` | Schema/mapping and index/release; alias/type collisions |
| Change parameter type | ParameterDefinition and each affected operation rule/schema; `schema_compiler.compile_schema`, `validator` | New operation version in published mode, release/reindex; old session values/templates |
| Add operation | Operation row + category membership-compatible fields/mappings/rules, direct schema, template(s), context rule as needed; `catalog.get_operation` | Direct ingest or publish; planner alias overlap, vendor support, rendering |
| Change requiredness | Files: `schema.json` required/vendor requirements; published: mapping `required`/`required_order` and rules; `schema_loader`, `required_fields` | Reindex/publish; clarification order and template contract |
| Change validation | JSON Schema bounds/enum, `rule_registry` handler registration, `validator`, or device policies as appropriate | Release/reindex when schema changes; invalid value acceptance/rejection |
| Change extraction | `parameters/normalizer.py`, `evidence.py`, `parameter_extractor.py`, `fields.py` | No reindex for Python-only edits; false-positive/omission tests |
| Change top-3 | `pipeline._process_intent` call and `retriever.retrieve_operation_candidates` default | No index rebuild; candidate recall/selector prompt behavior |
| Change operation selection | `operation_selector._explicit_operation/select_operation`, catalog aliases | Alias changes need reindex/publish; semantic proposal and confirmation tests |
| Add target attribute | `data/inventory/attributes.json` + device fields; `target_query`/`target_resolver` | No catalog reindex solely for inventory; ambiguous/conflict tests, source revision |
| Modify inventory | `data/inventory/devices.json`, `inventory.load_inventory` | No index rebuild; session invalidation, device policy, group cardinality |
| Add vendor | Inventory vendor, templates and published binding/support declarations; `template_selector`, `KnowledgeSnapshot.binding` | Direct ingest if template coverage text changes; published new release; syntax/profile checks |
| Add platform/version | Inventory + published TemplateBinding `platform/versions`; code-owned `operation_policies.PROFILES` when a policy requires it | New release for binding, source revision for inventory; blocked combinations |
| Add template | Direct `data/templates/<vendor>/<category>/<operation>/template.j2`; published binding input contract + asset; `renderer.render` | Direct ingest or publish; StrictUndefined/derivations/vendor syntax |
| Add vendor-specific parameter | Direct `x-required-by-vendor` or `x-vendor-profiles`; published operation rule/profile compilation; `schema_loader._apply_vendor_requirements` | Reindex/publish and version bump; vendor clarification/template contract |
| Clarification wording | ParameterDefinition `clarification` or issue message in validator/target/policy; `questions.build_questions` | Catalog wording reindex/publish if data changed; question tests |
| Add device/resource policy | `data/catalog/context_rules.json` references a reviewed handler in `devices/operation_policies.py`/`resource_policies.py`/`vendor_policies.py`; `validate_policy_binding` | Publish or direct reindex for catalog revision; fail-closed policy cases |
| Change derived template value | `knowledge/rule_registry.TEMPLATE_DERIVATIONS/derive_template_value`, binding contract or direct fallback in `renderer._prepare_context` | New release/version if contract/template changes; render correctness |
| Change publication | `knowledge/publication.publish`, `runtime.KnowledgeSnapshot`, `ingest.build_release_index` | Release integrity, rollback/atomicity/index identity; targeted publication tests |

Practical drill: for any field, follow definition -> membership -> operation mapping/rule or direct schema -> extraction/evidence -> validation/policy -> question -> template. For any odd output, identify its **owner** before editing: retrieval rank is not template selection; device identity is not parameter extraction; template presence is not capability proof.
