"""Convert raw MCP results into flat visualization datasets."""

from __future__ import annotations

import json
from typing import Any

from google.adk.agents.context import Context
from google.adk.workflow import BaseNode, node

from app.agents.state import ExecutedToolCall, StateKeys
from app.schemas.visualization import VisualizationDataset


def _flatten_metrics(metrics: Any) -> dict[str, Any]:
    return dict(metrics) if isinstance(metrics, dict) else {}


def _comparison_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    current = result.get("current")
    previous = result.get("previous")
    if not isinstance(current, dict) or not isinstance(previous, dict):
        return []

    effective = result.get("effective_period") or {}
    previous_period = result.get("previous_period") or result.get("comparison_period") or {}

    return [
        {"period": "Current", "period_label": effective.get("label"), **current},
        {"period": "Previous", "period_label": previous_period.get("label"), **previous},
    ]


def _ranking_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows = result.get("rows")
    if not isinstance(rows, list):
        return []

    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        entity = row.get("entity") or {}
        out.append({
            "rank": row.get("rank"),
            "entity_id": entity.get("id") if isinstance(entity, dict) else None,
            "entity_name": entity.get("name") if isinstance(entity, dict) else None,
            "entity_type": entity.get("type") if isinstance(entity, dict) else None,
            **_flatten_metrics(row.get("metrics")),
            "share_of_rank_metric": row.get("share_of_rank_metric"),
            "previous_rank_metric_value": row.get("previous_rank_metric_value"),
            "rank_metric_absolute_change": row.get("rank_metric_absolute_change"),
            "rank_metric_percent_change": row.get("rank_metric_percent_change"),
        })
    return out


def _trend_rows(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        return []

    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        entity = row.get("series_entity")
        item: dict[str, Any] = {
            "period_start": row.get("period_start"),
            "period_label": row.get("period_label"),
            **_flatten_metrics(row.get("metrics")),
        }
        if isinstance(entity, dict):
            item["series_id"] = entity.get("id")
            item["series_name"] = entity.get("name")
            item["series_type"] = entity.get("type")
        out.append(item)
    return out


def _breakdown_rows(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        return []

    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        entity = row.get("entity") or {}
        out.append({
            "entity_id": entity.get("id") if isinstance(entity, dict) else None,
            "entity_name": entity.get("name") if isinstance(entity, dict) else None,
            "entity_type": entity.get("type") if isinstance(entity, dict) else None,
            **_flatten_metrics(row.get("metrics")),
            "share_of_net_sales": row.get("share_of_net_sales"),
        })
    return out


def _dataset(call_id: str, view: str, rows: list[dict[str, Any]]) -> VisualizationDataset | None:
    if not rows:
        return None
    return VisualizationDataset(
        id=f"{call_id}:{view}",
        source_call_id=call_id,
        view=view,
        rows=rows,
    )


def normalize_visualization_datasets(
    tool_results: list[ExecutedToolCall],
) -> list[VisualizationDataset]:
    datasets: list[VisualizationDataset] = []

    for call in tool_results:
        if not call.is_success:
            continue

        result = call.result or {}
        created: list[VisualizationDataset | None] = []

        if call.tool_name == "sales_summary":
            current = result.get("current")
            if isinstance(current, dict):
                created.append(_dataset(call.call_id, "current", [dict(current)]))
            created.append(_dataset(call.call_id, "comparison", _comparison_rows(result)))

        elif call.tool_name == "sales_rank":
            created.append(_dataset(call.call_id, "ranking", _ranking_rows(result)))

        elif call.tool_name == "sales_trend":
            created.append(_dataset(call.call_id, "trend", _trend_rows(result.get("rows"))))

        elif call.tool_name == "product_overview":
            current = result.get("current")
            product = result.get("product") or {}
            if isinstance(current, dict):
                current_row = {
                    "product_id": product.get("id") if isinstance(product, dict) else None,
                    "product_name": product.get("name") if isinstance(product, dict) else None,
                    **dict(current),
                    "rank_by_units": result.get("rank_by_units"),
                    "rank_by_net_sales": result.get("rank_by_net_sales"),
                    "share_of_supplier_units": result.get("share_of_supplier_units"),
                    "share_of_supplier_net_sales": result.get("share_of_supplier_net_sales"),
                }
                created.append(_dataset(call.call_id, "current", [current_row]))

            created.append(_dataset(call.call_id, "comparison", _comparison_rows(result)))
            created.append(_dataset(call.call_id, "trend", _trend_rows(result.get("trend"))))
            created.append(_dataset(call.call_id, "channel_breakdown", _breakdown_rows(result.get("channel_breakdown"))))
            created.append(_dataset(call.call_id, "city_breakdown", _breakdown_rows(result.get("city_breakdown"))))

        datasets.extend(ds for ds in created if ds is not None)

    return datasets


def build_normalize_visualizations_node() -> BaseNode:
    def normalize_visualizations(
        ctx: Context,
        tool_results: list[dict[str, Any]] | None = None,
    ) -> None:
        results = [ExecutedToolCall.model_validate(r) for r in (tool_results or [])]
        datasets = normalize_visualization_datasets(results)
        ctx.state[StateKeys.VISUALIZATION_DATASETS_JSON] = json.dumps(
            [d.model_dump(mode="json") for d in datasets]
        )

    return node(normalize_visualizations, name="normalize_visualizations")
