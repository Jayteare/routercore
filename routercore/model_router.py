from __future__ import annotations

import json
from json import JSONDecodeError
from typing import Any

from pydantic import ValidationError

from routercore.models import RouterOutput


ALLOWED_STATUSES = [
    "routed",
    "needs_clarification",
    "requires_confirmation",
    "rejected",
    "fallback",
]

ALLOWED_WORKFLOWS = [
    "create_web_app",
    "create_storage_bucket",
    "create_service_account",
    "grant_iam_role",
    "create_scheduler_job",
]

REQUIRED_JSON_FIELDS = [
    "status",
    "workflow",
    "confidence",
    "parameters",
    "missing_fields",
    "candidate_workflows",
    "failure_reasons",
    "clarifying_question",
]


class OptionalModelDependencyError(RuntimeError):
    """Raised when optional local model dependencies are not installed."""


def extract_first_json_object(text: str) -> dict[str, Any] | None:
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def build_router_prompt(user_request: str) -> str:
    schema_example = {
        "status": "routed | needs_clarification | requires_confirmation | rejected | fallback",
        "workflow": "create_web_app | create_storage_bucket | create_service_account | grant_iam_role | create_scheduler_job | null",
        "confidence": 0.0,
        "parameters": {},
        "missing_fields": [],
        "candidate_workflows": [{"workflow": "create_web_app", "confidence": 0.0}],
        "failure_reasons": [],
        "clarifying_question": None,
    }
    return (
        "You are RouterCore, a routing model for DevOps agent workflows. "
        "Return only valid JSON matching the RouterCore schema.\n\n"
        f"Allowed statuses: {', '.join(ALLOWED_STATUSES)}\n"
        f"Allowed workflows: {', '.join(ALLOWED_WORKFLOWS)}\n"
        f"Required JSON fields: {', '.join(REQUIRED_JSON_FIELDS)}\n"
        "Workflow may be null only when no workflow is selected.\n"
        "Do not include markdown, explanations, or code fences. Return JSON only.\n\n"
        "RouterCore JSON schema example:\n"
        f"{json.dumps(schema_example, indent=2)}\n\n"
        f"User request: {user_request}\n"
        "JSON:"
    )


class ModelRouter:
    def __init__(
        self,
        model_name_or_path: str,
        *,
        device: str = "auto",
        max_new_tokens: int = 512,
    ) -> None:
        self.model_name_or_path = model_name_or_path
        self.device = device
        self.max_new_tokens = max_new_tokens

        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise OptionalModelDependencyError(
                "Optional model dependencies are unavailable. Install transformers and torch to run model eval."
            ) from exc

        self.torch = torch
        resolved_device = self._resolve_device(device)
        self.resolved_device = resolved_device
        self.tokenizer = AutoTokenizer.from_pretrained(model_name_or_path)
        self.model = AutoModelForCausalLM.from_pretrained(model_name_or_path)
        self.model.to(resolved_device)
        self.model.eval()

    def route(self, request_text: str) -> RouterOutput:
        prompt = build_router_prompt(request_text)
        try:
            model_text = self._generate_text(prompt)
            parsed = extract_first_json_object(model_text)
            if parsed is None:
                return self._fallback("model_output_parse_failed")
            return RouterOutput.model_validate(parsed)
        except (JSONDecodeError, ValidationError, ValueError, TypeError):
            return self._fallback("model_output_parse_failed")

    def _resolve_device(self, device: str) -> str:
        if device == "auto":
            return "cuda" if self.torch.cuda.is_available() else "cpu"
        if device == "cuda" and not self.torch.cuda.is_available():
            return "cpu"
        return device

    def _generate_text(self, prompt: str) -> str:
        encoded = self.tokenizer(prompt, return_tensors="pt")
        if hasattr(encoded, "to"):
            encoded = encoded.to(self.resolved_device)

        with self.torch.no_grad():
            output_ids = self.model.generate(
                **encoded,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,
                pad_token_id=self.tokenizer.eos_token_id,
            )

        input_length = encoded["input_ids"].shape[-1]
        generated_ids = output_ids[0][input_length:]
        return self.tokenizer.decode(generated_ids, skip_special_tokens=True)

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
