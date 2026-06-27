from app.ports.sales_analytics import SalesAnalyticsPort


class DashboardService:
    def __init__(self, sales_analytics: SalesAnalyticsPort) -> None:
        self.sales_analytics = sales_analytics

    async def get_supplier_summary(self, supplier_code: str) -> dict:
        return await self.sales_analytics.get_supplier_summary(supplier_code)

    async def get_supplier_revenue_trend(
        self,
        supplier_code: str,
        period_type: str = "month",
    ) -> dict:
        return await self.sales_analytics.get_supplier_revenue_trend(
            supplier_code=supplier_code,
            period_type=period_type,
        )

    async def get_top_products(
        self,
        supplier_code: str,
        limit: int = 5,
        sort_by: str = "revenue",
    ) -> dict:
        return await self.sales_analytics.get_top_products(
            supplier_code=supplier_code,
            limit=limit,
            sort_by=sort_by,
        )

    async def list_suppliers(self) -> dict:
        return await self.sales_analytics.list_suppliers()
