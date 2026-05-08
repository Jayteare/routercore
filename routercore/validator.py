from __future__ import annotations

from typing import Any

from routercore.models import RouterOutput, ValidationResult, WorkflowSchema
from routercore.schemas import get_workflow_schema


def _is_missing(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _matches_configured_value(value: Any, allowed_or_blocked: list[Any]) -> bool:
    if isinstance(value, str):
        return value.lower() in {str(item).lower() for item in allowed_or_blocked}
    return value in allowed_or_blocked


def _targeted_question(missing_fields: list[str], schema: WorkflowSchema) -> str | None:
    if not missing_fields:
        return None
    field = missing_fields[0]
    readable = field.replace("_", " ")
    allowed_values = schema.allowed_values.get(field)
    if allowed_values:
        allowed = ", ".join(str(value) for value in allowed_values)
        return f"What {readable} should RouterCore use? Allowed values: {allowed}."
    return f"What {readable} should RouterCore use?"


def validate_route(
    router_output: RouterOutput,
    schema: WorkflowSchema | None = None,
) -> ValidationResult:
    workflow_schema = schema or get_workflow_schema(router_output.workflow)
    if router_output.workflow is None:
        return ValidationResult(
            valid=False,
            workflow=None,
            failure_reasons=["Router did not select a workflow."],
            clarifying_question="Which workflow should this request use?",
        )

    if workflow_schema is None:
        return ValidationResult(
            valid=False,
            workflow=None,
            failure_reasons=[f"Unknown workflow: {router_output.workflow}"],
        )

    params = router_output.parameters
    missing_fields = [
        field
        for field in workflow_schema.required_fields
        if field not in params or _is_missing(params[field])
    ]

    invalid_fields: dict[str, str] = {}
    for field, allowed_values in workflow_schema.allowed_values.items():
        if field in params and not _is_missing(params[field]):
            if not _matches_configured_value(params[field], allowed_values):
                invalid_fields[field] = (
                    f"Value {params[field]!r} is not allowed. "
                    f"Allowed values: {allowed_values}"
                )

    blocked_fields: dict[str, Any] = {}
    for field, blocked_values in workflow_schema.blocked_values.items():
        if field in params and _matches_configured_value(params[field], blocked_values):
            blocked_fields[field] = params[field]

    failure_reasons: list[str] = []
    if missing_fields:
        failure_reasons.append(f"Missing required fields: {', '.join(missing_fields)}")
    if invalid_fields:
        failure_reasons.append("One or more fields failed allowed-value validation.")
    if blocked_fields:
        failure_reasons.append("One or more fields contains a blocked value.")

    return ValidationResult(
        valid=not (missing_fields or invalid_fields or blocked_fields),
        workflow=workflow_schema.workflow,
        missing_fields=missing_fields,
        invalid_fields=invalid_fields,
        blocked_fields=blocked_fields,
        failure_reasons=failure_reasons,
        clarifying_question=_targeted_question(missing_fields, workflow_schema),
    )
