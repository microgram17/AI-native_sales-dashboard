from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import SupplierSalesMetric, TimeGrain


class SupplierDateRange(BaseModel):
    supplier_id: str = Field(
        ...,
        description="Supplier ID from trusted server-side context. Do not infer from user text.",
    )
    date_from: date | None = None
    date_to: date | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "SupplierDateRange":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from cannot be after date_to")
        return self


class SupplierProductTimeseriesArgs(SupplierDateRange):
    metric: SupplierSalesMetric = "net_sales"
    grain: TimeGrain = "month"
    product_ids: list[str] | None = None


class SupplierTopProductsArgs(SupplierDateRange):
    metric: SupplierSalesMetric = "net_sales"
    limit: int = Field(default=10, ge=1, le=50)


class SupplierSalesSummaryArgs(SupplierDateRange):
    pass


class SupplierStoreBreakdownArgs(SupplierDateRange):
    metric: SupplierSalesMetric = "net_sales"
    group_by: Literal["store", "city", "channel"] = "store"