# Targets and device context

## From text to identity

`data/inventory/devices.json` holds stable `id`, hostname, aliases, role/site/location/vendor/platform/version, source refs, capabilities and interfaces/resources. `data/inventory/attributes.json` defines searchable attribute paths, aliases, weights and explicit-only fields. `devices.inventory.load_inventory` reads devices; older `resolve_targets` remains a compatibility resolver. Current main path is `target_query.extract_target_queries` -> `target_resolver.resolve_queries`.

`extract_target_queries` isolates a target-bearing clause (on/at/against/for, or trailing identity), avoids treating `on Ethernet1/1` as a device, and splits explicit joined target names when warranted. `parse_description` consumes longest names first, then explicit attribute labels (`site`, `role`, `vendor`, etc.), then vocabulary hits; it records literal spans, source and cardinality (`one`/`many`). If enabled, `_llm_constraints` can label **literal quoted evidence** against the allowed inventory vocabulary; its output cannot directly select a device. Remaining unrecognized words become `unresolved`, not invisible noise.

`target_resolver._matches` checks each constraint against inventory attribute paths (with registry aliases; management IP may be a subnet). `resolve_queries` scores each device by matched weights, but uses scores only for suggestions. A device is selected only if **every** stated constraint matches; multiple complete matches without `many` become `AMBIGUOUS_TARGET`. No complete match is `TARGET_CONFLICT` when each constraint is known somewhere, otherwise `TARGET_NOT_FOUND`. Missing and unresolved descriptions also become issues. Any query issue empties the returned `devices` list. The resolver returns selected evidence and candidate explanations, not just a hostname.

Example: `the Penang edge Juniper router` yields site/role/vendor constraints if present in inventory vocabulary; `resolve_queries` selects the one inventory record satisfying all three. If the prompt also says `Cisco`, no candidate may satisfy all constraints; it asks instead of accepting the highest-scored device. Read the live inventory before assuming which hostname is selected: the static trace is the contract, not a fixed answer about mutable device data.

On clarification, `refine_queries` merges a new descriptive attribute into the active query while preserving other constraints, but an explicit device name replaces the selector. In `pipeline.resume_task`, a resolved per-device group binding can instead parse the replacement reply afresh. The refreshed task invalidates old scope/confirmations/evidence so a target change cannot silently reuse device-derived values.

## After identity: context and policy

`context_validator.normalize_parameters_for_device` maps `interface`, aggregate/member interfaces and nested `interfaces[].name` through that device's name/alias index. `suggest_interfaces` ranks inventory names with `SequenceMatcher`; suggestions are **not** automatically applied. `validate_device_context` checks advertised feature/category support, interface existence (except reviewed new-loopback cases), nested interface names, and the operation's `device_policy` from `context.rules()`.

`operation_policies.validate_policy` dispatches switching/loopback/LAG policies or `resource_policies.validate_resource_policy`; `vendor_policies.validate_native_resource` handles vendor-specific resource behavior. The `PROFILES` map, validated policy IDs and explicit inventory facts can reject a syntactically valid command. For example `switchport_native_vlan_v1` requires a reviewed profile, an existing trunk and a native VLAN in the recorded allowed list. An inventory row lacking a required fact fails closed. These are code-owned domain rules, not inferred by the LLM. `context.parameter_options` can offer inventory interfaces/resource facts and scoped planned records, validated with `candidate_valid`; `context.context_conflicts` checks user input against planned facts/assignments and handles reviewed overrides.

## Where to edit

- Device identity, aliases, role/site, interfaces/capabilities: `data/inventory/devices.json`.
- Searchable attribute paths/synonyms/weights: `data/inventory/attributes.json`; parser grammar/LLM evidence rules in `devices/target_query.py`.
- Match/cardinality/conflict behavior: `devices/target_resolver.py`.
- Interface alias normalization/suggestions: `devices/context_validator.py`.
- Which fields may use planned context, resource keys and policy ID per operation: `data/catalog/context_rules.json` in files mode; published authoring/release in published mode.
- Reviewed policy semantics: `devices/operation_policies.py`, `resource_policies.py`, `vendor_policies.py`.

Do not confuse `source_refs` or `ansible` fields with live integrations: they are local inventory data. The current pipeline generates configurations only; it does not query NetBox or execute commands on a device.
