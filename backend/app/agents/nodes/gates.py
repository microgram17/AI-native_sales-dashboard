"""Deterministic gate nodes that skip the visualization or analytics agent based
on the effective route (visualization_only skips analytics; analysis_only skips
visualization)."""

from __future__ import annotations

from google.adk.agents.context import Context
from google.adk.workflow import BaseNode, node

from app.agents.state import (
    ROUTE_ANALYSIS_ONLY,
    ROUTE_DO_ANALYTICS,
    ROUTE_DO_VIZ,
    ROUTE_NEW_DATA,
    ROUTE_REUSE_DATA,
    ROUTE_SKIP_ANALYTICS,
    ROUTE_SKIP_VIZ,
    ROUTE_VISUALIZATION_ONLY,
    StateKeys,
)

_RUN_VIZ = {ROUTE_NEW_DATA, ROUTE_REUSE_DATA, ROUTE_VISUALIZATION_ONLY}
_RUN_ANALYTICS = {ROUTE_NEW_DATA, ROUTE_REUSE_DATA, ROUTE_ANALYSIS_ONLY}


def build_visualization_gate_node() -> BaseNode:
    def visualization_gate(ctx: Context, effective_route: str = "") -> None:
        ctx.route = ROUTE_DO_VIZ if effective_route in _RUN_VIZ else ROUTE_SKIP_VIZ

    return node(visualization_gate, name="visualization_gate")


def build_analytics_gate_node() -> BaseNode:
    def analytics_gate(ctx: Context, effective_route: str = "") -> None:
        ctx.route = ROUTE_DO_ANALYTICS if effective_route in _RUN_ANALYTICS else ROUTE_SKIP_ANALYTICS

    return node(analytics_gate, name="analytics_gate")
