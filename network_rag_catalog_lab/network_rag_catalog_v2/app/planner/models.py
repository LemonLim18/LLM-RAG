from dataclasses import dataclass, field
from typing import Any

@dataclass
class OperationIntent:
    intent_id: str
    request_text: str
    target_refs: list[str] = field(default_factory=list)
    target_text: str = ""
    source_spans: list[dict[str, Any]] = field(default_factory=list)
    issues: list[dict[str, Any]] = field(default_factory=list)

@dataclass
class PlannedTask:
    intent_id: str
    request_text: str
    category: str
    operation_id: str
    parameters: dict[str, Any]
    target_refs: list[str]
    status: str = "collecting"
    parameter_provenance: dict[str, str] = field(default_factory=dict)
    issues: list[dict[str, Any]] = field(default_factory=list)
    clarification_questions: list[str] = field(default_factory=list)
    clarification_history: list[dict[str, Any]] = field(default_factory=list)
    target_devices: list[dict[str, Any]] = field(default_factory=list)
    configs: list[dict[str, Any]] = field(default_factory=list)
    target_queries: list[dict[str, Any]] = field(default_factory=list)
    target_resolution: list[dict[str, Any]] = field(default_factory=list)
    logical_intent_id: str = ""
    device_id: str | None = None
    revision: int = 1
    source_revision: str = ""
    questions: list[dict[str, Any]] = field(default_factory=list)
    candidates: list[dict[str, Any]] = field(default_factory=list)
    confirmations: dict[str, Any] = field(default_factory=dict)
    item_ids: dict[str, str] = field(default_factory=dict)
    feedback: str = ""
    planning_issues: list[dict[str, Any]] = field(default_factory=list)
    source_spans: list[dict[str, Any]] = field(default_factory=list)
    scope_device_ids: list[str] = field(default_factory=list)
    parameter_evidence: dict[str, Any] = field(default_factory=dict)

@dataclass
class ExecutionPlan:
    original_prompt: str
    # If the caller doesn't provide intents, create an empty list by default.
    intents: list[OperationIntent] = field(default_factory=list)
    tasks: list[PlannedTask] = field(default_factory=list)
    status: str = "collecting"
    issues: list[dict[str, Any]] = field(default_factory=list)
    source_revision: str = ""
    schema_version: int = 2


@dataclass
class ClarificationAnswer:
    question_id: str
    revision: int
    source_revision: str
    kind: str = "custom"
    raw_input: str = ""
    selected_ids: list[str] = field(default_factory=list)
