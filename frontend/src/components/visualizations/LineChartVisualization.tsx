import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'
import type {
  DataFieldFormat,
  DataView,
  VisualizationSpec,
} from '../../types/agent'
import {
  dataViewToRows,
  fieldExists,
  numericFieldExists,
  resolveField,
} from '../../lib/dataView'
import {
  COLORS,
  formatShortNumber,
  longToWide,
} from '../../features/dashboard/components/visualizationUtils'
import { formatMetricValue } from '../../lib/format'
import { useTranslation } from '../../i18n/LanguageContext'
import {
  type Language,
  visualizationFieldLabel,
  visualizationValueLabel,
} from '../../i18n/translations'

interface Props {
  spec: VisualizationSpec
  dataView: DataView
}

const PRIMARY_AXIS_ID = 'primary'
const SECONDARY_AXIS_ID = 'secondary'

function formatAxisTick(
  value: unknown,
  language: Language,
  format: DataFieldFormat,
): string {
  if (
    typeof value !== 'number' ||
    Number.isNaN(value)
  ) {
    return String(value ?? '')
  }

  if (format === 'percentage_fraction') {
    const locale = language === 'sv' ? 'sv-SE' : 'en-SE'

    return `${new Intl.NumberFormat(locale, {
      maximumFractionDigits: 1,
    }).format(value * 100)}%`
  }

  return formatShortNumber(value)
}

function axisLabel(
  keys: string[],
  language: Language,
  dataView: DataView,
): string {
  if (keys.length === 0) return ''

  if (keys.length === 1) {
    const key = keys[0]
    const label = visualizationFieldLabel(language, key)
    return dataView.fields.find((field) => field.key === key)?.format === 'currency_sek'
      ? `${label} (SEK)`
      : visualizationFieldLabel(language, key)
  }

  const formats = keys.map((key) =>
    dataView.fields.find((field) => field.key === key)?.format,
  )
  if (formats.every((format) => format === 'currency_sek')) {
    return 'SEK'
  }

  if (formats.every((format) => format === 'percentage_fraction')) {
    return language === 'sv' ? 'Procent' : 'Percent'
  }

  return keys
    .map((key) => visualizationFieldLabel(language, key))
    .join(' / ')
}

const axisTick = {
  fontSize: 11,
  fill: 'var(--viz-axis)',
}

const axisLine = {
  stroke: 'var(--viz-axis-line)',
}

