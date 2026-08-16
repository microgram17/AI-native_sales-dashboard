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
from typing import Any

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


def _load_json(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default
    return default


def _summarize_last_request(value: Any) -> str:
    payload = _load_json(value, {})
    if not isinstance(payload, dict):
        return ""

    calls = payload.get("tool_calls")
    if not isinstance(calls, list) or not calls:
        return ""

    rendered: list[str] = []
    for call in calls:
        if not isinstance(call, dict):
            continue

        tool_name = call.get("tool_name")
        arguments = call.get("arguments")
        status = call.get("status")
        purpose = call.get("purpose")

        if not tool_name:
            continue

        # Period and scope are represented separately by stable semantic
        # context. Keep only the analytical shape/intent here.
        intent_arguments: dict[str, Any] = {}
        if isinstance(arguments, dict):
            intent_arguments = {
                key: value
                for key, value in arguments.items()
                if key not in {"period_start", "period_end", "scope"}
            }

        piece = str(tool_name)
        if intent_arguments:
            piece += f" {json.dumps(intent_arguments, sort_keys=True)}"
        if purpose:
            piece += f" purpose={purpose!r}"
        if status:
            piece += f" outcome={status}"
        rendered.append(piece)

    return "; ".join(rendered)


def _summarize_prior_context(state: dict) -> str:
    """Build semantic follow-up context independently of raw result reuse."""

    parts: list[str] = []

    entities = _load_json(state.get(StateKeys.CTX_ENTITIES_JSON), [])
    if isinstance(entities, list) and entities:
        rendered_entities = [
            f"{entity.get('id') or entity.get('name')} ({entity.get('name')})"
            for entity in entities
            if isinstance(entity, dict) and (entity.get("id") or entity.get("name"))
        ]
        if rendered_entities:
            if len(rendered_entities) > 5:
                shown = ", ".join(rendered_entities[:5])
                parts.append(
                    f"Referenced entities: {shown} (+{len(rendered_entities) - 5} more)"
                )
            else:
                parts.append(
                    f"Referenced entities: {', '.join(rendered_entities)}"
                )

    period = _load_json(state.get(StateKeys.CTX_PERIOD_JSON), None)
    if isinstance(period, dict) and period:
        parts.append(
            f"Previous period: {period.get('start')}..{period.get('end')}"
        )

    scope = _load_json(state.get(StateKeys.CTX_SCOPE_JSON), None)
    if isinstance(scope, dict) and scope:
        active = {key: value for key, value in scope.items() if value}
        if active:
            parts.append(
                f"Previous scope/filters: {json.dumps(active, sort_keys=True)}"
            )

    last_request = _summarize_last_request(
        state.get(StateKeys.CTX_LAST_REQUEST_JSON)
    )
    if last_request:
        parts.append(f"Last analytical request: {last_request}")

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
        self,
        request: AgentQueryRequest,
        context: RequestContext,
    ) -> AgentQueryResponse:
        conversation_id = request.conversation_id or uuid.uuid4().hex

        token = mint_mcp_context_token(
            user_id=context.user_id,
            supplier_id=context.supplier_id,
            roles=context.roles,
            settings=self._settings,
        )

        session = await self._session_service.get_session(
            app_name=self._app_name,
            user_id=context.user_id,
            session_id=conversation_id,
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
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in tools
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
            StateKeys.AVAILABLE_TOOL_NAMES: [tool.name for tool in tools],
            # This flag means reusable raw results exist from the latest turn.
            # Semantic context is summarized independently.
            StateKeys.HAS_PRIOR_RESULTS: bool(
                prior_state.get(StateKeys.CTX_HAS_RESULTS)
            ),
            StateKeys.PRIOR_CONTEXT_SUMMARY: _summarize_prior_context(
                prior_state
            ),
        }

        message = types.Content(
            role="user",
            parts=[types.Part(text=request.message)],
        )
        async for _ in self._runner.run_async(
            user_id=context.user_id,
            session_id=conversation_id,
            new_message=message,
            state_delta=state_delta,
        ):
            pass

        final = await self._session_service.get_session(
            app_name=self._app_name,
            user_id=context.user_id,
            session_id=conversation_id,
        )
        response_state = (
            (final.state or {}).get(StateKeys.RESPONSE)
            if final
            else None
        )
        if response_state:
            return AgentQueryResponse.model_validate(response_state)

        return AgentQueryResponse(
            conversation_id=conversation_id,
            message="No response was produced.",
        )
