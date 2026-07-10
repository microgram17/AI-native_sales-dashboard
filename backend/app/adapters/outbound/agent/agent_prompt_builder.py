from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any

from app.domain.agent_runtime_context import AgentRuntimeContext


def build_runtime_block(ctx: AgentRuntimeContext) -> str:
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


def build_session_context_block(state: Mapping[str, Any]) -> str:
    """Build a compact prior filter-context block injected into the agent instruction.

    Reads the follow-up filter context from ADK session.state (written by the tools
    via tool_context.state on prior turns). Returns an empty string when there has
    been no prior tool interaction in this session.

    Note: prior user/assistant message text is intentionally omitted here. ADK
    session.events carries the full turn-by-turn conversation history and makes
    it available to the model automatically. This block only injects structured
    filter state (date ranges, metrics, etc.) that guides follow-up tool routing.
    """
    last_tool_used = state.get("last_tool_used")
    filters = state.get("last_filters") or {}
    if not last_tool_used and not filters:
        return ""

    lines = ["Previous interaction context (use this to answer follow-up questions):"]

    date_from = filters.get("date_from")
    date_to = filters.get("date_to")
    if date_from or date_to:
        lines.append(f"- Previous date range: date_from={date_from}, date_to={date_to}")

    if "sort_by" in filters:
        lines.append(f"- Previous sort_by: {filters['sort_by']}")
    if "metric" in filters:
        lines.append(f"- Previous metric: {filters['metric']}")
    if "grain" in filters:
        lines.append(f"- Previous grain: {filters['grain']}")
    if "limit" in filters:
        lines.append(f"- Previous limit: {filters['limit']}")
    if "group_by" in filters:
        lines.append(f"- Previous group_by: {filters['group_by']}")
    if filters.get("city"):
        lines.append(f"- Previous city filter: {filters['city']}")
    if filters.get("channel"):
        lines.append(f"- Previous channel filter: {filters['channel']}")
    if filters.get("category"):
        lines.append(f"- Previous category filter: {filters['category']}")
    if filters.get("store_id"):
        lines.append(f"- Previous store_id filter: {filters['store_id']}")
    if filters.get("product_id"):
        lines.append(f"- Previous product_id filter: {filters['product_id']}")
    if last_tool_used:
        lines.append(f"- Previous tool called: {last_tool_used}")

    lines += [
        "",
        "Follow-up handling rules:",
        "- Reuse the previous date range (date_from/date_to) for ALL follow-up questions unless the user explicitly specifies a different time period.",
        "- If the user asks about top sellers, best products, or rankings, call get_top_products with the previous date range.",
        "- If the user mentions 'units sold', 'volume', 'quantity', or 'most popular', use sort_by='units' or metric='units' with the previous date range.",
        "- If the user asks about stores, locations, or channels, call get_store_breakdown with the previous date range.",
        "- If the user asks about trends, changes over time, or historical patterns, call get_product_timeseries with the previous date range.",
        "- If the user asks about overall sales summary, call get_sales_summary with the previous date range.",
        "- If the user asks about the best product in a specific city, store, channel, or category, call get_ranked_products with those filters.",
        "- If the user asks which city, store, or channel performs best, call get_ranked_locations.",
        "- Only change the date range if the user explicitly mentions a different period.",
    ]

    return "\n".join(lines)
