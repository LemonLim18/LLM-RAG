"""Add-only synthetic inventory writes. No runtime/AI or infrastructure imports."""
import json
import os
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.devices import inventory
from app.devices.target_resolver import resolve_intent_targets
from .inventory_service import _device, _revision
from .models import InventoryDetailResponse, ResponseModel
from .planning_service import PlanningError
from .saved_sessions import _reject_constant, _unique_object

Text = Annotated[str, Field(strict=True, min_length=1, max_length=120, pattern=r"^[^\x00-\x1f\x7f]+$")]
Token = Annotated[str, Field(strict=True, min_length=1, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:/-]*$")]
Feature = Literal['interface', 'vlan', 'ip_address', 'static_routing', 'ospf', 'bgp', 'isis', 'acl', 'qos']


class RegistrationModel(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class InitialInterface(RegistrationModel):
    name: Token
    aliases: list[Token] = Field(default_factory=list, max_length=16)
    type: Literal['ethernet', 'loopback']
    role: Text
    enabled: bool = Field(strict=True)


class DeclaredCapabilities(RegistrationModel):
    # Empty features in V9 means no category restriction, not "supports nothing".
    # Require explicit declarations instead of assigning capabilities silently.
    features: list[Feature] = Field(min_length=1, max_length=9)


class NewInventoryDevice(RegistrationModel):
    hostname: Token
    display_name: Text
    kind: Literal['router', 'switch', 'firewall']
    vendor: Literal['cisco', 'huawei', 'juniper']
    platform: Literal['iosxe', 'vrp', 'junos']
    version: Token
    site: Text
    role: Text
    location: Text | None = None
    aliases: list[Text] = Field(default_factory=list, max_length=16)
    tags: list[Text] = Field(default_factory=list, max_length=32)
    capabilities: DeclaredCapabilities
    interfaces: list[InitialInterface] = Field(default_factory=list, max_length=64)

    @model_validator(mode='after')
    def vendor_platform(self):
        if self.platform != {'cisco': 'iosxe', 'huawei': 'vrp', 'juniper': 'junos'}[self.vendor]:
            raise ValueError('Vendor/platform pair must be Cisco/iosxe, Huawei/vrp or Juniper/junos.')
        if len(set(self.capabilities.features)) != len(self.capabilities.features):
            raise ValueError('Declare each feature only once.')
        return self


class DeviceRegistration(RegistrationModel):
    expected_inventory_revision: str = Field(pattern=r'^[a-f0-9]{64}$')
    device: NewInventoryDevice


class InventoryErrorDetail(ResponseModel):
    code: str
    message: str
    current_inventory_revision: str | None = None


class InventoryErrorResponse(ResponseModel):
    detail: InventoryErrorDetail


class InventoryWriteError(PlanningError):
    def __init__(self, status, code, message, revision=None):
        super().__init__(status, code, message)
        self.revision = revision


# Validate fields consumed by the existing loader/projection/resolver, but do not
# coerce or reserialize original dictionaries. Rich policy/operational metadata
# remains intact and is not exposed or interpreted by this registration adapter.
class StoredInterface(BaseModel):
    model_config = ConfigDict(extra='allow', strict=True)
    name: str
    aliases: list[str] = Field(default_factory=list)
    type: str
    enabled: bool
    role: str
    neighbor: dict[str, str] | None = None


class StoredCapabilities(BaseModel):
    model_config = ConfigDict(extra='allow', strict=True)
    features: list[str]
    interface_name_style: str | None = None


class StoredDevice(BaseModel):
    model_config = ConfigDict(extra='allow', strict=True)
    id: str
    hostname: str
    display_name: str
    kind: str
    vendor: str
    platform: str
    version: str
    site: str
    role: str
    location: str | None = None
    status: str | None = None
    aliases: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    capabilities: StoredCapabilities
    interfaces: list[StoredInterface]


def validate_inventory(records):
    if not isinstance(records, list):
        raise ValueError('Inventory must be a list.')
    identities, ids, interfaces = {}, set(), {}
    for raw in records:
        device = StoredDevice.model_validate(raw)
        if not all(getattr(device, field).strip() for field in ('id', 'hostname', 'display_name', 'kind', 'vendor', 'platform', 'version', 'site', 'role')):
            raise ValueError('Required inventory fields cannot be blank.')
        if device.id.casefold() in ids:
            raise ValueError('Duplicate device ID.')
        ids.add(device.id.casefold())
        for name in [device.id, device.hostname, device.display_name, *device.aliases]:
            key = name.strip().casefold()
            if not key or (key in identities and identities[key] != device.id):
                raise ValueError('Device identity conflicts with another record.')
            identities[key] = device.id
        seen = {}
        for index, item in enumerate(device.interfaces):
            for name in [item.name, *item.aliases]:
                key = name.strip().casefold()
                if not key or (key in seen and seen[key] != index):
                    raise ValueError('Duplicate or empty interface identity.')
                seen[key] = index
        interfaces[device.id] = seen
        _device(raw)  # Verify the established safe projection before committing.
    for device in records:
        for item in device['interfaces']:
            neighbor = item.get('neighbor')
            if neighbor:
                target = identities.get(neighbor['device'].strip().casefold())
                if target not in interfaces or neighbor['interface'].strip().casefold() not in interfaces[target]:
                    raise ValueError('Unresolved neighbor reference.')


def register_device(request: DeviceRegistration) -> InventoryDetailResponse:
    # Same path object used by load_inventory, including controlled test overrides.
    path = inventory.INVENTORY_FILE
    temporary = path.with_suffix(f'.{uuid4().hex}.tmp')
    try:
        raw = path.read_bytes()
        records = json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
        validate_inventory(records)
        if inventory.load_inventory() != records:
            raise InventoryWriteError(409, 'STALE_INVENTORY', 'Inventory changed while reading. Reload before submitting.')
        revision = _revision(records)
        if revision != request.expected_inventory_revision:
            raise InventoryWriteError(409, 'STALE_INVENTORY', 'Inventory has changed. Reload and review before submitting.', revision)
        new = {'id': f'dev-{uuid4()}', **request.device.model_dump(mode='json'),
               'source_refs': {'registration': 'workbench:synthetic:not-discovered'}}
        proposed = [*records, new]
        try:
            validate_inventory(proposed)
            # Do not accept an identity which the actual selector cannot use.
            for name in [new['hostname'], new['display_name'], *new['aliases']]:
                if [device['id'] for device in resolve_intent_targets([name], proposed)] != [new['id']]:
                    raise ValueError('Identity is ambiguous to V9.')
        except (ValueError, KeyError, TypeError) as error:
            raise InventoryWriteError(409, 'IDENTITY_CONFLICT', 'Device or interface identities conflict or are ambiguous. Use unique names and aliases.', revision) from error
        response = InventoryDetailResponse(inventory_revision=_revision(proposed), device=_device(new))
        # ASCII escapes keep the output compatible with V9's default-encoding reader.
        content = json.dumps(proposed, ensure_ascii=True, indent=2, allow_nan=False).encode('utf-8') + b'\n'
        with temporary.open('xb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        latest = json.loads(path.read_bytes(), object_pairs_hook=_unique_object, parse_constant=_reject_constant)
        if _revision(latest) != revision:
            raise InventoryWriteError(409, 'STALE_INVENTORY', 'Inventory changed before save. Reload before submitting.')
        os.replace(temporary, path)
        return response
    except InventoryWriteError:
        raise
    except OSError as error:
        raise InventoryWriteError(503, 'INVENTORY_STORAGE_UNAVAILABLE', 'Inventory could not be saved. Reload inventory to inspect the outcome before trying again.') from error
    except (ValueError, TypeError, KeyError, ValidationError, RecursionError) as error:
        raise InventoryWriteError(409, 'INVALID_INVENTORY', 'Existing inventory is invalid or changed during registration. Nothing was repaired or overwritten.') from error
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
