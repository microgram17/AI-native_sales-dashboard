import { Component, useRef, type ReactNode } from 'react'
import type {
  VisualizationDataset,
  VisualizationSpec,
  ToolCallInfo,
} from '../../types/agent'
import { findDataset } from '../../lib/datasetResolver'
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

interface RendererProps {
  visualizations: VisualizationSpec[]
  datasets: VisualizationDataset[]
  toolCalls?: ToolCallInfo[]
}

export function VisualizationRenderer({
  visualizations,
  datasets,
  toolCalls = [],
}: RendererProps) {
  if (!visualizations || visualizations.length === 0) return null

  return (
    <div className="visualization-list">
      {visualizations.map((spec, i) => (
        <VisualizationCard
          key={`${spec.dataset}-${i}`}
          spec={spec}
          datasets={datasets}
          toolCalls={toolCalls}
        />
      ))}
    </div>
  )
}

function VisualizationCard({
  spec,
  datasets,
  toolCalls,
}: {
  spec: VisualizationSpec
  datasets: VisualizationDataset[]
  toolCalls: ToolCallInfo[]
}) {
  const dataset = findDataset(datasets, spec.dataset)
  const { language, t } = useTranslation()
  const targetRef = useRef<HTMLDivElement>(null)

  const exportColumns = dataset
    ? getVisualizationExportColumns(spec, dataset, language)
    : []
  const exportFilters = dataset
    ? getToolCallFilters(dataset, toolCalls, language)
    : []

  return (
    <div
      ref={targetRef}
      className="visualization-card"
    >
      <div className="visualization-card-header">
        <div className="visualization-title">
          {spec.title}
        </div>

        {dataset && (
          <ExportMenu
            targetRef={targetRef}
            title={spec.title}
            rows={dataset.rows}
            columns={exportColumns}
            filters={exportFilters}
          />
        )}
      </div>

      <VizBoundary fallbackText={t.vizRenderError}>
        {!dataset ? (
          <FallbackNote text={t.vizMissingDataset(spec.dataset)} />
        ) : (
          <VisualizationBody
            spec={spec}
            dataset={dataset}
          />
        )}
      </VizBoundary>
    </div>
  )
}


function getVisualizationExportColumns(
  spec: VisualizationSpec,
  dataset: VisualizationDataset,
  language: 'en' | 'sv',
): ExportColumn[] {
  const firstRow = dataset.rows[0] ?? {}

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
      dataset.rows.some((row) => Object.prototype.hasOwnProperty.call(row, key)),
    )
    .map((key) => ({
      key,
      label: visualizationFieldLabel(language, key),
    }))
}

function getToolCallFilters(
  dataset: VisualizationDataset,
  toolCalls: ToolCallInfo[],
  language: 'en' | 'sv',
): ExportFilter[] {
  const toolCall = toolCalls.find(
    (call) => call.call_id === dataset.source_call_id,
  )
  if (!toolCall) return []

  const filters: ExportFilter[] = []

  for (const [key, value] of Object.entries(toolCall.arguments ?? {})) {
    if (key === 'scope' && value && typeof value === 'object' && !Array.isArray(value)) {
      for (const [scopeKey, scopeValue] of Object.entries(value as Record<string, unknown>)) {
        if (
          scopeValue == null ||
          (Array.isArray(scopeValue) && scopeValue.length === 0)
        ) {
          continue
        }

        filters.push({
          label: visualizationFieldLabel(language, scopeKey),
          value: translateFilterValue(language, scopeValue),
        })
      }
      continue
    }

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
  dataset,
}: {
  spec: VisualizationSpec
  dataset: VisualizationDataset
}) {
  switch (spec.type) {
    case 'metric_cards':
      return (
        <MetricCardsVisualization
          spec={spec}
          dataset={dataset}
        />
      )
    case 'bar_chart':
      return (
        <BarChartVisualization
          spec={spec}
          dataset={dataset}
        />
      )
    case 'line_chart':
      return (
        <LineChartVisualization
          spec={spec}
          dataset={dataset}
        />
      )
    case 'table':
      return (
        <TableVisualization
          spec={spec}
          dataset={dataset}
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
