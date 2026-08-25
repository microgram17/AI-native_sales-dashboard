import { useEffect, useState } from 'react'
import {
  keepPreviousData,
  useInfiniteQuery,
  useQuery,
} from '@tanstack/react-query'
import { dashboardApi } from '../../api/dashboard'
import type {
  Grain,
  Metric,
  PerformanceView,
  ProductSortDirection,
  StoreGroupBy,
} from '../../types/dashboard'
import { KpiCard } from './components/KpiCard'
import { ProductTimeseriesChart } from './components/ProductTimeseriesChart'
import { TopProductsTable } from './components/TopProductsTable'
import { StoreBreakdownChart } from './components/StoreBreakdownChart'
import { SalesTrendChart } from './components/SalesTrendChart'
import {
  ChatPanel,
  type ChatPromptRequest,
} from '../../components/chat/ChatPanel'
import { ExportableRegion } from '../../components/export/ExportableRegion'
import type { ExportColumn, ExportFilter } from '../../lib/export/exportTypes'
import { visualizationFieldLabel } from '../../i18n/translations'
import { useTranslation } from '../../i18n/LanguageContext'
import { useTheme } from '../../i18n/ThemeContext'
import type { WidgetAnalysisRequest } from '../../types/agent'

function formatCardValue(value: number, unit: string | null): string {
  if (unit === 'SEK') {
    return new Intl.NumberFormat('sv-SE', {
      style: 'currency',
      currency: 'SEK',
      maximumFractionDigits: 0,
    }).format(value)
  }

  return value.toLocaleString('sv-SE', {
    maximumFractionDigits: 1,
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

function safeDivide(numerator: number, denominator: number): number {
  return denominator > 0 ? numerator / denominator : 0
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
  const [salesGrain, setSalesGrain] = useState<Grain>('month')
  const [salesMetric, setSalesMetric] = useState<Metric>('net_sales')

  // null means "let the backend choose the initial top 5".
  // [] means the user explicitly cleared the selection.
  const [selectedProductIds, setSelectedProductIds] =
    useState<string[] | null>(null)
  const [productAnalysisOpen, setProductAnalysisOpen] =
    useState(false)

  // Top products filter.
  const [topSortBy, setTopSortBy] =
    useState<Metric>('net_sales')
  const [topSortDirection, setTopSortDirection] =
    useState<ProductSortDirection>('desc')

  // Store breakdown filter.
  const [storeMetric, setStoreMetric] =
    useState<Metric>('net_sales')
  const [storeGroupBy, setStoreGroupBy] =
    useState<StoreGroupBy>('store')
  const [performanceView, setPerformanceView] =
    useState<PerformanceView>('ranking')
  const [selectedPerformanceGroupIds, setSelectedPerformanceGroupIds] =
    useState<string[] | null>(null)
  const [chatPrompt, setChatPrompt] =
    useState<ChatPromptRequest | null>(null)

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

  const {
    data: salesTimeseries,
    isLoading: salesTimeseriesLoading,
  } = useQuery({
    queryKey: ['sales-timeseries', dateFrom, dateTo, salesGrain, salesMetric],
    queryFn: () => dashboardApi.getSalesTimeseries({
      date_from: dateFrom,
      date_to: dateTo,
      grain: salesGrain,
      metric: salesMetric,
    }),
  })

  const {
    data: previousSalesTimeseries,
    isLoading: previousSalesTimeseriesLoading,
  } = useQuery({
    queryKey: [
      'sales-timeseries-previous',
      comparisonPeriod?.date_from ?? '',
      comparisonPeriod?.date_to ?? '',
      salesGrain,
      salesMetric,
    ],
    queryFn: () => {
      if (!comparisonPeriod) {
        throw new Error('No valid comparison period.')
      }
      return dashboardApi.getSalesTimeseries({
        ...comparisonPeriod,
        grain: salesGrain,
        metric: salesMetric,
      })
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
    enabled:
      productAnalysisOpen &&
      !explicitEmptyProductSelection,
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

  // Sortable, incrementally loaded product table.
  const {
    data: productTablePages,
    isLoading: productTableLoading,
    fetchNextPage: fetchNextProductPage,
    hasNextPage: hasNextProductPage,
    isFetchingNextPage: isFetchingNextProductPage,
  } = useInfiniteQuery({
    queryKey: [
      'product-table',
      dateFrom,
      dateTo,
      topSortBy,
      topSortDirection,
    ],
    initialPageParam: 0,
    placeholderData: keepPreviousData,
    staleTime: 60_000,
    queryFn: ({ pageParam }) =>
      dashboardApi.getProductTable({
        date_from: dateFrom,
        date_to: dateTo,
        sort_by: topSortBy,
        sort_direction: topSortDirection,
        offset: pageParam,
        limit: 25,
      }),
    getNextPageParam: (lastPage) => {
      const nextOffset = lastPage.offset + lastPage.rows.length
      return nextOffset < lastPage.total ? nextOffset : undefined
    },
  })
  const productTableRows =
    productTablePages?.pages.flatMap((page) => page.rows) ?? []
  const productTableTotal = productTablePages?.pages[0]?.total ?? 0

  // Product selector options.
  const { data: productsData } = useQuery({
    queryKey: ['products', dateFrom, dateTo],
    queryFn: () =>
      dashboardApi.getProducts({
        date_from: dateFrom,
        date_to: dateTo,
      }),
    enabled: productAnalysisOpen,
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

  const performanceGroupIdsParam =
    selectedPerformanceGroupIds?.length
      ? selectedPerformanceGroupIds.join(',')
      : undefined

  const {
    data: performanceTimeseries,
    isLoading: performanceTimeseriesLoading,
  } = useQuery({
    queryKey: [
      'performance-timeseries',
      dateFrom,
      dateTo,
      storeMetric,
      storeGroupBy,
      performanceGroupIdsParam ?? 'top-3',
    ],
    queryFn: () => dashboardApi.getPerformanceTimeseries({
      date_from: dateFrom,
      date_to: dateTo,
      grain: 'month',
      metric: storeMetric,
      group_by: storeGroupBy,
      group_ids: performanceGroupIdsParam,
      limit_groups: 3,
    }),
  })

  const backendDefaultPerformanceGroupIds = Array.from(
    new Set(
      (performanceTimeseries?.rows ?? [])
        .map((row) => row.group_id)
        .filter(Boolean),
    ),
  ).slice(0, 3)
  const displayedPerformanceGroupIds =
    selectedPerformanceGroupIds ?? backendDefaultPerformanceGroupIds

  const metricLabels: Record<Metric, string> = {
    net_sales: t.netSales,
    gross_sales: t.grossSales,
    units: t.unitsSold,
    orders: t.orders,
    discounts: t.discounts,
  }
  const groupLabels: Record<StoreGroupBy, string> = {
    store: t.groupStore,
    city: t.groupCity,
    channel: t.groupChannel,
  }

  const productTrendTitle =
    t.productTrendTitle(metricLabels[metric])
  const salesTrendTitle =
    t.salesTrendTitle(metricLabels[salesMetric])
  const performanceTitle = t.performanceTitle(
    metricLabels[storeMetric],
    groupLabels[storeGroupBy],
  )

  const sharedFilters: ExportFilter[] = [
    { label: t.dateFrom, value: dateFrom },
    { label: t.dateTo, value: dateTo },
  ]

  const summaryRows: Record<string, unknown>[] = summary
    ? [
        {
          net_sales: summary.net_sales,
          orders: summary.orders,
          average_order_value: safeDivide(
            summary.net_sales,
            summary.orders,
          ),
          units_per_order: safeDivide(
            summary.units,
            summary.orders,
          ),
        },
      ]
    : []

  const summaryColumns: ExportColumn[] = [
    { key: 'net_sales', label: t.netSales },
    { key: 'orders', label: t.orders },
    { key: 'average_order_value', label: t.averageOrderValue },
    { key: 'units_per_order', label: t.unitsPerOrder },
  ]

  const salesTrendColumns: ExportColumn[] = [
    {
      key: 'period',
      label: visualizationFieldLabel(language, 'period'),
    },
    { key: 'value', label: metricLabels[salesMetric] },
  ]
  const salesTrendFilters: ExportFilter[] = [
    ...sharedFilters,
    {
      label: t.grain,
      value: salesGrain === 'month' ? t.grainMonth : t.grainWeek,
    },
    { label: t.metric, value: metricLabels[salesMetric] },
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
  ]

  const storeColumns: ExportColumn[] = [
    {
      key: 'group_id',
      label: visualizationFieldLabel(
        language,
        storeGroupBy === 'store'
          ? 'store_id'
          : storeGroupBy,
      ),
    },
    {
      key: 'group_name',
      label: visualizationFieldLabel(
        language,
        storeGroupBy === 'store'
          ? 'store_name'
          : storeGroupBy,
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
      value:
        storeGroupBy === 'store'
          ? t.groupStore
          : storeGroupBy === 'city'
            ? t.groupCity
            : t.groupChannel,
    },
    {
      label: t.view,
      value: performanceView === 'ranking' ? t.ranking : t.trend,
    },
  ]
  const performanceRows = performanceView === 'ranking'
    ? storeBreakdown?.rows ?? []
    : performanceTimeseries?.rows ?? []
  const performanceColumns: ExportColumn[] = performanceView === 'ranking'
    ? storeColumns
    : [
        {
          key: 'period',
          label: visualizationFieldLabel(language, 'period'),
        },
        ...storeColumns,
      ]

  const comparisonLabel = t.vsPreviousPeriod
  const currentAverageOrderValue = summary
    ? safeDivide(summary.net_sales, summary.orders)
    : 0
  const previousAverageOrderValue = previousSummary
    ? safeDivide(previousSummary.net_sales, previousSummary.orders)
    : undefined
  const currentUnitsPerOrder = summary
    ? safeDivide(summary.units, summary.orders)
    : 0
  const previousUnitsPerOrder = previousSummary
    ? safeDivide(previousSummary.units, previousSummary.orders)
    : undefined
  const chatContext = {
    date_from: dateFrom,
    date_to: dateTo,
    metric: salesMetric,
    grain: salesGrain,
    group_by: storeGroupBy,
    view: performanceView,
    selected_group_ids: displayedPerformanceGroupIds,
  }

  function summaryWidgetAnalysis(
    metrics: Metric[],
  ): WidgetAnalysisRequest {
    return {
      widget: 'kpi',
      operation: 'summary',
      metrics,
      period_start: dateFrom,
      period_end: dateTo,
    }
  }

  function performanceWidgetScope() {
    if (performanceView !== 'trend') return {}
    if (storeGroupBy === 'store') {
      return { store_ids: displayedPerformanceGroupIds }
    }
    if (storeGroupBy === 'city') {
      return { cities: displayedPerformanceGroupIds }
    }
    return {
      channels: displayedPerformanceGroupIds
        .map((groupId) => groupId.toLowerCase())
        .filter(
          (groupId): groupId is 'online' | 'physical' =>
            groupId === 'online' || groupId === 'physical',
        ),
    }
  }

  function performanceWidgetAnalysis(): WidgetAnalysisRequest {
    if (performanceView === 'ranking') {
      return {
        widget: 'performance',
        operation: 'ranking',
        metrics: [storeMetric],
        period_start: dateFrom,
        period_end: dateTo,
        group_by: storeGroupBy,
        rank_by: storeMetric,
        limit: Math.min(
          20,
          Math.max(1, storeBreakdown?.rows.length ?? 1),
        ),
      }
    }

    return {
      widget: 'performance',
      operation: 'trend',
      metrics: [storeMetric],
      period_start: dateFrom,
      period_end: dateTo,
      grain: 'month',
      split_by: storeGroupBy,
      series_limit: Math.max(1, displayedPerformanceGroupIds.length),
      scope: performanceWidgetScope(),
    }
  }

  function requestChatPrompt(
    text: string,
    widgetAnalysis: WidgetAnalysisRequest,
  ) {
    setChatPrompt({ id: Date.now(), text, widgetAnalysis })
  }

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
            onChange={(event) => {
              setDateFrom(event.target.value)
              setSelectedPerformanceGroupIds(null)
            }}
          />
        </label>

        <label>
          <span>{t.dateTo}</span>
          <input
            type="date"
            value={dateTo}
            onChange={(event) => {
              setDateTo(event.target.value)
              setSelectedPerformanceGroupIds(null)
            }}
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
                explainLabel={t.explainWithAi}
                onExplain={() => requestChatPrompt(
                  t.explainKpi(t.netSales),
                  summaryWidgetAnalysis(['net_sales']),
                )}
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
                explainLabel={t.explainWithAi}
                onExplain={() => requestChatPrompt(
                  t.explainKpi(t.orders),
                  summaryWidgetAnalysis(['orders']),
                )}
              />

              <KpiCard
                label={t.averageOrderValue}
                value={formatCardValue(
                  currentAverageOrderValue,
                  'SEK',
                )}
                changePercent={percentChange(
                  currentAverageOrderValue,
                  previousAverageOrderValue,
                )}
                comparisonLabel={comparisonLabel}
                comparisonLoading={previousSummaryLoading}
                loading={summaryLoading}
                explainLabel={t.explainWithAi}
                onExplain={() => requestChatPrompt(
                  t.explainKpi(t.averageOrderValue),
                  summaryWidgetAnalysis(['net_sales', 'orders']),
                )}
              />

              <KpiCard
                label={t.unitsPerOrder}
                value={formatCardValue(currentUnitsPerOrder, null)}
                changePercent={percentChange(
                  currentUnitsPerOrder,
                  previousUnitsPerOrder,
                )}
                comparisonLabel={comparisonLabel}
                comparisonLoading={previousSummaryLoading}
                loading={summaryLoading}
                explainLabel={t.explainWithAi}
                onExplain={() => requestChatPrompt(
                  t.explainKpi(t.unitsPerOrder),
                  summaryWidgetAnalysis(['units', 'orders']),
                )}
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
        <div className="dashboard-overview-column">
          <ExportableRegion
            className="panel dashboard-sales-trend-panel"
            title={salesTrendTitle}
            rows={
              (salesTimeseries?.rows ?? []) as unknown as Record<
                string,
                unknown
              >[]
            }
            columns={salesTrendColumns}
            filters={salesTrendFilters}
          >
            <SalesTrendChart
              rows={salesTimeseries?.rows ?? []}
              previousRows={previousSalesTimeseries?.rows ?? []}
              loading={
                salesTimeseriesLoading ||
                previousSalesTimeseriesLoading
              }
              grain={salesGrain}
              metric={salesMetric}
              onGrainChange={setSalesGrain}
              onMetricChange={setSalesMetric}
              onExplain={() => requestChatPrompt(
                t.explainTrend(metricLabels[salesMetric]),
                {
                  widget: 'sales_trend',
                  operation: 'trend',
                  metrics: [salesMetric],
                  period_start: dateFrom,
                  period_end: dateTo,
                  grain: salesGrain,
                },
              )}
            />
          </ExportableRegion>

          <ExportableRegion
            className="panel dashboard-store-panel"
            title={performanceTitle}
            rows={performanceRows as unknown as Record<string, unknown>[]}
            columns={performanceColumns}
            filters={storeFilters}
          >
            <StoreBreakdownChart
              rows={storeBreakdown?.rows ?? []}
              loading={storeBreakdownLoading}
              metric={storeMetric}
              groupBy={storeGroupBy}
              view={performanceView}
              trendRows={performanceTimeseries?.rows ?? []}
              trendLoading={performanceTimeseriesLoading}
              selectedGroupIds={displayedPerformanceGroupIds}
              onMetricChange={(nextMetric) => {
                setStoreMetric(nextMetric)
                setSelectedPerformanceGroupIds(null)
              }}
              onGroupByChange={(nextGroup) => {
                setStoreGroupBy(nextGroup)
                setSelectedPerformanceGroupIds(null)
              }}
              onViewChange={setPerformanceView}
              onSelectedGroupsChange={setSelectedPerformanceGroupIds}
              onExplain={() => requestChatPrompt(
                t.explainPerformance(
                  metricLabels[storeMetric],
                  groupLabels[storeGroupBy],
                ),
                performanceWidgetAnalysis(),
              )}
            />
          </ExportableRegion>
        </div>

        <section className="panel dashboard-chat-panel">
          <div className="dashboard-static-panel-header">
            <h2>{t.askSalesData}</h2>
          </div>
          <ChatPanel
            dashboardContext={chatContext}
            contextLabel={t.chatContext(dateFrom, dateTo)}
            requestedPrompt={chatPrompt}
          />
        </section>
      </div>

      <div className="dashboard-secondary-grid dashboard-products-overview">
        <ExportableRegion
          className="panel dashboard-products-panel"
          title={t.productsTable}
          rows={
            (productTableRows ??
              []) as unknown as Record<
              string,
              unknown
            >[]
          }
          columns={topProductColumns}
          filters={topProductFilters}
        >
          <TopProductsTable
            rows={productTableRows}
            loading={productTableLoading}
            sortBy={topSortBy}
            sortDirection={topSortDirection}
            onSortChange={(nextMetric, nextDirection) => {
              setTopSortBy(nextMetric)
              setTopSortDirection(nextDirection)
            }}
            hasMore={hasNextProductPage}
            loadingMore={isFetchingNextProductPage}
            total={productTableTotal}
            onLoadMore={() => {
              void fetchNextProductPage()
            }}
          />
        </ExportableRegion>
      </div>

      <details
        className="product-analysis-disclosure"
        open={productAnalysisOpen}
        onToggle={(event) =>
          setProductAnalysisOpen(event.currentTarget.open)
        }
      >
        <summary>
          <span>
            <strong>{t.productAnalysis}</strong>
            <small>{t.productAnalysisDescription}</small>
          </span>
          <span className="product-analysis-chevron" aria-hidden="true">⌄</span>
        </summary>
        <ExportableRegion
          className="panel dashboard-trend-panel product-analysis-panel"
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
      </details>
    </div>
  )
}
