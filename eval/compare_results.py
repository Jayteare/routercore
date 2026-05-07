from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS_DIR = PROJECT_ROOT / "eval" / "results"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "docs" / "eval_comparison.md"

METRIC_NAMES = [
    "json_validity_rate",
    "workflow_accuracy",
    "status_accuracy",
    "required_field_presence_accuracy",
    "unsafe_rejection_accuracy",
    "false_route_rate",
]


def load_eval_results(results_dir: Path) -> list[dict[str, Any]]:
    if not results_dir.exists():
        return []

    results: list[dict[str, Any]] = []
    for path in sorted(results_dir.glob("*.json")):
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        metrics = payload.get("summary_metrics", {})
        if not isinstance(metrics, dict):
            continue
        results.append(
            {
                "name": _display_name(path, payload),
                "path": path,
                "metrics": {metric: metrics.get(metric) for metric in METRIC_NAMES},
            }
        )
    return results


def build_markdown_table(results: list[dict[str, Any]]) -> str:
    header = "| Model | " + " | ".join(f"`{metric}`" for metric in METRIC_NAMES) + " |"
    separator = "| --- | " + " | ".join("---:" for _ in METRIC_NAMES) + " |"
    rows = [header, separator]
    for result in results:
        values = [_format_metric(result["metrics"].get(metric)) for metric in METRIC_NAMES]
        rows.append(f"| {result['name']} | " + " | ".join(values) + " |")
    return "\n".join(rows)


def build_interpretation(results: list[dict[str, Any]]) -> str:
    if not results:
        return (
            "## Interpretation\n\n"
            "No eval result JSON files were found. Run one of the evaluation commands first, "
            "then regenerate this comparison report.\n"
        )

    best_extraction = _best_higher(results, "required_field_presence_accuracy")
    safest = _best_safety(results)
    false_route = _false_route_summary(results)
    next_step = _next_improvement(results)

    return (
        "## Interpretation\n\n"
        f"- Best structured extraction: {best_extraction}.\n"
        f"- Safest model: {safest}.\n"
        f"- False route rate: {false_route}.\n"
        f"- Improve next: {next_step}.\n"
    )


def build_report(results: list[dict[str, Any]]) -> str:
    table = build_markdown_table(results) if results else "_No eval result files found._"
    return (
        "# Evaluation Comparison\n\n"
        "This report compares RouterCore eval result artifacts from `eval/results/`.\n\n"
        "## Metrics\n\n"
        f"{table}\n\n"
        f"{build_interpretation(results)}"
    )


def write_report(
    results_dir: Path = DEFAULT_RESULTS_DIR,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> tuple[Path, list[dict[str, Any]], str]:
    results = load_eval_results(results_dir)
    report = build_report(results)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    return output_path, results, report


def _display_name(path: Path, payload: dict[str, Any]) -> str:
    if "model" in payload:
        return str(payload["model"])
    if "adapter" in payload:
        return f"LoRA: {Path(str(payload['adapter'])).name}"
    if path.stem == "fakerouter_eval":
        return "FakeRouter"
    return path.stem


def _format_metric(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.2%}"
    return "n/a"


def _best_higher(results: list[dict[str, Any]], metric: str) -> str:
    scored = [
        result
        for result in results
        if isinstance(result["metrics"].get(metric), (int, float))
    ]
    if not scored:
        return "not available"
    best = max(scored, key=lambda result: result["metrics"][metric])
    return f"{best['name']} ({_format_metric(best['metrics'][metric])})"


def _best_lower(results: list[dict[str, Any]], metric: str) -> str:
    scored = [
        result
        for result in results
        if isinstance(result["metrics"].get(metric), (int, float))
    ]
    if not scored:
        return "not available"
    best = min(scored, key=lambda result: result["metrics"][metric])
    best_value = best["metrics"][metric]
    tied = [result for result in scored if result["metrics"][metric] == best_value]
    names = ", ".join(result["name"] for result in tied)
    return f"{names} ({_format_metric(best_value)})"


def _best_safety(results: list[dict[str, Any]]) -> str:
    scored = [
        result
        for result in results
        if isinstance(result["metrics"].get("unsafe_rejection_accuracy"), (int, float))
        and isinstance(result["metrics"].get("false_route_rate"), (int, float))
    ]
    if not scored:
        return "not available"
    best = max(
        scored,
        key=lambda result: (
            result["metrics"]["unsafe_rejection_accuracy"],
            -result["metrics"]["false_route_rate"],
        ),
    )
    best_unsafe = best["metrics"]["unsafe_rejection_accuracy"]
    best_false_route = best["metrics"]["false_route_rate"]
    tied = [
        result
        for result in scored
        if result["metrics"]["unsafe_rejection_accuracy"] == best_unsafe
        and result["metrics"]["false_route_rate"] == best_false_route
    ]
    names = ", ".join(result["name"] for result in tied)
    label = "models" if len(tied) > 1 else "model"
    return (
        f"{names} "
        f"({label}; unsafe rejection {_format_metric(best_unsafe)}, "
        f"false route {_format_metric(best_false_route)})"
    )


def _false_route_summary(results: list[dict[str, Any]]) -> str:
    best = _best_lower(results, "false_route_rate")
    worst_rows = [
        result
        for result in results
        if isinstance(result["metrics"].get("false_route_rate"), (int, float))
        and result["metrics"]["false_route_rate"] > 0
    ]
    if not worst_rows:
        return f"remained low across available results; best is {best}"
    worst = max(worst_rows, key=lambda result: result["metrics"]["false_route_rate"])
    return (
        f"best is {best}; highest observed is {worst['name']} "
        f"({_format_metric(worst['metrics']['false_route_rate'])})"
    )


def _next_improvement(results: list[dict[str, Any]]) -> str:
    scored = [
        result
        for result in results
        if isinstance(result["metrics"].get("unsafe_rejection_accuracy"), (int, float))
        and isinstance(result["metrics"].get("false_route_rate"), (int, float))
        and isinstance(result["metrics"].get("required_field_presence_accuracy"), (int, float))
    ]
    if not scored:
        return "run at least one evaluation to identify the weakest metric"

    safe_candidates = [
        result
        for result in scored
        if result["metrics"]["unsafe_rejection_accuracy"] == 1.0
        and result["metrics"]["false_route_rate"] == 0.0
    ]
    candidates = safe_candidates or scored
    reference = max(
        candidates,
        key=lambda result: result["metrics"]["required_field_presence_accuracy"],
    )

    weaknesses = {
        "workflow_accuracy": "workflow classification",
        "status_accuracy": "status classification",
        "required_field_presence_accuracy": "structured parameter extraction",
        "unsafe_rejection_accuracy": "unsafe request rejection",
    }
    lowest_metric = min(
        weaknesses,
        key=lambda metric: reference["metrics"].get(metric, 1.0),
    )
    if reference["metrics"].get("false_route_rate", 0.0) > 0:
        return "reduce false routes before optimizing convenience metrics"
    return weaknesses[lowest_metric]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare RouterCore evaluation result JSON files.")
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path, results, report = write_report(args.results_dir, args.output)
    print(report)
    print(f"\nWrote comparison report to {output_path}")
    if not results:
        print("No result files were found.")


if __name__ == "__main__":
    main()
