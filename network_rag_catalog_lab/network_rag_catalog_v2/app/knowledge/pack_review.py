"""Review coherent packs using existing management envelopes, never direct SQL."""

from copy import deepcopy
from contextlib import contextmanager
import json
from hashlib import sha256
from pathlib import Path

from ..api.contracts import EntityChange, OperationContractInput
from .models import Category, Operation, ParameterDefinition
from .runtime import safe_path


def read_pack(path):
    root = Path(path).resolve()
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("format_version") != 1:
        raise ValueError("Unsupported knowledge pack format.")
    changes = [EntityChange.model_validate(row) for row in json.loads((root / "changes.json").read_text(encoding="utf-8"))]
    context = json.loads((root / "context_rules.json").read_text(encoding="utf-8"))
    assets = {}
    names = manifest.get("assets")
    if (not isinstance(names, list) or any(not isinstance(name, str) for name in names)
            or len(names) != len(set(names)) or set(manifest.get("asset_hashes", {})) != set(names)):
        raise ValueError("Pack assets require unique paths and exact reviewed hashes.")
    for relative in manifest["assets"]:
        if not relative.startswith("data/templates/") or not relative.endswith("/template.j2"):
            raise ValueError(f"Pack asset is not a template: {relative}")
        assets[relative] = safe_path(root / "assets", relative).read_bytes()
        if sha256(assets[relative]).hexdigest() != manifest["asset_hashes"][relative]:
            raise ValueError(f"Pack asset hash mismatch: {relative}")
    return {"manifest": manifest, "changes": changes, "context": context, "assets": assets}


def install_reviewed_assets(pack, base_dir):
    """Explicit caller action; never overwrite an existing template with new bytes."""
    paths = {name: safe_path(Path(base_dir), name) for name in pack["assets"]}
    for name, path in paths.items():
        if path.exists() and path.read_bytes() != pack["assets"][name]:
            raise ValueError(f"Conflicting template asset; review a versioned update: {name}")
    for name, path in paths.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            with path.open("xb") as stream:
                stream.write(pack["assets"][name])


def prepare_request(manager, pack, *, actor, reason):
    """Idempotent diff only: existing but different records require engineer review."""
    snapshot = manager.store.snapshot()
    rows = snapshot["catalogs"]
    changes = []
    models = {"category": ("categories", "category_id", Category),
              "parameter": ("parameters", "parameter_id", ParameterDefinition),
              "operation": ("operations", "operation_id", Operation)}
    for change in pack["changes"]:
        if change.entity in models and change.action == "create":
            name, key, model = models[change.entity]
            existing = next((row for row in rows[name] if row[key] == change.entity_id), None)
            if existing is not None:
                expected = {**change.values, key: change.entity_id}
                if model.model_validate(existing).model_dump() != model.model_validate(expected).model_dump():
                    raise ValueError(f"Pack conflicts with reviewed {change.entity} {change.entity_id}.")
                continue
        elif change.entity == "membership" and change.action == "assign":
            if change.values in rows["category_parameters"]:
                continue
        elif change.entity == "contract" and change.action == "replace":
            existing = next((row for row in rows["operations"] if row["operation_id"] == change.entity_id), None)
            if existing:
                current = {"version": existing["version"], **{key: [row for row in rows[name] if row["operation_id"] == change.entity_id]
                    for key, name in (("mappings", "operation_parameters"), ("rules", "operation_rules"), ("templates", "template_bindings"))}}
                if OperationContractInput.model_validate(current) != OperationContractInput.model_validate(change.values):
                    raise ValueError(f"Pack conflicts with reviewed contract {change.entity_id}.")
                continue
        else:
            raise ValueError("Packs only create records, assign memberships and install complete new contracts.")
        changes.append(change.model_dump())
    context = deepcopy(rows["context_rules"])
    for operation_id, rule in pack["context"].items():
        if operation_id in context["operations"] and context["operations"][operation_id] != rule:
            raise ValueError(f"Pack conflicts with reviewed context rules for {operation_id}.")
        context["operations"][operation_id] = rule
    if context != rows["context_rules"]:
        changes.append({"entity": "context_rules", "action": "replace", "values": context})
    if not changes:
        return None
    return {"expected_revision": snapshot["revision"], "actor": actor, "reason": reason, "changes": changes}


