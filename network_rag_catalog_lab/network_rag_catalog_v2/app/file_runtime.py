"""Direct catalog/schema/template support for terminal experiments."""

from hashlib import sha256
import json

from jinja2 import Environment, StrictUndefined, meta

from .config import DATA_DIR, OLLAMA_EMBED_MODEL


def catalog_revision():
    digest = sha256()
    for directory in ("catalog", "operations", "templates"):
        for path in sorted((DATA_DIR / directory).rglob("*")):
            if path.is_file() and path.suffix in {".json", ".j2"}:
                digest.update(path.relative_to(DATA_DIR).as_posix().encode())
                digest.update(path.read_bytes())
    return digest.hexdigest()


def validate_files():
    from .catalog import knowledge_service
    from .knowledge.migration import schema_parameter_references
    from .knowledge.rule_registry import TEMPLATE_DERIVATIONS, validate_handler_ids, validate_object_requirements
    from .knowledge.runtime import safe_path
    from .parameters.schema_loader import _apply_vendor_requirements
    from jsonschema import Draft202012Validator
    service = knowledge_service()
    service.validate_metadata()
    service.validate_category_parameters()
    schemas = {}
    for op in service.list_operations():
        expected = f"data/operations/{op.category_id}/{op.operation_id}/schema.json"
        if op.schema_path != expected:
            raise ValueError(f"Use the direct schema path {expected} for {op.operation_id}.")
        schema = json.loads(safe_path(DATA_DIR.parent, expected).read_text(encoding="utf-8"))
        _apply_vendor_requirements(schema, None)  # Verify declared semantic fields before extraction.
        refs = schema_parameter_references(schema, service.list_parameters())
        service.validate_schema_membership(op.category_id, refs)
        validate_handler_ids(schema)
        def check(node):
            validate_object_requirements(node)
            for child in node.get("properties", {}).values():
                check(child)
            if "items" in node:
                check(node["items"])
        check(schema)
        for vendor in schema.get("x-vendor-profiles", {}):
            profile = _apply_vendor_requirements(schema, [{"vendor": vendor}])
            Draft202012Validator.check_schema(profile)
            check(profile)
            service.validate_schema_membership(op.category_id, schema_parameter_references(profile, service.list_parameters()))
            validate_handler_ids(profile)
        if any(field not in schema["properties"] for fields in schema.get("x-required-by-vendor", {}).values() for field in fields):
            raise ValueError(f"Unknown vendor-required field for {op.operation_id}.")
        templates = list((DATA_DIR / "templates").glob(f"*/{op.category_id}/{op.operation_id}/template.j2"))
        if not templates:
            raise ValueError(f"No template exists for {op.operation_id}.")
        env = Environment(undefined=StrictUndefined)
        for path in templates:
            vendor = path.relative_to(DATA_DIR / "templates").parts[0]
            knowledge = op.vendor_knowledge.get(vendor)
            if knowledge and knowledge.status == "blocked_unverified":
                raise ValueError(f"Blocked operation has a direct template: {op.operation_id} / {vendor}")
            profile = _apply_vendor_requirements(schema, [{"vendor": vendor}])
            allowed = set(profile["properties"]) | {key for key, (_, source) in TEMPLATE_DERIVATIONS.items() if source in profile["properties"]}
            inputs = meta.find_undeclared_variables(env.parse(path.read_text(encoding="utf-8")))
            if set(schema.get("x-semantic-fields", [])) - inputs:
                raise ValueError(f"Template omits canonical semantic inputs: {path}")
            unknown = inputs - allowed
            if unknown:
                raise ValueError(f"Unbound template inputs in {path}: {sorted(unknown)}")
        schemas[op.operation_id] = schema
    return schemas


def file_documents(revision=None):
    from .catalog import knowledge_service
    schemas = validate_files()
    service = knowledge_service()
    revision = revision or catalog_revision()
    documents = []
    for op in service.list_operations():
        schema = schemas[op.operation_id]
        available = sorted(path.relative_to(DATA_DIR / "templates").parts[0]
                           for path in (DATA_DIR / "templates").glob(f"*/{op.category_id}/{op.operation_id}/template.j2"))
        support = {"template_vendors": available, "unimplemented_vendors": [vendor for vendor in ("cisco", "huawei", "juniper") if vendor not in available]}
        text = (f"Operation ID: {op.operation_id}\nCategory: {op.category_id}\nName: {op.display_name}\n"
                f"Aliases: {', '.join(op.aliases)}\nDescription: {op.description}\n"
                f"Use cases: {json.dumps(op.use_cases)}\nVendor templates: {json.dumps(support)}\n"
                "Recognize the intent even when the requested vendor template is unavailable; never substitute another vendor's commands.\n"
                f"Parameter contract: {json.dumps(schema, sort_keys=True)}")
        documents.append({"id": op.operation_id, "page_content": text, "metadata": {
            "operation_id": op.operation_id, "category": op.category_id, "operation_version": op.version,
            "catalog_revision": revision, "embedding_model": OLLAMA_EMBED_MODEL,
            "vendor_support": json.dumps(support, sort_keys=True)}})
    return documents
