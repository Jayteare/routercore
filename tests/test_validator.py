from routercore.models import RouterOutput
from routercore.policy import evaluate_policy
from routercore.router import FakeRouter
from routercore.validator import validate_route


def test_valid_route_is_accepted_for_preview():
    request = "Create a staging Python web app for the claims team in East US with diagnostics enabled."
    routed = FakeRouter().route(request)
    validation = validate_route(routed)
    decision = evaluate_policy(routed, validation, original_request=request)

    assert routed.workflow == "create_web_app"
    assert validation.valid is True
    assert decision.status == "routed"


def test_missing_required_fields_triggers_clarification():
    request = "Create a Python web app for the finance team."
    routed = FakeRouter().route(request)
    validation = validate_route(routed)
    decision = evaluate_policy(routed, validation, original_request=request)

    assert routed.workflow == "create_web_app"
    assert set(validation.missing_fields) == {"region", "environment"}
    assert decision.status == "needs_clarification"
    assert decision.clarifying_question is not None


def test_low_confidence_triggers_clarification():
    routed = RouterOutput(
        status="needs_clarification",
        workflow=None,
        confidence=0.30,
        candidate_workflows=[],
        parameters={},
    )
    validation = validate_route(routed)
    decision = evaluate_policy(routed, validation, original_request="Set up the thing.")

    assert decision.status == "needs_clarification"


def test_medium_confidence_triggers_confirmation():
    routed = RouterOutput(
        status="requires_confirmation",
        workflow="create_storage_bucket",
        confidence=0.70,
        parameters={
            "bucket_name": "claims-bucket",
            "region": "eastus",
            "environment": "staging",
        },
    )
    validation = validate_route(routed)
    decision = evaluate_policy(routed, validation, original_request="Create a staging bucket in East US.")

    assert validation.valid is True
    assert decision.status == "requires_confirmation"
