import { Component, type ReactNode } from 'react'
import type {
  VisualizationDataset,
  VisualizationSpec,
} from '../../types/agent'
import { findDataset } from '../../lib/datasetResolver'
import { MetricCardsVisualization } from './MetricCardsVisualization'
import { BarChartVisualization } from './BarChartVisualization'
import { LineChartVisualization } from './LineChartVisualization'
import { TableVisualization } from './TableVisualization'
import { useTranslation } from '../../i18n/LanguageContext'

interface RendererProps {
  visualizations: VisualizationSpec[]
  datasets: VisualizationDataset[]
}

export function VisualizationRenderer({
  visualizations,
  datasets,
}: RendererProps) {
  if (!visualizations || visualizations.length === 0) return null

  return (
    <div className="visualization-list">
      {visualizations.map((spec, i) => (
        <VisualizationCard
          key={`${spec.dataset}-${i}`}
          spec={spec}
          datasets={datasets}
        />
      ))}
    </div>
  )
}

function VisualizationCard({
  spec,
  datasets,
}: {
  spec: VisualizationSpec
  datasets: VisualizationDataset[]
}) {
  const dataset = findDataset(datasets, spec.dataset)
  const { t } = useTranslation()

  return (
    <div className="visualization-card">
      <div className="visualization-title">
        {spec.title}
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
