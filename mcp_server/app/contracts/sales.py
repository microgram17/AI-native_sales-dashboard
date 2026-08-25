"""Typed MCP contract models for the supplier sales analytics tools.

These models define the model-visible input scope and the structured output
returned by the analytics tools. They contain no visualization hints,
chart types or frontend component information — only semantic analytical data.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# ── Enumerations (dynamic SQL identifiers derive only from these) ───────────────

Channel = Literal["online", "physical"]
GroupBy = Literal["product", "category", "store", "city", "channel"]
SplitBy = GroupBy
EntityType = GroupBy
# Only additive metrics can be ranked; averages/rates remain supporting metrics.
RankBy = Literal[
    "units",
    "net_sales",
    "gross_sales",
    "orders",
    "discounts",
]
RankOrder = Literal["highest", "lowest"]
TrendGrain = Literal["day", "week", "month", "quarter"]
Status = Literal["success", "no_data", "not_found", "ambiguous"]
ProductResolutionStatus = Literal["success", "not_found", "ambiguous"]
DataViewKind = Literal["metrics", "categorical", "timeseries"]
DataFieldRole = Literal["dimension", "measure"]
DataFieldFormat = Literal[
    "text",
    "date",
    "integer",
    "decimal",
    "currency_sek",
    "percentage_fraction",
]


# ── Model-visible scope ─────────────────────────────────────────────────────────


class SalesScope(BaseModel):
    """Optional filters applied to a sales query. An empty list means no
    restriction on that dimension (e.g. empty ``channels`` = all channels)."""

    model_config = ConfigDict(extra="forbid")

    channels: list[Channel] = Field(
        default_factory=list,
        description="Restrict to these sales channels. Empty = all channels.",
    )
    cities: list[str] = Field(
        default_factory=list,
        description="Restrict to these store cities. Empty = all cities.",
    )
    store_ids: list[str] = Field(
        default_factory=list,
        description="Restrict to these store IDs. Empty = all stores.",
    )
    categories: list[str] = Field(
        default_factory=list,
        description="Restrict to these product categories. Empty = all categories.",
    )
    product_ids: list[str] = Field(
        default_factory=list,
        description=(
            "Restrict to canonical product IDs only, e.g. 'NORD-HOD-011'. "
            "Do not pass product names here. Named products must be resolved "
            "to canonical IDs first (or handled by product_overview)."
        ),
    )


class ProductOverviewScope(BaseModel):
    """Filters for a single-product overview. An empty list means no restriction
    on that dimension. product_ids and categories are intentionally not accepted."""

    model_config = ConfigDict(extra="forbid")

    channels: list[Channel] = Field(
        default_factory=list,
        description="Restrict to these sales channels. Empty = all channels.",
    )
    cities: list[str] = Field(
        default_factory=list,
        description="Restrict to these store cities. Empty = all cities.",
    )
    store_ids: list[str] = Field(
        default_factory=list,
        description="Restrict to these store IDs. Empty = all stores.",
    )


# ── Shared value objects ────────────────────────────────────────────────────────


class EffectivePeriod(BaseModel):
    """The date range actually used by a query."""

    model_config = ConfigDict(extra="forbid")

    start: date
    end: date
    label: str | None = None
    defaulted: bool = Field(
        default=False,
        description="True when no explicit period was supplied and the full "
        "available supplier range was used.",
    )


class AnalyticsEntity(BaseModel):
    """A business entity a metric snapshot describes."""

    model_config = ConfigDict(extra="forbid")

    type: EntityType
    id: str | None = None
    name: str


class DataField(BaseModel):
    """Semantic metadata used by clients to format a flat result field."""

    model_config = ConfigDict(extra="forbid")

    key: str
    role: DataFieldRole
    format: DataFieldFormat


class DataView(BaseModel):
    """A flat, renderer-neutral analytical view.

    ``kind`` describes the data shape rather than a concrete chart library or
    component. Clients may render metrics as cards, categorical data as bars,
    and timeseries data as lines, or fall back to a table.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    kind: DataViewKind
    rows: list[dict[str, Any]] = Field(default_factory=list)
    fields: list[DataField] = Field(default_factory=list)
    primary_dimension: str | None = None
    series_dimension: str | None = None
    default_measures: list[str] = Field(default_factory=list)
    default_visible: bool = True


class AnalyticsContext(BaseModel):
    """The effective query semantics shared by all views in one result."""

    model_config = ConfigDict(extra="forbid")

    operation: Literal["summary", "ranking", "trend", "product_overview"]
    effective_period: EffectivePeriod
    effective_scope: SalesScope
    grain: TrendGrain | None = None
    group_by: GroupBy | None = None
    rank_by: RankBy | None = None
    order: RankOrder | None = None
    split_by: SplitBy | None = None
    entity: AnalyticsEntity | None = None


class AnalyticsResult(BaseModel):
    """Common public result returned by every analytics MCP tool."""

    model_config = ConfigDict(extra="forbid")

    status: Status
    context: AnalyticsContext
    warnings: list[str] = Field(default_factory=list)
    candidates: list[AnalyticsEntity] = Field(default_factory=list)
    views: list[DataView] = Field(default_factory=list)


