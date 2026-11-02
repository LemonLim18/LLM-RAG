"""Validated request state. Authorization and clients never live in graph state."""
from typing import Literal
from pydantic import Field
from llm.gateway_models import StrictModel, Evidence, ToolResult
from llm.gateway_routing import SemanticRoute


class ToolStep(StrictModel):
    tool: str
    domain: Literal['inventory','topology','telemetry','syslog','incidents','configuration','knowledge','state']
    parameters: dict | None = None


class AgentState(StrictModel):
    request: str
    owner: str
    assistant: Literal['floating','studio']
    conversation: str
    route: SemanticRoute | None = None
    device_refs: list[str] = Field(default_factory=list)
    interface_refs: list[str] = Field(default_factory=list)
    context_references: dict = Field(default_factory=dict)
    plan: list[ToolStep] = Field(default_factory=list,max_length=32)
    results: list[dict] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    observations: list[dict] = Field(default_factory=list)
    coverage: dict = Field(default_factory=dict)
    validation: dict = Field(default_factory=dict)
    outcome_results: list[dict] = Field(default_factory=list,max_length=8)
    answer: str = ''
    limitations: list[str] = Field(default_factory=list)
    rounds: int = Field(default=0,ge=0,le=4)
    memory: dict = Field(default_factory=dict)
    assessment: dict = Field(default_factory=dict)
    pending_domains: list[str] = Field(default_factory=list,max_length=8)
    trace: list[str] = Field(default_factory=list)
    engineering_result: ToolResult | None = None
    studio_context: list[dict] = Field(default_factory=list)
    studio_evidence: list[Evidence] = Field(default_factory=list)
    studio_coverage: dict = Field(default_factory=dict)
    studio_answer: str = ''
    role_decision: dict = Field(default_factory=dict)
    investigation: dict = Field(default_factory=dict)
