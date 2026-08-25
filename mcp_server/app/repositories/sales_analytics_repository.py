"""Database access for the supplier sales analytics tools.

Contains only parameterized queries against the analytical daily views and the
supplier sales facts view. It makes no authorization decisions, chooses no
visualizations and produces no narrative text.

Distinct order counts are not additive across the entity axis, so the correct
daily view is selected per requested dimension:

- product entity / product_ids scope -> v_product_store_daily_sales
- category entity / categories scope  -> v_category_store_daily_sales
- store/city/channel or no entity     -> v_supplier_store_daily_sales
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import (
    Column,
    Date,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    and_,
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncEngine

from app.contracts.sales import GroupBy, RankBy, RankOrder, SalesScope, TrendGrain

_metadata = MetaData()


def _daily_view(name: str, *, product: bool = False, category: bool = False) -> Table:
    columns = [
        Column("supplier_id", String),
        Column("sales_date", Date),
    ]
    if product:
        columns += [Column("product_id", String), Column("product_name", String)]
    if product or category:
        columns.append(Column("category", String))
    columns += [
        Column("store_id", String),
        Column("store_name", String),
        Column("city", String),
        Column("channel", String),
        Column("units", Integer),
        Column("gross_sales", Numeric),
        Column("net_sales", Numeric),
        Column("discounts", Numeric),
        Column("orders", Integer),
    ]
    return Table(name, _metadata, *columns)


product_daily = _daily_view("v_product_store_daily_sales", product=True)
category_daily = _daily_view("v_category_store_daily_sales", category=True)
supplier_daily = _daily_view("v_supplier_store_daily_sales")

sales_facts = Table(
    "v_supplier_sales_facts",
    _metadata,
    Column("supplier_id", String),
    Column("order_date", Date),
    Column("product_id", String),
    Column("product_name", String),
)

products = Table(
    "products",
    _metadata,
    Column("product_id", String),
    Column("product_name", String),
    Column("supplier_id", String),
)


# Entity dimension -> (id column name | None, name column name)
_ENTITY_COLUMNS: dict[str, tuple[str | None, str]] = {
    "product": ("product_id", "product_name"),
    "category": (None, "category"),
    "store": ("store_id", "store_name"),
    "city": (None, "city"),
    "channel": (None, "channel"),
}


class SalesAnalyticsRepository:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    # ── helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _view_for(entity: str | None, scope: SalesScope) -> Table:
        if entity == "product" or scope.product_ids:
            return product_daily
        if entity == "category" or scope.categories:
            return category_daily
        return supplier_daily

    @staticmethod
    def _measure_columns(view: Table) -> list[Any]:
        return [
            func.coalesce(func.sum(view.c.units), 0).label("units"),
            func.coalesce(func.sum(view.c.gross_sales), 0).label("gross_sales"),
            func.coalesce(func.sum(view.c.net_sales), 0).label("net_sales"),
            func.coalesce(func.sum(view.c.discounts), 0).label("discounts"),
            func.coalesce(func.sum(view.c.orders), 0).label("orders"),
        ]

    @staticmethod
    def _rank_expression(view: Table, rank_by: RankBy) -> Any:
        # rank_by is restricted to additive measures, so a plain sum is correct.
        return func.coalesce(func.sum(view.c[rank_by]), 0)

    @staticmethod
    def _scope_conditions(view: Table, supplier_id: str, scope: SalesScope) -> list[Any]:
        cols = view.c.keys()
        conditions = [view.c.supplier_id == supplier_id]
        if scope.channels and "channel" in cols:
            conditions.append(view.c.channel.in_(scope.channels))
        if scope.cities and "city" in cols:
            conditions.append(view.c.city.in_(scope.cities))
        if scope.store_ids and "store_id" in cols:
            conditions.append(view.c.store_id.in_(scope.store_ids))
        if scope.categories and "category" in cols:
            conditions.append(view.c.category.in_(scope.categories))
        if scope.product_ids and "product_id" in cols:
            conditions.append(view.c.product_id.in_(scope.product_ids))
        return conditions

    async def _fetch_all(self, stmt: Any) -> list[dict[str, Any]]:
        async with self._engine.connect() as conn:
            result = await conn.execute(stmt)
            return [dict(row) for row in result.mappings().all()]

    async def _fetch_one(self, stmt: Any) -> dict[str, Any] | None:
        rows = await self._fetch_all(stmt)
        return rows[0] if rows else None

    # ── period ──────────────────────────────────────────────────────────────────

    async def fetch_available_period(self, supplier_id: str) -> tuple[date, date] | None:
        stmt = select(
            func.min(sales_facts.c.order_date).label("start"),
            func.max(sales_facts.c.order_date).label("end"),
        ).where(sales_facts.c.supplier_id == supplier_id)
        row = await self._fetch_one(stmt)
        if row is None or row["start"] is None or row["end"] is None:
            return None
        return row["start"], row["end"]

    # ── summary ───────────────────────────────────────────────────────────────---

    async def fetch_summary(
        self,
        *,
        supplier_id: str,
        period_start: date,
        period_end: date,
        scope: SalesScope,
    ) -> dict[str, Any] | None:
        view = self._view_for(None, scope)
        conditions = self._scope_conditions(view, supplier_id, scope)
        conditions.append(view.c.sales_date.between(period_start, period_end))
        stmt = select(*self._measure_columns(view)).where(and_(*conditions))
        row = await self._fetch_one(stmt)
        if row is None or row["orders"] == 0 and row["units"] == 0:
            return None
        return row

    # ── ranking ───────────────────────────────────────────────────────────────---

    async def fetch_ranking(
        self,
        *,
        supplier_id: str,
        group_by: GroupBy,
        rank_by: RankBy,
        period_start: date,
        period_end: date,
        scope: SalesScope,
        limit: int,
        order: RankOrder = "highest",
    ) -> list[dict[str, Any]]:
        view = self._view_for(group_by, scope)
        id_name, name_name = _ENTITY_COLUMNS[group_by]

        group_cols: list[Any] = []
        select_cols: list[Any] = []
        if id_name is not None:
            id_col = view.c[id_name].label("entity_id")
            select_cols.append(id_col)
            group_cols.append(view.c[id_name])
        name_col = view.c[name_name].label("entity_name")
        select_cols.append(name_col)
        group_cols.append(view.c[name_name])

        select_cols += self._measure_columns(view)
        rank_expr = self._rank_expression(view, rank_by).label("rank_value")
        select_cols.append(rank_expr)

        conditions = self._scope_conditions(view, supplier_id, scope)
        conditions.append(view.c.sales_date.between(period_start, period_end))

        ordering = rank_expr.asc() if order == "lowest" else rank_expr.desc()
        stmt = (
            select(*select_cols)
            .where(and_(*conditions))
            .group_by(*group_cols)
            .order_by(ordering.nullslast())
            .limit(limit)
        )
        return await self._fetch_all(stmt)

    async def fetch_ranking_total(
        self,
        *,
        supplier_id: str,
        group_by: GroupBy,
        rank_by: RankBy,
        period_start: date,
        period_end: date,
        scope: SalesScope,
    ) -> dict[str, Any] | None:
        """Aggregate the ranking view across all entities.

        Used as the denominator for share_of_rank_metric so that shares are
        consistent with the per-entity rows (same view).
        """
        view = self._view_for(group_by, scope)
        conditions = self._scope_conditions(view, supplier_id, scope)
        conditions.append(view.c.sales_date.between(period_start, period_end))
        stmt = select(*self._measure_columns(view)).where(and_(*conditions))
        return await self._fetch_one(stmt)

    async def fetch_previous_values_for_entities(
        self,
        *,
        supplier_id: str,
        group_by: GroupBy,
        rank_by: RankBy,
        period_start: date,
        period_end: date,
        scope: SalesScope,
        entity_keys: list[str],
    ) -> dict[str, float | None]:
        if not entity_keys:
            return {}
        view = self._view_for(group_by, scope)
        id_name, name_name = _ENTITY_COLUMNS[group_by]
        key_name = id_name or name_name
        key_col = view.c[key_name].label("entity_key")
        rank_expr = self._rank_expression(view, rank_by).label("rank_value")

        conditions = self._scope_conditions(view, supplier_id, scope)
        conditions.append(view.c.sales_date.between(period_start, period_end))
        conditions.append(view.c[key_name].in_(entity_keys))

        stmt = select(key_col, rank_expr).where(and_(*conditions)).group_by(view.c[key_name])
        rows = await self._fetch_all(stmt)
        return {
            row["entity_key"]: (None if row["rank_value"] is None else float(row["rank_value"]))
            for row in rows
        }

    # ── trend ─────────────────────────────────────────────────────────────────---

    async def fetch_trend(
        self,
        *,
        supplier_id: str,
        grain: TrendGrain,
        period_start: date,
        period_end: date,
        scope: SalesScope,
        split_by: GroupBy | None = None,
        series_entity_keys: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        view = self._view_for(split_by, scope)
        period_col = func.date_trunc(grain, view.c.sales_date).cast(Date)

        select_cols: list[Any] = [period_col.label("period_start")]
        group_cols: list[Any] = [period_col]

        key_name: str | None = None
        if split_by is not None:
            id_name, name_name = _ENTITY_COLUMNS[split_by]
            key_name = id_name or name_name
            if id_name is not None:
                select_cols.append(view.c[id_name].label("entity_id"))
                group_cols.append(view.c[id_name])
            select_cols.append(view.c[name_name].label("entity_name"))
            group_cols.append(view.c[name_name])

        select_cols += self._measure_columns(view)

        conditions = self._scope_conditions(view, supplier_id, scope)
        conditions.append(view.c.sales_date.between(period_start, period_end))
        if split_by is not None and series_entity_keys is not None:
            conditions.append(view.c[key_name].in_(series_entity_keys))

        stmt = (
            select(*select_cols)
            .where(and_(*conditions))
            .group_by(*group_cols)
            .order_by(period_col.asc())
        )
        return await self._fetch_all(stmt)

    # ── product resolution & overview ───────────────────────────────────────────

    async def resolve_product_exact_id(
        self, *, supplier_id: str, value: str
    ) -> dict[str, Any] | None:
        stmt = select(
            products.c.product_id, products.c.product_name
        ).where(
            and_(
                products.c.supplier_id == supplier_id,
                func.lower(products.c.product_id) == value.lower(),
            )
        )
        return await self._fetch_one(stmt)

    async def resolve_product_exact_name(
        self, *, supplier_id: str, value: str
    ) -> list[dict[str, Any]]:
        stmt = select(products.c.product_id, products.c.product_name).where(
            and_(
                products.c.supplier_id == supplier_id,
                func.lower(products.c.product_name) == value.lower(),
            )
        )
        return await self._fetch_all(stmt)

    async def resolve_product_partial(
        self, *, supplier_id: str, value: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        escaped = (
            value.replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )
        pattern = f"%{escaped}%"
        stmt = (
            select(products.c.product_id, products.c.product_name)
            .where(
                and_(
                    products.c.supplier_id == supplier_id,
                    products.c.product_name.ilike(pattern, escape="\\"),
                )
            )
            .order_by(products.c.product_name.asc())
            .limit(limit)
        )
        return await self._fetch_all(stmt)

    async def list_products_for_resolution(
        self,
        *,
        supplier_id: str,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        """Return supplier product identities for conservative typo fallback.

        Exact and substring matching run first. The catalogue is only scanned
        when those deterministic paths fail.
        """
        stmt = (
            select(
                products.c.product_id,
                products.c.product_name,
            )
            .where(
                products.c.supplier_id
                == supplier_id
            )
            .order_by(
                products.c.product_name.asc()
            )
            .limit(limit)
        )
        return await self._fetch_all(stmt)

    async def fetch_product_rank_context(
        self,
        *,
        supplier_id: str,
        product_id: str,
        period_start: date,
        period_end: date,
    ) -> dict[str, Any] | None:
        """Rank of the product among all supplier products, plus supplier totals.

        Uses v_product_store_daily_sales (product grain) with window functions.
        """
        view = product_daily
        agg = (
            select(
                view.c.product_id.label("product_id"),
                func.sum(view.c.units).label("u"),
                func.sum(view.c.net_sales).label("n"),
            )
            .where(
                and_(
                    view.c.supplier_id == supplier_id,
                    view.c.sales_date.between(period_start, period_end),
                )
            )
            .group_by(view.c.product_id)
            .subquery("agg")
        )
        ranked = select(
            agg.c.product_id,
            agg.c.u,
            agg.c.n,
            func.rank().over(order_by=agg.c.u.desc()).label("rank_units"),
            func.rank().over(order_by=agg.c.n.desc()).label("rank_net"),
            func.sum(agg.c.u).over().label("total_units"),
            func.sum(agg.c.n).over().label("total_net"),
        ).subquery("ranked")

        stmt = select(
            ranked.c.rank_units,
            ranked.c.rank_net,
            ranked.c.u,
            ranked.c.n,
            ranked.c.total_units,
            ranked.c.total_net,
        ).where(ranked.c.product_id == product_id)
        return await self._fetch_one(stmt)

    async def fetch_product_channel_breakdown(
        self, *, supplier_id: str, product_id: str, period_start: date, period_end: date
    ) -> list[dict[str, Any]]:
        return await self._fetch_entity_breakdown(
            supplier_id=supplier_id,
            product_id=product_id,
            period_start=period_start,
            period_end=period_end,
            dimension="channel",
        )

    async def fetch_product_city_breakdown(
        self, *, supplier_id: str, product_id: str, period_start: date, period_end: date
    ) -> list[dict[str, Any]]:
        return await self._fetch_entity_breakdown(
            supplier_id=supplier_id,
            product_id=product_id,
            period_start=period_start,
            period_end=period_end,
            dimension="city",
        )

    async def _fetch_entity_breakdown(
        self,
        *,
        supplier_id: str,
        product_id: str,
        period_start: date,
        period_end: date,
        dimension: str,
    ) -> list[dict[str, Any]]:
        view = product_daily
        dim_col = view.c[dimension].label("entity_name")
        stmt = (
            select(dim_col, *self._measure_columns(view))
            .where(
                and_(
                    view.c.supplier_id == supplier_id,
                    view.c.product_id == product_id,
                    view.c.sales_date.between(period_start, period_end),
                )
            )
            .group_by(view.c[dimension])
            .order_by(func.coalesce(func.sum(view.c.net_sales), 0).desc())
        )
        return await self._fetch_all(stmt)
