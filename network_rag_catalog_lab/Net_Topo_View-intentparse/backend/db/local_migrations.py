"""M0 additive schema upgrade; originals are backed up using SQLite's backup API."""
import sqlite3
import threading
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

_lock = threading.RLock()
VERSION = 'm0-local-1'
WORKFLOW_VERSION = 'm0.2-m0.3-local-workflows-1'

def backup_database(path, version=VERSION):
    path = Path(path)
    if not path.exists() or not path.stat().st_size:
        return None
    folder = path.parent / 'backups'
    folder.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    dest = folder / f'{path.stem}-before-{version}-{stamp}.db'
    with closing(sqlite3.connect(f'file:{path.as_posix()}?mode=ro', uri=True)) as source:
        with closing(sqlite3.connect(dest)) as target:
            source.backup(target)
    return dest

def ensure_local_schema(path):
    """One transaction, no row rewrites/drops; existing optional columns survive."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        conn = sqlite3.connect(path, timeout=20)
        try:
            has_versions = conn.execute("SELECT 1 FROM sqlite_master WHERE name='schema_migrations'").fetchone()
            if has_versions and conn.execute('SELECT 1 FROM schema_migrations WHERE version=?', (VERSION,)).fetchone():
                if not conn.execute("SELECT 1 FROM schema_migrations WHERE version='m0.1-authoring-1'").fetchone():
                    backup_database(path, 'm0.1-authoring-1')
                    conn.executescript('BEGIN IMMEDIATE;\n' + (Path(__file__).parent / 'migrations/m0_1_authoring.sql').read_text(encoding='utf-8'))
                    conn.execute("INSERT INTO schema_migrations(version) VALUES ('m0.1-authoring-1')")
                    conn.commit()
                if not conn.execute('SELECT 1 FROM schema_migrations WHERE version=?', (WORKFLOW_VERSION,)).fetchone():
                    backup_database(path, WORKFLOW_VERSION)
                    conn.executescript('BEGIN IMMEDIATE;\n' + (Path(__file__).parent / 'migrations/m0_2_m0_3_local_workflows.sql').read_text(encoding='utf-8'))
                    conn.execute('INSERT INTO schema_migrations(version) VALUES (?)', (WORKFLOW_VERSION,))
                    conn.commit()
                return
            backup_database(path)
            schema = (Path(__file__).parent / 'schema.sql').read_text(encoding='utf-8')
            # Build the desired schema in memory solely to inspect additive columns.
            desired = sqlite3.connect(':memory:')
            try:
                desired.executescript(schema)
                additions = []
                for (table,) in desired.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
                    existing = {r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')}
                    if not existing:
                        continue
                    for _, name, kind, required, default, pk in desired.execute(f'PRAGMA table_info("{table}")'):
                        if name not in existing:
                            if pk or (required and default is None):
                                raise RuntimeError(f'Manual migration required for {table}.{name}; original preserved')
                            suffix = f' DEFAULT {default}' if default is not None else ''
                            additions.append(f'ALTER TABLE "{table}" ADD COLUMN "{name}" {kind}{suffix};')
            finally:
                desired.close()
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('PRAGMA foreign_keys=ON')
            schema = '\n'.join(line for line in schema.splitlines() if not line.startswith('PRAGMA '))
            migration = (Path(__file__).parent / 'migrations' / 'm0_local.sql').read_text(encoding='utf-8')
            authoring = (Path(__file__).parent / 'migrations/m0_1_authoring.sql').read_text(encoding='utf-8')
            workflows = (Path(__file__).parent / 'migrations/m0_2_m0_3_local_workflows.sql').read_text(encoding='utf-8')
            conn.executescript('BEGIN IMMEDIATE;\n' + '\n'.join(additions) + '\n' + schema + '\n' + migration + '\n' + authoring + '\n' + workflows)
            conn.execute("INSERT INTO schema_migrations(version) VALUES ('m0.1-authoring-1')")
            conn.execute('INSERT INTO schema_migrations(version) VALUES (?)', (WORKFLOW_VERSION,))
            conn.execute('INSERT INTO schema_migrations(version) VALUES (?)', (VERSION,))
            violations = conn.execute('PRAGMA foreign_key_check').fetchall()
            if violations:
                raise RuntimeError(f'Existing database has {len(violations)} foreign-key violations; migration rolled back')
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
