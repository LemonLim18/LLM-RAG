-- Persistent local simulation state. Inventory and snapshots remain in the existing tables.
CREATE TABLE IF NOT EXISTS simulated_device_configs (
  device_id INTEGER PRIMARY KEY REFERENCES devices(id) ON DELETE CASCADE,
  config_text TEXT NOT NULL,
  source_snapshot_id INTEGER REFERENCES config_snapshots(id),
  source TEXT NOT NULL DEFAULT 'simulated',
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS local_workflow_attempts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  workflow TEXT NOT NULL CHECK(workflow IN ('ztp_publish','config_capture','config_restore')),
  device_id INTEGER REFERENCES devices(id) ON DELETE SET NULL,
  status TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'simulated',
  details_json TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_local_workflow_attempts_device ON local_workflow_attempts(device_id, created_at DESC);
