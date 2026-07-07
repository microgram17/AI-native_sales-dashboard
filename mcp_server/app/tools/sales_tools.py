from __future__ import annotations

from datetime import date
from typing import Literal

from mcp.server.fastmcp import FastMCP

from app.repositories.sales_repository import SalesRepository
from app.schemas.common import (
    ColumnSpec,
    DataQuality,
    SupplierSalesMetric,
    TimeGrain,
    ToolResult,
    VisualizationSpec,
)


def _metric_label(metric: SupplierSalesMetric) -> str:
    return {
        "net_sales": "Net sales",
        "gross_sales": "Gross sales",
        "units": "Units sold",
        "discounts": "Discounts",
        "orders": "Orders",
    }[metric]


def _metric_column_type(metric: SupplierSalesMetric):
    return {
        "net_sales": "currency",
        "gross_sales": "currency",
        "units": "integer",
        "discounts": "currency",
        "orders": "integer",
    }[metric]


def _metric_unit(metric: SupplierSalesMetric) -> str | None:
    return {
        "net_sales": "SEK",
        "gross_sales": "SEK",
        "units": None,
        "discounts": "SEK",
        "orders": None,
    }[metric]


def _value_column(metric: SupplierSalesMetric) -> ColumnSpec:
    return ColumnSpec(
        key="value",
        label=_metric_label(metric),
        type=_metric_column_type(metric),
        unit=_metric_unit(metric),
    )


def build_product_timeseries_result(
    *,
    rows: list[dict],
    metric: SupplierSalesMetric,
    grain: TimeGrain,
) -> ToolResult:
    return ToolResult(
        result_type="timeseries",
        title=f"{_metric_label(metric)} over time by product",
        description=f"{_metric_label(metric)} grouped by product and {grain}.",
        columns=[
            ColumnSpec(key="period", label="Period", type="date"),
            ColumnSpec(key="product_id", label="Product ID", type="string"),
            ColumnSpec(key="product_name", label="Product", type="string"),
            ColumnSpec(key="category", label="Category", type="string"),
            _value_column(metric),
        ],
        rows=rows,
        recommended_visualizations=[
            VisualizationSpec(
                type="line_chart",
                title=f"{_metric_label(metric)} over time by product",
                x_key="period",
                y_keys=["value"],
                series_key="product_name",
            )
        ],
        data_quality=DataQuality(row_count=len(rows)),
    )


def build_sales_summary_result(*, rows: list[dict]) -> ToolResult:
    return ToolResult(
        result_type="kpi",
        title="Supplier sales summary",
        columns=[
            ColumnSpec(key="gross_sales", label="Gross sales", type="currency", unit="SEK"),
            ColumnSpec(key="net_sales", label="Net sales", type="currency", unit="SEK"),
            ColumnSpec(key="discounts", label="Discounts", type="currency", unit="SEK"),
            ColumnSpec(key="units", label="Units sold", type="integer"),
            ColumnSpec(key="orders", label="Orders", type="integer"),
        ],
        rows=rows,
        recommended_visualizations=[
            VisualizationSpec(type="metric_card", title="Net sales", value_key="net_sales"),
            VisualizationSpec(type="metric_card", title="Units sold", value_key="units"),
            VisualizationSpec(type="metric_card", title="Orders", value_key="orders"),
        ],
        data_quality=DataQuality(row_count=len(rows)),
    )


def build_top_products_result(
    *,
    rows: list[dict],
    metric: SupplierSalesMetric,
    limit: int,
) -> ToolResult:
    return ToolResult(
        result_type="ranking",
        title=f"Top {limit} products by {_metric_label(metric).lower()}",
        columns=[
            ColumnSpec(key="rank", label="Rank", type="integer"),
            ColumnSpec(key="product_id", label="Product ID", type="string"),
            ColumnSpec(key="product_name", label="Product", type="string"),
            ColumnSpec(key="category", label="Category", type="string"),
            _value_column(metric),
        ],
        rows=rows,
        recommended_visualizations=[
            VisualizationSpec(
                type="bar_chart",
                title=f"Top products by {_metric_label(metric).lower()}",
                x_key="product_name",
                y_keys=["value"],
            )
        ],
        data_quality=DataQuality(row_count=len(rows)),
    )


