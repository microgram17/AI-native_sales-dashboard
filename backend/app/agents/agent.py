"""Single native ADK agent with direct access to the analytics MCP tools."""

from __future__ import annotations

from typing import Any

from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams
from google.adk.tools.tool_context import ToolContext

from app.schemas.agent import AgentTurnOutput


MCP_TOKEN = "mcp_token"
TURN_TOOL_CALLS = "turn_tool_calls"
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
- Resolve relative dates from the current date. Explicit user wording overrides
  dashboard context. A widget analysis request is authoritative for its period,
  metrics, grouping, grain, and scope.
- Conversation history supplies follow-up context. For a modifier such as
  "same, but online", call the correct analytics tool with the complete updated
  arguments.
- For a presentation-only follow-up such as "show that as a table", do not call
  an analytics tool. Select reusable view IDs and set render_as="table".
- Use only facts present in tool results. Do not invent data or claim causes.
  If asked why, say the descriptive sales data cannot establish causation and
  give only a short grounded observation.
- status="not_found" means an entity could not be matched; status="ambiguous"
  means the user must choose among candidates; status="no_data" means the
  understood query returned no rows.
- Keep message short. Select only views relevant to the question. Measure keys
  must exist in the selected view. Use render_as="default" unless the user asks
  for a table. Give each selected display a natural localized title.
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


def capture_tool_result(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
    tool_response: dict[str, Any],
) -> None:
    """Capture MCP metadata and semantic views without rewriting their rows."""

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
    toolset = McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=mcp_server_url.rstrip("/") + "/",
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
        after_tool_callback=capture_tool_result,
    )
    return agent, toolset
