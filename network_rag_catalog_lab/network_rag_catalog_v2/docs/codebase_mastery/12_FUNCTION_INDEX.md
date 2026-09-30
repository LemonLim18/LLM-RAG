# Function and class index

Format: `symbol` -> `file` -> principal caller(s) -> responsibility. Private helpers are included where they control a behavior; trivial serializers are grouped. Search `rg 'symbol\(' app main.py` before assuming a caller list is exhaustive (tests and CLI tools also call public functions).

## Entry, planning, pipeline

| Symbol | File | Principal caller(s) -> purpose |
|---|---|---|
| `main`, `_parse_args`, `_interactive_loop` | `main.py` | CLI -> create/resume/edit sessions, display and answer questions |
| `OperationIntent`, `PlannedTask`, `ExecutionPlan`, `ClarificationAnswer` | `app/planner/models.py` | Planner/pipeline/clarification -> transport and state records |
| `plan_intents`, `_fallback_plan`, `_validated_model_plan` | `app/planner/intent_planner.py` | `pipeline.run` -> split clauses, bound/verify optional LLM plan |
| `_operation_hits`, `_ambiguous_scope` | `app/planner/intent_planner.py` | planner -> catalog phrase spans and indirect-scope trigger |
| `run`, `_process_intent` | `app/pipeline.py` | session creation -> validate sources and turn each intent into tasks |
| `_finalize_task`, `_split_bindings` | `app/pipeline.py` | compatibility/tests, `_process_intent`/`refresh_plan` -> task construction and per-device copies |
| `_validation`, `_record_candidate`, `_refresh_task` | `app/pipeline.py` | task creation/resume/plan refresh -> recompute issues/evidence/status |
| `resume_task`, `_reject`, `correct_task` | `app/pipeline.py` | clarification service -> field-scoped answer/correction and rejection |
| `next_clarification`, `next_clarification_prompt` | `app/pipeline.py` | clients/tests -> first issue/question wording |
| `_cross_task_issues`, `refresh_plan`, `confirm_order` | `app/pipeline.py` | run/answer/reload -> whole-plan gate, resource conflicts, order confirmation |
| `plan_to_dict` | `app/pipeline.py` | CLI/session -> dataclass serialization |

## Catalog and retrieval

| Symbol | File | Principal caller(s) -> purpose |
|---|---|---|
| `knowledge_service`, `load_categories/operations/parameters`, `get_category/operation/parameter` | `app/catalog.py` | engine -> snapshot or direct typed catalog reads |
| `load_category_parameters`, `parameters_for_category`, `load_operation_parameters/rules`, `compare_operation_schema` | `app/catalog.py` | tooling/validation -> normalized catalog views |
| `category_for_text`, `operation_terms`, `parameter_label` | `app/catalog.py` | classifier/planner/questions -> catalog-controlled labels and phrases |
| `reload_catalog`, `validate_catalog` | `app/catalog.py` | `pipeline.run/refresh_plan` -> refresh and verify selected mode |
| `classify_category` | `app/retrieval/category_classifier.py` | `_process_intent` -> deterministic catalog alias or LLM category |
| `retrieve_operation_candidates` | `app/retrieval/operation_retriever.py` | `_process_intent` -> filtered Chroma top-k, catalog/release checks |
| `_explicit_operation`, `select_operation` | `app/retrieval/operation_selector.py` | `_process_intent` -> phrase shortcut or bounded LLM ID choice |
| `get_vectorstore` | `app/vectorstore.py` | retriever -> mode-specific Chroma with freshness checks |
| `build_document`, `ingest`, `ingest_files`, `build_release_index` | `app/ingest.py` | CLI/publication -> direct and release-specific index creation/verification |
| `catalog_revision`, `validate_files`, `file_documents` | `app/file_runtime.py` | catalog/ingest/vectorstore -> direct data integrity and RAG text |

## Parameters and clarification

