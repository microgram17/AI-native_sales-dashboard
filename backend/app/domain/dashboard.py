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

    # Optional metadata from agent-oriented tools — ignored by existing dashboard consumers.
    applied_filters: dict[str, Any] = Field(default_factory=dict)
    primary_metric: str | None = None
    dimension: str | None = None
    result_intent: str | None = None

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
            applied_filters=payload.applied_filters,
            primary_metric=payload.primary_metric,
            dimension=payload.dimension,
            result_intent=payload.result_intent,
        )


class DashboardResponse(BaseModel):
    user: UserInfo
    cards: list[KpiCard]
    artifacts: list[DashboardArtifact]


# --- Widget-specific response models ---

class SummaryResponse(BaseModel):
    date_from: str | None
    date_to: str | None
    gross_sales: float
    net_sales: float
    discounts: float
    units: int
    orders: int


class TimeseriesRow(BaseModel):
    period: str
    product_id: str
    product_name: str
    category: str
    value: float


class ProductTimeseriesResponse(BaseModel):
    date_from: str | None
    date_to: str | None
    grain: str
    metric: str
    limit_products: int
    rows: list[TimeseriesRow]


class TopProductsRow(BaseModel):
    rank: int
    product_id: str
    product_name: str
    category: str
    net_sales: float
    gross_sales: float
    units: int
    orders: int
    discounts: float


class TopProductsResponse(BaseModel):
    date_from: str | None
    date_to: str | None
    sort_by: str
    limit: int
    rows: list[TopProductsRow]


class ProductSelectorItem(BaseModel):
    product_id: str
    product_name: str
    category: str
    net_sales: float
    units: int


class ProductsResponse(BaseModel):
    date_from: str | None
    date_to: str | None
    products: list[ProductSelectorItem]
