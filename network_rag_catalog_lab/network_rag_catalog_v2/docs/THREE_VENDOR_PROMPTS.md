# Three-Vendor Terminal Examples

The direct-file runtime has all 38 requested operations for Cisco, Huawei and
Juniper. These are configuration-generation contracts, not device certifications.
Use SW1 (Cisco), SW2 (Huawei), or SW3 (Juniper), whose inventory is synthetic.
R1/R2/R3 retain their original capabilities and are not silently upgraded.

Start from the v2 directory:

```powershell
& ../../.venv/Scripts/python.exe main.py --interactive
```

Start a fresh session. The current files are indexed by `python -m app.ingest`;
run ingestion again only after editing catalog/schema/template files.
No pack import, SQLite write, release or activation is required.

Paste one example at a time. Commas separate parameters; semicolons separate
operations. These explicit-field examples establish a reproducible baseline;
paraphrase them afterwards to evaluate your local LLM.
Missing parameters still trigger one field-scoped question at a time.
Use `select 1` for a suggested option, or enter a custom value. No configurations
are released while any task in the request still needs clarification.
The examples do not mutate inventory or execute devices: each starts against
the same planned snapshot, not against the output of the preceding example.

## Vendor Semantics

- `modify_vlan`: Cisco changes active/suspend; Huawei/Juniper edit description.
  VLAN suspend is not a portable operation. Junos rename/edit asks for the
  existing VLAN object name and checks it against vlan_id.
- Junos OSPF uses the default instance, areas and logical interfaces, not a
  numeric process ID. Router-ID edits affect that routing instance and do not
  restart protocols. Network advertisement confirms the matching interfaces.
- ACL rule modification is full replacement, not a partial patch. Junos
  rule-N term names and insertion order must match inventory. Huawei
  traffic-filter leaves unmatched traffic permitted; the attachment schema
  requires explicit acknowledgement, rather than pretending Cisco semantics.
- QoS uses native contracts: Cisco policy classes, Huawei classifiers/behaviors
  and WRR weights, Junos forwarding classes/schedulers/maps. A WRR weight is
  not a bandwidth guarantee. Read the native fields in each example.
- Huawei policing applies only to its explicitly named classifier. CIR and PIR
  both use rate_bps; CBS and PBS both use burst_bytes, with excess discarded.
- Junos policy attachment selects an egress scheduler map; the optional
  classifier_name additionally attaches the DSCP classifier on ingress.
- Aggregation requires clean member ports; Junos ae indices must fit the
  already recorded aggregate-device count. No implicit deletion is performed.
- These previews still need exact hardware/NOS command validation before any
  real deployment. There is no execution or automatic commit.

## Clarification Example

```text
Create VLAN 100 named TEST on SW2; rename vlan, vlan_id 20, new_vlan_name "EMPLOYEES" on SW3
```

The Juniper task asks for `current_vlan_name`, offers `STAFF` from inventory,
and checks your selection. Until you answer, neither task is rendered.

## Cisco: 38 Operations

### vlan

**modify_vlan**

```text
modify vlan, vlan_id 20, vlan_status "suspend" on SW1
```

**rename_vlan**

```text
rename vlan, vlan_id 20, new_vlan_name "EMPLOYEES" on SW1
```

**create_vlan**

```text
create vlan, vlan_id 100, name "NEW_STAFF" on SW1
```

**delete_vlan**

```text
delete vlan, vlan_id 20, name "STAFF" on SW1
```

### interface

**set_interface_description**

```text
set interface description, interface "GigabitEthernet1/0/1", description "User port" on SW1
```

**set_interface_admin_state**

```text
set interface admin state, interface "GigabitEthernet1/0/1", admin_up false on SW1
```

**configure_access_port**

```text
configure access port, interface "GigabitEthernet1/0/1", vlan_id 20 on SW1
```

**configure_trunk_port**

```text
configure trunk port, interface "GigabitEthernet1/0/1", allowed_vlans [1,10,20], native_vlan 1 on SW1
```

**assign_vlan_to_trunk_port**

