import { useQuery } from '@tanstack/react-query'
import { dashboardApi } from '../../api/dashboard'
import type { KpiCardData, DashboardArtifact } from '../../types/dashboard'
import { KpiCard } from './components/KpiCard'
import { ProductTimeseriesChart } from './components/ProductTimeseriesChart'
import { TopProductsTable } from './components/TopProductsTable'
import { StoreBreakdownChart } from './components/StoreBreakdownChart'

function findArtifact(
  artifacts: DashboardArtifact[],
  sourceTool: string,
): DashboardArtifact | undefined {
  return artifacts.find((a) => a.source_tool === sourceTool)
}

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
  const { data, isLoading, isError } = useQuery({
    queryKey: ['dashboard'],
    queryFn: dashboardApi.getDashboard,
  })

  if (isLoading) {
    return (
      <div className="dashboard">
        <div className="panel" style={{ textAlign: 'center', padding: '2rem' }}>
          Loading dashboard…
        </div>
      </div>
    )
  }

  if (isError || !data) {
    return (
      <div className="dashboard">
        <div className="panel" style={{ textAlign: 'center', padding: '2rem', color: 'var(--danger, #ef4444)' }}>
          Failed to load dashboard data.
        </div>
      </div>
    )
  }

  const timeseries = findArtifact(data.artifacts, 'get_current_supplier_product_timeseries')
  const topProducts = findArtifact(data.artifacts, 'get_current_supplier_top_products')
  const storeBreakdown = findArtifact(data.artifacts, 'get_current_supplier_store_breakdown')

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div className="dashboard-title">
          <h1>Supplier Dashboard</h1>
          <span className="supplier-tagline">{data.user.supplier_id}</span>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <span style={{ fontSize: '0.875rem', color: 'var(--muted)' }}>
            {data.user.display_name}
          </span>
        </div>
      </header>

      <section className="kpi-grid">
        {data.cards.map((card: KpiCardData) => (
          <KpiCard
            key={card.key}
            label={card.label}
            value={formatCardValue(card.value, card.unit)}
          />
        ))}
      </section>

      <div className="dashboard-grid">
        <section className="panel">
          <h2>Product Revenue Trend</h2>
          <ProductTimeseriesChart
            rows={timeseries?.rows ?? []}
            loading={false}
          />
        </section>

        <section className="panel">
          <h2>Top Products</h2>
          <TopProductsTable
            rows={topProducts?.rows ?? []}
            loading={false}
          />
        </section>
      </div>

      <section className="panel">
        <h2>Store Breakdown</h2>
        <StoreBreakdownChart
          rows={storeBreakdown?.rows ?? []}
          loading={false}
        />
      </section>
    </div>
  )
}
