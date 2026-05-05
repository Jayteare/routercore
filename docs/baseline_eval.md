# Baseline Evaluation

## Baseline Summary

The deterministic `FakeRouter` establishes a conservative pre-fine-tuning baseline. It shows what RouterCore can do with keyword routing plus schema validation and an authoritative policy layer, before adding a prompted base model or fine-tuned router.

| Metric | Score |
| --- | ---: |
| `json_validity_rate` | 100.00% |
| `workflow_accuracy` | 97.01% |
| `status_accuracy` | 57.33% |
| `required_field_presence_accuracy` | 28.57% |
| `unsafe_rejection_accuracy` | 100.00% |
| `false_route_rate` | 0.00% |

## Interpretation

JSON validity is perfect because `FakeRouter` emits structured output.

Workflow accuracy is high because keyword routing can usually identify the broad workflow.

Status accuracy is limited because routing state decisions require more nuance than simple keyword matching.

Required-field presence accuracy is low because the deterministic router does not reliably extract complete structured parameters.

Unsafe rejection accuracy and false route rate are strong because the policy layer is conservative and authoritative.

## Why Fine-Tuning Is Still Needed

Fine-tuning should target:

- Better parameter extraction
- Better status classification
- Better clarification question generation
- Better handling of ambiguous phrasing

The goal is not to replace the policy layer. The goal is to improve the router proposal while preserving validation and policy redundancy.

## Track 2 Framing

This creates a clear Track 2 fine-tuning objective:

> Improve structured routing quality while preserving safe-routing behavior.
