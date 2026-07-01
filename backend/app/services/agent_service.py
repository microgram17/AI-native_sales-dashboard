from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import date
from typing import Any, Literal, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.ports.sales_analytics import SalesAnalyticsPort

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None

log = logging.getLogger(__name__)

_METADATA_KEYS: frozenset[str] = frozenset({
    "supplier_code", "found", "message", "date_from", "date_to",
    "period_type", "sku", "product_name", "sort_by", "dimension",
    "count", "limit",
    "period", "filters", "summary", "comparison", "breakdown_by", "sort",
})

_AGENT_TOOL_ALLOWLIST: frozenset[str] = frozenset({
    "get_sales_overview",
    "break_down_sales",
    "get_product_performance",
    "get_market_benchmark",
    "find_sales_changes",
    "get_available_data_context",
    "list_suppliers",
})

# ── Prompts ───────────────────────────────────────────────────────────────────

_PLANNER_SYSTEM = (
    "You are a supplier analytics planner. "
    "Call the available tool(s) to answer the user's question about one supplier. "
    "supplier_code is authorized by the backend and must always equal the provided value.\n"
    "Tool guidance:\n"
    "- get_sales_overview gives totals, KPI metrics, trend data by day/week/month, and optional previous-period comparison.\n"
    "- break_down_sales groups sales by product, sku, brand, category, sales_channel, country, region, city, store, or customer_segment.\n"
    "- get_product_performance ranks products/SKUs and supports sku, category, and brand filters.\n"
    "- get_market_benchmark gives weekly/monthly market share and comparable market aggregates.\n"
    "- find_sales_changes compares two explicit date ranges and returns the largest movers.\n"
    "- get_available_data_context lists available dates, products, categories, brands, regions, channels, and customer segments.\n"
    "- list_suppliers lists the available suppliers.\n"
    "Resolve relative dates (last month, Q1, this year) into YYYY-MM-DD using today's date. "
    "For period-over-period comparisons, prefer find_sales_changes when the user asks what changed or why, "
    "and get_sales_overview with compare_to_previous_period=true for overall KPI comparisons. "
    "Call 'unsupported' only when no available tool can safely answer."
)

_VIZ_SYSTEM = (
    "Choose the best chart type for the given analytics data. "
    "kpi_cards: scalar summary metrics - data_keys={label: <field>, value: <field>}. "
    "bar_chart: categories or rankings - data_keys={x: <category_field>, series: [{key, name}]}. "
    "line_chart: time series - data_keys={x: <time_field>, series: [{key, name}]}. "
    "table: multi-column rows - data_keys={columns: [<fields>]}. "
    "Use ONLY field names present in the data."
)

_ANSWER_SYSTEM = (
    "You are a strict analytics narrator for a supplier dashboard. "
    "Answer using only the provided tool data. "
    "Do not invent numbers, forecasts, or competitor details. "
    "If data is missing, say so clearly."
)

_UNSUPPORTED_SCHEMA: dict[str, Any] = {
    "name": "unsupported",
    "description": "Use ONLY when no available tool can safely answer the question.",
    "parameters": {
        "type": "object",
        "properties": {
            "reason": {"type": "string", "description": "Why this question cannot be answered"},
        },
        "required": ["reason"],
    },
}

# ── Models ────────────────────────────────────────────────────────────────────


class ToolInfo(BaseModel):
    name: str
    description: str = ""
    input_schema: dict[str, Any] = Field(default_factory=dict)


