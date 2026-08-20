import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
} from 'recharts'
import type {
  Metric,
  StoreBreakdownRow,
  StoreGroupBy,
} from '../../../types/dashboard'
import {
  COLORS,
  formatShortNumber,
  formatTooltipValue,
} from './visualizationUtils'
import {
  visualizationFieldLabel,
  visualizationValueLabel,
} from '../../../i18n/translations'
import { useTranslation } from '../../../i18n/LanguageContext'

interface StoreBreakdownChartProps {
  rows: StoreBreakdownRow[]
  loading: boolean
  metric: Metric
  groupBy: StoreGroupBy
  onMetricChange: (metric: Metric) => void
  onGroupByChange: (groupBy: StoreGroupBy) => void
}

function displayGroupName(
  row: StoreBreakdownRow,
  groupBy: StoreGroupBy,
  language: 'en' | 'sv',
): string {
  const explicitName = row.group_name?.trim()
  if (explicitName) return explicitName

  const id = row.group_id?.trim()
  if (
    groupBy === 'store' &&
    id &&
    /online/i.test(id)
  ) {
    return language === 'sv'
      ? 'Onlinebutik'
      : 'Online store'
  }

  if (id) return id

  return language === 'sv'
    ? 'Okänd'
    : 'Unknown'
}

export function StoreBreakdownChart({
  rows,
  loading,
  metric,
  groupBy,
  onMetricChange,
  onGroupByChange,
}: StoreBreakdownChartProps) {
  const { t, language } = useTranslation()

  const metricLabels: Record<Metric, string> = {
    net_sales: t.netSales,
    gross_sales: t.grossSales,
    units: t.unitsSold,
    orders: t.orders,
    discounts: t.discounts,
  }

  const groupByLabels: Record<StoreGroupBy, string> = {
    store: String(
      visualizationValueLabel(language, 'store'),
    ),
    city: String(
      visualizationValueLabel(language, 'city'),
    ),
    channel: String(
      visualizationValueLabel(language, 'channel'),
    ),
  }

  const chartRows = rows.map((row) => ({
    ...row,
    display_name: displayGroupName(
      row,
      groupBy,
      language,
    ),
  }))

  return (
    <div className="store-breakdown">
      <div className="store-breakdown-controls">
        <div className="dashboard-control">
          <label
            className="dashboard-control-label"
            htmlFor="store-breakdown-group"
          >
            {visualizationFieldLabel(
              language,
              'group_by',
            )}
          </label>

          <select
            id="store-breakdown-group"
            value={groupBy}
            onChange={(event) =>
              onGroupByChange(
                event.target.value as StoreGroupBy,
              )
            }
            className="dashboard-select"
          >
            {(
              Object.entries(groupByLabels) as [
                StoreGroupBy,
                string,
              ][]
            ).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </div>

        <div className="dashboard-control">
          <label
            className="dashboard-control-label"
            htmlFor="store-breakdown-metric"
          >
            {t.metric}
          </label>

          <select
            id="store-breakdown-metric"
            value={metric}
            onChange={(event) =>
              onMetricChange(
                event.target.value as Metric,
              )
            }
            className="dashboard-select"
          >
            {(
              Object.entries(metricLabels) as [
                Metric,
                string,
              ][]
            ).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="chart-placeholder">
          {t.loading}
        </div>
      ) : !chartRows.length ? (
        <div className="chart-placeholder">
          {t.noStoreData}
        </div>
      ) : (
        <ResponsiveContainer
          width="100%"
          height={Math.max(
            280,
            Math.min(380, chartRows.length * 34),
          )}
        >
          <BarChart
            data={chartRows}
            layout="vertical"
            margin={{
              top: 4,
              right: 18,
              left: 12,
              bottom: 4,
            }}
          >
            <XAxis
              type="number"
              tick={{
                fontSize: 10,
                fill: 'var(--viz-axis)',
              }}
              axisLine={{
                stroke:
                  'var(--viz-axis-line)',
              }}
              tickLine={{
                stroke:
                  'var(--viz-axis-line)',
              }}
              tickFormatter={(
                value: number,
              ) =>
                formatShortNumber(value)
              }
            />

            <YAxis
              type="category"
              dataKey="display_name"
              width={118}
              tick={{
                fontSize: 10,
                fill: 'var(--viz-axis)',
              }}
              axisLine={false}
              tickLine={false}
            />

            <Tooltip
              formatter={(value) => [
                formatTooltipValue(value),
                metricLabels[metric],
              ]}
              contentStyle={{
                background:
                  'var(--viz-tooltip-bg)',
                border:
                  '1px solid var(--viz-tooltip-border)',
                borderRadius: '8px',
                color: 'var(--text-h)',
              }}
            />

            <Bar
              dataKey="value"
              name={metricLabels[metric]}
              fill={COLORS[0]}
              radius={[0, 4, 4, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
