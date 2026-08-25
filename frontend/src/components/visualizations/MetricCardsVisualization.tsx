import type {
  DataView,
  VisualizationSpec,
} from '../../types/agent'
import {
  dataViewToRows,
  numericFieldExists,
  resolveField,
} from '../../lib/dataView'
import { formatMetricValue } from '../../lib/format'
import { useTranslation } from '../../i18n/LanguageContext'
import { visualizationFieldLabel } from '../../i18n/translations'

interface Props {
  spec: VisualizationSpec
  dataView: DataView
  highlightedMetric?: string | null
}

export function MetricCardsVisualization({
  spec,
  dataView,
  highlightedMetric,
}: Props) {
  const { language, t } = useTranslation()
  const rows = dataViewToRows(dataView)
  const row = rows[0]

  if (!row) return <Fallback text={t.vizNoMetrics} />

  const usable = spec.y_keys.filter(
    (key) =>
      numericFieldExists(rows, key) &&
      resolveField(row, key) !== undefined,
  )

  const orderedMetrics = highlightedMetric && usable.includes(highlightedMetric)
    ? [highlightedMetric, ...usable.filter((key) => key !== highlightedMetric)]
    : usable

  if (orderedMetrics.length === 0) return <Fallback text={t.vizNoMetrics} />

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
        {orderedMetrics.map((key) => {
          const isHighlighted = key === highlightedMetric
          return (
          <div
            key={key}
            className={[
              'visualization-metric-card',
              isHighlighted ? 'is-ranking-metric' : '',
            ].filter(Boolean).join(' ')}
          >
            <div className="visualization-metric-label">
              {visualizationFieldLabel(language, key)}
            </div>
            <div className="visualization-metric-value">
              {formatMetricValue(
                resolveField(row, key),
                dataView.fields.find((field) => field.key === key)?.format ?? 'decimal',
              )}
            </div>
            {isHighlighted && (
              <div className="visualization-ranking-badge">
                {t.rankingMetric}
              </div>
            )}
          </div>
          )
        })}
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
