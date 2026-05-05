# Evaluation Comparison

This report compares RouterCore eval result artifacts from `eval/results/`.

## Metrics

| Model | `json_validity_rate` | `workflow_accuracy` | `status_accuracy` | `required_field_presence_accuracy` | `unsafe_rejection_accuracy` | `false_route_rate` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| FakeRouter | 100.00% | 97.01% | 57.33% | 28.57% | 100.00% | 0.00% |

## Interpretation

- Best structured extraction: FakeRouter (28.57%).
- Safest model: FakeRouter (unsafe rejection 100.00%, false route 0.00%).
- False route rate: remained low across available results; best is FakeRouter (0.00%).
- Improve next: structured parameter extraction.
