"""Explicit vendor intent coverage; never equate RAG presence with a binding."""

from copy import deepcopy
import json
from pathlib import Path

from ..config import BASE_DIR
from .models import Operation, TemplateBinding

SPEC_PATH = "knowledge_packs/requested_vendor_coverage.json"


def read_scope(base_dir=BASE_DIR):
    spec = json.loads((Path(base_dir) / SPEC_PATH).read_text(encoding="utf-8"))
    if spec.get("format_version") != 1:
        raise ValueError("Unsupported vendor coverage specification.")
    vendors, categories = spec.get("vendors"), spec.get("categories")
    if (not isinstance(vendors, list) or len(vendors) != len(set(vendors)) or not vendors
            or any(not isinstance(vendor, str) for vendor in vendors)
            or not isinstance(categories, dict)):
        raise ValueError("Coverage needs unique vendor IDs and category operation lists.")
    if any(not isinstance(rows, list) or not rows for rows in categories.values()):
        raise ValueError("Coverage needs nonempty category operation lists.")
    identities = [identity for rows in categories.values() for identity in rows]
    if (any(not isinstance(identity, str) for identity in identities)
            or len(identities) != len(set(identities))):
        raise ValueError("Coverage operation IDs must be unique.")
    return spec


def validate_vendor_knowledge(operations, bindings):
    """A catalog editor cannot mark an unbound vendor executable (or vice versa)."""
    supported = {(row.operation_id, row.vendor) for row in bindings}
    for op in operations:
        for vendor, record in op.vendor_knowledge.items():
            has_binding = (op.operation_id, vendor) in supported
            if (record.status == "generation_supported") != has_binding:
                raise ValueError(f"Vendor knowledge contradicts template bindings: {op.operation_id} / {vendor}")
            if record.status == "blocked_unverified" and not record.requirements:
                raise ValueError(f"Blocked vendor knowledge needs actionable requirements: {op.operation_id} / {vendor}")


def _requested(catalogs, spec):
    operations = {row["operation_id"]: row for row in catalogs["operations"]}
    for category, identities in spec["categories"].items():
        for identity in identities:
            op = operations.get(identity)
            if not op or op["category_id"] != category or op["status"] != "active":
                raise ValueError(f"Requested operation missing, inactive or miscategorized: {identity}")
            yield op


def coverage_report(catalogs, spec):
    operations = list(_requested(catalogs, spec))
    bindings = [TemplateBinding.model_validate(row) for row in catalogs["template_bindings"]]
    validate_vendor_knowledge([Operation.model_validate(row) for row in operations], bindings)
    supported = {(row.operation_id, row.vendor) for row in bindings}
    rows = []
    for op in operations:
        for vendor in spec["vendors"]:
            record = op.get("vendor_knowledge", {}).get(vendor)
            rows.append({"operation_id": op["operation_id"], "category": op["category_id"],
                         "vendor": vendor, "intent_known": record is not None,
                         "has_binding": (op["operation_id"], vendor) in supported,
                         **(deepcopy(record) if record else {"status": "coverage_missing"})})
    return {"operation_count": len(operations), "vendor_intent_count": len(rows),
            "complete_intent_coverage": all(row["intent_known"] for row in rows),
            "complete_generation_coverage": all(row["has_binding"] for row in rows),
            "vendors": {vendor: {
                "intents": sum(row["intent_known"] for row in rows if row["vendor"] == vendor),
                "generation_supported": sum(row["has_binding"] for row in rows if row["vendor"] == vendor),
                "blocked_unverified": sum(not row["has_binding"] for row in rows if row["vendor"] == vendor),
            } for vendor in spec["vendors"]}, "rows": rows}


def prepare_coverage_request(snapshot, spec, *, actor, reason):
    catalogs = snapshot["catalogs"]
    supported = {(row["operation_id"], row["vendor"]) for row in catalogs["template_bindings"]}
    changes = []
    for op in _requested(catalogs, spec):
        records = deepcopy(op.get("vendor_knowledge", {}))
        for vendor in spec["vendors"]:
            if vendor in records:
                continue
            if (op["operation_id"], vendor) in supported:
                records[vendor] = {
                    "status": "generation_supported",
                    "reason": "Existing reviewed generation binding; only its declared platform/version profiles are eligible. This is not device certification.",
                    "requirements": ["Validate the selected device's capabilities, inventory facts and operation-specific required parameters before rendering."],
                }
            else:
                requirements = spec["blocked_requirements"].get(op["category_id"], {}).get(vendor)
                if not requirements:
                    raise ValueError(f"No reviewed blocking requirements: {op['operation_id']} / {vendor}")
                records[vendor] = {
                    "status": "blocked_unverified",
                    "reason": f"The {op['operation_id']} intent is known for {vendor}, but this catalog has no reviewed vendor-specific template binding. This is a catalog gap, not proof of absent vendor functionality.",
                    "requirements": [*requirements, *spec["operation_requirements"].get(op["operation_id"], []),
                                     "Add a versioned operation contract, vendor template and capability checks, then validate and publish before enabling generation."],
                }
        if records != op.get("vendor_knowledge", {}):
            changes.append({"entity": "operation", "action": "update", "entity_id": op["operation_id"],
                            "values": {"vendor_knowledge": records}})
    # Preserve existing authored notes, but reject stale/inconsistent support claims.
    candidate = deepcopy(catalogs)
    values = {change["entity_id"]: change["values"]["vendor_knowledge"] for change in changes}
    for op in candidate["operations"]:
        if op["operation_id"] in values:
            op["vendor_knowledge"] = values[op["operation_id"]]
    coverage_report(candidate, spec)
    return {"expected_revision": snapshot["revision"], "actor": actor, "reason": reason,
            "changes": changes} if changes else None


