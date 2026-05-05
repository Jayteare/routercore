from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from eval.metrics import compute_metrics
from eval.run_eval import EVAL_PATH, _actual_from_flow, _pass_fail_notes, load_jsonl
from routercore.model_router import ModelRouter, OptionalModelDependencyError
from routercore.policy import evaluate_policy
from routercore.validator import validate_route


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "eval" / "results"


def _safe_model_name(model_name: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", model_name).strip("_")
    return safe or "model"


def run_model_eval(
    *,
    model_name_or_path: str,
    limit: int | None = None,
    device: str = "auto",
) -> dict[str, Any]:
    router = ModelRouter(model_name_or_path, device=device)
    examples = load_jsonl(EVAL_PATH)
    if limit is not None:
        examples = examples[:limit]

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

    return {
        "model": model_name_or_path,
        "limit": limit,
        "summary_metrics": compute_metrics(metric_rows),
        "per_example_results": per_example_results,
    }


def _print_metrics_table(model_name: str, metrics: dict[str, float]) -> None:
    print(f"Prompted Model Evaluation: {model_name}")
    print("=" * (28 + len(model_name)))
    for name, value in metrics.items():
        print(f"{name:40} {value:6.2%}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate a local Hugging Face causal LM router baseline.")
    parser.add_argument("--model", required=True, help="Hugging Face model name or local model path.")
    parser.add_argument("--limit", type=int, default=None, help="Optional number of eval rows for a smoke test.")
    parser.add_argument(
        "--device",
        choices=["auto", "cpu", "cuda"],
        default="auto",
        help="Device for local model inference. Defaults to auto.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        output = run_model_eval(
            model_name_or_path=args.model,
            limit=args.limit,
            device=args.device,
        )
    except OptionalModelDependencyError as exc:
        print(str(exc))
        print("Skipping prompted model evaluation. Run `pip install transformers torch` to enable it.")
        return

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RESULTS_DIR / f"model_eval_{_safe_model_name(args.model)}.json"
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")

    _print_metrics_table(args.model, output["summary_metrics"])
    print(f"\nWrote detailed results to {output_path}")


if __name__ == "__main__":
    main()
