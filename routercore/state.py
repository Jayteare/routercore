from __future__ import annotations

from pydantic import BaseModel, Field

from routercore.models import PolicyDecision, RouterOutput, ValidationResult
from routercore.orchestrator import create_execution_preview
from routercore.policy import evaluate_policy
from routercore.router import FakeRouter
from routercore.validator import validate_route


class SessionState(BaseModel):
    original_request: str | None = None
    accumulated_context: list[str] = Field(default_factory=list)
    attempt_count: int = 0
    last_router_output: RouterOutput | None = None
    last_validation_result: ValidationResult | None = None
    last_policy_decision: PolicyDecision | None = None
    current_state: str = "idle"


class RouterCoreSession:
    def __init__(self, router: FakeRouter | None = None, state: SessionState | None = None):
        self.router = router or FakeRouter()
        self.state = state or SessionState()

    def route(self, request_text: str):
        self.state = SessionState(original_request=request_text.strip(), attempt_count=0)
        return self._run(request_text)

    def continue_with_clarification(self, answer: str):
        if not self.state.original_request:
            return self.route(answer)
        self.state.accumulated_context.append(answer.strip())
        combined = " ".join([self.state.original_request, *self.state.accumulated_context])
        return self._run(combined)

    def _run(self, request_text: str):
        self.state.attempt_count += 1
        router_output = self.router.route(request_text)
        validation_result = validate_route(router_output)
        policy_decision = evaluate_policy(
            router_output,
            validation_result,
            original_request=request_text,
        )
        preview = create_execution_preview(router_output, policy_decision)

        self.state.last_router_output = router_output
        self.state.last_validation_result = validation_result
        self.state.last_policy_decision = policy_decision
        self.state.current_state = policy_decision.status
        return router_output, validation_result, policy_decision, preview, self.state
