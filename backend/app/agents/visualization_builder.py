
"""Deterministic visualization selection for the constrained BI result shapes."""

from __future__ import annotations

import calendar
from datetime import date

from app.schemas.agent import AnalysisRequestState
from app.schemas.visualization import (
    VisualizationDataset,
    VisualizationPlan,
    VisualizationSpec,
)


_METRIC_LABELS = {
    "en": {
        "units": "Units sold",
        "net_sales": "Net sales",
        "gross_sales": "Gross sales",
        "discounts": "Discounts",
        "orders": "Orders",
        "average_selling_price": "Average selling price",
        "discount_rate": "Discount rate",
    },
    "sv": {
        "units": "Sålda enheter",
        "net_sales": "Nettoomsättning",
        "gross_sales": "Bruttoomsättning",
        "discounts": "Rabatter",
        "orders": "Beställningar",
        "average_selling_price": "Genomsnittligt försäljningspris",
        "discount_rate": "Rabattgrad",
    },
}

_GROUP_LABELS = {
    "en": {
        "product": "products",
        "category": "categories",
        "store": "stores",
        "city": "cities",
        "channel": "channels",
    },
    "sv": {
        "product": "produkter",
        "category": "kategorier",
        "store": "butiker",
        "city": "städer",
        "channel": "kanaler",
    },
}
_GROUP_SINGULAR = {
    "en": {
        "product": "Product",
        "category": "Category",
        "store": "Store",
        "city": "City",
        "channel": "Channel",
    },
    "sv": {
        "product": "Produkt",
        "category": "Kategori",
        "store": "Butik",
        "city": "Stad",
        "channel": "Kanal",
    },
}


_SELECTABLE_TREND_METRICS = (
    "net_sales",
    "gross_sales",
    "units",
    "orders",
    "discounts",
    "average_selling_price",
    "discount_rate",
)



def _metric_family(key: str) -> str:
    lowered = key.casefold()
    if any(
        token in lowered
        for token in ("rate", "share", "percent")
    ):
        return "rate"
    if any(
        token in lowered
        for token in (
            "sales",
            "revenue",
            "discount",
            "price",
            "cost",
            "sek",
        )
    ):
        return "currency"
    if any(
        token in lowered
        for token in (
            "units",
            "orders",
            "count",
            "quantity",
            "rank",
        )
    ):
        return "count"
    return "number"


def _numeric_field(
    dataset: VisualizationDataset,
    key: str,
) -> bool:
    values = [
        row.get(key)
        for row in dataset.rows
        if row.get(key) is not None
    ]
    return bool(values) and all(
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        for value in values
    )


def _field_exists(
    dataset: VisualizationDataset,
    key: str,
) -> bool:
    return any(
        key in row and row[key] is not None
        for row in dataset.rows
    )


def _find(
    datasets: list[VisualizationDataset],
    view: str,
) -> VisualizationDataset | None:
    return next(
        (
            dataset
            for dataset in datasets
            if dataset.view == view
        ),
        None,
    )


def _period_title(
    request: AnalysisRequestState,
) -> str:
    start = request.period_start
    end = request.period_end
    if start is None or end is None:
        return ""

    if (
        start == date(start.year, 1, 1)
        and end == date(start.year, 12, 31)
    ):
        return str(start.year)

    if start.year == end.year:
        for quarter in range(1, 5):
            start_month = (quarter - 1) * 3 + 1
            end_month = start_month + 2
            q_start = date(
                start.year,
                start_month,
                1,
            )
            q_end = date(
                start.year,
                end_month,
                calendar.monthrange(
                    start.year,
                    end_month,
                )[1],
            )
            if start == q_start and end == q_end:
                return f"Q{quarter} {start.year}"

    return (
        f"{start.isoformat()}–{end.isoformat()}"
    )


def _metric_label(
    language: str,
    metric: str,
) -> str:
    lang = "sv" if language == "sv" else "en"
    return _METRIC_LABELS[lang].get(
        metric,
        metric.replace("_", " ").capitalize(),
    )


