from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


Metric = Literal["net_sales", "gross_sales", "units", "discounts", "orders"]
Dimension = Literal["period", "product", "category", "store", "city", "channel"]
TimeGrain = Literal["day", "week", "month"]
Channel = Literal["online", "physical"]
SortDirection = Literal["asc", "desc"]

ColumnType = Literal["string", "integer", "number", "currency", "date", "boolean"]
ResultType = Literal["summary", "timeseries", "ranking", "table"]
ResultIntent = Literal["summary", "timeseries", "ranking", "single_winner", "table"]
VisualizationType = Literal["line_chart", "bar_chart", "metric_cards", "table"]


class MetricInfo(BaseModel):
    label: str
    column_type: ColumnType
    unit: str | None = None


METRIC_INFO: dict[Metric, MetricInfo] = {
    "net_sales": MetricInfo(label="Net sales", column_type="currency", unit="SEK"),
    "gross_sales": MetricInfo(label="Gross sales", column_type="currency", unit="SEK"),
    "units": MetricInfo(label="Units sold", column_type="integer"),
    "discounts": MetricInfo(label="Discounts", column_type="currency", unit="SEK"),
    "orders": MetricInfo(label="Orders", column_type="integer"),
}


DIMENSION_LABELS: dict[Dimension, str] = {
    "period": "Period",
    "product": "Product",
    "category": "Category",
    "store": "Store",
    "city": "City",
    "channel": "Channel",
}


DIMENSION_OUTPUT_KEYS: dict[Dimension, list[str]] = {
    "period": ["period"],
    "product": ["product_id", "product_name"],
    "category": ["category"],
    "store": ["store_id", "store_name"],
    "city": ["city"],
    "channel": ["channel"],
}


DIMENSION_DISPLAY_KEY: dict[Dimension, str] = {
    "period": "period",
    "product": "product_name",
    "category": "category",
    "store": "store_name",
    "city": "city",
    "channel": "channel",
}


class SalesFilters(BaseModel):
    """Reusable filters. Every filter must work with every sales query shape."""

    date_from: date | None = None
    date_to: date | None = None

    product_ids: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    store_ids: list[str] = Field(default_factory=list)
    cities: list[str] = Field(default_factory=list)
    channels: list[Channel] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_dates(self) -> "SalesFilters":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from cannot be after date_to")
        return self

    def without_empty_values(self) -> dict[str, Any]:
        """Return a compact filter dict for result metadata."""
        data = self.model_dump(mode="json")
        return {
            key: value
            for key, value in data.items()
            if value is not None and value != []
        }


class SalesOrderBy(BaseModel):
    """Sort by one selected metric or one selected output dimension key."""

    field: str
    direction: SortDirection = "desc"


class SalesQuery(BaseModel):
    """Composable sales query over v_supplier_sales_facts.

    This is intentionally not a dashboard/report model. It is a small analytical
    query language: metrics + dimensions + filters + optional grain/sort/limit.
    """

    metrics: list[Metric]
    dimensions: list[Dimension] = Field(default_factory=list)
    filters: SalesFilters = Field(default_factory=SalesFilters)

    grain: TimeGrain | None = None
    order_by: SalesOrderBy | None = None
    limit: int | None = Field(default=None, ge=1, le=500)

    @model_validator(mode="after")
    def validate_query(self) -> "SalesQuery":
        if not self.metrics:
            raise ValueError("metrics must contain at least one metric")

        if len(set(self.metrics)) != len(self.metrics):
            raise ValueError("metrics cannot contain duplicates")

        if len(set(self.dimensions)) != len(self.dimensions):
            raise ValueError("dimensions cannot contain duplicates")

        if "period" in self.dimensions and self.grain is None:
            raise ValueError("grain is required when dimensions includes 'period'")

        if "period" not in self.dimensions and self.grain is not None:
            raise ValueError("grain is only valid when dimensions includes 'period'")

        if self.order_by is not None:
            allowed = self.allowed_order_fields()
            if self.order_by.field not in allowed:
                raise ValueError(
                    f"order_by.field must be one of {sorted(allowed)} for this query; "
                    f"got {self.order_by.field!r}"
                )

        return self

    def output_dimension_keys(self) -> list[str]:
        keys: list[str] = []
        for dimension in self.dimensions:
            keys.extend(DIMENSION_OUTPUT_KEYS[dimension])
        return keys

    def allowed_order_fields(self) -> set[str]:
        """Fields that can appear in ORDER BY.

        Allows metric keys, concrete output dimension keys, and dimension names
        that map to their display key (e.g. "product" -> "product_name").
        """
        allowed: set[str] = set(self.metrics)
        allowed.update(self.output_dimension_keys())
        allowed.update(self.dimensions)
        return allowed


class ColumnSpec(BaseModel):
    key: str
    label: str
    type: ColumnType
    unit: str | None = None


class VisualizationSpec(BaseModel):
    type: VisualizationType
    title: str
    x_key: str | None = None
    y_keys: list[str] = Field(default_factory=list)
    series_key: str | None = None


class SalesQueryResult(BaseModel):
    result_type: ResultType
    result_intent: ResultIntent

    title: str
    columns: list[ColumnSpec]
    rows: list[dict[str, Any]]

    metrics: list[Metric]
    dimensions: list[Dimension]
    filters: SalesFilters

    primary_metric: Metric | None = None
    primary_dimension: Dimension | None = None

    recommended_visualization: VisualizationSpec | None = None

    @property
    def row_count(self) -> int:
        return len(self.rows)
