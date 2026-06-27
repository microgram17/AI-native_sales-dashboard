import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
} from 'recharts'
import type { RevenueTrendPoint } from '../../../types/dashboard'

interface RevenueTrendChartProps {
  data: RevenueTrendPoint[]
  loading: boolean
}

export function RevenueTrendChart({ data, loading }: RevenueTrendChartProps) {
  if (loading) return <div className="chart-placeholder">Loading…</div>
  if (!data.length) return <div className="chart-placeholder">No trend data available.</div>

  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart
        data={data}
        margin={{ top: 4, right: 16, left: 0, bottom: 4 }}
      >
        <XAxis
          dataKey="period_label"
          tick={{ fontSize: 11 }}
          interval="preserveStartEnd"
        />
        <YAxis
          tick={{ fontSize: 11 }}
          tickFormatter={(v: number) =>
            `${(v / 1_000).toFixed(0)}k`
          }
          width={44}
        />
        <Tooltip
          formatter={(v) =>
            typeof v === 'number'
              ? v.toLocaleString('sv-SE', { maximumFractionDigits: 0 }) + ' kr'
              : String(v)
          }
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Line
          type="monotone"
          dataKey="supplier_revenue"
          name="Your Revenue"
          stroke="var(--accent)"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
        />
        <Line
          type="monotone"
          dataKey="comparable_market_revenue"
          name="Market"
          stroke="var(--border)"
          strokeWidth={1.5}
          strokeDasharray="4 2"
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
