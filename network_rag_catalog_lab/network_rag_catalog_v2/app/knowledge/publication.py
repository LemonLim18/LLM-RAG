"""Validate the selected authoring repository, stage and atomically activate a release."""

from contextlib import contextmanager
from datetime import datetime, UTC
from hashlib import sha256
import json
from pathlib import Path
from uuid import uuid4

from jinja2 import Environment, StrictUndefined, meta, nodes

from ..config import BASE_DIR, CATALOG_RELEASES_DIR
from .file_repository import FileKnowledgeRepository
from .models import TemplateBinding
from .runtime import KnowledgeSnapshot, active_pointer
from .schema_compiler import compile_schema
from .services import KnowledgeService

_UNSPECIFIED = object()


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _sources(base, *, include_managed_catalogs=True):
    from .authoring_store import CATALOG_NAMES
    paths = [*base.joinpath("data/catalog").glob("*.json"),
             *base.joinpath("data/operations").rglob("schema.json"),
             *base.joinpath("data/templates").rglob("*.j2")]
    return {path.relative_to(base).as_posix(): path.read_bytes() for path in sorted(paths)
            if not path.name.startswith(".") and (include_managed_catalogs or path.parent != base / "data/catalog" or path.stem not in CATALOG_NAMES)}


def _source_digest(sources):
    return sha256(json.dumps({name: sha256(raw).hexdigest() for name, raw in sources.items()}, sort_keys=True).encode()).hexdigest()


def _service(root):
    return KnowledgeService(FileKnowledgeRepository(categories_file=root / "categories.json",
        operations_file=root / "operations.json", parameters_file=root / "parameters.json"))


def validate_bindings(records, service, schemas, sources):
    if not isinstance(records, list):
        raise ValueError("Template bindings must be an array.")
    bindings = [TemplateBinding.model_validate(record) for record in records]
    operations = {row.operation_id: row for row in service.list_operations(True)}
    seen = set()
    env = Environment(undefined=StrictUndefined)
    for binding in bindings:
        op = operations.get(binding.operation_id)
        if op is None or op.version != binding.operation_version:
            raise ValueError(f"Unknown/stale template binding: {binding.operation_id}")
        for version in binding.versions:
            key = (op.operation_id, binding.vendor, binding.platform, version)
            if key in seen:
                raise ValueError(f"Overlapping template binding: {key}")
            seen.add(key)
        name = binding.template_path
        if not name.startswith("data/templates/") or name not in sources or ".." in Path(name).parts:
            raise ValueError(f"Missing or unsafe template reference: {name}")
        schema = schemas[op.operation_id]
        contract = binding.input_contract
        if set(contract.fields) != set(schema["properties"]) or len(contract.fields) != len(set(contract.fields)):
            raise ValueError(f"Template input fields differ from schema: {name}")
        required = set(schema.get("required", [])) | set(schema.get("x-required-by-vendor", {}).get(binding.vendor, []))
        if set(contract.optional_defaults) - (set(contract.fields) - required):
            raise ValueError(f"Defaults may only declare optional schema inputs: {name}")
        from .rule_registry import TEMPLATE_DERIVATIONS
        for output, handler in contract.derived.items():
            spec = TEMPLATE_DERIVATIONS.get(output)
            if spec is None or spec[0] != handler or spec[1] not in required:
                raise ValueError(f"Invalid derived template inputs: {name}")
        tree = env.parse(sources[name].decode("utf-8"))
        if any(tree.find_all((nodes.Include, nodes.Import, nodes.FromImport, nodes.Extends))):
            raise ValueError("Templates must be standalone, reviewed artifacts.")
        unknown = meta.find_undeclared_variables(tree) - required - set(contract.optional_defaults) - set(contract.derived)
        if unknown:
            raise ValueError(f"Unbound template inputs in {name}: {sorted(unknown)}")
    for op in service.list_operations():
        if not any(binding.operation_id == op.operation_id for binding in bindings):
            raise ValueError(f"Active operation has no declared template support: {op.operation_id}")
    from .vendor_coverage import validate_vendor_knowledge
    validate_vendor_knowledge(operations.values(), bindings)
    return bindings


