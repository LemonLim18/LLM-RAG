# Mastery questions and concise answers

Try to answer without opening this page; then point to the owner function.

1. **Where does a terminal request enter?** `main.main -> clarification.create_session -> pipeline.run`.
2. **What is an intent versus a task?** `OperationIntent` is a planned request clause; `_split_bindings` may create one `PlannedTask` per device.
3. **What bypasses Chroma?** A unique catalog display name/alias in `operation_selector._explicit_operation`.
4. **Why classify category before operation retrieval?** Chroma queries use a category metadata filter to narrow candidates; a wrong category can exclude the correct operation.
5. **Who owns top three?** `_process_intent` passes `3` to `retrieve_operation_candidates`; the latter defaults to `k=3`.
6. **Why cannot Chroma decide the operation?** It returns ranked candidates/distances, not authority; `select_operation` restricts IDs and semantic choices require confirmation.
7. **What if index and files differ?** `vectorstore.get_vectorstore` rejects file-mode catalog revision/model/ID mismatches; reingest is needed for semantic retrieval.
8. **How does the LLM select a device?** It does not authoritatively. `target_query` may use bounded LLM literal labeling; `target_resolver` verifies all constraints against inventory.
9. **What happens if two devices match?** Unless the query explicitly has `many` cardinality, `resolve_queries` returns `AMBIGUOUS_TARGET` and candidates.
10. **Why separate target evidence from parameters?** `parameter_request` masks device descriptors so site/vendor/management facts are not mistaken for operation values.
11. **What stops an invented parameter?** `_filter_to_schema` applies literal/field evidence, then schema and device validation. It reduces hallucination risk, not a mathematical guarantee for arbitrary prose.
12. **Where is `prefix_length` normalized?** `normalizer.prefix_length_from_text` and `rule_registry.normalize_prefix`; `fields.parse_answer` uses that on a prefix-specific reply.
13. **Why does `Ethernet1/1` not mean `/1`?** Prefix parser only accepts full IPv4/CIDR, explicit prefix wording or a full bare `/N` answer.
14. **Who decides if a field is required?** Direct mode: operation `schema.json` plus vendor profile; published mode: operation mapping/rule compiled schema plus vendor requirements; `validator._find_missing_required` enforces it.
15. **What does category membership mean?** The parameter is allowed in that domain; it says nothing about requiredness for a particular operation.
16. **How are invalid interfaces handled?** `context_validator.validate_device_context` checks inventory; `_refresh_task` records a rejected candidate, clears the executable value and asks with `suggest_interfaces` options.
17. **Where do proposed context values come from?** `context.parameter_options` reads whitelisted inventory/resource/planned records and validates each candidate before displaying it.
18. **Can a user override a planned fact?** `context_conflicts` only permits an explicit reviewed override for allowed non-fact planned assignments and ties it to source revision; facts do not get that override path.
19. **What makes a question stale?** Mismatched question ID, task revision or source revision in `resume_task`; changed data also triggers refresh/rejection.
20. **What is saved in a session?** Full serialized plan, task questions/evidence/history and session metadata in `storage/sessions`; configs are cleared/revalidated on load.
21. **What happens when one of three tasks is incomplete?** `refresh_plan` does not render **any** task until all validate; independent tasks retain their validated state.
22. **Why is a same-request VLAN creation not inventory truth for another task?** Device policies read recorded inventory/resource facts; task outputs are staged text, not a source-of-truth mutation.
23. **Where does vendor support become authoritative?** Files mode: present vendor template plus inventory/policy validation; published mode: `KnowledgeSnapshot.binding` exact vendor/platform/version and reviewed metadata.
24. **What if a schema changes?** Direct files change `catalog_revision` and require reingestion for semantic search; published contract/template changes require a version bump/new release; stale questions revalidate.
25. **Why `StrictUndefined`?** `renderer.render` fails on undeclared Jinja inputs; it does not certify command semantics.
26. **What prevents an old release index mixing with a new catalog?** Published retrieval checks release ID/version/category; `KnowledgeSnapshot` verifies hashes and active pointer; `build_release_index` verifies document set before activation.
27. **What does SQLite own?** Transactional authoring state, revisions and audit, selected by `authority.json`; runtime published reads immutable release, while default terminal reads direct `data/`.
28. **Which pieces remain hardcoded?** Planner/target/extraction regexes, policy/profile IDs and implementations, mandatory validation handlers, derivations, top-k and files-mode directory convention. See `11_HARDCODED_VS_DATA_DRIVEN.md`.
29. **How do you debug a missing optional field?** Check schema property, `evidence.mentioned_fields`, `literal_candidates`, `_filter_to_schema`, `ExtractionResult.candidates`, then question/renderer contract; never first edit the template.
30. **What would you change to add `configure_ntp_server`?** Define category/parameter membership, operation ID/aliases, direct or compiled schema/mappings/rules, target/context policy if needed, vendor templates/bindings, then index/publish. Add Python only if no reviewed parser/policy/derivation covers its semantics. Check behavior in the selected runtime mode.
