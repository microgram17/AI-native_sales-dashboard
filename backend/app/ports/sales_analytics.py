from typing import Any, Protocol


class SalesAnalyticsPort(Protocol):
    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        ...

    async def list_tools(self) -> list[dict[str, Any]]:
        ...

    async def get_supplier_summary(self, supplier_code: str) -> dict:
        ...

    async def get_supplier_revenue_trend(
        self,
        supplier_code: str,
        period_type: str = "month",
    ) -> dict:
        ...

    async def get_top_products(
        self,
        supplier_code: str,
        limit: int = 5,
        sort_by: str = "revenue",
    ) -> dict:
        ...

    async def list_suppliers(self) -> dict:
        ...