```text
assign vlan to trunk port, interface "GigabitEthernet1/0/2", allowed_vlans [30] on SW1
```

**configure_trunk_allowed_vlans**

```text
configure trunk allowed vlans, interface "GigabitEthernet1/0/2", allowed_vlans [1,20] on SW1
```

**set_native_vlan**

```text
set native vlan, interface "GigabitEthernet1/0/2", native_vlan 10 on SW1
```

**configure_loopback_interface**

```text
configure loopback interface, interface "Loopback99", address "192.0.2.99", prefix_length 32 on SW1
```

**configure_port_channel**

```text
configure port channel, aggregate_interface "Port-channel5", member_interfaces ["GigabitEthernet1/0/3","GigabitEthernet1/0/4"], lacp_mode "active" on SW1
```

### static_routing

**add_default_route**

```text
add default route, next_hop "192.0.2.2", preference 200 on SW1
```

**add_floating_static_route**

```text
add floating static route, destination "10.50.0.0/16", next_hop "192.0.2.2", preference 200 on SW1
```

**configure_static_route**

```text
configure static route, destination "10.60.0.0/16", next_hop "192.0.2.2", preference 100 on SW1
```

**remove_static_route**

```text
remove static route, destination "10.50.0.0/16", next_hop "192.0.2.3" on SW1
```

### ospf

**enable_ospf_process**

```text
enable ospf process, process_id 200, router_id "192.0.2.200" on SW1
```

**set_ospf_router_id**

```text
set ospf router id, process_id 100, router_id "192.0.2.100" on SW1
```

**create_ospf_area**

```text
create ospf area, process_id 100, area "1", area_type "stub" on SW1
```

**assign_interface_to_ospf_area**

```text
assign interface to ospf area, process_id 100, interface "GigabitEthernet1/0/5", area "0" on SW1
```

**advertise_network**

```text
advertise network, process_id 100, network_prefix "192.0.2.0/24", area "0" on SW1
```

**configure_passive_interface**

```text
configure passive interface, process_id 100, interface "GigabitEthernet1/0/5", passive false on SW1
```

**configure_ospf_redistribution**

```text
configure ospf redistribution, process_id 100, redistribution_source "static", route_policy "LIMITED", ospf_metric 20, metric_type "2" on SW1
```

**configure_ospf**

```text
configure ospf, process_id 100, router_id "192.0.2.10", interfaces [{"name":"GigabitEthernet1/0/5","area":"0"}] on SW1
```

**remove_ospf_interface**

```text
remove ospf interface, process_id 100, interface "GigabitEthernet1/0/5", area "0" on SW1
```

### acl

**create_acl**

```text
create acl, acl_name "NEW_ACL", description "Reviewed policy" on SW1
```

**add_acl_rule**

```text
add acl rule, acl_name "STAFF", acl_rule_id 20, acl_action "permit", source_prefix "10.1.0.0/16", destination_prefix "10.2.0.0/16", ip_protocol "tcp", destination_port 443, log false on SW1
```

**modify_acl_rule**

```text
modify acl rule, acl_name "STAFF", acl_rule_id 10, acl_action "permit", source_prefix "10.1.0.0/16", destination_prefix "10.2.0.0/16", ip_protocol "tcp", destination_port 443, log false on SW1
```

**delete_acl_rule**

```text
delete acl rule, acl_name "STAFF", acl_rule_id 10 on SW1
```

**apply_acl_to_interface**

```text
apply acl to interface, acl_name "STAFF", interface "GigabitEthernet1/0/5", direction "ingress" on SW1
```

### qos

**create_qos_policy**

```text
create qos policy, policy_name "NEW_QOS", policy_terms [{"classifier_name":"VOICE","bandwidth_bps":20000000}] on SW1
```

**create_classifier**

```text
create classifier, classifier_name "NEW_CLASS", dscp_values [46,34], match_mode "any" on SW1
```

**classify_by_dscp**

```text
classify by dscp, classifier_name "VOICE", dscp_values [46], previous_dscp_values [46] on SW1
```

**configure_scheduler**

