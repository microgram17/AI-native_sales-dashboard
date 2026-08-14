"""Deterministic node: persist analytical context from successful results.

Runs after a valid new_data turn. Extracts entities, effective period and scope
without any extra LLM call so follow-up turns can inherit them.
"""

from __future__ import annotations

import json

from google.adk.agents.context import Context
from google.adk.workflow import BaseNode, node

from app.agents.state import ExecutedToolCall, StateKeys


def build_persist_context_node() -> BaseNode:
    def persist_context(
        ctx: Context,
        tool_results: list[dict] | None = None,
        successful_results_json: str = "[]",
    ) -> None:
        results = [ExecutedToolCall.model_validate(r) for r in (tool_results or [])]
        successful = [r for r in results if r.is_success]

        entities: list[dict] = []
        period = None
        scope = None
        for call in successful:
            result = call.result or {}
            if call.tool_name == "product_overview" and result.get("product"):
                entities.append(result["product"])
            rows = result.get("rows")
            if isinstance(rows, list) and rows:
                entity = rows[0].get("entity")
                if entity:
                    entities.append(entity)
            if period is None and result.get("effective_period"):
                period = result["effective_period"]
            if scope is None and result.get("effective_scope"):
                scope = result["effective_scope"]

        ctx.state[StateKeys.CTX_HAS_RESULTS] = bool(successful)
        ctx.state[StateKeys.CTX_TOOL_CALLS_JSON] = [r.model_dump() for r in results]
        ctx.state[StateKeys.CTX_RESULTS_JSON] = successful_results_json
        ctx.state[StateKeys.CTX_ENTITIES_JSON] = json.dumps(entities)
        ctx.state[StateKeys.CTX_PERIOD_JSON] = json.dumps(period)
        ctx.state[StateKeys.CTX_SCOPE_JSON] = json.dumps(scope)

    return node(persist_context, name="persist_context")
