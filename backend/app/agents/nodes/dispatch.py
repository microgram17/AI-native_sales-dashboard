"""Deterministic router-dispatch node: turns the router's decision into a route.

Falls back to new_data when a data-reuse route is chosen but no prior analytical
results exist.
"""

from __future__ import annotations

from typing import Any

from google.adk.agents.context import Context
from google.adk.workflow import BaseNode, node

from app.agents.state import (
    ROUTE_ANALYSIS_ONLY,
    ROUTE_CONVERSATION,
    ROUTE_NEW_DATA,
    ROUTE_REUSE_DATA,
    ROUTE_VISUALIZATION_ONLY,
    StateKeys,
)
from app.schemas.agent import RouteDecision

_REUSE_ROUTES = {ROUTE_REUSE_DATA, ROUTE_VISUALIZATION_ONLY, ROUTE_ANALYSIS_ONLY}


def _coerce_decision(value: Any) -> RouteDecision:
    if isinstance(value, RouteDecision):
        return value
    if isinstance(value, dict):
        return RouteDecision.model_validate(value)
    if isinstance(value, str) and value.strip():
        return RouteDecision.model_validate_json(value)
    return RouteDecision(route=ROUTE_NEW_DATA, reason="default")


def build_dispatch_node() -> BaseNode:
    def dispatch(
        ctx: Context,
        route_decision: Any = None,
        has_prior_results: bool = False,
    ) -> None:
        decision = _coerce_decision(route_decision)
        route = decision.route
        if route in _REUSE_ROUTES and not has_prior_results:
            route = ROUTE_NEW_DATA
        if route == ROUTE_CONVERSATION:
            route = ROUTE_CONVERSATION
        ctx.state[StateKeys.EFFECTIVE_ROUTE] = route
        ctx.route = route

    return node(dispatch, name="dispatch")
