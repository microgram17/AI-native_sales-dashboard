import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { dashboardApi } from '../../api/dashboard'
import type { Grain, Metric, StoreGroupBy } from '../../types/dashboard'
import { KpiCard } from './components/KpiCard'
import { ProductTimeseriesChart } from './components/ProductTimeseriesChart'
import { TopProductsTable } from './components/TopProductsTable'
import { StoreBreakdownChart } from './components/StoreBreakdownChart'
import { ChatPanel } from '../../components/chat/ChatPanel'
import { ExportableRegion } from '../../components/export/ExportableRegion'
import type { ExportColumn, ExportFilter } from '../../lib/export/exportTypes'
import {
  visualizationFieldLabel,
  visualizationValueLabel,
} from '../../i18n/translations'
import { useTranslation } from '../../i18n/LanguageContext'
import { useTheme } from '../../i18n/ThemeContext'

function formatCardValue(value: number, unit: string | null): string {
  if (unit === 'SEK') {
    return new Intl.NumberFormat('sv-SE', {
      style: 'currency',
      currency: 'SEK',
      maximumFractionDigits: 0,
    }).format(value)
  }

  return value.toLocaleString('sv-SE', {
    maximumFractionDigits: 0,
  })
}

function parseIsoDate(value: string): Date | null {
  const [year, month, day] = value
    .split('-')
    .map((part) => Number(part))

  if (!year || !month || !day) return null

  const parsed = new Date(Date.UTC(year, month - 1, day))
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

function formatIsoDate(value: Date): string {
  return value.toISOString().slice(0, 10)
}

function previousPeriod(
  dateFrom: string,
  dateTo: string,
): { date_from: string; date_to: string } | null {
  const from = parseIsoDate(dateFrom)
  const to = parseIsoDate(dateTo)

  if (!from || !to || to < from) return null

  const dayMs = 24 * 60 * 60 * 1000
  const durationDays =
    Math.round((to.getTime() - from.getTime()) / dayMs) + 1

  const previousTo = new Date(from.getTime() - dayMs)
  const previousFrom = new Date(
    previousTo.getTime() - (durationDays - 1) * dayMs,
  )

  return {
    date_from: formatIsoDate(previousFrom),
    date_to: formatIsoDate(previousTo),
  }
}

function percentChange(
  current: number,
  previous: number | undefined,
): number | null {
  if (
    previous === undefined ||
    previous === null ||
    previous === 0
  ) {
    return null
  }

  return ((current - previous) / previous) * 100
}

function uniqueProductIds(
  rows: { product_id: string }[],
): string[] {
  return Array.from(
    new Set(
      rows
        .map((row) => row.product_id)
        .filter(Boolean),
    ),
  )
}

export function DashboardPage() {
  const { language, setLanguage, t } = useTranslation()
  const { theme, toggleTheme } = useTheme()

  // Shared date range.
  const [dateFrom, setDateFrom] = useState('2025-07-01')
  const [dateTo, setDateTo] = useState('2026-06-30')

  // Timeseries-specific filters.
  const [grain, setGrain] = useState<Grain>('month')
  const [metric, setMetric] = useState<Metric>('net_sales')

  // null means "let the backend choose the initial top 5".
  // [] means the user explicitly cleared the selection.
  const [selectedProductIds, setSelectedProductIds] =
    useState<string[] | null>(null)

  // Top products filter.
  const [topSortBy, setTopSortBy] =
    useState<Metric>('net_sales')

  // Store breakdown filter.
  const [storeMetric, setStoreMetric] =
    useState<Metric>('net_sales')
  const [storeGroupBy, setStoreGroupBy] =
    useState<StoreGroupBy>('store')

  const comparisonPeriod = previousPeriod(dateFrom, dateTo)

  // Current KPI summary.
  const {
    data: summary,
    isLoading: summaryLoading,
  } = useQuery({
    queryKey: ['summary', dateFrom, dateTo],
    queryFn: () =>
      dashboardApi.getSummary({
        date_from: dateFrom,
        date_to: dateTo,
      }),
  })

  // Same-length immediately preceding period for KPI comparisons.
  const {
    data: previousSummary,
    isLoading: previousSummaryLoading,
  } = useQuery({
    queryKey: [
      'summary-previous',
      comparisonPeriod?.date_from ?? '',
      comparisonPeriod?.date_to ?? '',
    ],
    queryFn: () => {
      if (!comparisonPeriod) {
        throw new Error('No valid comparison period.')
      }

      return dashboardApi.getSummary(comparisonPeriod)
    },
    enabled: comparisonPeriod !== null,
  })

  const explicitEmptyProductSelection =
    selectedProductIds !== null &&
    selectedProductIds.length === 0

  const productIdsParam =
    selectedProductIds && selectedProductIds.length > 0
      ? [...selectedProductIds].sort().join(',')
      : undefined

  // Product timeseries widget.
  const {
    data: timeseries,
    isLoading: timeseriesLoading,
  } = useQuery({
    queryKey: [
      'product-timeseries',
      dateFrom,
      dateTo,
      grain,
      metric,
      productIdsParam ?? '',
      explicitEmptyProductSelection ? 'empty' : 'active',
    ],
    queryFn: () =>
      dashboardApi.getProductTimeseries({
        date_from: dateFrom,
        date_to: dateTo,
        grain,
        metric,
        product_ids: productIdsParam,
        limit_products: 5,
      }),
    enabled: !explicitEmptyProductSelection,
  })

  // The first unfiltered response is the actual backend-selected top 5.
  // Promote those IDs into explicit UI state so the checkboxes match the chart.
  const backendDefaultProductIds = uniqueProductIds(
    timeseries?.rows ?? [],
  ).slice(0, 5)

  const displayedProductIds =
    selectedProductIds ?? backendDefaultProductIds

  useEffect(() => {
    if (
      selectedProductIds !== null ||
      backendDefaultProductIds.length === 0
    ) {
      return
    }

    setSelectedProductIds(backendDefaultProductIds)
  }, [backendDefaultProductIds, selectedProductIds])

  // A new date range should get a fresh top-5 default for that period.
  useEffect(() => {
    setSelectedProductIds(null)
  }, [dateFrom, dateTo])

  // Top products widget.
  const {
    data: topProducts,
    isLoading: topLoading,
  } = useQuery({
    queryKey: [
      'top-products',
      dateFrom,
      dateTo,
      topSortBy,
    ],
    queryFn: () =>
      dashboardApi.getTopProducts({
        date_from: dateFrom,
        date_to: dateTo,
        sort_by: topSortBy,
        limit: 10,
      }),
  })

  // Product selector options.
  const { data: productsData } = useQuery({
    queryKey: ['products', dateFrom, dateTo],
    queryFn: () =>
      dashboardApi.getProducts({
        date_from: dateFrom,
        date_to: dateTo,
      }),
  })

  // Store breakdown with user-selectable metric.
  const {
    data: storeBreakdown,
    isLoading: storeBreakdownLoading,
  } = useQuery({
    queryKey: [
      'store-breakdown',
      dateFrom,
      dateTo,
      storeMetric,
      storeGroupBy,
    ],
    queryFn: () =>
      dashboardApi.getStoreBreakdown({
        date_from: dateFrom,
        date_to: dateTo,
        metric: storeMetric,
        group_by: storeGroupBy,
      }),
  })

  const metricLabels: Record<Metric, string> = {
    net_sales: t.netSales,
    gross_sales: t.grossSales,
    units: t.unitsSold,
    orders: t.orders,
    discounts: t.discounts,
  }

  const productTrendTitle =
    t.productTrendTitle(metricLabels[metric])

  const sharedFilters: ExportFilter[] = [
    { label: t.dateFrom, value: dateFrom },
    { label: t.dateTo, value: dateTo },
  ]

  const summaryRows: Record<string, unknown>[] = summary
    ? [
        {
          net_sales: summary.net_sales,
          gross_sales: summary.gross_sales,
          units: summary.units,
          orders: summary.orders,
        },
      ]
    : []

  const summaryColumns: ExportColumn[] = [
    { key: 'net_sales', label: t.netSales },
    { key: 'gross_sales', label: t.grossSales },
    { key: 'units', label: t.unitsSold },
    { key: 'orders', label: t.orders },
  ]

  const selectedProductNames =
    displayedProductIds.length > 0
      ? (productsData?.products ?? [])
          .filter((product) =>
            displayedProductIds.includes(product.product_id),
          )
          .map((product) => product.product_name)
      : [t.productsNoneSelected]

  const visibleTimeseriesRows =
    explicitEmptyProductSelection
      ? []
      : timeseries?.rows ?? []

  const timeseriesColumns: ExportColumn[] = [
    {
      key: 'period',
      label: visualizationFieldLabel(language, 'period'),
    },
    {
      key: 'product_id',
      label: visualizationFieldLabel(language, 'product_id'),
    },
    {
      key: 'product_name',
      label: visualizationFieldLabel(language, 'product_name'),
    },
    {
      key: 'category',
      label: visualizationFieldLabel(language, 'category'),
    },
    {
      key: 'value',
      label: metricLabels[metric],
    },
  ]

  const timeseriesFilters: ExportFilter[] = [
    ...sharedFilters,
    {
      label: t.grain,
      value:
        grain === 'month'
          ? t.grainMonth
          : t.grainWeek,
    },
    {
      label: t.metric,
      value: metricLabels[metric],
    },
    {
      label: visualizationFieldLabel(
        language,
        'product_ids',
      ),
      value: selectedProductNames,
    },
  ]

  const topProductColumns: ExportColumn[] = [
    {
      key: 'rank',
      label: visualizationFieldLabel(language, 'rank'),
    },
    {
      key: 'product_id',
      label: visualizationFieldLabel(
        language,
        'product_id',
      ),
    },
    {
      key: 'product_name',
      label: t.colProduct,
    },
    {
      key: 'category',
      label: t.colCategory,
    },
    { key: 'net_sales', label: t.netSales },
    { key: 'gross_sales', label: t.grossSales },
    { key: 'units', label: t.unitsSold },
    { key: 'orders', label: t.orders },
    { key: 'discounts', label: t.discounts },
  ]

  const topProductFilters: ExportFilter[] = [
    ...sharedFilters,
    {
      label: t.exportSortedBy,
      value: metricLabels[topSortBy],
    },
    {
      label: visualizationFieldLabel(language, 'limit'),
      value: 10,
    },
  ]

  const storeColumns: ExportColumn[] = [
    {
      key: 'group_id',
      label: visualizationFieldLabel(
        language,
        'store_id',
      ),
    },
    {
      key: 'group_name',
      label: visualizationFieldLabel(
        language,
        'store_name',
      ),
    },
    {
      key: 'value',
      label: metricLabels[storeMetric],
    },
  ]

  const storeFilters: ExportFilter[] = [
    ...sharedFilters,
    {
      label: t.metric,
      value: metricLabels[storeMetric],
    },
    {
      label: visualizationFieldLabel(
        language,
        'group_by',
      ),
      value: String(
        visualizationValueLabel(
          language,
          storeGroupBy,
        ),
      ),
    },
  ]

  const comparisonLabel = t.vsPreviousPeriod

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div className="dashboard-title">
          <h1>{t.dashboardTitle}</h1>
        </div>

        <div className="dashboard-toolbar">
          <button
            onClick={toggleTheme}
            title={
              theme === 'dark'
                ? 'Ljust läge'
                : 'Mörkt läge'
            }
            className="dashboard-icon-button"
          >
            {theme === 'dark' ? '☀️' : '🌙'}
          </button>

          <button
            onClick={() => setLanguage('en')}
            title="English"
            className={[
              'dashboard-icon-button',
              language === 'en' ? 'active' : '',
            ]
              .filter(Boolean)
              .join(' ')}
          >
            🇬🇧
          </button>

          <button
            onClick={() => setLanguage('sv')}
            title="Svenska"
            className={[
              'dashboard-icon-button',
              language === 'sv' ? 'active' : '',
            ]
              .filter(Boolean)
              .join(' ')}
          >
            🇸🇪
          </button>
        </div>
      </header>

      <div className="dashboard-date-range">
        <label>
          <span>{t.dateFrom}</span>
          <input
            type="date"
            value={dateFrom}
            onChange={(event) =>
              setDateFrom(event.target.value)
            }
          />
        </label>

        <label>
          <span>{t.dateTo}</span>
          <input
            type="date"
            value={dateTo}
            onChange={(event) =>
              setDateTo(event.target.value)
            }
          />
        </label>
      </div>

      <ExportableRegion
        className="dashboard-summary-region"
        title={t.salesSummary}
        rows={summaryRows}
        columns={summaryColumns}
        filters={sharedFilters}
      >
        <div className="kpi-grid">
          {summary ? (
            <>
              <KpiCard
                label={t.netSales}
                value={formatCardValue(
                  summary.net_sales,
                  'SEK',
                )}
                changePercent={percentChange(
                  summary.net_sales,
                  previousSummary?.net_sales,
                )}
                comparisonLabel={comparisonLabel}
                comparisonLoading={previousSummaryLoading}
                loading={summaryLoading}
              />

              <KpiCard
                label={t.grossSales}
                value={formatCardValue(
                  summary.gross_sales,
                  'SEK',
                )}
                changePercent={percentChange(
                  summary.gross_sales,
                  previousSummary?.gross_sales,
                )}
                comparisonLabel={comparisonLabel}
                comparisonLoading={previousSummaryLoading}
                loading={summaryLoading}
              />

              <KpiCard
                label={t.unitsSold}
                value={formatCardValue(
                  summary.units,
                  null,
                )}
                changePercent={percentChange(
                  summary.units,
                  previousSummary?.units,
                )}
                comparisonLabel={comparisonLabel}
                comparisonLoading={previousSummaryLoading}
                loading={summaryLoading}
              />

              <KpiCard
                label={t.orders}
                value={formatCardValue(
                  summary.orders,
                  null,
                )}
                changePercent={percentChange(
                  summary.orders,
                  previousSummary?.orders,
                )}
                comparisonLabel={comparisonLabel}
                comparisonLoading={previousSummaryLoading}
                loading={summaryLoading}
              />
            </>
          ) : (
            Array.from({ length: 4 }).map((_, index) => (
              <KpiCard
                key={index}
                label="—"
                value="…"
                loading
              />
            ))
          )}
        </div>
      </ExportableRegion>

      <div className="dashboard-primary-grid">
        <ExportableRegion
          className="panel dashboard-trend-panel"
          title={productTrendTitle}
          rows={
            visibleTimeseriesRows as unknown as Record<
              string,
              unknown
            >[]
          }
          columns={timeseriesColumns}
          filters={timeseriesFilters}
        >
          <ProductTimeseriesChart
            rows={visibleTimeseriesRows}
            loading={
              timeseriesLoading &&
              !explicitEmptyProductSelection
            }
            grain={grain}
            metric={metric}
            selectedProductIds={displayedProductIds}
            products={productsData?.products ?? []}
            onGrainChange={setGrain}
            onMetricChange={setMetric}
            onProductsChange={setSelectedProductIds}
          />
        </ExportableRegion>

        <section className="panel dashboard-chat-panel">
          <div className="dashboard-static-panel-header">
            <h2>{t.chat}</h2>
          </div>
          <ChatPanel />
        </section>
      </div>

      <div className="dashboard-secondary-grid">
        <ExportableRegion
          className="panel dashboard-store-panel"
          title={t.storeBreakdown}
          rows={
            (storeBreakdown?.rows ??
              []) as unknown as Record<
              string,
              unknown
            >[]
          }
          columns={storeColumns}
          filters={storeFilters}
        >
          <StoreBreakdownChart
            rows={storeBreakdown?.rows ?? []}
            loading={storeBreakdownLoading}
            metric={storeMetric}
            groupBy={storeGroupBy}
            onMetricChange={setStoreMetric}
            onGroupByChange={setStoreGroupBy}
          />
        </ExportableRegion>

        <ExportableRegion
          className="panel dashboard-products-panel"
          title={t.topProducts}
          rows={
            (topProducts?.rows ??
              []) as unknown as Record<
              string,
              unknown
            >[]
          }
          columns={topProductColumns}
          filters={topProductFilters}
        >
          <TopProductsTable
            rows={topProducts?.rows ?? []}
            loading={topLoading}
            sortBy={topSortBy}
            onSortByChange={setTopSortBy}
          />
        </ExportableRegion>
      </div>
    </div>
  )
}