def build_documents(operations, schemas, release_id, service, bindings=None):
    documents = []
    bindings = bindings or []
    known_vendors = sorted({binding.vendor for binding in bindings} | {
        vendor for op in operations for vendor in op.vendor_knowledge})
    for op in operations:
        if op.status != "active":
            continue
        schema = schemas[op.operation_id]
        summaries = [{"field_path": row.field_path, "required": row.required,
                      "parameter": service.get_parameter(row.parameter_id).to_legacy_dict()}
                     for row in service.list_operation_parameters(op.operation_id)]
        profiles = []
        for binding in bindings:
            if binding.operation_id != op.operation_id:
                continue
            required = list(dict.fromkeys([*schema.get("required", []),
                                          *schema.get("x-required-by-vendor", {}).get(binding.vendor, [])]))
            profiles.append({"vendor": binding.vendor, "platform": binding.platform,
                             "versions": binding.versions, "required_parameters": required,
                             "optional_parameters": [field for field in schema["properties"] if field not in required]})
        supported = {profile["vendor"] for profile in profiles}
        support = {"profiles": profiles, "unimplemented_vendors": [vendor for vendor in known_vendors if vendor not in supported]}
        if op.vendor_knowledge:
            support["vendors"] = [{"vendor": vendor, "intent_known": True, **record.model_dump()}
                                  for vendor, record in sorted(op.vendor_knowledge.items())]
        documents.append({"id": op.operation_id, "page_content": (
            f"Operation ID: {op.operation_id}\nCategory: {op.category_id}\nName: {op.display_name}\n"
            f"Aliases: {', '.join(op.aliases)}\nDescription: {op.description}\n"
            f"Vendor support and operation-specific parameters: {json.dumps(support, sort_keys=True)}\n"
            "A missing vendor binding is not executable support. Exact device capabilities and inventory facts must also validate.\n"
            "Recognize blocked intents without substituting another operation or another vendor's syntax.\n"
            f"Use cases: {json.dumps(op.use_cases)}\nParameter summaries: {json.dumps(summaries, sort_keys=True)}\n"
            f"Parameter contract: {json.dumps(schema, sort_keys=True)}"),
            "metadata": {"operation_id": op.operation_id, "category": op.category_id,
                         "operation_version": op.version, "release_id": release_id,
                         "vendor_support": json.dumps(support, sort_keys=True)}})
    return documents


def _validate_context_rules(configuration, schemas):
    from ..parameters.fields import schema_at
    from ..devices.operation_policies import validate_policy_binding
    from .resource_keys import validate_composite_keys
    for operation_id, rules in configuration["operations"].items():
        if operation_id not in schemas or any(other not in schemas for other in rules.get("conflicts_with", [])):
            raise ValueError(f"Unknown operation in context rules: {operation_id}")
        for path in rules.get("inventory_fields", []) + rules.get("planned_fields", []) + rules.get("resource_keys", []):
            schema_at(schemas[operation_id], path.replace("[]", "[0]"))
        if "device_policy" in rules:
            validate_policy_binding(rules["device_policy"], schemas[operation_id])
        validate_composite_keys(rules, schemas[operation_id])


@contextmanager
def _publication_lock(root):
    path = root / ".publication.lock"
    try:
        handle = path.open("x", encoding="utf-8")
    except FileExistsError as exc:
        raise ValueError("Another publication is in progress; review a stale lock after a crash.") from exc
    try:
        with handle:
            yield
    finally:
        path.unlink()


