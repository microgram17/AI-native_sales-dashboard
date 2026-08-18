"""Compile the canonical request and execute exactly one MCP analytics call."""

from __future__ import annotations

import json
from typing import Any

from google.adk.agents.context import Context
from google.adk.workflow import BaseNode, node

from app.agents.request_state import coerce_request
from app.agents.retrieval import compile_request
from app.agents.state import ExecutedToolCall, StateKeys
from app.integrations.mcp.client import McpClient, McpClientError


def _failure_message(language: str) -> str:
    if language == "sv":
        return "Analysfrågan kunde inte köras just nu."
    return "The analytics request could not be executed right now."


def _capabilities(value: Any) -> dict[str, str]:
    if isinstance(value, dict):
        return {str(k): str(v) for k, v in value.items()}
    if isinstance(value, str) and value.strip():
        try:
            raw = json.loads(value)
        except json.JSONDecodeError:
            return {}
        if isinstance(raw, dict):
            return {str(k): str(v) for k, v in raw.items()}
    return {}


def build_execute_request_node(mcp: McpClient) -> BaseNode:
    async def execute_request(
        ctx: Context,
        canonical_request_json: Any = "null",
        mcp_capabilities_json: Any = "{}",
        mcp_token: str | None = None,
        ui_language: str = "en",
    ) -> None:
        request = coerce_request(canonical_request_json)
        if request is None:
            raise RuntimeError("Canonical analytical request is missing.")

        compiled = compile_request(request)
        tool_name = _capabilities(mcp_capabilities_json).get(
            compiled.capability
        )
        if not tool_name:
            ctx.state[StateKeys.DIRECT_MESSAGE] = _failure_message(ui_language)
            ctx.state[StateKeys.TOOL_RESULTS] = []
            ctx.state[StateKeys.BUSINESS_RESULTS_JSON] = "[]"
            ctx.state[StateKeys.LAST_HAS_RESULTS] = False
            return

        try:
            outcome = await mcp.call_tool(
                tool_name,
                compiled.arguments,
                token=mcp_token,
            )
        except McpClientError:
            ctx.state[StateKeys.DIRECT_MESSAGE] = _failure_message(ui_language)
            ctx.state[StateKeys.TOOL_RESULTS] = []
            ctx.state[StateKeys.BUSINESS_RESULTS_JSON] = "[]"
            ctx.state[StateKeys.LAST_HAS_RESULTS] = False
            return

        if outcome.is_error:
            ctx.state[StateKeys.DIRECT_MESSAGE] = _failure_message(ui_language)
            result = ExecutedToolCall(
                call_id="analysis_1",
                tool_name=tool_name,
                arguments=compiled.arguments,
                purpose=compiled.purpose,
                error=outcome.error_message or "Tool execution error.",
            )
            ctx.state[StateKeys.TOOL_RESULTS] = [result.model_dump(mode="json")]
            ctx.state[StateKeys.BUSINESS_RESULTS_JSON] = "[]"
            ctx.state[StateKeys.LAST_HAS_RESULTS] = False
            ctx.state[StateKeys.LAST_TOOL_RESULTS] = [result.model_dump(mode="json")]
            ctx.state[StateKeys.LAST_BUSINESS_RESULTS_JSON] = "[]"
            return

        structured = outcome.structured or {}
        result = ExecutedToolCall(
            call_id="analysis_1",
            tool_name=tool_name,
            arguments=compiled.arguments,
            purpose=compiled.purpose,
            status=structured.get("status"),
            result=structured,
        )

        serialized = result.model_dump(mode="json")
        business = (
            [
                {
                    "call_id": result.call_id,
                    "tool_name": result.tool_name,
                    "result": result.result,
                }
            ]
            if result.is_business_result
            else []
        )

        ctx.state[StateKeys.TOOL_RESULTS] = [serialized]
        ctx.state[StateKeys.BUSINESS_RESULTS_JSON] = json.dumps(
            business,
            ensure_ascii=False,
        )

        ctx.state[StateKeys.LAST_TOOL_RESULTS] = [serialized]
        ctx.state[StateKeys.LAST_BUSINESS_RESULTS_JSON] = json.dumps(
            business,
            ensure_ascii=False,
        )
        ctx.state[StateKeys.LAST_HAS_RESULTS] = result.is_success

    return node(execute_request, name="execute_request")
