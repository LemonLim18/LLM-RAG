from copy import deepcopy
from typing import Any


def _norm(value: str) -> str:
    return "".join(ch.lower() for ch in value if ch.isalnum())


def _interface_index(device: dict) -> dict[str, str]:
    index = {}
    for interface in device.get("interfaces", []):
        names = [interface.get("name", "")]
        names.extend(interface.get("aliases", []))
        for name in names:
            if name:
                index[_norm(str(name))] = interface["name"]
    return index


def _resolve_interface_name(device: dict, name: Any) -> str | None:
    if not isinstance(name, str) or not name.strip():
        return None
    return _interface_index(device).get(_norm(name))


def normalize_parameters_for_device(params: dict, device: dict) -> dict:
    normalized = deepcopy(params)
    canonical = _resolve_interface_name(device, normalized.get("interface"))
    if canonical:
        normalized["interface"] = canonical

    interfaces = normalized.get("interfaces")
    if isinstance(interfaces, list):
        for item in interfaces:
            if not isinstance(item, dict):
                continue
            canonical = _resolve_interface_name(device, item.get("name"))
            if canonical:
                item["name"] = canonical
    return normalized


def validate_device_context(operation_id: str, category: str, params: dict, devices: list[dict]) -> list[dict]:
    issues = []
    for device in devices:
        features = set(device.get("capabilities", {}).get("features", []))
        if features and category not in features and operation_id not in features:
            issues.append({
                "type": "UNSUPPORTED_OPERATION",
                "field": "operation_id",
                "message": f"{device['hostname']} does not advertise support for {operation_id}.",
            })

        if isinstance(params.get("interface"), str) and not _resolve_interface_name(device, params["interface"]):
            known = ", ".join(i["name"] for i in device.get("interfaces", []))
            issues.append({
                "type": "INVALID_INTERFACE",
                "field": "interface",
                "message": f"{device['hostname']} has no interface named {params['interface']}. Known interfaces: {known}",
            })

        interfaces = params.get("interfaces")
        if isinstance(interfaces, list):
            for index, item in enumerate(interfaces):
                if not isinstance(item, dict) or not item.get("name"):
                    continue
                if not _resolve_interface_name(device, item["name"]):
                    known = ", ".join(i["name"] for i in device.get("interfaces", []))
                    issues.append({
                        "type": "INVALID_INTERFACE",
                        "field": f"interfaces[{index}].name",
                        "message": f"{device['hostname']} has no interface named {item['name']}. Known interfaces: {known}",
                    })
    return issues
