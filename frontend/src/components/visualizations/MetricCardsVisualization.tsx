import type {
  VisualizationDataset,
  VisualizationSpec,
} from '../../types/agent'
import {
  datasetToRows,
  numericFieldExists,
  resolveField,
} from '../../lib/datasetResolver'
import { formatMetricValue } from '../../lib/format'
import { useTranslation } from '../../i18n/LanguageContext'
import { visualizationFieldLabel } from '../../i18n/translations'

interface Props {
  spec: VisualizationSpec
  dataset: VisualizationDataset
}

export function MetricCardsVisualization({
  spec,
  dataset,
}: Props) {
  const { language, t } = useTranslation()
  const rows = datasetToRows(dataset)
  const row = rows[0]

  if (!row) return <Fallback text={t.vizNoMetrics} />

  const usable = spec.y_keys.filter(
    (key) =>
      numericFieldExists(rows, key) &&
      resolveField(row, key) !== undefined,
  )

  if (usable.length === 0) return <Fallback text={t.vizNoMetrics} />

  const caption =
    (resolveField(row, 'product_name') as string | undefined) ??
    (resolveField(row, 'entity_name') as string | undefined) ??
    undefined

  return (
    <div>
      {caption && (
        <div className="visualization-caption">
          {caption}
        </div>
      )}

      <div className="visualization-metric-grid">
        {usable.map((key) => (
          <div
            key={key}
            className="visualization-metric-card"
          >
            <div className="visualization-metric-label">
              {visualizationFieldLabel(language, key)}
            </div>
            <div className="visualization-metric-value">
              {formatMetricValue(
                key,
                resolveField(row, key),
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function Fallback({ text }: { text: string }) {
  return (
    <div className="visualization-fallback">
      {text}
    </div>
  )
}
