"""Repository for supplier-facing analytics queries.

The public methods are business-oriented and are intended to back MCP tools.
The repository receives supplier_code from trusted server-side context. The LLM
should never be allowed to provide supplier_code as a tool argument.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Literal, Mapping, Sequence

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

DateLike = str | date | None

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


DIMENSIONS: dict[str, tuple[str, str]] = {
    "product": ("product_name", "product_name"),
    "sku": ("sku", "sku"),
    "brand": ("brand", "brand"),
    "category": ("category", "category"),
    "sales_channel": ("sales_channel", "sales_channel"),
    "country": ("country", "country"),
    "region": ("region", "region"),
    "city": ("city", "city"),
    "store": ("store_name", "store_name"),
    "customer_segment": ("customer_segment", "customer_segment"),
}

SALES_SORT_COLUMNS: dict[str, str] = {
    "net_sales": "net_sales",
    "units": "units",
    "orders": "orders",
    "estimated_margin": "estimated_margin",
    "average_discount_percent": "average_discount_percent",
}

CHANGE_METRIC_EXPRESSIONS: dict[str, str] = {
    "net_sales": "COALESCE(SUM(net_sales), 0)::numeric",
    "units": "COALESCE(SUM(quantity), 0)::numeric",
    "orders": "COUNT(DISTINCT order_id)::numeric",
    "estimated_margin": "COALESCE(SUM(estimated_margin), 0)::numeric",
}

PRODUCT_SORT_COLUMNS: dict[str, str] = {
    "net_sales": "net_sales",
    "units": "units",
    "orders": "orders",
    "estimated_margin": "estimated_margin",
    "margin_rate": "margin_rate_pct",
    "discount_percent": "average_discount_percent",
    "price_vs_recommended": "price_vs_recommended_pct",
}

GRAIN_EXPRESSIONS: dict[str, str] = {
    "day": "order_date",
    "week": "week_start",
    "month": "month_start",
}


class SupplierAnalyticsRepository:
    """Analytics data access for the supplier BI MCP server."""

    def __init__(self, pool: AsyncConnectionPool):
        self.pool = pool

    async def get_sales_overview(
        self,
        *,
        supplier_code: str,
        date_from: DateLike = None,
        date_to: DateLike = None,
        grain: Grain = "week",
        compare_to_previous_period: bool = True,
    ) -> dict[str, Any]:
        """Return totals, trend data, and optional previous-period comparison."""
        self._validate_grain(grain)
        date_from_value = self._parse_date(date_from)
        date_to_value = self._parse_date(date_to)
        self._validate_date_range(date_from_value, date_to_value)

        totals = await self._fetch_one(
            supplier_code=supplier_code,
            query="""
                SELECT
                    COALESCE(SUM(net_sales), 0) AS net_sales,
                    COALESCE(SUM(gross_sales), 0) AS gross_sales,
                    COALESCE(SUM(quantity), 0) AS units,
                    COUNT(DISTINCT order_id) AS orders,
                    COUNT(*) AS order_lines,
                    COALESCE(SUM(estimated_margin), 0) AS estimated_margin,
                    CASE
                        WHEN COUNT(DISTINCT order_id) = 0 THEN NULL
                        ELSE SUM(net_sales) / COUNT(DISTINCT order_id)
                    END AS average_order_value,
                    CASE
                        WHEN SUM(quantity) = 0 THEN NULL
                        ELSE SUM(net_sales) / SUM(quantity)
                    END AS average_unit_price,
                    CASE
                        WHEN SUM(gross_sales) = 0 THEN NULL
                        ELSE SUM(discount_percent * gross_sales) / SUM(gross_sales)
                    END AS average_discount_percent,
                    CASE
                        WHEN SUM(net_sales) = 0 THEN NULL
                        ELSE SUM(estimated_margin) / SUM(net_sales) * 100
                    END AS margin_rate_pct,
                    MIN(order_date) AS first_order_date,
                    MAX(order_date) AS last_order_date,
                    MIN(currency) AS currency
                FROM supplier_order_line_facts
                WHERE supplier_code = %(supplier_code)s
                  AND (%(date_from)s::date IS NULL OR order_date >= %(date_from)s::date)
                  AND (%(date_to)s::date IS NULL OR order_date <= %(date_to)s::date)
            """,
            params={"date_from": date_from_value, "date_to": date_to_value},
        )

        grain_expression = GRAIN_EXPRESSIONS[grain]
        trend = await self._fetch_all(
            supplier_code=supplier_code,
            query=f"""
                SELECT
                    {grain_expression} AS period_start,
                    COALESCE(SUM(net_sales), 0) AS net_sales,
                    COALESCE(SUM(gross_sales), 0) AS gross_sales,
                    COALESCE(SUM(quantity), 0) AS units,
                    COUNT(DISTINCT order_id) AS orders,
                    COALESCE(SUM(estimated_margin), 0) AS estimated_margin,
                    CASE
                        WHEN SUM(net_sales) = 0 THEN NULL
                        ELSE SUM(estimated_margin) / SUM(net_sales) * 100
                    END AS margin_rate_pct
                FROM supplier_order_line_facts
                WHERE supplier_code = %(supplier_code)s
                  AND (%(date_from)s::date IS NULL OR order_date >= %(date_from)s::date)
                  AND (%(date_to)s::date IS NULL OR order_date <= %(date_to)s::date)
                GROUP BY {grain_expression}
                ORDER BY {grain_expression}
            """,
            params={"date_from": date_from_value, "date_to": date_to_value},
        )

        comparison: dict[str, Any] | None = None
        if compare_to_previous_period and date_from_value and date_to_value:
            comparison = await self._get_previous_period_comparison(
                supplier_code=supplier_code,
                date_from=date_from_value,
                date_to=date_to_value,
            )

        return json_ready(
            {
                "period": {"date_from": date_from_value, "date_to": date_to_value, "grain": grain},
                "totals": totals,
                "trend": trend,
                "comparison": comparison,
            }
        )

    async def break_down_sales(
        self,
        *,
        supplier_code: str,
        date_from: DateLike = None,
        date_to: DateLike = None,
        breakdown_by: BreakdownDimension = "category",
        metric: SalesMetric = "net_sales",
        sort: SortDirection = "desc",
        limit: int = 10,
    ) -> dict[str, Any]:
        """Aggregate supplier sales by a controlled business dimension."""
        dimension_column, dimension_label = self._get_dimension(breakdown_by)
        sort_column = self._get_sales_sort_column(metric)
        sort_direction = self._get_sort_direction(sort)
        safe_limit = self._safe_limit(limit, default=10, maximum=100)
        date_from_value = self._parse_date(date_from)
        date_to_value = self._parse_date(date_to)
        self._validate_date_range(date_from_value, date_to_value)

        rows = await self._fetch_all(
            supplier_code=supplier_code,
            query=f"""
                SELECT
                    {dimension_column} AS dimension_value,
                    '{dimension_label}' AS dimension_label,
                    COALESCE(SUM(net_sales), 0) AS net_sales,
                    COALESCE(SUM(gross_sales), 0) AS gross_sales,
                    COALESCE(SUM(quantity), 0) AS units,
                    COUNT(DISTINCT order_id) AS orders,
                    COALESCE(SUM(estimated_margin), 0) AS estimated_margin,
                    CASE
                        WHEN SUM(net_sales) = 0 THEN NULL
                        ELSE SUM(estimated_margin) / SUM(net_sales) * 100
                    END AS margin_rate_pct,
                    CASE
                        WHEN SUM(gross_sales) = 0 THEN NULL
                        ELSE SUM(discount_percent * gross_sales) / SUM(gross_sales)
                    END AS average_discount_percent,
                    CASE
                        WHEN SUM(quantity) = 0 THEN NULL
                        ELSE SUM(net_sales) / SUM(quantity)
                    END AS average_unit_price,
                    MIN(currency) AS currency
                FROM supplier_order_line_facts
                WHERE supplier_code = %(supplier_code)s
                  AND (%(date_from)s::date IS NULL OR order_date >= %(date_from)s::date)
                  AND (%(date_to)s::date IS NULL OR order_date <= %(date_to)s::date)
                GROUP BY {dimension_column}
                ORDER BY {sort_column} {sort_direction}, dimension_value ASC
                LIMIT %(limit)s
            """,
            params={
                "date_from": date_from_value,
                "date_to": date_to_value,
                "limit": safe_limit,
            },
        )

        return json_ready(
            {
                "period": {"date_from": date_from_value, "date_to": date_to_value},
                "breakdown_by": breakdown_by,
                "metric": metric,
                "sort": sort_direction.lower(),
                "rows": rows,
            }
        )

    async def get_product_performance(
        self,
        *,
        supplier_code: str,
        date_from: DateLike = None,
        date_to: DateLike = None,
        sku: str | None = None,
        category: str | None = None,
        brand: str | None = None,
        sort_by: ProductSortMetric = "net_sales",
        limit: int = 20,
    ) -> dict[str, Any]:
        """Return product/SKU performance for the scoped supplier."""
        sort_column = self._get_product_sort_column(sort_by)
        safe_limit = self._safe_limit(limit, default=20, maximum=100)
        date_from_value = self._parse_date(date_from)
        date_to_value = self._parse_date(date_to)
        self._validate_date_range(date_from_value, date_to_value)

        rows = await self._fetch_all(
            supplier_code=supplier_code,
            query=f"""
                SELECT
                    sku,
                    product_name,
                    brand,
                    category,
                    recommended_price,
                    unit_cost,
                    COALESCE(SUM(net_sales), 0) AS net_sales,
                    COALESCE(SUM(gross_sales), 0) AS gross_sales,
                    COALESCE(SUM(quantity), 0) AS units,
                    COUNT(DISTINCT order_id) AS orders,
                    COALESCE(SUM(estimated_margin), 0) AS estimated_margin,
                    CASE
                        WHEN SUM(net_sales) = 0 THEN NULL
                        ELSE SUM(estimated_margin) / SUM(net_sales) * 100
                    END AS margin_rate_pct,
                    CASE
                        WHEN SUM(gross_sales) = 0 THEN NULL
                        ELSE SUM(discount_percent * gross_sales) / SUM(gross_sales)
                    END AS average_discount_percent,
                    CASE
                        WHEN SUM(quantity) = 0 THEN NULL
                        ELSE SUM(net_sales) / SUM(quantity)
                    END AS average_unit_price,
                    CASE
                        WHEN SUM(recommended_price * quantity) = 0 THEN NULL
                        ELSE SUM((unit_price - recommended_price) * quantity)
                             / SUM(recommended_price * quantity) * 100
                    END AS price_vs_recommended_pct,
                    MIN(currency) AS currency
                FROM supplier_order_line_facts
                WHERE supplier_code = %(supplier_code)s
                  AND (%(date_from)s::date IS NULL OR order_date >= %(date_from)s::date)
                  AND (%(date_to)s::date IS NULL OR order_date <= %(date_to)s::date)
                  AND (%(sku)s::text IS NULL OR sku = %(sku)s::text)
                  AND (%(category)s::text IS NULL OR category = %(category)s::text)
                  AND (%(brand)s::text IS NULL OR brand = %(brand)s::text)
                GROUP BY sku, product_name, brand, category, recommended_price, unit_cost
                ORDER BY {sort_column} DESC NULLS LAST, product_name ASC
                LIMIT %(limit)s
            """,
            params={
                "date_from": date_from_value,
                "date_to": date_to_value,
                "sku": empty_to_none(sku),
                "category": empty_to_none(category),
                "brand": empty_to_none(brand),
                "limit": safe_limit,
            },
        )

        return json_ready(
            {
                "period": {"date_from": date_from_value, "date_to": date_to_value},
                "filters": {"sku": sku, "category": category, "brand": brand},
                "sort_by": sort_by,
                "rows": rows,
            }
        )

    async def get_market_benchmark(
        self,
        *,
        supplier_code: str,
        period_type: PeriodType = "month",
        date_from: DateLike = None,
        date_to: DateLike = None,
    ) -> dict[str, Any]:
        """Return precomputed market benchmark rows for the supplier."""
        if period_type not in {"week", "month"}:
            raise ValueError("period_type must be 'week' or 'month'")

        date_from_value = self._parse_date(date_from)
        date_to_value = self._parse_date(date_to)
        self._validate_date_range(date_from_value, date_to_value)

        rows = await self._fetch_all(
            supplier_code=supplier_code,
            query="""
                SELECT
                    period_type,
                    period_start,
                    period_label,
                    supplier_revenue,
                    supplier_units,
                    supplier_orders,
                    comparable_market_revenue,
                    comparable_market_units,
                    comparable_market_orders,
                    estimated_market_share_pct
                FROM market_benchmarks
                WHERE supplier_code = %(supplier_code)s
                  AND period_type = %(period_type)s
                  AND (%(date_from)s::date IS NULL OR period_start >= %(date_from)s::date)
                  AND (%(date_to)s::date IS NULL OR period_start <= %(date_to)s::date)
                ORDER BY period_start
            """,
            params={
                "period_type": period_type,
                "date_from": date_from_value,
                "date_to": date_to_value,
            },
        )

        return json_ready(
            {
                "period": {"date_from": date_from_value, "date_to": date_to_value},
                "period_type": period_type,
                "summary": self._summarize_benchmark_rows(rows),
                "periods": rows,
            }
        )

    async def find_sales_changes(
        self,
        *,
        supplier_code: str,
        current_date_from: DateLike,
        current_date_to: DateLike,
        comparison_date_from: DateLike,
        comparison_date_to: DateLike,
        breakdown_by: BreakdownDimension = "category",
        metric: ChangeMetric = "net_sales",
        limit: int = 10,
    ) -> dict[str, Any]:
        """Compare two periods and return the largest positive/negative movers."""
        dimension_column, dimension_label = self._get_dimension(breakdown_by)
        metric_expression = self._get_change_metric_expression(metric)
        safe_limit = self._safe_limit(limit, default=10, maximum=100)

        current_from = self._parse_required_date(current_date_from, "current_date_from")
        current_to = self._parse_required_date(current_date_to, "current_date_to")
        comparison_from = self._parse_required_date(comparison_date_from, "comparison_date_from")
        comparison_to = self._parse_required_date(comparison_date_to, "comparison_date_to")
        self._validate_date_range(current_from, current_to)
        self._validate_date_range(comparison_from, comparison_to)

        rows = await self._fetch_all(
            supplier_code=supplier_code,
            query=f"""
                WITH current_period AS (
                    SELECT
                        {dimension_column} AS dimension_value,
                        {metric_expression} AS current_value
                    FROM supplier_order_line_facts
                    WHERE supplier_code = %(supplier_code)s
                      AND order_date >= %(current_from)s::date
                      AND order_date <= %(current_to)s::date
                    GROUP BY {dimension_column}
                ),
                comparison_period AS (
                    SELECT
                        {dimension_column} AS dimension_value,
                        {metric_expression} AS comparison_value
                    FROM supplier_order_line_facts
                    WHERE supplier_code = %(supplier_code)s
                      AND order_date >= %(comparison_from)s::date
                      AND order_date <= %(comparison_to)s::date
                    GROUP BY {dimension_column}
                ),
                joined AS (
                    SELECT
                        COALESCE(c.dimension_value, p.dimension_value) AS dimension_value,
                        COALESCE(c.current_value, 0) AS current_value,
                        COALESCE(p.comparison_value, 0) AS comparison_value,
                        COALESCE(c.current_value, 0) - COALESCE(p.comparison_value, 0) AS absolute_change
                    FROM current_period c
                    FULL OUTER JOIN comparison_period p
                        ON p.dimension_value = c.dimension_value
                ),
                totals AS (
                    SELECT NULLIF(SUM(absolute_change), 0) AS total_change
                    FROM joined
                )
                SELECT
                    joined.dimension_value,
                    '{dimension_label}' AS dimension_label,
                    joined.current_value,
                    joined.comparison_value,
                    joined.absolute_change,
                    CASE
                        WHEN joined.comparison_value = 0 AND joined.current_value = 0 THEN 0
                        WHEN joined.comparison_value = 0 THEN NULL
                        ELSE joined.absolute_change / joined.comparison_value * 100
                    END AS percent_change,
                    CASE
                        WHEN totals.total_change IS NULL THEN NULL
                        ELSE joined.absolute_change / totals.total_change * 100
                    END AS contribution_to_total_change_pct
                FROM joined
                CROSS JOIN totals
                ORDER BY ABS(joined.absolute_change) DESC, joined.dimension_value ASC
                LIMIT %(limit)s
            """,
            params={
                "current_from": current_from,
                "current_to": current_to,
                "comparison_from": comparison_from,
                "comparison_to": comparison_to,
                "limit": safe_limit,
            },
        )

        return json_ready(
            {
                "current_period": {"date_from": current_from, "date_to": current_to},
                "comparison_period": {"date_from": comparison_from, "date_to": comparison_to},
                "breakdown_by": breakdown_by,
                "metric": metric,
                "rows": rows,
            }
        )

    async def get_available_data_context(
        self,
        *,
        supplier_code: str,
        include_products: bool = True,
        include_regions: bool = True,
        include_channels: bool = True,
        include_customer_segments: bool = True,
        product_limit: int = 200,
    ) -> dict[str, Any]:
        """Describe which data is available for the scoped supplier."""
        safe_product_limit = self._safe_limit(product_limit, default=200, maximum=1000)

        overview = await self._fetch_one(
            supplier_code=supplier_code,
            query="""
                SELECT
                    MIN(order_date) AS min_order_date,
                    MAX(order_date) AS max_order_date,
                    COUNT(DISTINCT sku) AS product_count,
                    COUNT(DISTINCT order_id) AS order_count,
                    COUNT(*) AS order_line_count,
                    MIN(currency) AS currency
                FROM supplier_order_line_facts
                WHERE supplier_code = %(supplier_code)s
            """,
            params={},
        )

        categories_and_brands = await self._fetch_one(
            supplier_code=supplier_code,
            query="""
                SELECT
                    COALESCE(array_agg(DISTINCT category ORDER BY category), ARRAY[]::text[]) AS categories,
                    COALESCE(array_agg(DISTINCT brand ORDER BY brand), ARRAY[]::text[]) AS brands
                FROM supplier_order_line_facts
                WHERE supplier_code = %(supplier_code)s
            """,
            params={},
        )

        result: dict[str, Any] = {
            "date_range": {
                "min_order_date": overview.get("min_order_date"),
                "max_order_date": overview.get("max_order_date"),
            },
            "product_count": overview.get("product_count", 0),
            "order_count": overview.get("order_count", 0),
            "order_line_count": overview.get("order_line_count", 0),
            "currency": overview.get("currency"),
            "categories": categories_and_brands.get("categories", []),
            "brands": categories_and_brands.get("brands", []),
        }

        if include_products:
            result["products"] = await self._fetch_all(
                supplier_code=supplier_code,
                query="""
                    SELECT DISTINCT sku, product_name, brand, category
                    FROM supplier_order_line_facts
                    WHERE supplier_code = %(supplier_code)s
                    ORDER BY product_name, sku
                    LIMIT %(limit)s
                """,
                params={"limit": safe_product_limit},
            )

        if include_regions:
            result["countries"] = await self._fetch_scalar_list(
                supplier_code=supplier_code,
                column="country",
            )
            result["regions"] = await self._fetch_scalar_list(
                supplier_code=supplier_code,
                column="region",
            )
            result["cities"] = await self._fetch_scalar_list(
                supplier_code=supplier_code,
                column="city",
            )

        if include_channels:
            result["sales_channels"] = await self._fetch_scalar_list(
                supplier_code=supplier_code,
                column="sales_channel",
            )

        if include_customer_segments:
            result["customer_segments"] = await self._fetch_scalar_list(
                supplier_code=supplier_code,
                column="customer_segment",
            )

        return json_ready(result)

    async def _get_previous_period_comparison(
        self,
        *,
        supplier_code: str,
        date_from: date,
        date_to: date,
    ) -> dict[str, Any]:
        period_days = (date_to - date_from).days + 1
        previous_to = date_from - timedelta(days=1)
        previous_from = previous_to - timedelta(days=period_days - 1)

        current_previous_rows = await self._fetch_one(
            supplier_code=supplier_code,
            query="""
                SELECT
                    COALESCE(SUM(net_sales), 0) AS previous_net_sales,
                    COALESCE(SUM(quantity), 0) AS previous_units,
                    COUNT(DISTINCT order_id) AS previous_orders,
                    COALESCE(SUM(estimated_margin), 0) AS previous_estimated_margin
                FROM supplier_order_line_facts
                WHERE supplier_code = %(supplier_code)s
                  AND order_date >= %(previous_from)s::date
                  AND order_date <= %(previous_to)s::date
            """,
            params={"previous_from": previous_from, "previous_to": previous_to},
        )

        current_rows = await self._fetch_one(
            supplier_code=supplier_code,
            query="""
                SELECT
                    COALESCE(SUM(net_sales), 0) AS current_net_sales,
                    COALESCE(SUM(quantity), 0) AS current_units,
                    COUNT(DISTINCT order_id) AS current_orders,
                    COALESCE(SUM(estimated_margin), 0) AS current_estimated_margin
                FROM supplier_order_line_facts
                WHERE supplier_code = %(supplier_code)s
                  AND order_date >= %(date_from)s::date
                  AND order_date <= %(date_to)s::date
            """,
            params={"date_from": date_from, "date_to": date_to},
        )

        return {
            "previous_period": {"date_from": previous_from, "date_to": previous_to},
            **current_previous_rows,
            **current_rows,
            "net_sales_change_pct": percent_change(
                current_rows.get("current_net_sales"),
                current_previous_rows.get("previous_net_sales"),
            ),
            "units_change_pct": percent_change(
                current_rows.get("current_units"),
                current_previous_rows.get("previous_units"),
            ),
            "orders_change_pct": percent_change(
                current_rows.get("current_orders"),
                current_previous_rows.get("previous_orders"),
            ),
            "estimated_margin_change_pct": percent_change(
                current_rows.get("current_estimated_margin"),
                current_previous_rows.get("previous_estimated_margin"),
            ),
        }

    async def _fetch_all(
        self,
        *,
        supplier_code: str,
        query: str,
        params: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        merged_params = {**params, "supplier_code": supplier_code}
        async with self.pool.connection() as conn:
            async with conn.transaction():
                # Defense-in-depth for future scoped views/RLS-like patterns.
                await conn.execute(
                    "SELECT set_config('app.supplier_code', %s, true)",
                    (supplier_code,),
                )
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(query, merged_params)
                    rows = await cur.fetchall()
                    return [dict(row) for row in rows]

    async def _fetch_one(
        self,
        *,
        supplier_code: str,
        query: str,
        params: Mapping[str, Any],
    ) -> dict[str, Any]:
        rows = await self._fetch_all(
            supplier_code=supplier_code,
            query=query,
            params=params,
        )
        return rows[0] if rows else {}

    async def _fetch_scalar_list(self, *, supplier_code: str, column: str) -> list[str]:
        if column not in {"country", "region", "city", "sales_channel", "customer_segment"}:
            raise ValueError(f"Unsupported scalar context column: {column}")

        rows = await self._fetch_all(
            supplier_code=supplier_code,
            query=f"""
                SELECT DISTINCT {column} AS value
                FROM supplier_order_line_facts
                WHERE supplier_code = %(supplier_code)s
                  AND {column} IS NOT NULL
                ORDER BY {column}
            """,
            params={},
        )
        return [row["value"] for row in rows]

    def _summarize_benchmark_rows(self, rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        if not rows:
            return {
                "period_count": 0,
                "latest_market_share_pct": None,
                "market_share_change_pct_points": None,
                "supplier_revenue_growth_pct": None,
                "comparable_market_revenue_growth_pct": None,
            }

        first = rows[0]
        latest = rows[-1]
        return {
            "period_count": len(rows),
            "first_period_start": first.get("period_start"),
            "latest_period_start": latest.get("period_start"),
            "latest_market_share_pct": latest.get("estimated_market_share_pct"),
            "market_share_change_pct_points": decimal_or_none(latest.get("estimated_market_share_pct"))
            - decimal_or_none(first.get("estimated_market_share_pct"))
            if latest.get("estimated_market_share_pct") is not None
            and first.get("estimated_market_share_pct") is not None
            else None,
            "supplier_revenue_growth_pct": percent_change(
                latest.get("supplier_revenue"),
                first.get("supplier_revenue"),
            ),
            "comparable_market_revenue_growth_pct": percent_change(
                latest.get("comparable_market_revenue"),
                first.get("comparable_market_revenue"),
            ),
        }

    @staticmethod
    def _parse_date(value: DateLike) -> date | None:
        if value is None or value == "":
            return None
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        return date.fromisoformat(str(value))

    @classmethod
    def _parse_required_date(cls, value: DateLike, field_name: str) -> date:
        parsed = cls._parse_date(value)
        if parsed is None:
            raise ValueError(f"{field_name} is required")
        return parsed

    @staticmethod
    def _validate_date_range(date_from: date | None, date_to: date | None) -> None:
        if date_from and date_to and date_from > date_to:
            raise ValueError("date_from must be earlier than or equal to date_to")

    @staticmethod
    def _validate_grain(grain: str) -> None:
        if grain not in GRAIN_EXPRESSIONS:
            raise ValueError("grain must be one of: day, week, month")

    @staticmethod
    def _get_dimension(breakdown_by: str) -> tuple[str, str]:
        try:
            return DIMENSIONS[breakdown_by]
        except KeyError as exc:
            raise ValueError(
                f"Unsupported breakdown_by '{breakdown_by}'. "
                f"Allowed values: {', '.join(DIMENSIONS)}"
            ) from exc

    @staticmethod
    def _get_sales_sort_column(metric: str) -> str:
        try:
            return SALES_SORT_COLUMNS[metric]
        except KeyError as exc:
            raise ValueError(
                f"Unsupported metric '{metric}'. "
                f"Allowed values: {', '.join(SALES_SORT_COLUMNS)}"
            ) from exc

    @staticmethod
    def _get_product_sort_column(sort_by: str) -> str:
        try:
            return PRODUCT_SORT_COLUMNS[sort_by]
        except KeyError as exc:
            raise ValueError(
                f"Unsupported sort_by '{sort_by}'. "
                f"Allowed values: {', '.join(PRODUCT_SORT_COLUMNS)}"
            ) from exc

    @staticmethod
    def _get_change_metric_expression(metric: str) -> str:
        try:
            return CHANGE_METRIC_EXPRESSIONS[metric]
        except KeyError as exc:
            raise ValueError(
                f"Unsupported metric '{metric}'. "
                f"Allowed values: {', '.join(CHANGE_METRIC_EXPRESSIONS)}"
            ) from exc

    @staticmethod
    def _get_sort_direction(sort: str) -> str:
        normalized = sort.lower()
        if normalized not in {"asc", "desc"}:
            raise ValueError("sort must be 'asc' or 'desc'")
        return normalized.upper()

    @staticmethod
    def _safe_limit(limit: int, *, default: int, maximum: int) -> int:
        try:
            parsed = int(limit)
        except (TypeError, ValueError):
            return default
        return max(1, min(parsed, maximum))


def empty_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def decimal_or_none(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def percent_change(current: Any, previous: Any) -> Decimal | None:
    current_decimal = decimal_or_none(current)
    previous_decimal = decimal_or_none(previous)
    if current_decimal is None or previous_decimal is None or previous_decimal == 0:
        return None
    return (current_decimal - previous_decimal) / previous_decimal * Decimal("100")


def json_ready(value: Any) -> Any:
    """Convert psycopg/Postgres values into MCP/JSON-friendly values."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, list):
        return [json_ready(item) for item in value]
    if isinstance(value, tuple):
        return [json_ready(item) for item in value]
    if isinstance(value, dict):
        return {key: json_ready(item) for key, item in value.items()}
    return value
