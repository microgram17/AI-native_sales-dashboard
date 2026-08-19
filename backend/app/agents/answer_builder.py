
"""Deterministic concise natural-language answers for successful BI retrievals.

This layer intentionally does not interpret causes or produce long analysis.
It states the direct answer in one short sentence (occasionally two for a
ranking), while the existing Analytics LLM remains reserved for explicit
interpretation, no-data, not-found and ambiguous outcomes.
"""

from __future__ import annotations

import calendar
from datetime import date
from typing import Any

from app.agents.state import ExecutedToolCall
from app.schemas.agent import AnalysisRequestState


_METRIC_LABELS = {
    "sv": {
        "units": "sålda enheter",
        "net_sales": "nettoomsättning",
        "gross_sales": "bruttoomsättning",
        "discounts": "rabatter",
        "orders": "beställningar",
        "average_selling_price": "genomsnittligt försäljningspris",
        "discount_rate": "rabattgrad",
    },
    "en": {
        "units": "units sold",
        "net_sales": "net sales",
        "gross_sales": "gross sales",
        "discounts": "discounts",
        "orders": "orders",
        "average_selling_price": "average selling price",
        "discount_rate": "discount rate",
    },
}

_GRAIN_LABELS = {
    "sv": {
        "day": "dagliga",
        "week": "veckovisa",
        "month": "månatliga",
        "quarter": "kvartalsvisa",
    },
    "en": {
        "day": "daily",
        "week": "weekly",
        "month": "monthly",
        "quarter": "quarterly",
    },
}


def _language(language: str) -> str:
    return "sv" if language == "sv" else "en"


def _format_number(value: Any, language: str, decimals: int = 0) -> str:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return str(value if value is not None else "")

    if decimals == 0:
        rendered = f"{value:,.0f}"
    else:
        rendered = f"{value:,.{decimals}f}"

    if language == "sv":
        rendered = (
            rendered
            .replace(",", "\u00a0")
            .replace(".", ",")
        )
    return rendered


def _format_metric_value(
    metric: str,
    value: Any,
    language: str,
) -> str:
    lang = _language(language)

    if metric == "discount_rate":
        if not isinstance(value, (int, float)):
            return str(value if value is not None else "")
        percentage = value * 100 if abs(value) <= 1 else value
        suffix = "%"
        return f"{_format_number(percentage, lang, 1)}{suffix}"

    if metric in {
        "net_sales",
        "gross_sales",
        "discounts",
        "average_selling_price",
    }:
        suffix = "kr" if lang == "sv" else "SEK"
        return f"{_format_number(value, lang, 0)} {suffix}"

    return _format_number(value, lang, 0)


def _metric_fact(
    metric: str,
    value: Any,
    language: str,
) -> str:
    lang = _language(language)
    rendered = _format_metric_value(metric, value, lang)

    if lang == "sv":
        if metric == "units":
            return f"{rendered} sålda enheter"
        if metric == "net_sales":
            return f"{rendered} i nettoomsättning"
        if metric == "gross_sales":
            return f"{rendered} i bruttoomsättning"
        if metric == "orders":
            return f"{rendered} beställningar"
        if metric == "discounts":
            return f"{rendered} i rabatter"
        if metric == "average_selling_price":
            return f"{rendered} i genomsnittligt försäljningspris"
        if metric == "discount_rate":
            return f"{rendered} rabattgrad"
        return f"{_METRIC_LABELS['sv'].get(metric, metric)}: {rendered}"

    if metric == "units":
        return f"{rendered} units sold"
    if metric == "net_sales":
        return f"{rendered} in net sales"
    if metric == "gross_sales":
        return f"{rendered} in gross sales"
    if metric == "orders":
        return f"{rendered} orders"
    if metric == "discounts":
        return f"{rendered} in discounts"
    if metric == "average_selling_price":
        return f"{rendered} average selling price"
    if metric == "discount_rate":
        return f"{rendered} discount rate"
    return f"{_METRIC_LABELS['en'].get(metric, metric)}: {rendered}"


def _join_facts(values: list[str], language: str) -> str:
    cleaned = [value for value in values if value]
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]
    if len(cleaned) == 2:
        return cleaned[0] + (" och " if language == "sv" else " and ") + cleaned[1]
    return ", ".join(cleaned[:-1]) + (
        f" och {cleaned[-1]}"
        if language == "sv"
        else f", and {cleaned[-1]}"
    )


def _quarter_label(start: date, end: date) -> str | None:
    if start.year != end.year:
        return None
    for quarter in range(1, 5):
        start_month = (quarter - 1) * 3 + 1
        end_month = start_month + 2
        q_start = date(start.year, start_month, 1)
        q_end = date(
            start.year,
            end_month,
            calendar.monthrange(start.year, end_month)[1],
        )
        if start == q_start and end == q_end:
            return f"Q{quarter} {start.year}"
    return None