def _metric_phrase(
    language: str,
    metrics: list[str],
) -> str:
    if not metrics:
        return (
            "Försäljning"
            if language == "sv"
            else "Sales"
        )

    labels = [
        _metric_label(language, metric)
        for metric in metrics
    ]
    if len(labels) == 1:
        return labels[0]

    # Standalone labels are title-cased for cards/axes. In a combined title,
    # only the first metric should retain the initial capital.
    normalized = [
        labels[0],
        *[label[:1].lower() + label[1:] for label in labels[1:]],
    ]

    if len(normalized) == 2:
        joiner = " och " if language == "sv" else " and "
        return joiner.join(normalized)

    return ", ".join(normalized[:-1]) + (
        f" och {normalized[-1]}"
        if language == "sv"
        else f", and {normalized[-1]}"
    )


def _entity_suffix(
    request: AnalysisRequestState,
) -> str:
    return (
        request.entity.name
        if request.entity is not None
        else ""
    )


def _join_human(
    values: list[str],
    language: str,
) -> str:
    cleaned = [
        value.strip()
        for value in values
        if value and value.strip()
    ]
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]
    if len(cleaned) == 2:
        joiner = " och " if language == "sv" else " and "
        return joiner.join(cleaned)
    return ", ".join(cleaned[:-1]) + (
        f" och {cleaned[-1]}"
        if language == "sv"
        else f", and {cleaned[-1]}"
    )


def _scope_title_parts(
    request: AnalysisRequestState,
    language: str,
) -> list[str]:
    """Human-readable active scope for deterministic visualization titles."""
    scope = request.scope
    parts: list[str] = []

    channels = list(scope.channels)
    if channels:
        channel_set = set(channels)
        if channel_set == {"online"}:
            parts.append("Online")
        elif channel_set == {"physical"}:
            parts.append(
                "Fysiska butiker"
                if language == "sv"
                else "Physical stores"
            )
        elif channel_set == {"online", "physical"}:
            parts.append(
                "Alla kanaler"
                if language == "sv"
                else "All channels"
            )
        else:
            parts.append(
                _join_human(channels, language)
            )

    if scope.cities:
        parts.append(
            _join_human(
                list(scope.cities),
                language,
            )
        )

    if scope.categories:
        category_names = _join_human(
            list(scope.categories),
            language,
        )
        parts.append(
            f"Kategori: {category_names}"
            if language == "sv"
            else f"Category: {category_names}"
        )

    if scope.store_ids:
        parts.append(
            (
                "Vald butik"
                if len(scope.store_ids) == 1
                else "Valda butiker"
            )
            if language == "sv"
            else (
                "Selected store"
                if len(scope.store_ids) == 1
                else "Selected stores"
            )
        )

    return parts


def _with_context(
    title: str,
    request: AnalysisRequestState,
    language: str,
    *,
    period_suffix: str | None = None,
) -> str:
    parts = [
        title,
        *_scope_title_parts(request, language),
    ]
    if period_suffix:
        parts.append(period_suffix)
    return " – ".join(part for part in parts if part)


def _distinct_x_count(
    dataset: VisualizationDataset,
    key: str = "period_label",
) -> int:
    return len(
        {
            row.get(key)
            for row in dataset.rows
            if row.get(key) is not None
        }
    )



def _title_summary(
    request: AnalysisRequestState,
    language: str,
) -> str:
    entity = _entity_suffix(request)
    period = _period_title(request)

    if language == "sv":
        title = "Försäljningsöversikt"
        if entity:
            title += f" för {entity}"
    else:
        title = "Sales overview"
        if entity:
            title += f" for {entity}"

    return _with_context(
        title,
        request,
        language,
        period_suffix=period or None,
    )


def _title_trend(
    request: AnalysisRequestState,
    language: str,
    metrics: list[str],
) -> str:
    title = _metric_phrase(
        language,
        metrics,
    )
    entity = _entity_suffix(request)
    period = _period_title(request)

    if entity:
        title += (
            f" för {entity}"
            if language == "sv"
            else f" for {entity}"
        )

    return _with_context(
        title,
        request,
        language,
        period_suffix=period or None,
    )


def _title_selectable_trend(
    request: AnalysisRequestState,
    language: str,
) -> str:
    """Metric-neutral title for a chart whose metric can change in the UI."""

    title = (
        "Utveckling"
        if language == "sv"
        else "Trend"
    )
    entity = _entity_suffix(request)
    period = _period_title(request)

    if entity:
        title += (
            f" för {entity}"
            if language == "sv"
            else f" for {entity}"
        )

    return _with_context(
        title,
        request,
        language,
        period_suffix=period or None,
    )


