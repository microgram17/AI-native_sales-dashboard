import { Component, useRef, useState, type ReactNode } from 'react'
import type {
  AnalyticsContext,
  DataView,
  DisplaySelection,
  VisualizationSpec,
} from '../../types/agent'
import { MetricCardsVisualization } from './MetricCardsVisualization'
import { BarChartVisualization } from './BarChartVisualization'
import { LineChartVisualization } from './LineChartVisualization'
import { TableVisualization } from './TableVisualization'
import { useTranslation } from '../../i18n/LanguageContext'
import { ExportMenu } from '../export/ExportMenu'
import type { ExportColumn, ExportFilter } from '../../lib/export/exportTypes'
import {
  visualizationFieldLabel,
  visualizationValueLabel,
} from '../../i18n/translations'

const REQUESTED_METRICS_OPTION = '__requested_metrics__'

interface RendererProps {
  displays: DisplaySelection[]
  dataViews: DataView[]
  dataContext?: AnalyticsContext | null
}

export function VisualizationRenderer({
  displays,
  dataViews,
  dataContext,
}: RendererProps) {
  const { language } = useTranslation()
  if (!displays || displays.length === 0) return null

  const cards = displays.flatMap((display) => {
    const view = dataViews.find((candidate) => candidate.id === display.view_id)
    if (!view) return []
    return [{
      spec: displayToSpec(display, view, language),
      dataView: view,
    }]
  })

  return (
    <div className="visualization-list">
      {cards.map(({ spec, dataView }, i) => (
        <VisualizationCard
          key={`${spec.view_id}-${i}`}
          spec={spec}
          dataView={dataView}
          dataContext={dataContext}
        />
      ))}
    </div>
  )
}

function displayToSpec(
  display: DisplaySelection,
  view: DataView,
  language: 'en' | 'sv',
): VisualizationSpec {
  const measureFields = view.fields.filter((field) => field.role === 'measure')
  const available = new Set(measureFields.map((field) => field.key))
  const requested = display.measure_keys.filter((key) => available.has(key))
  const yKeys = requested.length > 0
    ? requested
    : view.default_measures.filter((key) => available.has(key))
  const columns = view.fields.map((field) => field.key)
  const title = display.title?.trim() || visualizationFieldLabel(language, view.id)

  if (display.render_as === 'table') {
    return {
      view_id: view.id,
      type: 'table',
      title,
      y_keys: [],
      columns,
    }
  }

  if (view.kind === 'metrics') {
    return {
      view_id: view.id,
      type: 'metric_cards',
      title,
      y_keys: yKeys,
      selectable_y_keys: measureFields.map((field) => field.key),
      columns: [],
    }
  }

  const primaryFormat = measureFields.find((field) => field.key === yKeys[0])?.format
  const secondaryYKeys = yKeys.slice(1).filter((key) =>
    measureFields.find((field) => field.key === key)?.format !== primaryFormat,
  )

  if (view.kind === 'categorical' || view.kind === 'timeseries') {
    return {
      view_id: view.id,
      type: view.kind === 'timeseries' ? 'line_chart' : 'bar_chart',
      title,
      x_key: view.primary_dimension,
      y_keys: yKeys,
      secondary_y_keys: secondaryYKeys,
      selectable_y_keys: measureFields.map((field) => field.key),
      series_key: view.series_dimension,
      columns: [],
    }
  }

  return {
    view_id: view.id,
    type: 'table',
    title,
    y_keys: [],
    columns,
  }
}

function VisualizationCard({
  spec,
  dataView,
  dataContext,
}: {
  spec: VisualizationSpec
  dataView: DataView
  dataContext?: AnalyticsContext | null
}) {
  const { language, t } = useTranslation()
  const targetRef = useRef<HTMLDivElement>(null)
  const rankingMetric =
    dataContext?.operation === 'ranking' && dataContext.rank_by
      ? dataContext.rank_by
      : null

  const selectableMetrics = Array.from(new Set(spec.selectable_y_keys ?? [])).filter(
    (key) => numericMetricExists(dataView, key),
  )

  const requestedMetrics = spec.y_keys.filter((key) =>
    numericMetricExists(dataView, key),
  )

  const hasRequestedMetricCombination =
    requestedMetrics.length > 1

  const defaultSelection = hasRequestedMetricCombination
    ? REQUESTED_METRICS_OPTION
    : (
        requestedMetrics[0] ??
        selectableMetrics[0] ??
        ''
      )

  const [selectedMetric, setSelectedMetric] =
    useState(defaultSelection)

  const effectiveSelection =
    selectedMetric === REQUESTED_METRICS_OPTION &&
    hasRequestedMetricCombination
      ? REQUESTED_METRICS_OPTION
      : selectableMetrics.includes(selectedMetric)
        ? selectedMetric
        : defaultSelection

  const hasMetricSelector =
    spec.type === 'line_chart' &&
    selectableMetrics.length > 1 &&
    !!effectiveSelection

  const effectiveSpec: VisualizationSpec =
    !hasMetricSelector ||
    effectiveSelection === REQUESTED_METRICS_OPTION
      ? spec
      : {
          ...spec,
          y_keys: [effectiveSelection],
          secondary_y_keys: [],
        }

  const exportColumns = getVisualizationExportColumns(
    effectiveSpec,
    dataView,
    language,
  )
  const exportFilters = getContextFilters(dataContext, language)

  return (
    <div
      ref={targetRef}
      className="visualization-card"
    >
      <div className="visualization-card-header">
        <div className="visualization-title">
          {spec.title}
        </div>

        <ExportMenu
          targetRef={targetRef}
          title={spec.title}
          rows={dataView.rows}
          columns={exportColumns}
          filters={exportFilters}
        />
      </div>

      {rankingMetric && (
        <div className="visualization-ranking-basis">
          <span>{t.rankedBy}:</span>
          <strong>{visualizationFieldLabel(language, rankingMetric)}</strong>
        </div>
      )}

      {hasMetricSelector && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            marginBottom: '0.75rem',
            fontSize: '0.8125rem',
          }}
        >
          <span
            style={{
              color: 'var(--muted)',
              fontWeight: 500,
            }}
          >
            {t.metric}
          </span>
          <select
            aria-label={t.metric}
            value={effectiveSelection}
            onChange={(event) =>
              setSelectedMetric(event.target.value)
            }
            style={{
              padding: '0.25rem 0.5rem',
              fontSize: '0.8125rem',
              borderRadius: '4px',
              border: '1px solid var(--border, #334155)',
              background: 'var(--surface, #1e293b)',
              color: 'inherit',
              cursor: 'pointer',
            }}
          >
            {hasRequestedMetricCombination && (
              <option value={REQUESTED_METRICS_OPTION}>
                {requestedMetrics
                  .map((metric) =>
                    visualizationFieldLabel(language, metric),
                  )
                  .join(' + ')}
              </option>
            )}

            {selectableMetrics.map((metric) => (
              <option key={metric} value={metric}>
                {visualizationFieldLabel(language, metric)}
              </option>
            ))}
          </select>
        </div>
      )}

      <VizBoundary fallbackText={t.vizRenderError}>
        <VisualizationBody
          spec={effectiveSpec}
          dataView={dataView}
          highlightedMetric={rankingMetric}
        />
      </VizBoundary>
    </div>
  )
}


