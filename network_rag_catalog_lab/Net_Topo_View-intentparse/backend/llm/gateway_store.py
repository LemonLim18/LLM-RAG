"""Shared conversation repository over the existing Studio SQLite authority."""
import json
import threading
from uuid import uuid4

from fastapi import HTTPException

_migration_lock = threading.RLock()
VERSION = 'shared-ai-4-b2'


def create_agent_tables(c):
    c.execute('''CREATE TABLE IF NOT EXISTS ai_agent_investigations (
        id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL, owner TEXT NOT NULL,
        assistant TEXT NOT NULL, schema_version INTEGER NOT NULL,
        request_id TEXT NOT NULL, status TEXT NOT NULL,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(conversation_id,owner,assistant))''')
    c.execute('''CREATE TABLE IF NOT EXISTS ai_agent_checkpoints (
        thread_id TEXT NOT NULL, namespace TEXT NOT NULL, checkpoint_id TEXT NOT NULL,
        body TEXT NOT NULL, metadata TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(thread_id,namespace,checkpoint_id))''')


def finish_investigation(c,identity,request_id,status):
    c.execute("UPDATE ai_agent_investigations SET status=?,updated_at=CURRENT_TIMESTAMP WHERE conversation_id=? AND request_id=? AND status NOT IN ('cancelled','interrupted')",(status,identity,request_id))



def ensure_schema(db):
    from db.local_migrations import backup_database
    with _migration_lock:
        with db._connect() as c:
            if c.execute('SELECT 1 FROM schema_migrations WHERE version=?', (VERSION,)).fetchone():
                return
        backup_database(db._db_path, VERSION)
        with db._connect() as c:
            c.execute('BEGIN IMMEDIATE')
            columns = {r[1] for r in c.execute('PRAGMA table_info(ansible_chat_sessions)')}
            if 'assistant_kind' not in columns:
                c.execute("ALTER TABLE ansible_chat_sessions ADD COLUMN assistant_kind TEXT NOT NULL DEFAULT 'studio'")
            c.execute('''CREATE TABLE IF NOT EXISTS ai_turns (
                conversation_id TEXT NOT NULL, request_id TEXT NOT NULL, request_hash TEXT NOT NULL,
                prompt TEXT NOT NULL, result TEXT, state TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(conversation_id,request_id))''')
            c.execute("CREATE UNIQUE INDEX IF NOT EXISTS ai_one_pending_turn ON ai_turns(conversation_id) WHERE state='running'")
            c.execute('''CREATE TABLE IF NOT EXISTS ai_attachments (
                id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL, owner TEXT NOT NULL,
                name TEXT NOT NULL, digest TEXT NOT NULL, byte_size INTEGER NOT NULL,
                segments TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)''')
            attachment_columns={r[1] for r in c.execute('PRAGMA table_info(ai_attachments)')}
            if 'original_bytes' not in attachment_columns:
                c.execute('ALTER TABLE ai_attachments ADD COLUMN original_bytes BLOB')
            c.execute('''CREATE TABLE IF NOT EXISTS ai_evidence (
                id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL, request_id TEXT NOT NULL,
                body TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)''')
            c.execute('''CREATE TABLE IF NOT EXISTS ai_handoffs (id TEXT PRIMARY KEY, owner TEXT NOT NULL, source_conversation TEXT NOT NULL, body TEXT NOT NULL, studio_conversation TEXT)''')
            create_agent_tables(c)
            # Inventory metadata augments the existing records; no parallel inventory.
            columns = {r[1] for r in c.execute('PRAGMA table_info(devices)')}
            for name, default in [('site', ''), ('location', ''), ('aliases_json', '[]')]:
                if name not in columns:
                    c.execute(f"ALTER TABLE devices ADD COLUMN {name} TEXT NOT NULL DEFAULT '{default}'")
            if 'engineering_facts_json' not in columns:
                c.execute("ALTER TABLE devices ADD COLUMN engineering_facts_json TEXT NOT NULL DEFAULT '{}'")
            c.execute('INSERT INTO schema_migrations(version) VALUES (?)', (VERSION,))