@contextmanager
def rehearse(pack_paths, source_base=None):
    """Stage from the selected authority in a disposable SQLite project only."""
    import shutil
    import tempfile
    from ..config import BASE_DIR
    from .management import KnowledgeManagementService
    from .publication import publish
    from .runtime import active_snapshot, snapshot_scope

    source = Path(source_base or BASE_DIR)
    authoritative = KnowledgeManagementService(source).store.snapshot()
    with tempfile.TemporaryDirectory(prefix="knowledge-rehearsal-") as temporary:
        base = Path(temporary) / "project"
        shutil.copytree(source / "data", base / "data",
                        ignore=shutil.ignore_patterns(".authoring*", ".*.tmp"))
        for name, rows in authoritative["catalogs"].items():
            (base / "data/catalog" / (name + ".json")).write_text(json.dumps(rows), encoding="utf-8")
        releases = base / "storage/catalog_releases"
        publish(base_dir=base, releases_dir=releases, mode="offline")
        manager = KnowledgeManagementService(base, releases_dir=releases)
        result = manager.migrate_sqlite({"expected_revision": manager.inspect().revision, "actor": "pack-review",
                                        "reason": "Isolated pack rehearsal; never change source authority"})
        if not result.ok:
            raise ValueError(result)
        reports = []
        for path in pack_paths:
            pack = read_pack(path)
            install_reviewed_assets(pack, base)
            request = prepare_request(manager, pack, actor="pack-review", reason="Validate reviewed candidate pack")
            if request:
                before = manager.inspect().revision
                dry_run = manager.apply(request, dry_run=True)
                if not dry_run.ok or manager.inspect().revision != before:
                    raise ValueError(dry_run)
                result = manager.apply(request)
                if not result.ok:
                    raise ValueError(result)
            reports.append({"pack": pack["manifest"]["pack_id"], "changed": request is not None})
        state = manager.inspect()
        result = manager.publish({"expected_revision": state.revision, "expected_release": state.data["active_release"]["release_id"],
                                  "actor": "pack-review", "reason": "Isolated offline candidate publication", "mode": "offline"})
        if not result.ok:
            raise ValueError(result)
        snapshot = active_snapshot(releases)
        with snapshot_scope(snapshot):
            yield manager, snapshot, reports


def check_cases(snapshot, pack_paths):
    from ..devices.context_validator import validate_device_context
    from ..parameters.schema_loader import load_schema
    from ..parameters.validator import validate_parameter_result
    from ..templates.renderer import render
    from ..config import BASE_DIR
    devices = json.loads((BASE_DIR / "knowledge_packs/fixtures/devices.json").read_text(encoding="utf-8"))
    count = 0
    for path in pack_paths:
        for case in json.loads((Path(path) / "cases.json").read_text(encoding="utf-8")):
            operation = case["operation_id"]
            metadata = next(row for row in snapshot.service.list_operations() if row.operation_id == operation)
            for device in devices:
                supported = any(row["operation_id"] == operation and row["vendor"] == device["vendor"] and row["platform"] == device["platform"]
                                and device["version"] in row["versions"] for row in snapshot.manifest["template_bindings"])
                if not supported:
                    continue
                params = deepcopy(case["parameters"])
                if "interface" in params and device["vendor"] != "cisco":
                    index = next(i for i, item in enumerate(devices[0]["interfaces"]) if item["name"] == params["interface"])
                    params["interface"] = device["interfaces"][index]["name"]
                schema_result = validate_parameter_result(params, load_schema(operation, [device]))
                issues = validate_device_context(operation, metadata.category_id, params, [device])
                if not schema_result.valid or issues:
                    raise ValueError(f"{operation}/{device['hostname']}: {schema_result.issues} {issues}")
                output = render(device, operation, params)
                if not output.strip() or "None" in output or (device["vendor"] == "cisco" and case.get("expected", "") not in output):
                    raise ValueError(f"Golden command mismatch: {operation}/{device['hostname']}")
                count += 1
    return count


def main():
    import argparse
    from ..config import BASE_DIR
    parser = argparse.ArgumentParser(description="Rehearse reviewed packs in temporary SQLite; never activate the live catalog.")
    parser.add_argument("--packs", nargs="+", default=["vlan", "interface", "static_routing", "ospf", "acl", "qos"])
    parser.add_argument("--check-cases", action="store_true", help="Also validate and render the staged planned-device cases.")
    args = parser.parse_args()
    paths = [BASE_DIR / "knowledge_packs" / name for name in args.packs]
    with rehearse(paths) as (manager, snapshot, reports):
        verified = check_cases(snapshot, paths) if args.check_cases else None
        print(json.dumps({"mode": "isolated_offline", "authority": manager.inspect().data["authority"],
                          "operations": len(snapshot.manifest["schemas"]),
                          "bindings": len(snapshot.manifest["template_bindings"]), "verified_cases": verified, "packs": reports}, indent=2))


if __name__ == "__main__":
    main()
