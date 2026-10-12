-- Local source revisions and workspace metadata are missing from the legacy schema.
-- Latest revision is authoritative; earlier versions make edits/deletions recoverable.
CREATE TABLE IF NOT EXISTS authoring_revisions (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 namespace TEXT NOT NULL CHECK(namespace IN ('templates','schemas','ansible')),
 path TEXT NOT NULL,
 revision INTEGER NOT NULL,
 content TEXT,
 kind TEXT NOT NULL DEFAULT 'file' CHECK(kind IN ('file','dir')),
 deleted INTEGER NOT NULL DEFAULT 0 CHECK(deleted IN (0,1)),
 actor TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT (datetime('now')),
 UNIQUE(namespace,path,revision)
);
CREATE INDEX IF NOT EXISTS idx_authoring_latest ON authoring_revisions(namespace,path,revision DESC);

