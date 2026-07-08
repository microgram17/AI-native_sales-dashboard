from __future__ import annotations

import asyncio

from app.application.ports.supplier_analytics_port import SupplierAnalyticsPort
from app.domain.dashboard import DashboardArtifact, DashboardResponse, KpiCard, UserInfo
from app.domain.tool_result import ToolResultPayload
from app.domain.user_context import UserContext

# --- Dashboard filter defaults ---
_DATE_FROM = "2024-01-01"
_DATE_TO = "2026-06-30"
_METRIC = "net_sales"
_GRAIN = "month"
_TOP_LIMIT = 10
_STORE_GROUP_BY = "store"

# Keys to surface as KPI cards (order preserved in response)
_KPI_KEYS = ["net_sales", "gross_sales", "units", "orders"]


def _extract_kpi_cards(payload: ToolResultPayload) -> list[KpiCard]:
    if not payload.rows:
        return []

    row = payload.rows[0]
    col_meta = {col.key: col for col in payload.columns}
    cards: list[KpiCard] = []

    for key in _KPI_KEYS:
        if key not in row:
            continue
        col = col_meta.get(key)
        cards.append(
            KpiCard(
                key=key,
                label=col.label if col else key,
                value=float(row[key] or 0),
                unit=col.unit if col else None,
            )
        )

    return cards


class DashboardService:
    def __init__(self, port: SupplierAnalyticsPort) -> None:
        self._port = port

    async def get_dashboard(self, user: UserContext) -> DashboardResponse:
        sid = user.supplier_id

        summary, timeseries, top_products, store_breakdown = await asyncio.gather(
            self._port.get_sales_summary(sid, _DATE_FROM, _DATE_TO),
            self._port.get_product_timeseries(sid, _DATE_FROM, _DATE_TO, _METRIC, _GRAIN),
            self._port.get_top_products(sid, _DATE_FROM, _DATE_TO, _METRIC, _TOP_LIMIT),
            self._port.get_store_breakdown(sid, _DATE_FROM, _DATE_TO, _METRIC, _STORE_GROUP_BY),
        )

        cards = _extract_kpi_cards(summary)

        artifacts = [
            DashboardArtifact.from_tool_result("get_current_supplier_sales_summary", summary),
            DashboardArtifact.from_tool_result("get_current_supplier_product_timeseries", timeseries),
            DashboardArtifact.from_tool_result("get_current_supplier_top_products", top_products),
            DashboardArtifact.from_tool_result("get_current_supplier_store_breakdown", store_breakdown),
        ]

        return DashboardResponse(
            user=UserInfo(
                user_id=user.user_id,
                display_name=user.display_name,
                supplier_id=user.supplier_id,
            ),
            cards=cards,
            artifacts=artifacts,
        )
