"""Transient compute-only edits; these contracts do not create documents."""
from typing import Literal
from uuid import UUID
from pydantic import Field
from .generated_originals import StrictModel, Digest
from .working_documents import DocumentId


class EditRequest(StrictModel):
    expected_revision: UUID
    current_content: str = Field(strict=True, max_length=65536)
    instruction: str = Field(strict=True, min_length=1, max_length=2000)


class EditResponse(StrictModel):
    api_version: Literal[1] = 1
    document_id: DocumentId
    base_revision: UUID
    base_content_sha256: Digest
    proposal_id: UUID
    outcome: Literal['proposal', 'no_change', 'clarification_required', 'unsupported']
    message: str
    proposed_content: str | None = None
    operation_id: str = 'rename_vlan'
    parameters: dict[str, str | int] = Field(default_factory=dict)
    evidence: dict[str, str] = Field(default_factory=dict)
    authority: dict[str, str | None]
    validation: Literal['bounded_operation_only'] = 'bounded_operation_only'
    deployment: Literal['not_deployed'] = 'not_deployed'