export function LineChartVisualization({
  spec,
  dataView,
}: Props) {
  const { language, t } = useTranslation()
  const rows = dataViewToRows(dataView)
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

  const seriesKey = spec.series_key ?? null
  const hasSeries =
    !!seriesKey &&
    fieldExists(rows, seriesKey) &&
    rows.some((row) => {
      const value = resolveField(row, seriesKey)

      return (
        value !== undefined &&
        value !== null &&
        String(value) !== ''
      )
    })

  if (hasSeries && valueKeys.length === 1) {
    const metricKey = valueKeys[0]
    const flat = rows.map((row) => ({
      [xKey]: resolveField(row, xKey),
      __series: visualizationValueLabel(
        language,
        resolveField(row, seriesKey!),
      ),
      __value: resolveField(row, metricKey),
    }))

    const { wideData, seriesValues } =
      longToWide(
        flat,
        xKey,
        '__series',
        '__value',
      )

    return (
      <ResponsiveContainer
        width="100%"
        height={280}
      >
        <LineChart
          data={wideData}
          margin={{
            top: 8,
            right: 16,
            bottom: 8,
            left: 8,
          }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="var(--viz-grid)"
          />

          <XAxis
            dataKey={xKey}
            tick={axisTick}
            axisLine={axisLine}
            tickLine={axisLine}
          />

          <YAxis
            tickFormatter={(value) =>
              formatAxisTick(
                value,
                language,
                dataView.fields.find((field) => field.key === metricKey)?.format ?? 'decimal',
              )
            }
            tick={axisTick}
            axisLine={axisLine}
            tickLine={axisLine}
          />

          <Tooltip
            formatter={(value, name) => [
              formatMetricValue(
                value,
                dataView.fields.find((field) => field.key === metricKey)?.format ?? 'decimal',
              ),
              String(name),
            ]}
            contentStyle={{
              background:
                'var(--viz-tooltip-bg)',
              border:
                '1px solid var(--viz-tooltip-border)',
              borderRadius: '8px',
              boxShadow:
                'var(--viz-tooltip-shadow)',
              color: 'var(--text-h)',
            }}
            labelStyle={{
              color: 'var(--text-h)',
              fontWeight: 600,
            }}
          />

          <Legend
            wrapperStyle={{
              fontSize: 11,
              color: 'var(--text)',
            }}
          />

          {seriesValues.map((series, i) => (
            <Line
              key={series}
              type="monotone"
              dataKey={series}
              stroke={
                COLORS[i % COLORS.length]
              }
              dot={false}
              strokeWidth={2}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    )
  }

  const data = rows.map((row) => {
    const item: Record<string, unknown> = {
      [xKey]: resolveField(row, xKey),
    }

    for (const key of valueKeys) {
      item[key] = resolveField(row, key)
    }

    return item
  })

  const requestedSecondaryKeys = new Set(
    spec.secondary_y_keys ?? [],
  )
  const secondaryKeys = valueKeys.filter(
    (key) => requestedSecondaryKeys.has(key),
  )
  const primaryKeys = valueKeys.filter(
    (key) => !requestedSecondaryKeys.has(key),
  )

  const isDualAxis =
    primaryKeys.length > 0 &&
    secondaryKeys.length > 0
  const primaryMetricKey =
    primaryKeys[0] ?? valueKeys[0]
  const secondaryMetricKey =
    secondaryKeys[0] ?? null

  return (
    <ResponsiveContainer
      width="100%"
      height={300}
    >
      <LineChart
        data={data}
        margin={{
          top: 8,
          right: isDualAxis ? 28 : 16,
          bottom: 8,
          left: isDualAxis ? 20 : 8,
        }}
      >
        <CartesianGrid
          strokeDasharray="3 3"
          stroke="var(--viz-grid)"
        />

        <XAxis
          dataKey={xKey}
          tick={axisTick}
          axisLine={axisLine}
          tickLine={axisLine}
        />

        <YAxis
          yAxisId={PRIMARY_AXIS_ID}
          orientation="left"
          tickFormatter={(value) =>
            formatAxisTick(
              value,
              language,
              dataView.fields.find((field) => field.key === primaryMetricKey)?.format ?? 'decimal',
            )
          }
          tick={axisTick}
          axisLine={axisLine}
          tickLine={axisLine}
          width={isDualAxis ? 58 : 44}
          label={
            isDualAxis
              ? {
                  value:
                    axisLabel(primaryKeys, language, dataView),
                  angle: -90,
                  position: 'insideLeft',
                  style: {
                    fontSize: 11,
                    fill: 'var(--viz-axis)',
                  },
                }
              : undefined
          }
        />

        {isDualAxis &&
          secondaryMetricKey && (
            <YAxis
              yAxisId={SECONDARY_AXIS_ID}
              orientation="right"
              tickFormatter={(value) =>
                formatAxisTick(
                  value,
                  language,
                  dataView.fields.find((field) => field.key === secondaryMetricKey)?.format ?? 'decimal',
                )
              }
              tick={axisTick}
              axisLine={axisLine}
              tickLine={axisLine}
              width={68}
              label={{
                value:
                  axisLabel(secondaryKeys, language, dataView),
                angle: 90,
                position: 'insideRight',
                style: {
                  fontSize: 11,
                  fill: 'var(--viz-axis)',
                },
              }}
            />
          )}

        <Tooltip
          formatter={(value, name) => [
            formatMetricValue(
              value,
              dataView.fields.find((field) => field.key === String(name))?.format ?? 'decimal',
            ),
            visualizationFieldLabel(language, String(name)),
          ]}
          contentStyle={{
            background:
              'var(--viz-tooltip-bg)',
            border:
              '1px solid var(--viz-tooltip-border)',
            borderRadius: '8px',
            boxShadow:
              'var(--viz-tooltip-shadow)',
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

        {valueKeys.map((key, i) => {
          const useSecondaryAxis =
            isDualAxis &&
            requestedSecondaryKeys.has(key)

          return (
            <Line
              key={key}
              type="monotone"
              dataKey={key}
              name={key}
              yAxisId={
                useSecondaryAxis
                  ? SECONDARY_AXIS_ID
                  : PRIMARY_AXIS_ID
              }
              stroke={
                COLORS[i % COLORS.length]
              }
              dot={false}
              strokeWidth={2}
            />
          )
        })}
      </LineChart>
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
