import { describe, it, expect, afterEach } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import { VisualizationRenderer } from './VisualizationRenderer'
import { LanguageProvider } from '../../i18n/LanguageContext'
import type {
  VisualizationDataset,
  VisualizationSpec,
} from '../../types/agent'

afterEach(cleanup)


function renderVisualization(
  visualizations: VisualizationSpec[],
  datasets: VisualizationDataset[],
) {
  return render(
    <LanguageProvider>
      <VisualizationRenderer
        visualizations={visualizations}
        datasets={datasets}
      />
    </LanguageProvider>,
  )
}

const rankDataset: VisualizationDataset = {
  id: 'c1:ranking',
  source_call_id: 'c1',
  view: 'ranking',
  rows: [
    {
      rank: 1,
      entity_name: 'Hoodie',
      units: 40,
      net_sales: 1000,
      orders: 30,
    },
    {
      rank: 2,
      entity_name: 'Tee',
      units: 30,
      net_sales: 800,
      orders: 22,
    },
  ],
}

const trendDataset: VisualizationDataset = {
  id: 'c2:trend',
  source_call_id: 'c2',
  view: 'trend',
  rows: [
    {
      period_label: '2026-01',
      units: 1114,
      net_sales: 577975.25,
    },
    {
      period_label: '2026-02',
      units: 923,
      net_sales: 534170.10,
    },
  ],
}

function spec(
  partial: Partial<VisualizationSpec> &
    Pick<VisualizationSpec, 'type' | 'title' | 'dataset'>,
): VisualizationSpec {
  return {
    y_keys: [],
    secondary_y_keys: [],
    columns: [],
    ...partial,
  }
}

describe('VisualizationRenderer', () => {
  it('renders metric_cards', () => {
    renderVisualization(
      [
          spec({
            type: 'metric_cards',
            title: 'KPIs',
            dataset: 'c1:ranking',
            y_keys: ['units', 'net_sales'],
          }),
        ],
      [rankDataset],
    )

    expect(
      screen.getByText('KPIs'),
    ).toBeInTheDocument()
    expect(screen.getByText('Sålda enheter')).toBeInTheDocument()
    expect(screen.getByText('Nettoomsättning')).toBeInTheDocument()
  })

  it('renders bar_chart title', () => {
    renderVisualization(
      [
          spec({
            type: 'bar_chart',
            title: 'Top products',
            dataset: 'c1:ranking',
            x_key: 'entity_name',
            y_keys: ['units'],
          }),
        ],
      [rankDataset],
    )

    expect(
      screen.getByText('Top products'),
    ).toBeInTheDocument()
  })

  it('renders a single-axis line_chart', () => {
    renderVisualization(
      [
          spec({
            type: 'line_chart',
            title: 'Monthly sales',
            dataset: 'c2:trend',
            x_key: 'period_label',
            y_keys: ['net_sales'],
          }),
        ],
      [trendDataset],
    )

    expect(
      screen.getByText('Monthly sales'),
    ).toBeInTheDocument()
    expect(
      screen.queryByText('No valid data to chart.'),
    ).not.toBeInTheDocument()
  })

  it('renders a dual-axis line_chart', () => {
    renderVisualization(
      [
          spec({
            type: 'line_chart',
            title: 'Monthly units and net sales',
            dataset: 'c2:trend',
            x_key: 'period_label',
            y_keys: ['units', 'net_sales'],
            secondary_y_keys: ['net_sales'],
          }),
        ],
      [trendDataset],
    )

    expect(
      screen.getByText('Monthly units and net sales'),
    ).toBeInTheDocument()
    expect(
      screen.queryByText('No valid data to chart.'),
    ).not.toBeInTheDocument()
  })

  it('renders table with explicit columns', () => {
    renderVisualization(
      [
          spec({
            type: 'table',
            title: 'Ranking',
            dataset: 'c1:ranking',
            columns: [
              'rank',
              'entity_name',
              'units',
            ],
          }),
        ],
      [rankDataset],
    )

    expect(
      screen.getByText('Ranking'),
    ).toBeInTheDocument()
    expect(
      screen.getByText('Hoodie'),
    ).toBeInTheDocument()
    expect(
      screen.getByText('Tee'),
    ).toBeInTheDocument()
  })

  it('does not silently fall back to another dataset', () => {
    renderVisualization(
      [
          spec({
            type: 'bar_chart',
            title: 'Broken',
            dataset: 'does-not-exist',
            x_key: 'entity_name',
            y_keys: ['units'],
          }),
        ],
      [rankDataset],
    )

    expect(
      screen.getByText('Broken'),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/No visualization dataset/),
    ).toBeInTheDocument()
  })
})