| Symbol | File | Principal caller(s) -> purpose |
|---|---|---|
| `load_schema`, `_apply_vendor_requirements`, `_add_catalog_metadata` | `app/parameters/schema_loader.py` | pipeline/questions/renderer -> direct or released schema, vendor requiredness |
| `ExtractionResult`, `extract_parameter_result`, `extract_parameters`, `merge_parameters` | `app/parameters/parameter_extractor.py` | pipeline/compatibility -> grounded extraction result or wrapper/merge |
| `_explicit_values`, `_filter_to_schema`, `_filter_value`, `_contract`, `_parse_json` | `app/parameters/parameter_extractor.py` | extraction -> deterministic values, evidence filter, LLM contract/JSON |
| `normalize_key`, `parameter_identity/metadata`, `canonicalize_parameter_keys` | `app/parameters/normalizer.py` | extractor/questions -> canonical alias and field identity |
| `prefix_length_from_text`, `normalize_value`, `deterministic_values`, `explicit_alternatives` | `app/parameters/normalizer.py` | extractor/answer -> explicit network literals, normalization, ambiguity |
| `mask_literals`, `field_terms`, `value_tails`, `mentioned_fields` | `app/parameters/evidence.py` | extractor -> field-local evidence search |
| `literal_candidates`, `grounded_scalar` | `app/parameters/evidence.py` | extractor -> JSON/quoted/primitive-list literal and scalar grounding |
| `tokens`, `get_value`, `set_value`, `schema_at`, `leaf_values`, `parse_answer` | `app/parameters/fields.py` | pipeline/questions/context -> nested field paths and typed scoped answer |
| `ValidationIssue`, `ValidationResult`, `validate_parameter_result`, `validate_parameters` | `app/parameters/validator.py` | pipeline/context/renderer -> missing/schema/handler validation |
| `_find_missing_required`, `_network_value_issues`, `_safe_string_issues`, `_unique_interface_issues` | `app/parameters/validator.py` | validator/rule registry -> reviewed completeness and network checks |
| `network_rules` | `app/parameters/expansion_rules.py` | rule registry -> additional expansion-specific validation |
| `build_questions`, `answer_from_text`, `selected_options` | `app/questions.py` | pipeline/CLI -> prioritized question/option/answer contract |
| `ClarificationSession`, `create_session`, `load_session`, `save_session`, `session_to_dict` | `app/clarification.py` | CLI -> durable plan with revalidation on load |
| `apply_answer`, `apply_clarification`, `apply_correction`, `confirm_session_order` | `app/clarification.py` | CLI/future client -> answer/edit/order and persist |

## Devices and planned context

| Symbol | File | Principal caller(s) -> purpose |
|---|---|---|
| `load_inventory`, `find_explicit_target_references`, `find_explicit_group_references`, `resolve_targets` | `app/devices/inventory.py` | target query/compatibility -> local inventory and legacy reference support |
| `load_attributes`, `values_at`, `vocabulary` | `app/devices/target_query.py` | parser/resolver -> searchable attribute registry and values |
| `parse_description`, `extract_target_queries`, `_llm_constraints`, `parameter_request` | `app/devices/target_query.py` | planner/pipeline/resume -> evidence-backed selectors and parameter masking |
| `resolve_queries`, `_matches`, `resolve_intent_targets`, `refine_queries` | `app/devices/target_resolver.py` | pipeline/compatibility -> authoritative match, issues and refinement |
| `normalize_parameters_for_device`, `validate_device_context`, `suggest_interfaces` | `app/devices/context_validator.py` | pipeline/context/questions -> aliases, interface/feature/policy checks |
| `validate_policy_binding`, `allows_new_interface`, `validate_policy` | `app/devices/operation_policies.py` | publication/context validator -> reviewed policy dispatch |
| `validate_resource_policy`, `validate_native_resource`, `resource_options` | `app/devices/resource_policies.py`, `vendor_policies.py`, `resource_options.py` | policy/context -> resource safety and options |
| `context_revision`, `source_revision`, `rules` | `app/context.py` | pipeline/questions -> freshness hashes and current rules |
| `matching_records`, `candidate_valid`, `parameter_options`, `context_conflicts`, `validate_context_catalog` | `app/context.py` | pipeline/questions -> scoped planned facts, suggestions and conflicts |

