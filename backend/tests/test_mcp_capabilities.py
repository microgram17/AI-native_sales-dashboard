from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.integrations.mcp.capabilities import (
    CAP_PRODUCT_OVERVIEW,
    CAP_PRODUCT_RESOLVER,
    CAP_RANKING,
    CAP_SUMMARY,
    CAP_TREND,
    discover_capabilities,
)


@dataclass
class FakeTool:
    name: str
    input_schema: dict[str, Any]


def _tool(name: str, *properties: str) -> FakeTool:
    return FakeTool(
        name=name,
        input_schema={
            "properties": {key: {} for key in properties},
        },
    )


def test_capabilities_are_discovered_from_contract_not_tool_names():
    tools = [
        _tool("entity_lookup_v2", "product"),
        _tool("aggregate_kpis_v7", "period_start", "period_end", "scope"),
        _tool(
            "rank_entities_v4",
            "group_by",
            "rank_by",
            "period_start",
            "period_end",
            "scope",
            "limit",
            "order",
        ),
        _tool(
            "timeseries_v9",
            "grain",
            "period_start",
            "period_end",
            "scope",
            "split_by",
            "series_limit",
        ),
        _tool(
            "product_deep_dive_v3",
            "product",
            "period_start",
            "period_end",
            "scope",
        ),
    ]

    capabilities = discover_capabilities(tools)

    assert capabilities == {
        CAP_PRODUCT_RESOLVER: "entity_lookup_v2",
        CAP_SUMMARY: "aggregate_kpis_v7",
        CAP_RANKING: "rank_entities_v4",
        CAP_TREND: "timeseries_v9",
        CAP_PRODUCT_OVERVIEW: "product_deep_dive_v3",
    }
