"""Database integration tests for SalesAnalyticsService.

These require the migrated demo database (docker compose postgres on
localhost:5433, migrations + demo data applied).
"""

from __future__ import annotations

from datetime import date

import pytest

from app.contracts.sales import ProductOverviewScope, SalesScope
from app.services.sales_analytics_service import AnalyticsRequestError
from tests.conftest import OTHER_SUPPLIER, SUPPLIER

Q1_2026_START = date(2026, 1, 1)
Q1_2026_END = date(2026, 3, 31)
H1_2026_START = date(2026, 1, 1)
H1_2026_END = date(2026, 6, 30)


# 1
async def test_sales_summary_nordvale(service):
    result = await service.summary(
        supplier_id=SUPPLIER, period_start=None, period_end=None, scope=SalesScope()
    )
    assert result.status == "success"
    assert result.current.units > 0
    assert result.current.orders > 0
    assert result.effective_period.defaulted is True


# 2
async def test_sales_summary_online(service):
    result = await service.summary(
        supplier_id=SUPPLIER,
        period_start=H1_2026_START,
        period_end=H1_2026_END,
        scope=SalesScope(channels=["online"]),
    )
    assert result.status == "success"
    assert result.effective_scope.channels == ["online"]
    # explicit period -> comparison present
    assert result.previous_period is not None
    assert result.changes is not None


# 3
async def test_sales_rank_product_units(service):
    result = await service.rank(
        supplier_id=SUPPLIER,
        group_by="product",
        rank_by="units",
        period_start=None,
        period_end=None,
        scope=SalesScope(),
        limit=10,
    )
    assert result.status == "success"
    assert 1 <= len(result.rows) <= 10
    # ranked descending by units
    unit_values = [row.metrics.units for row in result.rows]
    assert unit_values == sorted(unit_values, reverse=True)
    assert result.rows[0].rank == 1
    assert result.rows[0].entity.id is not None


# 4
async def test_sales_rank_product_units_online(service):
    result = await service.rank(
        supplier_id=SUPPLIER,
        group_by="product",
        rank_by="units",
        period_start=None,
        period_end=None,
        scope=SalesScope(channels=["online"]),
        limit=5,
    )
    assert result.status == "success"
    assert result.rows
    assert result.rows[0].share_of_rank_metric is not None


# 5
async def test_sales_rank_product_stockholm_q1(service):
    result = await service.rank(
        supplier_id=SUPPLIER,
        group_by="product",
        rank_by="units",
        period_start=Q1_2026_START,
        period_end=Q1_2026_END,
        scope=SalesScope(cities=["Stockholm"]),
        limit=10,
    )
    assert result.status == "success"
    assert result.effective_period.start == Q1_2026_START
    assert result.effective_period.end == Q1_2026_END


# 6
async def test_sales_rank_category_net_sales(service):
    result = await service.rank(
        supplier_id=SUPPLIER,
        group_by="category",
        rank_by="net_sales",
        period_start=None,
        period_end=None,
        scope=SalesScope(),
        limit=10,
    )
    assert result.status == "success"
    net_values = [row.metrics.net_sales for row in result.rows]
    assert net_values == sorted(net_values, reverse=True)


# 7
async def test_sales_rank_channel_comparison(service):
    result = await service.rank(
        supplier_id=SUPPLIER,
        group_by="channel",
        rank_by="net_sales",
        period_start=None,
        period_end=None,
        scope=SalesScope(),
        limit=10,
    )
    assert result.status == "success"
    channels = {row.entity.name for row in result.rows}
    assert channels <= {"online", "physical"}
    assert len(result.rows) >= 1


# 8
async def test_sales_trend_monthly_2026(service):
    result = await service.trend(
        supplier_id=SUPPLIER,
        grain="month",
        period_start=H1_2026_START,
        period_end=H1_2026_END,
        scope=SalesScope(),
        split_by=None,
        series_limit=5,
    )
    assert result.status == "success"
    assert [row.period_label for row in result.rows] == [
        "2026-01",
        "2026-02",
        "2026-03",
        "2026-04",
        "2026-05",
        "2026-06",
    ]


