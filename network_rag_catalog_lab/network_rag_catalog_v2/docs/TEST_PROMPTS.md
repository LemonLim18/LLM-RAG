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

For the second prompt, reply `1` in terminal mode to choose the first offered
interface. Answer each OSPF field when requested: `GigabitEthernet0/0/0 in area 0`
for interfaces, then `process 100` for the process ID.

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

The second request keeps R3 ready and asks only about the second task's target.
See `DEVICE_RESOLUTION.md` for attribute governance and limits.
