CREATE TABLE schema_migrations(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);
CREATE TABLE authoring_state(singleton INTEGER PRIMARY KEY CHECK(singleton = 1), generation INTEGER NOT NULL CHECK(generation >= 1));
CREATE TABLE categories(category_id TEXT PRIMARY KEY, ordinal INTEGER UNIQUE NOT NULL, payload TEXT NOT NULL CHECK(json_valid(payload)));
CREATE TABLE parameters(parameter_id TEXT PRIMARY KEY, ordinal INTEGER UNIQUE NOT NULL, payload TEXT NOT NULL CHECK(json_valid(payload)));
CREATE TABLE category_parameters(
  category_id TEXT NOT NULL REFERENCES categories(category_id),
  parameter_id TEXT NOT NULL REFERENCES parameters(parameter_id),
  ordinal INTEGER UNIQUE NOT NULL, payload TEXT NOT NULL CHECK(json_valid(payload)),
  PRIMARY KEY(category_id, parameter_id)
);
CREATE TABLE operations(
  operation_id TEXT PRIMARY KEY, category_id TEXT NOT NULL REFERENCES categories(category_id),
  ordinal INTEGER UNIQUE NOT NULL, payload TEXT NOT NULL CHECK(json_valid(payload)),
  UNIQUE(operation_id, category_id)
);
CREATE TABLE operation_versions(
  operation_id TEXT NOT NULL, version INTEGER NOT NULL CHECK(version > 0), category_id TEXT NOT NULL,
  PRIMARY KEY(operation_id, version), UNIQUE(operation_id, version, category_id),
  FOREIGN KEY(operation_id, category_id) REFERENCES operations(operation_id, category_id)
);
CREATE TABLE operation_parameters(
  operation_id TEXT NOT NULL, operation_version INTEGER NOT NULL, category_id TEXT NOT NULL,
  parameter_id TEXT NOT NULL, field_path TEXT NOT NULL, ordinal INTEGER UNIQUE NOT NULL,
  payload TEXT NOT NULL CHECK(json_valid(payload)),
  PRIMARY KEY(operation_id, field_path),
  FOREIGN KEY(operation_id, operation_version, category_id) REFERENCES operation_versions(operation_id, version, category_id),
  FOREIGN KEY(category_id, parameter_id) REFERENCES category_parameters(category_id, parameter_id)
);
CREATE TABLE operation_rules(
  operation_id TEXT NOT NULL, operation_version INTEGER NOT NULL, field_path TEXT NOT NULL,
  ordinal INTEGER UNIQUE NOT NULL, payload TEXT NOT NULL CHECK(json_valid(payload)),
  PRIMARY KEY(operation_id, field_path),
  FOREIGN KEY(operation_id, operation_version) REFERENCES operation_versions(operation_id, version)
);
CREATE TABLE template_bindings(
  ordinal INTEGER PRIMARY KEY, operation_id TEXT NOT NULL, operation_version INTEGER NOT NULL,
  payload TEXT NOT NULL CHECK(json_valid(payload)),
  FOREIGN KEY(operation_id, operation_version) REFERENCES operation_versions(operation_id, version)
);
CREATE TABLE context_policies(
  operation_id TEXT PRIMARY KEY REFERENCES operations(operation_id),
  ordinal INTEGER UNIQUE NOT NULL, payload TEXT NOT NULL CHECK(json_valid(payload))
);
CREATE TABLE context_metadata(singleton INTEGER PRIMARY KEY CHECK(singleton = 1), payload TEXT NOT NULL CHECK(json_valid(payload)));
CREATE TABLE authoring_audit(
  audit_id TEXT PRIMARY KEY, generation INTEGER UNIQUE NOT NULL,
  actor TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL,
  before_revision TEXT, after_revision TEXT NOT NULL,
  before_catalogs TEXT NOT NULL CHECK(json_valid(before_catalogs)),
  after_catalogs TEXT NOT NULL CHECK(json_valid(after_catalogs))
);
