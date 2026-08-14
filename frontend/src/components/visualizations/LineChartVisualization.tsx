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
import type { VisualizationSpec, Dataset } from '../../types/agent'
import { datasetToRows, resolveField, pickLabelKey, pickValueKeys } from '../../lib/datasetResolver'
import {
  COLORS,
  formatShortNumber,
  formatTooltipValue,
  longToWide,
} from '../../features/dashboard/components/visualizationUtils'
import { humanizeKey } from '../../lib/format'

interface Props {
  spec: VisualizationSpec
  dataset: Dataset
}

export function LineChartVisualization({ spec, dataset }: Props) {
  const rows = datasetToRows(dataset)
  const xKey = pickLabelKey(rows, spec.x_key)
  const valueKeys = pickValueKeys(rows, spec.y_keys)

  if (rows.length === 0 || valueKeys.length === 0) {
    return <div style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>No data to chart.</div>
  }

  const seriesKey = spec.series_key ?? null
  const hasSeries =
    !!seriesKey && rows.some((r) => resolveField(r, seriesKey) !== undefined)

  // Multi-series (e.g. trend split by channel): pivot long -> wide.
  if (hasSeries && valueKeys.length === 1) {
    const flat = rows.map((r) => ({
      [xKey]: resolveField(r, xKey),
      __series: resolveField(r, seriesKey!),
      __value: resolveField(r, valueKeys[0]),
    }))
    const { wideData, seriesValues } = longToWide(flat, xKey, '__series', '__value')
    return (
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={wideData} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.15)" />
          <XAxis dataKey={xKey} tick={{ fontSize: 11 }} />
          <YAxis tickFormatter={formatShortNumber} tick={{ fontSize: 11 }} />
          <Tooltip formatter={formatTooltipValue} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          {seriesValues.map((s, i) => (
            <Line key={s} type="monotone" dataKey={s} stroke={COLORS[i % COLORS.length]} dot={false} strokeWidth={2} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    )
  }

  const data = rows.map((row) => {
    const item: Record<string, unknown> = { [xKey]: resolveField(row, xKey) }
    for (const key of valueKeys) item[key] = resolveField(row, key)
    return item
  })

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.15)" />
        <XAxis dataKey={xKey} tick={{ fontSize: 11 }} />
        <YAxis tickFormatter={formatShortNumber} tick={{ fontSize: 11 }} />
        <Tooltip formatter={formatTooltipValue} />
        {valueKeys.length > 1 && <Legend wrapperStyle={{ fontSize: 11 }} />}
        {valueKeys.map((key, i) => (
          <Line key={key} type="monotone" dataKey={key} name={humanizeKey(key)} stroke={COLORS[i % COLORS.length]} dot={false} strokeWidth={2} />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}
