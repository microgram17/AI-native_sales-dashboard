from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ColumnSpec(BaseModel):
    key: str
    label: str
    type: str
    unit: str | None = None
    description: str | None = None


class VisualizationSpec(BaseModel):
    type: str
    title: str
    x_key: str | None = None
    y_keys: list[str] = Field(default_factory=list)
    series_key: str | None = None
    value_key: str | None = None
    description: str | None = None


class DataQuality(BaseModel):
    row_count: int
    is_partial: bool = False
    warnings: list[str] = Field(default_factory=list)


class ToolResultPayload(BaseModel):
    result_type: str
    title: str
    columns: list[ColumnSpec]
    rows: list[dict[str, Any]]
    recommended_visualizations: list[VisualizationSpec] = Field(default_factory=list)
    description: str | None = None
    data_quality: DataQuality | None = None

    # Optional metadata fields — mirrors mcp_server ToolResult.
    # Ignored by existing dashboard consumers; used by agent-oriented tools.
    applied_filters: dict[str, Any] = Field(default_factory=dict)
    primary_metric: str | None = None
    dimension: str | None = None
    result_intent: str | None = None  # "single_winner" | "ranking" | "timeseries" | "breakdown"
