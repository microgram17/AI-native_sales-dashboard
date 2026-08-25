import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type {
  Grain,
  Metric,
  SalesTimeseriesRow,
} from '../../../types/dashboard'
import { useTranslation } from '../../../i18n/LanguageContext'
import {
  formatShortNumber,
  formatTooltipValue,
} from './visualizationUtils'

interface SalesTrendChartProps {
  rows: SalesTimeseriesRow[]
  previousRows: SalesTimeseriesRow[]
  loading: boolean
  grain: Grain
  metric: Metric
  onGrainChange: (grain: Grain) => void
  onMetricChange: (metric: Metric) => void
  onExplain: () => void
}

export function SalesTrendChart({
  rows,
  previousRows,
  loading,
  grain,
  metric,
  onGrainChange,
  onMetricChange,
  onExplain,
}: SalesTrendChartProps) {
  const { language, t } = useTranslation()
  const metricLabels: Record<Metric, string> = {
    net_sales: t.netSales,
    gross_sales: t.grossSales,
    units: t.unitsSold,
    orders: t.orders,
    discounts: t.discounts,
  }
  const periodFormatter = new Intl.DateTimeFormat(
    language === 'sv' ? 'sv-SE' : 'en-GB',
    {
      month: 'short',
      year: '2-digit',
      timeZone: 'UTC',
    },
  )
  const chartRows = rows.map((row, index) => ({
    period: periodFormatter.format(new Date(`${row.period}T00:00:00Z`)),
    current: row.value,
    previous: previousRows[index]?.value,
  }))

  return (
    <div className="sales-trend">
      <div className="sales-trend-controls">
        <div className="dashboard-control">
          <span className="dashboard-control-label">{t.grain}</span>
          <div className="grain-toggle">
            {(['month', 'week'] as Grain[]).map((item) => (
              <button
                key={item}
                type="button"
                className={grain === item ? 'active' : ''}
                onClick={() => onGrainChange(item)}
              >
                {item === 'month' ? t.grainMonth : t.grainWeek}
              </button>
            ))}
          </div>
        </div>

        <div className="dashboard-control">
          <label className="dashboard-control-label" htmlFor="sales-trend-metric">
            {t.metric}
          </label>
          <select
            id="sales-trend-metric"
            className="dashboard-select"
            value={metric}
            onChange={(event) => onMetricChange(event.target.value as Metric)}
          >
            {(Object.entries(metricLabels) as [Metric, string][]).map(
              ([key, label]) => (
                <option key={key} value={key}>{label}</option>
              ),
            )}
          </select>
        </div>

        <button type="button" className="explain-button" onClick={onExplain}>
          {t.explainWithAi}
        </button>
      </div>

      {loading ? (
        <div className="chart-placeholder">{t.loading}</div>
      ) : !chartRows.length ? (
        <div className="chart-placeholder">{t.noTimeseriesData}</div>
      ) : (
        <ResponsiveContainer width="100%" height={280}>
          <LineChart
            data={chartRows}
            margin={{ top: 12, right: 18, left: 0, bottom: 4 }}
          >
            <CartesianGrid stroke="var(--viz-grid)" vertical={false} />
            <XAxis
              dataKey="period"
              tick={{ fontSize: 11, fill: 'var(--viz-axis)' }}
              axisLine={{ stroke: 'var(--viz-axis-line)' }}
              tickLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fontSize: 11, fill: 'var(--viz-axis)' }}
              axisLine={false}
              tickLine={false}
              tickFormatter={formatShortNumber}
              width={48}
            />
            <Tooltip
              formatter={formatTooltipValue}
              contentStyle={{
                background: 'var(--viz-tooltip-bg)',
                border: '1px solid var(--viz-tooltip-border)',
                borderRadius: 8,
                color: 'var(--text-h)',
              }}
            />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Line
              type="monotone"
              dataKey="current"
              name={t.currentPeriod}
              stroke="var(--viz-series-1)"
              strokeWidth={2.5}
              dot={false}
              activeDot={{ r: 4 }}
            />
            <Line
              type="monotone"
              dataKey="previous"
              name={t.previousPeriod}
              stroke="var(--viz-axis)"
              strokeWidth={1.75}
              strokeDasharray="6 5"
              dot={false}
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
