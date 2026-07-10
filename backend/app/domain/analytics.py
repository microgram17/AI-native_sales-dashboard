from __future__ import annotations

from typing import Literal

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


ALLOWED_METRICS: frozenset[str] = frozenset(
    {"net_sales", "gross_sales", "units", "orders", "discounts"}
)
"""Frozenset of all valid Metric values."""
