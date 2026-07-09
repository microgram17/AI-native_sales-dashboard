import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'
import type { DashboardArtifact } from '../../types/dashboard'
import { KpiCard } from '../../features/dashboard/components/KpiCard'
import {
  COLORS,
  formatShortNumber,
  formatTooltipValue,
  longToWide,
} from '../../features/dashboard/components/visualizationUtils'

interface ChatArtifactRendererProps {
  artifact: DashboardArtifact
}

type VizType = 'line_chart' | 'bar_chart' | 'metric_card' | 'table'

function getVizType(artifact: DashboardArtifact): VizType {
  const viz = artifact.recommended_visualizations?.[0] as Record<string, unknown> | undefined
  if (viz?.type) {
    const t = viz.type as string
    if (t === 'line_chart' || t === 'bar_chart' || t === 'metric_card' || t === 'table') return t
  }
  switch (artifact.result_type) {
    case 'timeseries': return 'line_chart'
    case 'ranking':    return 'bar_chart'
    case 'breakdown':  return 'bar_chart'
    case 'kpi':
    case 'summary':    return 'metric_card'
    default:           return 'table'
  }
}

interface VizKeys {
  xKey: string
  yKey: string
  seriesKey: string | null
  valueKey: string
}

function getVizKeys(artifact: DashboardArtifact): VizKeys {
  const viz = artifact.recommended_visualizations?.[0] as Record<string, unknown> | undefined
  const xKey = (viz?.x_key as string | null) ?? defaultXKey(artifact)
  const yKeys = viz?.y_keys as string[] | null
  const yKey = yKeys?.[0] ?? defaultYKey(artifact)
  const seriesKey = (viz?.series_key as string | null) ?? defaultSeriesKey(artifact)
  const valueKey = (viz?.value_key as string | null) ?? 'value'
  return { xKey, yKey, seriesKey, valueKey }
}

function defaultXKey(artifact: DashboardArtifact): string {
  switch (artifact.result_type) {
    case 'timeseries': return 'period'
    case 'ranking':    return 'product_name'
    case 'breakdown':  return 'group_name'
    default: {
      const firstRow = artifact.rows[0]
      return Object.keys(firstRow ?? {})[0] ?? 'key'
    }
  }
}

function defaultYKey(artifact: DashboardArtifact): string {
  switch (artifact.result_type) {
    case 'timeseries': return 'value'
    case 'ranking':    return 'net_sales'
    case 'breakdown':  return 'value'
    default: {
      const firstRow = artifact.rows[0]
      return Object.keys(firstRow ?? {})[1] ?? 'value'
    }
  }
}

function defaultSeriesKey(artifact: DashboardArtifact): string | null {
  return artifact.result_type === 'timeseries' ? 'product_name' : null
}

// --- Sub-renderers ---

