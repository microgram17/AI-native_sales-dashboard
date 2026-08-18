
"""Decide whether an analytics LLM call adds value to the final response."""

from __future__ import annotations

import json
from typing import Any

from google.adk.agents.context import Context
from google.adk.workflow import BaseNode, node

from app.agents.request_state import coerce_request
from app.agents.state import (
    ROUTE_DO_ANALYTICS,
    ROUTE_SKIP_ANALYTICS,
)
from app.schemas.visualization import VisualizationPlan


def _coerce_visualization_plan(
    value: Any,
) -> VisualizationPlan:
    if isinstance(value, VisualizationPlan):
        return value
    if isinstance(value, dict):
        try:
            return VisualizationPlan.model_validate(
                value
            )
        except Exception:
            return VisualizationPlan()
    if isinstance(value, str) and value.strip():
        try:
            return VisualizationPlan.model_validate_json(
                value
            )
        except Exception:
            return VisualizationPlan()
    return VisualizationPlan()


def _has_non_success_outcome(
    value: Any,
) -> bool:
    raw = value
    if isinstance(value, str):
        try:
            raw = json.loads(value)
        except json.JSONDecodeError:
            return True

    if not isinstance(raw, list):
        return True

    for item in raw:
        if not isinstance(item, dict):
            return True
        result = item.get("result")
        if not isinstance(result, dict):
            return True
        if result.get("status") != "success":
            return True

    return False


def should_run_analytics(
    *,
    effective_mode: str,
    canonical_request_json: Any,
    business_results_json: Any,
    visualization_plan: Any,
    direct_message: str | None,
) -> bool:
    if direct_message:
        return False

    request = coerce_request(
        canonical_request_json
    )
    if request is None:
        return True

    if effective_mode == "analyze_existing":
        return True

    if request.interpretation_requested:
        return True

    if _has_non_success_outcome(
        business_results_json
    ):
        return True

    plan = _coerce_visualization_plan(
        visualization_plan
    )
    if not plan.visualizations:
        return True

    return False


def build_response_policy_node() -> BaseNode:
    def response_policy(
        ctx: Context,
        effective_mode: str = "",
        canonical_request_json: Any = "null",
        business_results_json: Any = "[]",
        visualization_plan: Any = None,
        direct_message: str | None = None,
    ) -> None:
        ctx.route = (
            ROUTE_DO_ANALYTICS
            if should_run_analytics(
                effective_mode=effective_mode,
                canonical_request_json=canonical_request_json,
                business_results_json=business_results_json,
                visualization_plan=visualization_plan,
                direct_message=direct_message,
            )
            else ROUTE_SKIP_ANALYTICS
        )

    return node(
        response_policy,
        name="response_policy",
    )
