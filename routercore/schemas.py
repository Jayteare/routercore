from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from routercore.models import WorkflowName, WorkflowSchema


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = PROJECT_ROOT / "data" / "schemas"


@lru_cache(maxsize=1)
def load_workflow_schemas() -> dict[str, WorkflowSchema]:
    schemas: dict[str, WorkflowSchema] = {}
    for path in sorted(SCHEMA_DIR.glob("*.json")):
        with path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
        schema = WorkflowSchema.model_validate(raw)
        schemas[schema.workflow] = schema
    return schemas


def get_workflow_schema(workflow: WorkflowName | str | None) -> WorkflowSchema | None:
    if workflow is None:
        return None
    return load_workflow_schemas().get(str(workflow))


def list_workflows() -> list[str]:
    return sorted(load_workflow_schemas())
