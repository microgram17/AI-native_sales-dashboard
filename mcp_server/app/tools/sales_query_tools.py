from __future__ import annotations

from datetime import date

from mcp.server.fastmcp import FastMCP

from app.repositories.sales_query_repository import SalesQueryRepository
from app.schemas.sales_query import (
    Channel,
    Dimension,
    Metric,
    SalesFilters,
    SalesOrderBy,
    SalesQuery,
    SortDirection,
    TimeGrain,
)


def register_sales_query_tools(
    mcp: FastMCP,
    repo: SalesQueryRepository,
) -> None:
    @mcp.tool()
    async def query_current_supplier_sales(
        supplier_id: str,
        metrics: list[Metric],
        dimensions: list[Dimension] | None = None,
        grain: TimeGrain | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        product_ids: list[str] | None = None,
        categories: list[str] | None = None,
        store_ids: list[str] | None = None,
        cities: list[str] | None = None,
        channels: list[Channel] | None = None,
        order_by_field: str | None = None,
        order_by_direction: SortDirection = "desc",
        limit: int | None = None,
    ) -> dict:
        """
        Query sales for the current supplier.

        Use this for sales summaries, rankings, breakdowns, and time series.

        Metrics:
        - net_sales
        - gross_sales
        - units
        - discounts
        - orders

        Dimensions:
        - period
        - product
        - category
        - store
        - city
        - channel

        If dimensions includes period, grain is required.

        Filters are composable and work with every query:
        - date_from/date_to
        - product_ids
        - categories
        - store_ids
        - cities
        - channels

        The caller must not invent supplier_id. In the final app, supplier_id is injected
        by the backend from authenticated supplier context.
        """
        query = SalesQuery(
            metrics=metrics,
            dimensions=dimensions or [],
            grain=grain,
            filters=SalesFilters(
                date_from=date_from,
                date_to=date_to,
                product_ids=product_ids or [],
                categories=categories or [],
                store_ids=store_ids or [],
                cities=cities or [],
                channels=channels or [],
            ),
            order_by=(
                SalesOrderBy(
                    field=order_by_field,
                    direction=order_by_direction,
                )
                if order_by_field
                else None
            ),
            limit=limit,
        )

        result = await repo.query_supplier_sales(
            supplier_id=supplier_id,
            query=query,
        )
        return result.model_dump(mode="json")