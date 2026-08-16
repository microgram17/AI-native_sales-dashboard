import type { VisualizationDataset, VisualizationSpec } from '../../types/agent'
import {
  datasetToRows,
  fieldExists,
  resolveField,
} from '../../lib/datasetResolver'
import { formatMetricValue, humanizeKey } from '../../lib/format'

interface Props {
  spec: VisualizationSpec
  dataset: VisualizationDataset
}

export function TableVisualization({ spec, dataset }: Props) {
  const rows = datasetToRows(dataset)
  if (rows.length === 0) {
    return <Fallback text="No rows to display." />
  }

  const columns = spec.columns.filter((column) =>
    fieldExists(rows, column),
  )
  if (columns.length === 0) {
    return <Fallback text="No valid table columns were provided." />
  }

  return (
    <div style={{ overflowX: 'auto', maxHeight: '360px' }}>
      <table
        style={{
          width: '100%',
          borderCollapse: 'collapse',
          fontSize: '0.8rem',
        }}
      >
        <thead>
          <tr>
            {columns.map((column) => (
              <th
                key={column}
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
                {humanizeKey(column)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {columns.map((column) => {
                const value = resolveField(row, column)
                const display =
                  typeof value === 'number'
                    ? formatMetricValue(column, value)
                    : String(value ?? '')

                return (
                  <td
                    key={column}
                    style={{
                      padding: '0.35rem 0.6rem',
                      borderBottom:
                        '1px solid rgba(51,65,85,0.4)',
                      whiteSpace: 'nowrap',
                    }}
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

function Fallback({ text }: { text: string }) {
  return (
    <div style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>
      {text}
    </div>
  )
}
