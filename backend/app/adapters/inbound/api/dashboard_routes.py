from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.adapters.inbound.api.dependencies import get_dashboard_service, get_user_context
from app.application.services.dashboard_service import DashboardService
from app.domain.dashboard import (
    DashboardResponse,
    ProductsResponse,
    ProductTimeseriesResponse,
    SummaryResponse,
    TopProductsResponse,
)
from app.domain.user_context import UserContext

router = APIRouter()


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    user: UserContext = Depends(get_user_context),
    service: DashboardService = Depends(get_dashboard_service),
) -> DashboardResponse:
    return await service.get_dashboard(user)


@router.get("/dashboard/summary", response_model=SummaryResponse)
async def get_summary(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    user: UserContext = Depends(get_user_context),
    service: DashboardService = Depends(get_dashboard_service),
) -> SummaryResponse:
    return await service.get_summary(
        user=user,
        date_from=date_from.isoformat() if date_from else None,
        date_to=date_to.isoformat() if date_to else None,
    )


@router.get("/dashboard/product-timeseries", response_model=ProductTimeseriesResponse)
async def get_product_timeseries(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    grain: Literal["week", "month"] = Query("month"),
    metric: Literal["net_sales", "gross_sales", "units", "discounts", "orders"] = Query("net_sales"),
    product_ids: str | None = Query(None, description="Comma-separated product IDs"),
    limit_products: int = Query(5, ge=1, le=20),
    user: UserContext = Depends(get_user_context),
    service: DashboardService = Depends(get_dashboard_service),
) -> ProductTimeseriesResponse:
    parsed_ids: list[str] | None = None
    if product_ids:
        parsed_ids = [s.strip() for s in product_ids.split(",") if s.strip()] or None

    return await service.get_product_timeseries_widget(
        user=user,
        date_from=date_from.isoformat() if date_from else None,
        date_to=date_to.isoformat() if date_to else None,
        grain=grain,
        metric=metric,
        product_ids=parsed_ids,
        limit_products=limit_products,
    )


@router.get("/dashboard/top-products", response_model=TopProductsResponse)
async def get_top_products(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    sort_by: Literal["net_sales", "gross_sales", "units", "discounts", "orders"] = Query("net_sales"),
    limit: int = Query(10, ge=1, le=50),
    user: UserContext = Depends(get_user_context),
    service: DashboardService = Depends(get_dashboard_service),
) -> TopProductsResponse:
    return await service.get_top_products_widget(
        user=user,
        date_from=date_from.isoformat() if date_from else None,
        date_to=date_to.isoformat() if date_to else None,
        sort_by=sort_by,
        limit=limit,
    )


@router.get("/dashboard/products", response_model=ProductsResponse)
async def get_products(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    user: UserContext = Depends(get_user_context),
    service: DashboardService = Depends(get_dashboard_service),
) -> ProductsResponse:
    return await service.get_supplier_products_widget(
        user=user,
        date_from=date_from.isoformat() if date_from else None,
        date_to=date_to.isoformat() if date_to else None,
    )