def _title_ranking(
    request: AnalysisRequestState,
    language: str,
) -> str:
    group = request.group_by or "product"
    metric = request.rank_by or "units"
    period = _period_title(request)
    n = request.limit
    metric_text = _metric_label(
        language,
        metric,
    ).casefold()

    if n == 1:
        noun = _GROUP_SINGULAR[
            "sv" if language == "sv" else "en"
        ][group]
        if language == "sv":
            comparison = (
                "högst"
                if request.rank_order == "highest"
                else "lägst"
            )
            title = (
                f"{noun} med {comparison} {metric_text}"
            )
        else:
            comparison = (
                "highest"
                if request.rank_order == "highest"
                else "lowest"
            )
            title = (
                f"{noun} with {comparison} {metric_text}"
            )
    elif language == "sv":
        direction = (
            "Topp"
            if request.rank_order == "highest"
            else "Botten"
        )
        title = (
            f"{direction} {n} "
            f"{_GROUP_LABELS['sv'][group]} "
            f"efter {metric_text}"
        )
    else:
        direction = (
            "Top"
            if request.rank_order == "highest"
            else "Bottom"
        )
        title = (
            f"{direction} {n} "
            f"{_GROUP_LABELS['en'][group]} "
            f"by {metric_text}"
        )

    return _with_context(
        title,
        request,
        language,
        period_suffix=period or None,
    )


def _title_comparison(
    request: AnalysisRequestState,
    language: str,
    metric: str,
) -> str:
    title = _metric_label(
        language,
        metric,
    )
    entity = _entity_suffix(request)
    period = _period_title(request)

    if entity:
        title += (
            f" för {entity}"
            if language == "sv"
            else f" for {entity}"
        )

    if period:
        period_text = (
            f"{period} jämfört med föregående period"
            if language == "sv"
            else f"{period} vs previous period"
        )
    else:
        period_text = (
            "Jämförelse"
            if language == "sv"
            else "Comparison"
        )

    return _with_context(
        title,
        request,
        language,
        period_suffix=period_text,
    )

def _available_metrics(
    request: AnalysisRequestState,
    dataset: VisualizationDataset,
) -> list[str]:
    requested = [
        metric
        for metric in request.metrics
        if _numeric_field(dataset, metric)
    ]
    if requested:
        return requested

    return [
        metric
        for metric in (
            "net_sales",
            "units",
            "orders",
            "average_selling_price",
        )
        if _numeric_field(dataset, metric)
    ]


def _selectable_trend_metrics(
    dataset: VisualizationDataset,
) -> list[str]:
    """All supported metrics already present in this trend dataset."""

    return [
        metric
        for metric in _SELECTABLE_TREND_METRICS
        if _numeric_field(dataset, metric)
    ]


def _primary_metric(
    metrics: list[str],
) -> str | None:
    if "net_sales" in metrics:
        return "net_sales"
    return metrics[0] if metrics else None


