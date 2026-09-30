"""Promote reviewed packs through SQLite services; publication is a separate step."""

import argparse
from copy import deepcopy
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sqlite3
from uuid import uuid4

from ..config import BASE_DIR, OLLAMA_EMBED_MODEL, OLLAMA_LLM_MODEL
from ..devices.inventory import _index_device
from .authoring_store import _atomic_json, authoring_lock
from .management import KnowledgeManagementService
from .pack_review import install_reviewed_assets, prepare_request, read_pack, rehearse
from .runtime import active_pointer, active_snapshot, safe_path

DOMAINS = ("vlan", "interface", "static_routing", "ospf", "acl", "qos")


def merge_demo_devices(current, additions):
    merged = deepcopy(current)
    identities = {device["id"] for device in current}
    if len(identities) != len(current):
        raise ValueError("Inventory contains duplicate device IDs.")
    for device in additions:
        existing = next((row for row in merged if row["id"] == device["id"]), None)
        if existing is not None:
            if existing != device:
                raise ValueError(f"Demonstration device conflicts with inventory: {device['id']}")
            continue
        names = set(_index_device(device))
        for other in merged:
            collision = names.intersection(_index_device(other))
            if collision:
                raise ValueError(f"Inventory name/alias conflict with {other['hostname']}: {sorted(collision)}")
        merged.append(deepcopy(device))
    return merged


def _require(result):
    if not result.ok:
        raise ValueError(result.model_dump_json())
    return result


