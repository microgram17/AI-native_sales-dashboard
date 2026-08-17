from __future__ import annotations

from app.agents.nodes.normalize_visualizations import (
    normalize_visualization_datasets,
)
from app.agents.nodes.validate_visualizations import (
    validate_visualization_plan,
)
from app.agents.state import ExecutedToolCall
from app.schemas.visualization import (
    VisualizationDataset,
    VisualizationPlan,
    VisualizationSpec,
)


def _call(
    tool_name: str,
    call_id: str,
    result: dict,
) -> ExecutedToolCall:
    return ExecutedToolCall(
        call_id=call_id,
        tool_name=tool_name,
        status="success",
        result=result,
    )


def _trend_dataset() -> VisualizationDataset:
    return VisualizationDataset(
        id="t1:trend",
        source_call_id="t1",
        view="trend",
        rows=[
            {
                "period_label": "2026-01",
                "units": 1114,
                "orders": 844,
                "net_sales": 577975.25,
                "gross_sales": 630535.60,
                "discount_rate": 0.0834,
            },
            {
                "period_label": "2026-02",
                "units": 923,
                "orders": 698,
                "net_sales": 534170.10,
                "gross_sales": 544169.03,
                "discount_rate": 0.0184,
            },
        ],
    )


def test_sales_summary_normalizes_current_and_comparison():
    result = {
        "status": "success",
        "effective_period": {
            "label": "2026-01-01 – 2026-06-30"
        },
        "previous_period": {
            "label": "2025-07-04 – 2025-12-31"
        },
        "current": {
            "units": 6561,
            "net_sales": 2738315.55,
        },
        "previous": {
            "units": 7310,
            "net_sales": 3127082.99,
        },
    }

    datasets = normalize_visualization_datasets(
        [_call("sales_summary", "s1", result)]
    )
    by_id = {
        dataset.id: dataset
        for dataset in datasets
    }

    assert (
        by_id["s1:current"].rows[0]["units"]
        == 6561
    )
    assert by_id["s1:comparison"].rows == [
        {
            "period": "Current",
            "period_label": (
                "2026-01-01 – 2026-06-30"
            ),
            "units": 6561,
            "net_sales": 2738315.55,
        },
        {
            "period": "Previous",
            "period_label": (
                "2025-07-04 – 2025-12-31"
            ),
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
                "entity": {
                    "type": "product",
                    "id": "P1",
                    "name": "Cardigan",
                },
                "metrics": {
                    "units": 170,
                    "net_sales": 154532.99,
                },
                "share_of_rank_metric": 0.1,
            }
        ],
    }

    datasets = normalize_visualization_datasets(
        [_call("sales_rank", "r1", result)]
    )
    row = datasets[0].rows[0]

    assert datasets[0].id == "r1:ranking"
    assert row["entity_name"] == "Cardigan"
    assert row["units"] == 170
    assert row["net_sales"] == 154532.99


def test_product_overview_creates_separate_views():
    result = {
        "status": "success",
        "product": {
            "type": "product",
            "id": "P1",
            "name": "Oxford",
        },
        "effective_period": {
            "label": "Q1"
        },
        "previous_period": {
            "label": "Previous"
        },
        "current": {
            "units": 62,
            "net_sales": 19322.44,
        },
        "previous": {
            "units": 79,
            "net_sales": 24337.85,
        },
        "trend": [
            {
                "period_start": "2026-01-01",
                "period_label": "2026-01",
                "series_entity": None,
                "metrics": {
                    "units": 17,
                    "net_sales": 5049.11,
                },
            }
        ],
        "channel_breakdown": [
            {
                "entity": {
                    "type": "channel",
                    "id": None,
                    "name": "physical",
                },
                "metrics": {
                    "units": 54,
                    "net_sales": 16636.28,
                },
                "share_of_net_sales": 0.861,
            }
        ],
        "city_breakdown": [
            {
                "entity": {
                    "type": "city",
                    "id": None,
                    "name": "Stockholm",
                },
                "metrics": {
                    "units": 23,
                    "net_sales": 6888.48,
                },
                "share_of_net_sales": 0.3565,
            }
        ],
    }

    datasets = normalize_visualization_datasets(
        [_call("product_overview", "p1", result)]
    )
    ids = {
        dataset.id
        for dataset in datasets
    }

    assert {
        "p1:current",
        "p1:comparison",
        "p1:trend",
        "p1:channel_breakdown",
        "p1:city_breakdown",
    } <= ids


