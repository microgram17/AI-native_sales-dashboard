interface KpiCardProps {
  label: string
  value: string | number
  changePercent?: number | null
  comparisonLabel?: string
  comparisonLoading?: boolean
  loading?: boolean
}

function formatChange(value: number): string {
  const prefix = value > 0 ? '+' : ''
  return `${prefix}${value.toLocaleString('sv-SE', {
    maximumFractionDigits: 1,
    minimumFractionDigits: 1,
  })}%`
}

export function KpiCard({
  label,
  value,
  changePercent,
  comparisonLabel,
  comparisonLoading = false,
  loading = false,
}: KpiCardProps) {
  const changeClass =
    changePercent === null ||
    changePercent === undefined ||
    changePercent === 0
      ? 'neutral'
      : changePercent > 0
        ? 'positive'
        : 'negative'

  return (
    <div
      className={`kpi-card${loading ? ' loading' : ''}`}
    >
      <span className="kpi-label">{label}</span>
      <span className="kpi-value">{value}</span>

      {comparisonLabel && (
        <div className="kpi-comparison">
          {comparisonLoading ? (
            <span className="kpi-change neutral">…</span>
          ) : changePercent === null ||
            changePercent === undefined ? (
            <span className="kpi-change neutral">—</span>
          ) : (
            <span className={`kpi-change ${changeClass}`}>
              {changePercent > 0
                ? '▲ '
                : changePercent < 0
                  ? '▼ '
                  : ''}
              {formatChange(changePercent)}
            </span>
          )}

          <span className="kpi-comparison-label">
            {comparisonLabel}
          </span>
        </div>
      )}
    </div>
  )
}
