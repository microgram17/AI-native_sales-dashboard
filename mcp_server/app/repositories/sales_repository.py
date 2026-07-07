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
    ) -> list[dict]:
        metric_sql = _METRIC_SQL[metric]
        grain_sql = _GRAIN_SQL[grain]

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
              AND (%(date_from)s IS NULL OR o.order_date >= %(date_from)s)
              AND (%(date_to)s IS NULL OR o.order_date <= %(date_to)s)
              AND (
                    %(product_ids)s IS NULL
                    OR p.product_id = ANY(%(product_ids)s)
              )
            GROUP BY
                period,
                p.product_id,
                p.product_name,
                p.category
            ORDER BY
                period ASC,
                p.product_name ASC;
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
              AND (%(date_from)s IS NULL OR o.order_date >= %(date_from)s)
              AND (%(date_to)s IS NULL OR o.order_date <= %(date_to)s);
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
              AND (%(date_from)s IS NULL OR o.order_date >= %(date_from)s)
              AND (%(date_to)s IS NULL OR o.order_date <= %(date_to)s)
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
              AND (%(date_from)s IS NULL OR o.order_date >= %(date_from)s)
              AND (%(date_to)s IS NULL OR o.order_date <= %(date_to)s)
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