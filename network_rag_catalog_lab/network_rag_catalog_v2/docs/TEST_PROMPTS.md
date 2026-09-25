# Test Prompts

Run these after `python -m app.ingest`. Add `--interactive` to test a
clarification conversation or `--no-interactive` to inspect the JSON session.

```text
Create VLAN 100 named STAFF on R1
Delete VLAN 100 named STAFF on R3

Configure OSPF process 100 on Ethernet1/1 in area 0 on R1
Configure OSPF on ge-0/0/0 in area 0 on R3
Remove OSPF process 100 from Ethernet1/1 in area 0 on R1

Configure BGP neighbor 192.0.2.2 with local AS 65000 and remote AS 65001 on R1
Remove BGP neighbor 192.0.2.2 with local AS 65000 and remote AS 65001 in peer group EBGP-PEER on R3

Enable IS-IS process CORE on ge-0/0/0 at level 2 on R3
Disable IS-IS on ge-0/0/0 on R3

Add static route to 10.20.0.0/16 through 192.168.1.1 on R3
Remove static route to 10.20.0.0/16 via 192.168.1.1 on R3

Configure IP address 192.0.2.1/24 on Ethernet1/1 on R1
Remove IP address 192.0.2.1/24 from Ethernet1/1 on R1
```

Clarification and inventory checks:

```text
Configure OSPF on R2
Configure IP address 10.10.10.1/24 on GigabitEthernet1/0/1 on R1
Create VLAN 200 named GUEST on core routers
Create VLAN 300 named TEST on Router 9
```

For the second prompt, reply `select 1` in terminal mode to choose the first offered
interface. Answer each OSPF field when requested: `GigabitEthernet0/0/0 in area 0`
for interfaces, then `100` for the process ID. Bare numbers are values, not choices.

## Inventory-context targets

| Prompt | Expected outcome / follow-up |
|---|---|
| Create VLAN 20 on the Penang edge Juniper router | R3, ready |
| Create VLAN 20 on the KL core router | Ask; answer `the Huawei one` -> R2 |
| Create VLAN 20 on KL core routers | R1 and R2, ready |
| Create VLAN 20 on the router in Kuala Lumpur running IOS-XE | R1, ready |
| Create VLAN 20 on the branch router | R3, ready |
| Create VLAN 20 on Cisco R2 | Conflict; choose a displayed device to correct |
| Create VLAN 20 on the Cisco router in Penang | Conflict; answer `Juniper` -> R3 |
| Create VLAN 20 on Router 9 | Unknown device; choose a suggestion |
| Create VLAN 20 on the London Cisco router | Unknown qualifier; never silently select R1 |
| Create VLAN 20 | Missing target; answer `Penang edge Juniper router` |
| Create VLAN 20 on the router with management IP 10.0.0.12 | R2 |
| Create VLAN 20 on routers with management subnet 10.0.0.0/24 | R1, R2, R3 |
| Create VLAN 20 on routers supporting IS-IS | R3 |
| Create VLAN 20 on the router with GigabitEthernet0/0/1 | R2 |

Mixed tasks:

```text
Create VLAN 20 on the Penang edge Juniper router and create VLAN 30 on the KL Cisco router
Create VLAN 20 on R3 and create VLAN 30 on the KL core router
```

The second request keeps R3 validated and asks about the second task's target.
No task renders until the whole request is complete.
See `DEVICE_RESOLUTION.md` for attribute governance and limits.

## Context-aware regression scenarios

| Prompt | Expected behavior |
|---|---|
| Create VLAN 20 and configure OSPF on R1 and R2 | Four independent bindings; nothing renders until all four validate |
| Create VLAN 20 and configure OSPF on R1; create VLAN 30 on R2 | First two operations use R1, last uses R2 |
| Configure interface IP on R1 | Choose interface; address/prefix choices are scoped to that interface |
| Configure OSPF process 100 on R1 using Ethernet1/1 and Loopback0 | Preserve both interfaces; ask each area separately |
| Configure OSPF on R1 and R3 | Different interface options; process ID required only for R1 |
| Configure BGP neighbor 192.0.2.2 local AS 65000 remote AS 65001 on R3 | Ask for peer group; never invent EBGP-PEER |
| Create VLAN 20 or 30 on R1 | Ask which VLAN ID; no first-match choice |
| Create VLAN 20 on R1; delete VLAN 20 on R1 | Require explicit ordering confirmation or a correction |
| Configure IP address 192.0.2.1/24 on Ethernet1/10 on R1 | Reject the interface; never shorten it to Ethernet1/1 |
| Create VLAN 20 on R1; do something unknown on R2 | Preserve first binding; ask which supported operation the second means |

For `Configure interface IP on R1`, try `select 1`, then `255.255.255.0`.
The address reply must be rejected with parameters unchanged. Enter `192.0.2.1`,
then `255.255.255.0` when the prefix question appears. Only then should rendering
produce `ip address 192.0.2.1 255.255.255.0`.

For a process-ID question, compare `1` (process 1) with `select 1` (the first
offered planned candidate, currently process 100). Try `-1`, `65536`, and `1abc`:
all must be rejected without changing accepted parameters.
