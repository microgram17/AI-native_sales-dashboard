import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
} from 'recharts'
import {
  COLORS,
  formatShortNumber,
  formatTooltipValue,
  longToWide,
} from './visualizationUtils'
import type { Grain, Metric, ProductSelectorItem, TimeseriesRow } from '../../../types/dashboard'

const METRIC_LABELS: Record<Metric, string> = {
  net_sales: 'Net Sales',
  gross_sales: 'Gross Sales',
  units: 'Units',
  orders: 'Orders',
  discounts: 'Discounts',
}

interface ProductTimeseriesChartProps {
  rows: TimeseriesRow[]
  loading: boolean
  grain: Grain
  metric: Metric
  selectedProductIds: string[]
  products: ProductSelectorItem[]
  onGrainChange: (g: Grain) => void
  onMetricChange: (m: Metric) => void
  onProductsChange: (ids: string[]) => void
}

export function ProductTimeseriesChart({
  rows,
  loading,
  grain,
  metric,
  selectedProductIds,
  products,
  onGrainChange,
  onMetricChange,
  onProductsChange,
}: ProductTimeseriesChartProps) {
  function toggleProduct(id: string) {
    if (selectedProductIds.includes(id)) {
      onProductsChange(selectedProductIds.filter((p) => p !== id))
    } else {
      onProductsChange([...selectedProductIds, id])
    }
  }

  return (
    <div>
      {/* Controls */}
      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '0.75rem', alignItems: 'flex-start' }}>
        {/* Grain toggle */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--muted)', fontWeight: 500 }}>Grain</span>
          <div style={{ display: 'flex', gap: '0.25rem' }}>
            {(['month', 'week'] as Grain[]).map((g) => (
              <button
                key={g}
                onClick={() => onGrainChange(g)}
                style={{
                  padding: '0.25rem 0.625rem',
                  fontSize: '0.8125rem',
                  borderRadius: '4px',
                  border: '1px solid var(--border, #334155)',
                  background: grain === g ? 'var(--accent)' : 'transparent',
                  color: grain === g ? '#fff' : 'inherit',
                  cursor: 'pointer',
                }}
              >
                {g.charAt(0).toUpperCase() + g.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Metric selector */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--muted)', fontWeight: 500 }}>Metric</span>
          <select
            value={metric}
            onChange={(e) => onMetricChange(e.target.value as Metric)}
            style={{
              padding: '0.25rem 0.5rem',
              fontSize: '0.8125rem',
              borderRadius: '4px',
              border: '1px solid var(--border, #334155)',
              background: 'var(--surface, #1e293b)',
              color: 'inherit',
              cursor: 'pointer',
            }}
          >
            {(Object.entries(METRIC_LABELS) as [Metric, string][]).map(([key, label]) => (
              <option key={key} value={key}>{label}</option>
            ))}
          </select>
        </div>

        {/* Product selector */}
        {products.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', flex: 1, minWidth: '160px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--muted)', fontWeight: 500 }}>
                Products {selectedProductIds.length > 0 ? `(${selectedProductIds.length} selected)` : '(top 5)'}
              </span>
              {selectedProductIds.length > 0 && (
                <button
                  onClick={() => onProductsChange([])}
                  style={{
                    fontSize: '0.7rem',
                    padding: '0.1rem 0.375rem',
                    borderRadius: '4px',
                    border: '1px solid var(--border, #334155)',
                    background: 'transparent',
                    color: 'var(--muted)',
                    cursor: 'pointer',
                  }}
                >
                  Clear
                </button>
              )}
            </div>
            <div
              style={{
                maxHeight: '120px',
                overflowY: 'auto',
                border: '1px solid var(--border, #334155)',
                borderRadius: '4px',
                padding: '0.25rem',
              }}
            >
              {products.map((p) => (
                <label
                  key={p.product_id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.375rem',
                    padding: '0.125rem 0.25rem',
                    fontSize: '0.8125rem',
                    cursor: 'pointer',
                    borderRadius: '3px',
                  }}
                >
                  <input
                    type="checkbox"
                    checked={selectedProductIds.includes(p.product_id)}
                    onChange={() => toggleProduct(p.product_id)}
                    style={{ cursor: 'pointer' }}
                  />
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {p.product_name}
                  </span>
                  <span style={{ fontSize: '0.7rem', color: 'var(--muted)', flexShrink: 0 }}>
                    {p.category}
                  </span>
                </label>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Chart */}
      {loading ? (
        <div className="chart-placeholder">Loading…</div>
      ) : !rows.length ? (
        <div className="chart-placeholder">No timeseries data available.</div>
      ) : (() => {
        const { wideData, seriesValues } = longToWide(rows as unknown as Record<string, unknown>[], 'period', 'product_name', 'value')
        if (!wideData.length) return <div className="chart-placeholder">No timeseries data available.</div>
        return (
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={wideData} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
              <XAxis dataKey="period" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
              <YAxis
                tick={{ fontSize: 11 }}
                tickFormatter={(v: number) => formatShortNumber(v)}
                width={44}
              />
              <Tooltip formatter={(v) => formatTooltipValue(v)} />
              {seriesValues.length > 1 && <Legend wrapperStyle={{ fontSize: 12 }} />}
              {seriesValues.map((series, i) => (
                <Line
                  key={series}
                  type="monotone"
                  dataKey={series}
                  name={series}
                  stroke={COLORS[i % COLORS.length]}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        )
      })()}
    </div>
  )
}
