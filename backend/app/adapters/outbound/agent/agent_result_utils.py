from __future__ import annotations

from datetime import date
from typing import Any

from app.domain.agent_runtime_context import AgentRuntimeContext
from app.domain.tool_result import ToolResultPayload


def clamp_dates(
    date_from: str | None,
    date_to: str | None,
    ctx: AgentRuntimeContext,
) -> tuple[str | None, str | None, bool]:
    """Clamp date_from/date_to to the available data range.

    Returns (clamped_from, clamped_to, was_clamped).
    If either value cannot be parsed as an ISO date, it is returned unchanged
    and was_clamped is False for that value.
    """
    was_clamped = False

    def _parse(s: str | None) -> date | None:
        if s is None:
            return None
        try:
            return date.fromisoformat(s)
        except ValueError:
            return None

    from_date = _parse(date_from)
    to_date = _parse(date_to)

    if from_date is not None:
        clamped = max(ctx.available_data_from, min(from_date, ctx.available_data_to))
        if clamped != from_date:
            from_date = clamped
            was_clamped = True

    if to_date is not None:
        clamped = max(ctx.available_data_from, min(to_date, ctx.available_data_to))
        if clamped != to_date:
            to_date = clamped
            was_clamped = True

    return (
        from_date.isoformat() if from_date is not None else date_from,
        to_date.isoformat() if to_date is not None else date_to,
        was_clamped,
    )


def compact_summary(payload: ToolResultPayload) -> dict[str, Any]:
    """Return compact data for the LLM — first 10 rows only, full payload goes to frontend."""
    result: dict[str, Any] = {
        "title": payload.title,
        "result_type": payload.result_type,
        "description": payload.description,
        "row_count": len(payload.rows),
        "columns": [col.model_dump() for col in payload.columns],
        "rows_preview": payload.rows[:10],
    }
    if payload.result_intent is not None:
        result["result_intent"] = payload.result_intent
    if payload.primary_metric is not None:
        result["primary_metric"] = payload.primary_metric
    if payload.applied_filters:
        result["applied_filters"] = payload.applied_filters
    return result


def annotate_clamped_summary(
    summary: dict[str, Any],
    ctx: AgentRuntimeContext,
    was_clamped: bool,
) -> None:
    """Add a data_range_note to summary if dates were clamped. Mutates summary in place."""
    if was_clamped:
        summary["data_range_note"] = (
            f"Dates were clamped to the available data range "
            f"({ctx.available_data_from} – {ctx.available_data_to}). "
            "Mention this limitation in your response."
        )
