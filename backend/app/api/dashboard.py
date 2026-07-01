from fastapi import APIRouter, Depends, HTTPException

from app.adapters.mcp_sales_client import McpSalesClient
from app.services.dashboard_service import DashboardService
from app.schemas.dashboard import (
    SupplierListResponse,
    SupplierRevenueTrendResponse,
    SupplierSummaryResponse,
    TopProductsResponse,
)
from app.schemas.auth import CurrentUserContext
from app.dependencies.current_user import get_current_user_context

router = APIRouter()


def get_dashboard_service() -> DashboardService:
    return DashboardService(sales_analytics=McpSalesClient())


def _check_supplier_access(supplier_code: str, user_ctx: CurrentUserContext) -> None:
    if supplier_code not in user_ctx.allowed_supplier_codes:
        raise HTTPException(
            status_code=403,
            detail=f"Access denied: supplier {supplier_code!r} not in your allowed list",
        )


@router.get("/summary/{supplier_code}")
async def get_dashboard_summary(
    supplier_code: str,
    service: DashboardService = Depends(get_dashboard_service),
    user_ctx: CurrentUserContext = Depends(get_current_user_context),
) -> SupplierSummaryResponse:
    _check_supplier_access(supplier_code, user_ctx)
    data = await service.get_supplier_summary(supplier_code)
    return SupplierSummaryResponse.model_validate(data)


@router.get("/trend/{supplier_code}")
async def get_supplier_revenue_trend(
    supplier_code: str,
    period_type: str = "month",
    service: DashboardService = Depends(get_dashboard_service),
    user_ctx: CurrentUserContext = Depends(get_current_user_context),
) -> SupplierRevenueTrendResponse:
    _check_supplier_access(supplier_code, user_ctx)
    data = await service.get_supplier_revenue_trend(
        supplier_code=supplier_code,
        period_type=period_type,
    )
    return SupplierRevenueTrendResponse.model_validate(data)


@router.get("/top-products/{supplier_code}")
async def get_top_products(
    supplier_code: str,
    limit: int = 5,
    sort_by: str = "revenue",
    service: DashboardService = Depends(get_dashboard_service),
    user_ctx: CurrentUserContext = Depends(get_current_user_context),
) -> TopProductsResponse:
    _check_supplier_access(supplier_code, user_ctx)
    data = await service.get_top_products(
        supplier_code=supplier_code,
        limit=limit,
        sort_by=sort_by,
    )
    return TopProductsResponse.model_validate(data)


@router.get("/suppliers")
async def list_suppliers(
    service: DashboardService = Depends(get_dashboard_service),
    user_ctx: CurrentUserContext = Depends(get_current_user_context),
) -> SupplierListResponse:
    data = await service.list_suppliers()
    # Filter the returned suppliers to only those the user is allowed to see
    all_suppliers = data.get("suppliers", [])
    allowed = [
        s for s in all_suppliers
        if s.get("supplier_code") in user_ctx.allowed_supplier_codes
    ]
    filtered = {**data, "suppliers": allowed, "count": len(allowed)}
    return SupplierListResponse.model_validate(filtered)