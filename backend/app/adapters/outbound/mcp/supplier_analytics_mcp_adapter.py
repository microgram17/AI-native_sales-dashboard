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
        date_from: str,
        date_to: str,
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
        date_from: str,
        date_to: str,
        metric: str,
        grain: str,
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
            },
        )
        return ToolResultPayload.model_validate(raw)

    async def get_top_products(
        self,
        supplier_id: str,
        date_from: str,
        date_to: str,
        metric: str,
        limit: int,
    ) -> ToolResultPayload:
        raw = await mcp_call_tool(
            self._url,
            "get_current_supplier_top_products",
            {
                "supplier_id": supplier_id,
                "date_from": date_from,
                "date_to": date_to,
                "metric": metric,
                "limit": limit,
            },
        )
        return ToolResultPayload.model_validate(raw)

    async def get_store_breakdown(
        self,
        supplier_id: str,
        date_from: str,
        date_to: str,
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
