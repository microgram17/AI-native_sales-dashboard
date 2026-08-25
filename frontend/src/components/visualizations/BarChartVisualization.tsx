import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'
import type {
  VisualizationDataset,
  VisualizationSpec,
} from '../../types/agent'
import {
  datasetToRows,
  fieldExists,
  numericFieldExists,
  resolveField,
} from '../../lib/datasetResolver'
import {
  COLORS,
} from '../../features/dashboard/components/visualizationUtils'
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

export function BarChartVisualization({
  spec,
  dataset,
}: Props) {
  const { language, t } = useTranslation()
  const rows = datasetToRows(dataset)
  const xKey = spec.x_key ?? null
  const valueKeys = spec.y_keys

  if (
    rows.length === 0 ||
    !xKey ||
    !fieldExists(rows, xKey) ||
    valueKeys.length === 0 ||
    !valueKeys.every((key) =>
      numericFieldExists(rows, key),
    )
  ) {
    return <Fallback text={t.vizNoChartData} />
  }

  const data = rows.map((row) => {
    const item: Record<string, unknown> = {
      [xKey]: visualizationValueLabel(
        language,
        resolveField(row, xKey),
      ),
    }

    for (const key of valueKeys) {
      item[key] = resolveField(row, key)
    }

    return item
  })
  const primaryFormat = dataset.fields.find(
    (field) => field.key === valueKeys[0],
  )?.format
  const formatTick = (value: unknown) =>
    formatMetricValue(valueKeys[0], value, primaryFormat)

  const longestLabel = Math.max(
    ...data.map((item) =>
      String(item[xKey] ?? '').length,
    ),
  )
  const horizontal =
    data.length > 6 || longestLabel > 16

  return (
    <ResponsiveContainer
      width="100%"
      height={Math.max(
        240,
        horizontal ? data.length * 34 : 260,
      )}
    >
      <BarChart
        data={data}
        layout={horizontal ? 'vertical' : 'horizontal'}
        margin={{
          top: 8,
          right: 16,
          bottom: 8,
          left: horizontal ? 24 : 8,
        }}
      >
        <CartesianGrid
          strokeDasharray="3 3"
          stroke="var(--viz-grid)"
        />

        {horizontal ? (
          <>
            <XAxis
              type="number"
              tickFormatter={formatTick}
              tick={{
                fontSize: 11,
                fill: 'var(--viz-axis)',
              }}
              axisLine={{
                stroke: 'var(--viz-axis-line)',
              }}
              tickLine={{
                stroke: 'var(--viz-axis-line)',
              }}
            />
            <YAxis
              type="category"
              dataKey={xKey}
              width={160}
              tick={{
                fontSize: 11,
                fill: 'var(--viz-axis)',
              }}
              axisLine={{
                stroke: 'var(--viz-axis-line)',
              }}
              tickLine={{
                stroke: 'var(--viz-axis-line)',
              }}
              interval={0}
            />
          </>
        ) : (
          <>
            <XAxis
              dataKey={xKey}
              tick={{
                fontSize: 11,
                fill: 'var(--viz-axis)',
              }}
              axisLine={{
                stroke: 'var(--viz-axis-line)',
              }}
              tickLine={{
                stroke: 'var(--viz-axis-line)',
              }}
              interval={0}
              angle={-15}
              textAnchor="end"
              height={50}
            />
            <YAxis
              tickFormatter={formatTick}
              tick={{
                fontSize: 11,
                fill: 'var(--viz-axis)',
              }}
              axisLine={{
                stroke: 'var(--viz-axis-line)',
              }}
              tickLine={{
                stroke: 'var(--viz-axis-line)',
              }}
            />
          </>
        )}

        <Tooltip
          formatter={(value, name) => [
            formatMetricValue(
              String(name),
              value,
              dataset.fields.find((field) => field.key === String(name))?.format,
            ),
            visualizationFieldLabel(language, String(name)),
          ]}
          contentStyle={{
            background: 'var(--viz-tooltip-bg)',
            border:
              '1px solid var(--viz-tooltip-border)',
            borderRadius: '8px',
            boxShadow: 'var(--viz-tooltip-shadow)',
            color: 'var(--text-h)',
          }}
          labelStyle={{
            color: 'var(--text-h)',
            fontWeight: 600,
          }}
        />

        {valueKeys.length > 1 && (
          <Legend
            formatter={(value) =>
              visualizationFieldLabel(language, String(value))
            }
            wrapperStyle={{
              fontSize: 11,
              color: 'var(--text)',
            }}
          />
        )}

        {valueKeys.map((key, i) => (
          <Bar
            key={key}
            dataKey={key}
            name={key}
            fill={COLORS[i % COLORS.length]}
            radius={[3, 3, 3, 3]}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  )
}

function Fallback({ text }: { text: string }) {
  return (
    <div className="visualization-fallback">
      {text}
    </div>
  )
}
