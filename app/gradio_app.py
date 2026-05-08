from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import gradio as gr

from routercore.state import RouterCoreSession, SessionState


EXAMPLES_PATH = Path(__file__).resolve().parents[1] / "data" / "examples" / "demo_inputs.json"


def _load_examples() -> list[str]:
    with EXAMPLES_PATH.open("r", encoding="utf-8") as handle:
        return [item["input"] for item in json.load(handle)]


def _json(model: Any) -> dict[str, Any]:
    return model.model_dump(mode="json")


def _preview_text(preview: Any) -> str:
    if not preview.can_preview:
        return preview.message
    steps = "\n".join(f"{index}. {step}" for index, step in enumerate(preview.steps, start=1))
    params = json.dumps(preview.parameters, indent=2, sort_keys=True)
    return f"{preview.message}\n\nSteps:\n{steps}\n\nParameters:\n```json\n{params}\n```"


def _decision_summary(policy_decision: Any, validation_result: Any, state: SessionState) -> str:
    lines = [
        f"**Decision:** `{policy_decision.status}`",
        f"**Workflow:** `{policy_decision.workflow or 'none'}`",
        f"**Attempt:** `{state.attempt_count}`",
    ]
    if validation_result.missing_fields:
        missing = ", ".join(f"`{field}`" for field in validation_result.missing_fields)
        lines.append(f"**Still needed:** {missing}")
    if policy_decision.clarifying_question:
        lines.append(f"**Clarifying question:** {policy_decision.clarifying_question}")
    if policy_decision.reasons:
        lines.append("**Reason:** " + "; ".join(policy_decision.reasons))
    if state.accumulated_context:
        context = " | ".join(state.accumulated_context)
        lines.append(f"**Accumulated context:** {context}")
    return "\n\n".join(lines)


def route_request(request_text: str):
    session = RouterCoreSession()
    router_output, validation_result, policy_decision, preview, state = session.route(request_text)
    return (
        _decision_summary(policy_decision, validation_result, state),
        _json(router_output),
        _json(validation_result),
        _json(policy_decision),
        _preview_text(preview),
        state,
    )


def continue_with_clarification(request_text: str, follow_up_answer: str, state: SessionState | None):
    session = RouterCoreSession(state=state or SessionState(original_request=request_text))
    router_output, validation_result, policy_decision, preview, state = session.continue_with_clarification(
        follow_up_answer
    )
    return (
        _decision_summary(policy_decision, validation_result, state),
        _json(router_output),
        _json(validation_result),
        _json(policy_decision),
        _preview_text(preview),
        state,
    )


def build_demo() -> gr.Blocks:
    with gr.Blocks(title="RouterCore") as demo:
        gr.Markdown(
            "# RouterCore\n"
            "Fine-tuning-ready workflow routing with schema validation, policy redundancy, "
            "clarification loops, and execution previews."
        )
        gr.Markdown(
            "### AMD ROCm Result\n"
            "| Baseline | Required fields | Status accuracy | Unsafe rejection | False routes |\n"
            "| --- | ---: | ---: | ---: | ---: |\n"
            "| FakeRouter | 28.57% | 57.33% | 100.00% | 0.00% |\n"
            "| Safety LoRA on AMD MI300X / ROCm | 100.00% | 86.67% | 100.00% | 0.00% |\n\n"
            "The live demo uses the lightweight deterministic router; the table shows the confirmed "
            "ROCm fine-tuning result from `eval/results/`."
        )

        state = gr.State(SessionState())

        with gr.Row():
            request_box = gr.Textbox(
                label="User request",
                lines=4,
                placeholder="Describe the workflow you want RouterCore to route.",
            )
            follow_up_box = gr.Textbox(
                label="Follow-up answer",
                lines=4,
                placeholder="Answer the clarifying question here.",
            )

        with gr.Row():
            route_button = gr.Button("Route Request", variant="primary")
            continue_button = gr.Button("Continue With Clarification")

        gr.Examples(
            examples=_load_examples(),
            inputs=request_box,
            label="Examples",
        )

        decision_summary = gr.Markdown(label="Decision Summary")

        with gr.Row():
            router_json = gr.JSON(label="Router Output JSON")
            validation_json = gr.JSON(label="Validation Result JSON")
            policy_json = gr.JSON(label="Policy Decision JSON")

        preview_markdown = gr.Markdown(label="Execution Preview / Clarifying Question")

        route_button.click(
            route_request,
            inputs=[request_box],
            outputs=[decision_summary, router_json, validation_json, policy_json, preview_markdown, state],
        )
        continue_button.click(
            continue_with_clarification,
            inputs=[request_box, follow_up_box, state],
            outputs=[decision_summary, router_json, validation_json, policy_json, preview_markdown, state],
        )

    return demo


if __name__ == "__main__":
    build_demo().launch()
