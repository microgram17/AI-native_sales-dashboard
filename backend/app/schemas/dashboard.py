from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

Metric = Literal["net_sales", "gross_sales", "units", "orders", "discounts"]
Grain = Literal["week", "month"]
StoreGroupBy = Literal["store", "city", "channel"]
ProductSortDirection = Literal["asc", "desc"]


class SummaryResponse(BaseModel):
    date_from: date | None = None
    date_to: date | None = None
    gross_sales: float
    net_sales: float
    discounts: float
    units: int
    orders: int


class SalesTimeseriesRow(BaseModel):
    period: date
    value: float


class SalesTimeseriesResponse(BaseModel):
    date_from: date | None = None
    date_to: date | None = None
    grain: Grain
    metric: Metric
    rows: list[SalesTimeseriesRow]


class TimeseriesRow(BaseModel):
    period: date
    product_id: str
    product_name: str
    category: str
    value: float


class ProductTimeseriesResponse(BaseModel):
    date_from: date | None = None
    date_to: date | None = None
    grain: Grain
    metric: Metric
    limit_products: int = Field(ge=1, le=20)
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
    date_from: date | None = None
    date_to: date | None = None
    sort_by: Metric
    limit: int = Field(ge=1, le=50)
    rows: list[TopProductsRow]


class ProductTableResponse(BaseModel):
    date_from: date | None = None
    date_to: date | None = None
    sort_by: Metric
    sort_direction: ProductSortDirection
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=50)
    total: int = Field(ge=0)
    rows: list[TopProductsRow]


class ProductSelectorItem(BaseModel):
    product_id: str
    product_name: str
    category: str
    net_sales: float
    units: int


class ProductsResponse(BaseModel):
    date_from: date | None = None
    date_to: date | None = None
    products: list[ProductSelectorItem]


class StoreBreakdownRow(BaseModel):
    group_id: str
    group_name: str
    value: float


class StoreBreakdownResponse(BaseModel):
    date_from: date | None = None
    date_to: date | None = None
    metric: Metric
    group_by: StoreGroupBy
    rows: list[StoreBreakdownRow]


class PerformanceTimeseriesRow(BaseModel):
    period: date
    group_id: str
    group_name: str
    value: float


class PerformanceTimeseriesResponse(BaseModel):
    date_from: date | None = None
    date_to: date | None = None
    grain: Grain
    metric: Metric
    group_by: StoreGroupBy
    limit_groups: int = Field(ge=1, le=5)
    rows: list[PerformanceTimeseriesRow]
