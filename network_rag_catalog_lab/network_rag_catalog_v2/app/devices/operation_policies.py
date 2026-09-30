"""Reviewed device policies for staged knowledge packs; unknown facts fail closed."""

import re


POLICY_FIELDS = {
    "c9300_vlan_state_v1": {"vlan_id": "integer", "vlan_status": "string"},
    "c9300_vlan_rename_v1": {"vlan_id": "integer", "new_vlan_name": "string"},
    "physical_interface_v1": {"interface": "string"},
    "c9300_access_v1": {"interface": "string", "vlan_id": "integer"},
    "c9300_trunk_setup_v1": {"interface": "string", "allowed_vlans": "array", "native_vlan": "integer"},
    "switchport_trunk_add_v1": {"interface": "string", "allowed_vlans": "array"},
    "c9300_trunk_replace_v1": {"interface": "string", "allowed_vlans": "array"},
    "switchport_native_vlan_v1": {"interface": "string", "native_vlan": "integer"},
    "c9300_loopback_v1": {"interface": "string", "address": "string", "prefix_length": "integer"},
    "c9300_routed_lag_v1": {"aggregate_interface": "string", "member_interfaces": "array", "lacp_mode": "string"},
}

PROFILES = {
    "cisco": ("iosxe", "17.9", "catalyst9300"),
    "huawei": ("vrp", "V200R024C10", "ce6800"),
    "juniper": ("junos", "23.4", "ex4300"),
}

MULTIVENDOR_POLICIES = {"physical_interface_v1", "switchport_trunk_add_v1", "switchport_native_vlan_v1"}


def validate_policy_binding(policy, schema):
    from .resource_policies import RESOURCE_FIELDS
    fields = {**POLICY_FIELDS, **RESOURCE_FIELDS}
    if not isinstance(policy, str) or policy not in fields:
        raise ValueError(f"Unknown device policy: {policy}")
    for field, kind in fields[policy].items():
        if schema.get("properties", {}).get(field, {}).get("type") != kind:
            raise ValueError(f"Device policy {policy} requires {field} ({kind}).")


def allows_new_interface(policy, value, vendor="cisco"):
    patterns = {"cisco": r"Loopback(?:0|[1-9][0-9]?)", "huawei": r"LoopBack(?:0|[1-9][0-9]?)", "juniper": r"lo0"}
    return (policy == "c9300_loopback_v1" and isinstance(value, str)
            and bool(re.fullmatch(patterns.get(vendor, r"(?!)"), value)))


def validate_policy(policy, params, device):
    from .resource_policies import RESOURCE_FIELDS, validate_resource_policy
    if policy in RESOURCE_FIELDS:
        return validate_resource_policy(policy, params, device)
    if policy not in POLICY_FIELDS:
        raise ValueError(f"Unknown device policy: {policy}")
    try:
        return _validate_switching_policy(policy, params, device)
    except (TypeError, ValueError, AttributeError, KeyError):
        return [{"type": "UNSUPPORTED_OPERATION", "field": "operation_id",
                 "message": f"{device.get('hostname', 'Device')}: malformed switching facts; review the source inventory."}]


