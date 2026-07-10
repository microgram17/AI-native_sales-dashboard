from __future__ import annotations

import os
import uuid

from google.adk import Runner
from google.adk.agents.readonly_context import ReadonlyContext
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
        # Shared across all requests so ADK session.events accumulates per-session
        # conversation history. The LLM receives prior turns automatically.
        # TODO(production): replace with DatabaseSessionService or VertexAiSessionService
        # to bound memory growth and survive restarts.
        self._session_service = InMemorySessionService()

    async def run(
        self,
        *,
        user: UserContext,
        message: str,
        runtime_context: AgentRuntimeContext,
        session_id: str | None,
    ) -> ChatResponse:
        resolved_session_id = session_id or str(uuid.uuid4())

        ctx = SalesToolContext(
            user=user,
            runtime_context=runtime_context,
            analytics_port=self._port,
        )
        tools = create_sales_tools(ctx)

        # ADK InstructionProvider: composed lazily per invocation. The follow-up
        # filter context is read from ADK session.state (written by the tools via
        # tool_context.state on prior turns). Returning a computed string bypasses
        # ADK's {key} templating, so curly braces in user messages cannot cause KeyErrors.
        def instruction_provider(ctx_ro: ReadonlyContext) -> str:
            return compose_sales_agent_instruction(runtime_context, ctx_ro.state)

        agent = create_sales_agent(self._agent_model, tools, instruction_provider)

        # Reuse the existing ADK session for this session_id so that session.events
        # accumulates turn-by-turn history and session.state carries follow-up filters.
        adk_session = await self._session_service.get_session(
            app_name=APP_NAME,
            user_id=user.user_id,
            session_id=resolved_session_id,
        )
        if adk_session is None:
            adk_session = await self._session_service.create_session(
                app_name=APP_NAME,
                user_id=user.user_id,
                session_id=resolved_session_id,
            )

        runner = Runner(
            agent=agent,
            app_name=APP_NAME,
            session_service=self._session_service,
        )

        new_message = types.Content(
            role="user",
            parts=[types.Part(text=message)],
        )

        response_text = ""
        async for event in runner.run_async(
            user_id=user.user_id,
            session_id=resolved_session_id,
            new_message=new_message,
        ):
            if event.is_final_response() and event.content and event.content.parts:
                response_text = event.content.parts[0].text or ""

        artifacts = [
            DashboardArtifact.from_tool_result(source_tool_name, payload)
            for source_tool_name, payload in ctx.collected
        ]

        return ChatResponse(
            session_id=resolved_session_id,
            assistant_message=response_text,
            artifacts=artifacts,
            tools_used=ctx.tools_used,
        )
