from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from app.services.dashboard_service import DashboardRequestError, DashboardService


class DashboardRepositoryStub:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def fetch_sales_timeseries(self, **kwargs: Any) -> list[dict[str, Any]]:
        self.calls.append(("sales_timeseries", kwargs))
        return [
            {"period": date(2026, 1, 1), "value": 1200},
            {"period": date(2026, 2, 1), "value": 1500.5},
        ]

    def fetch_performance_timeseries(
        self,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        self.calls.append(("performance_timeseries", kwargs))
        return [
            {
                "period": date(2026, 1, 1),
                "group_id": "STORE-1",
                "group_name": "Stockholm",
                "value": 900,
            }
        ]

    def fetch_product_table(self, **kwargs: Any) -> list[dict[str, Any]]:
        self.calls.append(("product_table", kwargs))
        return [
            {
                "product_id": "P-26",
                "product_name": "Product 26",
                "category": "Test",
                "net_sales": 100,
                "gross_sales": 120,
                "units": 4,
                "orders": 3,
                "discounts": 20,
                "total_count": 72,
            }
        ]


def test_sales_timeseries_maps_repository_rows() -> None:
    repository = DashboardRepositoryStub()
    service = DashboardService(repository)  # type: ignore[arg-type]

    result = service.sales_timeseries(
        supplier_id="NORDVALE",
        date_from=date(2026, 1, 1),
        date_to=date(2026, 2, 28),
        grain="month",
        metric="net_sales",
    )

    assert [row.value for row in result.rows] == [1200.0, 1500.5]
    assert repository.calls[0] == (
        "sales_timeseries",
        {
            "supplier_id": "NORDVALE",
            "date_from": date(2026, 1, 1),
            "date_to": date(2026, 2, 28),
            "grain": "month",
            "metric": "net_sales",
        },
    )


def test_performance_timeseries_preserves_group_identity() -> None:
    repository = DashboardRepositoryStub()
    service = DashboardService(repository)  # type: ignore[arg-type]

    result = service.performance_timeseries(
        supplier_id="NORDVALE",
        date_from=date(2026, 1, 1),
        date_to=date(2026, 3, 31),
        grain="month",
        metric="orders",
        group_by="store",
        group_ids=["STORE-1"],
        limit_groups=3,
    )

    assert result.rows[0].group_id == "STORE-1"
    assert result.rows[0].group_name == "Stockholm"
    assert repository.calls[0][1]["group_ids"] == ["STORE-1"]


def test_timeseries_rejects_an_inverted_period() -> None:
    repository = DashboardRepositoryStub()
    service = DashboardService(repository)  # type: ignore[arg-type]

    with pytest.raises(DashboardRequestError):
        service.sales_timeseries(
            supplier_id="NORDVALE",
            date_from=date(2026, 2, 1),
            date_to=date(2026, 1, 1),
            grain="month",
            metric="net_sales",
        )


def test_product_table_maps_pagination_and_global_rank() -> None:
    repository = DashboardRepositoryStub()
    service = DashboardService(repository)  # type: ignore[arg-type]

    result = service.product_table(
        supplier_id="NORDVALE",
        date_from=date(2026, 1, 1),
        date_to=date(2026, 6, 30),
        sort_by="net_sales",
        sort_direction="asc",
        offset=25,
        limit=25,
    )

    assert result.total == 72
    assert result.rows[0].rank == 26
    assert result.rows[0].product_id == "P-26"
    assert repository.calls[0][1]["offset"] == 25
    assert repository.calls[0][1]["sort_direction"] == "asc"
    assert result.sort_direction == "asc"
