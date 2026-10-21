"""Independent small-case oracle; never projected into model-visible records."""
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from development.seeded import seeded_scenario,VARIANTS
from development.network_model import Flow,NetworkModel,assess_flow,protocol_findings
from local_providers.development import Scenario


class SeededTests(unittest.TestCase):
    def test_generated_scenarios_match_independent_forwarding_and_protocol_expectations(self):
        # These expected statuses are specified independently of engine output.
        expected={'healthy':'delivered','interface_down':'failed','return_route':'partial',
                  'acl':'partial','ospf_timer':'delivered','bgp_as':'delivered','conflict':'delivered'}
        for seed in [17,83,205,401,997,2027]:
            for variant in VARIANTS:
                with self.subTest(seed=seed,variant=variant):
                    scenario=Scenario.model_validate(seeded_scenario(seed,variant)).model_dump()
                    flow=Flow.model_validate(scenario['network']['flows'][0])
                    self.assertEqual(assess_flow(scenario,flow)['status'],expected[variant])
                    findings=protocol_findings(NetworkModel.model_validate(scenario['network']))
                    if variant=='conflict':self.assertTrue(any(row['conflict'] for row in findings))
                    elif variant in {'ospf_timer','bgp_as'}:self.assertTrue(any(row['configuration_differences'] for row in findings))
                    for forbidden in ['expected_diagnosis','expected_outcome','oracle']:self.assertNotIn(forbidden,json.dumps(scenario))

    def test_reproducible_and_distinct_without_changing_base(self):
        a=seeded_scenario(33);b=seeded_scenario(33);c=seeded_scenario(34)
        self.assertEqual(a,b);self.assertNotEqual(a['devices'],c['devices'])
        a['devices'][0]['hostname']='edited'
        self.assertNotEqual(a,seeded_scenario(33))

    def test_invalid_generation_inputs_are_rejected(self):
        for seed,variant in [(-1,'healthy'),(65536,'healthy'),(1,'invented')]:
            with self.subTest(seed=seed,variant=variant),self.assertRaises(ValueError):seeded_scenario(seed,variant)