def _line_specs(
    request: AnalysisRequestState,
    language: str,
    dataset: VisualizationDataset,
) -> list[VisualizationSpec]:
    metrics = _available_metrics(
        request,
        dataset,
    )
    if not metrics:
        return []

    # A line chart requires an actual X-axis progression. One period is a
    # snapshot, not a trend, even if the MCP result was produced by sales_trend.
    if _distinct_x_count(dataset, "period_label") < 2:
        return []

    has_series = _field_exists(
        dataset,
        "series_name",
    )

    # Split-series charts are intentionally left non-interactive. The renderer
    # represents each requested metric as its own chart in that shape, so adding
    # the same metric selector to every chart would create duplicate controls.
    if has_series:
        return [
            VisualizationSpec(
                dataset=dataset.id,
                type="line_chart",
                title=_title_trend(
                    request,
                    language,
                    [metric],
                ),
                x_key="period_label",
                y_keys=[metric],
                secondary_y_keys=[],
                selectable_y_keys=[],
                series_key="series_name",
            )
            for metric in metrics
        ]

    families: list[str] = []
    for metric in metrics:
        family = _metric_family(metric)
        if family not in families:
            families.append(family)

    selectable_metrics = _selectable_trend_metrics(dataset)

    if len(families) <= 2:
        primary_family = _metric_family(metrics[0])
        secondary = [
            metric
            for metric in metrics
            if _metric_family(metric) != primary_family
        ]

        is_interactive = len(selectable_metrics) > 1
        return [
            VisualizationSpec(
                dataset=dataset.id,
                type="line_chart",
                title=(
                    _title_selectable_trend(
                        request,
                        language,
                    )
                    if is_interactive
                    else _title_trend(
                        request,
                        language,
                        metrics,
                    )
                ),
                x_key="period_label",
                y_keys=metrics,
                secondary_y_keys=secondary,
                selectable_y_keys=(
                    selectable_metrics
                    if is_interactive
                    else []
                ),
            )
        ]

    # More than two metric families would require more than two axes. Keep the
    # existing deterministic split and do not add selectors to each resulting
    # chart.
    specs: list[VisualizationSpec] = []
    for family in families:
        family_metrics = [
            metric
            for metric in metrics
            if _metric_family(metric) == family
        ]
        specs.append(
            VisualizationSpec(
                dataset=dataset.id,
                type="line_chart",
                title=_title_trend(
                    request,
                    language,
                    family_metrics,
                ),
                x_key="period_label",
                y_keys=family_metrics,
                secondary_y_keys=[],
                selectable_y_keys=[],
            )
        )
    return specs


def _table_spec(
    request: AnalysisRequestState,
    language: str,
    dataset: VisualizationDataset,
) -> VisualizationSpec:
    if dataset.view == "ranking":
        columns = [
            key
            for key in (
                "rank",
                "entity_name",
                "units",
                "net_sales",
                "gross_sales",
                "orders",
                "discounts",
                "average_selling_price",
                "discount_rate",
            )
            if _field_exists(dataset, key)
        ]
        title = _title_ranking(
            request,
            language,
        )
    elif dataset.view == "trend":
        columns = [
            key
            for key in (
                "period_label",
                "series_name",
                *request.metrics,
            )
            if _field_exists(dataset, key)
        ]
        title = _title_trend(
            request,
            language,
            request.metrics,
        )
    else:
        columns = [
            key
            for key in (
                "product_name",
                "period_label",
                *request.metrics,
            )
            if _field_exists(dataset, key)
        ]
        title = _title_summary(
            request,
            language,
        )

    return VisualizationSpec(
        dataset=dataset.id,
        type="table",
        title=title,
        columns=columns,
    )


