import {
  ResponsiveContainer,
  BarChart,
  Bar,
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
} from '../../features/dashboard/components/visualizationUtils'
import { formatMetricValue, humanizeKey } from '../../lib/format'

interface Props {
  spec: VisualizationSpec
  dataset: VisualizationDataset
}

export function BarChartVisualization({ spec, dataset }: Props) {
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

  const data = rows.map((row) => {
    const item: Record<string, unknown> = {
      [xKey]: resolveField(row, xKey),
    }
    for (const key of valueKeys) {
      item[key] = resolveField(row, key)
    }
    return item
  })

  const longestLabel = Math.max(
    ...data.map((item) => String(item[xKey] ?? '').length),
  )
  const horizontal = data.length > 6 || longestLabel > 16

  return (
    <ResponsiveContainer
      width="100%"
      height={Math.max(240, horizontal ? data.length * 34 : 260)}
    >
      <BarChart
        data={data}
        layout={horizontal ? 'vertical' : 'horizontal'}
        margin={{
          top: 8,
          right: 16,
          bottom: 8,
          left: horizontal ? 24 : 8,
        }}
      >
        <CartesianGrid
          strokeDasharray="3 3"
          stroke="rgba(148,163,184,0.15)"
        />

        {horizontal ? (
          <>
            <XAxis
              type="number"
              tickFormatter={formatShortNumber}
              tick={{ fontSize: 11 }}
            />
            <YAxis
              type="category"
              dataKey={xKey}
              width={160}
              tick={{ fontSize: 11 }}
              interval={0}
            />
          </>
        ) : (
          <>
            <XAxis
              dataKey={xKey}
              tick={{ fontSize: 11 }}
              interval={0}
              angle={-15}
              textAnchor="end"
              height={50}
            />
            <YAxis
              tickFormatter={formatShortNumber}
              tick={{ fontSize: 11 }}
            />
          </>
        )}

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
          <Bar
            key={key}
            dataKey={key}
            name={key}
            fill={COLORS[i % COLORS.length]}
            radius={[3, 3, 3, 3]}
          />
        ))}
      </BarChart>
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
