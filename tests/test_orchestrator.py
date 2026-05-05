from routercore.orchestrator import create_execution_preview
from routercore.policy import evaluate_policy
from routercore.router import FakeRouter
from routercore.validator import validate_route


def test_orchestrator_preview_returns_steps_but_executes_nothing():
    request = "Create a staging Python web app for the claims team in East US with diagnostics enabled."
    routed = FakeRouter().route(request)
    validation = validate_route(routed)
    decision = evaluate_policy(routed, validation, original_request=request)
    preview = create_execution_preview(routed, decision)

    assert preview.can_preview is True
    assert preview.steps
    assert preview.executes_real_actions is False
    assert "Create web app resource" in preview.steps
