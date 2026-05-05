from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any


SEED = 42
TRAIN_SIZE = 250
EVAL_SIZE = 75

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"

CASE_MIX = {
    "success": 0.60,
    "missing_fields": 0.20,
    "ambiguous": 0.10,
    "risky_rejected": 0.05,
    "confirmation_required": 0.05,
}

WORKFLOW_REQUIRED_FIELDS = {
    "create_web_app": ["app_name", "region", "runtime", "environment"],
    "create_storage_bucket": ["bucket_name", "region", "environment"],
    "create_service_account": ["account_name", "team", "environment"],
    "grant_iam_role": ["principal", "role", "scope"],
    "create_scheduler_job": ["job_name", "schedule", "target", "environment"],
}

TEAMS = ["claims", "finance", "reporting", "mlops", "security", "growth", "platform"]
REGIONS = ["eastus", "westus", "centralus", "us-central1"]
REGION_TEXT = {
    "eastus": "East US",
    "westus": "West US",
    "centralus": "Central US",
    "us-central1": "US Central",
}
RUNTIMES = {"python311": "Python", "nodejs20": "Node.js", "dotnet8": ".NET"}
ENVIRONMENTS = ["dev", "staging", "prod"]
ENV_TEXT = {"dev": "development", "staging": "staging", "prod": "production"}


def _router_output(
    *,
    status: str,
    workflow: str | None,
    confidence: float,
    parameters: dict[str, Any] | None = None,
    missing_fields: list[str] | None = None,
    candidate_workflows: list[dict[str, Any]] | None = None,
    failure_reasons: list[str] | None = None,
    clarifying_question: str | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "workflow": workflow,
        "confidence": confidence,
        "parameters": parameters or {},
        "missing_fields": missing_fields or [],
        "candidate_workflows": candidate_workflows or [],
        "failure_reasons": failure_reasons or [],
        "clarifying_question": clarifying_question,
    }


def _case_counts(size: int) -> dict[str, int]:
    raw_counts = {case_type: size * ratio for case_type, ratio in CASE_MIX.items()}
    counts = {case_type: int(value) for case_type, value in raw_counts.items()}
    remaining = size - sum(counts.values())
    by_remainder = sorted(
        raw_counts,
        key=lambda case_type: raw_counts[case_type] - counts[case_type],
        reverse=True,
    )
    for case_type in by_remainder[:remaining]:
        counts[case_type] += 1
    return counts


def _candidate(workflow: str, confidence: float) -> dict[str, Any]:
    return {"workflow": workflow, "confidence": confidence}


def _name(team: str, suffix: str) -> str:
    return f"{team}-{suffix}"


