from hashlib import sha256
import json

from ..devices.inventory import load_inventory
from .models import (
    InventoryCapabilities,
    InventoryDetailResponse,
    InventoryDevice,
    InventoryInterface,
    InventoryListResponse,
    InventoryNeighbor,
)


class DeviceNotFoundError(LookupError):
    def __init__(self, device_id: str):
        super().__init__(f"Inventory device '{device_id}' was not found.")
        self.device_id = device_id


def _revision(records: list[dict]) -> str:
    canonical = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(canonical.encode("utf-8")).hexdigest()


def _interface(record: dict) -> InventoryInterface:
    neighbor = record.get("neighbor")
    return InventoryInterface(
        name=str(record["name"]),
        aliases=[str(value) for value in record.get("aliases", [])],
        type=str(record["type"]),
        enabled=bool(record["enabled"]),
        role=str(record["role"]),
        neighbor=InventoryNeighbor(
            device=str(neighbor["device"]),
            interface=str(neighbor["interface"]),
        ) if neighbor else None,
    )


def _device(record: dict) -> InventoryDevice:
    capabilities = record.get("capabilities", {})
    return InventoryDevice(
        id=str(record["id"]),
        hostname=str(record["hostname"]),
        kind=str(record["kind"]),
        display_name=str(record["display_name"]),
        aliases=[str(value) for value in record.get("aliases", [])],
        vendor=str(record["vendor"]),
        platform=str(record["platform"]),
        version=str(record["version"]),
        site=str(record["site"]),
        role=str(record["role"]),
        location=str(record["location"]) if record.get("location") is not None else None,
        status=str(record["status"]) if record.get("status") is not None else None,
        tags=[str(value) for value in record.get("tags", [])],
        interfaces=[_interface(value) for value in record.get("interfaces", [])],
        capabilities=InventoryCapabilities(
            features=[str(value) for value in capabilities.get("features", [])],
            interface_name_style=(
                str(capabilities["interface_name_style"])
                if capabilities.get("interface_name_style") is not None else None
            ),
        ),
    )


def list_inventory_devices() -> InventoryListResponse:
    records = load_inventory()
    return InventoryListResponse(
        inventory_revision=_revision(records),
        devices=[_device(record) for record in records],
    )


def get_inventory_device(device_id: str) -> InventoryDetailResponse:
    snapshot = list_inventory_devices()
    device = next((item for item in snapshot.devices if item.id == device_id), None)
    if device is None:
        raise DeviceNotFoundError(device_id)
    return InventoryDetailResponse(
        inventory_revision=snapshot.inventory_revision,
        device=device,
    )
