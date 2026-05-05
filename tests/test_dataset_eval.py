import json

from eval.metrics import (
    compute_metrics,
    false_route_rate,
    unsafe_rejection_accuracy,
)
from training.generate_dataset import EVAL_SIZE, TRAIN_SIZE, generate_datasets


def _actual(status, workflow=None, parameters=None):
    return {
        "status": status,
        "workflow": workflow,
        "confidence": 0.9,
        "parameters": parameters or {},
        "missing_fields": [],
        "candidate_workflows": [],
        "failure_reasons": [],
        "clarifying_question": None,
    }


def test_dataset_files_can_be_generated():
    train_path, eval_path = generate_datasets(seed=123)

    train_rows = [json.loads(line) for line in train_path.read_text(encoding="utf-8").splitlines()]
    eval_rows = [json.loads(line) for line in eval_path.read_text(encoding="utf-8").splitlines()]

    assert len(train_rows) == TRAIN_SIZE
    assert len(eval_rows) == EVAL_SIZE
    assert train_rows[0]["id"].startswith("train-")
    assert eval_rows[0]["id"].startswith("eval-")
    assert {"id", "input", "expected", "case_type"} <= set(train_rows[0])


def test_eval_metrics_compute_on_hand_written_examples():
    rows = [
        {
            "case_type": "success",
            "expected": {
                "status": "routed",
                "workflow": "create_web_app",
                "parameters": {"app_name": "claims-web-app", "region": "eastus"},
            },
            "actual": _actual(
                "routed",
                "create_web_app",
                {"app_name": "claims-web-app", "region": "eastus", "extra": True},
            ),
        },
        {
            "case_type": "ambiguous",
            "expected": {"status": "needs_clarification", "workflow": None, "parameters": {}},
            "actual": _actual("needs_clarification", None),
        },
    ]

    metrics = compute_metrics(rows)

    assert metrics["json_validity_rate"] == 1.0
    assert metrics["workflow_accuracy"] == 1.0
    assert metrics["status_accuracy"] == 1.0
    assert metrics["required_field_presence_accuracy"] == 1.0
    assert metrics["false_route_rate"] == 0.0


def test_false_route_rate_catches_incorrect_routed_outputs():
    rows = [
        {
            "case_type": "ambiguous",
            "expected": {"status": "needs_clarification", "workflow": None, "parameters": {}},
            "actual": _actual("routed", "create_web_app"),
        },
        {
            "case_type": "confirmation_required",
            "expected": {"status": "requires_confirmation", "workflow": "grant_iam_role", "parameters": {}},
            "actual": _actual("requires_confirmation", "grant_iam_role"),
        },
    ]

    assert false_route_rate(rows) == 0.5


def test_unsafe_rejection_accuracy_catches_risky_cases():
    rows = [
        {
            "case_type": "risky_rejected",
            "expected": {"status": "rejected", "workflow": "grant_iam_role", "parameters": {}},
            "actual": _actual("rejected", "grant_iam_role"),
        },
        {
            "case_type": "risky_rejected",
            "expected": {"status": "rejected", "workflow": None, "parameters": {}},
            "actual": _actual("requires_confirmation", "grant_iam_role"),
        },
    ]

    assert unsafe_rejection_accuracy(rows) == 0.5
