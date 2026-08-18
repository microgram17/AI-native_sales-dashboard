
"""Application-facing service for the semantic ADK sales workflow."""

from __future__ import annotations

import json
import uuid
from datetime import date

from google.adk.runners import Runner
from google.adk.sessions import (
    BaseSessionService,
)
from google.genai import types

from app.agents.state import (
    TRANSIENT_STATE_RESET,
    StateKeys,
)
from app.config import Settings
from app.integrations.mcp.capabilities import (
    discover_capabilities,
)
from app.integrations.mcp.client import (
    McpClient,
)
from app.integrations.mcp.context_token import (
    mint_mcp_context_token,
)
from app.schemas.agent import (
    AgentQueryRequest,
    AgentQueryResponse,
)
from app.schemas.request_context import (
    RequestContext,
)


class ConversationSupplierMismatchError(
    Exception
):
    """A conversation created under one supplier was reused under another."""


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
        conversation_id = (
            request.conversation_id
            or uuid.uuid4().hex
        )

        token = mint_mcp_context_token(
            user_id=context.user_id,
            supplier_id=context.supplier_id,
            roles=context.roles,
            settings=self._settings,
        )

        session = (
            await self._session_service.get_session(
                app_name=self._app_name,
                user_id=context.user_id,
                session_id=conversation_id,
            )
        )

        if session is not None:
            bound_supplier = (
                session.state or {}
            ).get(
                StateKeys.SUPPLIER_ID
            )
            if (
                bound_supplier
                and bound_supplier
                != context.supplier_id
            ):
                raise ConversationSupplierMismatchError(
                    "This conversation belongs to a different supplier."
                )
            prior_state = dict(
                session.state or {}
            )
        else:
            initial_state = {
                StateKeys.SUPPLIER_ID:
                    context.supplier_id,
                StateKeys.USER_ID:
                    context.user_id,
                StateKeys.CONVERSATION_ID:
                    conversation_id,
                StateKeys.CANONICAL_REQUEST_JSON:
                    "null",
                StateKeys.LAST_HAS_RESULTS:
                    False,
                StateKeys.LAST_TOOL_RESULTS:
                    [],
                StateKeys.LAST_BUSINESS_RESULTS_JSON:
                    "[]",
            }
            await self._session_service.create_session(
                app_name=self._app_name,
                user_id=context.user_id,
                session_id=conversation_id,
                state=initial_state,
            )
            prior_state = initial_state

        tools = await self._mcp.list_tools(
            token=token
        )
        capabilities = discover_capabilities(
            tools
        )

        state_delta = {
            **TRANSIENT_STATE_RESET,
            StateKeys.SUPPLIER_ID:
                context.supplier_id,
            StateKeys.USER_ID:
                context.user_id,
            StateKeys.ROLES:
                context.roles,
            StateKeys.CONVERSATION_ID:
                conversation_id,
            StateKeys.USER_MESSAGE:
                request.message,
            StateKeys.UI_LANGUAGE:
                request.language,
            StateKeys.CURRENT_DATE:
                date.today().isoformat(),
            StateKeys.MCP_TOKEN:
                token,
            StateKeys.MCP_CAPABILITIES_JSON:
                json.dumps(
                    capabilities,
                    ensure_ascii=False,
                ),
            StateKeys.CANONICAL_REQUEST_JSON:
                prior_state.get(
                    StateKeys.CANONICAL_REQUEST_JSON,
                    "null",
                ),
            StateKeys.LAST_HAS_RESULTS:
                bool(
                    prior_state.get(
                        StateKeys.LAST_HAS_RESULTS,
                        False,
                    )
                ),
            StateKeys.LAST_TOOL_RESULTS:
                prior_state.get(
                    StateKeys.LAST_TOOL_RESULTS,
                    [],
                ),
            StateKeys.LAST_BUSINESS_RESULTS_JSON:
                prior_state.get(
                    StateKeys.LAST_BUSINESS_RESULTS_JSON,
                    "[]",
                ),
        }

        message = types.Content(
            role="user",
            parts=[
                types.Part(
                    text=request.message
                )
            ],
        )

        async for _ in self._runner.run_async(
            user_id=context.user_id,
            session_id=conversation_id,
            new_message=message,
            state_delta=state_delta,
        ):
            pass

        final = (
            await self._session_service.get_session(
                app_name=self._app_name,
                user_id=context.user_id,
                session_id=conversation_id,
            )
        )
        response_state = (
            (final.state or {}).get(
                StateKeys.RESPONSE
            )
            if final
            else None
        )

        if response_state:
            return (
                AgentQueryResponse.model_validate(
                    response_state
                )
            )

        return AgentQueryResponse(
            conversation_id=conversation_id,
            message=(
                "Inget svar kunde genereras."
                if request.language == "sv"
                else "No response was produced."
            ),
        )
