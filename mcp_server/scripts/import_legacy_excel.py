from __future__ import annotations

from datetime import date
import os
from pathlib import Path
from typing import Any

import pandas as pd
from psycopg import Connection

from app.db.connection import get_connection


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = Path(os.getenv("LEGACY_DATA_DIR") or PROJECT_ROOT / "data" / "legacy_exports")


def clean_records(dataframe: pd.DataFrame) -> list[dict[str, Any]]:
    cleaned = dataframe.where(pd.notnull(dataframe), None)
    return cleaned.to_dict("records")


def load_excel_sheet(path: Path, sheet_name: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing expected file: {path}")

    return pd.read_excel(path, sheet_name=sheet_name)


def parse_month_start(month_value: Any) -> date:
    parsed = pd.to_datetime(month_value).date()
    return parsed.replace(day=1)


def insert_suppliers(conn: Connection, suppliers: pd.DataFrame) -> int:
    records = clean_records(suppliers)

    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO suppliers (
                supplier_code,
                supplier_name,
                contact_email,
                primary_brand,
                primary_category
            )
            VALUES (
                %(supplier_code)s,
                %(supplier_name)s,
                %(contact_email)s,
                %(primary_brand)s,
                %(primary_category)s
            );
            """,
            records,
        )

    return len(records)


def insert_products(conn: Connection, products: pd.DataFrame) -> int:
    records = clean_records(products)

    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO products (
                sku,
                product_name,
                brand,
                category,
                supplier_code,
                unit_cost,
                recommended_price,
                currency
            )
            VALUES (
                %(sku)s,
                %(product_name)s,
                %(brand)s,
                %(category)s,
                %(supplier_code)s,
                %(unit_cost)s,
                %(recommended_price)s,
                %(currency)s
            );
            """,
            records,
        )

    return len(records)


def insert_stores(conn: Connection, stores: pd.DataFrame) -> int:
    records = clean_records(stores)

    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO stores (
                store_id,
                store_name,
                sales_channel,
                country,
                region,
                city
            )
            VALUES (
                %(store_id)s,
                %(store_name)s,
                %(sales_channel)s,
                %(country)s,
                %(region)s,
                %(city)s
            );
            """,
            records,
        )

    return len(records)


def insert_orders(conn: Connection, raw_sales: pd.DataFrame) -> int:
    orders = (
        raw_sales[
            [
                "order_id",
                "order_date",
                "week_start",
                "month",
                "store_id",
                "customer_segment",
                "anonymized_customer_id",
            ]
        ]
        .drop_duplicates(subset=["order_id"])
        .copy()
    )

    orders["order_date"] = pd.to_datetime(orders["order_date"]).dt.date
    orders["week_start"] = pd.to_datetime(orders["week_start"]).dt.date
    orders["month_start"] = orders["month"].apply(parse_month_start)

    records = clean_records(orders)

    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO orders (
                order_id,
                order_date,
                week_start,
                month_start,
                store_id,
                customer_segment,
                anonymized_customer_id
            )
            VALUES (
                %(order_id)s,
                %(order_date)s,
                %(week_start)s,
                %(month_start)s,
                %(store_id)s,
                %(customer_segment)s,
                %(anonymized_customer_id)s
            );
            """,
            records,
        )

    return len(records)


