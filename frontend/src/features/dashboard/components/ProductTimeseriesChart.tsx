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

interface ProductTimeseriesChartProps {
  rows: Array<Record<string, unknown>>
  loading: boolean
}

export function ProductTimeseriesChart({ rows, loading }: ProductTimeseriesChartProps) {
  if (loading) return <div className="chart-placeholder">Loading…</div>
  if (!rows.length) return <div className="chart-placeholder">No timeseries data available.</div>

  const { wideData, seriesValues } = longToWide(rows, 'period', 'product_name', 'value')

  if (!wideData.length) return <div className="chart-placeholder">No timeseries data available.</div>

  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={wideData} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
        <XAxis
          dataKey="period"
          tick={{ fontSize: 11 }}
          interval="preserveStartEnd"
        />
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
}
