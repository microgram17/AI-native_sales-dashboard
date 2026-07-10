from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Core analytics vocabulary — canonical types for the backend domain.
#
# The MCP server has its own equivalent types (SupplierSalesMetric, TimeGrain,
# etc.) in mcp_server/app/schemas/common.py. Those are intentionally separate
# — the MCP server is an independent service. Do not import from there.
# ---------------------------------------------------------------------------

Metric = Literal["net_sales", "gross_sales", "units", "orders", "discounts"]
"""A quantitative sell-through metric. Used by tools, ports, and result metadata."""

Grain = Literal["week", "month"]
"""Time aggregation grain for trend analysis."""

GroupBy = Literal["store", "city", "channel"]
"""Location/channel dimension for breakdown and ranking analysis."""

Channel = Literal["online", "physical"]
"""Sales channel filter value."""

Dimension = Literal["product", "category", "city", "store", "channel"]
"""The primary analytical dimension of a result — what the data is grouped or ranked by."""

ResultIntent = Literal["summary", "timeseries", "ranking", "single_winner", "breakdown", "table"]
"""What the analytics result was intended to answer.

Maps naturally to visualization choices:
  summary      → metric cards
  timeseries   → line chart
  ranking      → bar chart / ranked list
  single_winner → single metric card or highlighted row
  breakdown    → bar chart grouped by dimension
  table        → plain data table
"""

# ---------------------------------------------------------------------------
# Metric metadata — backend-side mirror of the MCP metric helper functions.
# Use these for display labels, column types, and units without calling MCP.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MetricInfo:
    """Human-readable metadata for a single metric."""

    label: str
    column_type: str  # "currency" | "integer"
    unit: str | None


METRIC_INFO: dict[str, MetricInfo] = {
    "net_sales": MetricInfo(label="Net sales", column_type="currency", unit="SEK"),
    "gross_sales": MetricInfo(label="Gross sales", column_type="currency", unit="SEK"),
    "units": MetricInfo(label="Units sold", column_type="integer", unit=None),
    "orders": MetricInfo(label="Orders", column_type="integer", unit=None),
    "discounts": MetricInfo(label="Discounts", column_type="currency", unit="SEK"),
}

ALLOWED_METRICS: frozenset[str] = frozenset(METRIC_INFO.keys())
"""Frozenset of all valid Metric values, derived from METRIC_INFO."""

# ---------------------------------------------------------------------------
# AnalyticsFilters — structured filter parameter vocabulary.
#
# Not yet enforced at runtime in existing paths. Defined here as the canonical
# shape for filter state (ChatSessionState.last_filters, SalesToolContext.used_filters)
# and as the target output type for future entity resolution.
# ---------------------------------------------------------------------------


class AnalyticsFilters(BaseModel):
    """Optional filter parameters for a scoped analytics query.

    All fields are optional — callers fill only the filters relevant to their
    query. Future entity resolution will populate these from user utterances.
    supplier_id is deliberately absent — it comes from UserContext, not filters.
    """

    date_from: str | None = None
    date_to: str | None = None
    city: str | None = None
    store_id: str | None = None
    channel: Channel | None = None
    category: str | None = None
    product_id: str | None = None
    product_ids: list[str] | None = None
