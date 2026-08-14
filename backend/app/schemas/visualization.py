from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

VisualizationType = Literal[
    "metric_cards",
    "bar_chart",
    "line_chart",
    "table",
]


class VisualizationSpec(BaseModel):
    """Advisory rendering hint for one tool result. It carries no MCP or backend
    business logic; the frontend decides how to render it."""

    dataset: str = Field(description="call_id of the tool result this visualizes.")
    type: VisualizationType
    title: str
    x_key: str | None = None
    y_keys: list[str] = Field(default_factory=list)
    series_key: str | None = None


class VisualizationPlan(BaseModel):
    """Structured visualization-agent output (ADK LlmAgent output_schema)."""

    visualizations: list[VisualizationSpec] = Field(default_factory=list)
