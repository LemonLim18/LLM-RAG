# Terminal Prompt Testing Guide

The direct runtime contains 44 canonical operations and 132 vendor templates.
All 38 requested operations are included. Default terminal mode reads `data/`
without a knowledge-pack, binding-record or release activation step.
Use this guide for configuration previews; it does not execute network changes.

For all **38 operations on each vendor**, use [the three-vendor examples](THREE_VENDOR_PROMPTS.md).
The examples below retain the original Cisco baseline.

## Start

From `network_rag_catalog_lab/network_rag_catalog_v2`, with Ollama running:

```powershell
& ../../.venv/Scripts/python.exe -m app.ingest
& ../../.venv/Scripts/python.exe main.py --interactive
```

Ingest once after editing catalog/schema/template files, not before every prompt.
The current files have already been ingested. See `DIRECT_RUNTIME.md` for details.

Paste one example below into the request prompt. Use commas between parameters
and semicolons between separate operations. Examples use explicit field names
and JSON literals to establish a reproducible starting point; then try your own
natural wording to evaluate the model.

The terminal asks one task/device/field question at a time. `select 1` chooses an
option; a bare number is a value. Custom text is accepted through the same validator.
Use `edit TASK_ID FIELD_PATH VALUE` for an explicit correction, `quit` to retain
a session, and `--resume SESSION_ID --interactive` to continue it. Start fresh
sessions after the switch to direct files; published-mode sessions cannot be
resumed as file-mode sessions.

## Available Devices

| Device | Context and supported generation |
| --- | --- |
| R1 | Existing Cisco IOS XE 17.9 router; original capabilities unchanged |
| R2 | Existing Huawei VRP 8 router; original capabilities unchanged |
| R3 | Existing Juniper Junos 23.4 router; original capabilities unchanged |
| SW1 | Synthetic Catalyst 9300 / IOS XE 17.9; all 32 new operations |
| SW2 | Synthetic Huawei VRP context; all 38 requested native generation contracts |
| SW3 | Synthetic Junos ELS context; all 38 requested native generation contracts |

SW records are planned demonstration facts with explicit source references.
They do not describe discovered devices or certify vendor CLI behavior.
Use R1/R2/R3 for legacy examples and the stated SW profiles for additions.
No operation is made portable to an unsupported profile by activation.

SW1 ports 1/0/1 and 1/0/2 are access and trunk; 1/0/3 and 1/0/4 are routed LACP
candidates; 1/0/5 is an addressed routed uplink. SW2 uses `10GE1/0/N`; SW3 uses
`ge-0/0/N`. Change interface names as well as the device when testing another vendor.
Existing resources include VLANs 1/10/20/30, OSPF process 100, ACLs STAFF/GUEST,
classifier VOICE and QoS policy QOS_BASE. Generation leaves those facts unchanged.

## All 44 Operation Examples

Required fields below apply to the example's target. Nested requirements are
shown by the complete list/object values in the prompt; vendor overlays still
apply (for example, Junos BGP needs a peer group).
Expected outcome: the selected operation/device and supplied values validate
and produce a configuration preview. A model-selected operation first requires
confirmation. Missing or conflicting values trigger clarification instead.
The 32 addition examples were exercised through the full deterministic pipeline;
the live checks are listed separately in the activation results.

### VLAN

#### create_vlan

Required: `vlan_id`.
Declared profiles: cisco/iosxe 17.9; huawei/vrp 8; juniper/junos 23.4. Inventory capabilities also apply.

```text
Create VLAN, vlan_id 100, name "STAFF" on R1
```

#### delete_vlan

Required: `vlan_id`.
Declared profiles: cisco/iosxe 17.9; huawei/vrp 8; juniper/junos 23.4. Inventory capabilities also apply.

```text
Delete VLAN, vlan_id 20, name "STAFF" on R1
```

#### modify_vlan

Required: `vlan_id`, `vlan_status`.
Declared profiles: cisco/iosxe 17.9. Inventory capabilities also apply.

```text
Modify VLAN, vlan_id 20, vlan_status "suspend" on SW1
```

#### rename_vlan

Required: `vlan_id`, `new_vlan_name`.
Declared profiles: cisco/iosxe 17.9. Inventory capabilities also apply.

```text
Rename VLAN, vlan_id 20, new_vlan_name "EMPLOYEES" on SW1
```

### Interface

#### set_interface_description

Required: `interface`, `description`.
Declared profiles: cisco/iosxe 17.9; huawei/vrp V200R024C10; juniper/junos 23.4. Inventory capabilities also apply.

```text
Set interface description, interface "GigabitEthernet1/0/1", description "User port" on SW1
```

#### set_interface_admin_state

Required: `interface`, `admin_up`.
Declared profiles: cisco/iosxe 17.9; huawei/vrp V200R024C10; juniper/junos 23.4. Inventory capabilities also apply.

