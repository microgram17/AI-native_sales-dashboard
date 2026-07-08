import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
} from 'recharts'
import type {
  VisualizationSpec,
  LineChartSpec,
  BarChartSpec,
  MetricCardSpec,
  TableSpec,
} from '../../../types/agent'
import {
  COLORS,
  formatShortNumber,
  formatTooltipValue,
  formatCellValue,
  longToWide,
} from './visualizationUtils'

// ── Shared fallback ───────────────────────────────────────────────────────────

function InvalidViz({ reason }: { reason?: string }) {
  return (
    <p className="viz-invalid" style={{ color: 'var(--muted)', fontSize: 12, padding: '8px 0' }}>
      {reason ?? 'Unable to render visualization.'}
    </p>
  )
}

// ── Line chart ────────────────────────────────────────────────────────────────

function LineChartVisualization({ spec }: { spec: LineChartSpec }) {
  const { x_key, y_keys, series_key, data, title } = spec

  if (!x_key || !y_keys?.length || !data?.length) {
    return <InvalidViz />
  }

  let chartData: Record<string, unknown>[] = data
  let seriesKeys: string[] = y_keys

  if (series_key) {
    if (y_keys.length !== 1) {
      return (
        <InvalidViz reason="Unable to render visualization: series_key with multiple y_keys is unsupported." />
      )
    }
    const { wideData, seriesValues } = longToWide(data, x_key, series_key, y_keys[0])
    chartData = wideData
    seriesKeys = seriesValues
  }

  return (
    <div className="viz-wrap">
      {title && <p className="viz-title">{title}</p>}
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={chartData} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
          <XAxis dataKey={x_key} tick={{ fontSize: 11 }} interval="preserveStartEnd" />
          <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => formatShortNumber(v)} width={44} />
          <Tooltip formatter={(v) => formatTooltipValue(v)} />
          {seriesKeys.length > 1 && <Legend wrapperStyle={{ fontSize: 11 }} />}
          {seriesKeys.map((sk, i) => (
            <Line
              key={sk}
              type="monotone"
              dataKey={sk}
              name={sk}
              stroke={COLORS[i % COLORS.length]}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

// ── Bar chart ─────────────────────────────────────────────────────────────────

function BarChartVisualization({ spec }: { spec: BarChartSpec }) {
  const { x_key, y_keys, series_key, data, title } = spec

  if (!x_key || !y_keys?.length || !data?.length) {
    return <InvalidViz />
  }

  let chartData: Record<string, unknown>[] = data
  let seriesKeys: string[] = y_keys

  if (series_key) {
    if (y_keys.length !== 1) {
      return (
        <InvalidViz reason="Unable to render visualization: series_key with multiple y_keys is unsupported." />
      )
    }
    const { wideData, seriesValues } = longToWide(data, x_key, series_key, y_keys[0])
    chartData = wideData
    seriesKeys = seriesValues
  }

  return (
    <div className="viz-wrap">
      {title && <p className="viz-title">{title}</p>}
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={chartData} margin={{ top: 4, right: 16, left: 0, bottom: 32 }}>
          <XAxis
            dataKey={x_key}
            tick={{ fontSize: 11 }}
            angle={-30}
            textAnchor="end"
            interval={0}
          />
          <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => formatShortNumber(v)} width={44} />
          <Tooltip formatter={(v) => formatTooltipValue(v)} />
          {seriesKeys.length > 1 && <Legend wrapperStyle={{ fontSize: 11 }} />}
          {seriesKeys.map((sk, i) => (
            <Bar
              key={sk}
              dataKey={sk}
              name={sk}
              fill={COLORS[i % COLORS.length]}
              radius={[3, 3, 0, 0]}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

// ── Metric card ───────────────────────────────────────────────────────────────

function MetricCardVisualization({ spec }: { spec: MetricCardSpec }) {
  const { label_key, value_key, sublabel_key, data, title, columns } = spec

  if (!label_key || !value_key || !data?.length) {
    return <InvalidViz />
  }

  const valueCol = columns?.find((c) => c.key === value_key)

  return (
    <div className="viz-wrap">
      {title && <p className="viz-title">{title}</p>}
      <div className="viz-kpi-cards">
        {data.map((item, i) => (
          <div key={i} className="viz-kpi-card">
            <span className="viz-kpi-label">{String(item[label_key] ?? '')}</span>
            <span className="viz-kpi-value">
              {formatCellValue(item[value_key], valueCol?.type)}
            </span>
            {sublabel_key != null && item[sublabel_key] !== undefined && (
              <span className="viz-kpi-sublabel">{String(item[sublabel_key] ?? '')}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Table ─────────────────────────────────────────────────────────────────────

function TableVisualization({ spec }: { spec: TableSpec }) {
  const { columns, data, title } = spec

  if (!columns?.length || !data?.length) {
    return <InvalidViz />
  }

  return (
    <div className="viz-wrap">
      {title && <p className="viz-title">{title}</p>}
      <div className="viz-table-wrap">
        <table className="viz-table">
          <thead>
            <tr>
              {columns.map((col) => (
                <th key={col.key}>{col.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row, i) => (
              <tr key={i}>
                {columns.map((col) => (
                  <td key={col.key}>{formatCellValue(row[col.key], col.type)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Top-level dispatcher ──────────────────────────────────────────────────────

interface Props {
  spec: VisualizationSpec
}

export function VisualizationRenderer({ spec }: Props) {
  if (!spec) return <InvalidViz />

  switch (spec.type) {
    case 'line_chart':
      return <LineChartVisualization spec={spec} />
    case 'bar_chart':
      return <BarChartVisualization spec={spec} />
    case 'metric_card':
      return <MetricCardVisualization spec={spec} />
    case 'table':
      return <TableVisualization spec={spec} />
    default:
      return <InvalidViz />
  }
}
