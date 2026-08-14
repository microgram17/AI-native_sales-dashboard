from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import DashboardServiceDep, RequestContextDep
from app.schemas.dashboard import (
    Grain,
    Metric,
    ProductTimeseriesResponse,
    ProductsResponse,
    StoreBreakdownResponse,
    StoreGroupBy,
    SummaryResponse,
    TopProductsResponse,
)
from app.services.dashboard_service import DashboardRequestError, parse_product_ids

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=SummaryResponse)
def get_summary(
    context: RequestContextDep,
    service: DashboardServiceDep,
    date_from: date | None = None,
    date_to: date | None = None,
) -> SummaryResponse:
    try:
        return service.summary(
            supplier_id=context.supplier_id,
            date_from=date_from,
            date_to=date_to,
        )
    except DashboardRequestError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/product-timeseries", response_model=ProductTimeseriesResponse)
def get_product_timeseries(
    context: RequestContextDep,
    service: DashboardServiceDep,
    date_from: date | None = None,
    date_to: date | None = None,
    grain: Grain = "month",
    metric: Metric = "net_sales",
    product_ids: str | None = None,
    limit_products: Annotated[int, Query(ge=1, le=20)] = 5,
) -> ProductTimeseriesResponse:
    try:
        return service.product_timeseries(
            supplier_id=context.supplier_id,
            date_from=date_from,
            date_to=date_to,
            grain=grain,
            metric=metric,
            product_ids=parse_product_ids(product_ids),
            limit_products=limit_products,
        )
    except DashboardRequestError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/top-products", response_model=TopProductsResponse)
def get_top_products(
    context: RequestContextDep,
    service: DashboardServiceDep,
    date_from: date | None = None,
    date_to: date | None = None,
    sort_by: Metric = "net_sales",
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> TopProductsResponse:
    try:
        return service.top_products(
            supplier_id=context.supplier_id,
            date_from=date_from,
            date_to=date_to,
            sort_by=sort_by,
            limit=limit,
        )
    except DashboardRequestError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/products", response_model=ProductsResponse)
def get_products(
    context: RequestContextDep,
    service: DashboardServiceDep,
    date_from: date | None = None,
    date_to: date | None = None,
) -> ProductsResponse:
    try:
        return service.products(
            supplier_id=context.supplier_id,
            date_from=date_from,
            date_to=date_to,
        )
    except DashboardRequestError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/store-breakdown", response_model=StoreBreakdownResponse)
def get_store_breakdown(
    context: RequestContextDep,
    service: DashboardServiceDep,
    date_from: date | None = None,
    date_to: date | None = None,
    metric: Metric = "net_sales",
    group_by: StoreGroupBy = "store",
) -> StoreBreakdownResponse:
    try:
        return service.store_breakdown(
            supplier_id=context.supplier_id,
            date_from=date_from,
            date_to=date_to,
            metric=metric,
            group_by=group_by,
        )
    except DashboardRequestError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
