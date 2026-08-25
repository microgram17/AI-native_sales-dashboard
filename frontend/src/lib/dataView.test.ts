import { describe, expect, it } from 'vitest'
import type { DataView } from '../types/agent'
import {
  dataViewToRows,
  fieldExists,
  numericFieldExists,
  resolveField,
} from './dataView'

const dataView: DataView = {
  id: 'ranking',
  kind: 'categorical',
  rows: [
    { rank: 1, entity_name: 'Hoodie', units: 40, net_sales: 1000 },
    { rank: 2, entity_name: 'Tee', units: 30, net_sales: 800 },
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

describe('DataView utilities', () => {
  it('returns flat rows unchanged', () => {
    expect(dataViewToRows(dataView)).toEqual(dataView.rows)
  })

  it('resolves exact flat fields only', () => {
    const row = dataView.rows[0]
    expect(resolveField(row, 'units')).toBe(40)
    expect(resolveField(row, 'metrics.units')).toBeUndefined()
  })

  it('validates field existence and numeric fields without fallback', () => {
    expect(fieldExists(dataView.rows, 'entity_name')).toBe(true)
    expect(fieldExists(dataView.rows, 'missing')).toBe(false)
    expect(numericFieldExists(dataView.rows, 'net_sales')).toBe(true)
    expect(numericFieldExists(dataView.rows, 'entity_name')).toBe(false)
  })
})
