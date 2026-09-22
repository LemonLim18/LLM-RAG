import unittest

from app.devices.inventory import resolve_targets
from app.parameters.schema_loader import load_schema
from app.parameters.validator import validate_parameters


class CatalogTests(unittest.TestCase):
    def test_alias_resolves_to_canonical_device(self):
        devices = resolve_targets(["core router 1"])
        self.assertEqual([d["hostname"] for d in devices], ["R1"])
        self.assertEqual(devices[0]["vendor"], "cisco")

    def test_multiple_aliases_resolve_without_duplicates(self):
        devices = resolve_targets(["R1", "core router 1", "R2"])
        self.assertEqual([d["hostname"] for d in devices], ["R1", "R2"])

    def test_schema_accepts_valid_vlan(self):
        schema = load_schema("create_vlan")
        validate_parameters({"vlan_id": 100, "name": "STAFF"}, schema)

    def test_schema_rejects_unknown_parameter(self):
        schema = load_schema("create_vlan")
        with self.assertRaises(ValueError):
            validate_parameters({"vlan_id": 100, "made_up": True}, schema)

    def test_schema_rejects_missing_required_parameter(self):
        schema = load_schema("configure_bgp_neighbor")
        with self.assertRaises(ValueError):
            validate_parameters({"local_as": 65000}, schema)


if __name__ == "__main__":
    unittest.main()