def _validate_switching_policy(policy, params, device):
    issues = []

    def reject(field, message, kind="DEVICE_CONTEXT"):
        issues.append({"type": kind, "field": field, "message": f"{device['hostname']}: {message}", "device": device["hostname"]})

    caps = device.get("capabilities", {})
    vendor = device.get("vendor")
    if ((device.get("platform"), str(device.get("version")), device.get("model_family")) != PROFILES.get(vendor)
            or policy not in caps.get("validated_policies", [])):
        reject("operation_id", "This operation requires an explicitly reviewed hardware/NOS profile and capability facts.", "UNSUPPORTED_OPERATION")
        return issues
    if not device.get("source_refs"):
        reject("operation_id", "Capability facts need an inventory source reference.", "UNSUPPORTED_OPERATION")
        return issues

    interfaces = {item["name"]: item for item in device.get("interfaces", [])}
    interface = interfaces.get(params.get("interface")) if isinstance(params.get("interface"), str) else None
    vlan_rows = device.get("vlans", [])
    if not isinstance(vlan_rows, list) or any(not isinstance(item, dict) or type(item.get("vlan_id")) is not int for item in vlan_rows):
        reject("operation_id", "Planned VLAN facts have an invalid shape.", "UNSUPPORTED_OPERATION")
        return issues
    vlans = {item["vlan_id"]: item for item in vlan_rows}
    if len(vlans) != len(vlan_rows):
        reject("operation_id", "Planned VLAN identities are duplicated.", "UNSUPPORTED_OPERATION")
        return issues

    for field in ("vlan_id", "native_vlan", "allowed_vlans"):
        value = params.get(field)
        values = value if isinstance(value, list) else [value] if value is not None else []
        if field not in POLICY_FIELDS[policy]:
            continue
        if any(type(item) is not int or item not in vlans or 1002 <= item <= 1005 for item in values):
            reject(field, "Select VLANs explicitly present in this device's planned VLAN inventory; creating them in the same request is not yet supported.")

    if policy in {"c9300_vlan_state_v1", "c9300_vlan_rename_v1"}:
        if vendor == "cisco" and caps.get("vtp_mode") != "transparent":
            reject("operation_id", "This initial VLAN-edit scope requires recorded VTP transparent mode.", "UNSUPPORTED_OPERATION")
        vlan_id = params.get("vlan_id")
        if vlan_id is not None and (type(vlan_id) is not int or not 2 <= vlan_id <= 1001):
            reject("vlan_id", "Only normal-range, non-default VLANs 2-1001 are supported by this edit contract.")
        name = params.get("new_vlan_name")
        if vendor == "juniper" and params.get("current_vlan_name") is not None:
            if vlans.get(vlan_id, {}).get("name") != params["current_vlan_name"]:
                reject("current_vlan_name", "The name must match the selected VLAN ID in inventory.")
        if isinstance(name, str) and any(str(v.get("name", "")).casefold() == name.casefold() and identity != vlan_id for identity, v in vlans.items()):
            reject("new_vlan_name", "That name already belongs to another planned VLAN.")
        return issues

    if policy == "c9300_loopback_v1":
        name = params.get("interface")
        if name is not None and not allows_new_interface(policy, name, vendor):
            reject("interface", "Use a loopback name supported by this vendor's schema.")
        elif interface and interface.get("type") != "loopback":
            reject("interface", "The name collides with a non-loopback inventory resource.")
        return issues

    if policy == "c9300_routed_lag_v1":
        aggregate = params.get("aggregate_interface")
        if vendor == "juniper" and isinstance(aggregate, str) and re.fullmatch(r"ae[0-9]+", aggregate):
            if int(aggregate[2:]) >= caps.get("aggregate_device_count", 0):
                reject("aggregate_interface", "The aggregate must fit the preconfigured Junos aggregated-device count.")
        existing = interfaces.get(aggregate) if isinstance(aggregate, str) else None
        if existing and (existing.get("type") != "lag" or existing.get("switchport_mode") != "routed"):
            reject("aggregate_interface", "The aggregate name collides with a resource outside the routed LACP scope.")
        if existing and existing.get("lacp_mode") not in (None, params.get("lacp_mode")):
            reject("lacp_mode", "Changing an existing aggregate's LACP mode is outside this membership operation.")
        members = params.get("member_interfaces", [])
        if not isinstance(members, list):
            return issues
        seen, characteristics = set(), set()
        for index, name in enumerate(members):
            path = f"member_interfaces[{index}]"
            if not isinstance(name, str) or name not in interfaces:
                reject(path, "Select an existing physical member on this device.", "INVALID_INTERFACE")
                continue
            item = interfaces[name]
            if vendor == "juniper" and item.get("logical_units") != []:
                reject(path, "Junos aggregate members must have explicitly empty logical units; no implicit deletion is performed.")
            if name in seen:
                reject(path, "Duplicate members, including aliases of the same port, are not allowed.")
            seen.add(name)
            if (item.get("type") != "ethernet" or item.get("switchport_mode") != "routed"
                    or item.get("ip_addresses") != [] or item.get("service_bindings") != []
                    or item.get("lag_capable") is not True or item.get("enabled") is not True):
                reject(path, "Members must be enabled, LAG-capable routed physical ports with explicitly empty address/service bindings.")
            if "aggregate" not in item or item["aggregate"] not in (None, aggregate):
                reject(path, "The member's current aggregate must be recorded and cannot belong to another group.")
            facts = (item.get("speed_mbps"), item.get("duplex"), item.get("mtu"))
            if any(value is None for value in facts):
                reject(path, "Member speed, duplex and MTU facts are required.")
            else:
                characteristics.add(facts)
        if len(characteristics) > 1:
            reject("member_interfaces", "All members must have matching speed, duplex and MTU.")
        if existing and characteristics and (existing.get("speed_mbps"), existing.get("duplex"), existing.get("mtu")) not in characteristics:
            reject("aggregate_interface", "Existing aggregate characteristics must match its proposed members.")
        return issues

    if params.get("interface") is None or interface is None:
        return issues
    if policy == "physical_interface_v1":
        if interface.get("type") != "ethernet" or "." in interface.get("name", ""):
            reject("interface", "This profile supports physical Ethernet interface properties only.")
        return issues
    if vendor == "juniper" and (interface.get("logical_units") != [0] or interface.get("encapsulation") != "ethernet-switching"):
        reject("interface", "Only confirmed ELS Ethernet-switching unit 0 is supported.")
    if (interface.get("type") != "ethernet" or interface.get("switchport_capable") is not True
            or "aggregate" not in interface or interface["aggregate"] is not None):
        reject("interface", "Use a recorded switchport-capable physical port that is not an aggregate member.")
    if interface.get("switchport_mode") not in {"access", "trunk"}:
        reject("interface", "Changing a routed or unknown-mode port into a switchport is outside this contract.")
    if policy in {"switchport_trunk_add_v1", "c9300_trunk_replace_v1", "switchport_native_vlan_v1"} and interface.get("switchport_mode") != "trunk":
        reject("interface", "This mutation requires an existing trunk; use the explicit trunk-setup operation first.")
    if policy == "switchport_native_vlan_v1" and params.get("native_vlan") is not None:
        if params["native_vlan"] not in interface.get("allowed_vlans", []):
            reject("native_vlan", "The requested native VLAN must already be in the recorded allowed list.")
    if policy in {"c9300_trunk_setup_v1", "c9300_trunk_replace_v1"}:
        native = params.get("native_vlan", interface.get("native_vlan"))
        allowed = params.get("allowed_vlans")
        if native is None:
            reject("native_vlan" if "native_vlan" in POLICY_FIELDS[policy] else "interface", "Specify a native VLAN or supply its existing inventory fact.")
        elif isinstance(allowed, list) and native not in allowed:
            reject("allowed_vlans", "This initial trunk policy requires the native VLAN to remain in the replacement allowed list.")
    return issues
