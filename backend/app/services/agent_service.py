"""Application service for the single native MCP-enabled sales agent."""

from __future__ import annotations

import json
import uuid
from datetime import date
from typing import Any

from google.adk.runners import Runner
from google.adk.sessions import BaseSessionService
from google.genai import types

from app.agents.agent import (
    LAST_ANALYTICS_RESULT,
    MCP_TOKEN,
    TURN_ANALYTICS_CALLED,
    TURN_ANALYTICS_RESULT,
    TURN_TOOL_CALLS,
)
from app.config import Settings
from app.integrations.mcp.context_token import mint_mcp_context_token
from app.schemas.agent import (
    AgentQueryRequest,
    AgentQueryResponse,
    AgentTurnOutput,
    AnalyticsContext,
    DataView,
    DisplaySelection,
    ToolCallInfo,
)
from app.schemas.request_context import RequestContext


SUPPLIER_ID = "supplier_id"
USER_ID = "user_id"
UI_LANGUAGE = "ui_language"
CURRENT_DATE = "current_date"
DASHBOARD_CONTEXT_JSON = "dashboard_context_json"
WIDGET_ANALYSIS_JSON = "widget_analysis_json"
LAST_VIEWS_SUMMARY_JSON = "last_views_summary_json"
AGENT_TURN_OUTPUT = "agent_turn_output"


class ConversationSupplierMismatchError(Exception):
    """A conversation created under one supplier was reused under another."""