function numericMetricExists(
  dataView: DataView,
  key: string,
): boolean {
  const values = dataView.rows
    .map((row) => row[key])
    .filter((value) => value != null)

  return (
    values.length > 0 &&
    values.every(
      (value) =>
        typeof value === 'number' &&
        !Number.isNaN(value),
    )
  )
}


function getVisualizationExportColumns(
  spec: VisualizationSpec,
  dataView: DataView,
  language: 'en' | 'sv',
): ExportColumn[] {
  const firstRow = dataView.rows[0] ?? {}

  let keys: string[]

  if (spec.type === 'table') {
    keys = spec.columns
  } else if (spec.type === 'metric_cards') {
    const identityKeys = [
      'entity_name',
      'product_name',
      'category',
      'store_name',
      'city',
      'channel',
    ].filter((key) => key in firstRow)

    keys = [...identityKeys, ...spec.y_keys]
  } else {
    keys = [
      spec.x_key,
      spec.series_key,
      ...spec.y_keys,
    ].filter((key): key is string => !!key)
  }

  return Array.from(new Set(keys))
    .filter((key) =>
      dataView.rows.some((row) => Object.prototype.hasOwnProperty.call(row, key)),
    )
    .map((key) => ({
      key,
      label: visualizationFieldLabel(language, key),
    }))
}

function getContextFilters(
  context: AnalyticsContext | null | undefined,
  language: 'en' | 'sv',
): ExportFilter[] {
  if (!context) return []

  const filters: ExportFilter[] = [
    {
      label: visualizationFieldLabel(language, 'period_start'),
      value: context.effective_period.start,
    },
    {
      label: visualizationFieldLabel(language, 'period_end'),
      value: context.effective_period.end,
    },
  ]

  for (const [key, value] of Object.entries(context.effective_scope ?? {})) {
    if (
      value == null ||
      (Array.isArray(value) && value.length === 0)
    ) {
      continue
    }

    filters.push({
      label: visualizationFieldLabel(language, key),
      value: translateFilterValue(language, value),
    })
  }

  return filters
}

function translateFilterValue(
  language: 'en' | 'sv',
  value: unknown,
): unknown {
  if (Array.isArray(value)) {
    return value.map((item) => visualizationValueLabel(language, item))
  }

  return visualizationValueLabel(language, value)
}

function VisualizationBody({
  spec,
  dataView,
  highlightedMetric,
}: {
  spec: VisualizationSpec
  dataView: DataView
  highlightedMetric?: string | null
}) {
  switch (spec.type) {
    case 'metric_cards':
      return (
        <MetricCardsVisualization
          spec={spec}
          dataView={dataView}
          highlightedMetric={highlightedMetric}
        />
      )
    case 'bar_chart':
      return (
        <BarChartVisualization
          spec={spec}
          dataView={dataView}
        />
      )
    case 'line_chart':
      return (
        <LineChartVisualization
          spec={spec}
          dataView={dataView}
        />
      )
    case 'table':
      return (
        <TableVisualization
          spec={spec}
          dataView={dataView}
        />
      )
    default:
      return (
        <LocalizedUnsupportedFallback />
      )
  }
}

function LocalizedUnsupportedFallback() {
  const { t } = useTranslation()
  return <FallbackNote text={t.vizUnsupported} />
}

function FallbackNote({ text }: { text: string }) {
  return (
    <div className="visualization-fallback">
      {text}
    </div>
  )
}

class VizBoundary extends Component<
  { children: ReactNode; fallbackText: string },
  { failed: boolean }
> {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  render() {
    if (this.state.failed) {
      return (
        <FallbackNote text={this.props.fallbackText} />
      )
    }

    return this.props.children
  }
}
