
from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.visualization import VisualizationDataset, VisualizationSpec


UiLanguage = Literal["en", "sv"]

TurnMode = Literal[
    "new_analysis",
    "modify_analysis",
    "visualize_existing",
    "analyze_existing",
    "conversation",
]

AnalysisOperation = Literal[
    "summary",
    "ranking",
    "trend",
    "product_overview",
]

Metric = Literal[
    "units",
    "net_sales",
    "gross_sales",
    "discounts",
    "orders",
    "average_selling_price",
    "discount_rate",
]

RankMetric = Literal[
    "units",
    "net_sales",
    "gross_sales",
    "discounts",
    "orders",
]

Grain = Literal["day", "week", "month", "quarter"]
GroupBy = Literal["product", "category", "store", "city", "channel"]
RankOrder = Literal["highest", "lowest"]
Channel = Literal["online", "physical"]
Presentation = Literal["auto", "chart", "cards", "table"]


class AgentQueryRequest(BaseModel):
    """Request body for POST /agent/query.

    Supplier identity intentionally does not appear here. It comes from trusted
    authenticated RequestContext on the server.
    """

    message: str
    conversation_id: str | None = None
    language: UiLanguage = "sv"


class ScopePatch(BaseModel):
    """A partial scope update produced by the turn interpreter.

    None means "leave this dimension unchanged". An empty list means
    "explicitly clear this dimension / include all".
    """

    model_config = ConfigDict(extra="forbid")

    channels: list[Channel] | None = None
    cities: list[str] | None = None
    store_ids: list[str] | None = None
    categories: list[str] | None = None


class TurnInterpretation(BaseModel):
    """Semantic interpretation of one user turn.

    This is intentionally not an MCP/tool plan. The LLM describes what changed
    in the user's analytical request; deterministic application code merges the
    patch with prior state, resolves identities and chooses the MCP capability.
    """

    model_config = ConfigDict(extra="forbid")

    mode: TurnMode

    operation: AnalysisOperation | None = None
    metrics: list[Metric] | None = None
    grain: Grain | None = None

    group_by: GroupBy | None = None
    rank_by: RankMetric | None = None
    rank_order: RankOrder | None = None
    limit: int | None = Field(default=None, ge=1, le=20)

    split_by: GroupBy | None = None
    series_limit: int | None = Field(default=None, ge=1, le=10)

    period_start: date | None = None
    period_end: date | None = None
    clear_period: bool = False

    product_query: str | None = None
    clear_product: bool = False

    scope: ScopePatch = Field(default_factory=ScopePatch)

    presentation: Presentation | None = None
    interpretation_requested: bool = False


class AnalysisScope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channels: list[Channel] = Field(default_factory=list)
    cities: list[str] = Field(default_factory=list)
    store_ids: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)


class CanonicalProduct(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["product"] = "product"
    id: str
    name: str


class AnalysisRequestState(BaseModel):
    """Canonical analytical state persisted across turns.

    Follow-ups patch this object. Anything the user does not change remains
    unchanged, which removes the need for separate inherit_* flags.
    """

    model_config = ConfigDict(extra="forbid")

    operation: AnalysisOperation
    metrics: list[Metric] = Field(default_factory=list)

    grain: Grain | None = None

    group_by: GroupBy | None = None
    rank_by: RankMetric | None = None
    rank_order: RankOrder = "highest"
    limit: int = Field(default=10, ge=1, le=20)

    split_by: GroupBy | None = None
    series_limit: int = Field(default=5, ge=1, le=10)

    period_start: date | None = None
    period_end: date | None = None

    scope: AnalysisScope = Field(default_factory=AnalysisScope)

    entity: CanonicalProduct | None = None
    pending_product_query: str | None = None

    presentation: Presentation = "auto"
    interpretation_requested: bool = False


class ToolCallInfo(BaseModel):
    """Executed tool-call metadata returned to the client."""

    call_id: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    purpose: str | None = None
    status: str | None = None
    error: str | None = None


class Dataset(BaseModel):
    """A successful raw MCP tool result exposed to the client."""

    call_id: str
    tool_name: str
    status: str
    result: dict[str, Any]


class AgentQueryResponse(BaseModel):
    conversation_id: str
    message: str
    tool_calls: list[ToolCallInfo] = Field(default_factory=list)
    datasets: list[Dataset] = Field(default_factory=list)
    visualization_datasets: list[VisualizationDataset] = Field(default_factory=list)
    visualizations: list[VisualizationSpec] = Field(default_factory=list)
