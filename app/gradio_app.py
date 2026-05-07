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


def route_request(request_text: str):
    session = RouterCoreSession()
    router_output, validation_result, policy_decision, preview, state = session.route(request_text)
    return (
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

        with gr.Row():
            router_json = gr.JSON(label="Router Output JSON")
            validation_json = gr.JSON(label="Validation Result JSON")
            policy_json = gr.JSON(label="Policy Decision JSON")

        preview_markdown = gr.Markdown(label="Execution Preview / Clarifying Question")

        route_button.click(
            route_request,
            inputs=[request_box],
            outputs=[router_json, validation_json, policy_json, preview_markdown, state],
        )
        continue_button.click(
            continue_with_clarification,
            inputs=[request_box, follow_up_box, state],
            outputs=[router_json, validation_json, policy_json, preview_markdown, state],
        )

    return demo


if __name__ == "__main__":
    build_demo().launch()
