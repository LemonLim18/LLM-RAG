"""Request-scoped, read-only release adapter. No active release means source mode."""

from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from functools import wraps
from hashlib import sha256
import json
from pathlib import Path
import re

from ..config import CATALOG_RELEASES_DIR
from .file_repository import FileKnowledgeRepository
from .services import KnowledgeService

_UNBOUND = object()
_current = ContextVar("knowledge_snapshot", default=_UNBOUND)


def safe_path(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or Path(relative).is_absolute():
        raise ValueError(f"Artifact path escapes its root: {relative}")
    return path


def active_pointer(root: Path | None = None) -> dict | None:
    path = (root or CATALOG_RELEASES_DIR) / "active.json"
    if not path.exists():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(value, dict) or not re.fullmatch(r"[a-f0-9]{32}", str(value.get("release_id", "")))
            or not re.fullmatch(r"[a-f0-9]{64}", str(value.get("manifest_sha256", "")))):
        raise ValueError("Invalid active knowledge release pointer.")
    return value


class KnowledgeSnapshot:
    def __init__(self, root: Path, pointer: dict):
        self.releases_root = root
        self.release_id = pointer["release_id"]
        self.root = safe_path(root, self.release_id)
        self._manifest_hash = pointer["manifest_sha256"]
        raw = (self.root / "manifest.json").read_bytes()
        if sha256(raw).hexdigest() != self._manifest_hash:
            raise ValueError("Knowledge manifest integrity check failed.")
        self._manifest = json.loads(raw)
        if self._manifest.get("format_version") != 1 or self._manifest.get("release_id") != self.release_id:
            raise ValueError("Unsupported or mismatched knowledge release.")
        self.verify()
        catalog = self.root / "catalog"
        self.service = KnowledgeService(FileKnowledgeRepository(
            categories_file=catalog / "categories.json", operations_file=catalog / "operations.json",
            parameters_file=catalog / "parameters.json"))

    @property
    def manifest(self):
        return deepcopy(self._manifest)

    def verify(self):
        if sha256((self.root / "manifest.json").read_bytes()).hexdigest() != self._manifest_hash:
            raise ValueError("Knowledge manifest changed after publication.")
        for name, expected in self._manifest["artifacts"].items():
            if sha256(safe_path(self.root, name).read_bytes()).hexdigest() != expected:
                raise ValueError(f"Published artifact changed: {name}")

    def read_json(self, relative):
        return json.loads(safe_path(self.root, relative).read_text(encoding="utf-8"))

    def schema(self, operation_id, vendor=None):
        if vendor is not None:
            profile = next((row for row in self._manifest["template_bindings"] if row["operation_id"] == operation_id and row["vendor"] == vendor), None)
            if profile and "schema_artifact" in profile:
                return self.read_json(profile["schema_artifact"])
        return self.read_json(self._manifest["schemas"][operation_id])

    def assert_active(self):
        pointer = active_pointer(self.releases_root)
        if not pointer or pointer != {"release_id": self.release_id, "manifest_sha256": self._manifest_hash}:
            raise ValueError("Knowledge release changed; revalidate against the active release.")

    def binding(self, device, operation_id):
        self.verify()
        self.assert_active()
        operation = self.service.get_operation(operation_id)
        knowledge = operation.vendor_knowledge.get(device["vendor"])
        if knowledge and knowledge.status == "blocked_unverified":
            raise ValueError(f"No declared template compatibility for {operation_id} / {device['vendor']}. "
                             f"Intent recognized; configuration generation blocked: {knowledge.reason} "
                             f"Required review: {' '.join(knowledge.requirements)}")
        for binding in self._manifest["template_bindings"]:
            if (binding["operation_id"] == operation_id and binding["vendor"] == device["vendor"]
                    and binding["platform"] == device["platform"] and str(device["version"]) in binding["versions"]):
                return deepcopy(binding)
        raise ValueError(f"No declared template compatibility for {operation_id} / {device['vendor']} {device['platform']} {device['version']}.")


def active_snapshot(root: Path | None = None):
    root = root or CATALOG_RELEASES_DIR
    pointer = active_pointer(root)
    if pointer is None and root.name == "catalog_releases":
        from .authority import authority
        if authority(root.parent.parent) == "sqlite":
            raise ValueError("SQLite authoring requires an active published release. Restore or publish it; source-mode fallback is forbidden.")
    return KnowledgeSnapshot(root, pointer) if pointer else None


def current_snapshot():
    from ..config import runtime_mode
    current = _current.get()
    return (active_snapshot() if runtime_mode() == "published" else None) if current is _UNBOUND else current


@contextmanager
def snapshot_scope(snapshot=_UNBOUND):
    """Explicit None is also useful to inspect the authoritative authoring files."""
    if snapshot is _UNBOUND and _current.get() is not _UNBOUND:
        yield _current.get()
        return
    snapshot = current_snapshot() if snapshot is _UNBOUND else snapshot
    token = _current.set(snapshot)
    try:
        yield snapshot
    finally:
        _current.reset(token)


def snapshot_request(function):
    @wraps(function)
    def scoped(*args, **kwargs):
        with snapshot_scope():
            return function(*args, **kwargs)
    return scoped