class AgentService:
    def __init__(
        self,
        *,
        runner: Runner,
        session_service: BaseSessionService,
        app_name: str,
        settings: Settings,
        toolset: Any | None = None,
    ) -> None:
        self._runner = runner
        self._session_service = session_service
        self._app_name = app_name
        self._settings = settings
        self._toolset = toolset

    async def close(self) -> None:
        if self._toolset is not None:
            await self._toolset.close()

    async def handle_query(
        self,
        request: AgentQueryRequest,
        context: RequestContext,
    ) -> AgentQueryResponse:
        conversation_id = request.conversation_id or uuid.uuid4().hex
        session = await self._session_service.get_session(
            app_name=self._app_name,
            user_id=context.user_id,
            session_id=conversation_id,
        )

        if session is None:
            prior_state: dict[str, Any] = {
                SUPPLIER_ID: context.supplier_id,
                USER_ID: context.user_id,
                LAST_ANALYTICS_RESULT: None,
            }
            await self._session_service.create_session(
                app_name=self._app_name,
                user_id=context.user_id,
                session_id=conversation_id,
                state=prior_state,
            )
        else:
            prior_state = dict(session.state or {})
            if prior_state.get(SUPPLIER_ID) not in {None, context.supplier_id}:
                raise ConversationSupplierMismatchError(
                    "This conversation belongs to a different supplier."
                )

        token = mint_mcp_context_token(
            user_id=context.user_id,
            supplier_id=context.supplier_id,
            roles=context.roles,
            settings=self._settings,
        )
        last_result = prior_state.get(LAST_ANALYTICS_RESULT)
        state_delta = {
            SUPPLIER_ID: context.supplier_id,
            USER_ID: context.user_id,
            UI_LANGUAGE: request.language,
            CURRENT_DATE: date.today().isoformat(),
            DASHBOARD_CONTEXT_JSON: _json_model(request.dashboard_context),
            WIDGET_ANALYSIS_JSON: _json_model(request.widget_analysis),
            LAST_VIEWS_SUMMARY_JSON: _summarize_views(last_result),
            MCP_TOKEN: token,
            TURN_TOOL_CALLS: [],
            TURN_ANALYTICS_CALLED: False,
            TURN_ANALYTICS_RESULT: None,
            AGENT_TURN_OUTPUT: None,
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
        final_state = dict(final.state or {}) if final else {}
        turn = _coerce_turn(final_state.get(AGENT_TURN_OUTPUT), request.language)
        analytics_called = bool(final_state.get(TURN_ANALYTICS_CALLED))
        selected_result = (
            final_state.get(TURN_ANALYTICS_RESULT)
            if analytics_called
            else final_state.get(LAST_ANALYTICS_RESULT)
        )
        analytics_context, views = _coerce_result(selected_result)

        # A conversational turn must not silently redisplay the previous result.
        if not analytics_called and not turn.displays:
            analytics_context, views = None, []

        displays = _validate_displays(
            turn.displays,
            views,
            analytics_context,
        )
        if analytics_called and views and not displays:
            displays = _default_displays(views)

        return AgentQueryResponse(
            conversation_id=conversation_id,
            message=turn.message,
            tool_calls=_coerce_tool_calls(final_state.get(TURN_TOOL_CALLS)),
            data_context=analytics_context if displays else None,
            data_views=views if displays else [],
            displays=displays,
        )


def _json_model(value: Any) -> str:
    return json.dumps(
        value.model_dump(mode="json") if value is not None else None,
        ensure_ascii=False,
    )


def _summarize_views(value: Any) -> str:
    if not isinstance(value, dict):
        return "null"
    context = value.get("context")
    summaries = []
    for raw in value.get("views") or []:
        if not isinstance(raw, dict):
            continue
        summaries.append(
            {
                "id": raw.get("id"),
                "kind": raw.get("kind"),
                "fields": [
                    field.get("key")
                    for field in raw.get("fields") or []
                    if isinstance(field, dict)
                ],
                "default_measures": raw.get("default_measures") or [],
            }
        )
    return json.dumps({"context": context, "views": summaries}, ensure_ascii=False)


def _coerce_turn(value: Any, language: str) -> AgentTurnOutput:
    try:
        if isinstance(value, AgentTurnOutput):
            return value
        if isinstance(value, dict):
            return AgentTurnOutput.model_validate(value)
        if isinstance(value, str) and value.strip():
            return AgentTurnOutput.model_validate_json(value)
    except Exception:
        pass
    return AgentTurnOutput(
        message=(
            "Inget svar kunde genereras."
            if language == "sv"
            else "No response was produced."
        )
    )


def _coerce_result(value: Any) -> tuple[AnalyticsContext | None, list[DataView]]:
    if not isinstance(value, dict) or value.get("status") != "success":
        return None, []
    try:
        context = AnalyticsContext.model_validate(value.get("context"))
        views = [DataView.model_validate(view) for view in value.get("views") or []]
    except Exception:
        return None, []
    return context, views


def _validate_displays(
    requested: list[DisplaySelection],
    views: list[DataView],
    context: AnalyticsContext | None = None,
) -> list[DisplaySelection]:
    by_id = {view.id: view for view in views}
    validated: list[DisplaySelection] = []
    seen: set[str] = set()
    for selection in requested:
        view = by_id.get(selection.view_id)
        if view is None or view.id in seen:
            continue
        ranking_measure = (
            context.rank_by
            if context is not None and context.operation == "ranking"
            else None
        )
        if ranking_measure is not None and view.kind == "metrics":
            # A single ranking result is presented as an overview card grid.
            measures = [
                key for key in view.default_measures if key in view.measure_keys
            ]
        elif ranking_measure in view.measure_keys:
            # A ranking visualizes the value used to produce the ranking.
            # Supporting metrics stay in the rows for the answer and exports,
            # but cannot create mixed-unit bars.
            measures = [ranking_measure]
        else:
            measures = [
                key for key in selection.measure_keys if key in view.measure_keys
            ]
        if not measures:
            measures = [
                key for key in view.default_measures if key in view.measure_keys
            ]
        validated.append(selection.model_copy(update={"measure_keys": measures}))
        seen.add(view.id)
    return validated


def _default_displays(views: list[DataView]) -> list[DisplaySelection]:
    return [
        DisplaySelection(
            view_id=view.id,
            measure_keys=[
                key for key in view.default_measures if key in view.measure_keys
            ],
        )
        for view in views
        if view.default_visible
    ]


def _coerce_tool_calls(value: Any) -> list[ToolCallInfo]:
    if not isinstance(value, list):
        return []
    calls: list[ToolCallInfo] = []
    for item in value:
        try:
            calls.append(ToolCallInfo.model_validate(item))
        except Exception:
            continue
    return calls
