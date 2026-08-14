"""Deterministic node: loads persisted analytical context into transient state.

Used by reuse_data / visualization_only / analysis_only routes so downstream
nodes read prior results without any new MCP call.
"""

from __future__ import annotations

from google.adk.agents.context import Context
from google.adk.workflow import BaseNode, node

from app.agents.state import StateKeys


def build_load_results_node() -> BaseNode:
    def load_results(ctx: Context) -> None:
        ctx.state[StateKeys.TOOL_RESULTS] = ctx.state.get(StateKeys.CTX_TOOL_CALLS_JSON) or []
        ctx.state[StateKeys.SUCCESSFUL_RESULTS_JSON] = (
            ctx.state.get(StateKeys.CTX_RESULTS_JSON) or "[]"
        )

    return node(load_results, name="load_results")
