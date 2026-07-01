import json
import os
from typing import Any
import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from app.ports.sales_analytics import SalesAnalyticsPort


DEFAULT_MCP_SERVER_URL = "http://mcp_server:8000/mcp/"
LOCAL_MCP_SERVER_URL = "http://127.0.0.1:8001/mcp/"


def get_mcp_server_url() -> str:
    if os.getenv("USE_LOCAL_MCP", "").lower() == "true":
        return LOCAL_MCP_SERVER_URL
    return os.getenv("MCP_SERVER_URL") or DEFAULT_MCP_SERVER_URL


class McpSalesClient(SalesAnalyticsPort):
    def __init__(self, server_url: str | None = None) -> None:
        self.server_url = server_url or get_mcp_server_url()

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        async with streamable_http_client(self.server_url) as (
            read_stream,
            write_stream,
            _,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(name, arguments=arguments)

                if result.structuredContent is not None:
                    return result.structuredContent

                if result.content:
                    item = result.content[0]
                    text = getattr(item, "text", None)

                    if text is not None:
                        try:
                            return json.loads(text)
                        except json.JSONDecodeError:
                            return {"text": text}

                    return item

                return None

    async def get_supplier_summary(self, supplier_code: str) -> dict:
        overview, benchmark, suppliers = await asyncio.gather(
            self.call_tool("get_sales_overview", {"supplier_code": supplier_code, "grain": "month"}),
            self.call_tool("get_market_benchmark", {"supplier_code": supplier_code, "period_type": "month"}),
            self.list_suppliers(),
        )
        if not isinstance(overview, dict):
            return {"found": False, "supplier_code": supplier_code, "message": "Dashboard data unavailable."}

        totals = overview.get("totals") or {}
        periods = benchmark.get("periods") if isinstance(benchmark, dict) else []
        latest_period = periods[-1] if periods else None
        supplier = _find_supplier(suppliers, supplier_code)

        return {
            "supplier_code": supplier_code,
            "supplier_name": supplier.get("supplier_name"),
            "found": True,
            "total_orders": int(totals.get("orders") or 0),
            "total_units": int(totals.get("units") or 0),
            "total_revenue": float(totals.get("net_sales") or 0),
            "estimated_margin": float(totals.get("estimated_margin") or 0),
            "average_order_value": float(totals.get("average_order_value") or 0),
            "latest_market_share": {
                "period": latest_period.get("period_label"),
                "estimated_market_share_pct": latest_period.get("estimated_market_share_pct"),
            } if latest_period else None,
        }

    async def get_supplier_revenue_trend(
        self,
        supplier_code: str,
        period_type: str = "month",
    ) -> dict:
        result = await self.call_tool(
            "get_market_benchmark",
            {"supplier_code": supplier_code, "period_type": period_type},
        )
        if not isinstance(result, dict):
            return {"found": False, "supplier_code": supplier_code, "period_type": period_type, "message": "Dashboard data unavailable."}

        return {
            "supplier_code": supplier_code,
            "period_type": period_type,
            "found": True,
            "points": [
                {
                    "period_start": row.get("period_start"),
                    "period_label": row.get("period_label"),
                    "supplier_revenue": row.get("supplier_revenue"),
                    "comparable_market_revenue": row.get("comparable_market_revenue"),
                    "estimated_market_share_pct": row.get("estimated_market_share_pct"),
                }
                for row in result.get("periods", [])
            ],
        }

    async def get_top_products(
        self,
        supplier_code: str,
        limit: int = 5,
        sort_by: str = "revenue",
    ) -> dict:
        sort_metric = "net_sales" if sort_by == "revenue" else sort_by
        result = await self.call_tool(
            "get_product_performance",
            {"supplier_code": supplier_code, "sort_by": sort_metric, "limit": limit},
        )
        if not isinstance(result, dict):
            return {"found": False, "supplier_code": supplier_code, "message": "Dashboard data unavailable."}

        return {
            "supplier_code": supplier_code,
            "found": True,
            "sort_by": sort_by,
            "limit": limit,
            "products": [
                {
                    "sku": row.get("sku"),
                    "product_name": row.get("product_name"),
                    "category": row.get("category"),
                    "total_revenue": row.get("net_sales"),
                    "total_units": row.get("units"),
                    "total_orders": row.get("orders"),
                }
                for row in result.get("rows", [])
            ],
        }

    async def list_suppliers(self) -> dict:
        return await self.call_tool("list_suppliers", {})

    async def list_tools(self) -> list[dict[str, Any]]:
        async with streamable_http_client(self.server_url) as (
            read_stream,
            write_stream,
            _,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.list_tools()
                return [
                    {
                        "name": t.name,
                        "description": t.description or "",
                        "input_schema": t.inputSchema,
                    }
                    for t in result.tools
                ]


def _find_supplier(suppliers_response: Any, supplier_code: str) -> dict[str, Any]:
    if not isinstance(suppliers_response, dict):
        return {}
    suppliers = suppliers_response.get("suppliers") or []
    for supplier in suppliers:
        if supplier.get("supplier_code") == supplier_code:
            return supplier
    return {}