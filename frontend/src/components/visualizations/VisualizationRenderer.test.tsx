import { describe, it, expect, afterEach } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import { VisualizationRenderer } from './VisualizationRenderer'
import type {
  VisualizationDataset,
  VisualizationSpec,
} from '../../types/agent'

afterEach(cleanup)

const rankDataset: VisualizationDataset = {
  id: 'c1:ranking',
  source_call_id: 'c1',
  view: 'ranking',
  rows: [
    { rank: 1, entity_name: 'Hoodie', units: 40, net_sales: 1000, orders: 30 },
    { rank: 2, entity_name: 'Tee', units: 30, net_sales: 800, orders: 22 },
  ],
}

const trendDataset: VisualizationDataset = {
  id: 'c2:trend',
  source_call_id: 'c2',
  view: 'trend',
  rows: [
    { period_label: '2026-01', net_sales: 100 },
    { period_label: '2026-02', net_sales: 200 },
  ],
}

function spec(
  partial: Partial<VisualizationSpec> &
    Pick<VisualizationSpec, 'type' | 'title' | 'dataset'>,
): VisualizationSpec {
  return { y_keys: [], columns: [], ...partial }
}

describe('VisualizationRenderer', () => {
  it('renders metric_cards', () => {
    render(
      <VisualizationRenderer
        visualizations={[
          spec({
            type: 'metric_cards',
            title: 'KPIs',
            dataset: 'c1:ranking',
            y_keys: ['units', 'net_sales'],
          }),
        ]}
        datasets={[rankDataset]}
      />,
    )
    expect(screen.getByText('KPIs')).toBeInTheDocument()
  })

  it('renders bar_chart title', () => {
    render(
      <VisualizationRenderer
        visualizations={[
          spec({
            type: 'bar_chart',
            title: 'Top products',
            dataset: 'c1:ranking',
            x_key: 'entity_name',
            y_keys: ['units'],
          }),
        ]}
        datasets={[rankDataset]}
      />,
    )
    expect(screen.getByText('Top products')).toBeInTheDocument()
  })

  it('renders line_chart title', () => {
    render(
      <VisualizationRenderer
        visualizations={[
          spec({
            type: 'line_chart',
            title: 'Monthly sales',
            dataset: 'c2:trend',
            x_key: 'period_label',
            y_keys: ['net_sales'],
          }),
        ]}
        datasets={[trendDataset]}
      />,
    )
    expect(screen.getByText('Monthly sales')).toBeInTheDocument()
  })

  it('renders table with explicit columns', () => {
    render(
      <VisualizationRenderer
        visualizations={[
          spec({
            type: 'table',
            title: 'Ranking',
            dataset: 'c1:ranking',
            columns: ['rank', 'entity_name', 'units'],
          }),
        ]}
        datasets={[rankDataset]}
      />,
    )
    expect(screen.getByText('Ranking')).toBeInTheDocument()
    expect(screen.getByText('Hoodie')).toBeInTheDocument()
    expect(screen.getByText('Tee')).toBeInTheDocument()
  })

  it('does not silently fall back to another dataset', () => {
    render(
      <VisualizationRenderer
        visualizations={[
          spec({
            type: 'bar_chart',
            title: 'Broken',
            dataset: 'does-not-exist',
            x_key: 'entity_name',
            y_keys: ['units'],
          }),
        ]}
        datasets={[rankDataset]}
      />,
    )

    expect(screen.getByText('Broken')).toBeInTheDocument()
    expect(screen.getByText(/No visualization dataset/)).toBeInTheDocument()
  })
})
