from fastapi import APIRouter, Depends

from app.adapters.mcp_sales_client import McpSalesClient
from app.services.dashboard_service import DashboardService
from app.schemas.dashboard import (
    SupplierListResponse,
    SupplierRevenueTrendResponse,
    SupplierSummaryResponse,
    TopProductsResponse,
)

router = APIRouter()


def get_dashboard_service() -> DashboardService:
    return DashboardService(sales_analytics=McpSalesClient())


@router.get("/summary/{supplier_code}")
async def get_dashboard_summary(
    supplier_code: str,
    service: DashboardService = Depends(get_dashboard_service),
) -> SupplierSummaryResponse:
    data = await service.get_supplier_summary(supplier_code)
    return SupplierSummaryResponse.model_validate(data)


@router.get("/trend/{supplier_code}")
async def get_supplier_revenue_trend(
    supplier_code: str,
    period_type: str = "month",
    service: DashboardService = Depends(get_dashboard_service),
) -> SupplierRevenueTrendResponse:
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
) -> TopProductsResponse:
    data = await service.get_top_products(
        supplier_code=supplier_code,
        limit=limit,
        sort_by=sort_by,
    )
    return TopProductsResponse.model_validate(data)


@router.get("/suppliers")
async def list_suppliers(
    service: DashboardService = Depends(get_dashboard_service),
) -> SupplierListResponse:
    data = await service.list_suppliers()
    return SupplierListResponse.model_validate(data)