def publish(*, base_dir=BASE_DIR, releases_dir=CATALOG_RELEASES_DIR, mode="chroma",
            index_builder=None, expected_release=_UNSPECIFIED, verify_legacy=False,
            expected_revision=None, actor="local", reason="Publish reviewed catalog"):
    """Failed stages are retained for inspection, never activated."""
    if mode not in {"offline", "chroma"}:
        raise ValueError("Publication mode must be offline or chroma.")
    base, root = Path(base_dir), Path(releases_dir)
    root.mkdir(parents=True, exist_ok=True)
    from .authoring_store import authoring_lock, AuthoringError
    from .authority import authoring_snapshot_unlocked, authority
    with _publication_lock(root), authoring_lock(base):
        if (base / "data/catalog/.authoring-pending.json").exists():
            raise AuthoringError("RECOVERY_REQUIRED", "Recover unfinished authoring before publication.")
        previous = active_pointer(root)
        previous_id = previous["release_id"] if previous else None
        if expected_release is not _UNSPECIFIED and expected_release != previous_id:
            raise ValueError("Stale publication: active release changed.")
        draft = authoring_snapshot_unlocked(base)
        sources = draft["sources"]
        if expected_revision is not None and draft["revision"] != expected_revision:
            raise AuthoringError("STALE_REVISION", "Authoring files changed before publication.")
        release_id = uuid4().hex
        stage = root / (".stage-" + release_id)
        stage.mkdir()
        for name, raw in sources.items():
            if name.startswith("data/catalog/"):
                path = stage / "catalog" / Path(name).name
                path.parent.mkdir(exist_ok=True)
                path.write_bytes(raw)
        service = _service(stage / "catalog")
        service.validate_metadata()
        service.validate_category_parameters()
        service.validate_operation_records()
        operations = service.list_operations(True)
        schemas = {}
        for op in operations:
            compiled = compile_schema(service, op.operation_id)
            if op.schema_source == "legacy" or (verify_legacy and op.schema_path):
                raw = json.loads(sources[op.schema_path])
                if not service.compare_operation_schema(op.operation_id, raw)["matches"]:
                    raise ValueError(f"Legacy schema comparison failed: {op.operation_id}")
            schemas[op.operation_id] = compiled
        bindings = validate_bindings(json.loads(sources["data/catalog/template_bindings.json"]), service, schemas, sources)
        _validate_context_rules(json.loads(sources["data/catalog/context_rules.json"]), schemas)
        # A contract/template change must have a new operation version, not just a new release ID.
        if previous:
            old = KnowledgeSnapshot(root, previous)
            old_ops = {row.operation_id: row for row in old.service.list_operations(True)}
            for op in operations:
                if op.operation_id not in old_ops:
                    continue
                before = old_ops[op.operation_id]
                if op.version < before.version:
                    raise ValueError(f"Operation version cannot decrease: {op.operation_id}")
                old_bindings = old.manifest["template_bindings"]
                old_signatures = sorted((row["vendor"], row["platform"], tuple(row["versions"]), row["template_sha256"], json.dumps(row["input_contract"], sort_keys=True)) for row in old_bindings if row["operation_id"] == op.operation_id)
                new_signatures = sorted((row.vendor, row.platform, tuple(row.versions), sha256(sources[row.template_path]).hexdigest(), json.dumps(row.input_contract.model_dump(), sort_keys=True)) for row in bindings if row.operation_id == op.operation_id)
                if op.version == before.version and (op.category_id != before.category_id or old.schema(op.operation_id) != schemas[op.operation_id] or old_signatures != new_signatures):
                    raise ValueError(f"Contract/template change requires an operation version bump: {op.operation_id}")
        schema_paths = {}
        for operation_id, schema in schemas.items():
            schema_paths[operation_id] = f"schemas/{operation_id}.json"
            _write(stage / schema_paths[operation_id], schema)
        released_bindings = []
        for index, binding in enumerate(bindings):
            from ..parameters.schema_loader import _apply_vendor_requirements
            relative = f"templates/{index}/template.j2"
            raw = sources[binding.template_path]
            destination = stage / relative
            destination.parent.mkdir(parents=True)
            destination.write_bytes(raw)
            profile_schema = f"schemas/profiles/{index}.json"
            _write(stage / profile_schema, _apply_vendor_requirements(schemas[binding.operation_id], [{"vendor": binding.vendor}]))
            released_bindings.append({**binding.model_dump(), "artifact_path": relative,
                                      "template_sha256": sha256(raw).hexdigest(), "schema_artifact": profile_schema})
        documents = build_documents(operations, schemas, release_id, service, bindings)
        _write(stage / "retrieval_documents.json", documents)
        retrieval = {"mode": mode, "ready": False}
        if mode == "chroma":
            index_path = base.resolve() / "storage/chroma"
            if index_builder is None:
                from ..ingest import build_release_index
                def index_builder(identity, records):
                    return build_release_index(identity, records, chroma_dir=index_path)
            receipt = index_builder(release_id, documents)
            if not isinstance(receipt, dict) or receipt.get("release_id") != release_id or receipt.get("ids") != sorted(doc["id"] for doc in documents):
                raise ValueError("Retrieval build did not verify the complete release.")
            if receipt.get("collection") != "knowledge_" + release_id or not receipt.get("embedding_model"):
                raise ValueError("Retrieval build returned an invalid index identity.")
            retrieval = {**receipt, "mode": mode, "ready": True, "index_path": str(index_path)}
        artifacts = {path.relative_to(stage).as_posix(): sha256(path.read_bytes()).hexdigest() for path in stage.rglob("*") if path.is_file()}
        manifest = {"format_version": 1, "release_id": release_id, "previous_release": previous_id,
                    "actor": actor, "reason": reason,
                    "authoring_backend": authority(base), "authoring_revision": draft["revision"],
                    "created_at": datetime.now(UTC).isoformat(), "source_digest": _source_digest(sources),
                    "schemas": schema_paths, "template_bindings": released_bindings,
                    "retrieval": retrieval, "artifacts": artifacts}
        _write(stage / "manifest.json", manifest)
        if authoring_snapshot_unlocked(base)["revision"] != draft["revision"] or active_pointer(root) != previous:
            raise ValueError("Authoring sources or active release changed during publication; retry.")
        destination = root / release_id
        stage.rename(destination)
        pointer = {"release_id": release_id, "manifest_sha256": sha256((destination / "manifest.json").read_bytes()).hexdigest()}
        snapshot = KnowledgeSnapshot(root, pointer)
        temporary = root / f".active-{release_id}.tmp"
        _write(temporary, pointer)
        temporary.replace(root / "active.json")
        return snapshot


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Explicitly publish without semantic retrieval.")
    parser.add_argument("--verify-legacy", action="store_true", help="Require equality with retained migration schemas.")
    args = parser.parse_args()
    snapshot = publish(mode="offline" if args.offline else "chroma", verify_legacy=args.verify_legacy)
    print(f"Published {snapshot.release_id} ({snapshot.manifest['retrieval']['mode']}).")


if __name__ == "__main__":
    main()
