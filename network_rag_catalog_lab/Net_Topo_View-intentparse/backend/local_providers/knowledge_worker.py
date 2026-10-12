"""CogniShield hosting adapter for V9 authoring; V9 source remains read-only."""
import json
import re
from pathlib import Path
import sqlite3
import sys
from copy import deepcopy
from hashlib import sha256
from datetime import datetime, timezone

sys.dont_write_bytecode = True
from v9_worker import protect_source


def main(payload):
    root, base = Path(payload['root']).resolve(), Path(payload['base']).resolve()
    if base.is_relative_to(root):
        raise ValueError('Knowledge workspace cannot be inside the preserved V9 repository.')
    protect_source(root)
    from app.knowledge.management import KnowledgeManagementService
    from app.knowledge.runtime import active_snapshot, active_pointer
    from app.knowledge.sqlite_repository import SQLiteAuthoringStore
    from app.knowledge.publication import _source_digest, publish
    from app.knowledge.authoring_store import authoring_lock, AuthoringError
    from app.knowledge.authority import authoring_store
    releases = base / 'storage/catalog_releases'
    action = payload['action']
    body = payload.get('body', {})
    actor = payload['actor']
    reason = body.get('reason', '').strip()
    if action not in {'inspect', 'schema', 'validate'} and not reason:
        raise ValueError('A change reason is required.')

    if action == 'initialize':
        # Seed only a new workspace from the verified active release, never from
        # unpublished sibling drafts. No inventory, sessions or credentials copied.
        if base.exists():
            raise ValueError('Knowledge workspace already exists; it will not be overwritten.')
        snapshot = active_snapshot(root / 'storage/catalog_releases')
        if snapshot is None:
            raise ValueError('A verified V9 baseline release is required.')
        base.mkdir(parents=True)
        for source in (snapshot.root / 'catalog').glob('*.json'):
            target = base / 'data/catalog' / source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
        for op in snapshot.service.list_operations(True):
            if op.schema_path:
                target = (base / op.schema_path).resolve()
                if not target.is_relative_to(base / 'data/operations'):
                    raise ValueError('Unsafe baseline schema path.')
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(snapshot.schema(op.operation_id)), encoding='utf-8')
        for binding in snapshot.manifest['template_bindings']:
            target = (base / binding['template_path']).resolve()
            if not target.is_relative_to(base / 'data/templates'):
                raise ValueError('Unsafe baseline template path.')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((snapshot.root / binding['artifact_path']).read_bytes())
        publish(base_dir=base, releases_dir=releases, mode='offline', actor=actor, reason=reason)
        service = KnowledgeManagementService(base)
        revision = service.store.snapshot()['revision']
        result = service.migrate_sqlite({'expected_revision': revision, 'actor': actor, 'reason': reason})
        if not result.ok:
            return result.model_dump()
    elif not base.exists():
        return {'ok': True, 'data': {'initialized': False}}

    # Extend V9's existing authoritative store only for genuinely missing template
    # text revisions. Catalog/compiler/publisher remain V9's implementations.
    database = base / 'storage/knowledge/catalog.sqlite3'
    with sqlite3.connect(database) as connection:
        exists = connection.execute("SELECT 1 FROM sqlite_master WHERE name='cognishield_template_revisions'").fetchone()
    if not exists:
        with authoring_lock(base):
            backup = database.with_name('catalog.before-template-revisions.sqlite3')
            if not backup.exists():
                with sqlite3.connect(database) as source, sqlite3.connect(backup) as target:
                    source.backup(target)
            with sqlite3.connect(database) as connection:
                connection.execute('CREATE TABLE IF NOT EXISTS cognishield_template_revisions (id INTEGER PRIMARY KEY, path TEXT NOT NULL, content TEXT NOT NULL, actor TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL)')

    original_snapshot = SQLiteAuthoringStore._snapshot
    def with_templates(self, connection):
        result = original_snapshot(self, connection)
        rows = connection.execute('SELECT path,content FROM cognishield_template_revisions WHERE id IN (SELECT MAX(id) FROM cognishield_template_revisions GROUP BY path)')
        for path, content in rows:
            result['sources'][path] = content.encode('utf-8')
        result['revision'] = sha256(f"sqlite:{result['generation']}:{_source_digest(result['sources'])}".encode()).hexdigest()
        return result
    SQLiteAuthoringStore._snapshot = with_templates
    service = KnowledgeManagementService(base)

    if action in {'initialize', 'inspect'}:
        snapshot = service.store.snapshot()
        with sqlite3.connect(database) as connection:
            history = [dict(zip(('actor','reason','created_at'), row)) for row in connection.execute('SELECT actor,reason,created_at FROM authoring_audit ORDER BY generation DESC LIMIT 15')]
        paths = {row['template_path'] for row in snapshot['catalogs']['template_bindings']}
        return {'ok': True, 'revision': snapshot['revision'], 'data': {'initialized': True,
            'catalogs': snapshot['catalogs'], 'templates': {p: snapshot['sources'][p].decode('utf-8') for p in paths},
            'active_release': active_pointer(releases), 'history': history, 'authority': 'sqlite',
            'publication_mode': 'offline', 'output_format': 'native_cli'}}
    if action == 'schema':
        return service.preview_schema(body['operation_id']).model_dump()
    if action == 'validate':
        return service.validate().model_dump()
    if action == 'edit':
        return service.apply({**body, 'actor': actor}).model_dump()
    if action == 'publish':
        return service.publish({**body, 'actor': actor, 'mode': 'offline'}).model_dump()
    if action == 'template':
        store = service.store
        with authoring_lock(base), store._connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            try:
                before = store._snapshot(connection)
                if before['revision'] != body['expected_revision']:
                    raise AuthoringError('STALE_REVISION', 'Knowledge changed; reload before saving.')
                path, content = body['path'], body['content']
                candidate = deepcopy(before['catalogs'])
                bound = [r for r in before['catalogs']['template_bindings'] if r['template_path'] == path]
                if body.get('operation_id'):
                    from app.knowledge.schema_compiler import compile_schema
                    from app.knowledge.services import KnowledgeService
                    from app.knowledge.document_repository import DocumentKnowledgeRepository
                    identity, vendor, platform = (body.get(k, '') for k in ('operation_id','vendor','platform'))
                    if not all(isinstance(v,str) and re.fullmatch(r'[a-z][a-z0-9_]*',v) for v in (identity,vendor,platform)):
                        raise ValueError('Operation, vendor and platform must be stable lowercase identifiers.')
                    operation = next((o for o in candidate['operations'] if o['operation_id']==identity), None)
                    if operation is None:
                        raise ValueError('Select an existing operation.')
                    schema = compile_schema(KnowledgeService(DocumentKnowledgeRepository(candidate)), identity)
                    # Server-generated path; the client cannot select a filesystem location.
                    from uuid import uuid4
                    path = f'data/templates/{vendor}/{operation["category_id"]}/{identity}/{platform}/{uuid4().hex}.j2'
                    required = set(schema.get('required',[])) | set(schema.get('x-required-by-vendor',{}).get(vendor,[]))
                    binding = {'operation_id':identity,'operation_version':operation['version'],'vendor':vendor,
                        'platform':platform,'versions':body.get('versions') or [],'template_path':path,
                        'input_contract':{'fields':list(schema['properties']),
                            'optional_defaults':{k:None for k in schema['properties'] if k not in required},'derived':{}}}
                    candidate['template_bindings'].append(binding)
                    bound = [binding]
                if not bound or len(content.encode('utf-8')) > 200000:
                    raise ValueError('Select a bound template or provide a new variant; maximum size is 200 KB.')
                affected = {r['operation_id'] for r in bound}
                for op in candidate['operations']:
                    if op['operation_id'] in affected:
                        op['version'] = op.get('version', 1) + 1
                        for table in ('operation_parameters', 'operation_rules', 'template_bindings'):
                            for row in candidate[table]:
                                if row['operation_id'] == op['operation_id']:
                                    row['operation_version'] = op['version']
                sources = {**before['sources'], path: content.encode('utf-8')}
                service._validate(candidate, sources, complete=True)
                service._require_published_runtime()
                store._replace_catalogs(connection, candidate)
                connection.execute('INSERT INTO cognishield_template_revisions(path,content,actor,reason,created_at) VALUES (?,?,?,?,?)', (path,content,actor,reason,datetime.now(timezone.utc).isoformat()))
                connection.execute('UPDATE authoring_state SET generation=generation+1 WHERE singleton=1')
                after = store._snapshot(connection)
                audit = store._audit(connection, before, after, actor, reason)
                connection.commit()
                return {'ok': True, 'revision': after['revision'], 'data': {'audit_id': audit, 'affected_operations': sorted(affected)}}
            except BaseException:
                connection.rollback()
                raise
    raise ValueError('Unsupported authoring action.')


if __name__ == '__main__':
    try:
        print(json.dumps(main(json.load(sys.stdin))))
    except Exception as exc:
        print(json.dumps({'ok': False, 'issues': [{'code': getattr(exc, 'code', 'VALIDATION_ERROR'), 'message': str(exc)}]}))
