from __future__ import annotations

from fastapi import Depends

from app.adapters.outbound.mcp.supplier_analytics_mcp_adapter import SupplierAnalyticsMcpAdapter
from app.application.services.dashboard_service import DashboardService
from app.auth.demo_user_context import DEMO_USER_CONTEXT
from app.core.config import Settings, get_settings
from app.domain.user_context import UserContext


def get_user_context() -> UserContext:
    """Returns the current user context. Replace body here when adding real auth."""
    return DEMO_USER_CONTEXT


def get_dashboard_service(settings: Settings = Depends(get_settings)) -> DashboardService:
    adapter = SupplierAnalyticsMcpAdapter(mcp_url=settings.mcp_server_url)
    return DashboardService(port=adapter)
