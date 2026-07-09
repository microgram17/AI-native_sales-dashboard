from __future__ import annotations

from datetime import date
from typing import Literal

from mcp.server.fastmcp import FastMCP

from app.repositories.sales_repository import SalesRepository
from app.schemas.common import (
    ColumnSpec,
    DataQuality,
    SupplierSalesMetric,
    TimeGrain,
    ToolResult,
    VisualizationSpec,
)


def _metric_label(metric: SupplierSalesMetric) -> str:
    return {
        "net_sales": "Net sales",
        "gross_sales": "Gross sales",
        "units": "Units sold",
        "discounts": "Discounts",
        "orders": "Orders",
    }[metric]


def _metric_column_type(metric: SupplierSalesMetric):
    return {
        "net_sales": "currency",
        "gross_sales": "currency",
        "units": "integer",
        "discounts": "currency",
        "orders": "integer",
    }[metric]


def _metric_unit(metric: SupplierSalesMetric) -> str | None:
    return {
        "net_sales": "SEK",
        "gross_sales": "SEK",
        "units": None,
        "discounts": "SEK",
        "orders": None,
    }[metric]


def _value_column(metric: SupplierSalesMetric) -> ColumnSpec:
    return ColumnSpec(
        key="value",
        label=_metric_label(metric),
        type=_metric_column_type(metric),
        unit=_metric_unit(metric),
    )


def build_product_timeseries_result(
    *,
    rows: list[dict],
    metric: SupplierSalesMetric,
    grain: TimeGrain,
) -> ToolResult:
    return ToolResult(
        result_type="timeseries",
        title=f"{_metric_label(metric)} over time by product",
        description=f"{_metric_label(metric)} grouped by product and {grain}.",
        columns=[
            ColumnSpec(key="period", label="Period", type="date"),
            ColumnSpec(key="product_id", label="Product ID", type="string"),
            ColumnSpec(key="product_name", label="Product", type="string"),
            ColumnSpec(key="category", label="Category", type="string"),
            _value_column(metric),
        ],
        rows=rows,
        recommended_visualizations=[
            VisualizationSpec(
                type="line_chart",
                title=f"{_metric_label(metric)} over time by product",
                x_key="period",
                y_keys=["value"],
                series_key="product_name",
            )
        ],
        data_quality=DataQuality(row_count=len(rows)),
    )


def build_sales_summary_result(*, rows: list[dict]) -> ToolResult:
    return ToolResult(
        result_type="kpi",
        title="Supplier sales summary",
        columns=[
            ColumnSpec(key="gross_sales", label="Gross sales", type="currency", unit="SEK"),
            ColumnSpec(key="net_sales", label="Net sales", type="currency", unit="SEK"),
            ColumnSpec(key="discounts", label="Discounts", type="currency", unit="SEK"),
            ColumnSpec(key="units", label="Units sold", type="integer"),
            ColumnSpec(key="orders", label="Orders", type="integer"),
        ],
        rows=rows,
        recommended_visualizations=[
            VisualizationSpec(type="metric_card", title="Net sales", value_key="net_sales"),
            VisualizationSpec(type="metric_card", title="Units sold", value_key="units"),
            VisualizationSpec(type="metric_card", title="Orders", value_key="orders"),
        ],
        data_quality=DataQuality(row_count=len(rows)),
    )


def build_top_products_result(
    *,
    rows: list[dict],
    sort_by: SupplierSalesMetric,
    limit: int,
) -> ToolResult:
    return ToolResult(
        result_type="ranking",
        title=f"Top {limit} products by {_metric_label(sort_by).lower()}",
        columns=[
            ColumnSpec(key="rank", label="Rank", type="integer"),
            ColumnSpec(key="product_id", label="Product ID", type="string"),
            ColumnSpec(key="product_name", label="Product", type="string"),
            ColumnSpec(key="category", label="Category", type="string"),
            ColumnSpec(key="net_sales", label="Net sales", type="currency", unit="SEK"),
            ColumnSpec(key="gross_sales", label="Gross sales", type="currency", unit="SEK"),
            ColumnSpec(key="units", label="Units sold", type="integer"),
            ColumnSpec(key="orders", label="Orders", type="integer"),
            ColumnSpec(key="discounts", label="Discounts", type="currency", unit="SEK"),
        ],
        rows=rows,
        recommended_visualizations=[
            VisualizationSpec(
                type="bar_chart",
                title=f"Top products by {_metric_label(sort_by).lower()}",
                x_key="product_name",
                y_keys=[sort_by],
            )
        ],
        data_quality=DataQuality(row_count=len(rows)),
    )


