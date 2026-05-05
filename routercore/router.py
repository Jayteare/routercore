from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from routercore.models import CandidateWorkflow, RouterOutput, WorkflowName


WORKFLOW_KEYWORDS: dict[WorkflowName, list[str]] = {
    "create_web_app": ["web app", "api", "flask", "python app", "app"],
    "create_storage_bucket": ["bucket", "storage", "blob"],
    "create_service_account": ["service account", "identity"],
    "grant_iam_role": ["iam", "permission", "role", "access", "grant"],
    "create_scheduler_job": ["schedule", "scheduler", "cron", "nightly", "daily job", "daily"],
}


@dataclass(frozen=True)
class MatchResult:
    workflow: WorkflowName
    score: int
    confidence: float


class FakeRouter:
    """Deterministic router that mirrors the future model output contract."""

    def route(self, request_text: str) -> RouterOutput:
        text = request_text.strip()
        lowered = text.lower()
        candidates = self._candidate_workflows(lowered)

        if not candidates:
            return RouterOutput(
                status="needs_clarification",
                workflow=None,
                confidence=0.25,
                parameters={},
                candidate_workflows=[
                    CandidateWorkflow(workflow="create_web_app", confidence=0.25),
                    CandidateWorkflow(workflow="create_scheduler_job", confidence=0.23),
                ],
                failure_reasons=["No workflow keywords matched with enough confidence."],
                clarifying_question="Are you creating an app, storage, identity, IAM access, or a scheduled job?",
            )

        best = candidates[0]
        route_status = self._status_for_confidence(best.confidence)
        params = self._extract_parameters(best.workflow, lowered)
        missing_fields = self._rough_missing_fields(best.workflow, params)

        return RouterOutput(
            status=route_status,
            workflow=best.workflow,
            confidence=best.confidence,
            parameters=params,
            missing_fields=missing_fields,
            candidate_workflows=[
                CandidateWorkflow(workflow=item.workflow, confidence=item.confidence)
                for item in candidates[:3]
            ],
            failure_reasons=[],
            clarifying_question=self._clarifying_question(missing_fields, best.confidence),
        )

    def _candidate_workflows(self, lowered: str) -> list[MatchResult]:
        matches: list[MatchResult] = []
        for workflow, keywords in WORKFLOW_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in lowered)
            if score:
                confidence = min(0.95, 0.45 + (score * 0.24))
                if "thing" in lowered and score == 1:
                    confidence = min(confidence, 0.58)
                matches.append(MatchResult(workflow, score, round(confidence, 2)))
        return sorted(matches, key=lambda item: item.confidence, reverse=True)

    @staticmethod
    def _status_for_confidence(confidence: float) -> str:
        if confidence < 0.55:
            return "needs_clarification"
        if confidence < 0.80:
            return "requires_confirmation"
        return "routed"

    def _extract_parameters(self, workflow: WorkflowName, lowered: str) -> dict[str, Any]:
        common = {
            "environment": self._extract_environment(lowered),
            "team": self._extract_team(lowered),
        }
        if workflow == "create_web_app":
            return self._drop_empty(
                {
                    "app_name": self._extract_named_value(lowered) or self._derived_name(common["team"], "web-app"),
                    "region": self._extract_region(lowered),
                    "runtime": self._extract_runtime(lowered),
                    "environment": common["environment"],
                    "team": common["team"],
                    "diagnostics_enabled": "diagnostics" in lowered or "monitoring" in lowered,
                }
            )
        if workflow == "create_storage_bucket":
            return self._drop_empty(
                {
                    "bucket_name": self._extract_named_value(lowered) or self._derived_name(common["team"], "bucket"),
                    "region": self._extract_region(lowered),
                    "environment": common["environment"],
                    "team": common["team"],
                    "storage_class": self._extract_storage_class(lowered),
                    "public_access": True if "public" in lowered else None,
                }
            )
        if workflow == "create_service_account":
            return self._drop_empty(
                {
                    "account_name": self._extract_named_value(lowered) or self._derived_name(common["team"], "svc"),
                    "team": common["team"],
                    "environment": common["environment"],
                    "description": "Generated from RouterCore request preview.",
                }
            )
        if workflow == "grant_iam_role":
            return self._drop_empty(
                {
                    "principal": self._extract_principal(lowered),
                    "role": self._extract_role(lowered),
                    "scope": self._extract_scope(lowered),
                    "environment": common["environment"],
                    "duration": self._extract_duration(lowered),
                }
            )
        if workflow == "create_scheduler_job":
            target = self._extract_target(lowered)
            return self._drop_empty(
                {
                    "job_name": self._extract_named_value(lowered) or self._derived_name(target, "scheduled-job"),
                    "schedule": self._extract_schedule(lowered),
                    "target": target,
                    "environment": common["environment"],
                    "timezone": self._extract_timezone(lowered),
                    "team": common["team"],
                }
            )
        return {}

    @staticmethod
    def _drop_empty(params: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in params.items() if value is not None and value != ""}

    @staticmethod
    def _derived_name(prefix: str | None, suffix: str) -> str | None:
        if not prefix:
            return None
        safe_prefix = re.sub(r"[^a-z0-9-]+", "-", prefix.lower()).strip("-")
        return f"{safe_prefix}-{suffix}"

    @staticmethod
    def _extract_named_value(lowered: str) -> str | None:
        match = re.search(r"(?:named|called)\s+([a-z0-9-]+)", lowered)
        return match.group(1) if match else None

    @staticmethod
    def _extract_environment(lowered: str) -> str | None:
        if "production" in lowered or re.search(r"\bprod\b", lowered):
            return "prod"
        if "staging" in lowered or "stage" in lowered:
            return "staging"
        if "development" in lowered or re.search(r"\bdev\b", lowered):
            return "dev"
        return None

    @staticmethod
    def _extract_region(lowered: str) -> str | None:
        region_aliases = {
            "east us": "eastus",
            "eastus": "eastus",
            "west us": "westus",
            "westus": "westus",
            "central us": "centralus",
            "centralus": "centralus",
            "us central": "us-central1",
            "us-central1": "us-central1",
        }
        for alias, value in region_aliases.items():
            if alias in lowered:
                return value
        return None

    @staticmethod
    def _extract_runtime(lowered: str) -> str | None:
        if "python" in lowered or "flask" in lowered:
            return "python311"
        if "node" in lowered or "javascript" in lowered:
            return "nodejs20"
        if ".net" in lowered or "dotnet" in lowered:
            return "dotnet8"
        return None

    @staticmethod
    def _extract_team(lowered: str) -> str | None:
        match = re.search(r"for (?:the )?([a-z0-9-]+) team", lowered)
        if match:
            return match.group(1)
        match = re.search(r"team ([a-z0-9-]+)", lowered)
        return match.group(1) if match else None

    @staticmethod
    def _extract_storage_class(lowered: str) -> str | None:
        for value in ["standard", "cool", "archive"]:
            if value in lowered:
                return value
        return None

    @staticmethod
    def _extract_principal(lowered: str) -> str | None:
        match = re.search(r"grant ([a-z0-9_.@-]+)", lowered)
        return match.group(1) if match else None

    @staticmethod
    def _extract_role(lowered: str) -> str | None:
        role_aliases = ["owner", "admin", "reader", "contributor", "viewer", "editor"]
        for role in role_aliases:
            if role in lowered:
                return role
        match = re.search(r"role ([a-z0-9_-]+)", lowered)
        return match.group(1) if match else None

    @staticmethod
    def _extract_scope(lowered: str) -> str | None:
        match = re.search(r"(?:to|on|for) ([a-z0-9_./*-]+)", lowered)
        if match:
            return match.group(1)
        if "production" in lowered:
            return "production"
        return None

    @staticmethod
    def _extract_duration(lowered: str) -> str | None:
        match = re.search(r"for (\d+\s*(?:day|days|hour|hours|week|weeks))", lowered)
        return match.group(1) if match else None

    @staticmethod
    def _extract_schedule(lowered: str) -> str | None:
        if "nightly" in lowered:
            return "0 2 * * *"
        if "daily" in lowered:
            return "0 9 * * *"
        match = re.search(r"cron\s+([0-9*/,\-\s]+)", lowered)
        return match.group(1).strip() if match else None

    @staticmethod
    def _extract_target(lowered: str) -> str | None:
        match = re.search(r"for ([a-z0-9-]+)", lowered)
        if match:
            return match.group(1)
        match = re.search(r"target(?:ing)? ([a-z0-9-]+)", lowered)
        return match.group(1) if match else None

    @staticmethod
    def _extract_timezone(lowered: str) -> str | None:
        if "los angeles" in lowered or "pacific" in lowered:
            return "America/Los_Angeles"
        if "new york" in lowered or "eastern" in lowered:
            return "America/New_York"
        if "utc" in lowered:
            return "UTC"
        return None

    @staticmethod
    def _rough_missing_fields(workflow: WorkflowName, params: dict[str, Any]) -> list[str]:
        required = {
            "create_web_app": ["app_name", "region", "runtime", "environment"],
            "create_storage_bucket": ["bucket_name", "region", "environment"],
            "create_service_account": ["account_name", "team", "environment"],
            "grant_iam_role": ["principal", "role", "scope"],
            "create_scheduler_job": ["job_name", "schedule", "target", "environment"],
        }
        return [field for field in required[workflow] if field not in params]

    @staticmethod
    def _clarifying_question(missing_fields: list[str], confidence: float) -> str | None:
        if missing_fields:
            return f"What {missing_fields[0].replace('_', ' ')} should RouterCore use?"
        if confidence < 0.80:
            return "Please confirm the selected workflow and parameters."
        return None
