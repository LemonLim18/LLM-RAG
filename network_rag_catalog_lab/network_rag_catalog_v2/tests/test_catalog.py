import unittest

from app.devices.context_validator import normalize_parameters_for_device, validate_device_context
from app.devices.inventory import resolve_targets
from app.parameters.schema_loader import load_schema
from app.parameters.validator import validate_parameter_result, validate_parameters


class CatalogTests(unittest.TestCase):
    def test_alias_resolves_to_canonical_device(self):
        devices = resolve_targets(["core router 1"])
        self.assertEqual([d["hostname"] for d in devices], ["R1"])
        self.assertEqual(devices[0]["vendor"], "cisco")

    def test_multiple_aliases_resolve_without_duplicates(self):
        devices = resolve_targets(["R1", "core router 1", "R2"])
        self.assertEqual([d["hostname"] for d in devices], ["R1", "R2"])

    def test_group_reference_resolves_to_multiple_devices(self):
        devices = resolve_targets(["core routers"])
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

    def test_validation_result_reports_missing_null_required_parameter(self):
        schema = load_schema("configure_ospf")
        result = validate_parameter_result({"process_id": None, "interfaces": None}, schema)
        self.assertFalse(result.valid)
        self.assertEqual([issue.type for issue in result.issues], ["MISSING", "MISSING"])

    def test_context_validation_rejects_unknown_interface(self):
        schema = load_schema("configure_interface_ip")
        validate_parameters({"interface": "GigabitEthernet1/1", "address": "10.1.1.1", "prefix_length": 24}, schema)
        devices = resolve_targets(["R1"])
        issues = validate_device_context(
            "configure_interface_ip",
            "ip_address",
            {"interface": "GigabitEthernet1/1", "address": "10.1.1.1", "prefix_length": 24},
            devices,
        )
        self.assertEqual(issues[0]["type"], "INVALID_INTERFACE")

    def test_context_normalizes_interface_alias_for_device(self):
        devices = resolve_targets(["R1"])
        params = normalize_parameters_for_device({"interface": "Eth1/1"}, devices[0])
        self.assertEqual(params["interface"], "Ethernet1/1")


if __name__ == "__main__":
    unittest.main()
