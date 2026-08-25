from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


UiLanguage = Literal["en", "sv"]
Metric = Literal[
    "units", "net_sales", "gross_sales", "discounts", "orders",
    "average_selling_price", "discount_rate",
]
Grain = Literal["day", "week", "month", "quarter"]
GroupBy = Literal["product", "category", "store", "city", "channel"]
RankMetric = Literal["units", "net_sales", "gross_sales", "discounts", "orders"]
Channel = Literal["online", "physical"]


class AnalysisScope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channels: list[Channel] = Field(default_factory=list)
    cities: list[str] = Field(default_factory=list)
    store_ids: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    product_ids: list[str] = Field(default_factory=list)


class EffectivePeriod(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start: date
    end: date
    label: str | None = None
    defaulted: bool = False


class AnalyticsEntity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    id: str | None = None
    name: str


class AnalyticsContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: Literal["summary", "ranking", "trend", "product_overview"]
    effective_period: EffectivePeriod
    effective_scope: AnalysisScope
    grain: Grain | None = None
    group_by: GroupBy | None = None
    rank_by: RankMetric | None = None
    order: Literal["highest", "lowest"] | None = None
    split_by: GroupBy | None = None
    entity: AnalyticsEntity | None = None


class DataField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    role: Literal["dimension", "measure"]
    format: Literal[
        "text", "date", "integer", "decimal", "currency_sek",
        "percentage_fraction",
    ]


class DataView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    kind: Literal["metrics", "categorical", "timeseries"]
    rows: list[dict[str, Any]] = Field(default_factory=list)
    fields: list[DataField] = Field(default_factory=list)
    primary_dimension: str | None = None
    series_dimension: str | None = None
    default_measures: list[str] = Field(default_factory=list)
    default_visible: bool = True

    @property
    def measure_keys(self) -> set[str]:
        return {field.key for field in self.fields if field.role == "measure"}


class DisplaySelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    view_id: str
    render_as: Literal["default", "table"] = "default"
    measure_keys: list[str] = Field(default_factory=list)
    title: str | None = None


class AgentTurnOutput(BaseModel):
    """Structured final response produced by the single ADK agent."""

    model_config = ConfigDict(extra="forbid")

    message: str
    displays: list[DisplaySelection] = Field(default_factory=list)


class DashboardContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date_from: date
    date_to: date
    metric: Metric | None = None
    grain: Grain | None = None
    group_by: GroupBy | None = None
    view: Literal["ranking", "trend"] | None = None
    selected_group_ids: list[str] = Field(default_factory=list)


class DashboardWidgetAnalysis(BaseModel):
    """Trusted analytical scope attached to an Explain-with-AI action."""

    model_config = ConfigDict(extra="forbid")

    widget: Literal["kpi", "sales_trend", "performance"]
    operation: Literal["summary", "trend", "ranking"]
    metrics: list[Metric] = Field(min_length=1)
    period_start: date
    period_end: date
    grain: Grain | None = None
    group_by: GroupBy | None = None
    rank_by: RankMetric | None = None
    split_by: GroupBy | None = None
    limit: int = Field(default=10, ge=1, le=20)
    series_limit: int = Field(default=3, ge=1, le=10)
    scope: AnalysisScope = Field(default_factory=AnalysisScope)

    @model_validator(mode="after")
    def validate_widget_semantics(self) -> DashboardWidgetAnalysis:
        if self.period_start > self.period_end:
            raise ValueError("period_start must be on or before period_end")
        if self.widget == "kpi" and self.operation != "summary":
            raise ValueError("KPI widgets require a summary operation")
        if self.widget == "sales_trend" and (
            self.operation != "trend" or self.split_by is not None
        ):
            raise ValueError("Sales-trend widgets require an unsplit trend operation")
        if self.widget == "performance":
            dimensions = {"store", "city", "channel"}
            if self.operation == "ranking":
                if self.group_by not in dimensions or self.rank_by is None:
                    raise ValueError(
                        "Performance rankings require a supported group and metric"
                    )
            elif self.operation == "trend":
                if self.split_by not in dimensions:
                    raise ValueError(
                        "Performance trends require a supported split dimension"
                    )
                selected = {
                    "store": self.scope.store_ids,
                    "city": self.scope.cities,
                    "channel": self.scope.channels,
                }[self.split_by]
                if not selected:
                    raise ValueError(
                        "Performance trends require the selected widget series"
                    )
            else:
                raise ValueError("Performance widgets require ranking or trend analysis")
        return self


class AgentQueryRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    language: UiLanguage = "sv"
    dashboard_context: DashboardContext | None = None
    widget_analysis: DashboardWidgetAnalysis | None = None


class ToolCallInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    call_id: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    status: str | None = None
    error: str | None = None


class AgentQueryResponse(BaseModel):
    conversation_id: str
    message: str
    tool_calls: list[ToolCallInfo] = Field(default_factory=list)
    data_context: AnalyticsContext | None = None
    data_views: list[DataView] = Field(default_factory=list)
    displays: list[DisplaySelection] = Field(default_factory=list)
