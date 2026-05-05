from __future__ import annotations

import argparse
import json
from pathlib import Path

from routercore.model_router import extract_first_json_object
from training.format_dataset import build_inference_prompt
from training.train_lora import OptionalTrainingDependencyError


def load_inference_dependencies():
    try:
        import torch
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        raise OptionalTrainingDependencyError(
            "Optional inference dependencies are unavailable. Install transformers, peft, and torch."
        ) from exc
    return {
        "torch": torch,
        "PeftModel": PeftModel,
        "AutoModelForCausalLM": AutoModelForCausalLM,
        "AutoTokenizer": AutoTokenizer,
    }


def run_lora_inference(
    *,
    base_model: str,
    adapter: Path,
    user_input: str,
    max_new_tokens: int,
) -> str:
    deps = load_inference_dependencies()
    torch = deps["torch"]
    PeftModel = deps["PeftModel"]
    AutoModelForCausalLM = deps["AutoModelForCausalLM"]
    AutoTokenizer = deps["AutoTokenizer"]

    device = "cuda" if torch.cuda.is_available() else "cpu"
    try:
        tokenizer = AutoTokenizer.from_pretrained(adapter if adapter.exists() else base_model)
    except Exception:
        tokenizer = AutoTokenizer.from_pretrained(base_model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(base_model)
    model = PeftModel.from_pretrained(model, adapter)
    model.to(device)
    model.eval()

    prompt = build_inference_prompt(user_input)
    encoded = tokenizer(prompt, return_tensors="pt").to(device)
    with torch.no_grad():
        output_ids = model.generate(
            **encoded,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    input_length = encoded["input_ids"].shape[-1]
    return tokenizer.decode(output_ids[0][input_length:], skip_special_tokens=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run inference with a RouterCore LoRA adapter.")
    parser.add_argument("--base-model", required=True)
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--max-new-tokens", type=int, default=512)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        raw_output = run_lora_inference(
            base_model=args.base_model,
            adapter=args.adapter,
            user_input=args.input,
            max_new_tokens=args.max_new_tokens,
        )
    except OptionalTrainingDependencyError as exc:
        print(str(exc))
        print("Skipping LoRA inference. Run `pip install transformers peft torch` to enable it.")
        return

    print("Raw model output:")
    print(raw_output)
    parsed = extract_first_json_object(raw_output)
    print("\nParsed JSON:")
    if parsed is None:
        print("Parse failed: no valid JSON object found.")
    else:
        print(json.dumps(parsed, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
