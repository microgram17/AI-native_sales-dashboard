"""Deterministic validator node. Routes back to the planner via ADK edges."""

from __future__ import annotations

from typing import Any

from google.adk.agents.context import Context
from google.adk.workflow import BaseNode, node

from app.agents.state import ROUTE_PROCEED, ROUTE_RETRY, ExecutedToolCall, StateKeys
from app.schemas.agent import ToolPlan

MAX_RETRIES = 2
_RECOGNIZED_STATUSES = {"success", "no_data", "not_found", "ambiguous"}


def _coerce_plan(value: Any) -> ToolPlan:
    if isinstance(value, ToolPlan):
        return value
    if isinstance(value, dict):
        return ToolPlan.model_validate(value)
    if isinstance(value, str) and value.strip():
        return ToolPlan.model_validate_json(value)
    return ToolPlan()


def _validate_call(call: ExecutedToolCall) -> list[str]:
    if call.failed:
        return [f"{call.tool_name}: execution failure ({call.error})."]
    if call.status not in _RECOGNIZED_STATUSES:
        return [f"{call.tool_name}: unrecognized status {call.status!r}."]
    if call.status != "success":
        return []
    result = call.result or {}
    if call.tool_name == "sales_rank" and not result.get("rows"):
        return ["sales_rank: success without ranking rows."]
    if call.tool_name == "sales_trend" and not result.get("rows"):
        return ["sales_trend: success without trend rows."]
    if call.tool_name == "product_overview" and not result.get("product"):
        return ["product_overview: success without a resolved product."]
    if call.tool_name == "sales_summary" and not result.get("current"):
        return ["sales_summary: success without summary metrics."]
    return []


def build_validate_results_node() -> BaseNode:
    def validate_results(
        ctx: Context,
        tool_plan: Any = None,
        tool_results: list[dict[str, Any]] | None = None,
        retry_count: int = 0,
    ) -> None:
        plan = _coerce_plan(tool_plan)
        results = [ExecutedToolCall.model_validate(r) for r in (tool_results or [])]

        errors: list[str] = []
        if not plan.tool_calls:
            errors.append("Planner produced no tool calls.")

        executed_ids = {r.call_id for r in results}
        for call in plan.tool_calls:
            if call.call_id not in executed_ids:
                errors.append(f"Tool call '{call.call_id}' did not execute.")
        for call in results:
            errors.extend(_validate_call(call))

        if errors:
            new_retry = retry_count + 1
            ctx.state[StateKeys.RETRY_COUNT] = new_retry
            ctx.state[StateKeys.LAST_VALIDATION_FAILED] = True
            previous = ctx.state.get(StateKeys.VALIDATION_ERRORS_TEXT, "")
            ctx.state[StateKeys.VALIDATION_ERRORS_TEXT] = (
                f"{previous} {' ; '.join(errors)}".strip()
            )
            ctx.route = ROUTE_RETRY if new_retry < MAX_RETRIES else ROUTE_PROCEED
        else:
            ctx.state[StateKeys.LAST_VALIDATION_FAILED] = False
            ctx.route = ROUTE_PROCEED

    return node(validate_results, name="validate_results")
