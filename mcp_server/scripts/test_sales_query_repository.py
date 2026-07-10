"""Manual repository smoke tests for the new composable sales query path.

Run from mcp_server/:

    uv run python -m scripts.test_sales_query_repository

The database must already be migrated and loaded with demo data.
"""

from __future__ import annotations

import asyncio
import json

from app.db.engine import dispose_engine, get_engine
from app.repositories.sales_query_repository import SalesQueryRepository
from app.schemas.sales_query import SalesFilters, SalesOrderBy, SalesQuery
from app.db.windows_asyncio import configure_windows_event_loop

configure_windows_event_loop()

SUPPLIER_ID = "NORDVALE"


async def main() -> None:
    repo = SalesQueryRepository(get_engine())

    print("\nTEST 1 — Sales summary")
    summary = await repo.query_supplier_sales(
        supplier_id=SUPPLIER_ID,
        query=SalesQuery(
            metrics=["net_sales", "units", "orders"],
        ),
    )
    print(json.dumps(summary.model_dump(mode="json"), indent=2, ensure_ascii=False)[:2000])

    print("\nTEST 2 — Best-selling product online")
    best_online = await repo.query_supplier_sales(
        supplier_id=SUPPLIER_ID,
        query=SalesQuery(
            metrics=["units", "net_sales", "orders"],
            dimensions=["product"],
            filters=SalesFilters(channels=["online"]),
            order_by=SalesOrderBy(field="units", direction="desc"),
            limit=1,
        ),
    )
    best_payload = best_online.model_dump(mode="json")
    print(json.dumps(best_payload, indent=2, ensure_ascii=False)[:2000])

    if not best_online.rows:
        raise RuntimeError("No best online product returned")

    product_id = best_online.rows[0]["product_id"]
    product_name = best_online.rows[0]["product_name"]

    print(f"\nSelected product: {product_id} — {product_name}")

    print("\nTEST 3 — Monthly units for that product online in 2026")
    trend = await repo.query_supplier_sales(
        supplier_id=SUPPLIER_ID,
        query=SalesQuery(
            metrics=["units"],
            dimensions=["period"],
            grain="month",
            filters=SalesFilters(
                date_from="2026-01-01",
                date_to="2026-06-30",
                product_ids=[product_id],
                channels=["online"],
            ),
            order_by=SalesOrderBy(field="period", direction="asc"),
        ),
    )
    print(json.dumps(trend.model_dump(mode="json"), indent=2, ensure_ascii=False)[:3000])

    print("\nTEST 4 — Cities by hoodie units")
    cities = await repo.query_supplier_sales(
        supplier_id=SUPPLIER_ID,
        query=SalesQuery(
            metrics=["units"],
            dimensions=["city"],
            filters=SalesFilters(categories=["Hoodies"]),
            order_by=SalesOrderBy(field="units", direction="desc"),
            limit=10,
        ),
    )
    print(json.dumps(cities.model_dump(mode="json"), indent=2, ensure_ascii=False)[:2000])

    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
