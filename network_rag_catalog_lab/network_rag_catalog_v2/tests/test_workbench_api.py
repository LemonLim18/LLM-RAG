import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from app.workbench.api import create_app
from app.devices.inventory import load_inventory
from app.workbench.inventory_service import DeviceNotFoundError, get_inventory_device, list_inventory_devices
from app.workbench.models import HealthResponse, InventoryDetailResponse, InventoryListResponse
from app.workbench.runtime_status import runtime_status


class WorkbenchApiTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()

    def route(self, path):
        return next(route for route in self.app.routes if getattr(route, "path", None) == path)

    def test_health_is_passive_and_successful(self):
        route = self.route("/api/v1/health")

        self.assertEqual(route.methods, {"GET"})
        self.assertIs(route.response_model, HealthResponse)
        self.assertEqual(HealthResponse().model_dump(), {
            "status": "ok",
            "service": "network-rag-workbench",
            "api_version": 1,
        })

    def test_direct_file_status_has_no_fabricated_release_or_ai_readiness(self):
        with TemporaryDirectory(dir=Path.cwd()) as directory, patch.dict(os.environ, {"NETWORK_RAG_RUNTIME": "files"}), \
                patch("app.workbench.runtime_status.BASE_DIR", Path(directory)):
            response = runtime_status()

        body = response.model_dump(mode="json")
        self.assertEqual(body["knowledge"], {
            "status": "ready",
            "configured_runtime_mode": "files",
            "effective_runtime_authority": "direct_files",
            "authoring_authority": "json",
            "active_release_id": None,
            "error_code": None,
        })
        self.assertEqual(body["llm"]["status"], "not_checked")
        self.assertEqual(body["embeddings"]["status"], "not_checked")
        self.assertEqual(body["retrieval"]["status"], "not_checked")

    def test_published_status_reports_the_actual_active_release(self):
        release_id = "a" * 32
        pointer = {"release_id": release_id, "manifest_sha256": "b" * 64}
        with TemporaryDirectory(dir=Path.cwd()) as directory:
            releases = Path(directory)
            (releases / "active.json").write_text(json.dumps(pointer), encoding="utf-8")
            with patch.dict(os.environ, {"NETWORK_RAG_RUNTIME": "published"}), \
                    patch("app.workbench.runtime_status.BASE_DIR", releases.parent), \
                    patch("app.workbench.runtime_status.CATALOG_RELEASES_DIR", releases):
                response = runtime_status()

        knowledge = response.model_dump(mode="json")["knowledge"]
        self.assertEqual(knowledge["effective_runtime_authority"], "published_release")
        self.assertEqual(knowledge["active_release_id"], release_id)

    def test_only_configured_local_origins_are_registered_for_cors(self):
        middleware = self.app.user_middleware[0]

        self.assertEqual(middleware.cls.__name__, "CORSMiddleware")
        self.assertEqual(
            middleware.kwargs["allow_origins"],
            ["http://127.0.0.1:5173", "http://localhost:5173"],
        )
        self.assertNotIn("https://example.invalid", middleware.kwargs["allow_origins"])

    def test_inventory_routes_are_registered_as_typed_gets(self):
        list_route = self.route("/api/v1/inventory/devices")
        detail_route = self.route("/api/v1/inventory/devices/{device_id}")

        self.assertEqual(list_route.methods, {"GET"})
        self.assertIs(list_route.response_model, InventoryListResponse)
        self.assertEqual(detail_route.methods, {"GET"})
        self.assertIs(detail_route.response_model, InventoryDetailResponse)

    def test_inventory_api_uses_the_same_v9_identity_and_vendor_records(self):
        source = {device["id"]: device for device in load_inventory()}
        response = list_inventory_devices()
        exposed = {device.id: device for device in response.devices}

        self.assertEqual(set(exposed), set(source))
        for device_id in ("dev-r1", "dev-r2", "dev-r3"):
            self.assertEqual(exposed[device_id].hostname, source[device_id]["hostname"])
            self.assertEqual(exposed[device_id].vendor, source[device_id]["vendor"])
        self.assertEqual(response.source, "synthetic")
        self.assertEqual(len(response.inventory_revision), 64)

    def test_inventory_detail_returns_known_device_without_internal_metadata(self):
        response = get_inventory_device("dev-r1")
        payload = response.model_dump(mode="json")["device"]

        self.assertEqual(payload["hostname"], "R1")
        self.assertEqual(payload["vendor"], "cisco")
        self.assertNotIn("ansible", payload)
        self.assertNotIn("monitoring", payload)
        self.assertNotIn("source_refs", payload)
        self.assertNotIn("management_ip", payload)

    def test_inventory_detail_distinguishes_unknown_device(self):
        with self.assertRaises(DeviceNotFoundError) as error:
            get_inventory_device("missing-device")

        self.assertEqual(error.exception.device_id, "missing-device")


if __name__ == "__main__":
    unittest.main()