# 9
async def test_sales_trend_split_by_channel(service):
    result = await service.trend(
        supplier_id=SUPPLIER,
        grain="month",
        period_start=H1_2026_START,
        period_end=H1_2026_END,
        scope=SalesScope(),
        split_by="channel",
        series_limit=5,
    )
    assert result.status == "success"
    assert result.split_by == "channel"
    assert all(row.series_entity is not None for row in result.rows)
    series = {row.series_entity.name for row in result.rows}
    assert series <= {"online", "physical"}


# 10
async def test_sales_trend_single_product(service):
    result = await service.trend(
        supplier_id=SUPPLIER,
        grain="month",
        period_start=H1_2026_START,
        period_end=H1_2026_END,
        scope=SalesScope(product_ids=["NORD-HOD-011"]),
        split_by=None,
        series_limit=5,
    )
    assert result.status == "success"
    assert result.rows


# 11
async def test_product_overview_exact_id(service):
    result = await service.product_overview(
        supplier_id=SUPPLIER,
        product="NORD-HOD-011",
        period_start=H1_2026_START,
        period_end=H1_2026_END,
        scope=ProductOverviewScope(),
    )
    assert result.status == "success"
    assert result.product.id == "NORD-HOD-011"
    assert result.rank_by_units is not None
    assert result.rank_by_net_sales is not None
    assert result.share_of_supplier_units is not None
    assert result.trend
    assert result.channel_breakdown


# 12
async def test_product_overview_exact_name(service):
    result = await service.product_overview(
        supplier_id=SUPPLIER,
        product="Minimal Logo Hoodie",
        period_start=H1_2026_START,
        period_end=H1_2026_END,
        scope=ProductOverviewScope(),
    )
    assert result.status == "success"
    assert result.product.id == "NORD-HOD-011"


# 13
async def test_product_overview_ambiguous(service):
    result = await service.product_overview(
        supplier_id=SUPPLIER,
        product="Hoodie",
        period_start=None,
        period_end=None,
        scope=ProductOverviewScope(),
    )
    assert result.status == "ambiguous"
    assert len(result.candidates) > 1
    assert all(c.id for c in result.candidates)


async def test_product_overview_not_found(service):
    result = await service.product_overview(
        supplier_id=SUPPLIER,
        product="does-not-exist-zzz",
        period_start=None,
        period_end=None,
        scope=ProductOverviewScope(),
    )
    assert result.status == "not_found"


# 14
async def test_no_data_handling(service):
    result = await service.summary(
        supplier_id=SUPPLIER,
        period_start=date(2020, 1, 1),
        period_end=date(2020, 12, 31),
        scope=SalesScope(),
    )
    assert result.status == "no_data"
    assert result.current is None


# 15
async def test_supplier_isolation(service):
    nordvale = await service.rank(
        supplier_id=SUPPLIER,
        group_by="product",
        rank_by="units",
        period_start=None,
        period_end=None,
        scope=SalesScope(),
        limit=20,
    )
    other = await service.rank(
        supplier_id=OTHER_SUPPLIER,
        group_by="product",
        rank_by="units",
        period_start=None,
        period_end=None,
        scope=SalesScope(),
        limit=20,
    )
    nordvale_ids = {row.entity.id for row in nordvale.rows}
    other_ids = {row.entity.id for row in other.rows}
    assert nordvale_ids
    assert other_ids
    assert nordvale_ids.isdisjoint(other_ids)


# 16
async def test_period_validation(service):
    with pytest.raises(AnalyticsRequestError):
        await service.summary(
            supplier_id=SUPPLIER,
            period_start=date(2026, 1, 1),
            period_end=None,
            scope=SalesScope(),
        )
    with pytest.raises(AnalyticsRequestError):
        await service.summary(
            supplier_id=SUPPLIER,
            period_start=date(2026, 3, 31),
            period_end=date(2026, 1, 1),
            scope=SalesScope(),
        )


