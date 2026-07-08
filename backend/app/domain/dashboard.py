from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.domain.tool_result import ColumnSpec, DataQuality, ToolResultPayload, VisualizationSpec


class UserInfo(BaseModel):
    user_id: str
    display_name: str
    supplier_id: str


class KpiCard(BaseModel):
    key: str
    label: str
    value: float
    unit: str | None = None


class DashboardArtifact(BaseModel):
    source_tool: str
    result_type: str
    title: str
    columns: list[ColumnSpec]
    rows: list[dict[str, Any]]
    recommended_visualizations: list[VisualizationSpec] = Field(default_factory=list)
    description: str | None = None
    data_quality: DataQuality | None = None

    @classmethod
    def from_tool_result(cls, source_tool: str, payload: ToolResultPayload) -> "DashboardArtifact":
        return cls(
            source_tool=source_tool,
            result_type=payload.result_type,
            title=payload.title,
            columns=payload.columns,
            rows=payload.rows,
            recommended_visualizations=payload.recommended_visualizations,
            description=payload.description,
            data_quality=payload.data_quality,
        )


class DashboardResponse(BaseModel):
    user: UserInfo
    cards: list[KpiCard]
    artifacts: list[DashboardArtifact]