class ConversationStore:
    def __init__(self, db):
        self.db = db

    def get(self, identity, owner, kind=None, connection=None):
        if connection is None:
            with self.db._connect() as c:
                return self.get(identity, owner, kind, c)
        row = connection.execute('SELECT * FROM ansible_chat_sessions WHERE id=? AND owner_username=?', (identity, owner)).fetchone()
        if row is None or (kind and row['assistant_kind'] != kind):
            raise HTTPException(404, 'Conversation not found for this account and assistant')
        result = dict(row)
        result['messages'] = json.loads(result.pop('messages_json'))
        result['updatedAt'] = result['updated_at']
        return result

    def create(self, owner, kind, identity=None):
        if kind not in {'floating', 'studio'}:
            raise HTTPException(422, 'Unknown assistant')
        identity = identity or uuid4().hex
        with self.db._connect() as c:
            c.execute('BEGIN IMMEDIATE')
            if c.execute('SELECT 1 FROM ansible_chat_sessions WHERE id=?', (identity,)).fetchone():
                return self.get(identity, owner, kind, c)
            c.execute('INSERT INTO ansible_chat_sessions(id,owner_username,title,messages_json,assistant_kind) VALUES (?,?,?,?,?)',
                      (identity, owner, 'New Chat', '[]', kind))
        return self.get(identity, owner, kind)

    def list(self, owner, kind):
        with self.db._connect() as c:
            ids = [r[0] for r in c.execute('SELECT id FROM ansible_chat_sessions WHERE owner_username=? AND assistant_kind=? ORDER BY updated_at DESC', (owner, kind))]
        return [self.get(i, owner, kind) for i in ids]

    def delete(self, identity, owner, kind=None):
        with self.db._connect() as c:
            c.execute('BEGIN IMMEDIATE')
            self.get(identity, owner, kind, c)
            c.execute('DELETE FROM ai_agent_checkpoints WHERE thread_id IN (SELECT id FROM ai_agent_investigations WHERE conversation_id=?)',(identity,))
            c.execute('DELETE FROM ai_agent_investigations WHERE conversation_id=?',(identity,))
            c.execute('DELETE FROM ai_handoffs WHERE source_conversation=? OR studio_conversation=?',(identity,identity))
            for table in ('ai_turns', 'ai_evidence', 'ai_attachments'):
                c.execute(f'DELETE FROM {table} WHERE conversation_id=?', (identity,))
            c.execute('DELETE FROM ansible_chat_sessions WHERE id=?', (identity,))

    def begin(self, identity, owner, request_id, request_hash, prompt):
        import sqlite3
        with self.db._connect() as c:
            c.execute('BEGIN IMMEDIATE')
            self.get(identity, owner, connection=c)
            c.execute("UPDATE ai_turns SET state='cancelled' WHERE conversation_id=? AND state='running' AND created_at < datetime('now','-5 minutes')", (identity,))
            prior = c.execute('SELECT * FROM ai_turns WHERE conversation_id=? AND request_id=?', (identity, request_id)).fetchone()
            if prior:
                if prior['request_hash'] != request_hash:
                    raise HTTPException(409, 'Request identity was already used with different content')
                if prior['state'] == 'completed':
                    return json.loads(prior['result'])
                raise HTTPException(409, 'This turn is running or cancelled; use a new request identity')
            try:
                c.execute("INSERT INTO ai_turns(conversation_id,request_id,request_hash,prompt,state) VALUES (?,?,?,?,'running')", (identity, request_id, request_hash, prompt))
            except sqlite3.IntegrityError as exc:
                raise HTTPException(409, 'A turn is already running in this conversation') from exc
        return None

    def finish(self, identity, owner, request_id, response):
        from datetime import datetime, timezone
        stamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        with self.db._connect() as c:
            c.execute('BEGIN IMMEDIATE')
            session = self.get(identity, owner, connection=c)
            changed = c.execute("UPDATE ai_turns SET result=?,state='completed' WHERE conversation_id=? AND request_id=? AND state='running'", (json.dumps(response), identity, request_id))
            if not changed.rowcount:
                raise HTTPException(409, 'Turn was cancelled; late results were discarded')
            finish_investigation(c,identity,request_id,'completed')
            prompt = c.execute('SELECT prompt FROM ai_turns WHERE conversation_id=? AND request_id=?', (identity, request_id)).fetchone()[0]
            messages = session['messages'] + [dict(id=request_id+'-user', role='user', content=prompt, timestamp=stamp),
                dict(id=request_id, role='assistant', content=response['answer'], timestamp=stamp, evidence=response.get('evidence', []), evidence_details=response.get('context_coverage',{}).get('agent',{}).get('record_details','')[:24000])]
            c.execute("UPDATE ansible_chat_sessions SET messages_json=?,title=CASE WHEN title='New Chat' THEN ? ELSE title END,updated_at=datetime('now') WHERE id=?", (json.dumps(messages[-1000:]), prompt[:80], identity))
            for evidence in response.get('evidence', []):
                c.execute('INSERT INTO ai_evidence(id,conversation_id,request_id,body) VALUES (?,?,?,?)', (evidence['id'], identity, request_id, json.dumps(evidence)))

    def cancel(self, identity, owner, request_id):
        self.get(identity, owner)
        with self.db._connect() as c:
            c.execute("UPDATE ai_turns SET state='cancelled' WHERE conversation_id=? AND request_id=? AND state='running'", (identity, request_id))
            finish_investigation(c,identity,request_id,'cancelled')

    def history(self, identity, user=None):
        with self.db._connect() as c:
            rows = c.execute("SELECT prompt,result FROM ai_turns WHERE conversation_id=? AND state='completed' ORDER BY rowid DESC LIMIT 10", (identity,)).fetchall()
        from llm.gateway_handoff import history_context
        messages = history_context(self.db,identity,user)
        for row in reversed(rows):
            messages.extend([dict(role='user', content=row['prompt'][:2000]), dict(role='assistant', content=json.loads(row['result'])['answer'][:4000])])
        while sum(len(message['content']) for message in messages)>12000:
            messages=messages[2:]
        return messages

    def last_result(self, identity, owner):
        with self.db._connect() as c:
            self.get(identity,owner,connection=c)
            row=c.execute("SELECT result FROM ai_turns WHERE conversation_id=? AND state='completed' ORDER BY rowid DESC LIMIT 1",(identity,)).fetchone()
        return json.loads(row['result']) if row else None

    def result_for(self,identity,owner,request_id):
        with self.db._connect() as c:
            self.get(identity,owner,connection=c)
            row=c.execute("SELECT result FROM ai_turns WHERE conversation_id=? AND request_id=? AND state='completed'",(identity,request_id)).fetchone()
        return json.loads(row[0]) if row else None
