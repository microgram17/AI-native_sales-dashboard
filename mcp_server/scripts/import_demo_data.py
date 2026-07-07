"""Import demo CSV data into PostgreSQL.

Reads normalized CSV files produced by generate_demo_data.py and loads them
into the database in FK-safe order.

Usage:
    uv run python -m scripts.import_demo_data
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from psycopg import Connection

from app.db.connection import get_connection


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CSV_DIR = PROJECT_ROOT / "data" / "demo" / "csv"

EXPECTED_FILES = [
    "suppliers.csv",
    "stores.csv",
    "products.csv",
    "orders.csv",
    "order_items.csv",
]


# ── Helpers ────────────────────────────────────────────────────────────────────

def clean_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Replace NaN with None for safe psycopg parameter binding."""
    return df.where(pd.notnull(df), None).to_dict("records")


def validate_csv_files() -> None:
    missing = [f for f in EXPECTED_FILES if not (CSV_DIR / f).exists()]
    if missing:
        raise FileNotFoundError(
            f"Missing expected CSV files in {CSV_DIR}:\n"
            + "\n".join(f"  - {f}" for f in missing)
            + "\n\nRun: uv run python -m scripts.generate_demo_data"
        )


def load_csv(filename: str) -> pd.DataFrame:
    return pd.read_csv(CSV_DIR / filename)


# ── Truncate ───────────────────────────────────────────────────────────────────

def truncate_all(conn: Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "TRUNCATE order_items, orders, products, stores, suppliers CASCADE;"
        )


# ── Inserters ──────────────────────────────────────────────────────────────────

def insert_suppliers(conn: Connection, df: pd.DataFrame) -> int:
    records = clean_records(df[["supplier_id", "supplier_name", "active"]])
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO suppliers (supplier_id, supplier_name, active)
            VALUES (%(supplier_id)s, %(supplier_name)s, %(active)s);
            """,
            records,
        )
    return len(records)


def insert_stores(conn: Connection, df: pd.DataFrame) -> int:
    df = df.copy()
    df["opened_date"] = pd.to_datetime(df["opened_date"]).dt.date
    records = clean_records(df[["store_id", "store_name", "store_type", "city", "opened_date", "active"]])
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO stores (store_id, store_name, store_type, city, opened_date, active)
            VALUES (%(store_id)s, %(store_name)s, %(store_type)s, %(city)s, %(opened_date)s, %(active)s);
            """,
            records,
        )
    return len(records)


def insert_products(conn: Connection, df: pd.DataFrame) -> int:
    df = df.copy()
    df["launch_date"] = pd.to_datetime(df["launch_date"]).dt.date
    cols = [
        "product_id", "supplier_id", "product_name", "category", "subcategory",
        "base_price_sek", "base_cost_sek", "launch_date", "active",
    ]
    records = clean_records(df[cols])
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO products (
                product_id, supplier_id, product_name, category, subcategory,
                base_price_sek, base_cost_sek, launch_date, active
            )
            VALUES (
                %(product_id)s, %(supplier_id)s, %(product_name)s, %(category)s, %(subcategory)s,
                %(base_price_sek)s, %(base_cost_sek)s, %(launch_date)s, %(active)s
            );
            """,
            records,
        )
    return len(records)


def insert_orders(conn: Connection, df: pd.DataFrame) -> int:
    df = df.copy()
    df["order_date"] = pd.to_datetime(df["order_date"]).dt.date
    cols = ["order_id", "order_date", "store_id", "order_status", "payment_method"]
    records = clean_records(df[cols])
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO orders (order_id, order_date, store_id, order_status, payment_method)
            VALUES (%(order_id)s, %(order_date)s, %(store_id)s, %(order_status)s, %(payment_method)s);
            """,
            records,
        )
    return len(records)


def insert_order_items(conn: Connection, df: pd.DataFrame) -> int:
    cols = [
        "order_item_id", "order_id", "product_id", "quantity",
        "unit_price_sek", "unit_cost_sek", "discount_amount_sek",
    ]
    records = clean_records(df[cols])
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO order_items (
                order_item_id, order_id, product_id, quantity,
                unit_price_sek, unit_cost_sek, discount_amount_sek
            )
            VALUES (
                %(order_item_id)s, %(order_id)s, %(product_id)s, %(quantity)s,
                %(unit_price_sek)s, %(unit_cost_sek)s, %(discount_amount_sek)s
            );
            """,
            records,
        )
    return len(records)


# ── Table counts ───────────────────────────────────────────────────────────────

def get_table_counts(conn: Connection) -> dict[str, int]:
    tables = ["suppliers", "stores", "products", "orders", "order_items"]
    counts: dict[str, int] = {}
    with conn.cursor() as cur:
        for table in tables:
            cur.execute(f"SELECT COUNT(*) FROM {table};")  # noqa: S608 — hardcoded names only
            row = cur.fetchone()
            counts[table] = row[0] if row else 0
    return counts


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    validate_csv_files()

    print("Loading CSVs …")
    df_suppliers   = load_csv("suppliers.csv")
    df_stores      = load_csv("stores.csv")
    df_products    = load_csv("products.csv")
    df_orders      = load_csv("orders.csv")
    df_order_items = load_csv("order_items.csv")

    with get_connection() as conn:
        print("Truncating existing data …")
        truncate_all(conn)

        print("Inserting data …")
        n_suppliers  = insert_suppliers(conn, df_suppliers)
        n_stores     = insert_stores(conn, df_stores)
        n_products   = insert_products(conn, df_products)
        n_orders     = insert_orders(conn, df_orders)
        n_items      = insert_order_items(conn, df_order_items)

        counts = get_table_counts(conn)

    print()
    print("Inserted:")
    print(f"  suppliers:   {n_suppliers}")
    print(f"  stores:      {n_stores}")
    print(f"  products:    {n_products}")
    print(f"  orders:      {n_orders}")
    print(f"  order_items: {n_items}")
    print()
    print("Database table counts:")
    for table, count in counts.items():
        print(f"  {table}: {count}")


if __name__ == "__main__":
    main()
