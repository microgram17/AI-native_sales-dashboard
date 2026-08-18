"""Deterministic response composer node (no LLM call).

A validated visualization is allowed to be the complete assistant answer. When
the response-policy gate intentionally skips analytics, message therefore stays
empty instead of adding generic filler such as "see the visualization below".
"""

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

    return [
        VisualizationDataset.model_validate(item)
        for item in raw
    ]


def build_compose_response_node() -> BaseNode:
    def compose_response(
        ctx: Context,
        tool_results: list[dict[str, Any]] | None = None,
        visualization_plan: Any = None,
        visualization_datasets_json: str = "[]",
        analysis: str | None = None,
        conversation_id: str = "",
        ui_language: str = "en",
    ) -> None:
        results = [
            ExecutedToolCall.model_validate(result)
            for result in (tool_results or [])
        ]
        viz = _coerce_viz(visualization_plan)
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

        # Empty prose is intentional when a visualization completely answers a
        # straightforward request. ChatMessage already supports rendering a
        # visualization without a text block.
        message = (analysis or "").strip()

        # Only fall back to text when neither prose nor a valid visualization
        # exists. Never add generic filler above a visualization.
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
                    status=result.status or "success",
                    result=result.result or {},
                )
                for result in results
                if result.is_success
            ],
            visualization_datasets=viz_datasets,
            visualizations=specs,
        )
        ctx.state[StateKeys.RESPONSE] = response.model_dump(
            mode="json"
        )

    return node(
        compose_response,
        name="compose_response",
    )
