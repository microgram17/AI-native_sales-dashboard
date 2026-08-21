from __future__ import annotations

from datetime import date

from app.agents.request_state import (
    apply_dashboard_context,
    build_new_request,
    effective_mode,
    merge_request,
)
from app.schemas.agent import DashboardContext, TurnInterpretation


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


def test_current_dashboard_trend_applies_exact_visible_store_series():
    request = build_new_request(
        TurnInterpretation(mode="new_analysis", operation="summary"),
        user_message="Analyze the current dashboard view.",
        current_date=date(2026, 8, 18),
    )

    contextualized = apply_dashboard_context(
        request,
        DashboardContext(
            date_from=date(2025, 7, 1),
            date_to=date(2026, 6, 30),
            metric="net_sales",
            grain="month",
            group_by="store",
            view="trend",
            selected_group_ids=["ONLINE-SE", "STO-001", "STO-002"],
        ),
        user_message="Analyze the current dashboard view.",
    )

    assert contextualized.operation == "trend"
    assert contextualized.metrics == ["net_sales"]
    assert contextualized.grain == "month"
    assert contextualized.split_by == "store"
    assert contextualized.scope.store_ids == [
        "ONLINE-SE",
        "STO-001",
        "STO-002",
    ]
    assert contextualized.series_limit == 3
    assert contextualized.period_start == date(2025, 7, 1)
    assert contextualized.period_end == date(2026, 6, 30)


def test_explicit_city_group_never_inherits_store_ids():
    request = build_new_request(
        TurnInterpretation(
            mode="new_analysis",
            operation="trend",
            metrics=["net_sales"],
            period_start=date(2025, 7, 1),
            period_end=date(2026, 6, 30),
        ),
        user_message="Show the net sales trend by city.",
        current_date=date(2026, 8, 18),
    )

    contextualized = apply_dashboard_context(
        request,
        DashboardContext(
            date_from=date(2025, 7, 1),
            date_to=date(2026, 6, 30),
            metric="net_sales",
            grain="month",
            group_by="store",
            view="trend",
            selected_group_ids=["ONLINE-SE", "STO-001"],
        ),
        user_message="Show the net sales trend by city.",
    )

    assert contextualized.operation == "trend"
    assert contextualized.split_by == "city"
    assert contextualized.scope.store_ids == []
    assert contextualized.scope.cities == []


def test_broad_period_analysis_defaults_to_monthly_trend():
    request = build_new_request(
        TurnInterpretation(
            mode="new_analysis",
            operation="summary",
            metrics=["net_sales"],
            period_start=date(2026, 1, 1),
            period_end=date(2026, 3, 31),
        ),
        user_message="Analyze net sales during Q1 2026.",
        current_date=date(2026, 8, 18),
    )

    assert request.operation == "trend"
    assert request.grain == "month"
    assert request.presentation == "auto"

    overview = build_new_request(
        TurnInterpretation(
            mode="new_analysis",
            operation="summary",
            metrics=["net_sales"],
            period_start=date(2026, 1, 1),
            period_end=date(2026, 3, 31),
        ),
        user_message="Show me a net sales overview for Q1 2026.",
        current_date=date(2026, 8, 18),
    )

    assert overview.operation == "trend"
    assert overview.grain == "month"


def test_explicit_total_question_remains_a_summary_snapshot():
    request = build_new_request(
        TurnInterpretation(
            mode="new_analysis",
            operation="trend",
            metrics=["net_sales"],
            period_start=date(2026, 1, 1),
            period_end=date(2026, 3, 31),
        ),
        user_message="What was the total net sales during Q1 2026?",
        current_date=date(2026, 8, 18),
    )

    assert request.operation == "summary"
    assert request.grain is None


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


def test_average_order_value_requests_supporting_metrics():
    request = build_new_request(
        TurnInterpretation(mode="new_analysis", operation="summary"),
        user_message="Explain the change in average order value.",
        current_date=date(2026, 8, 18),
    )

    assert request.metrics == ["net_sales", "orders"]


def test_units_per_order_requests_supporting_metrics():
    request = build_new_request(
        TurnInterpretation(mode="new_analysis", operation="summary"),
        user_message="Förklara förändringen i enheter per order.",
        current_date=date(2026, 8, 18),
    )

    assert request.metrics == ["units", "orders"]


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
        user_message="Vad var den totala nettoomsättningen under q1?",
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
