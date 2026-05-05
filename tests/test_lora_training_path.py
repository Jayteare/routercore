import builtins
import json

import pytest

from eval.run_lora_eval import load_lora_dependencies
from training.format_dataset import build_inference_prompt, format_dataset
from training.inference_lora import load_inference_dependencies
from training.train_lora import OptionalTrainingDependencyError, load_training_dependencies


def _write_jsonl(path, rows):
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_format_dataset_creates_instruction_files_from_sample_input(tmp_path):
    train_input = tmp_path / "train.jsonl"
    eval_input = tmp_path / "eval.jsonl"
    train_output = tmp_path / "routercore_train_instruct.jsonl"
    eval_output = tmp_path / "routercore_eval_instruct.jsonl"
    sample = {
        "id": "train-0001",
        "input": "Create a staging Python web app for claims in East US.",
        "expected": {
            "status": "routed",
            "workflow": "create_web_app",
            "confidence": 0.9,
            "parameters": {"app_name": "claims-web-app"},
            "missing_fields": [],
            "candidate_workflows": [],
            "failure_reasons": [],
            "clarifying_question": None,
        },
        "case_type": "success",
    }
    _write_jsonl(train_input, [sample])
    _write_jsonl(eval_input, [{**sample, "id": "eval-0001"}])

    format_dataset(train_input, eval_input, train_output, eval_output)

    train_row = json.loads(train_output.read_text(encoding="utf-8").splitlines()[0])
    eval_row = json.loads(eval_output.read_text(encoding="utf-8").splitlines()[0])

    assert train_row["id"] == "train-0001"
    assert "RouterCore JSON:" in train_row["text"]
    assert '"workflow": "create_web_app"' in train_row["text"]
    assert eval_row["id"] == "eval-0001"


def test_inference_prompt_builder_excludes_expected_json():
    prompt = build_inference_prompt("Create a staging Python web app for claims in East US.")

    assert "User request:" in prompt
    assert "RouterCore JSON:" in prompt
    assert "Create a staging Python web app" in prompt
    assert '"workflow": "create_web_app"' not in prompt
    assert prompt.rstrip().endswith("RouterCore JSON:")


def test_training_dependency_loader_fails_gracefully_without_optional_deps(monkeypatch):
    _patch_missing_optional_deps(monkeypatch)

    with pytest.raises(OptionalTrainingDependencyError):
        load_training_dependencies()


def test_inference_dependency_loader_fails_gracefully_without_optional_deps(monkeypatch):
    _patch_missing_optional_deps(monkeypatch)

    with pytest.raises(OptionalTrainingDependencyError):
        load_inference_dependencies()


def test_lora_eval_dependency_loader_fails_gracefully_without_optional_deps(monkeypatch):
    _patch_missing_optional_deps(monkeypatch)

    with pytest.raises(OptionalTrainingDependencyError):
        load_lora_dependencies()


def _patch_missing_optional_deps(monkeypatch):
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name in {"torch", "transformers", "datasets", "peft"}:
            raise ImportError(name)
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
