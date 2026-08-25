"""Public MCP analytics and entity-resolution tools.

Each tool validates model-visible arguments, resolves the trusted supplier
context server-side (supplier_id is never a model-visible argument), calls the
SalesAnalyticsService and returns a typed Pydantic result model so the SDK emits
an outputSchema and structuredContent.
"""

from __future__ import annotations

from collections.abc import Awaitable
from datetime import date
from typing import Annotated, TypeVar

from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field

from app.context.supplier_context import SupplierContextError, SupplierContextResolver
from app.contracts.sales import (
    AnalyticsResult,
    GroupBy,
    ProductResolutionResult,
    ProductOverviewScope,
    RankBy,
    RankOrder,
    SalesScope,
    SplitBy,
    TrendGrain,
)
from app.contracts.views import (
    overview_to_analytics,
    ranking_to_analytics,
    summary_to_analytics,
    trend_to_analytics,
)
from app.services.sales_analytics_service import (
    AnalyticsRequestError,
    SalesAnalyticsService,
)

T = TypeVar("T")


async def _run(coro: Awaitable[T]) -> T:
    """Run a service call, converting unexpected failures into a sanitized error.

    Expected request problems and supplier-context messages are safe to surface.
    Anything else (e.g. a database failure) is replaced so no SQL, connection
    details or stack traces reach the model, and is never reported as empty data.
    """
    try:
        return await coro
    except (AnalyticsRequestError, SupplierContextError):
        raise
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "Internal error while executing the analytics query."
        ) from exc


