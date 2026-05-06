# AMD Round 2 Safety Plan

The first AMD Developer Cloud / ROCm LoRA run proved that fine-tuning improves structured routing quality:

| Metric | FakeRouter | AMD LoRA Round 1 |
| --- | ---: | ---: |
| `workflow_accuracy` | 97.01% | 100.00% |
| `status_accuracy` | 57.33% | 80.00% |
| `required_field_presence_accuracy` | 28.57% | 91.84% |
| `unsafe_rejection_accuracy` | 100.00% | 75.00% |
| `false_route_rate` | 0.00% | 6.67% |

Round 2 focuses on recovering safety while preserving the LoRA extraction gains.

## Objective

Improve unsafe request rejection and reduce false routes without losing the required-field extraction improvement from round 1.

Target direction:

- Keep `required_field_presence_accuracy` above 85%.
- Keep `status_accuracy` at or above 80%.
- Push `unsafe_rejection_accuracy` back toward 100%.
- Push `false_route_rate` back toward 0%.

## Safety-Augmented Dataset

Generate the regular eval set plus a safety-heavy training split:

```bash
python3 -m training.generate_dataset --safety-augmented
```

Format the safety split for instruction tuning:

```bash
python3 -m training.format_dataset \
  --train-input data/train_safety.jsonl \
  --eval-input data/eval.jsonl \
  --train-output data/routercore_train_safety_instruct.jsonl \
  --eval-output data/routercore_eval_instruct.jsonl
```

The safety split increases adversarial examples for:

- Owner/admin IAM requests
- Broad-scope production permissions
- Production monitoring disablement
- Security bypass requests
- Destructive production operations

## AMD ROCm Training Command

Run this on the AMD Developer Cloud GPU VM:

```bash
python3 -m training.train_lora \
  --model Qwen/Qwen2.5-0.5B-Instruct \
  --train-file data/routercore_train_safety_instruct.jsonl \
  --eval-file data/routercore_eval_instruct.jsonl \
  --output-dir outputs/routercore-qwen-lora-safety \
  --max-steps 150 \
  --batch-size 1 \
  --gradient-accumulation-steps 8 \
  --learning-rate 2e-4 \
  --max-seq-length 1024
```

Evaluate the round 2 adapter:

```bash
python3 -m eval.run_lora_eval \
  --base-model Qwen/Qwen2.5-0.5B-Instruct \
  --adapter outputs/routercore-qwen-lora-safety \
  --limit 75

python3 -m eval.compare_results
```

## What To Look For

Round 2 is successful if the comparison report shows that the safety-tuned LoRA adapter keeps most of the structured extraction gain while lowering false routes and improving unsafe rejection accuracy.

The key submission story becomes stronger if the results show iteration:

1. Deterministic baseline is safe but weak at extraction.
2. AMD LoRA round 1 improves extraction but reveals safety regression.
3. Safety-augmented AMD LoRA round 2 reduces that regression.
