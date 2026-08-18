"""Direct MCP tests using FastMCP's in-memory list_tools/call_tool utilities."""

from __future__ import annotations

import pytest

from app.context.supplier_context import SupplierContextError
from app.contracts.sales import ProductOverviewScope
from app.tools.sales_tools import _run

EXPECTED_TOOLS = {"resolve_product", "sales_summary", "sales_rank", "sales_trend", "product_overview"}


async def test_expected_tools_registered(mcp_server):
    tools = await mcp_server.list_tools()
    names = {tool.name for tool in tools}
    assert names == EXPECTED_TOOLS


# 19
async def test_no_tool_exposes_supplier_id(mcp_server):
    tools = await mcp_server.list_tools()
    for tool in tools:
        properties = (tool.inputSchema or {}).get("properties", {})
        assert "supplier_id" not in properties, tool.name


# 20
async def test_all_tools_have_output_schema(mcp_server):
    tools = await mcp_server.list_tools()
    for tool in tools:
        assert tool.outputSchema is not None, tool.name


async def test_scope_is_a_nested_object_in_schema(mcp_server):
    tools = {tool.name: tool for tool in await mcp_server.list_tools()}
    summary = tools["sales_summary"]
    properties = summary.inputSchema["properties"]
    assert "scope" in properties
    defs = summary.inputSchema.get("$defs", {})
    assert "SalesScope" in defs
    scope_props = defs["SalesScope"]["properties"]
    assert {"channels", "cities", "store_ids", "categories", "product_ids"} <= set(
        scope_props
    )


# 17
async def test_limit_constraints_in_schema(mcp_server):
    tools = {tool.name: tool for tool in await mcp_server.list_tools()}
    rank_props = tools["sales_rank"].inputSchema["properties"]
    assert rank_props["limit"]["minimum"] == 1
    assert rank_props["limit"]["maximum"] == 20
    trend_props = tools["sales_trend"].inputSchema["properties"]
    assert trend_props["series_limit"]["minimum"] == 1
    assert trend_props["series_limit"]["maximum"] == 10


async def test_limit_out_of_range_is_rejected(mcp_server):
    with pytest.raises(Exception):
        await mcp_server.call_tool(
            "sales_rank",
            {"group_by": "product", "rank_by": "units", "limit": 50},
        )


async def test_call_summary_returns_structured_content(mcp_server):
    content, structured = await mcp_server.call_tool("sales_summary", {})
    assert structured["status"] in {"success", "no_data"}
    assert "effective_period" in structured
    assert "effective_scope" in structured


async def test_call_rank_online_returns_structured(mcp_server):
    content, structured = await mcp_server.call_tool(
        "sales_rank",
        {
            "group_by": "product",
            "rank_by": "units",
            "scope": {"channels": ["online"]},
            "limit": 5,
        },
    )
    assert structured["status"] == "success"
    assert structured["group_by"] == "product"
    assert structured["rows"]
    assert "supplier_id" not in structured


# ranking direction 3: invalid order is rejected by the schema
async def test_invalid_order_is_rejected(mcp_server):
    with pytest.raises(Exception):
        await mcp_server.call_tool(
            "sales_rank",
            {"group_by": "product", "rank_by": "units", "order": "sideways"},
        )


async def test_rank_by_enum_excludes_ratio_metrics(mcp_server):
    tools = {tool.name: tool for tool in await mcp_server.list_tools()}
    rank_by = tools["sales_rank"].inputSchema["properties"]["rank_by"]["enum"]
    assert set(rank_by) == {"units", "net_sales", "gross_sales", "orders", "discounts"}
    assert "average_selling_price" not in rank_by
    assert "discount_rate" not in rank_by


# restrict rank_by 4: average_selling_price rejected
async def test_average_selling_price_rejected_as_rank_by(mcp_server):
    with pytest.raises(Exception):
        await mcp_server.call_tool(
            "sales_rank",
            {"group_by": "product", "rank_by": "average_selling_price"},
        )


