# Template selection and rendering

## Runtime path

`pipeline._refresh_task` calls `template_selector.select_template` before declaring a task validated. `refresh_plan` later calls `renderer.render` only after every task is validated and cross-task order is settled. `render` selects the template again, obtains its contract, builds a context and renders with Jinja `StrictUndefined`; it returns text ending in a newline. It does **not** push config to devices or generate an Ansible playbook.

In files mode, `template_binding` deliberately returns `None`; `select_template` builds `data/templates/<device.vendor>/<operation.category_id>/<operation_id>/template.j2` and fails if missing. `renderer.render` reloads the direct operation schema for that device, validates it again, supplies `None` for absent optional fields and applies registered deterministic `TEMPLATE_DERIVATIONS` when source parameters exist. The fallback `_prepare_context` also handles legacy optional keys and computes a netmask from `prefix_length` when needed.

In published mode, `KnowledgeSnapshot.binding` checks vendor knowledge and an exact `(operation, vendor, platform, version)` binding in the active release. `select_template` points to the hashed release artifact; `renderer._prepare_context` uses the binding's declared `input_contract` (`fields`, `optional_defaults`, `derived`). `KnowledgeSnapshot.verify/assert_active` checks artifact hash and active pointer. `publication.validate_bindings` checks one reviewed template asset per binding, version alignment, no overlapping profiles, safe path, contract/schema parity, optional defaults only for optional fields, known derivations, standalone Jinja and no undeclared variables. Published per-profile schemas materialize vendor requirements.

## Real examples to inspect

- Cisco: `data/templates/cisco/vlan/create_vlan/template.j2` with `data/operations/vlan/create_vlan/schema.json`; device `R1` advertises VLAN in its feature list.
- Huawei: `data/templates/huawei/ospf/configure_ospf/template.j2` with device `R2` and `x-required-by-vendor` process ID; interface existence is checked before render.
- Juniper: `data/templates/juniper/ospf/configure_ospf/template.j2` with device `R3`; inspect current inventory capability and template before assuming a specific prompt is ready.

For the same `create_vlan` parameters `{"vlan_id": 100, "name": "STAFF"}`, the three current source templates show the mapping plainly:

```text
Cisco:   vlan 100 / name STAFF
Huawei:  vlan 100 / description STAFF
Juniper: set vlans STAFF vlan-id 100
```

These are outputs implied by `data/templates/{cisco,huawei,juniper}/vlan/create_vlan/template.j2`, not claims of field-certified syntax or active published bindings. For newer switching/QoS examples, a present template is still insufficient if `device_policy` requires facts the chosen device lacks.

## Ownership and failure flow

Operation-to-vendor template choice is `select_template`; supported profile identity is release binding in published mode and directory existence plus inventory/policy in files mode. Derivation ID -> calculation lives in `knowledge/rule_registry.py:derive_template_value`; `netmask`, ACL wildcard, destination/network address, DSCP and Huawei member formatting are examples. Optional omission belongs in the template/contract, while requiredness belongs in schema/mapping. `StrictUndefined` catches undeclared variables, but it does not by itself prove correct network semantics. A missing template or invalid contract blocks before/at render. Any renderer exception marks the **whole plan** failed; `refresh_plan` does not publish partially staged configs.
