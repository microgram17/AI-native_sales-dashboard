
"""Deterministically assemble the stable frontend AgentQueryResponse contract."""

from __future__ import annotations

import json
from typing import Any

from google.adk.agents.context import Context
from google.adk.workflow import BaseNode, node

from app.agents.state import ExecutedToolCall, StateKeys
from app.schemas.agent import (
    AgentQueryResponse,
    Dataset,
    ToolCallInfo,
)
from app.schemas.visualization import (
    VisualizationDataset,
    VisualizationPlan,
)


def _coerce_viz(
    value: Any,
) -> VisualizationPlan:
    if isinstance(value, VisualizationPlan):
        return value
    if isinstance(value, dict):
        try:
            return VisualizationPlan.model_validate(
                value
            )
        except Exception:
            return VisualizationPlan()
    if isinstance(value, str) and value.strip():
        try:
            return VisualizationPlan.model_validate_json(
                value
            )
        except Exception:
            return VisualizationPlan()
    return VisualizationPlan()


def _coerce_viz_datasets(
    value: Any,
) -> list[VisualizationDataset]:
    raw = value
    if isinstance(value, str):
        if not value.strip():
            return []
        try:
            raw = json.loads(value)
        except json.JSONDecodeError:
            return []

    if not isinstance(raw, list):
        return []

    return [
        VisualizationDataset.model_validate(item)
        for item in raw
    ]


def build_compose_response_node() -> BaseNode:
    def compose_response(
        ctx: Context,
        tool_results: list[dict[str, Any]] | None = None,
        visualization_plan: Any = None,
        visualization_datasets_json: Any = "[]",
        analysis: str | None = None,
        direct_message: str | None = None,
        conversation_id: str = "",
        ui_language: str = "en",
    ) -> None:
        results = [
            ExecutedToolCall.model_validate(
                result
            )
            for result in (tool_results or [])
        ]
        viz = _coerce_viz(
            visualization_plan
        )
        viz_datasets = _coerce_viz_datasets(
            visualization_datasets_json
        )

        valid_dataset_ids = {
            dataset.id
            for dataset in viz_datasets
        }
        specs = [
            spec
            for spec in viz.visualizations
            if spec.dataset in valid_dataset_ids
        ]

        message = (
            (direct_message or "").strip()
            or (analysis or "").strip()
        )

        if not message and not specs:
            message = (
                "Inget svar kunde genereras."
                if ui_language == "sv"
                else "No response was produced."
            )

        response = AgentQueryResponse(
            conversation_id=conversation_id,
            message=message,
            tool_calls=[
                ToolCallInfo(
                    call_id=result.call_id,
                    tool_name=result.tool_name,
                    arguments=result.arguments,
                    purpose=result.purpose,
                    status=result.status,
                    error=result.error,
                )
                for result in results
            ],
            datasets=[
                Dataset(
                    call_id=result.call_id,
                    tool_name=result.tool_name,
                    status=(
                        result.status
                        or "success"
                    ),
                    result=result.result or {},
                )
                for result in results
                if result.is_success
            ],
            visualization_datasets=viz_datasets,
            visualizations=specs,
        )

        ctx.state[
            StateKeys.RESPONSE
        ] = response.model_dump(
            mode="json"
        )

    return node(
        compose_response,
        name="compose_response",
    )
