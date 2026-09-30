"""Local intent-knowledge management. Editing and publication are separate actions."""

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re

from pydantic import ValidationError

from ..api.contracts import CatalogExport, EditRequest, ImportRequest, ManagementIssue, ManagementResult, MigrationRequest, OperationContractInput, PublishRequest
from ..config import BASE_DIR
from .authoring_store import AuthoringError, CATALOG_NAMES
from .authority import authoring_store, authority
from .document_repository import DocumentKnowledgeRepository
from .models import Category, CategoryParameter, Operation, ParameterDefinition
from .publication import _validate_context_rules, publish, validate_bindings
from .runtime import active_pointer, active_snapshot
from .schema_compiler import compile_schema
from .services import KnowledgeService


class KnowledgeManagementService:
    def __init__(self, base_dir=BASE_DIR, *, releases_dir=None):
        self.base = Path(base_dir)
        self.releases = Path(releases_dir) if releases_dir else self.base / "storage/catalog_releases"

    @property
    def store(self):
        return authoring_store(self.base)

    def _result(self, action):
        try:
            return action()
        except ValidationError as exc:
            return ManagementResult(ok=False, issues=[ManagementIssue(code="INVALID_REQUEST",
                path=".".join(str(part) for part in error["loc"]), message=error["msg"]) for error in exc.errors()])
        except AuthoringError as exc:
            return ManagementResult(ok=False, issues=[ManagementIssue(code=exc.code, path=exc.path, message=str(exc))])
        except (ValueError, KeyError, TypeError, OSError) as exc:
            return ManagementResult(ok=False, issues=[ManagementIssue(code="VALIDATION_ERROR", message=str(exc))])
        except Exception as exc:
            return ManagementResult(ok=False, issues=[ManagementIssue(code="BACKEND_ERROR", message=str(exc))])

    def _require_published_runtime(self):
        if active_snapshot(self.releases) is None:
            raise AuthoringError("PUBLICATION_REQUIRED", "Publish the reviewed baseline before management writes so drafts cannot alter source-mode runtime.")

    def _precommit(self, before, after):
        self._require_published_runtime()
        self._check_deletions(before, after)

    def inspect(self):
        def action():
            snapshot = self.store.snapshot()
            return ManagementResult(ok=True, revision=snapshot["revision"], data={
                "counts": {name: len(rows) for name, rows in snapshot["catalogs"].items()},
                "active_release": active_pointer(self.releases), "authority": authority(self.base)})
        return self._result(action)

    @staticmethod
    def _validate(catalogs, sources, *, complete):
        if set(catalogs) != set(CATALOG_NAMES):
            raise AuthoringError("INVALID_CATALOGS", "Catalog document names do not match the supported export format.")
        service = KnowledgeService(DocumentKnowledgeRepository(catalogs))
        service.validate_metadata()
        service.validate_category_parameters()
        service.validate_operation_records()
        schemas, warnings = {}, []
        for op in service.list_operations(True):
            if not complete and op.status == "inactive" and not service.list_operation_rules(op.operation_id):
                warnings.append(f"{op.operation_id}: incomplete inactive draft; complete or delete it before publication.")
                continue
            schemas[op.operation_id] = compile_schema(service, op.operation_id)
        bindings = catalogs["template_bindings"]
        if not complete:
            if any(row["operation_id"] not in schemas for row in bindings):
                raise ValueError("A template binding requires a complete operation schema.")
        validate_bindings(bindings, service, schemas, sources)
        _validate_context_rules(catalogs["context_rules"], schemas)
        return service, schemas, warnings

    def validate(self):
        def action():
            snapshot = self.store.snapshot()
            _, schemas, warnings = self._validate(snapshot["catalogs"], snapshot["sources"], complete=True)
            return ManagementResult(ok=True, revision=snapshot["revision"], data={"operations": list(schemas)}, warnings=warnings)
        return self._result(action)

    def preview_schema(self, operation_id, vendor=None):
        def action():
            from ..parameters.schema_loader import _apply_vendor_requirements
            snapshot = self.store.snapshot()
            service = KnowledgeService(DocumentKnowledgeRepository(snapshot["catalogs"]))
            service.validate_metadata()
            service.validate_category_parameters()
            schema = compile_schema(service, operation_id)
            if vendor is not None:
                if not any(row["operation_id"] == operation_id and row["vendor"] == vendor for row in snapshot["catalogs"]["template_bindings"]):
                    raise ValueError(f"No declared support for vendor {vendor}.")
                schema = _apply_vendor_requirements(schema, [{"vendor": vendor}])
            return ManagementResult(ok=True, revision=snapshot["revision"], data={"operation_id": operation_id, "schema": schema})
        return self._result(action)

    def _was_published(self, entity, identity):
        name, key = {"category": ("categories", "category_id"), "parameter": ("parameters", "parameter_id"),
                     "operation": ("operations", "operation_id")}[entity]
        for release in self.releases.glob("*"):
            if re.fullmatch(r"[a-f0-9]{32}", release.name) and (release / "manifest.json").exists():
                rows = json.loads((release / "catalog" / (name + ".json")).read_text(encoding="utf-8"))
                if any(row[key] == identity for row in rows):
                    return True
        return False

    def _change(self, catalogs, change):
        entity, action, identity, values = change.entity, change.action, change.entity_id, deepcopy(change.values)
        if entity == "membership":
            if action not in {"assign", "unassign"}:
                raise ValueError("Membership actions are assign/unassign.")
            pair = CategoryParameter.model_validate(values).model_dump()
            rows = catalogs["category_parameters"]
            if action == "assign":
                if pair in rows:
                    raise ValueError("Membership already exists.")
                rows.append(pair)
            else:
                if pair not in rows:
                    raise KeyError("Membership does not exist.")
                rows.remove(pair)
            return
        if entity == "context_rules":
            if action != "replace":
                raise ValueError("Context rules use replace.")
            catalogs["context_rules"] = values
            return
        if entity == "contract":
            if action != "replace":
                raise ValueError("Operation contracts use replace.")
            contract = OperationContractInput.model_validate(values)
            operation = next((row for row in catalogs["operations"] if row["operation_id"] == identity), None)
            if operation is None:
                raise KeyError(f"Unknown operation {identity}")
            if contract.version < operation.get("version", 1):
                raise ValueError("Operation version cannot decrease.")
            for name, rows in (("operation_parameters", contract.mappings), ("operation_rules", contract.rules), ("template_bindings", contract.templates)):
                if any(row.operation_id != identity or row.operation_version != contract.version for row in rows):
                    raise ValueError("Every contract record must use the selected operation ID and version.")
                catalogs[name] = [row for row in catalogs[name] if row["operation_id"] != identity] + [row.model_dump() for row in rows]
            operation.update(version=contract.version, schema_source="registry", mapping_mode="none")
            return
        name, key, model = {"category": ("categories", "category_id", Category),
                            "parameter": ("parameters", "parameter_id", ParameterDefinition),
                            "operation": ("operations", "operation_id", Operation)}[entity]
        if not identity:
            raise ValueError("This change requires entity_id.")
        rows = catalogs[name]
        current = next((row for row in rows if row[key] == identity), None)
        if action == "create":
            if current is not None:
                raise ValueError(f"{identity} already exists.")
            if key in values and values[key] != identity:
                raise ValueError("Record ID must equal entity_id.")
            if entity == "operation":
                values = {"status": "inactive", "schema_source": "registry", "mapping_mode": "none", **values}
            rows.append(model.model_validate({**values, key: identity}).to_legacy_dict())
            return
        if current is None:
            raise KeyError(f"Unknown {entity}: {identity}")
        if action == "update":
            if key in values and values[key] != identity:
                raise ValueError("Machine IDs cannot be renamed; edit display_name instead.")
            updated = model.model_validate({**current, **values}).to_legacy_dict()
            if entity == "operation" and updated.get("version", 1) < current.get("version", 1):
                raise ValueError("Operation version cannot decrease.")
            current.clear()
            current.update(updated)
        elif action == "retire" and entity in {"category", "operation"}:
            current["status"] = "inactive"
        elif action == "delete":
            if self._was_published(entity, identity):
                raise AuthoringError("PUBLISHED_DEPENDENCY", "Published identities cannot be deleted; retire or migrate them.")
            rows.remove(current)
        else:
            raise ValueError(f"Unsupported {entity} action: {action}")

    @staticmethod
    def _impact(before, after):
        changed = {name for name in before if before[name] != after[name]}
        operations = {row["operation_id"] for row in before["operations"] + after["operations"]}
        affected = set()
        for operation_id in operations:
            for name in ("operations", "operation_parameters", "operation_rules", "template_bindings"):
                if [row for row in before[name] if row["operation_id"] == operation_id] != [row for row in after[name] if row["operation_id"] == operation_id]:
                    affected.add(operation_id)
        if changed & {"categories", "parameters", "category_parameters", "context_rules"}:
            affected.update(operations)
        return {"changed_catalogs": sorted(changed), "affected_operations": sorted(affected)}

    def _check_deletions(self, before, after):
        for entity, name, key in (("category", "categories", "category_id"), ("parameter", "parameters", "parameter_id"), ("operation", "operations", "operation_id")):
            removed = {row[key] for row in before[name]} - {row[key] for row in after[name]}
            for identity in removed:
                if self._was_published(entity, identity):
                    raise AuthoringError("PUBLISHED_DEPENDENCY", f"Cannot remove published {entity} {identity}.")
                if entity == "operation":
                    planned = self.base / "data/planned/parameters.json"
                    if planned.exists() and any(row["operation_id"] == identity for row in json.loads(planned.read_text(encoding="utf-8"))["records"]):
                        raise AuthoringError("CONTEXT_DEPENDENCY", f"Planned context still references {identity}.")

    def apply(self, request, *, dry_run=False):
        def action():
            typed = EditRequest.model_validate(request)
            if not dry_run:
                self._require_published_runtime()
            snapshot = self.store.snapshot()
            if typed.expected_revision != snapshot["revision"]:
                raise AuthoringError("STALE_REVISION", "Authoring files changed; reload before editing.")
            candidate = deepcopy(snapshot["catalogs"])
            for index, change in enumerate(typed.changes):
                try:
                    self._change(candidate, change)
                except (ValueError, KeyError) as exc:
                    if isinstance(exc, AuthoringError):
                        raise
                    raise AuthoringError("INVALID_CHANGE", str(exc), f"changes.{index}") from exc
            self._check_deletions(snapshot["catalogs"], candidate)
            _, _, warnings = self._validate(candidate, snapshot["sources"], complete=False)
            impact = self._impact(snapshot["catalogs"], candidate)
            committed = {"revision": snapshot["revision"], "audit_id": None} if dry_run else self.store.commit(
                candidate, expected_revision=typed.expected_revision, actor=typed.actor, reason=typed.reason,
                precommit=lambda: self._precommit(snapshot["catalogs"], candidate))
            return ManagementResult(ok=True, revision=committed["revision"], data={**impact, "audit_id": committed["audit_id"], "dry_run": dry_run}, warnings=warnings)
        return self._result(action)

    def export(self):
        def action():
            snapshot = self.store.snapshot()
            assets = {name: sha256(raw).hexdigest() for name, raw in snapshot["sources"].items() if not name.startswith("data/catalog/")}
            bundle = CatalogExport(revision=snapshot["revision"], catalogs=snapshot["catalogs"], asset_hashes=assets)
            return ManagementResult(ok=True, revision=snapshot["revision"], data={"bundle": bundle.model_dump()})
        return self._result(action)

    def import_catalog(self, request):
        def action():
            typed = ImportRequest.model_validate(request)
            self._require_published_runtime()
            snapshot = self.store.snapshot()
            if snapshot["revision"] != typed.expected_revision:
                raise AuthoringError("STALE_REVISION", "Authoring files changed before import.")
            assets = {name: sha256(raw).hexdigest() for name, raw in snapshot["sources"].items() if not name.startswith("data/catalog/")}
            if assets != typed.bundle.asset_hashes:
                raise AuthoringError("ASSET_MISMATCH", "Restore/review the matching schema and template assets before importing catalog metadata.")
            candidate = typed.bundle.catalogs
            self._check_deletions(snapshot["catalogs"], candidate)
            self._validate(candidate, snapshot["sources"], complete=False)
            committed = self.store.commit(candidate, expected_revision=typed.expected_revision, actor=typed.actor, reason=typed.reason,
                precommit=lambda: self._precommit(snapshot["catalogs"], candidate))
            return ManagementResult(ok=True, revision=committed["revision"], data={"audit_id": committed["audit_id"]})
        return self._result(action)

    def publish(self, request, *, index_builder=None):
        def action():
            typed = PublishRequest.model_validate(request)
            snapshot = publish(base_dir=self.base, releases_dir=self.releases, mode=typed.mode,
                expected_release=typed.expected_release, expected_revision=typed.expected_revision,
                actor=typed.actor, reason=typed.reason, index_builder=index_builder)
            return ManagementResult(ok=True, revision=snapshot.manifest["authoring_revision"], data={"release_id": snapshot.release_id, "mode": typed.mode})
        return self._result(action)

    def migrate_sqlite(self, request):
        def action():
            from .sqlite_repository import migrate_to_sqlite
            typed = MigrationRequest.model_validate(request)
            result = migrate_to_sqlite(self.base, releases_dir=self.releases, **typed.model_dump())
            return ManagementResult(ok=True, revision=result["revision"], data=result)
        return self._result(action)

    def recover(self):
        return self._result(lambda: ManagementResult(ok=True, data=self.store.recover()))
