import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'
import type { VisualizationDataset, VisualizationSpec } from '../../types/agent'
import {
  datasetToRows,
  fieldExists,
  numericFieldExists,
  resolveField,
} from '../../lib/datasetResolver'
import {
  COLORS,
  formatShortNumber,
  longToWide,
} from '../../features/dashboard/components/visualizationUtils'
import { formatMetricValue, humanizeKey } from '../../lib/format'

interface Props {
  spec: VisualizationSpec
  dataset: VisualizationDataset
}

export function LineChartVisualization({ spec, dataset }: Props) {
  const rows = datasetToRows(dataset)
  const xKey = spec.x_key ?? null
  const valueKeys = spec.y_keys

  if (
    rows.length === 0 ||
    !xKey ||
    !fieldExists(rows, xKey) ||
    valueKeys.length === 0 ||
    !valueKeys.every((key) => numericFieldExists(rows, key))
  ) {
    return <Fallback />
  }

  const seriesKey = spec.series_key ?? null
  const hasSeries =
    !!seriesKey &&
    fieldExists(rows, seriesKey) &&
    rows.some((row) => {
      const value = resolveField(row, seriesKey)
      return value !== undefined && value !== null && String(value) !== ''
    })

  if (hasSeries && valueKeys.length === 1) {
    const metricKey = valueKeys[0]
    const flat = rows.map((row) => ({
      [xKey]: resolveField(row, xKey),
      __series: resolveField(row, seriesKey!),
      __value: resolveField(row, metricKey),
    }))

    const { wideData, seriesValues } = longToWide(
      flat,
      xKey,
      '__series',
      '__value',
    )

    return (
      <ResponsiveContainer width="100%" height={280}>
        <LineChart
          data={wideData}
          margin={{ top: 8, right: 16, bottom: 8, left: 8 }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="rgba(148,163,184,0.15)"
          />
          <XAxis dataKey={xKey} tick={{ fontSize: 11 }} />
          <YAxis
            tickFormatter={formatShortNumber}
            tick={{ fontSize: 11 }}
          />
          <Tooltip
            formatter={(value, name) => [
              formatMetricValue(metricKey, value),
              String(name),
            ]}
          />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          {seriesValues.map((series, i) => (
            <Line
              key={series}
              type="monotone"
              dataKey={series}
              stroke={COLORS[i % COLORS.length]}
              dot={false}
              strokeWidth={2}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    )
  }

  const data = rows.map((row) => {
    const item: Record<string, unknown> = {
      [xKey]: resolveField(row, xKey),
    }
    for (const key of valueKeys) {
      item[key] = resolveField(row, key)
    }
    return item
  })

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart
        data={data}
        margin={{ top: 8, right: 16, bottom: 8, left: 8 }}
      >
        <CartesianGrid
          strokeDasharray="3 3"
          stroke="rgba(148,163,184,0.15)"
        />
        <XAxis dataKey={xKey} tick={{ fontSize: 11 }} />
        <YAxis
          tickFormatter={formatShortNumber}
          tick={{ fontSize: 11 }}
        />
        <Tooltip
          formatter={(value, name) => [
            formatMetricValue(String(name), value),
            humanizeKey(String(name)),
          ]}
        />
        {valueKeys.length > 1 && (
          <Legend wrapperStyle={{ fontSize: 11 }} />
        )}
        {valueKeys.map((key, i) => (
          <Line
            key={key}
            type="monotone"
            dataKey={key}
            name={key}
            stroke={COLORS[i % COLORS.length]}
            dot={false}
            strokeWidth={2}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}

function Fallback() {
  return (
    <div style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>
      No valid data to chart.
    </div>
  )
}
