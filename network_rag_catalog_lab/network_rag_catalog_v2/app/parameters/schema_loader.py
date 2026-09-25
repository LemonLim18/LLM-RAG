from copy import deepcopy
import json
from pathlib import Path

from ..catalog import get_operation, get_parameter


def _add_catalog_metadata(schema: dict) -> dict:
    enriched = deepcopy(schema)
    for field, property_schema in enriched.get("properties", {}).items():
        try:
            metadata = get_parameter(property_schema.get("x-parameter-id", field))
        except KeyError:
            metadata = None
        if metadata:
            property_schema.setdefault("title", metadata["display_name"])
            property_schema["x-parameter"] = metadata
        if property_schema.get("type") == "object":
            enriched["properties"][field] = _add_catalog_metadata(property_schema)
        elif property_schema.get("type") == "array":
            property_schema["items"] = _add_catalog_metadata(property_schema.get("items", {}))
    return enriched


def _apply_vendor_requirements(schema: dict, devices: list[dict] | None) -> dict:
    """Add only the required fields relevant to the selected vendor set.

    A logical operation can have a small vendor-specific contract. For example,
    Junos OSPF has no Cisco-style numeric process ID, while Cisco and Huawei do.
    The base schema stays reusable until authoritative targets are known.
    """
    enriched = deepcopy(schema)
    requirements = enriched.get("x-required-by-vendor", {})
    required = list(enriched.get("required", []))
    for device in devices or []:
        for field in requirements.get(device.get("vendor"), []):
            if field not in required:
                required.append(field)
    enriched["required"] = required
    return enriched


def load_schema(operation_id: str, devices: list[dict] | None = None) -> dict:
    path = Path(__file__).resolve().parents[2] / get_operation(operation_id)["schema_path"]
    raw_schema = json.loads(path.read_text(encoding="utf-8"))
    return _add_catalog_metadata(_apply_vendor_requirements(raw_schema, devices))
