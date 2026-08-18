from __future__ import annotations

from datetime import date

from app.agents.nodes.normalize_visualizations import normalize_visualization_datasets
from app.agents.state import ExecutedToolCall
from app.schemas.agent import AnalysisRequestState, CanonicalProduct
from tests.conftest import summary_success, trend_success


def test_summary_injects_canonical_product_identity():
    request = AnalysisRequestState(
        operation="summary",
        metrics=["units", "net_sales"],
        period_start=date(2026, 1, 1),
        period_end=date(2026, 3, 31),
        entity=CanonicalProduct(
            id="AURA-JKT-025",
            name="Windbreaker Jacket",
        ),
    )
    call = ExecutedToolCall(
        call_id="c1",
        tool_name="sales_summary",
        status="success",
        result=summary_success(product_id="AURA-JKT-025"),
    )

    datasets = normalize_visualization_datasets([call], request)
    current = next(item for item in datasets if item.view == "current")

    assert current.rows[0]["product_id"] == "AURA-JKT-025"
    assert current.rows[0]["product_name"] == "Windbreaker Jacket"


def test_trend_is_flattened():
    call = ExecutedToolCall(
        call_id="c1",
        tool_name="sales_trend",
        status="success",
        result=trend_success(),
    )

    datasets = normalize_visualization_datasets([call], None)
    trend = next(item for item in datasets if item.view == "trend")

    assert trend.rows[0]["period_label"] == "2026-01"
    assert trend.rows[0]["units"] == 1114
    assert trend.rows[0]["net_sales"] == 577975.25
