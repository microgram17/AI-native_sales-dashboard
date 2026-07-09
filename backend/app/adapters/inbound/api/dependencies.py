from __future__ import annotations

from fastapi import Depends

from app.adapters.outbound.mcp.supplier_analytics_mcp_adapter import SupplierAnalyticsMcpAdapter
from app.application.services.dashboard_service import DashboardService
from app.auth.demo_user_context import DEMO_USER_CONTEXT
from app.core.config import Settings, get_settings
from app.adapters.outbound.agent.google_adk_agent_adapter import GoogleAdkAgentAdapter
from app.application.ports.agent_port import AgentPort
from app.application.services.chat_service import ChatService
from app.domain.user_context import UserContext


def get_user_context() -> UserContext:
    """Returns the current user context. Replace body here when adding real auth."""
    return DEMO_USER_CONTEXT


def get_dashboard_service(settings: Settings = Depends(get_settings)) -> DashboardService:
    adapter = SupplierAnalyticsMcpAdapter(mcp_url=settings.mcp_server_url)
    return DashboardService(port=adapter)


def get_agent_port(settings: Settings = Depends(get_settings)) -> AgentPort:
    mcp_adapter = SupplierAnalyticsMcpAdapter(mcp_url=settings.mcp_server_url)
    return GoogleAdkAgentAdapter(
        port=mcp_adapter,
        agent_model=settings.agent_model,
        openai_api_key=settings.openai_api_key,
        google_api_key=settings.google_api_key,
    )


def get_chat_service(agent: AgentPort = Depends(get_agent_port)) -> ChatService:
    return ChatService(agent=agent)