def build_visualization_plan(
    request: AnalysisRequestState,
    datasets: list[VisualizationDataset],
    language: str,
) -> VisualizationPlan:
    if not datasets:
        return VisualizationPlan()

    presentation = request.presentation

    if request.operation == "ranking":
        dataset = _find(
            datasets,
            "ranking",
        )
        if dataset is None:
            return VisualizationPlan()

        if presentation == "table":
            return VisualizationPlan(
                visualizations=[
                    _table_spec(
                        request,
                        language,
                        dataset,
                    )
                ]
            )

        metric = (
            request.rank_by
            or _primary_metric(
                _available_metrics(
                    request,
                    dataset,
                )
            )
        )
        if metric is None:
            return VisualizationPlan()

        if (
            presentation == "cards"
            or (
                presentation == "auto"
                and len(dataset.rows) == 1
            )
        ):
            card_metrics = [
                item
                for item in (
                    metric,
                    "units",
                    "net_sales",
                    "orders",
                    "average_selling_price",
                )
                if _numeric_field(dataset, item)
            ]
            card_metrics = list(
                dict.fromkeys(card_metrics)
            )
            return VisualizationPlan(
                visualizations=[
                    VisualizationSpec(
                        dataset=dataset.id,
                        type="metric_cards",
                        title=_title_ranking(
                            request,
                            language,
                        ),
                        y_keys=card_metrics,
                    )
                ]
            )

        return VisualizationPlan(
            visualizations=[
                VisualizationSpec(
                    dataset=dataset.id,
                    type="bar_chart",
                    title=_title_ranking(
                        request,
                        language,
                    ),
                    x_key="entity_name",
                    y_keys=[metric],
                )
            ]
        )

    if request.operation == "trend":
        dataset = _find(
            datasets,
            "trend",
        )
        if dataset is None:
            return VisualizationPlan()

        if presentation == "table":
            return VisualizationPlan(
                visualizations=[
                    _table_spec(
                        request,
                        language,
                        dataset,
                    )
                ]
            )

        line_specs = _line_specs(
            request,
            language,
            dataset,
        )
        if line_specs:
            return VisualizationPlan(
                visualizations=line_specs
            )

        # One X value cannot form a meaningful trend. For an automatic
        # presentation, degrade to a snapshot-style representation rather than
        # drawing a misleading one-point line. For an explicit chart request,
        # return no visualization instead of fabricating a meaningless graph.
        if presentation == "chart":
            return VisualizationPlan()

        metrics = _available_metrics(
            request,
            dataset,
        )
        if len(dataset.rows) == 1 and metrics:
            return VisualizationPlan(
                visualizations=[
                    VisualizationSpec(
                        dataset=dataset.id,
                        type="metric_cards",
                        title=_title_trend(
                            request,
                            language,
                            metrics,
                        ),
                        y_keys=metrics,
                    )
                ]
            )

        return VisualizationPlan(
            visualizations=[
                _table_spec(
                    request,
                    language,
                    dataset,
                )
            ]
        )

    if request.operation == "product_overview":
        current = _find(datasets, "current")
        trend = _find(datasets, "trend")
        comparison = _find(
            datasets,
            "comparison",
        )

        if presentation == "table":
            selected = trend or current
            if selected is None:
                return VisualizationPlan()
            return VisualizationPlan(
                visualizations=[
                    _table_spec(
                        request,
                        language,
                        selected,
                    )
                ]
            )

        if presentation == "chart":
            if trend is not None:
                primary = _primary_metric(
                    _available_metrics(
                        request,
                        trend,
                    )
                )
                if primary is not None:
                    chart_request = request.model_copy(
                        update={
                            "metrics": [primary]
                        }
                    )
                    line_specs = _line_specs(
                        chart_request,
                        language,
                        trend,
                    )
                    if line_specs:
                        # _line_specs owns metric-selector behavior for every
                        # non-series trend chart, including product overviews.
                        return VisualizationPlan(
                            visualizations=line_specs
                        )

            if comparison is not None:
                metrics = _available_metrics(
                    request,
                    comparison,
                )
                primary = _primary_metric(metrics)
                if primary is not None:
                    return VisualizationPlan(
                        visualizations=[
                            VisualizationSpec(
                                dataset=comparison.id,
                                type="bar_chart",
                                title=_title_comparison(
                                    request,
                                    language,
                                    primary,
                                ),
                                x_key="period_label",
                                y_keys=[primary],
                            )
                        ]
                    )

        if current is None:
            return VisualizationPlan()

        metrics = _available_metrics(
            request,
            current,
        )
        return VisualizationPlan(
            visualizations=[
                VisualizationSpec(
                    dataset=current.id,
                    type="metric_cards",
                    title=_title_summary(
                        request,
                        language,
                    ),
                    y_keys=metrics,
                )
            ]
        )

    current = _find(datasets, "current")
    comparison = _find(
        datasets,
        "comparison",
    )
    if current is None:
        return VisualizationPlan()

    if presentation == "table":
        return VisualizationPlan(
            visualizations=[
                _table_spec(
                    request,
                    language,
                    current,
                )
            ]
        )

    metrics = _available_metrics(
        request,
        current,
    )

    if presentation == "chart":
        selected = comparison or current
        primary = _primary_metric(
            _available_metrics(
                request,
                selected,
            )
        )
        if primary is None:
            return VisualizationPlan()

        x_key = (
            "period_label"
            if _field_exists(
                selected,
                "period_label",
            )
            else "product_name"
        )
        return VisualizationPlan(
            visualizations=[
                VisualizationSpec(
                    dataset=selected.id,
                    type="bar_chart",
                    title=_title_comparison(
                        request,
                        language,
                        primary,
                    ),
                    x_key=x_key,
                    y_keys=[primary],
                )
            ]
        )

    return VisualizationPlan(
        visualizations=[
            VisualizationSpec(
                dataset=current.id,
                type="metric_cards",
                title=_title_summary(
                    request,
                    language,
                ),
                y_keys=metrics,
            )
        ]
    )
