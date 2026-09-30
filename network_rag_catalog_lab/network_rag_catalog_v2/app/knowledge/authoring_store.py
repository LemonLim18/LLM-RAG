"""Revision-checked JSON authoring with a recoverable multi-file journal.

Published readers never read these in-progress files. Cooperating source readers
and publishers fail closed while the exclusive authoring lock/journal exists.
"""

from contextlib import contextmanager
from datetime import UTC, datetime
import json
import os
from pathlib import Path
from uuid import uuid4

CATALOG_NAMES = ("categories", "parameters", "operations", "category_parameters",
                 "operation_parameters", "operation_rules", "template_bindings", "context_rules")


class AuthoringError(ValueError):
    def __init__(self, code, message, path=""):
        super().__init__(message)
        self.code, self.path = code, path


def ensure_readable(catalog_dir):
    if (catalog_dir / ".authoring.lock").exists() or (catalog_dir / ".authoring-pending.json").exists():
        raise AuthoringError("AUTHORING_BUSY", "Authoring transaction is in progress or requires recovery.")


@contextmanager
def authoring_lock(base):
    directory = Path(base) / "data/catalog"
    path = directory / ".authoring.lock"
    try:
        handle = path.open("x", encoding="utf-8")
    except FileExistsError as exc:
        raise AuthoringError("AUTHORING_BUSY", "Authoring is locked. Verify no writer is running before removing a stale lock.") from exc
    try:
        with handle:
            handle.write(str(os.getpid()))
            handle.flush()
            yield
    finally:
        path.unlink()


def _atomic_text(path, text):
    temporary = path.with_name("." + path.name + "." + uuid4().hex + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _atomic_json(path, value):
    _atomic_text(path, json.dumps(value, indent=2) + "\n")


class JsonAuthoringStore:
    def __init__(self, base_dir):
        self.base = Path(base_dir)
        self.catalog_dir = self.base / "data/catalog"
        self.history_dir = self.base / "storage/catalog_authoring"
        self.pending_path = self.catalog_dir / ".authoring-pending.json"

    def _read(self):
        from .publication import _source_digest, _sources
        sources = _sources(self.base)
        catalogs = {name: json.loads(sources[f"data/catalog/{name}.json"]) for name in CATALOG_NAMES}
        return {"revision": _source_digest(sources), "catalogs": catalogs, "sources": sources}

    def snapshot(self):
        with authoring_lock(self.base):
            self._assert_authority()
            self._check_pending()
            return self._read()

    def _assert_authority(self):
        from .authority import authority
        if authority(self.base) != "json":
            raise AuthoringError("WRONG_AUTHORITY", "JSON is now import/export data; use the SQLite authoring service.")

    def _check_pending(self):
        if self.pending_path.exists():
            raise AuthoringError("RECOVERY_REQUIRED", "Recover the unfinished authoring transaction before continuing.")

    def commit(self, catalogs, *, expected_revision, actor, reason, precommit=None):
        if set(catalogs) != set(CATALOG_NAMES):
            raise AuthoringError("INVALID_CATALOGS", "Provide exactly the supported catalog documents.")
        with authoring_lock(self.base):
            self._assert_authority()
            self._check_pending()
            before = self._read()
            if before["revision"] != expected_revision:
                raise AuthoringError("STALE_REVISION", "Authoring files changed; reload and review your edits.")
            if precommit is not None:
                precommit()
            changes = {}
            for name in CATALOG_NAMES:
                if before["catalogs"][name] != catalogs[name]:
                    changes[name] = {"before": before["sources"][f"data/catalog/{name}.json"].decode("utf-8"),
                                     "after": json.dumps(catalogs[name], indent=2) + "\n"}
            if not changes:
                return {"revision": expected_revision, "audit_id": None}
            self.history_dir.mkdir(parents=True, exist_ok=True)
            transaction_id = uuid4().hex
            journal = {"format_version": 1, "id": transaction_id, "state": "prepared", "actor": actor,
                       "reason": reason, "created_at": datetime.now(UTC).isoformat(),
                       "before_revision": expected_revision, "changes": changes}
            journal_path = self.history_dir / (transaction_id + ".json")
            _atomic_json(journal_path, journal)
            _atomic_json(self.pending_path, {"id": transaction_id})
            try:
                for name, content in changes.items():
                    _atomic_text(self.catalog_dir / (name + ".json"), content["after"])
                revision = self._read()["revision"]
                journal.update(state="committed", after_revision=revision)
                _atomic_json(journal_path, journal)
            except Exception:
                # Roll back only bytes owned by this transaction; never overwrite an outside edit.
                self._restore(journal)
                journal["state"] = "rolled_back"
                _atomic_json(journal_path, journal)
                self.pending_path.unlink()
                raise
            self.pending_path.unlink()
            return {"revision": revision, "audit_id": transaction_id}

    def _restore(self, journal):
        for name, content in journal["changes"].items():
            if name not in CATALOG_NAMES:
                raise AuthoringError("INVALID_JOURNAL", "Journal contains an unknown catalog.")
            current = (self.catalog_dir / (name + ".json")).read_bytes().decode("utf-8")
            if current not in (content["before"], content["after"]):
                raise AuthoringError("RECOVERY_CONFLICT", f"Outside edit detected in {name}; manual reconciliation required.")
        for name, content in journal["changes"].items():
            _atomic_text(self.catalog_dir / (name + ".json"), content["before"])

    def recover(self):
        with authoring_lock(self.base):
            self._assert_authority()
            if not self.pending_path.exists():
                return {"recovered": False, "revision": self._read()["revision"]}
            import re
            identity = json.loads(self.pending_path.read_text(encoding="utf-8"))["id"]
            if not re.fullmatch(r"[a-f0-9]{32}", identity):
                raise AuthoringError("INVALID_JOURNAL", "Invalid transaction identity.")
            path = self.history_dir / (identity + ".json")
            journal = json.loads(path.read_text(encoding="utf-8"))
            if journal["state"] != "committed":
                self._restore(journal)
                journal["state"] = "rolled_back"
                _atomic_json(path, journal)
            elif self._read()["revision"] != journal["after_revision"]:
                raise AuthoringError("RECOVERY_CONFLICT", "Committed catalog changed before recovery; reconcile manually.")
            self.pending_path.unlink()
            return {"recovered": True, "audit_id": identity, "revision": self._read()["revision"]}
