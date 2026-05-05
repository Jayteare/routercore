# Demo Script

## 2-Minute Demo

### Opening Problem

"Agentic DevOps systems are powerful, but there is a risky step before execution: deciding what the user is actually asking for, whether the request is complete, and whether it is safe. RouterCore focuses on that pre-execution routing decision."

### System Overview

"RouterCore takes a natural-language request and sends it through four layers. First, the router proposes a workflow and structured parameters. Second, the schema validator checks required fields and allowed values. Third, the policy engine makes the final decision. Fourth, the orchestrator creates an execution preview only. Nothing is actually deployed or changed."

### Demo Case 1: Successful Web App Route

Input:

```text
Create a staging Python web app for the claims team in East US with diagnostics enabled.
```

"Here the router selects `create_web_app`, extracts parameters like runtime, region, environment, team, and diagnostics, and the validator accepts the route. The policy layer allows it for preview. The orchestrator shows the planned steps, but does not execute anything."

### Demo Case 2: Missing Fields Trigger Clarification

Input:

```text
Create a Python web app for the finance team.
```

"This is clearly a web app request, but it is missing required fields like region and environment. RouterCore does not pretend the request is complete. It returns `needs_clarification` with a targeted question."

### Demo Case 3: Risky IAM Owner Access Is Rejected

Input:

```text
Grant John owner access to production.
```

"This is the safety case. The router can identify `grant_iam_role`, but the policy layer is authoritative. Owner/admin grants are blocked, and production IAM changes are high risk, so the final decision is rejected."

### Evaluation Baseline

"The current deterministic baseline has 100% JSON validity, 97.01% workflow accuracy, 57.33% status accuracy, 28.57% required-field presence accuracy, 100% unsafe rejection accuracy, and 0% false route rate. That tells a useful story: the baseline is conservative and safe, but parameter extraction and status classification are where fine-tuning can help."

### Closing Fine-Tuning Plan

"The Track 2 plan is to fine-tune a compact Hugging Face causal model with LoRA on AMD Developer Cloud using ROCm. The goal is to improve structured routing quality while keeping validation and policy redundancy in place. RouterCore is not trying to replace safety rules with a model. It is trying to make the model's proposal better before policy makes the final call."
