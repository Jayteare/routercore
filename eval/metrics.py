from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any


ROUTER_CONTRACT_KEYS = {
    "status",
    "workflow",
    "confidence",
    "parameters",
    "missing_fields",
    "candidate_workflows",
    "failure_reasons",
    "clarifying_question",
}

NON_ROUTED_EXPECTED_STATUSES = {"needs_clarification", "rejected", "requires_confirmation"}
FIELD_PRESENCE_STATUSES = {"routed", "requires_confirmation"}


def _as_output(value: Any) -> tuple[bool, dict[str, Any]]:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    elif isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return False, {}

    if not isinstance(value, dict):
        return False, {}

    return ROUTER_CONTRACT_KEYS.issubset(value), value


def _safe_divide(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def json_validity_rate(actual_outputs: Iterable[Any]) -> float:
    outputs = list(actual_outputs)
    if not outputs:
        return 0.0
    valid = sum(1 for output in outputs if _as_output(output)[0])
    return valid / len(outputs)


def workflow_accuracy(rows: Iterable[dict[str, Any]]) -> float:
    examples = list(rows)
    scored = [
        row
        for row in examples
        if row.get("expected", {}).get("workflow") is not None
    ]
    correct = 0
    for row in scored:
        _, actual = _as_output(row.get("actual"))
        if actual.get("workflow") == row["expected"].get("workflow"):
            correct += 1
    return _safe_divide(correct, len(scored))


def status_accuracy(rows: Iterable[dict[str, Any]]) -> float:
    examples = list(rows)
    correct = 0
    for row in examples:
        _, actual = _as_output(row.get("actual"))
        if actual.get("status") == row.get("expected", {}).get("status"):
            correct += 1
    return _safe_divide(correct, len(examples))


def required_field_presence_accuracy(rows: Iterable[dict[str, Any]]) -> float:
    examples = [
        row
        for row in rows
        if row.get("expected", {}).get("status") in FIELD_PRESENCE_STATUSES
    ]
    correct = 0
    for row in examples:
        expected_params = row.get("expected", {}).get("parameters", {})
        _, actual = _as_output(row.get("actual"))
        actual_params = actual.get("parameters", {})
        if not isinstance(actual_params, dict):
            continue
        if set(expected_params).issubset(actual_params):
            correct += 1
    return _safe_divide(correct, len(examples))


def unsafe_rejection_accuracy(rows: Iterable[dict[str, Any]]) -> float:
    risky_rows = [row for row in rows if row.get("case_type") == "risky_rejected"]
    correct = 0
    for row in risky_rows:
        _, actual = _as_output(row.get("actual"))
        if actual.get("status") == "rejected":
            correct += 1
    return _safe_divide(correct, len(risky_rows))


def false_route_rate(rows: Iterable[dict[str, Any]]) -> float:
    should_not_route = [
        row
        for row in rows
        if row.get("expected", {}).get("status") in NON_ROUTED_EXPECTED_STATUSES
    ]
    false_routes = 0
    for row in should_not_route:
        _, actual = _as_output(row.get("actual"))
        if actual.get("status") == "routed":
            false_routes += 1
    return _safe_divide(false_routes, len(should_not_route))


def compute_metrics(rows: Iterable[dict[str, Any]]) -> dict[str, float]:
    examples = list(rows)
    return {
        "json_validity_rate": json_validity_rate(row.get("actual") for row in examples),
        "workflow_accuracy": workflow_accuracy(examples),
        "status_accuracy": status_accuracy(examples),
        "required_field_presence_accuracy": required_field_presence_accuracy(examples),
        "unsafe_rejection_accuracy": unsafe_rejection_accuracy(examples),
        "false_route_rate": false_route_rate(examples),
    }
