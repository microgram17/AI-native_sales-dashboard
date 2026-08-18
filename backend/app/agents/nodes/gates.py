"""Deterministic visualization and response-policy gates.

The visualization gate preserves the existing route behavior.

The analytics gate now also acts as a deterministic response policy:
- errors / no-data / ambiguous outcomes always get prose,
- requests without a valid visualization always get prose,
- explicit interpretation/explanation requests get prose,
- simple successful visualization-backed retrieval requests skip the analytics
  LLM entirely so the same data cannot be repeated in prose.

This makes visualizations first-class answers instead of relying on prompt
instructions to prevent duplication.
"""

from __future__ import annotations

import json
import re
from typing import Any

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
)
from app.schemas.visualization import VisualizationPlan


_RUN_VIZ = {
    ROUTE_NEW_DATA,
    ROUTE_REUSE_DATA,
    ROUTE_VISUALIZATION_ONLY,
}

# Routes where prose is potentially useful. visualization_only is intentionally
# excluded because the user explicitly asked for presentation, not new prose.
_RUN_ANALYTICS = {
    ROUTE_NEW_DATA,
    ROUTE_REUSE_DATA,
    ROUTE_ANALYSIS_ONLY,
}


# High-confidence wording that explicitly asks for interpretation rather than
# merely requesting data or a visualization.
_INTERPRETATION_PATTERNS = (
    # English
    r"\bwhy\b",
    r"\bexplain\b",
    r"\breason(?:s)?\b",
    r"\bcause(?:d|s)?\b",
    r"\bwhat\s+(?:stands?|stood)\s+out\b",
    r"\binsight(?:s)?\b",
    r"\banaly[sz]e\b",
    r"\banalysis\b",
    r"\binterpret(?:ation)?\b",
    r"\btakeaway(?:s)?\b",
    r"\bconclusion(?:s)?\b",
    r"\bwhat\s+can\s+we\s+(?:learn|conclude)\b",
    r"\bwhat\s+drove\b",
    # Swedish
    r"\bvarför\b",
    r"\bförklara\b",
    r"\banledning(?:ar)?\b",
    r"\borsak(?:er)?\b",
    r"\bvad\s+sticker\s+ut\b",
    r"\binsikt(?:er)?\b",
    r"\banalysera\b",
    r"\banalys\b",
    r"\btolka\b",
    r"\btolkning\b",
    r"\bslutsats(?:er)?\b",
    r"\bvad\s+kan\s+vi\s+(?:lära|dra\s+för\s+slutsats)\b",
    r"\bvad\s+drev\b",
)


def _coerce_visualization_plan(value: Any) -> VisualizationPlan:
    if isinstance(value, VisualizationPlan):
        return value

    if isinstance(value, dict):
        try:
            return VisualizationPlan.model_validate(value)
        except Exception:
            return VisualizationPlan()

    if isinstance(value, str) and value.strip():
        try:
            return VisualizationPlan.model_validate_json(value)
        except Exception:
            return VisualizationPlan()

    return VisualizationPlan()


def _has_valid_visualization(value: Any) -> bool:
    return bool(_coerce_visualization_plan(value).visualizations)


def _contains_non_success_business_outcome(value: Any) -> bool:
    """Return True when downstream prose is required to explain an outcome.

    successful_results_json is historical naming; it now contains all recognized
    business outcomes. Any non-success status must remain user-visible in prose.
    Invalid/unexpected input is handled conservatively by requesting analytics.
    """

    if value is None:
        return False

    raw = value
    if isinstance(value, str):
        if not value.strip():
            return False
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

        status = result.get("status")
        if status != "success":
            return True

    return False


def _requires_interpretation(user_message: str) -> bool:
    normalized = (user_message or "").casefold()
    return any(
        re.search(pattern, normalized, flags=re.IGNORECASE)
        for pattern in _INTERPRETATION_PATTERNS
    )


def should_run_analytics(
    *,
    effective_route: str,
    user_message: str,
    visualization_plan: Any,
    successful_results_json: Any,
) -> bool:
    """Deterministically decide whether an analytics LLM call adds value."""

    if effective_route not in _RUN_ANALYTICS:
        return False

    # analysis_only and reuse_data exist specifically because the user wants the
    # already-known data interpreted/rephrased. Keep the analytics path there.
    if effective_route in {
        ROUTE_ANALYSIS_ONLY,
        ROUTE_REUSE_DATA,
    }:
        return True

    # New-data error/business outcomes need a textual explanation.
    if _contains_non_success_business_outcome(successful_results_json):
        return True

    # If visualization generation failed or no visualization was appropriate,
    # prose must remain self-contained.
    if not _has_valid_visualization(visualization_plan):
        return True

    # A successful visualization-backed retrieval is allowed to stand on its
    # own unless the user explicitly asked for interpretation/explanation.
    return _requires_interpretation(user_message)


def build_visualization_gate_node() -> BaseNode:
    def visualization_gate(
        ctx: Context,
        effective_route: str = "",
    ) -> None:
        ctx.route = (
            ROUTE_DO_VIZ
            if effective_route in _RUN_VIZ
            else ROUTE_SKIP_VIZ
        )

    return node(
        visualization_gate,
        name="visualization_gate",
    )


def build_analytics_gate_node() -> BaseNode:
    def analytics_gate(
        ctx: Context,
        effective_route: str = "",
        user_message: str = "",
        visualization_plan: Any = None,
        successful_results_json: Any = "[]",
    ) -> None:
        ctx.route = (
            ROUTE_DO_ANALYTICS
            if should_run_analytics(
                effective_route=effective_route,
                user_message=user_message,
                visualization_plan=visualization_plan,
                successful_results_json=successful_results_json,
            )
            else ROUTE_SKIP_ANALYTICS
        )

    # Keep the existing node name so graph wiring and observability remain
    # stable; its responsibility is now the deterministic response policy.
    return node(
        analytics_gate,
        name="analytics_gate",
    )
