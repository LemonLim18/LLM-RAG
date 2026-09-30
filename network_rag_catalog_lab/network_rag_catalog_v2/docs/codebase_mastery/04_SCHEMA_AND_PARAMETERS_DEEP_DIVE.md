# Schemas and parameters

## Contract layers

`ParameterDefinition` (`app/knowledge/models.py`) gives stable ID, label, aliases, type, clarification text and optional normalizer. `CategoryParameter` only says that a category may use it; requiredness does **not** live there. `OperationParameterMapping` binds a parameter ID to an operation version and field path, position and required order. `OperationSchemaRule` carries local constraints (`minimum`, `enum`, pattern, conditional rules, handler IDs). `schema_compiler.compile_schema` combines mappings and rules into a JSON Schema, checks references/membership and registered handlers. A published release stores both base and vendor-profile compiled schemas. In **files mode**, `schema_loader.load_schema` instead reads `data/operations/<category>/<operation>/schema.json`; it applies `x-required-by-vendor` and enriches field metadata, but does not recompile mapping records for every prompt. This is the important authority distinction.

Example: `data/operations/interface/set_native_vlan/schema.json` requires `interface` (string) and `native_vlan` (integer 1-4094). The selected interface is then checked against inventory and switching policy; JSON Schema alone cannot establish that the port exists or the VLAN is present.

## Runtime value path

1. `pipeline._process_intent` calls `target_query.parameter_request` to mask device-identity spans. This prevents `R2` or a management address from becoming an operation value.
2. `schema_loader.load_schema` supplies properties and required lists, adjusted for vendor where available. For multiple devices it may use a union; `_split_bindings`/`_refresh_task` then revalidate each device under its own schema.
3. `parameter_extractor.extract_parameter_result` requests required plus explicitly mentioned optional fields (`evidence.mentioned_fields`); its prompt forbids guessing. A deterministic pass (`normalizer.deterministic_values` and `evidence.literal_candidates`) may satisfy them without calling the model.
4. If needed, the LLM gets a reduced contract via `_contract`, at most two attempts. `_parse_json` rejects non-objects; `_filter_to_schema` canonicalizes aliases, checks value shape, literal presence and field-specific grounding. Unproved values become missing, not executable. `explicit_alternatives`/multiple literals create `AMBIGUOUS` candidates. Mentioned-but-unresolved optional values create `UNRESOLVED_VALUE` candidates.
5. `ExtractionResult` carries parameters, provided/missing fields, provenance, candidates and diagnostics. `pipeline._refresh_task` normalizes interface aliases against the device and records accepted/rejected evidence.
6. `validator.validate_parameter_result` checks missing required/dependent/conditional fields (`rule_registry.required_fields`), Draft 2020-12 JSON Schema/format, then registered code-reviewed handlers. `pipeline._validation` adds `devices.context_validator.validate_device_context`.

The provenance vocabulary currently includes `deterministic_user`, `user`, `derived_from_user_netmask`, `inventory_normalization`, `clarification_user` and `context:<source_ref>`. A provenance label is not a cryptographic proof. The safety boundary is the independent evidence, schema, inventory and policy checks.

## The tricky functions

- `normalizer.canonicalize_parameter_keys`: only unique aliases map to a schema property; ambiguous alias collisions are not guessed.
- `normalizer.prefix_length_from_text`: accepts IPv4/CIDR, explicit prefix wording, and explicit/bare netmask in field-scoped answers; does not treat `Ethernet1/1` as `/1`.
- `normalizer._deterministic_values`: hand-coded common network expressions (VLAN, OSPF, BGP, interface, address, prefix). This is **domain-specific** Python, not a general parser.
- `evidence.mask_literals`: hides quoted/structured chunks while searching for field mentions; `literal_candidates` reads field-adjacent JSON/quoted/scalar/primitive-list literals and rejects duplicate object keys.
- `evidence.grounded_scalar`: requires the model's scalar to match a field-local literal or supported tail. Nested arrays/objects require exact literal equality in `_filter_value`.
- `fields.parse_answer`: parses **one question's** schema node (integer/boolean/array/object/prefix/string), not the whole request. Schema/device validation follows. `get_value`, `set_value`, `schema_at`, `leaf_values` support dotted/indexed paths.
- `validator._network_value_issues`, `_safe_string_issues`, `_unique_interface_issues`: mandatory reviewed handlers; `expansion_rules.network_rules` is additional under `expansion_network_v1`.

## Ownership example: `native_vlan`

Find `native_vlan` in `data/catalog/parameters.json`, its Interface membership in `category_parameters.json`, and its operation mapping/rule in `operation_parameters.json`/`operation_rules.json`. In files mode inspect the direct `set_native_vlan/schema.json`; in published mode inspect `compile_schema` output and a vendor profile artifact. Extraction recognizes a field-local value; schema enforces integer range; `operation_policies._validate_switching_policy` requires a reviewed device profile, existing trunk and that the native VLAN is already allowed. `questions.build_questions` supplies schema or context options if missing/invalid. `template_selector.select_template` chooses a vendor file; `renderer.render` supplies optional/derived inputs and executes StrictUndefined Jinja. No single registry row by itself makes this operation safe.

Limits worth knowing: deterministic extraction covers a finite vocabulary, semantic wording still depends on a weak model, and files-mode direct schemas can drift from normalized mapping records. `KnowledgeService.compare_operation_schema` and publication's optional legacy check expose, but do not magically remove, that drift.