```text
configure scheduler, policy_name "QOS_BASE", classifier_name "VOICE", bandwidth_bps 30000000 on SW1
```

**configure_shaping**

```text
configure shaping, policy_name "NEW_SHAPER", interface "GigabitEthernet1/0/5", rate_bps 100000000, direction "egress" on SW1
```

**configure_policing**

```text
configure policing, policy_name "NEW_POLICER", interface "GigabitEthernet1/0/5", rate_bps 100000000, burst_bytes 10000, direction "ingress", exceed_action "drop" on SW1
```

**apply_qos_policy_to_interface**

```text
apply qos policy to interface, policy_name "QOS_BASE", interface "GigabitEthernet1/0/5", direction "egress" on SW1
```

## Huawei: 38 Operations

### vlan

**modify_vlan**

```text
modify vlan, vlan_id 20, description "Staff department" on SW2
```

**rename_vlan**

```text
rename vlan, vlan_id 20, new_vlan_name "EMPLOYEES" on SW2
```

**create_vlan**

```text
create vlan, vlan_id 100, name "NEW_STAFF" on SW2
```

**delete_vlan**

```text
delete vlan, vlan_id 20, name "STAFF" on SW2
```

### interface

**set_interface_description**

```text
set interface description, interface "10GE1/0/1", description "User port" on SW2
```

**set_interface_admin_state**

```text
set interface admin state, interface "10GE1/0/1", admin_up false on SW2
```

**configure_access_port**

```text
configure access port, interface "10GE1/0/1", vlan_id 20 on SW2
```

**configure_trunk_port**

```text
configure trunk port, interface "10GE1/0/1", allowed_vlans [1,10,20], native_vlan 1 on SW2
```

**assign_vlan_to_trunk_port**

```text
assign vlan to trunk port, interface "10GE1/0/2", allowed_vlans [30] on SW2
```

**configure_trunk_allowed_vlans**

```text
configure trunk allowed vlans, interface "10GE1/0/2", allowed_vlans [1,20] on SW2
```

**set_native_vlan**

```text
set native vlan, interface "10GE1/0/2", native_vlan 10 on SW2
```

**configure_loopback_interface**

```text
configure loopback interface, interface "LoopBack99", address "192.0.2.99", prefix_length 32 on SW2
```

**configure_port_channel**

```text
configure port channel, aggregate_interface "Eth-Trunk5", member_interfaces ["10GE1/0/3","10GE1/0/4"], lacp_mode "active" on SW2
```

### static_routing

**add_default_route**

```text
add default route, next_hop "192.0.2.2", preference 200 on SW2
```

**add_floating_static_route**

```text
add floating static route, destination "10.50.0.0/16", next_hop "192.0.2.2", preference 200 on SW2
```

**configure_static_route**

```text
configure static route, destination "10.60.0.0/16", next_hop "192.0.2.2", preference 100 on SW2
```

**remove_static_route**

```text
remove static route, destination "10.50.0.0/16", next_hop "192.0.2.3" on SW2
```

### ospf

**enable_ospf_process**

```text
enable ospf process, process_id 200, router_id "192.0.2.200" on SW2
```

**set_ospf_router_id**

```text
set ospf router id, process_id 100, router_id "192.0.2.100" on SW2
```

**create_ospf_area**

```text
create ospf area, process_id 100, area "1", area_type "stub" on SW2
```

**assign_interface_to_ospf_area**

```text
assign interface to ospf area, process_id 100, interface "10GE1/0/5", area "0" on SW2
```

**advertise_network**

```text
advertise network, process_id 100, network_prefix "192.0.2.0/24", area "0" on SW2
```

**configure_passive_interface**

```text
configure passive interface, process_id 100, interface "10GE1/0/5", passive false on SW2
```

**configure_ospf_redistribution**

```text
configure ospf redistribution, process_id 100, redistribution_source "static", route_policy "LIMITED", ospf_metric 20, metric_type "2" on SW2
```

**configure_ospf**

```text
configure ospf, process_id 100, router_id "192.0.2.10", interfaces [{"name":"10GE1/0/5","area":"0"}] on SW2
```

**remove_ospf_interface**

