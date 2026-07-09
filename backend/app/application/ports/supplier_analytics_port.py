from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.tool_result import ToolResultPayload


class SupplierAnalyticsPort(ABC):
    @abstractmethod
    async def get_sales_summary(
        self,
        supplier_id: str,
        date_from: str | None,
        date_to: str | None,
    ) -> ToolResultPayload: ...

    @abstractmethod
    async def get_product_timeseries(
        self,
        supplier_id: str,
        date_from: str | None,
        date_to: str | None,
        metric: str,
        grain: str,
        product_ids: list[str] | None = None,
        limit_products: int = 5,
    ) -> ToolResultPayload: ...

    @abstractmethod
    async def get_top_products(
        self,
        supplier_id: str,
        date_from: str | None,
        date_to: str | None,
        sort_by: str,
        limit: int,
    ) -> ToolResultPayload: ...

    @abstractmethod
    async def get_store_breakdown(
        self,
        supplier_id: str,
        date_from: str | None,
        date_to: str | None,
        metric: str,
        group_by: str,
    ) -> ToolResultPayload: ...

    @abstractmethod
    async def get_supplier_products(
        self,
        supplier_id: str,
        date_from: str | None,
        date_to: str | None,
    ) -> ToolResultPayload: ...

    @abstractmethod
    async def get_ranked_products(
        self,
        supplier_id: str,
        date_from: str | None,
        date_to: str | None,
        metric: str,
        limit: int,
        city: str | None = None,
        store_id: str | None = None,
        channel: str | None = None,
        category: str | None = None,
    ) -> ToolResultPayload: ...

    @abstractmethod
    async def get_ranked_locations(
        self,
        supplier_id: str,
        date_from: str | None,
        date_to: str | None,
        metric: str,
        group_by: str,
        limit: int,
        category: str | None = None,
        product_id: str | None = None,
    ) -> ToolResultPayload: ...

    @abstractmethod
    async def get_filter_values(
        self,
        supplier_id: str,
    ) -> ToolResultPayload: ...
