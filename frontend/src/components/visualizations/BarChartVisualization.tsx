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
import type { VisualizationSpec, Dataset } from '../../types/agent'
import { datasetToRows, resolveField, pickLabelKey, pickValueKeys } from '../../lib/datasetResolver'
import {
  COLORS,
  formatShortNumber,
  formatTooltipValue,
} from '../../features/dashboard/components/visualizationUtils'
import { humanizeKey } from '../../lib/format'

interface Props {
  spec: VisualizationSpec
  dataset: Dataset
}

export function BarChartVisualization({ spec, dataset }: Props) {
  const rows = datasetToRows(dataset)
  const labelKey = pickLabelKey(rows, spec.x_key)
  const valueKeys = pickValueKeys(rows, spec.y_keys)

  if (rows.length === 0 || valueKeys.length === 0) {
    return <div style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>No data to chart.</div>
  }

  const data = rows.map((row) => {
    const item: Record<string, unknown> = { [labelKey]: resolveField(row, labelKey) }
    for (const key of valueKeys) item[key] = resolveField(row, key)
    return item
  })

  const longestLabel = Math.max(...data.map((d) => String(d[labelKey] ?? '').length))
  const horizontal = data.length > 6 || longestLabel > 16

  return (
    <ResponsiveContainer width="100%" height={Math.max(240, horizontal ? data.length * 34 : 260)}>
      <BarChart
        data={data}
        layout={horizontal ? 'vertical' : 'horizontal'}
        margin={{ top: 8, right: 16, bottom: 8, left: horizontal ? 24 : 8 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.15)" />
        {horizontal ? (
          <>
            <XAxis type="number" tickFormatter={formatShortNumber} tick={{ fontSize: 11 }} />
            <YAxis
              type="category"
              dataKey={labelKey}
              width={160}
              tick={{ fontSize: 11 }}
              interval={0}
            />
          </>
        ) : (
          <>
            <XAxis dataKey={labelKey} tick={{ fontSize: 11 }} interval={0} angle={-15} textAnchor="end" height={50} />
            <YAxis tickFormatter={formatShortNumber} tick={{ fontSize: 11 }} />
          </>
        )}
        <Tooltip formatter={formatTooltipValue} />
        {valueKeys.length > 1 && <Legend wrapperStyle={{ fontSize: 11 }} />}
        {valueKeys.map((key, i) => (
          <Bar key={key} dataKey={key} name={humanizeKey(key)} fill={COLORS[i % COLORS.length]} radius={[3, 3, 3, 3]} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  )
}
