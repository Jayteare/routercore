from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRAIN_INPUT = PROJECT_ROOT / "data" / "train.jsonl"
DEFAULT_EVAL_INPUT = PROJECT_ROOT / "data" / "eval.jsonl"
DEFAULT_TRAIN_OUTPUT = PROJECT_ROOT / "data" / "routercore_train_instruct.jsonl"
DEFAULT_EVAL_OUTPUT = PROJECT_ROOT / "data" / "routercore_eval_instruct.jsonl"

SYSTEM_PROMPT = """You are RouterCore, a routing model for DevOps agent workflows.
Return only valid JSON matching the RouterCore schema.
Do not include markdown, explanations, or code fences.

Allowed statuses:
routed, needs_clarification, requires_confirmation, rejected, fallback

Allowed workflows:
create_web_app, create_storage_bucket, create_service_account, grant_iam_role, create_scheduler_job

Required JSON fields:
status, workflow, confidence, parameters, missing_fields, candidate_workflows, failure_reasons, clarifying_question"""


def build_inference_prompt(user_request: str) -> str:
    return f"""{SYSTEM_PROMPT}

User request:
{user_request}

RouterCore JSON:
"""


def build_training_prompt(user_request: str, expected: dict[str, Any]) -> str:
    expected_json = json.dumps(expected, sort_keys=True)
    return f"{build_inference_prompt(user_request)}{expected_json}"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(row, sort_keys=True) for row in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def format_rows(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "id": row["id"],
            "text": build_training_prompt(row["input"], row["expected"]),
        }
        for row in rows
    ]


def format_dataset(
    train_input: Path = DEFAULT_TRAIN_INPUT,
    eval_input: Path = DEFAULT_EVAL_INPUT,
    train_output: Path = DEFAULT_TRAIN_OUTPUT,
    eval_output: Path = DEFAULT_EVAL_OUTPUT,
) -> tuple[Path, Path]:
    train_rows = format_rows(load_jsonl(train_input))
    eval_rows = format_rows(load_jsonl(eval_input))
    write_jsonl(train_output, train_rows)
    write_jsonl(eval_output, eval_rows)
    return train_output, eval_output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Format RouterCore JSONL data for causal-LM instruction tuning.")
    parser.add_argument("--train-input", type=Path, default=DEFAULT_TRAIN_INPUT)
    parser.add_argument("--eval-input", type=Path, default=DEFAULT_EVAL_INPUT)
    parser.add_argument("--train-output", type=Path, default=DEFAULT_TRAIN_OUTPUT)
    parser.add_argument("--eval-output", type=Path, default=DEFAULT_EVAL_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    train_output, eval_output = format_dataset(
        train_input=args.train_input,
        eval_input=args.eval_input,
        train_output=args.train_output,
        eval_output=args.eval_output,
    )
    print(f"Wrote instruction train data to {train_output}")
    print(f"Wrote instruction eval data to {eval_output}")


if __name__ == "__main__":
    main()
