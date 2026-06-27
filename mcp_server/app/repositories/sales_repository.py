from typing import Any

from app.db.connection import get_connection


def get_supplier_summary(supplier_code: str) -> dict[str, Any]:
    query = """
        SELECT
            p.supplier_code,
            s.supplier_name,
            COUNT(DISTINCT oi.order_id) AS total_orders,
            COALESCE(SUM(oi.quantity), 0) AS total_units,
            COALESCE(SUM(oi.net_sales), 0) AS total_revenue,
            COALESCE(SUM(oi.estimated_margin), 0) AS estimated_margin,
            CASE
                WHEN COUNT(DISTINCT oi.order_id) = 0 THEN 0
                ELSE COALESCE(SUM(oi.net_sales), 0) / COUNT(DISTINCT oi.order_id)
            END AS average_order_value
        FROM order_items oi
        JOIN products p
            ON p.sku = oi.sku
        JOIN suppliers s
            ON s.supplier_code = p.supplier_code
        WHERE p.supplier_code = %s
        GROUP BY p.supplier_code, s.supplier_name;
    """

    market_share_query = """
        SELECT
            period_label,
            estimated_market_share_pct
        FROM market_benchmarks
        WHERE supplier_code = %s
          AND period_type = 'month'
        ORDER BY period_start DESC
        LIMIT 1;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (supplier_code,))
            row = cur.fetchone()

            if row is None:
                return {
                    "supplier_code": supplier_code,
                    "found": False,
                    "message": "Supplier not found or has no sales data.",
                }

            cur.execute(market_share_query, (supplier_code,))
            market_share_row = cur.fetchone()

    return {
        "supplier_code": row[0],
        "supplier_name": row[1],
        "found": True,
        "total_orders": int(row[2]),
        "total_units": int(row[3]),
        "total_revenue": float(row[4]),
        "estimated_margin": float(row[5]),
        "average_order_value": float(row[6]),
        "latest_market_share": {
            "period": market_share_row[0],
            "estimated_market_share_pct": float(market_share_row[1]),
        }
        if market_share_row
        else None,
    }


def get_supplier_revenue_trend(
    supplier_code: str,
    period_type: str = "month",
) -> dict[str, Any]:
    normalized_period_type = period_type.lower().strip()
    if normalized_period_type not in {"week", "month"}:
        return {
            "supplier_code": supplier_code,
            "period_type": normalized_period_type,
            "found": False,
            "message": "Invalid period_type. Use 'week' or 'month'.",
            "points": [],
        }

    trend_query = """
        SELECT
            period_start,
            period_label,
            supplier_revenue,
            comparable_market_revenue,
            estimated_market_share_pct
        FROM market_benchmarks
        WHERE supplier_code = %s
          AND period_type = %s
        ORDER BY period_start ASC;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(trend_query, (supplier_code, normalized_period_type))
            rows = cur.fetchall()

    if not rows:
        return {
            "supplier_code": supplier_code,
            "period_type": normalized_period_type,
            "found": False,
            "message": "No revenue trend data available.",
            "points": [],
        }

    points = [
        {
            "period_start": row[0].isoformat(),
            "period_label": row[1],
            "supplier_revenue": float(row[2]),
            "comparable_market_revenue": float(row[3]),
            "estimated_market_share_pct": float(row[4]),
        }
        for row in rows
    ]

    return {
        "supplier_code": supplier_code,
        "period_type": normalized_period_type,
        "found": True,
        "points": points,
    }


def get_top_products(
    supplier_code: str,
    limit: int = 5,
    sort_by: str = "revenue",
) -> dict[str, Any]:
    normalized_sort_by = sort_by.lower().strip()
    allowed_sort_fields = {
        "revenue": "total_revenue",
        "units": "total_units",
        "orders": "total_orders",
    }

    if normalized_sort_by not in allowed_sort_fields:
        return {
            "supplier_code": supplier_code,
            "found": False,
            "message": "Invalid sort_by. Use 'revenue', 'units', or 'orders'.",
            "products": [],
        }

    sanitized_limit = max(1, min(int(limit), 50))
    order_column = allowed_sort_fields[normalized_sort_by]

    top_products_query = f"""
        SELECT
            p.sku,
            p.product_name,
            p.category,
            COALESCE(SUM(oi.net_sales), 0) AS total_revenue,
            COALESCE(SUM(oi.quantity), 0) AS total_units,
            COUNT(DISTINCT oi.order_id) AS total_orders
        FROM products p
        LEFT JOIN order_items oi
            ON oi.sku = p.sku
        WHERE p.supplier_code = %s
        GROUP BY p.sku, p.product_name, p.category
        ORDER BY {order_column} DESC, p.product_name ASC
        LIMIT %s;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(top_products_query, (supplier_code, sanitized_limit))
            rows = cur.fetchall()

    if not rows:
        return {
            "supplier_code": supplier_code,
            "found": False,
            "message": "No product data available for supplier.",
            "products": [],
        }

    products = [
        {
            "sku": row[0],
            "product_name": row[1],
            "category": row[2],
            "total_revenue": float(row[3]),
            "total_units": int(row[4]),
            "total_orders": int(row[5]),
        }
        for row in rows
    ]

    return {
        "supplier_code": supplier_code,
        "found": True,
        "sort_by": normalized_sort_by,
        "limit": sanitized_limit,
        "products": products,
    }


def list_suppliers() -> dict[str, Any]:
    list_query = """
        SELECT
            s.supplier_code,
            s.supplier_name,
            s.primary_brand,
            s.primary_category
        FROM suppliers s
        ORDER BY s.supplier_name ASC;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(list_query)
            rows = cur.fetchall()

    suppliers = [
        {
            "supplier_code": row[0],
            "supplier_name": row[1],
            "primary_brand": row[2],
            "primary_category": row[3],
        }
        for row in rows
    ]

    return {
        "count": len(suppliers),
        "suppliers": suppliers,
    }