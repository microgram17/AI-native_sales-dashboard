from __future__ import annotations

from typing import Literal

MetricLiteral = Literal["net_sales", "gross_sales", "units", "orders", "discounts"]
GrainLiteral = Literal["week", "month"]
GroupByLiteral = Literal["store", "city", "channel"]
ChannelLiteral = Literal["online", "physical"]

ALLOWED_METRICS: frozenset[str] = frozenset({"net_sales", "gross_sales", "units", "orders", "discounts"})
