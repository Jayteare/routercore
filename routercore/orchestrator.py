from __future__ import annotations

from routercore.models import ExecutionPreview, PolicyDecision, RouterOutput


PREVIEW_STEPS = {
    "create_web_app": [
        "Validate app settings",
        "Create web app resource",
        "Configure runtime",
        "Enable diagnostics if requested",
        "Return deployment summary",
    ],
    "create_storage_bucket": [
        "Validate bucket settings",
        "Create storage bucket resource",
        "Apply storage class and access policy",
        "Attach ownership metadata",
        "Return bucket summary",
    ],
    "create_service_account": [
        "Validate identity request",
        "Create service account",
        "Attach team metadata",
        "Apply default least-privilege policy",
        "Return identity summary",
    ],
    "grant_iam_role": [
        "Validate principal, role, and scope",
        "Check blocked role list",
        "Prepare least-privilege IAM grant",
        "Require human confirmation before handoff",
        "Return access-change summary",
    ],
    "create_scheduler_job": [
        "Validate schedule expression",
        "Create scheduler job definition",
        "Attach target workflow",
        "Configure retry and timezone settings",
        "Return scheduler summary",
    ],
}


def create_execution_preview(
    router_output: RouterOutput,
    policy_decision: PolicyDecision,
) -> ExecutionPreview:
    if policy_decision.status not in {"routed", "requires_confirmation"}:
        question = policy_decision.clarifying_question
        message = question or "No execution preview is available for this decision."
        return ExecutionPreview(
            workflow=policy_decision.workflow,
            status=policy_decision.status,
            can_preview=False,
            message=message,
            parameters=router_output.parameters,
        )

    steps = PREVIEW_STEPS.get(policy_decision.workflow or "", [])
    return ExecutionPreview(
        workflow=policy_decision.workflow,
        status=policy_decision.status,
        can_preview=True,
        message="Execution preview only. RouterCore will not execute real cloud or infrastructure actions.",
        steps=steps,
        parameters=router_output.parameters,
        executes_real_actions=False,
    )