def insert_order_items(conn: Connection, raw_sales: pd.DataFrame) -> int:
    order_items = raw_sales[
        [
            "order_line_id",
            "order_id",
            "sku",
            "quantity",
            "unit_price",
            "discount_percent",
            "gross_sales",
            "net_sales",
            "estimated_margin",
            "currency",
        ]
    ].copy()

    records = clean_records(order_items)

    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO order_items (
                order_line_id,
                order_id,
                sku,
                quantity,
                unit_price,
                discount_percent,
                gross_sales,
                net_sales,
                estimated_margin,
                currency
            )
            VALUES (
                %(order_line_id)s,
                %(order_id)s,
                %(sku)s,
                %(quantity)s,
                %(unit_price)s,
                %(discount_percent)s,
                %(gross_sales)s,
                %(net_sales)s,
                %(estimated_margin)s,
                %(currency)s
            );
            """,
            records,
        )

    return len(records)


def insert_market_benchmarks(
    conn: Connection,
    weekly_reports: pd.DataFrame,
    monthly_reports: pd.DataFrame,
) -> int:
    weekly = weekly_reports.copy()
    weekly["period_type"] = "week"
    weekly["period_start"] = pd.to_datetime(weekly["week_start"]).dt.date
    weekly["period_label"] = weekly["period_start"].astype(str)

    monthly = monthly_reports.copy()
    monthly["period_type"] = "month"
    monthly["period_start"] = monthly["month"].apply(parse_month_start)
    monthly["period_label"] = monthly["period_start"].apply(lambda value: value.strftime("%Y-%m"))

    benchmarks = pd.concat([weekly, monthly], ignore_index=True)

    benchmarks = benchmarks[
        [
            "supplier_code",
            "period_type",
            "period_start",
            "period_label",
            "supplier_revenue",
            "supplier_units",
            "supplier_orders",
            "comparable_market_revenue",
            "comparable_market_units",
            "comparable_market_orders",
            "estimated_market_share_pct",
        ]
    ]

    records = clean_records(benchmarks)

    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO market_benchmarks (
                supplier_code,
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
            )
            VALUES (
                %(supplier_code)s,
                %(period_type)s,
                %(period_start)s,
                %(period_label)s,
                %(supplier_revenue)s,
                %(supplier_units)s,
                %(supplier_orders)s,
                %(comparable_market_revenue)s,
                %(comparable_market_units)s,
                %(comparable_market_orders)s,
                %(estimated_market_share_pct)s
            );
            """,
            records,
        )

    return len(records)


def get_table_counts(conn: Connection) -> dict[str, int]:
    tables = [
        "suppliers",
        "products",
        "stores",
        "orders",
        "order_items",
        "market_benchmarks",
    ]

    counts = {}

    with conn.cursor() as cur:
        for table in tables:
            cur.execute(f"SELECT COUNT(*) FROM {table};")
            counts[table] = cur.fetchone()[0]

    return counts


def import_legacy_exports(data_dir: Path = DEFAULT_DATA_DIR) -> None:
    suppliers = load_excel_sheet(data_dir / "supplier_master_export.xlsx", "Suppliers")
    products = load_excel_sheet(data_dir / "product_master_export.xlsx", "Products")
    stores = load_excel_sheet(data_dir / "store_geography_export.xlsx", "Stores")
    raw_sales = load_excel_sheet(data_dir / "raw_retail_sales_export.xlsx", "Sales_Export")
    weekly_reports = load_excel_sheet(data_dir / "legacy_supplier_reports.xlsx", "Weekly_Reports")
    monthly_reports = load_excel_sheet(data_dir / "legacy_supplier_reports.xlsx", "Monthly_Reports")

    with get_connection() as conn:
        inserted_suppliers = insert_suppliers(conn, suppliers)
        inserted_products = insert_products(conn, products)
        inserted_stores = insert_stores(conn, stores)
        inserted_orders = insert_orders(conn, raw_sales)
        inserted_order_items = insert_order_items(conn, raw_sales)
        inserted_benchmarks = insert_market_benchmarks(conn, weekly_reports, monthly_reports)

        counts = get_table_counts(conn)

    print("Import completed.")
    print(f"- suppliers: {inserted_suppliers}")
    print(f"- products: {inserted_products}")
    print(f"- stores: {inserted_stores}")
    print(f"- orders: {inserted_orders}")
    print(f"- order_items: {inserted_order_items}")
    print(f"- market_benchmarks: {inserted_benchmarks}")
    print()
    print("Table counts:")
    for table, count in counts.items():
        print(f"- {table}: {count}")


def main() -> None:
    import_legacy_exports()


if __name__ == "__main__":
    main()