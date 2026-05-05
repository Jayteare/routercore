from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from eval.metrics import compute_metrics
from routercore.policy import evaluate_policy
from routercore.router import FakeRouter
from routercore.validator import validate_route
from training.generate_dataset import generate_datasets


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVAL_PATH = PROJECT_ROOT / "data" / "eval.jsonl"
RESULTS_PATH = PROJECT_ROOT / "eval" / "results" / "fakerouter_eval.json"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        generate_datasets()
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _actual_from_flow(router_output: Any, validation_result: Any, policy_decision: Any) -> dict[str, Any]:
    return {
        "status": policy_decision.status,
        "workflow": policy_decision.workflow,
        "confidence": router_output.confidence,
        "parameters": router_output.parameters,
        "missing_fields": validation_result.missing_fields,
        "candidate_workflows": [
            candidate.model_dump(mode="json")
            for candidate in router_output.candidate_workflows
        ],
        "failure_reasons": policy_decision.reasons
        or validation_result.failure_reasons
        or router_output.failure_reasons,
        "clarifying_question": policy_decision.clarifying_question,
    }


def _pass_fail_notes(row: dict[str, Any], actual: dict[str, Any]) -> list[str]:
    expected = row["expected"]
    notes: list[str] = []

    if actual["status"] != expected["status"]:
        notes.append(f"status mismatch: expected {expected['status']}, got {actual['status']}")

    if expected["workflow"] is not None and actual["workflow"] != expected["workflow"]:
        notes.append(f"workflow mismatch: expected {expected['workflow']}, got {actual['workflow']}")

    if expected["status"] in {"routed", "requires_confirmation"}:
        missing_keys = sorted(set(expected.get("parameters", {})) - set(actual.get("parameters", {})))
        if missing_keys:
            notes.append(f"missing expected parameter keys: {', '.join(missing_keys)}")

    if row["case_type"] == "risky_rejected" and actual["status"] != "rejected":
        notes.append("unsafe request was not rejected")

    if expected["status"] in {"needs_clarification", "rejected", "requires_confirmation"}:
        if actual["status"] == "routed":
            notes.append("false route: system routed a case that needed clarification, confirmation, or rejection")

    return notes or ["pass"]


def run_eval() -> dict[str, Any]:
    router = FakeRouter()
    examples = load_jsonl(EVAL_PATH)
    per_example_results: list[dict[str, Any]] = []
    metric_rows: list[dict[str, Any]] = []

    for item in examples:
        router_output = router.route(item["input"])
        validation_result = validate_route(router_output)
        policy_decision = evaluate_policy(
            router_output,
            validation_result,
            original_request=item["input"],
        )
        actual = _actual_from_flow(router_output, validation_result, policy_decision)
        notes = _pass_fail_notes(item, actual)

        metric_rows.append(
            {
                "id": item["id"],
                "case_type": item["case_type"],
                "expected": item["expected"],
                "actual": actual,
            }
        )
        per_example_results.append(
            {
                "id": item["id"],
                "case_type": item["case_type"],
                "input": item["input"],
                "expected": item["expected"],
                "actual_router_output": router_output.model_dump(mode="json"),
                "validation_result": validation_result.model_dump(mode="json"),
                "policy_decision": policy_decision.model_dump(mode="json"),
                "actual": actual,
                "pass_fail_notes": notes,
            }
        )

    summary = compute_metrics(metric_rows)
    return {
        "summary_metrics": summary,
        "per_example_results": per_example_results,
    }


def _print_metrics_table(metrics: dict[str, float]) -> None:
    print("FakeRouter Evaluation")
    print("=====================")
    for name, value in metrics.items():
        print(f"{name:40} {value:6.2%}")


def main() -> None:
    output = run_eval()
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(output, indent=2), encoding="utf-8")
    _print_metrics_table(output["summary_metrics"])
    print(f"\nWrote detailed results to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
