from __future__ import annotations

from pydantic import BaseModel

from app.domain.tool_result import ToolResultPayload


class UserInfo(BaseModel):
    user_id: str
    display_name: str
    supplier_id: str


class KpiCard(BaseModel):
    key: str
    label: str
    value: float
    unit: str | None = None


class DashboardArtifact(ToolResultPayload):
    """A ToolResultPayload annotated with the MCP tool that produced it.

    Inherits all analytics fields (columns, rows, recommended_visualizations,
    result_intent, etc.) from ToolResultPayload and adds source_tool so dashboard
    and chat consumers can locate a specific artifact by its originating tool.
    """

    source_tool: str

    @classmethod
    def from_tool_result(cls, source_tool: str, payload: ToolResultPayload) -> "DashboardArtifact":
        return cls(source_tool=source_tool, **payload.model_dump())


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
