# Template Review Sources

Reviewed 2026-09-29. References support candidate command semantics, not physical
device certification. Exact model/NOS/license lab acceptance remains separate.

## Cisco

- VLAN state/name and reserved identities:
  [Catalyst 9300 IOS XE 17.9 VLAN guide](https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9300/software/release/17-9/configuration_guide/vlan/b_179_vlan_9300_cg/configuring_vlans.html).
  Edits are limited to non-default normal-range IDs and recorded VTP transparent mode.
- Trunk add versus replace:
  [17.9 VLAN reference](https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9300/software/release/17-9/configuration_guide/vlan/b_179_vlan_9300_cg.pdf).
- Routed LACP:
  [17.9 EtherChannel guide](https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9300/software/release/17-9/configuration_guide/lyr2/b_179_lyr2_9300_cg/configuring_etherchannels.html).
  Members need recorded compatible attributes and empty address/service bindings.
- Interface properties:
  [17.9 interface reference](https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9300/software/release/17-9/command_reference/b_179_9300_cr/interface_and_hardware_commands.html).
- OSPF process, interface, area and passive behavior:
  [17.9 OSPF guide](https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9300/software/release/17-9/configuration_guide/rtng/b_179_rtng_9300_cg/configuring_ospf.html).
  Area creation is stub-only; router-ID changes do not trigger process restart.
- Static/default routes and route-map redistribution:
  [17.9 protocol-independent features](https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9300/software/release/17-9/configuration_guide/rtng/b_179_rtng_9300_cg/protocol_independent_features.html).
- Extended IPv4 ACEs, remarks and attachments:
  [17.9 IPv4 ACL guide](https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9300/software/release/17-9/configuration_guide/sec/b_179_sec_9300_cg/configuring_ipv4_acls.html).
  Full replacement has a possible transient enforcement gap; generation is not execution.
- DSCP classification, bandwidth, shaping and policing:
  [17.9 QoS guide](https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9300/software/release/17-9/configuration_guide/qos/b_179_qos_9300_cg/configuring_qos.html).
  Contracts use bps and burst bytes, with exact whole-kbps conversion for bandwidth.
- Exact DSCP removal:
  [IOS QoS match reference](https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/qos/command/qos-cr-book/qos-m1.pdf).
  The old list must be explicit and confirmed before replacement.

## Huawei

- Exact product-family/release VLAN example:
  [CE9800/8800/6800/5800 V200R024C10 port VLAN assignment](https://info.support.huawei.com/enterprise/en/doc/EDOC1100468591/526f31bd/example-for-assigning-vlans-based-on-ports).
  Search extraction was available; direct fetching returned HTTP 403 during review.
- Additive trunk membership:
  [Port trunk allow-pass reference](https://info.support.huawei.com/hedex/api/pages/EDOC1100210438/AEK0901G/09/resources/dc/port_trunk_allow-pass_vlan.html).
- Native VLAN:
  [VLAN configuration procedure](https://info.support.huawei.com/hedex/api/pages/EDOC1000053358/YEF0907R/25/resources/en-us_task_0133041564.html).
- Interface property context:
  [CloudEngine V200R024C10 interface configuration](https://info.support.huawei.com/enterprise/en/doc/EDOC1100468735/73f4f197/configuring-ip-addresses-on-an-interface).
  This is CE12800, not CE6800 hardware acceptance. Exact CE6800 description/admin
  command-reference and lab sign-off remain activation gates; candidate tests
  establish schema/render behavior only.

No Huawei ACL, QoS, aggregation or routing expansion binding is asserted by these
sources. Legacy Huawei bindings are unchanged.

## Juniper

- Numeric VLAN members and ELS native scope:
  [VLAN mapping](https://www.juniper.net/documentation/us/en/software/junos/open-config/topics/concept/openconfig-vlan-mapping.html),
  [Members statement](https://www.juniper.net/documentation/us/en/software/junos/cli-reference/topics/ref/statement/members-edit-interfaces-qfx-series.html).
  New mutations require an existing trunk and confirmed Ethernet-switching unit 0.
- Physical description/admin state:
  [Interface properties](https://www.juniper.net/documentation/us/en/software/junos/interfaces-fundamentals/topics/topic-map/physical-interface-properties.html),
  [Disable statement](https://www.juniper.net/documentation/us/en/software/junos/cli-reference/topics/ref/statement/disable-edit-interfaces.html).
- Per-next-hop preference:
  [Static-route preferences and qualified next hops](https://www.juniper.net/documentation/us/en/software/junos/static-routing/topics/topic-map/static-route-prefer-qualified-next-hop.html).
  Floating routes use qualified next hops, not a prefix-wide preference mutation.

Do not extrapolate these references to Juniper VLAN rename, Cisco-style OSPF
process creation, MQC policies or Cisco LACP modes. Those bindings are absent.