def build_products_result(*, rows: list[dict]) -> ToolResult:
    return ToolResult(
        result_type="table",
        title="Product selector",
        columns=[
            ColumnSpec(key="product_id", label="Product ID", type="string"),
            ColumnSpec(key="product_name", label="Product", type="string"),
            ColumnSpec(key="category", label="Category", type="string"),
            ColumnSpec(key="net_sales", label="Net sales", type="currency", unit="SEK"),
            ColumnSpec(key="units", label="Units sold", type="integer"),
        ],
        rows=rows,
        data_quality=DataQuality(row_count=len(rows)),
    )


def build_store_breakdown_result(
    *,
    rows: list[dict],
    metric: SupplierSalesMetric,
    group_by: str,
) -> ToolResult:
    return ToolResult(
        result_type="breakdown",
        title=f"{_metric_label(metric)} by {group_by}",
        columns=[
            ColumnSpec(key="group_id", label="Group ID", type="string"),
            ColumnSpec(key="group_name", label="Group", type="string"),
            _value_column(metric),
        ],
        rows=rows,
        recommended_visualizations=[
            VisualizationSpec(
                type="bar_chart",
                title=f"{_metric_label(metric)} by {group_by}",
                x_key="group_name",
                y_keys=["value"],
            )
        ],
        data_quality=DataQuality(row_count=len(rows)),
    )


def _metric_named_column(metric: SupplierSalesMetric) -> ColumnSpec:
    """Return a ColumnSpec with key=metric (used in ranked results where the column IS the metric)."""
    return ColumnSpec(
        key=metric,
        label=_metric_label(metric),
        type=_metric_column_type(metric),
        unit=_metric_unit(metric),
    )


def build_ranked_products_result(
    *,
    rows: list[dict],
    metric: SupplierSalesMetric,
    limit: int,
    applied_filters: dict,
) -> ToolResult:
    """Result builder for get_current_supplier_ranked_products.

    Avoids a single-bar chart when limit=1 (single winner).
    """
    result_intent = "single_winner" if limit == 1 else "ranking"
    title_prefix = "Best product" if limit == 1 else f"Top {limit} products"
    title = f"{title_prefix} by {_metric_label(metric).lower()}"

    vizs: list[VisualizationSpec] = []
    if limit > 1:
        vizs.append(
            VisualizationSpec(
                type="bar_chart",
                title=title,
                x_key="product_name",
                y_keys=[metric],
            )
        )

    return ToolResult(
        result_type="ranking",
        title=title,
        columns=[
            ColumnSpec(key="rank", label="Rank", type="integer"),
            ColumnSpec(key="product_id", label="Product ID", type="string"),
            ColumnSpec(key="product_name", label="Product", type="string"),
            ColumnSpec(key="category", label="Category", type="string"),
            _metric_named_column(metric),
        ],
        rows=rows,
        recommended_visualizations=vizs,
        data_quality=DataQuality(row_count=len(rows)),
        applied_filters=applied_filters,
        primary_metric=metric,
        dimension="product",
        result_intent=result_intent,
    )