function ArtifactTable({ artifact }: { artifact: DashboardArtifact }) {
  const cols = artifact.columns as Array<{ key: string; label: string }>
  const rows = artifact.rows

  const headers =
    cols.length > 0
      ? cols.map((c) => ({ key: c.key, label: c.label }))
      : Object.keys(rows[0] ?? {}).map((k) => ({ key: k, label: k }))

  return (
    <div style={{ overflowX: 'auto' }}>
      <table
        style={{
          width: '100%',
          borderCollapse: 'collapse',
          fontSize: '0.8rem',
        }}
      >
        <thead>
          <tr>
            {headers.map((h) => (
              <th
                key={h.key}
                style={{
                  padding: '0.4rem 0.6rem',
                  textAlign: 'left',
                  borderBottom: '1px solid var(--border, #334155)',
                  color: 'var(--muted)',
                  fontWeight: 500,
                  whiteSpace: 'nowrap',
                }}
              >
                {h.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {headers.map((h) => (
                <td
                  key={h.key}
                  style={{
                    padding: '0.35rem 0.6rem',
                    borderBottom: '1px solid rgba(51,65,85,0.4)',
                  }}
                >
                  {String(row[h.key] ?? '')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ArtifactBarChart({
  rows,
  xKey,
  yKey,
}: {
  rows: Record<string, unknown>[]
  xKey: string
  yKey: string
}) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={rows} margin={{ top: 4, right: 16, bottom: 48, left: 16 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border, #334155)" />
        <XAxis
          dataKey={xKey}
          tick={{ fontSize: 11 }}
          angle={-30}
          textAnchor="end"
          interval={0}
        />
        <YAxis
          tickFormatter={(v) => formatShortNumber(v)}
          tick={{ fontSize: 11 }}
          width={60}
        />
        <Tooltip formatter={(value) => formatTooltipValue(value)} />
        <Bar dataKey={yKey} fill={COLORS[0]} radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}

function ArtifactLineChart({
  rows,
  xKey,
  yKey,
  seriesKey,
}: {
  rows: Record<string, unknown>[]
  xKey: string
  yKey: string
  seriesKey: string | null
}) {
  if (seriesKey) {
    const { wideData, seriesValues } = longToWide(rows, xKey, seriesKey, yKey)
    return (
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={wideData} margin={{ top: 4, right: 16, bottom: 8, left: 16 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border, #334155)" />
          <XAxis dataKey={xKey} tick={{ fontSize: 11 }} />
          <YAxis
            tickFormatter={(v) => formatShortNumber(v)}
            tick={{ fontSize: 11 }}
            width={60}
          />
          <Tooltip formatter={(value) => formatTooltipValue(value)} />
          {seriesValues.length > 1 && <Legend />}
          {seriesValues.map((s, i) => (
            <Line
              key={s}
              type="monotone"
              dataKey={s}
              dot={false}
              stroke={COLORS[i % COLORS.length]}
              strokeWidth={2}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={rows} margin={{ top: 4, right: 16, bottom: 8, left: 16 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border, #334155)" />
        <XAxis dataKey={xKey} tick={{ fontSize: 11 }} />
        <YAxis
          tickFormatter={(v) => formatShortNumber(v)}
          tick={{ fontSize: 11 }}
          width={60}
        />
        <Tooltip formatter={(value) => formatTooltipValue(value)} />
        <Line
          type="monotone"
          dataKey={yKey}
          dot={false}
          stroke={COLORS[0]}
          strokeWidth={2}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}

function ArtifactMetricCards({
  artifact,
  valueKey,
}: {
  artifact: DashboardArtifact
  valueKey: string
}) {
  const cols = artifact.columns as Array<{ key: string; label: string }>
  const rows = artifact.rows

  // Single-row case: each numeric column becomes its own card
  if (rows.length === 1) {
    const row = rows[0]
    const numericCols = cols.filter((c) => typeof row[c.key] === 'number')
    if (numericCols.length > 0) {
      return (
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          {numericCols.map((c) => (
            <KpiCard
              key={c.key}
              label={c.label}
              value={formatShortNumber(row[c.key])}
            />
          ))}
        </div>
      )
    }
  }

  // Multi-row case: one card per row using valueKey + first other column as label
  const labelCol = cols.find((c) => c.key !== valueKey)
  if (labelCol) {
    return (
      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
        {rows.map((row, i) => (
          <KpiCard
            key={i}
            label={String(row[labelCol.key] ?? '')}
            value={formatShortNumber(row[valueKey])}
          />
        ))}
      </div>
    )
  }

  // Fallback
  return <ArtifactTable artifact={artifact} />
}

export function ChatArtifactRenderer({ artifact }: ChatArtifactRendererProps) {
  if (artifact.rows.length === 0) {
    return (
      <div
        style={{
          marginTop: '0.75rem',
          padding: '0.75rem 1rem',
          background: 'var(--surface, #1e293b)',
          borderRadius: '8px',
        }}
      >
        <div style={{ fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.25rem', color: 'var(--muted)' }}>
          {artifact.title}
        </div>
        <div style={{ fontSize: '0.8rem', color: 'var(--muted)', fontStyle: 'italic' }}>
          No data available.
        </div>
      </div>
    )
  }

  const vizType = getVizType(artifact)
  const { xKey, yKey, seriesKey, valueKey } = getVizKeys(artifact)

  return (
    <div
      style={{
        marginTop: '0.75rem',
        padding: '0.75rem 1rem',
        background: 'var(--surface, #1e293b)',
        borderRadius: '8px',
      }}
    >
      <div
        style={{
          fontSize: '0.8rem',
          fontWeight: 600,
          marginBottom: '0.25rem',
          color: 'var(--muted)',
        }}
      >
        {artifact.title}
      </div>
      {artifact.description && (
        <div style={{ fontSize: '0.75rem', color: 'var(--muted)', marginBottom: '0.5rem' }}>
          {artifact.description}
        </div>
      )}
      {vizType === 'bar_chart' && (
        <ArtifactBarChart rows={artifact.rows} xKey={xKey} yKey={yKey} />
      )}
      {vizType === 'line_chart' && (
        <ArtifactLineChart rows={artifact.rows} xKey={xKey} yKey={yKey} seriesKey={seriesKey} />
      )}
      {vizType === 'metric_card' && (
        <ArtifactMetricCards artifact={artifact} valueKey={valueKey} />
      )}
      {vizType === 'table' && <ArtifactTable artifact={artifact} />}
    </div>
  )
}
