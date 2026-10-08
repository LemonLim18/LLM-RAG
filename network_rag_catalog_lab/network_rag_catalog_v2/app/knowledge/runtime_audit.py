"""Read-only comparison of direct files, managed authoring and the active release.

Run before reconciling/publishing knowledge; a mismatch requires review, never
automatic copying of vendor semantics into another authority.
"""

import argparse
from contextlib import closing
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sqlite3

from ..config import BASE_DIR
from ..parameters.schema_loader import _apply_vendor_requirements
from .authority import authority
from .document_repository import DocumentKnowledgeRepository
from .file_repository import FileKnowledgeRepository
from .runtime import KnowledgeSnapshot, active_pointer, safe_path
from .schema_compiler import compile_schema
from .services import KnowledgeService


def _contract(schema):
    """Ignore presentation metadata, retaining assertions and runtime handlers."""
    if not isinstance(schema, dict):
        return deepcopy(schema)
    result = {key: deepcopy(value) for key, value in schema.items()
              if key not in {"title", "description", "x-parameter", "x-semantic-fields"}}
    # Property names are data, even when a field is named "description".
    for key in ("properties", "patternProperties", "$defs", "dependentSchemas"):
        if key in result:
            result[key] = {name: _contract(node) for name, node in result[key].items()}
    for key in ("items", "additionalProperties", "contains", "if", "then", "else", "not", "unevaluatedProperties"):
        if key in result:
            result[key] = _contract(result[key])
    for key in ("allOf", "anyOf", "oneOf", "prefixItems"):
        if key in result:
            result[key] = [_contract(node) for node in result[key]]
    return result


def audit_runtime(base_dir=BASE_DIR, operation_ids=None):
    base = Path(base_dir).resolve()
    catalog = base / "data/catalog"
    direct = KnowledgeService(FileKnowledgeRepository(categories_file=catalog / "categories.json",
        operations_file=catalog / "operations.json", parameters_file=catalog / "parameters.json"))
    backend = authority(base)
    if backend == "sqlite":
        from .sqlite_repository import SQLiteAuthoringStore
        with closing(sqlite3.connect((base / "storage/knowledge/catalog.sqlite3").as_uri() + "?mode=ro", uri=True)) as connection:
            documents = SQLiteAuthoringStore._catalogs(connection)
        managed = KnowledgeService(DocumentKnowledgeRepository(documents))
        bindings = documents["template_bindings"]
    else:
        managed = direct
        bindings = json.loads((catalog / "template_bindings.json").read_text(encoding="utf-8"))
    root = base / "storage/catalog_releases"
    pointer = active_pointer(root)
    published = KnowledgeSnapshot(root, pointer) if pointer else None
    ids = operation_ids or [op.operation_id for op in direct.list_operations()]
    differences = []

    def signature(service, identity, mode):
        op = service.get_operation(identity)
        raw = (json.loads(safe_path(base, op.schema_path).read_text(encoding="utf-8")) if mode == "files"
               else published.schema(identity) if mode == "published" else compile_schema(service, identity))
        vendor_contracts = {}
        for vendor in ("cisco", "huawei", "juniper"):
            if mode == "files":
                path = base / f"data/templates/{vendor}/{op.category_id}/{identity}/template.j2"
                knowledge = op.vendor_knowledge.get(vendor)
                supported = path.is_file() and not (knowledge and knowledge.status == "blocked_unverified")
                profiles = [{"schema": _contract(_apply_vendor_requirements(raw, [{"vendor": vendor}])),
                             "template_sha256": sha256(path.read_bytes()).hexdigest()}] if supported else []
            else:
                rows = published.manifest["template_bindings"] if mode == "published" else bindings
                profiles = []
                for row in rows:
                    if row["operation_id"] != identity or row["vendor"] != vendor:
                        continue
                    schema = published.schema(identity, vendor) if mode == "published" else _apply_vendor_requirements(raw, [{"vendor": vendor}])
                    path = safe_path(published.root, row["artifact_path"]) if mode == "published" else safe_path(base, row["template_path"])
                    profile = {"schema": _contract(schema), "template_sha256": sha256(path.read_bytes()).hexdigest()}
                    if profile not in profiles:
                        profiles.append(profile)
            vendor_contracts[vendor] = profiles
        # Direct mode has no platform/version binding restriction. Compare
        # equivalent semantic contracts separately from that deployment scope.
        return {"description": op.description, "schema": _contract(_apply_vendor_requirements(raw, None)),
                "vendors": vendor_contracts}

    for identity in ids:
        actual = signature(direct, identity, "files")
        for source, service in [("managed", managed), *([("published", published.service)] if published else [])]:
            try:
                expected = signature(service, identity, source)
            except KeyError:
                differences.append({"operation_id": identity, "source": source, "component": "operation", "reason": "missing"})
                continue
            for component in ("description", "schema", "vendors"):
                if actual[component] != expected[component]:
                    differences.append({"operation_id": identity, "source": source, "component": component,
                                        "files": actual[component], source: expected[component]})
    return {"managed_authority": backend, "knowledge_snapshot_id": published.release_id if published else "",
            "operations_checked": ids, "matches": not differences, "differences": differences,
            "scope": "Descriptions, schema assertions and vendor template content; direct mode has no managed platform/version binding gate."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--operation", action="append", dest="operations")
    parser.add_argument("--check", action="store_true", help="Exit nonzero on drift for use as a reconciliation gate.")
    args = parser.parse_args()
    result = audit_runtime(operation_ids=args.operations)
    print(json.dumps(result, indent=2))
    if args.check and not result["matches"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