```text
remove ospf interface, process_id 100, interface "10GE1/0/5", area "0" on SW2
```

### acl

**create_acl**

```text
create acl, acl_name "NEW_ACL", description "Reviewed policy" on SW2
```

**add_acl_rule**

```text
add acl rule, acl_name "STAFF", acl_rule_id 20, acl_action "permit", source_prefix "10.1.0.0/16", destination_prefix "10.2.0.0/16", ip_protocol "tcp", destination_port 443 on SW2
```

**modify_acl_rule**

```text
modify acl rule, acl_name "STAFF", acl_rule_id 10, acl_action "permit", source_prefix "10.1.0.0/16", destination_prefix "10.2.0.0/16", ip_protocol "tcp", destination_port 443 on SW2
```

**delete_acl_rule**

```text
delete acl rule, acl_name "STAFF", acl_rule_id 10 on SW2
```

**apply_acl_to_interface**

```text
apply acl to interface, acl_name "STAFF", interface "10GE1/0/5", direction "ingress", unmatched_action "permit" on SW2
```

### qos

**create_qos_policy**

```text
create qos policy, policy_name "NEW_QOS", policy_terms [{"classifier_name":"VOICE","behavior_name":"VOICE_BEHAVIOR"}] on SW2
```

**create_classifier**

```text
create classifier, classifier_name "NEW_CLASS", dscp_values [46,34], match_mode "any" on SW2
```

**classify_by_dscp**

```text
classify by dscp, classifier_name "VOICE", dscp_values [46], previous_dscp_values [46] on SW2
```

**configure_scheduler**

```text
configure scheduler, interface "10GE1/0/5", queue_id 4, scheduler_weight 20 on SW2
```

**configure_shaping**

```text
configure shaping, interface "10GE1/0/5", rate_bps 100000000, direction "egress" on SW2
```

**configure_policing**

```text
configure policing, policy_name "NEW_POLICER", interface "10GE1/0/5", rate_bps 100000000, burst_bytes 10000, direction "ingress", exceed_action "drop", classifier_name "VOICE", behavior_name "NEW_CAR" on SW2
```

**apply_qos_policy_to_interface**

```text
apply qos policy to interface, policy_name "QOS_BASE", interface "10GE1/0/5", direction "egress" on SW2
```

## Juniper: 38 Operations

### vlan

**modify_vlan**

```text
modify vlan, vlan_id 20, description "Staff department", current_vlan_name "STAFF" on SW3
```

**rename_vlan**

```text
rename vlan, vlan_id 20, new_vlan_name "EMPLOYEES", current_vlan_name "STAFF" on SW3
```

**create_vlan**

```text
create vlan, vlan_id 100, name "NEW_STAFF" on SW3
```

**delete_vlan**

```text
delete vlan, vlan_id 20, name "STAFF" on SW3
```

### interface

**set_interface_description**

```text
set interface description, interface "ge-0/0/1", description "User port" on SW3
```

**set_interface_admin_state**

```text
set interface admin state, interface "ge-0/0/1", admin_up false on SW3
```

**configure_access_port**

```text
configure access port, interface "ge-0/0/1", vlan_id 20 on SW3
```

**configure_trunk_port**

```text
configure trunk port, interface "ge-0/0/1", allowed_vlans [1,10,20], native_vlan 1 on SW3
```

**assign_vlan_to_trunk_port**

```text
assign vlan to trunk port, interface "ge-0/0/2", allowed_vlans [30] on SW3
```

**configure_trunk_allowed_vlans**

```text
configure trunk allowed vlans, interface "ge-0/0/2", allowed_vlans [1,20] on SW3
```

**set_native_vlan**

```text
set native vlan, interface "ge-0/0/2", native_vlan 10 on SW3
```

**configure_loopback_interface**

```text
configure loopback interface, interface "lo0", address "192.0.2.99", prefix_length 32 on SW3
```

**configure_port_channel**

```text
configure port channel, aggregate_interface "ae5", member_interfaces ["ge-0/0/3","ge-0/0/4"], lacp_mode "active" on SW3
```

### static_routing

