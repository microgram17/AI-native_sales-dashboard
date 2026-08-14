import { Component, type ReactNode } from 'react'
import type { Dataset, VisualizationSpec } from '../../types/agent'
import { findDataset } from '../../lib/datasetResolver'
import { MetricCardsVisualization } from './MetricCardsVisualization'
import { BarChartVisualization } from './BarChartVisualization'
import { LineChartVisualization } from './LineChartVisualization'
import { TableVisualization } from './TableVisualization'

interface RendererProps {
  visualizations: VisualizationSpec[]
  datasets: Dataset[]
}

// Renders every VisualizationSpec the backend returned. The frontend does not
// choose chart types — it renders whatever shape the backend selected.
export function VisualizationRenderer({ visualizations, datasets }: RendererProps) {
  if (!visualizations || visualizations.length === 0) return null
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '0.6rem' }}>
      {visualizations.map((spec, i) => (
        <VisualizationCard key={`${spec.dataset}-${i}`} spec={spec} datasets={datasets} />
      ))}
    </div>
  )
}

function VisualizationCard({ spec, datasets }: { spec: VisualizationSpec; datasets: Dataset[] }) {
  const dataset = findDataset(datasets, spec.dataset)
  return (
    <div
      style={{
        border: '1px solid var(--border, #334155)',
        borderRadius: '10px',
        padding: '0.75rem',
        background: 'rgba(30,41,59,0.4)',
      }}
    >
      <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.5rem' }}>{spec.title}</div>
      <VizBoundary>
        {!dataset ? (
          <FallbackNote text={`No dataset "${spec.dataset}" to visualize.`} />
        ) : (
          <VisualizationBody spec={spec} dataset={dataset} />
        )}
      </VizBoundary>
    </div>
  )
}

function VisualizationBody({ spec, dataset }: { spec: VisualizationSpec; dataset: Dataset }) {
  switch (spec.type) {
    case 'metric_cards':
      return <MetricCardsVisualization spec={spec} dataset={dataset} />
    case 'bar_chart':
      return <BarChartVisualization spec={spec} dataset={dataset} />
    case 'line_chart':
      return <LineChartVisualization spec={spec} dataset={dataset} />
    case 'table':
      return <TableVisualization spec={spec} dataset={dataset} />
    default:
      return <TableVisualization spec={spec} dataset={dataset} />
  }
}

function FallbackNote({ text }: { text: string }) {
  return <div style={{ fontSize: '0.78rem', color: 'var(--muted)' }}>{text}</div>
}

// Keeps one broken visualization from crashing the chat.
class VizBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() {
    return { failed: true }
  }
  render() {
    if (this.state.failed) return <FallbackNote text="This visualization could not be rendered." />
    return this.props.children
  }
}
