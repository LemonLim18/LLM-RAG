# Requested Operation Coverage

Direct-file runtime, corrected 2026-10-08. Supersedes the earlier Huawei 10/38 and Juniper
12/38 audit.

| Requested scope | Cisco | Huawei | Juniper |
| --- | --- | --- | --- |
| Canonical operation IDs available to RAG | 38 | 38 | 38 |
| Implemented generation templates | 38 | 37 | 37 |
| Missing templates in requested list | 0 | 1 | 1 |

The repository contains 44 operations and 130 template files in total, retaining
the six additional IP/BGP/IS-IS operations. There are no placeholder templates.
The requested 38 have 112 concrete vendor-operation templates.

- `add_default_route`: Cisco, Huawei, Juniper
- `add_floating_static_route`: Cisco, Huawei, Juniper
- `create_acl`: Cisco, Huawei, Juniper
- `add_acl_rule`: Cisco, Huawei, Juniper
- `modify_acl_rule`: Cisco, Huawei, Juniper
- `delete_acl_rule`: Cisco, Huawei, Juniper
- `apply_acl_to_interface`: Cisco, Huawei, Juniper
- `enable_ospf_process`: Cisco, Huawei, Juniper
- `set_ospf_router_id`: Cisco, Huawei, Juniper
- `create_ospf_area`: Cisco, Huawei, Juniper
- `assign_interface_to_ospf_area`: Cisco, Huawei, Juniper
- `advertise_network`: Cisco, Huawei, Juniper
- `configure_passive_interface`: Cisco, Huawei, Juniper
- `configure_ospf_redistribution`: Cisco, Huawei, Juniper
- `set_interface_description`: Cisco, Huawei, Juniper
- `set_interface_admin_state`: Cisco, Huawei, Juniper
- `configure_access_port`: Cisco, Huawei, Juniper
- `configure_trunk_port`: Cisco, Huawei, Juniper
- `assign_vlan_to_trunk_port`: Cisco, Huawei, Juniper
- `configure_trunk_allowed_vlans`: Cisco, Huawei, Juniper
- `set_native_vlan`: Cisco, Huawei, Juniper
- `configure_loopback_interface`: Cisco, Huawei, Juniper
- `configure_port_channel`: Cisco, Huawei, Juniper
- `create_qos_policy`: Cisco, Huawei, Juniper
- `create_classifier`: Cisco, Huawei, Juniper
- `classify_by_dscp`: Cisco, Huawei, Juniper
- `configure_scheduler`: Cisco, Huawei, Juniper
- `configure_shaping`: Cisco, Huawei, Juniper
- `configure_policing`: Cisco, Huawei, Juniper
- `apply_qos_policy_to_interface`: Cisco, Huawei, Juniper
- `modify_vlan`: Cisco; Huawei and Juniper blocked pending equivalent state semantics
- `rename_vlan`: Cisco, Huawei, Juniper
- `create_vlan`: Cisco, Huawei, Juniper
- `delete_vlan`: Cisco, Huawei, Juniper
- `configure_static_route`: Cisco, Huawei, Juniper
- `remove_static_route`: Cisco, Huawei, Juniper
- `configure_ospf`: Cisco, Huawei, Juniper
- `remove_ospf_interface`: Cisco, Huawei, Juniper

## What Coverage Means

Coverage is at the canonical intent level, using native vendor contracts. It does
not mean identical parameters, every feature variant, every hardware model or
certified device behavior. `modify_vlan` always means state change. The former
Huawei/Juniper description substitution was incorrect and has been removed.

Junos uses default-instance/interface OSPF and native scheduler maps; Huawei QoS
uses classifiers, behaviors and queue weights. Schemas collect those actual
inputs. Missing facts and conflicting resources still prevent unsafe previews.

Use SW1, SW2 and SW3 for the prepared examples. The original R1/R2/R3 inventory
is unchanged; it does not gain capabilities merely because templates exist.

See [complete vendor prompts and contract differences](THREE_VENDOR_PROMPTS.md)
and [implementation notes](MULTIVENDOR_RUNTIME.md). No pack import, publication,
SQLite change or activation step is required.