# restrict rank_by 5: discount_rate rejected
async def test_discount_rate_rejected_as_rank_by(mcp_server):
    with pytest.raises(Exception):
        await mcp_server.call_tool(
            "sales_rank",
            {"group_by": "product", "rank_by": "discount_rate"},
        )


# ranking rows include both supporting metrics (via structured output)
async def test_rank_rows_expose_supporting_metrics(mcp_server):
    _content, structured = await mcp_server.call_tool(
        "sales_rank",
        {"group_by": "product", "rank_by": "units", "limit": 3},
    )
    metrics = structured["rows"][0]["metrics"]
    assert "average_selling_price" in metrics
    assert "discount_rate" in metrics


# product_overview 7: accepts channel/city/store filters
async def test_product_overview_accepts_scope_filters(mcp_server):
    _content, structured = await mcp_server.call_tool(
        "product_overview",
        {
            "product": "NORD-HOD-011",
            "period_start": "2026-01-01",
            "period_end": "2026-06-30",
            "scope": {"channels": ["online"], "cities": ["Stockholm"]},
        },
    )
    assert structured["status"] in {"success", "no_data"}


# product_overview 8: product_ids rejected
async def test_product_overview_rejects_product_ids(mcp_server):
    with pytest.raises(Exception):
        await mcp_server.call_tool(
            "product_overview",
            {"product": "NORD-HOD-011", "scope": {"product_ids": ["NORD-HOD-011"]}},
        )
    with pytest.raises(Exception):
        ProductOverviewScope(product_ids=["NORD-HOD-011"])


# product_overview 9: categories rejected
async def test_product_overview_rejects_categories(mcp_server):
    with pytest.raises(Exception):
        await mcp_server.call_tool(
            "product_overview",
            {"product": "NORD-HOD-011", "scope": {"categories": ["Hoodies"]}},
        )
    with pytest.raises(Exception):
        ProductOverviewScope(categories=["Hoodies"])


# 11: unexpected ValueError is sanitized by _run
async def test_run_sanitizes_unexpected_valueerror():
    async def boom():
        raise ValueError("raw internal detail")

    with pytest.raises(RuntimeError) as info:
        await _run(boom())
    assert "raw internal detail" not in str(info.value)


# 12: SupplierContextError passes through _run unchanged
async def test_run_passes_through_supplier_context_error():
    async def boom():
        raise SupplierContextError("no supplier")

    with pytest.raises(SupplierContextError):
        await _run(boom())


async def test_rank_exposes_unambiguous_population_and_returned_totals(mcp_server):
    _content, structured = await mcp_server.call_tool(
        "sales_rank",
        {
            "group_by": "product",
            "rank_by": "net_sales",
            "period_start": "2026-01-01",
            "period_end": "2026-03-31",
            "limit": 5,
        },
    )

    assert structured["status"] == "success"
    assert "total_population_rank_metric_value" in structured
    assert "returned_rows_rank_metric_value" in structured
    assert "total_rank_metric_value" not in structured
    assert structured["total_population_rank_metric_value"] >= structured[
        "returned_rows_rank_metric_value"
    ]


async def test_resolve_product_exact_name(mcp_server):
    _content, structured = await mcp_server.call_tool(
        "resolve_product",
        {"product": "Minimal Logo Hoodie"},
    )
    assert structured["status"] == "success"
    assert structured["product"]["id"] == "NORD-HOD-011"
    assert structured["product"]["name"] == "Minimal Logo Hoodie"


async def test_resolve_product_ambiguous(mcp_server):
    _content, structured = await mcp_server.call_tool(
        "resolve_product",
        {"product": "Hoodie"},
    )
    assert structured["status"] == "ambiguous"
    assert len(structured["candidates"]) > 1


async def test_resolve_product_not_found(mcp_server):
    _content, structured = await mcp_server.call_tool(
        "resolve_product",
        {"product": "does-not-exist-zzz"},
    )
    assert structured["status"] == "not_found"
