from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from eval.metrics import compute_metrics
from eval.run_eval import EVAL_PATH, _actual_from_flow, _pass_fail_notes, load_jsonl
from routercore.model_router import extract_first_json_object
from routercore.models import RouterOutput
from routercore.policy import evaluate_policy
from routercore.validator import validate_route
from training.format_dataset import build_inference_prompt
from training.train_lora import OptionalTrainingDependencyError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "eval" / "results"


def load_lora_dependencies():
    try:
        import torch
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        raise OptionalTrainingDependencyError(
            "Optional LoRA eval dependencies are unavailable. Install transformers, peft, and torch."
        ) from exc
    return {
        "torch": torch,
        "PeftModel": PeftModel,
        "AutoModelForCausalLM": AutoModelForCausalLM,
        "AutoTokenizer": AutoTokenizer,
    }


def _safe_adapter_name(adapter: Path) -> str:
    name = adapter.name or str(adapter)
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")
    return safe or "adapter"


class LoraRouter:
    def __init__(
        self,
        *,
        base_model: str,
        adapter: Path,
        device: str = "auto",
        max_new_tokens: int = 512,
    ) -> None:
        deps = load_lora_dependencies()
        self.torch = deps["torch"]
        PeftModel = deps["PeftModel"]
        AutoModelForCausalLM = deps["AutoModelForCausalLM"]
        AutoTokenizer = deps["AutoTokenizer"]

        self.max_new_tokens = max_new_tokens
        self.device = self._resolve_device(device)
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(adapter if adapter.exists() else base_model)
        except Exception:
            self.tokenizer = AutoTokenizer.from_pretrained(base_model)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        base = AutoModelForCausalLM.from_pretrained(base_model)
        self.model = PeftModel.from_pretrained(base, adapter)
        self.model.to(self.device)
        self.model.eval()

    def route(self, request_text: str) -> RouterOutput:
        prompt = build_inference_prompt(request_text)
        encoded = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        with self.torch.no_grad():
            output_ids = self.model.generate(
                **encoded,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        input_length = encoded["input_ids"].shape[-1]
        raw_text = self.tokenizer.decode(output_ids[0][input_length:], skip_special_tokens=True)
        parsed = extract_first_json_object(raw_text)
        if parsed is None:
            return self._fallback("model_output_parse_failed")
        try:
            return RouterOutput.model_validate(parsed)
        except (ValidationError, ValueError, TypeError):
            return self._fallback("model_output_parse_failed")

    def _resolve_device(self, device: str) -> str:
        if device == "auto":
            return "cuda" if self.torch.cuda.is_available() else "cpu"
        if device == "cuda" and not self.torch.cuda.is_available():
            return "cpu"
        return device

    @staticmethod
    def _fallback(reason: str) -> RouterOutput:
        return RouterOutput(
            status="fallback",
            workflow=None,
            confidence=0.0,
            parameters={},
            missing_fields=[],
            candidate_workflows=[],
            failure_reasons=[reason],
            clarifying_question=None,
        )


def run_lora_eval(
    *,
    base_model: str,
    adapter: Path,
    limit: int | None = None,
    device: str = "auto",
) -> dict[str, Any]:
    router = LoraRouter(base_model=base_model, adapter=adapter, device=device)
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
        "base_model": base_model,
        "adapter": str(adapter),
        "limit": limit,
        "summary_metrics": compute_metrics(metric_rows),
        "per_example_results": per_example_results,
    }


def _print_metrics_table(adapter: Path, metrics: dict[str, float]) -> None:
    print(f"LoRA Evaluation: {adapter}")
    print("=" * (17 + len(str(adapter))))
    for name, value in metrics.items():
        print(f"{name:40} {value:6.2%}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate a RouterCore LoRA adapter.")
    parser.add_argument("--base-model", required=True)
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        output = run_lora_eval(
            base_model=args.base_model,
            adapter=args.adapter,
            limit=args.limit,
            device=args.device,
        )
    except OptionalTrainingDependencyError as exc:
        print(str(exc))
        print("Skipping LoRA evaluation. Run `pip install transformers peft torch` to enable it.")
        return

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RESULTS_DIR / f"lora_eval_{_safe_adapter_name(args.adapter)}.json"
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    _print_metrics_table(args.adapter, output["summary_metrics"])
    print(f"\nWrote detailed results to {output_path}")


if __name__ == "__main__":
    main()
