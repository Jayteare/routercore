import builtins

import pytest

from routercore.model_router import (
    ModelRouter,
    OptionalModelDependencyError,
    extract_first_json_object,
)


VALID_ROUTER_JSON = """
{
  "status": "routed",
  "workflow": "create_web_app",
  "confidence": 0.91,
  "parameters": {"app_name": "claims-web-app"},
  "missing_fields": [],
  "candidate_workflows": [{"workflow": "create_web_app", "confidence": 0.91}],
  "failure_reasons": [],
  "clarifying_question": null
}
"""


def test_extract_json_from_clean_json():
    parsed = extract_first_json_object(VALID_ROUTER_JSON)

    assert parsed is not None
    assert parsed["status"] == "routed"
    assert parsed["workflow"] == "create_web_app"


def test_extract_json_from_text_with_leading_and_trailing_junk():
    parsed = extract_first_json_object(f"thinking...\n{VALID_ROUTER_JSON}\nthanks")

    assert parsed is not None
    assert parsed["parameters"]["app_name"] == "claims-web-app"


def test_fallback_router_output_when_model_output_parsing_fails():
    router = ModelRouter.__new__(ModelRouter)
    router._generate_text = lambda _prompt: "not json at all"

    output = router.route("Create a web app.")

    assert output.status == "fallback"
    assert output.workflow is None
    assert output.confidence == 0.0
    assert "model_output_parse_failed" in output.failure_reasons


def test_model_router_imports_without_transformers_available(monkeypatch):
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name in {"torch", "transformers"}:
            raise ImportError(name)
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(OptionalModelDependencyError):
        ModelRouter("local-test-model")
