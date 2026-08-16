"""Deterministic response composer node (no LLM call)."""

from __future__ import annotations

import json
from typing import Any

from google.adk.agents.context import Context
from google.adk.workflow import BaseNode, node

from app.agents.state import ExecutedToolCall, StateKeys
from app.schemas.agent import AgentQueryResponse, Dataset, ToolCallInfo
from app.schemas.visualization import VisualizationDataset, VisualizationPlan


def _coerce_viz(value: Any) -> VisualizationPlan:
    if isinstance(value, VisualizationPlan):
        return value
    if isinstance(value, dict):
        return VisualizationPlan.model_validate(value)
    if isinstance(value, str) and value.strip():
        return VisualizationPlan.model_validate_json(value)
    return VisualizationPlan()


def _coerce_viz_datasets(
    value: str | list[dict[str, Any]] | None,
) -> list[VisualizationDataset]:
    if value is None:
        return []
    raw: Any = value
    if isinstance(value, str):
        if not value.strip():
            return []
        try:
            raw = json.loads(value)
        except json.JSONDecodeError:
            return []
    if not isinstance(raw, list):
        return []
    return [VisualizationDataset.model_validate(item) for item in raw]


def build_compose_response_node() -> BaseNode:
    def compose_response(
        ctx: Context,
        tool_results: list[dict[str, Any]] | None = None,
        visualization_plan: Any = None,
        visualization_datasets_json: str = "[]",
        analysis: str | None = None,
        conversation_id: str = "",
    ) -> None:
        results = [ExecutedToolCall.model_validate(r) for r in (tool_results or [])]
        viz = _coerce_viz(visualization_plan)
        viz_datasets = _coerce_viz_datasets(visualization_datasets_json)

        valid_dataset_ids = {dataset.id for dataset in viz_datasets}
        specs = [spec for spec in viz.visualizations if spec.dataset in valid_dataset_ids]

        message = (analysis or "").strip()
        if not message:
            message = (
                "Updated the visualization using the existing data."
                if specs
                else "No analysis was produced."
            )

        response = AgentQueryResponse(
            conversation_id=conversation_id,
            message=message,
            tool_calls=[
                ToolCallInfo(
                    call_id=r.call_id,
                    tool_name=r.tool_name,
                    arguments=r.arguments,
                    purpose=r.purpose,
                    status=r.status,
                    error=r.error,
                )
                for r in results
            ],
            datasets=[
                Dataset(
                    call_id=r.call_id,
                    tool_name=r.tool_name,
                    status=r.status or "success",
                    result=r.result or {},
                )
                for r in results
                if r.is_success
            ],
            visualization_datasets=viz_datasets,
            visualizations=specs,
        )
        ctx.state[StateKeys.RESPONSE] = response.model_dump(mode="json")

    return node(compose_response, name="compose_response")
