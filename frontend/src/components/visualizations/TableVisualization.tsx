import type { VisualizationSpec, Dataset } from '../../types/agent'
import { datasetToRows, resolveField } from '../../lib/datasetResolver'
import { formatMetricValue, humanizeKey } from '../../lib/format'

interface Props {
  spec: VisualizationSpec
  dataset: Dataset
}

export function TableVisualization({ dataset }: Props) {
  const rows = datasetToRows(dataset)
  if (rows.length === 0) {
    return (
      <div style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>No rows to display.</div>
    )
  }

  // Columns = scalar fields of the widest row (skip nested objects kept for dot-paths).
  const columns = Array.from(
    rows.reduce<Set<string>>((acc, row) => {
      for (const [k, v] of Object.entries(row)) {
        if (v == null || typeof v !== 'object') acc.add(k)
      }
      return acc
    }, new Set<string>()),
  )

  return (
    <div style={{ overflowX: 'auto', maxHeight: '360px' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
        <thead>
          <tr>
            {columns.map((c) => (
              <th
                key={c}
                style={{
                  padding: '0.4rem 0.6rem',
                  textAlign: 'left',
                  borderBottom: '1px solid var(--border, #334155)',
                  color: 'var(--muted)',
                  fontWeight: 500,
                  whiteSpace: 'nowrap',
                  position: 'sticky',
                  top: 0,
                  background: 'var(--surface, #1e293b)',
                }}
              >
                {humanizeKey(c)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {columns.map((c) => {
                const value = resolveField(row, c)
                const display = typeof value === 'number' ? formatMetricValue(c, value) : String(value ?? '')
                return (
                  <td
                    key={c}
                    style={{ padding: '0.35rem 0.6rem', borderBottom: '1px solid rgba(51,65,85,0.4)', whiteSpace: 'nowrap' }}
                  >
                    {display}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
