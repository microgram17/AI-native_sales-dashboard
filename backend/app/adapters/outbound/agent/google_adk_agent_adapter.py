from __future__ import annotations

import os
from datetime import date
from typing import Any, Literal

from google.adk import Agent, Runner
from google.adk.models.lite_llm import LiteLlm
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.application.ports.agent_port import AgentPort
from app.application.ports.supplier_analytics_port import SupplierAnalyticsPort
from app.domain.agent_runtime_context import AgentRuntimeContext
from app.domain.chat import ChatResponse
from app.domain.chat_session import ChatSessionState
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


def _clamp_dates(
    date_from: str | None,
    date_to: str | None,
    ctx: AgentRuntimeContext,
) -> tuple[str | None, str | None, bool]:
    """Clamp date_from/date_to to the available data range.

    Returns (clamped_from, clamped_to, was_clamped).
    If either value cannot be parsed as an ISO date, it is returned unchanged
    and was_clamped is False for that value.
    """
    was_clamped = False

    def _parse(s: str | None) -> date | None:
        if s is None:
            return None
        try:
            return date.fromisoformat(s)
        except ValueError:
            return None

    from_date = _parse(date_from)
    to_date = _parse(date_to)

    if from_date is not None:
        clamped = max(ctx.available_data_from, min(from_date, ctx.available_data_to))
        if clamped != from_date:
            from_date = clamped
            was_clamped = True

    if to_date is not None:
        clamped = max(ctx.available_data_from, min(to_date, ctx.available_data_to))
        if clamped != to_date:
            to_date = clamped
            was_clamped = True

    return (
        from_date.isoformat() if from_date is not None else date_from,
        to_date.isoformat() if to_date is not None else date_to,
        was_clamped,
    )


def _build_runtime_block(ctx: AgentRuntimeContext) -> str:
    """Build the per-request runtime context block appended to the agent instruction."""
    cur = ctx.current_date
    y = cur.year
    data_from = ctx.available_data_from
    data_to = ctx.available_data_to

    this_year_to = min(cur, data_to)

    # December: if Dec of current year starts after available_data_to, fall back to prior year.
    dec_start_cur = date(y, 12, 1)
    if dec_start_cur > data_to:
        dec_from = date(y - 1, 12, 1)
        dec_to = date(y - 1, 12, 31)
        dec_entry = (
            f"- 'December' (no year) → date_from={dec_from.isoformat()}, date_to={dec_to.isoformat()}"
            f" (Dec {y} is not yet in available data; using Dec {y - 1})"
        )
    else:
        dec_from = dec_start_cur
        dec_to = min(date(y, 12, 31), data_to)
        dec_entry = f"- 'December' (no year) → date_from={dec_from.isoformat()}, date_to={dec_to.isoformat()}"

    lines = [
        "Runtime context — resolve ALL date references using these values BEFORE calling any tool:",
        f"- Current analysis date: {cur.isoformat()}",
        f"- Available sales data: {data_from.isoformat()} through {data_to.isoformat()}",
        f"- 'this year' → date_from={date(y, 1, 1).isoformat()}, date_to={this_year_to.isoformat()}",
        f"- 'this month' → date_from={date(y, cur.month, 1).isoformat()}, date_to={min(cur, data_to).isoformat()}",
        f"- 'last year' → date_from={date(y - 1, 1, 1).isoformat()}, date_to={date(y - 1, 12, 31).isoformat()}",
        f"- 'Q1' / 'first quarter' (no year) → date_from={date(y, 1, 1).isoformat()}, date_to={date(y, 3, 31).isoformat()}",
        f"- 'Q2' / 'second quarter' (no year) → date_from={date(y, 4, 1).isoformat()}, date_to={date(y, 6, 30).isoformat()}",
        f"- 'Q3' / 'third quarter' (no year) → date_from={date(y, 7, 1).isoformat()}, date_to={date(y, 9, 30).isoformat()}",
        f"- 'Q4' / 'fourth quarter' (no year) → date_from={date(y, 10, 1).isoformat()}, date_to={date(y, 12, 31).isoformat()}",
        dec_entry,
        f"- For other month names without a year: if that month in {y} has not yet occurred or "
        f"exceeds {data_to.isoformat()}, use the same month in {y - 1} instead.",
        f"- Data beyond {data_to.isoformat()}: explain this limitation to the user; do not fabricate results.",
        f"- Data before {data_from.isoformat()}: explain that data starts at {data_from.isoformat()}.",
        "- Always pass resolved ISO dates (YYYY-MM-DD) as date_from and date_to to tools."
        " Never pass unresolved relative phrases.",
    ]
    return "\n".join(lines)


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


