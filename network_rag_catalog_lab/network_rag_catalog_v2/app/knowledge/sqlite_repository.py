"""Transactional local authoring, with lossless JSON export and typed read parity."""

from contextlib import contextmanager
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from uuid import uuid4

from .authoring_store import AuthoringError, CATALOG_NAMES, authoring_lock, _atomic_json
from .document_repository import DocumentKnowledgeRepository


def _json(value):
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))


class SQLiteAuthoringStore:
    def __init__(self, base_dir):
        self.base = Path(base_dir).resolve()
        self.path = self.base / "storage/knowledge/catalog.sqlite3"

    @contextmanager
    def _connection(self):
        if not self.path.is_file():
            raise AuthoringError("DATABASE_MISSING", "SQLite authority is selected but the database is missing. Restore it; JSON fallback is forbidden.")
        connection = sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True, timeout=5, isolation_level=None)
        try:
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA synchronous=FULL")
            if connection.execute("PRAGMA user_version").fetchone()[0] != 1:
                raise AuthoringError("DATABASE_VERSION", "Unsupported authoring database version.")
            yield connection
        except sqlite3.Error as exc:
            raise AuthoringError("DATABASE_ERROR", str(exc)) from exc
        finally:
            connection.close()

    @staticmethod
    def _catalogs(connection):
        result = {name: [json.loads(row[0]) for row in connection.execute(f"SELECT payload FROM {name} ORDER BY ordinal")]
                  for name in CATALOG_NAMES if name != "context_rules"}
        metadata = connection.execute("SELECT payload FROM context_metadata WHERE singleton=1").fetchone()
        result["context_rules"] = json.loads(metadata[0])
        result["context_rules"]["operations"] = {identity: json.loads(raw) for identity, raw in connection.execute(
            "SELECT operation_id, payload FROM context_policies ORDER BY ordinal")}
        return result

    def _snapshot(self, connection):
        from .publication import _sources, _source_digest
        catalogs = self._catalogs(connection)
        # Managed JSON files are now export/seed data, even if subsequently edited.
        sources = _sources(self.base, include_managed_catalogs=False)
        for name, document in catalogs.items():
            sources[f"data/catalog/{name}.json"] = (_json(document) + "\n").encode()
        generation = connection.execute("SELECT generation FROM authoring_state WHERE singleton=1").fetchone()[0]
        content_hash = _source_digest(sources)
        revision = sha256(f"sqlite:{generation}:{content_hash}".encode()).hexdigest()
        return {"revision": revision, "catalogs": catalogs, "sources": sources, "generation": generation}

    def _snapshot_unlocked(self):
        with self._connection() as connection:
            connection.execute("BEGIN")
            try:
                return self._snapshot(connection)
            finally:
                connection.rollback()

    def snapshot(self):
        with authoring_lock(self.base):
            self._assert_authority()
            return self._snapshot_unlocked()

    def _assert_authority(self):
        from .authority import authority
        if authority(self.base) != "sqlite":
            raise AuthoringError("WRONG_AUTHORITY", "SQLite has not been selected as authoring authority.")

    @staticmethod
    def _replace_catalogs(connection, catalogs):
        if set(catalogs) != set(CATALOG_NAMES):
            raise AuthoringError("INVALID_CATALOGS", "Provide the complete supported catalog document set.")
        for table in ("context_policies", "context_metadata", "template_bindings", "operation_rules", "operation_parameters",
                      "operation_versions", "operations", "category_parameters", "parameters", "categories"):
            connection.execute(f"DELETE FROM {table}")
        for name, key in (("categories", "category_id"), ("parameters", "parameter_id")):
            connection.executemany(f"INSERT INTO {name} VALUES (?, ?, ?)",
                [(row[key], index, _json(row)) for index, row in enumerate(catalogs[name])])
        connection.executemany("INSERT INTO category_parameters VALUES (?, ?, ?, ?)",
            [(row["category_id"], row["parameter_id"], index, _json(row)) for index, row in enumerate(catalogs["category_parameters"])])
        for index, row in enumerate(catalogs["operations"]):
            connection.execute("INSERT INTO operations VALUES (?, ?, ?, ?)", (row["operation_id"], row["category_id"], index, _json(row)))
            connection.execute("INSERT INTO operation_versions VALUES (?, ?, ?)", (row["operation_id"], row.get("version", 1), row["category_id"]))
        connection.executemany("INSERT INTO operation_parameters VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(row["operation_id"], row["operation_version"], row["category_id"], row["parameter_id"], row["field_path"], index, _json(row))
             for index, row in enumerate(catalogs["operation_parameters"])])
        connection.executemany("INSERT INTO operation_rules VALUES (?, ?, ?, ?, ?)",
            [(row["operation_id"], row["operation_version"], row["field_path"], index, _json(row)) for index, row in enumerate(catalogs["operation_rules"])])
        connection.executemany("INSERT INTO template_bindings VALUES (?, ?, ?, ?)",
            [(index, row["operation_id"], row["operation_version"], _json(row)) for index, row in enumerate(catalogs["template_bindings"])])
        context = catalogs["context_rules"]
        connection.execute("INSERT INTO context_metadata VALUES (1, ?)", (_json({key: value for key, value in context.items() if key != "operations"}),))
        connection.executemany("INSERT INTO context_policies VALUES (?, ?, ?)",
            [(identity, index, _json(row)) for index, (identity, row) in enumerate(context["operations"].items())])

    @staticmethod
    def _audit(connection, before, after, actor, reason):
        identity = uuid4().hex
        connection.execute("INSERT INTO authoring_audit VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (identity, after["generation"], actor, reason, datetime.now(UTC).isoformat(),
             before.get("revision"), after["revision"], _json(before.get("catalogs", {})), _json(after["catalogs"])))
        return identity

    def commit(self, catalogs, *, expected_revision, actor, reason, precommit=None):
        with authoring_lock(self.base), self._connection() as connection:
            self._assert_authority()
            connection.execute("BEGIN IMMEDIATE")
            try:
                before = self._snapshot(connection)
                if before["revision"] != expected_revision:
                    raise AuthoringError("STALE_REVISION", "Authoring changed; reload before saving.")
                if precommit:
                    precommit()
                if catalogs == before["catalogs"]:
                    connection.rollback()
                    return {"revision": expected_revision, "audit_id": None}
                self._replace_catalogs(connection, catalogs)
                connection.execute("UPDATE authoring_state SET generation=generation+1 WHERE singleton=1")
                after = self._snapshot(connection)
                audit_id = self._audit(connection, before, after, actor, reason)
                connection.commit()
                return {"revision": after["revision"], "audit_id": audit_id}
            except BaseException:
                connection.rollback()
                raise

    def recover(self):
        with authoring_lock(self.base), self._connection() as connection:
            self._assert_authority()
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok" or connection.execute("PRAGMA foreign_key_check").fetchall():
                raise AuthoringError("DATABASE_INTEGRITY", "Database needs operator restoration from a verified backup.")
            return {"recovered": False, "integrity": "ok", "revision": self._snapshot(connection)["revision"]}


