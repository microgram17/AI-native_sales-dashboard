from __future__ import annotations

from datetime import date

from app.agents.visualization_builder import build_visualization_plan
from app.schemas.agent import AnalysisRequestState, AnalysisScope, CanonicalProduct
from app.schemas.visualization import VisualizationDataset


def test_monthly_units_and_sales_get_dual_axis_line():
    request = AnalysisRequestState(
        operation="trend",
        metrics=["units", "net_sales"],
        grain="month",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 12, 31),
    )
    dataset = VisualizationDataset(
        id="c1:trend",
        source_call_id="c1",
        view="trend",
        rows=[
            {"period_label": "2026-01", "units": 100, "net_sales": 50000.0},
            {"period_label": "2026-02", "units": 110, "net_sales": 52000.0},
        ],
    )

    plan = build_visualization_plan(request, [dataset], "sv")
    spec = plan.visualizations[0]

    assert spec.type == "line_chart"
    assert spec.y_keys == ["units", "net_sales"]
    assert spec.secondary_y_keys == ["net_sales"]
    assert spec.selectable_y_keys == [
        "net_sales",
        "gross_sales",
        "units",
        "orders",
        "discounts",
        "average_selling_price",
        "discount_rate",
    ]
    assert spec.title == "Utveckling – 2026"


def test_explicit_chart_over_summary_uses_real_chart_not_cards():
    request = AnalysisRequestState(
        operation="summary",
        metrics=["units", "net_sales", "orders"],
        period_start=date(2026, 1, 1),
        period_end=date(2026, 3, 31),
        presentation="chart",
        entity=CanonicalProduct(
            id="AURA-JKT-025",
            name="Windbreaker Jacket",
        ),
    )
    current = VisualizationDataset(
        id="c1:current",
        source_call_id="c1",
        view="current",
        rows=[
            {
                "period_label": "2026-01-01 – 2026-03-31",
                "product_name": "Windbreaker Jacket",
                "units": 144,
                "net_sales": 178841.14,
                "orders": 127,
            }
        ],
    )
    comparison = VisualizationDataset(
        id="c1:comparison",
        source_call_id="c1",
        view="comparison",
        rows=[
            {
                "period_label": "2026-01-01 – 2026-03-31",
                "units": 144,
                "net_sales": 178841.14,
                "orders": 127,
            },
            {
                "period_label": "2025-10-03 – 2025-12-31",
                "units": 211,
                "net_sales": 258528.79,
                "orders": 175,
            },
        ],
    )

    plan = build_visualization_plan(request, [current, comparison], "sv")
    spec = plan.visualizations[0]

    assert spec.type == "bar_chart"
    assert spec.y_keys == ["net_sales"]
    assert "Windbreaker Jacket" in spec.title
    assert "Vindjacka" not in spec.title


def test_ranking_is_bar_chart_by_default():
    request = AnalysisRequestState(
        operation="ranking",
        metrics=["net_sales"],
        group_by="product",
        rank_by="net_sales",
        rank_order="highest",
        limit=5,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 3, 31),
    )
    dataset = VisualizationDataset(
        id="c1:ranking",
        source_call_id="c1",
        view="ranking",
        rows=[
            {"entity_name": "A", "net_sales": 100.0},
            {"entity_name": "B", "net_sales": 90.0},
        ],
    )

    plan = build_visualization_plan(request, [dataset], "sv")
    assert plan.visualizations[0].type == "bar_chart"



def test_trend_title_includes_online_scope():
    request = AnalysisRequestState(
        operation="trend",
        metrics=["units", "net_sales"],
        grain="month",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 12, 31),
        scope=AnalysisScope(channels=["online"]),
    )
    dataset = VisualizationDataset(
        id="c1:trend",
        source_call_id="c1",
        view="trend",
        rows=[
            {"period_label": "2026-01", "units": 100, "net_sales": 50000.0},
            {"period_label": "2026-02", "units": 110, "net_sales": 52000.0},
        ],
    )

    spec = build_visualization_plan(
        request,
        [dataset],
        "sv",
    ).visualizations[0]

    assert spec.title == "Utveckling – Online – 2026"


def test_trend_title_includes_physical_scope():
    request = AnalysisRequestState(
        operation="trend",
        metrics=["units", "net_sales"],
        grain="month",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 12, 31),
        scope=AnalysisScope(channels=["physical"]),
    )
    dataset = VisualizationDataset(
        id="c1:trend",
        source_call_id="c1",
        view="trend",
        rows=[
            {"period_label": "2026-01", "units": 100, "net_sales": 50000.0},
            {"period_label": "2026-02", "units": 110, "net_sales": 52000.0},
        ],
    )

    spec = build_visualization_plan(
        request,
        [dataset],
        "sv",
    ).visualizations[0]

    assert spec.title == (
        "Utveckling – Fysiska butiker – 2026"
    )