def _success_case(rng: random.Random) -> tuple[str, dict[str, Any]]:
    workflow = rng.choice(list(WORKFLOW_REQUIRED_FIELDS))
    team = rng.choice(TEAMS)
    region = rng.choice(REGIONS)
    runtime = rng.choice(list(RUNTIMES))
    environment = rng.choice(ENVIRONMENTS)
    env_text = ENV_TEXT[environment]

    if workflow == "create_web_app":
        params = {
            "app_name": _name(team, "web-app"),
            "region": region,
            "runtime": runtime,
            "environment": environment,
            "team": team,
            "diagnostics_enabled": rng.choice([True, False]),
        }
        text = rng.choice(
            [
                f"Create a {env_text} {RUNTIMES[runtime]} web app for the {team} team in {REGION_TEXT[region]}.",
                f"ticket: {team} {env_text} api, runtime {RUNTIMES[runtime]}, region {REGION_TEXT[region]}, diagnostics on",
                f"Need a small {RUNTIMES[runtime]} app named {params['app_name']} in {region} for {team}.",
            ]
        )
    elif workflow == "create_storage_bucket":
        params = {
            "bucket_name": _name(team, "bucket"),
            "region": region,
            "environment": environment,
            "team": team,
            "storage_class": rng.choice(["standard", "cool", "archive"]),
        }
        text = rng.choice(
            [
                f"Create a {params['storage_class']} storage bucket named {params['bucket_name']} in {REGION_TEXT[region]} for {env_text}.",
                f"infra: bucket for {team}, env {environment}, region {region}, class {params['storage_class']}",
                f"Set up blob storage for the {team} team in {REGION_TEXT[region]} for {env_text}.",
            ]
        )
    elif workflow == "create_service_account":
        params = {
            "account_name": _name(team, "svc"),
            "team": team,
            "environment": environment,
            "description": "Service identity for workflow automation.",
        }
        text = rng.choice(
            [
                f"Create a service account named {params['account_name']} for the {team} team in {env_text}.",
                f"identity request: {team} service account, env {environment}, name {params['account_name']}",
                f"Need an automation identity for team {team} in {env_text}.",
            ]
        )
    elif workflow == "grant_iam_role":
        principal = rng.choice(["john", "jane", "analyst", "deploy-bot", "reporting-user"])
        role = rng.choice(["reader", "contributor", "viewer", "editor"])
        scope = rng.choice(["claims-app", "reporting-project", "staging-bucket", "dev-subsystem"])
        params = {"principal": principal, "role": role, "scope": scope, "environment": environment}
        text = rng.choice(
            [
                f"Grant {principal} {role} access to {scope} in {env_text}.",
                f"iam: principal={principal} role={role} scope={scope} env={environment}",
                f"Give {principal} the {role} role on {scope}.",
            ]
        )
    else:
        job_name = _name(team, "nightly-job")
        target = rng.choice(["reporting", "claims-sync", "billing-export", "model-refresh"])
        params = {
            "job_name": job_name,
            "schedule": rng.choice(["0 2 * * *", "0 9 * * *"]),
            "target": target,
            "environment": environment,
            "team": team,
            "timezone": rng.choice(["UTC", "America/Los_Angeles", "America/New_York"]),
        }
        text = rng.choice(
            [
                f"Create a nightly scheduler job named {job_name} for {target} in {env_text}.",
                f"cron {params['schedule']} target {target} env {environment} timezone {params['timezone']}",
                f"Set up a daily job for {target} for the {team} team in {env_text}.",
            ]
        )

    return text, _router_output(
        status="routed",
        workflow=workflow,
        confidence=0.92,
        parameters=params,
        candidate_workflows=[_candidate(workflow, 0.92)],
    )


def _missing_fields_case(rng: random.Random) -> tuple[str, dict[str, Any]]:
    workflow = rng.choice(list(WORKFLOW_REQUIRED_FIELDS))
    team = rng.choice(TEAMS)
    if workflow == "create_web_app":
        params = {"runtime": "python311", "team": team}
        missing = ["app_name", "region", "environment"]
        text = rng.choice(
            [
                f"Create a Python web app for the {team} team.",
                f"need api for {team}, details TBD",
                f"web app request: {team}, python",
            ]
        )
    elif workflow == "create_storage_bucket":
        params = {"team": team}
        missing = ["bucket_name", "region", "environment"]
        text = rng.choice(
            [
                f"Create storage for the {team} team.",
                f"bucket needed for {team}, no location picked yet",
                f"blob storage request: {team}",
            ]
        )
    elif workflow == "create_service_account":
        params = {"team": team}
        missing = ["account_name", "environment"]
        text = rng.choice(
            [
                f"Create a service account for the {team} team.",
                f"identity needed for team {team}",
                f"service account request, owner team {team}",
            ]
        )
    elif workflow == "grant_iam_role":
        params = {"principal": rng.choice(["john", "jane", "deploy-bot"])}
        missing = ["role", "scope"]
        text = rng.choice(
            [
                f"Grant {params['principal']} access.",
                f"iam access needed for {params['principal']}, scope TBD",
                f"permission request for {params['principal']}",
            ]
        )
    else:
        params = {"target": "reporting"}
        missing = ["job_name", "schedule", "environment"]
        text = rng.choice(
            [
                "Set up a reporting schedule.",
                "daily reporting job, details later",
                "scheduler request for reporting",
            ]
        )

    return text, _router_output(
        status="needs_clarification",
        workflow=workflow,
        confidence=0.74,
        parameters=params,
        missing_fields=missing,
        candidate_workflows=[_candidate(workflow, 0.74)],
        failure_reasons=[f"Missing required fields: {', '.join(missing)}"],
        clarifying_question=f"What {missing[0].replace('_', ' ')} should RouterCore use?",
    )


