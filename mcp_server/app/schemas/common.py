from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


ColumnType = Literal[
    "string",
    "integer",
    "number",
    "currency",
    "percent",
    "date",
    "datetime",
    "boolean",
]

ResultType = Literal[
    "kpi",
    "timeseries",
    "ranking",
    "breakdown",
    "table",
]

ChartType = Literal[
    "line_chart",
    "bar_chart",
    "metric_card",
    "table",
]

TimeGrain = Literal["week", "month"]

SupplierSalesMetric = Literal[
    "net_sales",
    "gross_sales",
    "units",
    "discounts",
    "orders",
]


class ColumnSpec(BaseModel):
    key: str
    label: str
    type: ColumnType
    unit: str | None = None
    description: str | None = None


class DataQuality(BaseModel):
    row_count: int
    is_partial: bool = False
    warnings: list[str] = Field(default_factory=list)


class VisualizationSpec(BaseModel):
    type: ChartType
    title: str

    x_key: str | None = None
    y_keys: list[str] = Field(default_factory=list)
    series_key: str | None = None
    value_key: str | None = None

    description: str | None = None

    @model_validator(mode="after")
    def validate_chart_keys(self) -> "VisualizationSpec":
        if self.type in {"line_chart", "bar_chart"}:
            if not self.x_key:
                raise ValueError(f"{self.type} requires x_key")
            if not self.y_keys:
                raise ValueError(f"{self.type} requires at least one y_key")

        if self.type == "metric_card" and not self.value_key:
            raise ValueError("metric_card requires value_key")

        return self


class ToolResult(BaseModel):
    model_config = ConfigDict(
        json_encoders={
            Decimal: float,
            date: lambda v: v.isoformat(),
            datetime: lambda v: v.isoformat(),
        }
    )

    result_type: ResultType
    title: str
    columns: list[ColumnSpec]
    rows: list[dict[str, Any]]

    recommended_visualizations: list[VisualizationSpec] = Field(default_factory=list)

    description: str | None = None
    data_quality: DataQuality | None = None

    # Optional metadata fields — ignored by existing dashboard consumers.
    # Used by agent-oriented tools to communicate intent and applied filters.
    applied_filters: dict[str, Any] = Field(default_factory=dict)
    primary_metric: str | None = None
    dimension: str | None = None
    result_intent: str | None = None  # "single_winner" | "ranking" | "timeseries" | "breakdown"

    @model_validator(mode="after")
    def validate_visualization_keys_exist(self) -> "ToolResult":
        column_keys = {column.key for column in self.columns}

        for viz in self.recommended_visualizations:
            keys: list[str] = []

            if viz.x_key:
                keys.append(viz.x_key)

            if viz.series_key:
                keys.append(viz.series_key)

            if viz.value_key:
                keys.append(viz.value_key)

            keys.extend(viz.y_keys)

            missing = [key for key in keys if key not in column_keys]

            if missing:
                raise ValueError(
                    f"Visualization '{viz.title}' references unknown columns: {missing}"
                )

        return self