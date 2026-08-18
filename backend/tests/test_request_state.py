from __future__ import annotations

from datetime import date

from app.agents.request_state import (
    build_new_request,
    effective_mode,
    merge_request,
)
from app.schemas.agent import TurnInterpretation


def _trend_request():
    return build_new_request(
        TurnInterpretation(
            mode="new_analysis",
            operation="trend",
            metrics=["units", "net_sales"],
            grain="month",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 12, 31),
        ),
        user_message="Visa sålda enheter och nettoomsättning månadsvis för 2026.",
        current_date=date(2026, 8, 18),
    )


def test_modifier_patch_preserves_operation_period_grain_and_metrics():
    previous = _trend_request()

    updated = merge_request(
        previous,
        TurnInterpretation(
            mode="modify_analysis",
            scope={"channels": ["online"]},
        ),
        user_message="Visa samma sak men bara online.",
        current_date=date(2026, 8, 18),
    )

    assert updated.operation == "trend"
    assert updated.grain == "month"
    assert updated.metrics == ["units", "net_sales"]
    assert updated.period_start == date(2026, 1, 1)
    assert updated.period_end == date(2026, 12, 31)
    assert updated.scope.channels == ["online"]


def test_second_modifier_replaces_only_channel():
    previous = merge_request(
        _trend_request(),
        TurnInterpretation(
            mode="modify_analysis",
            scope={"channels": ["online"]},
        ),
        user_message="Visa samma sak men bara online.",
        current_date=date(2026, 8, 18),
    )

    updated = merge_request(
        previous,
        TurnInterpretation(mode="modify_analysis"),
        user_message="Och fysiska butiker?",
        current_date=date(2026, 8, 18),
    )

    assert updated.operation == "trend"
    assert updated.grain == "month"
    assert updated.metrics == ["units", "net_sales"]
    assert updated.period_start == date(2026, 1, 1)
    assert updated.period_end == date(2026, 12, 31)
    assert updated.scope.channels == ["physical"]


def test_generic_butiker_does_not_imply_physical_channel():
    previous = _trend_request()
    updated = merge_request(
        previous,
        TurnInterpretation(mode="modify_analysis"),
        user_message="Visa samma sak per butik.",
        current_date=date(2026, 8, 18),
    )
    assert updated.scope.channels == []


def test_graph_it_is_forced_to_visualize_existing_when_data_exists():
    previous = _trend_request()
    mode = effective_mode(
        TurnInterpretation(mode="modify_analysis"),
        previous=previous,
        has_prior_results=True,
        user_message="kan du grafa ut det?",
        current_date=date(2026, 8, 18),
    )
    assert mode == "visualize_existing"


def test_same_thing_phrase_forces_modify_even_if_llm_says_new_analysis():
    previous = _trend_request()
    mode = effective_mode(
        TurnInterpretation(mode="new_analysis"),
        previous=previous,
        has_prior_results=True,
        user_message="Visa samma sak men bara online.",
        current_date=date(2026, 8, 18),
    )
    assert mode == "modify_analysis"


def test_first_two_quarters_followup_changes_only_period():
    previous = _trend_request()
    updated = merge_request(
        previous,
        TurnInterpretation(mode="modify_analysis"),
        user_message="What about the first 2 quarters of 2026?",
        current_date=date(2026, 8, 18),
    )

    assert updated.operation == "trend"
    assert updated.grain == "month"
    assert updated.metrics == ["units", "net_sales"]
    assert updated.period_start == date(2026, 1, 1)
    assert updated.period_end == date(2026, 6, 30)



def test_q1_product_performance_does_not_become_quarterly_trend():
    request = build_new_request(
        TurnInterpretation(
            mode="new_analysis",
            operation="trend",
            metrics=["net_sales"],
            grain="quarter",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 3, 31),
            product_query="windereaker",
        ),
        user_message="Hur har det gått under q1 för våran windereaker?",
        current_date=date(2026, 8, 18),
    )

    assert request.operation == "product_overview"
    assert request.grain is None
    assert request.period_start == date(2026, 1, 1)
    assert request.period_end == date(2026, 3, 31)
    assert request.metrics == [
        "units",
        "net_sales",
        "orders",
        "average_selling_price",
    ]
    assert request.pending_product_query == "windereaker"


def test_explicit_quarterly_wording_still_creates_quarterly_trend():
    request = build_new_request(
        TurnInterpretation(
            mode="new_analysis",
            operation="trend",
            metrics=["net_sales"],
            grain="quarter",
            product_query="Windbreaker Jacket",
        ),
        user_message=(
            "Visa nettoomsättningen för Windbreaker Jacket "
            "kvartalsvis under 2026."
        ),
        current_date=date(2026, 8, 18),
    )

    assert request.operation == "trend"
    assert request.grain == "quarter"
    assert request.period_start == date(2026, 1, 1)
    assert request.period_end == date(2026, 12, 31)


def test_modifier_ignores_hallucinated_operation_and_grain():
    previous = _trend_request()

    updated = merge_request(
        previous,
        TurnInterpretation(
            mode="modify_analysis",
            operation="summary",
            grain="quarter",
            scope={"channels": ["online"]},
        ),
        user_message="Visa samma sak men bara online.",
        current_date=date(2026, 8, 18),
    )

    assert updated.operation == "trend"
    assert updated.grain == "month"
    assert updated.metrics == ["units", "net_sales"]
    assert updated.period_start == date(2026, 1, 1)
    assert updated.period_end == date(2026, 12, 31)
    assert updated.scope.channels == ["online"]