def build_store_breakdown_result(
    *,
    rows: list[dict],
    metric: SupplierSalesMetric,
    group_by: str,
) -> ToolResult:
    return ToolResult(
        result_type="breakdown",
        title=f"{_metric_label(metric)} by {group_by}",
        columns=[
            ColumnSpec(key="group_id", label="Group ID", type="string"),
            ColumnSpec(key="group_name", label="Group", type="string"),
            _value_column(metric),
        ],
        rows=rows,
        recommended_visualizations=[
            VisualizationSpec(
                type="bar_chart",
                title=f"{_metric_label(metric)} by {group_by}",
                x_key="group_name",
                y_keys=["value"],
            )
        ],
        data_quality=DataQuality(row_count=len(rows)),
    )


def register_sales_tools(mcp: FastMCP, repo: SalesRepository) -> None:
    @mcp.tool()
    async def get_current_supplier_product_timeseries(
        supplier_id: str,
        date_from: date | None = None,
        date_to: date | None = None,
        product_ids: list[str] | None = None,
        metric: Literal["net_sales", "gross_sales", "units", "discounts", "orders"] = "net_sales",
        grain: Literal["week", "month"] = "month",
    ) -> dict:
        """
        Get product performance over time for the current supplier.

        supplier_id must come from trusted server-side context.
        Do not ask the user for supplier_id.
        Do not infer supplier_id from user text.
        Use this for product trend questions over time.
        """
        if date_from and date_to and date_from > date_to:
            raise ValueError("date_from cannot be after date_to")

        rows = await repo.fetch_supplier_product_timeseries(
            supplier_id=supplier_id,
            date_from=date_from,
            date_to=date_to,
            product_ids=product_ids,
            metric=metric,
            grain=grain,
        )

        result = build_product_timeseries_result(
            rows=rows,
            metric=metric,
            grain=grain,
        )

        return result.model_dump(mode="json")

    @mcp.tool()
    async def get_current_supplier_sales_summary(
        supplier_id: str,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict:
        """
        Get a sales summary for the current supplier.

        supplier_id must come from trusted server-side context.
        Use this for dashboard summaries and high-level sales overview questions.
        """
        if date_from and date_to and date_from > date_to:
            raise ValueError("date_from cannot be after date_to")

        rows = await repo.fetch_supplier_sales_summary(
            supplier_id=supplier_id,
            date_from=date_from,
            date_to=date_to,
        )

        result = build_sales_summary_result(rows=rows)
        return result.model_dump(mode="json")

    @mcp.tool()
    async def get_current_supplier_top_products(
        supplier_id: str,
        metric: Literal["net_sales", "gross_sales", "units", "discounts", "orders"] = "net_sales",
        limit: int = 10,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict:
        """
        Get top products for the current supplier.

        supplier_id must come from trusted server-side context.
        Use this for product rankings and best/worst performer questions.
        """
        if not (1 <= limit <= 50):
            raise ValueError("limit must be between 1 and 50")

        if date_from and date_to and date_from > date_to:
            raise ValueError("date_from cannot be after date_to")

        rows = await repo.fetch_supplier_top_products(
            supplier_id=supplier_id,
            date_from=date_from,
            date_to=date_to,
            metric=metric,
            limit=limit,
        )

        result = build_top_products_result(
            rows=rows,
            metric=metric,
            limit=limit,
        )

        return result.model_dump(mode="json")

    @mcp.tool()
    async def get_current_supplier_store_breakdown(
        supplier_id: str,
        metric: Literal["net_sales", "gross_sales", "units", "discounts", "orders"] = "net_sales",
        group_by: Literal["store", "city", "channel"] = "store",
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict:
        """
        Get store, city, or channel breakdown for the current supplier.

        supplier_id must come from trusted server-side context.
        Use this for questions about stores, cities, or online versus physical sales.
        """
        if date_from and date_to and date_from > date_to:
            raise ValueError("date_from cannot be after date_to")

        rows = await repo.fetch_supplier_store_breakdown(
            supplier_id=supplier_id,
            date_from=date_from,
            date_to=date_to,
            metric=metric,
            group_by=group_by,
        )

        result = build_store_breakdown_result(
            rows=rows,
            metric=metric,
            group_by=group_by,
        )

        return result.model_dump(mode="json")