def _backup(manager, pack_hashes, actor, reason):
    exported = _require(manager.export())
    baseline = active_snapshot(manager.releases)
    if baseline is None:
        raise ValueError("An active baseline is required before promotion.")
    destination = manager.base / "storage/catalog_authoring/activation" / uuid4().hex
    destination.mkdir(parents=True)
    with authoring_lock(manager.base):
        snapshot = manager.store._snapshot_unlocked()
        if snapshot["revision"] != exported.revision:
            raise ValueError("Authoring changed while preparing backup; retry.")
        for name, raw in snapshot["sources"].items():
            target = safe_path(destination, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        for name in ("inventory", "planned"):
            shutil.copytree(manager.base / "data" / name, destination / "data" / name)
        with manager.store._connection() as source:
            target = sqlite3.connect(destination / "catalog.sqlite3")
            try:
                source.backup(target)
            finally:
                target.close()
        shutil.copy2(manager.base / "storage/knowledge/authority.json", destination / "authority.json")
        shutil.copytree(baseline.root, destination / "active_release")
        baseline.assert_active()
        _atomic_json(destination / "export.json", exported.data["bundle"])
        receipt = {
            "format_version": 1, "purpose": "generation-only lab prompting",
            "created_at": datetime.now(UTC).isoformat(), "actor": actor, "reason": reason,
            "before_revision": snapshot["revision"], "active_release": active_pointer(manager.releases),
            "models": {"chat": OLLAMA_LLM_MODEL, "embedding": OLLAMA_EMBED_MODEL},
            "pack_hashes": pack_hashes, "status": "backed_up", "packs": [], "new_assets": [],
            "inventory_added": [],
        }
        receipt["backup_hashes"] = {path.relative_to(destination).as_posix(): sha256(path.read_bytes()).hexdigest()
                                   for path in destination.rglob("*") if path.is_file()}
        _atomic_json(destination / "receipt.json", receipt)
    return destination, receipt, snapshot


def promote(base_dir=BASE_DIR, *, actor, reason):
    if not actor.strip() or not reason.strip():
        raise ValueError("Actor and reason are required.")
    base = Path(base_dir).resolve()
    manager = KnowledgeManagementService(base)
    state = _require(manager.inspect())
    if state.data["authority"] != "sqlite":
        raise ValueError("Pack promotion requires SQLite authority.")
    paths = [base / "knowledge_packs" / name for name in DOMAINS]
    packs = [read_pack(path) for path in paths]
    hashes = {path.relative_to(base).as_posix(): sha256(path.read_bytes()).hexdigest()
              for root in paths for path in root.rglob("*") if path.is_file()}
    fixture_path = base / "knowledge_packs/fixtures/devices.json"
    fixture_raw = fixture_path.read_bytes()
    hashes[fixture_path.relative_to(base).as_posix()] = sha256(fixture_raw).hexdigest()
    inventory_path = base / "data/inventory/devices.json"
    inventory_raw = inventory_path.read_bytes()
    current = json.loads(inventory_raw)
    merged = merge_demo_devices(current, json.loads(fixture_raw))
    all_assets = {}
    for pack in packs:
        prepare_request(manager, pack, actor=actor, reason=reason)
        for name, raw in pack["assets"].items():
            destination = safe_path(base, name)
            if name in all_assets and all_assets[name] != raw:
                raise ValueError(f"Packs disagree on template asset: {name}")
            if destination.exists() and destination.read_bytes() != raw:
                raise ValueError(f"Existing template differs from reviewed asset: {name}")
            all_assets[name] = raw
    backup, receipt, before = _backup(manager, hashes, actor, reason)
    receipt_path = backup / "receipt.json"
    try:
        if manager.inspect().revision != before["revision"]:
            raise ValueError("Authoring changed after backup; retry.")
        for pack in packs:
            receipt["new_assets"].extend(name for name in pack["assets"] if not (base / name).exists())
            _atomic_json(receipt_path, receipt)
            install_reviewed_assets(pack, base)
            request = prepare_request(manager, pack, actor=actor, reason=reason)
            result = None
            if request:
                _require(manager.apply(request, dry_run=True))
                result = _require(manager.apply(request))
            receipt["packs"].append({"pack": pack["manifest"]["pack_id"], "changed": request is not None,
                                     "revision": result.revision if result else manager.inspect().revision})
            receipt["status"] = "applying"
            _atomic_json(receipt_path, receipt)
        _require(manager.validate())
        after = manager.store.snapshot()
        previous_ids = {row["operation_id"] for row in before["catalogs"]["operations"]}
        for name in ("operations", "operation_parameters", "operation_rules", "template_bindings"):
            retained = [row for row in after["catalogs"][name] if row["operation_id"] in previous_ids]
            if retained != before["catalogs"][name]:
                raise ValueError(f"Promotion changed an existing contract: {name}")
        if active_pointer(manager.releases) != receipt["active_release"]:
            raise ValueError("Active release changed during promotion; review before continuing.")
        if inventory_path.read_bytes() != inventory_raw:
            raise ValueError("Inventory changed during promotion; review before merging demonstration devices.")
        if merged != current:
            receipt["inventory_added"] = [row["id"] for row in merged if row["id"] not in {item["id"] for item in current}]
            _atomic_json(receipt_path, receipt)
            _atomic_json(inventory_path, merged)
        receipt.update(status="applied_unpublished", after_revision=after["revision"],
                       operations=len(after["catalogs"]["operations"]),
                       bindings=len(after["catalogs"]["template_bindings"]))
        _atomic_json(receipt_path, receipt)
        return {"backup": str(backup), **receipt}
    except BaseException as exc:
        receipt.update(status="interrupted", error=str(exc))
        _atomic_json(receipt_path, receipt)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=BASE_DIR)
    parser.add_argument("--apply", action="store_true", help="Back up and apply packs/devices; does not publish.")
    parser.add_argument("--actor")
    parser.add_argument("--reason")
    args = parser.parse_args()
    if args.apply:
        if not args.actor or not args.reason:
            parser.error("--apply requires --actor and --reason")
        result = promote(args.project, actor=args.actor, reason=args.reason)
        print(json.dumps({key: result[key] for key in ("backup", "status", "operations", "bindings", "inventory_added", "packs")}, indent=2))
    else:
        with rehearse([args.project / "knowledge_packs" / name for name in DOMAINS], source_base=args.project) as (_, snapshot, reports):
            print(json.dumps({"mode": "isolated_offline", "operations": len(snapshot.manifest["schemas"]),
                              "bindings": len(snapshot.manifest["template_bindings"]), "packs": reports}, indent=2))


if __name__ == "__main__":
    main()
