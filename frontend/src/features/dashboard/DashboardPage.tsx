import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { dashboardApi } from '../../api/dashboard'
import { setDemoUser } from '../../api/client'
import { KpiCard } from './components/KpiCard'
import { SupplierSelector } from './components/SupplierSelector'
import { UserSelector } from './components/UserSelector'
import { RevenueTrendChart } from './components/RevenueTrendChart'
import { TopProductsTable } from './components/TopProductsTable'
import { AgentChat } from './components/AgentChat'

const DEFAULT_SUPPLIER = 'SUP-001'

const fmtCurrency = (n: number) =>
  new Intl.NumberFormat('sv-SE', {
    style: 'currency',
    currency: 'SEK',
    maximumFractionDigits: 0,
  }).format(n)

export function DashboardPage() {
  const [selectedUser, setSelectedUser] = useState('')
  const [supplierCode, setSupplierCode] = useState(DEFAULT_SUPPLIER)

  const { data: demoUsersData } = useQuery({
    queryKey: ['demoUsers'],
    queryFn: () => dashboardApi.listDemoUsers(),
  })

  // Set the first demo user once data loads
  useEffect(() => {
    if (demoUsersData?.users.length && !selectedUser) {
      const first = demoUsersData.users[0]
      setSelectedUser(first.user_id)
      setDemoUser(first.user_id)
      if (first.supplier_codes.length) {
        setSupplierCode(first.supplier_codes[0])
      }
    }
  }, [demoUsersData, selectedUser])

  function handleUserChange(userId: string) {
    const user = demoUsersData?.users.find((u) => u.user_id === userId)
    setSelectedUser(userId)
    setDemoUser(userId)
    if (user?.supplier_codes.length) {
      setSupplierCode(user.supplier_codes[0])
    }
  }

  const { data: suppliersData } = useQuery({
    queryKey: ['suppliers', selectedUser],
    queryFn: () => dashboardApi.listSuppliers(),
    enabled: !!selectedUser,
  })

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['summary', supplierCode],
    queryFn: () => dashboardApi.getSupplierSummary(supplierCode),
  })

  const { data: trend, isLoading: trendLoading } = useQuery({
    queryKey: ['trend', supplierCode],
    queryFn: () => dashboardApi.getRevenueTrend(supplierCode),
  })

  const { data: topProducts, isLoading: productsLoading } = useQuery({
    queryKey: ['topProducts', supplierCode],
    queryFn: () => dashboardApi.getTopProducts(supplierCode),
  })

  const suppliers = suppliersData?.suppliers ?? []

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div className="dashboard-title">
            <h1>Supplier Dashboard</h1>
            {summary?.supplier_name && (
              <span className="supplier-tagline">{summary.supplier_name}</span>
            )}
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <UserSelector
              users={demoUsersData?.users ?? []}
              selected={selectedUser}
              onChange={handleUserChange}
            />
            <SupplierSelector
              suppliers={suppliers}
              selected={supplierCode}
              onChange={setSupplierCode}
            />
          </div>
      </header>

      <section className="kpi-grid">
        <KpiCard
          label="Total Revenue"
          value={summary ? fmtCurrency(summary.total_revenue) : '—'}
          loading={summaryLoading}
        />
        <KpiCard
          label="Estimated Margin"
          value={summary ? fmtCurrency(summary.estimated_margin) : '—'}
          loading={summaryLoading}
        />
        <KpiCard
          label="Total Orders"
          value={summary ? summary.total_orders.toLocaleString() : '—'}
          loading={summaryLoading}
        />
        <KpiCard
          label="Avg Order Value"
          value={summary ? fmtCurrency(summary.average_order_value) : '—'}
          loading={summaryLoading}
        />
        <KpiCard
          label="Market Share"
          value={
            summary?.latest_market_share
              ? `${summary.latest_market_share.estimated_market_share_pct}%`
              : '—'
          }
          sub={summary?.latest_market_share?.period}
          loading={summaryLoading}
        />
      </section>

      <div className="dashboard-grid">
        <section className="panel">
          <h2>Revenue Trend</h2>
          <RevenueTrendChart
            data={trend?.points ?? []}
            loading={trendLoading}
          />
        </section>

        <section className="panel">
          <h2>Top Products</h2>
          <TopProductsTable
            products={topProducts?.products ?? []}
            loading={productsLoading}
          />
        </section>
      </div>

      <section className="panel">
        <h2>Ask the Agent</h2>
        <AgentChat supplierCode={supplierCode} />
      </section>
    </div>
  )
}
