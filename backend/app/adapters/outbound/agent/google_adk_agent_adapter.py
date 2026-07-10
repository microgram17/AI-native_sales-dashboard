from __future__ import annotations

import os

from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.adapters.outbound.agent.sales_agent.agent import APP_NAME, create_sales_agent
from app.adapters.outbound.agent.sales_agent.prompts import compose_sales_agent_instruction
from app.adapters.outbound.agent.sales_agent.tool_context import SalesToolContext
from app.adapters.outbound.agent.sales_agent.tools import create_sales_tools
from app.application.ports.agent_port import AgentPort
from app.application.ports.supplier_analytics_port import SupplierAnalyticsPort
from app.domain.agent_runtime_context import AgentRuntimeContext
from app.domain.chat import ChatResponse
from app.domain.chat_session import ChatSessionState
from app.domain.dashboard import DashboardArtifact
from app.domain.user_context import UserContext


class GoogleAdkAgentAdapter(AgentPort):
    """Implements AgentPort using Google ADK with LiteLLM for provider-flexible model routing.

    This is the only place in the backend that imports google.adk Runner/session and google.genai.
    ADK Agent construction lives in sales_agent/agent.py.
    Tool definitions live in sales_agent/tools.py.
    All google.adk and google.genai imports remain inside adapters/outbound/agent/.
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

    async def run(
        self,
        *,
        user: UserContext,
        message: str,
        runtime_context: AgentRuntimeContext,
        session_state: ChatSessionState,
    ) -> ChatResponse:
        ctx = SalesToolContext(
            user=user,
            runtime_context=runtime_context,
            analytics_port=self._port,
        )
        tools = create_sales_tools(ctx)
        instruction = compose_sales_agent_instruction(runtime_context, session_state)
        agent = create_sales_agent(self._agent_model, tools, instruction)

        session_service = InMemorySessionService()
        session = await session_service.create_session(
            app_name=APP_NAME,
            user_id=user.user_id,
        )
        runner = Runner(
            agent=agent,
            app_name=APP_NAME,
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
            for source_tool_name, payload in ctx.collected
        ]

        return ChatResponse(
            session_id=session_state.session_id,
            assistant_message=response_text,
            artifacts=artifacts,
            tools_used=ctx.tools_used,
            used_filters=ctx.used_filters,
        )
