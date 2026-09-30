"""One explicit authoring authority; runtime always prefers published releases."""

from pathlib import Path
import json

from .authoring_store import AuthoringError


def authority_path(base):
    return Path(base) / "storage/knowledge/authority.json"


def authority(base):
    path = authority_path(base)
    if not path.exists():
        if (path.parent / "catalog.sqlite3").exists():
            raise AuthoringError("MISSING_AUTHORITY", "Database exists without its authority marker. Recover migration or restore the marker; JSON fallback is forbidden.")
        return "json"
    record = json.loads(path.read_text(encoding="utf-8"))
    if record != {"format_version": 1, "backend": "sqlite", "database": "catalog.sqlite3"}:
        raise AuthoringError("INVALID_AUTHORITY", "Unknown authoring authority; do not fall back to JSON.")
    return "sqlite"


def authoring_store(base):
    if authority(base) == "sqlite":
        from .sqlite_repository import SQLiteAuthoringStore
        return SQLiteAuthoringStore(base)
    from .authoring_store import JsonAuthoringStore
    return JsonAuthoringStore(base)


def authoring_snapshot_unlocked(base):
    """Caller holds authoring_lock; also used for a final publication freshness check."""
    store = authoring_store(base)
    if authority(base) == "sqlite":
        return store._snapshot_unlocked()
    store._check_pending()
    return store._read()
