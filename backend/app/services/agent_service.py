"""Application-facing agent service backed by the ADK Runner + Workflow.

Owns per-request trusted context: mints the short-lived MCP context token,
reuses or creates the ADK session (bound to its supplier), resets transient
per-turn state while preserving persistent analytical context, and runs the
workflow.
"""

from __future__ import annotations

import json
import uuid
from datetime import date

from google.adk.runners import Runner
from google.adk.sessions import BaseSessionService
from google.genai import types

from app.agents.state import TRANSIENT_STATE_RESET, StateKeys
from app.config import Settings
from app.integrations.mcp.client import McpClient
from app.integrations.mcp.context_token import mint_mcp_context_token
from app.schemas.agent import AgentQueryRequest, AgentQueryResponse
from app.schemas.request_context import RequestContext


class ConversationSupplierMismatchError(Exception):
    """A conversation created under one supplier was reused under another."""


def _summarize_prior_context(state: dict) -> str:
    if not state.get(StateKeys.CTX_HAS_RESULTS):
        return ""
    parts: list[str] = []
    entities = json.loads(state.get(StateKeys.CTX_ENTITIES_JSON) or "[]")
    if entities:
        rendered = ", ".join(
            f"{e.get('id') or e.get('name')} ({e.get('name')})"
            for e in entities
            if isinstance(e, dict)
        )
        parts.append(f"Referenced entities: {rendered}")
    period = json.loads(state.get(StateKeys.CTX_PERIOD_JSON) or "null")
    if period:
        parts.append(
            f"Previous period: {period.get('start')}..{period.get('end')}"
        )
    scope = json.loads(state.get(StateKeys.CTX_SCOPE_JSON) or "null")
    if scope:
        active = {k: v for k, v in scope.items() if v}
        if active:
            parts.append(f"Previous scope/filters: {json.dumps(active)}")
    return " | ".join(parts)


class AgentService:
    def __init__(
        self,
        *,
        runner: Runner,
        session_service: BaseSessionService,
        app_name: str,
        mcp: McpClient,
        settings: Settings,
    ) -> None:
        self._runner = runner
        self._session_service = session_service
        self._app_name = app_name
        self._mcp = mcp
        self._settings = settings

    async def handle_query(
        self, request: AgentQueryRequest, context: RequestContext
    ) -> AgentQueryResponse:
        conversation_id = request.conversation_id or uuid.uuid4().hex

        token = mint_mcp_context_token(
            user_id=context.user_id,
            supplier_id=context.supplier_id,
            roles=context.roles,
            settings=self._settings,
        )

        session = await self._session_service.get_session(
            app_name=self._app_name, user_id=context.user_id, session_id=conversation_id
        )
        if session is not None:
            bound_supplier = (session.state or {}).get(StateKeys.SUPPLIER_ID)
            if bound_supplier and bound_supplier != context.supplier_id:
                raise ConversationSupplierMismatchError(
                    "This conversation belongs to a different supplier."
                )
            prior_state = dict(session.state or {})
        else:
            await self._session_service.create_session(
                app_name=self._app_name,
                user_id=context.user_id,
                session_id=conversation_id,
                state={
                    StateKeys.SUPPLIER_ID: context.supplier_id,
                    StateKeys.USER_ID: context.user_id,
                    StateKeys.CONVERSATION_ID: conversation_id,
                    StateKeys.CTX_HAS_RESULTS: False,
                },
            )
            prior_state = {}

        tools = await self._mcp.list_tools(token=token)
        catalog = [
            {"name": t.name, "description": t.description, "input_schema": t.input_schema}
            for t in tools
        ]

        state_delta = {
            **TRANSIENT_STATE_RESET,
            StateKeys.SUPPLIER_ID: context.supplier_id,
            StateKeys.USER_ID: context.user_id,
            StateKeys.ROLES: context.roles,
            StateKeys.CONVERSATION_ID: conversation_id,
            StateKeys.USER_MESSAGE: request.message,
            StateKeys.CURRENT_DATE: date.today().isoformat(),
            StateKeys.MCP_TOKEN: token,
            StateKeys.TOOL_CATALOG_JSON: json.dumps(catalog),
            StateKeys.AVAILABLE_TOOL_NAMES: [t.name for t in tools],
            StateKeys.HAS_PRIOR_RESULTS: bool(prior_state.get(StateKeys.CTX_HAS_RESULTS)),
            StateKeys.PRIOR_CONTEXT_SUMMARY: _summarize_prior_context(prior_state),
        }

        message = types.Content(role="user", parts=[types.Part(text=request.message)])
        async for _ in self._runner.run_async(
            user_id=context.user_id,
            session_id=conversation_id,
            new_message=message,
            state_delta=state_delta,
        ):
            pass

        final = await self._session_service.get_session(
            app_name=self._app_name, user_id=context.user_id, session_id=conversation_id
        )
        response_state = (final.state or {}).get(StateKeys.RESPONSE) if final else None
        if response_state:
            return AgentQueryResponse.model_validate(response_state)

        return AgentQueryResponse(
            conversation_id=conversation_id,
            message="No response was produced.",
        )
