from routercore.policy import evaluate_policy
from routercore.router import FakeRouter
from routercore.validator import validate_route


def test_blocked_iam_owner_role_gets_rejected():
    request = "Grant John owner access to production."
    routed = FakeRouter().route(request)
    validation = validate_route(routed)
    decision = evaluate_policy(routed, validation, original_request=request)

    assert routed.workflow == "grant_iam_role"
    assert validation.blocked_fields == {"role": "owner"}
    assert decision.status == "rejected"


def test_blocked_iam_admin_role_gets_rejected():
    request = "Grant Jane admin access to production."
    routed = FakeRouter().route(request)
    validation = validate_route(routed)
    decision = evaluate_policy(routed, validation, original_request=request)

    assert validation.blocked_fields == {"role": "admin"}
    assert decision.status == "rejected"


def test_destructive_production_request_gets_rejected():
    request = "Delete all production services and disable monitoring."
    routed = FakeRouter().route(request)
    validation = validate_route(routed)
    decision = evaluate_policy(routed, validation, original_request=request)

    assert decision.status == "rejected"
    assert any("Unsafe phrase matched" in reason for reason in decision.reasons)
