from __future__ import annotations

from datetime import date

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.schemas.common import SupplierSalesMetric, TimeGrain


_METRIC_SQL: dict[SupplierSalesMetric, str] = {
    "net_sales": "SUM(oi.quantity * oi.unit_price_sek - oi.discount_amount_sek)",
    "gross_sales": "SUM(oi.quantity * oi.unit_price_sek)",
    "units": "SUM(oi.quantity)",
    "discounts": "SUM(oi.discount_amount_sek)",
    "orders": "COUNT(DISTINCT o.order_id)",
}

_GRAIN_SQL: dict[TimeGrain, str] = {
    "week": "date_trunc('week', o.order_date)::date",
    "month": "date_trunc('month', o.order_date)::date",
}

# Metric SQL expressions against v_supplier_sales_facts columns (alias: f).
_VIEW_METRIC_SQL: dict[str, str] = {
    "net_sales": "SUM(f.net_sales)",
    "gross_sales": "SUM(f.gross_sales)",
    "units": "SUM(f.quantity)",
    "discounts": "SUM(f.discounts)",
    "orders": "COUNT(DISTINCT f.order_id)",
}


class SalesRepository:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self.pool = pool

    async def _fetch_all(self, query: str, params: dict) -> list[dict]:
        if self.pool.closed:
            await self.pool.open(wait=True)

        async with self.pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(query, params)
                rows = await cur.fetchall()

        return [dict(row) for row in rows]

    async def fetch_supplier_product_timeseries(
        self,
        *,
        supplier_id: str,
        date_from: date | None,
        date_to: date | None,
        grain: TimeGrain,
        metric: SupplierSalesMetric,
        product_ids: list[str] | None = None,
        limit_products: int = 5,
    ) -> list[dict]:
        metric_sql = _METRIC_SQL[metric]
        grain_sql = _GRAIN_SQL[grain]

        if product_ids is not None:
            # Explicit product filter — limit_products is ignored
            query = f"""
                SELECT
                    {grain_sql} AS period,
                    p.product_id,
                    p.product_name,
                    p.category,
                    ROUND(({metric_sql})::numeric, 2) AS value
                FROM order_items oi
                JOIN orders o
                    ON o.order_id = oi.order_id
                JOIN products p
                    ON p.product_id = oi.product_id
                WHERE p.supplier_id = %(supplier_id)s
                  AND o.order_status = 'completed'
                  AND (%(date_from)s::date IS NULL OR o.order_date >= %(date_from)s::date)
                  AND (%(date_to)s::date IS NULL OR o.order_date <= %(date_to)s::date)
                  AND p.product_id = ANY(%(product_ids)s::text[])
                GROUP BY period, p.product_id, p.product_name, p.category
                ORDER BY period ASC, p.product_name ASC;
            """
            return await self._fetch_all(
                query,
                {
                    "supplier_id": supplier_id,
                    "date_from": date_from,
                    "date_to": date_to,
                    "product_ids": product_ids,
                },
            )
        else:
            # No explicit products — CTE identifies top N products by metric first
            query = f"""
                WITH top_products AS (
                    SELECT p.product_id
                    FROM order_items oi
                    JOIN orders o
                        ON o.order_id = oi.order_id
                    JOIN products p
                        ON p.product_id = oi.product_id
                    WHERE p.supplier_id = %(supplier_id)s
                      AND o.order_status = 'completed'
                      AND (%(date_from)s::date IS NULL OR o.order_date >= %(date_from)s::date)
                      AND (%(date_to)s::date IS NULL OR o.order_date <= %(date_to)s::date)
                    GROUP BY p.product_id
                    ORDER BY {metric_sql} DESC
                    LIMIT %(limit_products)s
                )
                SELECT
                    {grain_sql} AS period,
                    p.product_id,
                    p.product_name,
                    p.category,
                    ROUND(({metric_sql})::numeric, 2) AS value
                FROM order_items oi
                JOIN orders o
                    ON o.order_id = oi.order_id
                JOIN products p
                    ON p.product_id = oi.product_id
                WHERE p.supplier_id = %(supplier_id)s
                  AND o.order_status = 'completed'
                  AND (%(date_from)s::date IS NULL OR o.order_date >= %(date_from)s::date)
                  AND (%(date_to)s::date IS NULL OR o.order_date <= %(date_to)s::date)
                  AND p.product_id IN (SELECT product_id FROM top_products)
                GROUP BY period, p.product_id, p.product_name, p.category
                ORDER BY period ASC, p.product_name ASC;
            """
            return await self._fetch_all(
                query,
                {
                    "supplier_id": supplier_id,
                    "date_from": date_from,
                    "date_to": date_to,
                    "limit_products": limit_products,
                },
            )

    async def fetch_supplier_sales_summary(
        self,
        *,
        supplier_id: str,
        date_from: date | None,
        date_to: date | None,
    ) -> list[dict]:
        query = """
            SELECT
                ROUND(SUM(oi.quantity * oi.unit_price_sek)::numeric, 2) AS gross_sales,
                ROUND(SUM(oi.quantity * oi.unit_price_sek - oi.discount_amount_sek)::numeric, 2) AS net_sales,
                ROUND(SUM(oi.discount_amount_sek)::numeric, 2) AS discounts,
                SUM(oi.quantity) AS units,
                COUNT(DISTINCT o.order_id) AS orders
            FROM order_items oi
            JOIN orders o
                ON o.order_id = oi.order_id
            JOIN products p
                ON p.product_id = oi.product_id
            WHERE p.supplier_id = %(supplier_id)s
              AND o.order_status = 'completed'
              AND (%(date_from)s::date IS NULL OR o.order_date >= %(date_from)s::date)
              AND (%(date_to)s::date IS NULL OR o.order_date <= %(date_to)s::date);
        """

        return await self._fetch_all(
            query,
            {
                "supplier_id": supplier_id,
                "date_from": date_from,
                "date_to": date_to,
            },
        )

    async def fetch_supplier_top_products(
        self,
        *,
        supplier_id: str,
        date_from: date | None,
        date_to: date | None,
        metric: SupplierSalesMetric,
        limit: int,
    ) -> list[dict]:
        metric_sql = _METRIC_SQL[metric]

        query = f"""
            SELECT
                ROW_NUMBER() OVER (ORDER BY {metric_sql} DESC) AS rank,
                p.product_id,
                p.product_name,
                p.category,
                ROUND(({metric_sql})::numeric, 2) AS value
            FROM order_items oi
            JOIN orders o
                ON o.order_id = oi.order_id
            JOIN products p
                ON p.product_id = oi.product_id
            WHERE p.supplier_id = %(supplier_id)s
              AND o.order_status = 'completed'
              AND (%(date_from)s::date IS NULL OR o.order_date >= %(date_from)s::date)
              AND (%(date_to)s::date IS NULL OR o.order_date <= %(date_to)s::date)
            GROUP BY
                p.product_id,
                p.product_name,
                p.category
            ORDER BY
                value DESC
            LIMIT %(limit)s;
        """

        return await self._fetch_all(
            query,
            {
                "supplier_id": supplier_id,
                "date_from": date_from,
                "date_to": date_to,
                "limit": limit,
            },
        )

    async def fetch_supplier_top_products_multi_metric(
        self,
        *,
        supplier_id: str,
        date_from: date | None,
        date_to: date | None,
        sort_by: SupplierSalesMetric,
        limit: int,
    ) -> list[dict]:
        sort_by_sql = _METRIC_SQL[sort_by]

        query = f"""
            SELECT
                ROW_NUMBER() OVER (ORDER BY {sort_by_sql} DESC) AS rank,
                p.product_id,
                p.product_name,
                p.category,
                ROUND((SUM(oi.quantity * oi.unit_price_sek - oi.discount_amount_sek))::numeric, 2) AS net_sales,
                ROUND((SUM(oi.quantity * oi.unit_price_sek))::numeric, 2) AS gross_sales,
                SUM(oi.quantity) AS units,
                COUNT(DISTINCT o.order_id) AS orders,
                ROUND((SUM(oi.discount_amount_sek))::numeric, 2) AS discounts
            FROM order_items oi
            JOIN orders o
                ON o.order_id = oi.order_id
            JOIN products p
                ON p.product_id = oi.product_id
            WHERE p.supplier_id = %(supplier_id)s
              AND o.order_status = 'completed'
              AND (%(date_from)s::date IS NULL OR o.order_date >= %(date_from)s::date)
              AND (%(date_to)s::date IS NULL OR o.order_date <= %(date_to)s::date)
            GROUP BY
                p.product_id,
                p.product_name,
                p.category
            ORDER BY
                {sort_by_sql} DESC
            LIMIT %(limit)s;
        """

        return await self._fetch_all(
            query,
            {
                "supplier_id": supplier_id,
                "date_from": date_from,
                "date_to": date_to,
                "limit": limit,
            },
        )

    async def fetch_supplier_products(
        self,
        *,
        supplier_id: str,
        date_from: date | None,
        date_to: date | None,
    ) -> list[dict]:
        query = """
            SELECT
                p.product_id,
                p.product_name,
                p.category,
                ROUND((SUM(oi.quantity * oi.unit_price_sek - oi.discount_amount_sek))::numeric, 2) AS net_sales,
                SUM(oi.quantity) AS units
            FROM order_items oi
            JOIN orders o
                ON o.order_id = oi.order_id
            JOIN products p
                ON p.product_id = oi.product_id
            WHERE p.supplier_id = %(supplier_id)s
              AND o.order_status = 'completed'
              AND (%(date_from)s::date IS NULL OR o.order_date >= %(date_from)s::date)
              AND (%(date_to)s::date IS NULL OR o.order_date <= %(date_to)s::date)
            GROUP BY
                p.product_id,
                p.product_name,
                p.category
            ORDER BY
                net_sales DESC;
        """

        return await self._fetch_all(
            query,
            {
                "supplier_id": supplier_id,
                "date_from": date_from,
                "date_to": date_to,
            },
        )

    async def fetch_supplier_store_breakdown(
        self,
        *,
        supplier_id: str,
        date_from: date | None,
        date_to: date | None,
        metric: SupplierSalesMetric,
        group_by: str,
    ) -> list[dict]:
        metric_sql = _METRIC_SQL[metric]

        group_sql = {
            "store": ("st.store_id", "st.store_name"),
            "city": ("st.city", "st.city"),
            "channel": ("st.store_type", "st.store_type"),
        }[group_by]

        query = f"""
            SELECT
                {group_sql[0]} AS group_id,
                {group_sql[1]} AS group_name,
                ROUND(({metric_sql})::numeric, 2) AS value
            FROM order_items oi
            JOIN orders o
                ON o.order_id = oi.order_id
            JOIN products p
                ON p.product_id = oi.product_id
            JOIN stores st
                ON st.store_id = o.store_id
            WHERE p.supplier_id = %(supplier_id)s
              AND o.order_status = 'completed'
              AND (%(date_from)s::date IS NULL OR o.order_date >= %(date_from)s::date)
              AND (%(date_to)s::date IS NULL OR o.order_date <= %(date_to)s::date)
            GROUP BY
                group_id,
                group_name
            ORDER BY
                value DESC;
        """

        return await self._fetch_all(
            query,
            {
                "supplier_id": supplier_id,
                "date_from": date_from,
                "date_to": date_to,
            },
        )

    # -------------------------------------------------------------------------
    # Agent-oriented methods — use v_supplier_sales_facts view
    # -------------------------------------------------------------------------

    async def fetch_supplier_ranked_products(
        self,
        *,
        supplier_id: str,
        date_from: date | None,
        date_to: date | None,
        metric: str,
        limit: int,
        city: str | None = None,
        store_id: str | None = None,
        channel: str | None = None,
        category: str | None = None,
    ) -> list[dict]:
        """Rank products by metric with optional dimension filters.

        Uses v_supplier_sales_facts. Only completed orders are included (view-filtered).
        """
        metric_expr = _VIEW_METRIC_SQL[metric]

        query = f"""
            SELECT
                ROW_NUMBER() OVER (ORDER BY {metric_expr} DESC) AS rank,
                f.product_id,
                f.product_name,
                f.category,
                ROUND(({metric_expr})::numeric, 2) AS {metric}
            FROM v_supplier_sales_facts f
            WHERE f.supplier_id = %(supplier_id)s
              AND (%(date_from)s::date IS NULL OR f.order_date >= %(date_from)s::date)
              AND (%(date_to)s::date IS NULL OR f.order_date <= %(date_to)s::date)
              AND (%(city)s::text IS NULL OR f.city = %(city)s::text)
              AND (%(store_id)s::text IS NULL OR f.store_id = %(store_id)s::text)
              AND (%(channel)s::text IS NULL OR f.channel = %(channel)s::text)
              AND (%(category)s::text IS NULL OR f.category = %(category)s::text)
            GROUP BY f.product_id, f.product_name, f.category
            ORDER BY {metric_expr} DESC
            LIMIT %(limit)s;
        """

        return await self._fetch_all(
            query,
            {
                "supplier_id": supplier_id,
                "date_from": date_from,
                "date_to": date_to,
                "city": city,
                "store_id": store_id,
                "channel": channel,
                "category": category,
                "limit": limit,
            },
        )

    async def fetch_supplier_ranked_locations(
        self,
        *,
        supplier_id: str,
        date_from: date | None,
        date_to: date | None,
        metric: str,
        group_by: str,
        limit: int,
        category: str | None = None,
        product_id: str | None = None,
    ) -> list[dict]:
        """Rank stores, cities, or channels by metric with optional product/category filters.

        Uses v_supplier_sales_facts. Only completed orders are included (view-filtered).
        """
        metric_expr = _VIEW_METRIC_SQL[metric]

        group_id_col, group_name_col = {
            "store": ("f.store_id", "f.store_name"),
            "city": ("f.city", "f.city"),
            "channel": ("f.channel", "f.channel"),
        }[group_by]

        query = f"""
            SELECT
                ROW_NUMBER() OVER (ORDER BY {metric_expr} DESC) AS rank,
                {group_id_col} AS group_id,
                {group_name_col} AS group_name,
                ROUND(({metric_expr})::numeric, 2) AS {metric}
            FROM v_supplier_sales_facts f
            WHERE f.supplier_id = %(supplier_id)s
              AND (%(date_from)s::date IS NULL OR f.order_date >= %(date_from)s::date)
              AND (%(date_to)s::date IS NULL OR f.order_date <= %(date_to)s::date)
              AND (%(category)s::text IS NULL OR f.category = %(category)s::text)
              AND (%(product_id)s::text IS NULL OR f.product_id = %(product_id)s::text)
            GROUP BY {group_id_col}, {group_name_col}
            ORDER BY {metric_expr} DESC
            LIMIT %(limit)s;
        """

        return await self._fetch_all(
            query,
            {
                "supplier_id": supplier_id,
                "date_from": date_from,
                "date_to": date_to,
                "category": category,
                "product_id": product_id,
                "limit": limit,
            },
        )

    async def fetch_supplier_filter_values(
        self,
        *,
        supplier_id: str,
    ) -> dict:
        """Return distinct filter values available for this supplier.

        Returns cities, channels, and categories.
        Uses v_supplier_sales_facts so only values with actual sales data are returned.
        """
        cities = [
            row["city"]
            for row in await self._fetch_all(
                "SELECT DISTINCT f.city FROM v_supplier_sales_facts f "
                "WHERE f.supplier_id = %(supplier_id)s ORDER BY f.city;",
                {"supplier_id": supplier_id},
            )
        ]
        channels = [
            row["channel"]
            for row in await self._fetch_all(
                "SELECT DISTINCT f.channel FROM v_supplier_sales_facts f "
                "WHERE f.supplier_id = %(supplier_id)s ORDER BY f.channel;",
                {"supplier_id": supplier_id},
            )
        ]
        categories = [
            row["category"]
            for row in await self._fetch_all(
                "SELECT DISTINCT f.category FROM v_supplier_sales_facts f "
                "WHERE f.supplier_id = %(supplier_id)s ORDER BY f.category;",
                {"supplier_id": supplier_id},
            )
        ]
        return {"cities": cities, "channels": channels, "categories": categories}