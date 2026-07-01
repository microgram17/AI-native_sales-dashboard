from __future__ import annotations

from pydantic import BaseModel


class LatestMarketShare(BaseModel):
    period: str
    estimated_market_share_pct: float


class SupplierSummaryResponse(BaseModel):
    supplier_code: str
    found: bool
    message: str | None = None
    supplier_name: str | None = None
    total_orders: int = 0
    total_units: int = 0
    total_revenue: float = 0.0
    estimated_margin: float = 0.0
    average_order_value: float = 0.0
    latest_market_share: LatestMarketShare | None = None


class RevenueTrendPoint(BaseModel):
    period_start: str
    period_label: str
    supplier_revenue: float
    comparable_market_revenue: float
    estimated_market_share_pct: float


class RevenueTrendResponse(BaseModel):
    supplier_code: str
    period_type: str
    found: bool
    message: str | None = None
    points: list[RevenueTrendPoint] = []


class TopProduct(BaseModel):
    sku: str
    product_name: str
    category: str
    total_revenue: float
    total_units: int
    total_orders: int


class TopProductsResponse(BaseModel):
    supplier_code: str
    found: bool
    sort_by: str = ""
    limit: int = 0
    message: str | None = None
    products: list[TopProduct] = []


class SupplierListItem(BaseModel):
    supplier_code: str
    supplier_name: str
    primary_brand: str | None = None
    primary_category: str | None = None


class SupplierListResponse(BaseModel):
    count: int
    suppliers: list[SupplierListItem]


# ── New tools ──────────────────────────────────────────────────────────────────


class PeriodSummaryResponse(BaseModel):
    supplier_code: str
    date_from: str
    date_to: str
    found: bool
    message: str | None = None
    total_orders: int = 0
    total_units: int = 0
    total_revenue: float = 0.0
    estimated_margin: float = 0.0
    average_order_value: float = 0.0


class SalesByChannelItem(BaseModel):
    dimension_value: str
    total_revenue: float
    total_units: int
    total_orders: int
    estimated_margin: float


class SalesByChannelResponse(BaseModel):
    supplier_code: str
    dimension: str
    date_from: str | None = None
    date_to: str | None = None
    found: bool
    message: str | None = None
    items: list[SalesByChannelItem] = []


class SalesByCategoryItem(BaseModel):
    dimension_value: str
    total_revenue: float
    total_units: int
    total_orders: int
    estimated_margin: float


class SalesByCategoryResponse(BaseModel):
    supplier_code: str
    dimension: str
    date_from: str | None = None
    date_to: str | None = None
    found: bool
    message: str | None = None
    items: list[SalesByCategoryItem] = []


# ── Analytics agent tools ──────────────────────────────────────────────────────


class SupplierDashboardDataResponse(BaseModel):
    found: bool
    supplier_code: str
    message: str | None = None
    summary: SupplierSummaryResponse | None = None
    trend: RevenueTrendResponse | None = None
    top_products: TopProductsResponse | None = None


class AnalyticsFilters(BaseModel):
    start_date: str | None = None
    end_date: str | None = None
    region: str | None = None
    city: str | None = None
    category: str | None = None
    brand: str | None = None
    sales_channel: str | None = None
    customer_segment: str | None = None
    sku: str | None = None


class AnalyticsResultRow(BaseModel):
    dimensions: dict[str, str]
    value: float
    extra_metrics: dict[str, float] | None = None


class AnalyticsQueryResponse(BaseModel):
    found: bool
    supplier_code: str
    metric: str
    dimensions: list[str] = []
    filters: dict | None = None
    time_grain: str | None = None
    items: list[AnalyticsResultRow] = []
    total_items: int = 0
    message: str | None = None


class ProductTrendPoint(BaseModel):
    period: str
    total_revenue: float
    total_units: int
    total_orders: int


class ProductTrendResponse(BaseModel):
    supplier_code: str
    sku: str
    product_name: str | None = None
    period_type: str
    found: bool
    message: str | None = None
    points: list[ProductTrendPoint] = []
