"""Single native ADK agent with direct access to the analytics MCP tools."""

from __future__ import annotations

import os
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams
from google.adk.tools.tool_context import ToolContext
from google.genai import types

from app.schemas.agent import AgentTurnOutput


MCP_TOKEN = "mcp_token"
TURN_TOOL_CALLS = "turn_tool_calls"
TURN_ANALYTICS_RESERVED = "turn_analytics_reserved"
TURN_ANALYTICS_CALLED = "turn_analytics_called"
TURN_ANALYTICS_RESULT = "turn_analytics_result"
LAST_ANALYTICS_RESULT = "last_analytics_result"

_ANALYTICS_TOOLS = {
    "sales_summary",
    "sales_rank",
    "sales_trend",
    "product_overview",
}


_INSTRUCTION = """You are a concise supplier sales analytics assistant.

Current date: {current_date}
UI language: {ui_language}
Dashboard context (trusted JSON or null): {dashboard_context_json}
Widget analysis request (trusted JSON or null): {widget_analysis_json}
Reusable data-view summary (JSON or null): {last_views_summary_json}

Use the MCP analytics tools directly. Their descriptions and schemas are the
source of truth for tool choice and arguments.

Rules:
- Reply entirely in Swedish when ui_language is "sv" and in English when it is
  "en". Preserve canonical entity names.
- Never send supplier_id or user identity as a tool argument. Supplier scope is
  supplied by trusted server authentication.
- For an analytics question, make exactly one analytics call. You may first use
  resolve_product when another analytics tool requires a canonical product ID.
- Once an analytics tool returns, stop calling tools and produce the final
  response. Never call analytics tools in parallel. A request about how one
  named product is doing uses product_overview directly; do not combine
  product_overview with resolve_product or another analytics tool.
- Resolve relative dates from the current date. Explicit user wording overrides
  dashboard context. A widget analysis request is authoritative for its period,
  metrics, grouping, grain, and scope.
- Conversation history supplies follow-up context. For a modifier such as
  "same, but online" or "and in Stockholm", always make a new analytics call
  with the complete updated arguments. Reuse the same named product, period,
  metric, and other filters unless the user changes them.
- A request to compare a product with "other", "all", or peer products widens
  the scope. Use sales_rank grouped by product, remove the prior product_ids
  filter, and filter by the resolved entity.category when available. Never
  compare a retained single-product scope with itself.
- When the user compares members of a dimension over time, use one sales_trend
  call with split_by (for example split_by="channel" for online versus
  physical). Do not make one filtered call per member. If the user explicitly
  asks for all members, set series_limit=10 instead of relying on the default
  top-five limit.
- For a presentation-only follow-up such as "show that as a table", do not call
  an analytics tool. Select reusable view IDs and set render_as="table". Only
  explicit presentation changes may reuse views; scope, period, metric, grain,
  ranking, and entity changes require fresh analytics.
- Use only facts present in tool results. Do not invent data or claim causes.
  If asked why, say the descriptive sales data cannot establish causation and
  give only a short grounded observation.
- status="not_found" means an entity could not be matched; status="ambiguous"
  means the user must choose among candidates; status="no_data" means the
  understood query returned no rows.
- The message is a short narrative answer, never a data transport. Use at most
  three short sentences. Never output a Markdown table, enumerate all rows, or
  repeat the full tool result; the selected DataViews carry the business data.
- Treat default_visible as the default presentation policy. For a broad or
  general overview, select only default-visible views; never select every
  available view merely because the tool returned it. Select a non-default
  view only when the user's current message explicitly requests that analysis.
  For product_overview: "how is it performing?" shows only the current metrics;
  select trend only for development over time, channel_breakdown only for a
  channel comparison, and city_breakdown only for a city/location breakdown.
- Measure keys must exist in the selected view. For categorical and timeseries
  views, use explicitly requested measures or otherwise the view's declared
  default_measures; do not select every measure by default. The frontend still
  offers the other declared measure fields in its metric picker.
- Use render_as="default" unless the user's current message explicitly asks
  for a table. A comparison does not imply a table. A timeseries uses
  render_as="default" unless a table was explicitly requested. Give each
  selected display a natural localized title.
- If a successful tool result has useful default-visible views and the user did
  not request a narrower presentation, select those views. Greetings and help
  questions require no tool and no displays.

Return the structured AgentTurnOutput only.
"""


