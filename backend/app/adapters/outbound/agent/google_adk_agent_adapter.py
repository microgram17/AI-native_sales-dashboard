from __future__ import annotations

import os
from typing import Any

from google.adk import Agent, Runner
from google.adk.models.lite_llm import LiteLlm
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.application.ports.agent_port import AgentPort
from app.application.ports.supplier_analytics_port import SupplierAnalyticsPort
from app.domain.chat import ChatResponse
from app.domain.dashboard import DashboardArtifact
from app.domain.tool_result import ToolResultPayload
from app.domain.user_context import UserContext

_APP_NAME = "supplier_sales_dashboard"

# Maps ADK tool function name → MCP-compatible source_tool name used in artifacts.
# Keeps artifact source_tool values consistent with the dashboard convention.
_SOURCE_TOOL = {
    "get_sales_summary": "get_current_supplier_sales_summary",
    "get_product_timeseries": "get_current_supplier_product_timeseries",
    "get_top_products": "get_current_supplier_top_products",
    "get_store_breakdown": "get_current_supplier_store_breakdown",
}

_SYSTEM_INSTRUCTION = (
    "You are a supplier-facing retail sell-through analytics assistant.\n"
    "All sales numbers are retail sell-through metrics for the current supplier's products.\n"
    "Use labels like 'retail net sales' and 'retail gross sales'.\n"
    "Do not mention retailer margin, cost, or profit.\n"
    "If the user asks for sales, product, or store data that matches a supported tool, "
    "call exactly one suitable tool.\n"
    "After calling a data tool, summarize the key insight from the result in 1-3 sentences.\n"
    "If the user asks a general non-data question, answer in text only — do not call any tool.\n"
    "You cannot change the supplier identity; it is set by the server."
)


def _compact_summary(payload: ToolResultPayload) -> dict[str, Any]:
    """Return compact data for the LLM — first 10 rows only, full payload goes to frontend."""
    return {
        "title": payload.title,
        "result_type": payload.result_type,
        "description": payload.description,
        "row_count": len(payload.rows),
        "columns": [col.model_dump() for col in payload.columns],
        "rows_preview": payload.rows[:10],
    }


class GoogleAdkAgentAdapter(AgentPort):
    """Implements AgentPort using Google ADK with LiteLLM for provider-flexible model routing.

    This is the only file in the backend that imports google.adk or google.genai.
    Supports OpenAI, Gemini, and other LiteLLM-compatible providers via AGENT_MODEL.
    """

    def __init__(
        self,
        port: SupplierAnalyticsPort,
        agent_model: str,
        openai_api_key: str | None,
        google_api_key: str | None,
    ) -> None:
        self._port = port
        self._agent_model = agent_model
        # Set API keys in environment once at construction — never logged.
        if openai_api_key:
            os.environ["OPENAI_API_KEY"] = openai_api_key
        if google_api_key:
            os.environ["GOOGLE_API_KEY"] = google_api_key

    async def run(self, user: UserContext, message: str) -> ChatResponse:
        # Per-request state — isolated to this coroutine, no shared mutable state.
        collected: list[tuple[str, ToolResultPayload]] = []
        tools_used: list[str] = []

        # Tool closures capture user + collected — supplier_id is never an LLM parameter.

        async def get_sales_summary(
            date_from: str | None = None,
            date_to: str | None = None,
        ) -> dict[str, Any]:
            """Get retail sell-through sales summary: net sales, gross sales, units, and orders."""
            payload = await self._port.get_sales_summary(
                supplier_id=user.supplier_id,
                date_from=date_from,
                date_to=date_to,
            )
            collected.append((_SOURCE_TOOL["get_sales_summary"], payload))
            tools_used.append("get_sales_summary")
            return _compact_summary(payload)

        async def get_product_timeseries(
            date_from: str | None = None,
            date_to: str | None = None,
            metric: str = "net_sales",
            grain: str = "month",
            limit: int = 5,
        ) -> dict[str, Any]:
            """Get retail sell-through timeseries trends for top products over time."""
            payload = await self._port.get_product_timeseries(
                supplier_id=user.supplier_id,
                date_from=date_from,
                date_to=date_to,
                metric=metric,
                grain=grain,
                limit_products=limit,
            )
            collected.append((_SOURCE_TOOL["get_product_timeseries"], payload))
            tools_used.append("get_product_timeseries")
            return _compact_summary(payload)

        async def get_top_products(
            date_from: str | None = None,
            date_to: str | None = None,
            sort_by: str = "net_sales",
            limit: int = 10,
        ) -> dict[str, Any]:
            """Get top performing products ranked by a retail sell-through metric."""
            payload = await self._port.get_top_products(
                supplier_id=user.supplier_id,
                date_from=date_from,
                date_to=date_to,
                sort_by=sort_by,
                limit=limit,
            )
            collected.append((_SOURCE_TOOL["get_top_products"], payload))
            tools_used.append("get_top_products")
            return _compact_summary(payload)

        async def get_store_breakdown(
            date_from: str | None = None,
            date_to: str | None = None,
            metric: str = "net_sales",
            group_by: str = "store",
        ) -> dict[str, Any]:
            """Get retail sell-through performance broken down by store."""
            payload = await self._port.get_store_breakdown(
                supplier_id=user.supplier_id,
                date_from=date_from,
                date_to=date_to,
                metric=metric,
                group_by=group_by,
            )
            collected.append((_SOURCE_TOOL["get_store_breakdown"], payload))
            tools_used.append("get_store_breakdown")
            return _compact_summary(payload)

        # Build agent per-request: tools capture request-scoped state.
        agent = Agent(
            name="supplier_sales_agent",
            model=LiteLlm(model=self._agent_model),
            instruction=_SYSTEM_INSTRUCTION,
            tools=[get_sales_summary, get_product_timeseries, get_top_products, get_store_breakdown],
        )

        session_service = InMemorySessionService()
        session = await session_service.create_session(
            app_name=_APP_NAME,
            user_id=user.user_id,
        )
        runner = Runner(
            agent=agent,
            app_name=_APP_NAME,
            session_service=session_service,
        )

        new_message = types.Content(
            role="user",
            parts=[types.Part(text=message)],
        )

        response_text = ""
        async for event in runner.run_async(
            user_id=user.user_id,
            session_id=session.id,
            new_message=new_message,
        ):
            if event.is_final_response() and event.content and event.content.parts:
                response_text = event.content.parts[0].text or ""

        artifacts = [
            DashboardArtifact.from_tool_result(source_tool_name, payload)
            for source_tool_name, payload in collected
        ]

        return ChatResponse(
            assistant_message=response_text,
            artifacts=artifacts,
            tools_used=tools_used,
        )