```text
Set interface admin state, interface "GigabitEthernet1/0/1", admin_up false on SW1
```

#### configure_access_port

Required: `interface`, `vlan_id`.
Declared profiles: cisco/iosxe 17.9. Inventory capabilities also apply.

```text
Configure access port, interface "GigabitEthernet1/0/1", vlan_id 20 on SW1
```

#### configure_trunk_port

Required: `interface`, `allowed_vlans`.
Declared profiles: cisco/iosxe 17.9. Inventory capabilities also apply.

```text
Configure trunk port, interface "GigabitEthernet1/0/1", allowed_vlans [1,10,20], native_vlan 1 on SW1
```

#### assign_vlan_to_trunk_port

Required: `interface`, `allowed_vlans`.
Declared profiles: cisco/iosxe 17.9; huawei/vrp V200R024C10; juniper/junos 23.4. Inventory capabilities also apply.

```text
Add VLANs to trunk, interface "GigabitEthernet1/0/2", allowed_vlans [30] on SW1
```

#### configure_trunk_allowed_vlans

Required: `interface`, `allowed_vlans`.
Declared profiles: cisco/iosxe 17.9. Inventory capabilities also apply.

```text
Replace trunk allowed VLANs, interface "GigabitEthernet1/0/2", allowed_vlans [1,20] on SW1
```

#### set_native_vlan

Required: `interface`, `native_vlan`.
Declared profiles: cisco/iosxe 17.9; huawei/vrp V200R024C10; juniper/junos 23.4. Inventory capabilities also apply.

```text
Set native VLAN, interface "GigabitEthernet1/0/2", native_vlan 10 on SW1
```

#### configure_loopback_interface

Required: `interface`, `address`, `prefix_length`.
Declared profiles: cisco/iosxe 17.9. Inventory capabilities also apply.

```text
Configure loopback interface, interface "Loopback99", address "192.0.2.99", prefix_length 32 on SW1
```

#### configure_port_channel

Required: `aggregate_interface`, `member_interfaces`, `lacp_mode`.
Declared profiles: cisco/iosxe 17.9. Inventory capabilities also apply.

```text
Configure routed port channel, aggregate_interface "Port-channel5", member_interfaces ["GigabitEthernet1/0/3","GigabitEthernet1/0/4"], lacp_mode "active" on SW1
```

### Static Routing

#### configure_static_route

Required: `destination`, `next_hop`.
Declared profiles: cisco/iosxe 17.9; huawei/vrp 8; juniper/junos 23.4. Inventory capabilities also apply.

```text
Configure Static Route, destination "198.51.100.0/24", next_hop "192.0.2.2" on R1
```

#### remove_static_route

Required: `destination`, `next_hop`.
Declared profiles: cisco/iosxe 17.9; huawei/vrp 8; juniper/junos 23.4. Inventory capabilities also apply.

```text
Remove Static Route, destination "198.51.100.0/24", next_hop "192.0.2.2" on R1
```

#### add_default_route

Required: `next_hop`.
Declared profiles: cisco/iosxe 17.9; juniper/junos 23.4. Inventory capabilities also apply.

```text
add default route, next_hop "192.0.2.2", preference 200 on SW1
```

#### add_floating_static_route

Required: `destination`, `next_hop`, `preference`.
Declared profiles: cisco/iosxe 17.9; juniper/junos 23.4. Inventory capabilities also apply.

```text
add floating static route, destination "10.50.0.0/16", next_hop "192.0.2.2", preference 200 on SW1
```

### OSPF

#### configure_ospf

Required: `interfaces`, `process_id`.
Declared profiles: cisco/iosxe 17.9; huawei/vrp 8; juniper/junos 23.4. Inventory capabilities also apply.

```text
Configure OSPF, process_id 100, interfaces [{"name":"Ethernet1/1","area":"0"}] on R1
```

#### remove_ospf_interface

Required: `interface`, `area`, `process_id`.
Declared profiles: cisco/iosxe 17.9; huawei/vrp 8; juniper/junos 23.4. Inventory capabilities also apply.

```text
Remove OSPF From Interface, process_id 100, area "0", interface "Ethernet1/1" on R1
```

#### enable_ospf_process

Required: `process_id`, `router_id`.
Declared profiles: cisco/iosxe 17.9. Inventory capabilities also apply.

```text
enable ospf process, process_id 200, router_id "192.0.2.200" on SW1
```

#### set_ospf_router_id

Required: `process_id`, `router_id`.
Declared profiles: cisco/iosxe 17.9. Inventory capabilities also apply.

```text
set ospf router id, process_id 100, router_id "192.0.2.100" on SW1
```

#### create_ospf_area

