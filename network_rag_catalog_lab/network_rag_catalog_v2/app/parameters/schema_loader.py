from copy import deepcopy
import json
from pathlib import Path

from ..catalog import compare_operation_schema, get_operation, get_parameter, knowledge_service, load_operation_parameters
from ..knowledge.runtime import current_snapshot, snapshot_request
from ..knowledge.schema_compiler import compile_schema
from ..config import BASE_DIR, runtime_mode


def _add_catalog_metadata(schema: dict, mappings: dict | None = None, path: str = "") -> dict:
    enriched = deepcopy(schema)
    for field, property_schema in enriched.get("properties", {}).items():
        field_path = f"{path}.{field}" if path else field
        try:
            parameter_id = (mappings or {}).get(field_path, property_schema.get("x-parameter-id", field))
            metadata = get_parameter(parameter_id)
        except KeyError:
            metadata = None
        if metadata:
            property_schema["title"] = metadata["display_name"]
            property_schema["x-parameter"] = metadata
        if property_schema.get("type") == "object":
            enriched["properties"][field] = _add_catalog_metadata(property_schema, mappings, field_path)
        elif property_schema.get("type") == "array":
            property_schema["items"] = _add_catalog_metadata(property_schema.get("items", {}), mappings, field_path + "[]")
    return enriched


def _merge_profile_node(left: dict, right: dict) -> dict:
    """Union extraction vocabulary recursively; enforce constraints per device."""
    if left == right:
        return deepcopy(left)
    if left.get("type") != right.get("type"):
        raise ValueError("Vendor profiles cannot redefine a canonical parameter's type.")
    merged = {key: deepcopy(value) for key, value in left.items()
              if key not in {"properties", "items", "required"} and right.get(key) == value}
    if left.get("type") == "object":
        properties = deepcopy(left.get("properties", {}))
        for name, node in right.get("properties", {}).items():
            properties[name] = _merge_profile_node(properties[name], node) if name in properties else deepcopy(node)
        merged["properties"] = properties
        merged["required"] = [name for name in left.get("required", []) if name in right.get("required", [])]
    elif left.get("type") == "array":
        merged["items"] = _merge_profile_node(left["items"], right["items"])
    return merged


def _apply_vendor_requirements(schema: dict, devices: list[dict] | None) -> dict:
    """Add only the required fields relevant to the selected vendor set.

    A logical operation can have a small vendor-specific contract. For example,
    Junos OSPF has no Cisco-style numeric process ID, while Cisco and Huawei do.
    The base schema stays reusable until authoritative targets are known.
    """
    enriched = deepcopy(schema)
    profiles = enriched.pop("x-vendor-profiles", {})
    semantic_fields = schema.get("x-semantic-fields", [])
    for vendor, profile in {"canonical": schema, **profiles}.items():
        if any(name not in profile.get("properties", {}) or name not in profile.get("required", [])
               for name in semantic_fields):
            raise ValueError(f"Vendor profile {vendor} removes required canonical semantic fields: {semantic_fields}")
    vendors = {device.get("vendor") for device in devices or []}
    if profiles:
        if len(vendors) == 1 and next(iter(vendors)) in profiles:
            enriched.update(deepcopy(profiles[next(iter(vendors))]))
        else:
            # Collect without imposing one vendor's grammar on another. Each
            # device binding is subsequently checked against its own profile.
            selected = [profiles[v] for v in sorted(vendors) if v in profiles] or list(profiles.values())
            # Extraction without a target must retain canonical inputs even if
            # every vendor profile omits them. Validation uses a single profile.
            properties = deepcopy(schema.get("properties", {})) if not vendors else {}
            for profile in selected:
                for name, definition in profile["properties"].items():
                    if name not in properties:
                        properties[name] = deepcopy(definition)
                    elif properties[name] != definition:
                        properties[name] = _merge_profile_node(properties[name], definition)
            enriched["properties"] = properties
            enriched["required"] = [name for name in selected[0]["required"]
                                    if all(name in p["required"] for p in selected)]
    requirements = enriched.get("x-required-by-vendor", {})
    required = list(enriched.get("required", []))
    for device in devices or []:
        for field in requirements.get(device.get("vendor"), []):
            if field not in required:
                required.append(field)
    enriched["required"] = required
    return enriched


@snapshot_request
def load_schema(operation_id: str, devices: list[dict] | None = None) -> dict:
    operation = get_operation(operation_id)
    snapshot = current_snapshot()
    if snapshot is None and runtime_mode() == "files":
        raw_schema = json.loads((BASE_DIR / operation["schema_path"]).read_text(encoding="utf-8"))
        return _add_catalog_metadata(_apply_vendor_requirements(raw_schema, devices))
    if snapshot or operation.get("schema_source") == "registry":
        vendors = {device.get("vendor") for device in devices or []}
        vendor = next(iter(vendors)) if len(vendors) == 1 else None
        raw_schema = snapshot.schema(operation_id, vendor) if snapshot else compile_schema(knowledge_service(), operation_id)
        mappings = {row["field_path"]: row["parameter_id"] for row in load_operation_parameters(operation_id)}
        return _add_catalog_metadata(_apply_vendor_requirements(raw_schema, devices), mappings)
    path = Path(__file__).resolve().parents[2] / operation["schema_path"]
    raw_schema = json.loads(path.read_text(encoding="utf-8"))
    mappings = None
    if operation.get("mapping_mode") == "compare":
        comparison = compare_operation_schema(operation_id, raw_schema)
        # Shadow edits cannot change validation or redirect parameter identity.
        if comparison["matches"]:
            mappings = {row["field_path"]: row["parameter_id"] for row in load_operation_parameters(operation_id)}
    return _add_catalog_metadata(_apply_vendor_requirements(raw_schema, devices), mappings)