class MetricSnapshot(BaseModel):
    """The standard metric set for a group of sales rows."""

    units: int = Field(description="Number of units sold.")
    net_sales: float = Field(description="Net sales in SEK.")
    gross_sales: float = Field(description="Gross sales in SEK.")
    discounts: float = Field(description="Discount amount in SEK.")
    orders: int = Field(description="Number of distinct orders at this result grain.")
    average_selling_price: float | None = Field(
        default=None,
        description="Net sales per unit in SEK (net_sales / units); null when units is 0.",
    )
    discount_rate: float | None = Field(
        default=None,
        description=(
            "Discounts divided by gross sales as a fraction from 0 to 1; "
            "for example 0.0355 means 3.55%. Null when gross_sales is 0."
        ),
    )


class MetricChange(BaseModel):
    """Period-over-period change for a single metric."""

    current: float
    previous: float | None = None
    absolute_change: float | None = Field(
        default=None,
        description=(
            "Current minus previous in the metric's native units. For ratio metrics "
            "such as discount_rate, this is a fractional-point difference; e.g. "
            "-0.0142 means a decrease of 1.42 percentage points."
        ),
    )
    percent_change: float | None = Field(
        default=None,
        description=(
            "Relative percentage change versus previous, calculated as "
            "(current - previous) / previous * 100."
        ),
    )


class MetricChanges(BaseModel):
    """Period-over-period change for each standard metric."""

    units: MetricChange | None = None
    net_sales: MetricChange | None = None
    gross_sales: MetricChange | None = None
    discounts: MetricChange | None = None
    orders: MetricChange | None = None
    average_selling_price: MetricChange | None = None
    discount_rate: MetricChange | None = None


class BreakdownRow(BaseModel):
    """One entity's contribution within a breakdown (e.g. channel or city)."""

    entity: AnalyticsEntity
    metrics: MetricSnapshot
    share_of_net_sales: float | None = None


# ── Tool result models ──────────────────────────────────────────────────────────


class ProductResolutionResult(BaseModel):
    """Canonical supplier-scoped product identity resolution."""

    status: ProductResolutionStatus
    product: AnalyticsEntity | None = None
    candidates: list[AnalyticsEntity] = Field(default_factory=list)


class SalesSummaryResult(BaseModel):
    status: Status
    effective_period: EffectivePeriod
    effective_scope: SalesScope
    warnings: list[str] = Field(default_factory=list)

    current: MetricSnapshot | None = None
    previous_period: EffectivePeriod | None = None
    previous: MetricSnapshot | None = None
    changes: MetricChanges | None = None


class RankedRow(BaseModel):
    rank: int
    entity: AnalyticsEntity
    metrics: MetricSnapshot
    share_of_rank_metric: float | None = Field(
        default=None,
        description=(
            "This entity's share of total_population_rank_metric_value, expressed "
            "as a fraction from 0 to 1."
        ),
    )
    previous_rank_metric_value: float | None = Field(
        default=None,
        description="This same entity's value for rank_by in the comparison period.",
    )
    rank_metric_absolute_change: float | None = Field(
        default=None,
        description=(
            "Current rank_by value minus this same entity's rank_by value in the "
            "comparison period."
        ),
    )
    rank_metric_percent_change: float | None = Field(
        default=None,
        description=(
            "Relative percentage change in this entity's rank_by value versus the "
            "comparison period."
        ),
    )


class SalesRankingResult(BaseModel):
    status: Status
    group_by: GroupBy
    rank_by: RankBy
    order: RankOrder = "highest"
    effective_period: EffectivePeriod
    effective_scope: SalesScope
    warnings: list[str] = Field(default_factory=list)

    total_population_rank_metric_value: float | None = Field(
        default=None,
        description=(
            "Value of rank_by across the complete eligible population before the "
            "result limit is applied. This is not the sum of only the returned rows."
        ),
    )
    returned_rows_rank_metric_value: float | None = Field(
        default=None,
        description=(
            "Sum of rank_by across only the rows returned in this response. For "
            "order='highest' this is the returned top-N total; for order='lowest' "
            "it is the returned bottom-N total."
        ),
    )
    comparison_period: EffectivePeriod | None = None
    rows: list[RankedRow] = Field(default_factory=list)


class TrendRow(BaseModel):
    period_start: date
    period_label: str
    series_entity: AnalyticsEntity | None = None
    metrics: MetricSnapshot


class SalesTrendResult(BaseModel):
    status: Status
    grain: TrendGrain
    split_by: SplitBy | None = None
    effective_period: EffectivePeriod
    effective_scope: SalesScope
    warnings: list[str] = Field(default_factory=list)

    rows: list[TrendRow] = Field(default_factory=list)


class ProductOverviewResult(BaseModel):
    status: Status
    effective_period: EffectivePeriod
    effective_scope: ProductOverviewScope
    warnings: list[str] = Field(default_factory=list)

    product: AnalyticsEntity | None = None
    current: MetricSnapshot | None = None
    previous_period: EffectivePeriod | None = None
    previous: MetricSnapshot | None = None
    changes: MetricChanges | None = None

    rank_by_units: int | None = None
    rank_by_net_sales: int | None = None
    share_of_supplier_units: float | None = None
    share_of_supplier_net_sales: float | None = None

    trend: list[TrendRow] = Field(default_factory=list)
    channel_breakdown: list[BreakdownRow] = Field(default_factory=list)
    city_breakdown: list[BreakdownRow] = Field(default_factory=list)

    candidates: list[AnalyticsEntity] = Field(default_factory=list)