Required: `process_id`, `area`, `area_type`.
Declared profiles: cisco/iosxe 17.9. Inventory capabilities also apply.

```text
create ospf area, process_id 100, area "1", area_type "stub" on SW1
```

#### assign_interface_to_ospf_area

Required: `process_id`, `interface`, `area`.
Declared profiles: cisco/iosxe 17.9. Inventory capabilities also apply.

```text
assign interface to ospf area, process_id 100, interface "GigabitEthernet1/0/5", area "0" on SW1
```

#### advertise_network

Required: `process_id`, `network_prefix`, `area`.
Declared profiles: cisco/iosxe 17.9. Inventory capabilities also apply.

```text
advertise network, process_id 100, network_prefix "192.0.2.0/24", area "0" on SW1
```

#### configure_passive_interface

Required: `process_id`, `interface`, `passive`.
Declared profiles: cisco/iosxe 17.9. Inventory capabilities also apply.

```text
configure passive interface, process_id 100, interface "GigabitEthernet1/0/5", passive false on SW1
```

#### configure_ospf_redistribution

Required: `process_id`, `redistribution_source`, `route_policy`, `ospf_metric`, `metric_type`.
Declared profiles: cisco/iosxe 17.9. Inventory capabilities also apply.

```text
configure ospf redistribution, process_id 100, redistribution_source "static", route_policy "LIMITED", ospf_metric 20, metric_type "2" on SW1
```

### ACL

#### create_acl

Required: `acl_name`, `description`.
Declared profiles: cisco/iosxe 17.9. Inventory capabilities also apply.

```text
create acl, acl_name "NEW_ACL", description "Reviewed policy" on SW1
```

#### add_acl_rule

Required: `acl_name`, `acl_rule_id`, `acl_action`, `source_prefix`, `destination_prefix`, `ip_protocol`.
Declared profiles: cisco/iosxe 17.9. Inventory capabilities also apply.

```text
add acl rule, acl_name "STAFF", acl_rule_id 20, acl_action "permit", source_prefix "10.1.0.0/16", destination_prefix "10.2.0.0/16", ip_protocol "tcp", destination_port 443, log false on SW1
```

#### modify_acl_rule

Required: `acl_name`, `acl_rule_id`, `acl_action`, `source_prefix`, `destination_prefix`, `ip_protocol`.
Declared profiles: cisco/iosxe 17.9. Inventory capabilities also apply.

```text
modify acl rule, acl_name "STAFF", acl_rule_id 10, acl_action "permit", source_prefix "10.1.0.0/16", destination_prefix "10.2.0.0/16", ip_protocol "tcp", destination_port 443, log false on SW1
```

#### delete_acl_rule

Required: `acl_name`, `acl_rule_id`.
Declared profiles: cisco/iosxe 17.9. Inventory capabilities also apply.

```text
delete acl rule, acl_name "STAFF", acl_rule_id 10 on SW1
```

#### apply_acl_to_interface

Required: `acl_name`, `interface`, `direction`.
Declared profiles: cisco/iosxe 17.9. Inventory capabilities also apply.

```text
apply acl to interface, acl_name "STAFF", interface "GigabitEthernet1/0/5", direction "ingress" on SW1
```

### QoS

#### create_qos_policy

Required: `policy_name`, `policy_terms`.
Declared profiles: cisco/iosxe 17.9. Inventory capabilities also apply.

```text
create qos policy, policy_name "NEW_QOS", policy_terms [{"classifier_name":"VOICE","bandwidth_bps":20000000}] on SW1
```

#### create_classifier

Required: `classifier_name`, `dscp_values`, `match_mode`.
Declared profiles: cisco/iosxe 17.9. Inventory capabilities also apply.

```text
create classifier, classifier_name "NEW_CLASS", dscp_values [46,34], match_mode "any" on SW1
```

#### classify_by_dscp

Required: `classifier_name`, `dscp_values`, `previous_dscp_values`.
Declared profiles: cisco/iosxe 17.9. Inventory capabilities also apply.

```text
classify by dscp, classifier_name "VOICE", dscp_values [46], previous_dscp_values [46] on SW1
```

#### configure_scheduler

Required: `policy_name`, `classifier_name`, `bandwidth_bps`.
Declared profiles: cisco/iosxe 17.9. Inventory capabilities also apply.

```text
configure scheduler, policy_name "QOS_BASE", classifier_name "VOICE", bandwidth_bps 30000000 on SW1
```

#### configure_shaping

Required: `policy_name`, `interface`, `rate_bps`, `direction`.
Declared profiles: cisco/iosxe 17.9. Inventory capabilities also apply.

```text
configure shaping, policy_name "NEW_SHAPER", interface "GigabitEthernet1/0/5", rate_bps 100000000, direction "egress" on SW1
```

#### configure_policing