def test_single_metric_sales_trend_still_exposes_other_dataset_metrics():
    request = AnalysisRequestState(
        operation="trend",
        metrics=["net_sales"],
        grain="month",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 3, 31),
    )
    dataset = VisualizationDataset(
        id="c1:trend",
        source_call_id="c1",
        view="trend",
        rows=[
            {
                "period_label": "2026-01",
                "units": 100,
                "net_sales": 50000.0,
                "gross_sales": 52000.0,
                "orders": 80,
            },
            {
                "period_label": "2026-02",
                "units": 110,
                "net_sales": 53000.0,
                "gross_sales": 54500.0,
                "orders": 84,
            },
        ],
    )

    spec = build_visualization_plan(
        request,
        [dataset],
        "sv",
    ).visualizations[0]

    assert spec.type == "line_chart"
    assert spec.y_keys == ["net_sales"]
    assert spec.selectable_y_keys == [
        "net_sales",
        "gross_sales",
        "units",
        "orders",
    ]
    assert spec.title == "Utveckling – 2026-01-01–2026-03-31"



def test_one_point_trend_never_renders_as_line_chart():
    request = AnalysisRequestState(
        operation="trend",
        metrics=["net_sales"],
        grain="quarter",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 3, 31),
        entity=CanonicalProduct(
            id="AURA-JKT-025",
            name="Windbreaker Jacket",
        ),
    )
    dataset = VisualizationDataset(
        id="c1:trend",
        source_call_id="c1",
        view="trend",
        rows=[
            {
                "period_label": "2026-Q1",
                "net_sales": 178841.14,
            }
        ],
    )

    plan = build_visualization_plan(
        request,
        [dataset],
        "sv",
    )

    assert len(plan.visualizations) == 1
    assert plan.visualizations[0].type == "metric_cards"


def test_explicit_chart_does_not_fabricate_one_point_line():
    request = AnalysisRequestState(
        operation="trend",
        metrics=["net_sales"],
        grain="quarter",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 3, 31),
        presentation="chart",
        entity=CanonicalProduct(
            id="AURA-JKT-025",
            name="Windbreaker Jacket",
        ),
    )
    dataset = VisualizationDataset(
        id="c1:trend",
        source_call_id="c1",
        view="trend",
        rows=[
            {
                "period_label": "2026-Q1",
                "net_sales": 178841.14,
            }
        ],
    )

    plan = build_visualization_plan(
        request,
        [dataset],
        "sv",
    )

    assert plan.visualizations == []


def test_product_overview_chart_falls_back_from_one_point_trend_to_comparison():
    request = AnalysisRequestState(
        operation="product_overview",
        metrics=["units", "net_sales", "orders", "average_selling_price"],
        period_start=date(2026, 1, 1),
        period_end=date(2026, 3, 31),
        presentation="chart",
        entity=CanonicalProduct(
            id="AURA-JKT-025",
            name="Windbreaker Jacket",
        ),
    )
    trend = VisualizationDataset(
        id="c1:trend",
        source_call_id="c1",
        view="trend",
        rows=[
            {
                "period_label": "2026-Q1",
                "net_sales": 178841.14,
            }
        ],
    )
    comparison = VisualizationDataset(
        id="c1:comparison",
        source_call_id="c1",
        view="comparison",
        rows=[
            {
                "period_label": "2026-01-01 – 2026-03-31",
                "net_sales": 178841.14,
            },
            {
                "period_label": "2025-10-03 – 2025-12-31",
                "net_sales": 258528.79,
            },
        ],
    )

    plan = build_visualization_plan(
        request,
        [trend, comparison],
        "sv",
    )

    assert len(plan.visualizations) == 1
    assert plan.visualizations[0].type == "bar_chart"
    assert plan.visualizations[0].x_key == "period_label"
    assert "Windbreaker Jacket" in plan.visualizations[0].title

def test_product_overview_trend_exposes_local_metric_selector():
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
        presentation="chart",
        entity=CanonicalProduct(
            id="AURA-JKT-025",
            name="Windbreaker Jacket",
        ),
    )
    trend = VisualizationDataset(
        id="c1:trend",
        source_call_id="c1",
        view="trend",
        rows=[
            {
                "period_label": "2026-01",
                "units": 53,
                "net_sales": 63207.28,
                "gross_sales": 68928.26,
                "discounts": 5720.98,
                "orders": 45,
                "average_selling_price": 1192.59,
                "discount_rate": 0.083,
            },
            {
                "period_label": "2026-02",
                "units": 42,
                "net_sales": 54129.64,
                "gross_sales": 54782.72,
                "discounts": 653.08,
                "orders": 36,
                "average_selling_price": 1288.80,
                "discount_rate": 0.0119,
            },
            {
                "period_label": "2026-03",
                "units": 49,
                "net_sales": 61504.22,
                "gross_sales": 63808.35,
                "discounts": 2304.13,
                "orders": 46,
                "average_selling_price": 1255.19,
                "discount_rate": 0.0361,
            },
        ],
    )

    spec = build_visualization_plan(
        request,
        [trend],
        "sv",
    ).visualizations[0]

    assert spec.type == "line_chart"
    assert spec.y_keys == ["net_sales"]
    assert spec.selectable_y_keys == [
        "net_sales",
        "gross_sales",
        "units",
        "orders",
        "discounts",
        "average_selling_price",
        "discount_rate",
    ]
    assert spec.title == (
        "Utveckling för Windbreaker Jacket – Q1 2026"
    )

