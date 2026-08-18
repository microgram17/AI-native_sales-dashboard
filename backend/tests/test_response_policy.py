from __future__ import annotations

import json

from app.agents.nodes.gates import should_run_analytics
from app.agents.state import (
    ROUTE_ANALYSIS_ONLY,
    ROUTE_NEW_DATA,
    ROUTE_REUSE_DATA,
    ROUTE_VISUALIZATION_ONLY,
)


def _viz_plan() -> dict:
    return {
        "visualizations": [
            {
                "dataset": "c1:ranking",
                "type": "bar_chart",
                "title": "Top products",
                "x_key": "entity_name",
                "y_keys": ["net_sales"],
            }
        ]
    }


def _results(status: str = "success") -> str:
    return json.dumps(
        [
            {
                "call_id": "c1",
                "tool_name": "sales_rank",
                "result": {
                    "status": status,
                },
            }
        ]
    )


def test_simple_successful_visualization_is_complete_answer() -> None:
    assert not should_run_analytics(
        effective_route=ROUTE_NEW_DATA,
        user_message="Show the top 5 products in Q1.",
        visualization_plan=_viz_plan(),
        successful_results_json=_results(),
    )


def test_explicit_interpretation_requests_prose() -> None:
    assert should_run_analytics(
        effective_route=ROUTE_NEW_DATA,
        user_message="Why did these products stand out?",
        visualization_plan=_viz_plan(),
        successful_results_json=_results(),
    )


def test_swedish_explicit_interpretation_requests_prose() -> None:
    assert should_run_analytics(
        effective_route=ROUTE_NEW_DATA,
        user_message="Varför sticker de här produkterna ut?",
        visualization_plan=_viz_plan(),
        successful_results_json=_results(),
    )


def test_no_data_requests_prose_even_with_visualization_plan() -> None:
    assert should_run_analytics(
        effective_route=ROUTE_NEW_DATA,
        user_message="Show sales.",
        visualization_plan=_viz_plan(),
        successful_results_json=_results("no_data"),
    )


def test_missing_visualization_requests_prose() -> None:
    assert should_run_analytics(
        effective_route=ROUTE_NEW_DATA,
        user_message="Show the top 5 products.",
        visualization_plan={"visualizations": []},
        successful_results_json=_results(),
    )


def test_analysis_only_always_runs_analytics() -> None:
    assert should_run_analytics(
        effective_route=ROUTE_ANALYSIS_ONLY,
        user_message="Which of those stands out?",
        visualization_plan=_viz_plan(),
        successful_results_json=_results(),
    )


def test_reuse_data_keeps_analytics_path() -> None:
    assert should_run_analytics(
        effective_route=ROUTE_REUSE_DATA,
        user_message="Summarize that differently.",
        visualization_plan=_viz_plan(),
        successful_results_json=_results(),
    )


def test_visualization_only_never_runs_analytics() -> None:
    assert not should_run_analytics(
        effective_route=ROUTE_VISUALIZATION_ONLY,
        user_message="Show that as a bar chart.",
        visualization_plan=_viz_plan(),
        successful_results_json=_results(),
    )