class ToolCallPlan(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    label: str


class ToolResult(BaseModel):
    tool_name: str
    label: str
    data: dict[str, Any]


class VizSelection(BaseModel):
    type: Literal["bar_chart", "line_chart", "kpi_cards", "table", "none"]
    title: str
    data_keys: dict[str, Any] = Field(default_factory=dict)


class Answer(BaseModel):
    text: str
    visualization_title: str = ""


# ── State ─────────────────────────────────────────────────────────────────────


class AgentState(TypedDict, total=False):
    supplier_code: str
    question: str
    available_tools: list[ToolInfo]
    tool_plans: list[ToolCallPlan]
    tool_results: list[ToolResult]
    visualization: dict[str, Any]
    answer: str
    error: str | None
    retries: int


# ── Pure helpers ──────────────────────────────────────────────────────────────


def _make_tool_schema(tool: ToolInfo) -> dict[str, Any]:
    params = dict(tool.input_schema)
    props = dict(params.get("properties", {}))
    required = list(params.get("required", []))
    if tool.name != "list_suppliers":
        props.pop("supplier_code", None)
        required = [field for field in required if field != "supplier_code"]
    props["label"] = {
        "type": "string",
        "description": "Short identifier for this call (e.g. 'main', 'q1_2024'). Use when calling the same tool multiple times.",
    }
    return {
        "name": tool.name,
        "description": tool.description,
        "parameters": {**params, "properties": props, "required": required},
    }


def _flatten_results(results: list[ToolResult]) -> list[dict[str, Any]]:
    if not results:
        return []
    if len(results) == 1:
        return _flatten_one(results[0].data)

    def _is_scalar(data: dict) -> bool:
        return not any(isinstance(v, list) and v and isinstance(v[0], dict) for v in data.values())

    if all(_is_scalar(r.data) for r in results):
        rows: list[dict[str, Any]] = []
        for r in results:
            row: dict[str, Any] = {"label": r.label}
            for k, v in r.data.items():
                if k not in _METADATA_KEYS and isinstance(v, (int, float)) and v is not False:
                    row[k] = v
            rows.append(row)
        return rows

    out: list[dict[str, Any]] = []
    for r in results:
        for item in _flatten_one(r.data):
            out.append({**item, "__source": r.label})
    return out


def _flatten_one(data: dict[str, Any]) -> list[dict[str, Any]]:
    metric = data.get("metric") if isinstance(data, dict) else None
    for val in data.values():
        if isinstance(val, list) and val and isinstance(val[0], dict):
            if _is_analytics_rows(val):
                return [_flatten_analytics_row(item, metric) for item in val]
            return list(val)
    return [
        {"metric": k.replace("_", " ").title(), "value": v}
        for k, v in data.items()
        if k not in _METADATA_KEYS and isinstance(v, (int, float)) and v is not False
    ]


def _is_analytics_rows(rows: list[Any]) -> bool:
    """True when rows use the generic {dimensions, value} analytics shape."""
    first = rows[0]
    return isinstance(first, dict) and "dimensions" in first and "value" in first


def _flatten_analytics_row(item: dict[str, Any], metric: str | None) -> dict[str, Any]:
    """Flatten one {dimensions, value, extra_metrics} row into flat chart fields.

    The grouping dimensions are lifted to top-level keys and the metric value is
    named after the metric (e.g. 'revenue') so the visualization step can map it.
    """
    row: dict[str, Any] = {}
    dims = item.get("dimensions")
    if isinstance(dims, dict):
        row.update(dims)
    value = item.get("value")
    if value is not None:
        row[metric or "value"] = value
    extra = item.get("extra_metrics")
    if isinstance(extra, dict):
        row.update(extra)
    return row


# ── Service ───────────────────────────────────────────────────────────────────


class AgentService:
    def __init__(self, sales_analytics: SalesAnalyticsPort, max_retries: int = 2) -> None:
        self.analytics = sales_analytics
        self._max_retries = max_retries
        self._llm = self._init_llm()
        self._viz_llm = self._llm.with_structured_output(VizSelection, method="function_calling")
        self._answer_llm = self._llm.with_structured_output(Answer)
        self.graph = self._build_graph()

    async def answer_question(self, supplier_code: str, question: str) -> dict[str, Any]:
        state = await self.graph.ainvoke(
            {"supplier_code": supplier_code, "question": question, "retries": 0}
        )
        tool_results: list[ToolResult] = state.get("tool_results") or []
        return {
            "answer": state.get("answer", ""),
            "visualization": state.get(
                "visualization", {"type": "none", "title": "", "data": [], "data_keys": {}}
            ),
            "source": {
                "tools": [r.tool_name for r in tool_results],
                "supplier_code": supplier_code,
            },
        }

    @staticmethod
    def _init_llm() -> Any:
        if ChatOpenAI is None:
            raise RuntimeError("langchain-openai is not installed.")
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is required.")
        raw = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
        _aliases = {"gpt-40-mini": "gpt-4o-mini", "gpt4o-mini": "gpt-4o-mini", "gpt-4o mini": "gpt-4o-mini"}
        return ChatOpenAI(model=_aliases.get(raw.lower(), raw), temperature=0)

    def _build_graph(self):
        g = StateGraph(AgentState)
        g.add_node("fetch_tools", self._fetch_tools)
        g.add_node("plan_tools", self._plan_tools)
        g.add_node("execute_tools", self._execute_tools)
        g.add_node("select_visualization", self._select_visualization)
        g.add_node("compose_answer", self._compose_answer)
        g.add_node("unsupported", self._unsupported)
        g.add_edge(START, "fetch_tools")
        g.add_edge("fetch_tools", "plan_tools")
        g.add_conditional_edges(
            "plan_tools",
            self._route_after_plan,
            {"execute_tools": "execute_tools", "plan_tools": "plan_tools", "unsupported": "unsupported"},
        )
        g.add_conditional_edges(
            "execute_tools",
            self._route_after_execute,
            {"select_visualization": "select_visualization", "unsupported": "unsupported"},
        )
        g.add_edge("select_visualization", "compose_answer")
        g.add_edge("compose_answer", END)
        g.add_edge("unsupported", END)
        return g.compile()

    # ── Nodes ─────────────────────────────────────────────────────────────────

    async def _fetch_tools(self, state: AgentState) -> dict:
        raw = await self.analytics.list_tools()
        if not raw:
            raise RuntimeError("MCP server returned no tools.")
        tools = [ToolInfo.model_validate(t) for t in raw if t.get("name") in _AGENT_TOOL_ALLOWLIST]
        if not tools:
            raise RuntimeError("MCP server returned no supported analytics tools.")
        return {"available_tools": tools}

    async def _plan_tools(self, state: AgentState) -> dict:
        schemas = [_make_tool_schema(t) for t in state["available_tools"]] + [_UNSUPPORTED_SCHEMA]
        messages = [
            SystemMessage(_PLANNER_SYSTEM),
            HumanMessage(
                f"Today: {date.today()}\n"
                f"Supplier: {state['supplier_code']}\n"
                f"Question: {state['question']}"
                + (f"\nPrevious error: {state['error']}" if state.get("error") else "")
            ),
        ]
        try:
            response = await self._llm.bind_tools(schemas, tool_choice="required").ainvoke(messages)
        except Exception as exc:
            log.warning("plan_tools failed: %s", exc)
            return {"tool_plans": [], "error": None, "retries": state.get("retries", 0) + 1}

        for tc in response.tool_calls:
            if tc["name"] == "unsupported":
                return {
                    "tool_plans": [],
                    "error": tc["args"].get("reason", "Unsupported question"),
                    "retries": self._max_retries,
                }

        plans = [
            ToolCallPlan(
                tool_name=tc["name"],
                arguments={k: v for k, v in tc.get("args", {}).items() if k != "label"},
                label=tc.get("args", {}).get("label") or tc["name"],
            )
            for tc in response.tool_calls
        ]
        for plan in plans:
            if plan.tool_name != "list_suppliers":
                plan.arguments["supplier_code"] = state["supplier_code"]
        return {"tool_plans": plans, "error": None}

    async def _execute_tools(self, state: AgentState) -> dict:
        plans: list[ToolCallPlan] = state["tool_plans"]
        raw_results = await asyncio.gather(
            *[self.analytics.call_tool(p.tool_name, p.arguments) for p in plans],
            return_exceptions=True,
        )
        results: list[ToolResult] = []
        for plan, raw in zip(plans, raw_results):
            if isinstance(raw, Exception):
                return {"error": f"Tool '{plan.tool_name}' failed: {raw}"}
            if not isinstance(raw, dict):
                raw = {"data": raw}
            if raw.get("found") is False:
                return {"error": raw.get("message") or f"No data for '{plan.tool_name}'."}
            results.append(ToolResult(tool_name=plan.tool_name, label=plan.label, data=raw))
        return {"tool_results": results}

    async def _select_visualization(self, state: AgentState) -> dict:
        results: list[ToolResult] = state["tool_results"]
        flat = _flatten_results(results)
        if not flat:
            return {"visualization": {"type": "none", "title": "No data", "data": [], "data_keys": {}}}
        summary = {"rows": len(flat), "fields": list(flat[0].keys()), "sample": flat[:3]}
        try:
            viz = await self._viz_llm.ainvoke([
                SystemMessage(_VIZ_SYSTEM),
                HumanMessage(
                    f"Question: {state['question']}\n"
                    f"Tools: {', '.join(r.tool_name for r in results)}\n"
                    f"Data summary: {json.dumps(summary, default=str)}"
                ),
            ])
            return {"visualization": {**viz.model_dump(), "data": flat}}
        except Exception as exc:
            log.warning("select_visualization failed: %s", exc)
            return {"visualization": {"type": "table", "title": "Analytics results", "data_keys": {"columns": list(flat[0].keys())}, "data": flat}}

    async def _compose_answer(self, state: AgentState) -> dict:
        results: list[ToolResult] = state.get("tool_results") or []
        viz = state.get("visualization") or {}
        results_json = json.dumps(
            [{"label": r.label, "tool": r.tool_name, "data": r.data} for r in results], default=str
        )
        answer = await self._answer_llm.ainvoke([
            SystemMessage(_ANSWER_SYSTEM),
            HumanMessage(
                f"Supplier: {state['supplier_code']}\n"
                f"Question: {state['question']}\n"
                f"Data: {results_json}\n"
                f"Chart type: {viz.get('type', 'none')}"
            ),
        ])
        return {"answer": answer.text, "visualization": {**viz, "title": answer.visualization_title or viz.get("title", "")}}

    async def _unsupported(self, state: AgentState) -> dict:
        reason = state.get("error") or "This question is outside the supported analytics scope."
        return {
            "answer": f"I can only answer supported supplier analytics questions. {reason}",
            "visualization": {"type": "none", "title": "Unsupported", "data": [], "data_keys": {}},
        }

    # ── Routing ───────────────────────────────────────────────────────────────

    def _route_after_plan(self, state: AgentState) -> str:
        if state.get("tool_plans"):
            return "execute_tools"
        if state.get("retries", 0) < self._max_retries:
            return "plan_tools"
        return "unsupported"

    def _route_after_execute(self, state: AgentState) -> str:
        return "unsupported" if state.get("error") else "select_visualization"
