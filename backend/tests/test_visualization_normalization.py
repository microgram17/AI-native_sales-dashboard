from __future__ import annotations

from app.agents.nodes.normalize_visualizations import normalize_visualization_datasets
from app.agents.nodes.validate_visualizations import validate_visualization_plan
from app.agents.state import ExecutedToolCall
from app.schemas.visualization import VisualizationPlan, VisualizationSpec


def _call(tool_name: str, call_id: str, result: dict) -> ExecutedToolCall:
    return ExecutedToolCall(
        call_id=call_id,
        tool_name=tool_name,
        status="success",
        result=result,
    )


def test_sales_summary_normalizes_current_and_comparison():
    result = {
        "status": "success",
        "effective_period": {"label": "2026-01-01 – 2026-06-30"},
        "previous_period": {"label": "2025-07-04 – 2025-12-31"},
        "current": {"units": 6561, "net_sales": 2738315.55},
        "previous": {"units": 7310, "net_sales": 3127082.99},
    }
    datasets = normalize_visualization_datasets([_call("sales_summary", "s1", result)])
    by_id = {d.id: d for d in datasets}

    assert by_id["s1:current"].rows[0]["units"] == 6561
    assert by_id["s1:comparison"].rows == [
        {
            "period": "Current",
            "period_label": "2026-01-01 – 2026-06-30",
            "units": 6561,
            "net_sales": 2738315.55,
        },
        {
            "period": "Previous",
            "period_label": "2025-07-04 – 2025-12-31",
            "units": 7310,
            "net_sales": 3127082.99,
        },
    ]


def test_sales_rank_flattens_entity_and_metrics():
    result = {
        "status": "success",
        "rows": [
            {
                "rank": 1,
                "entity": {"type": "product", "id": "P1", "name": "Cardigan"},
                "metrics": {"units": 170, "net_sales": 154532.99},
                "share_of_rank_metric": 0.1,
            }
        ],
    }
    datasets = normalize_visualization_datasets([_call("sales_rank", "r1", result)])
    row = datasets[0].rows[0]

    assert datasets[0].id == "r1:ranking"
    assert row["entity_name"] == "Cardigan"
    assert row["units"] == 170
    assert row["net_sales"] == 154532.99


def test_product_overview_creates_separate_views():
    result = {
        "status": "success",
        "product": {"type": "product", "id": "P1", "name": "Oxford"},
        "effective_period": {"label": "Q1"},
        "previous_period": {"label": "Previous"},
        "current": {"units": 62, "net_sales": 19322.44},
        "previous": {"units": 79, "net_sales": 24337.85},
        "trend": [
            {
                "period_start": "2026-01-01",
                "period_label": "2026-01",
                "series_entity": None,
                "metrics": {"units": 17, "net_sales": 5049.11},
            }
        ],
        "channel_breakdown": [
            {
                "entity": {"type": "channel", "id": None, "name": "physical"},
                "metrics": {"units": 54, "net_sales": 16636.28},
                "share_of_net_sales": 0.861,
            }
        ],
        "city_breakdown": [
            {
                "entity": {"type": "city", "id": None, "name": "Stockholm"},
                "metrics": {"units": 23, "net_sales": 6888.48},
                "share_of_net_sales": 0.3565,
            }
        ],
    }
    datasets = normalize_visualization_datasets([_call("product_overview", "p1", result)])
    ids = {d.id for d in datasets}

    assert {
        "p1:current",
        "p1:comparison",
        "p1:trend",
        "p1:channel_breakdown",
        "p1:city_breakdown",
    } <= ids


def test_validator_drops_missing_fields_and_mixed_units():
    datasets = normalize_visualization_datasets(
        [
            _call(
                "sales_rank",
                "r1",
                {
                    "status": "success",
                    "rows": [
                        {
                            "rank": 1,
                            "entity": {"type": "product", "id": "P1", "name": "A"},
                            "metrics": {"units": 10, "net_sales": 1000.0},
                        }
                    ],
                },
            )
        ]
    )

    plan = VisualizationPlan(
        visualizations=[
            VisualizationSpec(
                dataset="r1:ranking",
                type="bar_chart",
                title="Missing x",
                x_key="missing",
                y_keys=["units"],
            ),
            VisualizationSpec(
                dataset="r1:ranking",
                type="bar_chart",
                title="Mixed units",
                x_key="entity_name",
                y_keys=["units", "net_sales"],
            ),
            VisualizationSpec(
                dataset="r1:ranking",
                type="bar_chart",
                title="Valid",
                x_key="entity_name",
                y_keys=["net_sales"],
            ),
        ]
    )

    validated = validate_visualization_plan(plan, datasets)
    assert [spec.title for spec in validated.visualizations] == ["Valid"]