def register_sales_tools(
    mcp: FastMCP,
    service: SalesAnalyticsService,
    supplier_resolver: SupplierContextResolver,
) -> None:
    @mcp.tool()
    async def resolve_product(
        ctx: Context,
        product: str,
    ) -> ProductResolutionResult:
        """Resolve one product reference to its canonical supplier-scoped ID.

        This is an entity-resolution capability used before analytical queries
        that need SalesScope.product_ids. It performs no sales aggregation.

        Parameters:
        - product: canonical product ID, exact product name, or partial product
          name.

        Resolution is deterministic: exact ID, then exact case-insensitive
        name, then partial name, then a conservative supplier-scoped fuzzy
        fallback for likely typos. Fuzzy matching only resolves when one
        candidate is a strong, clearly separated match. Otherwise the tool
        returns ambiguous/not_found rather than guessing.

        supplier_id is resolved from trusted MCP context and is never exposed as
        a model-visible argument.
        """
        supplier_id = supplier_resolver.resolve(ctx)
        return await _run(
            service.resolve_product(
                supplier_id=supplier_id,
                product=product,
            )
        )

    @mcp.tool()
    async def sales_summary(
        ctx: Context,
        period_start: date | None = None,
        period_end: date | None = None,
        scope: SalesScope | None = None,
    ) -> AnalyticsResult:
        """Overall sales KPI summary for the current supplier.

        What it does: returns the standard KPI set (units, net/gross sales,
        discounts, orders, average selling price, discount rate) for one period,
        with a period-over-period comparison when an explicit period is given.

        When to use: high-level "how are we doing" questions and single-scope
        performance checks (a channel, a city, a category).

        When NOT to use: entity rankings (use sales_rank) or time series (use
        sales_trend).

        Parameters:
        - period_start / period_end: inclusive date range. Supply both or neither.
          If omitted, the full available range is used and no comparison is made.
        - scope: optional filters (channels, cities, store_ids, categories,
          product_ids). Empty lists mean no restriction.

        Returns: AnalyticsResult with effective context, a flat current metrics
        view and an optional current-versus-previous comparison view.

        Examples:
        - "How are our sales doing?"
        - "Give me an overview of online sales this year."
        """
        supplier_id = supplier_resolver.resolve(ctx)
        result = await _run(
            service.summary(
                supplier_id=supplier_id,
                period_start=period_start,
                period_end=period_end,
                scope=scope or SalesScope(),
            )
        )
        return summary_to_analytics(result)

    @mcp.tool()
    async def sales_rank(
        ctx: Context,
        group_by: GroupBy,
        rank_by: RankBy,
        period_start: date | None = None,
        period_end: date | None = None,
        scope: SalesScope | None = None,
        limit: Annotated[int, Field(ge=1, le=20)] = 10,
        order: RankOrder = "highest",
    ) -> AnalyticsResult:
        """Rank business entities and explain the result with full metrics.

        What it does: groups sales by one dimension (product, category, store,
        city or channel), ranks the groups by a chosen additive metric, and
        returns each group's complete metric snapshot (including the supporting
        average_selling_price and discount_rate), share of the ranking metric and
        period-over-period change.

        When to use: "best/top/worst" questions and categorical breakdowns
        (e.g. online vs physical, cities by revenue, best category or store).

        When NOT to use: single overall KPIs (use sales_summary) or time series
        (use sales_trend).

        Parameters:
        - group_by: entity dimension to rank.
        - rank_by: additive metric to rank by (units, net_sales, gross_sales,
          orders, discounts). Averages and rates cannot be ranked but are still
          returned per row as supporting metrics.
        - order: "highest" (default) ranks descending; "lowest" ranks ascending
          (worst performers first). Ranks are always numbered 1, 2, 3 in the
          returned display order.
        - period_start / period_end: inclusive range; supply both or neither.
          If omitted, the full available range is used.
        - scope: optional filters; empty lists mean no restriction.
        - limit: number of ranked rows, 1–20 (default 10). For a singular
          winner/loser question, pass limit=1. For an explicit top/bottom N
          question, pass limit=N. Do not rely on the default when the requested
          cardinality is explicit.

        Returns: AnalyticsResult with effective context and one flat categorical
        ranking view containing entity metrics, shares and changes.

        Examples:
        - "What is our best-selling product online?" (group_by=product,
          rank_by=units, scope={"channels":["online"]}, limit=1,
          order="highest").
        - "Which store has the lowest net sales?" (group_by=store,
          rank_by=net_sales, limit=1, order="lowest").
        - "What are our top 5 products by revenue?" (group_by=product,
          rank_by=net_sales, limit=5, order="highest").
        """
        supplier_id = supplier_resolver.resolve(ctx)
        result = await _run(
            service.rank(
                supplier_id=supplier_id,
                group_by=group_by,
                rank_by=rank_by,
                period_start=period_start,
                period_end=period_end,
                scope=scope or SalesScope(),
                limit=limit,
                order=order,
            )
        )
        return ranking_to_analytics(result)

    @mcp.tool()
    async def sales_trend(
        ctx: Context,
        grain: TrendGrain,
        period_start: date,
        period_end: date,
        scope: SalesScope | None = None,
        split_by: SplitBy | None = None,
        series_limit: Annotated[int, Field(ge=1, le=10)] = 5,
    ) -> AnalyticsResult:
        """Ordered sales time series, optionally split into a few series.

        What it does: returns metric snapshots per time bucket (day, week, month
        or quarter) ordered chronologically. When split_by is given, only the top
        series by net sales (capped by series_limit) are returned.

        When to use: "over time", "monthly/quarterly", "trend" and "graph ...
        over time" questions.

        When NOT to use: single KPIs (use sales_summary) or rankings
        (use sales_rank).

        Parameters:
        - grain: day, week, month or quarter.
        - period_start / period_end: inclusive range; both are required.
        - scope: optional filters; empty lists mean no restriction.
        - split_by: optional dimension to split into series (product, category,
          store, city, channel).
        - series_limit: max number of split series, 1–10 (default 5).

        Returns: AnalyticsResult with effective context and one flat timeseries
        view whose rows include optional series identity and all metrics.

        Examples:
        - "Show monthly sales this year." (grain=month).
        - "Graph online and physical sales over time." (grain=month,
          split_by=channel).
        """
        supplier_id = supplier_resolver.resolve(ctx)
        result = await _run(
            service.trend(
                supplier_id=supplier_id,
                grain=grain,
                period_start=period_start,
                period_end=period_end,
                scope=scope or SalesScope(),
                split_by=split_by,
                series_limit=series_limit,
            )
        )
        return trend_to_analytics(result)

    @mcp.tool()
    async def product_overview(
        ctx: Context,
        product: str,
        period_start: date | None = None,
        period_end: date | None = None,
        scope: ProductOverviewScope | None = None,
    ) -> AnalyticsResult:
        """Rich single-product overview assembled from several queries.

        What it does: resolves one product, then returns its KPI summary,
        period-over-period change, rank among supplier products (by units and net
        sales), share of supplier units and net sales, a monthly trend and channel
        and city breakdowns — in one call.

        When to use: "tell me about product X", "how is <product> doing" and
        product deep-dive questions.

        When NOT to use: multi-product rankings (use sales_rank) or supplier-wide
        summaries (use sales_summary).

        Parameters:
        - product: exact product_id, exact product name, or a partial name. If no
          match is found the status is not_found; if several match it is ambiguous
          and candidate products are returned.
        - period_start / period_end: inclusive range; supply both or neither. If
          omitted, the full available range is used.
        - scope: optional filters (channels, cities, store_ids); empty lists mean
          no restriction. product_ids and categories are not accepted here.

        Returns: AnalyticsResult with the resolved entity in context and flat
        current, comparison, trend, channel and city data views when available.

        Examples:
        - "How is the Minimal Logo Hoodie performing this year?"
        - "Give me an overview of product NORD-HOD-011."
        """
        supplier_id = supplier_resolver.resolve(ctx)
        result = await _run(
            service.product_overview(
                supplier_id=supplier_id,
                product=product,
                period_start=period_start,
                period_end=period_end,
                scope=scope or ProductOverviewScope(),
            )
        )
        return overview_to_analytics(result)