def test_validator_drops_missing_fields_and_mixed_unit_bar_chart():
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
                            "entity": {
                                "type": "product",
                                "id": "P1",
                                "name": "A",
                            },
                            "metrics": {
                                "units": 10,
                                "net_sales": 1000.0,
                            },
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
                y_keys=[
                    "units",
                    "net_sales",
                ],
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

    validated = validate_visualization_plan(
        plan,
        datasets,
    )

    assert [
        spec.title
        for spec in validated.visualizations
    ] == ["Valid"]


def test_validator_normalizes_two_family_line_chart_to_dual_axis():
    plan = VisualizationPlan(
        visualizations=[
            VisualizationSpec(
                dataset="t1:trend",
                type="line_chart",
                title="Monthly units and net sales",
                x_key="period_label",
                y_keys=[
                    "units",
                    "net_sales",
                ],
                # Even if the LLM omits or misstates this, the validator owns
                # the final deterministic axis assignment.
                secondary_y_keys=[],
            )
        ]
    )

    validated = validate_visualization_plan(
        plan,
        [_trend_dataset()],
    )

    assert len(validated.visualizations) == 1
    spec = validated.visualizations[0]
    assert spec.y_keys == [
        "units",
        "net_sales",
    ]
    assert spec.secondary_y_keys == [
        "net_sales"
    ]


def test_validator_preserves_same_family_line_chart_on_one_axis():
    plan = VisualizationPlan(
        visualizations=[
            VisualizationSpec(
                dataset="t1:trend",
                type="line_chart",
                title="Monthly sales",
                x_key="period_label",
                y_keys=[
                    "net_sales",
                    "gross_sales",
                ],
                secondary_y_keys=[
                    "gross_sales"
                ],
            )
        ]
    )

    validated = validate_visualization_plan(
        plan,
        [_trend_dataset()],
    )

    assert len(validated.visualizations) == 1
    assert (
        validated.visualizations[0].secondary_y_keys
        == []
    )


def test_validator_rejects_three_metric_families_on_one_line_chart():
    plan = VisualizationPlan(
        visualizations=[
            VisualizationSpec(
                dataset="t1:trend",
                type="line_chart",
                title="Too many axes",
                x_key="period_label",
                y_keys=[
                    "units",
                    "net_sales",
                    "discount_rate",
                ],
            )
        ]
    )

    validated = validate_visualization_plan(
        plan,
        [_trend_dataset()],
    )

    assert validated.visualizations == []


def test_validator_rejects_split_series_with_multiple_metric_columns():
    split = VisualizationDataset(
        id="t2:trend",
        source_call_id="t2",
        view="trend",
        rows=[
            {
                "period_label": "2026-01",
                "series_name": "A",
                "units": 10,
                "net_sales": 1000.0,
            },
            {
                "period_label": "2026-01",
                "series_name": "B",
                "units": 12,
                "net_sales": 1200.0,
            },
        ],
    )

    plan = VisualizationPlan(
        visualizations=[
            VisualizationSpec(
                dataset="t2:trend",
                type="line_chart",
                title="Ambiguous split",
                x_key="period_label",
                y_keys=[
                    "units",
                    "net_sales",
                ],
                series_key="series_name",
            )
        ]
    )

    validated = validate_visualization_plan(
        plan,
        [split],
    )

    assert validated.visualizations == []