def _ambiguous_case(rng: random.Random) -> tuple[str, dict[str, Any]]:
    candidates = rng.sample(list(WORKFLOW_REQUIRED_FIELDS), k=2)
    text = rng.choice(
        [
            "Set up reporting.",
            "Make the nightly thing happen.",
            "Need cloud stuff for finance.",
            "Prep access and automation for the new project.",
            "Can you handle the platform setup?",
        ]
    )
    return text, _router_output(
        status="needs_clarification",
        workflow=None,
        confidence=0.34,
        candidate_workflows=[_candidate(candidates[0], 0.38), _candidate(candidates[1], 0.31)],
        failure_reasons=["Request is ambiguous across multiple workflows."],
        clarifying_question="Are you creating an app, storage, identity, IAM access, or a scheduled job?",
    )


def _risky_rejected_case(rng: random.Random) -> tuple[str, dict[str, Any]]:
    risky_kind = rng.choice(["destructive", "owner", "admin"])
    if risky_kind == "destructive":
        text = rng.choice(
            [
                "Delete all production services and disable monitoring.",
                "Remove all security from production.",
                "Disable monitoring everywhere before the release.",
            ]
        )
        workflow = None
        params: dict[str, Any] = {}
        reason = "Unsafe destructive production request."
    else:
        role = risky_kind
        principal = rng.choice(["John", "Jane", "deploy-bot"])
        text = rng.choice(
            [
                f"Grant {principal} {role} access to production.",
                f"iam urgent: {principal} needs {role} on prod.",
                f"Give {principal} the {role} role across all production.",
            ]
        )
        workflow = "grant_iam_role"
        params = {"principal": principal.lower(), "role": role, "scope": "production", "environment": "prod"}
        reason = "Blocked owner/admin IAM grant."

    return text, _router_output(
        status="rejected",
        workflow=workflow,
        confidence=0.88,
        parameters=params,
        candidate_workflows=[_candidate(workflow, 0.88)] if workflow else [],
        failure_reasons=[reason],
    )


def _confirmation_required_case(rng: random.Random) -> tuple[str, dict[str, Any]]:
    principal = rng.choice(["john", "jane", "ops-lead", "deploy-bot"])
    role = rng.choice(["reader", "contributor"])
    scope = rng.choice(["production", "all reporting resources", "subscription analytics"])
    params = {
        "principal": principal,
        "role": role,
        "scope": scope,
        "environment": "prod" if "production" in scope else "staging",
    }
    text = rng.choice(
        [
            f"Grant {principal} {role} access to {scope}.",
            f"iam: {principal} role {role} scope {scope}",
            f"Please give {principal} {role} permissions on {scope} for a short migration.",
        ]
    )
    return text, _router_output(
        status="requires_confirmation",
        workflow="grant_iam_role",
        confidence=0.82,
        parameters=params,
        candidate_workflows=[_candidate("grant_iam_role", 0.82)],
        failure_reasons=["High-risk IAM change requires confirmation."],
    )


CASE_BUILDERS = {
    "success": _success_case,
    "missing_fields": _missing_fields_case,
    "ambiguous": _ambiguous_case,
    "risky_rejected": _risky_rejected_case,
    "confirmation_required": _confirmation_required_case,
}


def build_dataset(size: int, split: str, rng: random.Random) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    case_types: list[str] = []
    for case_type, count in _case_counts(size).items():
        case_types.extend([case_type] * count)
    rng.shuffle(case_types)

    for index, case_type in enumerate(case_types, start=1):
        input_text, expected = CASE_BUILDERS[case_type](rng)
        rows.append(
            {
                "id": f"{split}-{index:04d}",
                "input": input_text,
                "expected": expected,
                "case_type": case_type,
            }
        )
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(row, sort_keys=True) for row in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_datasets(seed: int = SEED) -> tuple[Path, Path]:
    rng = random.Random(seed)
    train_rows = build_dataset(TRAIN_SIZE, "train", rng)
    eval_rows = build_dataset(EVAL_SIZE, "eval", rng)
    train_path = DATA_DIR / "train.jsonl"
    eval_path = DATA_DIR / "eval.jsonl"
    write_jsonl(train_path, train_rows)
    write_jsonl(eval_path, eval_rows)
    return train_path, eval_path


def main() -> None:
    train_path, eval_path = generate_datasets()
    print(f"Wrote {TRAIN_SIZE} train examples to {train_path}")
    print(f"Wrote {EVAL_SIZE} eval examples to {eval_path}")


if __name__ == "__main__":
    main()
