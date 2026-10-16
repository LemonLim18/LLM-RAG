"""Shared wire contracts. Client content is context, never an authorization grant."""
from hashlib import sha256
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


def text_digest(text: str) -> str:
    return sha256(text.encode('utf-8')).hexdigest()


class Selection(StrictModel):
    text: str = Field(max_length=200000)
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)


class EditorSnapshot(StrictModel):
    document_id: str = Field(min_length=1, max_length=240)
    path: str = Field(min_length=1, max_length=240)
    content: str = Field(max_length=1000000)
    language: str = Field(min_length=1, max_length=40)
    model_id: str = Field(min_length=1, max_length=300)
    model_version: int = Field(ge=1)
    buffer_epoch: int = Field(ge=0)
    saved_revision: int = Field(ge=0)
    is_dirty: bool
    read_only: bool
    selection: Selection | None = None
    device_id: str | None = Field(default=None, max_length=100)

    @model_validator(mode='after')
    def valid_text(self):
        if len(self.content.encode('utf-8')) > 1000000:
            raise ValueError('Editor context exceeds 1 MiB UTF-8')
        if self.selection and (self.selection.end_line < self.selection.start_line or self.selection.text not in self.content):
            raise ValueError('Selection does not match the supplied editor buffer')
        return self


class TurnRequest(StrictModel):
    request_id: UUID
    prompt: str = Field(min_length=1, max_length=20000)
    model: str | None = Field(default=None, max_length=150)
    editor: EditorSnapshot | None = None
    attachment_ids: list[UUID] = Field(default_factory=list, max_length=5)


class Evidence(StrictModel):
    id: str
    source: str
    origin: Literal['stored', 'live', 'simulated', 'sample', 'prediction', 'user_supplied']
    time_scope: Literal['current', 'historical', 'forecast', 'unspecified'] = 'unspecified'
    captured_at: str | None = None
    retrieved_at: str | None = None
    requested_time_range: dict[str,str] | None = None
    freshness: Literal['not_applicable','unknown','fresh','stale'] = 'unknown'
    source_revision: str | None = None
    device_refs: list[str] = Field(default_factory=list)
    page: int | None = None
    start_line: int | None = None
    end_line: int | None = None
    authority: str = 'context_only'


class ToolResult(StrictModel):
    status: Literal['success', 'unavailable', 'denied', 'error']
    data: Any = None
    message: str = ''
    evidence: list[Evidence] = Field(default_factory=list)


class TurnResponse(StrictModel):
    request_id: str
    status: Literal['success', 'unavailable', 'denied', 'error', 'clarification_required']
    kind: Literal['answer', 'generation_preview', 'edit_proposal', 'clarification'] = 'answer'
    answer: str
    model: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    context_coverage: dict = Field(default_factory=dict)
    observations: list[dict] = Field(default_factory=list)
    answer_release: dict = Field(default_factory=dict)
    preview: dict | None = None
    proposal: dict | None = None
    execution_available: Literal[False] = False


class HandoffOperationCandidate(StrictModel):
    operation_id: str
    release_id: str
    authority: Literal['hint_only'] = 'hint_only'


class EngineeringHandoff(StrictModel):
    """Reviewed investigation context; acceptance never submits an engineering turn."""
    source_conversation: str
    source_turns: list[str]
    created_at: str
    device_refs: list[str]
    evidence_ids: list[str]
    evidence_snapshots: list[Evidence]
    requested_action: str
    operation_candidates: list[HandoffOperationCandidate] = Field(default_factory=list)
    knowledge_release: str | None = None
