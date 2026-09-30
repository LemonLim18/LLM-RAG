"""Strict envelopes for a local CLI and a future authenticated API."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ..knowledge.models import NonBlankText, StableId, OperationParameterMapping, OperationSchemaRule, TemplateBinding


class Contract(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class EntityChange(Contract):
    entity: Literal["category", "parameter", "operation", "membership", "contract", "context_rules"]
    action: Literal["create", "update", "delete", "retire", "assign", "unassign", "replace"]
    entity_id: StableId | None = None
    values: dict = Field(default_factory=dict)


class OperationContractInput(Contract):
    version: int = Field(ge=1)
    mappings: list[OperationParameterMapping]
    rules: list[OperationSchemaRule]
    templates: list[TemplateBinding]


class EditRequest(Contract):
    expected_revision: NonBlankText
    actor: NonBlankText
    reason: NonBlankText
    changes: list[EntityChange] = Field(min_length=1)


class PublishRequest(Contract):
    expected_revision: NonBlankText
    expected_release: str | None
    actor: NonBlankText
    reason: NonBlankText
    mode: Literal["offline", "chroma"] = "chroma"


class MigrationRequest(Contract):
    expected_revision: NonBlankText
    actor: NonBlankText
    reason: NonBlankText


class CatalogExport(Contract):
    format_version: Literal[1] = 1
    revision: str
    catalogs: dict[str, list | dict]
    asset_hashes: dict[str, str]


class ImportRequest(Contract):
    expected_revision: NonBlankText
    actor: NonBlankText
    reason: NonBlankText
    bundle: CatalogExport


class ManagementIssue(Contract):
    code: str
    path: str = ""
    message: str


class ManagementResult(Contract):
    ok: bool
    revision: str | None = None
    data: dict = Field(default_factory=dict)
    issues: list[ManagementIssue] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
