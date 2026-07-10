import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { dashboardApi } from '../../api/dashboard'
import type { DashboardArtifact, Grain, Metric } from '../../types/dashboard'
import { KpiCard } from './components/KpiCard'
import { ProductTimeseriesChart } from './components/ProductTimeseriesChart'
import { TopProductsTable } from './components/TopProductsTable'
import { StoreBreakdownChart } from './components/StoreBreakdownChart'
import { ChatPanel } from '../../components/chat/ChatPanel'
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

function findArtifact(
  artifacts: DashboardArtifact[],
  sourceTool: string,
): DashboardArtifact | undefined {
  return artifacts.find((a) => a.source_tool === sourceTool)
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

  // User context — fetched once, long stale time
  const { data: dashboardData } = useQuery({
    queryKey: ['dashboard'],
    queryFn: dashboardApi.getDashboard,
    staleTime: Infinity,
  })

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

  // Store breakdown comes from the full /dashboard artifact (no filter for now)
  const storeBreakdown = dashboardData
    ? findArtifact(dashboardData.artifacts, 'get_current_supplier_store_breakdown')
    : undefined

  const user = dashboardData?.user

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div className="dashboard-title">
          <h1>{t.dashboardTitle}</h1>
          {user && <span className="supplier-tagline">{user.supplier_id}</span>}
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          {user && (
            <span style={{ fontSize: '0.875rem', color: 'var(--muted)' }}>
              {user.display_name}
            </span>
          )}
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
      <section className="kpi-grid">
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
      </section>

      <div className="dashboard-grid">
        <section className="panel">
          <h2>{t.productRevenueTrend}</h2>
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
        </section>

        <section className="panel">
          <h2>{t.topProducts}</h2>
          <TopProductsTable
            rows={topProducts?.rows ?? []}
            loading={topLoading}
            sortBy={topSortBy}
            onSortByChange={setTopSortBy}
          />
        </section>
      </div>

      <section className="panel">
        <h2>{t.storeBreakdown}</h2>
        <StoreBreakdownChart
          rows={storeBreakdown?.rows ?? []}
          loading={false}
        />
      </section>

      <section className="panel" style={{ marginTop: '1.5rem' }}>
        <h2>{t.chat}</h2>
        <ChatPanel />
      </section>
    </div>
  )
}
