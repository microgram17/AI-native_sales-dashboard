
"""Graph wrapper for the deterministic visualization builder."""

from __future__ import annotations

import json
from typing import Any

from google.adk.agents.context import Context
from google.adk.workflow import BaseNode, node

from app.agents.request_state import coerce_request
from app.agents.state import StateKeys
from app.agents.visualization_builder import (
    build_visualization_plan,
)
from app.schemas.visualization import (
    VisualizationDataset,
)


def _coerce_datasets(
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


def build_build_visualizations_node() -> BaseNode:
    def build_visualizations(
        ctx: Context,
        canonical_request_json: Any = "null",
        visualization_datasets_json: Any = "[]",
        ui_language: str = "en",
    ) -> None:
        request = coerce_request(
            canonical_request_json
        )
        if request is None:
            ctx.state[
                StateKeys.VISUALIZATION_PLAN
            ] = {"visualizations": []}
            return

        datasets = _coerce_datasets(
            visualization_datasets_json
        )
        plan = build_visualization_plan(
            request,
            datasets,
            ui_language,
        )
        ctx.state[
            StateKeys.VISUALIZATION_PLAN
        ] = plan.model_dump(mode="json")

    return node(
        build_visualizations,
        name="build_visualizations",
    )
