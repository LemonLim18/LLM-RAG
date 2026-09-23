from dataclasses import dataclass, field
from typing import Any

@dataclass
class OperationIntent:
    intent_id: str
    request_text: str
    target_refs: list[str] = field(default_factory=list)

@dataclass
class PlannedTask:
    intent_id: str
    request_text: str
    category: str
    operation_id: str
    parameters: dict[str, Any]
    target_refs: list[str]
    status: str = "ready"
    parameter_provenance: dict[str, str] = field(default_factory=dict)
    issues: list[dict[str, Any]] = field(default_factory=list)
    clarification_questions: list[str] = field(default_factory=list)
    clarification_history: list[dict[str, Any]] = field(default_factory=list)
    target_devices: list[dict[str, Any]] = field(default_factory=list)
    configs: list[dict[str, Any]] = field(default_factory=list)
    target_queries: list[dict[str, Any]] = field(default_factory=list)
    target_resolution: list[dict[str, Any]] = field(default_factory=list)

@dataclass
class ExecutionPlan:
    original_prompt: str
    # If the caller doesn't provide intents, create an empty list by default.
    intents: list[OperationIntent] = field(default_factory=list)
    tasks: list[PlannedTask] = field(default_factory=list)