def _period_phrase(
    request: AnalysisRequestState,
    result: dict[str, Any],
    language: str,
) -> str:
    lang = _language(language)
    effective = result.get("effective_period")
    if isinstance(effective, dict) and effective.get("defaulted"):
        return (
            " under hela den tillgängliga perioden"
            if lang == "sv"
            else " across all available data"
        )

    start = request.period_start
    end = request.period_end
    if start is None or end is None:
        return ""

    if (
        start == date(start.year, 1, 1)
        and end == date(start.year, 12, 31)
    ):
        return (
            f" under {start.year}"
            if lang == "sv"
            else f" in {start.year}"
        )

    quarter = _quarter_label(start, end)
    if quarter:
        return (
            f" under {quarter}"
            if lang == "sv"
            else f" in {quarter}"
        )

    return (
        f" under perioden {start.isoformat()}–{end.isoformat()}"
        if lang == "sv"
        else f" for {start.isoformat()}–{end.isoformat()}"
    )


def _scope_phrase(
    request: AnalysisRequestState,
    language: str,
) -> str:
    lang = _language(language)
    parts: list[str] = []

    if request.scope.cities:
        if len(request.scope.cities) == 1:
            parts.append(
                f"i {request.scope.cities[0]}"
                if lang == "sv"
                else f"in {request.scope.cities[0]}"
            )
        else:
            joined = ", ".join(request.scope.cities)
            parts.append(
                f"i {joined}"
                if lang == "sv"
                else f"in {joined}"
            )

    channels = set(request.scope.channels)
    if channels == {"online"}:
        parts.append("online")
    elif channels == {"physical"}:
        parts.append(
            "i fysiska butiker"
            if lang == "sv"
            else "in physical stores"
        )

    if request.scope.categories:
        joined = ", ".join(request.scope.categories)
        parts.append(
            f"i kategorin {joined}"
            if lang == "sv"
            else f"in the {joined} category"
        )

    if not parts:
        return ""
    return " " + ", ".join(parts)


def _successful_result(
    tool_results: list[ExecutedToolCall],
) -> dict[str, Any] | None:
    for tool_result in tool_results:
        if tool_result.is_success and isinstance(tool_result.result, dict):
            return tool_result.result
    return None


def _requested_facts(
    request: AnalysisRequestState,
    values: dict[str, Any],
    language: str,
    *,
    max_items: int = 2,
) -> list[str]:
    preferred = [
        metric
        for metric in request.metrics
        if metric in values and values.get(metric) is not None
    ]

    if not preferred:
        preferred = [
            metric
            for metric in ("net_sales", "units", "orders")
            if metric in values and values.get(metric) is not None
        ]

    return [
        _metric_fact(metric, values.get(metric), language)
        for metric in preferred[:max_items]
    ]


def _ranking_answer(
    request: AnalysisRequestState,
    result: dict[str, Any],
    language: str,
) -> str:
    lang = _language(language)
    rows = result.get("rows")
    if not isinstance(rows, list) or not rows:
        return ""

    first = rows[0]
    if not isinstance(first, dict):
        return ""

    entity = first.get("entity")
    metrics = first.get("metrics")
    if not isinstance(entity, dict) or not isinstance(metrics, dict):
        return ""

    name = str(entity.get("name") or "").strip()
    metric = request.rank_by or str(result.get("rank_by") or "units")
    value = metrics.get(metric)
    if not name or value is None:
        return ""

    scope = _scope_phrase(request, lang)
    period = _period_phrase(request, result, lang)
    rendered = _format_metric_value(metric, value, lang)

    if lang == "sv":
        if metric == "units":
            verb = "säljer bäst" if request.rank_order == "highest" else "säljer minst"
            first_sentence = (
                f"{name} {verb}{scope} med {rendered} sålda enheter{period}."
            )
        elif metric == "orders":
            descriptor = "flest" if request.rank_order == "highest" else "färst"
            first_sentence = (
                f"{name} har {descriptor} beställningar{scope}: "
                f"{rendered}{period}."
            )
        else:
            label = _METRIC_LABELS["sv"].get(metric, metric)
            descriptor = "högst" if request.rank_order == "highest" else "lägst"
            first_sentence = (
                f"{name} har {descriptor} {label}{scope}: "
                f"{rendered}{period}."
            )

        if len(rows) > 1:
            direction = "högst" if request.rank_order == "highest" else "lägst"
            group = {
                "product": "produkterna",
                "category": "kategorierna",
                "store": "butikerna",
                "city": "städerna",
                "channel": "kanalerna",
            }.get(request.group_by or "product", "resultaten")
            return (
                f"{first_sentence} Diagrammet visar de {len(rows)} "
                f"{direction} rankade {group}."
            )
        return first_sentence

    if metric == "units":
        verb = "sells best" if request.rank_order == "highest" else "sells the least"
        first_sentence = (
            f"{name} {verb}{scope} with {rendered} units sold{period}."
        )
    elif metric == "orders":
        descriptor = "the most" if request.rank_order == "highest" else "the fewest"
        first_sentence = (
            f"{name} has {descriptor} orders{scope}: {rendered}{period}."
        )
    else:
        label = _METRIC_LABELS["en"].get(metric, metric)
        descriptor = "the highest" if request.rank_order == "highest" else "the lowest"
        first_sentence = (
            f"{name} has {descriptor} {label}{scope}: {rendered}{period}."
        )

    if len(rows) > 1:
        direction = "highest" if request.rank_order == "highest" else "lowest"
        group = {
            "product": "products",
            "category": "categories",
            "store": "stores",
            "city": "cities",
            "channel": "channels",
        }.get(request.group_by or "product", "results")
        return (
            f"{first_sentence} The chart shows the {len(rows)} "
            f"{direction}-ranked {group}."
        )
    return first_sentence


