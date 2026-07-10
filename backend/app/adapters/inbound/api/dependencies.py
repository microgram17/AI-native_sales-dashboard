from __future__ import annotations

from datetime import date

from fastapi import Depends

from app.adapters.outbound.mcp.supplier_analytics_mcp_adapter import SupplierAnalyticsMcpAdapter
from app.application.services.dashboard_service import DashboardService
from app.auth.demo_user_context import DEMO_USER_CONTEXT
from app.core.config import Settings, get_settings
from app.adapters.outbound.agent.google_adk_agent_adapter import GoogleAdkAgentAdapter
from app.application.ports.agent_port import AgentPort
from app.application.services.chat_service import ChatService
from app.domain.agent_runtime_context import AgentRuntimeContext
from app.domain.user_context import UserContext

# Singleton agent adapter — must not be recreated per request.
# Holds the shared InMemorySessionService that maintains ADK session history and state.
_agent_adapter: GoogleAdkAgentAdapter | None = None


def get_user_context() -> UserContext:
    """Returns the current user context. Replace body here when adding real auth."""
    return DEMO_USER_CONTEXT


def get_agent_runtime_context() -> AgentRuntimeContext:
    """Returns the runtime context used by the agent to resolve relative date phrases.

    Demo values — replace this function body with a real lookup (e.g. MCP
    data-availability query or config-driven values) when data availability
    is dynamic rather than fixed.
    """
    return AgentRuntimeContext(
        current_date=date(2026, 6, 30),
        available_data_from=date(2024, 1, 1),
        available_data_to=date(2026, 6, 30),
    )


def get_dashboard_service(settings: Settings = Depends(get_settings)) -> DashboardService:
    adapter = SupplierAnalyticsMcpAdapter(mcp_url=settings.mcp_server_url)
    return DashboardService(port=adapter)


def get_agent_port(settings: Settings = Depends(get_settings)) -> AgentPort:
    global _agent_adapter
    if _agent_adapter is None:
        mcp_adapter = SupplierAnalyticsMcpAdapter(mcp_url=settings.mcp_server_url)
        _agent_adapter = GoogleAdkAgentAdapter(
            port=mcp_adapter,
            agent_model=settings.agent_model,
            openai_api_key=settings.openai_api_key,
            google_api_key=settings.google_api_key,
        )
    return _agent_adapter


def get_chat_service(
    agent: AgentPort = Depends(get_agent_port),
) -> ChatService:
    return ChatService(agent=agent)
