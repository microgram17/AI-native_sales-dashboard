import {
  ResponsiveContainer,
  BarChart,
  Bar,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  XAxis,
  YAxis,
  Tooltip,
} from 'recharts'
import type {
  Metric,
  PerformanceTimeseriesRow,
  PerformanceView,
  StoreBreakdownRow,
  StoreGroupBy,
} from '../../../types/dashboard'
import {
  COLORS,
  formatShortNumber,
  formatTooltipValue,
  longToWide,
} from './visualizationUtils'
import { useTranslation } from '../../../i18n/LanguageContext'
import { performanceGroupDisplayName } from './performanceGroupDisplayName'

interface StoreBreakdownChartProps {
  rows: StoreBreakdownRow[]
  loading: boolean
  metric: Metric
  groupBy: StoreGroupBy
  view: PerformanceView
  trendRows: PerformanceTimeseriesRow[]
  trendLoading: boolean
  selectedGroupIds: string[]
  onMetricChange: (metric: Metric) => void
  onGroupByChange: (groupBy: StoreGroupBy) => void
  onViewChange: (view: PerformanceView) => void
  onSelectedGroupsChange: (groupIds: string[]) => void
  onExplain: () => void
}

export function StoreBreakdownChart({
  rows,
  loading,
  metric,
  groupBy,
  view,
  trendRows,
  trendLoading,
  selectedGroupIds,
  onMetricChange,
  onGroupByChange,
  onViewChange,
  onSelectedGroupsChange,
  onExplain,
}: StoreBreakdownChartProps) {
  const { t } = useTranslation()

  const metricLabels: Record<Metric, string> = {
    net_sales: t.netSales,
    gross_sales: t.grossSales,
    units: t.unitsSold,
    orders: t.orders,
    discounts: t.discounts,
  }

  const groupLabels: Record<StoreGroupBy, string> = {
    store: t.groupStore,
    city: t.groupCity,
    channel: t.groupChannel,
  }

  const chartRows = rows.map((row) => ({
    ...row,
    display_name: performanceGroupDisplayName(row, groupBy, {
      online: t.channelOnline,
      physical: t.channelPhysical,
      unknown: t.unknownGroup,
    }),
  }))
  const normalizedTrendRows = trendRows.map((row) => ({
    ...row,
    group_name: performanceGroupDisplayName(row, groupBy, {
      online: t.channelOnline,
      physical: t.channelPhysical,
      unknown: t.unknownGroup,
    }),
  }))
  const { wideData: trendData, seriesValues } = longToWide(
    normalizedTrendRows as unknown as Record<string, unknown>[],
    'period',
    'group_name',
    'value',
  )
  const addableGroups = chartRows.filter(
    (row) => !selectedGroupIds.includes(row.group_id),
  )

  function addGroup(groupId: string) {
    if (!groupId || selectedGroupIds.length >= 3) return
    onSelectedGroupsChange([...selectedGroupIds, groupId])
  }

  return (
    <div className="store-breakdown">
      <div className="store-breakdown-controls">
        <div className="dashboard-control">
          <span className="dashboard-control-label">{t.view}</span>
          <div className="grain-toggle">
            {(['ranking', 'trend'] as PerformanceView[]).map((item) => (
              <button
                key={item}
                type="button"
                className={view === item ? 'active' : ''}
                onClick={() => onViewChange(item)}
              >
                {item === 'ranking' ? t.ranking : t.trend}
              </button>
            ))}
          </div>
        </div>

        <div className="dashboard-control">
          <label
            className="dashboard-control-label"
            htmlFor="store-breakdown-group"
          >
            {t.groupBy}
          </label>
          <select
            id="store-breakdown-group"
            value={groupBy}
            onChange={(event) =>
              onGroupByChange(event.target.value as StoreGroupBy)
            }
            className="dashboard-select"
          >
            {(Object.entries(groupLabels) as [StoreGroupBy, string][]).map(
              ([key, label]) => (
                <option key={key} value={key}>{label}</option>
              ),
            )}
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
              onMetricChange(event.target.value as Metric)
            }
            className="dashboard-select"
          >
            {(Object.entries(metricLabels) as [Metric, string][]).map(
              ([key, label]) => (
                <option key={key} value={key}>{label}</option>
              ),
            )}
          </select>
        </div>

        <button
          type="button"
          className="explain-button"
          onClick={onExplain}
          disabled={
            (view === 'ranking' && loading) ||
            (view === 'trend' && (
              trendLoading || selectedGroupIds.length === 0
            ))
          }
        >
          {t.explainWithAi}
        </button>
      </div>

      {view === 'trend' && (
        <div className="performance-series-picker">
          <div className="performance-series-chips">
            {selectedGroupIds.map((groupId) => {
              const group = chartRows.find((row) => row.group_id === groupId)
              return (
                <button
                  type="button"
                  key={groupId}
                  disabled={selectedGroupIds.length === 1}
                  onClick={() => onSelectedGroupsChange(
                    selectedGroupIds.filter((item) => item !== groupId),
                  )}
                  title={t.removeComparison}
                >
                  {group?.display_name ?? groupId} <span aria-hidden="true">×</span>
                </button>
              )
            })}
          </div>
          {selectedGroupIds.length < 3 && addableGroups.length > 0 && (
            <select
              aria-label={t.addComparison}
              className="dashboard-select performance-add-select"
              value=""
              onChange={(event) => addGroup(event.target.value)}
            >
              <option value="">{t.addComparison}</option>
              {addableGroups.map((row) => (
                <option key={row.group_id} value={row.group_id}>
                  {row.display_name}
                </option>
              ))}
            </select>
          )}
        </div>
      )}

      {(view === 'ranking' ? loading : trendLoading) ? (
        <div className="chart-placeholder">
          {t.loading}
        </div>
      ) : view === 'ranking' && !rows.length ? (
        <div className="chart-placeholder">
          {t.noStoreData}
        </div>
      ) : view === 'trend' && !trendRows.length ? (
        <div className="chart-placeholder">{t.noPerformanceTrendData}</div>
      ) : view === 'ranking' ? (
        <ResponsiveContainer
          width="100%"
          height={Math.max(
            280,
            Math.min(380, rows.length * 34),
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
              interval={0}
              width={112}
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
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <LineChart
            data={trendData}
            margin={{ top: 8, right: 18, left: 0, bottom: 4 }}
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
            {seriesValues.map((series, index) => (
              <Line
                key={series}
                type="monotone"
                dataKey={series}
                stroke={COLORS[index % COLORS.length]}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4 }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