## Rendering and knowledge backend

| Symbol | File | Principal caller(s) -> purpose |
|---|---|---|
| `template_binding`, `select_template` | `app/templates/template_selector.py` | pipeline/renderer -> mode-specific support/path selection |
| `_prepare_context`, `render` | `app/templates/renderer.py` | `pipeline.refresh_plan` -> defaults/derivations and StrictUndefined Jinja |
| `KnowledgeRepository`, `AuthoringRepository` | `app/knowledge/repository.py` | services/stores -> read and write protocols |
| `Category`, `ParameterDefinition`, `CategoryParameter`, `Operation`, `OperationParameterMapping`, `OperationSchemaRule`, `TemplateBinding` | `app/knowledge/models.py` | repositories/management/compiler -> typed records |
| `FileKnowledgeRepository`, `DocumentKnowledgeRepository`, `SQLiteKnowledgeRepository` | `app/knowledge/*repository.py` | catalog/snapshot/management -> typed read adapters |
| `KnowledgeService` lookup/validate/compare methods | `app/knowledge/services.py` | catalog/management/publication -> cross-record rules |
| `JsonAuthoringStore`, `SQLiteAuthoringStore`, `migrate_to_sqlite` | `app/knowledge/authoring_store.py`, `sqlite_repository.py` | management/authority -> revisioned atomic authoring and migration |
| `authority`, `authoring_store`, `authoring_snapshot_unlocked` | `app/knowledge/authority.py` | management/publication -> single authoring backend selection |
| `KnowledgeManagementService.inspect/validate/preview_schema/apply/export/import_catalog/publish/migrate_sqlite/recover` | `app/knowledge/management.py` | CLI/future API -> typed governance actions |
| `schema_parameter_references`, `build_category_parameter_backfill`, `build_operation_backfill` | `app/knowledge/migration.py` | validation/migration -> legacy reference checks and backfill |
| `project_operation_schema`, `compare_projection` | `app/knowledge/operation_contracts.py` | service comparison -> normalized versus legacy schema |
| `compile_schema` | `app/knowledge/schema_compiler.py` | management/publication -> mapped/rule JSON Schema |
| `required_fields`, `validation_issues`, `validate_handler_ids`, `derive_template_value` | `app/knowledge/rule_registry.py` | validator/compiler/renderer -> reviewed handler registry |
| `validate_composite_keys`, `composite_values` | `app/knowledge/resource_keys.py` | publication/pipeline -> valid and matched cross-task resource identities |
| `active_pointer`, `KnowledgeSnapshot`, `current_snapshot`, `snapshot_scope`, `snapshot_request` | `app/knowledge/runtime.py` | all published reads -> integrity/active release and request pinning |
| `validate_bindings`, `build_documents`, `publish` | `app/knowledge/publication.py` | management/CLI -> checked immutable release and index activation |
| `read_pack`, `prepare_request`, `rehearse`, `check_cases` | `app/knowledge/pack_review.py` | pack tooling -> staged, hashed, isolated review |
| `promote`, `merge_demo_devices` | `app/knowledge/pack_promote.py` | explicit CLI -> idempotent reviewed pack/device promotion |
| `validate_vendor_knowledge`, `coverage_report` | `app/knowledge/vendor_coverage.py` | publication/tooling -> vendor support consistency |

Not indexed at function granularity: one-line wrappers, Pydantic validators that only enforce local shape, and test-only helpers. For any nontrivial symbol above, the named source file is the next stop, not this summary.
