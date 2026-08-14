"""Deterministic MCP executor node (not model-driven)."""

from __future__ import annotations

import json
from typing import Any

from google.adk.agents.context import Context
from google.adk.workflow import BaseNode, node

from app.agents.state import ExecutedToolCall, StateKeys
from app.integrations.mcp.client import McpClient, McpClientError
from app.schemas.agent import ToolPlan


def _coerce_plan(value: Any) -> ToolPlan:
    if isinstance(value, ToolPlan):
        return value
    if isinstance(value, dict):
        return ToolPlan.model_validate(value)
    if isinstance(value, str) and value.strip():
        return ToolPlan.model_validate_json(value)
    return ToolPlan()


def build_execute_tools_node(mcp: McpClient) -> BaseNode:
    async def execute_tools(
        ctx: Context,
        tool_plan: Any = None,
        available_tool_names: list[str] | None = None,
        mcp_token: str | None = None,
    ) -> None:
        plan = _coerce_plan(tool_plan)
        known = set(available_tool_names or [])
        results: list[ExecutedToolCall] = []

        for draft in plan.tool_calls:
            call = draft.to_call()
            if call.tool_name not in known:
                results.append(
                    ExecutedToolCall(
                        call_id=call.call_id,
                        tool_name=call.tool_name,
                        arguments=call.arguments,
                        purpose=call.purpose,
                        error=f"Unknown tool '{call.tool_name}'.",
                    )
                )
                continue
            try:
                outcome = await mcp.call_tool(call.tool_name, call.arguments, token=mcp_token)
            except McpClientError as exc:
                results.append(
                    ExecutedToolCall(
                        call_id=call.call_id,
                        tool_name=call.tool_name,
                        arguments=call.arguments,
                        purpose=call.purpose,
                        error=str(exc),
                    )
                )
                continue
            if outcome.is_error:
                results.append(
                    ExecutedToolCall(
                        call_id=call.call_id,
                        tool_name=call.tool_name,
                        arguments=call.arguments,
                        purpose=call.purpose,
                        error=outcome.error_message or "Tool execution error.",
                    )
                )
                continue
            structured = outcome.structured or {}
            results.append(
                ExecutedToolCall(
                    call_id=call.call_id,
                    tool_name=call.tool_name,
                    arguments=call.arguments,
                    purpose=call.purpose,
                    status=structured.get("status"),
                    result=structured,
                )
            )

        ctx.state[StateKeys.TOOL_RESULTS] = [r.model_dump() for r in results]
        successful = [
            {"call_id": r.call_id, "tool_name": r.tool_name, "result": r.result}
            for r in results
            if r.is_success
        ]
        ctx.state[StateKeys.SUCCESSFUL_RESULTS_JSON] = json.dumps(successful)

    return node(execute_tools, name="execute_tools")
