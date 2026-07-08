from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.tool_result import ToolResultPayload


class SupplierAnalyticsPort(ABC):
    @abstractmethod
    async def get_sales_summary(
        self,
        supplier_id: str,
        date_from: str,
        date_to: str,
    ) -> ToolResultPayload: ...

    @abstractmethod
    async def get_product_timeseries(
        self,
        supplier_id: str,
        date_from: str,
        date_to: str,
        metric: str,
        grain: str,
    ) -> ToolResultPayload: ...

    @abstractmethod
    async def get_top_products(
        self,
        supplier_id: str,
        date_from: str,
        date_to: str,
        metric: str,
        limit: int,
    ) -> ToolResultPayload: ...

    @abstractmethod
    async def get_store_breakdown(
        self,
        supplier_id: str,
        date_from: str,
        date_to: str,
        metric: str,
        group_by: str,
    ) -> ToolResultPayload: ...
