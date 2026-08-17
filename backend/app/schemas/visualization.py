from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

VisualizationType = Literal[
    "metric_cards",
    "bar_chart",
    "line_chart",
    "table",
]


class VisualizationDataset(BaseModel):
    """Flat, deterministic rows prepared specifically for visualization."""

    id: str = Field(description="Stable visualization dataset id, e.g. 'c1:ranking'.")
    source_call_id: str = Field(description="call_id of the MCP tool result this view came from.")
    view: str = Field(description="Semantic view name, e.g. current, comparison, ranking or trend.")
    rows: list[dict[str, Any]] = Field(default_factory=list)


class VisualizationSpec(BaseModel):
    """Rendering instruction over one normalized VisualizationDataset."""

    dataset: str = Field(description="VisualizationDataset.id to render.")
    type: VisualizationType
    title: str
    x_key: str | None = None
    y_keys: list[str] = Field(default_factory=list)
    secondary_y_keys: list[str] = Field(
        default_factory=list,
        description=(
            "Subset of y_keys rendered on the secondary/right Y axis. "
            "Used only by line_chart visualizations."
        ),
    )
    series_key: str | None = None
    columns: list[str] = Field(
        default_factory=list,
        description="Exact columns to render for table visualizations.",
    )


class VisualizationPlan(BaseModel):
    """Structured visualization-agent output (ADK LlmAgent output_schema)."""

    visualizations: list[VisualizationSpec] = Field(default_factory=list)