# 18
async def test_category_orders_not_summed_from_products(service):
    category = "Hoodies"
    category_rank = await service.rank(
        supplier_id=SUPPLIER,
        group_by="category",
        rank_by="orders",
        period_start=None,
        period_end=None,
        scope=SalesScope(categories=[category]),
        limit=5,
    )
    category_orders = next(
        row.metrics.orders
        for row in category_rank.rows
        if row.entity.name == category
    )

    product_rank = await service.rank(
        supplier_id=SUPPLIER,
        group_by="product",
        rank_by="orders",
        period_start=None,
        period_end=None,
        scope=SalesScope(categories=[category]),
        limit=20,
    )
    product_orders_sum = sum(row.metrics.orders for row in product_rank.rows)

    # A single order can contain several products of the same category, so the
    # summed product-level order counts must exceed the distinct category count.
    assert category_orders > 0
    assert category_orders < product_orders_sum


# ranking direction 1: default is highest (descending)
async def test_sales_rank_defaults_to_highest(service):
    result = await service.rank(
        supplier_id=SUPPLIER,
        group_by="product",
        rank_by="units",
        period_start=None,
        period_end=None,
        scope=SalesScope(),
        limit=5,
    )
    assert result.order == "highest"
    unit_values = [row.metrics.units for row in result.rows]
    assert unit_values == sorted(unit_values, reverse=True)
    assert [row.rank for row in result.rows] == list(range(1, len(result.rows) + 1))


# ranking direction 2: lowest sorts ascending, ranks stay 1..n
async def test_sales_rank_order_lowest_sorts_ascending(service):
    result = await service.rank(
        supplier_id=SUPPLIER,
        group_by="product",
        rank_by="units",
        period_start=None,
        period_end=None,
        scope=SalesScope(),
        limit=5,
        order="lowest",
    )
    assert result.order == "lowest"
    unit_values = [row.metrics.units for row in result.rows]
    assert unit_values == sorted(unit_values)
    assert [row.rank for row in result.rows] == list(range(1, len(result.rows) + 1))


# ranking rows still include both supporting metrics
async def test_ranking_rows_include_supporting_metrics(service):
    result = await service.rank(
        supplier_id=SUPPLIER,
        group_by="product",
        rank_by="units",
        period_start=None,
        period_end=None,
        scope=SalesScope(),
        limit=3,
    )
    top = result.rows[0]
    assert top.metrics.average_selling_price is not None
    assert top.metrics.discount_rate is not None


# product_overview accepts channel/city/store filters
async def test_product_overview_accepts_channel_city_store_filters(service):
    result = await service.product_overview(
        supplier_id=SUPPLIER,
        product="NORD-HOD-011",
        period_start=H1_2026_START,
        period_end=H1_2026_END,
        scope=ProductOverviewScope(
            channels=["online"], cities=["Stockholm"], store_ids=[]
        ),
    )
    assert result.status in {"success", "no_data"}
    assert result.effective_scope.channels == ["online"]
    assert result.effective_scope.cities == ["Stockholm"]


# expected request errors raise AnalyticsRequestError
async def test_expected_request_error_raises_analytics_request_error(service):
    with pytest.raises(AnalyticsRequestError):
        await service.rank(
            supplier_id=SUPPLIER,
            group_by="product",
            rank_by="units",
            period_start=None,
            period_end=date(2026, 3, 31),
            scope=SalesScope(),
            limit=5,
        )



async def test_sales_rank_exposes_population_and_returned_totals(service):
    result = await service.rank(
        supplier_id=SUPPLIER,
        group_by="product",
        rank_by="net_sales",
        period_start=Q1_2026_START,
        period_end=Q1_2026_END,
        scope=SalesScope(),
        limit=5,
    )

    assert result.status == "success"
    assert result.total_population_rank_metric_value is not None
    assert result.returned_rows_rank_metric_value is not None

    returned_sum = round(sum(row.metrics.net_sales for row in result.rows), 4)
    assert result.returned_rows_rank_metric_value == returned_sum
    assert (
        result.total_population_rank_metric_value
        >= result.returned_rows_rank_metric_value
    )


async def test_resolve_product_service_exact_name(service):
    result = await service.resolve_product(
        supplier_id=SUPPLIER,
        product="Minimal Logo Hoodie",
    )
    assert result.status == "success"
    assert result.product is not None
    assert result.product.id == "NORD-HOD-011"


async def test_resolve_product_service_exact_id_is_case_insensitive(service):
    result = await service.resolve_product(
        supplier_id=SUPPLIER,
        product="nord-hod-011",
    )
    assert result.status == "success"
    assert result.product is not None
    assert result.product.id == "NORD-HOD-011"
