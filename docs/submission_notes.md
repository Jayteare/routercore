# Submission Notes

## Project Title Options

- RouterCore: Safe Routing for Agentic DevOps
- RouterCore: Fine-Tuned Workflow Routing Before Agent Execution
- RouterCore: Safe Routing, Not Just Routing
- RouterCore: Policy-Aware Routing for DevOps Agents

## Short Description

RouterCore is a safe routing layer for agentic DevOps workflows. It converts natural-language requests into validated workflow routes, structured parameters, clarification questions, confirmation decisions, or policy rejections before an orchestrator can act.

## Long Description

RouterCore demonstrates the step before agent execution: deciding whether a user request should be routed, clarified, confirmed, rejected, or sent to fallback. The MVP includes a deterministic router, schema validator, policy engine, iterative clarification state, and execution-preview orchestrator. It intentionally does not execute real cloud or infrastructure actions.

For the AMD Developer Hackathon, RouterCore is framed as a Track 2 fine-tuning project. It includes synthetic train/eval data, FakeRouter baseline evaluation, optional prompted Hugging Face model evaluation, and a LoRA fine-tuning path designed for AMD Developer Cloud with ROCm. The goal is to improve structured router proposals while preserving validation and policy redundancy.

## Suggested Tags

- AI agents
- Fine-tuning
- AMD ROCm
- Hugging Face
- LoRA
- DevOps
- Safety
- Workflow routing
- Gradio
- Pydantic

## Track Selection Recommendation

Submit under Track 2: Fine-Tuning on AMD GPUs.

RouterCore also has a Track 1-style agent workflow demo, but the strongest judging story is the fine-tuning objective: improve structured routing quality while preserving safe-routing behavior.

## What To Submit On lablab

- Public GitHub repository
- Hugging Face Space link for the Gradio demo
- Short demo video
- README with setup instructions
- Baseline evaluation report
- Evaluation comparison report
- Notes on the LoRA fine-tuning plan and AMD ROCm readiness

## What To Include In The Video

- The problem: agents need a safe routing decision before execution.
- The app flow: router, validator, policy, orchestrator preview.
- A successful web app route.
- A missing-field clarification.
- A risky IAM owner request rejected by policy.
- Baseline metrics and what they imply.
- Fine-tuning plan on AMD Developer Cloud with ROCm.

## What To Include In The Slide Deck

- One-slide problem statement
- Architecture diagram
- Router output contract
- Policy redundancy examples
- Demo screenshots
- Baseline metrics table
- Fine-tuning objective and eval plan
- Next steps

## Hugging Face Space Deployment Notes

Use the Gradio app as the Space entrypoint. The Space can run the deterministic `FakeRouter` by default so it stays lightweight and reliable.

Recommended Space files:

- `app/gradio_app.py` or a root-level `app.py` wrapper
- `requirements.txt`
- `routercore/`
- `data/schemas/`
- `data/examples/`

Keep prompted model and LoRA evaluation optional. Large model downloads should not be required for the public demo Space unless the Space hardware and storage are explicitly configured for it.
