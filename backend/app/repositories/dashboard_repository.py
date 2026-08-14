from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.engine import Connection

from app.schemas.dashboard import Grain, Metric, StoreGroupBy

_METRIC_SQL: dict[Metric, str] = {
    "net_sales": "SUM(f.net_sales)",
    "gross_sales": "SUM(f.gross_sales)",
    "units": "SUM(f.quantity)",
    "orders": "COUNT(DISTINCT f.order_id)",
    "discounts": "SUM(f.discounts)",
}

_GRAIN_SQL: dict[Grain, str] = {
    "week": "date_trunc('week', f.order_date)::date",
    "month": "date_trunc('month', f.order_date)::date",
}

_STORE_GROUP_SQL: dict[StoreGroupBy, tuple[str, str]] = {
    "store": ("f.store_id", "f.store_name"),
    "city": ("f.city", "f.city"),
    "channel": ("f.channel", "f.channel"),
}


class DashboardRepository:
    """Read-only supplier dashboard queries over v_supplier_sales_facts."""

    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def fetch_summary(
        self,
        *,
        supplier_id: str,
        date_from: date | None,
        date_to: date | None,
    ) -> dict[str, Any]:
        where_sql, params = _scope(
            supplier_id=supplier_id, date_from=date_from, date_to=date_to
        )
        stmt = text(
            f"""
            SELECT
                COALESCE(SUM(f.gross_sales), 0) AS gross_sales,
                COALESCE(SUM(f.net_sales), 0) AS net_sales,
                COALESCE(SUM(f.discounts), 0) AS discounts,
                COALESCE(SUM(f.quantity), 0) AS units,
                COUNT(DISTINCT f.order_id) AS orders
            FROM v_supplier_sales_facts f
            WHERE {where_sql}
            """
        )
        return dict(self._connection.execute(stmt, params).mappings().one())

    def fetch_top_products(
        self,
        *,
        supplier_id: str,
        date_from: date | None,
        date_to: date | None,
        sort_by: Metric,
        limit: int,
    ) -> list[dict[str, Any]]:
        where_sql, params = _scope(
            supplier_id=supplier_id, date_from=date_from, date_to=date_to
        )
        metric_sql = _METRIC_SQL[sort_by]
        params["limit"] = limit
        stmt = text(
            f"""
            SELECT
                f.product_id,
                f.product_name,
                f.category,
                COALESCE(SUM(f.net_sales), 0) AS net_sales,
                COALESCE(SUM(f.gross_sales), 0) AS gross_sales,
                COALESCE(SUM(f.quantity), 0) AS units,
                COUNT(DISTINCT f.order_id) AS orders,
                COALESCE(SUM(f.discounts), 0) AS discounts
            FROM v_supplier_sales_facts f
            WHERE {where_sql}
            GROUP BY f.product_id, f.product_name, f.category
            ORDER BY {metric_sql} DESC, f.product_name ASC
            LIMIT :limit
            """
        )
        return [dict(row) for row in self._connection.execute(stmt, params).mappings().all()]

    def fetch_products(
        self,
        *,
        supplier_id: str,
        date_from: date | None,
        date_to: date | None,
    ) -> list[dict[str, Any]]:
        where_sql, params = _scope(
            supplier_id=supplier_id, date_from=date_from, date_to=date_to
        )
        stmt = text(
            f"""
            SELECT
                f.product_id,
                f.product_name,
                f.category,
                COALESCE(SUM(f.net_sales), 0) AS net_sales,
                COALESCE(SUM(f.quantity), 0) AS units
            FROM v_supplier_sales_facts f
            WHERE {where_sql}
            GROUP BY f.product_id, f.product_name, f.category
            ORDER BY net_sales DESC, f.product_name ASC
            """
        )
        return [dict(row) for row in self._connection.execute(stmt, params).mappings().all()]

    def fetch_product_timeseries(
        self,
        *,
        supplier_id: str,
        date_from: date | None,
        date_to: date | None,
        grain: Grain,
        metric: Metric,
        product_ids: list[str] | None,
        limit_products: int,
    ) -> list[dict[str, Any]]:
        effective_product_ids = product_ids
        if not effective_product_ids:
            effective_product_ids = self._fetch_top_product_ids(
                supplier_id=supplier_id,
                date_from=date_from,
                date_to=date_to,
                metric=metric,
                limit=limit_products,
            )

        if not effective_product_ids:
            return []

        where_sql, params = _scope(
            supplier_id=supplier_id, date_from=date_from, date_to=date_to
        )
        params["product_ids"] = effective_product_ids
        period_sql = _GRAIN_SQL[grain]
        metric_sql = _METRIC_SQL[metric]

        stmt = text(
            f"""
            SELECT
                {period_sql} AS period,
                f.product_id,
                f.product_name,
                f.category,
                COALESCE({metric_sql}, 0) AS value
            FROM v_supplier_sales_facts f
            WHERE {where_sql}
              AND f.product_id IN :product_ids
            GROUP BY period, f.product_id, f.product_name, f.category
            ORDER BY period ASC, f.product_name ASC
            """
        ).bindparams(bindparam("product_ids", expanding=True))

        return [dict(row) for row in self._connection.execute(stmt, params).mappings().all()]

    def fetch_store_breakdown(
        self,
        *,
        supplier_id: str,
        date_from: date | None,
        date_to: date | None,
        metric: Metric,
        group_by: StoreGroupBy,
    ) -> list[dict[str, Any]]:
        where_sql, params = _scope(
            supplier_id=supplier_id, date_from=date_from, date_to=date_to
        )
        group_id_sql, group_name_sql = _STORE_GROUP_SQL[group_by]
        metric_sql = _METRIC_SQL[metric]
        stmt = text(
            f"""
            SELECT
                {group_id_sql} AS group_id,
                {group_name_sql} AS group_name,
                COALESCE({metric_sql}, 0) AS value
            FROM v_supplier_sales_facts f
            WHERE {where_sql}
            GROUP BY {group_id_sql}, {group_name_sql}
            ORDER BY value DESC, group_name ASC
            """
        )
        return [dict(row) for row in self._connection.execute(stmt, params).mappings().all()]

    def _fetch_top_product_ids(
        self,
        *,
        supplier_id: str,
        date_from: date | None,
        date_to: date | None,
        metric: Metric,
        limit: int,
    ) -> list[str]:
        where_sql, params = _scope(
            supplier_id=supplier_id, date_from=date_from, date_to=date_to
        )
        params["limit"] = limit
        metric_sql = _METRIC_SQL[metric]
        stmt = text(
            f"""
            SELECT f.product_id
            FROM v_supplier_sales_facts f
            WHERE {where_sql}
            GROUP BY f.product_id
            ORDER BY {metric_sql} DESC, f.product_id ASC
            LIMIT :limit
            """
        )
        return [str(row[0]) for row in self._connection.execute(stmt, params).all()]


def _scope(
    *,
    supplier_id: str,
    date_from: date | None,
    date_to: date | None,
) -> tuple[str, dict[str, Any]]:
    clauses = ["f.supplier_id = :supplier_id"]
    params: dict[str, Any] = {"supplier_id": supplier_id}
    if date_from is not None:
        clauses.append("f.order_date >= :date_from")
        params["date_from"] = date_from
    if date_to is not None:
        clauses.append("f.order_date <= :date_to")
        params["date_to"] = date_to
    return " AND ".join(clauses), params
