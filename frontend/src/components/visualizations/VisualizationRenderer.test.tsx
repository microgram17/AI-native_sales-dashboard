import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { LanguageProvider } from '../../i18n/LanguageContext'
import { translations } from '../../i18n/translations'
import type {
  AnalyticsContext,
  DataView,
  DisplaySelection,
} from '../../types/agent'
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

const rankingContext: AnalyticsContext = {
  operation: 'ranking',
  effective_period: {
    start: '2026-01-01',
    end: '2026-12-31',
    label: '2026',
    defaulted: false,
  },
  effective_scope: {
    channels: [],
    cities: [],
    store_ids: [],
    categories: [],
    product_ids: [],
  },
  group_by: 'product',
  rank_by: 'net_sales',
  order: 'highest',
}

function renderView(
  display: DisplaySelection,
  view: DataView,
  dataContext?: AnalyticsContext,
) {
  return render(
    <LanguageProvider>
      <VisualizationRenderer
        displays={[display]}
        dataViews={[view]}
        dataContext={dataContext}
      />
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
      rankingContext,
    )

    expect(screen.getByText('Best product')).toBeInTheDocument()
    expect(screen.getByText('Hoodie')).toBeInTheDocument()
    expect(screen.getByText('Rangordnad efter:')).toBeInTheDocument()
    expect(screen.getByText('Rankningsmått')).toBeInTheDocument()
    const cards = container.querySelectorAll('.visualization-metric-card')
    expect(cards).toHaveLength(2)
    expect(cards[0]).toHaveClass('is-ranking-metric')
    expect(cards[0]).toHaveTextContent('Nettoomsättning')
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
      {
        ...rankingContext,
        rank_by: 'units',
      },
    )
    expect(screen.getByText('Top products')).toBeInTheDocument()
    expect(screen.getByText('Rangordnad efter:')).toBeInTheDocument()
    expect(screen.getByText('Sålda enheter')).toBeInTheDocument()
    expect(screen.queryByText('No valid data to chart.')).not.toBeInTheDocument()
  })

  it('provides English and Swedish ranking labels', () => {
    expect(translations.en.rankedBy).toBe('Ranked by')
    expect(translations.en.rankingMetric).toBe('Ranking metric')
    expect(translations.sv.rankedBy).toBe('Rangordnad efter')
    expect(translations.sv.rankingMetric).toBe('Rankningsmått')
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

  it('offers all requested trend measures but charts one at a time', () => {
    const multiMeasureTrend: DataView = {
      ...trend,
      rows: [
        { period_label: '2026-01', units: 10, net_sales: 1000 },
        { period_label: '2026-02', units: 12, net_sales: 1200 },
      ],
      fields: [
        { key: 'period_label', role: 'dimension', format: 'text' },
        { key: 'units', role: 'measure', format: 'integer' },
        { key: 'net_sales', role: 'measure', format: 'currency_sek' },
      ],
      default_measures: ['units'],
    }

    renderView(
      {
        view_id: 'trend',
        render_as: 'default',
        measure_keys: ['units', 'net_sales'],
        title: 'Monthly sales',
      },
      multiMeasureTrend,
    )

    const picker = screen.getByRole('combobox') as HTMLSelectElement
    const options = Array.from(picker.options)

    expect(picker.value).toBe('units')
    expect(options.map((option) => option.value)).toEqual([
      'units',
      'net_sales',
    ])
    expect(options.every((option) => !option.text.includes(' + '))).toBe(true)

    fireEvent.change(picker, { target: { value: 'net_sales' } })
    expect(picker.value).toBe('net_sales')
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