Required: `policy_name`, `interface`, `rate_bps`, `burst_bytes`, `direction`, `exceed_action`.
Declared profiles: cisco/iosxe 17.9. Inventory capabilities also apply.

```text
configure policing, policy_name "NEW_POLICER", interface "GigabitEthernet1/0/5", rate_bps 100000000, burst_bytes 10000, direction "ingress", exceed_action "drop" on SW1
```

#### apply_qos_policy_to_interface

Required: `policy_name`, `interface`, `direction`.
Declared profiles: cisco/iosxe 17.9. Inventory capabilities also apply.

```text
apply qos policy to interface, policy_name "QOS_BASE", interface "GigabitEthernet1/0/5", direction "egress" on SW1
```

### Interface IPv4 (Preserved)

#### configure_interface_ip

Required: `interface`, `address`, `prefix_length`.
Declared profiles: cisco/iosxe 17.9; huawei/vrp 8; juniper/junos 23.4. Inventory capabilities also apply.

```text
Configure Interface IPv4 Address, interface "Ethernet1/1", address "192.0.2.1", prefix_length 24 on R1
```

#### remove_interface_ip

Required: `interface`, `address`, `prefix_length`.
Declared profiles: cisco/iosxe 17.9; huawei/vrp 8; juniper/junos 23.4. Inventory capabilities also apply.

```text
Remove Interface IPv4 Address, interface "Ethernet1/1", address "192.0.2.1", prefix_length 24 on R1
```

### BGP (Preserved)

#### configure_bgp_neighbor

Required: `local_as`, `neighbor_ip`, `remote_as`.
Declared profiles: cisco/iosxe 17.9; huawei/vrp 8; juniper/junos 23.4. Inventory capabilities also apply.

```text
Configure BGP Neighbor, local_as 65000, neighbor_ip "192.0.2.2", remote_as 65001, peer_group "TRANSIT" on R1
```

#### remove_bgp_neighbor

Required: `local_as`, `neighbor_ip`, `remote_as`.
Declared profiles: cisco/iosxe 17.9; huawei/vrp 8; juniper/junos 23.4. Inventory capabilities also apply.

```text
Remove BGP Neighbor, local_as 65000, neighbor_ip "192.0.2.2", remote_as 65001, peer_group "TRANSIT" on R1
```

### IS-IS (Preserved)

#### configure_isis_interface

Required: `interface`, `level`.
Declared profiles: cisco/iosxe 17.9; huawei/vrp 8; juniper/junos 23.4. Inventory capabilities also apply.

```text
Configure IS-IS Interface, level "level-2", process_name "CORE", interface "ge-0/0/0" on R3
```

#### disable_isis_interface

Required: `interface`.
Declared profiles: cisco/iosxe 17.9; huawei/vrp 8; juniper/junos 23.4. Inventory capabilities also apply.

```text
Disable IS-IS Interface, process_name "CORE", interface "ge-0/0/0" on R3
```

## Clarification and Multiple Intents

```text
Configure OSPF on R2
Create VLAN 100 named STAFF
Create VLAN 100 named STAFF on the KL core router
Configure IP address 10.10.10.1/24 on GigabitEthernet1/0/1 on R1
Create VLAN 100 named STAFF on R1 and R2; set interface description, interface "GigabitEthernet1/0/1", description "User port" on SW1
```

These check missing parameters, missing target, ambiguous device, invalid interface
and independent operation/device scope respectively. The incomplete cases must
produce no configuration. For the first request, supply process 100 and interfaces
`[{"name":"GigabitEthernet0/0/0","area":"0"}]` when each field is requested.
An invalid value must leave already accepted fields intact.

For free-form RAG checks, try:

```text
Give the VLAN a different label: vlan_id 20, name "ENGINEERING" on SW1
For static routing, send unmatched IPv4 traffic through next_hop "192.0.2.2" with preference 200 on SW1
```

A semantic operation proposal requires confirmation. If the model cannot decide,
select the intended catalog operation; this is recorded as clarification, not
evidence of automatic interpretation accuracy.

## Current Limits

- All requested IDs have three vendor templates, but inputs and exact feature semantics differ; use the vendor examples.
- One incomplete task blocks rendering for the whole request.
- Same-request create/use chains do not simulate device state. Creating NEW_ACL does not establish it as a confirmed resource for another task.
- VLAN modification is Cisco state or Huawei/Juniper description; OSPF area creation is stub-only; redistribution requires a bounded route policy.
- ACL modification replaces a complete rule. Missing matches never mean permit-any.
- QoS inputs use integer bps/bytes and reviewed direction/policy relationships; arbitrary application-bandwidth intent is outside this catalog.
- Physical-device behavior and general weak-model accuracy remain unverified beyond the recorded checks.
- Use direct-file mode; the retained published release does not include these new templates. No further expansion is needed to begin prompting.
