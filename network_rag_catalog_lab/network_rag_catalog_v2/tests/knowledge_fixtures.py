import json
from pathlib import Path
import shutil
import tempfile
from unittest.mock import patch

from app.config import BASE_DIR
from app.knowledge.publication import _service, publish
from app.knowledge.runtime import snapshot_scope


class KnowledgeFixture:
    def setUp(self):
        self.enterContext(snapshot_scope(None))
        for target in ("app.llm.llm", "app.planner.intent_planner.llm", "app.parameters.parameter_extractor.llm"):
            self.enterContext(patch(target)).invoke.return_value.content = "null"
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.base = self.root / "project"
        shutil.copytree(BASE_DIR / "data", self.base / "data",
                        ignore=shutil.ignore_patterns(".authoring.lock", ".authoring-pending.json", ".*.tmp"))
        self.releases = self.root / "releases"
        self.service = _service(self.base / "data/catalog")

    def read(self, name):
        return json.loads((self.base / "data/catalog" / (name + ".json")).read_text(encoding="utf-8"))

    def write(self, name, value):
        (self.base / "data/catalog" / (name + ".json")).write_text(json.dumps(value), encoding="utf-8")
        self.service.reload()

    def publish(self, **kwargs):
        return publish(base_dir=self.base, releases_dir=self.releases, mode=kwargs.pop("mode", "offline"), **kwargs)

    def bump(self, operation_id):
        for name in ("operations", "operation_parameters", "operation_rules", "template_bindings"):
            rows = self.read(name)
            for row in rows:
                if row["operation_id"] == operation_id:
                    key = "version" if name == "operations" else "operation_version"
                    row[key] += 1
            self.write(name, rows)
