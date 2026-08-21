"""Derive a small, auditable fact set for analytical prose."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from typing import Any

from app.schemas.agent import AnalysisRequestState


_ADDITIVE_METRICS = {
    "units",
    "net_sales",
    "gross_sales",
    "discounts",
    "orders",
}

_METRIC_LABELS = {
    "en": {
        "units": "units",
        "net_sales": "net sales",
        "gross_sales": "gross sales",
        "discounts": "discounts",
        "orders": "orders",
        "average_selling_price": "average selling price",
        "discount_rate": "discount rate",
    },
    "sv": {
        "units": "sålda enheter",
        "net_sales": "nettoomsättning",
        "gross_sales": "bruttoomsättning",
        "discounts": "rabatter",
        "orders": "beställningar",
        "average_selling_price": "genomsnittligt försäljningspris",
        "discount_rate": "rabattgrad",
    },
}


def _coerce_business_results(value: Any) -> list[dict[str, Any]]:
    raw = value
    if isinstance(value, str):
        try:
            raw = json.loads(value)
        except json.JSONDecodeError:
            return []
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def _number(value: Any) -> float | int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(float(value)):
        return None
    return value


def _change(first: float | int, last: float | int) -> dict[str, Any]:
    percent = None if first == 0 else round((last - first) / abs(first) * 100, 2)
    return {
        "absolute": round(float(last - first), 2),
        "percent": percent,
    }


def _entity(value: Any) -> dict[str, str] | None:
    if not isinstance(value, dict):
        return None
    entity_id = str(value.get("id") or "").strip()
    name = str(value.get("name") or entity_id).strip()
    if not entity_id and not name:
        return None
    return {
        "type": str(value.get("type") or "series"),
        "id": entity_id,
        "name": name,
    }


def _trend_facts(
    request: AnalysisRequestState,
    result: dict[str, Any],
) -> dict[str, Any]:
    rows = [row for row in result.get("rows", []) if isinstance(row, dict)]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    entities: dict[str, dict[str, str] | None] = {}

    for row in rows:
        entity = _entity(row.get("series_entity"))
        key = (entity or {}).get("id") or (entity or {}).get("name") or "overall"
        grouped[key].append(row)
        entities[key] = entity

    series: list[dict[str, Any]] = []
    for key, series_rows in grouped.items():
        ordered = sorted(
            series_rows,
            key=lambda row: str(row.get("period_start") or ""),
        )
        metric_facts: dict[str, Any] = {}
        for metric in request.metrics:
            points: list[tuple[str, str, float | int]] = []
            for row in ordered:
                metrics = row.get("metrics")
                value = _number(metrics.get(metric)) if isinstance(metrics, dict) else None
                if value is not None:
                    points.append(
                        (
                            str(row.get("period_start") or ""),
                            str(row.get("period_label") or row.get("period_start") or ""),
                            value,
                        )
                    )
            if not points:
                continue
            first = points[0]
            last = points[-1]
            minimum = min(points, key=lambda point: point[2])
            maximum = max(points, key=lambda point: point[2])
            fact: dict[str, Any] = {
                "first": {"period": first[0], "label": first[1], "value": first[2]},
                "last": {"period": last[0], "label": last[1], "value": last[2]},
                "first_to_last_change": _change(first[2], last[2]),
                "minimum": {
                    "period": minimum[0],
                    "label": minimum[1],
                    "value": minimum[2],
                },
                "maximum": {
                    "period": maximum[0],
                    "label": maximum[1],
                    "value": maximum[2],
                },
                "observations": len(points),
            }
            if metric in _ADDITIVE_METRICS:
                fact["period_total"] = round(sum(point[2] for point in points), 2)
            metric_facts[metric] = fact

        if metric_facts:
            series.append(
                {
                    "entity": entities[key],
                    "metrics": metric_facts,
                }
            )

    return {
        "status": result.get("status"),
        "operation": "trend",
        "grain": result.get("grain") or request.grain,
        "split_by": result.get("split_by") or request.split_by,
        "effective_period": result.get("effective_period"),
        "effective_scope": result.get("effective_scope"),
        "requested_metrics": request.metrics,
        "row_count": len(rows),
        "series": series,
    }


def _ranking_facts(
    request: AnalysisRequestState,
    result: dict[str, Any],
) -> dict[str, Any]:
    metric = request.rank_by or result.get("rank_by") or "units"
    rows: list[dict[str, Any]] = []
    for row in result.get("rows", []):
        if not isinstance(row, dict):
            continue
        metrics = row.get("metrics")
        value = _number(metrics.get(metric)) if isinstance(metrics, dict) else None
        if value is None:
            continue
        rows.append(
            {
                "rank": row.get("rank"),
                "entity": _entity(row.get("entity")),
                "metric": metric,
                "value": value,
                "share": _number(row.get("share_of_rank_metric")),
                "comparison": {
                    "previous_value": _number(row.get("previous_rank_metric_value")),
                    "absolute_change": _number(row.get("rank_metric_absolute_change")),
                    "percent_change": _number(row.get("rank_metric_percent_change")),
                },
            }
        )

    return {
        "status": result.get("status"),
        "operation": "ranking",
        "group_by": result.get("group_by") or request.group_by,
        "rank_by": metric,
        "order": result.get("order") or request.rank_order,
        "effective_period": result.get("effective_period"),
        "comparison_period": result.get("comparison_period"),
        "effective_scope": result.get("effective_scope"),
        "row_count": len(rows),
        "rows": rows,
    }


def _summary_facts(
    request: AnalysisRequestState,
    result: dict[str, Any],
) -> dict[str, Any]:
    current = result.get("current") if isinstance(result.get("current"), dict) else {}
    previous = result.get("previous") if isinstance(result.get("previous"), dict) else {}
    metrics: dict[str, Any] = {}
    for metric in request.metrics:
        current_value = _number(current.get(metric))
        if current_value is None:
            continue
        previous_value = _number(previous.get(metric))
        metrics[metric] = {
            "current": current_value,
            "previous": previous_value,
            "change": (
                _change(previous_value, current_value)
                if previous_value is not None
                else None
            ),
        }
    return {
        "status": result.get("status"),
        "operation": request.operation,
        "effective_period": result.get("effective_period"),
        "comparison_period": result.get("previous_period"),
        "effective_scope": result.get("effective_scope"),
        "metrics": metrics,
    }


def derive_analysis_facts(
    request: AnalysisRequestState | None,
    business_results: Any,
) -> dict[str, Any]:
    items = _coerce_business_results(business_results)
    result = next(
        (
            item.get("result")
            for item in items
            if isinstance(item.get("result"), dict)
        ),
        None,
    )
    if request is None or not isinstance(result, dict):
        return {"status": "unavailable"}
    if result.get("status") != "success":
        return {
            "status": result.get("status") or "unavailable",
            "operation": request.operation,
            "effective_period": result.get("effective_period"),
            "effective_scope": result.get("effective_scope"),
        }
    if request.operation == "trend":
        return _trend_facts(request, result)
    if request.operation == "ranking":
        return _ranking_facts(request, result)
    return _summary_facts(request, result)


def facts_have_data(facts: dict[str, Any]) -> bool:
    if facts.get("status") != "success":
        return False
    if facts.get("operation") in {"trend", "ranking"}:
        return int(facts.get("row_count") or 0) > 0
    return bool(facts.get("metrics"))


def _format_value(metric: str, value: Any, language: str) -> str:
    number = _number(value)
    if number is None:
        return "–"
    if metric in {"net_sales", "gross_sales", "discounts", "average_selling_price"}:
        rendered = f"{number:,.2f}"
        if language == "sv":
            rendered = rendered.replace(",", "X").replace(".", ",").replace("X", " ")
        return f"{rendered} SEK"
    if metric == "discount_rate":
        return f"{float(number) * 100:.2f}%"
    return f"{number:,.0f}".replace(",", " " if language == "sv" else ",")


def render_analysis_facts(facts: dict[str, Any], language: str) -> str:
    """Safe fallback when generated prose contradicts the validated facts."""

    lang = "sv" if language == "sv" else "en"
    if not facts_have_data(facts):
        return "Inga data hittades för det valda urvalet." if lang == "sv" else "No data was found for the selected scope."

    operation = facts.get("operation")
    if operation == "trend":
        metric = next(iter(facts.get("requested_metrics") or ["net_sales"]))
        label = _METRIC_LABELS[lang].get(metric, metric)
        lines: list[str] = []
        for series in facts.get("series", [])[:3]:
            metric_fact = (series.get("metrics") or {}).get(metric)
            if not isinstance(metric_fact, dict):
                continue
            entity = series.get("entity") or {}
            name = entity.get("name") or ("Totalt" if lang == "sv" else "Overall")
            first = metric_fact["first"]
            last = metric_fact["last"]
            peak = metric_fact["maximum"]
            percent = metric_fact["first_to_last_change"].get("percent")
            change_text = ""
            if percent is not None:
                change_text = f" ({percent:+.2f}%)"
            if lang == "sv":
                lines.append(
                    f"{name}: {label} gick från {_format_value(metric, first['value'], lang)} "
                    f"i {first['label']} till {_format_value(metric, last['value'], lang)} "
                    f"i {last['label']}{change_text}. Högsta värdet var "
                    f"{_format_value(metric, peak['value'], lang)} i {peak['label']}."
                )
            else:
                lines.append(
                    f"{name}: {label} moved from {_format_value(metric, first['value'], lang)} "
                    f"in {first['label']} to {_format_value(metric, last['value'], lang)} "
                    f"in {last['label']}{change_text}. The peak was "
                    f"{_format_value(metric, peak['value'], lang)} in {peak['label']}."
                )
        return "\n\n".join(lines)

    if operation == "ranking":
        rows = facts.get("rows") or []
        if not rows:
            return ""
        metric = str(facts.get("rank_by") or "units")
        label = _METRIC_LABELS[lang].get(metric, metric)
        first = rows[0]
        name = (first.get("entity") or {}).get("name") or "–"
        period = facts.get("effective_period") or {}
        comparison = facts.get("comparison_period") or {}
        intro = (
            f"{name} rankas högst med {_format_value(metric, first.get('value'), lang)} i {label} "
            f"under {period.get('start')}–{period.get('end')}."
            if lang == "sv"
            else f"{name} ranks first with {_format_value(metric, first.get('value'), lang)} in {label} "
            f"during {period.get('start')}–{period.get('end')}."
        )
        changes: list[str] = []
        if comparison.get("start") and comparison.get("end"):
            for row in rows[:3]:
                percent = (row.get("comparison") or {}).get("percent_change")
                if percent is None:
                    continue
                row_name = (row.get("entity") or {}).get("name") or "–"
                changes.append(f"{row_name} {float(percent):+.2f}%")
            if changes:
                prefix = (
                    f"Jämfört med {comparison['start']}–{comparison['end']}: "
                    if lang == "sv"
                    else f"Compared with {comparison['start']}–{comparison['end']}: "
                )
                intro = f"{intro} {prefix}{', '.join(changes)}."
        return intro

    metrics = facts.get("metrics") or {}
    current_period = facts.get("effective_period") or {}
    comparison_period = facts.get("comparison_period") or {}
    rendered: list[str] = []
    for metric, values in metrics.items():
        label = _METRIC_LABELS[lang].get(metric, metric)
        text = f"{label}: {_format_value(metric, values.get('current'), lang)}"
        percent = ((values.get("change") or {}).get("percent"))
        if (
            percent is not None
            and comparison_period.get("start")
            and comparison_period.get("end")
        ):
            compared = (
                f"jämfört med {comparison_period['start']}–{comparison_period['end']}"
                if lang == "sv"
                else f"compared with {comparison_period['start']}–{comparison_period['end']}"
            )
            text += f" ({float(percent):+.2f}% {compared})"
        rendered.append(text)

    period = ""
    if current_period.get("start") and current_period.get("end"):
        period = (
            f"Under {current_period['start']}–{current_period['end']}: "
            if lang == "sv"
            else f"During {current_period['start']}–{current_period['end']}: "
        )
    return period + ", ".join(rendered) + "."
