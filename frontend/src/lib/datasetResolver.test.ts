import { describe, it, expect } from 'vitest'
import {
  datasetToRows,
  findDataset,
  resolveField,
  fieldExists,
  numericFieldExists,
} from './datasetResolver'
import type { VisualizationDataset } from '../types/agent'

const dataset: VisualizationDataset = {
  id: 'c1:ranking',
  source_call_id: 'c1',
  view: 'ranking',
  rows: [
    { rank: 1, entity_name: 'Hoodie', units: 40, net_sales: 1000 },
    { rank: 2, entity_name: 'Tee', units: 30, net_sales: 800 },
  ],
}

describe('datasetResolver', () => {
  it('finds only the exact normalized dataset id', () => {
    expect(findDataset([dataset], 'c1:ranking')).toBe(dataset)
    expect(findDataset([dataset], 'wrong')).toBeUndefined()
  })

  it('returns normalized rows unchanged', () => {
    expect(datasetToRows(dataset)).toEqual(dataset.rows)
  })

  it('resolves exact flat fields only', () => {
    const row = dataset.rows[0]
    expect(resolveField(row, 'units')).toBe(40)
    expect(resolveField(row, 'metrics.units')).toBeUndefined()
  })

  it('validates field existence and numeric fields without fallback', () => {
    expect(fieldExists(dataset.rows, 'entity_name')).toBe(true)
    expect(fieldExists(dataset.rows, 'missing')).toBe(false)
    expect(numericFieldExists(dataset.rows, 'net_sales')).toBe(true)
    expect(numericFieldExists(dataset.rows, 'entity_name')).toBe(false)
  })
})
