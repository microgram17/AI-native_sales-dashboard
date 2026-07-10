from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import (
    Column,
    Date,
    Float,
    Integer,
    MetaData,
    Numeric,
    Select,
    String,
    Table,
    cast,
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncEngine

from app.schemas.sales_query import (
    DIMENSION_DISPLAY_KEY,
    DIMENSION_LABELS,
    METRIC_INFO,
    Channel,
    ColumnSpec,
    Dimension,
    Metric,
    SalesFilters,
    SalesOrderBy,
    SalesQuery,
    SalesQueryResult,
    VisualizationSpec,
)


metadata = MetaData()

sales_facts = Table(
    "v_supplier_sales_facts",
    metadata,
    Column("order_item_id", String),
    Column("order_id", String),
    Column("order_date", Date),
    Column("supplier_id", String),
    Column("product_id", String),
    Column("product_name", String),
    Column("category", String),
    Column("store_id", String),
    Column("store_name", String),
    Column("channel", String),
    Column("city", String),
    Column("quantity", Integer),
    Column("gross_sales", Numeric),
    Column("net_sales", Numeric),
    Column("discounts", Numeric),
)


class SalesQueryRepository:
    """Executes composable sales queries over v_supplier_sales_facts.

    This repository is the analytical query compiler. It accepts a safe Pydantic
    query model, maps metrics/dimensions/filters through whitelisted SQLAlchemy
    expressions, and returns a structured result.

    No raw SQL is accepted from the LLM.
    """

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def query_supplier_sales(
        self,
        *,
        supplier_id: str,
        query: SalesQuery,
    ) -> SalesQueryResult:
        compiled = _CompiledQuery.from_query(query)

        stmt = self._build_statement(
            supplier_id=supplier_id,
            query=query,
            compiled=compiled,
        )

        async with self._engine.connect() as conn:
            result = await conn.execute(stmt)
            rows = [dict(row) for row in result.mappings().all()]

        return _build_result(query=query, rows=rows, compiled=compiled)

    def _build_statement(
        self,
        *,
        supplier_id: str,
        query: SalesQuery,
        compiled: "_CompiledQuery",
    ) -> Select:
        f = sales_facts.c

        select_columns = list(compiled.dimension_exprs.values()) + list(compiled.metric_exprs.values())

        stmt = select(*select_columns).where(f.supplier_id == supplier_id)

        filters = query.filters

        if filters.date_from is not None:
            stmt = stmt.where(f.order_date >= filters.date_from)
        if filters.date_to is not None:
            stmt = stmt.where(f.order_date <= filters.date_to)
        if filters.product_ids:
            stmt = stmt.where(f.product_id.in_(filters.product_ids))
        if filters.categories:
            stmt = stmt.where(f.category.in_(filters.categories))
        if filters.store_ids:
            stmt = stmt.where(f.store_id.in_(filters.store_ids))
        if filters.cities:
            stmt = stmt.where(f.city.in_(filters.cities))
        if filters.channels:
            stmt = stmt.where(f.channel.in_(filters.channels))

        if compiled.group_by_exprs:
            stmt = stmt.group_by(*compiled.group_by_exprs)

        if query.order_by is not None:
            order_expr = compiled.order_expr_for(query.order_by)
            stmt = stmt.order_by(order_expr)

        elif "period" in query.dimensions:
            stmt = stmt.order_by(compiled.dimension_exprs["period"].asc())

        elif query.dimensions:
            primary_metric = query.metrics[0]
            stmt = stmt.order_by(compiled.metric_exprs[primary_metric].desc())

        if query.limit is not None:
            stmt = stmt.limit(query.limit)

        return stmt


class _CompiledQuery:
    def __init__(
        self,
        *,
        dimension_exprs: dict[str, Any],
        metric_exprs: dict[str, Any],
        group_by_exprs: list[Any],
        order_field_exprs: dict[str, Any],
    ) -> None:
        self.dimension_exprs = dimension_exprs
        self.metric_exprs = metric_exprs
        self.group_by_exprs = group_by_exprs
        self.order_field_exprs = order_field_exprs

    @classmethod
    def from_query(cls, query: SalesQuery) -> "_CompiledQuery":
        f = sales_facts.c

        dimension_exprs: dict[str, Any] = {}
        group_by_exprs: list[Any] = []
        order_field_exprs: dict[str, Any] = {}

        for dimension in query.dimensions:
            if dimension == "period":
                # query validation guarantees grain is present.
                period_expr = cast(func.date_trunc(query.grain, f.order_date), Date).label("period")
                dimension_exprs["period"] = period_expr
                group_by_exprs.append(period_expr)
                order_field_exprs["period"] = period_expr

            elif dimension == "product":
                product_id = f.product_id.label("product_id")
                product_name = f.product_name.label("product_name")
                dimension_exprs["product_id"] = product_id
                dimension_exprs["product_name"] = product_name
                group_by_exprs.extend([f.product_id, f.product_name])
                order_field_exprs["product"] = product_name
                order_field_exprs["product_id"] = product_id
                order_field_exprs["product_name"] = product_name

            elif dimension == "category":
                category = f.category.label("category")
                dimension_exprs["category"] = category
                group_by_exprs.append(f.category)
                order_field_exprs["category"] = category

            elif dimension == "store":
                store_id = f.store_id.label("store_id")
                store_name = f.store_name.label("store_name")
                dimension_exprs["store_id"] = store_id
                dimension_exprs["store_name"] = store_name
                group_by_exprs.extend([f.store_id, f.store_name])
                order_field_exprs["store"] = store_name
                order_field_exprs["store_id"] = store_id
                order_field_exprs["store_name"] = store_name

            elif dimension == "city":
                city = f.city.label("city")
                dimension_exprs["city"] = city
                group_by_exprs.append(f.city)
                order_field_exprs["city"] = city

            elif dimension == "channel":
                channel = f.channel.label("channel")
                dimension_exprs["channel"] = channel
                group_by_exprs.append(f.channel)
                order_field_exprs["channel"] = channel

        metric_exprs: dict[str, Any] = {}
        for metric in query.metrics:
            expr = _metric_expression(metric).label(metric)
            metric_exprs[metric] = expr
            order_field_exprs[metric] = expr

        return cls(
            dimension_exprs=dimension_exprs,
            metric_exprs=metric_exprs,
            group_by_exprs=group_by_exprs,
            order_field_exprs=order_field_exprs,
        )

    def order_expr_for(self, order_by: SalesOrderBy) -> Any:
        expr = self.order_field_exprs[order_by.field]
        if order_by.direction == "asc":
            return expr.asc()
        return expr.desc()


def _metric_expression(metric: Metric) -> Any:
    f = sales_facts.c

    if metric == "net_sales":
        return cast(func.sum(f.net_sales), Float)
    if metric == "gross_sales":
        return cast(func.sum(f.gross_sales), Float)
    if metric == "units":
        return func.sum(f.quantity)
    if metric == "discounts":
        return cast(func.sum(f.discounts), Float)
    if metric == "orders":
        return func.count(func.distinct(f.order_id))

    raise ValueError(f"Unsupported metric: {metric}")


def _build_result(
    *,
    query: SalesQuery,
    rows: list[dict[str, Any]],
    compiled: _CompiledQuery,
) -> SalesQueryResult:
    primary_metric = query.metrics[0] if query.metrics else None
    primary_dimension = _primary_dimension(query)

    result_type, result_intent = _infer_result_type_and_intent(query)
    columns = _build_columns(query)
    visualization = _build_visualization(query, result_type=result_type, result_intent=result_intent, compiled=compiled)
    title = _build_title(query=query, result_intent=result_intent, primary_metric=primary_metric, primary_dimension=primary_dimension)

    return SalesQueryResult(
        result_type=result_type,
        result_intent=result_intent,
        title=title,
        columns=columns,
        rows=rows,
        metrics=query.metrics,
        dimensions=query.dimensions,
        filters=query.filters,
        primary_metric=primary_metric,
        primary_dimension=primary_dimension,
        recommended_visualization=visualization,
    )


def _primary_dimension(query: SalesQuery) -> Dimension | None:
    for dimension in query.dimensions:
        if dimension != "period":
            return dimension
    if query.dimensions:
        return query.dimensions[0]
    return None


def _infer_result_type_and_intent(query: SalesQuery) -> tuple[str, str]:
    if not query.dimensions:
        return "summary", "summary"

    if "period" in query.dimensions:
        return "timeseries", "timeseries"

    if (
        query.limit == 1
        and query.order_by is not None
        and query.order_by.field in query.metrics
        and query.order_by.direction == "desc"
    ):
        return "ranking", "single_winner"

    if query.order_by is not None and query.order_by.field in query.metrics:
        return "ranking", "ranking"

    return "table", "table"


def _build_columns(query: SalesQuery) -> list[ColumnSpec]:
    columns: list[ColumnSpec] = []

    for dimension in query.dimensions:
        if dimension == "period":
            columns.append(ColumnSpec(key="period", label="Period", type="date"))
        elif dimension == "product":
            columns.extend(
                [
                    ColumnSpec(key="product_id", label="Product ID", type="string"),
                    ColumnSpec(key="product_name", label="Product", type="string"),
                ]
            )
        elif dimension == "category":
            columns.append(ColumnSpec(key="category", label="Category", type="string"))
        elif dimension == "store":
            columns.extend(
                [
                    ColumnSpec(key="store_id", label="Store ID", type="string"),
                    ColumnSpec(key="store_name", label="Store", type="string"),
                ]
            )
        elif dimension == "city":
            columns.append(ColumnSpec(key="city", label="City", type="string"))
        elif dimension == "channel":
            columns.append(ColumnSpec(key="channel", label="Channel", type="string"))

    for metric in query.metrics:
        info = METRIC_INFO[metric]
        columns.append(
            ColumnSpec(
                key=metric,
                label=info.label,
                type=info.column_type,
                unit=info.unit,
            )
        )

    return columns


def _build_visualization(
    query: SalesQuery,
    *,
    result_type: str,
    result_intent: str,
    compiled: _CompiledQuery,
) -> VisualizationSpec | None:
    if result_intent == "single_winner":
        return None

    if result_type == "summary":
        return VisualizationSpec(
            type="metric_cards",
            title="Sales summary",
            y_keys=list(query.metrics),
        )

    primary_metric = query.metrics[0]

    if result_type == "timeseries":
        series_key = _timeseries_series_key(query)
        return VisualizationSpec(
            type="line_chart",
            title=_metric_title(primary_metric, suffix="over time"),
            x_key="period",
            y_keys=[primary_metric],
            series_key=series_key,
        )

    primary_dimension = _primary_dimension(query)
    if primary_dimension is not None:
        return VisualizationSpec(
            type="bar_chart",
            title=_metric_title(primary_metric, suffix=f"by {DIMENSION_LABELS[primary_dimension].lower()}"),
            x_key=DIMENSION_DISPLAY_KEY[primary_dimension],
            y_keys=[primary_metric],
        )

    return VisualizationSpec(type="table", title="Sales results")


def _timeseries_series_key(query: SalesQuery) -> str | None:
    for dimension in query.dimensions:
        if dimension == "period":
            continue
        return DIMENSION_DISPLAY_KEY[dimension]
    return None


def _build_title(
    *,
    query: SalesQuery,
    result_intent: str,
    primary_metric: Metric | None,
    primary_dimension: Dimension | None,
) -> str:
    if primary_metric is None:
        return "Sales results"

    metric_label = METRIC_INFO[primary_metric].label

    if result_intent == "summary":
        return "Sales summary"

    if result_intent == "timeseries":
        if primary_dimension and primary_dimension != "period":
            return f"{metric_label} over time by {DIMENSION_LABELS[primary_dimension].lower()}"
        return f"{metric_label} over time"

    if result_intent == "single_winner":
        if primary_dimension:
            return f"Best {DIMENSION_LABELS[primary_dimension].lower()} by {metric_label.lower()}"
        return f"Best result by {metric_label.lower()}"

    if result_intent == "ranking":
        if primary_dimension:
            return f"{DIMENSION_LABELS[primary_dimension]} ranking by {metric_label.lower()}"
        return f"Ranking by {metric_label.lower()}"

    return "Sales results"


def _metric_title(metric: Metric, *, suffix: str) -> str:
    return f"{METRIC_INFO[metric].label} {suffix}"



