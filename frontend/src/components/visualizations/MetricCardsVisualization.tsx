import type { VisualizationSpec, Dataset } from '../../types/agent'
import { datasetToRows, resolveField, pickValueKeys } from '../../lib/datasetResolver'
import { formatMetricValue, humanizeKey } from '../../lib/format'

interface Props {
  spec: VisualizationSpec
  dataset: Dataset
}

export function MetricCardsVisualization({ spec, dataset }: Props) {
  const rows = datasetToRows(dataset)
  const row = rows[0]
  if (!row) return <Fallback />

  const keys = spec.y_keys.length ? spec.y_keys : pickValueKeys(rows)
  const usable = keys.filter((k) => resolveField(row, k) !== undefined)
  if (usable.length === 0) return <Fallback />

  const caption = (resolveField(row, 'name') as string | undefined) ?? undefined

  return (
    <div>
      {caption && (
        <div style={{ fontSize: '0.8rem', color: 'var(--muted)', marginBottom: '0.4rem' }}>
          {caption}
        </div>
      )}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
        {usable.map((key) => (
          <div
            key={key}
            style={{
              flex: '1 1 120px',
              minWidth: '120px',
              padding: '0.6rem 0.75rem',
              borderRadius: '8px',
              background: 'rgba(51,65,85,0.35)',
              border: '1px solid var(--border, #334155)',
            }}
          >
            <div style={{ fontSize: '0.7rem', color: 'var(--muted)', marginBottom: '0.2rem' }}>
              {humanizeKey(key)}
            </div>
            <div style={{ fontSize: '1.1rem', fontWeight: 600 }}>
              {formatMetricValue(key, resolveField(row, key))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function Fallback() {
  return (
    <div style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>
      No metrics available to display.
    </div>
  )
}
