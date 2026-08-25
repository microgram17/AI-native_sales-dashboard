from datetime import date

from app.contracts.sales import (
    AnalyticsEntity,
    EffectivePeriod,
    MetricSnapshot,
    RankedRow,
    SalesRankingResult,
    SalesScope,
    SalesSummaryResult,
    SalesTrendResult,
    TrendRow,
)
from app.contracts.views import (
    ranking_to_analytics,
    summary_to_analytics,
    trend_to_analytics,
)


PERIOD = EffectivePeriod(
    start=date(2026, 1, 1),
    end=date(2026, 3, 31),
    label="Q1 2026",
)
METRICS = MetricSnapshot(
    units=10,
    net_sales=1250.0,
    gross_sales=1300.0,
    discounts=50.0,
    orders=8,
    average_selling_price=125.0,
    discount_rate=0.03846,
)


def test_summary_becomes_metrics_view_without_nested_metrics() -> None:
    result = summary_to_analytics(
        SalesSummaryResult(
            status="success",
            effective_period=PERIOD,
            effective_scope=SalesScope(),
            current=METRICS,
        )
    )
    assert result.context.operation == "summary"
    assert result.views[0].kind == "metrics"
    assert result.views[0].rows[0]["net_sales"] == 1250.0
    assert all(not isinstance(value, dict) for value in result.views[0].rows[0].values())


def test_single_item_ranking_becomes_metrics_view() -> None:
    result = ranking_to_analytics(
        SalesRankingResult(
            status="success",
            group_by="product",
            rank_by="units",
            effective_period=PERIOD,
            effective_scope=SalesScope(),
            rows=[
                RankedRow(
                    rank=1,
                    entity=AnalyticsEntity(type="product", id="P1", name="Hoodie"),
                    metrics=METRICS,
                )
            ],
        )
    )
    view = result.views[0]
    assert view.kind == "metrics"
    assert view.primary_dimension == "entity_name"
    assert view.default_measures == [
        "units",
        "net_sales",
        "gross_sales",
        "discounts",
        "orders",
        "average_selling_price",
        "discount_rate",
    ]


def test_multi_item_ranking_remains_categorical() -> None:
    result = ranking_to_analytics(
        SalesRankingResult(
            status="success",
            group_by="product",
            rank_by="units",
            effective_period=PERIOD,
            effective_scope=SalesScope(),
            rows=[
                RankedRow(
                    rank=1,
                    entity=AnalyticsEntity(type="product", id="P1", name="Hoodie"),
                    metrics=METRICS,
                ),
                RankedRow(
                    rank=2,
                    entity=AnalyticsEntity(type="product", id="P2", name="Tee"),
                    metrics=METRICS.model_copy(update={"units": 8}),
                ),
            ],
        )
    )
    view = result.views[0]
    assert view.kind == "categorical"
    assert view.primary_dimension == "entity_name"
    assert view.default_measures == ["units"]


def test_trend_declares_metadata_driven_formats() -> None:
    result = trend_to_analytics(
        SalesTrendResult(
            status="success",
            grain="month",
            effective_period=PERIOD,
            effective_scope=SalesScope(),
            rows=[
                TrendRow(
                    period_start=date(2026, 1, 1),
                    period_label="2026-01",
                    metrics=METRICS,
                )
            ],
        )
    )
    view = result.views[0]
    formats = {field.key: field.format for field in view.fields}
    assert view.kind == "timeseries"
    assert formats["net_sales"] == "currency_sek"
    assert formats["discount_rate"] == "percentage_fraction"
