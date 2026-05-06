# Evaluation Comparison

This report compares RouterCore eval result artifacts from `eval/results/`. The LoRA result below was produced from a RouterCore fine-tuning run on AMD Developer Cloud with ROCm on an AMD Instinct MI300X VM.

## Metrics

| Model | `json_validity_rate` | `workflow_accuracy` | `status_accuracy` | `required_field_presence_accuracy` | `unsafe_rejection_accuracy` | `false_route_rate` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| FakeRouter | 100.00% | 97.01% | 57.33% | 28.57% | 100.00% | 0.00% |
| LoRA: routercore-qwen-lora | 100.00% | 100.00% | 80.00% | 91.84% | 75.00% | 6.67% |

## Interpretation

- Best structured extraction: LoRA: routercore-qwen-lora (91.84%).
- Safest model: FakeRouter (unsafe rejection 100.00%, false route 0.00%).
- False route rate: best is FakeRouter (0.00%); highest observed is LoRA: routercore-qwen-lora (6.67%).
- Improve next: reduce false routes before optimizing convenience metrics.

## AMD Training Takeaway

Fine-tuning on AMD improved the model-like routing behavior substantially: required-field presence rose from 28.57% to 91.84%, workflow accuracy reached 100.00%, and status accuracy rose from 57.33% to 80.00%. The safety metrics are the important caveat: the LoRA router is better at structured extraction, but the deterministic/policy-backed baseline remains safer. This supports the RouterCore design thesis: fine-tuning should improve router proposals, while validation and policy remain authoritative.
