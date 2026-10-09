from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from app.planner.models import ExecutionPlan
from .models import ResponseModel


class PlanningRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    prompt: str = Field(strict=True, min_length=1, max_length=8000)
    mode: Literal["local_v9"]
    client_request_id: UUID


class SessionPayload(ResponseModel):
    session_id: str
    created_at: str
    updated_at: str
    status: str
    # Reuse V9's dataclasses, including every task/evidence/vendor field.
    plan: ExecutionPlan
    history: list[dict[str, JsonValue]]
    schema_version: int
    pending_questions: list[dict[str, JsonValue]]


class SessionSnapshot(ResponseModel):
    api_version: Literal[1] = 1
    mode: Literal["local_v9"] = "local_v9"
    inventory_source: Literal["synthetic"] = "synthetic"
    session_revision: str
    session: SessionPayload


class PlanningResponse(SessionSnapshot):
    client_request_id: UUID


class SavedSessionResponse(SessionSnapshot):
    origin: Literal["saved_session"] = "saved_session"
    freshness: Literal["not_checked"] = "not_checked"
    mutation_eligibility: Literal["not_checked"] = "not_checked"


class SavedSessionErrorDetail(ResponseModel):
    code: str
    message: str


class SavedSessionErrorResponse(ResponseModel):
    detail: SavedSessionErrorDetail


class CreationOutcome(ResponseModel):
    api_version: Literal[1] = 1
    client_request_id: UUID
    status: Literal["unknown", "in_progress", "completed", "terminal_error", "indeterminate", "corrupt"]
    message: str
    session_id: UUID | None = None
    session_revision: str | None = None
    error_code: str | None = None


class PlanningErrorDetail(ResponseModel):
    code: str
    message: str
    client_request_id: UUID
    current_session: PlanningResponse | None = None


class PlanningErrorResponse(ResponseModel):
    detail: PlanningErrorDetail


class AnswerInput(ResponseModel):
    question_id: str = Field(strict=True, min_length=1, max_length=200)
    revision: int = Field(strict=True, ge=1)
    source_revision: str = Field(strict=True, min_length=1, max_length=200)
    kind: Literal["custom", "selection"]
    raw_input: str = Field(default="", strict=True, max_length=8000)
    selected_ids: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_shape(self):
        if self.kind == "custom" and (not self.raw_input.strip() or self.selected_ids):
            raise ValueError("Custom answers require text and no option IDs.")
        if self.kind == "selection" and (self.raw_input or not self.selected_ids):
            raise ValueError("Selection answers require option IDs and no custom text.")
        return self


class AnswerRequest(ResponseModel):
    client_request_id: UUID
    expected_session_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    answer: AnswerInput


class AnswerResponse(PlanningResponse):
    accepted: Literal[True] = True
    answered_question_id: str
