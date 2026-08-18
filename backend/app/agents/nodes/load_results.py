
"""Load the latest successful analytical result for presentation/analysis reuse."""

from __future__ import annotations

from google.adk.agents.context import Context
from google.adk.workflow import BaseNode, node

from app.agents.state import StateKeys


def build_load_results_node() -> BaseNode:
    def load_results(ctx: Context) -> None:
        ctx.state[StateKeys.TOOL_RESULTS] = (
            ctx.state.get(StateKeys.LAST_TOOL_RESULTS) or []
        )
        ctx.state[StateKeys.BUSINESS_RESULTS_JSON] = (
            ctx.state.get(StateKeys.LAST_BUSINESS_RESULTS_JSON) or "[]"
        )

    return node(load_results, name="load_results")
