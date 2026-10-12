CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Preserve every existing row. Guard new/edited links against cross-device
-- interface references and duplicate/reversed physical port assignments.
CREATE TRIGGER IF NOT EXISTS m0_link_insert_guard BEFORE INSERT ON links BEGIN
 SELECT CASE WHEN NEW.src_device_id = NEW.dst_device_id THEN RAISE(ABORT, 'self link') END;
 SELECT CASE WHEN NEW.src_interface_id IS NOT NULL AND NOT EXISTS
 (SELECT 1 FROM interfaces WHERE id=NEW.src_interface_id AND device_id=NEW.src_device_id)
 THEN RAISE(ABORT, 'source interface ownership') END;
 SELECT CASE WHEN NEW.dst_interface_id IS NOT NULL AND NOT EXISTS
 (SELECT 1 FROM interfaces WHERE id=NEW.dst_interface_id AND device_id=NEW.dst_device_id)
 THEN RAISE(ABORT, 'destination interface ownership') END;
 SELECT CASE WHEN EXISTS (SELECT 1 FROM links WHERE
 src_interface_id IN (NEW.src_interface_id, NEW.dst_interface_id) OR
 dst_interface_id IN (NEW.src_interface_id, NEW.dst_interface_id))
 THEN RAISE(ABORT, 'interface already linked') END;
END;
CREATE TRIGGER IF NOT EXISTS m0_link_update_guard BEFORE UPDATE ON links BEGIN
 SELECT CASE WHEN NEW.src_device_id = NEW.dst_device_id THEN RAISE(ABORT, 'self link') END;
 SELECT CASE WHEN NEW.src_interface_id IS NOT NULL AND NOT EXISTS
 (SELECT 1 FROM interfaces WHERE id=NEW.src_interface_id AND device_id=NEW.src_device_id)
 THEN RAISE(ABORT, 'source interface ownership') END;
 SELECT CASE WHEN NEW.dst_interface_id IS NOT NULL AND NOT EXISTS
 (SELECT 1 FROM interfaces WHERE id=NEW.dst_interface_id AND device_id=NEW.dst_device_id)
 THEN RAISE(ABORT, 'destination interface ownership') END;
 SELECT CASE WHEN EXISTS (SELECT 1 FROM links WHERE id<>NEW.id AND
 (src_interface_id IN (NEW.src_interface_id, NEW.dst_interface_id) OR
 dst_interface_id IN (NEW.src_interface_id, NEW.dst_interface_id)))
 THEN RAISE(ABORT, 'interface already linked') END;
END;

-- Audit in the same transaction as the mutation, including deletes. No secrets.
CREATE TRIGGER IF NOT EXISTS m0_device_insert AFTER INSERT ON devices BEGIN
 INSERT INTO audit_log(user_id,action,target) VALUES ('local','device.create',CAST(NEW.id AS TEXT)); END;
CREATE TRIGGER IF NOT EXISTS m0_device_update AFTER UPDATE ON devices BEGIN
 INSERT INTO audit_log(user_id,action,target) VALUES ('local','device.update',CAST(NEW.id AS TEXT)); END;
CREATE TRIGGER IF NOT EXISTS m0_device_delete AFTER DELETE ON devices BEGIN
 INSERT INTO audit_log(user_id,action,target) VALUES ('local','device.delete',CAST(OLD.id AS TEXT)); END;
CREATE TRIGGER IF NOT EXISTS m0_interface_insert AFTER INSERT ON interfaces BEGIN
 INSERT INTO audit_log(user_id,action,target) VALUES ('local','interface.create',CAST(NEW.id AS TEXT)); END;
CREATE TRIGGER IF NOT EXISTS m0_interface_update AFTER UPDATE ON interfaces BEGIN
 INSERT INTO audit_log(user_id,action,target) VALUES ('local','interface.update',CAST(NEW.id AS TEXT)); END;
CREATE TRIGGER IF NOT EXISTS m0_interface_delete AFTER DELETE ON interfaces BEGIN
 DELETE FROM links WHERE src_interface_id=OLD.id OR dst_interface_id=OLD.id;
 INSERT INTO audit_log(user_id,action,target) VALUES ('local','interface.delete',CAST(OLD.id AS TEXT)); END;
CREATE TRIGGER IF NOT EXISTS m0_interface_unlink BEFORE DELETE ON interfaces BEGIN
 DELETE FROM links WHERE src_interface_id=OLD.id OR dst_interface_id=OLD.id; END;
CREATE TRIGGER IF NOT EXISTS m0_link_insert AFTER INSERT ON links BEGIN
 INSERT INTO audit_log(user_id,action,target) VALUES ('local','link.create',CAST(NEW.id AS TEXT)); END;
CREATE TRIGGER IF NOT EXISTS m0_link_update AFTER UPDATE ON links BEGIN
 INSERT INTO audit_log(user_id,action,target) VALUES ('local','link.update',CAST(NEW.id AS TEXT)); END;
CREATE TRIGGER IF NOT EXISTS m0_link_delete AFTER DELETE ON links BEGIN
 INSERT INTO audit_log(user_id,action,target) VALUES ('local','link.delete',CAST(OLD.id AS TEXT)); END;
CREATE TRIGGER IF NOT EXISTS m0_snapshot_insert AFTER INSERT ON config_snapshots BEGIN
 INSERT INTO audit_log(user_id,action,target) VALUES ('local','snapshot.create',CAST(NEW.id AS TEXT)); END;
CREATE TRIGGER IF NOT EXISTS m0_snapshot_update AFTER UPDATE ON config_snapshots BEGIN
 INSERT INTO audit_log(user_id,action,target) VALUES ('local','snapshot.update',CAST(NEW.id AS TEXT)); END;
CREATE TRIGGER IF NOT EXISTS m0_snapshot_delete AFTER DELETE ON config_snapshots BEGIN
 INSERT INTO audit_log(user_id,action,target) VALUES ('local','snapshot.delete',CAST(OLD.id AS TEXT)); END;
CREATE TRIGGER IF NOT EXISTS m0_policy_delete BEFORE DELETE ON policies BEGIN
 INSERT INTO audit_log(user_id,action,target,details)
 VALUES ('local','policy.delete',OLD.policy_id,(SELECT json_group_array(json_object('action',action,'old_value',old_value_json,'new_value',new_value_json,'actor',changed_by,'timestamp',timestamp)) FROM policy_audit_log WHERE policy_id=OLD.id)); END;
