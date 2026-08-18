from __future__ import annotations

from datetime import date

from app.agents.nodes.response_policy import should_run_analytics
from app.schemas.agent import AnalysisRequestState


def _request(*, interpret: bool = False) -> str:
    return AnalysisRequestState(
        operation="summary",
        metrics=["net_sales"],
        period_start=date(2026, 1, 1),
        period_end=date(2026, 3, 31),
        interpretation_requested=interpret,
    ).model_dump_json()


def _viz() -> dict:
    return {
        "visualizations": [
            {
                "dataset": "c1:current",
                "type": "metric_cards",
                "title": "Sales",
                "y_keys": ["net_sales"],
            }
        ]
    }


def test_simple_successful_visualization_skips_analytics():
    assert not should_run_analytics(
        effective_mode="new_analysis",
        canonical_request_json=_request(),
        business_results_json='[{"result":{"status":"success"}}]',
        visualization_plan=_viz(),
        direct_message=None,
    )


def test_interpretation_keeps_analytics():
    assert should_run_analytics(
        effective_mode="new_analysis",
        canonical_request_json=_request(interpret=True),
        business_results_json='[{"result":{"status":"success"}}]',
        visualization_plan=_viz(),
        direct_message=None,
    )


def test_not_found_keeps_analytics():
    assert should_run_analytics(
        effective_mode="new_analysis",
        canonical_request_json=_request(),
        business_results_json='[{"result":{"status":"not_found"}}]',
        visualization_plan={"visualizations": []},
        direct_message=None,
    )


def test_direct_message_skips_analytics():
    assert not should_run_analytics(
        effective_mode="new_analysis",
        canonical_request_json=_request(),
        business_results_json="[]",
        visualization_plan={"visualizations": []},
        direct_message="Choose a product.",
    )
