from __future__ import annotations

from app.adapters.outbound.mcp.mcp_client import mcp_call_tool
from app.application.ports.supplier_analytics_port import SupplierAnalyticsPort
from app.domain.tool_result import ToolResultPayload


class SupplierAnalyticsMcpAdapter(SupplierAnalyticsPort):
    """Implements SupplierAnalyticsPort by forwarding calls to the MCP server.

    This is the only file in the backend that knows MCP tool names or the MCP SDK.
    supplier_id is always injected here from server-side UserContext — never from
    the HTTP request.
    """

    def __init__(self, mcp_url: str) -> None:
        self._url = mcp_url

    async def get_sales_summary(
        self,
        supplier_id: str,
        date_from: str | None,
        date_to: str | None,
    ) -> ToolResultPayload:
        raw = await mcp_call_tool(
            self._url,
            "get_current_supplier_sales_summary",
            {
                "supplier_id": supplier_id,
                "date_from": date_from,
                "date_to": date_to,
            },
        )
        return ToolResultPayload.model_validate(raw)

    async def get_product_timeseries(
        self,
        supplier_id: str,
        date_from: str | None,
        date_to: str | None,
        metric: str,
        grain: str,
        product_ids: list[str] | None = None,
        limit_products: int = 5,
    ) -> ToolResultPayload:
        raw = await mcp_call_tool(
            self._url,
            "get_current_supplier_product_timeseries",
            {
                "supplier_id": supplier_id,
                "date_from": date_from,
                "date_to": date_to,
                "metric": metric,
                "grain": grain,
                "product_ids": product_ids,
                "limit_products": limit_products,
            },
        )
        return ToolResultPayload.model_validate(raw)

    async def get_top_products(
        self,
        supplier_id: str,
        date_from: str | None,
        date_to: str | None,
        sort_by: str,
        limit: int,
    ) -> ToolResultPayload:
        raw = await mcp_call_tool(
            self._url,
            "get_current_supplier_top_products",
            {
                "supplier_id": supplier_id,
                "date_from": date_from,
                "date_to": date_to,
                "sort_by": sort_by,
                "limit": limit,
            },
        )
        return ToolResultPayload.model_validate(raw)

    async def get_store_breakdown(
        self,
        supplier_id: str,
        date_from: str | None,
        date_to: str | None,
        metric: str,
        group_by: str,
    ) -> ToolResultPayload:
        raw = await mcp_call_tool(
            self._url,
            "get_current_supplier_store_breakdown",
            {
                "supplier_id": supplier_id,
                "date_from": date_from,
                "date_to": date_to,
                "metric": metric,
                "group_by": group_by,
            },
        )
        return ToolResultPayload.model_validate(raw)

    async def get_supplier_products(
        self,
        supplier_id: str,
        date_from: str | None,
        date_to: str | None,
    ) -> ToolResultPayload:
        raw = await mcp_call_tool(
            self._url,
            "get_current_supplier_products",
            {
                "supplier_id": supplier_id,
                "date_from": date_from,
                "date_to": date_to,
            },
        )
        return ToolResultPayload.model_validate(raw)

    async def get_ranked_products(
        self,
        supplier_id: str,
        date_from: str | None,
        date_to: str | None,
        metric: str,
        limit: int,
        city: str | None = None,
        store_id: str | None = None,
        channel: str | None = None,
        category: str | None = None,
    ) -> ToolResultPayload:
        raw = await mcp_call_tool(
            self._url,
            "get_current_supplier_ranked_products",
            {
                "supplier_id": supplier_id,
                "date_from": date_from,
                "date_to": date_to,
                "metric": metric,
                "limit": limit,
                "city": city,
                "store_id": store_id,
                "channel": channel,
                "category": category,
            },
        )
        return ToolResultPayload.model_validate(raw)

    async def get_ranked_locations(
        self,
        supplier_id: str,
        date_from: str | None,
        date_to: str | None,
        metric: str,
        group_by: str,
        limit: int,
        category: str | None = None,
        product_id: str | None = None,
    ) -> ToolResultPayload:
        raw = await mcp_call_tool(
            self._url,
            "get_current_supplier_ranked_locations",
            {
                "supplier_id": supplier_id,
                "date_from": date_from,
                "date_to": date_to,
                "metric": metric,
                "group_by": group_by,
                "limit": limit,
                "category": category,
                "product_id": product_id,
            },
        )
        return ToolResultPayload.model_validate(raw)

    async def get_filter_values(
        self,
        supplier_id: str,
    ) -> ToolResultPayload:
        raw = await mcp_call_tool(
            self._url,
            "get_current_supplier_filter_values",
            {"supplier_id": supplier_id},
        )
        return ToolResultPayload.model_validate(raw)
