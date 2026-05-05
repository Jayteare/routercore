from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


WorkflowName = Literal[
    "create_web_app",
    "create_storage_bucket",
    "create_service_account",
    "grant_iam_role",
    "create_scheduler_job",
]

RouteStatus = Literal[
    "routed",
    "needs_clarification",
    "requires_confirmation",
    "rejected",
    "fallback",
]

RiskLevel = Literal["low", "medium", "high"]


class CandidateWorkflow(BaseModel):
    workflow: WorkflowName
    confidence: float = Field(ge=0.0, le=1.0)


class RouterOutput(BaseModel):
    status: RouteStatus
    workflow: WorkflowName | None
    confidence: float = Field(ge=0.0, le=1.0)
    parameters: dict[str, Any] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    candidate_workflows: list[CandidateWorkflow] = Field(default_factory=list)
    failure_reasons: list[str] = Field(default_factory=list)
    clarifying_question: str | None = None


class WorkflowSchema(BaseModel):
    workflow: WorkflowName
    required_fields: list[str] = Field(default_factory=list)
    optional_fields: list[str] = Field(default_factory=list)
    allowed_values: dict[str, list[Any]] = Field(default_factory=dict)
    blocked_values: dict[str, list[Any]] = Field(default_factory=dict)
    risk_level: RiskLevel = "medium"
    requires_confirmation: bool = False


class ValidationResult(BaseModel):
    valid: bool
    workflow: WorkflowName | None
    missing_fields: list[str] = Field(default_factory=list)
    invalid_fields: dict[str, str] = Field(default_factory=dict)
    blocked_fields: dict[str, Any] = Field(default_factory=dict)
    failure_reasons: list[str] = Field(default_factory=list)
    clarifying_question: str | None = None


class PolicyDecision(BaseModel):
    status: RouteStatus
    workflow: WorkflowName | None
    confidence: float = Field(ge=0.0, le=1.0)
    accepted: bool = False
    requires_confirmation: bool = False
    execution_allowed: bool = False
    reasons: list[str] = Field(default_factory=list)
    clarifying_question: str | None = None


class ExecutionPreview(BaseModel):
    workflow: WorkflowName | None
    status: RouteStatus
    can_preview: bool
    message: str
    steps: list[str] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)
    executes_real_actions: bool = False
