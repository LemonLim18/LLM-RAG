from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue

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


class PlanningResponse(ResponseModel):
    api_version: Literal[1] = 1
    mode: Literal["local_v9"] = "local_v9"
    inventory_source: Literal["synthetic"] = "synthetic"
    client_request_id: UUID
    session_revision: str
    session: SessionPayload


class PlanningErrorDetail(ResponseModel):
    code: str
    message: str
    client_request_id: UUID


class PlanningErrorResponse(ResponseModel):
    detail: PlanningErrorDetail
