"""Literal claim regressions: deliberately narrower than semantic validation."""
import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from llm.orchestration.studio import verify_editor_router_ids

SOURCE = '''hostname QUALITY-GATE
interface GigabitEthernet0/1
 ip address 10.23.1.1 255.255.255.252
 no shutdown
interface Loopback0
 ip address 192.0.2.1 255.255.255.255
router ospf 20
 router-id 192.0.2.20
 network 10.23.1.0 0.0.0.3 area 0
router bgp 65010
 neighbor 192.0.2.2 remote-as 65020
 neighbor 192.0.2.3 remote-as 65030
ip route 203.0.113.0 255.255.255.0 10.23.1.2
ip access-list extended WEB
 permit tcp any any eq 443
'''


class EditorFactsTests(unittest.TestCase):
    def test_source_line_number_cannot_become_a_router_identity(self):
        docs=[{'source':'x.cfg','text':'hostname Branch-Spruce\nrouter bgp 65100\n neighbor 192.0.2.9 remote-as 65200\n'}]
        wrong='The draft configures BGP on router 2 with local AS 65100 and neighbor 192.0.2.9 remote AS 65200.'
        answer,changed=verify_editor_router_ids(wrong,docs,'x.cfg',question='Explain the local and remote AS settings.')
        self.assertTrue(changed)
        self.assertNotIn('on router 2',answer)
        correct='The draft for router Branch-Spruce uses local AS 65100 and neighbor 192.0.2.9 remote AS 65200.'
        self.assertEqual(verify_editor_router_ids(correct,docs,'x.cfg'),(correct,False))

    def test_as_explanation_cannot_infer_same_network_or_deny_available_source(self):
        docs=[{'source':'x.cfg','text':'router bgp 65100\n neighbor 192.0.2.9 remote-as 65200\n'}]
        question='Explain its local and remote AS settings.'
        for bad in ['The AS numbers identify autonomous systems, ensuring the routers are part of the same network.',
                    'The filename and line numbers are not provided. Local AS: 65100. Remote AS: 65200.']:
            with self.subTest(answer=bad):
                answer,changed=verify_editor_router_ids(bad,docs,'x.cfg',question=question)
                self.assertTrue(changed)
                self.assertIn('65100',answer);self.assertIn('65200',answer)
        good='Local AS: 65100; neighbor 192.0.2.9 remote AS: 65200. These configure eBGP, but do not prove session health.'
        self.assertEqual(verify_editor_router_ids(good,docs,'x.cfg',question=question),(good,False))

    def test_as_projection_preserves_line_numbers_and_declines_ambiguous_processes(self):
        from llm.orchestration.studio import as_command_context
        docs=[{'source':'x.cfg','text':'router bgp 65100\n\n neighbor 192.0.2.9 remote-as 65200\n','start_line':8}]
        question='Explain its local and remote AS settings.'
        self.assertEqual(as_command_context(question,docs,'x.cfg'),[
            {'line':8,'text':'router bgp 65100'},{'line':10,'text':'neighbor 192.0.2.9 remote-as 65200'}])
        self.assertEqual(as_command_context(question+' Investigate session health.',docs,'x.cfg'),[])
        self.assertEqual(as_command_context(question,docs+[{'source':'x.cfg','text':'router bgp 65300\n neighbor 192.0.2.8 remote-as 65400','start_line':12}],'x.cfg'),[])

    def check(self, answer):
        return verify_editor_router_ids(answer, [{'source': 'playbooks/q.cfg', 'text': SOURCE, 'start_line': 1}], 'playbooks/q.cfg')

    def test_contradictory_as_pairs_and_interface_addresses_reconstruct_source(self):
        cases = ['Local AS: 65020', 'Neighbor 192.0.2.2 has remote AS 65010.',
                 'Neighbor 192.0.2.3\nRemote AS: 65020', 'Neighbor 192.0.2.99 remote AS: 65020',
                 'Neighbor 192.0.2.2 with AS 65010',
                 'GigabitEthernet0/1 IP address: 192.0.2.1',
                 'GigabitEthernet0/1 IP address: 10.23.1.1/24',
                 'Ethernet9 IP address: 10.23.1.1',
                 'The static route 203.0.113.0/24 uses next hop 192.0.2.2.',
                 'GigabitEthernet0/1 is up.', 'The configuration is deployed.']
        for answer in cases:
            with self.subTest(answer=answer):
                corrected, changed = self.check(answer)
                self.assertTrue(changed)
                self.assertIn('ip address 10.23.1.1 255.255.255.252', corrected)
                self.assertIn('remote-as 65020', corrected)
                self.assertIn('current device state is not established', corrected)

    def test_correct_claims_and_explicit_uncertainty_remain_model_assisted(self):
        for answer in ['Local AS: 65010. Neighbor 192.0.2.2 remote AS: 65020.',
                       'GigabitEthernet0/1 IP address: 10.23.1.1/30',
                       'interface GigabitEthernet0/1\n ip address 10.23.1.1 255.255.255.252',
                       'GigabitEthernet0/1 IP address: 10.23.1.1, mask: 255.255.255.252',
                       'Static route 203.0.113.0/24 via 10.23.1.2.',
                       'OSPF router ID: 192.0.2.20. OSPF network: 10.23.1.0/30.',
                       'You could use local AS 65100 if the design requires it.',
                       'WEB permits HTTPS in the shown ACL; effective policy needs further evidence.']:
            with self.subTest(answer=answer): self.assertEqual(self.check(answer), (answer, False))

    def test_non_ios_and_uncovered_semantics_are_not_certified(self):
        answer = 'The policy intent requires further review.'
        self.assertEqual(verify_editor_router_ids(answer, [{'source': 'junos.j2', 'text': 'set system host-name R3'}], 'junos.j2'), (answer, False))
        # Pure interface configurations still receive the guard, without OSPF/BGP.
        corrected, changed = verify_editor_router_ids('Loopback0 IP address: 192.0.2.99', [{'source': 'x', 'text': 'interface Loopback0\n ip address 192.0.2.1 255.255.255.255'}], 'x')
        self.assertTrue(changed); self.assertIn('192.0.2.1', corrected)

    def test_comment_labels_do_not_establish_protocol_or_storage_state(self):
        docs=[{'source':'draft.cfg','text':'! KEEP_ROUTING_TEST\n! LOCAL_DRAFT_NOTE\nrouter bgp 65101\n'}]
        question='Explain the marker comment found in this open document.'
        wrong='The KEEP_ROUTING_TEST comment suggests that the OSPF configuration is frozen or held in a specific state. The LOCAL_DRAFT_NOTE comment indicates that the configuration is not saved to the configuration database.'
        answer,changed=verify_editor_router_ids(wrong,docs,'draft.cfg',question=question)
        self.assertTrue(changed)
        self.assertIn('! KEEP_ROUTING_TEST',answer);self.assertIn('! LOCAL_DRAFT_NOTE',answer)
        self.assertNotIn('router bgp',answer)
        self.assertIn('does not establish',answer)
        correct='`! KEEP_ROUTING_TEST` and `! LOCAL_DRAFT_NOTE` are author-written comments, not protocol commands. Their names alone do not establish runtime or save state.'
        self.assertEqual(verify_editor_router_ids(correct,docs,'draft.cfg',question=question),(correct,False))
        quoted='The first comment, "! KEEP_ROUTING_TEST", suggests that the OSPF protocol is frozen. The second comment, "! LOCAL_DRAFT_NOTE", implies that the configuration is not saved.'
        self.assertTrue(verify_editor_router_ids(quoted,docs,'draft.cfg',question=question)[1])

    def test_as_only_reconstruction_answers_roles_without_unrelated_ospf_dump(self):
        wrong='The BGP local AS is 65001 and remote AS is 65000.'
        docs=[{'source':'x.cfg','text':'router ospf 1\n router-id 192.0.2.1\nrouter bgp 65000\n neighbor 192.0.2.2 remote-as 65001\n! PRESERVE_MARKER\n'}]
        answer,changed=verify_editor_router_ids(wrong,docs,'x.cfg',question='Use the active draft to explain its local and remote AS settings.')
        self.assertTrue(changed)
        self.assertIn('65000',answer);self.assertIn('65001',answer);self.assertIn('192.0.2.2',answer)
        self.assertNotIn('router ospf',answer);self.assertNotIn('PRESERVE_MARKER',answer)
