import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { dashboardApi } from '../../api/dashboard'
import type { Grain, Metric } from '../../types/dashboard'
import { KpiCard } from './components/KpiCard'
import { ProductTimeseriesChart } from './components/ProductTimeseriesChart'
import { TopProductsTable } from './components/TopProductsTable'
import { StoreBreakdownChart } from './components/StoreBreakdownChart'
import { ChatPanel } from '../../components/chat/ChatPanel'
import { ExportableRegion } from '../../components/export/ExportableRegion'
import type { ExportColumn, ExportFilter } from '../../lib/export/exportTypes'
import { visualizationFieldLabel } from '../../i18n/translations'
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
  return value.toLocaleString('sv-SE', { maximumFractionDigits: 0 })
}

export function DashboardPage() {
  const { language, setLanguage, t } = useTranslation()
  const { theme, toggleTheme } = useTheme()

  // Shared date range
  const [dateFrom, setDateFrom] = useState('2025-07-01')
  const [dateTo, setDateTo] = useState('2026-06-30')

  // Timeseries-specific filters
  const [grain, setGrain] = useState<Grain>('month')
  const [metric, setMetric] = useState<Metric>('net_sales')
  const [selectedProductIds, setSelectedProductIds] = useState<string[]>([])

  // Top products filter
  const [topSortBy, setTopSortBy] = useState<Metric>('net_sales')

  // KPI summary widget
  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['summary', dateFrom, dateTo],
    queryFn: () => dashboardApi.getSummary({ date_from: dateFrom, date_to: dateTo }),
  })

  // Product timeseries widget
  const productIdsParam =
    selectedProductIds.length > 0 ? [...selectedProductIds].sort().join(',') : undefined
  const { data: timeseries, isLoading: timeseriesLoading } = useQuery({
    queryKey: ['product-timeseries', dateFrom, dateTo, grain, metric, productIdsParam ?? ''],
    queryFn: () =>
      dashboardApi.getProductTimeseries({
        date_from: dateFrom,
        date_to: dateTo,
        grain,
        metric,
        product_ids: productIdsParam,
        limit_products: 5,
      }),
  })

  // Top products widget
  const { data: topProducts, isLoading: topLoading } = useQuery({
    queryKey: ['top-products', dateFrom, dateTo, topSortBy],
    queryFn: () =>
      dashboardApi.getTopProducts({
        date_from: dateFrom,
        date_to: dateTo,
        sort_by: topSortBy,
        limit: 10,
      }),
  })

  // Product selector options (follows date range)
  const { data: productsData } = useQuery({
    queryKey: ['products', dateFrom, dateTo],
    queryFn: () => dashboardApi.getProducts({ date_from: dateFrom, date_to: dateTo }),
  })

  // Store breakdown follows the shared date range.
  const { data: storeBreakdown, isLoading: storeBreakdownLoading } = useQuery({
    queryKey: ['store-breakdown', dateFrom, dateTo],
    queryFn: () =>
      dashboardApi.getStoreBreakdown({
        date_from: dateFrom,
        date_to: dateTo,
        metric: 'net_sales',
        group_by: 'store',
      }),
  })


  const metricLabels: Record<Metric, string> = {
    net_sales: t.netSales,
    gross_sales: t.grossSales,
    units: t.unitsSold,
    orders: t.orders,
    discounts: t.discounts,
  }

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
    selectedProductIds.length > 0
      ? (productsData?.products ?? [])
          .filter((product) => selectedProductIds.includes(product.product_id))
          .map((product) => product.product_name)
      : [t.exportTopProducts]

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
    { label: t.grain, value: grain === 'month' ? t.grainMonth : t.grainWeek },
    { label: t.metric, value: metricLabels[metric] },
    {
      label: visualizationFieldLabel(language, 'product_ids'),
      value: selectedProductNames,
    },
  ]

  const topProductColumns: ExportColumn[] = [
    { key: 'rank', label: visualizationFieldLabel(language, 'rank') },
    { key: 'product_id', label: visualizationFieldLabel(language, 'product_id') },
    { key: 'product_name', label: t.colProduct },
    { key: 'category', label: t.colCategory },
    { key: 'net_sales', label: t.netSales },
    { key: 'gross_sales', label: t.grossSales },
    { key: 'units', label: t.unitsSold },
    { key: 'orders', label: t.orders },
    { key: 'discounts', label: t.discounts },
  ]

  const topProductFilters: ExportFilter[] = [
    ...sharedFilters,
    { label: t.exportSortedBy, value: metricLabels[topSortBy] },
    { label: visualizationFieldLabel(language, 'limit'), value: 10 },
  ]

  const storeColumns: ExportColumn[] = [
    { key: 'group_id', label: visualizationFieldLabel(language, 'store_id') },
    { key: 'group_name', label: visualizationFieldLabel(language, 'store_name') },
    { key: 'value', label: t.netSales },
  ]

  const storeFilters: ExportFilter[] = [
    ...sharedFilters,
    { label: t.metric, value: t.netSales },
    {
      label: visualizationFieldLabel(language, 'group_by'),
      value: visualizationFieldLabel(language, 'store_name'),
    },
  ]

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div className="dashboard-title">
          <h1>{t.dashboardTitle}</h1>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <div style={{ display: 'flex', gap: '3px', alignItems: 'center', marginLeft: '0.5rem' }}>
            {/* Theme toggle */}
            <button
              onClick={toggleTheme}
              title={theme === 'dark' ? 'Ljust läge' : 'Mörkt läge'}
              style={{
                fontSize: '1.1rem',
                lineHeight: 1,
                background: 'none',
                border: '2px solid transparent',
                borderRadius: '4px',
                cursor: 'pointer',
                padding: '2px 5px',
              }}
            >
              {theme === 'dark' ? '☀️' : '🌙'}
            </button>
            {/* Language toggle */}
            <button
              onClick={() => setLanguage('en')}
              title="English"
              style={{
                fontSize: '1.2rem',
                lineHeight: 1,
                background: 'none',
                border: language === 'en' ? '2px solid var(--accent, #6366f1)' : '2px solid transparent',
                borderRadius: '4px',
                cursor: 'pointer',
                padding: '2px 5px',
              }}
            >
              🇬🇧
            </button>
            <button
              onClick={() => setLanguage('sv')}
              title="Svenska"
              style={{
                fontSize: '1.2rem',
                lineHeight: 1,
                background: 'none',
                border: language === 'sv' ? '2px solid var(--accent, #6366f1)' : '2px solid transparent',
                borderRadius: '4px',
                cursor: 'pointer',
                padding: '2px 5px',
              }}
            >
              🇸🇪
            </button>
          </div>
        </div>
      </header>

      {/* Shared date range */}
      <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap' }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', fontSize: '0.875rem' }}>
          <span style={{ color: 'var(--muted)' }}>{t.dateFrom}</span>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            style={{
              padding: '0.25rem 0.5rem',
              borderRadius: '4px',
              border: '1px solid var(--border, #334155)',
              background: 'var(--surface, #1e293b)',
              color: 'inherit',
              fontSize: '0.875rem',
            }}
          />
        </label>
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', fontSize: '0.875rem' }}>
          <span style={{ color: 'var(--muted)' }}>{t.dateTo}</span>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            style={{
              padding: '0.25rem 0.5rem',
              borderRadius: '4px',
              border: '1px solid var(--border, #334155)',
              background: 'var(--surface, #1e293b)',
              color: 'inherit',
              fontSize: '0.875rem',
            }}
          />
        </label>
      </div>

      {/* KPI cards */}
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
              <KpiCard label={t.netSales} value={formatCardValue(summary.net_sales, 'SEK')} loading={summaryLoading} />
              <KpiCard label={t.grossSales} value={formatCardValue(summary.gross_sales, 'SEK')} loading={summaryLoading} />
              <KpiCard label={t.unitsSold} value={formatCardValue(summary.units, null)} loading={summaryLoading} />
              <KpiCard label={t.orders} value={formatCardValue(summary.orders, null)} loading={summaryLoading} />
            </>
          ) : (
            Array.from({ length: 4 }).map((_, i) => (
              <KpiCard key={i} label="—" value="…" loading={true} />
            ))
          )}
        </div>
      </ExportableRegion>

      <div className="dashboard-grid">
        <ExportableRegion
          className="panel"
          title={t.productRevenueTrend}
          rows={(timeseries?.rows ?? []) as unknown as Record<string, unknown>[]}
          columns={timeseriesColumns}
          filters={timeseriesFilters}
        >
          <ProductTimeseriesChart
            rows={timeseries?.rows ?? []}
            loading={timeseriesLoading}
            grain={grain}
            metric={metric}
            selectedProductIds={selectedProductIds}
            products={productsData?.products ?? []}
            onGrainChange={setGrain}
            onMetricChange={setMetric}
            onProductsChange={setSelectedProductIds}
          />
        </ExportableRegion>

        <ExportableRegion
          className="panel"
          title={t.topProducts}
          rows={(topProducts?.rows ?? []) as unknown as Record<string, unknown>[]}
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

      <ExportableRegion
        className="panel"
        title={t.storeBreakdown}
        rows={(storeBreakdown?.rows ?? []) as unknown as Record<string, unknown>[]}
        columns={storeColumns}
        filters={storeFilters}
      >
        <StoreBreakdownChart
          rows={storeBreakdown?.rows ?? []}
          loading={storeBreakdownLoading}
        />
      </ExportableRegion>

      <section className="panel" style={{ marginTop: '1.5rem' }}>
        <h2>{t.chat}</h2>
        <ChatPanel />
      </section>
    </div>
  )
}
