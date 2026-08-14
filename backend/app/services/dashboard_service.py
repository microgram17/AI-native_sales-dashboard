from __future__ import annotations

from datetime import date

from app.repositories.dashboard_repository import DashboardRepository
from app.schemas.dashboard import (
    Grain,
    Metric,
    ProductSelectorItem,
    ProductTimeseriesResponse,
    ProductsResponse,
    StoreBreakdownResponse,
    StoreBreakdownRow,
    StoreGroupBy,
    SummaryResponse,
    TimeseriesRow,
    TopProductsResponse,
    TopProductsRow,
)


class DashboardRequestError(ValueError):
    """Invalid standard-dashboard request."""


class DashboardService:
    def __init__(self, repository: DashboardRepository) -> None:
        self._repository = repository

    def summary(
        self,
        *,
        supplier_id: str,
        date_from: date | None,
        date_to: date | None,
    ) -> SummaryResponse:
        _validate_dates(date_from, date_to)
        row = self._repository.fetch_summary(
            supplier_id=supplier_id,
            date_from=date_from,
            date_to=date_to,
        )
        return SummaryResponse(
            date_from=date_from,
            date_to=date_to,
            gross_sales=_float(row.get("gross_sales")),
            net_sales=_float(row.get("net_sales")),
            discounts=_float(row.get("discounts")),
            units=_int(row.get("units")),
            orders=_int(row.get("orders")),
        )

    def product_timeseries(
        self,
        *,
        supplier_id: str,
        date_from: date | None,
        date_to: date | None,
        grain: Grain,
        metric: Metric,
        product_ids: list[str] | None,
        limit_products: int,
    ) -> ProductTimeseriesResponse:
        _validate_dates(date_from, date_to)
        rows = self._repository.fetch_product_timeseries(
            supplier_id=supplier_id,
            date_from=date_from,
            date_to=date_to,
            grain=grain,
            metric=metric,
            product_ids=product_ids,
            limit_products=limit_products,
        )
        return ProductTimeseriesResponse(
            date_from=date_from,
            date_to=date_to,
            grain=grain,
            metric=metric,
            limit_products=limit_products,
            rows=[
                TimeseriesRow(
                    period=row["period"],
                    product_id=str(row["product_id"]),
                    product_name=str(row["product_name"]),
                    category=str(row["category"]),
                    value=_float(row.get("value")),
                )
                for row in rows
            ],
        )

    def top_products(
        self,
        *,
        supplier_id: str,
        date_from: date | None,
        date_to: date | None,
        sort_by: Metric,
        limit: int,
    ) -> TopProductsResponse:
        _validate_dates(date_from, date_to)
        rows = self._repository.fetch_top_products(
            supplier_id=supplier_id,
            date_from=date_from,
            date_to=date_to,
            sort_by=sort_by,
            limit=limit,
        )
        return TopProductsResponse(
            date_from=date_from,
            date_to=date_to,
            sort_by=sort_by,
            limit=limit,
            rows=[
                TopProductsRow(
                    rank=index,
                    product_id=str(row["product_id"]),
                    product_name=str(row["product_name"]),
                    category=str(row["category"]),
                    net_sales=_float(row.get("net_sales")),
                    gross_sales=_float(row.get("gross_sales")),
                    units=_int(row.get("units")),
                    orders=_int(row.get("orders")),
                    discounts=_float(row.get("discounts")),
                )
                for index, row in enumerate(rows, start=1)
            ],
        )

    def products(
        self,
        *,
        supplier_id: str,
        date_from: date | None,
        date_to: date | None,
    ) -> ProductsResponse:
        _validate_dates(date_from, date_to)
        rows = self._repository.fetch_products(
            supplier_id=supplier_id,
            date_from=date_from,
            date_to=date_to,
        )
        return ProductsResponse(
            date_from=date_from,
            date_to=date_to,
            products=[
                ProductSelectorItem(
                    product_id=str(row["product_id"]),
                    product_name=str(row["product_name"]),
                    category=str(row["category"]),
                    net_sales=_float(row.get("net_sales")),
                    units=_int(row.get("units")),
                )
                for row in rows
            ],
        )

    def store_breakdown(
        self,
        *,
        supplier_id: str,
        date_from: date | None,
        date_to: date | None,
        metric: Metric,
        group_by: StoreGroupBy,
    ) -> StoreBreakdownResponse:
        _validate_dates(date_from, date_to)
        rows = self._repository.fetch_store_breakdown(
            supplier_id=supplier_id,
            date_from=date_from,
            date_to=date_to,
            metric=metric,
            group_by=group_by,
        )
        return StoreBreakdownResponse(
            date_from=date_from,
            date_to=date_to,
            metric=metric,
            group_by=group_by,
            rows=[
                StoreBreakdownRow(
                    group_id=str(row["group_id"]),
                    group_name=str(row["group_name"]),
                    value=_float(row.get("value")),
                )
                for row in rows
            ],
        )


def parse_product_ids(value: str | None) -> list[str] | None:
    if value is None:
        return None
    values = [item.strip() for item in value.split(",") if item.strip()]
    return values or None


def _validate_dates(date_from: date | None, date_to: date | None) -> None:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise DashboardRequestError("date_from cannot be after date_to")


def _float(value: object) -> float:
    return float(value or 0)


def _int(value: object) -> int:
    return int(value or 0)
