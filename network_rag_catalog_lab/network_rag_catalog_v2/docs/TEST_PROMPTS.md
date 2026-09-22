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
interface. For the OSPF prompt, reply:

```text
Use process 100 on GigabitEthernet0/0/0 in area 0.
```
