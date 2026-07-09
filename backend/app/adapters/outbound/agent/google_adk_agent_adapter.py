from __future__ import annotations

import os
from typing import Any, Literal

from google.adk import Agent, Runner
from google.adk.models.lite_llm import LiteLlm
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.adapters.outbound.agent.agent_prompt_builder import (
    build_runtime_block,
    build_session_context_block,
)
from app.adapters.outbound.agent.agent_result_utils import (
    annotate_clamped_summary,
    clamp_dates,
    compact_summary,
)
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
    "get_ranked_products": "get_current_supplier_ranked_products",
    "get_ranked_locations": "get_current_supplier_ranked_locations",
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
            date_from, date_to, was_clamped = clamp_dates(date_from, date_to, runtime_context)
            used_filters.update({"date_from": date_from, "date_to": date_to})
            payload = await self._port.get_sales_summary(
                supplier_id=user.supplier_id,
                date_from=date_from,
                date_to=date_to,
            )
            collected.append((_SOURCE_TOOL["get_sales_summary"], payload))
            tools_used.append("get_sales_summary")
            summary = compact_summary(payload)
            annotate_clamped_summary(summary, runtime_context, was_clamped)
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
            date_from, date_to, was_clamped = clamp_dates(date_from, date_to, runtime_context)
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
            summary = compact_summary(payload)
            annotate_clamped_summary(summary, runtime_context, was_clamped)
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
            date_from, date_to, was_clamped = clamp_dates(date_from, date_to, runtime_context)
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
            summary = compact_summary(payload)
            annotate_clamped_summary(summary, runtime_context, was_clamped)
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
            date_from, date_to, was_clamped = clamp_dates(date_from, date_to, runtime_context)
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
            summary = compact_summary(payload)
            annotate_clamped_summary(summary, runtime_context, was_clamped)
            return summary

        async def get_ranked_products(
            date_from: str | None = None,
            date_to: str | None = None,
            metric: Literal["net_sales", "gross_sales", "units", "orders", "discounts"] = "net_sales",
            limit: int = 10,
            city: str | None = None,
            store_id: str | None = None,
            channel: Literal["online", "physical"] | None = None,
            category: str | None = None,
        ) -> dict[str, Any]:
            """Rank products by a retail sell-through metric with optional dimension filters.

            PREFER this tool over get_top_products when the question includes a location or
            category filter, or when the user asks for a single winner.

            When to use:
            - 'what product sells the best in Stockholm?' → city='Stockholm', metric='units', limit=1
            - 'top 8 products by units in Stockholm' → city='Stockholm', metric='units', limit=8
            - 'highest revenue products online' → channel='online', metric='net_sales'
            - 'best-selling hoodies in Q1' → category='Hoodies', metric='units', date range set
            - 'top products by units in December' → metric='units', date range set

            metric selection:
            - metric='units'     → 'sells the best' / 'most popular' / 'most sold' / volume
            - metric='net_sales' → 'highest sales' / 'revenue' / 'top by value' (DEFAULT)
            - metric='orders'    → products in the most orders
            - metric='discounts' → most discounted products

            IMPORTANT: For 'best seller' or 'most popular' without saying 'revenue/value',
            you MUST use metric='units'.

            limit=1 returns a single winner; limit>1 returns a ranked list.

            Note: online stores have city='Online'. Use channel='online' for online-only queries.

            Date parameters: resolve all relative phrases using runtime context before calling.
            supplier_id is injected automatically — do not pass it.
            """
            if metric not in _ALLOWED_METRICS:
                metric = "net_sales"
            if channel not in {None, "online", "physical"}:
                channel = None
            limit = max(1, min(limit, 50))
            date_from, date_to, was_clamped = clamp_dates(date_from, date_to, runtime_context)
            used_filters.update({
                "date_from": date_from, "date_to": date_to,
                "metric": metric, "limit": limit,
                "city": city, "store_id": store_id,
                "channel": channel, "category": category,
            })
            payload = await self._port.get_ranked_products(
                supplier_id=user.supplier_id,
                date_from=date_from,
                date_to=date_to,
                metric=metric,
                limit=limit,
                city=city,
                store_id=store_id,
                channel=channel,
                category=category,
            )
            collected.append((_SOURCE_TOOL["get_ranked_products"], payload))
            tools_used.append("get_ranked_products")
            summary = compact_summary(payload)
            annotate_clamped_summary(summary, runtime_context, was_clamped)
            return summary

        async def get_ranked_locations(
            date_from: str | None = None,
            date_to: str | None = None,
            metric: Literal["net_sales", "gross_sales", "units", "orders", "discounts"] = "net_sales",
            group_by: Literal["store", "city", "channel"] = "store",
            limit: int = 10,
            category: str | None = None,
            product_id: str | None = None,
        ) -> dict[str, Any]:
            """Rank stores, cities, or channels by a retail sell-through metric.

            Use this for location/channel ranking questions:
            - 'which city sells hoodies best?' → group_by='city', category='Hoodies', metric='units'
            - 'which store sells Classic Cotton Tee best?' → group_by='store', product_id if known
            - 'online vs physical sales for socks' → group_by='channel', category='Socks'
            - 'best stores by units sold' → group_by='store', metric='units'
            - 'which city has the highest sales?' → group_by='city', metric='net_sales'

            group_by selection:
            - group_by='store'   → compare individual stores (DEFAULT)
            - group_by='city'    → compare cities (Stockholm, Uppsala, Göteborg, Online)
            - group_by='channel' → compare online vs physical

            metric selection:
            - metric='units'     → sells the best / most popular by location
            - metric='net_sales' → highest retail sales by location (DEFAULT)

            Note: When group_by='city', online stores appear as city='Online'.
            Use group_by='channel' for online vs physical comparison.

            product_id: pass if you know the specific product ID (get it via get_supplier_products first).
            supplier_id is injected automatically — do not pass it.
            """
            if metric not in _ALLOWED_METRICS:
                metric = "net_sales"
            if group_by not in {"store", "city", "channel"}:
                group_by = "store"
            limit = max(1, min(limit, 50))
            date_from, date_to, was_clamped = clamp_dates(date_from, date_to, runtime_context)
            used_filters.update({
                "date_from": date_from, "date_to": date_to,
                "metric": metric, "group_by": group_by, "limit": limit,
                "category": category, "product_id": product_id,
            })
            payload = await self._port.get_ranked_locations(
                supplier_id=user.supplier_id,
                date_from=date_from,
                date_to=date_to,
                metric=metric,
                group_by=group_by,
                limit=limit,
                category=category,
                product_id=product_id,
            )
            collected.append((_SOURCE_TOOL["get_ranked_locations"], payload))
            tools_used.append("get_ranked_locations")
            summary = compact_summary(payload)
            annotate_clamped_summary(summary, runtime_context, was_clamped)
            return summary

        # Build agent per-request: tools capture request-scoped state.
        # Instruction = base constant + per-request runtime context block + optional session context.
        session_block = build_session_context_block(session_state)
        full_instruction = _SYSTEM_INSTRUCTION + "\n\n" + build_runtime_block(runtime_context)
        if session_block:
            full_instruction += "\n\n" + session_block
        agent = Agent(
            name="supplier_sales_agent",
            model=LiteLlm(model=self._agent_model),
            instruction=full_instruction,
            tools=[
                get_sales_summary,
                get_product_timeseries,
                get_top_products,
                get_store_breakdown,
                get_ranked_products,
                get_ranked_locations,
            ],
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