def build_ranked_locations_result(
    *,
    rows: list[dict],
    metric: SupplierSalesMetric,
    group_by: str,
    limit: int,
    applied_filters: dict,
) -> ToolResult:
    """Result builder for get_current_supplier_ranked_locations."""
    result_intent = "single_winner" if limit == 1 else "ranking"
    dim_label = {"store": "store", "city": "city", "channel": "channel"}[group_by]
    title_prefix = f"Best {dim_label}" if limit == 1 else f"Top {limit} {dim_label}s"
    title = f"{title_prefix} by {_metric_label(metric).lower()}"

    vizs: list[VisualizationSpec] = []
    if limit > 1:
        vizs.append(
            VisualizationSpec(
                type="bar_chart",
                title=title,
                x_key="group_name",
                y_keys=[metric],
            )
        )

    return ToolResult(
        result_type="ranking",
        title=title,
        columns=[
            ColumnSpec(key="rank", label="Rank", type="integer"),
            ColumnSpec(key="group_id", label="Group ID", type="string"),
            ColumnSpec(key="group_name", label=dim_label.capitalize(), type="string"),
            _metric_named_column(metric),
        ],
        rows=rows,
        recommended_visualizations=vizs,
        data_quality=DataQuality(row_count=len(rows)),
        applied_filters=applied_filters,
        primary_metric=metric,
        dimension=group_by,
        result_intent=result_intent,
    )


def build_filter_values_result(*, filter_data: dict) -> ToolResult:
    """Result builder for get_current_supplier_filter_values."""
    rows = (
        [{"filter_type": "city", "value": v} for v in filter_data.get("cities", [])]
        + [{"filter_type": "channel", "value": v} for v in filter_data.get("channels", [])]
        + [{"filter_type": "category", "value": v} for v in filter_data.get("categories", [])]
    )
    return ToolResult(
        result_type="table",
        title="Available filter values",
        description="Distinct cities, channels, and categories with sales data for this supplier.",
        columns=[
            ColumnSpec(key="filter_type", label="Filter type", type="string"),
            ColumnSpec(key="value", label="Value", type="string"),
        ],
        rows=rows,
        data_quality=DataQuality(row_count=len(rows)),
    )


