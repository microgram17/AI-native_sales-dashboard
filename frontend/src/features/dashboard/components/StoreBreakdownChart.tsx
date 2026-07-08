import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
} from 'recharts'
import { COLORS, formatShortNumber, formatTooltipValue } from './visualizationUtils'

interface StoreBreakdownChartProps {
  rows: Array<Record<string, unknown>>
  loading: boolean
}

export function StoreBreakdownChart({ rows, loading }: StoreBreakdownChartProps) {
  if (loading) return <div className="chart-placeholder">Loading…</div>
  if (!rows.length) return <div className="chart-placeholder">No store breakdown data available.</div>

  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={rows} margin={{ top: 4, right: 16, left: 0, bottom: 32 }}>
        <XAxis
          dataKey="group_name"
          tick={{ fontSize: 11 }}
          angle={-30}
          textAnchor="end"
          interval={0}
        />
        <YAxis
          tick={{ fontSize: 11 }}
          tickFormatter={(v: number) => formatShortNumber(v)}
          width={44}
        />
        <Tooltip formatter={(v) => formatTooltipValue(v)} />
        <Bar
          dataKey="value"
          name="Net Sales"
          fill={COLORS[0]}
          radius={[3, 3, 0, 0]}
        />
      </BarChart>
    </ResponsiveContainer>
  )
}
