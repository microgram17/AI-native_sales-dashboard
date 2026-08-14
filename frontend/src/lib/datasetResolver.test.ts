import { describe, it, expect } from 'vitest'
import { datasetToRows, resolveField, pickLabelKey, pickValueKeys } from './datasetResolver'
import { formatMetricValue } from './format'
import type { Dataset } from '../types/agent'

const rankDataset: Dataset = {
  call_id: 'c1',
  tool_name: 'sales_rank',
  status: 'success',
  result: {
    rows: [
      { rank: 1, entity: { id: 'NORD-1', name: 'Hoodie' }, metrics: { units: 40, net_sales: 1000 } },
      { rank: 2, entity: { id: 'NORD-2', name: 'Tee' }, metrics: { units: 30, net_sales: 800 } },
    ],
  },
}

describe('datasetResolver', () => {
  it('flattens nested entity/metrics into top-level fields', () => {
    const rows = datasetToRows(rankDataset)
    expect(rows).toHaveLength(2)
    expect(rows[0].name).toBe('Hoodie')
    expect(rows[0].units).toBe(40)
  })

  it('resolveField supports dot paths and last-segment fallback', () => {
    const rows = datasetToRows(rankDataset)
    expect(resolveField(rows[0], 'metrics.units')).toBe(40)
    expect(resolveField(rows[0], 'name')).toBe('Hoodie')
  })

  it('picks label and value keys with fallbacks', () => {
    const rows = datasetToRows(rankDataset)
    expect(pickLabelKey(rows, undefined)).toBe('name')
    expect(pickValueKeys(rows, ['units'])).toEqual(['units'])
    expect(pickValueKeys(rows, []).length).toBeGreaterThan(0)
  })
})

describe('formatMetricValue', () => {
  it('formats sales as SEK currency', () => {
    expect(formatMetricValue('net_sales', 1000)).toMatch(/kr|SEK/)
  })
  it('formats rates as percentages', () => {
    expect(formatMetricValue('discount_rate', 0.04)).toContain('%')
  })
  it('formats counts as grouped integers', () => {
    expect(formatMetricValue('units', 1234)).toMatch(/1[\s ]?234/)
  })
})
