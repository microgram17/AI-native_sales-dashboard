"""Compile canonical analytical intent into an MCP capability + arguments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.integrations.mcp.capabilities import (
    CAP_PRODUCT_OVERVIEW,
    CAP_RANKING,
    CAP_SUMMARY,
    CAP_TREND,
)
from app.schemas.agent import AnalysisRequestState


@dataclass(frozen=True)
class CompiledAnalyticsRequest:
    capability: str
    arguments: dict[str, Any]
    purpose: str


_OPERATION_TO_CAPABILITY = {
    "summary": CAP_SUMMARY,
    "ranking": CAP_RANKING,
    "trend": CAP_TREND,
    "product_overview": CAP_PRODUCT_OVERVIEW,
}


def _period_arguments(request: AnalysisRequestState) -> dict[str, str]:
    if request.period_start is None or request.period_end is None:
        return {}
    return {
        "period_start": request.period_start.isoformat(),
        "period_end": request.period_end.isoformat(),
    }


def _sales_scope(request: AnalysisRequestState) -> dict[str, Any]:
    scope = request.scope.model_dump()
    if request.entity is not None:
        scope["product_ids"] = [request.entity.id]
    return scope


def _product_overview_scope(request: AnalysisRequestState) -> dict[str, Any]:
    return {
        "channels": list(request.scope.channels),
        "cities": list(request.scope.cities),
        "store_ids": list(request.scope.store_ids),
    }


def compile_request(
    request: AnalysisRequestState,
) -> CompiledAnalyticsRequest:
    capability = _OPERATION_TO_CAPABILITY[request.operation]
    arguments: dict[str, Any] = {}
    arguments.update(_period_arguments(request))

    if request.operation == "summary":
        arguments["scope"] = _sales_scope(request)

    elif request.operation == "ranking":
        arguments.update(
            {
                "group_by": request.group_by or "product",
                "rank_by": request.rank_by or "units",
                "scope": _sales_scope(request),
                "limit": request.limit,
                "order": request.rank_order,
            }
        )

    elif request.operation == "trend":
        if request.period_start is None or request.period_end is None:
            raise ValueError("Trend requests require period_start and period_end.")
        arguments.update(
            {
                "grain": request.grain or "month",
                "scope": _sales_scope(request),
                "series_limit": request.series_limit,
            }
        )
        if request.split_by is not None:
            arguments["split_by"] = request.split_by

    elif request.operation == "product_overview":
        if request.entity is None:
            raise ValueError("Product overview requires a resolved product.")
        arguments.update(
            {
                "product": request.entity.id,
                "scope": _product_overview_scope(request),
            }
        )

    return CompiledAnalyticsRequest(
        capability=capability,
        arguments=arguments,
        purpose=f"Execute canonical {request.operation} analysis.",
    )
