import { describe, it, expect, afterEach } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import { VisualizationRenderer } from './VisualizationRenderer'
import type { Dataset, VisualizationSpec } from '../../types/agent'

afterEach(cleanup)

const rankDataset: Dataset = {
  call_id: 'c1',
  tool_name: 'sales_rank',
  status: 'success',
  result: {
    rows: [
      { rank: 1, entity: { id: 'NORD-1', name: 'Hoodie' }, metrics: { units: 40, net_sales: 1000, orders: 30 } },
      { rank: 2, entity: { id: 'NORD-2', name: 'Tee' }, metrics: { units: 30, net_sales: 800, orders: 22 } },
    ],
  },
}

const trendDataset: Dataset = {
  call_id: 'c2',
  tool_name: 'sales_trend',
  status: 'success',
  result: {
    rows: [
      { period_label: '2026-01', metrics: { net_sales: 100 } },
      { period_label: '2026-02', metrics: { net_sales: 200 } },
    ],
  },
}

function spec(partial: Partial<VisualizationSpec> & Pick<VisualizationSpec, 'type' | 'title' | 'dataset'>): VisualizationSpec {
  return { y_keys: [], ...partial }
}

describe('VisualizationRenderer', () => {
  it('renders metric_cards', () => {
    render(
      <VisualizationRenderer
        visualizations={[spec({ type: 'metric_cards', title: 'KPIs', dataset: 'c1', y_keys: ['units', 'net_sales'] })]}
        datasets={[rankDataset]}
      />,
    )
    expect(screen.getByText('KPIs')).toBeInTheDocument()
    expect(screen.getByText('Hoodie')).toBeInTheDocument()
  })

  it('renders bar_chart (title shown)', () => {
    render(
      <VisualizationRenderer
        visualizations={[spec({ type: 'bar_chart', title: 'Top products', dataset: 'c1', x_key: 'name', y_keys: ['units'] })]}
        datasets={[rankDataset]}
      />,
    )
    expect(screen.getByText('Top products')).toBeInTheDocument()
  })

  it('renders line_chart (title shown)', () => {
    render(
      <VisualizationRenderer
        visualizations={[spec({ type: 'line_chart', title: 'Monthly sales', dataset: 'c2', x_key: 'period_label', y_keys: ['net_sales'] })]}
        datasets={[trendDataset]}
      />,
    )
    expect(screen.getByText('Monthly sales')).toBeInTheDocument()
  })

  it('renders table', () => {
    render(
      <VisualizationRenderer
        visualizations={[spec({ type: 'table', title: 'Ranking', dataset: 'c1' })]}
        datasets={[rankDataset]}
      />,
    )
    expect(screen.getByText('Ranking')).toBeInTheDocument()
    expect(screen.getByText('Hoodie')).toBeInTheDocument()
    expect(screen.getByText('Tee')).toBeInTheDocument()
  })

  it('renders multiple visualizations from one response', () => {
    render(
      <VisualizationRenderer
        visualizations={[
          spec({ type: 'metric_cards', title: 'KPIs', dataset: 'c1', y_keys: ['units'] }),
          spec({ type: 'bar_chart', title: 'Bars', dataset: 'c1', x_key: 'name', y_keys: ['units'] }),
        ]}
        datasets={[rankDataset]}
      />,
    )
    expect(screen.getByText('KPIs')).toBeInTheDocument()
    expect(screen.getByText('Bars')).toBeInTheDocument()
  })

  it('does not crash on a missing dataset reference', () => {
    render(
      <VisualizationRenderer
        visualizations={[spec({ type: 'bar_chart', title: 'Broken', dataset: 'does-not-exist', y_keys: ['units'] })]}
        datasets={[]}
      />,
    )
    expect(screen.getByText('Broken')).toBeInTheDocument()
    expect(screen.getByText(/No dataset/)).toBeInTheDocument()
  })
})
