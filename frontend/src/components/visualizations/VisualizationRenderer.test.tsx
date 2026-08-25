import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { LanguageProvider } from '../../i18n/LanguageContext'
import type { DataView, DisplaySelection } from '../../types/agent'
import { VisualizationRenderer } from './VisualizationRenderer'

afterEach(cleanup)

const ranking: DataView = {
  id: 'ranking',
  kind: 'categorical',
  rows: [
    { entity_name: 'Hoodie', units: 40, net_sales: 1000 },
    { entity_name: 'Tee', units: 30, net_sales: 800 },
  ],
  fields: [
    { key: 'entity_name', role: 'dimension', format: 'text' },
    { key: 'units', role: 'measure', format: 'integer' },
    { key: 'net_sales', role: 'measure', format: 'currency_sek' },
  ],
  primary_dimension: 'entity_name',
  default_measures: ['units'],
  default_visible: true,
}

const trend: DataView = {
  id: 'trend',
  kind: 'timeseries',
  rows: [
    { period_label: '2026-01', net_sales: 1000 },
    { period_label: '2026-02', net_sales: 1200 },
  ],
  fields: [
    { key: 'period_label', role: 'dimension', format: 'text' },
    { key: 'net_sales', role: 'measure', format: 'currency_sek' },
  ],
  primary_dimension: 'period_label',
  default_measures: ['net_sales'],
  default_visible: true,
}

function renderView(display: DisplaySelection, view: DataView) {
  return render(
    <LanguageProvider>
      <VisualizationRenderer displays={[display]} dataViews={[view]} />
    </LanguageProvider>,
  )
}

describe('VisualizationRenderer', () => {
  it('renders all default metrics for a one-item ranking', () => {
    const singleRanking: DataView = {
      ...ranking,
      kind: 'metrics',
      rows: [ranking.rows[0]],
      default_measures: ['units', 'net_sales'],
    }
    const { container } = renderView(
      {
        view_id: 'ranking',
        render_as: 'default',
        measure_keys: ['units', 'net_sales'],
        title: 'Best product',
      },
      singleRanking,
    )

    expect(screen.getByText('Best product')).toBeInTheDocument()
    expect(screen.getByText('Hoodie')).toBeInTheDocument()
    expect(container.querySelectorAll('.visualization-metric-card')).toHaveLength(2)
  })

  it('maps categorical views to a bar chart', () => {
    renderView(
      {
        view_id: 'ranking',
        render_as: 'default',
        measure_keys: ['units'],
        title: 'Top products',
      },
      ranking,
    )
    expect(screen.getByText('Top products')).toBeInTheDocument()
    expect(screen.queryByText('No valid data to chart.')).not.toBeInTheDocument()
  })

  it('maps timeseries views to a line chart', () => {
    renderView(
      {
        view_id: 'trend',
        render_as: 'default',
        measure_keys: ['net_sales'],
        title: 'Monthly sales',
      },
      trend,
    )
    expect(screen.getByText('Monthly sales')).toBeInTheDocument()
  })

  it('honors a table presentation override', () => {
    renderView(
      {
        view_id: 'ranking',
        render_as: 'table',
        measure_keys: ['units'],
        title: 'Ranking table',
      },
      ranking,
    )
    expect(screen.getByText('Ranking table')).toBeInTheDocument()
    expect(screen.getByText('Hoodie')).toBeInTheDocument()
    expect(screen.getByText('Tee')).toBeInTheDocument()
  })

  it('ignores a display that references a missing view', () => {
    const { container } = render(
      <LanguageProvider>
        <VisualizationRenderer
          displays={[{
            view_id: 'missing',
            render_as: 'default',
            measure_keys: ['units'],
          }]}
          dataViews={[ranking]}
        />
      </LanguageProvider>,
    )
    expect(container.querySelector('.visualization-card')).toBeNull()
  })

  it('falls back to a table for an unknown runtime shape', () => {
    const unknown = {
      ...ranking,
      kind: 'future-shape',
    } as unknown as DataView
    renderView(
      {
        view_id: 'ranking',
        render_as: 'default',
        measure_keys: ['units'],
        title: 'Future view',
      },
      unknown,
    )
    expect(screen.getByText('Hoodie')).toBeInTheDocument()
  })
})