def _trend_answer(
    request: AnalysisRequestState,
    result: dict[str, Any],
    language: str,
) -> str:
    lang = _language(language)
    grain = _GRAIN_LABELS[lang].get(
        request.grain or "month",
        request.grain or "month",
    )
    metric_names = [
        _METRIC_LABELS[lang].get(metric, metric)
        for metric in request.metrics
    ]
    metrics = _join_facts(metric_names, lang)
    scope = _scope_phrase(request, lang)
    period = _period_phrase(request, result, lang)

    if lang == "sv":
        return (
            f"Här är den {grain} utvecklingen för {metrics}{scope}{period}."
        )
    return (
        f"Here is the {grain} trend for {metrics}{scope}{period}."
    )


def _overview_answer(
    request: AnalysisRequestState,
    result: dict[str, Any],
    language: str,
) -> str:
    lang = _language(language)
    current = result.get("current")
    if not isinstance(current, dict):
        return ""

    product = result.get("product")
    canonical_name = ""
    if isinstance(product, dict):
        canonical_name = str(product.get("name") or "").strip()
    if not canonical_name and request.entity is not None:
        canonical_name = request.entity.name

    facts = _requested_facts(
        request,
        current,
        lang,
        max_items=2,
    )
    if not facts:
        return ""

    subject = canonical_name or (
        "Resultatet" if lang == "sv" else "The result"
    )
    scope = _scope_phrase(request, lang)
    period = _period_phrase(request, result, lang)

    return f"{subject}: {_join_facts(facts, lang)}{scope}{period}."


def _summary_answer(
    request: AnalysisRequestState,
    result: dict[str, Any],
    language: str,
) -> str:
    lang = _language(language)
    current = result.get("current")
    if not isinstance(current, dict):
        return ""

    facts = _requested_facts(
        request,
        current,
        lang,
        max_items=2,
    )
    if not facts:
        return ""

    subject = (
        request.entity.name
        if request.entity is not None
        else ("Resultatet" if lang == "sv" else "The result")
    )
    scope = _scope_phrase(request, lang)
    period = _period_phrase(request, result, lang)

    return f"{subject}: {_join_facts(facts, lang)}{scope}{period}."


def _visualization_reuse_answer(
    request: AnalysisRequestState,
    result: dict[str, Any],
    language: str,
) -> str:
    lang = _language(language)
    scope = _scope_phrase(request, lang)
    period = _period_phrase(request, result, lang)

    if request.entity is not None:
        return (
            f"Här är utvecklingen för {request.entity.name}{scope}{period}."
            if lang == "sv"
            else f"Here is the trend for {request.entity.name}{scope}{period}."
        )

    if request.operation == "ranking":
        return (
            "Här är rankningen som diagram."
            if lang == "sv"
            else "Here is the ranking as a chart."
        )

    return (
        "Här är resultatet som diagram."
        if lang == "sv"
        else "Here is the result as a chart."
    )


def build_short_answer(
    request: AnalysisRequestState,
    tool_results: list[ExecutedToolCall],
    language: str,
    *,
    effective_mode: str = "",
) -> str:
    """Build a short grounded answer for a successful straightforward request."""

    result = _successful_result(tool_results)
    if result is None:
        return ""

    if effective_mode == "visualize_existing":
        return _visualization_reuse_answer(
            request,
            result,
            language,
        )

    if request.operation == "ranking":
        return _ranking_answer(
            request,
            result,
            language,
        )

    if request.operation == "trend":
        return _trend_answer(
            request,
            result,
            language,
        )

    if request.operation == "product_overview":
        return _overview_answer(
            request,
            result,
            language,
        )

    return _summary_answer(
        request,
        result,
        language,
    )
