"""Convert internal analytics models to the public semantic DataView contract."""

from __future__ import annotations

from typing import Any

from app.contracts.sales import (
    AnalyticsContext,
    AnalyticsResult,
    DataField,
    DataView,
    MetricSnapshot,
    ProductOverviewResult,
    RankedRow,
    SalesRankingResult,
    SalesScope,
    SalesSummaryResult,
    SalesTrendResult,
    TrendRow,
)


_METRICS = (
    "units",
    "net_sales",
    "gross_sales",
    "discounts",
    "orders",
    "average_selling_price",
    "discount_rate",
)

_FORMATS = {
    "period_start": "date",
    "rank": "integer",
    "units": "integer",
    "orders": "integer",
    "net_sales": "currency_sek",
    "gross_sales": "currency_sek",
    "discounts": "currency_sek",
    "average_selling_price": "currency_sek",
    "discount_rate": "percentage_fraction",
    "share_of_rank_metric": "percentage_fraction",
    "share_of_net_sales": "percentage_fraction",
    "share_of_supplier_units": "percentage_fraction",
    "share_of_supplier_net_sales": "percentage_fraction",
}


def _field(key: str, role: str) -> DataField:
    return DataField(
        key=key,
        role=role,
        format=_FORMATS.get(key, "decimal" if role == "measure" else "text"),
    )


def _fields(
    rows: list[dict[str, Any]],
    *,
    dimensions: tuple[str, ...],
    measures: tuple[str, ...],
) -> list[DataField]:
    present = {
        key
        for row in rows
        for key, value in row.items()
        if value is not None
    }
    return [
        *[_field(key, "dimension") for key in dimensions if key in present],
        *[_field(key, "measure") for key in measures if key in present],
    ]


def _metrics(snapshot: MetricSnapshot | None) -> dict[str, Any]:
    return snapshot.model_dump(mode="json") if snapshot is not None else {}


def _available_measures(rows: list[dict[str, Any]]) -> list[str]:
    return [
        metric
        for metric in _METRICS
        if any(row.get(metric) is not None for row in rows)
    ]


def _metrics_view(
    *,
    view_id: str,
    rows: list[dict[str, Any]],
    default_visible: bool = True,
) -> DataView | None:
    if not rows:
        return None
    measures = _available_measures(rows)
    extra_measures = (
        "rank_by_units",
        "rank_by_net_sales",
        "share_of_supplier_units",
        "share_of_supplier_net_sales",
    )
    return DataView(
        id=view_id,
        kind="metrics",
        rows=rows,
        fields=_fields(
            rows,
            dimensions=("product_id", "product_name", "period_label"),
            measures=(*_METRICS, *extra_measures),
        ),
        default_measures=measures,
        default_visible=default_visible,
    )


def _comparison_view(
    result: SalesSummaryResult | ProductOverviewResult,
    *,
    product_id: str | None = None,
    product_name: str | None = None,
) -> DataView | None:
    if result.current is None or result.previous is None:
        return None
    identity = {
        "product_id": product_id,
        "product_name": product_name,
    } if product_id or product_name else {}
    rows = [
        {
            "period": "current",
            "period_label": result.effective_period.label,
            **identity,
            **_metrics(result.current),
        },
        {
            "period": "previous",
            "period_label": result.previous_period.label if result.previous_period else None,
            **identity,
            **_metrics(result.previous),
        },
    ]
    measures = _available_measures(rows)
    return DataView(
        id="comparison",
        kind="categorical",
        rows=rows,
        fields=_fields(
            rows,
            dimensions=("period", "period_label", "product_id", "product_name"),
            measures=_METRICS,
        ),
        primary_dimension="period_label",
        default_measures=measures[:1],
        default_visible=False,
    )


def _trend_rows(rows: list[TrendRow]) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for row in rows:
        item: dict[str, Any] = {
            "period_start": row.period_start.isoformat(),
            "period_label": row.period_label,
            **_metrics(row.metrics),
        }
        if row.series_entity is not None:
            item.update(
                {
                    "series_id": row.series_entity.id,
                    "series_name": row.series_entity.name,
                    "series_type": row.series_entity.type,
                }
            )
        flattened.append(item)
    return flattened


def _trend_view(rows: list[TrendRow], *, default_visible: bool = True) -> DataView | None:
    flat = _trend_rows(rows)
    if not flat:
        return None
    measures = _available_measures(flat)
    has_series = any(row.get("series_name") for row in flat)
    return DataView(
        id="trend",
        kind="timeseries",
        rows=flat,
        fields=_fields(
            flat,
            dimensions=(
                "period_start",
                "period_label",
                "series_id",
                "series_name",
                "series_type",
            ),
            measures=_METRICS,
        ),
        primary_dimension="period_label",
        series_dimension="series_name" if has_series else None,
        default_measures=measures[:1],
        default_visible=default_visible,
    )