def register_sales_tools(mcp: FastMCP, repo: SalesRepository) -> None:
    @mcp.tool()
    async def get_current_supplier_product_timeseries(
        supplier_id: str,
        date_from: date | None = None,
        date_to: date | None = None,
        product_ids: list[str] | None = None,
        metric: Literal["net_sales", "gross_sales", "units", "discounts", "orders"] = "net_sales",
        grain: Literal["week", "month"] = "month",
        limit_products: int = 5,
    ) -> dict:
        """
        Get product performance over time for the current supplier.

        supplier_id must come from trusted server-side context.
        Do not ask the user for supplier_id.
        Do not infer supplier_id from user text.
        Use this for product trend questions over time.
        When product_ids is omitted, returns the top limit_products products by metric.
        """
        if date_from and date_to and date_from > date_to:
            raise ValueError("date_from cannot be after date_to")
        if not (1 <= limit_products <= 20):
            raise ValueError("limit_products must be between 1 and 20")

        rows = await repo.fetch_supplier_product_timeseries(
            supplier_id=supplier_id,
            date_from=date_from,
            date_to=date_to,
            product_ids=product_ids,
            metric=metric,
            grain=grain,
            limit_products=limit_products,
        )

        result = build_product_timeseries_result(
            rows=rows,
            metric=metric,
            grain=grain,
        )

        return result.model_dump(mode="json")

    @mcp.tool()
    async def get_current_supplier_sales_summary(
        supplier_id: str,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict:
        """
        Get a sales summary for the current supplier.

        supplier_id must come from trusted server-side context.
        Use this for dashboard summaries and high-level sales overview questions.
        """
        if date_from and date_to and date_from > date_to:
            raise ValueError("date_from cannot be after date_to")

        rows = await repo.fetch_supplier_sales_summary(
            supplier_id=supplier_id,
            date_from=date_from,
            date_to=date_to,
        )

        result = build_sales_summary_result(rows=rows)
        return result.model_dump(mode="json")

    @mcp.tool()
    async def get_current_supplier_top_products(
        supplier_id: str,
        sort_by: Literal["net_sales", "gross_sales", "units", "discounts", "orders"] = "net_sales",
        limit: int = 10,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict:
        """
        Get top products for the current supplier with all key metrics.

        supplier_id must come from trusted server-side context.
        Use this for product rankings and best/worst performer questions.
        Returns net_sales, gross_sales, units, orders, and discounts for each product.
        Use sort_by to control which metric determines rank order.
        """
        if not (1 <= limit <= 50):
            raise ValueError("limit must be between 1 and 50")

        if date_from and date_to and date_from > date_to:
            raise ValueError("date_from cannot be after date_to")

        rows = await repo.fetch_supplier_top_products_multi_metric(
            supplier_id=supplier_id,
            date_from=date_from,
            date_to=date_to,
            sort_by=sort_by,
            limit=limit,
        )

        result = build_top_products_result(
            rows=rows,
            sort_by=sort_by,
            limit=limit,
        )

        return result.model_dump(mode="json")

    @mcp.tool()
    async def get_current_supplier_products(
        supplier_id: str,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict:
        """
        Get the product list for the current supplier, suitable for a product selector.

        supplier_id must come from trusted server-side context.
        Returns product_id, product_name, category, net_sales, and units.
        Ordered by net_sales descending within the given date range.
        """
        if date_from and date_to and date_from > date_to:
            raise ValueError("date_from cannot be after date_to")

        rows = await repo.fetch_supplier_products(
            supplier_id=supplier_id,
            date_from=date_from,
            date_to=date_to,
        )

        result = build_products_result(rows=rows)
        return result.model_dump(mode="json")

    @mcp.tool()
    async def get_current_supplier_store_breakdown(
        supplier_id: str,
        metric: Literal["net_sales", "gross_sales", "units", "discounts", "orders"] = "net_sales",
        group_by: Literal["store", "city", "channel"] = "store",
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict:
        """
        Get store, city, or channel breakdown for the current supplier.

        supplier_id must come from trusted server-side context.
        Use this for questions about stores, cities, or online versus physical sales.
        """
        if date_from and date_to and date_from > date_to:
            raise ValueError("date_from cannot be after date_to")

        rows = await repo.fetch_supplier_store_breakdown(
            supplier_id=supplier_id,
            date_from=date_from,
            date_to=date_to,
            metric=metric,
            group_by=group_by,
        )

        result = build_store_breakdown_result(
            rows=rows,
            metric=metric,
            group_by=group_by,
        )

        return result.model_dump(mode="json")

    @mcp.tool()
    async def get_current_supplier_ranked_products(
        supplier_id: str,
        date_from: date | None = None,
        date_to: date | None = None,
        metric: Literal["net_sales", "gross_sales", "units", "discounts", "orders"] = "net_sales",
        limit: int = 10,
        city: str | None = None,
        store_id: str | None = None,
        channel: Literal["online", "physical"] | None = None,
        category: str | None = None,
    ) -> dict:
        """
        Rank products by a selected retail sell-through metric with optional dimension filters.

        supplier_id must come from trusted server-side context.

        Use this tool when the user asks about best-selling or top-performing products
        AND the question includes a location or dimension filter, OR when the agent needs
        a single winner rather than an unfiltered top-N list.

        When to prefer this tool over get_current_supplier_top_products:
        - 'what product sells the best in Stockholm?' → city='Stockholm', metric='units', limit=1
        - 'top 8 products by units sold in Stockholm' → city='Stockholm', metric='units', limit=8
        - 'highest revenue products online' → channel='online', metric='net_sales'
        - 'best-selling hoodies in Q1' → category='Hoodies', metric='units', date_from/date_to set
        - 'top products by units in December' → metric='units', date range set

        metric selection:
        - metric='units'      → best-selling / most popular / volume / quantity sold (use for 'sells the best')
        - metric='net_sales'  → highest retail sales value / revenue (DEFAULT)
        - metric='orders'     → products appearing in the most orders
        - metric='discounts'  → most discounted products
        - metric='gross_sales' → only when user explicitly says gross sales

        limit: number of products to return (1-50). Use limit=1 for single-winner questions.

        Note: online stores have city='Online'. Use channel='online' for online-only filter.
        """
        if not (1 <= limit <= 50):
            raise ValueError("limit must be between 1 and 50")
        if date_from and date_to and date_from > date_to:
            raise ValueError("date_from cannot be after date_to")

        rows = await repo.fetch_supplier_ranked_products(
            supplier_id=supplier_id,
            date_from=date_from,
            date_to=date_to,
            metric=metric,
            limit=limit,
            city=city,
            store_id=store_id,
            channel=channel,
            category=category,
        )

        applied_filters = {
            k: v for k, v in {
                "date_from": date_from.isoformat() if date_from else None,
                "date_to": date_to.isoformat() if date_to else None,
                "metric": metric,
                "limit": limit,
                "city": city,
                "store_id": store_id,
                "channel": channel,
                "category": category,
            }.items() if v is not None
        }

        result = build_ranked_products_result(
            rows=rows,
            metric=metric,
            limit=limit,
            applied_filters=applied_filters,
        )

        return result.model_dump(mode="json")

    @mcp.tool()
    async def get_current_supplier_ranked_locations(
        supplier_id: str,
        date_from: date | None = None,
        date_to: date | None = None,
        metric: Literal["net_sales", "gross_sales", "units", "discounts", "orders"] = "net_sales",
        group_by: Literal["store", "city", "channel"] = "store",
        limit: int = 10,
        category: str | None = None,
        product_id: str | None = None,
    ) -> dict:
        """
        Rank stores, cities, or channels by a selected metric with optional product/category filters.

        supplier_id must come from trusted server-side context.

        Use this tool for location/channel ranking questions:
        - 'which city sells hoodies best?' → group_by='city', category='Hoodies', metric='units'
        - 'which store sells Classic Cotton Tee best?' → group_by='store', product_id=... if known
        - 'online vs physical sales for socks' → group_by='channel', category='Socks'
        - 'best stores by units sold' → group_by='store', metric='units'
        - 'which city has the highest sales?' → group_by='city', metric='net_sales'

        group_by selection:
        - group_by='store'   → compare individual stores
        - group_by='city'    → compare cities (Stockholm, Uppsala, Göteborg, Online)
        - group_by='channel' → compare online vs physical

        metric selection:
        - metric='units'     → units sold by location (use for 'sells the best'/'most popular')
        - metric='net_sales' → retail net sales by location (DEFAULT)
        - metric='orders'    → number of orders by location

        Note: When group_by='city', the online store appears as city='Online'.
        Use group_by='channel' instead for online vs physical comparison.
        """
        if not (1 <= limit <= 50):
            raise ValueError("limit must be between 1 and 50")
        if date_from and date_to and date_from > date_to:
            raise ValueError("date_from cannot be after date_to")

        rows = await repo.fetch_supplier_ranked_locations(
            supplier_id=supplier_id,
            date_from=date_from,
            date_to=date_to,
            metric=metric,
            group_by=group_by,
            limit=limit,
            category=category,
            product_id=product_id,
        )

        applied_filters = {
            k: v for k, v in {
                "date_from": date_from.isoformat() if date_from else None,
                "date_to": date_to.isoformat() if date_to else None,
                "metric": metric,
                "group_by": group_by,
                "limit": limit,
                "category": category,
                "product_id": product_id,
            }.items() if v is not None
        }

        result = build_ranked_locations_result(
            rows=rows,
            metric=metric,
            group_by=group_by,
            limit=limit,
            applied_filters=applied_filters,
        )

        return result.model_dump(mode="json")

    @mcp.tool()
    async def get_current_supplier_filter_values(
        supplier_id: str,
    ) -> dict:
        """
        Return distinct filter values available for this supplier: cities, channels, and categories.

        supplier_id must come from trusted server-side context.

        Use this before calling get_current_supplier_ranked_products or
        get_current_supplier_ranked_locations when you need to validate or discover
        available filter values (e.g. exact category names, available cities).
        Only returns values that have actual sales data.
        """
        filter_data = await repo.fetch_supplier_filter_values(supplier_id=supplier_id)
        result = build_filter_values_result(filter_data=filter_data)
        return result.model_dump(mode="json")