**add_default_route**

```text
add default route, next_hop "192.0.2.2", preference 200 on SW3
```

**add_floating_static_route**

```text
add floating static route, destination "10.50.0.0/16", next_hop "192.0.2.2", preference 200 on SW3
```

**configure_static_route**

```text
configure static route, destination "10.60.0.0/16", next_hop "192.0.2.2", preference 100 on SW3
```

**remove_static_route**

```text
remove static route, destination "10.50.0.0/16", next_hop "192.0.2.3" on SW3
```

### ospf

**enable_ospf_process**

```text
enable ospf process, router_id "192.0.2.200", interface "ge-0/0/5", area "0" on SW3
```

**set_ospf_router_id**

```text
set ospf router id, router_id "192.0.2.100" on SW3
```

**create_ospf_area**

```text
create ospf area, area "1", area_type "stub" on SW3
```

**assign_interface_to_ospf_area**

```text
assign interface to ospf area, interface "ge-0/0/5", area "0" on SW3
```

**advertise_network**

```text
advertise network, network_prefix "192.0.2.0/24", area "0", network_interfaces ["ge-0/0/5"] on SW3
```

**configure_passive_interface**

```text
configure passive interface, interface "ge-0/0/5", passive false, area "0" on SW3
```

**configure_ospf_redistribution**

```text
configure ospf redistribution, redistribution_source "static", route_policy "LIMITED", ospf_metric 20, metric_type "2", export_policy_name "OSPF_EXPORT" on SW3
```

**configure_ospf**

```text
configure ospf, router_id "192.0.2.10", interfaces [{"name":"ge-0/0/5","area":"0"}] on SW3
```

**remove_ospf_interface**

```text
remove ospf interface, interface "ge-0/0/5", area "0" on SW3
```

### acl

**create_acl**

```text
create acl, acl_name "NEW_ACL" on SW3
```

**add_acl_rule**

```text
add acl rule, acl_name "STAFF", acl_rule_id 20, acl_action "permit", source_prefix "10.1.0.0/16", destination_prefix "10.2.0.0/16", ip_protocol "tcp", destination_port 443, log false, next_rule_id 0 on SW3
```

**modify_acl_rule**

```text
modify acl rule, acl_name "STAFF", acl_rule_id 10, acl_action "permit", source_prefix "10.1.0.0/16", destination_prefix "10.2.0.0/16", ip_protocol "tcp", destination_port 443, log false, next_rule_id 0 on SW3
```

**delete_acl_rule**

```text
delete acl rule, acl_name "STAFF", acl_rule_id 10 on SW3
```

**apply_acl_to_interface**

```text
apply acl to interface, acl_name "STAFF", interface "ge-0/0/5", direction "ingress", logical_unit 0 on SW3
```

### qos

**create_qos_policy**

```text
create qos policy, policy_name "NEW_QOS", policy_terms [{"forwarding_class":"expedited-forwarding","scheduler_name":"VOICE_SCHED"}] on SW3
```

**create_classifier**

```text
create classifier, classifier_name "NEW_CLASS", dscp_values [46,34], match_mode "any", forwarding_class "expedited-forwarding", loss_priority "low" on SW3
```

**classify_by_dscp**

```text
classify by dscp, classifier_name "VOICE", dscp_values [46], previous_dscp_values [46], forwarding_class "expedited-forwarding", loss_priority "low" on SW3
```

**configure_scheduler**

```text
configure scheduler, scheduler_name "NEW_SCHED", bandwidth_bps 30000000 on SW3
```

**configure_shaping**

```text
configure shaping, interface "ge-0/0/5", rate_bps 100000000, direction "egress" on SW3
```

**configure_policing**

```text
configure policing, policy_name "NEW_POLICER", interface "ge-0/0/5", rate_bps 100000000, burst_bytes 10000, direction "ingress", exceed_action "drop", logical_unit 0 on SW3
```

**apply_qos_policy_to_interface**

```text
apply qos policy to interface, policy_name "QOS_BASE", interface "ge-0/0/5", direction "egress", classifier_name "VOICE" on SW3
```
