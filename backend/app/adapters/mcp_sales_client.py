import json
import os
from typing import Any

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
        return await self.call_tool(
            "get_supplier_summary",
            {"supplier_code": supplier_code},
        )

    async def get_supplier_revenue_trend(
        self,
        supplier_code: str,
        period_type: str = "month",
    ) -> dict:
        return await self.call_tool(
            "get_supplier_revenue_trend",
            {
                "supplier_code": supplier_code,
                "period_type": period_type,
            },
        )

    async def get_top_products(
        self,
        supplier_code: str,
        limit: int = 5,
        sort_by: str = "revenue",
    ) -> dict:
        return await self.call_tool(
            "get_top_products",
            {
                "supplier_code": supplier_code,
                "limit": limit,
                "sort_by": sort_by,
            },
        )

    async def list_suppliers(self) -> dict:
        return await self.call_tool("list_suppliers", {})