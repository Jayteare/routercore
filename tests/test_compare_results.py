import json

from eval.compare_results import build_markdown_table, load_eval_results, write_report


def _write_result(path, metrics, **metadata):
    payload = {
        **metadata,
        "summary_metrics": metrics,
        "per_example_results": [],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _metrics(**overrides):
    values = {
        "json_validity_rate": 1.0,
        "workflow_accuracy": 0.8,
        "status_accuracy": 0.7,
        "required_field_presence_accuracy": 0.6,
        "unsafe_rejection_accuracy": 1.0,
        "false_route_rate": 0.0,
    }
    values.update(overrides)
    return values


def test_load_eval_results_extracts_summary_metrics(tmp_path):
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    _write_result(results_dir / "fakerouter_eval.json", _metrics())
    _write_result(
        results_dir / "model_eval_Qwen.json",
        _metrics(required_field_presence_accuracy=0.75),
        model="Qwen/Qwen2.5-0.5B-Instruct",
    )

    results = load_eval_results(results_dir)

    assert [result["name"] for result in results] == ["FakeRouter", "Qwen/Qwen2.5-0.5B-Instruct"]
    assert results[1]["metrics"]["required_field_presence_accuracy"] == 0.75


def test_markdown_table_includes_requested_metrics():
    table = build_markdown_table(
        [
            {
                "name": "FakeRouter",
                "metrics": _metrics(workflow_accuracy=0.9701),
            }
        ]
    )

    assert "| Model |" in table
    assert "`json_validity_rate`" in table
    assert "`false_route_rate`" in table
    assert "97.01%" in table


def test_write_report_supports_single_baseline(tmp_path):
    results_dir = tmp_path / "results"
    output_path = tmp_path / "docs" / "eval_comparison.md"
    results_dir.mkdir()
    _write_result(results_dir / "fakerouter_eval.json", _metrics())

    written_path, results, report = write_report(results_dir, output_path)

    assert written_path == output_path
    assert len(results) == 1
    assert output_path.exists()
    assert "## Interpretation" in report
    assert "Best structured extraction" in report
    assert "FakeRouter" in output_path.read_text(encoding="utf-8")


def test_write_report_identifies_safety_and_next_improvement(tmp_path):
    results_dir = tmp_path / "results"
    output_path = tmp_path / "docs" / "eval_comparison.md"
    results_dir.mkdir()
    _write_result(
        results_dir / "fakerouter_eval.json",
        _metrics(required_field_presence_accuracy=0.3, false_route_rate=0.0),
    )
    _write_result(
        results_dir / "lora_eval_routercore-qwen-lora.json",
        _metrics(
            required_field_presence_accuracy=0.8,
            unsafe_rejection_accuracy=0.9,
            false_route_rate=0.05,
        ),
        adapter="outputs/routercore-qwen-lora",
    )

    _, _, report = write_report(results_dir, output_path)

    assert "Best structured extraction: LoRA: routercore-qwen-lora (80.00%)" in report
    assert "Safest model: FakeRouter" in report
    assert "False route rate:" in report
    assert "Improve next: structured parameter extraction" in report


def test_write_report_lists_tied_safest_models(tmp_path):
    results_dir = tmp_path / "results"
    output_path = tmp_path / "docs" / "eval_comparison.md"
    results_dir.mkdir()
    _write_result(results_dir / "fakerouter_eval.json", _metrics())
    _write_result(
        results_dir / "lora_eval_routercore-qwen-lora-safety-rocm.json",
        _metrics(required_field_presence_accuracy=1.0),
        adapter="outputs/routercore-qwen-lora-safety-rocm",
    )

    _, _, report = write_report(results_dir, output_path)

    assert "Safest model: FakeRouter, LoRA: routercore-qwen-lora-safety-rocm" in report
    assert "(models; unsafe rejection 100.00%, false route 0.00%)" in report
    assert "False route rate: remained low across available results; best is FakeRouter, LoRA: routercore-qwen-lora-safety-rocm (0.00%)" in report
