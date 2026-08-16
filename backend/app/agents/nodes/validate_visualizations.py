"""Validate visualization-agent output against normalized visualization data."""

from __future__ import annotations

import json
from typing import Any

from google.adk.agents.context import Context
from google.adk.workflow import BaseNode, node

from app.agents.state import StateKeys
from app.schemas.visualization import VisualizationDataset, VisualizationPlan, VisualizationSpec


def _coerce_plan(value: Any) -> VisualizationPlan:
    if isinstance(value, VisualizationPlan):
        return value
    if isinstance(value, dict):
        return VisualizationPlan.model_validate(value)
    if isinstance(value, str) and value.strip():
        return VisualizationPlan.model_validate_json(value)
    return VisualizationPlan()


def _coerce_datasets(value: str | list[dict[str, Any]] | None) -> list[VisualizationDataset]:
    if value is None:
        return []
    raw: Any = value
    if isinstance(value, str):
        if not value.strip():
            return []
        try:
            raw = json.loads(value)
        except json.JSONDecodeError:
            return []
    if not isinstance(raw, list):
        return []
    return [VisualizationDataset.model_validate(item) for item in raw]


def _field_exists(dataset: VisualizationDataset, key: str) -> bool:
    return bool(key) and any(key in row and row[key] is not None for row in dataset.rows)


def _numeric_field(dataset: VisualizationDataset, key: str) -> bool:
    values = [row.get(key) for row in dataset.rows if row.get(key) is not None]
    return bool(values) and all(
        isinstance(value, (int, float)) and not isinstance(value, bool)
        for value in values
    )


def _metric_family(key: str) -> str:
    k = key.lower()
    if any(token in k for token in ("rate", "share", "percent")):
        return "rate"
    if any(token in k for token in ("sales", "revenue", "discount", "price", "cost", "sek")):
        return "currency"
    if any(token in k for token in ("units", "orders", "count", "quantity", "rank")):
        return "count"
    return "number"


def _compatible_y_keys(keys: list[str]) -> bool:
    return len(keys) <= 1 or len({_metric_family(key) for key in keys}) == 1


def _validate_spec(
    spec: VisualizationSpec,
    datasets_by_id: dict[str, VisualizationDataset],
) -> VisualizationSpec | None:
    dataset = datasets_by_id.get(spec.dataset)
    if dataset is None or not dataset.rows:
        return None

    if spec.type == "metric_cards":
        if not spec.y_keys or not all(_numeric_field(dataset, key) for key in spec.y_keys):
            return None
        return spec.model_copy(update={"x_key": None, "series_key": None, "columns": []})

    if spec.type in {"bar_chart", "line_chart"}:
        if not spec.x_key or not _field_exists(dataset, spec.x_key):
            return None
        if not spec.y_keys or not all(_numeric_field(dataset, key) for key in spec.y_keys):
            return None
        if not _compatible_y_keys(spec.y_keys):
            return None
        if spec.series_key and not _field_exists(dataset, spec.series_key):
            return None
        return spec.model_copy(update={"columns": []})

    if spec.type == "table":
        if not spec.columns:
            return None
        valid_columns = [key for key in spec.columns if _field_exists(dataset, key)]
        if not valid_columns:
            return None
        return spec.model_copy(
            update={
                "x_key": None,
                "y_keys": [],
                "series_key": None,
                "columns": valid_columns,
            }
        )

    return None


def validate_visualization_plan(
    plan: VisualizationPlan,
    datasets: list[VisualizationDataset],
) -> VisualizationPlan:
    by_id = {dataset.id: dataset for dataset in datasets}
    valid: list[VisualizationSpec] = []
    for spec in plan.visualizations:
        checked = _validate_spec(spec, by_id)
        if checked is not None:
            valid.append(checked)
    return VisualizationPlan(visualizations=valid)


def build_validate_visualizations_node() -> BaseNode:
    def validate_visualizations(
        ctx: Context,
        visualization_plan: Any = None,
        visualization_datasets_json: str = "[]",
    ) -> None:
        plan = _coerce_plan(visualization_plan)
        datasets = _coerce_datasets(visualization_datasets_json)
        validated = validate_visualization_plan(plan, datasets)
        ctx.state[StateKeys.VISUALIZATION_PLAN] = validated.model_dump(mode="json")

    return node(validate_visualizations, name="validate_visualizations")
