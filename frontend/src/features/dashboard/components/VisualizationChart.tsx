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
import type { Visualization } from '../../../types/agent'

// Ordered palette — accent first, then muted tones
const COLORS = ['var(--accent)', '#94a3b8', '#64748b', '#e2a03f']

function shortNum(v: unknown): string {
  if (typeof v !== 'number') return String(v ?? '')
  if (Math.abs(v) >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`
  if (Math.abs(v) >= 1_000) return `${(v / 1_000).toFixed(0)}k`
  return v.toLocaleString('sv-SE', { maximumFractionDigits: 1 })
}

function fmtTooltip(v: unknown): string {
  if (typeof v !== 'number') return String(v ?? '')
  return v.toLocaleString('sv-SE', { maximumFractionDigits: 0 })
}

interface Props {
  viz: Visualization
}

export function VisualizationChart({ viz }: Props) {
  if (!viz || viz.type === 'none' || !viz.data?.length) return null

  const { type, title, data = [], data_keys = {} } = viz

  // ── KPI cards ───────────────────────────────────────────────────────────────
  if (type === 'kpi_cards') {
    const labelKey = data_keys.label ?? 'metric'
    const valueKey = data_keys.value ?? 'value'
    return (
      <div className="viz-wrap">
        {title && <p className="viz-title">{title}</p>}
        <div className="viz-kpi-cards">
          {data.map((item, i) => (
            <div key={i} className="viz-kpi-card">
              <span className="viz-kpi-label">{String(item[labelKey] ?? '')}</span>
              <span className="viz-kpi-value">{fmtTooltip(item[valueKey])}</span>
            </div>
          ))}
        </div>
      </div>
    )
  }

  // ── Bar chart ────────────────────────────────────────────────────────────────
  if (type === 'bar_chart') {
    const xKey = data_keys.x ?? 'name'
    const series = data_keys.series ?? [{ key: 'value', name: 'Value' }]
    return (
      <div className="viz-wrap">
        {title && <p className="viz-title">{title}</p>}
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 32 }}>
            <XAxis
              dataKey={xKey}
              tick={{ fontSize: 11 }}
              angle={-30}
              textAnchor="end"
              interval={0}
            />
            <YAxis tick={{ fontSize: 11 }} tickFormatter={shortNum} width={44} />
            <Tooltip formatter={fmtTooltip} />
            {series.length > 1 && <Legend wrapperStyle={{ fontSize: 11 }} />}
            {series.map((s, i) => (
              <Bar
                key={s.key}
                dataKey={s.key}
                name={s.name}
                fill={COLORS[i % COLORS.length]}
                radius={[3, 3, 0, 0]}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    )
  }

  // ── Line chart ───────────────────────────────────────────────────────────────
  if (type === 'line_chart') {
    const xKey = data_keys.x ?? 'period'
    const series = data_keys.series ?? [{ key: 'value', name: 'Value' }]
    return (
      <div className="viz-wrap">
        {title && <p className="viz-title">{title}</p>}
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
            <XAxis
              dataKey={xKey}
              tick={{ fontSize: 11 }}
              interval="preserveStartEnd"
            />
            <YAxis tick={{ fontSize: 11 }} tickFormatter={shortNum} width={44} />
            <Tooltip formatter={fmtTooltip} />
            {series.length > 1 && <Legend wrapperStyle={{ fontSize: 11 }} />}
            {series.map((s, i) => (
              <Line
                key={s.key}
                type="monotone"
                dataKey={s.key}
                name={s.name}
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

  // ── Table ────────────────────────────────────────────────────────────────────
  if (type === 'table') {
    const columns = data_keys.columns ?? Object.keys(data[0] ?? {})
    return (
      <div className="viz-wrap">
        {title && <p className="viz-title">{title}</p>}
        <div className="viz-table-wrap">
          <table className="viz-table">
            <thead>
              <tr>
                {columns.map((c) => (
                  <th key={c}>{c}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.map((row, i) => (
                <tr key={i}>
                  {columns.map((c) => (
                    <td key={c}>{String(row[c] ?? '')}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    )
  }

  return null
}
