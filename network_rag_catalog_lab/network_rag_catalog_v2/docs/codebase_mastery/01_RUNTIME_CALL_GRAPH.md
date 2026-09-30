# Runtime call graph

Read with `app/pipeline.py` open. An operation intent is a **clause**, not automatically a rendered task; one intent may split into per-device bindings.

```text
main.main
  -> clarification.create_session(prompt)
     -> pipeline.run(prompt) [snapshot_request]
        -> catalog.reload_catalog + validate_catalog
        -> context.validate_context_catalog
        -> planner.intent_planner.plan_intents
           -> _fallback_plan / optional bounded LLM _validated_model_plan
        -> _process_intent for each OperationIntent
           -> target_query.extract_target_queries
           -> operation_selector._explicit_operation
           -> otherwise category_classifier.classify_category
              -> operation_retriever.retrieve_operation_candidates(k=3)
              -> operation_selector.select_operation
           -> target_resolver.resolve_queries
           -> schema_loader.load_schema(operation, devices)
           -> target_query.parameter_request (mask device facts)
           -> parameter_extractor.extract_parameter_result
           -> _split_bindings -> _refresh_task
              -> resolve_queries -> normalize_parameters_for_device
              -> validator.validate_parameter_result
              -> devices.context_validator.validate_device_context
              -> context.context_conflicts -> template_selector.select_template
              -> questions.build_questions
        -> refresh_plan
           -> _split_bindings, _cross_task_issues
           -> only when every task validated: renderer.render per device
           -> ExecutionPlan.status = ready
     -> clarification.save_session
  -> main._interactive_loop -> clarification.apply_answer / apply_correction
     -> pipeline.resume_task / correct_task -> _refresh_task -> refresh_plan
     -> clarification.save_session
```

## Handoffs

| Transition | Input -> output | Why next stage runs |
|---|---|---|
| `main -> create_session -> run` | raw prompt -> `ExecutionPlan` | Preserve request and allow multi-turn state |
| `run -> plan_intents` | full prompt -> ordered `OperationIntent` list with source spans/target text | Bind each action to its own target clause |
| `_process_intent -> extract_target_queries` | clause or target_text -> constrained target query list | Targets are independent of operation parameters |
| `_explicit_operation` | request + active operation rows -> ID/None | Literal display name/alias can avoid model/index |
| `classify_category -> retrieve_operation_candidates` | clause -> category -> Chroma top 3 in that category | Reduce the semantic operation choice space |
| `select_operation` | candidate list -> allowed operation ID | Model choice is checked against retrieved IDs |
| `resolve_queries` | evidence constraints + inventory -> devices/issues/evidence | Inventory, not LLM, decides identity |
| `load_schema -> extract_parameter_result` | operation/device -> schema; masked clause -> values/provenance/candidates | Ask only about operation fields, retain explicit evidence |
| `_split_bindings -> _refresh_task` | logical task -> 1+ device-specific tasks | Vendor schema/policies can differ per device |
| `_refresh_task -> build_questions` | validation/context issues -> ordered structured questions | No rendering for unresolved information |
| `refresh_plan -> render` | all validated bindings -> staged configs -> ready plan | Whole-request gate, then final source-revision check |

## Branches and stopping points

- **Exact operation:** `_explicit_operation` matches catalog display name/alias. Category/Chroma/selector are skipped. Do not confuse this with the selector's later `_explicit_operation` over the candidate set.
- **Paraphrase:** `classify_category` tries catalog phrase lookup, then LLM; `retrieve_operation_candidates` calls Chroma; `select_operation` tries candidate phrase match, then two LLM attempts. `_process_intent` adds `OPERATION_PROPOSAL`, requiring confirmation before rendering.
- **Missing/ambiguous/conflicting target:** `resolve_queries` returns `MISSING_TARGET`, `AMBIGUOUS_TARGET`, `TARGET_NOT_FOUND`, `TARGET_CONFLICT`, or `TARGET_UNRESOLVED`. `_refresh_task` prioritizes target blockers, so parameter questions wait.
- **Missing parameter:** `extract_parameter_result` leaves a required field `None`; `validate_parameter_result` emits `MISSING`; `build_questions` picks a field-specific question.
- **Invalid parameter/interface:** schema/device checks emit issue; `_refresh_task` records rejected candidate and clears executable value; user must correct.
- **Unsupported vendor/profile:** in files mode missing vendor template or device capabilities/policy blocks; in published mode `KnowledgeSnapshot.binding` enforces exact vendor/platform/version and blocked-unverified metadata.
- **Context conflict:** `context_conflicts` compares applicable planned facts/assignments; confirmation requires provenance and matching source revision.
- **Cross-task conflict:** `_cross_task_issues` uses operation resource keys; `refresh_plan` requests order confirmation tied to task revisions.
- **Render failure:** staged configs are not assigned; `plan.status = failed`, `RENDER_FAILED` recorded. A partial per-task config is not released as a ready plan.

`@snapshot_request` pins one `KnowledgeSnapshot` in published mode across nested calls; `source_revision`/`KnowledgeSnapshot.assert_active` detect changed source/release. In files mode the same decorator scopes `None`, and file hashes protect against mid-request edits. These are safety checks, not device execution.
