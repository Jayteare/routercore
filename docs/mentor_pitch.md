# Mentor Pitch

## 30-Second Pitch

RouterCore is a safe routing layer for agentic DevOps workflows. Before an agent or orchestrator touches tools, RouterCore converts a messy user request into a structured route, validates it against workflow schemas, applies policy checks, and decides whether the request should be routed, clarified, confirmed, rejected, or sent to fallback. The project demonstrates safe routing, not just routing, with a deterministic baseline today and a clear LoRA fine-tuning path for AMD GPUs.

## 2-Minute Technical Explanation

The core idea is that agent systems need a reliable decision point before execution. A user might say, "Create a staging Python web app in East US," "Set up reporting," or "Grant John owner access to production." Those requests should not all flow directly into an agent executor.

RouterCore breaks the problem into layers:

1. The router proposes a workflow, confidence score, parameters, missing fields, and clarification hints.
2. The schema validator checks the proposal against JSON workflow definitions.
3. The policy engine makes the authoritative decision using confidence thresholds, blocked IAM roles, risky phrase detection, and confirmation rules.
4. The orchestrator produces an execution preview only. It does not run cloud actions.

The current router is deterministic so the demo works locally and the failure modes are visible. The training and eval layer then creates a Track 2 path: fine-tune a compact model to emit the same JSON contract, compare it against `FakeRouter` and a prompted base model, and keep validation plus policy as redundant safety controls.

## Track 2 Framing

RouterCore is designed for Track 2: Fine-Tuning on AMD GPUs. The fine-tuning objective is to improve structured routing quality while preserving safe-routing behavior.

The next milestone is to fine-tune a compact open-source causal language model on AMD Developer Cloud with ROCm using the synthetic RouterCore dataset, then evaluate it against:

- Deterministic `FakeRouter`
- Prompted base model
- LoRA fine-tuned router

## Track 1-Style Workflow Framing

Even though the main track fit is fine-tuning, RouterCore also demonstrates an agentic workflow pattern:

- User request intake
- Router proposal
- Schema validation
- Policy decision
- Clarification or confirmation loop
- Orchestrator handoff preview

This makes the demo easy to understand as an agent safety layer without overbuilding a full cloud execution platform.

## Current Baseline Results

| Metric | FakeRouter |
| --- | ---: |
| `json_validity_rate` | 100.00% |
| `workflow_accuracy` | 97.01% |
| `status_accuracy` | 57.33% |
| `required_field_presence_accuracy` | 28.57% |
| `unsafe_rejection_accuracy` | 100.00% |
| `false_route_rate` | 0.00% |

## Why Fine-Tuning Matters

The deterministic router is safe but limited. It usually identifies the broad workflow, but it struggles with nuanced status classification and complete parameter extraction. Fine-tuning should improve:

- Structured parameter extraction
- Status classification
- Clarifying question quality
- Ambiguous phrasing
- Generalization beyond keyword patterns

The goal is not to replace the policy layer. The goal is to improve the router proposal while preserving validation and policy redundancy.

## Policy Redundancy

RouterCore treats the router as a recommender, not an authority. The policy layer can reject or downgrade a route even if the router is confident.

Examples:

- `owner` and `admin` IAM roles are blocked.
- Destructive production phrases are rejected.
- Low-confidence routes ask for clarification.
- Medium-confidence and high-risk routes require confirmation.
- The orchestrator only previews actions.

This is why unsafe rejection accuracy and false route rate are strong in the baseline.

## Mentor Feedback

I would like feedback on:

- Whether the Track 2 fine-tuning objective is framed clearly enough.
- Which compact model would be strongest for a short AMD ROCm LoRA run.
- Whether the synthetic dataset should include more adversarial policy cases.
- Which metrics judges are most likely to care about.
- How to make the final demo video show both model improvement and safety redundancy in under three minutes.
