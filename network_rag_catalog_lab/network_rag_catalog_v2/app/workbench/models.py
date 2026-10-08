from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HealthResponse(ResponseModel):
    status: Literal["ok"] = "ok"
    service: Literal["network-rag-workbench"] = "network-rag-workbench"
    api_version: Literal[1] = 1


class PassiveCheck(ResponseModel):
    status: Literal["not_checked"] = "not_checked"
    configured_model: str | None = None
    reason: str


class KnowledgeAuthority(ResponseModel):
    status: Literal["ready", "unavailable"]
    configured_runtime_mode: Literal["files", "published"] | None
    effective_runtime_authority: Literal["direct_files", "published_release"] | None
    authoring_authority: Literal["json", "sqlite"] | None
    active_release_id: str | None
    error_code: str | None = None


class RuntimeStatusResponse(ResponseModel):
    api_version: Literal[1] = 1
    service: Literal["ready"] = "ready"
    knowledge: KnowledgeAuthority
    llm: PassiveCheck
    embeddings: PassiveCheck
    retrieval: PassiveCheck


class InventoryNeighbor(ResponseModel):
    device: str
    interface: str


class InventoryInterface(ResponseModel):
    name: str
    aliases: list[str] = Field(default_factory=list)
    type: str
    enabled: bool
    role: str
    neighbor: InventoryNeighbor | None = None


class InventoryCapabilities(ResponseModel):
    features: list[str] = Field(default_factory=list)
    interface_name_style: str | None = None


class InventoryDevice(ResponseModel):
    id: str
    hostname: str
    kind: str
    display_name: str
    aliases: list[str] = Field(default_factory=list)
    vendor: str
    platform: str
    version: str
    site: str
    role: str
    location: str | None = None
    status: str | None = None
    tags: list[str] = Field(default_factory=list)
    interfaces: list[InventoryInterface] = Field(default_factory=list)
    capabilities: InventoryCapabilities


class InventoryListResponse(ResponseModel):
    api_version: Literal[1] = 1
    source: Literal["synthetic"] = "synthetic"
    inventory_revision: str
    devices: list[InventoryDevice]


class InventoryDetailResponse(ResponseModel):
    api_version: Literal[1] = 1
    source: Literal["synthetic"] = "synthetic"
    inventory_revision: str
    device: InventoryDevice