class SQLiteKnowledgeRepository(DocumentKnowledgeRepository):
    """Repository-compatible typed snapshot reader; reload takes a fresh DB snapshot."""
    def __init__(self, base_dir):
        self.store = SQLiteAuthoringStore(base_dir)
        self.reload()

    def reload(self):
        self._documents = self.store.snapshot()["catalogs"]


def migrate_to_sqlite(base_dir, *, expected_revision, actor, reason, releases_dir=None):
    from .authority import authority, authority_path
    from .authoring_store import JsonAuthoringStore
    from .management import KnowledgeManagementService
    from .runtime import active_snapshot
    base = Path(base_dir).resolve()
    root = Path(releases_dir) if releases_dir else base / "storage/catalog_releases"
    with authoring_lock(base):
        if authority_path(base).exists() and authority(base) != "json":
            raise AuthoringError("ALREADY_MIGRATED", "SQLite is already authoritative; migration is not repeatable.")
        if active_snapshot(root) is None:
            raise AuthoringError("PUBLICATION_REQUIRED", "Publish a baseline release before the authority cutover.")
        source = JsonAuthoringStore(base)
        source._check_pending()
        snapshot = source._read()
        if snapshot["revision"] != expected_revision:
            raise AuthoringError("STALE_REVISION", "JSON authoring changed before migration.")
        KnowledgeManagementService._validate(snapshot["catalogs"], snapshot["sources"], complete=True)
        destination = base / "storage/knowledge"
        destination.mkdir(parents=True, exist_ok=True)
        store = SQLiteAuthoringStore(base)
        if store.path.exists():
            # Resume only a fully committed, unchanged first migration whose final
            # pointer write was interrupted. Never overwrite an unrelated database.
            with store._connection() as connection:
                migrated = store._snapshot(connection)
                audits = connection.execute("SELECT generation, before_revision FROM authoring_audit").fetchall()
                if (migrated["generation"] != 1 or audits != [(1, expected_revision)]
                        or migrated["catalogs"] != snapshot["catalogs"]
                        or connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok"
                        or connection.execute("PRAGMA foreign_key_check").fetchall()):
                    raise AuthoringError("DATABASE_EXISTS", "Existing database does not match this migration. Inspect it; it will not be overwritten.")
            _atomic_json(authority_path(base), {"format_version": 1, "backend": "sqlite", "database": "catalog.sqlite3"})
            return {"revision": migrated["revision"], "authority": "sqlite", "database": str(store.path), "resumed": True}
        _atomic_json(destination / ("json-backup-" + uuid4().hex + ".json"), {
            "format_version": 1, "revision": snapshot["revision"], "catalogs": snapshot["catalogs"],
            "actor": actor, "reason": reason})
        connection = sqlite3.connect(store.path, isolation_level=None)
        try:
            connection.execute("PRAGMA foreign_keys=ON")
            sql = (Path(__file__).parent / "migrations/001_authoring.sql").read_text(encoding="utf-8")
            connection.executescript("BEGIN IMMEDIATE;\n" + sql)
            connection.execute("INSERT INTO schema_migrations VALUES (1, ?)", (datetime.now(UTC).isoformat(),))
            connection.execute("PRAGMA user_version=1")
            store._replace_catalogs(connection, snapshot["catalogs"])
            connection.execute("INSERT INTO authoring_state VALUES (1, 1)")
            migrated = store._snapshot(connection)
            if migrated["catalogs"] != snapshot["catalogs"]:
                raise ValueError("Migration changed catalog data.")
            store._audit(connection, snapshot, migrated, actor, reason)
            if source._read()["revision"] != expected_revision:
                raise AuthoringError("STALE_REVISION", "JSON sources changed during migration.")
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()
        # Only this final atomic pointer makes SQLite authoritative. JSON is not deleted.
        _atomic_json(authority_path(base), {"format_version": 1, "backend": "sqlite", "database": "catalog.sqlite3"})
        return {"revision": migrated["revision"], "authority": "sqlite", "database": str(store.path)}
