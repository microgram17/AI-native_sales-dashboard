
from __future__ import annotations

from datetime import date

from app.agents.answer_builder import build_short_answer
from app.agents.state import ExecutedToolCall
from app.schemas.agent import (
    AnalysisRequestState,
    AnalysisScope,
    CanonicalProduct,
)


def _executed(tool_name: str, result: dict) -> list[ExecutedToolCall]:
    return [
        ExecutedToolCall(
            call_id="analysis_1",
            tool_name=tool_name,
            status="success",
            result=result,
        )
    ]


def test_swedish_ranking_answer_is_short_and_grounded():
    request = AnalysisRequestState(
        operation="ranking",
        metrics=["units"],
        group_by="product",
        rank_by="units",
        rank_order="highest",
        limit=5,
        scope=AnalysisScope(cities=["Stockholm"]),
    )
    result = {
        "status": "success",
        "effective_period": {
            "start": "2024-01-01",
            "end": "2026-06-30",
            "label": "All available data",
            "defaulted": True,
        },
        "rows": [
            {
                "rank": 1,
                "entity": {
                    "type": "product",
                    "id": "AURA-ACT-006",
                    "name": "Sports Bra",
                },
                "metrics": {
                    "units": 641,
                    "net_sales": 243374.59,
                },
            },
            {
                "rank": 2,
                "entity": {
                    "type": "product",
                    "id": "AURA-JKT-025",
                    "name": "Windbreaker Jacket",
                },
                "metrics": {
                    "units": 610,
                    "net_sales": 220000.0,
                },
            },
        ],
    }

    answer = build_short_answer(
        request,
        _executed("sales_rank", result),
        "sv",
    )

    assert answer.startswith(
        "Sports Bra säljer bäst i Stockholm med 641 sålda enheter"
    )
    assert "hela den tillgängliga perioden" in answer
    assert "Diagrammet visar de 2" in answer


def test_swedish_trend_answer_describes_requested_metrics_without_rows():
    request = AnalysisRequestState(
        operation="trend",
        metrics=["units", "net_sales"],
        grain="month",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 12, 31),
        scope=AnalysisScope(channels=["online"]),
    )
    result = {
        "status": "success",
        "effective_period": {
            "start": "2026-01-01",
            "end": "2026-12-31",
            "label": "2026",
            "defaulted": False,
        },
        "rows": [
            {
                "period_label": "2026-01",
                "metrics": {
                    "units": 229,
                    "net_sales": 129433.40,
                },
            },
        ],
    }

    answer = build_short_answer(
        request,
        _executed("sales_trend", result),
        "sv",
    )

    assert answer == (
        "Här är den månatliga utvecklingen för sålda enheter och "
        "nettoomsättning online under 2026."
    )


def test_product_overview_answer_uses_canonical_name_and_two_key_facts():
    request = AnalysisRequestState(
        operation="product_overview",
        metrics=[
            "units",
            "net_sales",
            "orders",
            "average_selling_price",
        ],
        period_start=date(2026, 1, 1),
        period_end=date(2026, 3, 31),
        entity=CanonicalProduct(
            id="AURA-JKT-025",
            name="Windbreaker Jacket",
        ),
    )
    result = {
        "status": "success",
        "effective_period": {
            "start": "2026-01-01",
            "end": "2026-03-31",
            "label": "2026-01-01 – 2026-03-31",
            "defaulted": False,
        },
        "product": {
            "type": "product",
            "id": "AURA-JKT-025",
            "name": "Windbreaker Jacket",
        },
        "current": {
            "units": 144,
            "net_sales": 178841.14,
            "orders": 127,
            "average_selling_price": 1241.95,
        },
    }

    answer = build_short_answer(
        request,
        _executed("product_overview", result),
        "sv",
    )

    assert answer == (
        "Windbreaker Jacket: 144 sålda enheter och "
        "178\u00a0841 kr i nettoomsättning under Q1 2026."
    )


def test_visualization_reuse_does_not_repeat_previous_kpis():
    request = AnalysisRequestState(
        operation="product_overview",
        metrics=["units", "net_sales"],
        period_start=date(2026, 1, 1),
        period_end=date(2026, 3, 31),
        presentation="chart",
        entity=CanonicalProduct(
            id="AURA-JKT-025",
            name="Windbreaker Jacket",
        ),
    )
    result = {
        "status": "success",
        "effective_period": {
            "start": "2026-01-01",
            "end": "2026-03-31",
            "defaulted": False,
        },
        "current": {
            "units": 144,
            "net_sales": 178841.14,
        },
    }

    answer = build_short_answer(
        request,
        _executed("product_overview", result),
        "sv",
        effective_mode="visualize_existing",
    )

    assert answer == (
        "Här är utvecklingen för Windbreaker Jacket under Q1 2026."
    )
    assert "144" not in answer
