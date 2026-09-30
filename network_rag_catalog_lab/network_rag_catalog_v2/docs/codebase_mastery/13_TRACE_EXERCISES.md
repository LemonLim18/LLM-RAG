# Static trace exercises

These are **source-derived walkthroughs, not executed test results**. Use `python main.py "..."` only when you are ready to check live model/index behavior. A weak LLM can fail where a trace says “candidate”; that failure is itself a branch to inspect. For each exercise, follow control, data, knowledge, state and failure maps together. Files mode is assumed unless stated otherwise.

## 1. Exact operation and one device

Prompt: `Create VLAN 100 named STAFF on R1`.

`main.main -> create_session -> pipeline.run`. `plan_intents` sees catalog phrase `create vlan`, creates one `OperationIntent`. `_process_intent` extracts target `R1`; `_explicit_operation` returns `create_vlan` without Chroma. `load_schema` reads `data/operations/vlan/create_vlan/schema.json` (`vlan_id` required, `name` optional). `parameter_request` masks target evidence; `extract_parameter_result` can capture `vlan_id=100`, `name=STAFF`, with user provenance. `resolve_queries` selects `dev-r1`; `_refresh_task` checks schema/context/template; if no planned-value conflict, task becomes validated. `refresh_plan` renders the Cisco template and sets ready. Inspect `data/planned/parameters.json` for a conflicting R1 record before asserting ready in a real run.

## 2. Paraphrase requiring retrieval

Prompt: `Put a new segmented broadcast domain 100 on R1`.

No catalog operation phrase may match, so `_process_intent` calls `classify_category`. If the LLM returns `vlan`, `retrieve_operation_candidates(..., 'vlan', 3)` queries Chroma. Only returned IDs may be selected by `select_operation`; if `create_vlan` is selected, `_process_intent` records `OPERATION_PROPOSAL`. The task remains in clarification until the user confirms the operation (and any missing field, because `vlan_id=100` may not be deterministically bound without “VLAN”). If category or top-k is wrong, it cannot silently substitute an arbitrary catalog operation. Trace `task.feedback`, `task.planning_issues`, `task.questions[0]`.

## 3. Missing required parameter, two turns

Prompt: `Configure OSPF on R2`.

Exact operation ID is `configure_ospf`; target resolves to Huawei R2. The direct schema requires `interfaces` and `x-required-by-vendor` adds `process_id` for Huawei. Extraction does not invent either. `_refresh_task` emits `MISSING` questions and `refresh_plan` leaves configs empty. On each answer `apply_answer -> resume_task -> fields.parse_answer -> _validation -> _refresh_task -> refresh_plan`. An integer process ID is accepted only for the process question; an `interfaces` answer needs a schema-shaped list with valid inventory names and area values. After two valid answers (possibly more if structure/area is incomplete), render may proceed. Note `questions.build_questions` uses schema order, so inspect the actual first field before answering.

## 4. Ambiguous descriptive target

Prompt: `Create VLAN 100 on the KL core router`.

`target_query.parse_description` yields `site=KL`, `role=core`; `target_resolver.resolve_queries` finds at least R1 and R2 in current inventory, so returns `AMBIGUOUS_TARGET`, candidate labels and no selected devices. `_refresh_task` prioritizes the target question. `select 1` or `select 2` passes an inventory-backed hostname through `resume_task`, then it reloads schema/policy for that device. Nothing renders while target is ambiguous.

## 5. Multiple devices and separate bindings

Prompt: `Create VLAN 100 on R1 and R2`.

Planner creates a logical intent with explicit joined targets. `resolve_queries` returns two devices. `_split_bindings` deep-copies to IDs like `intent-1:dev-r1` and `intent-1:dev-r2`, preserving a logical parent. Each `_refresh_task` can have different vendor requirements and issues. `refresh_plan` needs **both** validated before assigning any rendered configs. A user answer is scoped to one binding/question; it does not automatically change the sibling.

## 6. Unsupported device profile

Prompt: `Configure access port on GigabitEthernet0/0/0 with VLAN 20 on R2`.

The operation `configure_access_port` and Huawei source template may exist, but R2's recorded feature list lacks `interface` and the switching policy requires an explicitly reviewed profile/capability. `validate_device_context` reports `UNSUPPORTED_OPERATION` (and may report invalid interface resource shape). `_refresh_task` blocks the operation; template presence is not enough. Published mode can also block at `KnowledgeSnapshot.binding` when the `(vendor, platform, version)` binding is absent.

## 7. Context/device-policy failure

Prompt: `Set native VLAN 999 on GigabitEthernet1/0/1 on SW1`.

`set_native_vlan` requires `interface` and `native_vlan`. SW1 has a reviewed switching profile, but `operation_policies._validate_switching_policy` checks that requested VLAN exists in SW1's planned VLAN inventory and that the selected port is an existing trunk with the native VLAN in its allowed list. Current SW1 inventory lists only certain VLAN IDs, not 999. `DEVICE_CONTEXT` invalidates the field and `questions.build_questions` may offer relevant inventory values. Changing just the number without checking the trunk still may not yield ready. Follow `task.candidates` and `task.issues` to see each rejection.

## 8. Three-vendor generation shape

Prompt: `Create VLAN 100 on R1, R2 and R3`.

If planner interprets these as one coordinated explicit target set, `_split_bindings` yields Cisco/Huawei/Juniper tasks; all three have `create_vlan` templates and `vlan` capability in inventory. The same `vlan_id` is validated separately; `refresh_plan` selects each vendor's `template.j2`. Because target parsing and any planned context can alter this outcome, inspect `intents`, `target_queries`, bound devices and question list before treating it as a demonstrated success. For an unambiguous manual exercise, run three independent exact requests and compare configurations. No generated CLI should be treated as hardware-certified.

## Debug worksheet

For any trace write down: `OperationIntent.request_text/target_text` -> `target_queries` -> operation/category and selection method -> schema source/required fields -> `parameters` and `parameter_provenance` -> `target_devices` -> `issues/questions` -> `source_revision` -> template path -> `configs`. When a field changes unexpectedly, compare its provenance with `parameter_evidence` and `clarification_history` before changing the parser.
