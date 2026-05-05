from __future__ import annotations

import argparse
from pathlib import Path


class OptionalTrainingDependencyError(RuntimeError):
    """Raised when optional LoRA training dependencies are not installed."""


def load_training_dependencies():
    try:
        import torch
        from datasets import load_dataset
        from peft import LoraConfig, get_peft_model
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            DataCollatorForLanguageModeling,
            Trainer,
            TrainingArguments,
        )
    except ImportError as exc:
        raise OptionalTrainingDependencyError(
            "Optional training dependencies are unavailable. Install transformers, datasets, peft, and torch."
        ) from exc

    return {
        "torch": torch,
        "load_dataset": load_dataset,
        "LoraConfig": LoraConfig,
        "get_peft_model": get_peft_model,
        "AutoModelForCausalLM": AutoModelForCausalLM,
        "AutoTokenizer": AutoTokenizer,
        "DataCollatorForLanguageModeling": DataCollatorForLanguageModeling,
        "Trainer": Trainer,
        "TrainingArguments": TrainingArguments,
    }


def find_lora_target_modules(model, preferred_targets: list[str]) -> list[str]:
    module_suffixes = {name.split(".")[-1] for name, _ in model.named_modules()}
    return [target for target in preferred_targets if target in module_suffixes]


def train_lora(args: argparse.Namespace) -> None:
    deps = load_training_dependencies()
    torch = deps["torch"]
    load_dataset = deps["load_dataset"]
    LoraConfig = deps["LoraConfig"]
    get_peft_model = deps["get_peft_model"]
    AutoModelForCausalLM = deps["AutoModelForCausalLM"]
    AutoTokenizer = deps["AutoTokenizer"]
    DataCollatorForLanguageModeling = deps["DataCollatorForLanguageModeling"]
    Trainer = deps["Trainer"]
    TrainingArguments = deps["TrainingArguments"]

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(args.model)
    model.config.pad_token_id = tokenizer.pad_token_id

    preferred_targets = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
    target_modules = find_lora_target_modules(model, preferred_targets)
    if not target_modules:
        raise ValueError(
            "No common LoRA target modules were found. Expected one of: "
            f"{', '.join(preferred_targets)}. Inspect the model architecture and set compatible targets."
        )

    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=target_modules,
    )
    model = get_peft_model(model, lora_config)
    if hasattr(model, "print_trainable_parameters"):
        model.print_trainable_parameters()

    dataset = load_dataset(
        "json",
        data_files={"train": str(args.train_file), "eval": str(args.eval_file)},
    )

    def tokenize_batch(batch):
        tokenized = tokenizer(
            batch["text"],
            truncation=True,
            max_length=args.max_seq_length,
            padding=False,
        )
        return tokenized

    tokenized_dataset = dataset.map(
        tokenize_batch,
        batched=True,
        remove_columns=dataset["train"].column_names,
    )

    training_args = TrainingArguments(
        output_dir=str(args.output_dir),
        max_steps=args.max_steps,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        logging_steps=args.logging_steps,
        save_steps=args.max_steps,
        report_to=[],
        remove_unused_columns=False,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset["train"],
        eval_dataset=tokenized_dataset["eval"],
        data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False),
    )
    trainer.train()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    trainer.model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)

    device_name = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Saved LoRA adapter and tokenizer to {args.output_dir}")
    print(f"Training device detected by torch: {device_name}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fine-tune a RouterCore LoRA adapter.")
    parser.add_argument("--model", required=True, help="Base Hugging Face model name or path.")
    parser.add_argument("--train-file", type=Path, required=True)
    parser.add_argument("--eval-file", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-steps", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--max-seq-length", type=int, default=1024)
    parser.add_argument("--logging-steps", type=int, default=10)
    parser.add_argument("--lora-r", type=int, default=8)
    parser.add_argument("--lora-alpha", type=int, default=16)
    parser.add_argument("--lora-dropout", type=float, default=0.05)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        train_lora(args)
    except OptionalTrainingDependencyError as exc:
        print(str(exc))
        print("Skipping LoRA training. Run `pip install transformers datasets peft torch` to enable it.")
    except ValueError as exc:
        print(f"LoRA training configuration error: {exc}")
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
