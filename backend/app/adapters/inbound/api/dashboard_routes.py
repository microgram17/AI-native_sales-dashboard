from __future__ import annotations

from fastapi import APIRouter, Depends

from app.adapters.inbound.api.dependencies import get_dashboard_service, get_user_context
from app.application.services.dashboard_service import DashboardService
from app.domain.dashboard import DashboardResponse
from app.domain.user_context import UserContext

router = APIRouter()


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    user: UserContext = Depends(get_user_context),
    service: DashboardService = Depends(get_dashboard_service),
) -> DashboardResponse:
    return await service.get_dashboard(user)
