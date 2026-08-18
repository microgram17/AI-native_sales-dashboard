"""Shared fakes/fixtures for the ADK agent tests (offline: fake LLM + MCP)."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import jwt
from google.adk.agents.context import Context
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.workflow import node
from google.genai import types

from app.agents.graph import build_workflow
from app.agents.state import StateKeys, TRANSIENT_STATE_RESET
from app.config import get_settings
from app.integrations.mcp.client import (
    McpClientError,
    McpToolDefinition,
    McpToolResult,
)
from app.services.agent_service import AgentService

TOOL_NAMES = ["resolve_product", "sales_summary", "sales_rank", "sales_trend", "product_overview"]
APP_NAME = "test-agent"


def tool_catalog() -> list[McpToolDefinition]:
    return [McpToolDefinition(name=n, description=f"{n} tool", input_schema={}) for n in TOOL_NAMES]


def sales_rank_success(product_id: str = "NORD-HOD-011", channel: str = "online") -> dict[str, Any]:
    return {
        "status": "success",
        "group_by": "product",
        "rank_by": "units",
        "effective_period": {"start": "2026-01-01", "end": "2026-08-12"},
        "effective_scope": {"channels": [channel], "cities": [], "store_ids": [], "categories": [], "product_ids": []},
        "rows": [
            {"rank": 1, "entity": {"type": "product", "id": product_id, "name": "Minimal Logo Hoodie"},
             "metrics": {"units": 40, "net_sales": 1000.0, "orders": 30}}
        ],
    }


def _decode_supplier(token: str | None) -> str | None:
    if not token:
        return None
    claims = jwt.decode(token, options={"verify_signature": False})
    return claims.get("supplier_id")


class FakeMcpClient:
    def __init__(
        self,
        tools: list[McpToolDefinition] | None = None,
        call_results: dict[str, Any] | None = None,
        supplier_data: dict[str, dict] | None = None,
    ) -> None:
        self._tools = tools if tools is not None else tool_catalog()
        self._call_results = call_results or {}
        self._supplier_data = supplier_data
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.tokens: list[str | None] = []

    async def list_tools(self, token: str | None = None) -> list[McpToolDefinition]:
        self.tokens.append(token)
        return self._tools

    async def call_tool(self, name: str, arguments: dict[str, Any], token: str | None = None) -> McpToolResult:
        self.tokens.append(token)
        self.calls.append((name, arguments))
        if self._supplier_data is not None:
            supplier = _decode_supplier(token)
            data = self._supplier_data.get(supplier or "", sales_rank_success())
            return McpToolResult(structured=data, is_error=False)
        outcome = self._call_results.get(name, McpToolResult(structured=sales_rank_success(), is_error=False))
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def rank_result(structured: dict[str, Any] | None = None, is_error: bool = False) -> McpToolResult:
    return McpToolResult(
        structured=structured if structured is not None else sales_rank_success(),
        is_error=is_error,
        error_message="tool error" if is_error else None,
    )


def transport_failure() -> McpClientError:
    return McpClientError("connection refused")


def rank_plan_args() -> dict[str, Any]:
    return {"group_by": "product", "rank_by": "units", "period_start": "2026-01-01",
            "period_end": "2026-08-12", "order": "highest", "limit": 1}


def rank_plan_call() -> dict[str, Any]:
    return {"call_id": "c1", "tool_name": "sales_rank",
            "arguments_json": json.dumps(rank_plan_args()), "purpose": "rank products"}


# ── fake LLM agents as @node stand-ins ──────────────────────────────────────────


def make_router_node(route: str = "new_data", reason: str = "test"):
    @node
    def router(ctx: Context) -> None:
        ctx.state[StateKeys.ROUTE_DECISION] = {"route": route, "reason": reason}

    return router


def make_planner_node(
    tool_calls: list[dict] | None = None,
    *,
    vary: Callable[[int], list[dict]] | None = None,
    capture: dict | None = None,
    product_query: str | None = None,
    requested_grain: str | None = None,
    inherit_period: bool = False,
    inherit_scope: bool = False,
    inherit_entity: bool = False,
    inherit_operation: bool = False,
):
    @node
    def planner(ctx: Context) -> None:
        calls = ctx.state.get("_planner_calls", 0) + 1
        ctx.state["_planner_calls"] = calls
        if capture is not None:
            capture["prior_context_summary"] = ctx.state.get(
                StateKeys.PRIOR_CONTEXT_SUMMARY,
                "",
            )
        ctx.state[StateKeys.TOOL_PLAN] = {
            "tool_calls": vary(calls) if vary else (tool_calls or []),
            "product_query": product_query,
            "requested_grain": requested_grain,
            "inherit_period": inherit_period,
            "inherit_scope": inherit_scope,
            "inherit_entity": inherit_entity,
            "inherit_operation": inherit_operation,
        }

    return planner


def make_visualization_node(specs: list[dict] | None = None):
    @node
    def visualization(ctx: Context) -> None:
        ctx.state[StateKeys.VISUALIZATION_PLAN] = {"visualizations": specs or []}

    return visualization


def make_analytics_node(text: str = "Analysis text."):
    @node
    def analytics(ctx: Context) -> None:
        ctx.state[StateKeys.ANALYSIS] = text

    return analytics


def make_conversation_node(text: str = "Hello! I can help with sales analytics."):
    @node
    def conversation(ctx: Context) -> None:
        ctx.state[StateKeys.ANALYSIS] = text

    return conversation


def _seed_state(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    state = {
        StateKeys.USER_ID: "DEV-USER-001",
        StateKeys.SUPPLIER_ID: "NORDVALE",
        StateKeys.ROLES: ["admin"],
        StateKeys.USER_MESSAGE: "What is our best-selling product this year?",
        StateKeys.UI_LANGUAGE: "en",
        StateKeys.CURRENT_DATE: "2026-08-12",
        StateKeys.CONVERSATION_ID: "conv-1",
        StateKeys.MCP_TOKEN: None,
        StateKeys.TOOL_CATALOG_JSON: "[]",
        StateKeys.AVAILABLE_TOOL_NAMES: list(TOOL_NAMES),
        StateKeys.HAS_PRIOR_RESULTS: False,
        StateKeys.PRIOR_CONTEXT_SUMMARY: "",
        StateKeys.CTX_HAS_RESULTS: False,
        **TRANSIENT_STATE_RESET,
    }
    state.update(overrides or {})
    return state


async def run_workflow(
    *,
    mcp: FakeMcpClient,
    router=None,
    planner=None,
    visualization=None,
    analytics=None,
    conversation=None,
    user_message: str = "What is our best-selling product this year?",
    state_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    workflow = build_workflow(
        mcp=mcp,
        router=router or make_router_node("new_data"),
        planner=planner or make_planner_node([rank_plan_call()]),
        visualization=visualization or make_visualization_node(),
        analytics=analytics or make_analytics_node(),
        conversation=conversation or make_conversation_node(),
    )
    session_service = InMemorySessionService()
    state = _seed_state({StateKeys.USER_MESSAGE: user_message, **(state_overrides or {})})
    await session_service.create_session(app_name=APP_NAME, user_id="u", session_id="conv-1", state=state)
    runner = Runner(app_name=APP_NAME, agent=workflow, session_service=session_service)
    message = types.Content(role="user", parts=[types.Part(text=user_message)])
    async for _ in runner.run_async(user_id="u", session_id="conv-1", new_message=message):
        pass
    session = await session_service.get_session(app_name=APP_NAME, user_id="u", session_id="conv-1")
    return dict(session.state or {})


def build_agent_service(
    mcp: FakeMcpClient,
    *,
    router=None,
    planner=None,
    visualization=None,
    analytics=None,
    conversation=None,
) -> AgentService:
    workflow = build_workflow(
        mcp=mcp,
        router=router or make_router_node("new_data"),
        planner=planner or make_planner_node([rank_plan_call()]),
        visualization=visualization or make_visualization_node(),
        analytics=analytics or make_analytics_node(),
        conversation=conversation or make_conversation_node(),
    )
    session_service = InMemorySessionService()
    runner = Runner(app_name=APP_NAME, agent=workflow, session_service=session_service)
    return AgentService(
        runner=runner,
        session_service=session_service,
        app_name=APP_NAME,
        mcp=mcp,
        settings=get_settings(),
    )