def summary_to_analytics(result: SalesSummaryResult) -> AnalyticsResult:
    views: list[DataView] = []
    if result.current is not None:
        view = _metrics_view(
            view_id="current",
            rows=[
                {
                    "period_label": result.effective_period.label,
                    **_metrics(result.current),
                }
            ],
        )
        if view is not None:
            views.append(view)
    comparison = _comparison_view(result)
    if comparison is not None:
        views.append(comparison)
    return AnalyticsResult(
        status=result.status,
        context=AnalyticsContext(
            operation="summary",
            effective_period=result.effective_period,
            effective_scope=result.effective_scope,
        ),
        warnings=result.warnings,
        views=views,
    )


def _rank_row(row: RankedRow) -> dict[str, Any]:
    return {
        "rank": row.rank,
        "entity_id": row.entity.id,
        "entity_name": row.entity.name,
        "entity_type": row.entity.type,
        **_metrics(row.metrics),
        "share_of_rank_metric": row.share_of_rank_metric,
        "previous_rank_metric_value": row.previous_rank_metric_value,
        "rank_metric_absolute_change": row.rank_metric_absolute_change,
        "rank_metric_percent_change": row.rank_metric_percent_change,
    }


def ranking_to_analytics(result: SalesRankingResult) -> AnalyticsResult:
    rows = [_rank_row(row) for row in result.rows]
    views = []
    if rows:
        is_single_result = len(rows) == 1
        supporting = (
            "share_of_rank_metric",
            "previous_rank_metric_value",
            "rank_metric_absolute_change",
            "rank_metric_percent_change",
        )
        views.append(
            DataView(
                id="ranking",
                # A one-row ranking is a result metric, not a meaningful
                # categorical comparison. Multi-row rankings remain bars.
                kind="metrics" if is_single_result else "categorical",
                rows=rows,
                fields=_fields(
                    rows,
                    dimensions=("rank", "entity_id", "entity_name", "entity_type"),
                    measures=(*_METRICS, *supporting),
                ),
                primary_dimension="entity_name",
                default_measures=(
                    _available_measures(rows)
                    if is_single_result
                    else [result.rank_by]
                ),
            )
        )
    return AnalyticsResult(
        status=result.status,
        context=AnalyticsContext(
            operation="ranking",
            effective_period=result.effective_period,
            effective_scope=result.effective_scope,
            group_by=result.group_by,
            rank_by=result.rank_by,
            order=result.order,
        ),
        warnings=result.warnings,
        views=views,
    )


def trend_to_analytics(result: SalesTrendResult) -> AnalyticsResult:
    trend = _trend_view(result.rows)
    return AnalyticsResult(
        status=result.status,
        context=AnalyticsContext(
            operation="trend",
            effective_period=result.effective_period,
            effective_scope=result.effective_scope,
            grain=result.grain,
            split_by=result.split_by,
        ),
        warnings=result.warnings,
        views=[trend] if trend is not None else [],
    )


def _breakdown_view(view_id: str, rows: list[Any]) -> DataView | None:
    flat = [
        {
            "entity_id": row.entity.id,
            "entity_name": row.entity.name,
            "entity_type": row.entity.type,
            **_metrics(row.metrics),
            "share_of_net_sales": row.share_of_net_sales,
        }
        for row in rows
    ]
    if not flat:
        return None
    return DataView(
        id=view_id,
        kind="categorical",
        rows=flat,
        fields=_fields(
            flat,
            dimensions=("entity_id", "entity_name", "entity_type"),
            measures=(*_METRICS, "share_of_net_sales"),
        ),
        primary_dimension="entity_name",
        default_measures=["net_sales"],
        default_visible=False,
    )


def overview_to_analytics(result: ProductOverviewResult) -> AnalyticsResult:
    scope = SalesScope(
        channels=result.effective_scope.channels,
        cities=result.effective_scope.cities,
        store_ids=result.effective_scope.store_ids,
        product_ids=[result.product.id] if result.product and result.product.id else [],
    )
    views: list[DataView] = []
    if result.current is not None:
        view = _metrics_view(
            view_id="current",
            rows=[
                {
                    "period_label": result.effective_period.label,
                    "product_id": result.product.id if result.product else None,
                    "product_name": result.product.name if result.product else None,
                    **_metrics(result.current),
                    "rank_by_units": result.rank_by_units,
                    "rank_by_net_sales": result.rank_by_net_sales,
                    "share_of_supplier_units": result.share_of_supplier_units,
                    "share_of_supplier_net_sales": result.share_of_supplier_net_sales,
                }
            ],
        )
        if view is not None:
            views.append(view)
    comparison = _comparison_view(
        result,
        product_id=result.product.id if result.product else None,
        product_name=result.product.name if result.product else None,
    )
    trend = _trend_view(result.trend, default_visible=False)
    channel = _breakdown_view("channel_breakdown", result.channel_breakdown)
    city = _breakdown_view("city_breakdown", result.city_breakdown)
    views.extend(view for view in (comparison, trend, channel, city) if view is not None)
    return AnalyticsResult(
        status=result.status,
        context=AnalyticsContext(
            operation="product_overview",
            effective_period=result.effective_period,
            effective_scope=scope,
            grain="month" if result.trend else None,
            entity=result.product,
        ),
        warnings=result.warnings,
        candidates=result.candidates,
        views=views,
    )
