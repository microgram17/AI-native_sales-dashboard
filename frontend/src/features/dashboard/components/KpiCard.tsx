interface KpiCardProps {
  label: string
  value: string | number
  sub?: string
  loading?: boolean
}

export function KpiCard({ label, value, sub, loading = false }: KpiCardProps) {
  return (
    <div className={`kpi-card${loading ? ' loading' : ''}`}>
      <span className="kpi-label">{label}</span>
      <span className="kpi-value">{value}</span>
      {sub && <span className="kpi-sub">{sub}</span>}
    </div>
  )
}
