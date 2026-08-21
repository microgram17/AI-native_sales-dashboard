
"""Merge one semantic turn into the canonical analytical request."""

from __future__ import annotations

from datetime import date
from typing import Any

from google.adk.agents.context import Context
from google.adk.workflow import BaseNode, node

from app.agents.request_state import (
    apply_dashboard_context,
    build_new_request,
    coerce_dashboard_context,
    coerce_interpretation,
    coerce_request,
    effective_mode,
    merge_request,
    references_dashboard_context,
    request_to_json,
    validate_request,
)
from app.agents.state import (
    ROUTE_CONVERSATION,
    ROUTE_DIRECT,
    ROUTE_EXECUTE,
    ROUTE_REUSE,
    StateKeys,
)


def _localized_message(ui_language: str, key: str) -> str:
    messages = {
        "sv": {
            "no_prior": "Det finns ingen tidigare analys att återanvända ännu.",
            "product_required": "Vilken produkt vill du analysera?",
            "invalid": "Jag kunde inte tolka analysens period eller filter på ett säkert sätt.",
        },
        "en": {
            "no_prior": "There is no previous analysis to reuse yet.",
            "product_required": "Which product would you like to analyze?",
            "invalid": "I could not safely interpret the analysis period or filters.",
        },
    }
    language = "sv" if ui_language == "sv" else "en"
    return messages[language][key]


def build_resolve_turn_node() -> BaseNode:
    def resolve_turn(
        ctx: Context,
        turn_interpretation: Any = None,
        canonical_request_json: Any = "null",
        last_has_results: bool = False,
        user_message: str = "",
        current_date: str = "",
        ui_language: str = "en",
        widget_analysis_request_json: Any = "null",
        dashboard_context_json: Any = "null",
    ) -> None:
        interpretation = coerce_interpretation(turn_interpretation)
        previous = coerce_request(canonical_request_json)
        widget_request = coerce_request(widget_analysis_request_json)
        dashboard_context = coerce_dashboard_context(dashboard_context_json)

        if widget_request is not None:
            error = validate_request(widget_request)
            if error is not None:
                ctx.state[StateKeys.DIRECT_MESSAGE] = _localized_message(
                    ui_language,
                    "invalid",
                )
                ctx.route = ROUTE_DIRECT
                return

            ctx.state[StateKeys.EFFECTIVE_MODE] = "new_analysis"
            ctx.state[StateKeys.CANONICAL_REQUEST_JSON] = request_to_json(
                widget_request
            )
            ctx.route = ROUTE_EXECUTE
            return

        try:
            today = date.fromisoformat(current_date)
        except ValueError:
            today = date.today()

        mode = effective_mode(
            interpretation,
            previous=previous,
            has_prior_results=bool(last_has_results),
            user_message=user_message,
            current_date=today,
        )
        ctx.state[StateKeys.EFFECTIVE_MODE] = mode

        if mode == "conversation":
            ctx.route = ROUTE_CONVERSATION
            return

        if mode in {"visualize_existing", "analyze_existing"}:
            if previous is None or not last_has_results:
                if (
                    dashboard_context is not None
                    and references_dashboard_context(user_message)
                ):
                    interpretation_requested = mode == "analyze_existing"
                    mode = "new_analysis"
                    ctx.state[StateKeys.EFFECTIVE_MODE] = mode
                    interpretation = interpretation.model_copy(
                        update={
                            "mode": "new_analysis",
                            "operation": dashboard_context.view or "summary",
                            "interpretation_requested": (
                                interpretation_requested
                                or interpretation.interpretation_requested
                            ),
                        }
                    )
                else:
                    ctx.state[StateKeys.DIRECT_MESSAGE] = _localized_message(
                        ui_language,
                        "no_prior",
                    )
                    ctx.route = ROUTE_DIRECT
                    return

            else:
                request = previous.model_copy(
                    update={
                        "presentation": (
                            interpretation.presentation
                            or (
                                "chart"
                                if mode == "visualize_existing"
                                else previous.presentation
                            )
                        ),
                        "interpretation_requested": mode == "analyze_existing",
                    }
                )
                ctx.state[StateKeys.CANONICAL_REQUEST_JSON] = request_to_json(request)
                ctx.route = ROUTE_REUSE
                return

        if mode == "modify_analysis" and previous is not None:
            request = merge_request(
                previous,
                interpretation,
                user_message=user_message,
                current_date=today,
            )
        else:
            request = build_new_request(
                interpretation,
                user_message=user_message,
                current_date=today,
            )

        request = apply_dashboard_context(
            request,
            dashboard_context,
            user_message=user_message,
        )

        error = validate_request(request)
        if error == "product_overview requires a product":
            ctx.state[StateKeys.DIRECT_MESSAGE] = _localized_message(
                ui_language,
                "product_required",
            )
            ctx.route = ROUTE_DIRECT
            return
        if error is not None:
            ctx.state[StateKeys.DIRECT_MESSAGE] = _localized_message(
                ui_language,
                "invalid",
            )
            ctx.route = ROUTE_DIRECT
            return

        ctx.state[StateKeys.CANONICAL_REQUEST_JSON] = request_to_json(request)
        ctx.route = ROUTE_EXECUTE

    return node(resolve_turn, name="resolve_turn")
