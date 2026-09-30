# Pipeline deep dive

Source: `app/pipeline.py`. Read top to bottom. The module is an orchestration layer; catalog, parser, resolver, policies and renderer own the specialized decisions. Its public touchpoints are `run`, `resume_task`, `correct_task`, `refresh_plan`, `confirm_order`, `plan_to_dict` (and compatibility `_finalize_task`).

## Validation and task refresh (`_validation`, `_record_candidate`, `_refresh_task`)

```python
issues = [vars(issue) for issue in validate_parameter_result(params, schema).issues]
issues += validate_device_context(task.operation_id, task.category, params, task.target_devices)
```

This composes schema/handler issues with device-context issues; it does **not** itself decide whether a value came from inventory. `_record_candidate` saves a rejected value with field, evidence, operation/device and `validation='rejected'` so a question can explain what was wrong. `_refresh_task` is the main state recalculator:

1. Clear old configs. Compare `source_revision`; if changed, bump task revision, invalidate confirmations and non-inventory/schema context-derived values, and reconsider context-conflict candidates.
2. Resolve `target_queries` against current inventory; preserve resolution evidence. Set `scope_device_ids` for detected group membership. If a previously bound device disappears or group changes, make a `TARGET_CONFLICT` instead of silently retargeting.
3. Resolve operation metadata and load the schema for selected device(s). An unknown operation becomes `UNRESOLVED_OPERATION`.
4. Drop optional `None` values. For one device, normalize interface aliases using inventory and mark changed field provenance `inventory_normalization`.
5. Validate. Ignore `MISSING` until all bad supplied values have been cleared; move invalid non-root values to rejected candidates, set their parameter path to `None`. Root errors become operation issues. Collect unsupported-operation issues, rejected candidates and then fresh `MISSING` issues.
6. Check planned context conflicts and selected template for a single device. Keep operation/target issues ahead of dependent parameter issues.
7. Rebuild `parameter_evidence`, status (`validated` or `needs_clarification`), and `questions` via `build_questions`.

The key line is `task.issues = blockers or issues`: if operation or target is unsettled, parameter questions are deliberately deferred. `_refresh_task` never calls Jinja.

## Creating tasks (`_finalize_task`, `_split_bindings`, `_process_intent`)

`_finalize_task` is a compatibility constructor that makes a `PlannedTask`, then calls `_refresh_task`; it does not render. `_process_intent` creates an empty task from an `OperationIntent`, extracts target queries, then resolves the operation:

```python
operation = _explicit_operation(intent.request_text, load_operations())
if operation is None:
    category = classify_category(intent.request_text)
    retrieved = retrieve_operation_candidates(intent.request_text, category, 3)
    operation = select_operation(intent.request_text, category, retrieved)
```

It loads the per-device schema, masks device facts out of the parameter prompt with `parameter_request`, extracts values/evidence, and stores ambiguous candidates. A semantic choice adds `OPERATION_PROPOSAL` even when the model returned a valid ID. Failures are stored as `task.feedback`, then `_split_bindings` attempts refresh; there is no implicit fallback to some other operation. `_split_bindings` deep-copies a logical task for every resolved device, suffixing `intent_id` with device ID, while preserving `logical_intent_id`. If target/planning issues remain, it keeps a single unresolved task.

## Answering and editing (`resume_task`, `correct_task`)

`next_clarification` exposes first issue; `next_clarification_prompt` exposes first field/wording; `_reject` returns a copied task with feedback and rejected-answer history. `resume_task` requires `needs_clarification`, checks the question ID, task revision and source revision, then branches by question field:

- Target: selected names replace/refine target queries (`extract_target_queries` or `refine_queries`); clear device binding, scope, context confirmations and parameter evidence.
- Operation: select an active ID/display name, clear operation issues, **re-extract** under the replacement schema, clear confirmations.
- Parameter: use a selected option or `fields.parse_answer` for exactly that schema path; normalize interface names; validate proposed delta; retain existing validated values; update provenance, candidates, item IDs, optional override confirmation.

Every accepted answer increments task revision, appends clarification history, and calls `_refresh_task`. Rejected answers keep prior validated state via `_reject`. `correct_task` turns an explicit edit into a scoped question, reuses `resume_task`, and invalidates dependent context decisions for target/interface edits. It never edits a ready task merely because a free-text reply happens to contain another value.

## Whole-request gate (`_cross_task_issues`, `refresh_plan`, `confirm_order`)

`_cross_task_issues` reads `context.rules()['operations']` resource keys/constants/composite keys and compares tasks on the **same device**. Conflicting operation pairs or divergent duplicate actions produce `CROSS_TASK_CONFLICT`. `confirm_order` records a signature of selected task IDs, parameters and revisions, plus source revision; later edits invalidate the signature.

```python
if any(task.status != "validated" for task in tasks) or not tasks:
    plan.status = "needs_clarification"
    return plan
```

`refresh_plan` first refreshes/splits tasks, then enforces that gate. If valid, it checks cross-task order confirmation, sets plan `validated`, and (unless `render_complete=False`) stages every `render(device, operation_id, parameters)` result. It compares `source_revision()` again before assigning staged configs. Any rendering exception yields `failed` and `RENDER_FAILED`; no task is marked rendered. Only the final loop assigns `task.configs`, `task.status='rendered'`, and `plan.status='ready'`.

`run` reloads and validates catalog/context, plans intents, processes each, refreshes the full plan, optionally prints `plan_to_dict`. The outer `@snapshot_request` pins published knowledge for the call. Important limit: `_process_intent` catches broad exceptions into feedback, so a failed semantic retrieval may surface as a generic unresolved-operation question rather than a granular retrieval error.
