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



def test_plural_best_products_defaults_to_five_even_if_llm_says_one():
    request = build_new_request(
        TurnInterpretation(
            mode="new_analysis",
            operation="ranking",
            group_by="product",
            rank_by="units",
            rank_order="highest",
            limit=1,
            scope={"cities": ["Stockholm"]},
        ),
        user_message="Vilka produkter säljer bäst i Stockholm?",
        current_date=date(2026, 8, 18),
    )

    assert request.operation == "ranking"
    assert request.group_by == "product"
    assert request.rank_by == "units"
    assert request.rank_order == "highest"
    assert request.limit == 5
    assert request.scope.cities == ["Stockholm"]


def test_singular_best_product_defaults_to_one():
    request = build_new_request(
        TurnInterpretation(
            mode="new_analysis",
            operation="ranking",
            group_by="product",
            rank_by="units",
            rank_order="highest",
            limit=5,
        ),
        user_message="Vilken produkt säljer bäst?",
        current_date=date(2026, 8, 18),
    )

    assert request.limit == 1


def test_show_more_ranking_followup_forces_modify_and_increases_limit():
    previous = build_new_request(
        TurnInterpretation(
            mode="new_analysis",
            operation="ranking",
            group_by="product",
            rank_by="units",
            rank_order="highest",
            limit=1,
            scope={"cities": ["Stockholm"]},
        ),
        user_message="Vilka produkter säljer bäst i Stockholm?",
        current_date=date(2026, 8, 18),
    )

    mode = effective_mode(
        TurnInterpretation(mode="conversation"),
        previous=previous,
        has_prior_results=True,
        user_message="Kan du visa fler?",
        current_date=date(2026, 8, 18),
    )
    assert mode == "modify_analysis"

    updated = merge_request(
        previous,
        TurnInterpretation(
            mode="conversation",
            limit=1,
        ),
        user_message="Kan du visa fler?",
        current_date=date(2026, 8, 18),
    )

    assert updated.operation == "ranking"
    assert updated.limit == 10
    assert updated.group_by == "product"
    assert updated.rank_by == "units"
    assert updated.scope.cities == ["Stockholm"]


def test_show_fewer_ranking_followup_decreases_limit():
    previous = build_new_request(
        TurnInterpretation(
            mode="new_analysis",
            operation="ranking",
            group_by="product",
            rank_by="units",
            rank_order="highest",
            limit=10,
        ),
        user_message="Visa topp 10 produkter.",
        current_date=date(2026, 8, 18),
    )

    updated = merge_request(
        previous,
        TurnInterpretation(mode="modify_analysis"),
        user_message="Visa färre.",
        current_date=date(2026, 8, 18),
    )

    assert updated.limit == 5
def test_explicit_line_graph_after_summary_requires_new_monthly_trend():
    previous = build_new_request(
        TurnInterpretation(
            mode="new_analysis",
            operation="summary",
            metrics=[
                "units",
                "net_sales",
                "orders",
                "average_selling_price",
            ],
            period_start=date(2026, 1, 1),
            period_end=date(2026, 3, 31),
        ),
        user_message="Hur har det gått för oss under q1?",
        current_date=date(2026, 8, 18),
    )

    mode = effective_mode(
        TurnInterpretation(
            mode="visualize_existing",
            presentation="chart",
        ),
        previous=previous,
        has_prior_results=True,
        user_message="visa en linjegraf",
        current_date=date(2026, 8, 18),
    )

    assert mode == "modify_analysis"

    updated = merge_request(
        previous,
        TurnInterpretation(
            mode="visualize_existing",
            presentation="chart",
        ),
        user_message="visa en linjegraf",
        current_date=date(2026, 8, 18),
    )

    assert updated.operation == "trend"
    assert updated.grain == "month"
    assert updated.metrics == ["net_sales"]
    assert updated.presentation == "chart"
    assert updated.period_start == date(2026, 1, 1)
    assert updated.period_end == date(2026, 3, 31)


def test_line_graph_reuses_existing_product_overview_trend():
    previous = build_new_request(
        TurnInterpretation(
            mode="new_analysis",
            operation="product_overview",
            product_query="windbreaker",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 3, 31),
        ),
        user_message="Hur har det gått under q1 för vår windbreaker?",
        current_date=date(2026, 8, 18),
    )

    mode = effective_mode(
        TurnInterpretation(mode="modify_analysis"),
        previous=previous,
        has_prior_results=True,
        user_message="visa en linjegraf",
        current_date=date(2026, 8, 18),
    )

    assert mode == "visualize_existing"
