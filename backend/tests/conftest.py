"""Shared offline fakes for the simplified semantic-agent tests."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import json
import jwt
from google.adk.agents.context import Context
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.workflow import node
from google.genai import types

from app.agents.graph import build_workflow
from app.agents.state import StateKeys, TRANSIENT_STATE_RESET
from app.config import get_settings
from app.integrations.mcp.capabilities import discover_capabilities
from app.integrations.mcp.client import McpToolDefinition, McpToolResult
from app.services.agent_service import AgentService


TOOL_NAMES = [
    "resolve_product",
    "sales_summary",
    "sales_rank",
    "sales_trend",
    "product_overview",
]
APP_NAME = "test-agent"


def tool_catalog() -> list[McpToolDefinition]:
    schemas = {
        "resolve_product": {
            "properties": {"product": {"type": "string"}},
        },
        "sales_summary": {
            "properties": {
                "period_start": {},
                "period_end": {},
                "scope": {},
            },
        },
        "sales_rank": {
            "properties": {
                "group_by": {},
                "rank_by": {},
                "period_start": {},
                "period_end": {},
                "scope": {},
                "limit": {},
                "order": {},
            },
        },
        "sales_trend": {
            "properties": {
                "grain": {},
                "period_start": {},
                "period_end": {},
                "scope": {},
                "split_by": {},
                "series_limit": {},
            },
        },
        "product_overview": {
            "properties": {
                "product": {},
                "period_start": {},
                "period_end": {},
                "scope": {},
            },
        },
    }
    return [
        McpToolDefinition(
            name=name,
            description=f"{name} tool",
            input_schema=schemas[name],
        )
        for name in TOOL_NAMES
    ]



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

    async def list_tools(
        self,
        token: str | None = None,
    ) -> list[McpToolDefinition]:
        self.tokens.append(token)
        return self._tools

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        token: str | None = None,
    ) -> McpToolResult:
        self.tokens.append(token)
        self.calls.append((name, arguments))

        if self._supplier_data is not None and name != "resolve_product":
            supplier = _decode_supplier(token)
            structured = self._supplier_data.get(
                supplier or "",
                rank_success(),
            )
            return McpToolResult(structured=structured, is_error=False)

        outcome = self._call_results.get(
            name,
            McpToolResult(structured=rank_success(), is_error=False),
        )
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def mcp_result(structured: dict[str, Any]) -> McpToolResult:
    return McpToolResult(structured=structured, is_error=False)


def resolver_success(
    product_id: str = "AURA-JKT-025",
    name: str = "Windbreaker Jacket",
) -> McpToolResult:
    return mcp_result(
        {
            "status": "success",
            "product": {
                "type": "product",
                "id": product_id,
                "name": name,
            },
            "candidates": [],
        }
    )


def summary_success(
    *,
    product_id: str | None = None,
) -> dict[str, Any]:
    return {
        "status": "success",
        "effective_period": {
            "start": "2026-01-01",
            "end": "2026-03-31",
            "label": "2026-01-01 – 2026-03-31",
            "defaulted": False,
        },
        "effective_scope": {
            "channels": [],
            "cities": [],
            "store_ids": [],
            "categories": [],
            "product_ids": [product_id] if product_id else [],
        },
        "warnings": [],
        "current": {
            "units": 144,
            "net_sales": 178841.14,
            "gross_sales": 187519.33,
            "discounts": 8678.19,
            "orders": 127,
            "average_selling_price": 1241.95,
            "discount_rate": 0.0463,
        },
        "previous_period": {
            "start": "2025-10-03",
            "end": "2025-12-31",
            "label": "2025-10-03 – 2025-12-31",
            "defaulted": False,
        },
        "previous": {
            "units": 211,
            "net_sales": 258528.79,
            "gross_sales": 275968.89,
            "discounts": 17440.10,
            "orders": 175,
            "average_selling_price": 1225.25,
            "discount_rate": 0.0632,
        },
        "changes": {},
    }


def rank_success(
    product_id: str = "AURA-JKT-025",
) -> dict[str, Any]:
    return {
        "status": "success",
        "group_by": "product",
        "rank_by": "units",
        "order": "highest",
        "effective_period": {
            "start": "2026-01-01",
            "end": "2026-03-31",
            "label": "2026-01-01 – 2026-03-31",
            "defaulted": False,
        },
        "effective_scope": {
            "channels": [],
            "cities": [],
            "store_ids": [],
            "categories": [],
            "product_ids": [],
        },
        "warnings": [],
        "total_population_rank_metric_value": 1000.0,
        "returned_rows_rank_metric_value": 144.0,
        "comparison_period": {
            "start": "2025-10-03",
            "end": "2025-12-31",
            "label": "2025-10-03 – 2025-12-31",
            "defaulted": False,
        },
        "rows": [
            {
                "rank": 1,
                "entity": {
                    "type": "product",
                    "id": product_id,
                    "name": "Windbreaker Jacket",
                },
                "metrics": {
                    "units": 144,
                    "net_sales": 178841.14,
                    "gross_sales": 187519.33,
                    "discounts": 8678.19,
                    "orders": 127,
                    "average_selling_price": 1241.95,
                    "discount_rate": 0.0463,
                },
                "share_of_rank_metric": 0.144,
                "previous_rank_metric_value": 211.0,
                "rank_metric_absolute_change": -67.0,
                "rank_metric_percent_change": -31.75,
            }
        ],
    }


def trend_success() -> dict[str, Any]:
    return {
        "status": "success",
        "grain": "month",
        "split_by": None,
        "effective_period": {
            "start": "2026-01-01",
            "end": "2026-12-31",
            "label": "2026-01-01 – 2026-12-31",
            "defaulted": False,
        },
        "effective_scope": {
            "channels": [],
            "cities": [],
            "store_ids": [],
            "categories": [],
            "product_ids": [],
        },
        "warnings": [],
        "rows": [
            {
                "period_start": "2026-01-01",
                "period_label": "2026-01",
                "series_entity": None,
                "metrics": {
                    "units": 1114,
                    "net_sales": 577975.25,
                    "gross_sales": 630535.60,
                    "discounts": 52560.35,
                    "orders": 844,
                    "average_selling_price": 518.83,
                    "discount_rate": 0.0834,
                },
            },
            {
                "period_start": "2026-02-01",
                "period_label": "2026-02",
                "series_entity": None,
                "metrics": {
                    "units": 923,
                    "net_sales": 534170.10,
                    "gross_sales": 544169.03,
                    "discounts": 9998.93,
                    "orders": 698,
                    "average_selling_price": 578.73,
                    "discount_rate": 0.0184,
                },
            },
        ],
    }


def product_overview_success() -> dict[str, Any]:
    result = summary_success(product_id="AURA-JKT-025")
    return {
        **result,
        "product": {
            "type": "product",
            "id": "AURA-JKT-025",
            "name": "Windbreaker Jacket",
        },
        "rank_by_units": 3,
        "rank_by_net_sales": 3,
        "share_of_supplier_units": 0.04,
        "share_of_supplier_net_sales": 0.10,
        "trend": trend_success()["rows"],
        "channel_breakdown": [],
        "city_breakdown": [],
    }


def make_interpreter_node(
    interpretation: dict[str, Any] | None = None,
    *,
    decide: Callable[[str, int], dict[str, Any]] | None = None,
):
    @node
    def interpreter(ctx: Context) -> None:
        count = int(ctx.state.get("_interpreter_count", 0)) + 1
        ctx.state["_interpreter_count"] = count
        message = str(ctx.state.get(StateKeys.USER_MESSAGE, "") or "")
        payload = (
            decide(message, count)
            if decide is not None
            else (interpretation or {"mode": "conversation"})
        )
        ctx.state[StateKeys.TURN_INTERPRETATION] = payload

    return interpreter


def make_analytics_node(text: str = "Analytical insight."):
    @node
    def analytics(ctx: Context) -> None:
        ctx.state[StateKeys.ANALYSIS] = text

    return analytics


def make_conversation_node(text: str = "Hello."):
    @node
    def conversation(ctx: Context) -> None:
        ctx.state[StateKeys.ANALYSIS] = text

    return conversation


def _seed_state(
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state = {
        StateKeys.USER_ID: "DEV-USER-001",
        StateKeys.SUPPLIER_ID: "NORDVALE",
        StateKeys.ROLES: ["admin"],
        StateKeys.USER_MESSAGE: "",
        StateKeys.UI_LANGUAGE: "sv",
        StateKeys.CURRENT_DATE: "2026-08-18",
        StateKeys.CONVERSATION_ID: "conv-1",
        StateKeys.MCP_TOKEN: None,
        StateKeys.MCP_CAPABILITIES_JSON: json.dumps(
            discover_capabilities(tool_catalog())
        ),
        StateKeys.CANONICAL_REQUEST_JSON: "null",
        StateKeys.LAST_HAS_RESULTS: False,
        StateKeys.LAST_TOOL_RESULTS: [],
        StateKeys.LAST_BUSINESS_RESULTS_JSON: "[]",
        **TRANSIENT_STATE_RESET,
    }
    state.update(overrides or {})
    return state


async def run_workflow(
    *,
    mcp: FakeMcpClient,
    interpreter=None,
    analytics=None,
    conversation=None,
    user_message: str,
    state_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    workflow = build_workflow(
        mcp=mcp,
        interpreter=interpreter or make_interpreter_node({"mode": "conversation"}),
        analytics=analytics or make_analytics_node(),
        conversation=conversation or make_conversation_node(),
    )

    session_service = InMemorySessionService()
    state = _seed_state(
        {
            StateKeys.USER_MESSAGE: user_message,
            **(state_overrides or {}),
        }
    )
    await session_service.create_session(
        app_name=APP_NAME,
        user_id="u",
        session_id="conv-1",
        state=state,
    )

    runner = Runner(
        app_name=APP_NAME,
        agent=workflow,
        session_service=session_service,
    )
    message = types.Content(
        role="user",
        parts=[types.Part(text=user_message)],
    )
    async for _ in runner.run_async(
        user_id="u",
        session_id="conv-1",
        new_message=message,
    ):
        pass

    session = await session_service.get_session(
        app_name=APP_NAME,
        user_id="u",
        session_id="conv-1",
    )
    return dict(session.state or {})


def build_agent_service(
    mcp: FakeMcpClient,
    *,
    interpreter=None,
    analytics=None,
    conversation=None,
) -> AgentService:
    workflow = build_workflow(
        mcp=mcp,
        interpreter=interpreter or make_interpreter_node(
            {
                "mode": "new_analysis",
                "operation": "ranking",
                "group_by": "product",
                "rank_by": "units",
                "rank_order": "highest",
                "limit": 1,
                "period_start": "2026-01-01",
                "period_end": "2026-03-31",
            }
        ),
        analytics=analytics or make_analytics_node(),
        conversation=conversation or make_conversation_node(),
    )

    session_service = InMemorySessionService()
    runner = Runner(
        app_name=APP_NAME,
        agent=workflow,
        session_service=session_service,
    )

    return AgentService(
        runner=runner,
        session_service=session_service,
        app_name=APP_NAME,
        mcp=mcp,
        settings=get_settings(),
    )
