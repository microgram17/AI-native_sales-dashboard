"""MCP tools for supplier-facing analytics."""

from __future__ import annotations

from typing import Literal

from psycopg.rows import dict_row

from app.repositories.supplier_analytics_repository import SupplierAnalyticsRepository

Grain = Literal["day", "week", "month"]
BreakdownDimension = Literal[
    "product",
    "sku",
    "brand",
    "category",
    "sales_channel",
    "country",
    "region",
    "city",
    "store",
    "customer_segment",
]
SalesMetric = Literal[
    "net_sales",
    "units",
    "orders",
    "estimated_margin",
    "average_discount_percent",
]
ChangeMetric = Literal["net_sales", "units", "orders", "estimated_margin"]
ProductSortMetric = Literal[
    "net_sales",
    "units",
    "orders",
    "estimated_margin",
    "margin_rate",
    "discount_percent",
    "price_vs_recommended",
]
SortDirection = Literal["asc", "desc"]
PeriodType = Literal["week", "month"]


def register_sales_tools(mcp, repo: SupplierAnalyticsRepository) -> None:
    """Register dashboard-compatible and newer supplier analytics MCP tools."""
    register_supplier_analytics_tools(mcp, repo)

    @mcp.tool()
    async def list_suppliers() -> dict:
        """List suppliers available in the analytics database."""
        async with repo.pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    SELECT supplier_code, supplier_name, primary_brand, primary_category
                    FROM suppliers
                    ORDER BY supplier_name
                    """
                )
                rows = await cur.fetchall()

        suppliers = [dict(row) for row in rows]
        return {"count": len(suppliers), "suppliers": suppliers}


def register_supplier_analytics_tools(
    mcp,
    repo: SupplierAnalyticsRepository,
) -> None:
    """Register supplier analytics tools on a FastMCP-like server object.

    The `mcp` object only needs to expose an `@mcp.tool()` decorator. This keeps
    the file easy to adapt if your project wraps FastMCP differently.
    """
    @mcp.tool()
    async def get_sales_overview(
        supplier_code: str,
        date_from: str | None = None,
        date_to: str | None = None,
        grain: Grain = "week",
        compare_to_previous_period: bool = True,
    ) -> dict:
        """Get high-level sales performance for the authenticated supplier.

        Use this for questions like:
        - "How are my sales doing?"
        - "Summarize last month"
        - "Show the sales trend by week"
        - "Compare this period with the previous period"

        date_from and date_to should be ISO dates: YYYY-MM-DD. If omitted, the
        tool uses all available data for the supplier. The backend is responsible
        for authorizing and injecting supplier_code before calling this tool.
        """
        return await repo.get_sales_overview(
            supplier_code=supplier_code,
            date_from=date_from,
            date_to=date_to,
            grain=grain,
            compare_to_previous_period=compare_to_previous_period,
        )

    @mcp.tool()
    async def break_down_sales(
        supplier_code: str,
        date_from: str | None = None,
        date_to: str | None = None,
        breakdown_by: BreakdownDimension = "category",
        metric: SalesMetric = "net_sales",
        sort: SortDirection = "desc",
        limit: int = 10,
    ) -> dict:
        """Break supplier sales down by a controlled business dimension.

        Use this for questions like:
        - "Which regions sell best?"
        - "Break sales down by channel"
        - "Which customer segment buys the most?"
        - "Top categories by revenue"

        Supported breakdown_by values: product, sku, brand, category,
        sales_channel, country, region, city, store, customer_segment.
        """
        return await repo.break_down_sales(
            supplier_code=supplier_code,
            date_from=date_from,
            date_to=date_to,
            breakdown_by=breakdown_by,
            metric=metric,
            sort=sort,
            limit=limit,
        )

    @mcp.tool()
    async def get_product_performance(
        supplier_code: str,
        date_from: str | None = None,
        date_to: str | None = None,
        sku: str | None = None,
        category: str | None = None,
        brand: str | None = None,
        sort_by: ProductSortMetric = "net_sales",
        limit: int = 20,
    ) -> dict:
        """Analyze product/SKU performance for the authenticated supplier.

        Use this for questions like:
        - "Which products sell best?"
        - "Which SKUs have the highest margin?"
        - "Which products are discounted the most?"
        - "How is product X performing?"

        Optional filters are exact-match filters for sku, category, and brand.
        """
        return await repo.get_product_performance(
            supplier_code=supplier_code,
            date_from=date_from,
            date_to=date_to,
            sku=sku,
            category=category,
            brand=brand,
            sort_by=sort_by,
            limit=limit,
        )

    @mcp.tool()
    async def get_market_benchmark(
        supplier_code: str,
        period_type: PeriodType = "month",
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> dict:
        """Get market benchmark and estimated market share for the supplier.

        Use this for questions like:
        - "What is my market share?"
        - "Are we growing faster than the market?"
        - "How has our share changed over time?"

        This tool uses the precomputed market_benchmarks table.
        """
        return await repo.get_market_benchmark(
            supplier_code=supplier_code,
            period_type=period_type,
            date_from=date_from,
            date_to=date_to,
        )

    @mcp.tool()
    async def find_sales_changes(
        supplier_code: str,
        current_date_from: str,
        current_date_to: str,
        comparison_date_from: str,
        comparison_date_to: str,
        breakdown_by: BreakdownDimension = "category",
        metric: ChangeMetric = "net_sales",
        limit: int = 10,
    ) -> dict:
        """Find the biggest movers between two periods.

        Use this for questions like:
        - "Why did sales drop?"
        - "What changed compared to last month?"
        - "Which products drove the increase?"
        - "Where did performance decline?"

        The agent should choose explicit current and comparison date ranges.
        """
        return await repo.find_sales_changes(
            supplier_code=supplier_code,
            current_date_from=current_date_from,
            current_date_to=current_date_to,
            comparison_date_from=comparison_date_from,
            comparison_date_to=comparison_date_to,
            breakdown_by=breakdown_by,
            metric=metric,
            limit=limit,
        )

    @mcp.tool()
    async def get_available_data_context(
        supplier_code: str,
        include_products: bool = True,
        include_regions: bool = True,
        include_channels: bool = True,
        include_customer_segments: bool = True,
        product_limit: int = 200,
    ) -> dict:
        """Describe the data available for the authenticated supplier.

        Use this when the agent needs to know available date ranges, products,
        categories, brands, regions, channels, or customer segments before
        choosing a more specific analytics tool.
        """
        return await repo.get_available_data_context(
            supplier_code=supplier_code,
            include_products=include_products,
            include_regions=include_regions,
            include_channels=include_channels,
            include_customer_segments=include_customer_segments,
            product_limit=product_limit,
        )