def _headers(context: ReadonlyContext) -> dict[str, str]:
    token = str(context.state.get(MCP_TOKEN) or "").strip()
    return {"Authorization": f"Bearer {token}"} if token else {}


def _structured_content(response: Any) -> dict[str, Any] | None:
    if not isinstance(response, dict):
        return None
    for key in ("structuredContent", "structured_content"):
        value = response.get(key)
        if isinstance(value, dict):
            return value
    if {"status", "context", "views"}.issubset(response):
        return response
    return None


def enforce_tool_budget(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
) -> dict[str, Any] | None:
    """Prevent execution of any tool after this turn's analytics call."""

    del args
    blocked = tool_context.state.get(TURN_ANALYTICS_CALLED) or (
        tool.name in _ANALYTICS_TOOLS
        and tool_context.state.get(TURN_ANALYTICS_RESERVED)
    )
    if blocked:
        return {
            "isError": True,
            "error": "The analytics call limit for this turn has been reached.",
            "_blocked_by_tool_budget": True,
        }
    if tool.name in _ANALYTICS_TOOLS:
        # Reserve before execution so parallel calls from one model response
        # cannot both reach MCP before the first callback captures its result.
        tool_context.state[TURN_ANALYTICS_RESERVED] = True
    return None


def capture_tool_result(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
    tool_response: dict[str, Any],
) -> None:
    """Capture MCP metadata and semantic views without rewriting their rows."""

    if tool_response.get("_blocked_by_tool_budget"):
        return

    structured = _structured_content(tool_response)
    is_error = bool(tool_response.get("isError") or tool_response.get("is_error"))
    status = structured.get("status") if structured else None
    error = "Tool execution failed." if is_error else None
    call = {
        "call_id": tool_context.function_call_id
        or f"call_{len(tool_context.state.get(TURN_TOOL_CALLS, [])) + 1}",
        "tool_name": tool.name,
        "arguments": dict(args),
        "status": status,
        "error": error,
    }
    tool_context.state[TURN_TOOL_CALLS] = [
        *list(tool_context.state.get(TURN_TOOL_CALLS, [])),
        call,
    ]

    if tool.name not in _ANALYTICS_TOOLS:
        return

    tool_context.state[TURN_ANALYTICS_CALLED] = True
    tool_context.state[TURN_ANALYTICS_RESULT] = structured
    if (
        not is_error
        and structured is not None
        and structured.get("status") == "success"
        and structured.get("views")
    ):
        tool_context.state[LAST_ANALYTICS_RESULT] = structured


def build_sales_agent(
    model: LiteLlm,
    mcp_server_url: str,
) -> tuple[LlmAgent, McpToolset]:
    # ADK's MCP transport otherwise probes Google Application Default
    # Credentials for an optional mTLS client certificate on every local
    # request. This server authenticates with its own short-lived Bearer token;
    # operators that actually deploy mTLS can still override the environment.
    os.environ.setdefault("GOOGLE_API_USE_CLIENT_CERTIFICATE", "false")

    toolset = McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            # FastMCP mounts its canonical endpoint without a trailing slash.
            # Avoid a redirect so per-request Authorization is preserved.
            url=mcp_server_url.rstrip("/"),
        ),
        tool_filter=[
            "resolve_product",
            "sales_summary",
            "sales_rank",
            "sales_trend",
            "product_overview",
        ],
        header_provider=_headers,
    )
    agent = LlmAgent(
        name="sales_agent",
        model=model,
        instruction=_INSTRUCTION,
        tools=[toolset],
        output_schema=AgentTurnOutput,
        output_key="agent_turn_output",
        generate_content_config=types.GenerateContentConfig(
            temperature=0,
            max_output_tokens=512,
        ),
        before_tool_callback=enforce_tool_budget,
        after_tool_callback=capture_tool_result,
    )
    return agent, toolset
