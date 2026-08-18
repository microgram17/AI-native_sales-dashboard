"""Coordinates repository queries and constructs typed analytics results.

The service owns period resolution, previous-period comparison, share and change
computations, and result-model construction. It never chooses visualizations and
never produces narrative prose.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from app.contracts.sales import (
    AnalyticsEntity,
    BreakdownRow,
    EffectivePeriod,
    GroupBy,
    MetricChange,
    MetricChanges,
    MetricSnapshot,
    ProductOverviewResult,
    ProductResolutionResult,
    ProductOverviewScope,
    RankBy,
    RankedRow,
    RankOrder,
    SalesRankingResult,
    SalesScope,
    SalesSummaryResult,
    SalesTrendResult,
    SplitBy,
    TrendGrain,
    TrendRow,
)
from app.repositories.sales_analytics_repository import SalesAnalyticsRepository


class AnalyticsRequestError(Exception):
    """The requested analytical operation is invalid."""


_STANDARD_METRICS = (
    "units",
    "net_sales",
    "gross_sales",
    "discounts",
    "orders",
    "average_selling_price",
    "discount_rate",
)


def _money(value: Any) -> float:
    return round(float(value or 0), 2)


def _safe_ratio(numerator: Any, denominator: Any, digits: int) -> float | None:
    denom = float(denominator or 0)
    if denom == 0:
        return None
    return round(float(numerator or 0) / denom, digits)


def _period_label(grain: TrendGrain, start: date) -> str:
    if grain == "day":
        return start.isoformat()
    if grain == "week":
        iso = start.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"
    if grain == "month":
        return f"{start.year}-{start.month:02d}"
    quarter = (start.month - 1) // 3 + 1
    return f"{start.year}-Q{quarter}"


class SalesAnalyticsService:
    def __init__(self, repository: SalesAnalyticsRepository) -> None:
        self._repo = repository

    # ── period resolution ────────────────────────────────────────────────────---

    @staticmethod
    def _validate_period(period_start: date | None, period_end: date | None) -> None:
        if (period_start is None) != (period_end is None):
            raise AnalyticsRequestError(
                "period_start and period_end must be supplied together or both omitted"
            )
        if period_start is not None and period_end is not None and period_start > period_end:
            raise AnalyticsRequestError("period_start must be on or before period_end")

    async def _resolve_period(
        self,
        supplier_id: str,
        period_start: date | None,
        period_end: date | None,
    ) -> tuple[EffectivePeriod, EffectivePeriod | None, list[str]]:
        """Return (effective_period, comparison_period, warnings)."""
        self._validate_period(period_start, period_end)
        warnings: list[str] = []

        if period_start is not None and period_end is not None:
            effective = EffectivePeriod(
                start=period_start,
                end=period_end,
                label=f"{period_start.isoformat()} – {period_end.isoformat()}",
                defaulted=False,
            )
            length = (period_end - period_start).days + 1
            prev_end = period_start - timedelta(days=1)
            prev_start = prev_end - timedelta(days=length - 1)
            comparison = EffectivePeriod(
                start=prev_start,
                end=prev_end,
                label=f"{prev_start.isoformat()} – {prev_end.isoformat()}",
                defaulted=False,
            )
            return effective, comparison, warnings

        available = await self._repo.fetch_available_period(supplier_id)
        if available is None:
            today = date.today()
            warnings.append("No sales data is available for this supplier.")
            return (
                EffectivePeriod(start=today, end=today, label="No data", defaulted=True),
                None,
                warnings,
            )
        start, end = available
        warnings.append(
            "No period supplied; using the full available date range. "
            "Period-over-period comparison is not available for the full range."
        )
        return (
            EffectivePeriod(
                start=start,
                end=end,
                label="All available data",
                defaulted=True,
            ),
            None,
            warnings,
        )

    # ── snapshots & changes ──────────────────────────────────────────────────---

    @staticmethod
    def _snapshot(row: dict[str, Any] | None) -> MetricSnapshot | None:
        if row is None:
            return None
        units = int(row["units"] or 0)
        gross = _money(row["gross_sales"])
        net = _money(row["net_sales"])
        discounts = _money(row["discounts"])
        orders = int(row["orders"] or 0)
        return MetricSnapshot(
            units=units,
            net_sales=net,
            gross_sales=gross,
            discounts=discounts,
            orders=orders,
            average_selling_price=_safe_ratio(net, units, 2),
            discount_rate=_safe_ratio(discounts, gross, 4),
        )

    @staticmethod
    def _metric_value(snapshot: MetricSnapshot, metric: str) -> float | None:
        return getattr(snapshot, metric)

    @classmethod
    def _changes(
        cls, current: MetricSnapshot, previous: MetricSnapshot | None
    ) -> MetricChanges:
        changes = MetricChanges()
        for metric in _STANDARD_METRICS:
            current_value = cls._metric_value(current, metric)
            if current_value is None:
                continue
            previous_value = (
                cls._metric_value(previous, metric) if previous is not None else None
            )
            absolute = (
                None if previous_value is None else round(current_value - previous_value, 4)
            )
            percent = (
                None
                if not previous_value
                else round((current_value - previous_value) / previous_value * 100, 2)
            )
            setattr(
                changes,
                metric,
                MetricChange(
                    current=float(current_value),
                    previous=None if previous_value is None else float(previous_value),
                    absolute_change=absolute,
                    percent_change=percent,
                ),
            )
        return changes

    @staticmethod
    def _entity(group_by: GroupBy | SplitBy, row: dict[str, Any]) -> AnalyticsEntity:
        entity_id = row.get("entity_id")
        return AnalyticsEntity(
            type=group_by,
            id=entity_id,
            name=str(row["entity_name"]),
        )

    @staticmethod
    def _entity_key(row: dict[str, Any]) -> str:
        return str(row.get("entity_id") or row["entity_name"])

    # ── tool: summary ─────────────────────────────────────────────────────────---

    async def summary(
        self,
        *,
        supplier_id: str,
        period_start: date | None,
        period_end: date | None,
        scope: SalesScope,
    ) -> SalesSummaryResult:
        effective, comparison, warnings = await self._resolve_period(
            supplier_id, period_start, period_end
        )

        current_row = await self._repo.fetch_summary(
            supplier_id=supplier_id,
            period_start=effective.start,
            period_end=effective.end,
            scope=scope,
        )
        current = self._snapshot(current_row)
        if current is None:
            return SalesSummaryResult(
                status="no_data",
                effective_period=effective,
                effective_scope=scope,
                warnings=warnings,
            )

        previous: MetricSnapshot | None = None
        changes: MetricChanges | None = None
        if comparison is not None:
            previous_row = await self._repo.fetch_summary(
                supplier_id=supplier_id,
                period_start=comparison.start,
                period_end=comparison.end,
                scope=scope,
            )
            previous = self._snapshot(previous_row)
            changes = self._changes(current, previous)

        return SalesSummaryResult(
            status="success",
            effective_period=effective,
            effective_scope=scope,
            warnings=warnings,
            current=current,
            previous_period=comparison if previous is not None else None,
            previous=previous,
            changes=changes,
        )

    # ── tool: rank ────────────────────────────────────────────────────────────---

    async def rank(
        self,
        *,
        supplier_id: str,
        group_by: GroupBy,
        rank_by: RankBy,
        period_start: date | None,
        period_end: date | None,
        scope: SalesScope,
        limit: int,
        order: RankOrder = "highest",
    ) -> SalesRankingResult:
        effective, comparison, warnings = await self._resolve_period(
            supplier_id, period_start, period_end
        )

        rows = await self._repo.fetch_ranking(
            supplier_id=supplier_id,
            group_by=group_by,
            rank_by=rank_by,
            period_start=effective.start,
            period_end=effective.end,
            scope=scope,
            limit=limit,
            order=order,
        )
        if not rows:
            return SalesRankingResult(
                status="no_data",
                group_by=group_by,
                rank_by=rank_by,
                order=order,
                effective_period=effective,
                effective_scope=scope,
                warnings=warnings,
            )

        total_population_value: float | None = None
        total_row = await self._repo.fetch_ranking_total(
            supplier_id=supplier_id,
            group_by=group_by,
            rank_by=rank_by,
            period_start=effective.start,
            period_end=effective.end,
            scope=scope,
        )
        if total_row is not None:
            total_population_value = float(total_row[rank_by] or 0)

        returned_rows_value = round(
            sum(float(row["rank_value"] or 0) for row in rows),
            4,
        )

        if rank_by == "orders":
            warnings.append(
                "share_of_rank_metric for 'orders' is share of order participation; "
                "an order containing several ranked entities is counted in each."
            )

        previous_values: dict[str, float | None] = {}
        if comparison is not None:
            entity_keys = [self._entity_key(row) for row in rows]
            previous_values = await self._repo.fetch_previous_values_for_entities(
                supplier_id=supplier_id,
                group_by=group_by,
                rank_by=rank_by,
                period_start=comparison.start,
                period_end=comparison.end,
                scope=scope,
                entity_keys=entity_keys,
            )

        ranked_rows: list[RankedRow] = []
        for index, row in enumerate(rows, start=1):
            snapshot = self._snapshot(row)
            assert snapshot is not None
            rank_value = None if row["rank_value"] is None else float(row["rank_value"])
            share = (
                None
                if total_population_value in (None, 0) or rank_value is None
                else round(rank_value / total_population_value, 4)
            )
            key = self._entity_key(row)
            previous_value = previous_values.get(key)
            absolute = (
                None
                if previous_value is None or rank_value is None
                else round(rank_value - previous_value, 4)
            )
            percent = (
                None
                if not previous_value or rank_value is None
                else round((rank_value - previous_value) / previous_value * 100, 2)
            )
            ranked_rows.append(
                RankedRow(
                    rank=index,
                    entity=self._entity(group_by, row),
                    metrics=snapshot,
                    share_of_rank_metric=share,
                    previous_rank_metric_value=previous_value,
                    rank_metric_absolute_change=absolute,
                    rank_metric_percent_change=percent,
                )
            )

        return SalesRankingResult(
            status="success",
            group_by=group_by,
            rank_by=rank_by,
            order=order,
            effective_period=effective,
            effective_scope=scope,
            warnings=warnings,
            total_population_rank_metric_value=total_population_value,
            returned_rows_rank_metric_value=returned_rows_value,
            comparison_period=comparison,
            rows=ranked_rows,
        )

    # ── tool: trend ───────────────────────────────────────────────────────────---

    async def trend(
        self,
        *,
        supplier_id: str,
        grain: TrendGrain,
        period_start: date,
        period_end: date,
        scope: SalesScope,
        split_by: SplitBy | None,
        series_limit: int,
    ) -> SalesTrendResult:
        effective, _comparison, warnings = await self._resolve_period(
            supplier_id, period_start, period_end
        )

        series_entity_keys: list[str] | None = None
        if split_by is not None:
            top_rows = await self._repo.fetch_ranking(
                supplier_id=supplier_id,
                group_by=split_by,
                rank_by="net_sales",
                period_start=effective.start,
                period_end=effective.end,
                scope=scope,
                limit=series_limit,
            )
            series_entity_keys = [self._entity_key(row) for row in top_rows]
            warnings.append(
                f"split_by='{split_by}': showing the top {len(series_entity_keys)} "
                f"series by net sales (series_limit={series_limit})."
            )

        rows = await self._repo.fetch_trend(
            supplier_id=supplier_id,
            grain=grain,
            period_start=effective.start,
            period_end=effective.end,
            scope=scope,
            split_by=split_by,
            series_entity_keys=series_entity_keys,
        )
        if not rows:
            return SalesTrendResult(
                status="no_data",
                grain=grain,
                split_by=split_by,
                effective_period=effective,
                effective_scope=scope,
                warnings=warnings,
            )

        trend_rows: list[TrendRow] = []
        for row in rows:
            snapshot = self._snapshot(row)
            assert snapshot is not None
            entity = self._entity(split_by, row) if split_by is not None else None
            period_start_value: date = row["period_start"]
            trend_rows.append(
                TrendRow(
                    period_start=period_start_value,
                    period_label=_period_label(grain, period_start_value),
                    series_entity=entity,
                    metrics=snapshot,
                )
            )

        return SalesTrendResult(
            status="success",
            grain=grain,
            split_by=split_by,
            effective_period=effective,
            effective_scope=scope,
            warnings=warnings,
            rows=trend_rows,
        )

    # ── tool: product_overview ───────────────────────────────────────────────---

    async def product_overview(
        self,
        *,
        supplier_id: str,
        product: str,
        period_start: date | None,
        period_end: date | None,
        scope: ProductOverviewScope,
    ) -> ProductOverviewResult:
        effective, comparison, warnings = await self._resolve_period(
            supplier_id, period_start, period_end
        )

        resolution = await self.resolve_product(
            supplier_id=supplier_id,
            product=product,
        )
        if resolution.status == "not_found":
            warnings.append(f"No product matched '{product}'.")
            return ProductOverviewResult(
                status="not_found",
                effective_period=effective,
                effective_scope=scope,
                warnings=warnings,
            )
        if resolution.status == "ambiguous":
            warnings.append(
                f"'{product}' matched multiple products; refine using a product_id."
            )
            return ProductOverviewResult(
                status="ambiguous",
                effective_period=effective,
                effective_scope=scope,
                warnings=warnings,
                candidates=resolution.candidates,
            )

        product_entity = resolution.product
        if product_entity is None or product_entity.id is None:
            raise AnalyticsRequestError(
                "Product resolution succeeded without a canonical product ID."
            )

        product_id = product_entity.id

        # Overview is scoped to this one product; map the model-visible filters
        # (channels/cities/store_ids) onto an internal SalesScope for the repository.
        product_scope = SalesScope(
            channels=scope.channels,
            cities=scope.cities,
            store_ids=scope.store_ids,
            product_ids=[product_id],
        )

        current_row = await self._repo.fetch_summary(
            supplier_id=supplier_id,
            period_start=effective.start,
            period_end=effective.end,
            scope=product_scope,
        )
        current = self._snapshot(current_row)
        if current is None:
            warnings.append("No sales for this product in the effective period.")
            return ProductOverviewResult(
                status="no_data",
                effective_period=effective,
                effective_scope=scope,
                warnings=warnings,
                product=product_entity,
            )

        previous: MetricSnapshot | None = None
        changes: MetricChanges | None = None
        if comparison is not None:
            previous_row = await self._repo.fetch_summary(
                supplier_id=supplier_id,
                period_start=comparison.start,
                period_end=comparison.end,
                scope=product_scope,
            )
            previous = self._snapshot(previous_row)
            changes = self._changes(current, previous)

        rank_context = await self._repo.fetch_product_rank_context(
            supplier_id=supplier_id,
            product_id=product_id,
            period_start=effective.start,
            period_end=effective.end,
        )
        rank_by_units = None
        rank_by_net_sales = None
        share_units = None
        share_net = None
        if rank_context is not None:
            rank_by_units = int(rank_context["rank_units"])
            rank_by_net_sales = int(rank_context["rank_net"])
            share_units = _safe_ratio(rank_context["u"], rank_context["total_units"], 4)
            share_net = _safe_ratio(rank_context["n"], rank_context["total_net"], 4)

        trend_rows_raw = await self._repo.fetch_trend(
            supplier_id=supplier_id,
            grain="month",
            period_start=effective.start,
            period_end=effective.end,
            scope=product_scope,
            split_by=None,
            series_entity_keys=None,
        )
        trend = [
            TrendRow(
                period_start=row["period_start"],
                period_label=_period_label("month", row["period_start"]),
                series_entity=None,
                metrics=self._snapshot(row),  # type: ignore[arg-type]
            )
            for row in trend_rows_raw
        ]

        channel_breakdown = self._breakdowns(
            "channel",
            current.net_sales,
            await self._repo.fetch_product_channel_breakdown(
                supplier_id=supplier_id,
                product_id=product_id,
                period_start=effective.start,
                period_end=effective.end,
            ),
        )
        city_breakdown = self._breakdowns(
            "city",
            current.net_sales,
            await self._repo.fetch_product_city_breakdown(
                supplier_id=supplier_id,
                product_id=product_id,
                period_start=effective.start,
                period_end=effective.end,
            ),
        )

        return ProductOverviewResult(
            status="success",
            effective_period=effective,
            effective_scope=scope,
            warnings=warnings,
            product=product_entity,
            current=current,
            previous_period=comparison if previous is not None else None,
            previous=previous,
            changes=changes,
            rank_by_units=rank_by_units,
            rank_by_net_sales=rank_by_net_sales,
            share_of_supplier_units=share_units,
            share_of_supplier_net_sales=share_net,
            trend=trend,
            channel_breakdown=channel_breakdown,
            city_breakdown=city_breakdown,
        )

    def _breakdowns(
        self, entity_type: str, total_net: float, rows: list[dict[str, Any]]
    ) -> list[BreakdownRow]:
        result: list[BreakdownRow] = []
        for row in rows:
            snapshot = self._snapshot(row)
            if snapshot is None:
                continue
            share = None if total_net == 0 else round(snapshot.net_sales / total_net, 4)
            result.append(
                BreakdownRow(
                    entity=AnalyticsEntity(
                        type=entity_type,  # type: ignore[arg-type]
                        id=None,
                        name=str(row["entity_name"]),
                    ),
                    metrics=snapshot,
                    share_of_net_sales=share,
                )
            )
        return result

    async def resolve_product(
        self,
        *,
        supplier_id: str,
        product: str,
    ) -> ProductResolutionResult:
        """Resolve one product reference to a canonical supplier-owned product.

        Resolution order is deterministic:
        1. exact canonical ID (case-insensitive)
        2. exact product name (case-insensitive)
        3. partial product name

        Ambiguous partial/exact-name matches are never guessed.
        """

        query = product.strip()
        if not query:
            return ProductResolutionResult(status="not_found")

        exact_id = await self._repo.resolve_product_exact_id(
            supplier_id=supplier_id,
            value=query,
        )
        if exact_id is not None:
            return ProductResolutionResult(
                status="success",
                product=AnalyticsEntity(
                    type="product",
                    id=exact_id["product_id"],
                    name=exact_id["product_name"],
                ),
            )

        exact_name = await self._repo.resolve_product_exact_name(
            supplier_id=supplier_id,
            value=query,
        )
        if len(exact_name) == 1:
            row = exact_name[0]
            return ProductResolutionResult(
                status="success",
                product=AnalyticsEntity(
                    type="product",
                    id=row["product_id"],
                    name=row["product_name"],
                ),
            )
        if len(exact_name) > 1:
            return ProductResolutionResult(
                status="ambiguous",
                candidates=self._candidates(exact_name),
            )

        partial = await self._repo.resolve_product_partial(
            supplier_id=supplier_id,
            value=query,
        )
        if not partial:
            return ProductResolutionResult(status="not_found")
        if len(partial) == 1:
            row = partial[0]
            return ProductResolutionResult(
                status="success",
                product=AnalyticsEntity(
                    type="product",
                    id=row["product_id"],
                    name=row["product_name"],
                ),
            )
        return ProductResolutionResult(
            status="ambiguous",
            candidates=self._candidates(partial),
        )

    @staticmethod
    def _candidates(rows: list[dict[str, Any]]) -> list[AnalyticsEntity]:
        return [
            AnalyticsEntity(type="product", id=row["product_id"], name=row["product_name"])
            for row in rows
        ]
