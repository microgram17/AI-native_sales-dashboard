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
  const t = viz?.type as string | undefined
  if (t === 'line_chart' || t === 'bar_chart' || t === 'metric_card' || t === 'table') return t
  // No usable backend visualization spec — render the raw rows as a table.
  return 'table'
}

interface VizKeys {
  xKey: string
  yKey: string
  seriesKey: string | null
  valueKey: string
}

function getVizKeys(artifact: DashboardArtifact): VizKeys {
  // The backend (MCP result builder) is authoritative for chart axes. These are
  // only read once getVizType has returned a chart type, which implies the viz
  // spec is present and — per the MCP schema — carries x_key and y_keys.
  const viz = artifact.recommended_visualizations?.[0] as Record<string, unknown> | undefined
  return {
    xKey: (viz?.x_key as string | undefined) ?? '',
    yKey: (viz?.y_keys as string[] | undefined)?.[0] ?? '',
    seriesKey: (viz?.series_key as string | null | undefined) ?? null,
    valueKey: (viz?.value_key as string | undefined) ?? 'value',
  }
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

function isSingleWinner(artifact: DashboardArtifact): boolean {
  return (
    artifact.result_intent === 'single_winner' ||
    (artifact.result_type === 'ranking' && artifact.rows.length === 1)
  )
}

function ArtifactSingleWinner({ artifact }: { artifact: DashboardArtifact }) {
  const row = artifact.rows[0]
  const cols = artifact.columns as Array<{ key: string; label: string }>

  // Name column: the dimension's canonical column, else the first string column.
  const nameKey =
    artifact.dimension === 'product'
      ? 'product_name'
      : artifact.dimension
        ? 'group_name'
        : cols.find((c) => typeof row[c.key] === 'string' && c.key !== 'category')?.key

  // Metric column: the backend-declared primary_metric, else the first numeric column.
  const metricKey =
    artifact.primary_metric && artifact.primary_metric in row
      ? artifact.primary_metric
      : cols.find((c) => typeof row[c.key] === 'number' && c.key !== 'rank')?.key

  const metricLabel = cols.find((c) => c.key === metricKey)?.label ?? metricKey ?? ''
  const categoryVal =
    'category' in row && nameKey !== 'category' ? String(row['category'] ?? '') : null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem', padding: '0.25rem 0' }}>
      {nameKey && (
        <div style={{ fontSize: '1rem', fontWeight: 600, lineHeight: 1.3 }}>
          {String(row[nameKey] ?? '')}
        </div>
      )}
      {categoryVal && (
        <div style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>{categoryVal}</div>
      )}
      {metricKey && (
        <div style={{ fontSize: '0.875rem', color: 'var(--muted)' }}>
          {metricLabel}:{' '}
          <span style={{ fontWeight: 600, color: 'inherit' }}>
            {formatShortNumber(row[metricKey])}
          </span>
        </div>
      )}
    </div>
  )
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

  if (isSingleWinner(artifact)) {
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
        {artifact.description && (
          <div style={{ fontSize: '0.75rem', color: 'var(--muted)', marginBottom: '0.5rem' }}>
            {artifact.description}
          </div>
        )}
        <ArtifactSingleWinner artifact={artifact} />
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
