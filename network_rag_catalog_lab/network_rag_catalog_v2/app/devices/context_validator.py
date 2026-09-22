from copy import deepcopy
from difflib import SequenceMatcher
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


def suggest_interfaces(device: dict, requested_name: str, limit: int = 3) -> list[str]:
    """Rank authoritative interface names for a correction question."""
    query = _norm(requested_name)
    scores: dict[str, float] = {}
    for interface in device.get("interfaces", []):
        names = [interface.get("name", ""), *interface.get("aliases", [])]
        score = max(
            (SequenceMatcher(None, query, _norm(name)).ratio() for name in names if name),
            default=0.0,
        )
        scores[interface["name"]] = score
    return [name for name, _ in sorted(scores.items(), key=lambda item: item[1], reverse=True)[:limit]]


def find_explicit_interface_names(device: dict, text: str) -> list[str]:
    normalized_text = _norm(text)
    matches = []
    for candidate, canonical in _interface_index(device).items():
        if candidate and candidate in normalized_text:
            matches.append(canonical)
    return list(dict.fromkeys(matches))


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
            suggestions = suggest_interfaces(device, params["interface"])
            issues.append({
                "type": "INVALID_INTERFACE",
                "field": "interface",
                "message": f"{device['hostname']} has no interface named '{params['interface']}'.",
                "suggestions": suggestions,
                "device": device["hostname"],
            })

        interfaces = params.get("interfaces")
        if isinstance(interfaces, list):
            for index, item in enumerate(interfaces):
                if not isinstance(item, dict) or not item.get("name"):
                    continue
                if not _resolve_interface_name(device, item["name"]):
                    suggestions = suggest_interfaces(device, item["name"])
                    issues.append({
                        "type": "INVALID_INTERFACE",
                        "field": f"interfaces[{index}].name",
                        "message": f"{device['hostname']} has no interface named '{item['name']}'.",
                        "suggestions": suggestions,
                        "device": device["hostname"],
                    })
    return issues
