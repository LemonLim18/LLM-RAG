import json
from pathlib import Path
import shutil
import tempfile
import unittest

from app.config import BASE_DIR
from app.knowledge.runtime_audit import audit_runtime


class RuntimeAuditTests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.base = Path(directory)
        shutil.copytree(BASE_DIR / "data/catalog", self.base / "data/catalog")
        for relative in ("data/operations/vlan/modify_vlan", "data/templates/cisco/vlan/modify_vlan"):
            shutil.copytree(BASE_DIR / relative, self.base / relative)

    def test_matching_state_contract_without_a_release_is_not_fabricated(self):
        result = audit_runtime(self.base, ["modify_vlan"])
        self.assertTrue(result["matches"], result["differences"])
        self.assertEqual(result["knowledge_snapshot_id"], "")
        self.assertEqual(result["managed_authority"], "json")
        self.assertFalse((self.base / "storage").exists())

    def test_vendor_contract_drift_is_reported_without_writes(self):
        path = self.base / "data/operations/vlan/modify_vlan/schema.json"
        schema = json.loads(path.read_text())
        schema["properties"]["vlan_status"]["enum"] = ["active"]
        path.write_text(json.dumps(schema), encoding="utf-8")
        before = path.read_bytes()
        result = audit_runtime(self.base, ["modify_vlan"])
        self.assertFalse(result["matches"])
        self.assertEqual({row["component"] for row in result["differences"]}, {"schema", "vendors"})
        self.assertEqual(path.read_bytes(), before)
        self.assertFalse((self.base / "storage").exists())

    def test_description_parameter_is_not_confused_with_schema_annotation(self):
        path = self.base / "data/operations/vlan/modify_vlan/schema.json"
        schema = json.loads(path.read_text())
        schema["properties"]["description"] = {"type": "string"}
        path.write_text(json.dumps(schema), encoding="utf-8")
        result = audit_runtime(self.base, ["modify_vlan"])
        difference = next(row for row in result["differences"] if row["component"] == "schema")
        self.assertIn("description", difference["files"]["properties"])


if __name__ == "__main__":
    unittest.main()
