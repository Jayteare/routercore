# RouterCore

RouterCore is a focused proof-of-concept for the AMD Developer Hackathon. It shows how a lightweight routing model can make agentic systems safer and more reliable by converting messy natural-language requests into validated workflow routes, structured parameters, and policy-aware handoff previews.

The project fits Track 2, Fine-Tuning on AMD GPUs, while still presenting a Track 1-style agent workflow demo. The MVP uses a deterministic `FakeRouter` so the app works immediately, and keeps a clean boundary for replacing that router with a fine-tuned Hugging Face model later.

## Core Thesis

RouterCore demonstrates safe routing, not just routing. It focuses on the step before agent execution: deciding whether a request should be routed, clarified, confirmed, rejected, or escalated before any orchestrator or tool can act on it.

The router is only a recommender. The validator and policy layer provide redundant checks so malformed, low-confidence, ambiguous, or unsafe requests do not become confident agent actions.

## AMD Hackathon Fit

RouterCore is designed for Track 2: Fine-Tuning on AMD GPUs. The next milestone is fine-tuning a compact open-source model on AMD Developer Cloud with ROCm, then comparing it against the deterministic router and a prompted base model.

It also demonstrates a Track 1-style agentic workflow pattern through the router, validator, policy layer, clarification loop, and orchestrator preview. The demo stays intentionally scoped: it previews execution plans but does not run cloud or infrastructure actions.

## What It Demonstrates

- Workflow routing from natural language
- JSON schema-style workflow validation
- Policy redundancy after model/router output
- Iterative clarification for missing or uncertain fields
- Execution preview handoff without real cloud actions
- Evaluation and training hooks for future fine-tuning

RouterCore is intentionally not a cloud execution platform. It never creates infrastructure, changes IAM, or executes destructive actions.

## Mentor / Submission Docs

- [Mentor Pitch](docs/mentor_pitch.md)
- [Demo Script](docs/demo_script.md)
- [Submission Notes](docs/submission_notes.md)
- [Evaluation Comparison](docs/eval_comparison.md)
- [Architecture Diagram](docs/architecture.md)

## Evaluation Plan

RouterCore can compare deterministic, prompted, and fine-tuned routers using:

- JSON validity
- Workflow accuracy
- Status accuracy
- Required-field accuracy
- Unsafe request rejection accuracy
- False route rate

False route rate measures how often the system confidently routes a request that should have been clarified, confirmed, or rejected.

## Dataset and Evaluation

`training/generate_dataset.py` creates deterministic synthetic `data/train.jsonl` and `data/eval.jsonl` files across success, missing-field, ambiguous, risky-rejected, and confirmation-required cases. The dataset is designed to train and evaluate the router output contract without calling external LLM APIs.

The current baseline is `FakeRouter`, evaluated through the same router, validator, policy, and orchestrator decision path used by the app. Future runs can compare this baseline against a prompted base model and a fine-tuned router model using the same eval set and metrics.

False route rate matters because safe agent systems should avoid confidently handing off requests that needed clarification, confirmation, or rejection. A router that looks accurate but has a high false route rate is unsafe for agent execution.

See [Baseline Evaluation](docs/baseline_eval.md) for the current FakeRouter metrics and mentor-facing interpretation.

Generate a comparison report for all available eval artifacts with:

```bash
python -m eval.compare_results
```

## Prompted Model Baseline

RouterCore can optionally evaluate a local Hugging Face causal language model as a prompted baseline before LoRA fine-tuning:

```bash
python -m eval.run_model_eval --model Qwen/Qwen2.5-0.5B-Instruct --limit 10
```

This path is optional and local-friendly. It does not call paid APIs, and it is skipped gracefully if `transformers` or `torch` are not installed. The goal is to establish a second baseline between `FakeRouter` and a future fine-tuned router.

## LoRA Fine-Tuning

RouterCore includes an optional LoRA training path for AMD Developer Cloud / ROCm, and it can also run anywhere PyTorch supports the selected model.

```bash
python -m training.format_dataset
```

```bash
python -m training.train_lora \
  --model Qwen/Qwen2.5-0.5B-Instruct \
  --train-file data/routercore_train_instruct.jsonl \
  --eval-file data/routercore_eval_instruct.jsonl \
  --output-dir outputs/routercore-qwen-lora \
  --max-steps 100
```

```bash
python -m eval.run_lora_eval \
  --base-model Qwen/Qwen2.5-0.5B-Instruct \
  --adapter outputs/routercore-qwen-lora \
  --limit 25
```

This is intended to fine-tune a compact open-source model to emit the RouterCore JSON contract from natural-language DevOps requests, then compare the LoRA adapter against `FakeRouter` and the prompted base model.

## Example Flow

Input:

```text
Grant John owner access to production.
```

The router extracts `grant_iam_role` with parameters such as `principal=John`, `role=owner`, and `scope=production`. The policy layer rejects the request because owner/admin grants are blocked and high-risk production IAM changes are not allowed to proceed as normal routes.

## Architecture

1. `FakeRouter` proposes a workflow, confidence score, parameters, candidates, and clarification hints.
2. `validator` checks the route against workflow schema files in `data/schemas`.
3. `policy` makes the authoritative decision, including blocked values, confidence thresholds, unsafe phrase rejection, and high-risk confirmation.
4. `state` preserves the original request, accumulated clarification context, attempts, and latest decisions.
5. `orchestrator` creates a human-readable execution preview for accepted or confirmed routes only.

The router proposes; validation and policy decide. Clarification loops gather missing context and route again. Rejected requests stop without execution, fallback requests move to manual review or a larger orchestrator, and accepted or confirmed routes generate previews only.

## Workflows

- `create_web_app`
- `create_storage_bucket`
- `create_service_account`
- `grant_iam_role`
- `create_scheduler_job`

## Run Locally

```bash
pip install -r requirements.txt
python -m app.gradio_app
```

Then open the local Gradio URL printed by the command.

## Run Tests

```bash
pytest
```

## Fine-Tuning Plan

The current router is deterministic on purpose. Future work can replace `FakeRouter` with a fine-tuned model that emits the same router output contract:

```json
{
  "status": "routed",
  "workflow": "create_web_app",
  "confidence": 0.92,
  "parameters": {},
  "missing_fields": [],
  "candidate_workflows": [],
  "failure_reasons": [],
  "clarifying_question": null
}
```

The `training/` folder includes stubs for dataset generation, LoRA training, and inference. A hackathon extension would fine-tune a compact model with Hugging Face Transformers and PEFT on AMD GPUs with ROCm, then deploy the Gradio demo as a Hugging Face Space.

## Why Policy Redundancy Matters

Fine-tuned routers can be useful but should not be trusted as the final authority. RouterCore separates recommendation from enforcement:

- Validation catches missing and invalid parameters.
- Policy rejects unsafe requests such as destructive production changes.
- IAM owner/admin grants are blocked even when the router extracts them correctly.
- Medium-confidence and high-risk workflows require confirmation.
- The orchestrator previews actions but does not execute them.

This makes RouterCore a compact demo of safer agent handoff design.
