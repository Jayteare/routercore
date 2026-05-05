from __future__ import annotations

from routercore.models import PolicyDecision, RouterOutput, ValidationResult
from routercore.schemas import get_workflow_schema


UNSAFE_PHRASES = [
    "delete all production",
    "disable monitoring",
    "grant owner",
    "grant admin",
    "remove all security",
]

BROAD_SCOPE_MARKERS = [
    "*",
    "all",
    "organization",
    "org",
    "subscription",
    "tenant",
    "production",
    "prod",
]


def _contains_unsafe_phrase(request_text: str) -> list[str]:
    lowered = request_text.lower()
    return [phrase for phrase in UNSAFE_PHRASES if phrase in lowered]


def _is_broad_scope(value: object) -> bool:
    if value is None:
        return False
    lowered = str(value).lower()
    return any(marker in lowered for marker in BROAD_SCOPE_MARKERS)


def evaluate_policy(
    router_output: RouterOutput,
    validation_result: ValidationResult,
    original_request: str = "",
) -> PolicyDecision:
    workflow_schema = get_workflow_schema(router_output.workflow)
    reasons: list[str] = []

    unsafe_matches = _contains_unsafe_phrase(original_request)
    if unsafe_matches:
        return PolicyDecision(
            status="rejected",
            workflow=router_output.workflow,
            confidence=router_output.confidence,
            reasons=[f"Unsafe phrase matched: {phrase}" for phrase in unsafe_matches],
        )

    if validation_result.blocked_fields:
        return PolicyDecision(
            status="rejected",
            workflow=router_output.workflow,
            confidence=router_output.confidence,
            reasons=[
                f"Blocked value for {field}: {value}"
                for field, value in validation_result.blocked_fields.items()
            ],
        )

    if router_output.workflow is None or workflow_schema is None:
        if router_output.candidate_workflows or router_output.confidence < 0.55:
            return PolicyDecision(
                status="needs_clarification",
                workflow=None,
                confidence=router_output.confidence,
                reasons=["No authoritative workflow could be selected."],
                clarifying_question=router_output.clarifying_question
                or validation_result.clarifying_question
                or "Can you clarify which workflow you want?",
            )
        return PolicyDecision(
            status="rejected",
            workflow=None,
            confidence=router_output.confidence,
            reasons=["Unknown or unsupported workflow."],
        )

    if validation_result.missing_fields:
        return PolicyDecision(
            status="needs_clarification",
            workflow=router_output.workflow,
            confidence=router_output.confidence,
            reasons=validation_result.failure_reasons,
            clarifying_question=validation_result.clarifying_question,
        )

    if validation_result.invalid_fields:
        return PolicyDecision(
            status="needs_clarification",
            workflow=router_output.workflow,
            confidence=router_output.confidence,
            reasons=validation_result.failure_reasons,
            clarifying_question="Please provide valid values for the highlighted fields.",
        )

    if router_output.confidence < 0.55:
        return PolicyDecision(
            status="needs_clarification",
            workflow=router_output.workflow,
            confidence=router_output.confidence,
            reasons=["Router confidence is below 0.55."],
            clarifying_question=router_output.clarifying_question
            or "Can you clarify what you want RouterCore to set up?",
        )

    if router_output.confidence < 0.80:
        reasons.append("Router confidence is between 0.55 and 0.80.")

    if workflow_schema.risk_level == "high" or workflow_schema.requires_confirmation:
        reasons.append("Workflow is high risk and requires human confirmation.")

    if router_output.workflow == "grant_iam_role":
        environment = router_output.parameters.get("environment")
        scope = router_output.parameters.get("scope")
        if environment == "prod" or _is_broad_scope(scope):
            reasons.append("IAM request targets production or broad-scope permissions.")

    if reasons:
        return PolicyDecision(
            status="requires_confirmation",
            workflow=router_output.workflow,
            confidence=router_output.confidence,
            requires_confirmation=True,
            reasons=reasons,
        )

    return PolicyDecision(
        status="routed",
        workflow=router_output.workflow,
        confidence=router_output.confidence,
        accepted=True,
        execution_allowed=False,
        reasons=["Route accepted for execution preview only."],
    )
