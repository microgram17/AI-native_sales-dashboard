import type {
  VisualizationDataset,
  VisualizationSpec,
} from '../../types/agent'
import {
  datasetToRows,
  fieldExists,
  resolveField,
} from '../../lib/datasetResolver'
import { formatMetricValue } from '../../lib/format'
import { useTranslation } from '../../i18n/LanguageContext'
import {
  visualizationFieldLabel,
  visualizationValueLabel,
} from '../../i18n/translations'

interface Props {
  spec: VisualizationSpec
  dataset: VisualizationDataset
}

export function TableVisualization({
  spec,
  dataset,
}: Props) {
  const { language, t } = useTranslation()
  const rows = datasetToRows(dataset)

  if (rows.length === 0) {
    return <Fallback text={t.vizNoRows} />
  }

  const columns = spec.columns.filter((column) =>
    fieldExists(rows, column),
  )

  if (columns.length === 0) {
    return (
      <Fallback text={t.vizNoValidColumns} />
    )
  }

  return (
    <div className="visualization-table-wrap">
      <table className="visualization-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>
                {visualizationFieldLabel(language, column)}
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
                    ? formatMetricValue(
                        column,
                        value,
                        dataset.fields.find((field) => field.key === column)?.format,
                      )
                    : String(
                        visualizationValueLabel(language, value) ?? '',
                      )

                return (
                  <td key={column}>
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
    <div className="visualization-fallback">
      {text}
    </div>
  )
}