def _build_session_context_block(session_state: ChatSessionState) -> str:
    """Build a compact prior-context block injected into the agent instruction.

    Returns an empty string on the first message in a session (no prior context).
    """
    if session_state.last_user_message is None:
        return ""

    lines = ["Previous interaction context (use this to answer follow-up questions):"]

    filters = session_state.last_filters
    date_from = filters.get("date_from")
    date_to = filters.get("date_to")
    if date_from or date_to:
        lines.append(f"- Previous date range: date_from={date_from}, date_to={date_to}")

    if "sort_by" in filters:
        lines.append(f"- Previous sort_by: {filters['sort_by']}")
    elif "metric" in filters:
        lines.append(f"- Previous metric: {filters['metric']}")

    if "grain" in filters:
        lines.append(f"- Previous grain: {filters['grain']}")

    if session_state.last_tool_used:
        lines.append(f"- Previous tool called: {session_state.last_tool_used}")

    lines.append(f"- Previous user message: \"{session_state.last_user_message}\"")

    if session_state.last_assistant_message:
        preview = session_state.last_assistant_message[:200]
        lines.append(f"- Previous assistant response (truncated): \"{preview}\"")

    lines += [
        "",
        "Follow-up handling rules:",
        "- Reuse the previous date range (date_from/date_to) for ALL follow-up questions unless the user explicitly specifies a different time period.",
        "- If the user asks about top sellers, best products, or rankings, call get_top_products with the previous date range.",
        "- If the user mentions 'units sold', 'volume', 'quantity', or 'most popular', use sort_by='units' or metric='units' with the previous date range.",
        "- If the user asks about stores, locations, or channels, call get_store_breakdown with the previous date range.",
        "- If the user asks about trends, changes over time, or historical patterns, call get_product_timeseries with the previous date range.",
        "- If the user asks about overall sales summary, call get_sales_summary with the previous date range.",
        "- Only change the date range if the user explicitly mentions a different period.",
    ]

    return "\n".join(lines)


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

    async def run(self, *, user: UserContext, message: str, runtime_context: AgentRuntimeContext, session_state: ChatSessionState) -> ChatResponse:
        # Per-request state — isolated to this coroutine, no shared mutable state.
        collected: list[tuple[str, ToolResultPayload]] = []
        tools_used: list[str] = []
        used_filters: dict[str, Any] = {}

        # Tool closures capture user + collected — supplier_id is never an LLM parameter.

        async def get_sales_summary(
            date_from: str | None = None,
            date_to: str | None = None,
        ) -> dict[str, Any]:
            """Get a high-level retail sell-through sales summary: net sales, gross sales, units, and orders.

            Use this tool for overall/aggregate sales performance questions.
            Do NOT use this for product rankings (use get_top_products) or time trends (use get_product_timeseries).

            Date parameters:
            - date_from, date_to: ISO dates (YYYY-MM-DD). Resolve all relative phrases
              (e.g. 'this year', 'last month') using the runtime context in the instruction
              BEFORE calling this tool. Never omit when the user specified a time period.
            """
            date_from, date_to, was_clamped = _clamp_dates(date_from, date_to, runtime_context)
            used_filters.update({"date_from": date_from, "date_to": date_to})
            payload = await self._port.get_sales_summary(
                supplier_id=user.supplier_id,
                date_from=date_from,
                date_to=date_to,
            )
            collected.append((_SOURCE_TOOL["get_sales_summary"], payload))
            tools_used.append("get_sales_summary")
            summary = _compact_summary(payload)
            if was_clamped:
                summary["data_range_note"] = (
                    f"Dates were clamped to the available data range "
                    f"({runtime_context.available_data_from} – {runtime_context.available_data_to}). "
                    "Mention this limitation in your response."
                )
            return summary

        _ALLOWED_METRICS: frozenset[str] = frozenset({"net_sales", "gross_sales", "units", "orders", "discounts"})

        async def get_product_timeseries(
            date_from: str | None = None,
            date_to: str | None = None,
            metric: Literal["net_sales", "gross_sales", "units", "orders", "discounts"] = "net_sales",
            grain: Literal["week", "month"] = "month",
            limit: int = 5,
        ) -> dict[str, Any]:
            """Get retail sell-through trends for top products over time (line chart).

            Use this tool when the user asks about trends, changes over time, or historical data.

            metric selection:
            - metric="units"     → units sold over time, number of items sold over time, volume trend
            - metric="net_sales" → retail net sales over time, revenue trend, sales over time (DEFAULT)
            - metric="gross_sales" → only when user explicitly asks for gross sales over time
            - metric="orders"    → number of orders over time
            - metric="discounts" → discount amounts over time

            grain selection:
            - grain="month" → monthly trend (DEFAULT; use unless user asks for weekly detail)
            - grain="week"  → weekly trend

            Date parameters:
            - date_from, date_to: ISO dates (YYYY-MM-DD). Resolve all relative phrases
              (e.g. 'this year', 'last month') using the runtime context in the instruction
              BEFORE calling this tool. Never omit when the user specified a time period.
            """
            if metric not in _ALLOWED_METRICS:
                metric = "net_sales"
            if grain not in {"week", "month"}:
                grain = "month"
            limit = max(1, min(limit, 10))
            date_from, date_to, was_clamped = _clamp_dates(date_from, date_to, runtime_context)
            used_filters.update({"date_from": date_from, "date_to": date_to, "metric": metric, "grain": grain, "limit": limit})
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
            summary = _compact_summary(payload)
            if was_clamped:
                summary["data_range_note"] = (
                    f"Dates were clamped to the available data range "
                    f"({runtime_context.available_data_from} – {runtime_context.available_data_to}). "
                    "Mention this limitation in your response."
                )
            return summary

        async def get_top_products(
            date_from: str | None = None,
            date_to: str | None = None,
            sort_by: Literal["net_sales", "gross_sales", "units", "orders", "discounts"] = "net_sales",
            limit: int = 10,
        ) -> dict[str, Any]:
            """Get top performing products ranked by a retail sell-through metric (product ranking/leaderboard).

            Use this tool for product rankings, leaderboards, and best-seller lists.

            sort_by selection — choose based on what the user asks for:
            - sort_by="units"     → units sold, most popular products, best-selling by volume,
                                    quantity sold, number of items sold, how many were sold
            - sort_by="net_sales" → retail net sales, revenue, top products by value, sales (DEFAULT)
            - sort_by="gross_sales" → only when user explicitly asks for gross sales ranking
            - sort_by="orders"    → products appearing in the most orders, most ordered products
            - sort_by="discounts" → products with the most discounts applied

            IMPORTANT: If the user mentions 'units', 'popular', 'volume', 'quantity', or 'items sold',
            you MUST use sort_by="units".

            Date parameters:
            - date_from, date_to: ISO dates (YYYY-MM-DD). Resolve all relative phrases
              (e.g. 'this year', 'last month') using the runtime context in the instruction
              BEFORE calling this tool. Never omit when the user specified a time period.
            """
            if sort_by not in {"net_sales", "gross_sales", "units", "orders", "discounts"}:
                sort_by = "net_sales"
            limit = max(1, min(limit, 20))
            date_from, date_to, was_clamped = _clamp_dates(date_from, date_to, runtime_context)
            used_filters.update({"date_from": date_from, "date_to": date_to, "sort_by": sort_by, "limit": limit})
            payload = await self._port.get_top_products(
                supplier_id=user.supplier_id,
                date_from=date_from,
                date_to=date_to,
                sort_by=sort_by,
                limit=limit,
            )
            collected.append((_SOURCE_TOOL["get_top_products"], payload))
            tools_used.append("get_top_products")
            summary = _compact_summary(payload)
            if was_clamped:
                summary["data_range_note"] = (
                    f"Dates were clamped to the available data range "
                    f"({runtime_context.available_data_from} – {runtime_context.available_data_to}). "
                    "Mention this limitation in your response."
                )
            return summary

        async def get_store_breakdown(
            date_from: str | None = None,
            date_to: str | None = None,
            metric: Literal["net_sales", "gross_sales", "units", "orders", "discounts"] = "net_sales",
            group_by: Literal["store", "city", "channel"] = "store",
        ) -> dict[str, Any]:
            """Get retail sell-through performance broken down by store, city, or channel.

            Use this tool when the user asks to compare stores, locations, or sales channels.

            group_by selection:
            - group_by="store"   → compare individual stores (DEFAULT)
            - group_by="city"    → compare cities or geographic regions
            - group_by="channel" → compare online vs physical / sales channels

            metric selection:
            - metric="net_sales"   → retail net sales by group (DEFAULT)
            - metric="units"       → units sold by group
            - metric="gross_sales" → only when user explicitly asks for gross sales
            - metric="orders"      → number of orders by group
            - metric="discounts"   → discounts by group

            Date parameters:
            - date_from, date_to: ISO dates (YYYY-MM-DD). Resolve all relative phrases
              (e.g. 'this year', 'last month') using the runtime context in the instruction
              BEFORE calling this tool. Never omit when the user specified a time period.
            """
            if metric not in {"net_sales", "gross_sales", "units", "orders", "discounts"}:
                metric = "net_sales"
            if group_by not in {"store", "city", "channel"}:
                group_by = "store"
            date_from, date_to, was_clamped = _clamp_dates(date_from, date_to, runtime_context)
            used_filters.update({"date_from": date_from, "date_to": date_to, "metric": metric, "group_by": group_by})
            payload = await self._port.get_store_breakdown(
                supplier_id=user.supplier_id,
                date_from=date_from,
                date_to=date_to,
                metric=metric,
                group_by=group_by,
            )
            collected.append((_SOURCE_TOOL["get_store_breakdown"], payload))
            tools_used.append("get_store_breakdown")
            summary = _compact_summary(payload)
            if was_clamped:
                summary["data_range_note"] = (
                    f"Dates were clamped to the available data range "
                    f"({runtime_context.available_data_from} – {runtime_context.available_data_to}). "
                    "Mention this limitation in your response."
                )
            return summary

        # Build agent per-request: tools capture request-scoped state.
        # Instruction = base constant + per-request runtime context block + optional session context.
        session_block = _build_session_context_block(session_state)
        full_instruction = _SYSTEM_INSTRUCTION + "\n\n" + _build_runtime_block(runtime_context)
        if session_block:
            full_instruction += "\n\n" + session_block
        agent = Agent(
            name="supplier_sales_agent",
            model=LiteLlm(model=self._agent_model),
            instruction=full_instruction,
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
            session_id=session_state.session_id,
            assistant_message=response_text,
            artifacts=artifacts,
            tools_used=tools_used,
            used_filters=used_filters,
        )
